"""Thin HTTP commands for the independent system-level CAT sidecar."""
from urllib.parse import quote, urlencode


def add_cat_parser(sub):
    cat = sub.add_parser("cat", help="System roundtable; no Project or Work required")
    cat.add_argument("--url", default="http://127.0.0.1:8870", help="CAT origin, separate from PAOS")
    commands = cat.add_subparsers(dest="cat_command", required=True)
    commands.add_parser("list", help="List roundtables")
    create = commands.add_parser("create", help="Create a roundtable")
    create.add_argument("--title", required=True)
    for name, help_text in (("show", "Show a roundtable"), ("members", "List roundtable members"),
                            ("close", "Close a roundtable; history stays readable")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("room_id")
    join = commands.add_parser("join", help="Join by stable Home ID, including rooter-001")
    join.add_argument("room_id")
    join.add_argument("--home", required=True)
    join.add_argument("--label")
    # Seat participation: one CLI per state transition (member state backend).
    # Reads are inherently `members` already; keep the verbs explicit.
    seat = commands.add_parser(
        "seat",
        help="Change seat participation state of a joined Home (participant/observer/left)",
    )
    seat.add_argument("room_id")
    seat.add_argument("--home", required=True,
                      help="Stable joined Home ID whose seat state changes")
    seat.add_argument(
        "--state",
        required=True,
        choices=["participant", "observer", "left"],
        help=(
            "participant: by default receives reminders and can speak; "
            "observer: read-only, no reminders, no speech; "
            "left: resigned from seat, history kept, no reminders/speech"
        ),
    )
    send = commands.add_parser("send", help="Persist public speech, then remind other members once")
    send.add_argument("room_id")
    send.add_argument("--from", dest="sender_id", required=True, help="Joined stable Home ID")
    send.add_argument("--body", required=True, help="Literal text, @FILE or '-' for stdin")
    send.add_argument("--message-id", required=True, help="Reuse this ID for idempotent replay")
    send.add_argument("--reply-to", help="Existing message ID in this room")
    send.add_argument("--no-notify", action="store_true", help="Save speech without native reminders")
    read = commands.add_parser("read", help="Read public messages after a sequence number")
    read.add_argument("room_id")
    read.add_argument("--after", type=int, default=0)


def _room_summary(room: dict) -> dict:
    """`cat show` default AND --json view: output projection only.

    The original GET room still happens; the CLI just trims its echo.
    Room metadata passes through verbatim, lists/dicts become counts, and
    last_seq is `room["messages"][-1]["seq"]` with 0 for an empty room (the
    cursor start; every non-empty message carries seq by backend contract,
    so no field or type guessing and a non-empty bad seq is never folded
    into the empty-room 0). No message bodies are echoed. The full original
    room is only emitted on explicit --full-result; incremental reading via
    cat read --after (cursor, not paged).
    """
    summary: dict = {}
    counts: dict[str, int] = {}
    for key, value in dict(room).items():
        if isinstance(value, list):
            counts[key] = len(value)
        elif isinstance(value, dict):
            counts[key] = len(value)
        else:
            summary[key] = value
    messages = room.get("messages")
    if isinstance(messages, list):
        counts["last_seq"] = messages[-1]["seq"] if messages else 0
    summary["counts"] = counts
    summary["full_history"] = "cat read ROOM --after N (incremental cursor); original room via --full-result"
    return summary


def execute_cat(args, client, text_arg):
    command = args.cat_command
    if command == "list":
        return client.request("GET", "/api/rooms")
    if command == "create":
        return client.request("POST", "/api/rooms", {"title": args.title})
    path = "/api/rooms/" + quote(args.room_id, safe="")
    if command in {"show", "members"}:
        result = client.request("GET", path)
        if command == "members":
            return {"ok": True, "members": result["room"]["members"]}
        if getattr(args, "full_result", False):
            return result
        return {
            "ok": True,
            "room_id": args.room_id,
            "summary": _room_summary(result["room"]),
        }
    if command == "join":
        return client.request("POST", path + "/members", {
            "home_id": args.home, "label": args.label or args.home,
        })
    if command == "seat":
        # Backend contract stays explicit regardless of the CLI keyword chosen;
        # one command per state keeps the error surface single-line honest.
        return client.request(
            "POST",
            path + "/members/" + quote(args.home, safe="") + "/state",
            {"state": args.state},
        )
    if command == "read":
        return client.request("GET", path + "/messages?" + urlencode({"after": args.after}))
    if command == "close":
        return client.request("POST", path + "/close", {})
    return client.request("POST", path + "/messages", {
        "message_id": args.message_id,
        "sender_id": args.sender_id,
        "body": text_arg(args.body, "public message", required=True),
        "reply_to": args.reply_to,
        "notify": not args.no_notify,
    })
