export const e = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const labels = {
  residential:'Residenziale', office:'Uffici', commercial:'Commerciale', logistics:'Logistica', land:'Terreni', hospitality:'Hospitality', unknown:'Non disponibile',
  new:'Nuovo', good:'Buono', to_renovate:'Da ristrutturare', shell:'Grezzo',
  value_add:'Value Add', core_plus:'Core Plus', development:'Development', conversion:'Conversion',
  sale:'Vendita', rent:'Locazione', net:'Netta', gross:'Lorda',
  completed:'Completata', failed:'Non riuscita', partial:'Parziale', interrupted:'Interrotta', cancelled:'Annullata', cancelling:'In annullamento', queued:'In coda', running:'In esecuzione',
  due_diligence:'Due diligence',negotiation:'Negoziazione',acquired:'Acquisito',degraded:'Da controllare',shortlisted:'In shortlist', reviewing:'In valutazione', discarded:'Scartata',
  title:'Titolo',price:'Prezzo',surface:'Superficie',description:'Descrizione',city:'Comune',zone:'Micro-zona',address:'Indirizzo',property_type:'Tipologia',condition:'Stato',area_basis:'Tipo superficie',
  currency:'Valuta',transaction_type:'Operazione',rooms:'Locali',bathrooms:'Bagni',latitude:'Latitudine',longitude:'Longitudine',is_auction:'Asta',healthy:'Disponibile', blocked:'Accesso bloccato', unverified:'Da verificare', html:'HTML / browser', import:'Importazione',
};
export const label = value => labels[value] || value || 'Non disponibile';
export const reviewLabel = value => value === 'new' ? 'Da valutare' : label(value);
export function num(value, decimals = 0) { return value == null ? '—' : new Intl.NumberFormat('it-IT', {maximumFractionDigits:decimals}).format(value); }
export function euro(value, compact = false) {
  if (value == null) return '—';
  if (compact && value >= 1e6) return `€ ${num(value/1e6,2)} M`;
  if (compact && value >= 1e3) return `€ ${num(value/1e3,0)}k`;
  return `€ ${num(value)}`;
}
export function amount(value, currency='XXX') {
  if (value == null) return '—';
  return currency === 'EUR' ? euro(value) : `${num(value)} ${currency === 'XXX' ? '(valuta n.d.)' : e(currency)}`;
}
export function stamp(value, full = false) {
  if (!value) return 'Mai eseguito';
  return new Date(value).toLocaleString('it-IT', full ? {day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'} : {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
}
export function relative(value) {
  if (!value) return 'In attesa';
  const seconds = (Date.now()-new Date(value))/1000;
  if (seconds < 0) return `tra ${Math.max(1,Math.ceil(-seconds/60))} min`;
  if (seconds < 60) return 'adesso';
  if (seconds < 3600) return `${Math.floor(seconds/60)} min fa`;
  if (seconds < 86400) return `${Math.floor(seconds/3600)} ore fa`;
  return stamp(value);
}
export const initials = name => String(name || 'V').split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase();
export const safeUrl = url => /^https?:\/\//i.test(url || '') ? e(url) : '';
export const activeRun = run => ['queued','running','cancelling'].includes(run?.status);
export const tone = status => ({completed:'success',healthy:'success',running:'success',queued:'neutral',partial:'warning',failed:'danger',blocked:'danger',interrupted:'warning',cancelled:'neutral',unverified:'warning'}[status] || 'neutral');
export function strategyTags(p, limit = 3) {
  return (p.analysis?.strategies || []).slice(0,limit).map(s=>`<span class="strategy ${e(s.strategy)}">${e(label(s.strategy))}</span>`).join('') || '<span class="muted small">Da qualificare</span>';
}
export function score(p) {
  const value=p.priority?.score??p.priority_score;
  return value==null?'<span class="score missing">—</span>':`<span class="score ${value>=75?'high':value>=45?'medium':'low'}" title="Priorità di verifica">${num(value)}</span>`;
}
export function discount(p) {
  if (p.discount == null) return '<span class="muted">—</span>';
  const difference = -p.discount;
  return `<span class="delta ${difference<=0?'positive':'negative'}">${difference>0?'+':''}${num(difference,1)}%</span>`;
}
export function selectOptions(items, selected = '') {
  return items.map(([value, text])=>`<option value="${e(value)}" ${String(value)===String(selected)?'selected':''}>${e(text)}</option>`).join('');
}

export function availabilityTag(p){const name={sold:"Venduto",rented:"Affittato",withdrawn:"Ritirato",review:"Da verificare",unknown:"Da verificare",listed:"Pubblicato"}[p.availability];return name?`<span class="availability-tag ${["sold","rented","withdrawn","review"].includes(p.availability)?"closed":""}">${e(name)}</span>`:"";}
