<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api, STATUS_OPTIONS, STATUS_META } from '../api'
const props = defineProps({ modelValue: Boolean, application: Boolean })
const emit = defineEmits(['update:modelValue', 'saved'])
const form = reactive({ company: '', role: '', text: '', salary: '', channel: '', status: 'applied', notes: '' })
const saving = ref(false), error = ref('')
watch(() => props.modelValue, open => { if (open) { Object.assign(form, { company: '', role: '', text: '', salary: '', channel: '', status: 'applied', notes: '' }); error.value = '' } })
async function save() {
  if (saving.value) return
  if (!form.company.trim() || !form.role.trim() || (!props.application && !form.text.trim())) { error.value = props.application ? '请填写公司和岗位名称' : '请填写公司、岗位名称和职位描述'; return }
  saving.value = true; error.value = ''
  try {
    const result = props.application
      ? await api.post('/apply/manual', { company: form.company, role: form.role, channel: form.channel || '手动登记', status: form.status, notes: form.notes })
      : await api.post('/inbox/save', { company: form.company, role: form.role, text: form.text, channel: form.channel || '手动添加', parsed: { salary: form.salary, description: form.text }, status: '待评估' })
    ElMessage({ type: result.duplicate ? 'info' : 'success', message: result.duplicate ? '该记录已存在，未重复添加' : '添加成功' })
    emit('update:modelValue', false); emit('saved')
  } catch(e) { error.value = e.message } finally { saving.value = false }
}
</script>
<template>
  <el-dialog :model-value="modelValue" :title="application ? '添加投递记录' : '添加岗位'" width="min(600px, 94vw)" append-to-body :close-on-click-modal="!saving" :close-on-press-escape="!saving" :show-close="!saving" @update:model-value="emit('update:modelValue', $event)">
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-form label-position="top" :disabled="saving" @submit.prevent="save">
      <el-form-item label="公司名称" required><el-input v-model="form.company" maxlength="120" placeholder="填写公司名称" /></el-form-item>
      <el-form-item label="岗位名称" required><el-input v-model="form.role" maxlength="200" placeholder="填写岗位名称" /></el-form-item>
      <template v-if="!application"><el-form-item label="职位描述 / JD" required><el-input v-model="form.text" type="textarea" :rows="6" maxlength="20000" placeholder="粘贴岗位职责与任职要求" /></el-form-item><el-form-item label="薪资"><el-input v-model="form.salary" maxlength="120" placeholder="例如 20–30k·14薪（可选）" /></el-form-item></template>
      <el-form-item label="来源渠道"><el-input v-model="form.channel" maxlength="120" placeholder="官网、招聘平台、内推等（可选）" /></el-form-item>
      <template v-if="application"><el-form-item label="投递状态"><el-select v-model="form.status" style="width:100%"><el-option v-for="status in STATUS_OPTIONS" :key="status" :value="status" :label="STATUS_META[status].label" /></el-select></el-form-item><el-form-item label="备注"><el-input v-model="form.notes" type="textarea" :rows="3" maxlength="5000" placeholder="记录投递时间、反馈等（可选）" /></el-form-item></template>
    </el-form>
    <template #footer><el-button :disabled="saving" @click="emit('update:modelValue', false)">取消</el-button><el-button type="primary" :loading="saving" @click="save">确认添加</el-button></template>
  </el-dialog>
</template>
