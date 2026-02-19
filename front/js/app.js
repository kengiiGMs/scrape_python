import { initChat } from './chat.js';
import { initPipeline } from './pipeline.js';
import { initEmbeddings } from './embeddings.js';
import { initParticles } from './particles.js';
import { registerView, initRouter } from './router.js';

document.addEventListener('DOMContentLoaded', async () => {
  registerView('#/', 'landing-page');
  registerView('#/chat', 'chat-interface');

  initRouter();
  initChat();
  initPipeline();
  initEmbeddings();

  lucide.createIcons();

  await initParticles();
});
