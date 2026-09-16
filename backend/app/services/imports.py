from __future__ import annotations

import csv
import hashlib
import io

from ..db import dump,now,uid
from ..schemas import Listing,BenchmarkInput
from ..connectors.parser import number,extract_listing,canonical_url
from .store import upsert_listing,refresh_analysis


def read_csv(content):
    content=content.lstrip('\ufeff')
    try:
        dialect=csv.Sniffer().sniff(content[:4000],delimiters=',;\t')
    except csv.Error:
        dialect=csv.excel
    return list(csv.DictReader(io.StringIO(content),dialect=dialect))


def import_data(db,settings,request):
    if request.is_demo:
        raise ValueError('Le importazioni dimostrative non sono supportate.')
    if not request.permission_confirmed:
        raise ValueError('Conferma di poter usare e importare i contenuti.')
    if len(request.content.encode())>settings.max_import_bytes:
        raise ValueError('Import oltre il limite di 4 MB.')
    if request.kind=='benchmarks':
        rows=read_csv(request.content)
        if not 1<=len(rows)<=2000:raise ValueError('Importa da 1 a 2000 righe per volta.')
        validated=[]
        for index,row in enumerate(rows,2):
            try:
                row={k:v for k,v in row.items() if k and v!=''}
                row['is_demo']=request.is_demo
                for k in ('min_sqm','max_sqm'):row[k]=number(row.get(k))
                validated.append(BenchmarkInput.model_validate(row).model_dump())
            except Exception as exc:raise ValueError(f'Riga benchmark {index}: {str(exc)[:250]}') from exc
        with db.transaction() as con:
            for row in validated:
                # Re-import of the exact same series/period replaces, does not multiply.
                con.execute('''DELETE FROM benchmarks WHERE city=? AND zone=? AND property_type=? AND condition=?
                        AND area_basis=? AND currency=? AND transaction_type=? AND period=? AND is_demo=?''',
                        tuple(row[k] for k in ('city','zone','property_type','condition','area_basis','currency','transaction_type','period','is_demo')))
                row.update(id=uid(),imported_at=now())
                keys=list(row)
                con.execute(f"INSERT INTO benchmarks({','.join(keys)}) VALUES({','.join('?' for _ in keys)})",tuple(row[k] for k in keys))
        for p in db.all('SELECT id FROM properties WHERE is_demo=?',(int(request.is_demo),)):
            refresh_analysis(db,p['id'])
        return {'imported':len(validated),'kind':'benchmarks','is_demo':request.is_demo}
    listings=[]
    if request.kind=='html':
        if not request.source_url:raise ValueError('Indica la URL originaria del documento HTML.')
        listings=[extract_listing(request.content,request.source_url,is_demo=request.is_demo)]
    else:
        rows=read_csv(request.content)
        if not 1<=len(rows)<=2000:raise ValueError('Importa da 1 a 2000 righe per volta.')
        allowed=set(Listing.model_fields)-{'evidence','is_demo','images'}
        for index,row in enumerate(rows,2):
            try:
                item={k:v for k,v in row.items() if k in allowed and v!=''}
                item['url']=item.get('url') or f'import://csv/{hashlib.sha256(dump(item).encode()).hexdigest()[:24]}'
                item['listing_key']=item.get('listing_key') or hashlib.sha256(canonical_url(item['url']).encode()).hexdigest()[:24]
                for key in ('price','surface','rooms','bathrooms'):
                    if key in item:item[key]=number(item[key])
                if 'is_auction' in item:item['is_auction']=str(item['is_auction']).lower() in ('true','1','si','sì')
                item['is_demo']=request.is_demo
                item['evidence']={k:{'method':'CSV importato; dichiarato dal cliente','value':v,'source_url':item['url']} for k,v in item.items() if k not in ('evidence','is_demo')}
                listings.append(Listing.model_validate(item))
            except Exception as exc:raise ValueError(f'Riga annuncio {index}: {str(exc)[:250]}') from exc
    sid='imports-real'
    db.execute('INSERT INTO sources(id,name,kind,domain,config,status,permission_at,permission_note,created_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',
               (sid,'Import cliente','import','',dump({'is_demo':request.is_demo}),
                'healthy',now(),'Contenuti importati con dichiarazione di disponibilità dei diritti.',now()))
    new=0;changed=0
    for listing in listings:
        _,created,updated=upsert_listing(db,settings,sid,listing,raw=request.content if request.kind=='html' else dump(listing.model_dump()))
        new+=created;changed+=updated and not created
    return {'imported':len(listings),'new':new,'changed':changed,'is_demo':request.is_demo,'kind':request.kind}
