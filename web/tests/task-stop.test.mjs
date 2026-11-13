import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
const values = new Map(), timers = new Map()
globalThis.sessionStorage = { getItem: k => values.get(k) ?? null, setItem: (k,v) => values.set(k,String(v)), removeItem: k => values.delete(k) }
let next = 0
globalThis.setInterval = fn => { timers.set(++next, fn); return next }
globalThis.clearInterval = id => timers.delete(id)
const settle = async () => { for(let i=0;i<8;i++) await Promise.resolve() }
const response = (data, status=200) => ({ ok: status < 400, status, json: async () => data })
const source = (await readFile(new URL('../src/store.js', import.meta.url), 'utf8')).replace("from 'vue'", "from '" + new URL('../node_modules/vue/index.mjs', import.meta.url).href + "'").replace("from './api'", "from '" + new URL('../src/api.js', import.meta.url).href + "'")
const store = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'))

test('starting stop, late polling, retryable stop failure and cancelled recovery', async () => {
  let releaseStart, releasePoll
  globalThis.fetch = async (url) => {
    if(url.endsWith('/start')) return new Promise(resolve => { releaseStart=()=>resolve(response({task_id:'prep-1'})) })
    if(url.endsWith('/stop')) return response({status:'cancelled'})
    return response({status:'running'})
  }
  const start = store.startPrepGeneration({company:'公司',role:'岗位'})
  await settle(); assert.equal(store.prepTask.status,'starting')
  await store.stopPrepTask(); assert.equal(store.prepTask.stopping,true)
  releaseStart(); await start
  assert.equal(store.prepTask.status,'cancelled'); assert.equal(values.has('prepTaskId'),false)
  let done=0; store.onEvalDone(()=>done++)
  globalThis.fetch=async url=>url.endsWith('/stop')?response({status:'cancelled',done:1,ok:1}):new Promise(resolve=>{releasePoll=()=>resolve(response({status:'done',done:3}))})
  store.startEvalTask('batch-1',3); await settle()
  await store.stopEvalTask(); releasePoll(); await settle()
  assert.equal(store.evalTask.status,'cancelled'); assert.equal(store.evalTask.done,1); assert.equal(done,0)
  globalThis.fetch=async url=>url.endsWith('/stop')?response({detail:'temporary failure'},500):response({status:'running'})
  store.startEvalTask('batch-2',2); await settle()
  await assert.rejects(store.stopEvalTask()); assert.equal(store.evalTask.status,'running'); assert.equal(store.evalTask.stopping,false)
  globalThis.fetch=async()=>response({status:'cancelled'})
  await store.stopEvalTask(); assert.equal(store.evalTask.status,'cancelled')
  values.set('prepTaskId',JSON.stringify({id:'old',company:'公司',role:'岗位'}))
  store.resumePrepIfAny(); await settle()
  assert.equal(store.prepTask.status,'cancelled'); assert.equal(values.has('prepTaskId'),false)
  globalThis.fetch=async url=>url.endsWith('/stop')?response({detail:'Not Found'},404):response({status:'running'})
  store.startEvalTask('old-server',1); await settle()
  await assert.rejects(store.stopEvalTask(), /后端尚未加载停止接口/)
  assert.equal(store.evalTask.status,'running')
  globalThis.fetch=async()=>response({detail:'missing task'},404)
  await store.stopEvalTask()
  assert.equal(store.evalTask.status,'cancelled')
  assert.equal(timers.size,0)
})
