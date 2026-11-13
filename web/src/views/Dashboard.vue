<template>
  <div>
    <div class="page-title">首页</div>

    <!-- Hero：渐变 + 光斑视差 + 波浪 + 玻璃数据面板 -->
    <section class="hero" :class="{ in: mounted }" @mousemove="onHeroMove" @mouseleave="parallax.x = 0; parallax.y = 0">
      <div class="orb-pos" :style="{ transform: `translate(${parallax.x * 20}px, ${parallax.y * 14}px)` }">
        <div class="hero-orb orb-a"></div>
      </div>
      <div class="orb-pos" :style="{ transform: `translate(${parallax.x * -14}px, ${parallax.y * -10}px)` }">
        <div class="hero-orb orb-b"></div>
      </div>
      <span class="spark s1" :style="{ transform: `translate(${parallax.x * 30}px, ${parallax.y * 22}px)` }">✦</span>
      <span class="spark s2" :style="{ transform: `translate(${parallax.x * -24}px, ${parallax.y * 16}px)` }">✦</span>
      <span class="spark s3" :style="{ transform: `translate(${parallax.x * 16}px, ${parallax.y * -18}px)` }">✦</span>

      <svg class="hero-wave w1" viewBox="0 0 1440 110" preserveAspectRatio="none">
        <path d="M0,64 C240,110 480,10 720,44 C960,78 1200,96 1440,52 L1440,110 L0,110 Z" fill="rgba(255,255,255,.07)"></path>
      </svg>
      <svg class="hero-wave w2" viewBox="0 0 1440 110" preserveAspectRatio="none">
        <path d="M0,80 C260,30 520,100 760,66 C1000,32 1240,60 1440,84 L1440,110 L0,110 Z" fill="rgba(255,255,255,.05)"></path>
      </svg>

      <div class="hero-inner">
        <div class="hero-text">
          <div class="hero-greet">{{ greeting }}<b>{{ name }}</b></div>
          <div class="hero-date">{{ dateText }}</div>
          <div class="hero-next" v-if="nextStep">
            <span class="next-dot"></span>{{ nextStep.text }}
            <a class="next-link" @click="$router.push(nextStep.to)">
              {{ nextStep.action }}<el-icon :size="13"><ArrowRight /></el-icon>
            </a>
          </div>
        </div>

        <div class="hero-side" v-if="heroSide.ready">
          <div class="ring-wrap">
            <svg viewBox="0 0 90 90" class="ring">
              <circle class="ring-bg" cx="45" cy="45" r="34"></circle>
              <circle class="ring-fg" cx="45" cy="45" r="34"
                      :stroke-dasharray="RING_C" :stroke-dashoffset="mounted ? RING_C * (1 - heroSide.pct / 100) : RING_C"></circle>
            </svg>
            <div class="ring-center">
              <b class="num-tabular">{{ heroSide.pct }}%</b>
              <span>全程转化</span>
            </div>
          </div>
          <div class="hero-mini">
            <div class="hm-row" v-for="r in heroSide.rows" :key="r.label">
              <span class="hm-dot" :style="{ background: r.color }"></span>
              <span class="hm-label">{{ r.label }}</span>
              <b class="num-tabular">{{ r.value }}</b>
            </div>
          </div>
        </div>

        <button class="hero-cta" @click="$router.push('/inbox')">
          <el-icon style="margin-right:6px"><Promotion /></el-icon>去贴一份 JD
        </button>
      </div>
    </section>

    <!-- 统计卡：专属渐变 + 彩色投影 -->
    <section class="stats" :class="{ in: mounted }">
      <div class="stat-card" v-for="(s, i) in statCards" :key="s.label"
           :style="{ '--sc': s.color, '--sc1': s.c1, '--sc2': s.c2, transitionDelay: mounted ? (140 + i * 70) + 'ms' : '0ms' }"
           @click="$router.push(s.to)">
        <span class="stat-grad-chip"><el-icon :size="19"><component :is="s.icon" /></el-icon></span>
        <div class="stat-info">
          <div class="stat-num num-tabular">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
        <span class="stat-arrow"><el-icon :size="12"><ArrowRight /></el-icon></span>
      </div>
    </section>

    <el-row :gutter="14">
      <el-col :xs="24" :lg="12">
        <div class="page-card">
          <div class="sec-head">
            <el-icon color="#7a5af5"><TrendCharts /></el-icon>求职漏斗（累计）
            <span class="muted" style="margin-left:auto;font-weight:400">悬停查看各层转化</span>
          </div>
          <svg viewBox="0 0 470 286" style="width:100%;display:block" role="img" aria-label="求职漏斗图">
            <defs>
              <linearGradient v-for="(s, i) in funnelStages" :id="'fn-g' + i" :key="'g' + i" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" :stop-color="s.c1" /><stop offset="1" :stop-color="s.c2" />
              </linearGradient>
              <linearGradient :id="'fn-gl'" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#fff" stop-opacity=".28" /><stop offset="1" stop-color="#fff" stop-opacity="0" />
              </linearGradient>
              <filter id="fn-sh" x="-20%" y="-20%" width="140%" height="160%">
                <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#17324f" flood-opacity="0.2" />
              </filter>
            </defs>
            <g v-for="(s, i) in funnelStages" :key="s.label" class="fstage" :class="{ hov: hoverStage === i, offer: s.isOffer }"
               @mouseenter="hoverStage = i" @mouseleave="hoverStage = -1"
               :style="{ opacity: ready ? 1 : 0, transform: ready ? 'none' : 'translateY(10px) scale(.96)', transitionDelay: ready ? (i * 90) + 'ms' : '0ms' }">
              <polygon :points="s.points" :fill="`url(#fn-g${i})`" stroke-linejoin="round"
                       stroke-width="5" :stroke="`url(#fn-g${i})`" filter="url(#fn-sh)" />
              <polygon :points="s.gloss" fill="url(#fn-gl)" pointer-events="none" />
              <text v-if="s.wTop >= 130" :x="200" :y="s.y + 25" text-anchor="middle" fill="#fff" font-size="12.5" font-weight="600">
                {{ s.label }}<tspan fill="#dfe9ff" font-weight="400"> · {{ s.value }}</tspan>
              </text>
              <text v-else :x="200 + s.wTop / 2 + 10" :y="s.y + 24" text-anchor="start" fill="#3d4757" font-size="12.5" font-weight="600">
                {{ s.label }} · {{ s.value }}
              </text>
              <g v-if="s.conv !== null" class="conv-pill" :style="{ opacity: hoverStage === -1 || hoverStage === i ? 1 : .3 }">
                <rect x="404" :y="s.y + s.h - 3" width="62" height="20" rx="10"
                      :fill="convBg(s.conv)" :stroke="convEdge(s.conv)" />
                <text :x="435" :y="s.y + s.h + 11" text-anchor="middle" :fill="convFg(s.conv)" font-size="11" font-weight="600">
                  ↓ {{ s.conv }}%
                </text>
              </g>
            </g>
          </svg>
        </div>
      </el-col>
      <el-col :xs="24" :lg="12">
        <div class="page-card todo-card">
          <div class="sec-head">
            <el-icon color="#e07c1f"><Bell /></el-icon>待办提醒
            <span class="sec-badge" v-if="summary.todos?.length">{{ summary.todos.length }}</span>
          </div>
          <template v-if="summary.todos?.length">
            <div v-for="(t, i) in summary.todos" :key="i" class="todo-row">
              <span class="todo-chip"><el-icon :size="15"><Clock /></el-icon></span>
              <div class="todo-info">
                <div class="todo-main">{{ t.company }} · {{ t.role }}</div>
                <div class="muted">{{ t.detail }}</div>
              </div>
              <el-button size="small" type="primary" plain @click="$router.push('/jobs')">{{ t.action }}</el-button>
            </div>
          </template>
          <div class="start" v-else>
            <div class="start-label">暂无待办 · 今天从这里继续推进</div>
            <div class="start-row">
              <div class="start-item" v-for="q in quickStarts" :key="q.to" @click="$router.push(q.to)">
                <span class="chip" :class="q.chip"><el-icon :size="16"><component :is="q.icon" /></el-icon></span>
                <div class="start-info">
                  <b>{{ q.title }}</b>
                  <span>{{ q.hint }}</span>
                </div>
                <el-icon class="start-arrow"><ArrowRight /></el-icon>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card">
      <div class="sec-head">
        <el-icon color="#2f66f6"><Grid /></el-icon>功能入口
      </div>
      <div class="mod-grid" :class="{ in: mounted }">
        <div class="mod-card" v-for="(m, i) in modules" :key="m.path"
             :style="{ '--mc': m.color, '--mc1': m.c1, '--mc2': m.c2, transitionDelay: mounted ? (300 + i * 60) + 'ms' : '0ms' }"
             @click="$router.push(m.path)">
          <span class="mod-chip"><el-icon :size="19"><component :is="m.icon" /></el-icon></span>
          <b>{{ m.title }}</b>
          <span class="mod-arrow"><el-icon :size="11"><ArrowRight /></el-icon></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const summary = ref({})
const name = ref('')
const mounted = ref(false)
const ready = ref(false)
const hoverStage = ref(-1)
const parallax = reactive({ x: 0, y: 0 })

const RING_C = 213.63

function onHeroMove(e) {
  const r = e.currentTarget.getBoundingClientRect()
  parallax.x = ((e.clientX - r.left) / r.width - 0.5) * 2
  parallax.y = ((e.clientY - r.top) / r.height - 0.5) * 2
}

function tween(key, target) {
  const t0 = performance.now(), dur = 750
  const tick = (t) => {
    const p = Math.min(1, (t - t0) / dur)
    display[key] = Math.round(target * (1 - Math.pow(1 - p, 3)))
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

const display = reactive({ applying: 0, interviewing: 0, offer: 0, finished: 0 })

const hour = new Date().getHours()
const greeting = hour < 6 ? '凌晨好' : hour < 9 ? '早上好' : hour < 12 ? '上午好'
  : hour < 14 ? '中午好' : hour < 18 ? '下午好' : '晚上好'
const dateText = new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })

// 智能下一步：待办 > 未评估 > 未投递 > 面试准备 > Offer 对比 > 开始
const nextStep = computed(() => {
  const f = summary.value.funnel || {}
  const st = summary.value.stats || {}
  const todo = summary.value.todos || []
  if (todo.length) return { text: `「${todo[0].company} · ${todo[0].role}」${todo[0].detail}`, action: todo[0].action, to: '/jobs' }
  const gapEval = (f.collected ?? 0) - (f.evaluated ?? 0)
  if (gapEval > 0) return { text: `有 ${gapEval} 个岗位还没评估`, action: '去评估', to: '/jobs' }
  const gapApply = (f.evaluated ?? 0) - (f.applied ?? 0)
  if (gapApply > 0) return { text: `候选池有 ${gapApply} 个岗位通过评估，还没投递`, action: '去投递', to: '/jobs' }
  if (st.interviewing > 0) return { text: `有 ${st.interviewing} 场面试进行中`, action: '去准备', to: '/interview' }
  if (st.offer > 0) return { text: `已拿到 ${st.offer} 个 Offer，记得复盘对比`, action: '去复盘', to: '/debrief' }
  if ((f.collected ?? 0) === 0) return { text: '求职漏斗还是空的', action: '贴第一份 JD', to: '/inbox' }
  return { text: '各阶段都在推进', action: '看看技能提升', to: '/upskill' }
})

const heroSide = computed(() => {
  const f = summary.value.funnel || {}
  const collected = f.collected ?? 0
  const pct = collected ? Math.round(((f.offer ?? 0) / collected) * 100) : 0
  return {
    ready: collected > 0 || (f.applied ?? 0) > 0,
    pct,
    rows: [
      { label: '收集', value: collected, color: '#6d97ff' },
      { label: '面试', value: f.interviewing ?? 0, color: '#3d63f2' },
      { label: 'Offer', value: f.offer ?? 0, color: '#18a058' },
    ],
  }
})

onMounted(async () => {
  requestAnimationFrame(() => { mounted.value = true })
  const [d, p] = await Promise.all([
    api.get('/dashboard/summary'),
    api.get('/profile').catch(() => null),
  ])
  summary.value = d
  name.value = p?.candidate?.name || ''
  const s = d.stats || {}
  for (const k of ['applying', 'interviewing', 'offer', 'finished']) tween(k, s[k] ?? 0)
  setTimeout(() => { ready.value = true }, 200)
})

const statCards = computed(() => [
  { label: '投递中', value: display.applying, icon: 'Promotion', to: '/jobs', color: '#2f66f6', c1: '#5b8cff', c2: '#2f66f6' },
  { label: '面试中', value: display.interviewing, icon: 'Calendar', to: '/interview', color: '#7a5af5', c1: '#a78bfa', c2: '#7a5af5' },
  { label: 'Offer', value: display.offer, icon: 'Trophy', to: '/jobs', color: '#18a058', c1: '#34cc85', c2: '#17996a' },
  { label: '已出结果', value: display.finished, icon: 'CircleCheckFilled', to: '/jobs', color: '#f0654a', c1: '#ff9a7b', c2: '#f0654a' },
])

// 转化胶囊分色：顺畅绿 / 一般橙 / 卡点红
const convBg = (v) => (v >= 70 ? '#e6f7ee' : v >= 40 ? '#fdf3e5' : '#fdeceb')
const convEdge = (v) => (v >= 70 ? '#bfe8d2' : v >= 40 ? '#f3ddba' : '#f6ccc8')
const convFg = (v) => (v >= 70 ? '#17996a' : v >= 40 ? '#c96a10' : '#d93025')

const funnelStages = computed(() => {
  const f = summary.value.funnel || {}
  const rows = [
    { label: '收集', value: f.collected ?? 0, c1: '#6d97ff', c2: '#3f74f5' },
    { label: '评估通过', value: f.evaluated ?? 0, c1: '#5b86fb', c2: '#3564ef' },
    { label: '投递', value: f.applied ?? 0, c1: '#4a74f7', c2: '#2b55e8' },
    { label: '面试', value: f.interviewing ?? 0, c1: '#3d63f2', c2: '#2347d6' },
    { label: 'Offer', value: f.offer ?? 0, c1: '#34cc85', c2: '#17996a', isOffer: true },
  ]
  const max = Math.max(...rows.map(r => r.value), 1)
  return rows.map((r, i) => {
    const y = i * 54 + 6
    const h = 42
    const wTop = 90 + (r.value / max) * 240
    const next = rows[i + 1]
    const wBot = next ? 90 + (next.value / max) * 240 : wTop * 0.86
    const conv = next && r.value ? Math.round((next.value / r.value) * 100) : null
    const pts = [[200 - wTop / 2, y], [200 + wTop / 2, y], [200 + wBot / 2, y + h], [200 - wBot / 2, y + h]]
    const gloss = [[pts[0][0], y], [pts[1][0], y], [pts[2][0] - (pts[2][0] - pts[1][0]) * 0.4, y + h * 0.52], [pts[3][0] + (pts[0][0] - pts[3][0]) * -0.4, y + h * 0.52]]
    return { ...r, y, h, wTop, wBot, conv,
      points: pts.map(p => p.join(',')).join(' '),
      gloss: gloss.map(p => p.join(',')).join(' ') }
  })
})

const quickStarts = [
  { title: '贴一份 JD', hint: '岗位收集', to: '/inbox', icon: 'Box', chip: 'purple' },
  { title: '评估候选池', hint: '投递中心', to: '/jobs', icon: 'Promotion', chip: 'green' },
  { title: '练一场模拟面试', hint: '面试准备', to: '/interview', icon: 'Memo', chip: 'orange' },
]

const modules = [
  { path: '/profile', title: '个人档案', icon: 'User', color: '#2f66f6', c1: '#5b8cff', c2: '#2f66f6' },
  { path: '/inbox', title: '岗位收集', icon: 'Box', color: '#7a5af5', c1: '#a78bfa', c2: '#7a5af5' },
  { path: '/jobs', title: '投递中心', icon: 'Promotion', color: '#18a058', c1: '#34cc85', c2: '#17996a' },
  { path: '/interview', title: '面试准备', icon: 'Memo', color: '#e07c1f', c1: '#f5b26b', c2: '#e07c1f' },
  { path: '/debrief', title: '面试复盘', icon: 'EditPen', color: '#2f66f6', c1: '#5b8cff', c2: '#2f66f6' },
  { path: '/upskill', title: '技能提升', icon: 'Reading', color: '#e07c1f', c1: '#f5b26b', c2: '#e07c1f' },
]
</script>

<style scoped>
/* ---- Hero ---- */
.hero { position: relative; overflow: hidden; border-radius: 16px; padding: 30px 32px 34px; margin-bottom: 14px;
  background: linear-gradient(118deg, #101c47 0%, #1c3aad 38%, #2f66f6 72%, #5f8dff 100%);
  color: #fff; opacity: 0; transform: translateY(12px);
  box-shadow: 0 18px 44px rgba(16, 28, 71, .28); }
.hero.in { opacity: 1; transform: none; transition: opacity .6s ease, transform .7s cubic-bezier(.16,1,.3,1); }
.orb-pos { position: absolute; inset: 0; pointer-events: none; transition: transform .35s ease-out; }
.hero-orb { position: absolute; border-radius: 50%; filter: blur(58px); opacity: .55; }
.orb-a { width: 340px; height: 340px; background: #6f9bff; top: -150px; right: 4%; animation: orb-drift 9s ease-in-out infinite alternate; }
.orb-b { width: 280px; height: 280px; background: #8b5cf6; bottom: -160px; left: 12%; animation: orb-drift 12s ease-in-out infinite alternate-reverse; }
@keyframes orb-drift { from { transform: translate(0, 0); } to { transform: translate(48px, 22px); } }
.spark { position: absolute; color: rgba(255, 255, 255, .75); font-size: 13px; pointer-events: none;
  transition: transform .35s ease-out; animation: spark-twinkle 3.2s ease-in-out infinite; }
.spark.s1 { top: 22%; left: 46%; }
.spark.s2 { top: 64%; left: 30%; font-size: 10px; animation-delay: 1.1s; }
.spark.s3 { top: 30%; left: 62%; font-size: 11px; animation-delay: 2s; }
@keyframes spark-twinkle { 0%, 100% { opacity: .25; } 50% { opacity: .9; } }
.hero-wave { position: absolute; left: 0; right: 0; bottom: -2px; width: 100%; height: 90px; pointer-events: none; }
.hero-wave.w1 { animation: wave-sway 13s ease-in-out infinite alternate; }
.hero-wave.w2 { animation: wave-sway 17s ease-in-out infinite alternate-reverse; }
@keyframes wave-sway { from { transform: translateX(0); } to { transform: translateX(-26px); } }

.hero-inner { position: relative; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; z-index: 1; }
.hero-text { flex: 1; min-width: 260px; }
.hero-greet { font-size: 27px; font-weight: 700; letter-spacing: .5px; text-shadow: 0 2px 14px rgba(10, 22, 70, .35); }
.hero-greet b { margin-left: 9px; background: linear-gradient(90deg, #cfe0ff, #8fb5ff); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.hero-date { margin-top: 6px; font-size: 12.5px; color: #b9cdfa; }
.hero-next { display: flex; align-items: center; gap: 8px; margin-top: 16px; font-size: 13px; color: #e9efff;
  background: rgba(255, 255, 255, .12); border: 1px solid rgba(255, 255, 255, .22); border-radius: 11px;
  padding: 9px 15px; width: fit-content; max-width: 100%; backdrop-filter: blur(6px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .14); }
.next-dot { flex-shrink: 0; width: 7px; height: 7px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 0 3px rgba(74, 222, 128, .25); animation: dot-pulse 2.2s ease-in-out infinite; }
@keyframes dot-pulse { 0%, 100% { box-shadow: 0 0 0 3px rgba(74, 222, 128, .25); } 50% { box-shadow: 0 0 0 6px rgba(74, 222, 128, .08); } }
.next-link { display: inline-flex; align-items: center; gap: 2px; margin-left: 4px; color: #fff; font-weight: 600; cursor: pointer;
  border-bottom: 1px dashed rgba(255, 255, 255, .5); transition: all .2s ease; }
.next-link:hover { border-bottom-color: #fff; gap: 5px; }

/* Hero 玻璃数据面板 */
.hero-side { display: flex; align-items: center; gap: 16px; padding: 13px 18px; border-radius: 14px;
  background: rgba(255, 255, 255, .1); border: 1px solid rgba(255, 255, 255, .22);
  backdrop-filter: blur(8px); box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16), 0 10px 26px rgba(10, 22, 70, .22); }
.ring-wrap { position: relative; width: 86px; height: 86px; }
.ring { width: 100%; height: 100%; transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: rgba(255, 255, 255, .16); stroke-width: 7; }
.ring-fg { fill: none; stroke: #4ade80; stroke-width: 7; stroke-linecap: round;
  filter: drop-shadow(0 0 5px rgba(74, 222, 128, .55));
  transition: stroke-dashoffset 1.3s cubic-bezier(.22, 1, .36, 1) .45s; }
.ring-center { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; }
.ring-center b { font-size: 17px; font-weight: 700; line-height: 1.1; }
.ring-center span { font-size: 10px; color: #c3d4fb; }
.hero-mini { display: flex; flex-direction: column; gap: 7px; }
.hm-row { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
.hm-dot { width: 8px; height: 8px; border-radius: 3px; }
.hm-label { color: #c3d4fb; width: 36px; }
.hm-row b { margin-left: auto; font-size: 14px; min-width: 18px; text-align: right; }

.hero-cta { position: relative; overflow: hidden; display: inline-flex; align-items: center; border: none; cursor: pointer;
  background: #fff; color: #1c3ca8; font-size: 14px; font-weight: 600; font-family: inherit;
  padding: 12px 26px; border-radius: 26px; transition: transform .2s ease, box-shadow .25s ease;
  box-shadow: 0 8px 22px rgba(8, 20, 70, .3); }
.hero-cta:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(8, 20, 70, .42); }
.hero-cta:active { transform: translateY(0); }
.hero-cta::after { content: ""; position: absolute; top: 0; left: -70%; width: 45%; height: 100%;
  background: linear-gradient(105deg, transparent, rgba(47, 102, 246, .18), transparent); transform: skewX(-20deg); transition: left .55s ease; }
.hero-cta:hover::after { left: 130%; }

/* ---- 统计卡 ---- */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 14px; }
.stat-card { position: relative; display: flex; align-items: center; gap: 13px; cursor: pointer; overflow: hidden;
  border: 1px solid #eaeef6; border-radius: 13px; padding: 17px 18px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--sc) 9%, #fff) 0%, #fff 58%);
  opacity: 0; transform: translateY(12px);
  transition: opacity .5s ease, transform .55s cubic-bezier(.16,1,.3,1), box-shadow .28s ease, border-color .28s ease; }
.stats.in .stat-card { opacity: 1; transform: none; }
.stat-card::before { content: ""; position: absolute; right: -16px; top: -20px; width: 84px; height: 84px; border-radius: 50%;
  border: 13px solid var(--sc); opacity: .07; transition: transform .3s ease; }
.stat-card:hover { transform: translateY(-4px) !important; border-color: color-mix(in srgb, var(--sc) 38%, #fff);
  box-shadow: 0 12px 26px color-mix(in srgb, var(--sc) 24%, transparent); }
.stat-card:hover::before { transform: scale(1.15) rotate(10deg); }
.stat-card:hover .stat-grad-chip { transform: scale(1.1) rotate(-6deg); box-shadow: 0 7px 16px color-mix(in srgb, var(--sc) 45%, transparent); }
.stat-card:hover .stat-arrow { opacity: 1; transform: translateX(0); }
.stat-grad-chip { flex-shrink: 0; width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; color: #fff;
  background: linear-gradient(135deg, var(--sc1), var(--sc2));
  box-shadow: 0 5px 13px color-mix(in srgb, var(--sc) 38%, transparent);
  transition: transform .3s cubic-bezier(.34,1.56,.64,1), box-shadow .3s ease; }
.stat-num { font-size: 28px; font-weight: 800; line-height: 1.05; color: #1f2733; }
.stat-label { font-size: 12px; color: #8a93a3; margin-top: 3px; }
.stat-arrow { margin-left: auto; flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; background: var(--sc); color: #fff;
  display: grid; place-items: center; opacity: 0; transform: translateX(-8px); transition: all .25s ease; }

/* ---- 区块标题 ---- */
.sec-head { display: flex; align-items: center; gap: 7px; font-size: 14px; font-weight: 600; margin: 0 0 12px; }
.sec-head::before { content: ""; width: 4px; height: 14px; border-radius: 2px; background: linear-gradient(180deg, #5b8cff, #2f66f6); }
.sec-badge { min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; background: #d93025; color: #fff;
  font-size: 11px; font-weight: 600; display: inline-grid; place-items: center; }

/* ---- 漏斗 ---- */
.fstage { cursor: default; transform-box: fill-box; transform-origin: center top;
  transition: transform .5s cubic-bezier(.16,1,.3,1), opacity .5s ease, filter .25s ease; }
.fstage.hov { filter: brightness(1.08) saturate(1.07); transform: scale(1.025); }
.fstage.offer polygon:first-of-type { animation: offer-glow 2.8s ease-in-out infinite; }
@keyframes offer-glow {
  0%, 100% { filter: drop-shadow(0 0 0 rgba(24, 160, 88, 0)); }
  50% { filter: drop-shadow(0 5px 13px rgba(24, 160, 88, .55)); }
}
.conv-pill { transition: opacity .25s ease; }

/* ---- 待办 / 快捷开始 ---- */
.todo-row { display: flex; align-items: center; gap: 11px; padding: 10px 0; border-bottom: 1px solid #f0f2f7; font-size: 13px; }
.todo-row:last-child { border-bottom: none; }
.todo-chip { flex-shrink: 0; width: 30px; height: 30px; border-radius: 8px; background: #fdeceb; color: #d93025; display: grid; place-items: center; }
.todo-main { font-weight: 500; color: #1f2733; }
.todo-info { flex: 1; min-width: 0; }
.start-label { font-size: 12.5px; color: #8a93a3; margin: 4px 0 12px; }
.start-row { display: flex; flex-direction: column; gap: 9px; }
.start-item { display: flex; align-items: center; gap: 12px; border: 1px solid #e8ecf4; border-radius: 10px;
  padding: 11px 14px; cursor: pointer; transition: all .2s ease; }
.start-item:hover { border-color: #c9d6f2; background: #f8faff; transform: translateX(4px); }
.start-item:hover .start-arrow { opacity: 1; transform: translateX(0); }
.start-info { flex: 1; display: flex; flex-direction: column; gap: 1px; }
.start-info b { font-size: 13px; color: #1f2733; }
.start-info span { font-size: 11.5px; color: #98a1b0; }
.start-arrow { color: #2f66f6; font-size: 14px; opacity: 0; transform: translateX(-6px); transition: all .22s ease; }

/* ---- 功能入口 ---- */
.mod-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
.mod-card { position: relative; border: 1px solid #e4e8f0; border-radius: 13px; padding: 17px 10px 15px; text-align: center;
  cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 9px; background: #fff; overflow: hidden;
  opacity: 0; transform: translateY(12px);
  transition: opacity .5s ease, transform .55s cubic-bezier(.16,1,.3,1), border-color .22s ease, box-shadow .28s ease; }
.mod-grid.in .mod-card { opacity: 1; transform: none; }
.mod-card::after { content: ""; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(150deg, color-mix(in srgb, var(--mc) 9%, transparent), transparent 62%);
  opacity: 0; transition: opacity .28s ease; }
.mod-card:hover { border-color: color-mix(in srgb, var(--mc) 45%, #fff); transform: translateY(-4px) !important;
  box-shadow: 0 12px 26px color-mix(in srgb, var(--mc) 26%, transparent); }
.mod-card:hover::after { opacity: 1; }
.mod-card:hover .mod-chip { transform: scale(1.13) rotate(-6deg); box-shadow: 0 8px 18px color-mix(in srgb, var(--mc) 42%, transparent); }
.mod-card:hover .mod-arrow { opacity: 1; transform: scale(1); }
.mod-card::before { content: ""; position: absolute; top: 0; left: 14%; right: 14%; height: 3px; border-radius: 2px;
  background: linear-gradient(90deg, var(--mc1), var(--mc2)); opacity: 0; transform: scaleX(.35); transition: all .3s ease; }
.mod-card:hover::before { opacity: .9; transform: scaleX(1); }
.mod-chip { position: relative; z-index: 1; width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; color: #fff;
  background: linear-gradient(135deg, var(--mc1), var(--mc2));
  box-shadow: 0 5px 13px color-mix(in srgb, var(--mc) 35%, transparent);
  transition: transform .3s cubic-bezier(.34,1.56,.64,1), box-shadow .3s ease; }
.mod-card b { position: relative; z-index: 1; font-size: 13px; color: #1f2733; }
.mod-arrow { position: absolute; right: 10px; top: 10px; width: 20px; height: 20px; border-radius: 50%;
  background: var(--mc); color: #fff; display: grid; place-items: center;
  opacity: 0; transform: scale(.5); transition: all .25s cubic-bezier(.34,1.56,.64,1); }

@media (prefers-reduced-motion: reduce) {
  .hero, .stat-card, .mod-card, .fstage, .conv-pill, .orb-pos, .spark, .ring-fg { transition: none !important; }
  .hero-orb, .spark, .hero-wave, .next-dot, .fstage.offer polygon:first-of-type { animation: none !important; }
}
</style>
