"""Machine-only transport diagnostics; never copy exception messages or payloads."""
from urllib.error import URLError


_NATIVE_STATUS_VALUES = frozenset({"systemError", "not_returned", "unrecognized"})


def exception_fields(error):
    cause = error.reason if isinstance(error, URLError) and isinstance(error.reason, BaseException) else error
    fields = {"exception_type": type(cause).__name__}
    for name in ("errno", "winerror"):
        value = getattr(cause, name, None)
        if type(value) is int:
            fields[name] = value
    return fields


def transport_fields(value):
    """Select only the technical fields that can cross a receipt boundary."""
    if not isinstance(value, dict):
        return {}
    result = {}
    request_id = value.get("request_id")
    if isinstance(request_id, str) and len(request_id) == 32 and all(c in "0123456789abcdef" for c in request_id):
        result["request_id"] = request_id
    if isinstance(value.get("phase"), str) and value["phase"] in {"http_wait", "status_read", "native_submit", "http_reply"}:
        result["phase"] = value["phase"]
    native_status = value.get("native_status")
    if isinstance(native_status, str) and native_status in _NATIVE_STATUS_VALUES:
        result["native_status"] = native_status
    name = value.get("exception_type")
    if isinstance(name, str) and len(name) <= 80 and name.isidentifier():
        result["exception_type"] = name
    for name in ("errno", "winerror", "http_status"):
        if type(value.get(name)) is int:
            result[name] = value[name]
    return result
