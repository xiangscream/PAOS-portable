#!/usr/bin/env python3
"""窄架构检查：只守机械边界（docs/planning/11-V05-NARROW-WRITE-CONTRACT.md §5）。

零依赖、范围很窄。这里**不检查**命名风格、函数长度、注释格式 —— 那些制造仪式感而不防
回归。反过来，事务语义（谁有权推进 revision、谁能 append Ledger）Ruff/ESLint 也查不出
来，所以只有自己写。

九条规则：

1. local_server.py / workflow_service.py 不得直接写项目文件
2. 两个 Agent 窄写适配器不得手工推进 revision / append Ledger / 写 operation receipts
3. 两个 Agent 窄写适配器必须经由 mutate_v2
4. 服务层不得用 store.root 猜目录、不得用 write_text() 写 Context Pack
5. Contracts 不得 import ProjectStore / WorkflowService / local_server
6. local_server.py 不得直接调用 _atomic_write 或直接写项目文件
7. project_store.py 不得 import session_workflow / work_workflow / coordination_workflow / local_server
8. context_compiler.py 不得 import HTTP 层，也不得引用 private-data 路径
9. scripts/paos.py 必须是 REST 薄客户端，不得 import Store/Workflow 或引用 private-data

规则只看文本，不做 import 与执行 —— 检查本身不能有副作用。
用法：python3 scripts/check_architecture.py（通过时静默退出 0）。
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "attention-dashboard-v1-static"

# 只有 project_store 自己可以写项目文件；服务层与 HTTP 层必须经由它。
SERVICE_LAYER = ("local_server.py", "workflow_service.py")

# 两个 Agent 窄写适配器（合同 §1.5：只做校验、描述 touched paths、生成业务结果）
NARROW_ADAPTERS = ("update_human_from_agent", "update_project_lists_from_agent")
# 它们的共同实现；规则 2/3 实际要检查的是这条路径。
NARROW_SHARED = "_narrow_agent_write"

# 项目文件写操作的痕迹。mkdir 不在其中：日志目录与 inbox 目录都合法要建目录，
# 把 mkdir 一律禁掉只会制造误报，而真正的危险是绕过 _atomic_write 写 JSON。
PROJECT_WRITE_MARKERS = (
    re.compile(r"\.write_text\s*\("),
    re.compile(r"\bos\.replace\s*\("),
    re.compile(r"\bjson\.dump\s*\("),
    re.compile(r"""\.open\s*\(\s*["']w"""),
)

# 适配器不得手工做的事（这些全部属于 mutate_v2）
MANUAL_TRANSACTION_MARKERS = (
    (re.compile(r"""\[\s*["']revision["']\s*\]\s*="""), "手工推进 revision"),
    (re.compile(r"""["']ledger["']\s*\]?\s*(?:,\s*\[\s*\]\s*)?\)?\.append"""), "手工 append Ledger"),
    (re.compile(r"""\[\s*["']operation_receipts["']\s*\]\s*(?:\[[^\]]*\]\s*)?="""), "手工写 operation receipts"),
    (re.compile(r"_atomic_write\s*\("), "直接调用 _atomic_write"),
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def function_source(tree: ast.Module, source: str, name: str) -> str | None:
    """取出某个函数的源码文本（含嵌套定义）。找不到返回 None。"""
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return None


def calls_in(tree: ast.Module, name: str) -> set[str]:
    """某个函数体内真实发生的方法调用名集合。

    用 AST 而不是文本搜索：注释与 docstring 里提到 "mutate_v2" 的地方很多
    （合同就写在注释里），按文本判断会让"其实没调用"也通过检查。
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            called: set[str] = set()
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Call):
                    continue
                func = inner.func
                if isinstance(func, ast.Attribute):
                    called.add(func.attr)
                elif isinstance(func, ast.Name):
                    called.add(func.id)
            return called
    return set()


def check_service_layer_does_not_write_projects(problems: list[str]) -> None:
    """规则 1：HTTP 层与服务层不得直接写项目文件。

    为什么：项目文件的每一次写入都必须带 revision、Ledger event 与 receipt。绕过
    project_store 直接落盘就绕过了这三样，事后无法审计，也无法幂等重试。
    """
    for filename in SERVICE_LAYER:
        path = APP_DIR / filename
        source = read(path)
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for marker in PROJECT_WRITE_MARKERS:
                if marker.search(line):
                    problems.append(
                        f"{filename}:{lineno} 直接写文件（{stripped[:70]}）；"
                        f"项目状态必须经由 project_store.mutate_v2 落盘。"
                    )


def check_narrow_adapters(problems: list[str]) -> None:
    """规则 2 与 3：两个窄写适配器不得自己管事务，必须经由 mutate_v2。"""
    path = APP_DIR / "project_store.py"
    source = read(path)
    tree = ast.parse(source)

    bodies = {}
    for name in (*NARROW_ADAPTERS, NARROW_SHARED):
        body = function_source(tree, source, name)
        if body is None:
            problems.append(
                f"project_store.py 找不到 {name}()；窄写入路径被改名或删除，"
                f"请同步更新本检查与 11-V05-NARROW-WRITE-CONTRACT.md。"
            )
            continue
        bodies[name] = body

    # 规则 3：适配器必须走 mutate_v2。用 AST 看真实调用：两个入口把活交给
    # _narrow_agent_write，所以它们调用它即算到达；共同实现自己必须真的调 mutate_v2。
    for name in NARROW_ADAPTERS:
        if name not in bodies:
            continue
        called = calls_in(tree, name)
        if "mutate_v2" not in called and NARROW_SHARED not in called:
            problems.append(
                f"project_store.py 的 {name}() 没有经由 mutate_v2；"
                f"幂等、自动 rebase 与结构化 409 会全部失效。"
            )

    # 规则 2：共同实现与两个入口都不得手工管事务。
    for name, body in bodies.items():
        for marker, label in MANUAL_TRANSACTION_MARKERS:
            if marker.search(body):
                problems.append(
                    f"project_store.py 的 {name}() {label}；这些属于 mutate_v2。"
                )

    if NARROW_SHARED in bodies and "mutate_v2" not in calls_in(tree, NARROW_SHARED):
        problems.append(
            f"project_store.py 的 {NARROW_SHARED}() 里没有真实的 mutate_v2 调用；"
            f"注释里提到不算 —— 窄写入必须实际经过统一原子入口。"
        )


def check_service_layer_does_not_guess_paths(problems: list[str]) -> None:
    """规则 4：服务层不得用 store.root 猜目录，Context Pack 只能经原子写入口。

    为什么：路径推断点必须唯一（project_store.context_pack_path）。多处各自拼路径时，
    改布局就会漏掉其中一处，而漏掉的那处会静默写到旧位置。
    """
    for filename in SERVICE_LAYER:
        path = APP_DIR / filename
        source = read(path)
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r"\bstore\.root\b|\bself\.store\.root\b", line):
                problems.append(
                    f"{filename}:{lineno} 用 store.root 猜目录；"
                    f"路径推断必须留在 project_store 里（唯一推断点）。"
                )
            if "context_pack" in line.lower() and ".write_text" in line:
                problems.append(
                    f"{filename}:{lineno} 用 write_text 写 Context Pack；"
                    f"必须走 project_store.write_context_pack_atomic()。"
                )


# HIS-Q6 新增的四条窄架构边界：让“未来跑 verify 的 Agent”能在不读完全部源码的
# 情况下识别出“这层越权了”的结构性破坏。

CONTRACT_FILES = (
    "session_contracts.py",
    "coordination_contracts.py",
    "project_contracts.py",
)

FORBIDDEN_CONTRACT_IMPORTS = ("project_store", "workflow_service", "local_server")
STORE_FORBIDDEN_IMPORTS = (
    "session_workflow",
    "coordination_workflow",
    "local_server",
)


def _top_level_import_modules(source: str, path: Path) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    modules: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    return modules


def check_contracts_do_not_import_runtime(problems: list[str]) -> None:
    """规则 5：Contracts 只能做校验，不得依赖 Store/Workflow/HTTP。"""
    for filename in CONTRACT_FILES:
        path = APP_DIR / filename
        source = read(path)
        for module in _top_level_import_modules(source, path):
            if module in FORBIDDEN_CONTRACT_IMPORTS:
                problems.append(
                    f"{filename} import 了运行时模块 {module}；"
                    f"合同层不得依赖 ProjectStore/WorkflowService/local_server。"
                )


def check_local_server_no_atomic_write(problems: list[str]) -> None:
    """规则 6：HTTP Adapter 不得绕过 mutate_v2 直接落账。"""
    source = read(APP_DIR / "local_server.py")
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"\b_atomic_write\s*\(", line):
            problems.append(
                f"local_server.py:{lineno} 直接调用 _atomic_write；"
                f"HTTP Adapter 必须经由 WorkflowService，不能绕过它落账。"
            )


def check_store_does_not_import_workflows(problems: list[str]) -> None:
    """规则 7：Store 永远不知道 Workflow。"""
    source = read(APP_DIR / "project_store.py")
    for module in _top_level_import_modules(source, APP_DIR / "project_store.py"):
        if module in STORE_FORBIDDEN_IMPORTS:
            problems.append(
                f"project_store.py import 了 workflow/HTTP 模块 {module}；"
                f"Store 永远不知道 Workflow。"
            )


def check_context_compiler_boundary(problems: list[str]) -> None:
    """规则 8：Prompt 只读投影，不依赖 HTTP，也不直接引用私有数据路径。"""
    path = APP_DIR / "context_compiler.py"
    source = read(path)
    for module in _top_level_import_modules(source, path):
        if module == "local_server":
            problems.append(
                "context_compiler.py import 了 local_server；"
                "Prompt 渲染层不得依赖 HTTP Adapter。"
            )
    for lineno, line in enumerate(source.splitlines(), start=1):
        if "private-data" in line:
            problems.append(
                f"context_compiler.py:{lineno} 引用了 private-data 路径；"
                "Prompt 渲染层只持有引用，不得直接读取私有数据。"
            )



def check_paos_cli_boundary(problems: list[str]) -> None:
    """规则 9：CLI 只能通过 HTTP，不得绕过 REST 直接碰领域运行时/私有数据。"""
    path = REPO_ROOT / "scripts" / "paos.py"
    if not path.exists():
        problems.append("scripts/paos.py 不存在；Agent-friendly REST CLI 缺失。")
        return
    source = read(path)
    forbidden_modules = {
        "project_store", "workflow_service", "session_workflow", "work_workflow",
        "coordination_workflow", "local_server",
    }
    for module in _top_level_import_modules(source, path):
        if module in forbidden_modules:
            problems.append(f"scripts/paos.py import 了 {module}；CLI 必须只走 REST。")
    for lineno, line in enumerate(source.splitlines(), start=1):
        if "private-data" in line:
            problems.append(f"scripts/paos.py:{lineno} 引用了 private-data；CLI 不得直接读取私有状态。")
        if "_atomic_write" in line or ".mutate_v2(" in line:
            problems.append(f"scripts/paos.py:{lineno} 绕过 HTTP 写状态；CLI 必须只走 REST。")


def main() -> int:
    problems: list[str] = []
    check_service_layer_does_not_write_projects(problems)
    check_narrow_adapters(problems)
    check_service_layer_does_not_guess_paths(problems)
    check_contracts_do_not_import_runtime(problems)
    check_local_server_no_atomic_write(problems)
    check_store_does_not_import_workflows(problems)
    check_context_compiler_boundary(problems)
    check_paos_cli_boundary(problems)

    if problems:
        print("架构检查失败：")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("架构检查通过（9 条机械边界）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
