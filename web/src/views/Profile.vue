<template>
  <div>
    <div class="page-title">个人档案</div>
    <el-card shadow="never">
      <el-tabs v-model="tab">
        <el-tab-pane label="基本信息" name="basic" />
        <el-tab-pane label="教育与经历" name="edu" />
        <el-tab-pane label="论文与荣誉" name="pub" />
        <el-tab-pane label="求职偏好" name="pref" />
        <el-tab-pane label="面试素材" name="stars" />
      </el-tabs>

      <div style="display:flex;gap:10px;align-items:center;margin:-4px 0 14px">
        <el-upload :show-file-list="false" accept=".pdf,.docx" :http-request="doImport">
          <el-button :loading="importing" plain>
            <el-icon v-if="!importing" style="margin-right:4px"><Upload /></el-icon>
            {{ importing ? `解析中 ${importElapsed}s` : '导入简历（PDF / Word）' }}
          </el-button>
        </el-upload>
      </div>

      <el-form v-if="tab === 'basic'" label-width="84px">
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="姓名"><el-input v-model="c.name" /></el-form-item></el-col>
          <el-col :span="8">
            <el-form-item label="性别">
              <el-select v-model="c.gender" clearable><el-option label="男" value="男" /><el-option label="女" value="女" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="出生年月"><el-date-picker v-model="c.birth" type="month" value-format="YYYY-MM" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8">
            <el-form-item label="求职身份">
              <el-select v-model="c.identity"><el-option label="应届生" value="应届生" /><el-option label="社招" value="社招" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="政治面貌">
              <el-select v-model="c.politics" clearable>
                <el-option v-for="p in POLITICS" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="现居城市"><el-input v-model="c.city" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="手机"><el-input v-model="c.phone" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="邮箱"><el-input v-model="c.email" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="语言"><el-input v-model="c.languages" placeholder="如：英语 CET-6" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="技能">
            <el-input v-model="c.skills" type="textarea" :autosize="{ minRows: 4, maxRows: 12 }"
                      placeholder="每行一条技能描述，例如：&#10;熟悉 PyTorch，掌握 Megatron-LM / DeepSpeed 分布式训练框架&#10;具备 SFT / LoRA / GRPO 大模型微调与对齐经验" />
          </el-form-item></el-col>
          <el-col :span="24"><el-form-item label="自我评价"><el-input v-model="c.self_evaluation" type="textarea" :rows="3" /></el-form-item></el-col>
        </el-row>
      </el-form>

      <div v-else-if="tab === 'edu'">
        <div class="sec">
          <div class="sec-head"><span>教育经历</span>
            <el-button size="small" @click="c.education.push({ school: '', degree: '本科', major: '', start: '', end: '', rank_: '' })">+ 添加</el-button>
          </div>
          <div v-for="(e, i) in c.education" :key="i" class="entry">
            <el-row :gutter="12">
              <el-col :span="7"><el-input v-model="e.school" placeholder="学校" /></el-col>
              <el-col :span="4"><el-select v-model="e.degree"><el-option v-for="d in DEGREES" :key="d" :label="d" :value="d" /></el-select></el-col>
              <el-col :span="6"><el-input v-model="e.major" placeholder="专业" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.start" type="month" value-format="YYYY-MM" placeholder="起始" class="w100" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.end" type="month" value-format="YYYY-MM" placeholder="至今" class="w100" /></el-col>
              <el-col :span="1"><el-button text type="danger" @click="c.education.splice(i, 1)">删</el-button></el-col>
            </el-row>
            <el-row :gutter="12" style="margin-top:6px">
              <el-col :span="8"><el-input v-model="e.rank_" placeholder="成绩 / 排名（可选），如 GPA 3.7/4.0，专业前 10%" /></el-col>
            </el-row>
          </div>
        </div>

        <div class="sec">
          <div class="sec-head"><span>工作经历</span>
            <el-button size="small" @click="c.work.push({ company: '', title: '', start: '', end: '', description: '' })">+ 添加</el-button>
          </div>
          <div v-for="(e, i) in c.work" :key="i" class="entry">
            <el-row :gutter="12">
              <el-col :span="7"><el-input v-model="e.company" placeholder="公司" /></el-col>
              <el-col :span="5"><el-input v-model="e.title" placeholder="岗位" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.start" type="month" value-format="YYYY-MM" placeholder="起始" class="w100" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.end" type="month" value-format="YYYY-MM" placeholder="至今" class="w100" /></el-col>
              <el-col :span="1" :offset="5"><el-button text type="danger" @click="c.work.splice(i, 1)">删</el-button></el-col>
            </el-row>
            <el-input v-model="e.description" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="工作内容与成果（含量化结果）" style="margin-top:6px" />
          </div>
        </div>

        <div class="sec">
          <div class="sec-head"><span>实习经历</span>
            <el-button size="small" @click="c.internship.push({ company: '', title: '', start: '', end: '', description: '' })">+ 添加</el-button>
          </div>
          <div v-for="(e, i) in c.internship" :key="i" class="entry">
            <el-row :gutter="12">
              <el-col :span="7"><el-input v-model="e.company" placeholder="公司" /></el-col>
              <el-col :span="5"><el-input v-model="e.title" placeholder="岗位" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.start" type="month" value-format="YYYY-MM" placeholder="起始" class="w100" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.end" type="month" value-format="YYYY-MM" placeholder="结束" class="w100" /></el-col>
              <el-col :span="1" :offset="5"><el-button text type="danger" @click="c.internship.splice(i, 1)">删</el-button></el-col>
            </el-row>
            <el-input v-model="e.description" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="实习内容与成果" style="margin-top:6px" />
          </div>
        </div>

        <div class="sec">
          <div class="sec-head"><span>项目经历</span>
            <el-button size="small" @click="c.project.push({ name: '', role: '', start: '', end: '', description: '' })">+ 添加</el-button>
          </div>
          <div v-for="(e, i) in c.project" :key="i" class="entry">
            <el-row :gutter="12">
              <el-col :span="7"><el-input v-model="e.name" placeholder="项目名称" /></el-col>
              <el-col :span="5"><el-input v-model="e.role" placeholder="担任角色" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.start" type="month" value-format="YYYY-MM" placeholder="起始" class="w100" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.end" type="month" value-format="YYYY-MM" placeholder="结束" class="w100" /></el-col>
              <el-col :span="1" :offset="5"><el-button text type="danger" @click="c.project.splice(i, 1)">删</el-button></el-col>
            </el-row>
            <el-input v-model="e.description" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="项目描述与个人贡献" style="margin-top:6px" />
          </div>
        </div>
      </div>

      <div v-else-if="tab === 'pub'">
        <div class="sec">
          <div class="sec-head"><span>论文发表</span>
            <el-button size="small" @click="c.publications.push({ title: '', level: 'CCF-C', venue: '', year: '', authors: '一作' })">+ 添加</el-button>
          </div>
          <div v-for="(e, i) in c.publications" :key="i" class="entry">
            <el-row :gutter="12">
              <el-col :span="8"><el-input v-model="e.title" placeholder="论文标题" /></el-col>
              <el-col :span="4"><el-select v-model="e.level"><el-option v-for="l in PUB_LEVELS" :key="l" :label="l" :value="l" /></el-select></el-col>
              <el-col :span="6"><el-input v-model="e.venue" placeholder="期刊 / 会议" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.year" type="year" value-format="YYYY" placeholder="年份" class="w100" /></el-col>
              <el-col :span="2"><el-select v-model="e.authors"><el-option v-for="a in AUTHOR_POS" :key="a" :label="a" :value="a" /></el-select></el-col>
              <el-col :span="1"><el-button text type="danger" @click="c.publications.splice(i, 1)">删</el-button></el-col>
            </el-row>
          </div>
        </div>

        <div class="sec">
          <div class="sec-head"><span>荣誉奖项</span>
            <el-button size="small" @click="c.awards.push({ name: '', level: '校级', year: '' })">+ 添加</el-button>
          </div>
          <div v-for="(e, i) in c.awards" :key="i" class="entry">
            <el-row :gutter="12">
              <el-col :span="10"><el-input v-model="e.name" placeholder="奖项名称，如 国家奖学金" /></el-col>
              <el-col :span="4"><el-select v-model="e.level"><el-option v-for="l in AWARD_LEVELS" :key="l" :label="l" :value="l" /></el-select></el-col>
              <el-col :span="3"><el-date-picker v-model="e.year" type="year" value-format="YYYY" placeholder="年份" class="w100" /></el-col>
              <el-col :span="1"><el-button text type="danger" @click="c.awards.splice(i, 1)">删</el-button></el-col>
            </el-row>
          </div>
        </div>

        <div class="sec">
          <div class="sec-head"><span>资格证书</span>
            <el-button size="small" @click="c.certificates.push({ name: '', year: '' })">+ 添加</el-button>
          </div>
          <div v-for="(e, i) in c.certificates" :key="i" class="entry">
            <el-row :gutter="12">
              <el-col :span="10"><el-input v-model="e.name" placeholder="证书名称，如 CET-6 / 软考中级" /></el-col>
              <el-col :span="3"><el-date-picker v-model="e.year" type="year" value-format="YYYY" placeholder="年份" class="w100" /></el-col>
              <el-col :span="1"><el-button text type="danger" @click="c.certificates.splice(i, 1)">删</el-button></el-col>
            </el-row>
          </div>
        </div>
      </div>

      <el-form v-else-if="tab === 'pref'" label-width="84px">
        <el-row :gutter="16">
          <el-col :span="8"><el-form-item label="目标城市"><el-input v-model="c.target_cities" placeholder="如：深圳、广州" /></el-form-item></el-col>
          <el-col :span="8">
            <el-form-item label="目标类型">
              <el-select v-model="c.target_type" multiple placeholder="可多选">
                <el-option v-for="t in TARGET_TYPES" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="薪资期望"><el-input v-model="c.salary_expect" placeholder="如：28-35k · 14 薪起" /></el-form-item></el-col>
          <el-col :span="8">
            <el-form-item label="用工底线">
              <el-select v-model="c.employment_bottom_line">
                <el-option label="外包/劳务派遣 一票否决" value="外包/劳务派遣 一票否决" />
                <el-option label="可接受外包" value="可接受外包" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="户口编制">
              <el-select v-model="c.hukou"><el-option v-for="h in HUKOU" :key="h" :label="h" :value="h" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="加班容忍">
              <el-select v-model="c.overtime_tolerance">
                <el-option label="不接受大小周和996" value="不接受大小周和996" />
                <el-option label="可接受大小周，不接受996" value="可接受大小周，不接受996" />
                <el-option label="大小周和996都能接受" value="大小周和996都能接受" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24"><el-form-item label="其他否决"><el-input v-model="c.other_vetoes" type="textarea" :rows="2" placeholder="顿号分隔：如 出差>20%、竞业限制" /></el-form-item></el-col>
        </el-row>
      </el-form>

      <div v-else>
        <div v-for="(s, i) in stars" :key="i" style="margin-bottom:14px">
          <div style="display:flex;gap:10px;margin-bottom:6px">
            <el-input v-model="s.title" placeholder="素材标题，如：订单系统重构 QPS 3k→12k" />
            <el-button text type="danger" @click="stars.splice(i, 1)">删除</el-button>
          </div>
          <el-input v-model="s.content" type="textarea" :rows="3" placeholder="情境 / 任务 / 行动 / 结果" />
        </div>
        <el-button plain @click="stars.push({ title: '', content: '', source: '手填' })">+ 添加素材</el-button>
      </div>

      <div style="margin-top:16px">
        <el-button type="primary" :loading="saving" @click="save"><el-icon style="margin-right:3px"><Check /></el-icon>保存</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api, uploadFile } from '../api'

const DEGREES = ['专科', '本科', '硕士', '博士']
const POLITICS = ['中共党员', '中共预备党员', '共青团员', '民主党派', '群众']
const PUB_LEVELS = ['SCI 一区', 'SCI 二区', 'SCI 三区', 'SCI 四区', 'CCF-A', 'CCF-B', 'CCF-C', 'EI 会议', 'EI 期刊', '北大核心', '南大核心', '其他']
const AUTHOR_POS = ['一作', '二作', '三作及以后', '通讯作者']
const AWARD_LEVELS = ['国家级', '省级', '市级', '校级', '企业/竞赛', '其他']
const TARGET_TYPES = ['互联网大厂', '互联网中厂', '国企央企', '中小厂', '外企']
const HUKOU = ['需要', '加分项', '无所谓']

const tab = ref('basic')
const c = reactive({ education: [], work: [], internship: [], project: [], publications: [], awards: [], certificates: [], target_type: [] })
const stars = ref([])
const saving = ref(false)
const importing = ref(false)
const importElapsed = ref(0)
let importTimer = null

async function doImport({ file }) {
  importing.value = true
  importElapsed.value = 0
  importTimer = setInterval(() => { importElapsed.value++ }, 1000)
  try {
    const d = await uploadFile('/profile/import', file)
    let n = 0
    for (const [k, v] of Object.entries(d.candidate)) {
      if (v === '' || v === null || v === undefined) continue  // 空值不覆盖已填内容
      c[k] = v
      n++
    }
    ElMessage.success(`AI 解析完成，填充 ${n} 项，请核对后保存`)
  } catch (e) { ElMessage.error(e.message) } finally { importing.value = false; if (importTimer) clearInterval(importTimer) }
}

onMounted(async () => {
  const d = await api.get('/profile')
  Object.assign(c, d.candidate)
  stars.value = d.stars
})

async function save() {
  saving.value = true
  try {
    await api.put('/profile', { candidate: JSON.parse(JSON.stringify(c)), stars: stars.value })
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}
</script>

<style scoped>
.sec { margin-bottom: 18px; }
.sec-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; font-size: 14px; font-weight: 600; }
.entry { border: 1px solid #e4e8f0; border-radius: 8px; padding: 10px; margin-bottom: 8px; }
.w100 { width: 100%; }
</style>
