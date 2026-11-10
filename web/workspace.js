// Navigation and shared interaction behavior.
import { $ } from './view-utils.js';
const views = {
  observe: ['实时观测', '关注识别画面、场地位置与小车运动。'],
  tags: ['标签数据', '搜索、筛选标签，并检查每一次观测的质量与坐标。'],
  settings: ['设备设置', '选择一个设置分组，修改后单独应用。'],
};
const settingsGroups = ['source-settings', 'camera-settings', 'detector-settings', 'preview-settings'];
let toastTimer;

export function currentView() {
  const key = location.hash.slice(1);
  return settingsGroups.includes(key) ? 'settings' : Object.hasOwn(views, key) ? key : 'observe';
}

export function navigate(view) {
  if (currentView() === view) return Promise.resolve();
  return new Promise(resolve => {
    window.addEventListener('hashchange', resolve, {once: true});
    location.hash = view;
  });
}

export function initWorkspace(onViewChange) {
  function update() {
    const active = currentView();
    for (const key of Object.keys(views)) $('view-' + key).hidden = key !== active;
    document.querySelectorAll('[data-view]').forEach(link => {
      if (link.dataset.view === active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    $('workspace-title').textContent = views[active][0];
    $('workspace-description').textContent = views[active][1];
    document.title = views[active][0] + ' · AprilTag';
    onViewChange(active);
    const group = settingsGroups.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'source-settings';
    for (const id of settingsGroups) $(id).hidden = id !== group;
    document.querySelectorAll('.settings-nav a[href^="#"]').forEach(link => {
      if (link.hash === '#' + group) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    // Keep keyboard focus visible if history changes hide the active panel.
    if (document.activeElement.closest('[hidden]')) $('workspace-title').focus({preventScroll: true});
  }
  window.addEventListener('hashchange', update);
  update();
  document.querySelector('.skip-link').addEventListener('click', event => {
    event.preventDefault();
    $('main').focus();
  });
  const menu = $('export-menu');
  document.addEventListener('click', event => {
    if (!menu.contains(event.target) || event.target.closest('a')) menu.open = false;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.open) {
      menu.open = false;
      menu.querySelector('summary').focus();
    }
  });
}

export function toast(message, error = false) {
  $('toast').textContent = message;
  $('toast').className = error ? 'error' : '';
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, error ? 7000 : 4500);
}

export async function runAction(button, action) {
  if (button.disabled) return;
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  try { await action(); }
  catch (error) { toast(error.message, true); }
  finally {
    button.disabled = false;
    button.removeAttribute('aria-busy');
  }
}

export function confirmAction(title, description, label) {
  const dialog = $('confirm-dialog');
  $('confirm-title').textContent = title;
  $('confirm-description').textContent = description;
  $('confirm-submit').textContent = label;
  dialog.returnValue = '';
  return new Promise(resolve => {
    dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirm'), {once: true});
    dialog.showModal();
  });
}
