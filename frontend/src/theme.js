// Loaded synchronously in <head>: applies the saved theme before first paint (no light flash for
// dark users) and keeps the browser chrome colour in step with every later theme change.
(()=>{
  const root=document.documentElement;
  try{root.dataset.theme=localStorage.getItem('vedra.theme')||'light';}catch{root.dataset.theme='light';}
  const meta=document.querySelector('meta[name="theme-color"]');
  const sync=()=>meta?.setAttribute('content',root.dataset.theme==='dark'?'#0b1017':'#f7f8fa');
  sync();
  new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['data-theme']});
})();
