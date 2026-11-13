import { reactive } from 'vue'
import { api } from './api'

const RES_KEY = 'matchResults', HISTORY_KEY = 'jobloop.matchHistory', CRITERIA_KEY = 'matchCriteria'
let historyMemory = []
function readJSON(storage, key, fallback) { try { return JSON.parse(storage?.getItem(key)) ?? fallback } catch { return fallback } }
export function getMatchResults() { return readJSON(sessionStorage, RES_KEY, null) }
export function getMatchCriteria() { return readJSON(sessionStorage, CRITERIA_KEY, null) }
export function getMatchHistory() {
  const saved = readJSON(globalThis.localStorage, HISTORY_KEY, [])
  return [...new Set([...historyMemory, ...readJSON(sessionStorage, HISTORY_KEY, []), ...(Array.isArray(saved) ? saved : []), ...(getMatchResults() || []).map(row => row.company)].filter(name => typeof name === 'string' && name.trim()))]
}
export function setMatchResults(results, criteria) {
  historyMemory = [...new Set([...getMatchHistory(), ...results.map(row => row.company)])]
  try { globalThis.localStorage?.setItem(HISTORY_KEY, JSON.stringify(historyMemory)) } catch {}
  try { sessionStorage.setItem(HISTORY_KEY, JSON.stringify(historyMemory)) } catch {}
  sessionStorage.setItem(RES_KEY, JSON.stringify(results))
  if (criteria) sessionStorage.setItem(CRITERIA_KEY, JSON.stringify(criteria))
}
export function clearMatchResults() {
  historyMemory = getMatchHistory()
  try { globalThis.localStorage?.setItem(HISTORY_KEY, JSON.stringify(historyMemory)); sessionStorage.setItem(HISTORY_KEY, JSON.stringify(historyMemory)) } catch {}
  sessionStorage.removeItem(RES_KEY)
}

/** 可停止的评估/准备包任务。取消与轮询使用版本号隔离，防止迟到响应恢复旧任务。 */
const makeTask = () => reactive({ id: null, status: 'idle', stopping: false, stopRequested: false, progress: '', elapsed: 0, error: null, warning: '', company: '', role: '', done: 0, total: 0, current: '' })
export const matchTask = makeTask()
export const prepTask = makeTask()
export const evalTask = makeTask()
function controller(task, key, path, startPath) {
  const doneCallbacks = new Set(), errorCallbacks = new Set(), resumedCallbacks = new Set()
  let pollTimer, elapsedTimer, version = 0, polling = false
  const read = () => { try { return JSON.parse(sessionStorage.getItem(key)) } catch { return sessionStorage.getItem(key) } }
  const clearTimers = () => { clearInterval(pollTimer); clearInterval(elapsedTimer); pollTimer = elapsedTimer = null }
  function store() { sessionStorage.setItem(key, JSON.stringify({ id: task.id, company: task.company, role: task.role, elapsed: task.elapsed, criteria: task.criteria })) }
  function accept(data) {
    if (key === 'matchTaskId' && data.status === 'done') {
      if (!Array.isArray(data.results)) throw new Error('匹配结果格式异常')
      setMatchResults(data.results, task.criteria)
    }
    Object.assign(task, data, { stopping: false, stopRequested: false, warning: data.warning || '' })
    if (data.status === 'running') return
    clearTimers(); sessionStorage.removeItem(key)
    if (data.status === 'done') {
      const payload = key === 'matchTaskId' ? data.results : key === 'prepTaskId' ? { company: task.company, role: task.role, prep: data.prep } : data
      doneCallbacks.forEach(cb => cb(payload))
    } else if (data.status === 'error') errorCallbacks.forEach(cb => cb(data.error))
  }
  async function poll() {
    if (polling || task.status !== 'running' || task.stopping || !task.id) return
    const token = version, id = task.id
    polling = true
    try {
      const data = await api.get(path + encodeURIComponent(id))
      if (token !== version || task.stopping || task.status !== 'running') return
      accept(data)
    } catch(e) {
      if (token !== version) return
      if (e.status === 404) accept({ status: 'error', error: '任务不存在，服务可能已重启，请重新发起。' })
      else task.warning = '获取进度失败，将自动重试：' + e.message
    } finally { if (token === version) polling = false }
  }
  function timers() {
    clearTimers()
    elapsedTimer = setInterval(() => { task.elapsed++; store() }, 1000)
    pollTimer = setInterval(poll, 2500)
    void poll()
  }
  async function stop() {
    if (!['starting', 'running'].includes(task.status) || task.stopping) return
    task.stopRequested = true; task.stopping = true
    if (!task.id) return
    const token = ++version
    polling = false
    try {
      let data
      try { data = await api.post(path + encodeURIComponent(task.id) + '/stop', {}) }
      catch(e) {
        if (e.status !== 404) throw e
        // Distinguish a vanished task from an old server missing the stop route.
        try {
          data = await api.get(path + encodeURIComponent(task.id))
          if (data.status === 'running') throw new Error('后端尚未加载停止接口，请重启服务后重试')
        } catch(checkError) {
          if (checkError.status !== 404) throw checkError
          data = { status: 'cancelled', progress: '任务已不存在，已停止跟踪' }
        }
      }
      if (token !== version) return
      if (!['cancelled', 'done', 'error'].includes(data.status)) throw new Error('停止状态异常，请重试')
      accept(data)
    } catch(e) {
      if (token === version) { task.stopping = false; task.stopRequested = false; task.warning = '停止失败：' + e.message }
      throw e
    }
  }
  function attach(id, context = {}) {
    ++version; polling = false; clearTimers()
    Object.assign(task, { id, status: 'running', stopping: false, stopRequested: false, error: null, warning: '', elapsed: 0, done: 0, current: '', progress: '启动中', ...context })
    store(); timers()
  }
  async function start(body) {
    if (['starting', 'running'].includes(task.status)) return
    ++version; polling = false; clearTimers()
    Object.assign(task, { id: null, status: 'starting', stopping: false, stopRequested: false, error: null, warning: '', elapsed: 0, done: 0, total: body.ids?.length || 0, company: body.company || '', role: body.role || '', criteria: key === 'matchTaskId' ? { directions: [...body.directions], cities: [...body.cities], job_type: body.job_type, categories: [...body.categories] } : undefined, progress: '启动中' })
    try {
      const data = await api.post(startPath, body)
      if (!data.task_id) throw new Error('后端未返回任务编号')
      const shouldStop = task.stopRequested
      task.id = data.task_id; task.status = 'running'; task.stopping = false
      store()
      if (shouldStop) { await stop(); if (task.status === 'running') timers() }
      else timers()
    } catch(e) {
      if (task.id) { if (task.status === 'running') timers() }
      else accept({ status: 'error', error: e.message })
      throw e
    }
  }
  function resume() {
    const saved = read()
    const value = typeof saved === 'string' ? { id: saved } : saved
    if (!value?.id) return false
    attach(value.id, value)
    resumedCallbacks.forEach(cb => cb(value))
    return true
  }
  return { start, stop, attach, resume, read, done: cb => doneCallbacks.add(cb), error: cb => errorCallbacks.add(cb), resumed: cb => resumedCallbacks.add(cb),
    clear() { ++version; polling = false; clearTimers(); Object.assign(task, { id: null, status: 'idle', stopping: false, stopRequested: false, progress: '', error: null }); sessionStorage.removeItem(key) } }
}
const prepController = controller(prepTask, 'prepTaskId', '/interview/generate/task/', '/interview/generate/start')
const evalController = controller(evalTask, 'evalTaskId', '/rank/score/batch/', '/rank/score/batch/start')
export const startPrepGeneration = body => prepController.start(body)
export const startEvaluation = ids => evalController.start({ ids })
export const stopPrepTask = () => prepController.stop()
export const stopEvalTask = () => evalController.stop()
export const onPrepDone = cb => prepController.done(cb)
export const onPrepError = cb => prepController.error(cb)
export const onPrepResumed = cb => prepController.resumed(cb)
export const onEvalDone = cb => evalController.done(cb)
export const onEvalError = cb => evalController.error(cb)
export const resumePrepIfAny = () => prepController.resume()
export const resumeEvalIfAny = () => evalController.resume()
export const loadPrepId = () => prepController.read()
export const clearPrepTask = () => prepController.clear()
export const startPrepTask = (id, company, role) => prepController.attach(id, { company, role })
export const startEvalTask = (id, total) => evalController.attach(id, { total })

const matchController = controller(matchTask, 'matchTaskId', '/inbox/ai-match/task/', '/inbox/ai-match/start')
export const onMatchDone = cb => matchController.done(cb)
export const onMatchError = cb => matchController.error(cb)
export const resumeMatchIfAny = () => matchController.resume()
export const stopMatchTask = () => matchController.stop()
export const startMatchTask = id => matchController.attach(id)
export async function startMatchGeneration(criteria, change = false) {
  const excluded = change ? getMatchHistory() : []
  if (excluded.length > 5000) throw new Error('历史排除名单已超过 5000 家，无法继续严格换批；请调整条件后重新智能匹配。')
  return matchController.start({ ...criteria, exclude_companies: excluded })
}
