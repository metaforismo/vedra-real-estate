// Overflow menu shared by search cards and source rows: a native <details>, so it works without a script.
// Three dots; icons.js is shared, so the glyph lives with its only user.
const more='<svg class="icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg>';
// Background refreshes re-render the page: the open menu survives them instead of closing under the pointer.
let openMenu=null;

export function cardMenu(id,name,items,cls=''){
  const list=items.filter(Boolean).join('');if(!list)return '';
  return `<details class="card-menu ${cls}" data-id="${id}" ${openMenu===id?'open data-restored':''}><summary class="icon-button" id="card-menu-${id}" aria-label="Altre azioni per ${name}">${more}</summary><div class="card-menu-list">${list}</div></details>`;
}

// Close on outside click, after choosing an item, and on Escape.
if(typeof document!=='undefined'){
  document.addEventListener('click',event=>{
    for(const menu of document.querySelectorAll('details.card-menu[open]')){
      if(!menu.contains(event.target))menu.open=false;
      else if(event.target.closest('.card-menu-list [data-action]')){menu.open=false;menu.querySelector('summary').focus({preventScroll:true});}
    }
  });
  document.addEventListener('toggle',event=>{
    const menu=event.target;if(!menu.matches?.('details.card-menu'))return;
    if(menu.open)openMenu=menu.dataset.id;else if(openMenu===menu.dataset.id&&menu.isConnected)openMenu=null;
  },true);
  document.addEventListener('keydown',event=>{
    const menu=event.key==='Escape'&&document.querySelector('details.card-menu[open]');
    if(menu){menu.open=false;menu.querySelector('summary').focus({preventScroll:true});}
  });
}
