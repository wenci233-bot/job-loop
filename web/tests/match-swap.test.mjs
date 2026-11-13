import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
const cache = new Map(), persistent = new Map(), timers = new Map()
const storage = map => ({ getItem:k=>map.get(k)??null, setItem:(k,v)=>map.set(k,String(v)), removeItem:k=>map.delete(k) })
globalThis.sessionStorage=storage(cache);globalThis.localStorage=storage(persistent)
let next=0
globalThis.setInterval=fn=>{timers.set(++next,fn);return next};globalThis.clearInterval=id=>timers.delete(id)
const settle=async()=>{for(let i=0;i<15;i++)await Promise.resolve()}
const response=(data,status=200)=>({ok:status<400,status,json:async()=>data})
const source=(await readFile(new URL('../src/store.js',import.meta.url),'utf8')).replace("from 'vue'", "from '"+new URL('../node_modules/vue/index.mjs',import.meta.url).href+"'").replace("from './api'", "from '"+new URL('../src/api.js',import.meta.url).href+"'")
const store=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))
const criteria={directions:['算法'],cities:['深圳'],job_type:'日常实习',categories:['互联网中厂']}

test('matching cancellation and swap keep previous data, filters, and cumulative history',async()=>{
  store.setMatchResults([{company:'甲公司',role:'算法'}],criteria)
  let releaseStart,releasePoll;const bodies=[]
  globalThis.fetch=async(url,opts)=>{
    if(url.endsWith('/start')){bodies.push(JSON.parse(opts.body));return new Promise(r=>releaseStart=()=>r(response({task_id:'m1'})))}
    return response({status:'cancelled'})
  }
  const starting=store.startMatchGeneration(criteria,true)
  await settle();await store.stopMatchTask();releaseStart();await starting
  assert.equal(store.matchTask.status,'cancelled');assert.equal(store.getMatchResults()[0].company,'甲公司')
  assert.deepEqual(bodies[0],{...criteria,exclude_companies:['甲公司']})
  globalThis.fetch=async(url)=>url.endsWith('/start')?response({task_id:'m2'}):url.endsWith('/stop')?response({status:'cancelled'}):new Promise(r=>releasePoll=()=>r(response({status:'done',results:[{company:'迟到公司'}]})))
  await store.startMatchGeneration(criteria,true);await settle();await store.stopMatchTask();releasePoll();await settle()
  assert.equal(store.getMatchResults()[0].company,'甲公司');assert.ok(!store.getMatchHistory().includes('迟到公司'))
  globalThis.fetch=async(url)=>url.endsWith('/start')?response({task_id:'m3'}):response({status:'done',results:[{company:'乙公司'}],warning:'数量不足'})
  await store.startMatchGeneration(criteria,true);await settle()
  assert.equal(store.getMatchResults()[0].company,'乙公司');assert.deepEqual(store.getMatchHistory(),['甲公司','乙公司'])
  assert.deepEqual(store.getMatchCriteria(),criteria);assert.equal(store.matchTask.warning,'数量不足')
  globalThis.fetch=async(url)=>url.endsWith('/start')?response({task_id:'m4'}):response({status:'error',error:'无新结果'})
  await store.startMatchGeneration(criteria,true);await settle()
  assert.equal(store.getMatchResults()[0].company,'乙公司')
  store.clearMatchResults();assert.equal(store.getMatchResults(),null);assert.deepEqual(store.getMatchHistory(),['甲公司','乙公司'])
  assert.equal(timers.size,0)
})
