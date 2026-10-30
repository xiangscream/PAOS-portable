#!/usr/bin/env python3
"""Cross-platform one-shot verify for Personal Agent OS.

Usage:
  python scripts/verify.py
  # or on Windows:
  .\\scripts\\verify.ps1

Runs seven gates:
  [1/7] Architecture
  [2/7] Python tests
  [3/7] Derived data
  [4/7] Node tests (TZ=UTC)
  [5/7] Node tests (TZ=Asia/Shanghai)
  [6/7] Python compileall
  [7/7] JS node --check

Writes nothing except test-generated build caches. PAOS_NODE / PAOS_PYTHON
environment variables override the runtime lookups used by PowerShell users.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "attention-dashboard-v1-static"
PIPELINE = ROOT / "attention-memory-pipeline-v0"
ADAPTERS = ROOT / "runtime_adapters"


def _usable_path(value: str) -> bool:
    if os.name == "nt":
        return os.path.isfile(value) or shutil.which(value) is not None
    return os.path.isfile(value) and os.access(value, os.X_OK)


def python_exe() -> str:
    value = os.environ.get("PAOS_PYTHON")
    if value and _usable_path(value):
        return value
    return sys.executable


def node_exe() -> str:
    value = os.environ.get("PAOS_NODE")
    if value and _usable_path(value):
        return value
    found = shutil.which("node")
    if found:
        return found
    sys.stderr.write("FAIL: Node 未找到；请设置 PAOS_NODE。\n")
    raise SystemExit(1)


def run(cmd, *, cwd=None, env=None):
    full_env = os.environ.copy()
    full_env.setdefault("PYTHONIOENCODING", "utf-8")
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=full_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def parse_unittest(output: str):
    """Return (tests, ok)."""
    match = re.search(r"Ran (\d+) tests", output)
    tests = int(match.group(1)) if match else 0
    ok = "OK" in output and "FAILED" not in output
    return tests, ok


def parse_node_tap(output: str):
    """Return (passed, failed) from Node TAP summary lines.

    Node 22 prints `# pass N`; Node 24 prints `ℹ pass N`. Accept both.
    """
    passed = 0
    failed = 0
    for raw in output.splitlines():
        line = raw.strip()
        line = line.removeprefix("# ").removeprefix("ℹ ")
        m = re.match(r"pass (\d+)", line)
        if m:
            passed += int(m.group(1))
        m = re.match(r"fail (\d+)", line)
        if m:
            failed += int(m.group(1))
    return passed, failed


def check_architecture():
    script = ROOT / "scripts" / "check_architecture.py"
    proc = run([python_exe(), str(script)])
    ok = proc.returncode == 0
    return ok, proc.stdout.strip() or ("(no output)" if ok else "(no output)")


def python_tests():
    commands = [
        ("pipeline", PIPELINE),
        ("app", APP),
    ]
    total = 0
    all_ok = True
    for _name, cwd in commands:
        proc = run(
            [python_exe(), "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            cwd=cwd,
        )
        tests, ok = parse_unittest(proc.stdout or "")
        total += tests
        all_ok = all_ok and ok and proc.returncode == 0
    return all_ok, total


def ensure_derived_data():
    """Build data is git-ignored but required by the Dashboard Node test.

    Old verify.ps1 ran this before the Dashboard suite. The helper only
    generates build/ when the whole build/ directory is absent; it never
    overwrites an existing build (zero-overwrite contract).
    """
    script = ROOT / "scripts" / "ensure_build_data.py"
    proc = run([python_exe(), str(script)], cwd=ROOT)
    ok = proc.returncode == 0
    stdout = (proc.stdout or "").strip()
    detail = stdout.splitlines()[0] if stdout else "FAIL (no output)"
    return ok, detail


def node_tests(tz):
    files = sorted((APP / "tests").glob("*.test.mjs"))
    if not files:
        return False, 0
    total_pass = 0
    total_fail = 0
    all_ok = True
    for file in files:
        proc = run([node_exe(), "--test", str(file)], cwd=APP, env={"TZ": tz})
        passed, failed = parse_node_tap(proc.stdout or "")
        total_pass += passed
        total_fail += failed
        all_ok = all_ok and proc.returncode == 0 and failed == 0
    return all_ok, total_pass


def compileall():
    proc = run([
        python_exe(),
        "-m",
        "compileall",
        "-q",
        str(APP),
        str(PIPELINE),
        str(ADAPTERS),
    ])
    return proc.returncode == 0


def js_check():
    files = sorted(APP.glob("*.mjs")) + sorted((APP / "tests").glob("*.mjs"))
    all_ok = True
    for file in files:
        proc = run([node_exe(), "--check", str(file)], cwd=APP)
        all_ok = all_ok and proc.returncode == 0
    return all_ok


def report(label, ok, detail):
    mark = "PASS" if ok else "FAIL"
    print(f"{label} ........ {mark} {detail}")


def main() -> int:
    python = python_exe()
    node = node_exe()
    print(f"PAOS verify (python={python}, node={node})")

    arch_ok, arch_detail = check_architecture()
    report("[1/7] Architecture", arch_ok, arch_detail.splitlines()[0] if arch_detail else "PASS")

    py_ok, py_tests = python_tests()
    report("[2/7] Python tests", py_ok, f"{py_tests} tests")

    derived_ok, derived_detail = ensure_derived_data()
    report("[3/7] Derived data", derived_ok, derived_detail)

    node_utc_ok, node_utc = node_tests("UTC")
    report("[4/7] Node UTC", node_utc_ok, f"{node_utc} pass")

    node_sh_ok, node_sh = node_tests("Asia/Shanghai")
    report("[5/7] Node Asia/Shanghai", node_sh_ok, f"{node_sh} pass")

    comp_ok = compileall()
    report("[6/7] Python compileall", comp_ok, "PASS" if comp_ok else "FAIL")

    js_ok = js_check()
    report("[7/7] JS node --check", js_ok, "PASS" if js_ok else "FAIL")

    ok = all([arch_ok, py_ok, derived_ok, node_utc_ok, node_sh_ok, comp_ok, js_ok])
    print("========================================")
    print(" 结果: PASS (7/7)" if ok else " 结果: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
