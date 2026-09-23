from __future__ import annotations

import asyncio
import csv
import io
import logging
from app.db_drivers import IntegrityError
import secrets
from ..security import token_hash
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from ..connectors.parser import extract_listing, discover_links
from ..connectors.safe_http import SafeFetcher, SourceBlocked
from ..db import dump,load,now,uid
from ..datasets import legacy_source
from .store import agent_dict,upsert_listing,link_agent,property_dict
from .hermes import HermesClient
from .llm import ChatModelClient
from .operations import notify, source_failed, source_succeeded
from .worker_lock import WorkerLock, PostgresWorkerLock
from ..connectors.sitemap import sitemap_links

log=logging.getLogger('vedra.engine')


class RunCancelled(Exception):
    pass


class Engine:
    def __init__(self,db,settings):
        self.db=db;self.settings=settings
        from .omi import OmiClient
        self.omi=OmiClient(settings)
        from .availability import AvailabilityChecker
        self.availability=AvailabilityChecker(settings)
        self.stopping=False
        self.collect_locks={}
        self.active_task=None
        self.last_tick=None
        self.run_capabilities={}
        self.worker_lock=PostgresWorkerLock(db) if db.dialect=='postgres' else WorkerLock(settings.data_dir / 'worker.lock')
        self.instance_id=uid()
        self.started_at=now()

    def enqueue(self,agent_id: str,trigger='manual') -> dict:
        row=self.db.one('SELECT * FROM agents WHERE id=?',(agent_id,))
        if not row: raise ValueError('Agente non trovato.')
        agent=agent_dict(row)
        source_rows=self.db.all('SELECT id,kind,enabled,config FROM sources')
        selected=[s for s in source_rows if s['id'] in agent['source_ids']]
        if len(selected)!=len(set(agent['source_ids'])) or not all(s['enabled'] for s in selected):
            raise ValueError('Una fonte è assente o disabilitata.')
        modes={s['kind']=='demo' or (s['kind']=='import' and bool(load(s['config'],{}).get('is_demo'))) for s in selected}
        if True in modes:
            raise ValueError('Le fonti dimostrative precedenti non sono più utilizzabili.')
        is_demo=False
        rid=uid()
        try:
            self.db.execute('''INSERT INTO runs(id,agent_id,status,trigger,runtime,created_at,is_demo,config_snapshot)
                VALUES(?,?,'queued',?,?,?,?,?)''',(rid,agent_id,trigger,agent['runtime'],now(),int(is_demo),dump(agent)))
        except IntegrityError:
            existing=self.db.one("SELECT * FROM runs WHERE agent_id=? AND status IN ('queued','running','cancelling')",(agent_id,))
            if existing: return existing
            raise
        self.db.event(rid,'queue','Esecuzione accodata. Configurazione e criteri salvati.')
        return self.db.one('SELECT * FROM runs WHERE id=?',(rid,))

    def save_stats(self,rid,stats):
        self.db.execute('UPDATE runs SET stats=? WHERE id=?',(dump(stats),rid))

    def check_cancel(self,rid):
        row=self.db.one('SELECT status FROM runs WHERE id=?',(rid,))
        if not row or row['status'] not in ('running','queued') or self.stopping:
            raise RunCancelled()

    async def collect(self,rid: str) -> dict:
        lock=self.collect_locks.setdefault(rid,asyncio.Lock())
        async with lock:
            run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
            if not run: raise ValueError('Run non trovata')
            self.check_cancel(rid)
            if run['collected']:
                return self.collect_result(rid)
            agent=load(run['config_snapshot'])
            stats={'found':0,'processed':0,'new':0,'changed':0,'errors':0,'sources_ok':0,'sources_total':len(agent['source_ids'])}
            limit=agent['criteria']['max_listings']
            for sid in agent['source_ids']:
                self.check_cancel(rid)
                source=self.db.one('SELECT * FROM sources WHERE id=?',(sid,))
                if not source or not source['enabled']:
                    stats['errors']+=1
                    self.db.event(rid,'source','Fonte disabilitata prima dell’esecuzione.','warning')
                    continue
                health=self.db.one('SELECT * FROM source_health WHERE source_id=?',(sid,))
                if health and health['next_retry'] and health['next_retry']>now():
                    stats['errors']+=1
                    self.db.event(rid,'source','Fonte temporaneamente in pausa dopo un errore.','warning')
                    continue
                self.db.event(rid,'discovery',f"Acquisizione: {source['name']}.")
                try:
                    if legacy_source(source):
                        raise SourceBlocked('Fonte dimostrativa ritirata. Configura una fonte reale.')
                    if source['kind']=='import':
                        rows=self.db.all('SELECT id FROM properties WHERE source_id=? AND is_demo=0 AND lower(city)=lower(?) LIMIT ?', (sid,agent['city'],limit))
                        stats['found']+=len(rows)
                        for row in rows:
                            self.db.execute('INSERT INTO run_properties VALUES(?,?,0) ON CONFLICT DO NOTHING',(rid,row['id']))
                            link_agent(self.db,agent,row['id'])
                            stats['processed']+=1
                    else:
                        await self.collect_live(rid,source,agent,stats,limit)
                    self.save_stats(rid,stats)
                    stats['sources_ok']+=1
                    source_succeeded(self.db,sid)
                    self.db.execute("UPDATE sources SET status='healthy',last_checked=?,last_error=NULL WHERE id=?",(now(),sid))
                except RunCancelled: raise
                except Exception as exc:
                    stats['errors']+=1
                    message=str(exc)[:500] if isinstance(exc,(SourceBlocked,ValueError)) else f'Acquisizione interrotta: {type(exc).__name__}'
                    self.db.execute("UPDATE sources SET status='blocked',last_checked=?,last_error=? WHERE id=?",(now(),message,sid))
                    source_failed(self.db,sid,message,getattr(exc,'retry_after',0))
                    if not health or not health['failures']:
                        notify(self.db,self.settings,kind='source_blocked',title='Fonte da controllare',body=source['name']+': '+message,
                               run_id=rid,is_demo=run['is_demo'],dedupe_key=f'source:{sid}:{rid}')
                    self.db.event(rid,'source',message,'error')
                finally:
                    self.save_stats(rid,stats)
            if run['runtime'] in ('hermes','llm'): self.prepare_semantic_tasks(rid)
            self.db.execute('UPDATE runs SET collected=1,stats=? WHERE id=?',(dump(stats),rid))
            self.db.event(rid,'screening',f"{stats['processed']} annunci strutturati; filtri e benchmark applicati in codice.",data=stats)
            return self.collect_result(rid)

    def prepare_semantic_tasks(self,rid):
        """Bind semantic work to immutable evidence, including old records not yet analyzed by AI."""
        run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        agent=load(run['config_snapshot']); c=agent['criteria']
        rows=self.db.all('SELECT p.*,rp.changed FROM properties p JOIN run_properties rp ON rp.property_id=p.id WHERE rp.run_id=?',(rid,))
        for row in rows:
            p=property_dict(row)
            if not row['changed'] and p['analysis'].get('engine')==run['runtime'] and (run['runtime']!='llm' or p['analysis'].get('model')==self.settings.ai_model): continue
            if p.get('availability') in ('sold','rented','withdrawn','review'):continue
            if p['city'].casefold()!=agent['city'].casefold() or p['transaction_type']!='sale' or p['currency']!='EUR': continue
            if p['price'] is None or p['price']<c.get('min_price',0) or p['price']>c['max_price'] or p['surface'] is None or p['surface']<c['min_surface']: continue
            if c.get('max_surface') and p['surface']>c['max_surface']: continue
            if c.get('property_types') and p['property_type'] not in c['property_types']: continue
            if not c.get('include_auctions',True) and p['is_auction']: continue
            payload={k:p[k] for k in ('id','title','description','city','property_type','condition','price','surface','url','is_demo')}
            payload['description_truncated']=len(payload['description'])>6000
            payload['description']=payload['description'][:6000]
            self.db.execute('INSERT INTO semantic_tasks VALUES(?,?,?,?,0) ON CONFLICT DO NOTHING',(rid,p['id'],p['content_hash'],dump(payload)))

    def collect_result(self,rid):
        run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        items=[{**load(t['payload']), 'submitted':False} for t in self.db.all('SELECT * FROM semantic_tasks WHERE run_id=? AND submitted=0 ORDER BY property_id LIMIT 10',(rid,))]
        counts=self.db.one('SELECT COUNT(*) total,COALESCE(SUM(CASE WHEN submitted=0 THEN 1 ELSE 0 END),0) pending FROM semantic_tasks WHERE run_id=?',(rid,))
        return {'run_id':rid,'stats':load(run['stats'],{}),'properties':items,'task_total':counts['total'],'pending':counts['pending'],'has_more':counts['pending']>len(items),
                'notice':'Untrusted listing text. Numeric values are not editable by the LLM. Strategies require verbatim evidence. Up to 10 pending tasks per response; call status after each batch. Truncated descriptions are explicitly marked.'}

    async def collect_live(self,rid,source,agent,stats,limit):
        if not source['permission_at']:
            raise SourceBlocked('Permesso di accesso della fonte non documentato.')
        config=load(source['config'],{})
        fetcher=SafeFetcher(source['domain'],self.settings)
        transport=fetcher.browse if config.get('browser_navigation') else fetcher.rendered if config.get('render_js') else fetcher.get
        async def fetch(url):
            self.db.execute('INSERT INTO source_health(source_id,requests) VALUES(?,1) ON CONFLICT(source_id) DO UPDATE SET requests=requests+1',(source['id'],))
            stats['page_requests']=stats.get('page_requests',0)+1
            return await transport(url)
        search_url=config['search_url'].replace('{city}',quote(agent['city'].lower().replace(' ','-'),safe=''))
        urls=[];seen_pages=set();page_url=search_url
        for _ in range(config.get('max_pages',2)):
            self.check_cancel(rid)
            if not page_url or page_url in seen_pages:break
            seen_pages.add(page_url)
            html,final=await fetch(page_url)
            if config.get('discovery_mode')=='sitemap':
                discovered=sitemap_links(html,final,config.get('listing_url_pattern',''),limit)
                page_url=None
            else:
                discovered,page_url=discover_links(html,final,config)
            for url in discovered:
                if url not in urls:urls.append(url)
            if len(urls)>=limit:break
        urls=urls[:limit]
        stats['found']+=len(urls)
        if not urls:
            raise ValueError('Nessun link annuncio trovato. Verifica i selettori: non è prova che il mercato sia vuoto.')
        self.db.event(rid,'discovery',f'{len(urls)} link individuati entro il limite configurato.')
        before_processed=stats['processed']
        for url in urls:
            self.check_cancel(rid)
            cached=self.db.one('SELECT p.id,c.last_detail_at FROM properties p LEFT JOIN listing_checks c ON c.property_id=p.id WHERE p.source_id=? AND p.url=?',(source['id'],url))
            cutoff=(datetime.now(timezone.utc)-timedelta(hours=config.get('detail_refresh_hours',24))).isoformat(timespec='seconds')
            if cached and cached['last_detail_at'] and cached['last_detail_at']>cutoff:
                self.db.execute('INSERT INTO run_properties VALUES(?,?,0) ON CONFLICT DO NOTHING',(rid,cached['id']))
                link_agent(self.db,agent,cached['id'])
                stats['cached']=stats.get('cached',0)+1
                stats['processed']+=1
                continue
            try:
                html,final=await fetch(url)
                listing=extract_listing(html,final,config.get('fields',{}))
                await self.availability.enrich(listing,config.get('retain_images',False))
                await self.omi.enrich(listing,agent['city'])
                self.check_cancel(rid)
                if not config.get('retain_images',False):listing.images=[];listing.evidence.pop('images',None)
                snapshot=html if config.get('retain_raw_html',True) else dump(listing.model_dump())
                pid,created,changed=upsert_listing(self.db,self.settings,source['id'],listing,raw=snapshot,run_id=rid)
                link_agent(self.db,agent,pid)
                stats['processed']+=1;stats['new']+=created;stats['changed']+=changed and not created
                self.save_stats(rid,stats)
                self.db.event(rid,'extract',f'Acquisito: {listing.title[:90]}',data={'property_id':pid,'new':bool(created),'changed':bool(changed)})
            except (SourceBlocked,RunCancelled):raise
            except Exception as exc:
                stats['errors']+=1
                self.save_stats(rid,stats)
                self.db.event(rid,'extract',f'Estrazione non riuscita: {str(exc)[:200]}','warning',{'url':url})

        if stats['processed']==before_processed:
            raise ValueError('Nessun annuncio estratto dalla fonte: controlla i selettori e il formato dei dati.')

    def finish(self,rid,status=None,error=None):
        row=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        stats=load(row['stats'],{})
        from .analysis import screen
        snapshot=load(row['config_snapshot'])
        current=self.db.all('SELECT p.* FROM properties p JOIN run_properties rp ON rp.property_id=p.id WHERE rp.run_id=?',(rid,))
        stats['qualified']=sum(screen(property_dict(p),snapshot)[0] for p in current)
        if status is None:
            status='partial' if stats.get('errors') else 'completed'
            # A verified catalog can contain only recent/irrelevant listings. An
            # empty delta is successful only after the full Hermes protocol.
            verified_discovery=(row['runtime']=='hermes' and stats.get('discovery')=='hermes'
                                and row['collected'] and row['analysis_done'])
            if not stats.get('sources_ok') or (stats.get('found') and not stats.get('processed') and not verified_discovery):
                status='failed'
        self.db.execute('UPDATE runs SET status=?,finished_at=?,stats=?,error=? WHERE id=?',(status,now(),dump(stats),error,rid))
        agent=self.db.one('SELECT * FROM agents WHERE id=?',(row['agent_id'],))
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=agent['interval_minutes'])).isoformat(timespec='seconds') if agent['active'] and agent['interval_minutes'] else None
        self.db.execute('UPDATE agents SET next_run=? WHERE id=?',(nxt,row['agent_id']))
        self.db.event(rid,'finish',f'Esecuzione {status}. {stats.get("qualified",0)} annunci compatibili con i criteri.', 'error' if status=='failed' else 'info')
        self.collect_locks.pop(rid,None)
        self.run_capabilities.pop(rid,None)
        self.db.execute('DELETE FROM run_capabilities WHERE run_id=?',(rid,))

    async def execute(self,rid):
        try:
            async with asyncio.timeout(self.settings.run_timeout):
                await self._execute(rid)
        except TimeoutError:
            self.finish(rid,'failed','Budget temporale della run esaurito; dati già acquisiti conservati.')

    async def _execute(self,rid):
        run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        self.db.execute("UPDATE runs SET status='running',started_at=? WHERE id=? AND status='queued'",(now(),rid))
        remote_id=None
        try:
            self.check_cancel(rid)
            if run['runtime']=='llm':
                await self.collect(rid)
                await self.classify_with_model(rid)
            elif run['runtime']=='hermes':
                # Online runs start Hermes before collection; archive analysis can skip idle turns.
                online=load(run['config_snapshot']).get('criteria',{}).get('online_discovery',False)
                has_work=online or bool((await self.collect(rid))['properties'])
                if not has_work:
                    self.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
                    self.db.event(rid,'classify','Nessun task semantico nuovo: nessun modello AI chiamato.')
                else:
                    client=HermesClient(self.settings)
                    capability=secrets.token_hex(32)
                    self.run_capabilities[rid]=capability
                    expires=(datetime.now(timezone.utc)+timedelta(seconds=self.settings.run_timeout)).isoformat(timespec='seconds')
                    self.db.execute('INSERT INTO run_capabilities VALUES(?,?,?) ON CONFLICT(run_id) DO UPDATE SET token_hash=excluded.token_hash,expires_at=excluded.expires_at',(rid,token_hash(capability),expires))
                    browser_required=online and any(load(s['config']).get('browser_navigation') for s in
                        (self.db.one('SELECT config FROM sources WHERE id=?',(sid,)) for sid in load(run['config_snapshot'])['source_ids']) if s)
                    if browser_required:
                        remote_id=await client.start(rid,capability,online=True,browser_required=True)
                    else:
                        remote_id=await client.start(rid,capability,online=True) if online else await client.start(rid,capability)
                    self.db.execute('UPDATE runs SET hermes_run_id=? WHERE id=?',(remote_id,rid))
                    self.db.event(rid,'hermes','Hermes avviato. Skill verticali e bridge vincolato al workflow.')
                    deadline=asyncio.get_running_loop().time()+self.settings.hermes_timeout
                    while asyncio.get_running_loop().time()<deadline:
                        self.check_cancel(rid)
                        state=await client.status(remote_id)
                        status=state.get('status')
                        if status=='completed':
                            current=self.db.one('SELECT collected,analysis_done FROM runs WHERE id=?',(rid,))
                            if not current['collected'] or not current['analysis_done']:
                                raise RuntimeError('Hermes ha terminato senza completare il protocollo collect / classify / finish.')
                            self.db.event(rid,'hermes','Hermes completato.',data={'usage':state.get('usage',{})})
                            break
                        if status in ('failed','cancelled'):
                            raise RuntimeError(f'Hermes run {status}.')
                        await asyncio.sleep(1)
                    else:
                        await client.stop(remote_id)
                        raise RuntimeError('Timeout Hermes; stop richiesto. Nessun fallback AI silenzioso.')
            else:
                await self.collect(rid)
                self.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
                self.db.event(rid,'classify','Classificazione deterministica completata. Nessun modello AI chiamato.')
            self.check_cancel(rid)
            self.finish(rid)
        except (RunCancelled,asyncio.CancelledError) as exc:
            if remote_id:
                try: await HermesClient(self.settings).stop(remote_id)
                except Exception: pass
            self.finish(rid,'cancelled','Interrotta. Eventuali dati già acquisiti rimangono tracciati.')
            if isinstance(exc,asyncio.CancelledError) and not self.stopping:
                raise
        except Exception as exc:
            if remote_id:
                try: await HermesClient(self.settings).stop(remote_id)
                except Exception: pass
            message=str(exc)[:500]
            self.db.event(rid,'error',message,'error')
            self.finish(rid,'failed',message)

    async def mail_loop(self):
        from .mail import deliver_due
        while not self.stopping:
            try:
                await deliver_due(self.db,self.settings)
            except Exception:
                log.exception('Email worker failed')
            await asyncio.sleep(2)

    async def classify_with_model(self,rid):
        from .store import refresh_analysis
        client=ChatModelClient(self.settings)
        tasks=self.db.all('SELECT * FROM semantic_tasks WHERE run_id=? AND submitted=0 ORDER BY property_id',(rid,))
        for task in tasks[:self.settings.max_ai_listings]:
            self.check_cancel(rid)
            analysis,usage=await client.classify(load(task['payload']))
            self.check_cancel(rid)
            current=self.db.one('SELECT content_hash FROM properties WHERE id=?',(task['property_id'],))
            if not current or current['content_hash']!=task['content_hash']:
                raise ValueError('Annuncio modificato durante l’analisi; ripetere la run.')
            refresh_analysis(self.db,task['property_id'],analysis)
            self.db.execute('INSERT INTO ai_usage VALUES(?,?,?,?,?,?,?,?,?)',
                (uid(),rid,task['property_id'],self.settings.ai_model,usage['input_tokens'],usage['output_tokens'],usage['estimated_eur'],now(),int(usage['usage_reported'])))
            self.db.execute('UPDATE semantic_tasks SET submitted=1 WHERE run_id=? AND property_id=?',(rid,task['property_id']))
            self.db.event(rid,'classify','Classificazione AI validata con evidenze.',data={'property_id':task['property_id'],**usage})
        if len(tasks)>self.settings.max_ai_listings:
            run=self.db.one('SELECT stats FROM runs WHERE id=?',(rid,))
            stats=load(run['stats'],{});stats['errors']=stats.get('errors',0)+1
            stats['ai_deferred']=len(tasks)-self.settings.max_ai_listings
            self.save_stats(rid,stats)
            self.db.event(rid,'classify','Budget AI raggiunto. Gli annunci rimanenti saranno analizzati in una run successiva.','warning')
        else:
            self.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
        if not tasks:
            self.db.event(rid,'classify','Nessun annuncio nuovo o cambiato: zero chiamate AI.')

    async def loop(self):
        # Exactly one process/worker. See deployment guide before horizontal scaling.
        self.db.execute("UPDATE runs SET status='interrupted',finished_at=?,error='Processo riavviato: run non ripresa automaticamente.' WHERE status IN ('running','cancelling')",(now(),))
        self.db.execute("UPDATE runs SET status='cancelled',finished_at=?,error='Dataset dimostrativo ritirato.' WHERE is_demo=1 AND status='queued'",(now(),))
        self.db.execute('DELETE FROM run_capabilities')
        while not self.stopping:
            self.worker_lock.assert_owned()
            self.last_tick=now()
            try:
                self.db.execute('INSERT INTO worker_status VALUES(?,?,?,?,0) ON CONFLICT(id) DO UPDATE SET instance_id=excluded.instance_id,last_tick=excluded.last_tick,started_at=excluded.started_at,stopping=0',
                                ('primary', self.instance_id, self.last_tick, self.started_at))
                if not self.active_task or self.active_task.done():
                    self.active_task=None
                    if self.settings.scheduler:
                        for a in self.db.all('SELECT * FROM agents WHERE active=1 AND interval_minutes>0 AND next_run<=?',(now(),)):
                            try:self.enqueue(a['id'],'schedule')
                            except ValueError:pass
                    queued=self.db.one("SELECT id FROM runs WHERE status='queued' ORDER BY created_at LIMIT 1")
                    if queued:self.active_task=asyncio.create_task(self.execute(queued['id']))
            except Exception:
                log.exception('Worker iteration failed')
            await asyncio.sleep(0.5)
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            await self.active_task
