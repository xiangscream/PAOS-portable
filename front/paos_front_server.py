"""Optional board for Portable. Existing file readers and CLI own all facts.

Run with ``python portable.py serve`` after initializing this checkout. No Core,
WorkBuddy Python, fixed drive, background consumer or CAT data directory needed.
The visual board originates from S040's WorkBuddy prototype.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

PACKAGE = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE / "code" / "personal-agent-os" / "scripts"))

from paos_attention_service import AttentionServiceProblem, read_home_state
from paos_home import HomeProblem, agent_project_id, project_agent_home, rooter_home
from paos_installation import InstallationProblem, effective_data_root, load_installation_descriptor
from paos_library import LibraryProblem, load_library_roots, scan_skills, scan_workflows
from paos_registry import ProjectRegistry, RegistryProblem
from paos_workstation import posix_windows_drive_locator


class BoardProblem(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


READ_ERRORS = (BoardProblem, HomeProblem, AttentionServiceProblem, RegistryProblem,
               InstallationProblem, LibraryProblem, OSError, UnicodeError)


def error_view(error: Exception) -> dict:
    return {"ok": False, "error": str(error),
            "error_code": getattr(error, "code", type(error).__name__)}


def runtime_path(locator: str) -> Path:
    return Path(posix_windows_drive_locator(locator)).expanduser()


class Board:
    def __init__(self, installation_file: Path, *, cat_url: str = ""):
        self.installation_file = Path(installation_file).resolve()
        self.installation = load_installation_descriptor(self.installation_file)
        if not self.installation["configured"]:
            raise BoardProblem("installation_missing", "先运行 portable.py init，或显式指定已有安装描述。")
        self.registry = ProjectRegistry(self.installation_file)
        self.cat_url = cat_url

    def run_paos(self, args: list[str]) -> dict:
        """One existing CLI invocation. Never infer success from missing output."""
        source = runtime_path(self.installation["source_root"])
        env = dict(os.environ, PAOS_INSTALLATION_FILE=str(self.installation_file),
                   PAOS_LIBRARY_ROOTS_CONFIG=self.installation["library_roots_config"],
                   PYTHONIOENCODING="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(source / "scripts" / "paos.py"),
                 "--installation-file", str(self.installation_file), "--json", "--full-result", *args],
                env=env, capture_output=True, text=True, encoding="utf-8", timeout=90,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error_code": "cli_result_unknown", "retry": False,
                    "error": "调用未及时返回，结果未知；请核原件，不自动重发。"}
        raw = result.stdout.strip() or result.stderr.strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "error_code": "cli_output_invalid", "returncode": result.returncode,
                    "error": raw or "CLI 未返回 JSON。"}
        if not isinstance(value, dict):
            return {"ok": False, "error_code": "cli_output_invalid", "error": "CLI 未返回对象。"}
        if result.returncode:
            value["ok"] = False
        return value

    def projects(self) -> list[dict]:
        directory = effective_data_root(self.installation) / "project-registry" / "projects"
        return [self.registry.read_record(path.stem) for path in sorted(directory.glob("*.json"))]

    def home(self, home_id: str) -> dict:
        if home_id == "rooter-001":
            locator = self.installation.get("rooter_home")
            if not locator:
                raise BoardProblem("rooter_unbound", "当前安装未绑定 Rooter 工位。")
            return rooter_home(home_path=runtime_path(locator))
        return project_agent_home(project=self.registry.read(agent_project_id(home_id)), agent_id=home_id)

    def agent(self, home_id: str) -> dict:
        ref = self.home(home_id)
        state = read_home_state(ref)
        todo = state["todo"]
        if (todo["home_id"], todo["home_kind"], todo["project_id"]) != (
                ref["home_id"], ref["home_kind"], ref["project_id"]):
            raise BoardProblem("todo_identity_mismatch", f"{home_id} 的 TODO 身份与登记不一致。")
        home = Path(ref["home_path"])
        mails = sorted((home / "mailbox").glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        current = todo["current"]
        return {"ok": True, "id": home_id, "home_path": str(home), "project": ref["project_id"],
                **current, "tasks": todo["counts"], "task_items": todo["tasks"],
                "pending_notices": state["notices"]["pending_count"], "mail_total": len(mails),
                "todo": (home / "TODO.md").read_text(encoding="utf-8"),
                "entry": (home / "ENTRY.md").read_text(encoding="utf-8") if (home / "ENTRY.md").is_file() else "",
                "mails": [{"name": p.name, "preview": p.read_text(encoding="utf-8")[:600]} for p in mails[:6]],
                "docs": [p.name for p in home.glob("*.md") if p.name not in {"TODO.md", "ENTRY.md", "CONTACT.md", "STATUS.md"}]}

    def examples(self) -> dict:
        roots = load_library_roots(runtime_path(self.installation["library_roots_config"]))
        result = {"workflow": [], "skill": [], "tool": [], "skipped": [], "registered": roots["registered"]}
        if not roots["registered"]:
            return result
        for kind, scanner in (("workflow", scan_workflows), ("skill", scan_skills)):
            for item in scanner(runtime_path(roots[f"{kind}_root"]), skipped=result["skipped"]):
                if item["status"] == "active":
                    result[kind].append({**item, "kind": kind})
        if roots["tool_catalog"]:
            result["tool"].append({"id": "tool-catalog", "title": "本机工具目录（使用前核实实际入口）",
                                   "kind": "tool", "path": roots["tool_catalog"]})
        return result

    def cat(self, args: list[str]) -> dict:
        if not self.cat_url:
            return {"ok": False, "error_code": "cat_not_configured", "error": "CAT 未配置；工位文件功能仍可使用。"}
        return self.run_paos(["cat", "--url", self.cat_url, *args])

    def dashboard(self, project_id: str = "") -> dict:
        projects = self.projects()
        selected = self.registry.read_record(project_id) if project_id else (projects[0] if projects else None)
        agents = []
        if selected:
            for home_id in selected["homes"]:
                try:
                    agents.append(self.agent(home_id))
                except READ_ERRORS as exc:
                    agents.append({"id": home_id, **error_view(exc)})
        rooms_result = self.cat(["list"]) if self.cat_url else self.cat([])
        rooms = rooms_result["rooms"] if rooms_result.get("ok") else []
        root = runtime_path(selected["root_path"]) if selected else None
        index = root / "INDEX.md" if root else None
        return {"ok": True, "project": selected["id"] if selected else "",
                "coordinator": selected["coordinator_home_id"] if selected else "", "agents": agents,
                "projects": [{"id": p["id"], "name": runtime_path(p["root_path"]).name} for p in projects],
                "index": index.read_text(encoding="utf-8") if index and index.is_file() else "",
                "examples": self.examples(), "rooms": rooms,
                "cat": {"ok": True} if rooms_result.get("ok") else rooms_result}

    def create_room(self, title: str, members: list[str]) -> dict:
        for member in members:
            self.home(member)
        result = self.cat(["create", "--title", title])
        if not result.get("ok"):
            return result
        room_id = result["room"]["id"]
        for member in members:
            joined = self.cat(["join", room_id, "--home", member])
            if not joined.get("ok"):
                return {**joined, "room_id": room_id, "phase": "join"}
        return {"ok": True, "room_id": room_id}

    def room(self, room_id: str) -> dict:
        result = self.cat(["show", room_id])
        return {"ok": True, **result["room"]} if result.get("ok") else result

    def send_message(self, room_id: str, sender: str, body: str, message_id: str) -> dict:
        joined = self.cat(["join", room_id, "--home", sender])
        if not joined.get("ok"):
            return joined
        return self.cat(["send", room_id, "--from", sender, "--body", body, "--message-id", message_id])

    def hint(self, home_id: str, example: dict) -> dict:
        self.home(home_id)
        resources = self.examples()
        item = next((x for kind in ("workflow", "skill", "tool") for x in resources[kind]
                     if (x["id"], x["kind"]) == (example.get("id"), example.get("kind"))), None)
        if item is None:
            raise BoardProblem("example_not_found", "选择的库资源不在当前安装登记中。")
        return self.run_paos(["agent", "send", agent_project_id(home_id), "--to", home_id,
                              "--sender-kind", "human", "--subject", f"方法参考：{item['title']}",
                              "--body", f"请按当前责任判断是否采用此参考。\n{item['title']}\n{item['path']}",
                              "--message-id", f"board-reference-{uuid.uuid4().hex}"])


class Handler(BaseHTTPRequestHandler):
    def _json(self, value: dict, status: int = 200):
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path in {"/", "/index.html"}:
            data = (STATIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        try:
            if url.path == "/api/dashboard":
                value = self.server.board.dashboard(parse_qs(url.query).get("project", [""])[0])
            elif url.path.startswith("/api/agent/"):
                value = self.server.board.agent(unquote(url.path.rsplit("/", 1)[-1]))
            elif url.path.startswith("/api/room/"):
                value = self.server.board.room(unquote(url.path.rsplit("/", 1)[-1]))
            else:
                self._json({"ok": False, "error": "未找到此入口。", "error_code": "not_found"}, 404)
                return
            self._json(value)
        except READ_ERRORS as exc:
            self._json(error_view(exc), 422)

    def do_POST(self):
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("请求必须为 JSON 对象。")
        except (ValueError, UnicodeError) as exc:
            self._json({"ok": False, "error": str(exc), "error_code": "bad_json"}, 400)
            return
        try:
            if self.path == "/api/room":
                members = payload.get("members")
                if not isinstance(members, list) or len(members) < 2 or not all(isinstance(x, str) for x in members):
                    raise BoardProblem("members_invalid", "请选择至少两个登记工位。")
                value = self.server.board.create_room(str(payload.get("title") or "画板沟通"), members)
            elif self.path == "/api/hint":
                value = self.server.board.hint(str(payload.get("agent_id") or ""), payload.get("example") or {})
            elif self.path.startswith("/api/room/") and self.path.endswith("/message"):
                body = str(payload.get("body") or "").strip()
                if not body:
                    raise BoardProblem("empty_body", "请输入发言内容。")
                value = self.server.board.send_message(unquote(self.path.rsplit("/", 2)[-2]),
                                                      str(payload.get("sender_id") or "human"), body,
                                                      str(payload.get("message_id") or f"board-{uuid.uuid4().hex}"))
            else:
                self._json({"ok": False, "error": "未找到此入口。", "error_code": "not_found"}, 404)
                return
            self._json(value)
        except READ_ERRORS as exc:
            self._json(error_view(exc), 422)

    def log_message(self, fmt, *args):
        return


def make_server(board: Board, *, port: int = 8780) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.board = board
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--installation-file", type=Path, default=PACKAGE / "config/local/installation.json")
    parser.add_argument("--cat-url", default="", help="可选 CAT 地址；不配置不阻塞工位读取")
    args = parser.parse_args(argv)
    try:
        server = make_server(Board(args.installation_file, cat_url=args.cat_url), port=args.port)
    except READ_ERRORS as exc:
        print(json.dumps(error_view(exc), ensure_ascii=False), file=sys.stderr)
        return 2
    print(f"PAOS 画板：http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
