"""提示词模板加载：模板放 prompts/*.md，禁止把提示词硬编码在代码里（AGENTS 硬规则 3）。"""
from __future__ import annotations

from server.config import PROMPT_DIR


def render(name: str, **kwargs) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise RuntimeError(f"提示词模板缺失：prompts/{name}.md")
    text = path.read_text(encoding="utf-8")
    for k, v in kwargs.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text
