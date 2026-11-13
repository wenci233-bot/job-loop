"""主流雇主官方招聘页映射：为「去申请」提供官网跳转地址。仅收录可信域名，未知返回 None。"""

CAREERS = {
    "腾讯": "https://careers.tencent.com",
    "字节跳动": "https://jobs.bytedance.com",
    "阿里巴巴": "https://talent.alibaba.com",
    "蚂蚁集团": "https://talent.antgroup.com",
    "华为": "https://career.huawei.com",
    "荣耀": "https://career.honor.com",
    "小米": "https://hr.xiaomi.com",
    "vivo": "https://hr.vivo.com",
    "oppo": "https://careers.oppo.com",
    "一加": "https://careers.oneplus.com",
    "网易": "https://campus.163.com",
    "百度": "https://talent.baidu.com",
    "美团": "https://zhaopin.meituan.com",
    "京东": "https://campus.jd.com",
    "快手": "https://zhaopin.kuaishou.cn",
    "拼多多": "https://careers.pinduoduo.com",
    "小红书": "https://job.xiaohongshu.com",
    "哔哩哔哩": "https://careers.bilibili.com",
    "滴滴": "https://careers.didiglobal.com",
    "微软": "https://careers.microsoft.com",
    "谷歌": "https://www.google.com/about/careers",
    "亚马逊": "https://www.amazon.jobs",
    "苹果": "https://jobs.apple.com",
    "shein": "https://careers.shein.com",
    "希音": "https://careers.shein.com",
    "比亚迪": "https://job.byd.com",
    "宁德时代": "https://career.catl.com",
    "大疆": "https://we.dji.com",
    "理想": "https://job.lixiang.com",
    "蔚来": "https://nio.jobs.feishu.cn",
    "小鹏": "https://job.xiaopeng.com",
    "吉利": "https://zhaopin.geely.com",
    "中国电信": "https://campus.chinatelecom.cn",
    "中国移动": "https://job.10086.cn",
    "中国联通": "https://chinaunicom.cn",
    "工商银行": "https://job.icbc.com.cn",
    "建设银行": "https://job.ccb.com",
    "招商银行": "https://career.cmbchina.com",
    "中国银行": "https://campus.bankofchina.com",
    "农业银行": "https://job.abchina.com",
    "中兴": "https://job.zte.com.cn",
    "海康威视": "https://campus.hikvision.com",
    "科大讯飞": "https://campus.iflytek.com",
    "商汤": "https://www.sensetime.com/cn/careers",
    "云天励飞": "https://www.intellifusion.com",
    "寒武纪": "https://www.cambricon.com",
    "地平线": "https://horizon.cc",
    "联想": "https://talent.lenovo.com",
    "浪潮": "https://hr.inspur.com",
    "携程": "https://campus.ctrip.com",
    "知乎": "https://www.zhihu.com/careers",
}


def careers_url(company: str) -> str | None:
    """公司名 → 官方招聘页；精确与包含双向匹配，未命中返回 None。"""
    name = (company or "").strip()
    if not name:
        return None
    for key, url in CAREERS.items():
        if key == name:
            return url
    for key, url in CAREERS.items():
        if key in name or name in key:
            return url
    return None
