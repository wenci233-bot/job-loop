"""公司真实 logo：常见雇主域名映射 → favicon 服务下载 → 本地缓存。
未映射/下载失败返回 None，前端回退字母牌。负缓存避免重复慢查询。"""
from __future__ import annotations

import re
import time
import urllib.request
from pathlib import Path

from server.config import DATA_DIR

CACHE = DATA_DIR / "logos"

KNOWN_DOMAINS = {
    "腾讯": "qq.com", "字节跳动": "bytedance.com", "字节": "bytedance.com",
    "阿里巴巴": "alibaba.com", "阿里": "alibaba.com", "淘天": "taobao.com",
    "华为": "huawei.com", "荣耀": "honor.com", "小米": "mi.com", "红米": "mi.com",
    "vivo": "vivo.com", "oppo": "oppo.com", "一加": "oneplus.com", "真我": "realme.com",
    "美团": "meituan.com", "网易": "163.com", "百度": "baidu.com", "京东": "jd.com",
    "拼多多": "pinduoduo.com", "快手": "kuaishou.com", "小红书": "xiaohongshu.com",
    "哔哩哔哩": "bilibili.com", "B站": "bilibili.com", "滴滴": "didiglobal.com",
    "微软": "microsoft.com", "谷歌": "google.com", "亚马逊": "amazon.com", "苹果": "apple.com",
    "shein": "shein.com", "希音": "shein.com", "temu": "temu.com",
    "比亚迪": "byd.com", "宁德时代": "catl.com", "大疆": "dji.com",
    "理想": "lixiang.com", "蔚来": "nio.com", "小鹏": "xiaopeng.com", "吉利": "geely.com",
    "奇瑞": "chery.com", "长城汽车": "gwm.com.cn", "广汽": "gac.com.cn", "上汽": "saicmotor.com",
    "中国电信": "chinatelecom.com.cn", "电信": "chinatelecom.com.cn",
    "中国移动": "chinamobile.com", "移动": "chinamobile.com",
    "中国联通": "chinaunicom.cn", "联通": "chinaunicom.cn",
    "工商银行": "icbc.com.cn", "建设银行": "ccb.com", "招商银行": "cmbchina.com",
    "中国银行": "bankofchina.com", "农业银行": "abchina.com", "交通银行": "bankcomm.com",
    "中兴": "zte.com.cn", "海康威视": "hikvision.com", "科大讯飞": "iflytek.com",
    "商汤": "sensetime.com", "云从": "cloudwalk.com", "云天励飞": "intellifusion.com",
    "寒武纪": "cambricon.com", "地平线": "horizon.cc", "文远知行": "weride.ai",
    "网易有道": "youdao.com", "携程": "ctrip.com", "去哪儿": "qunar.com",
    "蜻蜓": "ximalaya.com", "喜马拉雅": "ximalaya.com", "知乎": "zhihu.com",
    "贝壳": "ke.com", "联想": "lenovo.com", "浪潮": "inspur.com",
    "中国电科": "cetc.com.cn", "航天科技": "spacechina.com", "中航工业": "aviationindustry.com.cn",
}

_MISS_TTL = 7 * 24 * 3600

# AI 厂商 → 官网域名（favicon 即厂商 logo）
VENDOR_DOMAINS = {
    "OpenAI": "openai.com",
    "Anthropic": "anthropic.com",
    "Google": "google.com",
    "DeepSeek": "deepseek.com",
    "xAI": "x.ai",
    "阿里云百炼": "alibaba.com",
    "智谱AI": "zhipuai.cn",
    "月之暗面": "moonshot.cn",
    "MiniMax": "minimaxi.com",
    "字节火山": "volcengine.com",
}


def _safe_name(company: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]", "", company)[:24] or "unknown"


def _resolve_domain(company: str) -> str | None:
    name = re.sub(r"[（(].*?[)）]|\[.*?\]|股份有限公司|有限公司|科技|集团", "", company).strip()
    for key, domain in KNOWN_DOMAINS.items():
        if key == name or key == company:
            return domain
    for key, domain in KNOWN_DOMAINS.items():
        if key in company or company in key:
            return domain
    return None


def _openers():
    """先走系统代理，再试直连（本机环境两者都可能通）。"""
    yield urllib.request.build_opener()
    yield urllib.request.build_opener(urllib.request.ProxyHandler({}))


# 手工核验过的公司 Logo 直链：自动抓取（duckduckgo/google favicon）对部分公司会拿到
# 错误或低清的站点图标，这里按公司关键词直接指定官方图片地址。
# 每项为 (图片URL, Referer)，Referer 可为空串。新增一项前先用浏览器确认图片内容。
LOGO_OVERRIDES = {
    "阿里巴巴": ("https://static.alibabagroup.com/static/c33a2ec2-de56-429a-b279-2d6211a83108.png",
                 "https://www.alibabagroup.com/"),
}


def get_logo(company: str) -> Path | None:
    company = (company or "").strip()
    if not company:
        return None
    ensure_cache()
    safe = _safe_name(company)
    path = CACHE / f"{safe}.png"
    if path.exists():
        return path
    # 官方直链覆盖：命中关键词就直接下载手工核验过的图，不 go 自动抓取
    for key, (url, referer) in LOGO_OVERRIDES.items():
        if key not in company:
            continue
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
        if referer:
            headers["Referer"] = referer
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            if len(data) > 600:
                path.write_bytes(data)
                return path
        except Exception:
            continue
    miss = CACHE / f"{safe}.miss"
    if miss.exists() and time.time() - miss.stat().st_mtime < _MISS_TTL:
        return None
    domain = _resolve_domain(company)
    if not domain:
        miss.write_text("no-domain")
        return None
    # icons.duckduckgo.com 境内可直连，排前面；google s2 需要代理，走系统代理时可用
    urls = [f"https://icons.duckduckgo.com/ip3/{domain}.ico",
            f"https://www.google.com/s2/favicons?domain={domain}&sz=128"]
    for url in urls:
        for opener in _openers():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with opener.open(req, timeout=7) as resp:
                    data = resp.read()
                if len(data) > 600:
                    path.write_bytes(data)
                    return path
            except Exception:
                continue
    miss.write_text("fetch-failed")
    return None


def get_vendor_logo(vendor: str) -> Path | None:
    """厂商 logo（官网 favicon），与公司 logo 同一缓存管线。"""
    domain = VENDOR_DOMAINS.get((vendor or "").strip())
    if not domain:
        return None
    ensure_cache()
    safe = "vendor_" + re.sub(r"[^\w一-鿿]", "", vendor)[:20]
    path = CACHE / f"{safe}.png"
    if path.exists():
        return path
    # 与公司 logo 相同的顺序：境内可直连的 duckduckgo 在前
    urls = [f"https://icons.duckduckgo.com/ip3/{domain}.ico",
            f"https://www.google.com/s2/favicons?domain={domain}&sz=128"]
    for url in urls:
        for opener in _openers():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with opener.open(req, timeout=7) as resp:
                    data = resp.read()
                if len(data) > 600:
                    path.write_bytes(data)
                    return path
            except Exception:
                continue
    return None


def ensure_cache() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
