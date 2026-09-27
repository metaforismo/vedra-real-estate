"""On-demand national OMI references from the public GeoPOI consultation.

Quotes remain official ranges, not observations of individual transactions.
Published listing coordinates locate a point; they do not certify an address.
"""
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import re
import unicodedata
from uuid import uuid4
import httpx
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from ..connectors.safe_http import SafeFetcher, SourceBlocked
from ..db import now

HOST='www1.agenziaentrate.gov.it'
BASE='https://'+HOST+'/servizi/geopoi_omi/'
VERSION='omi-public/1.0'


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold()) if c.isalnum())


def checked(value,pattern):
    if not re.fullmatch(pattern,value):raise ValueError('Codice OMI non valido.')
    return value


def point_in_ring(x,y,ring):
    inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        ax,ay=a[:2];bx,by=b[:2]
        if ((ay>y)!=(by>y)) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside


def zone_at(features,lat,lon):
    matches=[]
    for f in features:
        g=f.get('geometry',{});polys=[g.get('coordinates',[])] if g.get('type')=='Polygon' else g.get('coordinates',[]) if g.get('type')=='MultiPolygon' else []
        # GeoPOI rings are not consistently outer-ring first; parity also handles holes.
        if any(sum(point_in_ring(lon,lat,r) for r in poly)%2 for poly in polys):
            distance=math.inf
            for poly in polys:
                for ring in poly:
                    for a,b in zip(ring,ring[1:]+ring[:1]):
                        ax=(a[0]-lon)*111320*math.cos(math.radians(lat));ay=(a[1]-lat)*111320
                        bx=(b[0]-lon)*111320*math.cos(math.radians(lat));by=(b[1]-lat)*111320
                        dx=bx-ax;dy=by-ay
                        t=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy))) if dx or dy else 0
                        distance=min(distance,math.hypot(ax+t*dx,ay+t*dy))
            matches.append((f,round(distance,1)))
    return matches[0] if len(matches)==1 and matches[0][1]>=20 else None


def parse_quotes(html):
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for tr in soup.select('tr'):
        cells=[' '.join(x.get_text(' ',strip=True).split()) for x in tr.select('td')]
        if len(cells)!=8:continue
        try:
            low,high=float(cells[2].replace(',','.')),float(cells[3].replace(',','.'))
        except ValueError:continue
        if not 0<low<=high<1_000_000 or cells[4] not in ('L','N'):continue
        rows.append({'type':cells[0],'condition':cells[1],'min_sqm':low,'max_sqm':high,
                     'area_basis':'gross' if cells[4]=='L' else 'net'})
    if not rows:raise ValueError('Tabella OMI assente o formato cambiato.')
    return rows


class OmiClient:
    def __init__(self,settings):
        self.settings=replace(settings,live_domains=[HOST])
        self.root=settings.data_dir/'market-cache'
        self.lock=asyncio.Lock();self.last_request=0;self.robots=None

    async def document(self,path,ttl=30*86400):
        if not self.settings.omi_enabled:raise ValueError('Consultazione OMI non attivata.')
        url=BASE+path;key=sha256(url.encode()).hexdigest();file=self.root/(key+'.json')
        async with self.lock:
            if file.exists():
                data=json.loads(file.read_text())
                age=(datetime.now(timezone.utc)-datetime.fromisoformat(data['retrieved_at'])).total_seconds()
                if 0<=age<ttl:return data
            fetcher=SafeFetcher(HOST,self.settings);fetcher.last_request=self.last_request;fetcher.robots=self.robots
            try:body,final=await fetcher.get(url)
            except (SourceBlocked,httpx.HTTPError,OSError) as exc:
                raise ValueError('Fonte OMI temporaneamente non disponibile; riprova più tardi.') from exc
            finally:self.last_request=fetcher.last_request;self.robots=fetcher.robots
            data={'body':body,'source_url':final,'retrieved_at':now(),'version':VERSION}
            self.root.mkdir(parents=True,exist_ok=True)
            temp=file.with_suffix('.'+uuid4().hex+'.tmp');temp.write_text(json.dumps(data));temp.replace(file)
            return data

    async def data(self,**params):
        doc=await self.document('zoneomi.php?'+urlencode(params),86400 if params['richiesta']==5 else 30*86400)
        try:return json.loads(doc['body']),doc
        except json.JSONDecodeError as exc:raise ValueError('Risposta OMI non valida.') from exc

    async def provinces(self):
        data,_=await self.data(richiesta=1)
        return [{'code':checked(x['PROVINCIA'],r'[A-Z]{2}'),'name':x['DIZIONE']} for x in data]

    async def cities(self,province):
        data,_=await self.data(richiesta=2,prov=checked(province,r'[A-Z]{2}'))
        return [{'code':checked(x['CODCOM'],r'[A-Z][0-9]{3}'),'name':x['DIZIONE'],'province':province} for x in data]

    async def periods(self):
        data,_=await self.data(richiesta=5)
        return sorted({checked(x['SEMESTRE'],r'20[0-9]{2}[12]') for x in data},reverse=True)

    async def zones(self,city_code,period=None):
        period=period or (await self.periods())[0]
        geo,doc=await self.data(richiesta=6,codcom=checked(city_code,r'[A-Z][0-9]{3}'),semestre=checked(period,r'20[0-9]{2}[12]'))
        if not isinstance(geo,dict) or geo.get('cod')!=0 or not isinstance(geo.get('dat'),dict):raise ValueError('Perimetri OMI non disponibili per comune e periodo.')
        features=geo['dat'].get('features',[])
        if not features:raise ValueError('Nessuna zona OMI disponibile.')
        return features,period,doc

    async def quotes(self,city_code,zone,period,usage='R'):
        checked(city_code,r'[A-Z][0-9]{3}');checked(zone,r'[BCDER][0-9]{1,3}');checked(period,r'20[0-9]{2}[12]');checked(usage,r'[RCPT]')
        uses,_=await self.data(richiesta=8,codcom=city_code,semestre=period,zo=zone)
        use=next((x for x in uses if x['DESCR_TIPOLOGIA'].startswith(usage)),None)
        if not use:raise ValueError('Quotazioni assenti per questa destinazione e zona.')
        link=checked(use['LINK_ZONA'],r'[A-Z]{2}[0-9]{8}')
        # The final coordinates only center the printable map; the quote is keyed by codes.
        doc=await self.document(f'stampaomi.php?{city_code}/{link}/{period}/{usage}/{zone}/0/0')
        rows=parse_quotes(doc['body'])
        text=BeautifulSoup(doc['body'],'html.parser').get_text(' ',strip=True)
        if not re.search(r'Anno\s*'+period[:4]+r'\s*-\s*Semestre\s*'+period[-1],text):raise ValueError('Periodo della tabella OMI incoerente.')
        return {'rows':rows,'period':period[:4]+'-S'+period[-1],'city_code':city_code,'zone_code':zone,
                'source_url':doc['source_url'],'retrieved_at':doc['retrieved_at'],'source_label':'Agenzia Entrate – OMI','version':VERSION}

    def cached_cities(self):
        results={}
        for file in self.root.glob('*.json'):
            try:
                doc=json.loads(file.read_text())
                if 'richiesta=2&prov=' not in doc['source_url']:continue
                province=doc['source_url'].rsplit('prov=',1)[1]
                for x in json.loads(doc['body']):results[x['CODCOM']]={'code':x['CODCOM'],'name':x['DIZIONE'],'province':province}
            except (ValueError,KeyError,TypeError):continue
        return list(results.values())

    async def enrich(self,listing,city_hint=''):
        if not self.settings.omi_enabled:return
        if listing.latitude is None or listing.longitude is None:
            listing.evidence['market_context']={'status':'unavailable','reason':'Coordinate della fonte assenti: impossibile assegnare una zona OMI.'};return
        cities=[c for c in self.cached_cities() if norm(c['name'])==norm(listing.city or city_hint)]
        if len(cities)!=1:
            listing.evidence['market_context']={'status':'unavailable','reason':'Comune non identificato univocamente nel catalogo OMI. Consulta il comune in Benchmark.'};return
        city=cities[0]
        try:
            features,period,geo_doc=await self.zones(city['code'])
            match=zone_at(features,listing.latitude,listing.longitude)
            if not match:raise ValueError('Punto fuori perimetro, ambiguo o a meno di 20 m dal confine OMI.')
            feature,distance=match;zone=checked(feature['properties']['zona'],r'[BCDER][0-9]{1,3}')
            if not listing.city:
                listing.city=city['name']
                listing.evidence['city']={'method':'published point inside official OMI municipality','value':city['name'],'source_url':geo_doc['source_url']}
            if not listing.zone:
                listing.zone=zone
                listing.evidence['zone']={'method':'published point inside official OMI polygon; address precision unverified','value':zone,'source_url':geo_doc['source_url']}
            usage={'residential':'R','commercial':'C','office':'T','logistics':'P'}.get(listing.property_type)
            if not usage:raise ValueError('Tipologia non supportata per il confronto OMI.')
            context=await self.quotes(city['code'],zone,period,usage)
            context.update(status='available',zone_label=feature['properties'].get('descZona',zone),
                geometry_source=geo_doc['source_url'],boundary_distance_m=distance,
                location_method='Intersezione del punto pubblicato dalla fonte con i perimetri OMI; posizione da verificare.',
                latitude=listing.latitude,longitude=listing.longitude)
            listing.evidence['market_context']=context
            # Keep OMI geography separate from the listing's own neighborhood text.
        except (SourceBlocked,ValueError,KeyError,TypeError) as exc:
            listing.evidence['market_context']={'status':'unavailable','reason':str(exc)[:250]}


def reference_scenarios(p):
    context=p.get('evidence',{}).get('market_context',{})
    if context.get('status')!='available':return context
    result=dict(context);result['scenarios']=[]
    try:
        year=int(context['period'][:4]);month=6 if context['period'][-1]=='1' else 12
        current=datetime.now(timezone.utc);age=(current.year-year)*12+current.month-month
    except (KeyError,ValueError):return {'status':'unavailable','reason':'Periodo OMI non valido.'}
    result['stale']=age>18 or age<0
    if result['stale']:return result
    if p.get('currency')!='EUR' or p.get('transaction_type')!='sale' or not p.get('surface') or not p.get('price'):return result
    for row in context['rows']:
        if p.get('property_type')=='residential' and not row['type'].casefold().startswith(('abitazioni','ville')):continue
        low=row['min_sqm'];high=row['max_sqm'];sqm=p['price']/p['surface']
        result['scenarios'].append(row|{'range_min':round(low*p['surface']), 'range_max':round(high*p['surface']),
            'delta_midpoint_pct':round((sqm/((low+high)/2)-1)*100,1),
            'assumptions':['Immobile classificabile come '+row['type'], 'Stato OMI '+row['condition'],
                           'Superficie interamente '+('lorda' if row['area_basis']=='gross' else 'netta'),
                           'Posizione pubblicata dalla fonte corretta'],
            'kind':'conditional_reference','confidence':'non_calibrata'})
    return result
