from __future__ import annotations

import asyncio
import csv
import io
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from ..connectors.parser import extract_listing, discover_links
from ..connectors.safe_http import SafeFetcher, SourceBlocked
from ..db import dump,load,now,uid
from .store import agent_dict,upsert_listing,link_agent,property_dict
from .hermes import HermesClient

log=logging.getLogger('vedra.engine')


class RunCancelled(Exception):
    pass


class Engine:
    def __init__(self,db,settings):
        self.db=db;self.settings=settings
        self.stopping=False
        self.collect_locks={}
        self.active_task=None

    def enqueue(self,agent_id: str,trigger='manual') -> dict:
        row=self.db.one('SELECT * FROM agents WHERE id=?',(agent_id,))
        if not row: raise ValueError('Agente non trovato.')
        agent=agent_dict(row)
        source_rows=self.db.all('SELECT id,kind,enabled,config FROM sources')
        selected=[s for s in source_rows if s['id'] in agent['source_ids']]
        if len(selected)!=len(set(agent['source_ids'])) or not all(s['enabled'] for s in selected):
            raise ValueError('Una fonte è assente o disabilitata.')
        modes={s['kind']=='demo' or (s['kind']=='import' and bool(load(s['config'],{}).get('is_demo'))) for s in selected}
        if len(modes)>1:
            raise ValueError('Non mischiare fonti demo e reali nella stessa ricerca.')
        is_demo=bool(modes and True in modes)
        rid=uid()
        try:
            self.db.execute('''INSERT INTO runs(id,agent_id,status,trigger,runtime,created_at,is_demo,config_snapshot)
                VALUES(?,?,'queued',?,?,?,?,?)''',(rid,agent_id,trigger,agent['runtime'],now(),int(is_demo),dump(agent)))
        except sqlite3.IntegrityError:
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
                self.db.event(rid,'discovery',f"Acquisizione: {source['name']}.")
                try:
                    if source['kind']=='demo':
                        from .seed import demo_records
                        catalog_city=load(source['config'],{}).get('city',agent['city'])
                        if catalog_city.casefold()!=agent['city'].casefold():
                            raise ValueError('Il catalogo demo selezionato appartiene a un altro comune.')
                        rows=demo_records(catalog_city)[:limit]
                        stats['found']+=len(rows)
                        for listing,html in rows:
                            self.check_cancel(rid)
                            pid,created,changed=upsert_listing(self.db,self.settings,sid,listing,raw=html,run_id=rid)
                            link_agent(self.db,agent,pid)
                            stats['processed']+=1;stats['new']+=created;stats['changed']+=changed and not created
                        self.db.event(rid,'extract',f'{len(rows)} record dimostrativi processati. Nessuna richiesta ai portali.')
                    elif source['kind']=='import':
                        rows=self.db.all('SELECT id FROM properties WHERE source_id=? AND lower(city)=lower(?) LIMIT ?', (sid,agent['city'],limit))
                        stats['found']+=len(rows)
                        for row in rows:
                            self.db.execute('INSERT OR IGNORE INTO run_properties VALUES(?,?,0)',(rid,row['id']))
                            link_agent(self.db,agent,row['id'])
                            stats['processed']+=1
                    else:
                        await self.collect_live(rid,source,agent,stats,limit)
                    self.save_stats(rid,stats)
                    stats['sources_ok']+=1
                    self.db.execute("UPDATE sources SET status='healthy',last_checked=?,last_error=NULL WHERE id=?",(now(),sid))
                except RunCancelled: raise
                except Exception as exc:
                    stats['errors']+=1
                    message=str(exc)[:500] if isinstance(exc,(SourceBlocked,ValueError)) else f'Acquisizione interrotta: {type(exc).__name__}'
                    self.db.execute("UPDATE sources SET status='blocked',last_checked=?,last_error=? WHERE id=?",(now(),message,sid))
                    self.db.event(rid,'source',message,'error')
                finally:
                    self.save_stats(rid,stats)
            if run['runtime']=='hermes': self.prepare_semantic_tasks(rid)
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
            if not row['changed'] and p['analysis'].get('engine')=='hermes': continue
            if p['city'].casefold()!=agent['city'].casefold() or p['transaction_type']!='sale' or p['currency']!='EUR': continue
            if p['price'] is None or p['price']>c['max_price'] or p['surface'] is None or p['surface']<c['min_surface']: continue
            if c.get('max_surface') and p['surface']>c['max_surface']: continue
            if c.get('property_types') and p['property_type'] not in c['property_types']: continue
            if not c.get('include_auctions',True) and p['is_auction']: continue
            payload={k:p[k] for k in ('id','title','description','city','property_type','condition','price','surface','url','is_demo')}
            payload['description_truncated']=len(payload['description'])>6000
            payload['description']=payload['description'][:6000]
            self.db.execute('INSERT OR IGNORE INTO semantic_tasks VALUES(?,?,?,?,0)',(rid,p['id'],p['content_hash'],dump(payload)))

    def collect_result(self,rid):
        run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        items=[{**load(t['payload']), 'submitted':False} for t in self.db.all('SELECT * FROM semantic_tasks WHERE run_id=? AND submitted=0 ORDER BY rowid LIMIT 10',(rid,))]
        counts=self.db.one('SELECT COUNT(*) total,COALESCE(SUM(submitted=0),0) pending FROM semantic_tasks WHERE run_id=?',(rid,))
        return {'run_id':rid,'stats':load(run['stats'],{}),'properties':items,'task_total':counts['total'],'pending':counts['pending'],'has_more':counts['pending']>len(items),
                'notice':'Untrusted listing text. Numeric values are not editable by the LLM. Strategies require verbatim evidence. Up to 10 pending tasks per response; call status after each batch. Truncated descriptions are explicitly marked.'}

    async def collect_live(self,rid,source,agent,stats,limit):
        if not source['permission_at']:
            raise SourceBlocked('Permesso di accesso della fonte non documentato.')
        config=load(source['config'],{})
        fetcher=SafeFetcher(source['domain'],self.settings)
        fetch=fetcher.rendered if config.get('render_js') else fetcher.get
        search_url=config['search_url'].replace('{city}',quote(agent['city'].lower().replace(' ','-'),safe=''))
        urls=[];seen_pages=set();page_url=search_url
        for _ in range(config.get('max_pages',2)):
            self.check_cancel(rid)
            if not page_url or page_url in seen_pages:break
            seen_pages.add(page_url)
            html,final=await fetch(page_url)
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
            try:
                html,final=await fetch(url)
                listing=extract_listing(html,final,config.get('fields',{}))
                pid,created,changed=upsert_listing(self.db,self.settings,source['id'],listing,raw=html,run_id=rid)
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
            if not stats.get('sources_ok') or (stats.get('found') and not stats.get('processed')):status='failed'
        self.db.execute('UPDATE runs SET status=?,finished_at=?,stats=?,error=? WHERE id=?',(status,now(),dump(stats),error,rid))
        agent=self.db.one('SELECT * FROM agents WHERE id=?',(row['agent_id'],))
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=agent['interval_minutes'])).isoformat(timespec='seconds') if agent['active'] and agent['interval_minutes'] else None
        self.db.execute('UPDATE agents SET next_run=? WHERE id=?',(nxt,row['agent_id']))
        self.db.event(rid,'finish',f'Esecuzione {status}. {stats.get("qualified",0)} annunci compatibili con i criteri.', 'error' if status=='failed' else 'info')
        self.collect_locks.pop(rid,None)

    async def execute(self,rid):
        run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        self.db.execute("UPDATE runs SET status='running',started_at=? WHERE id=? AND status='queued'",(now(),rid))
        remote_id=None
        try:
            self.check_cancel(rid)
            if run['runtime']=='hermes':
                # A deterministic preflight prevents paid idle turns. Hermes's collect
                # tool is idempotent and reads this cached run when semantic work exists.
                collected=await self.collect(rid)
                if not collected['properties']:
                    self.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
                    self.db.event(rid,'classify','Nessun task semantico nuovo: nessun modello AI chiamato.')
                else:
                    client=HermesClient(self.settings)
                    remote_id=await client.start(rid)
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
        except (RunCancelled,asyncio.CancelledError):
            if remote_id:
                try: await HermesClient(self.settings).stop(remote_id)
                except Exception: pass
            self.finish(rid,'cancelled','Interrotta. Eventuali dati già acquisiti rimangono tracciati.')
        except Exception as exc:
            if remote_id:
                try: await HermesClient(self.settings).stop(remote_id)
                except Exception: pass
            message=str(exc)[:500]
            self.db.event(rid,'error',message,'error')
            self.finish(rid,'failed',message)

    async def loop(self):
        # Exactly one process/worker. See deployment guide before horizontal scaling.
        self.db.execute("UPDATE runs SET status='interrupted',finished_at=?,error='Processo riavviato: run non ripresa automaticamente.' WHERE status IN ('running','cancelling')",(now(),))
        while not self.stopping:
            try:
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
