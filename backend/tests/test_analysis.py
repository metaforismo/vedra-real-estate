from datetime import datetime,timezone
import pytest
from app.services.analysis import completeness,classify_rules,validate_semantic,match_benchmark,opportunity,screen,duplicate_candidates


def sample():
    return dict(id='a',source_id='s1',title='Ufficio da ristrutturare',description="Possibile cambio d’uso da verificare.",
      price=200000,surface=100,city='Milano',zone='Zona Test',address='Via Test 1',property_type='office',condition='to_renovate',area_basis='commercial',
      currency='EUR',transaction_type='sale',is_demo=False,is_auction=False)


def bench():
    p=sample();period=f"{datetime.now(timezone.utc).year}-S1"
    return {k:p[k] for k in ('city','zone','property_type','condition','area_basis','currency','transaction_type','is_demo')}|dict(min_sqm=2000,max_sqm=3000,period=period)


def test_complete_does_not_mean_accurate():
    p=sample();assert completeness(p)==(100,[])
    p['condition']='unknown';p['address']=None
    assert completeness(p)[0]==80


def test_rule_strategies_with_evidence():
    a=classify_rules(sample());assert a['engine']=='rules'
    assert {x['strategy'] for x in a['strategies']}=={'value_add','conversion'}
    assert any('urbanistica' in c for c in a['caveats'])


def test_negation_is_not_positive_signal():
    assert not classify_rules({'title':'Ufficio','description':"Non è possibile cambio d'uso."})['strategies']


def test_asset_type_alone_not_conversion():
    assert not classify_rules({'title':'Ufficio','description':'Ampio e luminoso.'})['strategies']


def test_semantic_exact_evidence():
    raw={'summary':'L’annuncio dichiara lavori necessari.','strategies':[{'strategy':'value_add','evidence':'da ristrutturare'}],'caveats':[]}
    a=validate_semantic(sample(),raw)
    assert a['engine']=='hermes' and a['strategies'][0]['evidence']=='da ristrutturare'
    raw['strategies'][0]['evidence']='rendimento garantito'
    with pytest.raises(ValueError):validate_semantic(sample(),raw)


def test_semantic_cannot_change_price_or_duplicate_strategy():
    with pytest.raises(ValueError):validate_semantic(sample(),{'summary':'Test','price':100})
    with pytest.raises(ValueError):validate_semantic(sample(),{'summary':'Test','strategies':[{'strategy':'value_add','evidence':'da ristrutturare'}]*2})


def test_benchmark_exact_keys_only():
    assert match_benchmark(sample(),[bench()])[0]
    for k,v in [('zone','Altra zona'),('property_type','residential'),('condition','good'),('area_basis','net'),('currency','USD'),('transaction_type','rent'),('is_demo',True)]:
        assert match_benchmark(sample(),[bench()|{k:v}])[0] is None


def test_benchmark_no_guess_with_unknown_basis():
    assert match_benchmark(sample()|{'area_basis':'unknown'},[bench()])[0] is None


def test_stale_and_future_benchmark():
    y=datetime.now(timezone.utc).year
    assert match_benchmark(sample(),[bench()|{'period':f'{y-4}-S1'}])[0] is None
    assert match_benchmark(sample(),[bench()|{'period':f'{y+1}-S1'}])[0] is None


def test_score_formula_and_null():
    p=sample();b=bench();a=classify_rules(p)
    score,discount,details=opportunity(p,b,a)
    assert (score,discount)==(93,20)
    assert sum(x['points'] for x in details)==93
    assert opportunity(p,None,a)==(None,None,[])
    assert opportunity(p|{'price':None},b,a)==(None,None,[])

@pytest.mark.parametrize('price,score',[(10000,100),(900000,30)])
def test_score_bounded(price,score):
    assert opportunity(sample()|{'price':price},bench(),classify_rules(sample()))[0]==score


def test_filters_and_unknown_discount():
    p=sample()|{'analysis':classify_rules(sample()),'discount':None}
    a={'city':'Milano','criteria':{'max_price':300000,'min_surface':80}}
    assert screen(p,a)==(True,[])
    a['criteria']['min_discount']=20
    assert not screen(p,a)[0] and 'Confronto' in screen(p,a)[1][0]
    assert not screen(p|{'transaction_type':'rent'},a)[0]


def test_possible_duplicate_not_auto_merge():
    p=sample();q=p|{'id':'b','source_id':'s2','surface':102,'price':210000}
    suggestions=duplicate_candidates([p,q]);assert len(suggestions)==1 and 'non uniti' in suggestions[0]['reason']
    assert not duplicate_candidates([p,q|{'is_demo':True}])
    assert not duplicate_candidates([p,q|{'address':None}])


@pytest.mark.parametrize('price,qualified', [(499999,False),(500000,True),(550000,True),(600000,True),(600001,False),(None,False)])
def test_budget_interval_inclusive(price, qualified):
    agent={'city':'Milano','criteria':{'min_price':500000,'max_price':600000}}
    assert screen(sample()|{'price':price},agent)[0] is qualified


def test_budget_interval_rejects_inversion_and_preserves_legacy():
    from app.schemas import Criteria
    with pytest.raises(ValueError):
        Criteria(min_price=600000,max_price=500000)
    assert Criteria(max_price=600000).min_price == 0


@pytest.mark.parametrize('query,field,text,qualified',[
    ('Argonne','zone','Argonne-Corsica',True),
    ('viale Corsica','address','Viale Corsica 41',True),
    ('porta romana','title','Bilocale PORTA ROMANA, Milano',True),
    ('Como','address','Via Comolli',False),
    ('Duomo','description','A dieci minuti dal Duomo',False),
    ('Duomo','zone','',False),
    ('[Duomo]','zone','Duomo',True),
])
def test_location_requires_literal_source_location(query,field,text,qualified):
    agent={'city':'Milano','criteria':{'location_query':query}}
    p=sample()|{field:text}
    assert screen(p,agent)[0] is qualified


def test_location_validation():
    from app.schemas import Criteria
    assert Criteria(location_query='  Porta   Romana  ').location_query=='Porta Romana'
    with pytest.raises(ValueError):Criteria(location_query='x'*101)
