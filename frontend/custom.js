/* Custom Simulator v0.9: project editor, continuous 2D animation, PLC IO. */
(() => {
'use strict';
const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
const api=()=>window.pywebview&&window.pywebview.api;
const clone=x=>JSON.parse(JSON.stringify(x));
const colors={blue:'#3b82f6',orange:'#f97316',green:'#22c55e',red:'#ef4444',yellow:'#facc15',purple:'#a855f7'};
const names={blue:'Blauw',orange:'Oranje',green:'Groen',red:'Rood',yellow:'Geel',purple:'Paars'};
let project=null,catalog=null,selected=null,lastState=null,running=false,inCustom=false,saveName='mijn_simulatie';
let drag=null,busy=false,refreshBusy=false,visuals=new Map(),stripeElements=[],lastFrame=0;
let snapshotAt=0,renderedVersion='',renderedLayout='',snapGrid=true;
const FULL_VIEW={x:0,y:0,width:1200,height:720};
let viewport={...FULL_VIEW},pan=null;
const MIN_ZOOM=.35,MAX_ZOOM=5;
const heldButtons=new Set();
function h(tag,attrs={},...children){const el=document.createElement(tag);for(const [key,v] of Object.entries(attrs)){if(key==='text')el.textContent=v;else if(key==='className')el.className=v;else el.setAttribute(key,v);}children.forEach(x=>el.append(x));return el;}
function s(tag,attrs={}){const el=document.createElementNS(NS,tag);for(const [key,v] of Object.entries(attrs))el.setAttribute(key,v);return el;}
function t(group,text,x,y,opts={}){const el=s('text',{x,y,fill:'#dce8f4','text-anchor':'middle','font-size':13,...opts});el.textContent=text;group.append(el);return el;}
function msg(text,kind='info'){const box=$('customMessage');if(!box)return;box.textContent=text;box.className='custom-message '+kind;}
function applyViewport(){const el=$('customCanvas');if(el)el.setAttribute('viewBox',`${viewport.x} ${viewport.y} ${viewport.width} ${viewport.height}`);const z=$('customZoomValue');if(z)z.textContent=Math.round(1200/viewport.width*100)+'%';}
function zoomAt(factor,clientX,clientY){const el=$('customCanvas');if(!el)return;const anchor=pxy({clientX,clientY});const zoom=Math.max(MIN_ZOOM,Math.min(MAX_ZOOM,1200/viewport.width*factor));const width=1200/zoom,height=720/zoom,scale=width/viewport.width;viewport={x:anchor.x-(anchor.x-viewport.x)*scale,y:anchor.y-(anchor.y-viewport.y)*scale,width,height};applyViewport();}
function zoomCenter(factor){const r=$('customCanvas').getBoundingClientRect();zoomAt(factor,r.left+r.width/2,r.top+r.height/2);}
function resetView(){viewport={...FULL_VIEW};applyViewport();}
function pxy(event){const svg=$('customCanvas'),p=svg.createSVGPoint();p.x=event.clientX;p.y=event.clientY;const transform=svg.getScreenCTM();return transform?p.matrixTransform(transform.inverse()):{x:0,y:0};}
function unit(c){const a=(c.settings.rotation||0)*Math.PI/180;return [Math.cos(a),Math.sin(a)];}
function end(c){const [dx,dy]=unit(c),l=c.settings.length;return {x:c.x+dx*l,y:c.y+dy*l};}
function nearest(belts,x,y,maxDistance=90){let best=null;for(const b of belts){const [dx,dy]=unit(b),along=(x-b.x)*dx+(y-b.y)*dy,side=(x-b.x)*dy-(y-b.y)*dx;if(along>=-18&&along<=b.settings.length+18&&Math.abs(side)<=maxDistance){const score=Math.abs(side)+Math.max(0,-along,along-b.settings.length);if(!best||score<best.score)best={belt:b,pos:Math.max(0,Math.min(b.settings.length,along)),side,score};}}return best;}
function scaffold(){
 const cards=document.querySelector('#homeScreen .home-cards');
 const card=h('article',{className:'sim-card available custom-home-card'});
 card.innerHTML='<div class="sim-image custom-art"><span>▦</span><span>⚙</span><span>◎</span></div><div class="sim-card-body"><div class="sim-card-top"><span class="sim-category">04 / MODULAR AUTOMATION</span><span class="sim-status ready">v1.0</span></div><h3>Custom Simulator</h3><p>Bouw je eigen 2D-installatie met invoerbakken, lichtsluizen, transportbanden en TwinCAT ADS.</p><button id="openCustom" class="sim-launch" type="button">Open editor →</button></div>';
 cards.append(card);
 const root=h('section',{id:'customWorkspace',className:'custom-workspace',hidden:''});
 root.innerHTML=`<div class="custom-head"><div><button class="back-home" id="customBack">← Alle simulaties</button><div class="overline">INSTALLATIE 04 / MODULAR AUTOMATION</div><h2>Custom <span>Simulator</span> <small class="custom-version">v1.0</small></h2><p>Stel een 2D-installatie samen · PLC bepaalt de besturing · simulator beheert de fysica</p></div><span id="customMode" class="mode-tag">EDITOR</span></div>
 <div class="custom-toolbar panel"><label>Project <input id="customProjectName" maxlength="80" value="Mijn eerste installatie"></label><button class="btn ghost" id="customNew">Nieuw</button><button class="btn ghost" id="customSave">Opslaan</button><button class="btn ghost" id="customOpen">Openen</button><button class="btn primary" id="customConnect">▶ Start / Verbinden</button><button class="btn stop" id="customDisconnect" disabled>■ Stop</button></div>
 <div class="custom-editor-actions"><button type="button" class="btn ghost" id="customDuplicate">Dupliceren (Ctrl+D)</button><button type="button" class="btn ghost" id="customRotate">Roteer 90° (R)</button></div>
 <div class="custom-columns"><aside class="panel custom-palette"><div class="overline">01 / COMPONENTEN</div><h3>Bibliotheek</h3><p>Klik om componenten te plaatsen. Sleep ze op het werkvlak.</p><div id="customCatalog"></div><hr><div class="overline">VERBINDING</div><p id="customTarget">—</p><div id="customMissing"></div></aside>
 <div class="custom-main panel"><div class="custom-canvas-header"><strong>2D-installatie</strong><label class="custom-snap"><input type="checkbox" id="customGridSnap" checked> Raster 10</label><div class="custom-view-controls"><button id="customZoomOut" type="button" title="Uitzoomen" aria-label="Uitzoomen">−</button><span id="customZoomValue">100%</span><button id="customZoomIn" type="button" title="Inzoomen" aria-label="Inzoomen">+</button><button id="customZoomReset" type="button" title="Passend beeld">Reset</button></div></div><svg id="customCanvas" viewBox="0 0 1200 720" aria-label="2D machine-editor"></svg><div class="custom-view-hint">Muiswiel: zoom op cursor · Sleep lege ruimte: verschuiven · Middelste muisknop of Shift+slepen: pannen · Reset: volledig overzicht</div><div class="custom-stats"><span id="customGenerated">Geproduceerd: 0</span><span id="customInFlight">Op banden: 0</span><span id="customCollected">Opgevangen: 0</span></div><div id="customMessage" class="custom-message" role="status">Plaats componenten en klik Start.</div></div>
 <aside class="panel custom-properties"><div class="overline">02 / EIGENSCHAPPEN</div><h3>Configuratie</h3><div id="customProperties">Selecteer een component.</div><hr><div class="overline">LIVE I/O</div><div id="customIo"></div><p class="custom-tip">PLC OUT → machine, machine IN → PLC. BOOL-signalen; zonder mapping werkt een invoerbak automatisch.</p></aside></div>`;
 const footer=document.querySelector('.shell > footer');footer.parentNode.insertBefore(root,footer);
 $('openCustom').onclick=show;$('customBack').onclick=back;
 $('customNew').onclick=()=>{if(running)return;project={version:1,name:'Nieuwe installatie',components:[]};selected=null;lastState=null;renderAll();msg('Nieuw project gestart.');};
 $('customSave').onclick=save;$('customOpen').onclick=open;
 $('customDuplicate').onclick=duplicateSelected;$('customRotate').onclick=rotateSelected;$('customConnect').onclick=connect;$('customDisconnect').onclick=disconnect;
 $('customProjectName').oninput=e=>{if(!running&&project)project.name=e.target.value;};
 $('customGridSnap').onchange=e=>snapGrid=e.target.checked;
 const canvas=$('customCanvas');
 $('customZoomIn').onclick=()=>zoomCenter(1.25);$('customZoomOut').onclick=()=>zoomCenter(.8);$('customZoomReset').onclick=resetView;
 canvas.addEventListener('wheel',e=>{e.preventDefault();zoomAt(Math.exp(-e.deltaY*.0015),e.clientX,e.clientY);},{passive:false});
 canvas.addEventListener('contextmenu',e=>e.preventDefault());
 canvas.addEventListener('pointerdown',e=>{if(e.button===1||e.button===2||e.shiftKey||e.target===canvas||e.target.getAttribute('data-background')==='yes'){pan={id:e.pointerId,x:e.clientX,y:e.clientY,origin:{...viewport}};canvas.setPointerCapture(e.pointerId);e.preventDefault();}});
 canvas.addEventListener('pointermove',e=>{if(pan&&pan.id===e.pointerId){const r=canvas.getBoundingClientRect();if(r.width&&r.height){viewport.x=pan.origin.x-(e.clientX-pan.x)*pan.origin.width/r.width;viewport.y=pan.origin.y-(e.clientY-pan.y)*pan.origin.height/r.height;applyViewport();}return;}if(!drag||running)return;const c=project.components.find(c=>c.id===drag.id);if(!c)return;const p=pxy(e);let x=p.x-drag.dx,y=p.y-drag.dy;
   if(snapGrid){x=Math.round(x/10)*10;y=Math.round(y/10)*10;}
   const belts=project.components.filter(item=>item.type==='conveyor'&&item.id!==c.id);
   if(c.type==='source'||c.type==='sink'){let best=null;for(const b of belts){const pt=c.type==='source'?{x:b.x,y:b.y}:end(b);const angle=(b.settings.rotation||0)*Math.PI/180;const offset=c.type==='source'?-68:68;const tx=pt.x+Math.cos(angle)*offset,ty=pt.y+Math.sin(angle)*offset;const d=Math.hypot(x-tx,y-ty);if(d<42&&(!best||d<best.d))best={x:tx,y:ty,d};}if(best){x=best.x;y=best.y;}}
   if(c.type==='sensor'){const near=nearest(belts,x,y,75);if(near){const [dx,dy]=unit(near.belt),side=near.side<0?-42:42;x=near.belt.x+dx*near.pos-dy*side;y=near.belt.y+dy*near.pos+dx*side;}}
   if(c.type==='conveyor'){for(const b of belts){const pt=end(b);if(Math.hypot(x-pt.x,y-pt.y)<35){x=pt.x;y=pt.y;break;}}}
   c.x=Math.min(1200,Math.max(0,Math.round(x)));c.y=Math.min(720,Math.max(0,Math.round(y)));renderScene();});
 canvas.addEventListener('pointerup',e=>{if(pan&&pan.id===e.pointerId)pan=null;if(drag){drag=null;renderProperties();}});canvas.addEventListener('pointercancel',()=>{drag=null;pan=null;});
 window.addEventListener('pointerup',()=>{for(const id of heldButtons)press(id,false);heldButtons.clear();});
 window.addEventListener('blur',()=>{for(const id of heldButtons)press(id,false);heldButtons.clear();});
 window.addEventListener('keydown',e=>{if(!inCustom||running||e.target.matches('input,select,textarea'))return;if((e.key==='Delete'||e.key==='Backspace')&&selected){removeSelected();}else if(e.ctrlKey&&e.key.toLowerCase()==='d'){e.preventDefault();duplicateSelected();}else if(e.key.toLowerCase()==='r'){rotateSelected();}});
 requestAnimationFrame(frame);
}
function show(){document.querySelectorAll('#homeScreen,#simulationWorkspace,#garageWorkspace').forEach(e=>e.hidden=true);$('customWorkspace').hidden=false;inCustom=true;document.title='PLC Simulation Lab — Custom Simulator';renderAll();}
function back(){if(running){msg('Stop de simulatie voordat je wisselt.','warn');return;}inCustom=false;$('customWorkspace').hidden=true;showScreen('home');}
function add(type){if(running)return;if(project.components.length>=100){msg('Maximaal 100 componenten.','error');return;}const d=catalog[type],id=type+Date.now().toString(36);const plc={};Object.keys(d.io).forEach(k=>plc[k]='');const n=project.components.length;
 const c={id,type,x:170+(n%5)*95,y:150+Math.floor(n/5)*90,settings:clone(d.defaults),plc};project.components.push(c);selected=id;renderAll();}
function removeSelected(){if(!selected||running)return;project.components=project.components.filter(c=>c.id!==selected);selected=null;renderAll();}
function renderScene(){const canvas=$('customCanvas');canvas.replaceChildren();stripeElements=[];visuals.clear();applyViewport();
 const defs=s('defs'),grid=s('pattern',{id:'customGrid',width:30,height:30,patternUnits:'userSpaceOnUse'});grid.append(s('path',{d:'M30 0H0V30',fill:'none',stroke:'#60718b','stroke-width':'.6',opacity:'.30'}));defs.append(grid);canvas.append(defs,s('rect',{'data-background':'yes',x:-10000,y:-10000,width:20000,height:20000,fill:'url(#customGrid)'}));
 const belts=project.components.filter(c=>c.type==='conveyor');
 // Links are inferred from geometry, not user-drawn PLC wires.
 for(const b of belts){const e=end(b);for(const c of project.components){if(c.id===b.id)continue;let dist=999,target=null;if(c.type==='source'){dist=Math.hypot(c.x-b.x,c.y-b.y);target={x:b.x,y:b.y};}else if(c.type==='sink'||c.type==='conveyor'){dist=Math.hypot(c.x-e.x,c.y-e.y);target=e;}if(dist< (c.type==='conveyor'?42:112)){canvas.append(s('line',{x1:c.x,y1:c.y,x2:target.x,y2:target.y,stroke:'#2dd4bf','stroke-width':2,'stroke-dasharray':'7 6',opacity:'.8','pointer-events':'none'}));}}}
 for(const c of project.components){const g=s('g',{transform:`translate(${c.x} ${c.y})`,'data-id':c.id,class:`custom-object ${selected===c.id?'selected':''}`});const live=(lastState?.values?.[c.id])||{};
 if(c.type==='conveyor'){
   const length=c.settings.length,angle=c.settings.rotation||0;const body=s('g',{transform:`rotate(${angle})`});body.append(s('rect',{x:0,y:-22,width:length,height:44,rx:18,fill:'#283e53',stroke:'#718ba5','stroke-width':3}));
   body.append(s('rect',{x:9,y:-16,width:Math.max(1,length-18),height:32,rx:9,fill:live.motor?'#186b69':'#375164',class:'custom-belt-surface'}));
   // Per-belt clip path prevents the moving tread texture escaping rounded edges.
   const clipId='customBeltClip_'+c.id;const cp=s('clipPath',{id:clipId,clipPathUnits:'userSpaceOnUse'});cp.append(s('rect',{x:9,y:-16,width:Math.max(1,length-18),height:32,rx:9}));defs.append(cp);
   const clipped=s('g',{'clip-path':`url(#${clipId})`});const stripes=s('g',{class:'belt-stripes'});
   for(let i=-40;i<length+55;i+=25)stripes.append(s('line',{x1:i,y1:-13,x2:i,y2:13,stroke:'#8fabb9','stroke-width':3,opacity:'.8'}));
   clipped.append(stripes);body.append(clipped);stripeElements.push({node:stripes,speed:c.settings.speed,motor:!!live.motor,angle,length,id:c.id,phase:0});
   body.append(s('circle',{cx:13,r:8,fill:'#92a8bd'}),s('circle',{cx:length-13,r:8,fill:'#92a8bd'}));t(body,c.id,length/2,45);g.append(body);
 }else if(c.type==='sensor'){
   const near=nearest(belts,c.x,c.y,90);if(near){const b=near.belt,[dx,dy]=unit(b),offset=near.side<0?-32:32,ex=b.x+dx*near.pos-dy*offset,ey=b.y+dy*near.pos+dx*offset;
      const beam=s('line',{x1:ex-c.x,y1:ey-c.y,x2:ex-c.x+dy*offset*2,y2:ey-c.y-dx*offset*2,stroke:live.detected?'#fb7185':'#38bdf8',class:'custom-sensor-beam','stroke-width':3,'stroke-dasharray':live.detected?'4 9':'7 4','pointer-events':'none'});g.append(beam);
   }g.append(s('rect',{x:-13,y:-13,width:26,height:26,rx:5,fill:live.detected?'#16a34a':'#2563eb',class:'custom-sensor-body',stroke:'#bfdbfe','stroke-width':2}),s('circle',{r:5,fill:'#f0f9ff'}));
 }else if(c.type==='source'||c.type==='sink'){
   const source=c.type==='source',filled=!source&&!!live.full;g.append(s('path',{d:'M-30 -25 H30 L23 28 H-23Z',fill:filled?'#854d0e':'#31475d',class:'custom-bin-body',stroke:filled?'#fbbf24':'#9bb3c8','stroke-width':2}));
   if(source){for(let i=0;i<3;i++)g.append(s('rect',{x:-19+i*13,y:-7+(i%2)*9,width:12,height:12,rx:2,fill:[colors.blue,colors.orange,colors.green][i]}));}else{t(g,String(lastState?.collected?.[c.id]||0),0,6,{'font-size':20,'font-weight':'bold',class:'custom-bin-count'});}
   t(g,source?'IN':'OUT',0,-39,{'font-size':12,'font-weight':'bold'});
 }else if(c.type==='button'){
   g.append(s('rect',{x:-24,y:-24,width:48,height:48,rx:8,fill:'#40556b',stroke:'#8094a7','stroke-width':2}),s('circle',{r:17,fill:live.pressed?'#86efac':'#16a34a',class:'custom-button-led',stroke:'#bbf7d0','stroke-width':3}));
 }else if(c.type==='lamp'){
   g.append(s('circle',{r:24,fill:live.on?'#fde047':'#59471d',class:'custom-lamp-body',stroke:'#eab308','stroke-width':3}),s('circle',{r:10,fill:live.on?'#fff7ae':'#a16207',class:'custom-lamp-center'}));
 }else if(c.type==='package'){
   if(!running)g.append(s('rect',{x:-14,y:-14,width:28,height:28,rx:3,fill:colors[c.settings.color]||colors.blue,stroke:'#eff6ff','stroke-width':2}));
 }
 if(c.type!=='conveyor')t(g,c.id,0,c.type==='source'||c.type==='sink'?46:-33,{'font-size':12});
 if(selected===c.id){g.append(s('circle',{r:c.type==='conveyor'?0:35,fill:'none',stroke:'#5eead4','stroke-width':2,'stroke-dasharray':'5 4','pointer-events':'none'}));}
 g.addEventListener('pointerdown',event=>{if(event.button!==0||event.shiftKey)return;event.stopPropagation();selected=c.id;if(running){if(c.type==='button'){heldButtons.add(c.id);press(c.id,true);}return;}
   const p=pxy(event);drag={id:c.id,dx:p.x-c.x,dy:p.y-c.y};canvas.setPointerCapture(event.pointerId);renderProperties();});
 canvas.append(g);
 }
 const dynamic=s('g',{id:'customParcels','pointer-events':'none'});canvas.append(dynamic);
 if(running&&lastState)updateParcels(lastState.parcels||[]);
}
function updateSceneStates(){if(!project||!lastState)return;
 for(const c of project.components){const g=Array.from($('customCanvas').querySelectorAll('.custom-object')).find(n=>n.getAttribute('data-id')===c.id);if(!g)continue;const val=lastState.values?.[c.id]||{};
  const set=(selector,attr,v)=>{const node=g.querySelector(selector);if(node)node.setAttribute(attr,v);};
  if(c.type==='conveyor')set('.custom-belt-surface','fill',val.motor?'#186b69':'#375164');
  if(c.type==='sensor'){set('.custom-sensor-body','fill',val.detected?'#16a34a':'#2563eb');set('.custom-sensor-beam','stroke',val.detected?'#fb7185':'#38bdf8');set('.custom-sensor-beam','stroke-dasharray',val.detected?'4 9':'7 4');}
  if(c.type==='lamp'){set('.custom-lamp-body','fill',val.on?'#fde047':'#59471d');set('.custom-lamp-center','fill',val.on?'#fff7ae':'#a16207');}
  if(c.type==='button')set('.custom-button-led','fill',val.pressed?'#86efac':'#16a34a');
  if(c.type==='sink'){const full=!!val.full;set('.custom-bin-body','fill',full?'#854d0e':'#31475d');set('.custom-bin-body','stroke',full?'#fbbf24':'#9bb3c8');const count=g.querySelector('.custom-bin-count');if(count)count.textContent=String(lastState.collected?.[c.id]||0);}
 }
 for(const b of stripeElements)b.motor=!!lastState.values?.[b.id]?.motor;
}
function updateParcels(parcels){const layer=$('customParcels');if(!layer)return;const now=performance.now();const ids=new Set(parcels.map(p=>p.id));
 for(const [id,obj] of visuals){if(!ids.has(id)){obj.node.remove();visuals.delete(id);}}
 for(const p of parcels){let obj=visuals.get(p.id);if(!obj){const node=s('g');node.append(s('rect',{x:-15,y:-14,width:30,height:28,rx:4,fill:colors[p.color]||'#64748b',stroke:'#e2e8f0','stroke-width':2}),s('path',{d:'M -15 0 H 15 M 0 -14 V 14',stroke:'#ffffff','stroke-opacity':'.22','stroke-width':2}));layer.append(node);obj={node,x:p.x,y:p.y,sample:{...p},sampleAt:now};visuals.set(p.id,obj);node.setAttribute('transform',`translate(${obj.x} ${obj.y})`);}else{obj.sample={...p};obj.sampleAt=now;const jump=Math.hypot(p.x-obj.x,p.y-obj.y);if(jump>120){obj.x=p.x;obj.y=p.y;}}}
}
function frame(now){const dt=Math.min(.05,(now-(lastFrame||now))/1000);lastFrame=now;
 if(inCustom&&running&&lastState){
  for(const b of stripeElements){if(b.motor)b.phase=(b.phase+b.speed*dt)%25;b.node.setAttribute('transform',`translate(${b.phase} 0)`);}
  const belts=new Map(project.components.filter(c=>c.type==='conveyor').map(c=>[c.id,c]));
  for(const obj of visuals.values()){
   const sample=obj.sample,belt=belts.get(sample.belt);let tx=sample.x,ty=sample.y;
   // Predict between backend samples. Clamp to belt end and correct gently on next snapshot.
   if(belt&&lastState.values?.[belt.id]?.motor){const seconds=Math.min((now-obj.sampleAt)/1000,.18);const [dx,dy]=unit(belt);const endPos=end(belt);const along=Math.max(0,Math.min(belt.settings.length,(sample.x-belt.x)*dx+(sample.y-belt.y)*dy+belt.settings.speed*seconds));tx=belt.x+dx*along;ty=belt.y+dy*along;}
   const follow=1-Math.exp(-dt*24);obj.x+=(tx-obj.x)*follow;obj.y+=(ty-obj.y)*follow;obj.node.setAttribute('transform',`translate(${obj.x} ${obj.y})`);
  }
 }
 requestAnimationFrame(frame);
}
function renderProperties(){const root=$('customProperties');root.replaceChildren();const c=project.components.find(x=>x.id===selected);if(!c){root.textContent='Selecteer een component op het werkvlak.';return;}
 root.append(h('strong',{text:catalog[c.type].label+' · '+c.id}));
 const field=(label,key,value,opts,onChange)=>{const wrap=h('label',{className:'custom-field'});wrap.append(h('span',{text:label}));let el;if(opts.options){el=h('select');for(const [v,l] of opts.options)el.append(h('option',{value:v,text:l}));el.value=String(value);}else{el=h('input',{type:opts.type||'text',value:String(value)});if(opts.min!==undefined)el.min=String(opts.min);if(opts.max!==undefined)el.max=String(opts.max);if(opts.step!==undefined)el.step=String(opts.step);}el.disabled=running;el.onchange=()=>{try{onChange(el.value);renderAll();msg('Instelling aangepast — vergeet niet op te slaan.','ok');}catch(err){msg(String(err),'error');renderProperties();}};wrap.append(el);root.append(wrap);};
 field('X positie','x',c.x,{type:'number',min:0,max:1200},v=>setCoord(c,'x',v));field('Y positie','y',c.y,{type:'number',min:0,max:720},v=>setCoord(c,'y',v));
 const labels={length:'Lengte',speed:'Snelheid (eenheden/s)',rotation:'Rotatie',range:'Detectietolerantie',interval:'Interval (sec)',capacity:'Capaciteit',color:'Pakketkleur',mode:'Aanvoermodus',pattern:'Kleurenpatroon'};
 for(const [key,value] of Object.entries(c.settings)){
 let opts={type:'number',min:1,max:600};if(key==='rotation')opts={options:[['0','→ Rechts'],['90','↓ Omlaag'],['180','← Links'],['270','↑ Omhoog']]};
 if(key==='mode')opts={options:[['fixed','Vaste kleur'],['random','Willekeurig'],['pattern','Vast patroon']]};
 if(key==='color')opts={options:Object.entries(names).map(([v,l])=>[v,l])};
 if(key==='pattern')opts={type:'text'};
 if(c.type==='source' && key==='color' && c.settings.mode!=='fixed')continue;
 if(c.type==='source' && key==='pattern' && c.settings.mode!=='pattern')continue;
 if(key==='interval')opts={type:'number',min:.2,max:120,step:.1};
 if(key==='capacity')opts={type:'number',min:1,max:250};
 field(labels[key]||key,key,value,opts,v=>{if(['mode','color','pattern'].includes(key))c.settings[key]=v;else c.settings[key]=Number(v);});
 }
 for(const [port,symbol] of Object.entries(c.plc))field(`PLC ${port} (${catalog[c.type].io[port].toUpperCase()})`,port,symbol,{type:'text'},v=>{if(v&&!/^[A-Za-z_][A-Za-z0-9_.]*$/.test(v))throw Error('Ongeldige symboolnaam');c.plc[port]=v.trim();});
 if(c.type==='sink'){const info=h('div',{className:'custom-sink-count',text:'Ontvangen: '+(lastState?.collected?.[c.id]||0)+' / '+c.settings.capacity});root.append(info);if(running){const empty=h('button',{className:'btn ghost full-width',text:'Opvangbak leegmaken'});empty.onclick=()=>api().custom_empty_sink(c.id).then(state=>{lastState=state;renderIo();renderProperties();});root.append(empty);}}
 if(c.type==='button'&&running){const b=h('button',{className:'btn start full-width',text:'Drukknop ingedrukt houden'});b.onpointerdown=()=>press(c.id,true);b.onpointerup=()=>press(c.id,false);b.onpointercancel=()=>press(c.id,false);b.onpointerleave=()=>press(c.id,false);root.append(b);}
 const del=h('button',{className:'btn stop full-width',text:'Component verwijderen'});del.disabled=running;del.onclick=removeSelected;root.append(del);
}
function duplicateSelected(){
 if(!selected||running)return;const source=project.components.find(c=>c.id===selected);if(!source)return;
 const copy=clone(source);let i=2;let candidate=source.id+'_copy';while(project.components.some(c=>c.id===candidate)){candidate=source.id+'_copy'+i++;}
 if(candidate.length>40){msg('Component-ID wordt te lang om veilig te dupliceren.','error');return;}
 copy.id=candidate;copy.x=Math.min(1200,copy.x+45);copy.y=Math.min(720,copy.y+45);
 for(const key of Object.keys(copy.plc))copy.plc[key]='';
 if(project.components.length>=100){msg('Maximaal 100 componenten toegestaan.','error');return;}
 project.components.push(copy);selected=copy.id;renderAll();msg('Component gedupliceerd. Stel indien nodig een nieuwe PLC-mapping in.','ok');
}
function rotateSelected(){if(!selected||running)return;const c=project.components.find(x=>x.id===selected);if(!c||c.type!=='conveyor'){msg('Roteren is beschikbaar voor transportbanden.','error');return;}
 c.settings.rotation=((Number(c.settings.rotation)||0)+90)%360;renderAll();msg('Transportband 90° gedraaid.','ok');
}
function setCoord(c,key,v){const n=Number(v);if(!Number.isFinite(n)||n<0||n>(key==='x'?1200:720))throw Error('Ongeldige positie');c[key]=n;}
function renderAll(){if(!project||!catalog)return;$('customProjectName').value=project.name;$('customProjectName').disabled=running;
 $('customCatalog').replaceChildren();for(const type of Object.keys(catalog)){const b=h('button',{className:'custom-catalog-item',text:'＋ '+catalog[type].label});b.disabled=running;b.onclick=()=>add(type);$('customCatalog').append(b);}
 ['customNew','customSave','customOpen'].forEach(id=>$(id).disabled=running);$('customConnect').disabled=running;$('customDisconnect').disabled=!running;
 $('customMode').textContent=running?'SIMULATIE ACTIEF':'EDITOR';$('customDuplicate').disabled=running||!selected;$('customRotate').disabled=running||!selected||project.components.find(c=>c.id===selected)?.type!=='conveyor';renderScene();renderProperties();renderIo();}
function renderIo(){if(!lastState)return;const root=$('customIo');root.replaceChildren();if(running){for(const c of project.components){for(const [port,direction] of Object.entries(catalog[c.type].io)){const row=h('div',{className:'custom-io-row'});row.append(h('span',{text:c.id+'.'+port+' '+direction.toUpperCase()}),h('strong',{text:lastState.values?.[c.id]?.[port]?'TRUE':'FALSE'}));root.append(row);}}}
 $('customMissing').textContent=lastState.missing?.length?'Ontbrekende symbolen: '+lastState.missing.join(', '):'Geen ontbrekende symbolen gemeld';$('customTarget').textContent=lastState.target+(lastState.demo?' · DEMO':' · ADS');
 $('customGenerated').textContent='Geproduceerd: '+(lastState.generated||0);$('customInFlight').textContent='Op banden: '+(lastState.parcels||[]).length;
 $('customCollected').textContent='Opgevangen: '+Object.values(lastState.collected||{}).reduce((a,b)=>a+b,0);
}
async function guard(fn){if(busy)return;busy=true;try{await fn();}catch(err){msg(String(err),'error');}finally{busy=false;}}
async function apply(){project.name=$('customProjectName').value;return api().custom_load_project(project);}
async function connect(){await guard(async()=>{await apply();const state=await api().custom_connect();lastState=state;running=!!state.connected;if(state.error)msg(state.error,'error');else msg(state.demo?'Demo actief. Druk op de groene knop om de band te starten.':'ADS verbonden: besturing via TwinCAT.','ok');project=state.project;renderAll();});}
async function disconnect(){await guard(async()=>{lastState=await api().custom_disconnect();running=false;renderAll();msg('Simulatie gestopt.','ok');});}
async function press(id,pressed){if(!running||!api())return;try{await api().custom_press(id,pressed);}catch(err){msg(String(err),'error');}}
async function save(){await guard(async()=>{if(running)throw Error('Stop de simulatie voor je opslaat.');await apply();const filename=window.prompt('Bestandsnaam (letters, cijfers, _ en -)',saveName);if(!filename)return;const res=await api().custom_save(filename);saveName=filename;msg('Project opgeslagen: '+res.path,'ok');});}
async function open(){await guard(async()=>{if(running)throw Error('Stop de simulatie.');const files=await api().custom_list_projects();if(!files.length)throw Error('Geen projecten gevonden.');const filename=window.prompt('Open project:\n'+files.join('\n'),files[0]);if(!filename)return;const state=await api().custom_open(filename);lastState=state;project=state.project;selected=null;saveName=filename;renderAll();msg('Project geladen: '+filename,'ok');});}
async function refresh(){if(!api()||refreshBusy||!inCustom)return;refreshBusy=true;try{const state=await api().custom_get_state();const changed=state.connected!==running;lastState=state;running=state.connected;if(changed){project=state.project;renderAll();}else if(running){updateParcels(state.parcels||[]);for(const b of stripeElements){const id=b.node.parentNode.parentNode.getAttribute('data-id');b.motor=!!state.values?.[id]?.motor;}
   // Update colors and counters in place: NEVER recreate the scene on PLC I/O changes.
   updateSceneStates();
   renderIo();if(selected&&project.components.find(c=>c.id===selected)?.type==='sink'){const info=$('customProperties').querySelector('.custom-sink-count');if(info){const c=project.components.find(c=>c.id===selected);info.textContent='Ontvangen: '+(state.collected?.[selected]||0)+' / '+c.settings.capacity;}}
 }if(state.error)msg(state.error,'error');}catch(err){msg('Status ophalen mislukt: '+String(err),'error');}finally{refreshBusy=false;}}
function boot(){scaffold();const start=async()=>{if(!api()){setTimeout(start,300);return;}try{catalog=await api().custom_catalog();lastState=await api().custom_get_state();project=lastState.project;renderAll();msg('Editor klaar. Componenten kun je naast de band plaatsen.','ok');setInterval(refresh,150);}catch(err){msg('Custom editor initialisatie: '+String(err),'error');}};start();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
