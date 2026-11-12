'use strict';

const $ = (name) => document.getElementById(name);
const ioMeta = [
  ['start', 'bStartButton', 'IN'],
  ['stop', 'bStopButton', 'IN'],
  ['sensor_entry', 'bSensorEntry', 'IN'],
  ['sensor_exit', 'bSensorExit', 'IN'],
  ['reject_type', 'bRejectType', 'IN'],
  ['motor', 'bConveyorMotor', 'OUT'],
  ['diverter', 'bDiverter', 'OUT'],
];

let bridgeReady = false;
let state = null;
let lastError = '';
let pollingActive = false;
let commandInFlight = false;
let pollingTimer = null;
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

function render(data) {
  if (!data) return;
  state = data;
  const connected = !!data.connected;
  const inputs = data.inputs || {};
  const outputs = data.outputs || {};
  const world = data.world || {};
  const motor = connected && !!outputs.motor;
  const diverter = connected && !!outputs.diverter;
  $('connectionBadge').classList.toggle('connected', connected);
  $('connectionLabel').textContent = connected ? 'Verbonden' : 'Niet verbonden';
  $('targetValue').textContent = data.target || '—';
  $('protocolValue').textContent = data.demo ? 'OFFLINE · demo-PLC' : 'TwinCAT ADS / pyads';
  $('modeTag').textContent = data.demo ? 'DEMO · VOORBEELDLOGICA' : 'LIVE · ADS';
  $('modeTag').className = 'mode-tag ' + (data.demo ? 'demo' : 'live');
  $('conveyorStage').classList.toggle('running', motor);
  $('motorMiniText').textContent = motor ? 'MOTOR AAN' : 'MOTOR UIT';
  $('entryAssembly').classList.toggle('active', !!inputs.sensor_entry);
  $('exitAssembly').classList.toggle('active', !!inputs.sensor_exit);
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
    $('io-' + key).textContent = v ? 'TRUE' : 'FALSE';
    $('io-' + key).classList.toggle('on', v);
    $('led-' + key).classList.toggle('on', v);
  }
  for (const name of ['disconnectButton', 'startButton', 'stopButton', 'blueButton', 'orangeButton', 'resetButton']) {
    $(name).disabled = !connected || commandInFlight;
  }
  $('autoFeedToggle').disabled = !connected || commandInFlight;
  $('connectButton').disabled = connected || commandInFlight;
  $('footerStatus').textContent = connected
    ? (data.demo ? 'Offline voorbeeldbesturing actief · geen TwinCAT' : 'PLC-communicatie actief · echte TwinCAT-uitgangen')
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
      visuals.set(p.id, { element, shownX: p.x, x: p.x, lane: p.lane, at: now });
    }
    const visual = visuals.get(p.id);
    visual.x = p.x;
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
    const width = $('beltTrack').clientWidth;
    const running = !!(state.connected && state.outputs && state.outputs.motor);
    const speed = Number(state.world.speed || 0);
    for (const visual of visuals.values()) {
      const age = Math.min((timestamp - visual.at) / 1000, 0.13);
      const predicted = visual.x + (running ? age * speed : 0);
      const follow = Math.min(1, seconds * 23);
      visual.shownX += (predicted - visual.shownX) * follow;
      const left = (visual.shownX * width) - 24;
      const branchProgress = visual.lane === 'reject'
        ? Math.max(0, Math.min(1, (visual.shownX - 0.70) / 0.32)) : 0;
      // The parcel enters a lower branch after D-01; the model owns that lane.
      const down = branchProgress * 63;
      visual.element.style.transform = `translate3d(${left.toFixed(2)}px, ${down.toFixed(2)}px, 0)`;
    }
  }
  requestAnimationFrame(frame);
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
  } catch (error) {
    $('footerStatus').textContent = 'Status ophalen mislukt: ' + String(error);
  }
  pollingTimer = setTimeout(poll, 110);
}

function init() {
  buildIoRows();
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
    poll();
  }
  window.addEventListener('pywebviewready', onReady);
  if (window.pywebview && window.pywebview.api) onReady();
  // If opened in a normal browser, the GUI is only a static preview.
  setTimeout(() => {
    if (!bridgeReady) $('footerStatus').textContent = 'Open start_demo.cmd om de simulator te bedienen';
  }, 1700);
}

document.addEventListener('DOMContentLoaded', init);
