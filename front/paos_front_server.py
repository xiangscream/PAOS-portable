"""PAOS 画板后端（给新手看的说明）

## 这个文件是干什么的？

它是 PAOS 画板（那个网页）的"后端"。网页本身（index.html）只负责把数据画出来，
真正"去读文件、整理数据、执行动作"的事都发生在这里。

可以把它理解成一个**小小的本地服务**，跑在你自己电脑上（127.0.0.1，不外网），
做三件事：
  1. 把散在各处的数据（工位 TODO、共享库目录、CAT 房间）**读出来、整理成 JSON**；
  2. 把 JSON 通过几个网址（路由）**提供给网页**；
  3. 网页要点"创建房间""给 agent 留提示""在房间发言"时，**替网页去调用官方命令**。

## 它是怎么搭起来的？（底层架构）

```
网页（index.html）
   │  浏览器发 HTTP 请求
   ▼
本文件（paos_front_server.py）
   │  读文件 → 整理成 JSON → 返回给网页
   │  需要写数据时 → 调 paos 官方 CLI（不自己拼文件）
   ▼
磁盘上的真实数据
   · 工位：D:/paos-business/Workstations/<agent>/
   · 共享库：D:/paos-portable/libraries/
   · CAT 房间：~/.paos/cat/data/rooms/
```

**为什么这么简单？** 因为 PAOS 的事实源本来就是文件（Markdown/JSON）。
后端只需要"读文件 + 调官方写入命令"，不需要数据库、不需要框架、不需要登录。

## 路由表（每个网址是干什么的）

| 方法 | 网址 | 干什么 |
| --- | --- | --- |
| GET  | `/`                    | 返回画板网页（index.html） |
| GET  | `/api/dashboard?project=X` | 给网页"一屏数据"：工位列表、CAT 房间、范例库、INDEX、项目登记 |
| GET  | `/api/agent/<工位id>`    | 返回某个工位的详情（TODO 全文、最近邮件、成果文档） |
| GET  | `/api/room/<房间id>`     | 返回某个 CAT 房间的完整内容（成员、全部消息） |
| POST | `/api/room`            | 连线用：创建 CAT 房间，并把成员入座（走官方 cat create + join） |
| POST | `/api/room/<房间id>/message` | 在房间里发一句话（先让发言者入座，再走官方 cat send） |
| POST | `/api/hint`            | 给某个 agent 留"请按范例参考"的提示（走官方 agent send） |

**一个关键原则**：读数据可以直接读文件（快），**写数据一律走官方命令**
（paos cat create/join/send、paos agent send）。因为官方命令会处理
版本、回执、去重、状态机，绕过它们容易制造"看起来成功但其实没成"的假状态。

## 用到哪些库？

只用 Python 标准库（http.server、json、re、pathlib、subprocess 等），
**没有任何第三方依赖**，一台能跑 Python 的电脑就能运行。

## 怎么启动？

    python paos_front_server.py --port 8780
然后浏览器打开 http://127.0.0.1:8780/ 。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BUSINESS = Path("D:/paos-business")
LIBRARIES = Path("D:/paos-portable/libraries")
CAT_ROOMS = Path.home() / ".paos" / "cat" / "data" / "rooms"
STATIC = Path(__file__).parent
CODE = Path("D:/paos-portable/code/personal-agent-os")
INSTALL = "D:/paos-portable/config/installation.json"
PY = "C:/Users/remo/.workbuddy/binaries/python/versions/3.13.12/python.exe"


def run_paos(args: list[str]) -> dict:
    """执行一条 paos 官方命令，返回它的 JSON 结果。

    这是**唯一**的写数据通道：凡是要创建房间、发消息、留提示，
    都通过它调用官方 CLI，而不是自己去改文件。
    这样官方的回执、状态机、去重都会生效。
    """
    env = dict(os.environ)
    env["PAOS_INSTALLATION_FILE"] = INSTALL   # 告诉 CLI 用哪份安装配置
    env["PYTHONIOENCODING"] = "utf-8"          # Windows 控制台避免中文乱码
    try:
        r = subprocess.run([PY, "scripts/paos.py"] + args, cwd=CODE, env=env,
                           capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "cli_timeout"}
    try:
        return json.loads(r.stdout)
    except Exception:
        # 官方命令没返回 JSON 时，把退出码和末尾输出带回去，方便排查
        return {"ok": r.returncode == 0, "stdout": r.stdout[-600:], "stderr": r.stderr[-400:]}


# ---------- 读取 ----------

def parse_todo(path: Path) -> dict:
    info = {"stage": "", "next_action": "", "waiting": "", "tasks": {}}
    if not path.exists():
        return info
    lines = path.read_text(encoding="utf-8").split("\n")
    for line in lines:
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m and m.group(1) in ("stage", "next_action", "waiting"):
            raw = m.group(2).strip()
            try:
                info[m.group(1)] = json.loads(raw)
            except Exception:
                info[m.group(1)] = raw.strip('"')
        elif line.startswith("state:"):
            m2 = re.match(r"state:\s*\"?(\w+)\"?", line.strip())
            if m2:
                st = m2.group(1)
                info["tasks"][st] = info["tasks"].get(st, 0) + 1
    return info


def read_team(project_root: Path) -> tuple[list[dict], str]:
    """以 TEAM.md 为唯一渲染依据：成员、职责、Harness、Coordinator。"""
    members, coordinator = [], ""
    team_file = project_root / "TEAM.md"
    if not team_file.exists():
        return members, coordinator
    text = team_file.read_text(encoding="utf-8")
    m = re.search(r"Coordinator：([\w-]+)", text)
    if m:
        coordinator = m.group(1)
    for match in re.finditer(r"###\s+([\w-]+)\n(.*?)(?=###|\Z)", text, re.S):
        aid = match.group(1)
        block = match.group(2)

        def field(name):
            f = re.search(rf"{name}：(.+)", block)
            return f.group(1).strip() if f else ""

        members.append({"id": aid, "role": field("职责"),
                        "harness": field("Harness"), "status": field("成员状态")})
    return members, coordinator


def read_agents(project_root: Path) -> tuple[list[dict], str]:
    members, coordinator = read_team(project_root)
    ws = project_root / "Workstations"
    out = []
    for m in members:
        home = ws / m["id"]
        todo = parse_todo(home / "TODO.md") if (home / "TODO.md").exists() else {"stage": "", "next_action": "", "waiting": "", "tasks": {}}
        notices = home / "notices"
        n_total = len(list(notices.glob("*.md"))) if notices.exists() else 0
        n_handled = len(list((notices / ".handled").glob("*.json"))) if (notices / ".handled").exists() else 0
        mailbox = home / "mailbox"
        n_mail = len(list(mailbox.glob("*.md"))) if mailbox.exists() else 0
        out.append({**m, "project": project_root.name, "stage": todo["stage"],
                    "next_action": todo["next_action"], "waiting": todo["waiting"],
                    "tasks": todo["tasks"], "pending_notices": n_total - n_handled,
                    "mail_total": n_mail})
    return out, coordinator


def read_catalog(path: Path, kind: str) -> list[dict]:
    """解析 CATALOG.md 的 Markdown 表格为范例列表。"""
    items = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("|") or "---" in line or "ID |" in line or "Skill |" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0] or cells[0] in ("ID", "Skill"):
            continue
        items.append({"id": cells[0], "title": cells[1], "kind": kind,
                      "path": cells[-1] if cells else ""})
    return items


def read_rooms() -> list[dict]:
    out = []
    if not CAT_ROOMS.exists():
        return out
    for f in sorted(CAT_ROOMS.glob("room-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        msgs = d.get("messages") or []
        out.append({
            "id": d.get("id"),
            "title": d.get("title"),
            "status": d.get("status"),
            "members": [m.get("home_id") for m in d.get("members", [])],
            "message_count": len(msgs),
            "last_message": (msgs[-1].get("body", "")[:160] if msgs else ""),
        })
    return out


def read_projects() -> list[dict]:
    root = Path("D:/paos-portable/data/project-registry/projects")
    out = []
    if not root.exists():
        return out
    for f in sorted(root.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        out.append({
            "id": d.get("id"),
            "name": d.get("name"),
            "area": d.get("area"),
            "status": d.get("status"),
            "next_items": d.get("next_items") or [],
            "decisions": [{"title": x.get("title"), "status": x.get("status"),
                           "rationale": (x.get("rationale") or "")[:220]}
                          for x in (d.get("decisions") or [])[-4:]],
        })
    return out


def read_index(project_root: Path) -> str:
    f = project_root / "INDEX.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


PROJECT_LIBS = {"3002": Path("D:/paos-business")}


def dashboard(project: str = "3002") -> dict:
    """给网页"一屏数据"：当前项目库的工位、INDEX、CAT 房间、范例库、项目登记。
    project 参数决定读哪个项目库（PROJECT_LIBS 里的键）。
    """
    root = PROJECT_LIBS.get(project, PROJECT_LIBS["3002"])
    agents, coordinator = read_agents(root)
    return {
        "project": project,
        "coordinator": coordinator,
        "agents": agents,
        "index": read_index(root),
        "projects": read_projects(),
        "examples": {
            "workflow": read_catalog(LIBRARIES / "workflow" / "CATALOG.md", "workflow"),
            "skill": read_catalog(LIBRARIES / "skill" / "CATALOG.md", "skill"),
            "tool": read_catalog(LIBRARIES / "tool-catalog.md", "tool"),
        },
        "rooms": read_rooms(),
    }


# ---------- 动作 ----------

def create_room(title: str, members: list[str]) -> dict:
    """连线时创建 CAT 房间，并把参与成员逐个"请进房间"（入座）。

    为什么要 join？因为 `cat create --title` 只建空房间、不加人；
    而 CAT 规定"没入座就不能发言"。所以创建后必须逐个 join，
    否则后面在房间里发言会报 sender_not_seated。
    """
    d = run_paos(["cat", "create", "--title", title])
    room = d.get("room") or {}
    rid = room.get("id") or d.get("room_id")
    if not rid:
        return {"ok": False, "error": "create_failed", "detail": d}
    joined = []
    for m in members:
        r = run_paos(["cat", "join", rid, "--home", m])
        joined.append({"home": m, "result": r.get("ok", r.get("state", ""))})
    return {"ok": True, "room_id": rid, "joined": joined, "create": d}


def send_hint(agent_id: str, example: dict) -> dict:
    project = agent_id.split("-")[0]
    subject = f"请按范例作为参考：{example.get('title') or example.get('id')}"
    body = (f"来自画板：请以 `{example.get('kind')}` 范例 **{example.get('title')}**"
            f"（`{example.get('id')}`）作为当前工作的参考。\n\n路径：`{example.get('path')}`\n")
    return run_paos(["agent", "send", project, "--to", agent_id,
                     "--subject", subject, "--body", body, "--sender-kind", "human"])


def room_detail(room_id: str) -> dict:
    """读某个 CAT 房间的完整内容：标题、成员、状态、全部消息。
    用于网页"点进房间看完整对话"那一页。
    """
    f = CAT_ROOMS / f"{room_id}.json"
    if not f.exists():
        return {"ok": False, "error": "room_not_found"}
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {"ok": False, "error": "room_unreadable"}
    return {"ok": True, "id": d.get("id"), "title": d.get("title"),
            "status": d.get("status"), "members": d.get("members", []),
            "messages": d.get("messages", [])}


def send_room_message(room_id: str, sender_id: str, body: str) -> dict:
    """在房间里发一句话。先让发言者入座，再走官方 cat send。

    发言前必须 join（CAT 的规矩：没入座不能说话）。
    重复 join 已入座的人不会有副作用，所以每次都先 join 一次最稳妥。
    """
    run_paos(["cat", "join", room_id, "--home", sender_id])
    mid = f"msg-front-{uuid.uuid4().hex[:10]}"
    return run_paos(["cat", "send", room_id, "--from", sender_id,
                     "--body", body, "--message-id", mid])


def agent_detail(agent_id: str) -> dict:
    """读某个工位的详情：TODO 全文、最近邮件（带预览）、成果文档名。
    用于网页"双击节点看工位"那一页。
    """
    home = BUSINESS / "Workstations" / agent_id
    if not home.exists():
        return {"ok": False, "error": "home_not_found"}
    todo = (home / "TODO.md").read_text(encoding="utf-8") if (home / "TODO.md").exists() else ""
    entry = (home / "ENTRY.md").read_text(encoding="utf-8") if (home / "ENTRY.md").exists() else ""
    mails = []
    mb = home / "mailbox"
    if mb.exists():
        for p in sorted(mb.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
            body = p.read_text(encoding="utf-8")[:600]
            mails.append({"name": p.name, "preview": body})
    docs = [p.name for p in home.glob("*.md") if p.name not in ("TODO.md", "ENTRY.md", "CONTACT.md", "STATUS.md")]
    return {"ok": True, "id": agent_id, "todo": todo, "entry": entry, "mails": mails, "docs": docs}


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _static(self, name, ctype):
        p = STATIC / name
        if not p.exists():
            self._json({"ok": False, "error": "not_found"}, 404)
            return
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._static("index.html", "text/html; charset=utf-8")
        elif self.path.startswith("/api/dashboard"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            self._json(dashboard(q.get("project", ["3002"])[0]))
        elif self.path.startswith("/api/agent/"):
            self._json(agent_detail(self.path.rsplit("/", 1)[-1]))
        elif self.path.startswith("/api/room/"):
            self._json(room_detail(self.path.rsplit("/", 1)[-1]))
        else:
            self._json({"ok": False, "error": "not_found"}, 404)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._json({"ok": False, "error": "bad_json"}, 400)
            return
        if self.path == "/api/room":
            title = (payload.get("title") or "").strip() or "画板沟通"
            members = payload.get("members") or []
            self._json(create_room(title, members))
        elif self.path == "/api/hint":
            agent = payload.get("agent_id", "")
            example = payload.get("example") or {}
            self._json(send_hint(agent, example))
        elif self.path.startswith("/api/room/") and self.path.endswith("/message"):
            room_id = self.path.rsplit("/", 2)[-2]
            sender = (payload.get("sender_id") or "human").strip()
            body = (payload.get("body") or "").strip()
            if not body:
                self._json({"ok": False, "error": "empty_body"}, 400)
            else:
                self._json(send_room_message(room_id, sender, body))
        else:
            self._json({"ok": False, "error": "not_found"}, 404)

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8780)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"PAOS 画板后端：http://127.0.0.1:{args.port}/  (Ctrl+C 停止)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
