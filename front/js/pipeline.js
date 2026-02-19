import { API_BASE, state } from './config.js';
import { showModal, hideModal } from './modal.js';
import { openChat } from './chat.js';
import { toast } from './toast.js';
import { navigate } from './router.js';

let loadingScreen;
let newModal, newModalBox, existingModal, existingModalBox;

// ── Pipeline progress state ───────────────────────────────────
let elapsedTimer = null;
let elapsedSeconds = 0;
let progressInterval = null;

// Step definitions: { label, icon, subtitle, estimatedMs, progressStart, progressEnd }
const STEPS = [
  { label: 'Scraping do site', icon: 'globe', subtitle: 'Lendo HTML e extraindo conteúdo...', estimatedMs: 22000, pStart: 2, pEnd: 35 },
  { label: 'Gerando Markdown', icon: 'file-text', subtitle: 'Estruturando conteúdo extraído...', estimatedMs: 1500, pStart: 35, pEnd: 40 },
  { label: 'Ingestão com IA', icon: 'brain', subtitle: 'Gemini processando FAQs (2-3 min)...', estimatedMs: 130000, pStart: 40, pEnd: 95 },
];

// ── Init ──────────────────────────────────────────────────────
export function initPipeline() {
  loadingScreen = document.getElementById('loading-screen');
  newModal = document.getElementById('new-modal');
  newModalBox = document.getElementById('new-modal-box');
  existingModal = document.getElementById('existing-modal');
  existingModalBox = document.getElementById('existing-modal-box');

  document.getElementById('btn-new-site').addEventListener('click', openNewModal);
  document.getElementById('btn-existing').addEventListener('click', openExistingModal);
  document.getElementById('submit-btn').addEventListener('click', startPipeline);
  document.getElementById('btn-reset').addEventListener('click', resetApp);

  newModal.addEventListener('click', (e) => { if (e.target === newModal) closeNewModal(); });
  existingModal.addEventListener('click', (e) => { if (e.target === existingModal) closeExistingModal(); });
  document.getElementById('url-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') startPipeline();
  });
  document.getElementById('close-new-modal').addEventListener('click', closeNewModal);
  document.getElementById('close-existing-modal').addEventListener('click', closeExistingModal);
}

// ── Modal helpers ─────────────────────────────────────────────
function openNewModal() {
  showModal(newModal, newModalBox);
  setTimeout(() => document.getElementById('url-input').focus(), 350);
}
function closeNewModal() { hideModal(newModal, newModalBox); }
function openExistingModal() { showModal(existingModal, existingModalBox); loadPipelines(); }
function closeExistingModal() { hideModal(existingModal, existingModalBox); }

// ── Progress UI helpers ───────────────────────────────────────

function resetSteps() {
  for (let i = 0; i < STEPS.length; i++) {
    const el = document.getElementById(`step-${i}`);
    if (!el) continue;
    el.className = 'pipeline-step';
    const icon = el.querySelector('.step-icon');
    icon.className = 'step-icon step-icon--pending';
    // restore original icon
    icon.innerHTML = `<i data-lucide="${STEPS[i].icon}" class="w-3.5 h-3.5"></i>`;
    const timeEl = el.querySelector('.step-time');
    timeEl.textContent = timeEl.dataset.orig || timeEl.textContent;
  }
  setProgress(0);
  setTitle('Iniciando pipeline...');
  setSubtitle('aguardando...');
  document.getElementById('pipeline-elapsed').textContent = '0s';
}

function setTitle(t) {
  document.getElementById('pipeline-title').textContent = t;
}
function setSubtitle(t) {
  document.getElementById('pipeline-subtitle').textContent = t;
}
function setProgress(pct) {
  const bar = document.getElementById('pipeline-progress-bar');
  const lbl = document.getElementById('pipeline-progress-pct');
  bar.style.width = pct + '%';
  lbl.textContent = Math.round(pct) + '%';
}

/**
 * Smoothly animate progress from `from` toward `to` over `ms` milliseconds.
 * Returns a stop function.
 */
function animateProgress(from, to, ms) {
  clearInterval(progressInterval);
  const steps = Math.max(1, Math.round(ms / 200));
  const delta = (to - from) / steps;
  let current = from;
  setProgress(current);

  progressInterval = setInterval(() => {
    current = Math.min(to, current + delta);
    setProgress(current);
    if (current >= to) clearInterval(progressInterval);
  }, 200);

  return () => clearInterval(progressInterval);
}

function activateStep(index) {
  const step = STEPS[index];
  const el = document.getElementById(`step-${index}`);
  if (!el) return;

  el.classList.add('step--active');
  const iconEl = el.querySelector('.step-icon');
  iconEl.className = 'step-icon step-icon--active';
  // spinning inner dot
  iconEl.innerHTML = `<div class="step-spin-dot"></div>`;

  // Update orb icon
  const orb = document.getElementById('pipeline-orb-icon');
  orb.innerHTML = `<i data-lucide="${step.icon}" class="w-7 h-7 text-purple-300"></i>`;
  lucide.createIcons();

  setTitle(step.label);
  setSubtitle(step.subtitle);
  animateProgress(step.pStart, step.pEnd, step.estimatedMs);
}

function completeStep(index, actualMs) {
  const el = document.getElementById(`step-${index}`);
  if (!el) return;

  el.classList.remove('step--active');
  el.classList.add('step--done');
  const iconEl = el.querySelector('.step-icon');
  iconEl.className = 'step-icon step-icon--done';
  iconEl.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5"></i>`;
  lucide.createIcons();

  // show actual time
  const timeEl = el.querySelector('.step-time');
  if (actualMs) {
    timeEl.textContent = (actualMs / 1000).toFixed(1) + 's';
    timeEl.classList.add('text-emerald-400');
  }
}

// ── Elapsed counter ────────────────────────────────────────────
function startElapsed() {
  elapsedSeconds = 0;
  clearInterval(elapsedTimer);
  elapsedTimer = setInterval(() => {
    elapsedSeconds++;
    const m = Math.floor(elapsedSeconds / 60);
    const s = elapsedSeconds % 60;
    document.getElementById('pipeline-elapsed').textContent =
      m > 0 ? `${m}m ${s}s` : `${s}s`;
  }, 1000);
}
function stopElapsed() {
  clearInterval(elapsedTimer);
  elapsedTimer = null;
}

// ── Show / Hide loading screen ────────────────────────────────
function showLoading() {
  resetSteps();
  lucide.createIcons();
  loadingScreen.classList.remove('hidden');
  startElapsed();
  activateStep(0);
  lucide.createIcons();
}
function hideLoading() {
  stopElapsed();
  clearInterval(progressInterval);
  loadingScreen.classList.add('hidden');
}

// ── Main pipeline ─────────────────────────────────────────────
async function startPipeline() {
  const urlInput = document.getElementById('url-input');
  const url = urlInput.value.trim();
  const btn = document.getElementById('submit-btn');

  if (!url) {
    urlInput.classList.add('ring-2', 'ring-red-500/50');
    setTimeout(() => urlInput.classList.remove('ring-2', 'ring-red-500/50'), 2000);
    return;
  }

  state.currentUrl = url;
  btn.disabled = true;
  btn.innerHTML = '<div class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div> Processando...';

  closeNewModal();

  setTimeout(() => {
    showLoading();
  }, 400);

  try {
    // The API does all 3 steps in one call — we advance the UI optimistically using timers.
    const step0Start = Date.now();

    // Simulated step 1 advance: after 22s mark step 0 done, activate step 1
    const step1Timer = setTimeout(() => {
      completeStep(0, Date.now() - step0Start);

      const step1Start = Date.now();
      activateStep(1);
      lucide.createIcons();

      // Step 2 is nearly instant — advance after 1.5s
      const step2Timer = setTimeout(() => {
        completeStep(1, Date.now() - step1Start);
        activateStep(2);
        lucide.createIcons();
      }, 1500);
    }, 22000);

    // Real API call
    const apiStart = Date.now();
    const response = await fetch(`${API_BASE}/api/pipeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, table: state.currentTable, clear: false }),
    });

    const totalMs = Date.now() - apiStart;
    clearTimeout(step1Timer);

    const data = await response.json();
    if (!response.ok || !data.success) {
      throw new Error(data.detail || data.message || 'Erro no pipeline');
    }

    // Mark all remaining steps done
    for (let i = 0; i < STEPS.length; i++) {
      const el = document.getElementById(`step-${i}`);
      if (el && !el.classList.contains('step--done')) {
        completeStep(i);
      }
    }
    setProgress(100);
    setTitle('Concluído!');
    setSubtitle('Base de conhecimento pronta');
    lucide.createIcons();

    state.currentIdConta = data.data.ID_Conta;
    let hostname;
    try { hostname = new URL(url).hostname; } catch { hostname = url; }

    setTimeout(() => {
      hideLoading();
      navigate('#/chat');
      openChat(hostname);
    }, 900);

  } catch (error) {
    stopElapsed();
    clearInterval(progressInterval);
    hideLoading();
    toast.error('Erro ao processar: ' + error.message);
    console.error(error);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="rocket" class="w-4 h-4"></i> Processar Site';
    lucide.createIcons();
  }
}

// ── Pipelines list ────────────────────────────────────────────
async function loadPipelines() {
  const list = document.getElementById('pipelines-list');
  list.innerHTML = `
    <div class="flex items-center justify-center py-12 text-gray-500 text-sm">
      <div class="animate-spin w-5 h-5 border-2 border-gray-600 border-t-purple-400 rounded-full mr-3"></div>
      Carregando bases...
    </div>`;

  try {
    const response = await fetch(`${API_BASE}/api/pipelines`);
    const data = await response.json();

    if (!data.success || !data.data || data.data.length === 0) {
      list.innerHTML = `
        <div class="flex flex-col items-center justify-center py-14 text-gray-400">
          <div class="empty-state-icon">
            <i data-lucide="inbox" class="w-7 h-7 text-purple-400/60"></i>
          </div>
          <p class="text-sm font-medium text-gray-300">Nenhuma base processada</p>
          <p class="text-xs text-gray-500 mt-1.5 max-w-[220px] text-center leading-relaxed">Processe um site para criar sua primeira base de conhecimento</p>
        </div>`;
      lucide.createIcons();
      return;
    }

    state.pipelines = data.data;

    list.innerHTML = state.pipelines
      .map((p, idx) => `
        <div class="pipeline-item px-4 py-3.5 border-b border-white/5 cursor-pointer flex items-center justify-between" data-idx="${idx}">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center flex-shrink-0">
              <i data-lucide="globe" class="w-4 h-4 text-purple-400"></i>
            </div>
            <div>
              <div class="text-sm font-medium text-gray-200">${p.url_inferido}</div>
              <div class="text-xs text-gray-500">${p.total_faqs} FAQs disponíveis</div>
            </div>
          </div>
          <i data-lucide="chevron-right" class="w-4 h-4 text-gray-600"></i>
        </div>`)
      .join('');

    lucide.createIcons();

    list.querySelectorAll('.pipeline-item').forEach((item) => {
      item.addEventListener('click', () => {
        const pipeline = state.pipelines[parseInt(item.dataset.idx)];
        state.currentIdConta = pipeline.ID_Conta;
        state.currentUrl = pipeline.url_inferido;
        closeExistingModal();
        setTimeout(() => {
          navigate('#/chat');
          openChat(pipeline.url_inferido);
        }, 400);
      });
    });
  } catch (error) {
    list.innerHTML = `
      <div class="flex flex-col items-center justify-center py-14 text-red-400">
        <div class="empty-state-icon" style="background: linear-gradient(135deg, rgba(239,68,68,0.1), rgba(239,68,68,0.05));">
          <i data-lucide="alert-circle" class="w-7 h-7 text-red-400/70"></i>
        </div>
        <p class="text-sm font-medium">Erro ao carregar</p>
        <p class="text-xs text-gray-500 mt-1.5 max-w-[240px] text-center leading-relaxed">${error.message}</p>
      </div>`;
    toast.error('Falha ao carregar sites: ' + error.message);
    lucide.createIcons();
  }
}

// ── Reset ─────────────────────────────────────────────────────
function resetApp() {
  state.currentIdConta = null;
  state.currentUrl = '';
  document.body.style.overflow = '';
  document.getElementById('url-input').value = '';
  navigate('#/');
}
