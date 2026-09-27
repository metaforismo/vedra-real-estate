"""Source availability is independent of the team's deal stage."""
import asyncio
import csv
import io
from itertools import chain
import re
import shutil
import subprocess
from hashlib import sha256

from ..db import now
from .media import ImageStore

CLOSED = {'sold', 'rented', 'withdrawn'}
LABELS = {'sold':'Venduto', 'rented':'Affittato', 'withdrawn':'Ritirato',
          'listed':'Pubblicato', 'unknown':'Da verificare', 'review':'Da verificare'}
WORDS = {'venduto':'sold', 'venduta':'sold', 'sold':'sold', 'affittato':'rented',
         'affittata':'rented', 'ritirato':'withdrawn', 'ritirata':'withdrawn'}


def explicit_status(text):
    text=' '.join(str(text).casefold().split())
    for match in re.finditer(r'\b(vendut[oa]|sold|affittat[oa]|ritirat[oa])\b',text):
        # An advertisement saying "non ancora venduto" is not a sale event.
        if re.search(r'\b(non|mai|se|sarà|verrà|viene)\b',text[max(0,match.start()-30):match.start()]):continue
        return WORDS[match.group()],match.group()
    return None


def image_status(body):
    """Bounded raster OCR. Only exact, high-confidence status words close a listing."""
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS=20_000_000
    with Image.open(io.BytesIO(body)) as original:
        if original.width*original.height>20_000_000:raise ValueError('Immagine troppo grande')
        im=ImageOps.exif_transpose(original).convert('RGB')
        im.thumbnail((1800,1800))
        from .status_ocr import ribbon_crop
        ribbon=ribbon_crop(im)
        variants=chain([(ribbon[0],ribbon[1],7,'ribbon')] if ribbon else [],
                       ((im.rotate(angle,expand=True,fillcolor='white'),angle,11,'page')
                        for angle in (0,-32,32,-45,45)))
        uncertain=None
        for raster,angle,mode,region in variants:
            out=io.BytesIO();raster.save(out,format='PNG')
            result=subprocess.run(['tesseract','stdin','stdout','--psm',str(mode),'tsv'],
                                  input=out.getvalue(),capture_output=True,timeout=12,check=True)
            rows=list(csv.DictReader(io.StringIO(result.stdout.decode('utf-8',errors='replace')),delimiter='\t'))
            for row in rows:
                word=re.sub(r'[^a-z]','',row.get('text','').casefold())
                confidence=float(row.get('conf',-1))
                if word in WORDS and confidence>=50:
                    line=' '.join(r.get('text','') for r in rows if all(r.get(k)==row.get(k) for k in ('block_num','par_num','line_num')))
                    if explicit_status(line):
                        evidence={'status':WORDS[word] if confidence>=85 else 'review',
                                  'word':word,'confidence':round(confidence,1),'rotation':angle,'region':region}
                        if confidence>=85:return evidence
                        uncertain=evidence
        if uncertain:return uncertain
        if ribbon:
            return {'status':'review','word':'','confidence':None,'rotation':ribbon[1],
                    'region':'ribbon','reason':'Fascia grafica rilevata; stato non leggibile con certezza.'}
    return None


class AvailabilityChecker:
    def __init__(self,settings):
        self.settings=settings
        self.images=ImageStore(settings)

    async def enrich(self,listing,retain_images=False):
        evidence=listing.evidence.get('availability',{})
        if listing.availability in CLOSED:return
        checked=0;errors=[]
        if retain_images and listing.images:
            if not shutil.which('tesseract'):
                errors.append('OCR non disponibile')
            else:
                for url in listing.images[:2]:
                    try:
                        body,_=await self.images.get(url)
                        result=await asyncio.to_thread(image_status,body)
                        checked+=1
                        if result:
                            listing.availability=result['status']
                            listing.evidence['availability']={'method':'image OCR / exact status word' if result['status'] in CLOSED else 'image OCR / review required',
                                'value':result['word'],'source_url':url,'checked_at':now(),
                                'sha256':sha256(body).hexdigest(),**result}
                            return
                    except Exception as exc:
                        errors.append(type(exc).__name__)
        listing.availability='review' if errors else 'listed'
        listing.evidence['availability']={'method':'published listing / status checks',
            'value':listing.availability,'source_url':listing.url,'checked_at':now(),
            'images_checked':checked,'images_total':len(listing.images),'errors':errors,
            'note':'Pagina pubblicata; disponibilità da confermare con la fonte.'}


def priority(p,benchmark=None,analysis=None):
    from .analysis import completeness
    analysis=analysis or p.get('analysis') or {}
    state=p.get('availability','unknown')
    if state in CLOSED or state=='review':
        return {'score':0,'label':LABELS[state],'version':'triage/1.0','factors':[],
                'reason':'Annuncio non attivo: escluso dalle ricerche.'}
    quality=round(completeness(p)[0]*.3,1)
    availability=10 if state=='listed' else 0
    # A published page cannot earn the 20 points reserved for source-confirmed availability.
    economics=0
    economic_label='Confronto economico assente'
    if benchmark and p.get('price') and p.get('surface'):
        mid=(benchmark['min_sqm']+benchmark['max_sqm'])/2
        delta=(1-p['price']/p['surface']/mid)*100
        economics=round(max(0,min(40,20+delta*.8)),1)
        economic_label='Prezzo su benchmark omogeneo'
    elif p.get('evidence',{}).get('market_context',{}).get('status')=='available':
        from .omi import reference_scenarios
        if reference_scenarios(p).get('scenarios'):
            economics=10;economic_label='OMI disponibile; confronto condizionato'
    strategies=min(10,5*len(analysis.get('strategies',[])))
    factors=[{'label':'Dati documentati','points':quality,'max':30},
             {'label':'Annuncio pubblicato; disponibilità non confermata','points':availability,'max':20},
             {'label':economic_label,'points':economics,'max':40},
             {'label':'Strategie documentate','points':strategies,'max':10}]
    score=round(sum(x['points'] for x in factors))
    return {'score':score,'label':'Priorità di verifica','version':'triage/1.0','factors':factors,
            'reason':'Indice operativo a regole, non valutazione o probabilità di rendimento.'}
