"""Contact preparation from stored evidence; no invented missing facts."""
from datetime import datetime,timedelta,timezone
from ..db import load
from .asset_evidence import AssetEvidence


def freshness(row,instant=None):
    instant=instant or datetime.now(timezone.utc)
    config=load(row.get('config'),{})
    hours=config.get('detail_refresh_hours',24)
    if isinstance(hours,bool) or not isinstance(hours,(int,float)) or not 1<=hours<=720:hours=24
    value=row.get('last_detail_at')
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
    except (TypeError,ValueError,AttributeError):parsed=None
    valid=parsed is not None and parsed<=instant
    stale=not valid or parsed<=instant-timedelta(hours=hours)
    return {'status':'stale' if stale else 'recent','checked_at':value if valid else None,
            'due_at':(parsed+timedelta(hours=hours)).isoformat() if valid else None,'hours':hours,
            'method':'Importazione' if row.get('kind')=='import' else 'Pagina acquisita',
            'label':'Da ricontrollare' if stale else 'Acquisizione recente'}


class DecisionSupport:
    def __init__(self,db,ids,assets=None):
        self.assets=assets or AssetEvidence(db);self.rows={}
        for offset in range(0,len(ids),400):
            batch=tuple(ids[offset:offset+400]);marks=','.join('?' for _ in batch)
            for row in db.all('''SELECT p.id,s.kind,s.config,c.last_detail_at FROM properties p
                JOIN sources s ON s.id=p.source_id LEFT JOIN listing_checks c ON c.property_id=p.id
                WHERE p.id IN ('''+marks+')',batch):self.rows[row['id']]=row

    def freshness(self,p):return freshness(self.rows.get(p['id'],{}))

    def summarize(self,p):
        age=self.freshness(p);decision=p.get('decision',{});cross=p.get('cross_sources',{})
        latest=self.assets.latest_contact(p['id']) if len(self.assets.members(p['id']))>1 else None
        related=latest if latest and latest['property_id']!=p['id'] else None
        questions=[]
        if age['status']=='stale' or cross.get('availability_conflict'):
            questions.append('L’immobile è ancora disponibile? Confermare prima di procedere.')
        last=(decision.get('calls') or [None])[0]
        if not last or last.get('mandate_status')!='confirmed_by_team':
            questions.append('Qual è il rapporto con la proprietà e chi ha il mandato?')
        if not decision.get('cadastral'):
            questions.append('Richiedere categoria catastale e documentazione aggiornata.')
        if any(x.get('strategy')=='conversion' for x in p.get('analysis',{}).get('strategies',[])):
            questions.append('Quali documenti supportano il cambio d’uso dichiarato?')
        if 'Prezzi richiesti diversi' in cross.get('conflicts',[]):
            questions.append('Qual è il prezzo aggiornato e perché differisce tra le fonti?')
        if not decision.get('published_at'):
            questions.append('Da quando è in vendita? Ci sono ribassi precedenti al nostro storico?')
        missing=[g['label'].lower() for g in p.get('market_references',{}).get('groups',[]) if g['median_sqm'] is None]
        if missing:questions.append('Integrare comparabili: '+', '.join(missing)+'.')
        if not p.get('benchmark'):questions.append('Manca un benchmark compatibile: verificare il vantaggio di prezzo.')
        return {'freshness':age,'related_contact':related,'questions':questions}
