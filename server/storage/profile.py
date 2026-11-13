"""个人档案：结构化 JSON（网申式：教育/工作/实习/项目/论文/荣誉为记录数组）。storage 层唯一写入方。"""
from __future__ import annotations

from server.config import PROFILE_DIR, ensure_dirs
from server.storage.files import read_json, write_json

CANDIDATE_FILE = PROFILE_DIR / "candidate.json"
STARS_FILE = PROFILE_DIR / "stars.json"

# 字符串字段默认 ""；列表字段默认 []；带选项的字段给默认选项（空值回落默认，防旧数据失效）
DEFAULT_CANDIDATE = {
    # 基本信息
    "name": "", "gender": "", "birth": "", "identity": "社招", "politics": "",
    "city": "", "phone": "", "email": "", "languages": "",
    "self_evaluation": "", "skills": "",
    # 经历（记录数组）
    "education": [],      # {school, degree, major, start, end, rank_}
    "work": [],           # {company, title, start, end, description}
    "internship": [],     # {company, title, start, end, description}
    "project": [],        # {name, role, start, end, description}
    # 论文与荣誉（记录数组）
    "publications": [],   # {title, level, venue, year, authors}
    "awards": [],         # {name, level, year}
    "certificates": [],   # {name, year}
    # 求职偏好
    "target_cities": "", "target_type": [],
    "employment_bottom_line": "外包/劳务派遣 一票否决",
    "hukou": "无所谓", "salary_expect": "",
    "overtime_tolerance": "不接受大小周和996", "other_vetoes": "",
}


def _normalize(candidate: dict) -> dict:
    out = {}
    for k, dv in DEFAULT_CANDIDATE.items():
        v = candidate.get(k)
        if isinstance(dv, list):
            out[k] = v if isinstance(v, list) else []
        elif isinstance(v, str) and v:
            out[k] = v
        elif isinstance(v, (int, float)):
            out[k] = str(v)
        else:
            out[k] = dv if dv else ""
    # 旧字段迁移：skills_main/skills_extra → skills
    if not out.get("skills"):
        legacy = " / ".join(filter(None, [candidate.get("skills_main", ""), candidate.get("skills_extra", "")]))
        if legacy:
            out["skills"] = legacy
    return out


def load_candidate() -> dict:
    ensure_dirs()
    return _normalize(read_json(CANDIDATE_FILE, {}))


def load_stars() -> list[dict]:
    ensure_dirs()
    return [{"title": str(s.get("title", "")), "content": str(s.get("content", "")),
             "source": str(s.get("source", "手填"))} for s in read_json(STARS_FILE, [])]


def save(candidate: dict, stars: list[dict]) -> None:
    ensure_dirs()
    write_json(CANDIDATE_FILE, _normalize(candidate))
    write_json(STARS_FILE, [{"title": s.get("title", ""), "content": s.get("content", ""),
                             "source": s.get("source", "手填")} for s in stars])
