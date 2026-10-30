"""OS process-instance identity and the installed receiver invocation contract.

Command lines are used only to classify legacy registrations; never returned or
logged. PID, executable name, timestamps of files and reachable ports are not
positive identity evidence.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import re


def valid_identity(value):
    return isinstance(value, str) and re.fullmatch(r"windows:[0-9]+|linux:[0-9a-f-]{36}:[0-9]+", value) is not None


def receiver_invocation(argv, runtime_file, stop_file):
    args = list(argv[1:])
    while args and args[0] in {"-u", "-B"}:
        args.pop(0)
    if args[:2] == ["-X", "utf8"]:
        args = args[2:]
        while args and args[0] in {"-u", "-B"}:
            args.pop(0)
    if args and (args[0] == "-c" or args[0].casefold().endswith(".py")):
        return None  # An embedded/custom server is not a proved invocation mismatch.
    if args and args[0].startswith("-") and args[0] != "-m":
        return None
    if args[:2] != ["-m", "wakeup_native.codex_receiver"]:
        return False
    args = args[2:]
    options = {}
    while args:
        option, equal, value = args.pop(0).partition("=")
        if option not in {"--runtime-file", "--stop-file"} or option in options:
            return None
        if not equal:
            if not args:
                return None
            value = args.pop(0)
        options[option] = value
    if set(options) != {"--runtime-file", "--stop-file"}:
        return None
    if not stop_file:
        return None
    for option, expected in (("--runtime-file", runtime_file), ("--stop-file", stop_file)):
        supplied = options[option]
        if not os.path.isabs(supplied):
            return None
        if os.path.normcase(os.path.abspath(supplied)) == os.path.normcase(os.path.abspath(expected)):
            continue
        try:
            if not os.path.samefile(supplied, expected):
                return False
        except OSError:
            return None
    return True


def _windows_argv(pid):
    from ctypes import wintypes
    system_root = os.environ.get("SystemRoot")
    if not system_root:
        return None
    shell = Path(system_root) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = ("[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
              f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' -ErrorAction Stop; "
              "$p.CommandLine | ConvertTo-Json -Compress")
    result = subprocess.run([str(shell), "-NoProfile", "-NonInteractive", "-Command", script],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        return None
    command = json.loads(result.stdout.decode("utf-8-sig"))
    if not isinstance(command, str) or not command.strip():
        return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.CommandLineToArgvW.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int))
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel.LocalFree.argtypes = (wintypes.HLOCAL,)
    kernel.LocalFree.restype = wintypes.HLOCAL
    count = ctypes.c_int()
    pointer = shell32.CommandLineToArgvW(command, ctypes.byref(count))
    if not pointer:
        return None
    try:
        return [pointer[i] for i in range(count.value)]
    finally:
        kernel.LocalFree(pointer)


def _windows_snapshot(pid, runtime_file, stop_file):
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x101000, False, pid)  # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
    if not handle:
        return {"alive": False if ctypes.get_last_error() == 87 else None}
    try:
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                      ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return {"alive": None}
        identity = f"windows:{(created.dwHighDateTime << 32) | created.dwLowDateTime}"
        argv = _windows_argv(pid) if runtime_file else None
        state = kernel.WaitForSingleObject(handle, 0)
        if state not in {0, 258}:
            return {"alive": None}
        return {"alive": state == 258, "identity": identity,
                "invocation_matches": receiver_invocation(argv, runtime_file, stop_file) if argv is not None else None}
    finally:
        kernel.CloseHandle(handle)


def _linux_snapshot(pid, runtime_file, stop_file):
    proc = Path("/proc") / str(pid)
    def state():
        fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return fields[0], f"linux:{boot}:{fields[19]}"
    status, identity = state()
    argv = (proc / "cmdline").read_bytes().decode("utf-8").rstrip("\0").split("\0") if runtime_file else None
    final_status, final_identity = state()
    if identity != final_identity:
        return {"alive": None}
    return {"alive": final_status not in {"Z", "X", "x"}, "identity": identity,
            "invocation_matches": receiver_invocation(argv, runtime_file, stop_file) if argv is not None else None}


def process_snapshot(pid, runtime_file=None, stop_file=None):
    try:
        if os.name == "nt":
            return _windows_snapshot(pid, runtime_file, stop_file)
        if sys.platform.startswith("linux"):
            return _linux_snapshot(pid, runtime_file, stop_file)
        return {"alive": None}
    except FileNotFoundError:
        gone = os.name != "nt" and Path("/proc").is_dir() and not (Path("/proc") / str(pid)).exists()
        return {"alive": False if gone else None}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"alive": None}


def stop_windows_instance(pid, expected_identity):
    """Stop only the already-authorized instance, rechecking the same OS handle."""
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x101001, False, pid)  # QUERY | SYNCHRONIZE | TERMINATE
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        created, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                      ctypes.byref(kernel_time), ctypes.byref(user_time)):
            raise ctypes.WinError(ctypes.get_last_error())
        actual = f"windows:{(created.dwHighDateTime << 32) | created.dwLowDateTime}"
        if actual != expected_identity:
            raise ValueError("receiver_instance_changed_before_update")
        if not kernel.TerminateProcess(handle, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        if kernel.WaitForSingleObject(handle, 5000) != 0:
            raise OSError("receiver_exit_not_confirmed")
    finally:
        kernel.CloseHandle(handle)
