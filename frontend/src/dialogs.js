import {comparisonContent} from './comparison-ui.js';
import {historyPreview} from './history-ui.js';
import {runContent} from './run-ui.js';
import {decisionSection} from './decision-ui.js';
import {priceLadder,signalFacts,marketPosition} from './signals-ui.js';
import {marketContext} from './market-ui.js';
import {propertyTools,stages} from './product-ui.js';
import {icon} from './icons.js';
import {e,label,reviewLabel,num,euro, amount,stamp,safeUrl,discount,selectOptions,engineName} from './utils.js';
import {notice,badge} from './ui.js';
import {monogram} from './sources-ui.js';
import {originNote} from './portal-alerts-ui.js';
const closeButton = '<button type="button" class="icon-button modal-close" data-action="close-modal" aria-label="Chiudi finestra">'+icon('close')+'</button>';
export function modalFrame(title, subtitle, body, cls='') {
  return `<dialog class="modal ${cls}" aria-labelledby="modal-title"><div class="modal-header"><div><h2 id="modal-title">${e(title)}</h2>${subtitle?`<p>${e(subtitle)}</p>`:''}</div>${closeButton}</div>${body}</dialog>`;
}
const formError = '<div class="form-error" id="modal-error" role="alert"></div>';
// Modal contract: Annulla + one primary, no icon on the primary.
export const footer = (text) => `<div class="modal-form-footer"><button type="button" class="btn" data-action="close-modal">Annulla</button><button type="submit" class="btn primary">${text}</button></div>`;
const types = ['residential','office','commercial','logistics','land','hospitality'];
const strategies = ['value_add','core_plus','development','conversion'];

export function agentDialog(s, agent, copy=false) {
  const a=agent || {name:'',city:'Milano',criteria:{opportunity_only:true,contact_policy:'prefer_direct',max_price:1500000,min_surface:100,max_listings:30,property_types:[],strategies:[],include_auctions:true},source_ids:[],runtime:s.data.runtime.ai_configured?'scout':'local',interval_minutes:360,active:true};
  const c=a.criteria,sources=s.data.sources,readOnly=s.user.role==='viewer';
  const web=sources.filter(src=>src.kind==='html'),files=sources.filter(src=>src.kind!=='html');
  const advancedCount=(c.max_surface!=null?1:0)+(c.include_auctions?1:0);
  const startPages=Object.values(c.source_urls||{}).filter(Boolean).length;
  // A copy reuses every criterion but saves as a new search: no id, no revision.
  const id=copy?'':agent?.id||'';
  const chips=(name,values,selected)=>`<div class="choice-chips">${values.map(x=>`<label class="choice-chip"><input type="checkbox" name="${name}" value="${x}" ${selected.includes(x)?'checked':''}><span>${label(x)}</span></label>`).join('')}</div>`;
  const sourceCard=src=>`<label class="source-choice"><input type="checkbox" name="source_ids" value="${e(src.id)}" ${a.source_ids.includes(src.id)?'checked':''} ${!src.enabled?'disabled':''}>${monogram(src)}<span class="source-choice-text"><strong>${e(src.name)}</strong><small>${e(src.kind==='html'?src.domain:`${num(src.property_count)} immobili`)}${!src.enabled?' · in pausa':''}</small></span><span class="source-choice-check" aria-hidden="true">${icon('check')}</span></label>`;
  const section=(key,title,hint,body)=>`<section class="research-section" aria-labelledby="${key}-heading"><header class="research-section-head"><h3 id="${key}-heading">${title}</h3>${hint?`<p>${hint}</p>`:''}</header><div class="research-section-body">${body}</div></section>`;
  const runtimes=[...((s.data.runtime.ai_configured||a.runtime==='scout')?[['scout',engineName('scout')]]:[]),['local',engineName('local')],...((s.data.runtime.ai_configured||a.runtime==='llm')?[['llm',engineName('llm')]]:[]),...((s.data.runtime.hermes_configured||a.runtime==='hermes')?[['hermes','Hermes (legacy)']]:[])];
  return modalFrame(copy?'Crea una variante':agent?'Configura ricerca':'Nuova ricerca',copy?'Stessi criteri della ricerca originale: cambia ciò che serve e salva.':'',`<form id="agent-form" data-id="${e(id)}" data-revision="${e(copy?'':agent?.revision||'')}" class="modal-form research-form"><nav class="research-steps" aria-label="Sezioni della ricerca">${[['asset','Cosa cercare'],['research','Dove e come'],['criteria','Requisiti'],['schedule','Frequenza']].map(([key,text],i)=>`<button type="button" data-research-jump="${key}" ${i?'':'aria-current="true"'}>${text}</button>`).join('')}</nav><fieldset ${readOnly?'disabled':''}>
    ${section('asset','Cosa cercare','',`
      <div class="form-grid"><label>Nome<input name="name" value="${e(a.name)}" placeholder="Milano · Value Add uffici" required minlength="2" maxlength="100" data-missing="Inserisci un nome"></label><label>Comune<input name="city" value="${e(a.city)}" placeholder="Milano" required minlength="2" maxlength="100" data-missing="Indica il comune"></label>
      <label class="span-2"><span class="field-caption">Zona o indirizzo <span class="optional-label">facoltativo</span></span><input name="location_query" value="${e(c.location_query||'')}" maxlength="100" placeholder="Porta Romana, oppure viale Corsica"><small>Cercata nella zona, nell’indirizzo e nel titolo dell’annuncio.</small></label></div>
      <div class="form-grid research-numbers"><label>Budget minimo (€)<input name="min_price" type="text" inputmode="numeric" autocomplete="off" data-amount data-min="0" data-max="1000000000" value="${num(c.min_price??0)}" required data-missing="Indica il budget minimo, anche 0"></label><label>Budget massimo (€)<input name="max_price" type="text" inputmode="numeric" autocomplete="off" data-amount data-min="1" data-max="1000000000" data-not-below="min_price" data-not-below-message="Inferiore al budget minimo" value="${c.max_price==null?'':num(c.max_price)}" required data-missing="Indica il budget massimo"></label>
      <label>Superficie minima (m²)<input name="min_surface" type="number" inputmode="numeric" min="0" step="any" value="${c.min_surface}" required data-missing="Indica la superficie minima, anche 0"></label><label>Sconto minimo (%)<input name="min_discount" type="number" inputmode="decimal" min="0" max="100" step="any" value="${c.min_discount??''}" placeholder="Nessuno" aria-describedby="discount-hint"></label>
      <small class="span-2 field-note" id="discount-hint">Lo sconto è calcolato sul prezzo di zona.</small></div>
      <div class="field-group"><span class="field-label">Tipologie <span class="optional-label">(vuoto: tutte)</span></span>${chips('property_types',types,c.property_types)}</div>
      <div class="field-group"><span class="field-label">Strategie <span class="optional-label">riconosciute dal testo dell’annuncio</span></span>${chips('strategies',strategies,c.strategies)}</div>`)}
    ${section('research','Dove e come cercare','Scout apre i siti scelti come farebbe una persona e segue le tue istruzioni.',`
      <div class="field-group" id="research-sources"><span class="field-label">Fonti</span>${sources.length?`${web.length?`<div class="source-choices">${web.map(sourceCard).join('')}</div>`:''}${files.length?`${web.length?'<span class="source-choices-label">Archivio importato</span>':''}<div class="source-choices">${files.map(sourceCard).join('')}</div>`:''}`:'<p class="muted">Nessuna fonte. <a href="#sources">Collega una fonte</a>.</p>'}</div>
      <label>Motore<select name="runtime">${selectOptions(runtimes,a.runtime)}</select></label>
      <label class="research-instructions">Istruzioni di ricerca<textarea aria-label="Istruzioni di ricerca" name="research_instructions" rows="5" maxlength="6000" placeholder="Es.: apri solo le sezioni uffici e negozi.&#10;Salta affitti, aste e nuove costruzioni.&#10;Annota sempre il nome del broker e se ha il mandato.">${e(c.research_instructions||'')}</textarea><small>Dove cercare, cosa aprire, cosa saltare. <span class="scout-only-note">Valgono solo con il motore Scout.</span></small></label>
      ${web.length?`<details class="research-settings" ${startPages?'open':''}><summary>Pagine di partenza<span class="setting-indicator" data-instruction-indicator ${startPages?'':'hidden'}>Configurate</span></summary><div class="disclosure-body"><p class="field-note">Facoltative. Un indirizzo del sito da cui Scout inizia, per esempio una ricerca già filtrata.</p>${web.map(src=>`<label>${e(src.name)}<input name="source_url_${e(src.id)}" type="url" maxlength="2000" value="${e(c.source_urls?.[src.id]||'')}" placeholder="${e(src.config.search_url||`https://${src.domain}/`)}"></label>`).join('')}</div></details>`:'<span data-instruction-indicator hidden></span>'}`)}
    ${section('criteria','Requisiti','Un annuncio entra solo se il suo testo li dimostra.',`
      <label>Criteri personalizzati<textarea aria-label="Criteri personalizzati" name="custom_prompt" maxlength="6000" rows="4" placeholder="Un requisito per riga, es.:&#10;Cambio d’uso indicato nell’annuncio&#10;Immobile libero al rogito">${e(c.custom_prompt||'')}</textarea><small>Ogni requisito viene verificato con una citazione dell’annuncio.</small></label>
      <div class="research-pair"><label class="check-line"><input type="checkbox" name="opportunity_only" ${c.opportunity_only?'checked':''}><span>Solo sotto il prezzo di zona<small>Esclude prezzi in linea e annunci senza confronto.</small></span></label>
      <label>Contatto cercato<select name="contact_policy" aria-label="Contatto cercato">${selectOptions([['prefer_direct','Precedenza al contatto diretto'],['require_direct','Solo diretto, con recapito'],['any','Qualsiasi inserzionista']],c.contact_policy||'any')}</select><small>Proprietario o mandato esclusivo dichiarati, da confermare.</small></label></div>
      <details class="research-advanced"><summary>Superficie massima e aste<span class="setting-indicator" data-filter-indicator ${advancedCount?'':'hidden'}>${advancedCount} ${advancedCount===1?'selezionato':'selezionati'}</span></summary><div class="disclosure-body">
      <label>Superficie massima (opzionale)<input name="max_surface" type="number" min="1" step="any" value="${c.max_surface??''}" placeholder="Nessun massimo"></label><label class="check-line"><input type="checkbox" name="include_auctions" ${c.include_auctions?'checked':''}> Includi aste</label>
      </div></details>`)}
    ${section('schedule','Frequenza','',`
      <div class="form-grid"><label>Esegui<select name="interval_minutes">${selectOptions([[0,'Solo avvio manuale'],[15,'Ogni 15 minuti'],[30,'Ogni 30 minuti'],[60,'Ogni ora'],[360,'Ogni 6 ore'],[1440,'Ogni giorno'],[10080,'Ogni settimana']],a.interval_minutes)}</select></label><label>${c.online_discovery?'Nuovi annunci':'Annunci'} per fonte<input name="max_listings" type="number" min="1" max="100" value="${c.max_listings}" required></label></div>
      <div class="checkbox-row"><label class="check-line"><input type="checkbox" name="active" ${a.active?'checked':''}> Ricerca attiva</label><label class="check-line" data-hermes-only ${a.runtime==='hermes'?'':'hidden'}><input type="checkbox" name="online_discovery" ${c.online_discovery?'checked':''}> Ricerca online con Hermes</label></div>
      <details class="research-help"><summary>Come viene eseguita</summary><p>Scout apre le fonti web come una persona: sceglie annunci e sezioni seguendo le tue istruzioni e legge ogni scheda. I valori non scritti nella pagina restano vuoti. I siti che bloccano l’accesso automatico vengono segnalati, non aggirati. Gli altri motori rianalizzano l’archivio. La frequenza vale anche a browser chiuso.</p></details>`)}
    ${formError}<div class="research-save-conflict" hidden><button type="button" class="btn primary" data-action="reload-research">Rileggi ricerca</button></div>${readOnly?'':footer('Salva ricerca')}</fieldset></form>`,'medium-modal research-modal');
}

export function sourceDialog(source,presets=[]) {
  const s=source||{name:'',domain:'',permission_note:'',config:{search_url:'',listing_selector:'a.property-link',listing_url_pattern:'/immobili/',next_selector:'a[rel="next"]',max_pages:2,render_js:false,fields:{price:'.price',surface:'.surface',city:'.city',zone:'.zone',property_type:'.asset-type',condition:'.condition',area_basis:'.area-basis',transaction_type:'.transaction'}}};
  // Presets are cards (native radios) grouped by what Scout can do with them; the hidden select keeps the app's single fill-in path.
  const groups=[['agency','Reti di agenzie','Scout naviga il sito e legge gli immobili con mandato.'],['portal','Portali','Spesso bloccano l’accesso automatico: verifica prima di usarli.']];
  const card=(p,i)=>`<label class="preset-card"><input type="radio" name="source_preset_choice" value="${i}" aria-label="${e(p.name)}" aria-describedby="preset-domain-${i}">${monogram(p)}<span><strong>${e(p.name)}</strong><small id="preset-domain-${i}">${e(p.domain)}</small></span></label>`;
  const presetPicker=!source&&presets.length?`<fieldset class="preset-picker"><legend>Scegli la fonte</legend>
    ${groups.map(([g,title,hint])=>presets.some(p=>p.group===g)?`<div class="preset-group" data-group="${g}"><p class="preset-group-title"><strong>${title}</strong><span>${hint}</span></p><div class="preset-grid">${presets.map((p,i)=>p.group===g?card(p,i):'').join('')}</div></div>`:'').join('')}
    <div class="preset-grid preset-other">${presets.map((p,i)=>!p.group?card(p,i):'').join('')}<label class="preset-card"><input type="radio" name="source_preset_choice" value="" checked><span class="monogram" aria-hidden="true">${icon('plus')}</span><span><strong>Altro sito</strong><small>Configurazione manuale</small></span></label></div>
    <select id="source-preset" aria-label="Portale" hidden tabindex="-1"><option value="">Personalizzata</option>${presets.map((p,i)=>`<option value="${i}">${e(p.name)}</option>`).join('')}</select>
  </fieldset>`:'';
  return modalFrame(source?'Configura fonte':'Collega fonte','',`<form id="source-form" data-id="${e(source?.id||'')}" class="modal-form source-form">
    ${presetPicker}
    <div class="source-form-block"><div class="form-grid"><label>Nome fonte<input name="name" required minlength="2" maxlength="100" value="${e(s.name)}" placeholder="Catalogo agenzia" data-missing="Inserisci un nome"></label><label>Dominio<input name="domain" required value="${e(s.domain)}" placeholder="www.agenzia.it" data-missing="Indica il dominio"></label><label class="span-2">URL della ricerca<input name="search_url" required value="${e(s.config.search_url)}" placeholder="https://www.agenzia.it/vendita/" data-missing="Incolla l’indirizzo della ricerca"><small>La pagina da cui partire. Per un altro comune incolla la ricerca del sito.</small></label></div>
    <label class="check-line"><input type="checkbox" name="browser_navigation" ${s.config.browser_navigation?'checked':''}><span>Apri le pagine in un browser<small>Legge le pagine pubbliche come un visitatore. Necessario per i siti che caricano gli annunci con JavaScript; le reti di agenzie lo usano sempre.</small></span></label></div>
    <details class="source-advanced"><summary>Impostazioni di acquisizione</summary><div class="disclosure-body"><div class="form-grid">
    <label>Comune per il test<input name="probe_city" maxlength="120" value="${e(s.config.probe_city||'')}" placeholder="Se l’URL contiene {city}"></label><label>Rileggi dettagli dopo (ore)<input name="detail_refresh_hours" type="number" min="1" max="720" value="${s.config.detail_refresh_hours||24}"></label><label>Massimo pagine<input name="max_pages" type="number" min="1" max="5" value="${s.config.max_pages}" required></label><label>Scoperta URL<select name="discovery_mode">${selectOptions([["links","Link HTML"],["sitemap","Sitemap XML"]],s.config.discovery_mode||"links")}</select></label>
    <label>Selettore annunci<input name="listing_selector" required value="${e(s.config.listing_selector)}"></label><label>Filtro percorso<input name="listing_url_pattern" value="${e(s.config.listing_url_pattern)}"></label><label class="span-2">Selettore pagina successiva<input name="next_selector" value="${e(s.config.next_selector)}"></label></div>
    <label>Selettori dei campi · JSON<textarea name="fields" class="code-input" rows="5" spellcheck="false">${e(JSON.stringify(s.config.fields,null,2))}</textarea></label>
    <label class="check-line"><input type="checkbox" name="render_js" ${s.config.render_js?'checked':''}> Rendering JavaScript</label><label class="check-line"><input type="checkbox" name="retain_images" ${s.config.retain_images?'checked':''}> Conserva riferimenti alle foto</label><label class="check-line"><input type="checkbox" name="facts_only" ${s.config.retain_raw_html===false?'checked':''}> Conserva solo i dati estratti</label><p class="field-note">Il dominio deve essere abilitato sul server. <code>{city}</code> usa il comune della ricerca in minuscolo.</p></div></details>
    <div class="permission-block"><div class="permission-head">${icon('lock')}<div><strong>Autorizzazione</strong><span>Vedra accede solo a siti per cui il team ha il permesso di acquisizione e riuso.</span></div></div>
    <label>Permesso di accesso e riuso<textarea name="permission_note" rows="2" required minlength="10" maxlength="2000" data-missing="Descrivi il permesso di accesso e riuso" placeholder="Es.: accordo con la rete del 12/09/2026, solo annunci di vendita, uso interno.">${e(s.permission_note)}</textarea></label><label class="check-line"><input type="checkbox" name="permission_confirmed" required data-missing="Conferma l’autorizzazione per salvare" ${source?'checked':''}> Confermo l’autorizzazione all’accesso automatizzato e al riuso.</label></div>
    ${formError}${footer(source?'Salva fonte':'Collega fonte')}</form>`,'medium-modal source-modal');
}

export function sourceProbeDialog(result) {
  const sample=result.sample;
  const raw=result.notice||'Verifica non riuscita.';
  // Each known failure gets a plain reason and the next useful step; the raw result stays one click away.
  const [reason,next]=/HTTP 403/.test(raw)?['Il sito rifiuta l’accesso dal server (HTTP 403).','Molti portali bloccano l’accesso automatico. Usa una rete di agenzie oppure importa i dati.']
    :/BROWSER_ENABLED/.test(raw)?['Il browser del server non è attivo.','Chiedi all’amministratore di attivarlo, poi ripeti la verifica.']
    :/allowlist/.test(raw)?['Il dominio non è abilitato sul server.','Chiedi all’amministratore di aggiungerlo ai domini consentiti.']
    :/Challenge/i.test(raw)?['Il sito richiede una verifica anti-bot.','Vedra non aggira questi controlli. Scegli un’altra fonte o importa i dati.']
    :[raw,''];
  const missing=result.missing_fields||[];
  return modalFrame(result.ok?'Accesso verificato':'Accesso non riuscito','',`<div class="modal-body probe-result">
    ${result.ok?`<div class="probe-stats"><div><strong>${num(result.links_found)}</strong><span>Annunci trovati</span></div><div><strong>${sample?'Sì':'No'}</strong><span>Annuncio letto in prova</span></div></div>
    ${sample?`<div class="probe-sample"><span class="probe-label">Annuncio di prova</span><strong>${e(sample.title||'Titolo mancante')}</strong><p>${[sample.price!=null?amount(sample.price,sample.currency):'Prezzo mancante',sample.surface!=null?`${num(sample.surface)} m²`:'',sample.city||'Comune mancante'].filter(Boolean).map(e).join(' · ')}</p></div>`:''}
    ${missing.length?`<div class="probe-missing"><span class="probe-label">Campi non trovati</span><div>${missing.map(x=>`<span>${e(label(x))}</span>`).join('')}</div></div>`:''}
    <p class="probe-note">Il test non importa annunci.</p>`
    :`<div class="probe-failure">${icon('warning')}<div><strong>${e(reason)}</strong>${next?`<p>${e(next)}</p>`:''}</div></div>`}
    <details class="probe-details"><summary>Dettagli tecnici</summary><pre class="json-result">${e(JSON.stringify(result,null,2))}</pre></details>
    </div>`,'medium-modal probe-modal');
}

export {importDialog} from './import-ui.js';

export function propertyDialog(s,p) {
  const editor=s.user.role!=='viewer', sourceUrl=safeUrl(p.url);
  const missing=p.missing_fields || [];
  // Price and €/m² already lead the sheet: the record lists everything else once.
  const surface=p.surface==null?null:`${num(p.surface)} m²${p.area_basis&&p.area_basis!=='unknown'?' · '+(p.area_basis==='commercial'?'commerciale':label(p.area_basis).toLowerCase()):''}`;
  const factRows=[['Superficie',surface],['Tipologia',p.property_type],['Stato manutentivo',p.condition],['Operazione',p.transaction_type],['Indirizzo',p.address],['Micro-zona',p.zone],['Locali',p.rooms==null?null:num(p.rooms)],['Bagni',p.bathrooms==null?null:num(p.bathrooms)],['Asta',p.is_auction?'Sì':'Non indicata']]
    .map(([k,v])=>[k,v==null||v===''||v==='unknown'?null:['Tipologia','Stato manutentivo','Operazione'].includes(k)?label(v):v]);
  const priority=p.priority||{score:0,factors:[],label:'Priorità di verifica'};
  const availability={sold:'Venduto',rented:'Affittato',withdrawn:'Ritirato',review:'Da verificare',unknown:'Da verificare',listed:'Pubblicato'}[p.availability]||'Da verificare';
  const closed=['sold','rented','withdrawn','review'].includes(p.availability);
  const position=marketPosition(p), phone=/^\+?\d{6,16}$/.test(p.decision?.contact?.telephone||'')?p.decision.contact.telephone:'';
  const place=[p.city,p.zone].filter(Boolean).map(e).join(' · ')||'Località da verificare';
  return `<dialog class="modal property-drawer" aria-labelledby="modal-title"><div class="drawer-top"><div class="drawer-breadcrumb">${icon('building')}<span>${e(p.source_name||'Immobile')}</span></div>
    <div class="drawer-top-actions"><button class="btn sheet-star ${p.starred?'starred':''}" data-action="detail-star" data-id="${e(p.id)}" aria-pressed="${Boolean(p.starred)}" ${editor?'':'disabled'}>${icon('star')}<span>${p.starred?'Salvato':'Salva'}</span></button>${sourceUrl?`<a class="btn source-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer"><span>Annuncio</span>${icon('upRight')}</a>`:''}${closeButton}</div></div>
    <div class="drawer-content">${p.images?.length?`<figure class="drawer-hero"><img class="listing-photo" src="/api/properties/${encodeURIComponent(p.id)}/image?index=0" alt="Foto dell’annuncio" decoding="async"></figure>`:''}
    <header class="sheet-head"><p class="sheet-source">${e(p.source_name||'Immobile')}</p><div class="property-title-row"><span class="sheet-place">${place}</span><div class="sheet-status">${badge(availability,closed?'warning':'neutral')}<label class="stage-pill"><span>Fase</span><select data-review="${e(p.id)}" aria-label="Fase del team" ${editor?'':'disabled'}>${selectOptions(stages.map(x=>[x,reviewLabel(x)]),p.review_status)}</select></label></div></div>
    <h1 id="modal-title">${e(p.title)}</h1><p class="drawer-subtitle">${[p.address?`${icon('pin')}${e(p.address)}`:'',p.property_type&&p.property_type!=='unknown'?e(label(p.property_type)):'',p.condition&&p.condition!=='unknown'?e(label(p.condition)):''].filter(Boolean).map(x=>`<span>${x}</span>`).join('')}</p></header>
    ${closed?notice(`${e(availability)} · escluso dalle opportunità attive.`,'warning'):''}
    ${originNote(p)}
    <div class="deal-hero">
      <div class="deal-value"><span>Prezzo richiesto</span><strong>${amount(p.price,p.currency)}</strong><p>${p.price_sqm!=null?`${amount(p.price_sqm,p.currency)}/m²`:'Prezzo al m² non calcolabile'}${p.surface!=null?` · ${num(p.surface)} m²`:''}</p></div>
      <div class="deal-position"><span>Rispetto al mercato</span>${position?`<strong class="signal-delta ${position.tone}">${e(position.text)}</strong><p>${e(position.label)}</p>`:'<strong class="muted">—</strong><p>Nessun riferimento confrontabile</p>'}</div>
      <div class="deal-score">${priorityBlock(priority,closed)}</div>
    </div>
    <div class="deal-actions">${propertyTools(s,p)}<div class="export-actions" role="group" aria-label="Esporta scheda"><a class="btn" href="/api/properties/${e(p.id)}/memo.xlsx">${icon('download')} Excel</a><a class="btn" href="/api/properties/${e(p.id)}/memo.docx">${icon('document')} Word</a></div></div>
    ${valuation(p)}
    ${decisionSection(s,p)}
    ${fourReferences(p,benchmarkDetails(p)+marketContext(p))}
    ${p.screenings.length?`<section class="detail-section"><div class="section-title"><h2>Criteri delle ricerche</h2></div><div class="screening-list">${p.screenings.map(a=>`<div class="screening-item"><span>${e(a.name)}</span>${badge(a.fit?'Nei criteri':'Fuori criteri',a.fit?'success':'neutral')}${qualitativeCheck(a)}${a.fit_reasons.some(r=>!a.custom_prompt||!r.startsWith('Criteri personalizzati'))?`<p>${a.fit_reasons.filter(r=>!a.custom_prompt||!r.startsWith('Criteri personalizzati')).map(e).join(' · ')}</p>`:''}</div>`).join('')}</div></section>`:''}
    <section class="detail-section analysis-section" ${closed||(!['hermes','llm'].includes(p.analysis.engine)&&!p.analysis.strategies?.length)?'hidden':''}><div class="section-title"><h2>Analisi dell’annuncio</h2><span class="runtime-label ${p.analysis.engine==='hermes'?'hermes':''}">${['hermes','llm'].includes(p.analysis.engine)?'Sintesi automatica':'Metodo: regole'}</span></div>${['hermes','llm'].includes(p.analysis.engine)?`<p class="asset-summary">${e(p.analysis.summary||'')}</p>`:''}<details><summary>Evidenze e verifiche</summary><div class="evidence-strategies">${(p.analysis.strategies||[]).map(x=>`<div class="strategy-evidence"><span class="strategy ${e(x.strategy)}">${e(label(x.strategy))}</span><blockquote>“${e(x.evidence)}”</blockquote><small>Evidenza testuale nell’annuncio · non verifica tecnica</small></div>`).join('') || '<p class="muted">Nessuna strategia documentata.</p>'}</div>${(p.analysis.caveats||[]).map(c=>`<p class="caveat">${icon('info')}${e(c)}</p>`).join('')}</details></section>
    <section class="detail-section record-section"><div class="section-title"><h2>Dati dell’annuncio</h2><span class="section-meta">${completeness(p,missing)}</span></div><dl class="facts-grid">${factRows.map(([k,v])=>`<div class="${v==null?'missing':''}"><dt>${e(k)}</dt><dd>${e(v??'Non indicato')}</dd></div>`).join('')}</dl>${missing.length?`<p class="missing-fields">${icon('info')} Mancano: ${missing.map(label).map(e).join(', ')}.</p>`:''}<details class="source-evidence"><summary>Provenienza campo per campo</summary><div class="table-scroll"><table class="evidence-table"><thead><tr><th>Campo</th><th>Valore</th><th>Metodo</th></tr></thead><tbody>${Object.entries(p.evidence).filter(([,v])=>v?.method).map(([k,v])=>`<tr><td>${e(label(k))}</td><td>${e(typeof v.value==='object'?JSON.stringify(v.value):v.value)}</td><td><code>${e(v.method)}</code></td></tr>`).join('')}</tbody></table></div><p><a class="text-link" href="/api/properties/${e(p.id)}/snapshot">${icon('download')} Testo originale acquisito</a></p></details></section>
    ${p.images?.length>1?`<section class="detail-section"><div class="section-title"><h2>Foto</h2>${sourceUrl?`<a class="text-link" href="${sourceUrl}" target="_blank" rel="noopener noreferrer">${e(p.source_name)} ${icon('upRight')}</a>`:''}</div><div class="listing-gallery">${p.images.slice(0,6).map((_,i)=>`<img class="listing-photo" src="/api/properties/${encodeURIComponent(p.id)}/image?index=${i}" alt="Immagine ${i+1} dell’annuncio" loading="lazy" decoding="async">`).join('')}</div></section>`:''}
    ${historyPreview(p)}
    <section class="detail-section notes-section"><div class="section-title"><h2>Note del team</h2>${p.notes.length?`<span class="section-meta">${num(p.notes.length)}</span>`:''}</div>${editor?`<form id="note-form" data-id="${e(p.id)}"><label class="sr-only" for="note-body">Aggiungi una nota</label><textarea name="body" id="note-body" rows="2" maxlength="4000" required placeholder="Scrivi una nota per il team…" data-missing="Scrivi il testo della nota"></textarea><div class="note-submit"><div id="modal-error" class="form-error" role="alert"></div><button class="btn small-btn" type="submit">Aggiungi nota</button></div></form>`:''}<div class="notes-list">${p.notes.map(n=>`<article><div><strong>${e(n.author)}</strong><time>${stamp(n.created_at)}</time></div><p>${e(n.body)}</p></article>`).join('') || (editor?'':'<p class="muted small">Ancora nessuna nota.</p>')}</div></section>
    <p class="detail-provenance">${e(p.source_name)} · ultima acquisizione ${stamp(p.last_seen,true)}</p></div>
    ${p.decision?`<div class="sheet-dock">${phone?`<a class="btn" href="tel:${e(phone)}">${icon('phone')} Chiama</a>`:''}<button class="btn primary" data-action="contact-log" data-id="${e(p.id)}" ${editor?'':'disabled'}>Registra contatto</button></div>`:''}</dialog>`;
}

// The sheet opens at its final place as a skeleton of itself; the loaded sheet (or an error) swaps in place.
const drawerFrame=content=>`<dialog class="modal property-drawer" aria-labelledby="modal-title"><div class="drawer-top"><div class="drawer-breadcrumb"></div><div class="drawer-top-actions">${closeButton}</div></div><div class="drawer-content">${content}</div></dialog>`;
export function drawerSkeleton(){
  return drawerFrame(`<div class="sheet-skeleton" role="status" aria-live="polite"><h1 id="modal-title" class="sr-only">Immobile · caricamento…</h1><span class="sr-only">Caricamento…</span>
    <i class="skeleton sk-meta"></i><i class="skeleton sk-title"></i><i class="skeleton sk-meta sk-short"></i>
    <div class="sk-hero"><i class="skeleton sk-figure"></i><i class="skeleton sk-figure"></i><i class="skeleton sk-figure"></i></div>
    <div class="sk-tools"><i class="skeleton"></i><i class="skeleton"></i><i class="skeleton"></i></div>
    <i class="skeleton sk-card"></i></div>`);
}
export function drawerMessage(message){
  return drawerFrame(`<h1 id="modal-title" class="sr-only">Immobile</h1><div class="sheet-message" role="alert"><strong>Scheda non disponibile</strong><p>${e(message)}</p></div>`);
}

// Presence of fields, not their accuracy: named by what is missing rather than as a score.
function completeness(p,missing){
  if(missing.length)return `${num(missing.length)} ${missing.length===1?'dato mancante':'dati mancanti'}`;
  return p.completeness==null||p.completeness>=100?'Dati completi':`Completezza ${num(p.completeness)}%`;
}

// Triage index from rules, not a valuation: the four parts are shown as one segmented bar.
function priorityBlock(priority,closed){
  const bar=priority.factors.length?`<span class="priority-bar" aria-hidden="true">${priority.factors.map(f=>`<i style="flex:${f.max}"><b style="width:${Math.min(100,f.points/f.max*100).toFixed(1)}%"></b></i>`).join('')}</span>`:'';
  return `<details class="priority-method plain"><summary><span>Priorità di verifica</span>${closed?`<strong class="priority-closed">${e(priority.label&&priority.label!=='Priorità di verifica'?priority.label:'Non attivo')}</strong>`:`<strong>${num(priority.score)}<small>/100</small></strong>`}${bar}</summary><div class="priority-detail"><p>${e(priority.reason||'Indice operativo a regole.')}</p>${priority.factors.map(f=>`<div><span>${e(f.label)}</span><strong>${num(f.points,1)}<small>/${f.max}</small></strong></div>`).join('')}</div></details>`;
}

export function runDialog(run,canEdit=true) {
  return modalFrame(run.agent_name,'',`<div class="modal-body" id="run-content">${runContent(run,canEdit)}</div>`,'medium-modal run-modal');
}
export function compareDialog(properties) {
  return modalFrame('Confronto',`${properties.length} immobili selezionati`,comparisonContent(properties),'wide-modal comparison-modal');
}
export function userDialog() {
  return modalFrame('Nuovo utente','Accesso a questo workspace.',`<form id="user-form" class="modal-form"><div class="form-grid"><label class="span-2">Nome<input name="name" required minlength="2" maxlength="100" autocomplete="off" data-missing="Inserisci un nome"></label><label class="span-2">Email<input name="email" type="email" required autocomplete="off"></label><label>Ruolo<select name="role">${selectOptions([['viewer','Sola lettura'],['analyst','Analista'],['admin','Amministratore']])}</select></label><label>Password iniziale<input name="password" type="password" minlength="12" maxlength="256" autocomplete="new-password" required></label></div>${notice('Gli analisti gestiscono ricerche, revisioni e note. Solo gli amministratori configurano fonti, importazioni e utenti.')}${formError}${footer('Crea account')}</form>`);
}

function valuation(p) {
  if(!p.signals)return '';
  return `<section class="valuation" aria-labelledby="valuation-title"><div class="valuation-head"><h2 id="valuation-title">Prezzo e mercato</h2></div>${priceLadder(p)}${signalFacts(p)}</section>`;
}

function benchmarkDetails(p){
  const benchmark=p.benchmark;
  return `<details class="reference-extra"><summary>Prezzo di zona usato nei filtri</summary>${benchmark?`<div class="benchmark-box"><div><span>Range di riferimento / m²</span><strong>${euro(benchmark.min_sqm)} <span>–</span> ${euro(benchmark.max_sqm)}</strong><small>${e(benchmark.source_label)} · ${e(benchmark.period)}</small></div><div><span>Scostamento dal punto medio</span><strong>${discount(p)}</strong><small>${e(benchmark.zone)} · ${e(label(benchmark.property_type))}</small></div></div><div class="score-explanation">${(p.score_breakdown||[]).map(b=>`<div><span>${e(b.label)}<small><code>${e(b.formula)}</code></small></span><strong>${num(b.points,1)} <small>/ ${b.max}</small></strong></div>`).join('')}</div><p class="small muted">Confronto limitato a stato e base di superficie compatibili. Non certifica sconto, margine, cambio d’uso o valore di rivendita. ${safeUrl(benchmark.source_url)?`<a href="${safeUrl(benchmark.source_url)}" target="_blank" rel="noopener noreferrer">Fonte ${icon('upRight')}</a>`:''}</p>`:'<p class="small muted">Nessun prezzo di zona compatibile configurato.</p>'}</details>`;
}

// One € sign per range: "€ 3300–3500/m²" reads faster than two amounts.
const sqmRange=(lo,hi,cur)=>lo==null||hi==null?'Non disponibile':cur==='EUR'?`€ ${num(lo)}–${num(hi)}/m²`:`${amount(lo,cur)}–${amount(hi,cur)}/m²`;

function fourReferences(p,extra='') {
  const refs=p.market_references;if(!refs)return extra?`<section class="detail-section">${extra}</section>`:'';
  return `<section class="detail-section market-decision-section"><details class="reference-samples" ${p.signals?'':'open'}><summary><h2>Riferimenti di mercato</h2><span class="section-meta">Campioni, OMI e metodo</span></summary><div class="reference-grid">${refs.groups.map(g=>`<article class="reference-card"><span>${e(g.label)}</span><strong class="${g.median_sqm==null?'reference-missing':''}">${g.median_sqm==null?'—':amount(g.median_sqm,p.currency)+'/m²'}</strong><small>${g.median_sqm==null?e(g.reason):`${num(g.count)} annunci · ${num(g.source_count??0)} ${g.source_count===1?'fonte':'fonti'}`}</small>${g.q1_sqm!=null?`<small>Fascia centrale: ${sqmRange(g.q1_sqm,g.q3_sqm,p.currency)}</small>`:''}${g.asking_delta_pct!=null?`<small>Richiesta ${Math.abs(g.asking_delta_pct)<.05?'in linea con la mediana':`${num(Math.abs(g.asking_delta_pct),1)}% ${g.asking_delta_pct<0?'sotto':'sopra'} la mediana`}</small>`:''}${(g.warnings||[]).map(w=>`<small class="evidence-warning">${e(w)}</small>`).join('')}${g.items.length?`<details><summary>Vedi campione</summary><p class="small muted">${stamp(g.oldest_observed,true)} – ${stamp(g.newest_observed,true)} · Intervallo osservato</p>${g.items.map(x=>`<button class="plain-link" data-action="property" data-id="${e(x.id)}">${e(x.title)} · ${amount(x.price_sqm,p.currency)}/m²<small>${e(x.source)} · ${stamp(x.observed_at,true)}</small></button>`).join('')}</details>`:''}</article>`).join('')}<article class="reference-card omi-reference"><span>OMI</span>${refs.omi?.status==='available'&&!refs.omi?.stale&&refs.omi.rows?.length?`${refs.omi.rows.slice(0,2).map(r=>`<div class="omi-reference-row"><strong>${sqmRange(r.min_sqm,r.max_sqm,'EUR')}</strong><small>${e(r.type)} · ${e(r.condition)} · ${r.area_basis==='gross'?'lorda':'netta'}</small></div>`).join('')}<small>${e(refs.omi.period)} · ${e(refs.omi.zone_code||'')} · riferimento di zona</small>${refs.omi.rows.length>2?`<small>${refs.omi.rows.length} fasce nella tabella OMI della scheda</small>`:''}`:`<strong class="reference-missing">—</strong><small>${e(refs.omi?.stale?'Periodo da aggiornare: '+refs.omi.period:refs.omi?.reason||'Quotazione di zona non disponibile')}</small>`}</article></div><details><summary>Come confrontiamo</summary><p class="small muted">${e(refs.method)} La fascia centrale contiene il 50% dei prezzi osservati, non è un intervallo di confidenza. Più fonti non significano necessariamente informazioni indipendenti.${refs.sample_limited?' Campione limitato ai 1.000 annunci più recenti.':''}</p></details>${extra}</details></section>`;
}

function qualitativeCheck(a) {
  if(!a.custom_prompt)return '';
  const result=a.custom_assessment;
  const status={matched:'Coerente',not_matched:'Non coerente',uncertain:'Da verificare'};
  const checks=result?.checks?.length?result.checks:result?[{criterion:a.custom_prompt,...result}]:[];
  const matched=checks.filter(c=>c.status==='matched').length;
  const shownQuotes=new Set(checks.flatMap(c=>c.evidence||[]));
  const extra=[...new Set(result?.evidence||[])].filter(q=>!shownQuotes.has(q));
  return `<details class="qualitative-check"><summary>Criteri AI · ${status[result?.status]||'Da analizzare'}${checks.length?`<span class="setting-indicator">${num(matched)} / ${num(checks.length)} coerenti</span>`:''}</summary>
    ${checks.length?checks.map(c=>`<article class="criterion-result"><div class="criterion-heading"><strong>${e(c.criterion)}</strong>${badge(status[c.status]||'Da verificare',c.status==='matched'?'success':c.status==='not_matched'?'neutral':'warning')}</div><p>${e(c.reason)}</p>${c.evidence?.length?`<details class="criterion-evidence"><summary>Evidenze · ${num(new Set(c.evidence).size)}</summary>${[...new Set(c.evidence)].map(q=>`<blockquote>${e(q)}</blockquote>`).join('')}</details>`:''}</article>`).join(''):`<p class="preserve-lines">${e(a.custom_prompt)}</p><p>Esegui la ricerca per verificare questi criteri.</p>`}
    ${result?.checks?.length?`<details class="criterion-summary"><summary>Sintesi AI</summary><p>${e(result.reason)}</p>${extra.map(q=>`<blockquote>${e(q)}</blockquote>`).join('')}</details>`:''}
  </details>`;
}
