"""Paginated, source-preserving benchmark inventory; no valuation estimates."""
import math


def catalog(db,q='',condition='',currency='',page=1):
    clauses=['is_demo=0'];params=[]
    if q.strip():
        term='%'+q.strip().lower().replace('!','!!').replace('%','!%').replace('_','!_')+'%'
        clauses.append("(LOWER(city) LIKE ? ESCAPE '!' OR LOWER(zone) LIKE ? ESCAPE '!' OR LOWER(source_label) LIKE ? ESCAPE '!')")
        params.extend([term]*3)
    for key,value in [('condition',condition),('currency',currency)]:
        if value:clauses.append(key+'=?');params.append(value)
    where=' AND '.join(clauses)
    total=db.one('SELECT COUNT(*) n FROM benchmarks WHERE '+where,tuple(params))['n']
    pages=max(1,math.ceil(total/20));page=min(page,pages)
    rows=db.all('SELECT * FROM benchmarks WHERE '+where+' ORDER BY city,zone,period DESC,id LIMIT 20 OFFSET ?',tuple(params)+((page-1)*20,))
    return {'items':rows,'total':total,'page':page,'pages':pages,'page_size':20,'has_next':page<pages,
            'archive_total':db.one('SELECT COUNT(*) n FROM benchmarks WHERE is_demo=0')['n'],
            'currencies':[r['currency'] for r in db.all('SELECT DISTINCT currency FROM benchmarks WHERE is_demo=0 ORDER BY currency')],
            'conditions':[r['condition'] for r in db.all('SELECT DISTINCT condition FROM benchmarks WHERE is_demo=0 ORDER BY condition')]}
