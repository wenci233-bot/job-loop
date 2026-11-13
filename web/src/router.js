import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'

const routes = [
  { path: '/', component: Dashboard, meta: { title: '首页' } },
  { path: '/profile', component: () => import('./views/Profile.vue'), meta: { title: '个人档案' } },
  { path: '/inbox', component: () => import('./views/Inbox.vue'), meta: { title: '岗位收集' } },
  { path: '/jobs', component: () => import('./views/Jobs.vue'), meta: { title: '投递中心' } },
  { path: '/interview', component: () => import('./views/Interview.vue'), meta: { title: '面试准备' } },
  { path: '/debrief', component: () => import('./views/Debrief.vue'), meta: { title: '面试复盘' } },
  { path: '/upskill', component: () => import('./views/Upskill.vue'), meta: { title: '技能提升' } },
  { path: '/settings', component: () => import('./views/Settings.vue'), meta: { title: '系统设置' } },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
