from __future__ import annotations

import asyncio
import json
import logging
import secrets
from app.db_drivers import IntegrityError
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path

from fastapi import Depends,FastAPI,HTTPException,Request,Response
from fastapi.responses import FileResponse,JSONResponse,StreamingResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .config import Settings,load_env
from .db import Database,dump,load,now,uid
from .datasets import require_real_dataset, legacy_source
from .security import (bootstrap_user,current_user,require_admin,require_editor,require_bridge,
                       LoginLimiter,create_session,verify_password,password_hash,token_hash,BodyLimitMiddleware)
from .schemas import (AgentInput,SourceInput,LoginInput,UserInput,ReviewInput,NoteInput,ImportInput,SemanticAnalysis)
from .services.engine import Engine
from .services.hermes import HermesClient,HermesUnavailable
from .services.store import property_dict,list_properties,agent_dict,refresh_analysis,link_agent
from .services.analysis import QUALITY_FIELDS,duplicate_candidates,validate_semantic
from .services.imports import import_data
from .services.exports import export_csv,export_xlsx,export_docx

log=logging.getLogger('vedra')


def create_app(settings: Settings | None=None) -> FastAPI:
    load_env()
    settings=settings or Settings()
    db=Database.from_settings(settings)
    engine=Engine(db,settings)
    from .services.omi import OmiClient
    omi=OmiClient(settings)
    limiter=LoginLimiter()

    @asynccontextmanager
    async def lifespan(app):
        db.initialize();bootstrap_user(db,settings)
        from .services.worker import serve_worker
        if settings.worker_enabled:
            engine.worker_lock.acquire()
        task = asyncio.create_task(serve_worker(engine, acquired=True)) if settings.worker_enabled else None
        try:
            yield
        finally:
            engine.stopping = True
            if task:
                await task
            db.close()



    app=FastAPI(title='Vedra Real Estate API',version=__version__,lifespan=lifespan,
                docs_url=None,openapi_url='/api/openapi.json',redoc_url=None)
    app.state.db=db;app.state.engine=engine;app.state.settings=settings
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=[x.strip() for x in settings.allowed_hosts])
    app.add_middleware(BodyLimitMiddleware,limit=5_000_000)

    @app.middleware('http')
    async def security_headers(request,call_next):
        request_id=secrets.token_hex(8)
        origin=request.headers.get('origin')
        allowed={settings.public_origin}
        if not settings.cookie_secure:
            allowed|={'http://localhost:8000','http://127.0.0.1:8000','http://testserver'}
        if request.method not in ('GET','HEAD','OPTIONS') and origin and origin not in allowed:
            return JSONResponse({'detail':'Origine non autorizzata.'},status_code=403)
        try:
            length=int(request.headers.get('content-length','0'))
        except ValueError:
            return JSONResponse({'detail':'Content-Length non valido.'},status_code=400)
        if length>5_000_000:
            return JSONResponse({'detail':'Richiesta troppo grande (massimo 5 MB).'},status_code=413)
        response=await call_next(request)
        response.headers['X-Request-ID']=request_id
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data:; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path.startswith(('/api/','/bridge/')):response.headers['Cache-Control']='no-store'
        if settings.cookie_secure:response.headers['Strict-Transport-Security']='max-age=31536000'
        return response

    @app.exception_handler(ValueError)
    async def value_error(request,exc):
        return JSONResponse({'detail':str(exc)[:700]},status_code=422)

    @app.exception_handler(HermesUnavailable)
    async def hermes_error(request,exc):
        return JSONResponse({'detail':str(exc)},status_code=503)

    @app.exception_handler(IntegrityError)
    async def conflict(request,exc):
        return JSONResponse({'detail':'Operazione in conflitto con un elemento esistente.'},status_code=409)

    @app.get('/api/health')
    def health():
        return {'status':'ok','version':__version__}

    @app.get('/api/docs',include_in_schema=False)
    def reference(user=Depends(current_user)):
        from html import escape
        rows=[]
        for path,methods in app.openapi()['paths'].items():
            for method,operation in methods.items():
                if method not in ('get','post','put','patch','delete'):continue
                rows.append(f"<tr><td>{method.upper()}</td><td><code>{escape(path)}</code></td><td>{escape(operation.get('summary',''))}</td></tr>")
        return HTMLResponse("<!doctype html><html lang='it'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Vedra · API reference</title><style>body{font:15px system-ui;max-width:1100px;margin:4rem auto;padding:0 1rem;color:#203c31;background:#f5f6f2}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #d8dfd7}code{font-size:13px}a{color:inherit}</style><h1>Vedra API</h1><p>Riferimento locale, senza dipendenze CDN. Le API della dashboard usano cookie di sessione; le scritture richiedono X-CSRF-Token. Il bridge usa un token Bearer separato.</p><p><a href='/api/openapi.json'>Schema OpenAPI completo (JSON)</a> · <a href='/'>Dashboard</a></p><table><tr><th>Metodo</th><th>Percorso</th><th>Operazione</th></tr>"+''.join(rows)+"</table></html>")

    @app.post('/api/auth/login')
    def login(body: LoginInput,request: Request,response: Response):
        limiter.check(request.client.host if request.client else 'unknown')
        user=db.one('SELECT * FROM users WHERE email=?',(body.email.lower().strip(),))
        # Spend password work even for a nonexistent email to reduce enumeration.
        valid=verify_password(body.password,user['password_hash']) if user else bool(password_hash(body.password) and False)
        if not valid:raise HTTPException(401,'Email o password non corretti.')
        token,csrf=create_session(db,user,settings.session_hours)
        response.set_cookie('vedra_session',token,httponly=True,secure=settings.cookie_secure,samesite='strict',max_age=settings.session_hours*3600,path='/')
        return {'user':{k:user[k] for k in ('id','email','name','role')},'csrf':csrf}

    @app.get('/api/auth/me')
    def me(user=Depends(current_user)):
        return {'user':{k:user[k] for k in ('id','email','name','role')},'csrf':user['csrf']}

    @app.post('/api/auth/logout')
    def logout(request:Request,response:Response,user=Depends(current_user)):
        db.execute('DELETE FROM sessions WHERE token_hash=?',(token_hash(request.cookies.get('vedra_session','')),))
        response.delete_cookie('vedra_session',path='/')
        return {'ok':True}

    @app.get('/api/users')
    def users(user=Depends(require_admin)):
        return db.all('SELECT id,email,name,role,created_at FROM users ORDER BY created_at')

    @app.post('/api/users',status_code=201)
    def add_user(body:UserInput,user=Depends(require_admin)):
        if '@' not in body.email:raise ValueError('Email non valida.')
        ident=uid()
        db.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(ident,body.email.lower().strip(),password_hash(body.password),body.name,body.role,now()))
        return {'id':ident}

    def all_agents():
        agents=[]
        for row in db.all('SELECT * FROM agents ORDER BY created_at'):
            a=agent_dict(row)
            a['last_run']=db.one('SELECT * FROM runs WHERE agent_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(a['id'],))
            if a['last_run']:
                a['last_run']['stats']=load(a['last_run']['stats'],{})
                a['last_run'].pop('config_snapshot',None)
            counts=db.one('SELECT COUNT(*) total,COALESCE(SUM(fit),0) qualified FROM agent_properties WHERE agent_id=?',(a['id'],))
            a.update(counts)
            sources=[db.one('SELECT kind,config FROM sources WHERE id=?',(s,)) for s in a['source_ids']]
            a['is_demo']=any(s and (s['kind']=='demo' or (s['kind']=='import' and load(s['config'],{}).get('is_demo'))) for s in sources)
            if not a['is_demo']:
                agents.append(a)
        return agents

    def all_sources():
        output=[]
        for row in db.all('SELECT * FROM sources ORDER BY created_at'):
            row['config']=load(row['config'],{})
            probe_record=db.one('SELECT checked_at,report FROM source_probes WHERE source_id=?',(row['id'],))
            row['last_probe']={'checked_at':probe_record['checked_at'],**load(probe_record['report'],{})} if probe_record else None
            row['allowed_on_server']=row['domain'] in settings.live_domains if row['kind']=='html' else True
            count=db.one('SELECT COUNT(*) n,AVG(completeness) quality FROM properties WHERE source_id=?',(row['id'],))
            row.update({'property_count':count['n'],'quality':round(count['quality'] or 0)})
            if not legacy_source(row):
                output.append(row)
        return output

    def runs_list():
        output=[]
        for row in db.all('SELECT r.*,a.name agent_name FROM runs r JOIN agents a ON a.id=r.agent_id WHERE r.is_demo=0 ORDER BY r.created_at DESC,r.id DESC LIMIT 100'):
            row['stats']=load(row['stats'],{});row.pop('config_snapshot',None)
            output.append(row)
        return output

    from .routes.insights import register as register_insights
    register_insights(app, db, settings)
    from .routes.catalog import router as catalog_router
    app.include_router(catalog_router)

    @app.get('/api/workspace')
    def workspace(dataset:str='real',user=Depends(current_user)):
        require_real_dataset(dataset)
        properties=list_properties(db,dataset=dataset)
        memberships={}
        for item in db.all('SELECT ap.*,a.name FROM agent_properties ap JOIN agents a ON a.id=ap.agent_id'):
            memberships.setdefault(item['property_id'],[]).append({'id':item['agent_id'],'name':item['name'],'fit':bool(item['fit']),'reasons':load(item['fit_reasons'],[])})
        for item in properties: item['search_matches']=memberships.get(item['id'],[])
        coverage=[]
        for key in QUALITY_FIELDS:
            count=sum(p.get(key) not in (None,'','unknown',[],{}) for p in properties)
            coverage.append({'field':key,'present':count,'total':len(properties),'percent':round(count/len(properties)*100,1) if properties else 0})
        relevant_runs=runs_list()
        stats={
          'properties':len(properties),'benchmarked':sum(p['benchmark'] is not None for p in properties),
          'high_priority':sum(p['score'] is not None and p['score']>=75 for p in properties),
          'shortlisted':sum(p['review_status']=='shortlisted' for p in properties),
          'quality':round(sum(p['completeness'] for p in properties)/len(properties),1) if properties else 0,
          'total_asking':sum(p['price'] or 0 for p in properties),
          'type_counts':dict(Counter(p['property_type'] for p in properties)),
          'city_counts':dict(Counter(p['city'] or 'Non disponibile' for p in properties)),

          'real_count':db.one('SELECT COUNT(*) n FROM properties WHERE is_demo=0')['n'],
        }
        return {'properties':properties,'agents':all_agents(),'sources':all_sources(),'runs':relevant_runs,
                'stats':stats,'coverage':coverage,'duplicates':duplicate_candidates(properties),
                'limit':2000,'has_more':stats['real_count']>len(properties),
                'runtime':{'version':__version__,'hermes_configured':bool(settings.hermes_key),
                           'ai_configured':settings.ai_configured,'ai_model':settings.ai_model,
                           'browser_enabled':settings.browser_enabled,'scheduler_enabled':settings.scheduler,'database':db.dialect},'server_time':now()}

    @app.get('/api/agents')
    def agents(user=Depends(current_user)):return all_agents()

    def validate_agent(body):
        if body.criteria.online_discovery and body.runtime!='hermes':
            raise ValueError('La ricerca online richiede Hermes.')
        if len(set(body.source_ids))!=len(body.source_ids):raise ValueError('Fonte duplicata.')
        sources=[db.one('SELECT * FROM sources WHERE id=?',(sid,)) for sid in body.source_ids]
        if any(not s for s in sources):raise ValueError('Fonte non trovata.')
        modes={s['kind']=='demo' or (s['kind']=='import' and load(s['config'],{}).get('is_demo',False)) for s in sources}
        if True in modes:raise ValueError('Le fonti dimostrative precedenti non sono più utilizzabili.')
        if body.runtime=='llm' and not settings.ai_configured:
            raise ValueError('Configura il provider AI sul server prima di selezionarlo.')
        if body.runtime=='hermes' and not settings.hermes_key:
            raise ValueError('Configura Hermes prima di selezionarlo.')

    @app.post('/api/agents',status_code=201)
    def add_agent(body:AgentInput,user=Depends(require_editor)):
        validate_agent(body)
        ident=uid();timestamp=now()
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=body.interval_minutes)).isoformat(timespec='seconds') if body.active and body.interval_minutes else None
        db.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?,?,?)',(ident,body.name,body.city,dump(body.criteria.model_dump()),dump(body.source_ids),body.runtime,body.interval_minutes,int(body.active),nxt,timestamp,timestamp))
        return {'id':ident}

    @app.put('/api/agents/{ident}')
    def edit_agent(ident:str,body:AgentInput,user=Depends(require_editor)):
        if not db.one('SELECT id FROM agents WHERE id=?',(ident,)):raise HTTPException(404,'Agente non trovato.')
        validate_agent(body)
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=body.interval_minutes)).isoformat(timespec='seconds') if body.active and body.interval_minutes else None
        db.execute('UPDATE agents SET name=?,city=?,criteria=?,source_ids=?,runtime=?,interval_minutes=?,active=?,next_run=?,updated_at=? WHERE id=?',
                   (body.name,body.city,dump(body.criteria.model_dump()),dump(body.source_ids),body.runtime,body.interval_minutes,int(body.active),nxt,now(),ident))
        agent=agent_dict(db.one('SELECT * FROM agents WHERE id=?',(ident,)))
        for p in db.all('SELECT property_id id FROM agent_properties WHERE agent_id=?',(ident,)):link_agent(db,agent,p['id'])
        return {'ok':True,'notice':'Le run già in corso mantengono il proprio snapshot di configurazione.'}

    @app.post('/api/agents/{ident}/toggle')
    def toggle_agent(ident:str,user=Depends(require_editor)):
        a=db.one('SELECT * FROM agents WHERE id=?',(ident,))
        if not a:raise HTTPException(404,'Agente non trovato.')
        active=not a['active']
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=a['interval_minutes'])).isoformat(timespec='seconds') if active and a['interval_minutes'] else None
        db.execute('UPDATE agents SET active=?,next_run=?,updated_at=? WHERE id=?',(int(active),nxt,now(),ident))
        return {'active':active,'notice':'Pausa sospende le esecuzioni future, non quella corrente.'}

    @app.post('/api/agents/{ident}/run',status_code=202)
    def run_agent(ident:str,user=Depends(require_editor)):
        from .services.preflight import check_agent
        row=db.one('SELECT * FROM agents WHERE id=?',(ident,))
        if not row:raise HTTPException(404,'Agente non trovato.')
        readiness=check_agent(db,settings,row)
        if not readiness['can_enqueue'] and not readiness['active_run']:
            raise HTTPException(409,'La ricerca non ha fonti o runtime utilizzabili. Apri Diagnostica agente per i dettagli.')
        run=engine.enqueue(ident)
        return {'id':run['id'],'status':run['status']}

    @app.get('/api/agents/{ident}/preflight')
    def preflight_agent(ident:str,user=Depends(current_user)):
        from .services.preflight import check_agent
        row=db.one('SELECT * FROM agents WHERE id=?',(ident,))
        if not row:raise HTTPException(404,'Agente non trovato.')
        return check_agent(db,settings,row)

    @app.get('/api/runs/{ident}')
    def get_run(ident:str,user=Depends(current_user)):
        row=db.one('SELECT r.*,a.name agent_name FROM runs r JOIN agents a ON a.id=r.agent_id WHERE r.id=? AND r.is_demo=0',(ident,))
        if not row:raise HTTPException(404,'Run non trovata.')
        row['stats']=load(row['stats'],{});row['config_snapshot']=load(row['config_snapshot'],{})
        row['events']=db.all('SELECT * FROM events WHERE run_id=? ORDER BY id',(ident,))
        for e in row['events']:e['data']=load(e['data'],{})
        return row

    @app.post('/api/runs/{ident}/cancel')
    def cancel_run(ident:str,user=Depends(require_editor)):
        row=db.one('SELECT * FROM runs WHERE id=?',(ident,))
        if not row:raise HTTPException(404,'Run non trovata.')
        if row['status']=='queued':engine.finish(ident,'cancelled','Annullata prima dell’avvio.')
        elif row['status']=='running':db.execute("UPDATE runs SET status='cancelling' WHERE id=?",(ident,))
        return {'ok':True}

    @app.get('/api/runs/{ident}/events')
    async def run_events(ident:str,request:Request,user=Depends(current_user)):
        if not db.one('SELECT id FROM runs WHERE id=?',(ident,)):raise HTTPException(404,'Run non trovata.')
        try:last=int(request.headers.get('last-event-id','0'))
        except ValueError:last=0
        async def generate():
            cursor=last
            for _ in range(600):
                if await request.is_disconnected():break
                for row in db.all('SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id',(ident,cursor)):
                    cursor=row['id'];row['data']=load(row['data'],{})
                    yield f'id: {cursor}\nevent: progress\ndata: {dump(row)}\n\n'
                status=db.one('SELECT status FROM runs WHERE id=?',(ident,))['status']
                if status not in ('queued','running','cancelling'):
                    yield f'event: done\ndata: {dump({"status":status})}\n\n';break
                yield ': heartbeat\n\n'
                await asyncio.sleep(1)
        return StreamingResponse(generate(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})

    @app.get('/api/sources')
    def sources(user=Depends(current_user)):return all_sources()

    @app.get('/api/source-presets')
    def source_presets(user=Depends(current_user)):
        from .connectors.portals import presets
        return presets()

    @app.post('/api/sources',status_code=201)
    def create_source(body:SourceInput,user=Depends(require_admin)):
        ident=uid()
        db.execute('INSERT INTO sources(id,name,kind,domain,config,permission_note,permission_at,created_at) VALUES(?,?,?,?,?,?,?,?)',
                   (ident,body.name,'html',body.domain,dump(body.config.model_dump()),body.permission_note,now(),now()))
        return {'id':ident,'allowed_on_server':body.domain in settings.live_domains}

    @app.put('/api/sources/{ident}')
    def edit_source(ident:str,body:SourceInput,user=Depends(require_admin)):
        if not db.one("SELECT id FROM sources WHERE id=? AND kind='html'",(ident,)):raise HTTPException(404,'Fonte HTML non trovata.')
        with db.transaction() as con:
            db.begin_write(con)
            con.execute("UPDATE sources SET name=?,domain=?,config=?,permission_note=?,permission_at=?,status='unverified',last_error=NULL WHERE id=?",
                        (body.name,body.domain,dump(body.config.model_dump()),body.permission_note,now(),ident))
            # A successful probe of the old parser is not evidence for this configuration.
            con.execute('DELETE FROM source_probes WHERE source_id=?',(ident,))
        return {'ok':True}

    @app.post('/api/sources/{ident}/toggle')
    def toggle_source(ident:str,user=Depends(require_admin)):
        db.execute('UPDATE sources SET enabled=1-enabled WHERE id=?',(ident,))
        return {'ok':True}

    @app.post('/api/sources/{ident}/probe')
    async def probe_source(ident:str,user=Depends(require_admin)):
        from .services.source_probe import probe
        row=db.one('SELECT * FROM sources WHERE id=?',(ident,))
        if not row or legacy_source(row):raise HTTPException(404,'Fonte non trovata.')
        if row['kind']!='html':return {'ok':True,'notice':'Fonte importata: nessuna richiesta di rete necessaria.'}
        if not row['enabled'] or not row['permission_at']:raise ValueError('Fonte disabilitata o permesso non documentato.')
        return await probe(db,settings,row)

    @app.get('/api/properties/{ident}')
    def property_detail(ident:str,user=Depends(current_user)):
        row=db.one('SELECT p.*,s.name source_name FROM properties p JOIN sources s ON p.source_id=s.id WHERE p.id=? AND p.is_demo=0',(ident,))
        if not row:raise HTTPException(404,'Immobile non trovato.')
        p=property_dict(row)
        p['observations']=db.all('SELECT id,observed_at,price,content_hash,parser_version FROM observations WHERE property_id=? ORDER BY observed_at,id',(ident,))
        p['notes']=db.all('SELECT n.id,n.body,n.created_at,u.name author FROM notes n JOIN users u ON u.id=n.user_id WHERE property_id=? ORDER BY n.created_at DESC',(ident,))
        p['screenings']=db.all('SELECT a.id,a.name,ap.fit,ap.fit_reasons FROM agent_properties ap JOIN agents a ON ap.agent_id=a.id WHERE ap.property_id=?',(ident,))
        for a in p['screenings']:a['fit_reasons']=load(a['fit_reasons'],[])
        check=db.one('SELECT last_detail_at FROM listing_checks WHERE property_id=?',(ident,))
        p['last_detail_at']=check['last_detail_at'] if check else None
        p['duplicates']=[d for d in duplicate_candidates(list_properties(db,dataset='real',city=p['city'])) if ident in (d['a'],d['b'])]
        return p

    @app.patch('/api/properties/{ident}')
    def review_property(ident:str,body:ReviewInput,user=Depends(require_editor)):
        if not db.one('SELECT id FROM properties WHERE id=? AND is_demo=0',(ident,)):raise HTTPException(404,'Immobile non trovato.')
        values=body.model_dump(exclude_none=True)
        if values:
            with db.transaction() as con:
                db.begin_write(con)
                con.execute(f"UPDATE properties SET {','.join(k+'=?' for k in values)} WHERE id=?",tuple(values.values())+(ident,))
                if 'review_status' in values:
                    con.execute('''INSERT INTO deal_work(property_id,version,updated_at,updated_by) VALUES(?,1,?,?)
                        ON CONFLICT(property_id) DO UPDATE SET version=version+1,updated_at=excluded.updated_at,updated_by=excluded.updated_by''',(ident,now(),user['id']))
            from .services.operations import audit
            audit(db,user['id'],'property.review_updated',ident,values)
        return {'ok':True}

    @app.post('/api/properties/{ident}/notes',status_code=201)
    def note_property(ident:str,body:NoteInput,user=Depends(require_editor)):
        if not db.one('SELECT id FROM properties WHERE id=? AND is_demo=0',(ident,)):raise HTTPException(404,'Immobile non trovato.')
        db.execute('INSERT INTO notes VALUES(?,?,?,?,?)',(uid(),ident,user['id'],body.body,now()))
        return {'ok':True}

    @app.get('/api/properties/{ident}/snapshot')
    def snapshot(ident:str,user=Depends(current_user)):
        row=db.one('SELECT snapshot_path FROM observations WHERE property_id=? AND snapshot_path IS NOT NULL ORDER BY observed_at DESC,id DESC LIMIT 1',(ident,))
        if not row:raise HTTPException(404,'Snapshot non disponibile.')
        path=(settings.data_dir/row['snapshot_path']).resolve()
        if not path.is_relative_to((settings.data_dir/'snapshots').resolve()):raise HTTPException(403)
        return FileResponse(path,media_type='text/plain',filename=f'vedra-{ident}-source.txt')

    @app.post('/api/imports')
    def import_file(body:ImportInput,user=Depends(require_admin)):
        return import_data(db,settings,body)

    @app.get('/api/benchmarks')
    def benchmarks(user=Depends(current_user)):
        return db.all('SELECT * FROM benchmarks WHERE is_demo=0 ORDER BY city,zone,period DESC LIMIT 3000')

    @app.get('/api/omi/provinces')
    async def omi_provinces(user=Depends(current_user)):
        return await omi.provinces()

    @app.get('/api/omi/cities')
    async def omi_cities(province:str,user=Depends(current_user)):
        return await omi.cities(province)

    @app.get('/api/omi/zones')
    async def omi_zones(city_code:str,user=Depends(current_user)):
        features,period,doc=await omi.zones(city_code)
        return {'period':period,'retrieved_at':doc['retrieved_at'],'zones':[
            {'code':f['properties']['zona'],'name':f['properties']['descZona']} for f in features]}

    @app.get('/api/omi/quotes')
    async def omi_quotes(city_code:str,zone:str,period:str,usage:str='R',user=Depends(current_user)):
        return await omi.quotes(city_code,zone,period,usage)

    @app.post('/api/export')
    def selected_export(body: dict, user=Depends(current_user)):
        kind=body.get('format')
        dataset=body.get('dataset','real')
        ids=body.get('ids',[])
        if kind not in ('csv','xlsx') or dataset != 'real':
            raise ValueError('Formato o dataset non valido.')
        if not isinstance(ids,list) or len(ids)>2000 or any(not isinstance(x,str) for x in ids):
            raise ValueError('Selezione non valida: massimo 2000 immobili.')
        selected=set(ids)
        from .services.catalog import by_ids
        rows=by_ids(db,sorted(selected))
        if len(rows)!=len(selected):raise ValueError('Selezione non più disponibile. Ricarica gli annunci.')
        if not rows:raise ValueError('Nessun immobile selezionato.')
        content=export_csv(rows) if kind=='csv' else export_xlsx(rows)
        mime='text/csv; charset=utf-8' if kind=='csv' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="vedra-opportunita.{kind}"'})

    @app.get('/api/export/{kind}')
    def export(kind:str,dataset:str='real',city:str='',q:str='',starred:bool=False,status:str='',agent_id:str='',ids:str='',user=Depends(current_user)):
        from .services.catalog import export_rows
        from .product_schemas import ViewFilters
        if dataset != 'real':
            raise ValueError('Dataset non operativo.')
        rows=export_rows(db,ViewFilters(city=city,q=q,starred=starred,status=status,agent_id=agent_id))
        if ids:
            selected=set(ids.split(','));rows=[p for p in rows if p['id'] in selected]
            if len(rows)!=len(selected):raise ValueError('Selezione non disponibile nei filtri indicati.')
        if kind=='csv':data=export_csv(rows);mime='text/csv; charset=utf-8'
        elif kind=='xlsx':data=export_xlsx(rows);mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:raise HTTPException(404,'Formato non supportato.')
        return Response(data,media_type=mime,headers={'Content-Disposition':f'attachment; filename="vedra-opportunita.{kind}"'})

    @app.get('/api/properties/{ident}/memo.docx')
    def memo(ident:str,user=Depends(current_user)):
        p=property_detail(ident,user)
        return Response(export_docx(p),media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        headers={'Content-Disposition':f'attachment; filename="vedra-scheda-{ident[:8]}.docx"'})

    @app.get('/api/runtime')
    async def runtime(user=Depends(require_admin)):
        result={'ai_configured':settings.ai_configured,'ai_model':settings.ai_model,'ai_verified':False,'hermes_configured':bool(settings.hermes_key),'bridge_configured':bool(settings.bridge_token),
                'browser_enabled':settings.browser_enabled,'allowed_live_domains':settings.live_domains,'scheduler_enabled':settings.scheduler,'database':db.dialect,
                'public_origin':settings.public_origin,'cookie_secure':settings.cookie_secure}
        if settings.hermes_key:
            try:
                caps=await HermesClient(settings).capabilities()
                result['hermes_reachable']=True;result['capabilities']=caps
                result['tools']=await HermesClient(settings).verify_tools()
                result['hermes_tools_verified']=True
            except HermesUnavailable as exc:result['hermes_reachable']=False;result['error']=str(exc)
        return result

    from .services.origination import Origination
    origination=Origination(engine)

    @app.post('/bridge/runs/{ident}/search',dependencies=[Depends(require_bridge)])
    async def bridge_search(ident:str):
        return await origination.search(ident)

    @app.post('/bridge/runs/{ident}/browse',dependencies=[Depends(require_bridge)])
    async def bridge_browse(ident:str,body:dict):
        import re
        if (set(body)!={'source_id','ref'} or not isinstance(body['source_id'],str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',body['source_id'])
            or not isinstance(body['ref'],str) or not re.fullmatch(r'([a-f0-9]{24})?',body['ref'])):
            raise HTTPException(422,'Riferimento browser non valido.')
        return await origination.browse(ident,body['source_id'],body['ref'])

    @app.post('/bridge/runs/{ident}/acquire',dependencies=[Depends(require_bridge)])
    async def bridge_acquire(ident:str,body:dict):
        if set(body)!={'url'} or not isinstance(body['url'],str) or len(body['url'])>2000:
            raise HTTPException(422,'Indica una URL valida.')
        return await origination.acquire(ident,body['url'])

    @app.post('/bridge/runs/{ident}/complete-collection',dependencies=[Depends(require_bridge)])
    async def bridge_complete_collection(ident:str):
        return await origination.complete(ident)

    # Narrow machine-to-machine surface. No arbitrary URL, shell or admin operations.
    # Use an isolated Hermes profile; credentials never go to the client dashboard.
    @app.post('/bridge/runs/{ident}/collect',dependencies=[Depends(require_bridge)])
    async def bridge_collect(ident:str):
        row=db.one("SELECT * FROM runs WHERE id=? AND runtime='hermes' AND status='running'",(ident,))
        if not row:raise HTTPException(409,'Run Hermes attiva non trovata.')
        return await engine.collect(ident)

    @app.get('/bridge/runs/{ident}',dependencies=[Depends(require_bridge)])
    def bridge_get(ident:str):
        row=db.one("SELECT * FROM runs WHERE id=? AND runtime='hermes' AND status='running'",(ident,))
        if not row:raise HTTPException(409,'Run Hermes attiva non trovata.')
        return engine.collect_result(ident)

    @app.post('/bridge/runs/{ident}/analysis/{pid}',dependencies=[Depends(require_bridge)])
    def bridge_analysis(ident:str,pid:str,body:SemanticAnalysis):
        row=db.one("SELECT * FROM runs WHERE id=? AND runtime='hermes' AND status='running' AND collected=1",(ident,))
        if not row:raise HTTPException(409,'Raccolta della run non completata.')
        eligible=db.one('SELECT property_id FROM semantic_tasks WHERE run_id=? AND property_id=?',(ident,pid))
        if not eligible:raise HTTPException(403,'L’immobile non appartiene all’insieme classificabile della run.')
        p=property_dict(db.one('SELECT * FROM properties WHERE id=? AND is_demo=0',(pid,)))
        task=db.one('SELECT * FROM semantic_tasks WHERE run_id=? AND property_id=?',(ident,pid))
        if not task or task['content_hash']!=p['content_hash']:
            raise HTTPException(409,'Il contenuto è cambiato dopo la raccolta. Esegui nuovamente la ricerca.')
        analysis=validate_semantic(load(task['payload']),body.model_dump())
        refresh_analysis(db,pid,analysis)
        db.execute('UPDATE semantic_tasks SET submitted=1 WHERE run_id=? AND property_id=?',(ident,pid))
        db.event(ident,'classify',f'Classificazione Hermes validata: {p["title"][:80]}.',data={'property_id':pid})
        return {'ok':True}

    @app.post('/bridge/runs/{ident}/finish',dependencies=[Depends(require_bridge)])
    def bridge_finish(ident:str):
        row=db.one("SELECT * FROM runs WHERE id=? AND runtime='hermes' AND status='running' AND collected=1",(ident,))
        if not row:raise HTTPException(409,'Run non pronta per la chiusura.')
        if db.one('SELECT COUNT(*) n FROM semantic_tasks WHERE run_id=? AND submitted=0',(ident,))['n']:
            raise HTTPException(409,'Mancano classificazioni: non è possibile dichiarare completato il lavoro AI.')
        db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(ident,))
        return {'ok':True,'notice':'Il worker chiuderà la run dopo aver osservato la conclusione di Hermes.'}

    @app.post('/bridge/agents/{ident}/enqueue',dependencies=[Depends(require_bridge)],status_code=202)
    def bridge_enqueue(ident:str):
        a=db.one('SELECT * FROM agents WHERE id=?',(ident,))
        if not a or not a['active']:raise HTTPException(409,'Agente assente o in pausa.')
        if a['interval_minutes']!=0:raise HTTPException(409,'Per scheduler esterno imposta frequenza Manuale, evitando due scheduler.')
        run=engine.enqueue(ident,'external')
        return {'id':run['id'],'status':run['status']}

    from .routes.product import router as product_router
    app.include_router(product_router)

    frontend=settings.root/'frontend'
    app.mount('/assets',StaticFiles(directory=frontend/'src'),name='assets')
    app.mount('/public',StaticFiles(directory=frontend/'public'),name='public')

    @app.get('/',include_in_schema=False)
    def index():return FileResponse(frontend/'index.html',headers={'Cache-Control':'no-cache'})

    return app


app=create_app()
