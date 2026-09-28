// Loaded synchronously in <head>: applies the saved theme before first paint (no light flash for
// dark users) and keeps the browser chrome colour in step with every later theme change.
(()=>{
  const root=document.documentElement;
  // No saved choice: follow the system, live, until the user picks a theme with the toggle.
  const system=matchMedia('(prefers-color-scheme: dark)');
  const saved=()=>{try{return localStorage.getItem('vedra.theme');}catch{return null;}};
  root.dataset.theme=saved()||(system.matches?'dark':'light');
  system.addEventListener('change',()=>{if(saved())return;root.dataset.theme=system.matches?'dark':'light';root.dispatchEvent(new Event('vedra:theme'));});
  const meta=document.querySelector('meta[name="theme-color"]');
  const sync=()=>meta?.setAttribute('content',root.dataset.theme==='dark'?'#0b1017':'#f7f8fa');
  sync();
  new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['data-theme']});
})();
