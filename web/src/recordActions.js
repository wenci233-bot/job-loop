import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from './api'
export function useRecordDeletion(refresh) {
  const deleting = ref(false)
  async function remove(records, application = false) {
    if (deleting.value || !records.length) return
    const ids = [...new Set(records.map(row => String(row.id)))]
    deleting.value = true
    try {
      const description = application ? '仅删除投递记录，保留岗位、准备包和面试资料；关联岗位可重新创建申请。' : '将同步删除收集记录、候选岗位及其评分。已有投递记录和面试资料会保留。'
      await ElMessageBox.confirm(`确定删除${ids.length === 1 ? '“' + records[0].company + ' · ' + records[0].role + '”' : '选中的 ' + ids.length + ' 条记录'}？${description}`, application ? '删除投递记录' : '删除岗位', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
      const result = await api.post(application ? '/apply/delete' : '/inbox/delete', { ids, confirmed: true })
      ElMessage.success(`已删除 ${result.deleted} 条记录`)
      await refresh()
    } catch(e) { if (e !== 'cancel' && e !== 'close') ElMessage.error(e.message) }
    finally { deleting.value = false }
  }
  return { deleting, remove }
}
