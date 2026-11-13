<template>
  <div class="jd">
    <div class="jd-head" v-if="!plain">
      <div class="jd-title">{{ title }}</div>
      <div class="jd-meta">
        <span v-for="m in metaItems" :key="m.label">
          <span class="jd-meta-label">{{ m.label }}</span>{{ m.value }}
        </span>
        <el-tag v-if="salary" size="small" type="warning" effect="plain">{{ salary }}</el-tag>
      </div>
    </div>

    <template v-if="description">
      <div class="jd-sec-title">职位描述</div>
      <p v-for="(para, i) in descParas" :key="i" class="jd-para">{{ para }}</p>
    </template>

    <template v-if="requirements.length">
      <div class="jd-sec-title">职位要求</div>
      <ol class="jd-list">
        <li v-for="(r, i) in requirements" :key="i">{{ r }}</li>
      </ol>
    </template>

    <template v-if="bonus.length">
      <div class="jd-sec-title">加分项</div>
      <ol class="jd-list">
        <li v-for="(b, i) in bonus" :key="i">{{ b }}</li>
      </ol>
    </template>

    <template v-if="rawText && !description">
      <div class="jd-sec-title">岗位描述原文</div>
      <pre class="jd-raw">{{ rawText }}</pre>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  company: String,
  meta: { type: Array, default: () => [] },   // [{label, value}]
  salary: String,
  description: String,
  requirements: { type: Array, default: () => [] },
  bonus: { type: Array, default: () => [] },
  rawText: String,
  plain: Boolean,   // 紧凑模式：隐藏标题头（外层卡片已展示公司/岗位/薪资时用）
})

const descParas = computed(() =>
  (props.description || '').split(/\n+/).map(s => s.trim()).filter(Boolean))
const metaItems = computed(() => props.meta.filter(m => m.value))
</script>

<style scoped>
.jd { max-width: 860px; }
.jd-head { margin-bottom: 4px; }
.jd-title { font-size: 16px; font-weight: 600; color: var(--e-text, #1f2733); }
.jd-meta { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 6px; font-size: 12.5px; color: #5b6575; align-items: center; }
.jd-meta-label { color: #98a1b0; margin-right: 2px; }
.jd-sec-title { font-size: 14px; font-weight: 600; color: #1f2733; border-left: 3px solid #2f66f6; padding-left: 8px; margin: 16px 0 8px; }
.jd-para { font-size: 13px; color: #3d4757; line-height: 1.85; margin: 0 0 8px; white-space: pre-wrap; }
.jd-list { margin: 0; padding-left: 20px; }
.jd-list li { font-size: 13px; color: #3d4757; line-height: 1.85; margin-bottom: 4px; }
.jd-raw { white-space: pre-wrap; word-break: break-word; font-family: inherit; font-size: 13px; color: #3d4757; line-height: 1.8; margin: 0; }
</style>
