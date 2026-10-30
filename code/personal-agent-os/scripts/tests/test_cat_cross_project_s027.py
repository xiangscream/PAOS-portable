"""Cross-Project targeted CAT path (s027, w071/r062 v13).

Covers the approved contract (HUMAN-REVIEW-IMPLEMENTATION-PLAN §220/§293):
Room Project association is navigation-only; the cross-Project receiver is
verified by its exact registered Home — never a guessed home/participant.

Realful-scoped:
- a real temp CAT HTTP server (rooms/exchanges/inbox);
- real tmp target project tree (Workstations/2001-s022 with ENTRY.md +
  identity-matching paos-todo/v3 TODO.md);
- the real public seam functions (no component-level stubs).
"""

from __future__ import annotations

import base64
import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


def _v3_todo_text(agent_id: str, project_id: str) -> str:
    return (
        '---\nschema: "paos-todo/v3"\nhome_kind: "project_agent"\n'
        f'home_id: "{agent_id}"\nproject_id: "{project_id}"\n---\n\n'
        "# Current\n\nobjective: \"test\"\n"
        "next_action: \"none\"\n\n# Tasks\n"
    )


def _make_target_home(root: Path, agent_id: str, project_id: str) -> Path:
    home = root / "Workstations" / agent_id
    home.mkdir(parents=True)
    (home / "ENTRY.md").write_text("# fixed\n", encoding="utf-8")
    (home / "TODO.md").write_text(
        _v3_todo_text(agent_id, project_id), encoding="utf-8"
    )
    return home


class _FakeCatServer:
    def __init__(self, room: dict, exchanges_history: list):
        self.room = room
        self.exchanges_history = exchanges_history
        self.srv = None
        self.port = 0

    def start(self) -> str:
        outer = self

        class H(BaseHTTPRequestHandler):
            def _send(self, payload, status=200):
                if status == 200:
                    payload = {"ok": True, **payload}
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

            def do_GET(self):
                base, _, query = self.path.strip("/").partition("?")
                parts = base.split("/")
                room_id = parts[2] if len(parts) >= 3 else ""
                if base.split("?")[0] == f"api/rooms/{room_id}" and room_id in {
                    "room-f96fc33111b9",
                }:
                    return self._send({"room": outer.room})
                if room_id == "room-f96fc33111b9" and base.endswith("/exchanges"):
                    return self._send(
                        {"exchanges": outer.exchanges_history}
                    )
                if room_id == "room-f96fc33111b9" and base.endswith("/inbox"):
                    participant_id = urllib.parse.parse_qs(query).get(
                        "participant_id", [""]
                    )[0]
                    pending = [
                        e
                        for e in outer.exchanges_history
                        if e.get("target_id") == participant_id
                        and not e.get("acknowledged")
                    ]
                    return self._send({"items": pending})
                return self._send({"ok": False, "error": "not found"}, 404)

            def do_POST(self):
                base = self.path.strip("/").split("?")[0]
                if not base.endswith("/exchanges"):
                    return self._send({"ok": False, "error": "not found"}, 404)
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length))
                exchange = dict(payload)
                exchange["exchange_id"] = f"ex-fake-{len(outer.exchanges_history)+1:03d}"
                outer.exchanges_history.append(exchange)
                return self._send({"exchange": exchange})

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        time.sleep(0.2)
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        self.srv.shutdown()


def _participant(participant_id: str, agent_id: str) -> dict:
    return {"participant_id": participant_id, "paos_session_id": agent_id}


_ROOM_2001 = {
    "room_id": "room-f96fc33111b9",
    "status": "open",
    "expired": False,
    "activation_owner": "paos",
    "participants": [
        _participant("68d21-0002", "2001-s022"),
        _participant("force-placeholder-human", "human"),
    ],
    "paos_binding": {"project_id": "2001"},
}


def _project_dict(pid: str, root_path: str, members: list[str]) -> dict:
    return {
        "id": pid,
        "root_path": root_path,
        "sessions": [{"id": m} for m in members],
    }


def _load_real_modules(monkeypatch):
    """Import the real public modules from the candidate source tree."""
    src = Path(__file__).resolve().parent.parent
    import importlib.util as iu
    import sys

    real_src = str(src)
    if real_src not in sys.path:
        sys.path.insert(0, real_src)

    mods = {}
    for name in ["paos_notice", "paos_mail", "paos_contact", "paos_todo_v3",
                 "paos_workstation", "paos_home", "paos_agent_activation",
                 "paos_cat_activation", "paos_attention_service"]:
        spec = iu.spec_from_file_location(name, src / f"{name}.py")
        mod = iu.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            raise RuntimeError(f"{name}: {type(e).__name__}: {e}") from e
        mods[name] = mod
    cat = mods["paos_cat_activation"]
    att = mods["paos_attention_service"]
    # attention service references modules by the original import namespaces
    att.persist_cat_agent_message = cat.persist_cat_agent_message
    return cat, att, mods


def test_raw_persist_defaults_strict_binding_gate(monkeypatch, tmp_path):
    """RAW helper layer keeps its strict default: a bare
    persist_cat_agent_message call (no verified-Home service path, no
    navigation flag) still rejects binding mismatch."""
    cat, _att, _mods = _load_real_modules(monkeypatch)
    srv = _FakeCatServer(dict(_ROOM_2001), [])
    base = srv.start()
    try:
        with pytest.raises(cat.CatActivationProblem) as info:
            cat.persist_cat_agent_message(
                project_id="3002",
                cat_base=base,
                room_id="room-f96fc33111b9",
                target_agent_id="2001-s022",
                content="x",
            )
        assert info.value.code == "cat_project_binding_mismatch"
    finally:
        srv.stop()


def test_reverse_room_navigation_reaches_exact_invoked_home(monkeypatch, tmp_path):
    """Real reverse input (R063-REAL-REVERSE-INPUT): 2001-s022 → 3002-s032,
    invoked Project=3002, receiver Home Project=3002, Room business
    association=2001.  §5.3: the Room binding is navigation-only — the
    verified exact-Home service path must deliver, in this direction too."""
    cat, att, _mods = _load_real_modules(monkeypatch)
    root = tmp_path
    receiver_id = "3002-s032"
    home = root / "Workstations" / receiver_id
    home.mkdir(parents=True)
    (home / "ENTRY.md").write_text("# fixed\n", encoding="utf-8")
    (home / "TODO.md").write_text(_v3_todo_text(receiver_id, "3002"), encoding="utf-8")

    invoked = _project_dict("3002", str(root), ["3002-s027", receiver_id])

    room = dict(_ROOM_2001)
    # Rooter 已正式登记 3002-s032 在该 Room 的真实 participant（原反向输入）
    room["participants"] = list(room["participants"]) + [
        _participant("68d21-0005", "3002-s032")
    ]
    srv = _FakeCatServer(room, [])
    base = srv.start()
    try:
        result = att.send_cat_source(
            root=root,
            project=invoked,
            cat_base=base,
            room_id="room-f96fc33111b9",
            target_agent_id=receiver_id,
            content="reverse room input",
            sender_agent_id="2001-s022",
            message_id="msg-reverse-room-1",
            request_activation=True,
            target_project_lookup=None,
        )
        assert result.get("schema") == "paos-attention-cat-send/v1"
        assert result.get("notice", {}).get("notice_id")
        nav = result["cat"]["project_binding"]
        assert nav.get("navigation_only") is True
        assert nav.get("bound_project_id") == "2001"
        assert result["notice"]["home_id"] == receiver_id
        assert result["notice"]["project_id"] == "3002"
        assert result["transport_state"] == "pending"
        home_ref = result.get("home") or {}
        assert home_ref.get("home_id") == receiver_id
        assert home_ref.get("project_id") == "3002"
    finally:
        srv.stop()


def test_cross_project_send_verifies_exact_receiver_home(monkeypatch, tmp_path):
    cat, att, _mods = _load_real_modules(monkeypatch)
    # real tmp target tree (receiver verified by exact Home)
    target_root = tmp_path / "2001-LRC101"
    _make_target_home(target_root, "2001-s022", "2001")
    p3002 = _project_dict("3002", str(tmp_path / "3002-root"), ["3002-s027"])
    p2001 = _project_dict("2001", str(target_root), ["2001-s022"])

    def lookup(_pid: str) -> dict:
        return p2001

    srv = _FakeCatServer(dict(_ROOM_2001), [])
    base = srv.start()
    try:
        output = att.send_cat_source(
            root=tmp_path / "3002-root",
            project=p3002,
            cat_base=base,
            room_id="room-f96fc33111b9",
            target_agent_id="2001-s022",
            content="cross-project direction",
            sender_agent_id="",   # human fallback (no fake room member)
            request_activation=False,
            target_project_lookup=lookup,
        )
        assert output["transport_state"] == "pending"
        assert output["cross_project"]["target_project_id"] == "2001"
        assert output["cross_project"]["room_binding"]["navigation_only"] is True
        # durable exchange actually appended with no fabricated target
        assert srv.exchanges_history[0]["operation_id"], srv.exchanges_history
        assert srv.exchanges_history[0]["target_id"] == "68d21-0002"
    finally:
        srv.stop()


def test_cross_project_orient_or_missing_home_never_guessed(monkeypatch, tmp_path):
    cat, att, _mods = _load_real_modules(monkeypatch)
    # registered member, but its exact Home dir absent => refuse, no guess
    p3002 = _project_dict("3002", str(tmp_path / "3002-root"), ["3002-s027"])
    p2001 = _project_dict("2001", str(tmp_path / "2001-root"), ["2001-s022"])

    def lookup(_pid: str) -> dict:
        return p2001

    srv = _FakeCatServer(dict(_ROOM_2001), [])
    base = srv.start()
    try:
        with pytest.raises(Exception) as ei:
            att._resolve_target_project_agent_home(
                project=p3002,
                agent_id="2001-s022",
                root_override=str(tmp_path / "3002-root"),
                target_project_lookup=lookup,
            )
        assert "不存在" in str(ei.value) or "Home" in str(ei.value)
        assert not (tmp_path / "2001-root" / "Workstations").exists()
    finally:
        srv.stop()


# ---------------------------------------------------------------------------
# s029 takeover (r063): CLI/HTTP same-seam regressions
# ---------------------------------------------------------------------------

def test_http_cross_project_send_uses_same_exact_home_seam(monkeypatch, tmp_path):
    """Real localhost PAOS server: HTTP CAT send to another project's exact
    registered v3 Home lands the same durable Notice as the CLI path."""
    import importlib.util as iu
    import sys

    src = Path(__file__).resolve().parent.parent.parent
    static = src / "attention-dashboard-v1-static"
    if str(static) not in sys.path:
        sys.path.insert(0, str(static))
    import local_server

    root = tmp_path
    target_id, target_pid = "2001-s022", "2001"
    _make_target_home(root, target_id, target_pid)

    # the invoked-project sender must be a CAT room participant (transport contract)
    room = dict(_ROOM_2001)
    room["participants"] = list(room["participants"]) + [
        _participant("68d21-0003", "3002-s027")
    ]
    cat_srv = _FakeCatServer(room, [])
    cat_base = cat_srv.start()
    try:
        invoked = _project_dict("3002", str(root), ["3002-s027"])
        target = _project_dict(target_pid, str(root), [target_id])

        class TwoProjectStore:
            def __init__(self, projects):
                self._projects = projects

            def get_v2(self, project_id):
                return self._projects[project_id]

        store = TwoProjectStore({"3002": invoked, "2001": target})
        server = local_server.build_server(
            "127.0.0.1", 0, root / "inbox",
            project_store=store,
            workflow_service=object(),
            installation_path=root / "missing-installation.json",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            body = json.dumps({
                "cat_base": cat_base,
                "room_id": "room-f96fc33111b9",
                "target_agent_id": target_id,
                "content": "http seam cross project",
                "sender_agent_id": "3002-s027",
                "message_id": "msg-http-cross-1",
            }).encode("utf-8")
            req = urllib.request.Request(
                base + "/api/projects/3002/attention/cat",
                data=body, method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            assert payload.get("ok") is True
            home = payload.get("home") or {}
            assert home.get("home_id") == target_id
            assert home.get("project_id") == target_pid
        finally:
            server.shutdown()
            server.server_close()
    finally:
        cat_srv.stop()


def test_http_cross_project_unregistered_target_rejected(monkeypatch, tmp_path):
    """Non-convention / unregistered target (rooter-001) is never guessed:
    HTTP returns the stable home_agent_unknown error, not a 500."""
    import importlib.util as iu
    import sys

    src = Path(__file__).resolve().parent.parent.parent
    static = src / "attention-dashboard-v1-static"
    if str(static) not in sys.path:
        sys.path.insert(0, str(static))
    import local_server

    root = tmp_path
    cat_srv = _FakeCatServer(dict(_ROOM_2001), [])
    cat_base = cat_srv.start()
    try:
        invoked = _project_dict("3002", str(root), ["3002-s027"])

        class OneProjectStore:
            def __init__(self, projects):
                self._projects = projects

            def get_v2(self, project_id):
                return self._projects[project_id]

        store = OneProjectStore({"3002": invoked})
        server = local_server.build_server(
            "127.0.0.1", 0, root / "inbox",
            project_store=store,
            workflow_service=object(),
            installation_path=root / "missing-installation.json",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            body = json.dumps({
                "cat_base": cat_base,
                "room_id": "room-f96fc33111b9",
                "target_agent_id": "rooter-001",
                "content": "should not resolve",
                "sender_agent_id": "3002-s027",
            }).encode("utf-8")
            req = urllib.request.Request(
                base + "/api/projects/3002/attention/cat",
                data=body, method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status, payload = resp.status, json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                status, payload = exc.code, json.loads(exc.read())
            assert status == 422
            assert payload.get("error_code") == "home_agent_unknown"
        finally:
            server.shutdown()
            server.server_close()
    finally:
        cat_srv.stop()


def test_http_cross_project_non_v3_target_rejected(monkeypatch, tmp_path):
    """Target registered in its own project but Home TODO still v2 → the
    exact-Home gate rejects (attention_home_not_v3), never a guessed write."""
    import importlib.util as iu
    import sys

    src = Path(__file__).resolve().parent.parent.parent
    static = src / "attention-dashboard-v1-static"
    if str(static) not in sys.path:
        sys.path.insert(0, str(static))
    import local_server

    root = tmp_path
    target_id, target_pid = "2001-s022", "2001"
    home = root / "Workstations" / target_id
    home.mkdir(parents=True)
    (home / "ENTRY.md").write_text("# fixed\n", encoding="utf-8")
    (home / "TODO.md").write_text(
        '---\nschema: "paos-todo/v2"\nproject_id: "2001"\nagent_id: "2001-s022"\n---\n\n# Current\n',
        encoding="utf-8",
    )

    cat_srv = _FakeCatServer(dict(_ROOM_2001), [])
    cat_base = cat_srv.start()
    try:
        invoked = _project_dict("3002", str(root), ["3002-s027"])
        target = _project_dict(target_pid, str(root), [target_id])

        class TwoProjectStore:
            def __init__(self, projects):
                self._projects = projects

            def get_v2(self, project_id):
                return self._projects[project_id]

        store = TwoProjectStore({"3002": invoked, "2001": target})
        server = local_server.build_server(
            "127.0.0.1", 0, root / "inbox",
            project_store=store,
            workflow_service=object(),
            installation_path=root / "missing-installation.json",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            body = json.dumps({
                "cat_base": cat_base,
                "room_id": "room-f96fc33111b9",
                "target_agent_id": target_id,
                "content": "non v3 target",
                "sender_agent_id": "3002-s027",
            }).encode("utf-8")
            req = urllib.request.Request(
                base + "/api/projects/3002/attention/cat",
                data=body, method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    status, payload = resp.status, json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                status, payload = exc.code, json.loads(exc.read())
            assert status == 422
            assert payload.get("error_code") == "attention_home_not_v3"
        finally:
            server.shutdown()
            server.server_close()
    finally:
        cat_srv.stop()


def test_cli_cross_project_target_lookup_rejects_non_member(monkeypatch, tmp_path):
    """CLI lookup keeps the invoked-project path unchanged for non-members."""
    from paos_home import agent_project_id
    from paos_workstation import posix_windows_drive_locator
    import importlib.util as iu
    import sys

    src = Path(__file__).resolve().parent.parent.parent
    scripts = src / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import paos as paos_cli

    target_id = "2001-s022"
    _make_target_home(tmp_path, target_id, "2001")
    target_project = _project_dict("2001", str(tmp_path), [target_id])

    class StubClient:
        """Mirrors the real server contract: GET /api/projects/{id} returns
        {"project": <v2 dict>}; unknown ids raise HTTPError-like failures."""

        def __init__(self, projects):
            self._projects = projects

        def request(self, method, path):
            pid = path.rsplit("/", 1)[-1]
            if pid in self._projects:
                return {"project": self._projects[pid]}
            import urllib.error

            raise urllib.error.HTTPError(path, 404, "Not Found", hdrs=None, fp=None)

    # registered member of its own project with exact v3 Home → callable
    lookup = paos_cli._cross_project_target_lookup(
        StubClient({"2001": target_project}), tmp_path, target_id
    )
    assert callable(lookup)
    assert lookup("2001")["id"] == "2001"

    # target NOT a member of its claimed project → None (no guess)
    bad_project = _project_dict("2001", str(tmp_path), ["2001-s099"])
    assert paos_cli._cross_project_target_lookup(
        StubClient({"2001": bad_project}), tmp_path, target_id
    ) is None

    # non-convention id → None before any lookup
    assert paos_cli._cross_project_target_lookup(
        StubClient({"2001": target_project}), tmp_path, "rooter-001"
    ) is None

    # registered member but Home TODO not v3 → lookup still routes; the
    # service `_assert_home_v3` rejects with the precise attention_home_not_v3
    home = tmp_path / "Workstations" / target_id
    (home / "TODO.md").write_text(
        '---\nschema: "paos-todo/v2"\nproject_id: "2001"\nagent_id: "2001-s022"\n---\n',
        encoding="utf-8",
    )
    lookup_non_v3 = paos_cli._cross_project_target_lookup(
        StubClient({"2001": target_project}), tmp_path, target_id
    )
    assert callable(lookup_non_v3)
    assert lookup_non_v3("2001")["id"] == "2001"


def test_http_reverse_room_navigation_invoked_member(monkeypatch, tmp_path):
    """HTTP layer of the real reverse input: receiver (3002-s032) is an
    invoked-project member → cross_lookup is None; §5.3 navigation must
    still deliver through the same service seam (CLI/HTTP parity)."""
    import importlib.util as iu
    import sys

    src = Path(__file__).resolve().parent.parent.parent
    static = src / "attention-dashboard-v1-static"
    if str(static) not in sys.path:
        sys.path.insert(0, str(static))
    import local_server

    root = tmp_path
    receiver_id = "3002-s032"
    home = root / "Workstations" / receiver_id
    home.mkdir(parents=True)
    (home / "ENTRY.md").write_text("# fixed\n", encoding="utf-8")
    (home / "TODO.md").write_text(_v3_todo_text(receiver_id, "3002"), encoding="utf-8")

    room = dict(_ROOM_2001)
    room["participants"] = list(room["participants"]) + [
        _participant("68d21-0005", receiver_id)
    ]
    cat_srv = _FakeCatServer(room, [])
    cat_base = cat_srv.start()
    try:
        invoked = _project_dict("3002", str(root), ["3002-s027", receiver_id])

        class OneProjectStore:
            def __init__(self, projects):
                self._projects = projects

            def get_v2(self, project_id):
                return self._projects[project_id]

        store = OneProjectStore({"3002": invoked})
        server = local_server.build_server(
            "127.0.0.1", 0, root / "inbox",
            project_store=store,
            workflow_service=object(),
            installation_path=root / "missing-installation.json",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            body = json.dumps({
                "cat_base": cat_base,
                "room_id": "room-f96fc33111b9",
                "target_agent_id": receiver_id,
                "content": "http reverse room input",
                "sender_agent_id": "2001-s022",
                "message_id": "msg-http-reverse-1",
            }).encode("utf-8")
            req = urllib.request.Request(
                base + "/api/projects/3002/attention/cat",
                data=body, method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            assert payload.get("schema") == "paos-attention-cat-send/v1"
            assert payload["notice"]["home_id"] == receiver_id
            assert payload["cat"]["project_binding"]["navigation_only"] is True
            assert payload["cat"]["project_binding"]["bound_project_id"] == "2001"
        finally:
            server.shutdown()
            server.server_close()
    finally:
        cat_srv.stop()
