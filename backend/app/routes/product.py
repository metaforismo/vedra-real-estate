from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from statistics import median

from fastapi import APIRouter, Depends, HTTPException, Request

from ..db import dump, load, now, uid
from ..datasets import require_real_dataset
from ..services.worker import worker_health
from ..product_schemas import DealWorkInput, DuplicateInput, PasswordInput, SavedViewInput, ScenarioInput
from ..security import current_user, require_editor, require_admin, verify_password, password_hash, token_hash
from ..services.operations import audit
from ..services.scenarios import calculate

router = APIRouter(prefix='/api')


def property_or_404(db, ident):
    item = db.one('SELECT * FROM properties WHERE id=? AND is_demo=0', (ident,))
    if not item:
        raise HTTPException(404, 'Immobile non trovato.')
    return item


@router.get('/operations')
def operations(request: Request, dataset: str = 'real', user=Depends(current_user)):
    db, engine, settings = request.app.state.db, request.app.state.engine, request.app.state.settings
    require_real_dataset(dataset)
    where = '' if dataset=='all' else ' WHERE is_demo=?'
    args = () if dataset=='all' else (int(dataset=='demo'),)
    daily = db.all('''SELECT substr(created_at,1,10) AS "day",COUNT(*) total,
        SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) completed,SUM(CASE WHEN status IN ('failed','partial','interrupted') THEN 1 ELSE 0 END) failed
        FROM runs''' + where + ' GROUP BY "day" ORDER BY "day" DESC LIMIT 14', args)
    unread = db.one('''SELECT COUNT(*) n FROM notifications n WHERE NOT EXISTS(
        SELECT 1 FROM notification_reads r WHERE r.notification_id=n.id AND r.user_id=?)''' + ('' if dataset=='all' else ' AND n.is_demo=?'), (user['id'],)+args)['n']
    counts = db.one("SELECT COUNT(*) total,SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) pending,SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) failed FROM mail_outbox")
    return {
        'workspace': {'name':settings.workspace_name, 'id':settings.workspace_id, 'isolation':'dedicated-deployment'},
        'worker': worker_health(db,settings),
        'daily_runs':daily, 'unread':unread,
        'ai_usage':db.one('''SELECT COUNT(*) accepted_analyses,COALESCE(SUM(usage_reported),0) reported_analyses,
            SUM(input_tokens) input_tokens,SUM(output_tokens) output_tokens,SUM(estimated_eur) estimated_eur
            FROM ai_usage u JOIN runs r ON r.id=u.run_id''' + ('' if dataset=='all' else ' WHERE r.is_demo=?'),args),
        'source_health':db.all('SELECT * FROM source_health'),
        'team':db.all('SELECT id,name,role FROM users ORDER BY name'),
        'work':[dict(row,checklist=load(row['checklist'])) for row in db.all('SELECT * FROM deal_work')],
        'duplicate_reviews':db.all('SELECT * FROM duplicate_reviews'),
        'saved_views':[dict(r,filters=load(r['filters'])) for r in db.all('SELECT * FROM saved_views WHERE user_id=? ORDER BY name', (user['id'],))],
        'mail':{'enabled':settings.mail_enabled, **counts},
        'limits':{'max_ai_listings':settings.max_ai_listings,'run_timeout_seconds':settings.run_timeout},
    }


@router.get('/readiness')
def readiness(request: Request, user=Depends(require_admin)):
    db, engine, settings = request.app.state.db, request.app.state.engine, request.app.state.settings
    disk = shutil.disk_usage(settings.data_dir)
    checks = {
        'database': db.healthy(),
        'disk': disk.free > 100_000_000,
        'worker': worker_health(db,settings)['healthy'],
        'sources': any(not (row['kind']=='demo' or load(row['config'],{}).get('is_demo')) for row in db.all('SELECT kind,config FROM sources WHERE enabled=1')),
    }
    return {'ready':all(checks.values()), 'checks':checks, 'disk_free_mb':round(disk.free/1_000_000),
            'hermes_configured':bool(settings.hermes_key), 'hermes_verified':False, 'ai_configured':settings.ai_configured,
            'notice':'La verifica rete/modello va eseguita separatamente. Un HTTP 200 non garantisce la copertura delle fonti.'}


@router.get('/notifications')
def notifications(request: Request, dataset: str='real', user=Depends(current_user)):
    require_real_dataset(dataset)
    db = request.app.state.db
    where = '' if dataset=='all' else 'WHERE n.is_demo=?'
    args = (user['id'],) if dataset=='all' else (user['id'],int(dataset=='demo'))
    return db.all('''SELECT n.*,r.read_at FROM notifications n LEFT JOIN notification_reads r
        ON r.notification_id=n.id AND r.user_id=? ''' + where + ' ORDER BY n.created_at DESC,n.id DESC LIMIT 200', args)


@router.post('/notifications/read-all')
def read_all(request: Request, user=Depends(current_user)):
    request.app.state.db.execute('''INSERT INTO notification_reads
        SELECT id,?,? FROM notifications WHERE is_demo=0 ON CONFLICT DO NOTHING''', (user['id'],now()))
    return {'ok':True}


@router.post('/notifications/{ident}/read')
def read_notification(ident: str, request: Request, user=Depends(current_user)):
    db = request.app.state.db
    if not db.one('SELECT id FROM notifications WHERE id=? AND is_demo=0', (ident,)):
        raise HTTPException(404, 'Notifica non trovata.')
    db.execute('INSERT INTO notification_reads VALUES(?,?,?) ON CONFLICT DO NOTHING', (ident,user['id'],now()))
    return {'ok':True}


@router.get('/properties/{ident}/work')
def get_work(ident: str, request: Request, user=Depends(current_user)):
    db = request.app.state.db
    property_or_404(db,ident)
    row = db.one('SELECT * FROM deal_work WHERE property_id=?', (ident,))
    return dict(row,checklist=load(row['checklist'])) if row else {
        'property_id':ident, 'owner_id':None, 'due_date':None, 'checklist':{}, 'version':0}


@router.put('/properties/{ident}/work')
def update_work(ident: str, body: DealWorkInput, request: Request, user=Depends(require_editor)):
    db = request.app.state.db
    property_or_404(db,ident)
    if body.owner_id and not db.one("SELECT id FROM users WHERE id=? AND role IN ('admin','analyst')", (body.owner_id,)):
        raise ValueError('Assegnatario non disponibile o in sola lettura.')
    with db.transaction() as con:
        # Serialize version checks with writes; no lost checklist updates between two reviewers.
        db.begin_write(con)
        old = con.execute('SELECT version FROM deal_work WHERE property_id=?', (ident,)).fetchone()
        actual = old['version'] if old else 0
        if actual != body.version:
            raise HTTPException(409, 'Un collega ha modificato questa revisione. Riapri la scheda prima di salvare.')
        con.execute('''INSERT INTO deal_work VALUES(?,?,?,?,?,?,?) ON CONFLICT(property_id) DO UPDATE SET
            owner_id=excluded.owner_id,due_date=excluded.due_date,checklist=excluded.checklist,
            version=excluded.version,updated_at=excluded.updated_at,updated_by=excluded.updated_by''',
            (ident,body.owner_id,body.due_date.isoformat() if body.due_date else None,
             dump(body.checklist.model_dump()),actual+1,now(),user['id']))
        if body.stage:
            con.execute('UPDATE properties SET review_status=? WHERE id=?',(body.stage,ident))
    audit(db,user['id'],'deal.work_updated',ident,{'version':actual+1})
    return {'ok':True,'version':actual+1}


@router.post('/scenarios/calculate')
def preview_scenario(body: ScenarioInput, user=Depends(current_user)):
    return calculate(body.inputs)


@router.get('/properties/{ident}/scenarios')
def scenarios(ident: str, request: Request, user=Depends(current_user)):
    db = request.app.state.db
    property_or_404(db,ident)
    rows = db.all('SELECT s.*,u.name author FROM scenarios s JOIN users u ON s.author_id=u.id WHERE property_id=? ORDER BY s.created_at DESC', (ident,))
    return [dict(row,inputs=load(row['inputs']),result=calculate(ScenarioInput(name=row['name'],inputs=load(row['inputs'])).inputs)) for row in rows]


@router.post('/properties/{ident}/scenarios',status_code=201)
def save_scenario(ident: str, body: ScenarioInput, request: Request, user=Depends(require_editor)):
    db = request.app.state.db
    p = property_or_404(db,ident)
    if p['currency']!='EUR':
        raise ValueError('Il modello finanziario usa EUR. Verificare prima la valuta del dato.')
    if db.one('SELECT COUNT(*) n FROM scenarios WHERE property_id=?', (ident,))['n']>=30:
        raise ValueError('Massimo 30 scenari per immobile: elimina uno scenario precedente.')
    sid = uid()
    db.execute('INSERT INTO scenarios VALUES(?,?,?,?,?,?)',
               (sid,ident,body.name,dump(body.inputs.model_dump(mode='json')),user['id'],now()))
    audit(db,user['id'],'scenario.created',sid,{'property_id':ident})
    return {'id':sid,'result':calculate(body.inputs)}


@router.delete('/scenarios/{ident}')
def delete_scenario(ident: str, request: Request, user=Depends(require_editor)):
    db = request.app.state.db
    row = db.one('SELECT * FROM scenarios WHERE id=?',(ident,))
    if not row:
        raise HTTPException(404,'Scenario non trovato.')
    if row['author_id']!=user['id'] and user['role']!='admin':
        raise HTTPException(403,'Puoi eliminare solo i tuoi scenari.')
    db.execute('DELETE FROM scenarios WHERE id=?',(ident,))
    audit(db,user['id'],'scenario.deleted',ident)
    return {'ok':True}


@router.get('/properties/{ident}/comparables')
def comparables(ident: str, request: Request, user=Depends(current_user)):
    db = request.app.state.db
    p = property_or_404(db,ident)
    required = ('city','zone','property_type','condition','area_basis','transaction_type','currency')
    missing = [k for k in required if not p[k] or p[k] in ('unknown','XXX')]
    if missing or not p['surface']:
        return {'items':[], 'median_sqm':None,'reason':'Metadati insufficienti per confronti omogenei: '+', '.join(missing or ['superficie'])}
    cutoff = (datetime.now(timezone.utc)-timedelta(days=90)).isoformat(timespec='seconds')
    where = ' AND '.join(f'{key}=?' for key in required)
    rows = db.all('SELECT id,title,url,source_id,price,surface,last_seen FROM properties WHERE '+where+''' AND is_demo=?
        AND availability NOT IN ('sold','rented','withdrawn','review')
        AND id!=? AND price>0 AND surface BETWEEN ? AND ? AND last_seen>=? ORDER BY last_seen DESC LIMIT 100''',
        tuple(p[k] for k in required)+(p['is_demo'],ident,p['surface']*.7,p['surface']*1.3,cutoff))
    # Exclude the subject and repeated confirmed assets, not just repeated URLs.
    groups = {}
    def root(x):
        while groups.get(x,x)!=x:
            x=groups[x]
        return x
    for pair in db.all("SELECT a,b FROM duplicate_reviews WHERE decision='same_asset'"):
        groups[root(pair['b'])]=root(pair['a'])
    seen = {root(ident)}
    accepted = []
    for row in rows:
        cluster = root(row['id'])
        if cluster in seen:
            continue
        seen.add(cluster)
        accepted.append(dict(row,price_sqm=round(row['price']/row['surface'],2)))
        if len(accepted)>=12:
            break
    return {'items':accepted,'median_sqm':round(median(r['price_sqm'] for r in accepted),2) if len(accepted)>=3 else None,
            'reason':'Prezzi richiesti, non transazioni. Stessi metadati, superficie ±30%, osservati negli ultimi 90 giorni. Mediana disponibile da 3 comparabili. Non modifica lo score OMI.'}


@router.post('/saved-views', status_code=201)
def save_view(body: SavedViewInput, request: Request, user=Depends(current_user)):
    db = request.app.state.db
    if db.one('SELECT COUNT(*) n FROM saved_views WHERE user_id=?',(user['id'],))['n']>=30:
        raise ValueError('Massimo 30 viste personali.')
    ident = uid()
    db.execute('INSERT INTO saved_views VALUES(?,?,?,?,?)', (ident,user['id'],body.name,dump(body.filters.model_dump()),now()))
    return {'id':ident}


@router.delete('/saved-views/{ident}')
def delete_view(ident: str, request: Request, user=Depends(current_user)):
    db = request.app.state.db
    if not db.one('SELECT id FROM saved_views WHERE id=? AND user_id=?',(ident,user['id'])):
        raise HTTPException(404,'Vista non trovata.')
    db.execute('DELETE FROM saved_views WHERE id=? AND user_id=?',(ident,user['id']))
    return {'ok':True}


@router.post('/duplicates/review')
def review_duplicate(body: DuplicateInput, request: Request, user=Depends(require_editor)):
    db = request.app.state.db
    a,b = sorted((body.a,body.b))
    if a==b:
        raise ValueError('Selezionare due annunci diversi.')
    pa,pb = property_or_404(db,a),property_or_404(db,b)
    if pa['is_demo']!=pb['is_demo']:
        raise ValueError('Non si possono collegare demo e dati reali.')
    db.execute('''INSERT INTO duplicate_reviews VALUES(?,?,?,?,?) ON CONFLICT(a,b) DO UPDATE SET
        decision=excluded.decision,user_id=excluded.user_id,updated_at=excluded.updated_at''',
        (a,b,body.decision,user['id'],now()))
    audit(db,user['id'],'duplicate.reviewed',a,{'b':b,'decision':body.decision})
    return {'ok':True,'notice':'Gli annunci restano separati con le rispettive fonti e osservazioni.'}


@router.get('/audit')
def audit_history(request: Request, user=Depends(require_admin)):
    return request.app.state.db.all('''SELECT a.*,u.name actor FROM audit_log a LEFT JOIN users u ON u.id=a.user_id
        ORDER BY a.id DESC LIMIT 200''')


@router.post('/auth/password')
def change_password(body: PasswordInput, request: Request, user=Depends(current_user)):
    db = request.app.state.db
    old = db.one('SELECT password_hash FROM users WHERE id=?',(user['id'],))
    if not verify_password(body.current_password,old['password_hash']):
        raise HTTPException(403,'Password attuale non corretta.')
    if body.current_password==body.new_password:
        raise ValueError('La nuova password deve essere diversa.')
    with db.transaction() as con:
        con.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(body.new_password),user['id']))
        con.execute('DELETE FROM sessions WHERE user_id=? AND token_hash!=?',
                    (user['id'],token_hash(request.cookies.get('vedra_session',''))))
    audit(db,user['id'],'user.password_changed',user['id'])
    return {'ok':True,'notice':'Password aggiornata; le altre sessioni sono state revocate.'}
