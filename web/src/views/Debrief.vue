<template>
  <div>
    <div class="page-title">面试复盘</div>

    <div class="page-card">
      <el-select v-model="picked" placeholder="选择要复盘的申请" style="width:360px">
        <el-option v-for="r in rows" :key="r.company + r.role"
                   :label="`${r.company} · ${r.role}`" :value="r.company + '||' + r.role" />
      </el-select>
    </div>

    <div class="page-card">
      <div class="sec-title" style="display:flex;align-items:center;gap:6px">
        <el-icon color="#2f66f6"><ChatDotRound /></el-icon>面试问答记录
        <el-button size="small" text type="primary" @click="qa.push({ question: '', answer: '' })">
          <el-icon><Plus /></el-icon>添加一题
        </el-button>
      </div>
      <div class="raw-box">
        <el-input v-model="raw" type="textarea" :rows="3"
                  placeholder="懒人模式：把面试经过口述粘贴到这里（面试官问了什么、你怎么答的），AI 自动整理成问答对" />
        <div style="margin-top:8px">
          <el-button size="small" type="primary" plain :loading="organizing" :disabled="!raw.trim()" @click="organize">
            <el-icon style="margin-right:3px"><MagicStick /></el-icon>AI 整理成问答对
          </el-button>
        </div>
      </div>
      <div class="qa-entry" v-for="(q, i) in qa" :key="i">
        <div class="qa-head">
          <span class="qa-no">Q{{ i + 1 }}</span>
          <el-input v-model="q.question" placeholder="面试官的问题（尽量原话）" />
          <el-button text type="danger" @click="qa.splice(i, 1)">删除</el-button>
        </div>
        <div class="qa-answer-label"><el-icon color="#18a058"><EditPen /></el-icon>我的回答</div>
        <el-input v-model="q.answer" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }"
                  class="qa-answer" placeholder="你当时是怎么回答的（越完整，AI 评价越准）" />
      </div>
      <el-empty v-if="!qa.length" description="点「添加一题」记录面试官的问题和你的回答" :image-size="60" />

      <div style="margin-top:16px">
        <div class="sec-title" style="display:flex;align-items:center;gap:6px">
          <el-icon color="#e07c1f"><View /></el-icon>面试官关注点
        </div>
        <el-checkbox-group v-model="form.focus">
          <el-checkbox v-for="f in FOCUS" :key="f" :value="f" :label="f" />
        </el-checkbox-group>
        <el-input v-model="focusExtra" placeholder="其他关注点（回车添加）" style="width:260px;margin-top:8px"
                  @keydown.enter="addFocus" />
      </div>

      <div style="margin-top:16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <el-button type="primary" :loading="reviewing" :disabled="!validQaCount" @click="review">
          <el-icon style="margin-right:3px"><MagicStick /></el-icon>AI 逐题评价与改进{{ validQaCount ? `（${validQaCount} 题）` : '' }}
        </el-button>
        <div style="display:flex;align-items:center;gap:8px">
          <span class="muted">整体自评</span>
          <el-rate v-model="form.rating" />
        </div>
        <el-input v-model="form.note" placeholder="备注（可选，如 HR 反馈、流程感受）" style="width:300px" />
      </div>
    </div>

    <div class="page-card" v-if="report">
      <div class="report-top">
        <div class="report-score" :style="{ color: scoreColor(report.overall) }">{{ report.overall }}</div>
        <div>
          <el-tag :type="report.overall >= 75 ? 'success' : report.overall >= 55 ? 'warning' : 'danger'" effect="dark">
            {{ report.overall >= 75 ? '表现良好' : report.overall >= 55 ? '尚需打磨' : '需要加练' }}
          </el-tag>
          <div class="muted" style="margin-top:4px">{{ report.advice }}</div>
        </div>
      </div>

      <div class="rp-q" v-for="(q, i) in report.per_question" :key="i">
        <div class="rp-q-head">
          <el-tag size="small" :type="q.verdict === '出色' ? 'success' : q.verdict === '达标' ? 'primary' : 'danger'" effect="dark">
            {{ q.verdict }}
          </el-tag>
          <b>{{ q.question }}</b>
        </div>
        <div class="rp-my-answer" v-if="myAnswerOf(q)">我的回答：{{ myAnswerOf(q) }}</div>
        <div class="rp-eval">{{ q.evaluation }}</div>
        <div class="rp-improve" v-if="q.improved_points?.length">
          <div class="rp-improve-title">改进后的回答要点</div>
          <div class="fb-point" v-for="(p, j) in q.improved_points" :key="j">{{ p }}</div>
        </div>
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

      <div style="margin-top:16px;display:flex;gap:10px;align-items:center">
        <el-button type="success" :loading="saving" @click="save">
          <el-icon style="margin-right:3px"><Select /></el-icon>确认存档本次复盘
        </el-button>
        <span class="muted">存档后进入历史复盘，供校准与技能提升使用</span>
      </div>
    </div>

    <div class="page-card" v-if="history.length">
      <div class="sec-title" style="display:flex;align-items:center;gap:6px">
        <el-icon color="#7a5af5"><List /></el-icon>历史复盘
      </div>
      <el-table ref="hisTableRef" :data="history" size="small" class="clickable-rows"
                :row-class-name="row => 'his-row'" @row-click="toggleHistory">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="his-detail">
              <div class="his-summary" v-if="row.review">
                <span class="score-pill" :style="{ background: scoreColor(row.review.overall || 0) + '18', color: scoreColor(row.review.overall || 0) }">{{ row.review.overall ?? '—' }} 分</span>
                <el-tag size="small" effect="dark" :type="row.review.overall >= 75 ? 'success' : row.review.overall >= 55 ? 'warning' : 'danger'">
                  {{ row.review.overall >= 75 ? '表现良好' : row.review.overall >= 55 ? '尚需打磨' : '需要加练' }}
                </el-tag>
                <span class="his-advice" v-if="row.review.advice">{{ row.review.advice }}</span>
              </div>
              <div class="his-block" v-for="(item, i) in row.qa || []" :key="'q' + i">
                <div class="his-q"><span class="qa-no">Q{{ i + 1 }}</span><span>{{ item.question }}</span></div>
                <div class="his-a" v-if="item.answer">我的回答：{{ item.answer }}</div>
                <div class="his-eval" v-for="(rq, j) in reviewFor(row, item.question)" :key="'e' + j"
                     :class="rq.verdict === '出色' ? 'ok' : rq.verdict === '需改进' ? 'bad' : ''">
                  <div class="his-eval-head">
                    <el-tag size="small" effect="dark" :type="rq.verdict === '出色' ? 'success' : rq.verdict === '达标' ? 'primary' : 'danger'">
                      {{ rq.verdict }}
                    </el-tag>
                    <span class="his-eval-label">AI 逐题评价</span>
                  </div>
                  <div class="his-eval-text">{{ rq.evaluation }}</div>
                  <template v-if="rq.improved_points?.length">
                    <div class="his-improve-title">改进后的回答要点</div>
                    <div class="his-improve" v-for="(pt, k) in rq.improved_points" :key="k">{{ pt }}</div>
                  </template>
                </div>
              </div>
              <div class="his-block" v-if="row.focus?.length">
                <span class="blk-label">面试官关注点</span>
                <div class="stuck-tags"><el-tag v-for="(f, i) in row.focus" :key="i" size="small" effect="plain">{{ f }}</el-tag></div>
              </div>
              <div class="his-block" v-if="row.note">
                <span class="blk-label purple">备注</span>
                <div class="his-note">{{ row.note }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="日期" width="100" />
        <el-table-column prop="company_role" label="申请" min-width="170" />
        <el-table-column label="轮次" width="60">
          <template #default="{ row }">{{ row.round }}</template>
        </el-table-column>
        <el-table-column label="题目" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ (row.qa || []).map(x => x.question).join('；') || '—' }}</template>
        </el-table-column>
        <el-table-column label="得分" width="80">
          <template #default="{ row }">
            <span class="score-pill" :style="{ background: scoreColor(row.review?.overall || 0) + '18', color: scoreColor(row.review?.overall || 0) }">{{ row.review?.overall ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rating" label="自评" width="60" />
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const FOCUS = ['项目深挖', '技术基础', '系统设计', '加班文化', '稳定性', '薪资期望', '到岗时间', '团队协作', '学历背景']

const rows = ref([])
const picked = ref('')
const reviewing = ref(false)
const saving = ref(false)
const organizing = ref(false)
const report = ref(null)
const history = ref([])
const focusExtra = ref('')
const raw = ref('')
function addFocus() {
  const v = focusExtra.value.trim()
  if (v && !form.focus.includes(v)) form.focus.push(v)
  focusExtra.value = ''
}

async function organize() {
  const text = raw.value.trim()
  if (text.length < 20) { ElMessage.warning('口述内容太短（至少 20 字）'); return }
  if (validQaCount.value) {
    try {
      await ElMessageBox.confirm('当前已填写的问答将被 AI 整理结果覆盖，继续？', '覆盖确认',
                                { type: 'warning', confirmButtonText: '覆盖', cancelButtonText: '取消' })
    } catch { return }
  }
  organizing.value = true
  try {
    const d = await api.post('/debrief/organize', { raw: text })
    qa.splice(0, qa.length, ...((d.qa || []).map(x => ({ question: x.question || '', answer: x.answer || '' }))))
    for (const f of d.focus || []) if (f && !form.focus.includes(f)) form.focus.push(f)
    raw.value = ''
    ElMessage.success(`已整理出 ${qa.length} 道问答，请核对后点击「AI 逐题评价与改进」`)
  } catch (e) { ElMessage.error(e.message) } finally { organizing.value = false }
}

const qa = reactive([])
const form = reactive({ focus: [], rating: 3, note: '' })

const validQaCount = computed(() => qa.filter(x => String(x.question || '').trim()).length)
const pickedApp = computed(() => {
  if (!picked.value) return null
  const [company, role] = picked.value.split('||')
  return { company, role }
})

// 切换申请时清空未存档的问答/报告（防跨岗位数据混淆）
watch(picked, () => {
  qa.splice(0, qa.length)
  report.value = null
  form.focus = []
  form.rating = 3
  form.note = ''
  raw.value = ''
})

const scoreColor = (s) => (s >= 75 ? '#18a058' : s >= 55 ? '#e07c1f' : '#d93025')
const myAnswerOf = (q) => {
  const qt = String(q.question || '').trim()
  let m = qa.find(x => x.question === q.question)
  if (!m) m = qa.find(x => qt && (x.question.includes(qt) || qt.includes(x.question.trim())))
  if (!m) m = qa.find(x => {  // 再退一步：取问题前 12 字做包含匹配
    const head = qt.slice(0, 12)
    return head.length >= 6 && x.question.includes(head)
  })
  return m?.answer || ''
}

async function review() {
  if (!pickedApp.value) { ElMessage.warning('请先选择要复盘的申请'); return }
  if (!qa.some(x => String(x.question || '').trim())) { ElMessage.warning('请至少填写一道面试题'); return }
  reviewing.value = true
  try {
    report.value = await api.post('/debrief/review', { ...pickedApp.value, qa: [...qa], focus: form.focus })
  } catch (e) { ElMessage.error(e.message) } finally { reviewing.value = false }
}

async function save() {
  if (!pickedApp.value) { ElMessage.warning('请先选择要复盘的申请'); return }
  if (!report.value) { ElMessage.warning('请先完成 AI 评价再存档'); return }
  saving.value = true
  try {
    await api.post('/debrief/save', {
      ...pickedApp.value, qa: [...qa], focus: form.focus,
      rating: form.rating, note: form.note, review: report.value,
    })
    ElMessage.success('复盘已存档')
    qa.splice(0, qa.length)
    report.value = null
    form.focus = []
    form.rating = 3
    form.note = ''
    await refresh()
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}

async function acceptStar(s) {
  try {
    const d = await api.get('/profile')
    d.stars.push({ title: s.title, content: s.content, source: '复盘实战' })
    await api.put('/profile', { candidate: d.candidate, stars: d.stars })
    s._done = true
    ElMessage.success('已加入面试素材库')
  } catch (e) { ElMessage.error(e.message) }
}

async function refresh() {
  rows.value = (await api.get('/interview/applications')).rows
  history.value = (await api.get('/debrief/list')).rounds
}

const hisTableRef = ref()
function toggleHistory(row) {
  hisTableRef.value?.toggleRowExpansion(row)
}
function reviewFor(row, question) {
  const list = row.review?.per_question || []
  const qt = String(question || '').trim()
  let m = list.find(x => x.question === question)
  if (!m) m = list.find(x => qt && (x.question.includes(qt) || qt.includes(x.question.trim())))
  if (!m) m = list.find(x => { const head = qt.slice(0, 12); return head.length >= 6 && x.question.includes(head) })
  return m ? [m] : []
}

onMounted(refresh)
</script>

<style scoped>
.sec-title { font-size: 14.5px; font-weight: 600; margin-bottom: 12px; }
.raw-box { background: #f8faff; border: 1px dashed #c9d6f2; border-radius: 10px; padding: 12px; margin-bottom: 14px; }
.qa-entry { border: 1px solid #e8ecf4; border-radius: 10px; padding: 12px; margin-bottom: 10px; background: #fff; }
.qa-head { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.qa-head .el-input { flex: 1; }
.qa-no { flex-shrink: 0; padding: 0 8px; height: 22px; border-radius: 5px; background: #2f66f6; color: #fff; font-size: 12px; font-weight: 600; display: inline-grid; place-items: center; }
.qa-answer { margin-top: 6px; }
.qa-answer-label { display: flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; color: #18a058; margin: 10px 0 4px; }
.report-top { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.report-score { font-size: 40px; font-weight: 700; line-height: 1; }
.rp-q { border: 1px solid #e8ecf4; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; }
.rp-q-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.rp-q-head b { font-size: 13.5px; color: #1f2733; }
.rp-my-answer { font-size: 12.5px; color: #3d6b52; background: #f2f9f5; border-left: 3px solid #18a058; border-radius: 6px; padding: 7px 10px; margin-top: 8px; line-height: 1.6; }
.rp-eval { font-size: 13px; color: #3d4757; line-height: 1.8; margin-top: 8px; padding-top: 6px; border-top: 1px dashed #eef1f7; }
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
.fb-point { font-size: 12.5px; color: #3d4757; line-height: 1.7; padding-left: 12px; position: relative; }
.fb-point::before { content: ""; position: absolute; left: 0; top: 9px; width: 5px; height: 5px; border-radius: 50%; background: #e07c1f; }
.stuck-tags { display: flex; flex-wrap: wrap; gap: 6px; }
:deep(.his-row) { cursor: pointer; }
:deep(.his-row:hover td) { background: #f5f8ff; }
.his-detail { padding: 6px 14px 12px; max-width: 920px; }
.his-summary { display: flex; align-items: center; gap: 10px; background: #f8faff; border: 1px solid #e3eaf8; border-radius: 10px; padding: 10px 14px; margin-bottom: 14px; flex-wrap: wrap; }
.his-advice { flex: 1; min-width: 260px; font-size: 12.5px; color: #5b6575; line-height: 1.6; }
.score-pill { display: inline-flex; align-items: center; justify-content: center; padding: 2px 10px; border-radius: 12px; font-weight: 700; font-size: 12.5px; font-variant-numeric: tabular-nums; }
.his-block { margin-bottom: 18px; }
.his-q { display: flex; align-items: flex-start; gap: 7px; font-size: 13.5px; font-weight: 600; color: #1f2733; line-height: 1.6; margin-bottom: 7px; }
.his-a { font-size: 12.5px; color: #3d6b52; background: #f2f9f5; border-left: 3px solid #18a058; border-radius: 6px; padding: 7px 10px; line-height: 1.65; }
.his-eval { margin-top: 10px; background: #fff; border: 1px solid #e8ecf4; border-left: 3px solid #2f66f6; border-radius: 8px; padding: 10px 14px; }
.his-eval.ok { border-left-color: #18a058; }
.his-eval.bad { border-left-color: #d93025; }
.his-eval-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.his-eval-label { font-size: 11.5px; font-weight: 600; color: #8a93a3; }
.his-eval-text { font-size: 13px; color: #3d4757; line-height: 1.8; }
.his-improve-title { margin: 9px 0 5px; font-size: 12px; font-weight: 600; color: #2f66f6; }
.his-improve { font-size: 12.5px; color: #3d4757; line-height: 1.7; padding-left: 12px; position: relative; margin-bottom: 4px; }
.his-improve::before { content: ""; position: absolute; left: 0; top: 9px; width: 5px; height: 5px; border-radius: 50%; background: #2f66f6; opacity: .55; }
.his-note { font-size: 12.5px; color: #3d4757; line-height: 1.6; }
</style>
