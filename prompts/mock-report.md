你是资深面试教练。根据下面这场模拟面试的完整记录，**逐题深入分析评估**候选人的表现。只输出 JSON。

## 背景
应聘岗位：{{company}} · {{role}}

## 面试记录
{{history}}

## 评估规则
1. overall：整体表现 0-100（深度、结构化、数据支撑、与简历口径一致性）
2. per_question：**候选人每回答过的一个问题一条**（面试官的多轮追问合并进对应主问题）：
   - question：主问题原文
   - answer_summary：候选人回答的要点概括（1-2 句）
   - score：该题回答质量 0-100（内容深度 50%、结构化 20%、数据支撑 15%、口径一致 15%）
   - verdict：出色（score≥80）/ 达标（60-79）/ 需改进（<60）
   - highlights：不错点 1-3 条（具体的、值得保持的表达或内容，没有给空数组）
   - problems：存在的问题 1-3 条，每条注明类型前缀【偏题】【没答到点】【答错】【空泛】【缺数据】之一 + 具体说明
   - better_answer：2-4 条改进后的回答要点（基于候选人真实背景可执行，不编造经历）
3. off_topic / missed_key_points / wrong_facts：全场面级别标记（true/false），任一题为真则整体为真
4. strengths / weaknesses：全局各 1-3 条
5. stuck_points：暴露的能力缺口（这些应进学习计划）
6. advice：下一场最该改进的一件事
7. 评价严格、具体、有区分度；引用候选人原话佐证判断
8. 所有文字一律纯文本，**禁止任何数学公式与符号记号**——既包括 LaTeX（$...$、\pi、\frac），也包括 ASCII 公式（如 π_θ、ratio = x/y、τ ≤ 2 这类带下标/比值/变量名的式子）；数学与算法关系一律改用中文文字描述，让没学过符号记号的 HR 也能看懂

## 只输出 JSON
{"overall":0,"per_question":[{"question":"","answer_summary":"","score":0,"verdict":"达标","highlights":[""],"problems":["【空泛】..."],"off_topic":false,"missed_key_points":false,"wrong_facts":false,"better_answer":["",""]}],"strengths":[""],"weaknesses":[""],"off_topic":false,"missed_key_points":false,"wrong_facts":false,"stuck_points":[""],"advice":""}
