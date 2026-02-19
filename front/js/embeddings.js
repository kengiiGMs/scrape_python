import { state } from './config.js';
import { showModal, hideModal } from './modal.js';
import { toast } from './toast.js';

let embedModal, embedModalBox;
let tables = ['marketing_rag'];

export function initEmbeddings() {
  embedModal = document.getElementById('embed-modal');
  embedModalBox = document.getElementById('embed-modal-box');

  document.getElementById('btn-embeddings').addEventListener('click', openEmbedModal);
  document.getElementById('close-embed-modal').addEventListener('click', closeEmbedModal);
  embedModal.addEventListener('click', (e) => { if (e.target === embedModal) closeEmbedModal(); });

  document.getElementById('embed-add-btn').addEventListener('click', addTable);
  document.getElementById('embed-new-table').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addTable();
  });
}

function openEmbedModal() {
  showModal(embedModal, embedModalBox);
  renderState();
}

function closeEmbedModal() {
  hideModal(embedModal, embedModalBox);
}

function renderState() {
  document.getElementById('embed-active-id').textContent = state.currentIdConta || '—';
  document.getElementById('embed-badge-label').textContent = state.currentTable;
  renderTables();
}

function renderTables() {
  const list = document.getElementById('embed-tables-list');
  list.innerHTML = tables.map(t => {
    const isActive = t === state.currentTable;
    return `
      <div class="table-item flex items-center gap-3 px-3 py-2.5 rounded-xl border ${isActive ? 'border-purple-500/30 bg-purple-500/10 active' : 'border-white/5 hover:border-purple-500/15'}" data-table="${t}">
        <div class="w-2 h-2 rounded-full ${isActive ? 'bg-purple-400' : 'bg-gray-600'}"></div>
        <span class="text-sm text-gray-200">${t}</span>
        ${isActive ? '<span class="ml-auto text-[10px] text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full">ativo</span>' : '<span class="ml-auto text-[10px] text-gray-600 hover:text-gray-400 cursor-pointer">selecionar</span>'}
      </div>`;
  }).join('');

  list.querySelectorAll('.table-item').forEach(item => {
    item.addEventListener('click', () => {
      const table = item.dataset.table;
      if (table !== state.currentTable) {
        state.currentTable = table;
        toast.success(`Tabela alterada para ${table}`);
        renderState();
      }
    });
  });
}

function addTable() {
  const input = document.getElementById('embed-new-table');
  const name = input.value.trim().replace(/[^a-zA-Z0-9_]/g, '');

  if (!name) return;
  if (tables.includes(name)) {
    toast.info('Tabela já existe');
    return;
  }

  tables.push(name);
  input.value = '';
  renderTables();
  toast.success(`Tabela "${name}" adicionada`);
}

export function updateBadge() {
  const label = document.getElementById('embed-badge-label');
  if (label) label.textContent = state.currentTable;
}
