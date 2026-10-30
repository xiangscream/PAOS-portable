"""Passive, exact-self reminder endpoint owned by a Codex Desktop thread.

Start inside the target's own Desktop environment. No caller/pipe arguments,
tool proxy, thread selector, model override, consumer, or automatic resend.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import sys
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError

from wakeup_native.codex_app_tools import DesktopPipeClient
from paos_contact import _codex_receiver_view
from runtime_injection import _native_lock, _request
from wakeup_native.diagnostics import exception_fields, transport_fields
from wakeup_native.process_identity import process_snapshot, stop_windows_instance, valid_identity


class ReceiverError(RuntimeError):
    def __init__(self, code, detail, status=409, *, diagnostic=None):
        super().__init__(detail)
        self.code = code
        self.status = status
        self.diagnostic = transport_fields(diagnostic)


def _native_status(value):
    if value is None:
        return "not_returned"
    if isinstance(value, str) and value in {"active", "idle", "notLoaded", "systemError"}:
        return value
    return "unrecognized"


class SelfReminder:
    def __init__(self, client, session_id, stop_file):
        self.client = client
        self.session_id = session_id
        self.stop_file = Path(stop_file)

    @classmethod
    def from_desktop(cls, stop_file):
        session = os.environ.get("CODEX_THREAD_ID", "").strip()
        pipe = os.environ.get("CODEX_APP_TOOLS_PIPE_PATH", "").strip()
        if not session or not pipe:
            raise ReceiverError("codex_caller_unavailable", "Start from the target's own Codex Desktop environment", 503)
        return cls(DesktopPipeClient(pipe, session), session, stop_file)

    def send(self, payload, *, observe=None):
        if not isinstance(payload, dict) or set(payload) != {"session_id", "message"}:
            raise ReceiverError("invalid_request", "Only session_id and message are accepted", 400)
        if payload["session_id"] != self.session_id:
            raise ReceiverError("target_not_granted", "This receiver can remind only its own thread", 403)
        if not isinstance(payload["message"], str) or not payload["message"].strip():
            raise ReceiverError("invalid_request", "message must be nonempty text", 400)
        if self.stop_file.exists():
            raise ReceiverError("native_stopped", "Explicit STOP prevents native injection")
        if observe:
            observe("status_read_started")
        try:
            status = self.client.thread_status(self.session_id)
        except (OSError, EOFError, RuntimeError) as exc:
            raise ReceiverError("native_unreachable", f"Own Desktop status is unavailable ({type(exc).__name__})", 503,
                                diagnostic={"phase": "status_read", **exception_fields(exc)}) from exc
        if observe:
            observe("status_read_returned", native_status=_native_status(status))
        if not isinstance(status, str) or status not in {"active", "idle", "notLoaded"}:
            raise ReceiverError("native_unavailable", f"Target is not wakeable: {status}", 503,
                                diagnostic={"phase": "status_read", "native_status": _native_status(status)})
        if self.stop_file.exists():
            raise ReceiverError("native_stopped", "Explicit STOP prevents native injection")
        if observe:
            observe("native_submit_started")
        try:
            self.client.wake(self.session_id, payload["message"])
        except (OSError, EOFError, RuntimeError, json.JSONDecodeError, UnicodeError) as exc:
            # Sending may already have reached Desktop. Never retry it here.
            raise ReceiverError("delivery_not_confirmed", f"Own Desktop send receipt is unavailable ({type(exc).__name__}); do not resend", 502,
                                diagnostic={"phase": "native_submit", **exception_fields(exc)}) from exc
        if observe:
            observe("native_result_returned")
        return {"accepted": True, "session_id": self.session_id, "completed": False,
                "native_status_before_submit": status}


def make_server(reminder, token, lifecycle=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # No HTTP access log containing caller content or credentials.

        def do_POST(self):
            self.request_id = None
            self.started_at = time.monotonic()
            if self.path != "/send":
                self.reply(404, {"error": "unknown_endpoint"})
                return
            if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                self.reply(401, {"error": "authorization_required"})
                return
            supplied_id = self.headers.get("X-PAOS-Request-ID")
            # Missing IDs get a local correlation ID; they never grant access.
            self.request_id = supplied_id if supplied_id is not None else uuid.uuid4().hex
            if transport_fields({"request_id": self.request_id}).get("request_id") != self.request_id:
                self.request_id = None
                self.reply(400, {"error": "invalid_request", "retry": False})
                return
            self.observe("request_received")
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                result = reminder.send(payload, observe=self.observe)
            except ValueError as exc:
                self.observe("request_rejected", error_code="invalid_request", **exception_fields(exc))
                self.reply(400, {"error": "invalid_request", "retry": False})
                return
            except ReceiverError as exc:
                self.observe("native_result_unknown" if exc.code == "delivery_not_confirmed" else "request_rejected",
                             error_code=exc.code, **exc.diagnostic)
                self.reply(exc.status, {"error": exc.code, "retry": False,
                                        "diagnostic": {"request_id": self.request_id, **exc.diagnostic}})
                return
            self.reply(200, {**result, "request_id": self.request_id})

        def observe(self, event, **fields):
            if lifecycle is None or self.request_id is None:
                return
            row = {"request_id": self.request_id,
                   "elapsed_ms": round((time.monotonic() - self.started_at) * 1000), **fields}
            try:
                record_lifecycle(lifecycle, event, **row)
            except OSError as exc:
                # Observability failure cannot change delivery or replay a send.
                print(json.dumps({"event": "request_log_failed", "request_id": self.request_id,
                                  **exception_fields(exc)}), file=sys.stderr, flush=True)

        def reply(self, status, body):
            data = json.dumps(body).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except OSError as exc:
                self.observe("http_reply_failed", phase="http_reply", http_status=status, **exception_fields(exc))
                return  # The peer is gone. Record the failure; never send again.
            self.observe("http_reply_returned", http_status=status)

    # Single request execution at a time, including the native status/send pair.
    return HTTPServer(("127.0.0.1", 0), Handler)


def serve(runtime_file, stop_file):
    runtime_file = Path(runtime_file)
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    lifecycle_file = runtime_file.with_name(runtime_file.name + ".lifecycle.jsonl")
    fd = os.open(lifecycle_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as lifecycle:
        record_lifecycle(lifecycle, "starting", parent_pid=os.getppid(), python=sys.executable)
        returned = False
        try:
            serve_owned_runtime(runtime_file, stop_file, lifecycle)
            returned = True
        finally:
            error = None if returned else sys.exc_info()[1]
            record_lifecycle(lifecycle, "exit", outcome="exception" if error else "normal_return",
                             exception_type=type(error).__name__ if error else None,
                             error_code=error.code if isinstance(error, ReceiverError) else None)


def record_lifecycle(stream, event, **fields):
    # Fixed operational fields only: never exception text, payload, token or pipe.
    row = {"at": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(), "event": event, **fields}
    stream.write(json.dumps(row) + "\n")
    stream.flush()


def serve_owned_runtime(runtime_file, stop_file, lifecycle):
    reminder = SelfReminder.from_desktop(stop_file)
    if reminder.stop_file.exists():
        raise ReceiverError("native_stopped", "Original STOP prevents receiver prepare; leave the grant unchanged")
    target = {"runtime": "codex", "session_id": reminder.session_id, "stop_file": str(reminder.stop_file),
              "extension": {"receiver_runtime_file": str(runtime_file)}}
    # Share the existing Windows/Linux native lock with senders and preparers.
    with _native_lock(target):
        if runtime_file.exists():
            view = _codex_receiver_view(target)
            if view.get("reason") == "legacy_identity_unverified":
                migrate_legacy_runtime(runtime_file, reminder, lifecycle)
                return  # Keep the authenticated original receiver, not this launcher PID.
            if view["state"] not in {"process_not_running", "process_identity_mismatch"}:
                raise ReceiverError("receiver_not_rotatable", "Existing grant is live, unknown or not this thread; keep it unchanged")
            archive = runtime_file.with_name(f"{runtime_file.name}.stale-{view['pid']}-{time.time_ns()}.json")
            runtime_file.rename(archive)
            record_lifecycle(lifecycle, "stale_archived", old_pid=view["pid"], archive=str(archive))
        server, runtime = publish_owned_runtime(runtime_file, reminder, lifecycle)
    try:
        record_lifecycle(lifecycle, "ready", session_id=reminder.session_id, endpoint=runtime["endpoint"])
        server.serve_forever()
    finally:
        server.server_close()
        runtime_file.unlink()


def publish_owned_runtime(runtime_file, reminder, lifecycle=None):
    process = process_snapshot(os.getpid())
    if process["alive"] is not True or not valid_identity(process.get("identity")):
        raise ReceiverError("process_identity_unavailable", "Own OS process instance is not verified", 503)
    token = secrets.token_urlsafe(32)
    server = make_server(reminder, token, lifecycle)
    runtime = {"schema": "paos-codex-self-reminder/v1", "pid": os.getpid(),
               "process_identity": process["identity"],
               "receiver_behavior": "native_followup",
               "endpoint": f"http://127.0.0.1:{server.server_port}",
               "session_id": reminder.session_id, "token": token}
    try:
        # Exclusive creation prevents a second launcher replacing a live grant.
        fd = os.open(runtime_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:
        server.server_close()
        raise
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(runtime, stream)
    except OSError:
        server.server_close()
        runtime_file.unlink()
        raise
    return server, runtime


def verified_owned_runtime(runtime_file, reminder):
    """Verify the exact Owner, invocation, instance and authenticated rejection.

    The existing endpoint checks self and rejects an empty message before any
    Desktop read/send. A reachable port or an unauthenticated 400 is insufficient.
    """
    original = runtime_file.read_bytes()
    old = json.loads(original)
    process = process_snapshot(old["pid"], str(runtime_file), str(reminder.stop_file))
    if process["alive"] is not True or process.get("invocation_matches") is not True or not valid_identity(process.get("identity")):
        raise ReceiverError("legacy_receiver_unverified", "Legacy receiver invocation is not verified", 503)
    if "process_identity" in old and old["process_identity"] != process["identity"]:
        raise ReceiverError("receiver_identity_mismatch", "Registered process instance changed; keep registration", 503)
    try:
        _request({"timeout_seconds": 2}, old["endpoint"], "POST", "/send",
                 {"session_id": reminder.session_id, "message": ""}, token=old["token"])
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            verified = exc.code == 400 and isinstance(body, dict) and body.get("error") == "invalid_request"
        except (ValueError, OSError):
            verified = False
    except (URLError, OSError, ValueError):
        verified = False
    else:
        verified = False
    final = process_snapshot(old["pid"], str(runtime_file), str(reminder.stop_file))
    if (not verified or final != process or runtime_file.read_bytes() != original
            or reminder.stop_file.exists()):
        raise ReceiverError("legacy_receiver_unverified", "Legacy authenticated identity changed or is unavailable; keep registration", 503)
    return original, old, process


def retire_owned_runtime(runtime_file, stop_file):
    """Explicit Windows Owner update; normal SessionStart never calls this."""
    reminder = SelfReminder.from_desktop(stop_file)
    target = {"runtime": "codex", "session_id": reminder.session_id, "stop_file": str(reminder.stop_file),
              "extension": {"receiver_runtime_file": str(runtime_file)}}
    with _native_lock(target):
        if reminder.stop_file.exists():
            raise ReceiverError("native_stopped", "Original STOP prevents receiver update")
        view = _codex_receiver_view(target)
        if view["state"] in {"process_not_running", "process_identity_mismatch"} or view["reason"] == "runtime_file_missing":
            return  # Normal prepare handles an absent or positively stale registration.
        if view["prepared"] is not True and view["reason"] != "legacy_identity_unverified":
            raise ReceiverError("receiver_update_unverified", "Own receiver instance is unknown or foreign; keep registration", 503)
        _, old, process = verified_owned_runtime(runtime_file, reminder)
        stop_windows_instance(old["pid"], process["identity"])
        # Keep the exact old registration; normal prepare archives it after exit.


def migrate_legacy_runtime(runtime_file, reminder, lifecycle):
    original, old, process = verified_owned_runtime(runtime_file, reminder)
    archive = runtime_file.with_name(f"{runtime_file.name}.legacy-{old['pid']}-{time.time_ns()}.json")
    with os.fdopen(os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stream:
        stream.write(original)
    updated = {**old, "process_identity": process["identity"]}
    temp = runtime_file.with_name(f"{runtime_file.name}.identity-{time.time_ns()}.tmp")
    try:
        with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as stream:
            json.dump(updated, stream)
        os.replace(temp, runtime_file)
    finally:
        temp.unlink(missing_ok=True)
    record_lifecycle(lifecycle, "identity_migrated", old_pid=old["pid"], archive=str(archive))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-file", required=True)
    parser.add_argument("--stop-file", required=True)
    args = parser.parse_args()
    serve(args.runtime_file, args.stop_file)


if __name__ == "__main__":
    main()
