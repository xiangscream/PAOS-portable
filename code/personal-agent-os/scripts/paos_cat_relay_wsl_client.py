"""WSL 侧一次性 HTTP 子进程：把 PAOS Windows relay 的 HTTP 信封转发到
WSL 内 127.0.0.1:8870 的**唯一** CAT 服务，并把原样应答返回给 Windows 端。

stdin：一个 JSON 对象 {"method","path","headers","body_b64"}；stdout：一个
JSON 对象 {"status","headers","body_b64"}（或 {"status":502,"error":…}）。
不写任何 CAT 存储、无状态、零第三方依赖。超时默认 180 秒（可由调用方
覆盖），慢的原生提醒在返回与其预期一致地延迟呈现，不会被提前切断。"""
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.request
from urllib.request import Request as UrllibRequest

# 固定 loopback-only转发：不允许 caller 绕开默认 host；不加代理不跟重定向。
_LOCAL_ONLY_CLIENT: urllib.request.OpenerDirector | None = None
NO_PROXY = urllib.request.ProxyHandler({})
NO_REDIRECT = type(
    "_NoRedirect",
    (urllib.request.HTTPRedirectHandler,),
    {"redirect_request": lambda self, req, fp, code, msg: None},
)


def _local_client() -> urllib.request.OpenerDirector:
    global _LOCAL_ONLY_CLIENT
    if _LOCAL_ONLY_CLIENT is None:
        _LOCAL_ONLY_CLIENT = urllib.request.build_opener(NO_PROXY, NO_REDIRECT())
    return _LOCAL_ONLY_CLIENT




_STRIP_FORWARDED_HEADERS = {
    "proxy-authorization", "forwarded", "via",
    "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-forwarded-port",
    "transfer-encoding", "content-encoding" ,
}


def _clean_headers(value: object) -> dict[str, str]:
    clean: dict[str, str] = {}
    if isinstance(value, dict):
        for key, content in value.items():
            text_key = str(key or "").strip()
            text_value = str(content or "")
            lowered = text_key.lower()
            if not text_key or lowered in {"host", "connection"} | _STRIP_FORWARDED_HEADERS:
                continue
            clean[text_key] = text_value
    return clean


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    port = int(args[0]) if args else 8870
    timeout = float(args[1]) if len(args) > 1 else 180.0
    envelope = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    method = str(envelope.get("method") or "GET").upper()
    path = str(envelope.get("path") or "/")
    body = base64.b64decode(envelope.get("body_b64") or "")
    headers = _clean_headers(envelope.get("headers"))
    if not path.startswith("/"):
        delivered = {
            "status": 502,
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
            "body_b64": base64.b64encode(
                f"CAT relay child rejected non-relative path {path!r}: "
                "固定 loopback only（不跟绝对 URL，防止把同一调用转发到外域）。\n"
            ).decode("ascii"),
        }
        sys.stdout.buffer.write(json.dumps(delivered).encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    target = f"http://127.0.0.1:{port}{path}"
    request = UrllibRequest(target, data=body if body else None, method=method)
    for key, value in headers.items():
        request.add_header(key, value)
    try:
        with _local_client().open(request, timeout=timeout) as response:
            status = int(response.status)
            outer = response.read()
            response_headers = {key: response.headers.get(key, "")
                                for key in response.headers.keys()
                                if key.lower() not in {"connection", "transfer-encoding"}}
    except urllib.error.HTTPError as error:
        status = int(error.code)
        outer = error.read()
        response_headers = {key: error.headers.get(key, "")
                            for key in error.headers.keys()
                            if key.lower() not in {"connection", "transfer-encoding"}}
    # timeout/socket errors surface through OSError/URLError in urllib;
    # a bare socket.timeout import is unnecessary (already OSError subclass).
    except (OSError, urllib.error.URLError) as problem:
        response = {
            "status": 502,
            "headers": {},
            "body_b64": base64.b64encode(
                f"CAT service unreachable inside WSL at 127.0.0.1:{port}: {problem}\n".encode("utf-8")
            ).decode("ascii"),
        }
        sys.stdout.buffer.write(json.dumps(response).encode("utf-8"))
        sys.stdout.buffer.flush()
        return 0
    delivered = {
        "status": status,
        "headers": response_headers,
        "body_b64": base64.b64encode(outer).decode("ascii"),
    }
    sys.stdout.buffer.write(json.dumps(delivered).encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
