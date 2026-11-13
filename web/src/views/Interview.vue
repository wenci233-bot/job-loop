<template>
  <div>
    <div class="page-title">面试准备</div>
    <el-alert v-if="prepTask.warning" :title="prepTask.warning" type="warning" :closable="false" />
    <el-alert v-if="prepTask.status === 'cancelled'" title="已停止生成，已有准备包已保留，可重新生成。" type="info" :closable="false" />

    <div class="page-card">
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <el-select v-model="picked" filterable placeholder="选择候选岗位或已创建的申请" style="width:360px"
                   :disabled="mocking || prepBusy || !!deletingMock">
          <el-option v-for="r in rows" :key="JSON.stringify([r.company, r.role])"
                     :label="`${r.company} · ${r.role}（${r.source === 'candidate' ? '候选岗位' : '已创建申请'}）${r.has_prep ? '（已有准备包）' : ''}`"
                     :value="r.company + '||' + r.role" />
        </el-select>
        <el-button v-if="prepBusy" type="danger" :loading="prepTask.stopping" @click="stopGeneration">{{ prepTask.stopping ? '正在停止…' : '停止生成' }}</el-button>
        <el-button type="primary" :disabled="!pickedApp || prepBusy" :loading="prepBusy" @click="generate">
          <el-icon v-if="!prepBusy" style="margin-right:3px"><MagicStick /></el-icon>
          {{ prepBusy ? `生成中 ${prepTask.elapsed}s` : (prep ? '重新生成准备包' : 'AI 生成准备包') }}
        </el-button>
        <el-button v-if="prep && !mocking" type="warning" @click="startMock">
          <el-icon style="margin-right:3px"><Microphone /></el-icon>开始模拟面试
        </el-button>
        <el-button v-if="mocking" type="danger" plain @click="endMock" :loading="reporting">
          <el-icon style="margin-right:3px"><SwitchButton /></el-icon>结束并出报告
        </el-button>
      </div>
      <div v-if="prepBusy" style="margin-top:12px;max-width:420px">
        <el-progress :percentage="Math.min(95, Math.round(prepTask.elapsed / 1.2))" :stroke-width="8" />
        <div class="muted" style="margin-top:2px">{{ prepTask.progress }} · {{ prepTask.elapsed }}s · 切换页面不会中断</div>
      </div>
    </div>

    <div class="page-card" v-if="prepBusy">
      <div style="display:flex;align-items:center;gap:14px">
        <el-icon color="#2f66f6" :size="26" class="is-loading"><Loading /></el-icon>
        <div style="flex:1">
          <div style="font-weight:600;font-size:14px">正在生成「{{ prepTask.role }}」的面试准备包</div>
          <el-progress :percentage="Math.min(95, Math.round(prepTask.elapsed / 1.2))" :stroke-width="8" style="margin-top:8px" />
          <div class="muted" style="margin-top:4px">已用时 {{ prepTask.elapsed }} 秒 · 切换页面不会中断</div>
        </div>
      </div>
    </div>

    <div class="page-card" v-if="savedMocks.length">
      <div class="sec-title" style="display:flex;align-items:center;gap:6px">
        <el-icon color="#7a5af5"><Tickets /></el-icon>历史模拟面试
        <span class="muted" style="margin-left:auto;font-weight:400">点击行展开完整对话与逐题分析</span>
      </div>
      <el-table :data="savedMocks" size="small" ref="mockTableRef" row-key="id"
                class="mock-table" @row-click="onMockRowClick">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="mock-detail">
              <div class="md-label">对话记录</div>
              <div class="md-chat">
                <div v-for="(m, i) in row.history" :key="i"
                     :class="['bubble', m.role === 'interviewer' ? 'bubble-ai' : 'bubble-user']">{{ m.text }}</div>
              </div>
              <div class="md-label" style="margin-top:16px">逐题分析</div>
              <div class="rp-q" v-for="(q, i) in row.report?.per_question || []" :key="i">
                <div class="rp-q-head">
                  <span class="score-pill" :style="{ background: scoreColor(q.score) + '18', color: scoreColor(q.score) }">{{ q.score }} 分</span>
                  <el-tag size="small" effect="dark" :type="q.verdict === '出色' ? 'success' : q.verdict === '达标' ? 'primary' : 'danger'">{{ q.verdict }}</el-tag>
                  <b class="rp-q-text">{{ q.question }}</b>
                </div>
                <div class="rp-ans" v-if="q.answer_summary"><b>我的回答：</b>{{ q.answer_summary }}</div>
                <template v-if="q.highlights?.length">
                  <div class="rp-block-title ok"><el-icon><CircleCheckFilled /></el-icon>不错点</div>
                  <div class="fb-point ok" v-for="(p, j) in q.highlights" :key="'h' + j">{{ p }}</div>
                </template>
                <template v-if="q.problems?.length">
                  <div class="rp-block-title bad"><el-icon><WarningFilled /></el-icon>问题</div>
                  <div class="fb-point bad" v-for="(p, j) in q.problems" :key="'p' + j">{{ p }}</div>
                </template>
                <div class="flag-row" v-if="q.off_topic || q.missed_key_points || q.wrong_facts">
                  <el-tag v-if="q.off_topic" size="small" type="danger" effect="plain">偏题</el-tag>
                  <el-tag v-if="q.missed_key_points" size="small" type="warning" effect="plain">没答到点</el-tag>
                  <el-tag v-if="q.wrong_facts" size="small" type="danger" effect="plain">答错</el-tag>
                </div>
                <div class="rp-improve" v-if="q.better_answer?.length">
                  <div class="rp-improve-title">更好的答法</div>
                  <div class="fb-point" v-for="(p, j) in q.better_answer" :key="'b' + j">{{ p }}</div>
                </div>
              </div>
              <el-empty v-if="!row.report?.per_question?.length" description="该场记录暂无逐题分析数据" :image-size="50" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.date) }}</template>
        </el-table-column>
        <el-table-column label="问答轮数" width="90" align="center">
          <template #default="{ row }">{{ row.rounds }} 轮</template>
        </el-table-column>
        <el-table-column label="总分" width="90" align="center">
          <template #default="{ row }">
            <span class="score-pill" :style="{ background: scoreColor(row.overall || 0) + '18', color: scoreColor(row.overall || 0) }">{{ row.overall ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最弱一题" min-width="220">
          <template #default="{ row }">
            <span class="weakest">{{ weakest(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }"><el-button size="small" text type="primary" :disabled="!!deletingMock" @click.stop="viewDebrief(row.id)">查看历史复盘</el-button><el-button size="small" text type="danger" :disabled="!!deletingMock" :loading="deletingMock === row.id" @click.stop="deleteSavedMock(row)">删除</el-button></template>
        </el-table-column>
      </el-table>
    </div>

    <template v-if="prep && !mocking">
      <div class="page-card" v-if="prep.checklist?.length">
        <div class="sec-title" style="display:flex;align-items:center;gap:6px">
          <el-icon color="#e07c1f"><Finished /></el-icon>面试前检查清单
        </div>
        <div class="check-strip">
          <div class="check-item" v-for="(c, i) in prep.checklist" :key="i">
            <el-icon color="#2f66f6"><CircleCheckFilled /></el-icon>{{ c }}
          </div>
        </div>
      </div>

      <div class="page-card" v-for="layer in layersWithQ" :key="layer.key">
        <div class="layer-head">
          <span class="layer-badge" :style="{ background: layer.color + '18', color: layer.color }">{{ layer.key }}</span>
          <b>{{ layer.label }}</b>
        </div>
        <div class="q-card" v-for="(q, i) in layer.questions" :key="i">
          <div class="q-main" @click="q.open = !q.open">
            <el-icon class="q-arrow" :class="{ open: q.open }"><ArrowRight /></el-icon>
            <div style="flex:1;min-width:0">
              <div class="q-text"><span class="q-badge q">Q</span>{{ q.question }}</div>
              <div class="q-intent"><el-icon><Aim /></el-icon>{{ q.intent }}</div>
            </div>
            <el-tag v-if="q.category === '场景'" size="small" type="warning" effect="plain">场景题</el-tag>
            <el-tag v-else size="small" effect="plain" type="info">{{ q.category }}</el-tag>
          </div>
          <el-collapse-transition>
            <div v-show="q.open" class="q-body">
              <div class="q-sub"><span class="q-badge a">A</span>可直接使用的答题要点（85-90 分版）</div>
              <div class="q-point" v-for="(p, j) in q.answer_points" :key="j">{{ p }}</div>
              <template v-if="q.insight_points?.length">
                <div class="q-sub insight"><el-icon color="#7a5af5"><Lightbulb /></el-icon>启发点 · 结合自己经历再拓展</div>
                <div class="insight-line" v-for="(p, j) in q.insight_points" :key="'i' + j">{{ p }}</div>
              </template>
              <template v-if="q.followups?.length">
                <div class="q-sub" style="margin-top:10px">追问链（提前备好下钻）</div>
                <div class="q-chain">
                  <span class="chain-item" v-for="(f, j) in q.followups" :key="j">
                    <span class="chain-step">{{ j + 2 }}</span>{{ f }}
                  </span>
                </div>
              </template>
              <div class="q-source">来源：{{ q.source || '档案' }}</div>
            </div>
          </el-collapse-transition>
        </div>
      </div>
    </template>

    <div class="page-card" v-if="mocking">
      <div class="sec-title" style="display:flex;align-items:center;gap:6px">
        <el-icon color="#2f66f6"><ChatDotRound /></el-icon>模拟面试 · {{ pickedApp?.company }} {{ pickedApp?.role }}
      </div>
      <div class="chat-box" ref="chatBoxRef">
        <div v-for="(m, i) in mockHistory" :key="i"
             :class="['bubble', m.role === 'interviewer' ? 'bubble-ai' : 'bubble-user']">
          {{ m.text }}
        </div>
        <div v-if="thinking" class="bubble bubble-ai bubble-thinking">面试官正在考虑下一个问题…</div>
      </div>
      <div style="display:flex;gap:10px;margin-top:10px">
        <el-input v-model="draft" type="textarea" :rows="2" :disabled="thinking || mockEnded"
                  placeholder="以候选人的身份回答（回答完面试官会继续追问）" @keydown.ctrl.enter="reply" />
        <div style="display:flex;flex-direction:column;gap:8px">
          <el-button type="primary" :disabled="!draft.trim() || thinking || mockEnded" @click="reply">发送</el-button>
          <el-button :disabled="thinking" @click="endMock" :loading="reporting">结束</el-button>
        </div>
      </div>
    </div>

    <div class="page-card" v-if="report">
      <div style="display:flex;justify-content:flex-end;margin-bottom:12px">
        <el-button type="primary" plain :disabled="!savedMockId || !report._saved" @click="viewDebrief(savedMockId)">查看历史复盘</el-button>
      </div>
      <div class="report-top">
        <div class="report-score" :style="{ color: scoreColor(report.overall) }">{{ report.overall }}</div>
        <div>
          <el-tag :type="report.overall >= 75 ? 'success' : report.overall >= 55 ? 'warning' : 'danger'" effect="dark">
            {{ report.overall >= 75 ? '表现良好' : report.overall >= 55 ? '尚需打磨' : '需要加练' }}
          </el-tag>
          <div class="muted" style="margin-top:4px;max-width:640px">{{ report.advice }}</div>
          <div class="saved-hint" v-if="report._saved">
            <el-icon><CircleCheckFilled /></el-icon>{{ report._debriefSynced ? '本场记录已自动加入历史模拟面试和历史复盘' : '本场记录已保存，历史复盘将在打开时自动同步' }}
          </div>
        </div>
      </div>

      <div class="rp-q" v-for="(q, i) in report.per_question" :key="i">
        <div class="rp-q-head">
          <span class="score-pill" :style="{ background: scoreColor(q.score) + '18', color: scoreColor(q.score) }">{{ q.score }} 分</span>
          <el-tag size="small" effect="dark" :type="q.verdict === '出色' ? 'success' : q.verdict === '达标' ? 'primary' : 'danger'">{{ q.verdict }}</el-tag>
          <b class="rp-q-text">{{ q.question }}</b>
        </div>
        <div class="rp-ans" v-if="q.answer_summary"><b>我的回答：</b>{{ q.answer_summary }}</div>
        <template v-if="q.highlights?.length">
          <div class="rp-block-title ok"><el-icon><CircleCheckFilled /></el-icon>不错点</div>
          <div class="fb-point ok" v-for="(p, j) in q.highlights" :key="'h' + j">{{ p }}</div>
        </template>
        <template v-if="q.problems?.length">
          <div class="rp-block-title bad"><el-icon><WarningFilled /></el-icon>问题</div>
          <div class="fb-point bad" v-for="(p, j) in q.problems" :key="'p' + j">{{ p }}</div>
        </template>
        <div class="flag-row" v-if="q.off_topic || q.missed_key_points || q.wrong_facts">
          <el-tag v-if="q.off_topic" size="small" type="danger" effect="plain">偏题</el-tag>
          <el-tag v-if="q.missed_key_points" size="small" type="warning" effect="plain">没答到点</el-tag>
          <el-tag v-if="q.wrong_facts" size="small" type="danger" effect="plain">答错</el-tag>
        </div>
        <div class="rp-improve" v-if="q.better_answer?.length">
          <div class="rp-improve-title">更好的答法</div>
          <div class="fb-point" v-for="(p, j) in q.better_answer" :key="'b' + j">{{ p }}</div>
        </div>
      </div>

      <div class="flag-row" style="margin-top:12px" v-if="report.off_topic || report.missed_key_points || report.wrong_facts">
        <span class="muted">全场标记：</span>
        <el-tag v-if="report.off_topic" size="small" type="danger" effect="plain">存在偏题</el-tag>
        <el-tag v-if="report.missed_key_points" size="small" type="warning" effect="plain">存在没答到点</el-tag>
        <el-tag v-if="report.wrong_facts" size="small" type="danger" effect="plain">存在答错</el-tag>
      </div>

      <div class="rp-cols">
        <div v-if="report.strengths?.length">
          <div class="eval-sub"><el-icon color="#18a058"><CircleCheckFilled /></el-icon>全局亮点</div>
          <div class="point-line good" v-for="(s, i) in report.strengths" :key="i">{{ s }}</div>
        </div>
        <div v-if="report.weaknesses?.length">
          <div class="eval-sub"><el-icon color="#d93025"><WarningFilled /></el-icon>共性问题</div>
          <div class="point-line warn" v-for="(w, i) in report.weaknesses" :key="i">{{ w }}</div>
        </div>
      </div>

      <template v-if="report.star_proposals?.length">
        <div class="fb-sub"><el-icon color="#18a058"><StarFilled /></el-icon>STAR 素材入库提议</div>
        <div class="fb-item" v-for="(s, i) in report.star_proposals" :key="'s' + i">
          <b>{{ s.title }}</b>
          <p>{{ s.content }}</p>
          <el-button size="small" type="success" plain :disabled="s._done" @click="acceptStar(s)">
            {{ s._done ? '已入库' : '接受入库' }}
          </el-button>
        </div>
      </template>
      <template v-if="report.repeated?.length">
        <div class="fb-sub"><el-icon color="#d93025"><Bell /></el-icon>重复考点</div>
        <div class="stuck-tags">
          <el-tag v-for="(r, i) in report.repeated" :key="i" type="danger" effect="plain">
            {{ r.topic }} · 已出现 {{ r.count }} 次
          </el-tag>
        </div>
      </template>
    </div>

    <div class="page-card" v-if="!prep && !prepBusy && !mocking && !savedMocks.length">
      <el-empty description="选择一个候选岗位或申请，AI 生成有层次的面试准备包" :image-size="90" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { ElCollapseTransition, ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import { useRouter } from 'vue-router'
import { prepTask, startPrepGeneration, stopPrepTask, loadPrepId, clearPrepTask, onPrepDone, onPrepResumed } from '../store'

const LAYERS = {
  L1: { key: 'L1', label: '基础介绍题', desc: '简历必问：项目是什么、你的角色', color: '#2f66f6' },
  L2: { key: 'L2', label: '项目深挖题', desc: '追问细节：为什么这么选、数据怎么来的', color: '#7a5af5' },
  L3: { key: 'L3', label: '压力质疑题', desc: '挑战方案、边界条件、如果重来', color: '#e07c1f' },
  L4: { key: 'L4', label: '岗位匹配题', desc: '你的经验如何迁移到对方业务', color: '#18a058' },
}

const rows = ref([])
const picked = ref('')
const prep = ref(null)
const mocking = ref(false)
const thinking = ref(false)
const reporting = ref(false)
const mockEnded = ref(false)
const mockHistory = ref([])
const draft = ref('')
const report = ref(null)
const chatBoxRef = ref()
const savedMocks = ref([])
const router = useRouter()
function viewDebrief(sessionId) {
  router.push({ path: '/debrief', query: { mock_session: sessionId } })
}
const deletingMock = ref(''), savedMockId = ref('')
let mockLoadVersion = 0
function onMockRowClick(row, column, event) {
  if (event?.target?.closest?.('.el-button, .el-table__expand-icon')) return
  mockTableRef.value?.toggleRowExpansion(row)
}
async function deleteSavedMock(row) {
  if (deletingMock.value || !pickedApp.value) return
  const target = { ...pickedApp.value, session_id: row.id }
  const selection = picked.value
  deletingMock.value = row.id
  try {
    await ElMessageBox.confirm(`确定删除 ${fmtTime(row.date)} 的这场模拟面试？该场完整对话和逐题分析将被删除，其他场次和准备包会保留。`, '删除历史模拟面试', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
    ++mockLoadVersion
    const result = await api.post('/interview/mock/delete', { ...target, confirmed: true })
    if (picked.value === selection) {
      savedMocks.value = savedMocks.value.filter(item => item.id !== target.session_id)
      if (savedMockId.value === target.session_id && report.value) report.value._saved = false
    }
    ElMessage.success(result.deleted ? '该场模拟面试已删除' : '该场记录已不存在，列表已更新')
  } catch(e) { if (e !== 'cancel' && e !== 'close') ElMessage.error(e.message) }
  finally { deletingMock.value = '' }
}

const pickedApp = computed(() => {
  if (!picked.value) return null
  const [company, role] = picked.value.split('||')
  return { company, role }
})

const layersWithQ = computed(() => {
  if (!prep.value) return []
  return Object.values(LAYERS)
    .map(l => ({ ...l, questions: prep.value.questions.filter(q => q.layer === l.key).map(q => reactive({ ...q, open: false })) }))
    .filter(l => l.questions.length)
})

const scoreColor = (s) => (s >= 75 ? '#18a058' : s >= 55 ? '#e07c1f' : '#d93025')
const fmtTime = (d) => (d || '').replace('T', ' ')

const weakest = (row) => {
  const qs = (row.report?.per_question || []).filter(q => typeof q.score === 'number')
  if (!qs.length) return '—'
  const w = qs.reduce((a, b) => (b.score < a.score ? b : a))
  return `${w.score} 分 · ${w.question}`
}

async function refresh() {
  try { rows.value = (await api.get('/interview/applications')).rows }
  catch (e) { ElMessage.error(e.message) }
}
let activatedOnce = false
onActivated(() => {
  if (activatedOnce) refresh()
  activatedOnce = true
})

async function loadSavedMocks() {
  const version = ++mockLoadVersion, selection = picked.value
  if (!pickedApp.value) { savedMocks.value = []; return }
  const q = `company=${encodeURIComponent(pickedApp.value.company)}&role=${encodeURIComponent(pickedApp.value.role)}`
  try {
    const data = await api.get(`/interview/mock/list?${q}`)
    if (version === mockLoadVersion && selection === picked.value) savedMocks.value = data.sessions
  } catch { if (version === mockLoadVersion && selection === picked.value) savedMocks.value = [] }
}

const prepBusy = computed(() => ['starting', 'running'].includes(prepTask.status))
async function stopGeneration() { try { await stopPrepTask(); if (prepTask.status === 'cancelled') ElMessage.info('已停止生成，已有准备包已保留') } catch(e) { ElMessage.error(e.message) } }
async function generate() {
  if (!pickedApp.value || prepBusy.value) return
  report.value = null
  try {
    await startPrepGeneration({ company: pickedApp.value.company, role: pickedApp.value.role })
  } catch (e) { ElMessage.error(e.message) }
}

// 生成完成（App 级全局回调）：与本页选中岗位一致时加载
onPrepDone(({ company, role, prep: p }) => {
  if (pickedApp.value && pickedApp.value.company === company && pickedApp.value.role === role) {
    prep.value = p
    ElMessage.success(`准备包已生成：${p.questions.length} 题`)
  }
  refresh()
})
onPrepResumed((saved) => {
  if (!picked.value) picked.value = saved.company + '||' + saved.role
})

// 切换岗位时：重置模拟状态、加载对应准备包与历史模拟记录
watch(picked, (v) => {
  if (mocking.value || mockHistory.value.length) {
    mocking.value = false
    mockHistory.value = []
    mockEnded.value = false
    thinking.value = false
  }
  prep.value = null
  report.value = null
  savedMockId.value = ''
  savedMocks.value = []
  if (!v) return
  const [company, role] = v.split('||')
  api.get(`/interview/prep?company=${encodeURIComponent(company)}&role=${encodeURIComponent(role)}`)
    .then(d => { if (d.prep && picked.value === v) prep.value = d.prep })
    .catch(() => {})
  loadSavedMocks()
})

async function startMock() {
  savedMockId.value = ''
  mocking.value = true
  mockHistory.value = []
  report.value = null
  mockEnded.value = false
  thinking.value = true
  try {
    const d = await api.post('/interview/mock', { ...pickedApp.value, history: [] })
    mockHistory.value.push({ role: 'interviewer', text: d.question })
    if (d.end) mockEnded.value = true
  } catch (e) { ElMessage.error(e.message); mocking.value = false } finally { thinking.value = false }
  scrollChat()
}

async function reply() {
  const text = draft.value.trim()
  if (!text) return
  mockHistory.value.push({ role: 'candidate', text })
  draft.value = ''
  thinking.value = true
  scrollChat()
  try {
    const d = await api.post('/interview/mock', { ...pickedApp.value, history: mockHistory.value })
    mockHistory.value.push({ role: 'interviewer', text: d.question })
    if (d.end) mockEnded.value = true
  } catch (e) { ElMessage.error(e.message) } finally { thinking.value = false }
  scrollChat()
}

async function endMock() {
  const answers = mockHistory.value.filter(x => x.role === 'candidate').length
  if (!answers) { ElMessage.warning('至少回答一个问题再出报告'); return }
  reporting.value = true
  try {
    report.value = await api.post('/interview/report', { ...pickedApp.value, history: mockHistory.value })
    // 自动存档本场模拟面试（完整对话 + 逐题报告），供历史回看
    try {
      const saved = await api.post('/interview/mock/save', { ...pickedApp.value, history: mockHistory.value, report: report.value })
      savedMockId.value = saved.session.id
      report.value._saved = true
      report.value._debriefSynced = saved.debrief_synced === true
      if (saved.sync_warning) ElMessage.warning('模拟记录已保存，复盘同步待重试：' + saved.sync_warning)
    } catch { /* 存档失败不影响报告展示 */ }
    mocking.value = false
    await loadSavedMocks()
    if (report.value.stuck_points?.length) {
      ElMessage({ message: '卡壳点已记录，可在技能提升里跟进', type: 'info' })
    }
  } catch (e) { ElMessage.error(e.message) } finally { reporting.value = false }
}

function scrollChat() {
  nextTick(() => { if (chatBoxRef.value) chatBoxRef.value.scrollTop = chatBoxRef.value.scrollHeight })
}

onMounted(async () => {
  await refresh()
  if (!picked.value) {
    const saved = loadPrepId()
    if (saved) picked.value = saved.company + '||' + saved.role
  }
  if (picked.value) {
    const [company, role] = picked.value.split('||')
    api.get(`/interview/prep?company=${encodeURIComponent(company)}&role=${encodeURIComponent(role)}`)
      .then(d => { if (d.prep && !prep.value) prep.value = d.prep })
      .catch(() => {})
  } else {
    const first = rows.value.find(r => r.has_prep)
    if (first) picked.value = first.company + '||' + first.role
  }
})
</script>

<style scoped>
.sec-title { font-size: 14.5px; font-weight: 600; margin-bottom: 12px; }
.check-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; }
.check-item { display: flex; gap: 6px; align-items: flex-start; background: #f6f9ff; border: 1px solid #e3eaf8; border-radius: 8px; padding: 8px 10px; font-size: 12.5px; color: #3d4757; line-height: 1.6; }
.layer-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.layer-badge { border-radius: 6px; padding: 2px 8px; font-size: 12px; font-weight: 600; }
.layer-head b { font-size: 14px; }
.q-card { border: 1px solid #e8ecf4; border-radius: 9px; margin-bottom: 8px; overflow: hidden; transition: border-color .2s ease; }
.q-card:hover { border-color: #c9d6f2; }
.q-main { display: flex; gap: 10px; align-items: flex-start; padding: 11px 12px; cursor: pointer; }
.q-arrow { margin-top: 3px; color: #98a1b0; transition: transform .2s ease; }
.q-arrow.open { transform: rotate(90deg); }
.q-text { font-size: 13.5px; font-weight: 500; color: #1f2733; line-height: 1.6; display: flex; align-items: flex-start; gap: 6px; }
.q-badge { flex-shrink: 0; width: 18px; height: 18px; border-radius: 5px; display: inline-grid; place-items: center; font-size: 11px; font-weight: 700; margin-top: 1px; }
.q-badge.q { background: #2f66f6; color: #fff; }
.q-badge.a { background: #18a058; color: #fff; }
.q-intent { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #8a93a3; margin-top: 3px; }
.q-body { background: #fafbfe; border-top: 1px solid #eef1f7; padding: 10px 14px 12px 34px; }
.q-sub { font-size: 12px; font-weight: 600; color: #5b6575; margin-bottom: 5px; display: flex; align-items: center; gap: 4px; }
.q-sub.insight { color: #7a5af5; }
.q-point { font-size: 12.5px; color: #3d4757; line-height: 1.75; padding-left: 12px; position: relative; }
.q-point::before { content: ""; position: absolute; left: 0; top: 9px; width: 5px; height: 5px; border-radius: 50%; background: #2f66f6; opacity: .55; }
.insight-line { font-size: 12.5px; color: #7a5af5; line-height: 1.75; background: #f6f3ff; border: 1px dashed #d8cefc; border-radius: 6px; padding: 6px 10px; margin-bottom: 5px; }
.q-chain { display: flex; flex-direction: column; gap: 5px; }
.chain-item { display: flex; gap: 7px; font-size: 12.5px; color: #5b6575; line-height: 1.6; align-items: baseline; }
.chain-step { flex-shrink: 0; width: 18px; height: 18px; border-radius: 50%; background: #eef2fb; color: #2f66f6; font-size: 11px; display: grid; place-items: center; }
.q-source { margin-top: 10px; font-size: 11.5px; color: #98a1b0; }
.chat-box { height: 380px; overflow-y: auto; background: #f6f8fc; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.bubble { max-width: 78%; padding: 10px 13px; border-radius: 12px; font-size: 13.5px; line-height: 1.7; white-space: pre-wrap; }
.bubble-ai { background: #fff; border: 1px solid #e4e8f0; border-left: 3px solid #2f66f6; align-self: flex-start; border-top-left-radius: 3px; }
.bubble-user { background: #2f66f6; color: #fff; align-self: flex-end; border-bottom-right-radius: 3px; }
.bubble-thinking { color: #98a1b0; font-size: 12.5px; }
.report-top { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.report-score { font-size: 40px; font-weight: 700; line-height: 1; }
.saved-hint { display: flex; align-items: center; gap: 4px; margin-top: 6px; font-size: 12px; color: #18a058; }
.rp-q { border: 1px solid #e8ecf4; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; }
.rp-q-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.rp-q-head b { font-size: 13.5px; color: #1f2733; }
.rp-q-text { flex: 1; min-width: 220px; }
.score-pill { display: inline-flex; align-items: center; justify-content: center; padding: 2px 10px; border-radius: 12px; font-weight: 700; font-size: 12.5px; font-variant-numeric: tabular-nums; flex-shrink: 0; }
.rp-ans { font-size: 12.5px; color: #3d4757; background: #f6f9ff; border-left: 3px solid #2f66f6; border-radius: 6px; padding: 7px 10px; margin-top: 8px; line-height: 1.65; }
.rp-block-title { display: flex; align-items: center; gap: 4px; font-size: 12.5px; font-weight: 600; margin: 10px 0 5px; }
.rp-block-title.ok { color: #18a058; }
.rp-block-title.bad { color: #d93025; }
.fb-point { font-size: 12.5px; color: #3d4757; line-height: 1.7; padding-left: 12px; position: relative; margin-bottom: 3px; }
.fb-point::before { content: ""; position: absolute; left: 0; top: 9px; width: 5px; height: 5px; border-radius: 50%; background: #e07c1f; }
.fb-point.ok::before { background: #18a058; }
.fb-point.ok { color: #1f7a4d; }
.fb-point.bad::before { background: #d93025; }
.fb-point.bad { color: #8f2b25; }
.flag-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.rp-improve { margin-top: 8px; background: #f8faff; border-radius: 8px; padding: 8px 12px; }
.rp-improve-title { font-size: 12px; font-weight: 600; color: #2f66f6; margin-bottom: 4px; }
.rp-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
@media (max-width: 760px) { .rp-cols { grid-template-columns: 1fr; } }
.eval-sub { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 600; margin: 10px 0 6px; }
.point-line { font-size: 12.5px; line-height: 1.7; padding-left: 20px; position: relative; }
.point-line.good { color: #1f7a4d; }
.point-line.warn { color: #a05a17; }
.fb-sub { display: flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 600; margin: 12px 0 8px; }
.fb-item { background: #fafbfe; border: 1px solid #eef1f7; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.fb-item p { font-size: 12.5px; color: #3d4757; line-height: 1.7; margin: 6px 0; }
.stuck-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.mock-table :deep(.el-table__row) { cursor: pointer; }
.mock-detail { padding: 8px 12px 12px; background: #fafbfe; }
.md-label { font-size: 12.5px; font-weight: 700; color: #5b6575; margin-bottom: 8px; }
.md-chat { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; background: #f6f8fc; border-radius: 8px; padding: 10px; }
.md-chat .bubble { max-width: 85%; font-size: 12.5px; padding: 8px 11px; }
.weakest { font-size: 12.5px; color: #5b6575; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
</style>
