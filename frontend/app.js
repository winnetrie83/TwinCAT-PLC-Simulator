'use strict';

const $ = (name) => document.getElementById(name);
const ioMeta = [
  ['start', 'bStartButton', 'IN'],
  ['stop', 'bStopButton', 'IN'],
  ['sensor_entry', 'bSensorEntry', 'IN'],
  ['sensor_exit', 'bSensorExit', 'IN'],
  ['reject_type', 'bRejectType', 'IN'],
  ['sensor_reject', 'bSensorReject (LS-03)', 'IN'],
  ['motor', 'bConveyorMotor', 'OUT'],
  ['diverter', 'bDiverter', 'OUT'],
];

let bridgeReady = false;
let state = null;
let garageState = null;
let activeScreen = 'home';
let lastError = '';
let commandInFlight = false;
let lastFrame = 0;
const visuals = new Map();

function buildIoRows() {
  const root = $('ioRows');
  for (const [key, name, direction] of ioMeta) {
    const line = document.createElement('div');
    line.className = 'io-row';
    const lhs = document.createElement('div');
    lhs.className = 'io-name';
    const led = document.createElement('i');
    led.className = 'led';
    led.id = 'led-' + key;
    const label = document.createElement('span');
    label.textContent = name;
    lhs.append(led, label);
    const rhs = document.createElement('div');
    const dir = document.createElement('span');
    dir.className = 'dir';
    dir.textContent = direction + '  ';
    const val = document.createElement('code');
    val.id = 'io-' + key;
    val.textContent = 'FALSE';
    rhs.append(dir, val);
    line.append(lhs, rhs);
    root.append(line);
  }
}

function renderSymbolDiagnostics(id, data) {
  const node = $(id);
  if (!node) return;
  node.replaceChildren();
  if (!data.connected || data.demo || !data.symbol_diagnostics) return;
  const diag = data.symbol_diagnostics;
  const missing = diag.missing || [];
  const extras = diag.extras || [];
  const summary = document.createElement('div');
  summary.className = missing.length ? 'symbol-status warning' : 'symbol-status success';
  summary.textContent = missing.length
    ? `PLC verbonden · ${missing.length} verwachte variabele(n) ontbreken`
    : 'PLC verbonden · alle verwachte variabelen gevonden';
  node.append(summary);
  if (missing.length) {
    const list = document.createElement('div');
    list.className = 'symbol-list';
    list.textContent = 'Ontbrekend: ' + missing.join(', ');
    node.append(list);
  }
  if (diag.inventory_status === 'available') {
    const detail = document.createElement('details');
    const heading = document.createElement('summary');
    heading.textContent = `Extra onbekende MAIN-symbolen (${extras.length})`;
    detail.append(heading);
    const value = document.createElement('div');
    value.className = 'symbol-list';
    value.textContent = extras.length ? extras.join(', ') : 'Geen extra MAIN-symbolen gevonden.';
    detail.append(value);
    node.append(detail);
  } else {
    const note = document.createElement('div');
    note.className = 'symbol-list';
    note.textContent = 'Extra variabelen konden niet worden uitgelezen (symbolenoverzicht niet beschikbaar).';
    node.append(note);
  }
}

function render(data) {
  if (!data) return;
  state = data;
  renderSymbolDiagnostics('symbolDiagnostics', data);
  const connected = !!data.connected;
  const inputs = data.inputs || {};
  const outputs = data.outputs || {};
  const world = data.world || {};
  const motor = connected && !!outputs.motor;
  const diverter = connected && !!outputs.diverter;
  if(activeScreen !== 'garage') $('connectionBadge').classList.toggle('connected', connected);
  if(activeScreen !== 'garage') $('connectionLabel').textContent = connected ? 'Verbonden' : 'Niet verbonden';
  $('targetValue').textContent = data.target || '—';
  $('protocolValue').textContent = data.demo ? 'OFFLINE · demo-PLC' : 'TwinCAT ADS / pyads';
  $('modeTag').textContent = data.demo ? 'DEMO · VOORBEELDLOGICA' : 'LIVE · ADS';
  $('modeTag').className = 'mode-tag ' + (data.demo ? 'demo' : 'live');
  $('conveyorStage').classList.toggle('running', motor);
  $('motorMiniText').textContent = motor ? 'MOTOR AAN' : 'MOTOR UIT';
  $('entryAssembly').classList.toggle('active', !!inputs.sensor_entry);
  $('exitAssembly').classList.toggle('active', !!inputs.sensor_exit);
  $('rejectSensor').classList.toggle('active', !!inputs.sensor_reject);
  $('diverter').classList.toggle('active', diverter);
  $('motorValue').textContent = motor ? 'TRUE' : 'FALSE';
  $('diverterValue').textContent = diverter ? 'TRUE' : 'FALSE';
  $('motorValue').classList.toggle('on', motor);
  $('diverterValue').classList.toggle('on', diverter);
  $('cycleValue').textContent = connected ? Number(outputs.counter || 0).toLocaleString('nl-BE') : '—';
  $('normalCount').textContent = world.normal_count || 0;
  $('rejectCount').textContent = world.reject_count || 0;
  $('queueCount').textContent = world.queue_count || 0;
  $('autoFeedToggle').checked = !!world.auto_feed;
  for (const [key, , direction] of ioMeta) {
    const v = direction === 'IN' ? !!inputs[key] : !!outputs[key];
    const known = !connected || data.demo || !data.symbol_diagnostics || data.symbol_diagnostics.available[key] !== false;
    $('io-' + key).textContent = connected && !known ? 'ONTBREEKT' : (v ? 'TRUE' : 'FALSE');
    $('io-' + key).classList.toggle('on', v);
    $('led-' + key).classList.toggle('on', known && v);
  }
  for (const name of ['disconnectButton', 'startButton', 'stopButton', 'blueButton', 'orangeButton', 'resetButton']) {
    $(name).disabled = !connected || commandInFlight;
  }
  $('autoFeedToggle').disabled = !connected || commandInFlight;
  $('connectButton').disabled = connected || commandInFlight;
  if(activeScreen !== 'garage') $('footerStatus').textContent = connected
    ? (data.demo ? 'Offline voorbeeldbesturing actief · geen TwinCAT' : 'PLC-communicatie actief · TwinCAT-uitgangen')
    : 'Niet verbonden — klik op Verbinden';
  if (data.error) {
    lastError = data.error;
    $('errorMessage').textContent = data.error;
    $('errorMessage').hidden = false;
  } else if (lastError) {
    lastError = '';
    $('errorMessage').hidden = true;
  }
  updateVisuals(world.packages || []);
  if (!$('homeScreen').hidden) {
    const runningNow = connected && motor;
    $('homeRuntime').textContent = runningNow ? 'Let op: transportband draait nog — ga terug om STOP te drukken' : (connected ? 'Transportband verbonden met PLC' : 'Geen actieve verbinding');
    $('homeRuntime').classList.toggle('active', runningNow);
  }
}

function updateVisuals(packages) {
  const now = performance.now();
  const ids = new Set();
  for (const p of packages) {
    ids.add(p.id);
    if (!visuals.has(p.id)) {
      const element = document.createElement('div');
      element.className = 'parcel ' + (p.kind === 'reject' ? 'orange' : 'blue');
      $('packageLayer').appendChild(element);
      visuals.set(p.id, {element, shownX:p.x, shownY:p.y || 0,
                          x:p.x, y:p.y || 0, lane:p.lane, at:now});
    }
    const visual = visuals.get(p.id);
    if (p.lane === 'reject' && visual.lane !== 'reject') {
      $('rejectPackageLayer').appendChild(visual.element);
      visual.shownX = p.x;
      visual.shownY = 0;
    }
    visual.x = p.x;
    visual.y = p.y || 0;
    visual.lane = p.lane;
    visual.at = now;
  }
  for (const [id, visual] of visuals) {
    if (!ids.has(id)) {
      visual.element.remove();
      visuals.delete(id);
    }
  }
}

function frame(timestamp) {
  const seconds = Math.min((timestamp - (lastFrame || timestamp)) / 1000, 0.05);
  lastFrame = timestamp;
  if (state && state.world) {
    const stage = $('conveyorStage').getBoundingClientRect();
    const track = $('beltTrack').getBoundingClientRect();
    const branch = $('rejectConveyor').getBoundingClientRect();
    const mainCenterY = track.top - stage.top + track.height / 2;
    const branchCenterX = branch.left - stage.left + branch.width / 2;
    const verticalTravel = branch.bottom - stage.top - mainCenterY - 18;
    const running = !!(state.connected && state.outputs && state.outputs.motor);
    const mainSpeed = Number(state.world.speed || 0);
    const rejectSpeed = Number(state.world.reject_speed || 0);
    const sensor = $('rejectSensor');
    // The visual beam and physics sensor use the SAME normalized coordinate.
    sensor.style.left = (branchCenterX - 48) + 'px';
    sensor.style.top = (mainCenterY + verticalTravel * .62 - 8) + 'px';
    for (const visual of visuals.values()) {
      const age = Math.min((timestamp - visual.at) / 1000, 0.13);
      const follow = Math.min(1, seconds * 23);
      if (visual.lane === 'reject') {
        const predictedY = visual.y + (running ? age * rejectSpeed : 0);
        visual.shownY += (predictedY - visual.shownY) * follow;
        // Once diverted, the package travels STRAIGHT DOWN on a 90° belt.
        const left = branchCenterX - 24;
        const top = mainCenterY - 17 + visual.shownY * verticalTravel;
        visual.element.style.transform = `translate3d(${left.toFixed(2)}px, ${top.toFixed(2)}px, 0)`;
      } else {
        const predictedX = visual.x + (running ? age * mainSpeed : 0);
        visual.shownX += (predictedX - visual.shownX) * follow;
        const left = (visual.shownX * track.width) - 24;
        visual.element.style.transform = `translate3d(${left.toFixed(2)}px, 0px, 0)`;
      }
    }
  }
  requestAnimationFrame(frame);
}

const garageMeta = [
  ['button','bGateButton','IN'],
  ['limit_open','bGateLimitOpen','IN'],
  ['limit_closed','bGateLimitClosed','IN'],
  ['motor_open','bGateMotorOpen','OUT'],
  ['motor_close','bGateMotorClose','OUT'],
];

function buildGarageIoRows() {
  const root=$('garageIoRows');
  for (const [key,label,direction] of garageMeta) {
    const line=document.createElement('div'); line.className='io-row';
    const lhs=document.createElement('div'); lhs.className='io-name';
    const led=document.createElement('i'); led.className='led'; led.id='garage-led-'+key;
    const name=document.createElement('span'); name.textContent=label; lhs.append(led,name);
    const rhs=document.createElement('div');
    const dir=document.createElement('span'); dir.className='dir';dir.textContent=direction+'  ';
    const value=document.createElement('code');value.id='garage-io-'+key;value.textContent='FALSE';
    rhs.append(dir,value);line.append(lhs,rhs);root.append(line);
  }
}
function renderGarage(data) {
  if (!data) return;
  garageState=data;
  renderSymbolDiagnostics('garageSymbolDiagnostics', data);
  const inputs=data.inputs||{}, outputs=data.outputs||{}, connected=!!data.connected;
  const position=Math.max(0,Math.min(1,Number(data.position)||0));
  $('garageDoor').style.transform=`translateY(${-position*100}%)`;
  $('garagePosition').textContent=(position<=0?'GESLOTEN':position>=1?'OPEN':'IN BEWEGING / TUSSENSTAND')+' · '+Math.round(position*100)+'%';
  $('garageLimitOpen').classList.toggle('active',!!inputs.limit_open);
  $('garageLimitClosed').classList.toggle('active',!!inputs.limit_closed);
  $('garageModeTag').textContent=data.demo?'DEMO · VOORBEELDLOGICA':'LIVE · ADS';
  $('garageModeTag').className='mode-tag '+(data.demo?'demo':'live');
  $('gateOpenValue').textContent=!!outputs.motor_open?'TRUE':'FALSE';
  $('gateCloseValue').textContent=!!outputs.motor_close?'TRUE':'FALSE';
  $('gateOpenValue').classList.toggle('on',!!outputs.motor_open);
  $('gateCloseValue').classList.toggle('on',!!outputs.motor_close);
  $('gateCycleValue').textContent=connected?Number(outputs.counter||0).toLocaleString('nl-BE'):'—';
  $('garageTarget').textContent=data.target||'—';
  $('garageConnect').disabled=connected||commandInFlight;
  $('garageDisconnect').disabled=!connected||commandInFlight;
  $('garageButton').disabled=!connected||commandInFlight;
  $('garageFault').hidden=!data.conflict;
  const alert=$('garageError');alert.hidden=!data.error;alert.textContent=data.error||'';
  for (const [key,,direction] of garageMeta){
    const v=direction==='IN'?!!inputs[key]:!!outputs[key];
    const known=!connected||data.demo||!data.symbol_diagnostics||data.symbol_diagnostics.available[key]!==false;
    $('garage-io-'+key).textContent=connected&&!known?'ONTBREEKT':(v?'TRUE':'FALSE');
    $('garage-io-'+key).classList.toggle('on',v);
    $('garage-led-'+key).classList.toggle('on',known&&v);
  }
  if(activeScreen==='garage'){
    $('connectionBadge').classList.toggle('connected',connected);
    $('connectionLabel').textContent=connected?'Garage verbonden':'Niet verbonden';
    $('footerStatus').textContent=connected?'Garagepoort · '+(data.demo?'demo':'LIVE ADS'):'Garagepoort niet verbonden';
  }
}
async function issueGarage(method) {
  if (!bridgeReady || commandInFlight) return;
  commandInFlight=true;
  try {renderGarage(await window.pywebview.api[method]());}
  catch(e){$('garageError').textContent=String(e);$('garageError').hidden=false;}
  finally {commandInFlight=false;if(garageState) renderGarage(garageState);}
}

async function issue(method, ...args) {
  if (!bridgeReady || commandInFlight) return;
  commandInFlight = true;
  try {
    const response = await window.pywebview.api[method](...args);
    render(response);
  } catch (error) {
    $('errorMessage').textContent = 'Desktopcommunicatie mislukt: ' + String(error);
    $('errorMessage').hidden = false;
  } finally {
    commandInFlight = false;
    if (state) render(state);
  }
}

async function poll() {
  if (!bridgeReady) return;
  try {
    const newState = await window.pywebview.api.get_state();
    render(newState);
    renderGarage(await window.pywebview.api.garage_get_state());
  } catch (error) {
    $('footerStatus').textContent = 'Status ophalen mislukt: ' + String(error);
  }
  setTimeout(poll, 110);
}

function showScreen(name) {
  activeScreen=name;
  $('homeScreen').hidden=name!=='home';
  $('simulationWorkspace').hidden=name!=='conveyor';
  $('garageWorkspace').hidden=name!=='garage';
  const conveyorRunning=!!(state&&state.connected&&state.outputs&&state.outputs.motor);
  const garageRunning=!!(garageState&&garageState.connected&&garageState.outputs&&
                       (garageState.outputs.motor_open||garageState.outputs.motor_close));
  const running=conveyorRunning||garageRunning;
  $('homeRuntime').textContent=running
    ? 'Let op: '+(conveyorRunning?'transportband':'garagepoort')+' is actief — stop de beweging voor het wisselen'
    : (state&&state.connected?'Transportband verbonden':garageState&&garageState.connected?'Garagepoort verbonden':'Geen actieve verbinding');
  $('homeRuntime').classList.toggle('active',running);
  document.title='PLC Simulation Lab — '+(name==='home'?'Simulaties':name==='garage'?'Garagepoort':'Transportband');
  if(name==='garage'&&garageState) renderGarage(garageState);
  if(name==='conveyor'&&state) render(state);
}

function init() {
  initProfiles();
  buildIoRows();
  buildGarageIoRows();
  $('openGarage').onclick=()=>showScreen('garage');
  $('garageBackHome').onclick=()=>showScreen('home');
  $('garageConnect').onclick=()=>issueGarage('garage_connect');
  $('garageDisconnect').onclick=()=>issueGarage('garage_disconnect');
  $('garageButton').onclick=()=>issueGarage('garage_press_button');
  $('openConveyor').onclick = () => showScreen('conveyor');
  $('backHome').onclick = () => showScreen('home');
  showScreen('home');
  $('connectButton').onclick = () => issue('connect');
  $('disconnectButton').onclick = () => issue('disconnect');
  $('startButton').onclick = () => issue('press_start');
  $('stopButton').onclick = () => issue('press_stop');
  $('blueButton').onclick = () => issue('add_package', 'standard');
  $('orangeButton').onclick = () => issue('add_package', 'reject');
  $('resetButton').onclick = () => issue('reset_scene');
  $('autoFeedToggle').onchange = (event) => issue('set_auto_feed', !!event.target.checked);
  requestAnimationFrame(frame);
  function onReady() {
    if (bridgeReady) return;
    bridgeReady = true;
    $('footerStatus').textContent = 'Desktopbridge klaar · klik op Verbinden';
    window.pywebview.api.get_profiles().then(refreshProfiles).catch(e=>window.alert('Profielen laden mislukt: '+String(e)));
    poll();
  }
  window.addEventListener('pywebviewready', onReady);
  if (window.pywebview && window.pywebview.api) onReady();
  setTimeout(() => {
    if (!bridgeReady) $('footerStatus').textContent = 'Open start_demo.cmd om de simulator te bedienen';
  }, 1700);
}

document.addEventListener('DOMContentLoaded', init);

// Connection profiles are shared by conveyor and garage, and persisted by Python.
let profileData = null;
let editingProfileId = null;
const profileSelectors = ['homeProfileSelect', 'profileSelect', 'garageProfileSelect'];

function setProfileError(message) {
  $('profileError').hidden = !message;
  $('profileError').textContent = message || '';
}
function profileIsConnected() {
  return !!((state && state.connected) || (garageState && garageState.connected));
}
function refreshProfiles(data) {
  profileData = data;
  const selected = data.profiles.find(p => p.id === data.selected_id);
  for (const id of profileSelectors) {
    const select = $(id);
    select.replaceChildren();
    for (const p of data.profiles) {
      const option = document.createElement('option');
      option.value = p.id;
      option.textContent = `${p.name}  (${p.ams_net_id}:${p.ads_port})`;
      select.appendChild(option);
    }
    select.value = data.selected_id;
  }
  if(selected) {
    // This is the selected next target, even before a connection is established.
    if(!state || !state.connected) $('targetValue').textContent = `${selected.ams_net_id}:${selected.ads_port}`;
    if(!garageState || !garageState.connected) $('garageTarget').textContent = `${selected.ams_net_id}:${selected.ads_port}`;
  }
  const list = $('profileEditorList');
  list.replaceChildren();
  for (const p of data.profiles) {
    const option = document.createElement('option');
    option.value = p.id;
    option.textContent = p.name + ' · ' + p.ads_port;
    list.appendChild(option);
  }
  if(editingProfileId && data.profiles.some(p=>p.id===editingProfileId)) list.value=editingProfileId;
  else if (editingProfileId !== null) editingProfileId = data.selected_id;
  if (editingProfileId) {
    list.value=editingProfileId;
    editProfile(editingProfileId);
  }
}
function editProfile(id) {
  const profile = profileData && profileData.profiles.find(p=>p.id===id);
  editingProfileId = profile ? id : null;
  $('profileEditorList').value = editingProfileId || '';
  $('profileName').value = profile ? profile.name : '';
  $('profileNetId').value = profile ? profile.ams_net_id : '';
  $('profilePort').value = profile ? String(profile.ads_port) : '851';
  $('profileDelete').disabled = !profile || profileData.profiles.length===1;
}
async function selectProfile(id) {
  if(!profileData || id === profileData.selected_id) return;
  if(profileIsConnected()) {
    refreshProfiles(profileData);
    window.alert('Verbreek eerst de actieve PLC-verbinding om van profiel te wisselen.');
    return;
  }
  try {
    refreshProfiles(await window.pywebview.api.select_profile(id));
    // Refresh state snapshots so their target labels agree immediately.
    render(await window.pywebview.api.get_state());
    renderGarage(await window.pywebview.api.garage_get_state());
  } catch(e) {
    refreshProfiles(profileData);
    window.alert('Profiel wisselen mislukt: ' + String(e));
  }
}
function openProfileEditor() {
  if(!profileData) return;
  $('profileModal').hidden=false;
  setProfileError('');
  editProfile(profileData.selected_id);
}
function closeProfileEditor(){ $('profileModal').hidden=true; setProfileError(''); }
function initProfiles() {
  for (const id of profileSelectors) $(id).addEventListener('change',e=>selectProfile(e.target.value));
  for (const id of ['homeProfileEdit','profileEdit','garageProfileEdit']) $(id).addEventListener('click',openProfileEditor);
  $('profileClose').onclick=closeProfileEditor;
  $('profileModal').addEventListener('click',event=>{ if(event.target===$('profileModal')) closeProfileEditor(); });
  $('profileEditorList').onchange=event=>editProfile(event.target.value);
  $('profileNew').onclick=()=>{editProfile(null);setProfileError('');$('profileName').focus();};
  $('profileForm').onsubmit=async event=>{
    event.preventDefault();
    if (profileIsConnected()) {setProfileError('Verbreek eerst de actieve PLC-verbinding.');return;}
    try {
      const data=await window.pywebview.api.save_profile(editingProfileId,$('profileName').value,
        $('profileNetId').value,Number($('profilePort').value));
      editingProfileId = editingProfileId || data.selected_id;
      refreshProfiles(data);
      render(await window.pywebview.api.get_state());
      renderGarage(await window.pywebview.api.garage_get_state());
      setProfileError('');
    } catch(e) {setProfileError(String(e));}
  };
  $('profileDelete').onclick=async()=>{
    if(!editingProfileId) return;
    if(profileIsConnected()){setProfileError('Verbreek eerst de actieve PLC-verbinding.');return;}
    if(!window.confirm('Dit verbindingsprofiel definitief verwijderen?')) return;
    try {
      const data=await window.pywebview.api.delete_profile(editingProfileId);
      editingProfileId=data.selected_id;
      refreshProfiles(data);
      render(await window.pywebview.api.get_state());
      renderGarage(await window.pywebview.api.garage_get_state());
      setProfileError('');
    } catch(e){setProfileError(String(e));}
  };
}
