import io
import subprocess
import pytest
from PIL import Image
from app.schemas import Listing
from app.db import load,now
from app.services.availability import image_status,explicit_status,priority,AvailabilityChecker
from app.services.store import upsert_listing,property_dict
from app.services.analysis import screen
from app.services.catalog import search as query_catalog
from app.catalog_schemas import CatalogQuery


def test_status_negation_and_whole_words():
    assert explicit_status('TRILOCALE VENDUTO')[0]=='sold'
    assert explicit_status('non ancora venduto') is None
    assert explicit_status('venditore disponibile') is None
    assert explicit_status('sarà venduto arredato') is None


def test_ocr_confidence_and_evidence(monkeypatch):
    im=Image.new('RGB',(50,50),'white');body=io.BytesIO();im.save(body,format='PNG')
    header='level\tblock_num\tpar_num\tline_num\tconf\ttext\n'
    responses=iter([header+'5\t1\t1\t1\t70\tVENDUTO\n',header+'5\t1\t1\t1\t95\tVENDUTO\n'])
    def run(*args,**kwargs):return subprocess.CompletedProcess(args,0,next(responses).encode(),b'')
    monkeypatch.setattr(subprocess,'run',run)
    result=image_status(body.getvalue())
    assert result['status']=='sold' and result['confidence']==95 and result['rotation']==-32


def test_ocr_rejects_negation(monkeypatch):
    im=Image.new('RGB',(20,20),'white');body=io.BytesIO();im.save(body,format='PNG')
    tsv=b'level\tblock_num\tpar_num\tline_num\tconf\ttext\n5\t1\t1\t1\t95\tNON\n5\t1\t1\t1\t95\tVENDUTO\n'
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a,0,tsv,b''))
    assert image_status(body.getvalue()) is None


async def test_image_evidence_closes_listing(settings,monkeypatch):
    from app.services import availability
    p=Listing(listing_key='x',url='https://catalog.example/x',title='Test',images=['https://catalog.example/one.jpg'])
    async def get(self,url):return b'bytes','image/jpeg'
    monkeypatch.setattr(availability.ImageStore,'get',get)
    monkeypatch.setattr(availability.shutil,'which',lambda _:True)
    monkeypatch.setattr(availability,'image_status',lambda _:dict(status='sold',word='venduto',confidence=92,rotation=-32))
    await AvailabilityChecker(settings).enrich(p,True)
    assert p.availability=='sold' and p.evidence['availability']['sha256']
    assert p.evidence['availability']['source_url']==p.images[0]


def test_closed_survives_weak_recheck_and_excluded_from_catalog(db,settings):
    db.execute('INSERT INTO sources(id,name,kind,created_at) VALUES(?,?,?,?)',('s','Fixture','import',now()))
    p=Listing(listing_key='one',url='https://catalog.example/one',title='Test',price=500000,surface=80,city='Milano',transaction_type='sale',currency='EUR',availability='sold',evidence={'availability':{'value':'venduto'}})
    pid,_,_=upsert_listing(db,settings,'s',p)
    upsert_listing(db,settings,'s',p.model_copy(update={'availability':'listed','evidence':{}}))
    row=property_dict(db.one('SELECT * FROM properties WHERE id=?',(pid,)))
    assert row['availability']=='sold' and row['priority']['score']==0
    assert not screen(row,{'city':'Milano','criteria':{}})[0]
    assert query_catalog(db,CatalogQuery())['total']==0
    assert query_catalog(db,CatalogQuery(availability='sold'))['total']==1


def test_priority_operates_without_fabricated_economic_data():
    p=dict(title='Test',price=500000,surface=80,city='Milano',availability='listed')
    result=priority(p)
    assert 0<result['score']<50
    assert sum(x['points'] for x in result['factors'])==result['score']
    assert result['factors'][2]['points']==0
    assert priority(p|{'availability':'sold'})['score']==0
    assert priority(p|{'availability':'review'})['score']==0


def test_ribbon_geometry_ignores_red_objects():
    from app.services.status_ocr import ribbon_crop
    from PIL import ImageDraw
    im=Image.new('RGB',(900,600),'white');draw=ImageDraw.Draw(im)
    draw.rectangle((200,100,600,500),fill='red')
    assert ribbon_crop(im) is None


def test_diagonal_sale_ribbon_with_real_ocr():
    import shutil
    from PIL import ImageDraw,ImageFont
    if not shutil.which('tesseract'):pytest.skip('Tesseract required for raster integration test')
    ribbon=Image.new('RGB',(740,150),(205,45,45))
    ImageDraw.Draw(ribbon).text((370,75),'VENDUTO',font=ImageFont.load_default(size=95),fill='white',anchor='mm')
    image=ribbon.rotate(30,expand=True,fillcolor='white')
    body=io.BytesIO();image.save(body,format='PNG')
    result=image_status(body.getvalue())
    assert result and result['status']=='sold' and result['region']=='ribbon'
    assert result['confidence']>=85


def test_uncertain_sale_text_never_becomes_published(monkeypatch):
    im=Image.new('RGB',(20,20),'white');body=io.BytesIO();im.save(body,format='PNG')
    tsv=b'level\tblock_num\tpar_num\tline_num\tconf\ttext\n5\t1\t1\t1\t70\tVENDUTO\n'
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a,0,tsv,b''))
    assert image_status(body.getvalue())['status']=='review'


def test_unreadable_ribbon_requires_review(monkeypatch):
    from app.services import status_ocr
    im=Image.new('RGB',(20,20),'white');body=io.BytesIO();im.save(body,format='PNG')
    monkeypatch.setattr(status_ocr,'ribbon_crop',lambda _: (im,-30))
    tsv=b'level\tblock_num\tpar_num\tline_num\tconf\ttext\n'
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:subprocess.CompletedProcess(a,0,tsv,b''))
    assert image_status(body.getvalue())['status']=='review'
