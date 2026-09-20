"""Full-archive search shared by the explorer and exports, with bound SQL values."""
from datetime import datetime, timedelta, timezone

from ..catalog_schemas import CatalogQuery
from ..db import load, now
from ..product_schemas import ViewFilters
from .store import property_dict

SORTS = {
    'score': 'p.priority_score DESC,p.last_seen DESC,p.id',
    'price': "p.currency,(p.price IS NULL),p.price,p.id",
    'latest': 'p.last_seen DESC,p.id',
    'newest': 'p.first_seen DESC,p.id',
    'quality': 'p.completeness DESC,p.id',
    'due': '(w.due_date IS NULL),w.due_date,p.id',
}
FROM = ''' FROM properties p JOIN sources s ON s.id=p.source_id
           LEFT JOIN deal_work w ON w.property_id=p.id'''
SELECT = '''SELECT p.*,s.name source_name,COALESCE(w.version,0) work_version,
            w.owner_id,w.due_date'''


def where_clause(filters: ViewFilters, *, instant: datetime | None = None) -> tuple[str, tuple]:
    instant = instant or datetime.now(timezone.utc)
    clauses, values = ['p.is_demo=0'], []
    if filters.availability=='open':clauses.append("p.availability NOT IN ('sold','rented','withdrawn','review')")
    elif filters.availability!='all':
        clauses.append('p.availability=?');values.append(filters.availability)
    for key, column in (('city','p.city'), ('type','p.property_type'), ('status','p.review_status'),
                        ('source_id','p.source_id'), ('currency','p.currency')):
        value = getattr(filters, key)
        if value:
            clauses.append(f'lower({column})=lower(?)')
            values.append(value)
    if filters.q.strip():
        term = filters.q.strip().replace('!', '!!').replace('%', '!%').replace('_', '!_')
        clauses.append("(" + ' OR '.join(f"lower(COALESCE(p.{key},'')) LIKE lower(?) ESCAPE '!'"
                                         for key in ('title','city','zone','address','listing_key')) + ")")
        values.extend([f'%{term}%'] * 5)
    if filters.strategy:
        clauses.append('EXISTS(SELECT 1 FROM property_strategies ps WHERE ps.property_id=p.id AND ps.strategy=?)')
        values.append(filters.strategy)
    if filters.starred:
        clauses.append('p.starred=1')
    if filters.agent_id or filters.qualified:
        membership = ['ap.property_id=p.id']
        if filters.agent_id:
            membership.append('ap.agent_id=?')
            values.append(filters.agent_id)
        if filters.qualified:
            membership.append('ap.fit=1')
        clauses.append('EXISTS(SELECT 1 FROM agent_properties ap WHERE ' + ' AND '.join(membership) + ')')
    for name in ('price','surface'):
        for edge, sign in (('min','>='),('max','<=')):
            value = getattr(filters, f'{edge}_{name}')
            if value is not None:
                clauses.append(f'p.{name}{sign}?')
                values.append(value)
    cutoff = (instant - timedelta(days=7)).isoformat()
    if filters.focus == 'new':
        clauses.append('p.first_seen>=?'); values.append(cutoff)
    elif filters.focus == 'stale':
        clauses.append('p.last_seen<?'); values.append(cutoff)
    elif filters.focus == 'unbenchmarked':
        clauses.append('p.benchmark IS NULL')
    elif filters.focus == 'overdue':
        clauses.append("w.due_date<? AND p.review_status NOT IN ('acquired','discarded')")
        values.append(instant.date().isoformat())
    elif filters.focus == 'unassigned':
        clauses.append("w.owner_id IS NULL AND p.review_status NOT IN ('acquired','discarded')")
    return ' WHERE ' + ' AND '.join(clauses), tuple(values)


def attach_memberships(con, rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    # Batches also work on older SQLite builds with 999 variable limits.
    memberships = {}
    for start in range(0, len(rows), 400):
        ids = tuple(row['id'] for row in rows[start:start+400])
        marks = ','.join('?' for _ in ids)
        for item in con.execute('''SELECT ap.*,a.name FROM agent_properties ap JOIN agents a ON a.id=ap.agent_id
            WHERE ap.property_id IN (''' + marks + ')', ids).fetchall():
            memberships.setdefault(item['property_id'], []).append({
                'id':item['agent_id'], 'name':item['name'], 'fit':bool(item['fit']),
                'reasons':load(item['fit_reasons'], [])})
    result = []
    for row in rows:
        p = property_dict(dict(row))
        p['search_matches'] = memberships.get(p['id'], [])
        result.append(p)
    return result


def search(db, query: CatalogQuery) -> dict:
    where, args = where_clause(query)
    with db.transaction() as con:
        total = con.execute('SELECT COUNT(*) n' + FROM + where, args).fetchone()['n']
        pages = max(1, (total + query.page_size - 1) // query.page_size)
        page = min(query.page, pages)
        rows = con.execute(SELECT + FROM + where + ' ORDER BY ' + SORTS[query.sort] + ' LIMIT ? OFFSET ?',
                           args + (query.page_size, (page - 1) * query.page_size)).fetchall()
        items = attach_memberships(con, rows)
    return {'items':items, 'total':total, 'page':page, 'page_size':query.page_size, 'pages':pages,
            'has_next':page < pages, 'computed_at':now(), 'scope':'full-archive'}


def by_ids(db, ids: list[str]) -> list[dict]:
    result = []
    with db.transaction() as con:
        for start in range(0, len(ids), 400):
            batch = tuple(ids[start:start+400])
            if batch:
                rows = con.execute(SELECT + FROM + ' WHERE p.is_demo=0 AND p.id IN (' + ','.join('?' for _ in batch) + ')', batch).fetchall()
                result.extend(attach_memberships(con, rows))
    ordered = {row['id']:row for row in result}
    return [ordered[ident] for ident in ids if ident in ordered]


def export_rows(db, filters: ViewFilters, *, limit: int = 2000) -> list[dict]:
    where, args = where_clause(filters)
    with db.transaction() as con:
        rows = con.execute(SELECT + FROM + where + ' ORDER BY ' + SORTS[filters.sort] + ' LIMIT ?', args + (limit+1,)).fetchall()
        if len(rows) > limit:
            raise ValueError(f'La vista supera {limit} annunci. Restringi i filtri: nessuna esportazione viene troncata.')
        return attach_memberships(con, rows)


def facets(db) -> dict:
    # These are archive-wide values, not just the visible page.
    cities = db.all("SELECT min(city) city FROM properties WHERE is_demo=0 AND city!='' GROUP BY lower(city) ORDER BY min(city) LIMIT 1001")
    return {'cities':[r['city'] for r in cities[:1000]], 'cities_truncated':len(cities)>1000,
            'currencies':[r['currency'] for r in db.all("SELECT DISTINCT currency FROM properties WHERE is_demo=0 AND currency!='XXX' ORDER BY currency")],
            'total':db.one('SELECT COUNT(*) n FROM properties WHERE is_demo=0')['n']}
