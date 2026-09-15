import io
import csv
import pytest
from app.db import dump,now,uid
from app.schemas import Listing,ImportInput
from app.services.seed import seed,demo_records
from app.services.store import upsert_listing,property_dict
from app.services.imports import import_data
from app.services.exports import export_csv,export_xlsx
from app.security import csv_safe


def test_seed_idempotent(db,settings):
    seed(db,settings);seed(db,settings)
    assert db.one('SELECT COUNT(*) n FROM properties')['n']==36
    assert db.one('SELECT COUNT(*) n FROM benchmarks')['n']==120
    assert db.one('SELECT COUNT(*) n FROM agents')['n']==3


def test_upsert_history_and_human_decisions(db,settings):
    seed(db,settings)
    listing,html=demo_records('Milano')[0]
    pid,new,changed=upsert_listing(db,settings,'demo-milano',listing,raw=html)
    assert not new and not changed
    db.execute("UPDATE properties SET review_status='shortlisted',starred=1 WHERE id=?",(pid,))
    before=db.one('SELECT COUNT(*) n FROM observations WHERE property_id=?',(pid,))['n']
    revised=listing.model_copy(update={'price':listing.price-10000})
    same,new,changed=upsert_listing(db,settings,'demo-milano',revised,raw=html+'revised')
    assert same==pid and not new and changed
    assert db.one('SELECT COUNT(*) n FROM observations WHERE property_id=?',(pid,))['n']==before+1
    p=property_dict(db.one('SELECT * FROM properties WHERE id=?',(pid,)))
    assert p['review_status']=='shortlisted' and p['starred']
    assert db.one('SELECT COUNT(*) n FROM properties')['n']==36


def csv_text(rows):
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows);return out.getvalue()


def request(rows,is_demo=False):
    return ImportInput(kind='csv',content=csv_text(rows),permission_confirmed=True,is_demo=is_demo)


def row(**kwargs):
    return dict(listing_key='test1',url='https://catalog.example/p/1',title='Immobile test',city='Milano',price='850000',surface='500',currency='EUR',transaction_type='sale',description='Da ristrutturare.',**kwargs)


def test_import_explicit_label_and_dedupe(db,settings):
    out=import_data(db,settings,request([row()],True));assert out['new']==1
    out=import_data(db,settings,request([row()],True));assert out['new']==0
    assert db.one('SELECT is_demo FROM properties')['is_demo']==1
    assert db.one('SELECT score FROM properties')['score'] is None


def test_invalid_import_validates_before_write(db,settings):
    records=[row(),row()|{'listing_key':'bad','property_type':'invalid'}]
    # DictWriter needs the same columns in both rows.
    records[0]['property_type']='office'
    with pytest.raises(ValueError):import_data(db,settings,request(records))
    assert db.one('SELECT COUNT(*) n FROM properties')['n']==0


def test_import_permission_required(db,settings):
    with pytest.raises(ValueError):import_data(db,settings,ImportInput(kind='csv',content=csv_text([row()])))


def test_missing_import_price_remains_unknown(db,settings):
    import_data(db,settings,request([row()|{'price':'Prezzo su richiesta'}]))
    p=db.one('SELECT * FROM properties');assert p['price'] is None and p['score'] is None


def test_imported_unknown_fields_do_not_override_evidence(db,settings):
    data=row()|{'evidence':'injected','is_demo':'false','score':'99'}
    import_data(db,settings,request([data],True))
    p=property_dict(db.one('SELECT * FROM properties'))
    assert p['is_demo'] and p['score'] is None and isinstance(p['evidence'],dict)


def test_formula_injection_export_escaped(db,settings):
    import_data(db,settings,request([row()|{'title':'=HYPERLINK("https://evil.example")'}],True))
    p=property_dict(db.one('SELECT * FROM properties'))
    raw=export_csv([p]).decode('utf-8-sig')
    assert "'=HYPERLINK" in raw
    from openpyxl import load_workbook
    wb=load_workbook(io.BytesIO(export_xlsx([p])))
    assert wb.active['B3'].data_type=='s' and wb.active['B3'].value.startswith("'=")
    assert csv_safe(-4.5)=='-4.5'


def test_benchmark_import_replace_series(db,settings):
    from datetime import datetime
    b=dict(city='Milano',zone='Test',property_type='office',condition='good',area_basis='commercial',currency='EUR',transaction_type='sale',min_sqm='1000',max_sqm='2000',period=f'{datetime.now().year}-S1',source_label='Test sintetico',source_url='demo://benchmark')
    req=ImportInput(kind='benchmarks',content=csv_text([b]),permission_confirmed=True,is_demo=True)
    import_data(db,settings,req);import_data(db,settings,req)
    assert db.one('SELECT COUNT(*) n FROM benchmarks')['n']==1
