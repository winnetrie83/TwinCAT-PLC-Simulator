/* v1.0.1 tank exercise, deliberately separate from the custom editor. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
let active=false,connected=false,busy=false,last=null,refreshing=false;
const api=()=>window.pywebview?.api;
const fmt=v=>Number(v||0).toFixed(1);
const names={start:'Startdrukknop',stop:'Stopdrukknop',level_low:'Laag niveausensor',level_high:'Hoog niveausensor',pressure_high:'Hoge-druksensor',pressure:'Drukwaarde (REAL)',pump_in:'Vulpomp P1',pump_out:'Afvoerpomp P2'};
const component=(tag,attrs={},html='')=>{let e=document.createElement(tag);for(const [k,v] of Object.entries(attrs)){if(k==='className')e.className=v;else e.setAttribute(k,v);}e.innerHTML=html;return e;};
function init(){
  const v=document.querySelector('.topright .vchip');if(v)v.textContent='BETA 1.0.1';
  const footerLabel=document.querySelector('.shell > footer span');if(footerLabel)footerLabel.textContent='PLC SIMULATION LAB · BETA 1.0.1';
  const cards=document.querySelector('#homeScreen .home-cards');
  const old=Array.from(cards.querySelectorAll('.sim-card')).find(c=>c.textContent.includes('Drukvat &'));
  if(old)old.remove();
  const card=component('article',{className:'sim-card available'},`<div class="sim-image vessel-art" aria-hidden="true"><div class="art-vessel"><div class="art-liquid"></div></div><div class="art-pipe left"></div><div class="art-pipe right"></div><div class="art-pump left"></div><div class="art-pump right"></div></div><div class="sim-card-body"><div class="sim-card-top"><span class="sim-category">03 / PROCESS CONTROL</span><span class="sim-status ready">Beschikbaar</span></div><h3>Drukvat &amp; pompen</h3><p>Bestuur de vul- en afvoerpomp in TwinCAT. Lees niveau-, druk- en alarmsensoren uit.</p><button class="sim-launch" id="openTank" type="button">Open simulatie →</button></div>`);
  const custom=cards.querySelector('.custom-home-card');cards.insertBefore(card,custom);
  const root=component('section',{id:'tankWorkspace',className:'tank-workspace',hidden:''},`
    <div class="tank-head"><div><button class="back-home" id="tankBack" type="button">← Alle simulaties</button><div class="overline">INSTALLATIE 03 / PROCESS CONTROL</div><h2>Drukvat <span>&amp; twee pompen</span></h2><p>TwinCAT bepaalt de motorcommando's; de simulator berekent de virtuele niveaus en sensoren.</p></div><span id="tankMode" class="mode-tag">NIET VERBONDEN</span></div>
    <div class="tank-layout">
      <div class="panel tank-visual"><div class="overline">FYSIEKE INSTALLATIE</div><svg viewBox="0 0 760 480" id="tankSvg" role="img" aria-label="Vloeistofvat met vulpomp, afvoerpomp en niveausensoren">
       <defs><clipPath id="tankFluidClip"><rect x="260" y="80" width="240" height="304" rx="12"/></clipPath><linearGradient id="tankWater" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#38bdf8"/><stop offset="1" stop-color="#0e7490"/></linearGradient></defs>
       <path d="M120 219 H260" stroke="#64748b" stroke-width="17" fill="none"/><path d="M500 335 H635" stroke="#64748b" stroke-width="17" fill="none"/>
       <rect x="260" y="80" width="240" height="304" rx="12" stroke="#9fb5cd" stroke-width="7" fill="#152c43"/>
       <g clip-path="url(#tankFluidClip)"><rect id="tankLiquid" x="262" y="278" width="236" height="105" fill="url(#tankWater)"/><path id="tankWave" d="" fill="none" stroke="#a5f3fc" stroke-width="4" opacity=".65"/></g>
       <path d="M260 141 H500 M260 309 H500" stroke="#60a5fa" stroke-dasharray="7 7" stroke-width="2" opacity=".85"/>
       <g fill="#dbeafe" font-size="17"><text x="505" y="145">HIGH 80%</text><text x="505" y="314">LOW 25%</text><text x="380" y="64" text-anchor="middle">TANK T-01</text></g>
       <circle cx="121" cy="219" r="36" id="tankPumpIn" fill="#334155" stroke="#94a3b8" stroke-width="5"/><text x="121" y="226" text-anchor="middle" fill="white" font-size="20">P1</text>
       <circle cx="639" cy="335" r="36" id="tankPumpOut" fill="#334155" stroke="#94a3b8" stroke-width="5"/><text x="639" y="342" text-anchor="middle" fill="white" font-size="20">P2</text>
       <g fill="#abc2d6" font-size="14" text-anchor="middle"><text x="121" y="279">Vulpomp</text><text x="639" y="396">Afvoerpomp</text></g>
       <text id="tankPercent" x="380" y="225" fill="#fff" font-size="42" font-weight="700" text-anchor="middle">35%</text>
       <text id="tankPressure" x="380" y="255" fill="#dbeafe" font-size="18" text-anchor="middle">88 kPa</text>
      </svg><div class="tank-metrics"><div>Niveau <strong id="tankLevelMetric">35.0%</strong></div><div>Druk (model) <strong id="tankPressureMetric">88.0 kPa</strong></div><div>Pomp P1 <strong id="tankInMetric">UIT</strong></div><div>Pomp P2 <strong id="tankOutMetric">UIT</strong></div></div><p class="tank-note">Didactisch vereenvoudigd model: de drukwaarde is een simulatieparameter en geen nauwkeurige hydraulische of thermodynamische berekening.</p></div>
      <aside class="tank-side"><div class="panel"><div class="overline">01 / VERBINDING</div><h3>PLC-verbinding</h3><div id="tankTarget" class="tank-target">—</div><div class="tank-actions"><button id="tankConnect" class="btn primary">● Verbinden</button><button id="tankDisconnect" class="btn ghost">Verbreken</button></div><p class="tank-note">Gebruikt het verbindingsprofiel dat op het hoofdmenu geselecteerd is. Eerst andere simulaties verbreken.</p></div>
      <div class="panel"><div class="overline">02 / BEDIENING</div><h3>Virtuele drukknoppen</h3><div class="tank-actions"><button id="tankStart" class="btn start">▶ START</button><button id="tankStop" class="btn stop">■ STOP</button></div><label id="tankCycleRow" class="tank-note" style="display:block;margin-top:12px"><input type="checkbox" id="tankCycle" /> DEMO: automatisch leegpompen tot 25% na bereiken van 80%</label><p class="tank-note">Standaard stopt de demo op 80%. Met de optie hierboven pendelt de demo tussen 25% en 80%. In LIVE bepaalt alleen de PLC de pompcommando’s.</p></div>
      <div class="panel"><div class="overline">03 / LIVE I/O</div><h3>Signalen</h3><div id="tankIo"></div><div id="tankDiag" class="tank-diagnostics"></div></div>
      <div id="tankError" class="custom-message" role="status">Klaar om te verbinden.</div></aside>
    </div>`);
 const footer=document.querySelector('.shell > footer');footer.parentNode.insertBefore(root,footer);
 $('openTank').onclick=open;$('tankBack').onclick=back;
 $('tankConnect').onclick=()=>call('tank_connect');$('tankDisconnect').onclick=()=>call('tank_disconnect');
 $('tankStart').onclick=()=>call('tank_press_start');$('tankStop').onclick=()=>call('tank_press_stop');
 $('tankCycle').onchange=()=>call('tank_set_demo_cycle',$('tankCycle').checked);
 setInterval(poll,120);
}
function open(){
 document.querySelectorAll('#homeScreen,#simulationWorkspace,#garageWorkspace,#customWorkspace').forEach(e=>{if(e)e.hidden=true;});
 $('tankWorkspace').hidden=false;active=true;document.title='PLC Simulation Lab — Drukvat';poll();
}
function back(){if(connected){$('tankError').textContent='Verbreek eerst de tankverbinding.';return;}
 active=false;$('tankWorkspace').hidden=true;if(typeof showScreen==='function')showScreen('home');else $('homeScreen').hidden=false;
}
async function call(method,...args){if(busy||!api())return;busy=true;try{render(await api()[method](...args));}catch(e){$('tankError').textContent='Fout: '+String(e);}finally{busy=false;updateButtons();}}
function updateButtons(){if(!$('tankConnect'))return; $('tankConnect').disabled=connected||busy;$('tankDisconnect').disabled=!connected||busy;$('tankStart').disabled=!connected||busy;$('tankStop').disabled=!connected||busy;}
function render(state){if(!state)return;last=state;connected=!!state.connected;
 const w=state.world||{},signals=state.signals||{},level=Math.max(0,Math.min(100,Number(w.level)||0));
 const y=383-level*3.03;
 $('tankLiquid').setAttribute('y',y);$('tankLiquid').setAttribute('height',383-y);
 $('tankWave').setAttribute('d',`M 262 ${y} Q 320 ${y-4} 380 ${y} T 498 ${y}`);
 $('tankPercent').textContent=Math.round(level)+'%';$('tankPressure').textContent=fmt(w.pressure)+' kPa';
 $('tankLevelMetric').textContent=fmt(level)+'%';$('tankPressureMetric').textContent=fmt(w.pressure)+' kPa';
 for(const [key,id] of [['pump_in','tankInMetric'],['pump_out','tankOutMetric']])$(id).textContent=signals[key]?'AAN':'UIT';
 $('tankPumpIn').setAttribute('fill',signals.pump_in?'#15803d':'#334155');
 $('tankPumpOut').setAttribute('fill',signals.pump_out?'#15803d':'#334155');
 $('tankMode').textContent=connected?(state.demo?'DEMO · '+(state.demo_cycle?'CYCLUS':'80% VASTHOUDEN'):'LIVE · ADS'):'NIET VERBONDEN';
 $('tankCycleRow').style.display=state.demo?'block':'none'; $('tankCycle').checked=!!state.demo_cycle;
 $('tankTarget').textContent=state.target||'—';
 const root=$('tankIo');root.replaceChildren();
 for(const [key,title] of Object.entries(names)){
   const row=component('div',{className:'tank-io-row'});
   const left=component('span');left.textContent=title;
   const value=component('strong');const missing=connected&&!state.demo&&state.diagnostics?.available?.[key]===false;
   value.textContent=missing?'ONTBREEKT':key==='pressure'?fmt(signals[key])+' kPa':signals[key]?'TRUE':'FALSE';
   if(signals[key]&&key!=='pressure')value.classList.add('active');row.append(left,value);root.append(row);
 }
 const diag=state.diagnostics||{};
 $('tankDiag').textContent=diag.missing?.length?'Ontbrekend: '+diag.missing.join(', '):'Alle verwachte PLC-symbolen beschikbaar of nog niet gecontroleerd.';
 $('tankError').textContent=state.error|| (state.pump_conflict?'Motorconflict: beide pompen actief; vloeistofbeweging geblokkeerd.':w.overflow?'Waarschuwing: tank heeft de maximumcapaciteit bereikt.':'Geen fouten gemeld.');
 updateButtons();
}
async function poll(){if(!active||refreshing||!api())return;refreshing=true;try{render(await api().tank_get_state());}catch(e){$('tankError').textContent='Statusfout: '+String(e);}finally{refreshing=false;}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
