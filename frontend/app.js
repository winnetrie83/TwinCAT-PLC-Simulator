'use strict';

const $ = (id) => document.getElementById(id);
let ready = false;
let polling = false;
let busy = false;
let lastError = '';

function boolText(value) { return value ? 'TRUE' : 'FALSE'; }

function mark(id, active) {
  $(id).classList.toggle('on', !!active);
}

function render(state) {
  if (!state || !state.values) return;
  const v = state.values;
  const connected = !!state.connected;
  $('connectionBadge').classList.toggle('connected', connected);
  $('connectionLabel').textContent = connected ? 'Verbonden' : 'Niet verbonden';
  $('communicationValue').textContent = state.demo ? 'DEMO · offline model' : 'ADS · pyads';
  $('modeTag').textContent = state.demo ? 'DEMONSTRATIE' : 'LIVE ADS';
  $('targetValue').textContent = state.demo ? 'Geen PLC nodig' : state.target;
  $('footerStatus').textContent = connected ? (state.demo ? 'Offline demonstratie actief' : 'TwinCAT PLC verbonden') : 'Nog niet verbonden';
  $('motorValue').textContent = boolText(v.motor);
  $('sensorValue').textContent = boolText(v.sensor);
  $('cycleValue').textContent = connected ? Number(v.counter).toLocaleString('nl-BE') : '—';
  $('startValue').textContent = boolText(v.start);
  $('stopValue').textContent = boolText(v.stop);
  $('sensorSmallValue').textContent = boolText(v.sensor);
  $('motorSmallValue').textContent = boolText(v.motor);
  ['motorValue', 'sensorValue'].forEach((id) => mark(id, id === 'motorValue' ? v.motor : v.sensor));
  [['startLed', 'startValue', v.start], ['stopLed', 'stopValue', v.stop],
   ['sensorLed', 'sensorSmallValue', v.sensor], ['motorLed', 'motorSmallValue', v.motor]]
   .forEach(([led, code, value]) => { mark(led, value); mark(code, value); });
  $('conveyorScene').classList.toggle('running', connected && !!v.motor);
  $('conveyorScene').classList.toggle('sensor-active', connected && !!v.sensor);
  if (document.activeElement !== $('sensorToggle')) $('sensorToggle').checked = !!v.sensor;
  $('connectButton').disabled = busy || !ready || connected;
  $('disconnectButton').disabled = busy || !ready || !connected;
  $('startButton').disabled = busy || !ready || !connected;
  $('stopButton').disabled = busy || !ready || !connected;
  $('sensorToggle').disabled = busy || !ready || !connected;
  const error = state.error || '';
  if (error) {
    $('alert').hidden = false;
    $('alert').textContent = error;
    lastError = error;
  } else if (lastError) {
    $('alert').hidden = true;
    lastError = '';
  }
}

async function callApi(method, ...args) {
  if (!ready || busy) return;
  busy = true;
  try {
    const result = await window.pywebview.api[method](...args);
    render(result);
  } catch (err) {
    $('alert').hidden = false;
    $('alert').textContent = 'Applicatiefout: ' + String(err);
  } finally {
    busy = false;
    if (ready) refresh();
  }
}

async function refresh() {
  if (!ready || polling || busy) return;
  polling = true;
  try {
    const result = await window.pywebview.api.get_state();
    render(result);
  } catch (err) {
    $('footerStatus').textContent = 'Communicatiefout in interface';
  } finally {
    polling = false;
  }
}

$('connectButton').addEventListener('click', () => callApi('connect'));
$('disconnectButton').addEventListener('click', () => callApi('disconnect'));
$('startButton').addEventListener('click', () => callApi('press_start'));
$('stopButton').addEventListener('click', () => callApi('press_stop'));
$('sensorToggle').addEventListener('change', (event) => callApi('set_sensor', event.target.checked));

window.addEventListener('pywebviewready', () => {
  ready = true;
  $('footerStatus').textContent = 'Interface beschikbaar';
  refresh();
  window.setInterval(refresh, 350);
});
