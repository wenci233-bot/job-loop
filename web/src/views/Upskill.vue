<template>
  <div>
    <div class="page-title">技能提升</div>

    <div class="page-card">
      <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
        <el-button type="primary" :loading="generating" @click="makeRoadmap">
          <el-icon style="margin-right:3px"><MagicStick /></el-icon>{{ roadmap ? '重新生成路线图' : 'AI 生成学习路线图' }}
        </el-button>
        <el-button :loading="analyzing" @click="loadGaps">
          <el-icon style="margin-right:3px"><TrendCharts /></el-icon>刷新差距热图
        </el-button>
        <span class="muted" v-if="roadmap">生成于 {{ roadmap.date }}</span>
      </div>
    </div>

    <div class="page-card" v-if="roadmap">
      <div class="sec-title" style="display:flex;align-items:center;gap:6px">
        <el-icon color="#18a058"><Guide /></el-icon>学习路线图
        <span class="muted" style="margin-left:auto">{{ doneCount }}/{{ roadmap.roadmap.length }} 阶段完成</span>
      </div>

      <div class="dir-card">
        <div class="dir-label">画像概述</div>
        <p class="dir-text">{{ roadmap.direction }}</p>
        <p class="dir-advice" v-if="roadmap.advice"><el-icon><InfoFilled /></el-icon>{{ roadmap.advice }}</p>
      </div>

      <div class="phase-wrap">
        <div v-for="(p, idx) in roadmap.roadmap" :key="p.phase" class="phase-item">
          <!-- 左侧轨道 -->
          <div class="ph-rail">
            <span class="ph-dot" :class="{ done: p.done, current: isCurrent(p) }">{{ p.done ? '✓' : p.phase }}</span>
            <span class="ph-line" v-if="idx < roadmap.roadmap.length - 1"></span>
          </div>
          <!-- 阶段卡 -->
          <div class="phase-box" :class="{ current: isCurrent(p), done: p.done }">
            <div class="ph-badge" :class="isCurrent(p) ? 'now' : (p.done ? 'ok' : '')">
              {{ p.done ? '已完成' : (isCurrent(p) ? '▶ 当前阶段 · 从这里开始' : '待开始') }}
            </div>
            <div class="ph-title-row">
              <b class="ph-title">{{ p.title }}</b>
              <span class="ph-weeks">约 {{ p.weeks }} 周</span>
            </div>
            <p class="ph-goal" v-if="p.why">{{ p.why }}</p>
            <p class="ph-goal">{{ p.goal }}</p>
            <div class="ph-block">
              <span class="blk-label">学什么</span>
              <div class="ph-topics">
                <span class="topic-chip" v-for="(t, i) in p.topics" :key="i" :class="{ first: i === 0 }">{{ t }}</span>
              </div>
            </div>
            <div class="ph-block" v-if="p.closes?.length">
              <span class="blk-label ok">弥补哪些岗位要求</span>
              <div class="ph-topics" style="margin-top:4px">
                <span class="topic-chip close-chip" v-for="(c, i) in p.closes" :key="i">{{ c }}</span>
              </div>
            </div>
            <div class="ph-block" v-if="p.milestone">
              <span class="blk-label purple">完成检验</span>
              <p class="milestone">{{ p.milestone }}</p>
            </div>
            <div class="plan-res" v-if="p.resources?.length">
              <a v-for="(r, j) in p.resources" :key="j" :href="r.url" target="_blank" rel="noopener" class="res-link">
                <el-icon><Link /></el-icon>{{ r.title }}
              </a>
            </div>
            <div style="margin-top:10px">
              <el-button size="small" :type="p.done ? 'success' : 'default'" plain @click="toggleDone(p)">
                <el-icon style="margin-right:3px"><Check /></el-icon>{{ p.done ? '已完成' : '标记完成' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="page-card" v-if="gapData.gaps?.length">
      <div class="sec-title" style="display:flex;align-items:center;gap:6px">
        <el-icon color="#e07c1f"><TrendCharts /></el-icon>技能差距热图（关键词频次参考）
      </div>
      <div class="heat" v-for="(g, i) in gapData.gaps" :key="i">
        <span class="h-rank" :class="'r' + heatLevel(g)">{{ i + 1 }}</span>
        <span class="h-name">{{ g.keyword }}</span>
        <div class="h-track">
          <div class="h-fill" :style="{ width: heatWidth(g) + '%', background: heatColor(g) }"></div>
        </div>
        <span class="h-meta">
          <span class="h-pct num-tabular">{{ Math.round(heatWidth(g)) }}%</span>
          <el-tag v-if="g.stuck_count" size="small" type="danger" style="margin-left:6px">★卡壳 {{ g.stuck_count }}</el-tag>
        </span>
      </div>
      <div class="heat-legend">
        <span><i style="background:#d93025"></i>面试卡壳</span>
        <span><i style="background:#f0894f"></i>高频要求</span>
        <span><i style="background:#4a90d9"></i>一般差距</span>
      </div>
    </div>

    <div class="page-card" v-if="!roadmap && !generating">
      <el-empty description="添加目标岗位后，AI 生成你的专属学习路线图" :image-size="90" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const gapData = ref({})
const roadmap = ref(null)
const analyzing = ref(false)
const generating = ref(false)

const doneCount = computed(() => (roadmap.value?.roadmap || []).filter(p => p.done).length)
const currentPhase = computed(() => {
  const p = (roadmap.value?.roadmap || []).find(x => !x.done)
  return p ? p.phase : 99
})
const covType = (c) => ({ 已覆盖: 'success', 部分覆盖: 'warning', 缺口: 'danger' }[c] || 'info')

const isCurrent = (p) => {
  const first = (roadmap.value?.roadmap || []).find(x => !x.done)
  return first ? first.phase === p.phase : false
}

const heatLevel = (g) => (g.stuck_count > 0 ? 3 : g.jd_count >= 2 ? 2 : 1)
const heatColor = (g) => {
  const lv = heatLevel(g)
  const w = heatWidth(g)
  if (lv === 3) return 'linear-gradient(90deg, #d93025, #f0704f)'
  if (lv === 2 || w > 55) return 'linear-gradient(90deg, #e07c1f, #f0b26a)'
  return 'linear-gradient(90deg, #4a90d9, #7ab3ec)'
}

const heatWidth = (g) => {
  const max = Math.max(...(gapData.value.gaps || []).map(x => x.jd_count * 2 + x.stuck_count * 3), 1)
  return Math.max(8, ((g.jd_count * 2 + g.stuck_count * 3) / max) * 100)
}

async function loadGaps() {
  analyzing.value = true
  try { gapData.value = await api.get('/upskill/gaps') } finally { analyzing.value = false }
}

async function makeRoadmap() {
  generating.value = true
  try {
    const d = await api.post('/upskill/roadmap')
    roadmap.value = d.roadmap
    ElMessage.success(`路线图已生成：${d.roadmap.roadmap.length} 个阶段`)
  } catch (e) { ElMessage.error(e.message) } finally { generating.value = false }
}

async function toggleDone(p) {
  try {
    roadmap.value = await api.post('/upskill/roadmap/progress', { phase: p.phase, done: !p.done })
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(async () => {
  await loadGaps()
  const d = await api.get('/upskill/roadmap')
  if (d.roadmap) roadmap.value = d.roadmap
})
</script>

<style scoped>
.sec-title { font-size: 14.5px; font-weight: 600; margin-bottom: 12px; }
.direction { font-size: 13px; color: #3d4757; line-height: 1.8; background: #f8faff; border: 1px solid #e3eaf8; border-radius: 10px; padding: 12px 14px; }
.heat { display: flex; align-items: center; gap: 12px; margin: 10px 0; }
.h-name { width: 150px; flex-shrink: 0; font-size: 13px; color: #1f2733; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.h-track { flex: 1; height: 16px; background: #f0f2f7; border-radius: 5px; overflow: hidden; }
.h-fill { height: 100%; background: #2f66f6; border-radius: 5px; transition: width .6s cubic-bezier(.22,1,.36,1); }
.h-fill.stuck { background: linear-gradient(90deg, #d93025, #f0704f); }
.h-meta { width: 210px; flex-shrink: 0; font-size: 12px; color: #5b6575; display: flex; align-items: center; }
.closes-label { color: #18a058; font-weight: 600; }
.closes-item { display: inline-block; margin-right: 10px; }
.plan-res { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.res-link { display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; color: #2f66f6; text-decoration: none; background: #f0f5ff; border-radius: 6px; padding: 4px 10px; }
.res-link:hover { background: #e0eaff; }
.advice { margin-top: 6px; font-size: 12.5px; color: #3d4757; background: #f8faff; border: 1px dashed #c9d6f2; border-radius: 8px; padding: 8px 12px; line-height: 1.6; }
.dir-card { background: linear-gradient(180deg, #f8faff, #f3f6fd); border: 1px solid #e3eaf8; border-radius: 12px; padding: 18px 20px 14px; margin-bottom: 18px; }
.dir-divider { height: 1px; background: linear-gradient(90deg, transparent, #d8e2f5, transparent); margin: 6px 0 12px; }
.dir-text { margin: 0 0 8px; font-size: 13.5px; color: #1f2733; line-height: 1.8; }
.dir-advice { display: flex; align-items: flex-start; gap: 5px; margin: 0; font-size: 12.5px; color: #5b6575; line-height: 1.7; }
.dir-advice .el-icon { margin-top: 3px; flex-shrink: 0; color: #e07c1f; }
.phase-wrap { display: flex; flex-direction: column; }
.phase-item { display: flex; gap: 14px; }
.ph-rail { width: 34px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; }
.ph-dot { width: 30px; height: 30px; border-radius: 50%; background: #eef2fb; color: #2f66f6; font-weight: 700; font-size: 13px; display: grid; place-items: center; border: 2px solid #d5e0f5; flex-shrink: 0; }
.ph-dot.current { background: #2f66f6; color: #fff; border-color: #2f66f6; box-shadow: 0 0 0 4px rgba(47,102,246,.15); }
.ph-dot.done { background: #18a058; color: #fff; border-color: #18a058; }
.ph-line { flex: 1; width: 2px; background: #dfe5f0; margin: 4px 0; }
.phase-box { flex: 1; min-width: 0; border: 1px solid #e8ecf4; border-radius: 12px; padding: 16px 18px; margin-bottom: 18px; background: #fff; transition: box-shadow .2s ease, border-color .2s ease; }
.phase-box.current { border-color: #2f66f6; box-shadow: 0 4px 16px rgba(47,102,246,.13); background: linear-gradient(180deg, #f8faff, #fff); }
.phase-box.done { opacity: .75; }
.ph-badge { display: inline-block; font-size: 11px; font-weight: 600; border-radius: 6px; padding: 2px 8px; margin-bottom: 8px; background: #f0f2f7; color: #8a93a3; }
.ph-badge.now { background: #2f66f6; color: #fff; }
.ph-badge.ok { background: #e6f7ee; color: #18a058; }
.ph-title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.ph-title { font-size: 14.5px; color: #1f2733; }
.ph-weeks { font-size: 12px; color: #e07c1f; font-weight: 600; }
.ph-goal { font-size: 13px; color: #3d4757; line-height: 1.75; margin: 0 0 10px; }
.ph-block { margin-bottom: 10px; }
.blk-label { display: inline-block; font-size: 11.5px; font-weight: 600; color: #2f66f6; background: #eef3ff; border-radius: 5px; padding: 1px 8px; margin-bottom: 6px; }
.blk-label.ok { color: #18a058; background: #e6f7ee; }
.blk-label.purple { color: #7a5af5; background: #f0ecfe; }
.ph-topics { display: flex; flex-wrap: wrap; gap: 6px; }
.topic-chip { font-size: 12.5px; color: #3d4757; background: #f5f7fb; border: 1px solid #e4e8f0; border-radius: 6px; padding: 3px 10px; }
.topic-chip.first { border-color: #2f66f6; color: #2f66f6; font-weight: 500; }
.milestone { margin: 4px 0 0; font-size: 12.5px; color: #5b3ea8; background: #f8f5ff; border-left: 3px solid #7a5af5; border-radius: 6px; padding: 7px 10px; line-height: 1.6; }
</style>
