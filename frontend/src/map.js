import {e,num} from './utils.js';
import {icon} from './icons.js';

// Schematic outline drawn for orientation, not a cadastral/cartographic boundary.
const outlines = [
  [[6.8,45.1],[7.2,44.2],[7.5,43.8],[8.4,44.3],[9.5,44.1],[10.3,43.5],[11.1,42.5],[12.2,41.8],[13.7,41.2],[14.4,40.7],[15.4,40],[15.9,39.5],[16.1,39],[15.7,38.2],[15.8,38],[16.5,38.5],[17.1,39],[16.9,39.4],[16.5,39.7],[16.9,40.4],[17.7,40.3],[18.3,39.9],[18.4,40.3],[17.5,40.9],[16.5,41.3],[16,41.9],[15.2,41.9],[14.2,42.7],[13.5,43.5],[12.6,44.2],[12.3,44.8],[12.4,45.4],[13.2,45.7],[13.8,45.7],[13.7,46.4],[12.4,46.8],[12.1,47.1],[11.1,46.9],[10.4,46.8],[9.9,46.3],[9.2,46.5],[8.9,46],[8.3,46.2],[7.8,45.8],[7.3,45.8],[6.9,46],[6.8,45.1]],
  [[8.5,41.1],[9.2,41.2],[9.8,40.5],[9.6,39.2],[8.9,39],[8.4,39.3],[8.4,40.3],[8.5,41.1]],
  [[12.5,38.1],[13.7,38],[14.8,38.2],[15.5,38.2],[15.1,37.3],[15.1,36.7],[14.2,37],[13.3,37.3],[12.4,37.7],[12.5,38.1]],
];
export function located(items) {
  return items.filter(p=>Number.isFinite(p.latitude)&&Number.isFinite(p.longitude)&&Math.abs(p.latitude)<=85&&Math.abs(p.longitude)<=180);
}
function layout(items,mode){
  const valid=located(items), width=640, height=390;
  let bounds=[6,36,19.3,48];
  if(mode==='fit'&&valid.length){
    const lons=valid.map(p=>p.longitude),lats=valid.map(p=>p.latitude);
    const minX=Math.min(...lons),maxX=Math.max(...lons),minY=Math.min(...lats),maxY=Math.max(...lats);
    const pad=Math.max(.04,(maxX-minX)*.18,(maxY-minY)*.18);
    bounds=[minX-pad,minY-pad,maxX+pad,maxY+pad];
  }
  const [left,bottom,right,top]=bounds, cos=Math.cos(((top+bottom)/2)*Math.PI/180);
  const scale=Math.min((width-60)/((right-left)*cos),(height-40)/(top-bottom));
  const project=([lon,lat])=>[width/2+(lon-(left+right)/2)*scale*cos,height/2-(lat-(top+bottom)/2)*scale];
  const groups=new Map();
  for(const p of valid){
    const [x,y]=project([p.longitude,p.latitude]);
    if(x<16||x>width-16||y<16||y>height-16)continue;
    const key=[Math.round(x/32),Math.round(y/32)].join(':');
    const group=groups.get(key)||{x:0,y:0,items:[]};group.x+=x;group.y+=y;group.items.push(p);groups.set(key,group);
  }
  return {width,height,project,valid,groups:[...groups.values()].map(g=>({...g,x:g.x/g.items.length,y:g.y/g.items.length}))};
}
export function mapGroup(items,mode,index){return layout(items,mode).groups[Number(index)]?.items||[];}
export function mapPanel(items,mode='italy'){
  const {width,height,project,valid,groups}=layout(items,mode);
  const shown=groups.reduce((n,g)=>n+g.items.length,0),missing=items.length-valid.length;
  const paths=outlines.map(points=>'M'+points.map(pt=>project(pt).map(n=>n.toFixed(2)).join(',')).join('L')+'Z');
  return `<div class="map-canvas"><svg viewBox="0 0 ${width} ${height}" role="group" aria-label="Posizioni dichiarate dagli annunci"><defs><pattern id="map-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="currentColor" opacity=".12"/></pattern><clipPath id="map-clip"><rect width="${width}" height="${height}" rx="12"/></clipPath></defs><g clip-path="url(#map-clip)"><rect class="map-water" width="${width}" height="${height}"/><rect width="${width}" height="${height}" fill="url(#map-grid)"/>${paths.map(d=>`<path class="map-land" d="${d}"/>`).join('')}${groups.map((g,i)=>`<g class="map-point" role="button" tabindex="0" data-action="map-group" data-index="${i}" transform="translate(${g.x.toFixed(2)} ${g.y.toFixed(2)})" aria-label="Apri ${g.items.length} immobili, ${e(g.items[0].city)}"><title>${e(g.items[0].city)} · ${g.items.length} immobili</title><circle class="map-point-halo" r="${g.items.length>1?25:13}"/><circle r="${g.items.length>1?17:6}"/>${g.items.length>1?`<text text-anchor="middle" dominant-baseline="central">${g.items.length}</text>`:''}</g>`).join('')}</g></svg>${!valid.length?`<div class="map-empty"><span>${icon('pin')}</span><strong>Nessuna posizione disponibile</strong><p>La mappa si popola con le coordinate dichiarate dalle fonti.</p></div>`:''}<div class="map-controls"><button class="btn small-btn ${mode==='italy'?'selected':''}" data-action="map-mode" data-mode="italy">Italia</button><button class="btn small-btn ${mode==='fit'?'selected':''}" data-action="map-mode" data-mode="fit" ${valid.length?'':'disabled'}>${icon('expand')} Adatta ai dati</button></div></div><div class="map-caption"><span>${num(shown)} in vista${missing?` · ${num(missing)} senza coordinate`:''}</span><span>Carta schematica · non catastale</span></div>`;
}
