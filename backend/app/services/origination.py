"""Hermes-directed discovery: the model selects links; code verifies source facts."""
import asyncio
import re
from functools import wraps
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, quote, urljoin

from ..connectors.parser import discover_links, extract_listing, canonical_url
from ..connectors.safe_http import SafeFetcher, SourceBlocked
from ..db import load, dump, now
from .store import upsert_listing, link_agent
from .operations import source_succeeded, source_failed


def serialized(method):
    @wraps(method)
    async def call(self,rid,*args):
        async with self.engine.collect_locks.setdefault(rid,asyncio.Lock()):
            return await method(self,rid,*args)
    return call


class Origination:
    def __init__(self, engine):
        self.engine=engine; self.db=engine.db; self.settings=engine.settings

    def context(self,rid):
        self.engine.check_cancel(rid)
        row=self.db.one('SELECT * FROM runs WHERE id=?',(rid,))
        agent=load(row['config_snapshot'])
        if row['runtime']!='hermes' or not agent['criteria'].get('online_discovery'):
            raise ValueError('Ricerca online Hermes non abilitata per questa run.')
        return row,agent

    def sources(self,agent):
        rows=[self.db.one('SELECT * FROM sources WHERE id=?',(sid,)) for sid in agent['source_ids']]
        return [s for s in rows if s and s['kind']=='html' and s['enabled'] and s['permission_at'] and s['domain'] in self.settings.live_domains]

    async def fetch(self,rid,source,fetcher,url):
        health=self.db.one('SELECT next_retry FROM source_health WHERE source_id=?',(source['id'],))
        if health and health['next_retry'] and health['next_retry']>now():
            raise ValueError('Fonte in pausa dopo un errore; riprova più tardi.')
        try:
            return await fetcher.get(url)
        except Exception as exc:
            message=str(exc)[:300] if isinstance(exc,SourceBlocked) else type(exc).__name__
            source_failed(self.db,source['id'],message,getattr(exc,'retry_after',0))
            self.db.execute("UPDATE sources SET status='blocked',last_error=?,last_checked=? WHERE id=?",(message,now(),source['id']))
            self.db.event(rid,'source',message,'error',{'source_id':source['id']})
            raise ValueError('Fonte non raggiungibile: '+message) from exc

    @serialized
    async def search(self,rid):
        row,agent=self.context(rid)
        if row['collected']:raise ValueError('Raccolta già chiusa.')
        previous=self.db.all("SELECT data FROM events WHERE run_id=? AND step='hermes_discovery'",(rid,))
        if previous:return {'criteria':agent['criteria'],'city':agent['city'],'sources':[load(x['data']) for x in previous]}
        result=[]
        for source in self.sources(agent):
            cfg=load(source['config']);fetcher=SafeFetcher(source['domain'],self.settings)
            url=cfg['search_url'].replace('{city}',quote(agent['city'].lower(),safe=''))
            links=[];pages=set();candidates=[]
            for _ in range(cfg.get('max_pages',2)):
                self.engine.check_cancel(rid)
                if not url or url in pages:break
                pages.add(url);html,final=await self.fetch(rid,source,fetcher,url)
                found,url=discover_links(html,final,cfg)
                self.engine.check_cancel(rid)
                soup=BeautifulSoup(html,'html.parser')
                for link in found:
                    anchor=next((a for a in soup.select('a[href]') if canonical_url(urljoin(final,a['href']))==link),None)
                    card=anchor.find_parent(class_='wdk-listing-card') if anchor else None
                    hint=card.select_one('.wdk-price') if card else None
                    candidates.append({'url':link,'asking_price_hint':hint.get_text(' ',strip=True) if hint else ''})
                links.extend(x for x in found if x not in links)
            data={'source_id':source['id'],'name':source['name'],'urls':links[:100],'candidates':candidates[:100],'requests':fetcher.request_count}
            self.db.event(rid,'hermes_discovery',f'Hermes ha cercato in {source["name"]}: {len(links)} link.',data=data)
            result.append(data)
        if not result:raise ValueError('Nessuna fonte online configurata e autorizzata.')
        return {'criteria':agent['criteria'],'city':agent['city'],'sources':result,'instruction':'Select candidate URLs and call acquire_listing. Only source-verified fields are saved.'}

    @serialized
    async def acquire(self,rid,url):
        row,agent=self.context(rid)
        if row['collected']:raise ValueError('Raccolta già chiusa.')
        url=canonical_url(url)
        discoveries=[load(e['data']) for e in self.db.all("SELECT data FROM events WHERE run_id=? AND step='hermes_discovery'",(rid,))]
        eligible=next((d for d in discoveries if url in d['urls']),None)
        if not eligible:raise ValueError('URL non presente nei risultati verificati di questa run.')
        source=next((s for s in self.sources(agent) if s['id']==eligible['source_id']),None)
        if not source:raise ValueError('Fonte non più disponibile.')
        existing=self.db.one('SELECT p.* FROM properties p JOIN run_properties r ON p.id=r.property_id WHERE r.run_id=? AND p.url=?',(rid,url))
        if existing:return {'property_id':existing['id'],'already_acquired':True}
        count=self.db.one('SELECT COUNT(*) n FROM run_properties r JOIN properties p ON p.id=r.property_id WHERE r.run_id=? AND p.source_id=?',(rid,source['id']))['n']
        if count>=agent['criteria']['max_listings']:raise ValueError('Limite annunci raggiunto: chiudi la raccolta.')
        cfg=load(source['config']);fetcher=SafeFetcher(source['domain'],self.settings)
        raw,final=await self.fetch(rid,source,fetcher,url)
        self.engine.check_cancel(rid)
        listing=extract_listing(raw,final,cfg.get('fields',{}))
        # A city suffix in the extracted address is evidence, not a source-wide default.
        if not listing.city and listing.address and re.search(r'\b'+re.escape(agent['city'])+r'\s*$',listing.address,re.I):
            listing.city=agent['city'];listing.evidence['city']={'method':'address suffix','value':listing.address,'source_url':final}
        if cfg.get('retain_raw_html',True):snapshot=raw
        else:
            listing.images=[];snapshot=dump(listing.model_dump())
        pid,created,changed=upsert_listing(self.db,self.settings,source['id'],listing,raw=snapshot,run_id=rid)
        link_agent(self.db,agent,pid)
        self.db.event(rid,'hermes_acquire',f'Hermes ha acquisito: {listing.title[:100]}',data={'property_id':pid,'url':final,'new':created,'changed':changed})
        self.update_progress(rid,agent)
        source_succeeded(self.db,source['id'],fetcher.request_count)
        self.db.execute("UPDATE sources SET status='healthy',last_checked=?,last_error=NULL WHERE id=?",(now(),source['id']))
        return {'property_id':pid,'listing':listing.model_dump(),'new':created,'changed':changed}

    def update_progress(self,rid,agent):
        events=[load(e['data']) for e in self.db.all("SELECT data FROM events WHERE run_id=? AND step='hermes_acquire'",(rid,))]
        discovery=[load(e['data']) for e in self.db.all("SELECT data FROM events WHERE run_id=? AND step='hermes_discovery'",(rid,))]
        stats={'found':sum(len(x['urls']) for x in discovery),'processed':len(events),'new':sum(x['new'] for x in events),'changed':sum(x['changed'] and not x['new'] for x in events),'errors':self.db.one("SELECT COUNT(*) n FROM events WHERE run_id=? AND step='source' AND level='error'",(rid,))['n'],'sources_total':len(agent['source_ids']),'sources_ok':len({urlsplit(x['url']).hostname for x in events}),'discovery':'hermes'}
        self.engine.save_stats(rid,stats)
        return stats

    @serialized
    async def complete(self,rid):
        row,agent=self.context(rid)
        if row['collected']:return self.engine.collect_result(rid)
        stats=self.update_progress(rid,agent)
        if not stats['processed']:raise ValueError('Nessun annuncio acquisito: non dichiarare una ricerca completata.')
        self.engine.prepare_semantic_tasks(rid)
        self.db.execute('UPDATE runs SET collected=1 WHERE id=?',(rid,))
        return self.engine.collect_result(rid)
