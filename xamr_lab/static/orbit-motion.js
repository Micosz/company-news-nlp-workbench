'use strict';
// Presentation only. Completion is called only after the real API has succeeded.
// No simulated percentage, synthetic metrics, or changes to server duration.
function createOrbitMotion(scene, options = {}) {
  const motion = options.motion || window.matchMedia('(prefers-reduced-motion: reduce)');
  const now = options.now || (() => performance.now());
  const delay = options.delay || (ms => new Promise(resolve => setTimeout(resolve, ms)));
  let started = 0, generation = 0;
  const phase = value => { scene.dataset.phase = value; };
  return {
    start() { generation++; started = now(); phase('flight'); },
    async complete() {
      const token = generation;
      if (!motion.matches) await delay(Math.max(0, 1500 - (now() - started)));
      if (token !== generation) return;
      phase('impact');
      if (!motion.matches) await delay(600);
      if (token === generation) phase('settled');
    },
    reset() { generation++; phase('idle'); }
  };
}
if (typeof module !== 'undefined' && module.exports) module.exports = {createOrbitMotion};
