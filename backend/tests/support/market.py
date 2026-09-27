"""Synthetic benchmark and OMI documents only for the disposable browser QA."""
import json
from hashlib import sha256
from urllib.parse import urlencode
from app.db import now,uid
from app.services.omi import BASE,VERSION


def seed_market(db,settings):
    template=db.one('SELECT * FROM benchmarks WHERE is_demo=0 LIMIT 1')
    row={**template,'id':uid(),'city':'QA città benchmark','zone':'Centro','currency':'USD','source_label':'QA fonte benchmark','source_url':'https://example.test/benchmark'}
    keys=list(row);db.execute('INSERT INTO benchmarks('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(row[k] for k in keys))
    root=settings.data_dir/'market-cache';root.mkdir(exist_ok=True)
    def document(path,body):
        url=BASE+path
        (root/(sha256(url.encode()).hexdigest()+'.json')).write_text(json.dumps({'body':body,'source_url':url,'retrieved_at':now(),'version':VERSION}))
    def data(params,value):document('zoneomi.php?'+urlencode(params),json.dumps(value))
    data({'richiesta':1},[{'PROVINCIA':'MI','DIZIONE':'Milano QA'}])
    data({'richiesta':2,'prov':'MI'},[{'CODCOM':'F205','DIZIONE':'Milano QA'}])
    data({'richiesta':5},[{'SEMESTRE':'20252'}])
    features=[{'type':'Feature','properties':{'zona':zone,'descZona':name},'geometry':{'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}} for zone,name in [('B1','Centro QA'),('D1','Periferia QA')]]
    data({'richiesta':6,'codcom':'F205','semestre':'20252'},{'cod':0,'dat':{'features':features}})
    for zone in ('B1','D1'):
        data({'richiesta':8,'codcom':'F205','semestre':'20252','zo':zone},[{'DESCR_TIPOLOGIA':u+' QA','LINK_ZONA':'MI00000001'} for u in 'RCPT'])
        for usage in 'RCPT':
            cells=['QA '+usage+' '+zone,'Normale','2000','3000','L','1','2','L']
            document(f'stampaomi.php?F205/MI00000001/20252/{usage}/{zone}/0/0','<h1>Anno 2025 - Semestre 2</h1><table><tr>'+''.join('<td>'+x+'</td>' for x in cells)+'</tr></table>')
    return row['id']
