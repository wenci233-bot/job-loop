<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo"><span class="mark"><el-icon><Briefcase /></el-icon></span>求职闭环系统</div>
      <el-menu :default-active="active" router background-color="transparent" text-color="#a7b6d6"
               active-text-color="#ffffff" class="side-menu">
        <el-menu-item index="/"><el-icon><HomeFilled /></el-icon><span>首页</span></el-menu-item>
        <div class="nav-group">求职流程</div>
        <el-menu-item index="/profile"><el-icon><User /></el-icon><span>个人档案</span></el-menu-item>
        <el-menu-item index="/inbox"><el-icon><Box /></el-icon><span>岗位收集</span></el-menu-item>
        <el-menu-item index="/jobs"><el-icon><Promotion /></el-icon><span>投递中心</span></el-menu-item>
        <el-menu-item index="/interview"><el-icon><Memo /></el-icon><span>面试准备</span></el-menu-item>
        <el-menu-item index="/debrief"><el-icon><EditPen /></el-icon><span>面试复盘</span></el-menu-item>
        <div class="nav-group">持续改进</div>
        <el-menu-item index="/upskill"><el-icon><Reading /></el-icon><span>技能提升</span></el-menu-item>
        <div class="nav-group">系统</div>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon><span>系统设置</span></el-menu-item>
      </el-menu>
    </aside>
    <div class="main">
      <div class="topbar">
        <span class="title">{{ route.meta.title }}</span>
        <span class="spacer"></span>
      </div>
      <div class="content">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { resumeMatchIfAny, onMatchDone, onMatchError,
         resumePrepIfAny, onPrepDone, onPrepError,
         resumeEvalIfAny, onEvalDone, onEvalError } from './store'

const route = useRoute()
const router = useRouter()
const active = computed(() => route.path)

onMounted(() => {
  // 全局兜底轮询：智能匹配 / 准备包生成在后台跑，完成时右下角通知
  resumeMatchIfAny()
  resumePrepIfAny()
  resumeEvalIfAny()
  onMatchDone(results => {
    ElNotification({
      title: '智能匹配完成',
      message: `共 ${results.length} 条推荐，点击查看结果`,
      type: 'success', position: 'bottom-right', duration: 0,
      onClick: () => router.push('/inbox'),
    })
  })
  onMatchError(err => {
    ElNotification({ title: '智能匹配失败', message: err, type: 'error',
                     position: 'bottom-right', duration: 0 })
  })
  onPrepDone(({ company, role, prep }) => {
    ElNotification({
      title: '面试准备包已生成',
      message: `${company} · ${role}（${prep.questions.length} 题），点击查看`,
      type: 'success', position: 'bottom-right', duration: 0,
      onClick: () => router.push('/interview'),
    })
  })
  onPrepError(err => {
    ElNotification({ title: '准备包生成失败', message: err, type: 'error',
                     position: 'bottom-right', duration: 0 })
  })
  onEvalDone(d => {
    ElNotification({
      title: '批量评估完成',
      message: `已评估 ${d.ok ?? d.done}/${d.total} 个岗位，点击查看报告`,
      type: 'success', position: 'bottom-right', duration: 0,
      onClick: () => router.push('/jobs'),
    })
  })
  onEvalError(err => {
    ElNotification({ title: '批量评估失败', message: err, type: 'error',
                     position: 'bottom-right', duration: 0 })
  })
})
</script>

<style>
.side-menu { border-right: none; }
.side-menu .el-menu-item { margin: 2px 10px; border-radius: 8px; height: 42px; }
.side-menu .el-menu-item:hover { background: rgba(255,255,255,.07); }
.side-menu .el-menu-item.is-active { background: #2f66f6; }
</style>
