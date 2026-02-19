const ICONS = {
  error: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
  success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
  info: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
};

let container = null;

function ensureContainer() {
  if (container) return container;
  container = document.createElement('div');
  container.className = 'toast-container';
  document.body.appendChild(container);
  return container;
}

function dismiss(el) {
  el.classList.add('removing');
  el.addEventListener('animationend', () => el.remove(), { once: true });
}

export function showToast(message, type = 'info', duration = 4500) {
  const wrap = ensureContainer();

  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `
    ${ICONS[type] || ICONS.info}
    <span>${message}</span>
    <span class="toast-close">&times;</span>`;

  el.querySelector('.toast-close').addEventListener('click', () => dismiss(el));
  wrap.appendChild(el);

  if (duration > 0) {
    setTimeout(() => { if (el.parentNode) dismiss(el); }, duration);
  }

  return el;
}

export const toast = {
  error: (msg, ms) => showToast(msg, 'error', ms),
  success: (msg, ms) => showToast(msg, 'success', ms),
  info: (msg, ms) => showToast(msg, 'info', ms),
};
