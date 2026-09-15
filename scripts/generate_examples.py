#!/usr/bin/env python3
"""Rebuild explicitly synthetic import fixtures; never downloads external data."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import io
import json

ROOT=Path(__file__).resolve().parents[1]


def csv_bytes(rows):
    output=io.StringIO(newline='')
    writer=csv.DictWriter(output,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
    return output.getvalue()


def main():
    rows=[{'listing_key':'sample-office-001','url':'demo://examples/office-001','title':'ESEMPIO SINTETICO · Ufficio da ristrutturare',
      'city':'Milano','zone':'Zona Campione','address':'Via Campione 1','property_type':'office','condition':'to_renovate',
      'price':600000,'surface':400,'area_basis':'commercial','currency':'EUR','transaction_type':'sale',
      'description':'DATO SINTETICO. Ufficio da ristrutturare, con possibile cambio d’uso dichiarato nell’esempio. Urbanistica e costi non verificati.'},
      {'listing_key':'sample-flat-002','url':'demo://examples/flat-002','title':'ESEMPIO SINTETICO · Appartamento locato',
       'city':'Monza','zone':'Zona Campione','address':'Via Campione 2','property_type':'residential','condition':'good',
       'price':310000,'surface':120,'area_basis':'commercial','currency':'EUR','transaction_type':'sale',
       'description':'DATO SINTETICO. Appartamento a reddito; il contratto di locazione non è allegato.'},
      {'listing_key':'sample-missing-003','url':'demo://examples/missing-003','title':'ESEMPIO SINTETICO · Prezzo non disponibile',
       'city':'Como','zone':'Zona Campione','address':'','property_type':'office','condition':'unknown',
       'price':'','surface':210,'area_basis':'unknown','currency':'EUR','transaction_type':'sale',
       'description':'DATO SINTETICO. Il prezzo e la base di superficie non sono specificati.'}]
    benchmarks=[]
    for p,minimum,maximum in [(rows[0],1800,2200),(rows[1],2200,2600)]:
        benchmarks.append({k:p[k] for k in ('city','zone','property_type','condition','area_basis','currency','transaction_type')}|
          {'min_sqm':minimum,'max_sqm':maximum,'period':f'{datetime.now(timezone.utc).year}-S1',
           'source_label':'ESEMPIO SINTETICO, NON OMI','source_url':'demo://examples/benchmark'})
    node={'@context':'https://schema.org','@type':'RealEstateListing','name':rows[0]['title'],'description':rows[0]['description'],
          'offers':{'price':600000,'priceCurrency':'EUR','businessFunction':'http://purl.org/goodrelations/v1#Sell'},
          'floorSize':{'value':400,'unitCode':'MTK'},'address':{'streetAddress':'Via Campione 1','addressLocality':'Milano'},
          'additionalProperty':[{'@type':'PropertyValue','name':k,'value':rows[0][k]} for k in ('zone','property_type','condition','area_basis')]}
    html='<!doctype html><html lang="it"><meta charset="utf-8"><title>VEDRA · Fixture sintetica</title><script type="application/ld+json">'+json.dumps(node,ensure_ascii=False)+'</script><h1>'+rows[0]['title']+'</h1><p>Questa pagina è una fixture. Non rappresenta un immobile sul mercato.</p></html>'
    for folder in (ROOT/'frontend/public/examples',ROOT/'fixtures/imports'):
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'properties-demo.csv').write_text(csv_bytes(rows))
        (folder/'benchmarks-demo.csv').write_text(csv_bytes(benchmarks))
        (folder/'listing-demo.html').write_text(html)
    folder=ROOT/'fixtures/html';folder.mkdir(parents=True,exist_ok=True)
    (folder/'listing.html').write_text(html)
    (folder/'catalog.html').write_text('<!doctype html><h1>Catalogo di test sintetico</h1><a class="property-link" href="/immobili/001">Ufficio</a><a class="property-link" href="/immobili/002">Appartamento</a><a rel="next" href="/vendita/milano/?page=2">Pagina successiva</a>')
    (folder/'robots.txt').write_text('User-agent: *\nAllow: /\n')
    source={'name':'Esempio, sostituire con fonte autorizzata','domain':'catalog.example',
      'config':{'search_url':'https://catalog.example/vendita/{city}/','listing_selector':'a.property-link','listing_url_pattern':'/immobili/','next_selector':'a[rel="next"]','fields':{},'max_pages':2,'render_js':False},
      'permission_note':'Sostituire con il riferimento al permesso effettivo prima di usare la fonte.','permission_confirmed':False}
    (ROOT/'fixtures/source.example.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
    print('Fixture sintetiche rigenerate. Nessun accesso di rete.')

if __name__=='__main__':main()
