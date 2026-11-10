import { $, dl, esc, fmt, patchList, roles, vec } from './view-utils.js';
import { currentView, navigate } from './workspace.js';

let selected = 10;
let state;
let latestTags = [];
const mobile = matchMedia('(max-width: 760px)');

export function selectedTag() { return selected; }

function tagList(s) {
  const map = new Map((s.tags || []).map(tag => [tag.id, tag]));
  for (const [id, tag] of Object.entries(s.configured_tags || {})) {
    if (!map.has(Number(id))) map.set(Number(id), {id: Number(id), name: tag.name, role: tag.role, status: 'unseen', size_m: tag.size_m});
  }
  return [...map.values()].sort((a, b) => a.id - b.id);
}
function statusText(tag) {
  return {visible: '可见', stale: '暂失', lost: '丢失', unseen: '未出现'}[tag.status] || '—';
}

function renderTable(tags) {
  const search = $('tag-search').value.trim().toLocaleLowerCase();
  const filter = $('tag-filter').value;
  const shown = tags.filter(tag => {
    const matchesText = `${tag.id} ${tag.name ?? ''}`.toLocaleLowerCase().includes(search);
    const matchesStatus = filter === 'all' || (filter === 'missing' ? ['stale', 'lost'].includes(tag.status) : tag.status === filter);
    return matchesText && matchesStatus;
  });
  $('table-count').textContent = `${shown.length} / ${tags.length}`;
  $('table-empty').hidden = shown.length > 0;
  $('reset-filters').hidden = !search && filter === 'all';
  patchList('tag-table', shown.map(tag => {
    const live = tag.status === 'visible';
    const world = !!tag.world_xyz_m;
    const position = world ? vec(tag.world_xyz_m.slice(0, 2), 3) + ' m'
      : tag.center_px ? vec(tag.center_px, 1) + ' px' : '—';
    const heading = world ? tag.heading_world_deg : tag.heading_image_deg;
    const speed = tag.speed_m_s != null ? fmt(tag.speed_m_s, 3) + ' m/s'
      : tag.speed_px_s != null ? fmt(tag.speed_px_s, 1) + ' px/s' : '—';
    return `<tr data-id="${tag.id}" class="${tag.id === selected ? 'selected ' : ''}${live ? '' : 'dim'}">
      <td><button class="tag-select" data-tag-id="${tag.id}" aria-pressed="${tag.id === selected}" aria-label="检查 ID ${tag.id} ${esc(tag.name)}"><strong>${tag.id}</strong> · ${esc(tag.name)}</button></td>
      <td><i class="status-dot ${tag.status}" aria-hidden="true"></i>${statusText(tag)}<small>${tag.age_ms == null ? '等待首次识别' : fmt(tag.age_ms, 0) + ' ms 前'}</small></td>
      <td>${position}<small>${world ? '场地' : '图像'}朝向 ${fmt(heading)}°</small></td>
      <td>${speed}</td><td>裕量 ${fmt(tag.decision_margin)}<small>纠错 ${fmt(tag.hamming, 0)} · 短边 ${fmt(tag.min_edge_px)} px</small></td>
      <td>${tag.seen_ratio == null ? '—' : fmt(tag.seen_ratio * 100, 1) + '%'}</td></tr>`;
  }).join(''), 'data-id');
}

function renderRoster(tags) {
  $('roster-count').textContent = tags.filter(tag => tag.status === 'visible').length + ' 可见 / ' + tags.length;
  patchList('tag-roster', tags.map(tag => `
    <button class="tag-card ${tag.id === selected ? 'selected' : ''}" data-tag-id="${tag.id}"
      aria-label="检查 ID ${tag.id} ${esc(tag.name)}，${statusText(tag)}">
      <span><strong>ID ${tag.id}</strong><span class="tag-card-status"><i class="status-dot ${tag.status}" aria-hidden="true"></i>${statusText(tag)}</span></span>
      <small>${esc(tag.name || roles[tag.role] || '未配置标签')}</small>
    </button>`).join('') || '<p class="muted">暂无标签。将打印标签放入画面后开始观测。</p>', 'data-tag-id');
}

function renderDetails(tag, snapshot) {
  const seen = !!tag?.center_px;
  $('details').hidden = !seen;
  $('detail-empty').hidden = seen;
  $('tag-title').textContent = tag ? `ID ${tag.id} · ${tag.name || ''}` : '等待标签';
  $('tag-role').textContent = tag ? `${roles[tag.role] || '标签'} · ${snapshot.family || 'tag36h11'}` : '从表格选择标签';
  $('tag-status').textContent = tag ? statusText(tag) : '—';
  $('tag-status').className = 'pill ' + (tag?.status === 'visible' ? 'good' : tag?.status === 'stale' ? 'warn' : 'bad');
  if (!seen) return;
  dl('pixel-details', [
    ['中心 (u, v)', vec(tag.center_px) + ' px'],
    ['图像朝向', fmt(tag.heading_image_deg) + '°'],
    ['短边 / 长边', fmt(tag.min_edge_px) + ' / ' + fmt(tag.max_edge_px) + ' px'],
    ['投影面积', fmt(tag.area_px2, 0) + ' px²'],
    ['图像速度', fmt(tag.speed_px_s) + ' px/s'],
    ['跟踪时长', fmt(tag.track_seconds) + ' s'],
  ]);
  $('quality-bar').style.width = Math.max(0, Math.min(100, tag.decision_margin ?? 0)) + '%';
  dl('quality-details', [
    ['Decision margin', fmt(tag.decision_margin, 2)],
    ['Hamming 纠错位数', fmt(tag.hamming, 0)],
    ['可见帧数 / 可见率', fmt(tag.seen_frames, 0) + ' / ' + fmt(tag.seen_ratio == null ? null : tag.seen_ratio * 100) + '%'],
    ['最近观测', fmt(tag.age_ms, 0) + ' ms 前'],
  ]);
  const pose = tag.pose;
  dl('pose-details', pose ? [
    ['标签实际边长', fmt(tag.size_m == null ? null : tag.size_m * 1000, 0) + ' mm'],
    ['平移 X, Y, Z', vec(pose.camera_xyz_m, 3) + ' m'],
    ['直线距离', fmt(pose.range_m, 3) + ' m'],
    ['RPY · ZYX', vec(pose.rpy_deg, 1) + '°'],
    ['离轴倾角', fmt(pose.tilt_deg) + '°'],
    ['重投影 RMS', fmt(pose.reprojection_rms_px, 3) + ' px'],
    ['另一解 RMS', fmt(pose.alternative_rms_px, 3) + ' px'],
    ['平面位姿歧义', pose.ambiguous ? '两解接近，谨慎使用' : '当前最小重投影解'],
  ] : [['状态', '需要相机内参与实际标签尺寸']]);
  dl('world-details', tag.world_xyz_m ? [
    ['标签中心 X, Y, Z', vec(tag.world_xyz_m, 3) + ' m'],
    ['安装高度', fmt(tag.height_m, 3) + ' m'],
    ['标签前向角', fmt(tag.heading_world_deg) + '°'],
    ['平面速度 · 滤波', fmt(tag.speed_m_s, 3) + ' m/s'],
  ] : [['状态', '需要四角外参及标签安装高度']]);
  $('raw-details').textContent = '角点 0,1,2,3 (px)\n'
    + (tag.corners_px || []).map((point, index) => `${index}: [${vec(point)}]`).join('\n')
    + (pose ? '\n\n旋转矩阵 · tag → camera\n' + pose.rotation_matrix.map(row => vec(row, 4)).join('\n') : '');
}

export function renderTags(snapshot) {
  state = snapshot;
  latestTags = tagList(state);
  if (latestTags.length && !latestTags.some(tag => tag.id === selected)) {
    selected = (latestTags.find(tag => tag.status === 'visible' && tag.role !== 'fixed') || latestTags[0]).id;
  }
  const key = latestTags.map(tag => `${tag.id}:${tag.name}`).join(',');
  if ($('selected-tag').dataset.key !== key) {
    $('selected-tag').replaceChildren(...latestTags.map(tag => new Option(`ID ${tag.id} · ${tag.name || ''}`, tag.id)));
    $('selected-tag').dataset.key = key;
  }
  $('selected-tag').value = selected;
  if (currentView() === 'tags') {
    renderTable(latestTags);
    renderDetails(latestTags.find(tag => tag.id === selected), state);
  } else if (currentView() === 'observe') renderRoster(latestTags);
}

async function chooseTag(id, fromRoster = false) {
  selected = id;
  await navigate('tags');
  if (state) renderTags(state);
  if (mobile.matches) {
    $('tag-dialog').append($('inspector'));
    if (!$('tag-dialog').open) $('tag-dialog').showModal();
    document.body.classList.add('inspector-open');
    $('close-inspector').focus();
  } else if (fromRoster) $('inspector').focus();
}

export function initTags() {
  const dialog = $('tag-dialog');
  $('tag-table').addEventListener('click', event => {
    const row = event.target.closest('tr[data-id]');
    if (row) chooseTag(Number(row.dataset.id));
  });
  $('tag-roster').addEventListener('click', event => {
    const card = event.target.closest('[data-tag-id]');
    if (card) chooseTag(Number(card.dataset.tagId), true);
  });
  $('selected-tag').addEventListener('change', event => {
    selected = Number(event.target.value);
    if (state) renderTags(state);
  });
  for (const id of ['tag-search', 'tag-filter']) {
    $(id).addEventListener(id === 'tag-search' ? 'input' : 'change', () => renderTable(latestTags));
  }
  $('reset-filters').addEventListener('click', () => {
    $('tag-search').value = '';
    $('tag-filter').value = 'all';
    renderTable(latestTags);
    $('tag-search').focus();
  });
  $('close-inspector').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => {
    $('inspector-host').append($('inspector'));
    document.body.classList.remove('inspector-open');
    if (currentView() === 'tags') {
      const row = $('tag-table').querySelector(`[data-tag-id="${selected}"]`);
      (row || $('tag-search')).focus({preventScroll: true});
    }
  });
  mobile.addEventListener('change', () => { if (dialog.open) dialog.close(); });
  window.addEventListener('hashchange', () => { if (dialog.open && currentView() !== 'tags') dialog.close(); });
}

