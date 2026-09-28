import {e,num,amount,stamp} from './utils.js';
import {action} from './ui.js';
import {formatAmount,parseAmount} from './forms.js';

const money=value=>value==null?'—':`€ ${num(value,2)}`;

export const scenarioFields=[
  ['purchase','Prezzo di acquisto (€)',null,.01,1e9],['sale','Rivendita ipotizzata (€)','',.01,1e10],
  ['months','Durata (mesi)',12,1,120],['target_roi_pct','ROI obiettivo (%)',0,0,300],
  ['works','Lavori (€)',0,0,1e9],['acquisition_costs','Costi di acquisto e imposte (€)',0,0,1e9],
  ['contingency_pct','Imprevisti sui lavori (%)',10,0,100],['selling_pct','Costi di vendita (%)',3,0,99.99],
  ['holding_monthly','Gestione mensile (€)',0,0,1e7],
  ['stress_sale_pct','Stress: ribasso rivendita (%)',10,0,90],['stress_works_pct','Stress: rincaro lavori (%)',20,0,300],['stress_delay_months','Stress: ritardo (mesi)',6,0,120],
];
// Euro amounts are text fields formatted on blur (586.000), parsed with parseAmount; the rest stay numeric.
export const amountFields=new Set(['purchase','sale','works','acquisition_costs','holding_monthly']);
// Only the three facts of the operation are required; every other field ships with a default and a blank one
// falls back to it on submit (scenarioInputs), so clearing Lavori never blocks the calculation.
const missing={purchase:'Indica il prezzo di acquisto',sale:'Indica il prezzo di rivendita',months:'Indica la durata in mesi'};
export function savedScenarios(s,rows){
  return `<h3>Scenari salvati <span class="number-pill">${rows.length}</span></h3>${rows.length?rows.map(row=>`<div><span><strong>${e(row.name)}</strong><small>${e(row.author)} · ${stamp(row.created_at)}</small></span><span class="${row.result.profit<0?'danger-text':''}">${money(row.result.profit)}<small>Risultato operazione</small></span><div class="saved-scenario-actions">${action('load-scenario','Apri','','btn',`data-id="${e(row.id)}" aria-label="Apri scenario ${e(row.name)}"`)}${s.user.role!=='viewer'&&(s.user.role==='admin'||s.user.id===row.author_id)?action('delete-scenario','','close','icon-button',`data-id="${e(row.id)}" aria-label="Elimina scenario ${e(row.name)}"`):''}</div></div>`).join(''):'<p class="muted small">Nessuno scenario salvato.</p>'}`;
}
// Blank optional fields take their default; amounts are parsed from their grouped text.
export function scenarioInputs(read){
  const inputs={};
  for(const [key,,fallback] of scenarioFields){
    const raw=read(key).trim();
    inputs[key]=raw===''&&fallback!=null&&fallback!==''?fallback:amountFields.has(key)?parseAmount(raw):Number(raw);
  }
  return inputs;
}
// The dialog footer: Torna all’immobile on the left, Salva scenario and Calcola (primary) on the right.
export function scenarioForm(s,p,rows){
  const field=([key,title,value,min,max])=>{
    const initial=key==='purchase'?(p.currency==='EUR'?p.price??'':''):value;
    const input=amountFields.has(key)?`type="text" inputmode="decimal" autocomplete="off" data-amount data-min="${min}" data-max="${max}" value="${e(formatAmount(initial))}"`
      :`type="number" min="${min}" max="${max}" step="${['months','stress_delay_months'].includes(key)?1:.01}" value="${e(initial)}"`;
    return `<label for="scenario-${key}">${title}<input id="scenario-${key}" name="${key}" ${input}${missing[key]?` required data-missing="${missing[key]}"`:''}></label>`;
  };
  const group=(title,fields)=>`<fieldset class="scenario-group"><legend>${title}</legend><div class="form-grid">${fields.map(field).join('')}</div></fieldset>`;
  return `<div class="modal-body scenario-body"><div class="scenario-context"><span>${e(p.city)} · ${p.surface==null?'Superficie non indicata':num(p.surface)+' m²'}</span><strong>Prezzo richiesto ${amount(p.price,p.currency)}</strong></div><div class="scenario-layout"><form id="scenario-form" data-id="${e(p.id)}"><div class="scenario-name"><div class="scenario-name-head"><label for="scenario-name">Nome scenario</label><span id="scenario-state" class="scenario-state" role="status">Bozza</span></div><input id="scenario-name" name="name" value="Scenario base" maxlength="80" required data-missing="Dai un nome allo scenario"></div>${group('Operazione',scenarioFields.slice(0,4))}${group('Costi',scenarioFields.slice(4,9))}<details class="scenario-stress"><summary>Stress combinato <span>Modifica ipotesi</span></summary><p>Ribasso, rincaro e ritardo applicati insieme.</p><div class="form-grid">${scenarioFields.slice(9).map(field).join('')}</div></details><p class="scenario-assumptions">Valori in EUR, senza finanziamento. Includi nei costi le imposte applicabili.</p><div class="form-error" id="modal-error" role="alert"></div></form><section id="scenario-result" class="scenario-results" aria-live="polite">${scenarioPending('Compila le ipotesi e premi Calcola.')}</section></div><section class="saved-scenarios">${savedScenarios(s,rows)}</section></div><div class="modal-form-footer"><button type="button" class="btn footer-back" data-action="property" data-id="${e(p.id)}">Torna all’immobile</button><button type="submit" form="scenario-form" class="btn primary">Calcola</button>${s.user.role!=='viewer'?'<button type="submit" form="scenario-form" name="save" value="true" class="btn">Salva scenario</button>':''}</div>`;
}
// Until the first calculation the results panel is one quiet line, not an empty box.
export const scenarioPending=text=>`<div class="scenario-empty"><h3>Risultati</h3><p>${e(text)}</p></div>`;
export function scenarioResult(r){
  const metric=(title,value,negative=false)=>`<div><span>${title}</span><strong class="${negative?'danger-text':''}">${value}</strong></div>`;
  return `<div class="scenario-output"><h3 tabindex="-1">Risultati</h3><div class="scenario-kpis">${metric('Risultato operazione',money(r.profit),r.profit<0)}${metric('ROI semplice',num(r.roi_pct,2)+'%',r.roi_pct<0)}</div><div class="scenario-target"><span>Prezzo massimo per il tuo obiettivo</span><strong>${r.max_purchase>0?money(r.max_purchase):'Nessun prezzo positivo'}</strong><small>ROI obiettivo ${num(r.target_roi_pct,2)}% · ${r.max_purchase<=0?'Rivedi le ipotesi':r.target_met?'Raggiunto nel caso base':'Acquisto da rinegoziare'}</small></div><dl class="scenario-facts"><div><dt>Capitale impiegato</dt><dd>${money(r.invested)}</dd></div><div><dt>Rivendita di pareggio</dt><dd>${money(r.breakeven_sale)}</dd></div></dl>${r.stress?`<section class="scenario-stress-result"><h4>Con stress combinato</h4><dl class="scenario-facts"><div><dt>Risultato sotto stress</dt><dd class="${r.stress.profit<0?'danger-text':''}">${money(r.stress.profit)}</dd></div><div><dt>ROI semplice</dt><dd>${num(r.stress.roi_pct,2)}%</dd></div><div><dt>Acquisto massimo sotto stress</dt><dd>${r.stress.max_purchase>0?money(r.stress.max_purchase):'Nessun prezzo positivo'}</dd></div></dl><p>Rivendita −${num(r.inputs.stress_sale_pct,2)}%, lavori +${num(r.inputs.stress_works_pct,2)}%, ritardo ${num(r.inputs.stress_delay_months)} mesi.</p></section>`:''}<details class="scenario-method"><summary>Sensibilità e metodo</summary><p>ROI non annualizzato. Debito, flussi intermedi e imposte non inserite sono esclusi. Nessuna probabilità di successo stimata.</p><p>I costi di acquisto restano fissi: aggiornali se cambia il prezzo.</p><div class="table-scroll"><table><caption>Risultato al variare di rivendita e lavori</caption><thead><tr><th>Rivendita</th><th>Lavori base</th><th>Lavori +20%</th></tr></thead><tbody>${[-10,0,10].map(shift=>`<tr><th>${shift>0?'+':''}${shift}%</th>${[0,20].map(w=>{const value=r.sensitivity.find(x=>x.sale_change_pct===shift&&x.works_change_pct===w)?.profit;return `<td class="${value<0?'danger-text':''}">${money(value)}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div></details><p class="scenario-model-note">Ipotesi utente · ROI non annualizzato.</p></div>`;
}
