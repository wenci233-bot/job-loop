"""AI 网关：OpenAI 兼容接口的最小封装。对 429/5xx/网络错误退避重试（认证类 4xx 不重试）。"""
from __future__ import annotations

from concurrent.futures import CancelledError

def check_cancelled(event):
    if event is not None and event.is_set():
        raise CancelledError()

import json
import re
import time
import urllib.error
import urllib.request

from server.config import read_env

_NO_RETRY_CODES = {401, 403, 404, 413, 422}
_RETRIES = 2          # 首次失败后最多再试 2 次
_BACKOFF = [2, 5]     # 每次重试前的等待秒数

# 常用 LaTeX 命令 → Unicode 符号（模型偶尔无视禁令输出数学公式时的兜底转换）
_LATEX_SYMBOLS = {
    "pi": "π", "theta": "θ", "Theta": "Θ", "Delta": "Δ", "delta": "δ", "alpha": "α",
    "beta": "β", "gamma": "γ", "lambda": "λ", "mu": "μ", "sigma": "σ", "tau": "τ",
    "eta": "η", "rho": "ρ", "omega": "ω", "Omega": "Ω", "phi": "φ", "epsilon": "ε",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠",
    "times": "×", "cdot": "·", "cdots": "…", "ldots": "…", "dots": "…",
    "approx": "≈", "sim": "~", "propto": "∝", "infty": "∞", "pm": "±",
    "to": "→", "rightarrow": "→", "Rightarrow": "⇒", "leftarrow": "←",
    "sum": "Σ", "prod": "Π", "sqrt": "√", "partial": "∂", "nabla": "∇",
}


def plain_math(text) -> str:
    """把 AI 输出里偶发的 LaTeX 数学标记转成纯文本：$...$ 剥壳、\\pi 类命令转 Unicode、上下标括号化。"""
    s = str(text)
    s = re.sub(r"\$\s*([^$]*?)\s*\$", r"\1", s)
    s = s.replace("\\(", "").replace("\\)", "").replace("\\[", "").replace("\\]", "")
    s = re.sub(r"[_^]\{([^{}]*)\}", r"(\1)", s)

    def _sub(m: re.Match) -> str:
        name = m.group(1)
        return _LATEX_SYMBOLS.get(name, _LATEX_SYMBOLS.get(name.lower(), name))

    s = re.sub(r"\\([A-Za-z]+)", _sub, s)
    s = re.sub(r"\\([^A-Za-z\s])", r"\1", s)  # \| \, \; 等符号命令剥掉反斜杠
    return s.replace("{", "").replace("}", "")


def _headers(cfg: dict) -> dict:
    return {
        "Authorization": f"Bearer {cfg['AI_API_KEY']}",
        "Content-Type": "application/json",
    }


def _post_chat(cfg: dict, body: bytes, timeout: int, cancel_event=None) -> str:
    url = cfg["AI_BASE_URL"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers=_headers(cfg), method="POST")
    last_err: Exception | None = None
    for attempt in range(_RETRIES + 1):
        check_cancelled(cancel_event)
        if attempt:
            delay = _BACKOFF[min(attempt - 1, len(_BACKOFF) - 1)]
            if cancel_event is None:
                time.sleep(delay)
            elif cancel_event.wait(delay):
                raise CancelledError()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            check_cancelled(cancel_event)
            return data["choices"][0]["message"]["content"]
        except CancelledError:
            raise
        except urllib.error.HTTPError as e:
            if e.code in _NO_RETRY_CODES:
                raise
            last_err = e
        except Exception as e:  # 超时/连接错误
            last_err = e
    raise last_err if last_err else RuntimeError("AI 调用失败")


def chat(messages: list[dict], timeout: int = 60, cancel_event=None) -> str:
    check_cancelled(cancel_event)
    cfg = read_env()
    if not cfg["AI_API_KEY"]:
        raise RuntimeError("未配置 AI_API_KEY，请先在系统设置里填写")
    body = json.dumps({"model": cfg["AI_MODEL"], "messages": messages}).encode("utf-8")
    try:
        return _post_chat(cfg, body, timeout, cancel_event=cancel_event)
    except CancelledError:
        raise
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"AI 接口返回 HTTP {e.code}（Key 无效或模型不可用）") from e
    except Exception as e:
        raise RuntimeError(f"AI 调用失败（已重试）：{e}") from e


def test_connection() -> dict:
    cfg = read_env()
    if not cfg["AI_API_KEY"]:
        return {"ok": False, "error": "未配置 AI_API_KEY"}
    url = cfg["AI_BASE_URL"].rstrip("/") + "/models"
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers=_headers(cfg), method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return {"ok": True, "latency_ms": int((time.perf_counter() - start) * 1000),
                "model": cfg["AI_MODEL"]}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}（Key 无效或接口路径不对）"}
    except Exception as e:  # 网络/超时等
        return {"ok": False, "error": str(e)}
