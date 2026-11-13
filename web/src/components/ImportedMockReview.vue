<script setup>
defineProps({ entry: { type: Object, required: true } })
const flags = { off_topic: '偏题', missed_key_points: '没答到点', wrong_facts: '答错' }
</script>
<template>
  <section class="imported-review">
    <el-tag type="info" size="small">来源：模拟面试</el-tag>
    <p class="muted">原场次时间：{{ (entry.source_date || entry.date || '').replace('T', ' ') }}</p>
    <details class="conversation"><summary>查看完整原始对话</summary><div v-for="(turn, i) in entry.mock_history" :key="i"><b>{{ turn.role === 'candidate' ? '我的回答' : '面试官' }}：</b>{{ turn.text }}</div></details>
    <article v-for="(q, i) in entry.mock_report?.per_question || []" :key="i" class="question">
      <div class="question-title"><el-tag :type="q.verdict === '出色' ? 'success' : q.verdict === '达标' ? 'primary' : 'danger'">{{ q.score ?? '—' }} 分 · {{ q.verdict }}</el-tag><b>{{ q.question }}</b></div>
      <p v-if="q.answer_summary" class="answer"><b>回答摘要：</b>{{ q.answer_summary }}</p>
      <template v-if="q.highlights?.length"><h4>不错点</h4><ul><li v-for="(item, j) in q.highlights" :key="j">{{ item }}</li></ul></template>
      <template v-if="q.problems?.length"><h4>问题</h4><ul><li v-for="(item, j) in q.problems" :key="j">{{ item }}</li></ul></template>
      <div class="flags"><template v-for="(label, key) in flags" :key="key"><el-tag v-if="q[key]" size="small" type="warning">{{ label }}</el-tag></template></div>
      <template v-if="q.better_answer?.length"><h4>更好的答法</h4><ol><li v-for="(item, j) in q.better_answer" :key="j">{{ item }}</li></ol></template>
    </article>
    <div class="flags"><template v-for="(label, key) in flags" :key="key"><el-tag v-if="entry.mock_report?.[key]" size="small" type="warning">全场：{{ label }}</el-tag></template></div>
    <template v-for="(label, field) in { strengths: '全局亮点', weaknesses: '共性问题', stuck_points: '卡壳点' }" :key="field"><template v-if="entry.mock_report?.[field]?.length"><h4>{{ label }}</h4><ul><li v-for="(item, i) in entry.mock_report[field]" :key="i">{{ item }}</li></ul></template></template>
  </section>
</template>
<style scoped>
.imported-review{line-height:1.8;font-size:13px}.question{border:1px solid #e4e8f0;border-radius:10px;padding:14px;margin:12px 0}.question-title{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.answer{background:#f2f6ff;border-left:3px solid #2f66f6;padding:10px}.conversation{padding:10px;background:#f8faff;border-radius:8px;margin:10px 0}.conversation summary{cursor:pointer;color:#2f66f6}.conversation div{white-space:pre-wrap;padding:8px 0;overflow-wrap:anywhere}.flags{display:flex;gap:8px;flex-wrap:wrap}h4{margin:12px 0 4px}ul,ol{margin:4px 0;padding-left:24px}
</style>
