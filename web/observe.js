import { $, dl, fmt } from './view-utils.js';

const colors = ['#18a87b', '#e4a125', '#438de0', '#b87acb'];

function drawMap(state, healthy, selected) {
  const canvas = $('map');
  const ctx = canvas.getContext('2d');
  const width = 700, height = 440, pad = 45;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(0, 0, width, height);
  const metric = state.world_calibrated;
  const bounds = state.boundary_xy_m || [[0, 0], [3, 0], [3, 3], [0, 3]];
  const xs = bounds.map(point => point[0]), ys = bounds.map(point => point[1]);
  const x0 = metric ? Math.min(...xs) : 0, x1 = metric ? Math.max(...xs) : state.width || 1440;
  const y0 = metric ? Math.min(...ys) : 0, y1 = metric ? Math.max(...ys) : state.height || 1000;
  const scale = Math.min((width - pad * 2) / (x1 - x0 || 1), (height - pad * 2) / (y1 - y0 || 1));
  const ox = (width - (x1 - x0) * scale) / 2, oy = (height - (y1 - y0) * scale) / 2;
  const xy = point => [ox + (point[0] - x0) * scale,
    metric ? height - oy - (point[1] - y0) * scale : oy + (point[1] - y0) * scale];
  const path = (points, close = false) => {
    ctx.beginPath();
    points.forEach((point, index) => index ? ctx.lineTo(...xy(point)) : ctx.moveTo(...xy(point)));
    if (close) ctx.closePath();
  };
  ctx.lineWidth = 1;
  ctx.strokeStyle = '#e1e8ef';
  const steps = 6;
  for (let index = 0; index <= steps; index++) {
    const x = x0 + (x1 - x0) * index / steps, y = y0 + (y1 - y0) * index / steps;
    path([[x, y0], [x, y1]]);
    ctx.stroke();
    path([[x0, y], [x1, y]]);
    ctx.stroke();
    ctx.fillStyle = '#91a1b0';
    ctx.font = '11px system-ui';
    const point = xy([x, y0]);
    ctx.fillText(fmt(x, metric ? 1 : 0), point[0] - 8, metric ? point[1] + 20 : point[1] - 12);
  }
  path(metric ? bounds : [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], true);
  ctx.strokeStyle = '#bdcbd8';
  ctx.stroke();
  const tags = (state.tags || []).filter(tag => metric ? tag.world_xyz_m : tag.center_px);
  for (const tag of tags) {
    const point = xy(metric ? tag.world_xyz_m : tag.center_px);
    const live = tag.status === 'visible' && healthy;
    const color = live ? colors[tag.id % 4] : '#acbac6';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    const history = (tag.history || []).map(item => metric ? item.world : item.pixel).filter(Boolean);
    if (history.length > 1 && tag.role !== 'fixed') {
      path(history);
      ctx.globalAlpha = .5;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    if (tag.id === selected) {
      ctx.beginPath();
      ctx.arc(...point, 13, 0, Math.PI * 2);
      ctx.fillStyle = '#1d75c51a';
      ctx.fill();
      ctx.strokeStyle = '#a2c7e5';
      ctx.stroke();
    }
    ctx.fillStyle = color;
    if (tag.role === 'fixed') ctx.fillRect(point[0] - 4, point[1] - 4, 8, 8);
    else {
      ctx.beginPath();
      ctx.arc(...point, 5.5, 0, Math.PI * 2);
      ctx.fill();
    }
    const angle = metric ? tag.heading_world_deg : tag.heading_image_deg;
    if (angle != null) {
      const radians = -angle * Math.PI / 180;
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(...point);
      ctx.lineTo(point[0] + 19 * Math.cos(radians), point[1] + 19 * Math.sin(radians));
      ctx.stroke();
    }
    ctx.fillStyle = live ? '#38536b' : '#a0afbb';
    ctx.font = tag.id === selected ? 'bold 12px system-ui' : '11px system-ui';
    ctx.fillText(`ID ${tag.id}${live ? '' : ' · 旧'}`, point[0] + 10, point[1] - 10);
  }
  ctx.fillStyle = '#8b9dad';
  ctx.font = '11px system-ui';
  ctx.fillText(metric ? 'WORLD X →  /  Y ↑ · m' : 'IMAGE u →  /  v ↓ · px', 18, height - 12);
  if (!metric) {
    ctx.fillStyle = '#8a9dad';
    ctx.font = '12px system-ui';
    ctx.fillText('未标定：显示图像平面位置，透视会压缩距离', 30, 23);
  }
}

export function renderObserve(state, healthy, selected) {
  drawMap(state, healthy, selected);
  const metric = state.world_calibrated;
  const robots = (state.tags || []).filter(tag => tag.status === 'visible' && healthy
    && tag.role !== 'fixed' && (metric ? tag.world_xyz_m : tag.center_px));
  const point = tag => metric ? tag.world_xyz_m : tag.center_px;
  let minimum = Infinity;
  for (let i = 0; i < robots.length; i++) {
    for (let j = i + 1; j < robots.length; j++) {
      const a = point(robots[i]), b = point(robots[j]);
      minimum = Math.min(minimum, Math.hypot(a[0] - b[0], a[1] - b[1]));
    }
  }
  dl('fleet-details', [
    ['可见小车', `${robots.length}`],
    ['车间最小中心距', Number.isFinite(minimum) ? fmt(minimum, metric ? 3 : 0) + (metric ? ' m' : ' px') : '—'],
  ]);
}
