<template>
  <div>
    <div class="page-title">投递中心</div>
    <el-alert v-if="evalTask.warning" :title="evalTask.warning" type="warning" :closable="false" />
    <el-alert v-if="evalTask.status === 'cancelled'" title="已停止评估，已完成的评分已保留，可重新选择岗位评估。" type="info" :closable="false" />

    <div class="stats-line">
      <div class="stat-card" v-for="st in statCards" :key="st.label" :style="{ '--ac': st.color }">
        <span class="chip" :style="{ background: st.color + '1a', color: st.color }">
          <el-icon :size="17"><component :is="st.icon" /></el-icon>
        </span>
        <div>
          <div class="stat-num num-tabular">{{ st.value }}</div>
          <div class="muted">{{ st.label }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="sec-head-row">
        <h3 style="display:flex;align-items:center;gap:6px"><el-icon color="#2f66f6"><Filter /></el-icon>候选岗位</h3>
        <template v-if="evalBusy">
          <el-progress :percentage="Math.min(96, Math.round((evalTask.done / Math.max(evalTask.total,1)) * 100))"
                       :stroke-width="8" style="flex:1;min-width:180px;max-width:300px" />
          <span class="muted">正在评估 {{ evalTask.current || '…' }}（{{ evalTask.done }}/{{ evalTask.total }}）</span>
        </template>
        <span class="management-actions" style="margin-left:auto">
          <el-button size="small" type="primary" plain @click="addJobOpen = true">添加岗位</el-button>
          <el-button size="small" type="danger" plain :disabled="!selectedRows.length || evalBusy || !!scoring || deleting" @click="remove(selectedRows)">删除选中（{{ selectedRows.length }}）</el-button>
          <el-button v-if="evalBusy" type="danger" size="small" :loading="evalTask.stopping" @click="stopEvaluation">{{ evalTask.stopping ? '正在停止…' : '停止评估' }}</el-button>
          <el-button type="primary" size="small" :disabled="!selectedIds.length || evalBusy"
                     :loading="evalBusy" @click="batchEval">
            <el-icon style="margin-right:3px"><MagicStick /></el-icon>AI 批量评估（{{ selectedIds.length }}）
          </el-button>
        </span>
      </div>
      <el-table ref="poolTableRef" :data="entries" size="small" class="clickable-rows"
                empty-text="暂无候选岗位 —— 去岗位收集贴 JD 或跑 AI 智能匹配" row-key="id"
                :row-class-name="poolRowClass" @selection-change="selectedRows = $event" @row-click="onPoolRowClick">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="pool-detail">
              <div class="pool-detail-main">
                <JdDetail :title="row.role" :company="row.company"
                          :meta="[{label:'渠道', value: row.channel}, {label:'状态', value: row.status}]"
                          :salary="row.parsed?.salary || (row.parsed?.ai_salary ?? '')"
                          :description="row.parsed?.description || ''"
                          :requirements="row.parsed?.requirements || []"
                          :bonus="row.parsed?.bonus || []"
                          :raw-text="row.text" />
              </div>
              <div class="pool-detail-side" v-if="row.rank || row.veto">
                <div class="eval-card">
                  <template v-if="row.veto">
                    <el-tag type="danger" effect="dark" size="large">一票否决</el-tag>
                    <div class="reason-line" v-for="(r, i) in row.reasons" :key="i">{{ r }}</div>
                  </template>
                  <template v-else>
                    <div class="eval-top">
                      <div class="eval-score">{{ row.score }}</div>
                      <div>
                        <el-tag :type="verdictType(row.rank?.verdict)" effect="dark">{{ row.rank?.verdict || '已评估' }}</el-tag>
                        <div class="muted" v-if="row.rank?.estimated" style="margin-top:4px">规则估算，建议重试 AI 评估</div>
                      </div>
                    </div>
                    <div class="dim-row" v-for="d in row.rank?.dimensions || []" :key="d.name">
                      <span class="dim-name">{{ d.name }}</span>
                      <div class="dim-track"><div class="dim-fill"
                        :style="{ width: d.score + '%', background: dimColor(d.score) }"></div></div>
                      <span class="dim-score">{{ d.score }}</span>
                    </div>
                    <template v-if="row.rank?.strengths?.length">
                      <div class="eval-sub"><el-icon color="#18a058"><CircleCheckFilled /></el-icon>匹配亮点</div>
                      <div class="point-line good" v-for="(s, i) in row.rank.strengths" :key="i">
                        <span class="pl-no">{{ i + 1 }}.</span><el-tag v-if="catOf(s)" size="small" :type="catType(catOf(s))" effect="plain" class="pl-cat">{{ catOf(s) }}</el-tag>
                        <span class="pl-text">{{ catText(s) }}</span>
                      </div>
                    </template>
                    <template v-if="row.rank?.gaps?.length">
                      <div class="eval-sub"><el-icon color="#e07c1f"><WarningFilled /></el-icon>差距风险</div>
                      <div class="point-line warn" v-for="(g, i) in row.rank.gaps" :key="i">
                        <span class="pl-no">{{ i + 1 }}.</span><el-tag v-if="catOf(g)" size="small" :type="catType(catOf(g))" effect="plain" class="pl-cat">{{ catOf(g) }}</el-tag>
                        <span class="pl-text">{{ catText(g) }}</span>
                      </div>
                    </template>
                    <div v-if="row.rank?.suggestion" class="suggestion">{{ row.rank.suggestion }}</div>
                  </template>
                </div>
              </div>
              <div class="pool-detail-side" v-else>
                <el-empty description="尚未评估" :image-size="60">
                  <el-button size="small" type="primary" :loading="scoring === row.id" @click.stop="score(row)">
                    <el-icon style="margin-right:3px"><MagicStick /></el-icon>AI 匹配评估
                  </el-button>
                </el-empty>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column type="selection" width="42" :selectable="() => !evalBusy && !scoring && !deleting" />
        <el-table-column type="index" label="#" width="50" />
        <el-table-column label="公司" min-width="120">
          <template #default="{ row }">
            <span class="cell-company"><CompanyLogo :name="row.company" :size="24" />{{ row.company }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="岗位" min-width="150" show-overflow-tooltip />
        <el-table-column label="薪资" width="130">
          <template #default="{ row }">
            <span v-if="salaryOf(row)" class="salary-text" :title="salaryOf(row)">{{ shortSalary(row) }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="匹配分" width="96" align="center">
          <template #default="{ row }">
            <template v-if="row.veto"><el-tag size="small" type="danger">否决</el-tag></template>
            <template v-else-if="row.score != null">
              <span class="score-pill" :style="{ background: scoreColor(row.score) + '14', color: scoreColor(row.score) }">{{ row.score }}</span>
            </template>
            <span v-else class="muted">待评</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" class-name="ops-col">
          <template #default="{ row }">
            <el-button v-if="!row.veto && row.score == null" size="small" type="primary" plain
                       :loading="scoring === row.id" @click.stop="score(row)">
              {{ scoring === row.id ? `评估中 ${scoringElapsed}s` : '' }}
              <el-icon v-if="scoring !== row.id" style="margin-right:3px"><MagicStick /></el-icon>{{ scoring === row.id ? '' : 'AI 评估' }}
            </el-button>
            <el-button v-if="!row.veto && row.status !== '已申请'" size="small" type="success" plain
                       @click.stop="apply(row)">
              <el-icon style="margin-right:3px"><Plus /></el-icon>创建申请
            </el-button>
            <el-button size="small" text type="danger" :disabled="deleting || evalBusy || !!scoring" @click.stop="remove([row])">删除</el-button>
            <el-tooltip content="打开官网" placement="top">
              <el-button v-if="row.apply_url" size="small" text type="primary" @click.stop="openApply(row)">
                <el-icon><Link /></el-icon>
              </el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="page-card">
      <div class="sec-head-row">
        <h3 style="display:flex;align-items:center;gap:6px"><el-icon color="#18a058"><Notebook /></el-icon>我的投递</h3>
        <div class="management-actions" style="margin-left:auto"><el-button size="small" type="primary" @click="addApplicationOpen = true">添加投递</el-button><el-button size="small" type="danger" plain :disabled="!selectedApplications.length || deleting" @click="remove(rows.filter(row => selectedApplications.includes(row.id)), true)">删除选中（{{ selectedApplications.length }}）</el-button></div>
      </div>
      <el-empty v-if="!rows.length" description="还没有投递记录 —— 在上方候选岗位里点「创建申请」" :image-size="70" />
      <div class="track-list">
        <div class="track-card" v-for="r in rows" :key="r.id">
          <div class="track-head">
            <div style="display:flex;align-items:center;gap:9px">
              <el-checkbox :model-value="selectedApplications.includes(r.id)" :disabled="deleting" :aria-label="'选择投递：' + r.company + ' · ' + r.role" @change="checked => selectedApplications = checked ? [...selectedApplications, r.id] : selectedApplications.filter(id => id !== r.id)" /><CompanyLogo :name="r.company" :size="30" />
              <b>{{ r.company }}</b><span class="muted"> · {{ r.role }}</span>
            </div>
            <el-tag size="small" :type="statusMeta(r.status)?.type || 'info'">{{ statusMeta(r.status)?.label || r.status }}</el-tag>
          </div>
          <el-steps :active="stepOf(r)" :align-center="true" class="track-steps"
                    :process-status="finalOf(r) ? (r.status === 'offer' ? 'success' : 'error') : 'process'"
                    :finish-status="finalOf(r) ? (r.status === 'offer' ? 'success' : 'error') : 'finish'">
            <el-step title="候选" :description="r.fit_rating ? `匹配 ${r.fit_rating}` : ''" />
            <el-step title="创建申请" :description="r.date" />
            <el-step title="已投递" />
            <el-step title="面试" :description="roundLabel(r)" />
            <el-step title="结果" :description="finalLabel(r)" />
          </el-steps>
          <div class="track-foot">
            <span class="muted track-notes">{{ r.notes || '暂无备注' }}</span>
            <el-button size="small" text type="danger" :disabled="deleting" @click="remove([r], true)">删除</el-button>
            <el-button size="small" text type="primary" @click="openUpdate(r)">
              <el-icon style="margin-right:3px"><EditPen /></el-icon>更新状态
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <AddRecordDialog v-model="addJobOpen" @saved="refresh" />
    <AddRecordDialog v-model="addApplicationOpen" application @saved="refresh" />
    <el-dialog v-model="dialog" title="推进求职进度" width="440" append-to-body>
      <el-form label-width="70px">
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option v-for="s in STATUS_OPTIONS" :key="s" :label="STATUS_META[s]?.label || s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="反馈原话（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="submitUpdate">确认更新</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, STATUS_META, STATUS_OPTIONS } from '../api'
import { evalTask, startEvaluation, stopEvalTask, onEvalDone } from '../store'
import JdDetail from '../components/JdDetail.vue'
import AddRecordDialog from '../components/AddRecordDialog.vue'
import { useRecordDeletion } from '../recordActions'
import CompanyLogo from '../components/CompanyLogo.vue'

const evalBusy = computed(() => ['starting', 'running'].includes(evalTask.status))
async function stopEvaluation() { try { await stopEvalTask(); if (evalTask.status === 'cancelled') { ElMessage.info('已停止评估，已完成的评分已保留'); await refresh() } } catch(e) { ElMessage.error(e.message) } }
watch(() => evalTask.status, status => { if (status === 'cancelled') refresh() })
const addJobOpen = ref(false), addApplicationOpen = ref(false), selectedApplications = ref([])
const { deleting, remove } = useRecordDeletion(refresh)
const entries = ref([])
const rows = ref([])
const scoring = ref(null)
const scoringElapsed = ref(0)
let scoringTimer = null
const poolTableRef = ref()
const selectedRows = ref([])

const selectedIds = computed(() =>
  selectedRows.value.filter(r => !r.veto && r.score == null && r.status !== '已申请').map(r => r.id))

async function batchEval() {
  if (!selectedIds.value.length) return
  try {
    await startEvaluation(selectedIds.value)
  } catch (e) { ElMessage.error(e.message) }
}

onEvalDone(() => { refresh() })
const dialog = ref(false)
const form = ref({ company: '', role: '', status: 'applied', note: '' })

const salaryOf = (row) => row.parsed?.salary || ''
const shortSalary = (row) => {
  const full = salaryOf(row)
  const cut = full.split('（')[0]
  return cut.length > 14 ? cut.slice(0, 13) + '…' : cut
}
const applyCount = computed(() => rows.value.length)
const interviewingCount = computed(() => rows.value.filter(r => String(r.status).startsWith('interview')).length)
const doneCount = computed(() => rows.value.filter(r => ['offer', 'rejected', 'no_response', 'withdrawn', 'offer_declined'].includes(r.status)).length)
const statCards = computed(() => [
  { label: '候选岗位', value: entries.value.length, icon: 'Filter', color: '#2f66f6' },
  { label: '已创建申请', value: applyCount.value, icon: 'Document', color: '#7a5af5' },
  { label: '面试中', value: interviewingCount.value, icon: 'Calendar', color: '#e07c1f' },
  { label: '已出结果', value: doneCount.value, icon: 'Trophy', color: '#18a058' },
])
const statusMeta = (s) => STATUS_META[s]
const statusType = (s) => ({ 待评估: 'info', 已评估: 'primary', 已否决: 'danger', 已申请: 'success', 已收藏: 'warning' }[s] || 'info')
const scoreColor = (s) => (s >= 75 ? '#18a058' : s >= 55 ? '#e07c1f' : '#d93025')
const _CAT_KEYS = ['实习', '论文', '项目', '竞赛', '获奖', '成绩']
const _CAT_HINTS = { 实习: ['实习', '工作经历', '在职'], 论文: ['论文', '顶会', '一作', 'ICML', 'TCSVT', '期刊'],
  项目: ['项目', '课题', '重构', '平台'], 竞赛: ['竞赛', 'ACM', '比赛'], 获奖: ['奖学金', '获奖', '荣誉'],
  成绩: ['GPA', '排名', '绩点'], 技能: ['技能', '掌握', '熟悉', '栈'], 发展: ['发展', '方向', '偏好'] }
function catOf(t) {
  const text = String(t)
  const m = text.match(/^【(.+?)】/)
  if (m) return m[1]
  for (const cat of _CAT_KEYS) {
    if ((text).includes(cat)) return cat
    if ((text).includes('【' + cat + '】')) return cat
  }
  for (const [cat, hints] of Object.entries(_CAT_HINTS)) {
    if (hints.some(h => text.toLowerCase().includes(h.toLowerCase()))) return cat
  }
  return null
}
const catText = (t) => String(t).replace(/^【.+?】\s*/, '')
const catType = (c) => ({ 实习: 'success', 论文: 'warning', 项目: 'primary', 竞赛: 'warning', 获奖: 'success', 成绩: 'info', 技能: 'primary', 发展: 'warning', 学历: 'info' }[c] || 'info')
const dimColor = (s) => scoreColor(s)
const verdictType = (v) => (v === '推荐投递' ? 'success' : v === '谨慎投递' ? 'warning' : 'danger')
const finalOf = (r) => ['offer', 'rejected', 'no_response', 'withdrawn', 'offer_declined'].includes(r.status)
const finalLabel = (r) => (r.status === 'offer' ? 'Offer' : finalOf(r) ? '已结束' : '')
const roundLabel = (r) => {
  const m = STATUS_META[r.status]
  return String(r.status).startsWith('interview') && m ? m.label : ''
}

const poolRowClass = ({ row }) => (row.veto ? 'veto-row' : '')

function stepOf(r) {
  if (r.status === 'drafted') return 2
  if (r.status === 'applied') return 3
  if (String(r.status).startsWith('interview')) return 4
  if (finalOf(r)) return 5
  return 1
}

function onPoolRowClick(row, _column, event) {
  if (event?.target?.closest?.('.el-button, .el-checkbox, .el-table__expand-icon')) return
  poolTableRef.value?.toggleRowExpansion(row)
}

async function refresh() {
  try {
    const [pool, applications] = await Promise.all([api.get('/rank/candidates'), api.get('/apply/list')])
    entries.value = pool.entries; rows.value = applications.rows
    selectedRows.value = []; selectedApplications.value = []; poolTableRef.value?.clearSelection()
  } catch(e) { ElMessage.error(e.message) }
}

async function score(row) {
  scoring.value = row.id
  scoringElapsed.value = 0
  scoringTimer = setInterval(() => { scoringElapsed.value++ }, 1000)
  try {
    const d = await api.post('/rank/score/' + row.id)
    Object.assign(row, d.entry)
    if (d.result.veto) ElMessage.warning('触线否决：' + d.result.reasons[0])
    else ElMessage.success(`评估完成：${d.result.score} 分 · ${d.result.verdict}`)
    poolTableRef.value?.toggleRowExpansion(row, true)
  } catch (e) { ElMessage.error(e.message) } finally { scoring.value = null; clearInterval(scoringTimer) }
}

function openApply(row) {
  if (row.apply_url) window.open(row.apply_url, '_blank')
}

async function apply(row) {
  try {
    await api.post('/apply/create', { inbox_id: row.id })
    ElMessage.success('已创建申请，进入「我的投递」跟踪进度')
    await refresh()
  } catch (e) { ElMessage.error(e.message) }
}

function openUpdate(r) {
  form.value = { company: r.company, role: r.role, status: r.status, note: '' }
  dialog.value = true
}

async function submitUpdate() {
  try {
    await api.post('/tracker/status', form.value)
    ElMessage.success('进度已更新')
    dialog.value = false
    await refresh()
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(refresh)
onActivated(() => { refresh() })
</script>

<style scoped>
.management-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.management-actions .el-button+.el-button{margin-left:0}.sec-head-row{flex-wrap:wrap}

.stats-line { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 14px; }
.stat-card { background: linear-gradient(180deg, #fff, #fbfcff); border: 1px solid #e8ecf4; border-left: 3px solid var(--ac, #2f66f6); border-radius: 10px; padding: 10px 14px; display: flex; gap: 10px; align-items: center; box-shadow: 0 1px 3px rgba(23,43,99,.06); transition: transform .18s ease, box-shadow .2s ease; }
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 5px 14px rgba(23,43,99,.09); }
.stat-card .chip { width: 34px; height: 34px; border-radius: 9px; display: grid; place-items: center; flex-shrink: 0; }
.stat-num { font-size: 20px; font-weight: 700; color: #1f2733; }
.track-card { background: linear-gradient(180deg, #ffffff, #fdfefe); }
.sec-head-row { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
.sec-head-row h3 { margin: 0; font-size: 14.5px; font-weight: 600; }
.pool-detail { display: flex; gap: 20px; align-items: flex-start; padding: 6px 8px; }
:deep(.ops-col .cell) { white-space: nowrap; }
.salary-text { color: #e07c1f; font-weight: 600; font-variant-numeric: tabular-nums; }
.score-pill { display: inline-block; padding: 3px 12px; border-radius: 12px; font-weight: 700; font-size: 13px; font-variant-numeric: tabular-nums; }
.pool-detail-main { flex: 1.4; min-width: 0; }
.pool-detail-side { flex: 1; min-width: 260px; max-width: 380px; }
.eval-card { background: linear-gradient(180deg, #f8faff, #f3f6fd); border: 1px solid #e3eaf8; border-radius: 10px; padding: 14px; }
.eval-top { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
.eval-score { font-size: 34px; font-weight: 700; line-height: 1; color: #2f66f6; }
.dim-row { display: flex; align-items: center; gap: 8px; margin: 7px 0; }
.dim-name { width: 62px; font-size: 12px; color: #5b6575; flex-shrink: 0; }
.dim-track { flex: 1; height: 8px; background: #e8ecf5; border-radius: 4px; overflow: hidden; }
.dim-fill { height: 100%; border-radius: 4px; transition: width .5s cubic-bezier(.22,1,.36,1); }
.dim-score { width: 26px; text-align: right; font-size: 12px; color: #3d4757; }
.eval-sub { display: flex; align-items: center; gap: 5px; font-size: 12.5px; font-weight: 600; margin: 10px 0 4px; }
.point-line { font-size: 12.5px; line-height: 1.75; display: flex; align-items: flex-start; gap: 6px; margin-bottom: 7px; }
.pl-no { font-weight: 700; flex-shrink: 0; }
.point-line.good .pl-no { color: #18a058; }
.point-line.warn .pl-no { color: #e07c1f; }
.pl-cat { flex-shrink: 0; }
.pl-text { flex: 1; min-width: 0; }
.point-line.good .pl-text { color: #1f7a4d; }
.point-line.warn .pl-text { color: #a05a17; }
.reason-line { font-size: 13px; color: #8f2b25; line-height: 1.8; margin-top: 8px; }
.suggestion { margin-top: 10px; background: #fff; border: 1px dashed #c9d6f2; border-radius: 8px; padding: 8px 10px; font-size: 12.5px; color: #3d4757; line-height: 1.6; }
.track-list { display: flex; flex-direction: column; gap: 10px; }
.track-card { border: 1px solid #e4e8f0; border-radius: 10px; padding: 14px 16px 10px; transition: border-color .2s ease, box-shadow .2s ease; }
.track-card:hover { border-color: #c9d6f2; box-shadow: 0 3px 10px rgba(23,43,99,.07); }
.track-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.track-steps :deep(.el-step__title) { font-size: 12.5px; }
.track-steps :deep(.el-step__description) { font-size: 11px; }
.track-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #f0f2f7; }
.track-notes { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:deep(.veto-row) { background: #fdf3f2; }
.cell-company { display: flex; align-items: center; }
</style>

