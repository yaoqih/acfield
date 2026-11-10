import { $, fmt } from './view-utils.js';
import { api } from './api.js';
import { toast } from './workspace.js';

const cameraControls = ['brightness', 'contrast', 'saturation', 'exposure', 'gain'];
const cameraNames = {brightness: '亮度', contrast: '对比度', saturation: '饱和度', exposure: '曝光', gain: '增益'};
const forms = new Map();
let state = {};
let familiesKey = '';
let deviceBusy = false;

function values(form) {
  return Object.fromEntries([...form.querySelectorAll('input, select')].map(field => [field.id, field.value]));
}

function dirty(group) {
  return Object.entries(values(group.form)).some(([id, value]) =>
    id in group.baseline ? value !== group.baseline[id] : group.touched.has(id));
}

function feedback(group) {
  const changed = dirty(group);
  group.form.dataset.dirty = String(changed);
  const status = group.form.querySelector('.form-status');
  status.textContent = group.error || (group.busy ? '正在提交，等待执行结果…'
    : group.loading ? (changed ? '有未应用的修改 · 正在读取当前参数…' : '正在读取当前参数…')
    : changed ? '有未应用的修改' : '与当前设置一致');
  status.className = 'form-status ' + (group.error ? 'error' : changed ? 'dirty' : '');
  group.form.querySelector('[data-reset]').hidden = !changed || group.loadError;
  group.form.querySelector('[data-reset]').disabled = group.busy || group.loading;
  group.form.querySelector('[data-retry]').hidden = !group.loadError;
  group.form.querySelector('button[type="submit"]').disabled = group.busy || group.loading || group.loadError;
  group.form.setAttribute('aria-busy', String(group.busy || group.loading));
}

function hydrate(group, entries) {
  for (const [id, raw] of Object.entries(entries)) {
    const field = $(id);
    const value = String(raw ?? '');
    const edited = id in group.baseline ? field.value !== group.baseline[id] : group.touched.has(id);
    if (field.tagName === 'SELECT' && ![...field.options].some(option => option.value === value)) {
      field.add(new Option(value, value));
    }
    group.baseline[id] = value;
    if (!edited) field.value = value;
  }
  feedback(group);
}

function createForm(name, submit) {
  const form = $(name + '-form');
  const group = {form, baseline: {}, touched: new Set(), loading: true, busy: false, error: '', loadError: false};
  forms.set(name, group);
  form.insertAdjacentHTML('beforeend', `<div class="form-feedback"><span class="form-status" role="status"></span><button type="button" class="text-button" data-reset hidden>恢复当前设置</button><button type="button" class="text-button" data-retry hidden>重新读取</button></div>`);
  for (const event of ['input', 'change']) form.addEventListener(event, ({target}) => {
    if (!target.matches('input, select')) return;
    group.touched.add(target.id);
    group.error = group.loadError ? group.error : '';
    feedback(group);
  });
  form.querySelector('[data-reset]').addEventListener('click', () => {
    for (const [id, value] of Object.entries(group.baseline)) $(id).value = value;
    group.touched.clear();
    group.error = '';
    feedback(group);
    form.querySelector('input, select').focus({preventScroll: true});
  });
  form.querySelector('[data-retry]').addEventListener('click', () => name === 'preview' ? loadPreview() : loadConfig());
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (group.busy || group.loading) return;
    if (name !== 'preview' && deviceBusy) {
      group.error = '请等待当前设备操作完成，再应用其他设备设置';
      feedback(group);
      return;
    }
    if (name !== 'preview') deviceBusy = true;
    group.busy = true;
    group.error = '';
    const snapshot = values(form);
    const fields = [...form.querySelectorAll('input, select')];
    fields.forEach(field => { field.disabled = true; });
    const button = form.querySelector('button[type="submit"]');
    button.setAttribute('aria-busy', 'true');
    feedback(group);
    try {
      const applied = await submit(snapshot);
      hydrate(group, applied || snapshot);
      group.touched.clear();
      // Submitted fields were locked; the server-confirmed values are the new baseline.
      for (const [id, value] of Object.entries(applied || snapshot)) $(id).value = String(value);
      toast('设置已应用');
    } catch (error) {
      group.error = error.message;
      toast(error.message, true);
    } finally {
      if (name !== 'preview') deviceBusy = false;
      group.busy = false;
      fields.forEach(field => { field.disabled = false; });
      button.removeAttribute('aria-busy');
      feedback(group);
    }
  });
  feedback(group);
}

// /api/control only queues work. Confirm source/detector changes using new worker events.
let pendingControl;
async function control(action, payload, matches) {
  const known = new Set((state.events || []).map(event => event.time + event.text));
  let timer;
  const completed = new Promise((resolve, reject) => {
    pendingControl = {known, matches, resolve, reject};
    timer = setTimeout(() => reject(Error('操作已提交但尚未确认，请在实验事件中查看结果后重试')), 10000);
  });
  // Attach a rejection handler immediately, including while the POST is pending.
  completed.catch(() => {});
  try {
    await api('/api/control', {action, ...payload});
    await completed;
  } finally {
    clearTimeout(timer);
    pendingControl = null;
  }
}

async function readSettings(names, load) {
  names.forEach(name => {
    Object.assign(forms.get(name), {loading: true, error: '', loadError: false});
    feedback(forms.get(name));
  });
  try { await load(); }
  catch (error) {
    names.forEach(name => Object.assign(forms.get(name), {error: '无法读取设置：' + error.message, loadError: true}));
  } finally {
    names.forEach(name => {
      forms.get(name).loading = false;
      feedback(forms.get(name));
    });
  }
}

function loadConfig() {
  return readSettings(['source', 'camera', 'detector'], async () => {
    const {config, state: snapshot} = await api('/api/config');
    hydrate(forms.get('camera'), {
      ...Object.fromEntries(['width', 'height', 'fps'].map(key => ['camera-' + key, config[key]])),
      ...Object.fromEntries(cameraControls.map(key => ['camera-' + key, config.camera_controls?.[key] ?? ''])),
    });
    // A newer poll can arrive before this slower request finishes.
    const active = state.source ? state : snapshot || {};
    hydrate(forms.get('source'), {source: active.source || config.source});
    hydrate(forms.get('detector'), {family: active.family || config.family, decimate: active.decimate ?? config.decimate});
  });
}

function loadPreview() {
  return readSettings(['preview'], async () => {
    const preview = await api('/api/preview');
    hydrate(forms.get('preview'), {'preview-width': preview.width, 'preview-fps': preview.fps});
  });
}

export function initSettings() {
  createForm('source', async fields => {
    await control('source', {source: fields.source}, s => s.source === fields.source
      && (s.events || []).some(event => event.text.startsWith('已连接')));
  });
  createForm('detector', async fields => {
    const payload = {family: fields.family, decimate: Number(fields.decimate)};
    await control('detector', payload, s => s.family === payload.family && s.decimate === payload.decimate
      && (s.events || []).some(event => event.text.startsWith('检测器：')));
  });
  createForm('preview', async fields => {
    const preview = await api('/api/preview', {width: Number(fields['preview-width']), fps: Number(fields['preview-fps'])});
    return {'preview-width': preview.width, 'preview-fps': preview.fps};
  });
  createForm('camera', async fields => {
    const {config, state: active} = await api('/api/config');
    if (!/^\d+$/.test(active.source) || active.source_kind !== 'camera') {
      throw Error('请先在“输入源”中连接实物相机，再应用采集设置');
    }
    Object.assign(config, {
      source: active.source, enabled: true,
      width: Number(fields['camera-width']), height: Number(fields['camera-height']),
      fps: Number(fields['camera-fps']), camera_controls: {},
    });
    for (const key of cameraControls) {
      if (fields['camera-' + key] !== '') config.camera_controls[key] = Number(fields['camera-' + key]);
    }
    await api('/api/config', config);
  });
  // Preview is independent of device configuration, including loading and retry.
  loadConfig();
  loadPreview();
}

export function updateSettings(snapshot) {
  state = snapshot;
  if (!forms.size) return;
  if (pendingControl) {
    const fresh = (state.events || []).filter(event => !pendingControl.known.has(event.time + event.text));
    if (fresh.some(event => event.level === 'error')) pendingControl.reject(Error(fresh.find(event => event.level === 'error').text));
    else if (fresh.length && pendingControl.matches({...state, events: fresh})) pendingControl.resolve();
  }
  if (state.source && state.source !== 'disconnected') hydrate(forms.get('source'), {source: state.source});
  if (state.family && state.decimate != null) hydrate(forms.get('detector'), {family: state.family, decimate: state.decimate});
  const key = (state.families || []).join(',');
  if (key && key !== familiesKey) {
    familiesKey = key;
    const selected = $('family').value;
    $('family').replaceChildren(...state.families.map(value => new Option(value, value)));
    if (![...$('family').options].some(option => option.value === selected)) $('family').add(new Option(selected, selected));
    $('family').value = selected;
  }
  $('camera-target').textContent = state.source_kind === 'camera' ? `当前相机：${state.source}` : '当前未连接实物相机，请先配置输入源。';
  if (state.camera_control_results) {
    const results = Object.entries(state.camera_control_results);
    $('camera-result').textContent = results.length ? results.map(([key, value]) =>
      `${cameraNames[key] || key}: ${value.accepted ? '驱动接受' + (value.actual != null ? '（读回 ' + fmt(value.actual, 2) + '）' : '') : '不支持或被拒绝'}`).join(' · ') : '未指定图像参数';
  }
}
