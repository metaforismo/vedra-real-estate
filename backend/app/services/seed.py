from __future__ import annotations

import html
import json
from datetime import datetime,timedelta,timezone

from ..db import dump,now,uid
from ..schemas import Listing
from ..connectors.parser import extract_listing
from .store import upsert_listing,link_agent

CITIES={
 'Milano': [('Lambrate',2600),('Bovisa',2300),('Porta Romana',5100),('Navigli',4300)],
 'Monza': [('Centro',2900),('San Biagio',2200),('Triante',2100),('San Rocco',1700)],
 'Como': [('Camerlata',2100),('Borghi',2900),('Centro',3900),('Tavernola',2400)]
}
DESCRIPTIONS=[
 'Ufficio da ristrutturare, spazi aperti e doppio accesso. Il venditore dichiara un possibile cambio d’uso a residenziale, da verificare con un tecnico. Superficie commerciale dichiarata.',
 'Appartamento frazionabile con ingresso indipendente e balcone. Da ristrutturare. La configurazione dei locali e i costi di riqualificazione richiedono sopralluogo.',
 'Negozio a reddito, attualmente locato. Contratto e canone da verificare in due diligence. Buono stato manutentivo dichiarato.',
 'Villa da ristrutturare con giardino. Possibile valorizzazione degli spazi esistenti, senza indicazioni documentate di nuova volumetria.',
 'Ufficio in buono stato con sale riunioni e accesso indipendente. Nessuna ipotesi di conversione verificata. Disponibile per sopralluogo.',
 'Capannone in buono stato con area di carico. Immobile locato: verificare durata residua e posizione del conduttore.',
 'Appartamento da ristrutturare con tre esposizioni. La riqualificazione potrebbe migliorare la fruibilità; nessun rendimento è garantito.',
 'Negozio in buono stato. Non è possibile un cambio di destinazione e non è previsto frazionamento, secondo il testo dimostrativo.',
 'Terreno edificabile con documentazione urbanistica da acquisire. Ogni sviluppo resta subordinato alla verifica degli indici e dei vincoli.',
 'Palazzina da ristrutturare. Possibile cambio d’uso dichiarato dal proponente, non certificato. Dati catastali non disponibili.',
 'Appartamento in buono stato, a reddito. Canone e spese non specificati nella scheda; l’ottimizzazione deve essere approfondita.',
 'Laboratorio da ristrutturare, con accesso al piano terra. Il prezzo non è indicato in questo esempio per mostrare un caso di dato mancante.'
]
TYPES=['office','residential','commercial','residential','office','logistics','residential','commercial','land','office','residential','office']
NAMES=['Spazi direzionali da ripensare','Appartamento con doppio ingresso','Locale commerciale a reddito','Villa con giardino privato','Uffici con ingresso indipendente','Spazio logistico con cortile','Residenza da valorizzare','Negozio con vetrine su strada','Area di sviluppo residenziale','Palazzina indipendente','Appartamento locato','Laboratorio al piano terra']
SURFACES=[510,175,280,320,240,740,145,180,1600,660,115,210]
DISCOUNTS=[.28,.21,.06,.16,-.09,.13,.31,-.04,.10,.24,.08,.19]


def demo_records(city: str) -> list[tuple[Listing,str]]:
    if city not in CITIES:return []
    output=[]
    for i in range(12):
        zone,base=CITIES[city][i%4]
        multiplier={'office':.76,'commercial':.90,'residential':1,'logistics':.42,'land':.22}[TYPES[i]]
        midpoint=base*multiplier
        surface=SURFACES[i]
        price=round(surface*midpoint*(1-DISCOUNTS[i])/1000)*1000 if i!=11 else None
        condition='to_renovate' if i in (0,1,3,6,9,11) else 'good'
        address=f'Via Esempio {10+i}' if i not in (3,9) else None
        url=f'demo://{city.lower()}/immobile/{i+1:03}'
        data={'@context':'https://schema.org','@type':'RealEstateListing','name':f'{NAMES[i]} · {zone}',
              'description':DESCRIPTIONS[i],'offers':{'@type':'Offer','price':price,'priceCurrency':'EUR','businessFunction':'http://purl.org/goodrelations/v1#Sell'},
              'floorSize':{'@type':'QuantitativeValue','value':surface,'unitCode':'MTK'},
              'address':{'@type':'PostalAddress','addressLocality':city,'streetAddress':address},
              'numberOfRooms': [8,5,3,9,6,2,4,2,None,12,3,4][i]}
        fixture=f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><title>VEDRA fixture sintetica</title>
<script type="application/ld+json">{json.dumps(data,ensure_ascii=False)}</script></head>
<body><p>DATI SINTETICI, NON È UN ANNUNCIO REALE.</p><h1>{html.escape(data['name'])}</h1>
<span class="zone">{zone}</span><span class="asset-type">{TYPES[i]}</span>
<span class="condition">{condition}</span><span class="area-basis">commercial</span></body></html>'''
        parsed=extract_listing(fixture,url,{'zone':'.zone','property_type':'.asset-type','condition':'.condition','area_basis':'.area-basis'},is_demo=True)
        output.append((parsed,fixture))
    return output


def seed(db,settings):
    if db.one("SELECT id FROM sources WHERE kind='demo' LIMIT 1"):return
    for city,zones in CITIES.items():
        for zone,base in zones:
            for typ,mult in {'office':.76,'commercial':.90,'residential':1,'logistics':.42,'land':.22}.items():
                for condition in ('to_renovate','good'):
                    year=datetime.now(timezone.utc).year
                    db.execute('INSERT INTO benchmarks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (uid(),city,zone,typ,condition,'commercial','EUR','sale',round(base*mult*.9),round(base*mult*1.1),f'{year}-S1',
                        'Benchmark sintetico Vedra, non OMI','demo://benchmark',1,now()))
    for index,city in enumerate(CITIES):
        sid=f'demo-{city.lower()}'
        db.execute('INSERT INTO sources(id,name,kind,domain,config,status,created_at) VALUES(?,?,?,?,?,?,?)',
                   (sid,f'Catalogo demo · {city}','demo','',dump({'city':city}),'healthy',now()))
        aid=f'agent-{city.lower()}'
        criteria={'max_price':1500000,'min_surface':100,'max_surface':None,'property_types':[],
                  'strategies':[],'min_discount':None,'include_auctions':True,'max_listings':30}
        agent={'id':aid,'name':f'{city} · '+['Value Add','Opportunità','Asset Discovery'][index],'city':city,'criteria':criteria,
               'source_ids':[sid],'runtime':'local','interval_minutes':60,'active':True}
        nxt=(datetime.now(timezone.utc)+timedelta(minutes=60)).isoformat(timespec='seconds')
        db.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (aid,agent['name'],city,dump(criteria),dump([sid]),'local',60,1,nxt,now(),now()))
        rid=uid()
        db.execute('INSERT INTO runs(id,agent_id,status,trigger,runtime,created_at,started_at,finished_at,is_demo,collected,analysis_done,config_snapshot) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   (rid,aid,'completed','seed','local',now(),now(),now(),1,1,1,dump(agent)))
        for listing,fixture in demo_records(city):
            pid,_,_=upsert_listing(db,settings,sid,listing,raw=fixture,run_id=rid)
            link_agent(db,agent,pid)
        qualified=db.one('SELECT COUNT(*) n FROM agent_properties WHERE agent_id=? AND fit=1',(aid,))['n']
        stats={'found':12,'processed':12,'new':12,'changed':0,'errors':0,'qualified':qualified,'sources_ok':1,'sources_total':1}
        db.execute('UPDATE runs SET stats=? WHERE id=?',(dump(stats),rid))
        db.event(rid,'seed','Dataset dimostrativo inizializzato da fixture HTML locali. Nessuno scraping live.',data=stats)
    for p in db.all('SELECT id FROM properties WHERE score>=80 ORDER BY score DESC LIMIT 3'):
        db.execute("UPDATE properties SET starred=1,review_status='shortlisted' WHERE id=?",(p['id'],))
