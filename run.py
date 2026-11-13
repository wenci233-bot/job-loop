"""启动：python run.py [--port 18556] [--no-open]。"""
from __future__ import annotations

import argparse
from pathlib import Path
import socket
import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"


def _open_browser(url: str, delay: float = 1.2) -> None:
    time.sleep(delay)
    webbrowser.open(url)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="启动当前目录的求职闭环系统")
    parser.add_argument("--port", type=int, default=18556, help="监听端口，默认 18556；多副本请指定不同端口")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("端口必须在 1 到 65535 之间")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((HOST, args.port))
            probe.listen(1)
    except OSError as exc:
        if exc.errno not in (98, 48, 10048):
            raise
        alternate = args.port + 1 if args.port < 65535 else 18556
        print(f"端口 {args.port} 已被占用，可能已有其他项目副本正在运行。")
        print(f'如需启动当前副本，请使用其他端口：\npython "{Path(__file__).resolve()}" --port {alternate}')
        return 1
    url = f"http://{HOST}:{args.port}"
    if not args.no_open:
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    print(f"求职闭环系统启动中：{url}（Ctrl+C 退出）")
    uvicorn.run("server.app:app", host=HOST, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
