// Portal alert emails in Fonti, and the provenance of listings that came from a portal card
// (an alert email or a results page sent with Vedra Capture) in the list and in the sheet.
import {api} from './api.js';
import {action} from './ui.js';
import {icon} from './icons.js';
import {createRequestGuard} from './request-guard.js';
import {amount,e,num,relative,safeUrl} from './utils.js';
import {monogram} from './sources-ui.js';

const plural=(n,one,many)=>`${num(n)} ${n===1?one:many}`;
const day=value=>{
  const date=new Date(value);if(Number.isNaN(date.getTime()))return '';
  const same=date.getFullYear()===new Date().getFullYear();
  return date.toLocaleDateString('it-IT',same?{day:'numeric',month:'short'}:{day:'numeric',month:'short',year:'numeric'});
};

// "Da avviso immobiliare.it · 28 set": null when the listing did not come from a portal card.
export function portalOrigin(p){
  const card=p?.evidence?.portal_card;
  if(!card||typeof card!=='object'||!card.portal)return null;
  // A row read first from its detail page was only seen again in a card: say so, with the latest sighting.
  const also=card.from_card===false;
  const when=day(also?card.seen_at:(card.first_seen_at||card.seen_at));
  const results=card.origin==='results_page';
  const how=also?(results?'Visto anche nei risultati di':'Visto anche in un avviso'):(results?'Dai risultati di':'Da avviso');
  return {text:`${how} ${card.portal}${when?` · ${when}`:''}`,portal:card.portal,incomplete:Boolean(card.incomplete),
    url:safeUrl(card.source_url||p.url),oldPrice:typeof card.old_price==='number'?card.old_price:null,drop:Boolean(card.price_drop)};
}

export function originTag(p){
  const o=portalOrigin(p);
  if(!o||!o.incomplete)return '';
  return `<span class="portal-origin-tag">${e(o.text)} · da completare</span>`;
}

export function originNote(p){
  const o=portalOrigin(p);if(!o)return '';
  const drop=o.drop&&o.oldPrice!=null?` · ribasso dichiarato da ${amount(o.oldPrice,'EUR')}`:o.drop?' · ribasso dichiarato':'';
  const todo=o.incomplete?`<p>Da completare: apri l’annuncio e invia con Vedra Capture.${o.url?` <a class="text-link" href="${o.url}" target="_blank" rel="noopener noreferrer">Apri su ${e(o.portal)} ${icon('upRight')}</a>`:''}</p>`:'';
  return `<div class="portal-origin-note ${o.incomplete?'is-partial':''}"><span>${icon('mail')}${e(o.text)}${drop}</span>${todo}</div>`;
}

// One line per result, with only the counts that are not zero.
export function uploadSummary(r){
  const parts=[plural(r.files,'email','email')];
  if(r.cards)parts.push(plural(r.cards,'annuncio','annunci'));
  if(r.created)parts.push(plural(r.created,'nuovo','nuovi'));
  if(r.updated)parts.push(plural(r.updated,'aggiornato','aggiornati'));
  if(r.no_price)parts.push(`${num(r.no_price)} senza prezzo`);
  if(r.duplicates)parts.push(`${num(r.duplicates)} già ${r.duplicates===1?'letta':'lette'}`);
  if(r.ignored)parts.push(`${num(r.ignored)} non dai portali`);
  if(r.empty)parts.push(`${num(r.empty)} senza annunci`);
  return parts.join(' · ');
}

const STATUS={processed:'',empty:'Nessun annuncio riconosciuto',ignored:'Mittente non tra i portali',rejected:'Non letta'};
function recentRow(m){
  const counts=m.status==='processed'?[plural(m.cards,'annuncio','annunci'),m.created?plural(m.created,'nuovo','nuovi'):'',m.updated?plural(m.updated,'aggiornato','aggiornati'):''].filter(Boolean).join(' · ')
    :m.status==='rejected'&&m.note?m.note.replace(/[.:].*$/,''):STATUS[m.status]||'';
  const name=m.portal||m.sender_domain||'Email';
  return `<li class="alert-message ${m.status==='processed'?'':'is-muted'}">${monogram({name},'tiny')}<span class="alert-message-text"><strong>${e(m.subject||name)}</strong><small>${e(name)} · ${e(day(m.sent_at||m.processed_at))}</small></span><span class="alert-message-counts">${e(counts)}</span></li>`;
}

export function alertsSection(s){
  if(!s.user||s.user.role==='viewer')return '';
  const st=s.portalAlerts||{};const d=st.data;
  const imap=d?.imap||{},t=d?.totals||{};
  const buttons=action('alerts-pick',st.busy?'Lettura…':'Carica email','upload','btn',st.busy?'disabled aria-busy="true"':'')
    +(imap.configured?action('alerts-check','Controlla ora','refresh','btn',st.busy?'disabled':''):'')
    +'<input type="file" id="alerts-file" accept=".eml,message/rfc822" multiple hidden>';
  const identity=imap.configured
    ?`<div class="source-identity"><span class="monogram" aria-hidden="true">${icon('mail')}</span><div><h3>${e(imap.user)}</h3><span>${e(imap.host)} · ogni ${num(imap.poll_minutes)} min</span></div></div>`
    :`<div class="source-identity"><span class="monogram file" aria-hidden="true">${icon('mail')}</span><div><h3>Casella non collegata</h3><span>Carica le email degli avvisi salvate in formato .eml</span></div></div>`;
  const metrics=d?`<dl class="source-metrics">
      <div><dt>Email lette</dt><dd>${num(t.read||0)}</dd></div>
      <div><dt>Ignorate</dt><dd>${num((t.ignored||0)+(t.rejected||0))}</dd></div>
      <div><dt>Annunci nuovi</dt><dd>${num(t.created||0)}</dd></div>
      <div><dt>Aggiornati</dt><dd>${num(t.updated||0)}</dd></div>
      ${imap.configured?`<div><dt>Controllata</dt><dd>${d.checked_at?e(relative(d.checked_at)):'Mai'}</dd></div>`:''}
    </dl>`:'';
  const error=d?.error&&imap.configured?`<p class="source-note alert-error">${icon('warning')}${e(d.error)}</p>`:'';
  const loading=!d&&!st.error?'<p class="pg-note">Caricamento…</p>':'';
  const failed=st.error?`<p class="source-note alert-error">${icon('warning')}${e(st.error)} ${action('alerts-retry','Riprova','','btn')}</p>`:'';
  const result=st.result?`<p class="alert-result ${st.result.failed?'is-failed':''}" role="status">${icon(st.result.failed?'warning':'check')}${e(st.result.text)}</p>`:'';
  const recent=d?.recent?.length?`<ul class="alert-messages" aria-label="Ultime email">${d.recent.slice(0,5).map(recentRow).join('')}</ul>`:'';
  const address=imap.configured?`<strong>${e(imap.user)}</strong>`:'la casella dedicata del team';
  return `<section class="source-directory portal-alerts" aria-labelledby="portal-alerts-title"><div class="source-directory-heading alerts-heading"><div><h2 id="portal-alerts-title">Avvisi dei portali</h2><p>Le ricerche salvate su immobiliare.it, idealista e casa.it arrivano per email: Vedra aggiunge gli annunci.</p></div><div class="source-directory-actions">${buttons}</div></div>
    <div class="source-list"><article class="source-card source-row alerts-mailbox">${identity}${metrics}${error}${failed}${loading}</article>
    ${result}${recent}
    <details class="alerts-howto"><summary>Come collegare una ricerca</summary><ol>
      <li>Sul portale salva la ricerca e attiva gli avvisi via email.</li>
      <li>Come indirizzo usa ${address}${imap.configured?'':', oppure salva l’email come .eml e caricala qui'}.</li>
      <li>Gli annunci compaiono in Immobili con i dati dell’avviso. Per il resto apri l’annuncio e invialo con Vedra Capture.</li>
    </ol></details></div></section>`;
}

const toBase64=file=>new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onload=()=>resolve(String(reader.result).split(',',2)[1]||'');
  reader.onerror=()=>reject(new Error('File non leggibile.'));
  reader.readAsDataURL(file);
});

export function createPortalAlertsController({s,render,refresh=async()=>{},request=api,read=toBase64}){
  const guard=createRequestGuard();
  const state=()=>s.portalAlerts||(s.portalAlerts={data:null,error:'',busy:false,result:null});
  const visible=()=>s.page==='sources'&&s.user&&s.user.role!=='viewer';
  async function load(){
    if(!visible())return;
    guard.invalidate();const current=guard.capture(),user=s.user;
    try{
      const data=await request('/portal-alerts');
      if(!current()||s.user!==user)return;
      Object.assign(state(),{data,error:''});
    }catch(error){
      if(!current()||s.user!==user)return;
      state().error='Stato degli avvisi non disponibile.';
    }
    if(visible())render();
  }
  async function upload(files){
    const st=state();if(st.busy||!files.length)return;
    const total={files:0,cards:0,created:0,updated:0,no_price:0,duplicates:0,ignored:0,empty:0};const errors=[];
    st.busy=true;st.result=null;render();
    try{
      for(const file of files){
        try{
          if(file.size>(st.data?.max_mb||2)*1_000_000)throw new Error(`${file.name}: oltre ${st.data?.max_mb||2} MB.`);
          const r=await request('/portal-alerts/upload',{method:'POST',body:{name:file.name.slice(0,200),eml_base64:await read(file)}});
          total.files++;
          if(r.status==='duplicate')total.duplicates++;
          else if(r.status==='ignored')total.ignored++;
          else if(r.status==='empty')total.empty++;
          for(const key of ['cards','created','updated','no_price'])total[key]+=r[key]||0;
        }catch(error){errors.push(error.message);}
      }
    }finally{st.busy=false;}
    st.result={text:[total.files?uploadSummary(total):'',...errors].filter(Boolean).join(' · '),failed:errors.length>0};
    await load();
    if(total.created||total.updated)await refresh(true);
    render();
  }
  return {load,upload,cancel:()=>guard.invalidate(),reset(){guard.invalidate();s.portalAlerts=null;},actions:{
    'alerts-pick'(){document.getElementById('alerts-file')?.click();},
    'alerts-retry'(){return load();},
    async 'alerts-check'(){
      const st=state();if(st.busy)return;st.busy=true;st.result=null;render();
      try{
        const r=await request('/portal-alerts/check',{method:'POST'});
        // A mailbox error stays on the mailbox row (from the status); only a successful pass adds a result line.
        st.result=r.error?null:{text:r.read||r.ignored?uploadSummary({...r,files:r.read+r.ignored}):'Nessuna nuova email.',failed:false};
        if(r.created||r.updated)await refresh(true);
      }catch(error){st.result={text:error.message,failed:true};}
      finally{st.busy=false;}
      await load();render();
    },
  }};
}
