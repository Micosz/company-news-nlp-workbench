const assert=require('node:assert/strict');
const {createOrbitMotion}=require('./static/orbit-motion.js');
(async()=>{
 for(const [elapsed,reduced,expected] of [[0,false,[1500,600]],[2000,false,[0,600]],[0,true,[]]]){
 let t=0,waits=[],scene={dataset:{}};const m=createOrbitMotion(scene,{motion:{matches:reduced},now:()=>t,delay:async ms=>waits.push(ms)});
 m.start();assert.equal(scene.dataset.phase,'flight');t=elapsed;await m.complete();assert.deepEqual(waits,expected);assert.equal(scene.dataset.phase,'settled');m.reset();assert.equal(scene.dataset.phase,'idle');
 }
 let release;const scene={dataset:{}};const m=createOrbitMotion(scene,{motion:{matches:false},now:()=>0,delay:()=>new Promise(r=>release=r)});m.start();const pending=m.complete();m.reset();release();await pending;assert.equal(scene.dataset.phase,'idle');console.log('4 orbit lifecycle cases passed');
})();
