import { API_BASE, state } from './config.js';
import { renderMarkdown } from './markdown.js';
import { updateBadge } from './embeddings.js';

let chatMessages, chatInput, sendBtn;

export function initChat() {
  chatMessages = document.getElementById('chat-messages');
  chatInput = document.getElementById('chat-input');
  sendBtn = document.getElementById('send-btn');

  sendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
  });
}

export function openChat(siteUrl) {
  const chatActiveUrl = document.getElementById('chat-active-url');

  chatActiveUrl.textContent = siteUrl;
  chatInput.disabled = false;
  sendBtn.disabled = false;
  document.body.style.overflow = 'hidden';

  updateBadge();

  chatMessages.innerHTML = '';
  appendSystemMessage(`Agente pronto! Analisei todo o conteúdo de ${siteUrl}`);
  setTimeout(() => {
    appendBotMessage('Olá! Eu processei o site com sucesso e já entendo todo o contexto, serviços e informações disponíveis. Como posso te ajudar?');
  }, 500);
  setTimeout(() => chatInput.focus(), 600);
}

export function appendSystemMessage(text) {
  const div = document.createElement('div');
  div.className = 'flex justify-center my-3 animate-slide-down';
  div.innerHTML = `
    <span class="text-xs bg-purple-500/10 text-purple-300 px-4 py-1.5 rounded-full border border-purple-500/20">
      ${text}
    </span>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
  const el = document.createElement('div');
  el.textContent = text;
  return el.innerHTML;
}

export function appendUserMessage(text) {
  const div = document.createElement('div');
  div.className = 'flex flex-row-reverse gap-3 max-w-[80%] ml-auto animate-slide-up';
  div.innerHTML = `
    <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-600 flex-shrink-0 flex items-center justify-center shadow-md">
      <i data-lucide="user" class="w-4 h-4 text-white"></i>
    </div>
    <div class="bubble-user p-4 rounded-2xl rounded-tr-none text-sm text-gray-100">
      ${escapeHtml(text)}
    </div>`;
  chatMessages.appendChild(div);
  lucide.createIcons();
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

export function appendBotMessage(text) {
  const div = document.createElement('div');
  div.className = 'flex gap-3 max-w-[80%] animate-slide-up';
  div.innerHTML = `
    <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-gray-700 to-gray-800 flex-shrink-0 flex items-center justify-center shadow-md border border-white/5">
      <i data-lucide="bot" class="w-4 h-4 text-purple-300"></i>
    </div>
    <div class="bot-msg bubble-bot p-4 rounded-2xl rounded-tl-none text-sm text-gray-200">
      ${renderMarkdown(text)}
    </div>`;
  chatMessages.appendChild(div);
  lucide.createIcons();
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

export function showTypingIndicator() {
  const div = document.createElement('div');
  div.id = 'typing-indicator';
  div.className = 'flex gap-3 max-w-[80%] animate-slide-up';
  div.innerHTML = `
    <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-gray-700 to-gray-800 flex-shrink-0 flex items-center justify-center shadow-md border border-white/5">
      <i data-lucide="bot" class="w-4 h-4 text-purple-300"></i>
    </div>
    <div class="bubble-bot px-5 py-4 rounded-2xl rounded-tl-none flex items-center gap-1.5">
      <div class="w-2 h-2 rounded-full bg-purple-400 typing-dot"></div>
      <div class="w-2 h-2 rounded-full bg-purple-400 typing-dot"></div>
      <div class="w-2 h-2 rounded-full bg-purple-400 typing-dot"></div>
    </div>`;
  chatMessages.appendChild(div);
  lucide.createIcons();
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

export function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message || !state.currentIdConta) return;

  appendUserMessage(message);
  chatInput.value = '';
  chatInput.disabled = true;
  sendBtn.disabled = true;
  showTypingIndicator();

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, ID_Conta: state.currentIdConta }),
    });

    const data = await response.json();
    removeTypingIndicator();

    if (!response.ok || !data.success) {
      throw new Error(data.detail || 'Erro no chat');
    }

    appendBotMessage(data.data.reply || 'Sem resposta do agente');
  } catch (error) {
    removeTypingIndicator();
    appendSystemMessage('Erro: ' + error.message);
    console.error(error);
  } finally {
    chatInput.disabled = false;
    sendBtn.disabled = false;
    chatInput.focus();
  }
}
