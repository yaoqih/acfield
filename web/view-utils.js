// Small presentation helpers shared by the workspaces.
export const $ = id => document.getElementById(id);
export const fmt = (value, digits = 1) => value == null || !Number.isFinite(Number(value))
  ? '—' : Number(value).toFixed(digits);
export const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));
export const roles = {fixed: '固定角点', pursuer: '小车', evader: '小车', robot: '小车', unknown: '未配置标签'};
export const vec = (value, digits = 2) => value ? value.map(x => fmt(x, digits)).join(', ') : '未标定';

export function dl(id, pairs) {
  $(id).innerHTML = pairs.map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('');
}

// Update values in place. Retain row/button identity, keyboard focus and scroll position.
function patchElement(current, next) {
  for (const attribute of current.getAttributeNames()) {
    if (!next.hasAttribute(attribute)) current.removeAttribute(attribute);
  }
  for (const {name, value} of next.attributes) {
    if (current.getAttribute(name) !== value) current.setAttribute(name, value);
  }
  [...next.childNodes].forEach((child, index) => {
    const previous = current.childNodes[index];
    if (!previous) current.append(child.cloneNode(true));
    else if (previous.nodeType !== child.nodeType || previous.nodeName !== child.nodeName) previous.replaceWith(child.cloneNode(true));
    else if (child.nodeType === Node.ELEMENT_NODE) patchElement(previous, child);
    else if (previous.textContent !== child.textContent) previous.textContent = child.textContent;
  });
  while (current.childNodes.length > next.childNodes.length) current.lastChild.remove();
}

export function patchList(id, markup, keyAttribute) {
  const container = $(id);
  const template = document.createElement('template');
  template.innerHTML = markup;
  const existing = new Map([...container.children].map(node => [node.getAttribute(keyAttribute), node]));
  [...template.content.children].forEach((next, index) => {
    const key = next.getAttribute(keyAttribute);
    const previous = existing.get(key);
    const node = previous || next;
    if (previous) patchElement(previous, next);
    if (container.children[index] !== node) container.insertBefore(node, container.children[index] || null);
    existing.delete(key);
  });
  existing.forEach(node => node.remove());
}
