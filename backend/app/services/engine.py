from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
from app.db_drivers import IntegrityError
import secrets
import time
from ..security import token_hash
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from ..connectors.parser import extract_listing, discover_links
from ..connectors.safe_http import SafeFetcher, SourceBlocked, BudgetReached
from ..db import dump,load,now,uid
from ..legacy import is_legacy_source
from .store import agent_dict,upsert_listing,link_agent,property_dict
from .hermes import HermesClient
from .llm import ChatModelClient, ModelUnavailable
from .scout import ScoutModel, ModelSlow, MIN_CALL_SECONDS, digest_page, plan_page, needs_model, open_points, extract as scout_extract
from .operations import notify, source_failed, source_succeeded
from .worker_lock import WorkerLock, PostgresWorkerLock
from ..connectors.sitemap import sitemap_links

log=logging.getLogger('vedra.engine')

# What the team reads in run events and notifications: plain words and what to do next.
# Messages written for them (SourceBlocked, ValueError, ModelUnavailable) pass through; a Python error
# becomes the fallback sentence and its type and detail go to the log only.
STATUS_WORDS={'completed':'completata','partial':'parziale','failed':'non riuscita','cancelled':'annullata'}
SOURCE_STOPPED='Lettura della fonte interrotta da un errore imprevisto. Riprova più tardi; se si ripete, controlla la fonte in Fonti.'
RUN_STOPPED='Esecuzione interrotta da un errore imprevisto. Gli annunci già letti restano salvati; riprova più tardi.'
RUN_TIMEOUT='Tempo massimo dell’esecuzione superato. Gli annunci già letti restano salvati; riprova o riduci le fonti della ricerca.'


# Connector refusals keep their technical wording in the source's last error (Fonti shows it on request);
# the notification and the run log say what happened and what to do, in the team's words.
SOURCE_WORDS=(
    (re.compile(r'Challenge',re.I),'Il sito chiede una verifica anti-robot: Vedra non la aggira. Usa gli avvisi email o Vedra Capture.'),
    (re.compile(r'allowlist'),'Il sito non è abilitato sul server: chiedi al referente tecnico di aggiungerlo.'),
    (re.compile(r'BROWSER_ENABLED|extra browser'),'Il browser del server non è attivo: chiedi al referente tecnico di attivarlo.'),
    (re.compile(r'robots\.txt non verificabile'),'Le regole di accesso del sito non sono leggibili ora: riprova più tardi.'),
    (re.compile(r'robots\.txt'),'Il sito esclude la lettura automatica di queste pagine: Vedra rispetta la sua scelta.'),
    (re.compile(r'blocca l’accesso automatico \(HTTP \d+\)'),'Il sito blocca l’accesso automatico: Vedra non aggira il blocco. Usa un’altra fonte, gli avvisi email o Vedra Capture.'),
    (re.compile(r'risponde HTTP \d+'),'Il sito non ha risposto correttamente. Riprova più tardi; se si ripete, controlla l’indirizzo in Fonti.'),
    (re.compile(r'non risolve'),'Indirizzo del sito non raggiungibile: controlla che sia scritto correttamente in Fonti.'),
)


def count(n,one,many):
    return f'{n} {one if n==1 else many}'


def plain_source(message):
    return next((plain for pattern,plain in SOURCE_WORDS if pattern.search(message)),message)


def plain_error(exc,fallback):
    from pydantic import ValidationError
    if isinstance(exc,(SourceBlocked,ModelUnavailable)) or (isinstance(exc,ValueError) and not isinstance(exc,ValidationError)):
        return str(exc)[:500]
    log.warning('%s: %s',type(exc).__name__,str(exc)[:500])
    return fallback


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
        self.deadlines={}
        self.active_task=None
        self.last_tick=None
        self.run_capabilities={}
        self.worker_lock=PostgresWorkerLock(db) if db.dialect=='postgres' else WorkerLock(settings.data_dir / 'worker.lock')
        self.instance_id=uid()
        self.started_at=now()
        self.alerts_task=None
        self.alerts_due=0.0

    def enqueue(self,agent_id: str,trigger='manual') -> dict:
        row=self.db.one('SELECT * FROM agents WHERE id=?',(agent_id,))
        if not row: raise ValueError('Agente non trovato.')
        agent=agent_dict(row)
        source_rows=self.db.all('SELECT id,kind,enabled,config FROM sources')
        selected=[s for s in source_rows if s['id'] in agent['source_ids']]
        if len(selected)!=len(set(agent['source_ids'])) or not all(s['enabled'] for s in selected):
            raise ValueError('Una fonte è assente o disabilitata.')
        if any(is_legacy_source(s) for s in selected):
            raise ValueError('Una fonte legacy non è più utilizzabile.')
        rid=uid()
        try:
            self.db.execute('''INSERT INTO runs(id,agent_id,status,trigger,runtime,created_at,is_demo,config_snapshot)
                VALUES(?,?,'queued',?,?,?,?,?)''',(rid,agent_id,trigger,agent['runtime'],now(),0,dump(agent)))
        except IntegrityError:
            existing=self.db.one("SELECT * FROM runs WHERE agent_id=? AND status IN ('queued','running','cancelling')",(agent_id,))
            if existing: return existing
            raise
        self.db.event(rid,'queue','Esecuzione accodata. Configurazione e criteri salvati.')
        return self.db.one('SELECT * FROM runs WHERE id=?',(rid,))

    def save_stats(self,rid,stats):
        self.db.execute('UPDATE runs SET stats=? WHERE id=?',(dump(stats),rid))

    def scout_deadline(self,rid):
        """Scout stops before the run's hard limit, keeping time for the short summary calls that follow."""
        start=self.deadlines.get(rid)
        if start is None:return None
        return start-min(self.settings.run_timeout*0.2,180)

    def scout_time_left(self,rid):
        deadline=self.scout_deadline(rid)
        return float('inf') if deadline is None else deadline-asyncio.get_running_loop().time()

    @staticmethod
    def count_model_failure(stats,exc,what):
        stats[what]=stats.get(what,0)+1
        stats['errors']+=1
        key='ai_timeouts' if isinstance(exc,ModelSlow) else 'ai_failures'
        stats[key]=stats.get(key,0)+1
        if getattr(exc,'deadline',False):stats['ai_deadline']=True

    def report_unread(self,rid,stats):
        """One plain sentence when the AI service left pages or listings unread: shown on the run and notified."""
        pages,listings,sources=stats.get('ai_pages_unread',0),stats.get('ai_listings_unread',0),stats.get('ai_sources_unread',0)
        if not (pages or listings or sources or stats.get('ai_listings_partial') or stats.get('ai_deadline')):return
        parts=[]
        if pages:parts.append(f"{pages} {'pagina' if pages==1 else 'pagine'} su {stats.get('ai_pages',0)} non {'letta' if pages==1 else 'lette'}")
        if listings:parts.append(f"{listings} {'scheda non letta' if listings==1 else 'schede non lette'}")
        partial=stats.get('ai_listings_partial',0)
        if partial:parts.append(f"{partial} {'scheda letta' if partial==1 else 'schede lette'} solo dai dati strutturati")
        if sources:parts.append(f"{sources} {'fonte non aperta' if sources==1 else 'fonti non aperte'}")
        cause=('Il servizio AI ha risposto troppo lentamente' if stats.get('ai_timeouts') and not stats.get('ai_failures') else
               'Il servizio AI non ha dato risposte utilizzabili' if stats.get('ai_failures') and not stats.get('ai_timeouts') else
               'Il servizio AI ha risposto troppo lentamente o con errori')
        if stats.get('ai_deadline'):cause+=', tempo massimo della ricerca raggiunto'
        message=f"{cause}: {', '.join(parts) or 'lettura interrotta'}. Nessun annuncio è stato scartato per questo; riprova più tardi."
        stats['ai_notice']=message
        self.db.event(rid,'scout',message,'warning',{'timeouts':stats.get('ai_timeouts',0),'failures':stats.get('ai_failures',0)})
        notify(self.db,self.settings,kind='ai_unavailable',title='Ricerca parziale',body=message,run_id=rid,dedupe_key=f'ai:{rid}')

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
                if run['runtime']=='scout' and self.scout_time_left(rid)<MIN_CALL_SECONDS:
                    # The run's deadline is spent: the remaining sources are not read, and the summary says so.
                    stats['ai_deadline']=True;stats['ai_sources_unread']=stats.get('ai_sources_unread',0)+1
                    self.db.event(rid,'source',f"{source['name']}: non letta, tempo massimo della ricerca raggiunto.",'warning')
                    continue
                self.db.event(rid,'discovery',f"Acquisizione: {source['name']}.")
                try:
                    if is_legacy_source(source):
                        raise SourceBlocked('Fonte legacy ritirata. Configura una fonte operativa.')
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
                    message=plain_error(exc,SOURCE_STOPPED)
                    self.db.execute("UPDATE sources SET status='blocked',last_checked=?,last_error=? WHERE id=?",(now(),message,sid))
                    source_failed(self.db,sid,message,getattr(exc,'retry_after',0))
                    if not health or not health['failures']:
                        notify(self.db,self.settings,kind='source_blocked',title='Fonte da controllare',body=source['name']+': '+plain_source(message),
                               run_id=rid,dedupe_key=f'source:{sid}:{rid}')
                    self.db.event(rid,'source',plain_source(message),'error')
                finally:
                    self.save_stats(rid,stats)
            if run['runtime']=='scout':self.report_unread(rid,stats)
            if run['runtime'] in ('hermes','llm','scout'): self.prepare_semantic_tasks(rid)
            self.db.execute('UPDATE runs SET collected=1,stats=? WHERE id=?',(dump(stats),rid))
            self.db.event(rid,'screening',f"{count(stats['processed'],'annuncio letto','annunci letti')}; criteri e prezzi di zona applicati.",data=stats)
            return self.collect_result(rid)

    def prepare_semantic_tasks(self,rid):
        """Bind semantic work to immutable evidence, including old records not yet analyzed by AI."""
        run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        from .analysis import custom_assessment
        agent=load(run['config_snapshot']); c=agent['criteria']
        rows=self.db.all('SELECT p.*,rp.changed FROM properties p JOIN run_properties rp ON rp.property_id=p.id WHERE rp.run_id=?',(rid,))
        for row in rows:
            p=property_dict(row)
            prompt=c.get('custom_prompt','')
            needs_custom=bool(prompt) and custom_assessment(p,prompt) is None
            if not needs_custom and not row['changed'] and p['analysis'].get('engine')==run['runtime'] and (run['runtime']!='llm' or p['analysis'].get('model')==self.settings.ai_model): continue
            if p.get('availability') in ('sold','rented','withdrawn','review'):continue
            if p['city'].casefold()!=agent['city'].casefold() or p['transaction_type']!='sale' or p['currency']!='EUR': continue
            if p['price'] is None or p['price']<c.get('min_price',0) or p['price']>c['max_price'] or p['surface'] is None or p['surface']<c['min_surface']: continue
            if c.get('max_surface') and p['surface']>c['max_surface']: continue
            if c.get('property_types') and p['property_type'] not in c['property_types']: continue
            if not c.get('include_auctions',True) and p['is_auction']: continue
            payload={k:p[k] for k in ('id','title','description','city','property_type','condition','price','surface','url')}
            from .decision_facts import source_context
            payload['source_context']=source_context(p)
            payload['custom_prompt']=prompt
            payload['content_hash']=p['content_hash']
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
        from .research_brief import catalog_url
        scout=ScoutModel(self.settings,deadline=self.scout_deadline(rid)) if agent.get('runtime')=='scout' else None
        try:
            await self._collect_pages(rid,source,agent,stats,limit,config,fetch,catalog_url(agent,source),scout)
        finally:
            # Model cost is real even when the source fails half-way: always account for it.
            if scout:
                for key,value in scout.usage.items():stats['ai_'+key]=round(stats.get('ai_'+key,0)+value,6)
                self.save_stats(rid,stats)

    async def _collect_pages(self,rid,source,agent,stats,limit,config,fetch,search_url,scout):
        strong,weak,seen_pages,notes,reasons=[],[],set(),[],{}
        # Scout reads each page like a person: listings that fit the brief, other listings, sections worth
        # opening and the next page. Without Scout the configured selectors walk the result pages only.
        configured=bool(config.get('listing_url_pattern')) or config.get('listing_selector','a[href]').strip() not in ('','a','a[href]') or config.get('discovery_mode')=='sitemap'
        queue=[search_url];page_budget=max(config.get('max_pages',2),4) if scout else config.get('max_pages',2)
        unread=0
        while queue and len(seen_pages)<page_budget:
            self.check_cancel(rid)
            if scout and scout.time_left()<MIN_CALL_SECONDS:
                stats['ai_deadline']=True
                break
            page_url=queue.pop(0)
            if not page_url or page_url in seen_pages:continue
            seen_pages.add(page_url)
            try:html,final=await fetch(page_url)
            except BudgetReached as exc:
                self.db.event(rid,'discovery',f'{exc} La prossima esecuzione riprende da qui.','warning')
                break
            if config.get('discovery_mode')=='sitemap':
                discovered,next_url=sitemap_links(html,final,config.get('listing_url_pattern',''),limit),None
            else:
                discovered,next_url=discover_links(html,final,config)
            if scout:
                stats['ai_pages']=stats.get('ai_pages',0)+1
                try:plan=await plan_page(scout,digest_page(html,final),agent)
                except ModelUnavailable as exc:
                    # A model hiccup on one page is not a blocked source: keep going with what the selectors see.
                    # The page is counted as unread so the run never reports it as "nothing fitting".
                    plan={'listings':[],'others':[],'follow':[],'next':None,'note':''}
                    unread+=1;self.count_model_failure(stats,exc,'ai_pages_unread')
                    self.db.event(rid,'scout',f'Pagina non interpretata: {str(exc)[:160]}','warning',{'url':final})
                    if isinstance(exc,ModelSlow) and exc.deadline:break
                else:
                    if plan['note']:notes.append(plan['note'])
                    self.db.event(rid,'scout',f"Pagina letta: {len(plan['listings'])} annunci pertinenti, {len(plan['others'])} altri, {len(plan['follow'])} sezioni da aprire. {plan['note']}".strip(),data={'url':final,'usage':dict(scout.usage)})
                strong+=[u for u in plan['listings'] if u not in strong]
                reasons={**plan.get('reasons',{}),**reasons}
                weak+=[u for u in [*plan['others'],*(discovered if configured else [])] if u not in strong and u not in weak]
                # Specific sections first, then the next page of the same results.
                queue=[u for u in [*plan['follow'],next_url or plan['next'],*queue] if u and u not in seen_pages]
                if len(strong)>=limit:break
            else:
                strong+=[u for u in discovered if u not in strong]
                if next_url:queue.insert(0,next_url)
                if len(strong)>=limit:break
        # With written instructions only listings that fit are opened; a generic search fills up with the rest.
        specific=bool(scout and str(agent['criteria'].get('research_instructions') or '').strip())
        urls=[*strong,*([] if specific else (u for u in weak if u not in strong))][:limit]
        stats['found']+=len(urls)
        if not urls:
            if scout and (unread or stats.get('ai_deadline')):
                # Pages the model could not read prove nothing about the market: not a "no match".
                self.db.event(rid,'discovery','Pagine non lette dal servizio AI: nessuna conclusione su questa fonte.','warning')
                return
            if scout:
                # Scout read the pages and found nothing that fits: a result, not a broken source.
                stats['no_match']=stats.get('no_match',0)+1
                self.db.event(rid,'discovery','Nessun annuncio pertinente in questa fonte. '+(notes[-1] if notes else ''),'info')
                return
            raise ValueError('Nessun link annuncio trovato. Verifica i selettori: non è prova che il mercato sia vuoto.')
        self.db.event(rid,'discovery',f"{count(len(urls),'link individuato','link individuati')} entro il limite configurato"+(f" ({len(strong[:limit])} {'pertinente' if len(strong[:limit])==1 else 'pertinenti'})." if scout else '.'))
        before_processed=stats['processed']
        for position,url in enumerate(urls):
            self.check_cancel(rid)
            if scout and scout.time_left()<MIN_CALL_SECONDS:
                stats['ai_deadline']=True
                stats['ai_listings_unread']=stats.get('ai_listings_unread',0)+len(urls)-position
                break
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
                try:listing=extract_listing(html,final,config.get('fields',{}))
                except ValueError:
                    if not scout:raise
                    listing=None
                if scout and needs_model(listing):
                    try:listing=await scout_extract(scout,html,final,listing)
                    except ModelUnavailable as exc:
                        if listing is None:
                            # Not read, not rejected: counted apart from pages that are not listings.
                            self.count_model_failure(stats,exc,'ai_listings_unread')
                            self.save_stats(rid,stats)
                            self.db.event(rid,'extract',f'Scheda non letta dal servizio AI: {str(exc)[:160]}','warning',{'url':url})
                            if isinstance(exc,ModelSlow) and exc.deadline:
                                stats['ai_listings_unread']+=len(urls)-position-1
                                break
                            continue
                        # Kept from structured data, but the fields only the model reads (contact, condition...) are missing.
                        self.count_model_failure(stats,exc,'ai_listings_partial')
                await self.availability.enrich(listing,config.get('retain_images',False))
                await self.omi.enrich(listing,agent['city'])
                self.check_cancel(rid)
                if not config.get('retain_images',False):listing.images=[];listing.evidence.pop('images',None)
                snapshot=html if config.get('retain_raw_html',True) else dump(listing.model_dump())
                pid,created,changed=upsert_listing(self.db,self.settings,source['id'],listing,raw=snapshot,run_id=rid)
                link_agent(self.db,agent,pid)
                stats['processed']+=1;stats['new']+=created;stats['changed']+=changed and not created
                self.save_stats(rid,stats)
                detail={}
                if scout:
                    # Why the listing was opened (the card's own words) and what the page did not let Scout check.
                    detail={'fit':url in strong,'reason':reasons.get(url),'open':open_points(listing,agent)}
                self.db.event(rid,'extract',f'Acquisito: {listing.title[:90]}',data={'property_id':pid,'new':bool(created),'changed':bool(changed),**detail})
            except BudgetReached as exc:
                self.db.event(rid,'extract',f'{exc} Gli annunci restanti saranno letti alla prossima esecuzione.','warning')
                break
            except RunCancelled:raise
            except SourceBlocked as exc:
                # A refusal (HTTP 401/403/429, challenge, robots) stops the source; a single page that does not
                # load is that page's problem.
                if not scout or getattr(exc,'retry_after',0) or any(k in str(exc) for k in ('blocca','Challenge','robots','bloccata')):raise
                stats['errors']+=1
                self.save_stats(rid,stats)
                self.db.event(rid,'extract',f'Pagina non caricata: {str(exc)[:200]}','warning',{'url':url})
            except Exception as exc:
                stats['errors']+=1
                self.save_stats(rid,stats)
                self.db.event(rid,'extract',plain_error(exc,'Scheda non leggibile: dati mancanti o in un formato inatteso.')[:240],'warning',{'url':url})
        if stats['processed']==before_processed:
            if scout and stats.get('ai_listings_unread'):return
            if scout:
                self.db.event(rid,'extract','Nessuna scheda leggibile tra quelle aperte: riproverà alla prossima esecuzione.','warning')
                return
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
            # Listings the AI service could not read are unread, not failed: the run is partial and says why.
            if status=='failed' and stats.get('ai_notice') and (stats.get('sources_ok') or 0)+stats.get('ai_sources_unread',0)>=stats.get('sources_total',1) \
                    and (stats.get('sources_ok') or stats.get('ai_sources_unread')):
                status='partial'
        if status=='partial' and not error and stats.get('ai_notice'):
            error=stats['ai_notice']
        self.db.execute('UPDATE runs SET status=?,finished_at=?,stats=?,error=? WHERE id=?',(status,now(),dump(stats),error,rid))
        agent=self.db.one('SELECT * FROM agents WHERE id=?',(row['agent_id'],))
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=agent['interval_minutes'])).isoformat(timespec='seconds') if agent['active'] and agent['interval_minutes'] else None
        self.db.execute('UPDATE agents SET next_run=? WHERE id=?',(nxt,row['agent_id']))
        self.db.event(rid,'finish',f'Esecuzione {STATUS_WORDS.get(status,status)}. {count(stats.get("qualified",0),"annuncio compatibile","annunci compatibili")} con i criteri.', 'error' if status=='failed' else 'info')
        self.collect_locks.pop(rid,None)
        self.deadlines.pop(rid,None)
        self.run_capabilities.pop(rid,None)
        self.db.execute('DELETE FROM run_capabilities WHERE run_id=?',(rid,))

    async def execute(self,rid):
        try:
            self.deadlines[rid]=asyncio.get_running_loop().time()+self.settings.run_timeout
            async with asyncio.timeout(self.settings.run_timeout):
                await self._execute(rid)
        except TimeoutError:
            self.finish(rid,'failed',RUN_TIMEOUT)

    async def _execute(self,rid):
        run=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        self.db.execute("UPDATE runs SET status='running',started_at=? WHERE id=? AND status='queued'",(now(),rid))
        remote_id=None
        try:
            self.check_cancel(rid)
            if run['runtime']=='llm':
                await self.collect(rid)
                await self.classify_with_model(rid)
            elif run['runtime']=='scout':
                await self.collect(rid)
                pending=self.db.one('SELECT COUNT(*) n FROM semantic_tasks WHERE run_id=? AND submitted=0',(rid,))['n']
                if pending:await self.classify_with_model(rid)
                else:
                    self.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
                    self.db.event(rid,'classify','Nessun annuncio nuovo o cambiato da analizzare.')
            elif run['runtime']=='hermes':
                # Online runs start Hermes before collection; archive analysis can skip idle turns.
                online=load(run['config_snapshot']).get('criteria',{}).get('online_discovery',False)
                has_work=online or bool((await self.collect(rid))['properties'])
                if not has_work:
                    self.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
                    self.db.event(rid,'classify','Nessun annuncio nuovo da analizzare: nessun modello AI usato.')
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
                    self.db.event(rid,'hermes','Hermes avviato.')
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
                self.db.event(rid,'classify','Analisi completata con le regole, senza modello AI.')
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
            message=plain_error(exc,RUN_STOPPED)
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
        runtime=self.db.one('SELECT runtime FROM runs WHERE id=?',(rid,))['runtime']
        skipped=0
        for task in tasks[:self.settings.max_ai_listings]:
            self.check_cancel(rid)
            try:analysis,usage=await client.classify(load(task['payload']))
            except ModelUnavailable as exc:
                # Scout already stored the listing; one unverifiable summary must not discard the whole search.
                if runtime!='scout':raise
                skipped+=1
                self.db.event(rid,'classify',f'Sintesi AI non validata, annuncio conservato senza sintesi: {str(exc)[:160]}','warning',{'property_id':task['property_id']})
                self.db.execute('UPDATE semantic_tasks SET submitted=1 WHERE run_id=? AND property_id=?',(rid,task['property_id']))
                continue
            self.check_cancel(rid)
            current=self.db.one('SELECT content_hash FROM properties WHERE id=?',(task['property_id'],))
            if not current or current['content_hash']!=task['content_hash']:
                raise ValueError('Annuncio modificato durante l’analisi; ripetere la run.')
            refresh_analysis(self.db,task['property_id'],analysis)
            self.db.execute('INSERT INTO ai_usage VALUES(?,?,?,?,?,?,?,?,?)',
                (uid(),rid,task['property_id'],self.settings.ai_model,usage['input_tokens'],usage['output_tokens'],usage['estimated_eur'],now(),int(usage['usage_reported'])))
            self.db.execute('UPDATE semantic_tasks SET submitted=1 WHERE run_id=? AND property_id=?',(rid,task['property_id']))
            self.db.event(rid,'classify','Classificazione AI validata con evidenze.',data={'property_id':task['property_id'],**usage})
        if skipped:
            run=self.db.one('SELECT stats FROM runs WHERE id=?',(rid,))
            stats=load(run['stats'],{});stats['ai_summaries_skipped']=skipped
            self.save_stats(rid,stats)
        if len(tasks)>self.settings.max_ai_listings:
            run=self.db.one('SELECT stats FROM runs WHERE id=?',(rid,))
            stats=load(run['stats'],{});stats['errors']=stats.get('errors',0)+1
            stats['ai_deferred']=len(tasks)-self.settings.max_ai_listings
            self.save_stats(rid,stats)
            self.db.event(rid,'classify','Limite di analisi AI per questa esecuzione raggiunto: gli altri annunci saranno analizzati alla prossima.','warning')
        else:
            self.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
        if not tasks:
            self.db.event(rid,'classify','Nessun annuncio nuovo o cambiato da analizzare con l’AI.')

    def poll_alerts(self):
        # Portal alert mailbox: read-only check in a thread, one at a time, every ALERTS_POLL_MINUTES.
        clock=time.monotonic()
        if (self.alerts_task and not self.alerts_task.done()) or clock<self.alerts_due:return
        from .portal_alerts import check_mailbox
        self.alerts_due=clock+self.settings.alerts_poll_minutes*60
        self.alerts_task=asyncio.create_task(asyncio.to_thread(check_mailbox,self.db,self.settings))
        self.alerts_task.add_done_callback(lambda t:t.cancelled() or not t.exception() or log.error('Alert mailbox check failed: %s',type(t.exception()).__name__))

    async def loop(self):
        # Exactly one process/worker. See deployment guide before horizontal scaling.
        self.db.execute("UPDATE runs SET status='interrupted',finished_at=?,error='Processo riavviato: run non ripresa automaticamente.' WHERE status IN ('running','cancelling')",(now(),))
        self.db.execute("UPDATE runs SET status='cancelled',finished_at=?,error='Dati legacy ritirati.' WHERE is_demo=1 AND status='queued'",(now(),))
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
                if self.settings.scheduler and self.settings.alerts_imap_configured:self.poll_alerts()
            except Exception:
                log.exception('Worker iteration failed')
            await asyncio.sleep(0.5)
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            await self.active_task
