const views = {};
let currentView = null;

export function registerView(hash, elementId) {
  views[hash] = elementId;
}

export function navigate(hash) {
  if (location.hash !== hash) {
    location.hash = hash;
  } else {
    handleRoute();
  }
}

function handleRoute() {
  const hash = location.hash || '#/';

  for (const [route, elId] of Object.entries(views)) {
    const el = document.getElementById(elId);
    if (!el) continue;

    if (route === hash) {
      el.classList.add('active');
      el.classList.remove('hidden');
      currentView = route;
    } else {
      el.classList.remove('active');
      el.classList.add('hidden');
    }
  }
}

export function initRouter() {
  window.addEventListener('hashchange', handleRoute);

  if (!location.hash) {
    location.hash = '#/';
  } else {
    handleRoute();
  }
}

export function currentRoute() {
  return currentView || '#/';
}
