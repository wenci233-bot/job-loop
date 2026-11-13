"""简历导入：PDF/Word 文本提取 + AI 双路并行结构化解析（加速：总耗时≈较慢一路）。"""
from __future__ import annotations

import html
import json
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf

from server.services import ai, prompts
from server.storage.profile import DEFAULT_CANDIDATE

SUPPORTED = (".pdf", ".docx")

# 允许 AI 回填的字段（与 storage/profile.py 的 DEFAULT_CANDIDATE 对齐）
_LIST_FIELDS = {"education", "work", "internship", "project",
                "publications", "awards", "certificates", "target_type"}
_STR_FIELDS = {"name", "gender", "birth", "identity", "politics", "city", "phone", "email",
               "languages", "self_evaluation", "skills",
               "target_cities", "salary_expect"}


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = pymupdf.open(str(path))
        try:
            return "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
    if suffix == ".docx":
        with zipfile.ZipFile(str(path)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        return html.unescape(re.sub(r"<[^>]+>", "", xml))
    raise ValueError(f"暂不支持 {suffix or '未知'} 格式，请上传 PDF 或 .docx（旧 .doc 请先另存为 .docx）")


def _parse_json_obj(raw: str) -> dict:
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError("AI 返回内容无法解析，请重试")
    return json.loads(raw[start:end + 1])


def _extract_leg(name: str, resume_text: str, timeout: int) -> dict:
    prompt = prompts.render(name, resume=resume_text[:8000])
    return _parse_json_obj(ai.chat([{"role": "user", "content": prompt}], timeout=timeout))


def parse_to_candidate(resume_text: str) -> dict:
    """双路并行提取：A=基本信息+技能（短输出） ‖ B=经历+论文+奖项（长输出）。
    单路失败自动串行重试一次；总耗时≈较慢一路。"""
    with ThreadPoolExecutor(max_workers=2) as ex:
        fa = ex.submit(_extract_leg, "profile-extract-a", resume_text, 90)
        fb = ex.submit(_extract_leg, "profile-extract-b", resume_text, 120)
        results, errors = {}, []
        for key, fut in (("a", fa), ("b", fb)):
            try:
                results[key] = fut.result()
            except Exception as e:
                errors.append((key, e))

    # 失败的一路串行重试一次
    for key, _err in errors:
        leg = "profile-extract-a" if key == "a" else "profile-extract-b"
        timeout = 90 if key == "a" else 120
        try:
            results[key] = _extract_leg(leg, resume_text, timeout)
        except Exception as e:
            raise RuntimeError(f"AI 解析失败（{leg}）：{e}") from e

    data = {**results.get("a", {}), **results.get("b", {})}
    out: dict = {}
    for k, v in data.items():
        if k in _LIST_FIELDS and isinstance(v, list):
            out[k] = [dict(item) if isinstance(item, dict) else item for item in v]
        elif k in _STR_FIELDS and isinstance(v, (str, int, float)):
            out[k] = str(v)
    if not out:
        raise RuntimeError("AI 未解析出任何字段，请重试")
    return out
