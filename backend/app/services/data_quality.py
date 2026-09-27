"""One definition of missing data for archive counts, filters and exports."""
from .analysis import QUALITY_FIELDS


def missing_condition(field, prefix='p.'):
    if field not in QUALITY_FIELDS:
        raise ValueError('Campo di qualità non valido.')
    column=prefix+field
    if field in ('price','surface'):
        return f'{column} IS NULL'
    return f"({column} IS NULL OR {column}='' OR {column}='unknown')"


def report(db):
    expressions=[f'SUM(CASE WHEN {missing_condition(field)} THEN 1 ELSE 0 END) missing_{field}' for field in QUALITY_FIELDS]
    row=db.one('SELECT COUNT(*) total,SUM(CASE WHEN p.benchmark IS NULL THEN 1 ELSE 0 END) unbenchmarked,'+
               ','.join(expressions)+' FROM properties p WHERE p.is_demo=0')
    total=row['total']
    coverage=[{'field':field,'present':total-(row['missing_'+field] or 0),'missing':row['missing_'+field] or 0,'total':total,
               'percent':round((total-(row['missing_'+field] or 0))/total*100,1) if total else None} for field in QUALITY_FIELDS]
    return {'total':total,'unbenchmarked':row['unbenchmarked'] or 0,'coverage':coverage,
            'completeness':round(sum(c['present'] for c in coverage)/(total*len(coverage))*100,1) if total else None,
            'scope':'full-archive'}
