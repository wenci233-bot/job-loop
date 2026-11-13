"""打包入口：PyInstaller 用。与 run.py 的区别是不用字符串导入 app（打包后字符串导入不可靠）。

开发时也可以用它启动：python launcher.py
"""
from __future__ import annotations

import sys
import threading
import time
import webbrowser

import uvicorn

from server.app import app

HOST, PORT = "127.0.0.1", 18555
URL = f"http://{HOST}:{PORT}"


def _open_browser(delay: float = 1.5) -> None:
    time.sleep(delay)
    webbrowser.open(URL)


if __name__ == "__main__":
    if "--no-open" not in sys.argv:
        threading.Thread(target=_open_browser, daemon=True).start()
    print(f"Job Loop 启动中：{URL}（关闭本窗口即退出）")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
