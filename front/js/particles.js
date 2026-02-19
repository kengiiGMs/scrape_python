export async function initParticles() {
  if (typeof tsParticles === 'undefined') {
    console.warn('tsParticles not loaded');
    return;
  }

  await tsParticles.load({
    id: 'tsparticles',
    options: {
      fullScreen: false,
      fpsLimit: 60,
      particles: {
        number: {
          value: 60,
          density: { enable: true, area: 900 },
        },
        color: {
          value: ['#3b82f6', '#8b5cf6', '#a855f7', '#ef4444', '#6366f1'],
        },
        shape: { type: 'circle' },
        opacity: {
          value: { min: 0.15, max: 0.4 },
          animation: { enable: true, speed: 0.6, minimumValue: 0.1, sync: false },
        },
        size: {
          value: { min: 1, max: 3 },
          animation: { enable: true, speed: 1.5, minimumValue: 0.5, sync: false },
        },
        links: {
          enable: true,
          distance: 140,
          color: '#8b5cf6',
          opacity: 0.08,
          width: 1,
        },
        move: {
          enable: true,
          speed: { min: 0.3, max: 0.8 },
          direction: 'none',
          random: true,
          straight: false,
          outModes: { default: 'out' },
        },
      },
      interactivity: {
        detectsOn: 'window',
        events: {
          onHover: { enable: true, mode: 'grab' },
          resize: true,
        },
        modes: {
          grab: { distance: 160, links: { opacity: 0.2, color: '#a855f7' } },
        },
      },
      detectRetina: true,
    },
  });
}
