"""Four separate references from observed, compatible evidence; never a valuation."""
from datetime import datetime, timedelta, timezone
from statistics import median


class MarketReferences:
    def __init__(self, db):
        self.db=db
        self.cache={}
        from .asset_evidence import AssetEvidence
        self.assets=AssetEvidence(db)

    def root(self,ident):return self.assets.root(ident)

    def for_property(self,p,same_condition=False):
        categories=[('to_renovate','Da ristrutturare'),('renovated','Ristrutturato'),('new','Nuovo')]
        if same_condition:categories=[(p.get('condition'),'Stesso stato')]
        required=('city','zone','property_type','area_basis','currency','transaction_type')
        # An undeclared surface basis is compared only with other undeclared ones (equality below),
        # never mixed with commercial or net surfaces.
        missing=[k for k in required if not p.get(k) or (p[k] in ('unknown','XXX') and k!='area_basis')]
        labels={'city':'comune','zone':'zona','property_type':'tipologia','area_basis':'tipo di superficie','currency':'valuta','transaction_type':'vendita o affitto','surface':'superficie','condition':'stato manutentivo'}
        if not p.get('surface'):missing.append('surface')
        if same_condition and p.get('condition') in (None,'','unknown'):missing.append('condition')
        auction=same_condition and p.get('is_auction')
        if p.get('is_demo'):missing.append('annuncio reale')
        items=[];limited=False
        if not missing and not auction and (same_condition or p['transaction_type']=='sale'):
            key=tuple(str(p[k]).casefold() for k in required)
            if key not in self.cache:
                instant=datetime.now(timezone.utc)
                cutoff=(instant-timedelta(days=90)).isoformat(timespec='seconds')
                where=' AND '.join(f'lower(p.{k})=?' for k in required)
                self.cache[key]=self.db.all('SELECT p.*,s.name source_name,s.domain source_domain FROM properties p JOIN sources s ON s.id=p.source_id WHERE '+where+" AND p.is_demo=0 AND p.is_auction=0 AND p.availability='listed' AND p.price>0 AND p.surface>0 AND p.last_seen>=? AND p.last_seen<=? ORDER BY p.last_seen DESC,p.id LIMIT 1001",key+(cutoff,instant.isoformat()))
            raw=self.cache[key];limited=len(raw)>1000
            self.assets.preload(row['id'] for row in raw[:1000] if len(self.assets.members(row['id']))>1)
            seen={self.root(p['id'])}
            for row in raw[:1000]:
                if row['condition'] not in {c[0] for c in categories} or not p['surface']*.7<=row['surface']<=p['surface']*1.3:continue
                cluster=self.root(row['id'])
                if cluster in seen or cluster in self.assets.contradictions:continue
                if len(self.assets.members(row['id']))>1:
                    cross=self.assets.for_property(row)
                    if cross['conflicts'] or cross['limited']:continue
                seen.add(cluster)
                items.append({'id':row['id'],'title':row['title'],'condition':row['condition'],'price_sqm':round(row['price']/row['surface'],2),'surface':row['surface'],'price':row['price'],'currency':row['currency'],'url':row['url'],'source':row['source_name'],'source_id':row['source_id'],'source_domain':row['source_domain'],'observed_at':row['last_seen']})
        groups=[]
        for condition,label in categories:
            sample=[r for r in items if r['condition']==condition]
            values=[r['price_sqm'] for r in sample]
            enough=len(sample)>=3
            sources=len({r['source_domain'] or r['source_id'] for r in sample})
            ordered=sorted(values)
            def percentile(fraction):
                index=(len(ordered)-1)*fraction;lower=int(index);upper=min(lower+1,len(ordered)-1)
                return round(ordered[lower]+(ordered[upper]-ordered[lower])*(index-lower),2)
            spread=round((max(values)-min(values))/median(values)*100,1) if enough else None
            warnings=[]
            if sample and sources==1:warnings.append('Una sola fonte nel campione')
            if enough and spread>50:warnings.append('Prezzi molto dispersi: confronta i singoli annunci')
            if len(sample)>12:warnings.append('Mostrati i primi 12 asset del campione')
            groups.append({'key':condition,'label':label,'count':len(sample),'median_sqm':round(median(values),2) if enough else None,'min_sqm':min(values) if enough else None,'max_sqm':max(values) if enough else None,'items':sample[:12], 'source_count':sources,'asking_delta_pct':round((p['price']/p['surface']/median(values)-1)*100,1) if enough and p.get('price') and p.get('condition')==condition else None,'q1_sqm':percentile(.25) if enough else None,'q3_sqm':percentile(.75) if enough else None,'spread_pct':spread,'oldest_observed':min((r['observed_at'] for r in sample),default=None),'newest_observed':max((r['observed_at'] for r in sample),default=None),'warnings':warnings, 'reason':('Dati mancanti: '+', '.join(labels.get(k,k) for k in missing)) if missing else 'Per le aste serve un confronto dedicato' if auction else 'Solo compravendite' if not same_condition and p.get('transaction_type')!='sale' else 'Servono almeno 3 asset confrontabili' if not enough else 'Prezzi richiesti osservati'})
        return {'groups':groups,'omi':p.get('market_context',{}),'sample_limited':limited,'method':'Zona dichiarata coincidente, stessa tipologia, valuta, operazione e base superficie (non dichiarata solo con non dichiarata); superficie ±30%; ultimi 90 giorni. Aste, annunci chiusi e duplicati confermati esclusi; asset con dati discordanti tra fonti da verificare. Buono non equivale a ristrutturato. Prezzi richiesti, non prezzi di transazione.'}
