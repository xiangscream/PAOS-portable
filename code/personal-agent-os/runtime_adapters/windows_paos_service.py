"""Long-running Task Scheduler action for Core or the Windows WSL bridge."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


def bind_host_to_job() -> int:
    """Own this host and its future children until Windows closes our job handle."""
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in
            ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
             "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int,
        ctypes.c_void_p, wintypes.DWORD)
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = ()
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    # NULL security attributes make this unnamed handle non-inheritable.
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        error = ctypes.get_last_error()
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        error = ctypes.get_last_error()
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    # Keep the handle open for the host's entire process lifetime. Closing it here
    # would also terminate this host. All future Popen children inherit job membership,
    # not the handle; host exit (including Task Scheduler Stop) closes the last handle.
    return job


def serve(role: str, installation_file: Path) -> int:
    installation = json.loads(installation_file.read_text(encoding="utf-8"))
    if installation["schema"] != "paos-installation/v1":
        raise ValueError("Expected paos-installation/v1")
    source = Path(installation["source_root"])
    data_root = str(installation.get("data_root") or "").strip()
    if not data_root:
        raise ValueError("Installation descriptor is missing data_root")
    data_path = Path(data_root)
    if not data_path.is_absolute():
        raise ValueError("Installation data_root must be absolute")
    if not data_path.is_dir():
        raise ValueError("Installation data_root does not exist")
    python = Path(sys.executable).with_name("python.exe")
    logs = data_path / "logs" / "windows-services"
    logs.mkdir(parents=True, exist_ok=True)

    def record(event: str, **fields) -> None:
        with (logs / f"{role}.lifecycle.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                "event": event, "role": role, "host_pid": os.getpid(),
                "host_ppid": os.getppid(), "source_root": str(source), **fields}) + "\n")

    with (logs / f"{role}.stdout.log").open("ab") as stdout, \
            (logs / f"{role}.stderr.log").open("ab") as stderr:
        # pythonw has no console. Preserve startup failures and tracebacks too.
        sys.stderr = open(logs / f"{role}.host-errors.log", "a", encoding="utf-8")
        record("host_started")
        job_handle = bind_host_to_job()
        record("job_bound", kill_on_close=True)
        if role == "core":
            command = [str(python), "-X", "utf8", "-u",
                "attention-dashboard-v1-static/paos_server.py", "--port", "8766",
                "--installation-file", str(installation_file)]
        else:
            query = ("Get-NetIPAddress -AddressFamily IPv4 | "
                "Where-Object { $_.InterfaceAlias -like '*WSL*' } | "
                "Select-Object -First 1 -ExpandProperty IPAddress")
            address = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                "-Command", query], check=True, capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
            if not address:
                raise RuntimeError("WSL network interface absent; start bridge after WSL is available")
            command = [str(python), "-X", "utf8", "-u", "-m",
                "runtime_adapters.windows_wsl_paos_bridge", "--listen-host", address,
                "--listen-port", "8766", "--target-port", "8766"]
        child = subprocess.Popen(command, cwd=source, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        record("child_started", child_pid=child.pid)
        exit_code = child.wait()
        record("child_exited", child_pid=child.pid, exit_code=exit_code)
        return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=("core", "bridge"))
    parser.add_argument("--installation-file", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(serve(args.role, args.installation_file))
