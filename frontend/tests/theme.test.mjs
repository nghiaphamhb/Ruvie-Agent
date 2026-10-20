import assert from 'node:assert/strict';
import test from 'node:test';
import {get} from 'svelte/store';

async function fixture(saved={},dark=false,blocked=false){
  const previous=globalThis.window;
  const mediaListeners=new Set(),storageListeners=new Set(),writes=[];
  const media={matches:dark,addEventListener:(_,fn)=>mediaListeners.add(fn),removeEventListener:(_,fn)=>mediaListeners.delete(fn)};
  globalThis.window={matchMedia:()=>media,localStorage:{getItem:key=>{if(blocked)throw Error('blocked');return saved[key]??null;},setItem:(key,value)=>{if(blocked)throw Error('blocked');saved[key]=value;writes.push([key,value]);}},addEventListener:(_,fn)=>storageListeners.add(fn),removeEventListener:(_,fn)=>storageListeners.delete(fn)};
  const module=await import('../src/lib/features/settings/theme.ts').catch(()=>null);
  assert.ok(module,'theme state must exist');
  const states=[];
  return {create(id){const state=module.createThemeState(id);states.push(state);return state;},writes,saved,
    system(value){media.matches=value;for(const fn of mediaListeners)fn({matches:value});},
    storage(key,newValue){for(const fn of storageListeners)fn({key,newValue});},
    close(){for(const state of states)state.dispose();globalThis.window=previous;},mediaListeners,storageListeners};
}

test('system follows OS changes without persisting detected colors',async()=>{
  const f=await fixture();try{const state=f.create('alice');assert.deepEqual(get(state),{preference:'system',resolved:'light'});f.system(true);assert.equal(get(state).resolved,'dark');assert.deepEqual(f.writes,[]);}finally{f.close();}
});
test('manual choices persist per account and ignore OS until system is selected',async()=>{
  const f=await fixture({},true);try{
    const alice=f.create('alice');alice.select('light');f.system(false);f.system(true);assert.equal(get(alice).resolved,'light');
    const bob=f.create('bob');assert.equal(get(bob).preference,'system');assert.equal(get(f.create('alice')).preference,'light');
    alice.select('system');assert.equal(get(alice).resolved,'dark');assert.equal(f.writes.at(-1)[1],'system');
    const before=get(alice);alice.select('bogus');assert.deepEqual(get(alice),before);
  }finally{f.close();}
});
test('storage failures keep a usable in-session theme',async()=>{
  const f=await fixture({},false,true);try{const state=f.create('alice');state.select('dark');assert.equal(get(state).resolved,'dark');}finally{f.close();}
});
test('storage changes affect only the matching account and dispose removes listeners',async()=>{
  const f=await fixture();try{const state=f.create('alice');state.select('dark');const key=f.writes[0][0];f.storage(key+'other','light');assert.equal(get(state).resolved,'dark');f.storage(key,'light');assert.equal(get(state).resolved,'light');f.storage(key,'invalid');assert.equal(get(state).preference,'system');state.dispose();assert.equal(f.mediaListeners.size,0);assert.equal(f.storageListeners.size,0);}finally{f.close();}
});
