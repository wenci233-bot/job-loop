async function req(method, url, body) {
  const resp = await fetch('/api' + url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) { const error = new Error(data.detail || 'HTTP ' + resp.status); error.status = resp.status; throw error }
  return data
}

export const api = {
  get: (u) => req('GET', u),
  post: (u, b) => req('POST', u, b),
  put: (u, b) => req('PUT', u, b),
}

export async function uploadFile(url, file) {
  const fd = new FormData()
  fd.append('file', file)
  const resp = await fetch('/api' + url, { method: 'POST', body: fd })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) { const error = new Error(data.detail || 'HTTP ' + resp.status); error.status = resp.status; throw error }
  return data
}

export const STATUS_META = {
  drafted: { label: '草稿', type: 'info' },
  applied: { label: '已投递', type: 'primary' },
  interview_1: { label: '一面', type: 'warning' },
  interview_2: { label: '二面', type: 'warning' },
  interview_3: { label: '三面', type: 'warning' },
  interview_4: { label: '四面', type: 'warning' },
  interview_hr: { label: 'HR 面', type: 'warning' },
  offer: { label: 'Offer', type: 'success' },
  offer_declined: { label: '婉拒 Offer', type: 'info' },
  rejected: { label: '未通过', type: 'danger' },
  withdrawn: { label: '已撤回', type: 'info' },
  // 旧数据兼容展示
  interviewing: { label: '面试中', type: 'warning' },
  no_response: { label: '无回音', type: 'danger' },
}
export const STATUS_OPTIONS = ['drafted', 'applied', 'interview_1', 'interview_2', 'interview_3',
                               'interview_4', 'interview_hr', 'offer', 'offer_declined', 'rejected', 'withdrawn']
