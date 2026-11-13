<template>
  <div>
    <div class="page-title">系统设置</div>

    <div class="page-card" style="max-width:620px">
      <h3 style="margin:0 0 12px;font-size:14px;display:flex;align-items:center;gap:6px">
        <el-icon color="#2f66f6"><Connection /></el-icon>AI 接入
      </h3>
      <el-form label-width="86px" label-position="left">
        <el-form-item label="API 地址"><el-input v-model="form.AI_BASE_URL" placeholder="https://api.openai-proxy.org/v1" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="form.AI_API_KEY" type="password" show-password
          :placeholder="masked ? '已保存（' + masked + '），留空则不修改' : '尚未配置'" /></el-form-item>
      </el-form>
      <div style="display:flex;gap:10px;align-items:center">
        <el-button type="primary" :loading="saving" @click="save"><el-icon style="margin-right:3px"><Check /></el-icon>保存</el-button>
        <el-button :loading="testing" @click="test"><el-icon style="margin-right:3px"><Connection /></el-icon>测试连接</el-button>
        <el-tag v-if="testResult?.ok" type="success">连接正常 · {{ testResult.latency_ms }}ms</el-tag>
        <el-tag v-else-if="testResult" type="danger">{{ testResult.error }}</el-tag>
      </div>
      <p class="muted" style="margin:14px 0 0">v0.1.0</p>
    </div>

    <div class="page-card">
      <h3 style="margin:0 0 4px;font-size:14px;display:flex;align-items:center;gap:6px">
        <el-icon color="#7a5af5"><Grid /></el-icon>模型广场
        <span class="muted" style="margin-left:auto">当前使用：<b style="color:#2f66f6">{{ form.AI_MODEL || '未选择' }}</b></span>
      </h3>

      <div class="mall-filter">
        <span class="mall-label">厂商</span>
        <span class="mall-chips">
          <span class="mall-chip" :class="{ active: vendorFilter === '全部' }" @click="vendorFilter = '全部'">全部</span>
          <span class="mall-chip" v-for="v in vendors" :key="v" :class="{ active: vendorFilter === v }" @click="vendorFilter = v">
            <img class="vendor-logo" :src="vendorLogoUrl(v)" @error="$event.target.style.display = 'none'" alt="">{{ v }}
          </span>
        </span>
      </div>
      <div class="mall-filter">
        <span class="mall-label">搜索</span>
        <el-input v-model="search" placeholder="搜索模型…" style="width:240px" size="small" clearable>
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button size="small" style="margin-left:8px" :loading="loadingModels" @click="loadModels">
          <el-icon style="margin-right:3px"><Refresh /></el-icon>{{ models.length ? '刷新列表' : '拉取模型列表' }}
        </el-button>
        <span class="muted" v-if="models.length">{{ filteredModels.length }} / {{ models.length }} 个模型</span>
      </div>

      <el-alert v-if="modelError" type="warning" :closable="false" show-icon :title="modelError"
                description="拉取失败一般是 Key 未保存或网络问题；保存上方接入信息后重试" style="margin:10px 0" />

      <div class="mall-list" v-if="filteredModels.length">
        <div class="mall-row" v-for="m in filteredModels" :key="m"
             :class="{ active: form.AI_MODEL === m }" @click="form.AI_MODEL = m">
          <img class="vendor-logo lg" :src="vendorLogoUrl(vendorOf(m))" @error="$event.target.style.display = 'none'" alt="">
          <span class="mall-name">{{ m }}</span>
          <el-icon v-if="form.AI_MODEL === m" color="#2f66f6"><Select /></el-icon>
        </div>
      </div>
      <el-empty v-else-if="!loadingModels && !modelError" description="点「拉取模型列表」从网关获取可用模型" :image-size="70" />

      <div v-if="dirty" style="margin-top:12px;display:flex;gap:10px;align-items:center">
        <el-button type="primary" size="small" :loading="saving" @click="saveModel">
          <el-icon style="margin-right:3px"><Check /></el-icon>切换为 {{ form.AI_MODEL }}
        </el-button>
        <span class="muted">点击模型行选择，确认后保存生效</span>
      </div>
    </div>

    <div class="page-card">
      <h3 style="margin:0 0 4px;font-size:14px;display:flex;align-items:center;gap:6px;flex-wrap:wrap">
        <el-icon color="#d93025"><Warning /></el-icon>数据重置
        <span class="muted" style="margin-left:auto;font-weight:400">按模块勾选要清空的数据 · 执行后不可恢复 · documents/backup 真实档案备份不受影响</span>
      </h3>
      <div class="reset-grid">
        <div class="reset-group" v-for="g in resetGroups" :key="g.key"
             :class="{ active: resetSel.includes(g.key) }" @click="toggleReset(g.key)">
          <div class="rg-head">
            <span class="rg-check"><el-icon v-if="resetSel.includes(g.key)"><Select /></el-icon></span>
            <b>{{ g.label }}</b>
            <span class="rg-count">{{ g.count > 0 ? g.count + ' 项' : '空' }}</span>
          </div>
          <div class="rg-desc">{{ g.desc }}</div>
          <div class="rg-detail">{{ g.detail }}</div>
        </div>
      </div>
      <div style="margin-top:14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <el-button size="small" @click="resetSel = resetGroups.map(g => g.key)">全选</el-button>
        <el-button size="small" @click="resetSel = []">清空选择</el-button>
        <el-button type="danger" :disabled="!resetSel.length" :loading="resetting" @click="runReset">
          <el-icon style="margin-right:3px"><Delete /></el-icon>重置所选{{ resetSel.length ? `（${resetSel.length} 类）` : '' }}
        </el-button>
        <span class="muted">点击执行后需输入「重置」二字二次确认</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const form = ref({ AI_BASE_URL: '', AI_API_KEY: '', AI_MODEL: 'gemini-3.7-flash' })
const masked = ref('')
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const models = ref([])
const modelError = ref('')
const loadingModels = ref(false)
const vendorFilter = ref('全部')
const search = ref('')
const dirty = ref(false)

const VENDOR_ORDER = ['OpenAI', 'Anthropic', 'Google', 'DeepSeek', 'xAI', '阿里云百炼', '智谱AI', '月之暗面', 'MiniMax', '字节火山']
const curatedSet = ref(new Set())
const vendorOverride = ref(new Map())
const VENDOR_RULES = [
  ['Anthropic', ['claude']],
  ['Google', ['gemini', 'gemma']],
  ['DeepSeek', ['deepseek']],
  ['xAI', ['grok']],
  ['阿里云百炼', ['qwen', 'wan']],
  ['智谱AI', ['glm']],
  ['月之暗面', ['kimi', 'moonshot']],
  ['MiniMax', ['minimax', 'abab']],
  ['字节火山', ['doubao', 'seed-oss']],
  ['OpenAI', ['gpt', 'o1', 'o3', 'o4', 'chatgpt', 'dall-e', 'whisper', 'text-embedding', 'davinci']],
]
function vendorOf(id) {
  const mapped = vendorOverride.value.get(id)
  if (mapped) return mapped
  const s = String(id).toLowerCase()
  for (const [vendor, keys] of VENDOR_RULES) {
    if (keys.some(k => s.includes(k))) return vendor
  }
  return '其他'
}
const vendorLogoUrl = (v) => '/api/logo/vendor?v=' + encodeURIComponent(v)
const vendorColor = (v) => ({ OpenAI: '#10a37f', Anthropic: '#d97757', Google: '#4285f4', DeepSeek: '#4d6bfe',
  xAI: '#1f2733', 阿里云百炼: '#ff6a00', 智谱AI: '#3859ff', 月之暗面: '#1a1a1a', MiniMax: '#f53f3f',
  字节火山: '#00b2ff', 其他: '#8a93a3' }[v] || '#8a93a3')

const vendors = computed(() => {
  const set = new Set(models.value.map(vendorOf))
  return VENDOR_ORDER.filter(v => set.has(v)).concat([...set].filter(v => !VENDOR_ORDER.includes(v)))
})
const filteredModels = computed(() => {
  let list = models.value
  if (vendorFilter.value !== '全部') list = list.filter(m => vendorOf(m) === vendorFilter.value)
  const q = search.value.trim().toLowerCase()
  if (q) list = list.filter(m => m.toLowerCase().includes(q))
  return list
})

watch(() => form.value.AI_MODEL, (v) => { dirty.value = true })

// 按模型广场截图收录的主流厂商新一代模型（前缀白名单，自动兼容后续小版本）
const CURATED = [
  ['OpenAI', ['gpt-6.1', 'gpt-6.', 'gpt-5.6']],
  ['Anthropic', ['claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5', 'claude-fable-5-1',
                 'claude-opus-5', 'claude-sonnet-5', 'claude-fable-5', 'claude-opus-4-8', 'claude-opus-4-7']],
  ['Google', ['gemini-4', 'gemini-3']],
  ['DeepSeek', ['deepseek-v4', 'deepseek-v3.2']],
  ['阿里云百炼', ['qwen3.8', 'qwen3.7', 'qwen3.6', 'qwen3.5']],
  ['智谱AI', ['glm-5']],
  ['月之暗面', ['kimi-k3', 'kimi-k2']],
]
function curatedVendor(id) {
  const s = String(id).toLowerCase()
  for (const [vendor, prefixes] of CURATED) {
    if (prefixes.some(p => s.startsWith(p.toLowerCase()))) return vendor
  }
  return null
}

async function loadModels() {
  loadingModels.value = true
  modelError.value = ''
  try {
    const d = await api.get('/settings/models')
    const curated = []
    for (const m of d.models) {
      const v = curatedVendor(m)
      if (v) {
        models.value.push(m)
        curatedSet.value.add(m)
        vendorOverride.value.set(m, v)
      }
    }
    models.value = [...curatedSet.value]
  } catch (e) { modelError.value = e.message } finally { loadingModels.value = false }
}

async function save() {
  saving.value = true
  try {
    await api.put('/settings', form.value)
    ElMessage.success('已保存')
    if (form.value.AI_API_KEY) masked.value = form.value.AI_API_KEY.slice(0, 6) + '…'
    form.value.AI_API_KEY = ''
    if (!models.value.length) loadModels()
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}


async function saveModel() {
  saving.value = true
  try {
    await api.put('/settings', { AI_MODEL: form.value.AI_MODEL })
    ElMessage.success('模型已切换为 ' + form.value.AI_MODEL)
    dirty.value = false
    testResult.value = null
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}

async function test() {
  testing.value = true
  try { testResult.value = await api.post('/settings/test') } catch (e) { testResult.value = { ok: false, error: e.message } } finally { testing.value = false }
}

// ---- 数据重置 ----
const resetGroups = ref([])
const resetSel = ref([])
const resetting = ref(false)

async function loadResetInventory() {
  try { resetGroups.value = (await api.get('/reset/inventory')).groups } catch { /* 设置页其余功能不受影响 */ }
}

function toggleReset(key) {
  const i = resetSel.value.indexOf(key)
  if (i >= 0) resetSel.value.splice(i, 1)
  else resetSel.value.push(key)
}

async function runReset() {
  if (!resetSel.value.length) return
  let confirmWord = ''
  try {
    ({ value: confirmWord } = await ElMessageBox.prompt(
      `将永久删除选中的 ${resetSel.value.length} 类数据，此操作不可恢复！请输入「重置」二字确认：`,
      '危险操作确认',
      { type: 'error', confirmButtonText: '立即重置', cancelButtonText: '取消',
        inputPlaceholder: '输入：重置', inputPattern: /^重置$/, inputErrorMessage: '请输入「重置」二字' }))
  } catch { return }
  resetting.value = true
  try {
    const d = await api.post('/reset/run', { keys: resetSel.value, confirm: confirmWord })
    ElMessage.success(`已重置 ${Object.keys(d.removed).length} 类数据`)
    resetSel.value = []
    await loadResetInventory()
  } catch (e) { ElMessage.error(e.message) } finally { resetting.value = false }
}

onMounted(async () => {
  const s = await api.get('/settings')
  form.value.AI_BASE_URL = s.AI_BASE_URL
  form.value.AI_MODEL = s.AI_MODEL
  masked.value = s.AI_API_KEY_MASKED
  if (s.AI_API_KEY_MASKED) loadModels()
  dirty.value = false
  loadResetInventory()
})
</script>

<style scoped>
.mall-filter { display: flex; align-items: flex-start; gap: 10px; margin: 10px 0; flex-wrap: wrap; }
.mall-label { font-size: 12.5px; color: #5b6575; width: 34px; flex-shrink: 0; line-height: 26px; }
.mall-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.mall-chip { font-size: 12.5px; padding: 4px 12px; border-radius: 7px; cursor: pointer; background: #f5f7fb; border: 1px solid #e4e8f0; color: #3d4757; transition: all .15s ease; }
.mall-chip:hover { border-color: #2f66f6; color: #2f66f6; }
.mall-chip.active { background: #1f2733; border-color: #1f2733; color: #fff; }
.mall-list { margin-top: 10px; max-height: 380px; overflow-y: auto; border: 1px solid #eef1f7; border-radius: 10px; }
.mall-row { display: flex; align-items: center; gap: 10px; padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #f5f7fb; transition: background .15s ease; }
.mall-row:hover { background: #f5f8ff; }
.mall-row.active { background: #eef4ff; }
.mall-vtag { flex-shrink: 0; font-size: 11px; font-weight: 600; border-radius: 5px; padding: 2px 8px; min-width: 64px; text-align: center; }
.mall-name { flex: 1; font-size: 13px; color: #1f2733; font-family: Consolas, Menlo, monospace; }
.vendor-logo { width: 16px; height: 16px; border-radius: 3px; object-fit: contain; vertical-align: -3px; margin-right: 5px; background: #fff; }
.vendor-logo.lg { width: 22px; height: 22px; border-radius: 5px; border: 1px solid #eef1f7; vertical-align: 0; }
.reset-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; margin-top: 12px; }
.reset-group { border: 1px solid #e8ecf4; border-radius: 10px; padding: 12px 14px; cursor: pointer; transition: all .15s ease; }
.reset-group:hover { border-color: #c9d6f2; }
.reset-group.active { border-color: #d93025; background: #fff5f4; box-shadow: 0 2px 10px rgba(217, 48, 37, .08); }
.rg-head { display: flex; align-items: center; gap: 8px; }
.rg-check { width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid #c6cdd8; display: inline-grid; place-items: center; color: #fff; flex-shrink: 0; transition: all .15s ease; }
.reset-group.active .rg-check { background: #d93025; border-color: #d93025; }
.rg-check .el-icon { font-size: 11px; }
.rg-head b { font-size: 13.5px; color: #1f2733; }
.rg-count { margin-left: auto; font-size: 11.5px; color: #8a93a3; font-weight: 600; }
.rg-desc { margin-top: 6px; font-size: 12px; color: #5b6575; line-height: 1.5; }
.rg-detail { margin-top: 4px; font-size: 11.5px; color: #98a1b0; }
</style>
