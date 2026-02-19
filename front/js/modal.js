/**
 * Generic modal show/hide helpers with CSS transition support.
 */

export function showModal(modal, box) {
  modal.classList.remove('hidden');
  requestAnimationFrame(() => {
    box.classList.remove('scale-95', 'opacity-0');
    box.classList.add('scale-100', 'opacity-100');
  });
}

export function hideModal(modal, box) {
  box.classList.add('scale-95', 'opacity-0');
  box.classList.remove('scale-100', 'opacity-100');
  setTimeout(() => modal.classList.add('hidden'), 300);
}
