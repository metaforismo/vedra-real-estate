"""Atomic configuration writes and receipts, independent of scheduler timestamps."""
import hashlib
import json
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from ..db import dump,load,now,uid

FIELDS=('name','city','criteria','source_ids','runtime','interval_minutes','active')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def revision(row):
    config={key:row[key] for key in FIELDS}
    for key in ('criteria','source_ids'):
        if isinstance(config[key],str):config[key]=load(config[key])
    config['active']=bool(config['active'])
    return digest(config)


def conflict(message,ident=None):
    raise HTTPException(409,{'message':message,'agent_id':ident})


def save(db,body,user_id,validate,ident=None):
    from .store import agent_dict,property_dict
    from .analysis import screen
    key=str(body.request_id) if body.request_id else None
    fingerprint=digest({'agent_id':ident,'body':body.model_dump(mode='json',exclude={'request_id'})})
    with db.transaction() as con:
        db.begin_write(con)
        if key:
            receipt=con.execute('SELECT * FROM agent_write_receipts WHERE request_id=?',(key,)).fetchone()
            if receipt:
                if receipt['user_id']!=user_id:conflict('Identificativo di richiesta già utilizzato. Riapri la ricerca.')
                result=load(receipt['response'])
                if receipt['fingerprint']!=fingerprint:
                    conflict('Ricerca già salvata. Rileggila prima di modificarla.',result['id'])
                return result
        row=None
        if ident:
            row=con.execute('SELECT * FROM agents WHERE id=?',(ident,)).fetchone()
            if not row:raise HTTPException(404,'Ricerca non più disponibile.')
            if body.expected_revision and body.expected_revision!=revision(dict(row)):
                conflict('Ricerca aggiornata da un altro operatore. Rileggila per salvare; la bozza resta qui.',ident)
        validate(body,con)
        timestamp=now()
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=body.interval_minutes)).isoformat(timespec='seconds') if body.active and body.interval_minutes else None
        values=(body.name,body.city,dump(body.criteria.model_dump()),dump(body.source_ids),body.runtime,body.interval_minutes,int(body.active),nxt)
        if row:
            con.execute('UPDATE agents SET name=?,city=?,criteria=?,source_ids=?,runtime=?,interval_minutes=?,active=?,next_run=?,updated_at=? WHERE id=?',values+(timestamp,ident))
        else:
            ident=uid()
            con.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?,?,?)',(ident,)+values+(timestamp,timestamp))
        agent=agent_dict(dict(con.execute('SELECT * FROM agents WHERE id=?',(ident,)).fetchone()))
        if row:
            # Configuration and deterministic screening commit together, or neither does.
            rows=con.execute('SELECT p.* FROM properties p JOIN agent_properties ap ON ap.property_id=p.id WHERE ap.agent_id=?',(ident,)).fetchall()
            for item in rows:
                p=property_dict(dict(item));fit,reasons=screen(p,agent)
                con.execute('UPDATE agent_properties SET fit=?,fit_reasons=?,score=? WHERE agent_id=? AND property_id=?',
                            (int(fit),dump(reasons),p['score'],ident,p['id']))
        result={'id':ident,'ok':True,'revision':agent['revision']}
        if key:con.execute('INSERT INTO agent_write_receipts VALUES(?,?,?,?,?)',(key,user_id,fingerprint,dump(result),timestamp))
        return result
