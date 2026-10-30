"""Windows 侧 loopback HTTP relay → 唯一 WSL CAT 服务（零第三方依赖）。

目的：Windows Human 浏览器与 Windows `paos cat`（默认 URL `127.0.0.1:8870`）
能正常使用同一 CAT 单 Store/单服务；不改 WSL 服务 binding、不开放非
loopback、不改防火墙/全局 WSL 网络；同 Cat 数据源；无状态。

- 本进程只在 Windows `127.0.0.1:<listen-port>` 监听（loopback-only）。
- 每个 HTTP 请求起一个一次性子进程（默认 `wsl.exe -u <user> -- python3 -u
  <scripts>/paos_cat_relay_wsl_client.py <service-port>`），把 HTTP 请求封
  装成 JSON 信封传入子进程，由子进程在 WSL 内访问 `127.0.0.1:<service-port>`
  并原样返回 status/headers/body，本端把应答回写客户端；不写任何数据。
- upstream 不可达 → 子进程返回 {"status":502,"error":…}，本端把 502 + 明确
  文本回给 CLI/浏览器（真实失败表达，不吞错）。
- 手动启停；不自动注册计划任务/开机自启；Ctrl+C 退出。
- `--child-command-file`：测试/维护注入（JSON 数组子进程 argv），生产默认
  构造不使用。
"""
from __future__ import annotations

import base64
import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


def _relay_child_timeout() -> float:
    """一次 child 的明确超时；环境可覆盖，不依赖 wrapper/CLI timeout。"""
    raw = os.environ.get("PAOS_CAT_RELAY_CHILD_TIMEOUT", "30")
    return float(raw)


class RelayConfig:
    def __init__(
        self,
        service_port: int,
        wsl_user: str,
        child_command_file: str = "",
    ) -> None:
        self.service_port = service_port
        self.wsl_user = wsl_user
        self.child_command_file = child_command_file


def to_posix_path_windows_aware(text_path: str) -> str:
    """Windows 绝对脚本路径 → WSL view。无 os.name 分支，无论宿主是 Windows
    还是其他，都把 `C:\\path`/`C:/path` 一律映射成 `/mnt/<drive>/path`。
    POSIX 形式的路径原样返回（仅本 Source 内部用，不是通用 locator）。"""
    text = text_path.strip()
    drive = text[0:1].lower()
    rest = text[2:]
    if drive.isalpha() and (text[1:2] == ":"):
        pure = rest.replace("\\", "/").lstrip("/")
        return f"/mnt/{drive}/{pure}"
    return text.replace("\\", "/")


def _bridge_posix_from_file(path: Path) -> str:
    """Windows 脚本绝对路径 → WSL 可见路径（独立 relay 入口专用，不借
    locator 合同避免 host-os 分支）。真实中文/空格路径走默认 child builder。"""
    return to_posix_path_windows_aware(str(path.resolve()))


def default_child_builder(config: RelayConfig):
    """生产默认：每个请求一个 `wsl.exe` 子进程，转发唯一的 CAT 服务"""

    script = Path(__file__).resolve().parent / "paos_cat_relay_wsl_client.py"
    bridge_posix = _bridge_posix_from_file(script)
    wsl_exe = r"C:\Windows\System32\wsl.exe"

    def build() -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            [
                wsl_exe, "-u", config.wsl_user, "--",
                "/usr/bin/python3", "-u", bridge_posix,
                str(config.service_port),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    return build


def injected_child_builder(argv: list[str]):
    def build() -> subprocess.Popen[bytes]:
        return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    return build


class _Handler(BaseHTTPRequestHandler):
    server_version = "PaosCatRelay/1.0"

    def _forward(self) -> None:
        config: RelayConfig = self.server.relay_config  # type: ignore[attr-defined]
        child_builder: Callable[[], subprocess.Popen[bytes]] = self.server.child_builder  # type: ignore[attr-defined]
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        envelope = {
            "method": self.command,
            "path": self.path,
            "headers": {key: value for key, value in self.headers.items()},
            "body_b64": base64.b64encode(body).decode("ascii"),
        }
        payload = json.dumps(envelope).encode("utf-8")
        def _plain_502(text: str) -> None:
            data = (text + "\n").encode("utf-8")
            self.send_response(502, "Bad Gateway")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        try:
            child = child_builder()
        except OSError as problem:
            _plain_502(f"CAT relay child start failed: {problem}")
            return
        try:
            out, unused_err = child.communicate(payload, timeout=_relay_child_timeout())
        except subprocess.TimeoutExpired:
            # 单个已知 child 超时即回收，用明确 502；不积累管道，不吞错。
            used_timeout = _relay_child_timeout()
            try:
                child.kill()
                child.communicate(timeout=10)
            except OSError:
                pass
            _plain_502(
                f"CAT relay child did not respond within {used_timeout:.0f}s"
            )
            return
        finally:
            if child.poll() is None:
                try:
                    child.terminate()
                except OSError:
                    pass
        try:
            reply = json.loads(out.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            reply = {"status": 502, "error": "relay child produced no reusable reply",
                     "body_b64": ""}
        status = int(reply.get("status") or 502)
        response_body = base64.b64decode(reply.get("body_b64") or b"")
        if status == 502 and reply.get("error"):
            text = f"CAT service unreachable via relay: {reply.get('error')}"
            response_body = text.encode("utf-8")
        self.send_response(status)
        for key, value in (reply.get("headers") or {}).items():
            lowered = str(key or "").lower()
            if lowered in {"connection", "transfer-encoding", "content-length", "content-encoding"}:
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _forward

    def log_message(self, format: str, *args: Any) -> None:
        # 一次性请求日志默认静默，不刷标准输出；错误本身仍然如实返回。
        return


def serve(
    listen_host: str,
    listen_port: int,
    relay_config: RelayConfig,
    child_builder: Callable[[], subprocess.Popen[bytes]],
) -> dict[str, Any]:
    """构造一个 relay server（**不自动 serve_forever**）。

    标准使用：main 在调用线程直接 `server.serve_forever(...)`；测试需要
    线程时用 `start_serve_thread(unit)` 单独沿同一构造器启动。唯一 serve
    loop；shutdown_relay 按 `shutdown → server_close → join` 正常收尾。"""
    server = ThreadingHTTPServer((listen_host, listen_port), _Handler)
    server.relay_config = relay_config  # type: ignore[attr-defined]
    server.child_builder = child_builder  # type: ignore[attr-defined]
    return {
        "server": server,
        "thread": None,
        "address": server.server_address,
    }


def start_serve_thread(unit: dict[str, Any]) -> threading.Thread:
    """唯一的 serve loop 线程（tests 用，main 直接 serve_forever 不用）。"""
    thread = threading.Thread(
        target=unit["server"].serve_forever,
        kwargs={"poll_interval": 0.5},
        daemon=True,
    )
    thread.start()
    unit["thread"] = thread
    return thread


def shutdown_relay(unit: dict[str, Any]) -> None:
    """正常顺序收尾：shutdown → server_close → join（仅当同一线程在测试里
    `start_serve_thread` 起过；main 的同线程 serve_forever 可以直接
    KeyboardInterrupt，join 不必等）。不吞异常。"""
    server: ThreadingHTTPServer = unit["server"]
    server_thread = unit.get("thread")
    server.shutdown()
    clean_up(server, server_thread)


def clean_up(server: ThreadingHTTPServer,
             server_thread: threading.Thread | None) -> None:
    server.server_close()
    if server_thread is not None and server_thread.is_alive():
        server_thread.join(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-port", type=int, default=8870)
    parser.add_argument("--service-port", type=int, default=8870,
                        help="WSL 内 CAT 服务的 loopback 端口")
    parser.add_argument("--wsl-user", default="remo")
    parser.add_argument("--child-command-file", default="",
                        help="测试/维护注入：JSON 数组子进程 argv")
    args = parser.parse_args(argv)

    config = RelayConfig(args.service_port, args.wsl_user, args.child_command_file)
    if config.child_command_file:
        runtime_args = json.loads(Path(config.child_command_file).read_text(encoding="utf-8"))
        builder = injected_child_builder(runtime_args)
    else:
        builder = default_child_builder(config)
    unit = serve("127.0.0.1", args.listen_port, config, builder)
    print(f"[OK] CAT Windows relay on 127.0.0.1:{args.listen_port} -> "
          f"WSL 127.0.0.1:{args.service_port} (Ctrl+C to stop)", flush=True)
    # 单一线程持续 serve_forever：**无 TTL/定时器**，在显式 STOP / Ctrl+C 前一直
    # 存活并响应正常请求。显式停止走 shutdown_relay(unit) 正常顺序关停。
    server = unit["server"]
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_relay(unit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
