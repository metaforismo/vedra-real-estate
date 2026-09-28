// Dialog forms validate inline: the browser's constraints decide what is invalid, the message is ours, in Italian,
// under the field; the first invalid field is revealed (collapsed <details> opened) and focused. No native bubbles.
import {num} from './utils.js';

// Amounts are written and shown as "586.000": a dot before groups of three digits separates thousands, a comma
// is the decimal mark. "1500.5" stays a decimal. Returns null when empty, NaN when unreadable.
export function parseAmount(text){
  const raw=String(text??'').replace(/[€\s]/g,'');
  if(!raw)return null;
  const normal=raw.includes(',')?raw.replace(/\./g,'').replace(',','.'):/^-?\d{1,3}(\.\d{3})+$/.test(raw)?raw.replace(/\./g,''):raw;
  const value=Number(normal);
  return Number.isFinite(value)?value:NaN;
}
export const formatAmount=value=>value==null||value===''||!Number.isFinite(Number(value))?String(value??''):num(Number(value),2);

// Grouped amounts (data-amount: Scenario euro fields, research budgets) are text inputs, so the browser cannot
// check them as numbers; min/max and "not below another field" are checked on the parsed value.
const isAmount=field=>field.dataset.amount!==undefined;
function checkAmount(field){
  const value=parseAmount(field.value),{min,max,notBelow}=field.dataset;
  const floor=notBelow?parseAmount(field.form?.elements.namedItem(notBelow)?.value):null;
  field.setCustomValidity(value==null?''
    :Number.isNaN(value)?'Inserisci un importo, per esempio 250.000'
    :min!=null&&value<Number(min)?`Minimo ${num(Number(min),2)}`
    :max!=null&&value>Number(max)?`Massimo ${num(Number(max),2)}`
    :floor!=null&&!Number.isNaN(floor)&&value<floor?(field.dataset.notBelowMessage||`Almeno ${num(floor,2)}`):'');
}
function message(field){
  const v=field.validity;
  if(v.valueMissing)return field.dataset.missing||(field.type==='checkbox'?'Conferma per continuare':field.tagName==='SELECT'?'Scegli un’opzione':'Campo obbligatorio');
  if(v.customError)return field.validationMessage;
  if(v.tooShort)return field.dataset.missing&&!field.value.trim()?field.dataset.missing:`Almeno ${num(field.minLength)} caratteri`;
  if(v.typeMismatch)return field.type==='email'?'Indirizzo email non valido':field.type==='url'?'Indirizzo non valido: deve iniziare con https://':'Valore non valido';
  if(v.badInput)return 'Inserisci un numero';
  if(v.rangeUnderflow)return `Minimo ${num(Number(field.min),2)}`;
  if(v.rangeOverflow)return `Massimo ${num(Number(field.max),2)}`;
  if(v.stepMismatch)return Number(field.step)===1?'Inserisci un numero intero':'Valore non valido';
  return 'Valore non valido';
}
const errorId=field=>`${field.id||`${field.form?.id||'form'}-${field.name}`}-error`;
function describe(field,id,on){
  const ids=(field.getAttribute('aria-describedby')||'').split(/\s+/).filter(x=>x&&x!==id);
  if(on)ids.push(id);
  if(ids.length)field.setAttribute('aria-describedby',ids.join(' '));else field.removeAttribute('aria-describedby');
}
export function clearFieldError(field){
  const id=errorId(field);
  document.getElementById(id)?.remove();
  field.removeAttribute('aria-invalid');describe(field,id,false);
}
function showFieldError(field,text){
  const id=errorId(field);
  let node=document.getElementById(id);
  if(!node){
    node=document.createElement('small');node.className='field-error';node.id=id;
    // Inside the label the text would join the field's name: it is drawn from data-message (no text node) and
    // hidden from the name; aria-describedby still announces it.
    node.setAttribute('aria-hidden','true');
    const label=field.closest('label');
    if(label&&['checkbox','radio'].includes(field.type))label.append(node);else field.after(node);
  }
  node.dataset.message=text;
  field.setAttribute('aria-invalid','true');describe(field,id,true);
}
// <select data-requires="note" data-requires-value="discarded">: the named field becomes required for that choice.
function syncConditional(form){
  for(const select of form.querySelectorAll('[data-requires]')){
    const target=form.elements.namedItem(select.dataset.requires);
    if(target)target.required=select.value===select.dataset.requiresValue;
  }
}
export function validateForm(form){
  syncConditional(form);
  let first=null;
  for(const field of form.elements){
    if(!field.willValidate||!field.name)continue;
    if(isAmount(field))checkAmount(field);
    if(field.checkValidity())clearFieldError(field);
    else{showFieldError(field,message(field));first??=field;}
  }
  if(first){
    for(let node=first.parentElement;node&&node!==form;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;
    first.scrollIntoView({block:'center',behavior:'instant'});first.focus({preventScroll:true});
  }
  return !first;
}
export function installFormValidation(){
  document.addEventListener('submit',event=>{
    const form=event.target;
    if(!(form instanceof HTMLFormElement)||!form.noValidate||!form.closest('dialog'))return;
    if(!validateForm(form)){event.preventDefault();event.stopImmediatePropagation();}
  },true);
  // An error clears as soon as the field becomes valid; it never appears while typing.
  const recheck=event=>{
    let field=event.target;
    if(field.dataset?.requires&&field.form){syncConditional(field.form);field=field.form.elements.namedItem(field.dataset.requires)||field;}
    // Changing the minimum can clear (never raise) the error on the field that must not go below it.
    if(field.name&&field.form)for(const dependent of field.form.querySelectorAll(`[data-not-below="${CSS.escape(field.name)}"][aria-invalid="true"]`)){checkAmount(dependent);if(dependent.checkValidity())clearFieldError(dependent);}
    if(field.getAttribute?.('aria-invalid')!=='true')return;
    if(isAmount(field))checkAmount(field);
    if(field.checkValidity())clearFieldError(field);
  };
  document.addEventListener('input',recheck,true);document.addEventListener('change',recheck,true);
  document.addEventListener('focusout',event=>{
    const field=event.target;if(!field.dataset||!isAmount(field))return;
    const value=parseAmount(field.value);if(value!=null&&!Number.isNaN(value))field.value=formatAmount(value);
  },true);
}
