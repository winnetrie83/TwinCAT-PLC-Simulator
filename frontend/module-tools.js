/* PLC Simulation Lab v1.1 — fixed-exercise I/O mapping and behavioural test panel. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const api=()=>window.pywebview?.api;
const MODULES={conveyor:'Transportband',garage:'Garagepoort',tank:'Drukvat'};
const LABELS={start:'Start',stop:'Stop',sensor_entry:'Ingangssensor',sensor_exit:'Uitgangssensor',reject_type:'Afkeurtype',sensor_reject:'Afvoersensor',motor:'Transportmotor',diverter:'Diverter',counter:'Cycluscounter',button:'Drukknop',limit_open:'Eindschakelaar open',limit_closed:'Eindschakelaar gesloten',motor_open:'Motor openen',motor_close:'Motor sluiten',level_low:'Niveausensor laag',level_high:'Niveausensor hoog',pressure_high:'Drukalarm',pressure:'Drukwaarde (REAL)',pump_in:'Vulpomp',pump_out:'Afvoerpomp'};
let mapping=null,busy=false,lastResults='',testPoll=null;
function el(tag,cls,text){let e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
function note(message,error=false){const e=$('moduleToolInfo');e.textContent=message;e.classList.toggle('error',error);}
function visible(v){$('moduleToolOverlay').hidden=!v;}
function form(){let mod=$('moduleToolModule').value,fields=mapping.mappings[mod],root=$('moduleToolFields');root.replaceChildren();
 for(const [key,value] of Object.entries(fields)){
  let label=el('label','module-tool-field');let text=el('span','',LABELS[key]||key);let input=el('input');input.value=value;input.dataset.key=key;input.maxLength=160;input.spellcheck=false;input.autocomplete='off';label.append(text,input);root.append(label);
 }
 note('De I/O-namen worden buiten de projectmap opgeslagen. Verbreek eerst de actieve simulatie om te wijzigen.');
}
async function load(){mapping=await api().io_mapping_get();form();}
async function save(reset=false){if(busy)return;busy=true;try{const mod=$('moduleToolModule').value;
 const data=Object.fromEntries(Array.from($('moduleToolFields').querySelectorAll('input')).map(e=>[e.dataset.key,e.value.trim()]));
 mapping=reset?await api().io_mapping_reset(mod):await api().io_mapping_save(mod,data);
 form();note(reset?'Standaard I/O-symbolen hersteld.':'I/O-mapping opgeslagen.');
 }catch(e){note(String(e),true);}finally{busy=false;}}
function renderResults(status){const root=$('moduleToolResults');root.replaceChildren();
 let summary=el('p','',status.message||'');root.append(summary);
 for(const item of status.results||[]){let row=el('div','module-tool-result');let sign=el('strong',item.passed?'pass':'fail',item.passed?'✓':'✕');let text=el('div');text.append(el('b','',item.name),el('small','',item.details));row.append(sign,text);root.append(row);}
 $('moduleToolRun').disabled=!!status.running;
}
async function testRefresh(){if(!api())return;try{const status=await api().exercise_test_status();renderResults(status);if(!status.running&&testPoll){clearInterval(testPoll);testPoll=null;}}catch(e){note('Teststatus: '+e,true);}}
async function run(){if(busy)return;const mod=$('moduleToolModule').value;if(!window.confirm(`Deze test bedient virtuele drukknoppen voor ${MODULES[mod]} en kan de installatie laten bewegen. Gebruik uitsluitend een lokale didactische TwinCAT-runtime, nooit fysieke productieapparatuur. Doorgaan?`))return;
 busy=true;try{const status=await api().exercise_test_start(mod);renderResults(status);if(testPoll)clearInterval(testPoll);testPoll=setInterval(testRefresh,350);note('Test loopt. Schakel niet van simulatie of ADS-profiel tijdens de test.');}catch(e){note(String(e),true);}finally{busy=false;}}
function setup(){if($('moduleToolOverlay'))return;
 const home=document.querySelector('#homeScreen .home-footer')||$('homeScreen');
 const btn=el('button','btn ghost module-tool-launch','⚙ PLC I/O-mapping & oefeningtests');btn.id='moduleToolOpen';home.parentNode.insertBefore(btn,home);
 const overlay=el('div','module-tool-overlay');overlay.id='moduleToolOverlay';overlay.hidden=true;
 const panel=el('section','module-tool-panel');panel.innerHTML=`<header><div><div class="overline">PLC SIMULATION LAB / v1.1</div><h2>I/O-mapping & oefeningtests</h2><p>Configureer je symbolen en controleer het gedrag van je eigen TwinCAT-programma.</p></div><button class="btn ghost" id="moduleToolClose">Sluiten</button></header>
 <label class="module-tool-pick">Simulatie <select id="moduleToolModule"><option value="conveyor">Transportband</option><option value="garage">Garagepoort</option><option value="tank">Drukvat & pompen</option></select></label>
 <div class="module-tool-columns"><div><h3>PLC I/O-symbolen</h3><div id="moduleToolFields" class="module-tool-fields"></div><div class="module-tool-actions"><button class="btn primary" id="moduleToolSave">Mapping opslaan</button><button class="btn ghost" id="moduleToolReset">Standaard herstellen</button></div></div>
 <div><h3>Automatische PLC-gedragstest</h3><p>Open de gekozen oefening, maak verbinding met DEMO of een lokale TwinCAT-runtime, en start daarna de test. De simulator bedient de virtuele knoppen en controleert de waarneembare PLC-uitgangen.</p><button class="btn primary" id="moduleToolRun">Testscenario starten</button><div id="moduleToolResults" class="module-tool-results">Nog geen scenario uitgevoerd.</div><p class="module-tool-warning">Geen veiligheidsvalidatie of beoordeling van de broncode. Tests zijn afhankelijk van het beginpunt en de beschikbare PLC-symbolen.</p></div></div>
 <div id="moduleToolInfo" class="module-tool-info" role="status"></div>`;
 overlay.append(panel);document.body.append(overlay);
 btn.onclick=async()=>{visible(true);try{await load();await testRefresh();}catch(e){note('I/O-mapping laden mislukt: '+e,true);}};
 $('moduleToolClose').onclick=()=>visible(false);
 overlay.onclick=e=>{if(e.target===overlay)visible(false);};
 $('moduleToolModule').onchange=form;
 $('moduleToolSave').onclick=()=>save(false);
 $('moduleToolReset').onclick=()=>{if(window.confirm('Standaard mapping voor deze oefening herstellen?'))save(true);};
 $('moduleToolRun').onclick=run;
 const chip=document.querySelector('.topright .vchip');if(chip)chip.textContent='BETA 1.1';
 const foot=document.querySelector('.shell > footer span');if(foot)foot.textContent='PLC SIMULATION LAB · BETA 1.1';
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup);else setup();
})();
