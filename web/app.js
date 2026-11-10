import { $, esc, fmt } from './view-utils.js';
import { api, healthy, pollState } from './api.js';
import { confirmAction, currentView, initWorkspace, runAction, toast } from './workspace.js';
import { initSettings, updateSettings } from './settings.js';
import { initTags, renderTags, selectedTag } from './tags.js';
import { renderObserve } from './observe.js';

let state;
let lastEvent = '';

async function control(action) {
  await api('/api/control', {action});
  toast('操作已提交，执行结果见实验事件');
}

$('record').addEventListener('click', () => runAction($('record'), async () => {
  const wasRecording = !!state?.recording;
  await api('/api/control', {action: 'record'});
  // Keep the toggle busy until polling observes the worker's result.
  const deadline = Date.now() + 5000;
  while (!!state?.recording === wasRecording && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (!!state?.recording !== wasRecording) toast(wasRecording ? '记录已结束' : '开始记录逐帧数据');
  else toast('记录操作已提交，请在实验事件中确认结果');
}));
$('calibrate-world').addEventListener('click', () => runAction($('calibrate-world'), async () => {
  await api('/api/operations', {action: 'calibrate'});
  toast('场地外参已锁定');
}));
for (const [id, action, title, description, label] of [
  ['reset-world', 'reset_world', '清除场地标定？', '将清除已保存的场地外参、轨迹和累计统计，恢复像素观测。之后需要重新锁定四角外参。', '确认清除标定'],
  ['clear-tracks', 'clear_tracks', '清空轨迹统计？', '将清空所有标签的运动轨迹、跟踪时长和可见率统计，随后从新帧重新累计。', '确认清空轨迹'],
]) {
  $(id).addEventListener('click', async () => {
    if (await confirmAction(title, description, label)) {
      runAction($(id), () => action === 'reset_world'
        ? api('/api/operations', {action}).then(() => toast('场地标定已清除'))
        : control(action));
    }
  });
}

function renderDiagnostics(snapshot, live) {
  const warnings = snapshot.warnings || [];
  const summary = snapshot.error || (!live ? '等待新画面，请检查输入源。'
    : snapshot.demo ? '合成演示运行中 · 数据仅用于验证流程'
    : !snapshot.calibrated ? '正在使用像素坐标 · 完成相机标定可查看三维位置'
    : !snapshot.world_calibrated ? '相机已标定 · 锁定场地外参后可查看米制位置与速度'
    : warnings.length ? `定位运行中 · 有 ${warnings.length} 项诊断提示` : '定位正常 · 场地坐标已就绪');
  if ($('notice').textContent !== summary) $('notice').textContent = summary;
  $('diagnostics').className = 'notice ' + (!live ? 'error' : warnings.length && !snapshot.demo ? 'warning' : '');
  const items = [...(snapshot.error ? [snapshot.error] : []), ...warnings];
  const markup = items.map(text => `<li>${esc(text)}</li>`).join('');
  if ($('diagnostic-list').innerHTML !== markup) $('diagnostic-list').innerHTML = markup;
  $('diagnostic-details').hidden = !items.length;
  $('diagnostic-count').textContent = items.length;
  const action = $('diagnostic-action');
  action.hidden = live && (snapshot.demo || snapshot.world_calibrated);
  action.href = live ? '/calibration' : '#source-settings';
  action.textContent = live ? '前往标定 →' : '检查输入源 →';
}

function renderWorkspace() {
  if (!state) return;
  renderTags(state);
  if (currentView() === 'observe') renderObserve(state, healthy(state), selectedTag());
}

function render(s) {
  const live = healthy(s);
  state = s;
  $('clock').textContent = new Date().toLocaleTimeString('zh-CN', {hour12: false});
  $('connection').textContent = live ? (s.demo ? '演示运行中' : '实时连接中') : s.status === 'offline' ? '服务已断开' : '等待输入源';
  $('connection').className = 'pill ' + (live ? 'good' : 'bad');
  $('settings-source-status').textContent = live ? (s.demo ? '合成演示' : `相机 ${s.source}`) : '未就绪';
  $('settings-source-status').className = 'pill ' + (live ? 'good' : 'warn');
  $('fps').textContent = live ? fmt(s.fps) : '0.0';
  $('visible').textContent = live ? (s.visible_count ?? 0) : 0;
  $('fleet-count').textContent = `已配置 ${s.known_count ?? Object.keys(s.configured_tags || {}).length} 个身份`;
  $('detect-time').textContent = fmt(s.detection_ms);
  $('frame-age').textContent = fmt(s.frame_age_ms ?? s.state_age_ms, 0);
  $('resolution').textContent = s.width ? `${s.width} × ${s.height}` : '—';
  $('image-quality').textContent = `亮度 ${fmt(s.mean_brightness, 0)} / 255 · 清晰度 ${fmt(s.laplacian_variance, 0)}`;
  $('calibration').textContent = s.world_calibrated ? '场地已标定' : s.calibrated ? '内参已标定' : '像素观测';
  $('calibration-detail').textContent = s.demo ? '演示参数 · 非实机精度' : s.world_calibrated ? '已补偿标签安装高度' : '内参与外参分别配置';
  $('source-label').textContent = s.demo ? '合成场景 · 非实物相机' : s.source ? `输入源 ${s.source}` : '未连接';
  $('backend').textContent = s.backend || 'AprilTag 3';
  $('frame-number').textContent = `FRAME ${String(s.frame_id || 0).padStart(6, '0')}`;
  $('image-offline').hidden = live;
  renderDiagnostics(s, live);
  $('record').classList.toggle('active', !!s.recording);
  $('record').setAttribute('aria-pressed', String(!!s.recording));
  $('record-label').textContent = s.recording ? '停止记录' : '开始记录';
  $('record-path').textContent = s.recording ? `正在记录 · ${s.record_path}` : '点击“开始记录”保存逐帧 JSONL，含未检出帧';
  updateSettings(s);
  renderWorkspace();
  $('world-rms').textContent = s.world_info ? `四角 RMS ${fmt(s.world_info.rms_px, 3)} px · 相机高度 ${fmt(s.world_info.camera_world_xyz_m[2], 2)} m` : '';
  $('map-mode').textContent = s.world_calibrated ? '米制俯视图' : '图像平面 · px';
  $('map-mode').className = 'pill ' + (s.world_calibrated ? 'good' : 'warn');
  renderEvents(s);
}

function renderEvents(s) {
  const events = (s.events || []).slice(0, 10);
  $('event-count').textContent = events.length;
  $('event-latest').textContent = events[0] ? `${events[0].time} · ${events[0].text}` : '等待实验事件';
  const markup = events.map(event => `<div class="event ${event.level === 'error' ? 'error' : ''}"><time>${esc(event.time)}</time><span>${esc(event.text)}</span></div>`).join('') || '<div class="muted">等待实验事件</div>';
  if ($('events').innerHTML !== markup) $('events').innerHTML = markup;
  const event = events[0];
  if (event && event.time + event.text !== lastEvent) {
    lastEvent = event.time + event.text;
    if (event.level === 'error') {
      toast(event.text, true);
      $('event-log').open = true;
    }
  }
}

initTags();
initSettings();
initWorkspace(renderWorkspace);
pollState(render);
