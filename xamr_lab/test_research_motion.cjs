'use strict';
// DOM/API doubles test control flow only, not browser rendering or model scores.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname+'/static/research.js','utf8').split('(async () => {')[0];
function harness() {
  const nodes = new Map(), phases = [];
  const get = id => {
    if (!nodes.has(id)) nodes.set(id,{hidden:false,disabled:false,value:'',checked:false, dataset:{},
      firstElementChild:{textContent:''},classList:{toggle(){},remove(){}},setAttribute(){},focus(){},scrollIntoView(){}});
    return nodes.get(id);
  };
  get('dataset').value='ann1-dev';get('algorithm').value='OR';
  const context=vm.createContext({document:{getElementById:get},console,URL,Blob,Uint8Array,atob,
    createOrbitMotion:()=>({start:()=>phases.push('flight'),complete:async()=>phases.push('impact'),reset:()=>phases.push('idle')})});
  vm.runInContext(source,context);
  vm.runInContext(`storage=async()=>{};history=async()=>{};render=item=>{current=item;};`,context);
  return {context,get,phases};
}
(async()=>{
 const h=harness();let resolve,calls=0;
 h.context.api=()=>{calls++;return new Promise(r=>resolve=r)};
 const pending=h.get('run').onclick();
 assert.equal(h.get('run').disabled,true);assert.equal(h.get('output').hidden,true);
 await h.get('run').onclick();assert.equal(calls,1,'repeated click must not create a second API call');
 resolve({report:{id:'real-response'},archive_base64:''});await pending;
 assert.deepEqual(h.phases,['flight','impact','idle']);assert.equal(h.get('output').hidden,false);assert.equal(h.get('run').disabled,false);
 // Failed rerun restores the previous evidence and never plays the success collision.
 h.phases.length=0;h.context.api=async()=>{throw Error('test network failure')};await h.get('run').onclick();
 assert.deepEqual(h.phases,['flight','idle']);assert.equal(h.get('output').hidden,false);assert.match(h.get('status').textContent,/test network failure/);
 assert.equal(vm.runInContext('current.report.id',h.context),'real-response');
 const fresh=harness();fresh.context.api=async()=>{throw Error('test failure')};await fresh.get('run').onclick();
 assert.equal(fresh.get('output').hidden,true);assert.equal(fresh.get('empty').hidden,false);
 const gated=harness();gated.get('dataset').value='ann1-test_common';await gated.get('run').onclick();assert.deepEqual(gated.phases,[]);
 console.log('5 integration cases passed: real-response ordering, repeated click, rerun error, initial error, acknowledgement gate');
})().catch(error=>{console.error(error);process.exitCode=1});
