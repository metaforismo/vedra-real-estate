"""Cross-source dossiers from team-confirmed links, never from a guessed identity."""
from collections import defaultdict
from ..db import load
from .decision_facts import text_facts


class AssetEvidence:
    def __init__(self,db):
        self.db=db;self.parents={};self.cache={}
        reviews=db.all('SELECT a,b,decision FROM duplicate_reviews')
        for pair in reviews:
            if pair['decision']=='same_asset':self.parents[self.root(pair['b'])]=self.root(pair['a'])
        self.groups=defaultdict(set)
        for ident in self.parents:
            self.groups[self.root(ident)].add(ident)
            self.groups[self.root(ident)].add(self.root(ident))
        self.contradictions={self.root(p['a']) for p in reviews if p['decision']=='distinct' and self.root(p['a'])==self.root(p['b'])}

    def root(self,ident):
        while self.parents.get(ident,ident)!=ident:ident=self.parents[ident]
        return ident

    def members(self,ident):return sorted(self.groups.get(self.root(ident),{ident}))

    def _result(self,root,ids,rows):
        entries=[]
        for row in rows:
            facts=load(row['evidence'],{}).get('decision_facts',{})
            declarations=text_facts(row['title'],row['description'])
            entries.append({k:row[k] for k in ('id','title','url','price','currency','surface','area_basis','transaction_type','availability','condition','last_seen','source','source_id','domain')}|
                           {'contact':facts.get('contact') or {},'mandate':(facts.get('mandate') or declarations.get('mandate') or {}).get('quote','')})
        conflicts=[]
        fields=[('price','Prezzi richiesti diversi',('currency','transaction_type')),('surface','Superfici diverse',('area_basis',)),('availability','Disponibilità discordante',()),('condition','Stati manutentivi diversi',())]
        for key,label,context in fields:
            buckets=defaultdict(set)
            for row in entries:
                value=row[key];scope=tuple(row[k] for k in context)
                if value in (None,'unknown','XXX','review') or any(x in (None,'unknown','XXX') for x in scope):continue
                buckets[scope].add(value)
            if any(len(values)>1 for values in buckets.values()):conflicts.append(label)
        if len(ids)>100:conflicts.append('Gruppo ampio: confronto parziale')
        if root in self.contradictions:conflicts.insert(0,'Collegamenti tra annunci da rivedere')
        result={'entries':entries,'count':len(ids),'limited':len(ids)>100,'conflicts':conflicts,
                'identity_conflict':root in self.contradictions,
                'availability_conflict':'Disponibilità discordante' in conflicts}
        self.cache[root]=result
        return result

    def preload(self,identifiers):
        roots={self.root(ident) for ident in identifiers}
        roots={root for root in roots if root not in self.cache}
        wanted=sorted({ident for root in roots for ident in self.members(root)[:100]})
        rows=[]
        for offset in range(0,len(wanted),400):
            batch=tuple(wanted[offset:offset+400]);marks=','.join('?' for _ in batch)
            rows.extend(self.db.all('''SELECT p.id,p.title,p.url,p.price,p.currency,p.surface,p.area_basis,p.transaction_type,
                p.availability,p.condition,p.last_seen,p.evidence,p.description,s.name source,s.domain,s.id source_id
                FROM properties p JOIN sources s ON s.id=p.source_id WHERE p.is_demo=0 AND p.id IN ('''+marks+') ORDER BY p.last_seen DESC,p.id',batch))
        for root in roots:self._result(root,self.members(root),[row for row in rows if self.root(row['id'])==root])

    def for_property(self,p):
        root=self.root(p['id'])
        if root not in self.cache:self.preload([p['id']])
        return self.cache[root]

    def latest_contact(self,ident):
        latest=None;ids=self.members(ident)
        for start in range(0,len(ids),400):
            batch=tuple(ids[start:start+400]);marks=','.join('?' for _ in batch)
            row=self.db.one('''SELECT c.*,u.name author FROM contact_actions c JOIN users u ON u.id=c.user_id
                WHERE c.property_id IN ('''+marks+') ORDER BY c.created_at DESC,c.id DESC LIMIT 1',batch)
            if row and (latest is None or (row['created_at'],row['id'])>(latest['created_at'],latest['id'])):latest=row
        return latest
