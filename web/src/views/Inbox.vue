<template>
  <div>
    <div class="page-title">岗位收集</div>
    <el-alert v-if="matchTask.error" :title="matchTask.error" type="error" :closable="false" />
    <el-alert v-if="matchTask.warning" :title="matchTask.warning" type="warning" :closable="false" />
    <el-alert v-if="matchTask.status === 'cancelled'" title="匹配已停止，上一批结果已保留。" type="info" :closable="false" />
    <el-tabs v-model="mode">
      <el-tab-pane label="手动贴入" name="manual" />
      <el-tab-pane label="AI 智能匹配" name="ai" />
    </el-tabs>

    <div v-if="mode === 'manual'" class="page-card">
      <el-row :gutter="14">
        <el-col :span="13">
          <el-input v-model="text" type="textarea" :rows="9" placeholder="粘贴岗位描述全文" />
          <div style="margin-top:10px">
            <el-button type="primary" @click="parse" :loading="parsing">
              <el-icon v-if="!parsing" style="margin-right:3px"><Search /></el-icon>解析
            </el-button>
            <el-button v-if="preview" type="success" @click="save" :loading="saving">
              <el-icon style="margin-right:3px"><Select /></el-icon>确认入库
            </el-button>
          </div>
        </el-col>
        <el-col :span="11">
          <el-empty v-if="!preview" description="暂无解析结果" :image-size="60" />
          <el-form v-else label-width="72px" label-position="left" size="small">
            <el-form-item label="公司"><el-input v-model="form.company" /></el-form-item>
            <el-form-item label="岗位"><el-input v-model="form.role" /></el-form-item>
            <el-form-item label="薪资"><span>{{ preview.salary || '—' }}</span></el-form-item>
            <el-form-item label="关键要求">
              <div class="muted" v-for="(r, i) in preview.requirements" :key="i">{{ r }}</div>
            </el-form-item>
          </el-form>
          <el-alert v-if="preview?.role_type_warning" type="error" :closable="false" show-icon
                    :title="preview.role_type_warning + '，请确认用工性质'" />
        </el-col>
      </el-row>
    </div>

    <div v-else class="page-card">
      <el-form label-width="84px">
        <el-row :gutter="16">
          <el-col :span="11">
            <el-form-item label="意向岗位">
              <el-input :disabled="matchBusy" v-model="directionText" type="textarea"
                        :autosize="{ minRows: 2, maxRows: 5 }"
                        placeholder="自由输入岗位、行业或求职描述，例如：半导体、芯片验证，或想找新能源行业的硬件研发岗位" />
              <div class="muted direction-hint">支持任意行业和岗位，多个方向可换行填写。AI 优先按求职意向推荐，再结合档案判断匹配程度与能力差距。</div>
            </el-form-item>
          </el-col>
          <el-col :span="7">
            <el-form-item label="城市">
              <el-select :disabled="matchBusy" v-model="ai.cities" multiple filterable allow-create default-first-option
                         placeholder="可多选" style="width:100%">
                <el-option v-for="c in CITIES" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="求职类型">
              <el-select :disabled="matchBusy" v-model="ai.job_type" style="width:100%">
                <el-option v-for="t in JOB_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="行业类别">
              <el-select :disabled="matchBusy" v-model="ai.categories" multiple filterable allow-create default-first-option
                         placeholder="选填，不限行业；也可输入自定义类别后按回车" style="width:100%">
                <el-option v-for="cat in CATEGORIES" :key="cat" :value="cat" :label="cat" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <div style="margin-left:84px;display:flex;align-items:center;gap:14px;flex-wrap:wrap">
          <el-button :type="matchBusy ? 'danger' : 'primary'" :loading="matchTask.stopping" @click="matchBusy ? stopMatch() : runMatch(false)">
            <el-icon v-if="!matchBusy" style="margin-right:4px"><MagicStick /></el-icon>{{ matchTask.stopping ? '正在停止…' : matchBusy ? '停止匹配' : '智能匹配' }}
          </el-button>
          <el-button :disabled="matchBusy || !aiResults.length" @click="runMatch(true)">不满意，换一批</el-button>
          <div v-if="matchBusy" style="flex:1;min-width:240px;max-width:380px">
            <el-progress :percentage="Math.min(99, Math.round(matchTask.done / Math.max(matchTask.total, 3) * 100))" :stroke-width="8" />
            <div class="muted" style="margin-top:2px">{{ matchTask.progress || '匹配中' }} · {{ matchTask.elapsed }}s</div>
          </div>
        </div>
      </el-form>
    </div>

    <div class="page-card" v-if="aiResults.length">
      <div class="match-head">
        <b>匹配结果 · {{ aiResults.length }} 条</b>
        <span class="match-actions">
          <el-button size="small" text type="primary" @click="aiOpen = !aiOpen">
            {{ aiOpen ? '收起' : '展开' }}
            <el-icon class="chev" :class="{ open: aiOpen }" style="margin-left:2px"><ArrowRight /></el-icon>
          </el-button>
          <el-button size="small" text type="info" :disabled="matchBusy" @click="closeMatch">清空</el-button>
        </span>
      </div>
      <div class="job-list" v-show="aiOpen">
        <div class="job-card" v-for="(row, $index) in aiResults" :key="row.company + row.role"
             :class="{ open: row._open }">
          <div class="job-head" @click="row._open = !row._open">
            <CompanyLogo :name="row.company" :size="42" />
            <div class="job-title">
              <div class="job-line1">
                <el-tag size="small" :type="tierType(row.tier)" effect="dark">{{ row.tier || '匹配' }}</el-tag>
                <b>{{ row.company }}</b>
                <span class="job-role">{{ row.role }}</span>
              </div>
              <el-rate :model-value="row.stars" disabled size="small" />
            </div>
            <div class="job-salary">{{ row.salary || '面议' }}</div>
            <div class="job-actions" @click.stop>
              <el-button v-if="row.careers_url" size="small" type="warning" plain
                       tag="a" :href="row.careers_url" target="_blank" rel="noopener">
              <el-icon style="margin-right:3px"><Link /></el-icon>官网
            </el-button>
              <el-button size="small" type="primary" plain :disabled="isCollected(row)"
                         @click="addAi(row, $index, '待评估')">
                <el-icon style="margin-right:3px"><Plus /></el-icon>
                {{ isCollected(row) ? '已在候选池' : '加入候选池' }}
              </el-button>
              <span class="chev" :class="{ open: row._open }"><el-icon><ArrowRight /></el-icon></span>
            </div>
          </div>
          <el-collapse-transition>
            <div v-if="row._open" class="job-detail">
              <div class="jd-sec-title">推荐理由</div>
              <div class="why-item" v-for="(w, i) in whyPoints(row)" :key="i" :data-n="(i + 1) + '、'">{{ w }}</div>
              <div style="margin:10px 0">
                <el-tag size="small" effect="plain">建议渠道：{{ row.channel_hint }}</el-tag>
              </div>
              <JdDetail plain :salary="row.salary" :description="row.description"
                        :requirements="row.requirements" :bonus="row.bonus" />
            </div>
          </el-collapse-transition>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="sec-title" style="display:flex;align-items:center;gap:6px">
        <el-icon color="#2f66f6"><List /></el-icon>收集记录
        <el-button size="small" type="primary" style="margin-left:auto" @click="addOpen = true">添加岗位</el-button>
      </div>
      <div style="display:flex;justify-content:flex-end;margin-bottom:8px" v-if="selected.length">
        <el-button size="small" type="danger" plain :loading="deleting" @click="deleteSelected">
          <el-icon style="margin-right:3px"><Delete /></el-icon>删除选中（{{ selected.length }}）
        </el-button>
      </div>
      <el-table ref="entryTableRef" :data="entries" size="small" empty-text="暂无岗位"
                :row-class-name="({ row }) => row.veto ? 'veto-row' : ''"
                @selection-change="selected = $event">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding: 6px 10px 12px">
              <JdDetail :title="`${row.company} · ${row.role}`"
                        :meta="[{ label: '渠道', value: row.channel }, { label: '状态', value: row.status }]"
                        :salary="row.parsed?.salary || ''" :description="row.parsed?.description || ''"
                        :requirements="row.parsed?.requirements || []" :bonus="row.parsed?.bonus || []"
                        :raw-text="row.text" />
            </div>
          </template>
        </el-table-column>
        <el-table-column type="selection" width="42" :selectable="() => !deleting" />
        <el-table-column type="index" label="#" width="52" />
        <el-table-column label="公司" min-width="130">
          <template #default="{ row }">
            <span class="cell-company"><CompanyLogo :name="row.company" :size="22" />{{ row.company }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="岗位" min-width="130" />
        <el-table-column prop="channel" label="渠道" width="100" />
        <el-table-column label="薪资" width="120">
          <template #default="{ row }">
            <span v-if="row.parsed?.salary" class="salary-text" :title="row.parsed.salary">{{ row.parsed.salary.split('（')[0] }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="$router.push('/jobs')">去评估</el-button>
            <el-button size="small" text type="danger" :disabled="deleting" @click="remove([row])">删除</el-button>
            <el-button v-if="row.status !== '已申请' && row.apply_url" size="small" text type="primary"
                       tag="a" :href="row.apply_url" target="_blank" rel="noopener">去申请</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <AddRecordDialog v-model="addOpen" @saved="refresh" />
  </div>
</template>

<script setup>
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { ElMessage, ElCollapseTransition } from 'element-plus'
import { api } from '../api'
import JdDetail from '../components/JdDetail.vue'
import AddRecordDialog from '../components/AddRecordDialog.vue'
import { useRecordDeletion } from '../recordActions'
import CompanyLogo from '../components/CompanyLogo.vue'
import { matchTask, startMatchGeneration, stopMatchTask, getMatchResults, getMatchCriteria, clearMatchResults } from '../store'

const matchBusy = computed(() => ['starting', 'running'].includes(matchTask.status))
const selected = ref([])
const addOpen = ref(false), entryTableRef = ref()
const { deleting, remove } = useRecordDeletion(async () => { selected.value = []; entryTableRef.value?.clearSelection(); await refresh() })
const deleteSelected = () => remove(selected.value)

const CATEGORIES = ['互联网大厂', '互联网中厂', '手机厂', '半导体', '新能源', '制造业', '医疗健康', '国企', '银行']
const JOB_TYPES = ['暑期实习', '日常实习', '校招', '社招']
const CITIES = ['北京', '上海', '深圳', '广州', '杭州', '成都', '南京', '武汉', '西安', '苏州', '长沙', '合肥']

const mode = ref('manual')
const text = ref('')
const preview = ref(null)
const form = ref({ company: '', role: '' })
const entries = ref([])
const parsing = ref(false)
const saving = ref(false)

const ai = ref({ directions: [], cities: [], job_type: '校招', categories: [] })
// 保持 directions 数组协议，兼容已有匹配条件与换批记录。
const directionText = computed({
  get: () => ai.value.directions.join('\n'),
  set: value => { ai.value.directions = value.split('\n') },
})
const aiResults = ref([])
const aiOpen = ref(true)
function closeMatch() {
  aiResults.value = []
  aiOpen.value = true
  clearMatchResults()
}
const savedAs = ref({})
const normalize = value => String(value || '').replace(/[（(].*?[)）]|[\s·]/g, '')
const isCollected = row => entries.value.some(entry => normalize(entry.company) === normalize(row.company) && normalize(entry.role) === normalize(row.role))

const statusType = (s) => ({ 待评估: 'info', 已评估: 'primary', 已否决: 'danger', 已申请: 'success', 已收藏: 'warning', 已忽略: 'info' }[s] || 'info')
const tierType = (t) => ({ 冲刺: 'danger', 匹配: 'primary', 稳妥: 'success' }[t] || 'primary')
const whyPoints = (row) => String(row.why || '').split(/\n+/).map(s => s.trim()).filter(Boolean)

async function refresh() { entries.value = (await api.get('/rank/candidates')).entries }

async function parse() {
  parsing.value = true
  try {
    preview.value = await api.post('/inbox/parse', { text: text.value })
    form.value.company = preview.value.company
    form.value.role = preview.value.role
  } catch (e) { ElMessage.error(e.message) } finally { parsing.value = false }
}

async function save() {
  saving.value = true
  try {
    const d = await api.post('/inbox/save', { ...form.value, text: text.value, parsed: preview.value })
    if (d.duplicate) ElMessage.info('该岗位已在候选池（' + d.status + '），未重复添加')
    else ElMessage.success('已加入候选池')
    preview.value = null; text.value = ''
    await refresh()
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}

async function stopMatch() {
  try { await stopMatchTask() } catch(e) { ElMessage.error(e.message) }
}
async function runMatch(change = false) {
  if (matchBusy.value) return
  const criteria = change ? (getMatchCriteria() || ai.value) : ai.value
  const directions = [...new Set(criteria.directions.map(value => value.trim()).filter(Boolean))]
  if (!directions.length) { ElMessage.warning('请先输入意向岗位、行业或求职描述'); return }
  const body = { directions, cities: [...criteria.cities], job_type: criteria.job_type, categories: [...criteria.categories] }
  if (change) ai.value = { ...body }
  try { await startMatchGeneration(body, change) }
  catch(e) { ElMessage.error(e.message) }
}

// 匹配完成（无论当时在哪个页面），回到本页时展示结果
watch(() => matchTask.status, (st) => {
  if (st === 'done') {
    const r = getMatchResults()
    if (r?.length) {
      aiResults.value = r
      aiOpen.value = true
      savedAs.value = {}
      ElMessage.success(`匹配完成：${r.length} 条推荐`)
    }
  }
})

onMounted(() => {
  refresh()
  const criteria = getMatchCriteria()
  if (criteria) ai.value = criteria
  const saved = getMatchResults()
  if (saved?.length) aiResults.value = saved
})
// keep-alive：每次切回本页刷新收集记录（其他页的改动同步过来）
onActivated(() => { refresh() })

async function addAi(row, i, status) {
  try {
    const d = await api.post('/inbox/save', {
      company: row.company, role: row.role || ai.value.directions.join('/'),
      text: `AI 推荐目标：${row.company} ${row.role}（${ai.value.job_type}·${row.tier || '匹配'}）\n推荐理由：${row.why}\n建议渠道：${row.channel_hint}\n推荐程度：${'★'.repeat(row.stars)}\n薪资待遇：${row.salary || '未提供'}\n\n岗位介绍：${row.description || row.detail}\n能力要求：${(row.requirements || []).join('；')}`,
      channel: 'AI 匹配', parsed: { salary: row.salary || '', description: row.description, requirements: row.requirements, bonus: row.bonus }, status,
    })
    savedAs.value = { ...savedAs.value, [i]: status }
    if (d.duplicate) ElMessage.info('该岗位已在候选池（' + d.status + '），未重复添加')
    else ElMessage.success(status === '已收藏' ? '已收藏' : '已加入候选池')
    await refresh()
  } catch (e) { ElMessage.error(e.message) }
}
</script>

<style scoped>
.direction-hint { margin-top: 6px; line-height: 1.6; }
.logo-mini { width: 22px; height: 22px; border-radius: 5px; color: #fff; font-size: 12px; font-weight: 600; display: inline-grid; place-items: center; margin-right: 7px; vertical-align: -5px; }
.cell-company { display: flex; align-items: center; }
.salary-text { color: #e07c1f; font-weight: 600; font-variant-numeric: tabular-nums; }

.match-head { display: flex; align-items: center; gap: 10px; padding-bottom: 10px; border-bottom: 1px solid #eef1f7; margin-bottom: 12px; }
.match-head b { font-size: 14px; }
.match-actions { margin-left: auto; display: flex; align-items: center; gap: 4px; }
.job-list { display: flex; flex-direction: column; gap: 10px; }
.job-card { border: 1px solid #e8ecf4; border-radius: 12px; background: #fff; overflow: hidden; transition: border-color .2s ease, box-shadow .25s ease; }
.job-card:hover { border-color: #c9d6f2; box-shadow: 0 4px 14px rgba(23, 43, 99, .08); }
.job-card.open { border-color: #b9cbf5; box-shadow: 0 6px 18px rgba(47, 102, 246, .1); }
.job-head { display: flex; align-items: center; gap: 12px; padding: 12px 14px; cursor: pointer; user-select: none; }
.logo-tile { width: 42px; height: 42px; border-radius: 10px; color: #fff; font-size: 18px; font-weight: 600; display: grid; place-items: center; flex-shrink: 0; box-shadow: inset 0 -2px 4px rgba(0, 0, 0, .12); }
.job-title { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.job-line1 { display: flex; align-items: center; gap: 8px; min-width: 0; }
.job-line1 b { font-size: 14.5px; color: #1f2733; white-space: nowrap; }
.job-role { font-size: 13px; color: #5b6575; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.job-salary { font-size: 17px; font-weight: 700; color: #e07c1f; white-space: nowrap; font-variant-numeric: tabular-nums; flex-shrink: 0; }
.job-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.chev { color: #98a1b0; transition: transform .25s cubic-bezier(.22, 1, .36, 1); display: grid; place-items: center; }
.chev.open { transform: rotate(90deg); color: #2f66f6; }
.job-detail { padding: 4px 16px 16px 68px; border-top: 1px solid #f0f2f7; animation: detailIn .32s cubic-bezier(.22, 1, .36, 1) both; }
@keyframes detailIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: none; } }
.jd-sec-title { font-size: 14px; font-weight: 600; color: #1f2733; border-left: 3px solid #2f66f6; padding-left: 8px; margin: 12px 0 8px; }
.jd-para { font-size: 13px; color: #3d4757; line-height: 1.8; margin: 0 0 10px; }
.why-item { font-size: 13px; color: #3d4757; line-height: 1.85; padding-left: 24px; position: relative; margin-bottom: 4px; }
.why-item::before { content: attr(data-n); position: absolute; left: 0; top: 0; color: #2f66f6; font-weight: 600; }
@media (max-width: 900px) { .job-head { flex-wrap: wrap; } .job-detail { padding-left: 16px; } }
</style>
