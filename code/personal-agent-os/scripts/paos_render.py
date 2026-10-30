"""展示层：把结果 dict 渲染为人类可读文本。

从 paos.py 提取，纯函数、无业务依赖，仅做 result.get 与字符串拼接。
"""
from typing import Any


def render_workbench(result: dict[str, Any]) -> str:
    lines = [
        f"工作台：{result.get('root', '')}",
        "页面：" + " / ".join(f"{key}={value}" for key, value in sorted((result.get('counts') or {}).items())),
    ]
    for row in result.get("conflicts") or []:
        lines.append(f"冲突保留：{row.get('page')} ({row.get('reason', '')})")
    for row in result.get("missing") or []:
        lines.append(f"未生成：{row.get('page')} ({row.get('reason', row.get('status'))})")
    lines.append("只读源事实；生成页可重建，人工修改保留为冲突。")
    return "\n".join(lines)


def render_program_rollback(result: dict[str, Any]) -> str:
    if result.get("apply"):
        return (
            f"程序回退已应用：{result.get('previous_source')} → {result.get('source_root')}\n"
            f"数据根保持：{result.get('data_root')}\n"
            f"描述备份：{result.get('descriptor_backup')}\n"
            "运行中服务需按正常重载才能加载新代码。"
        )
    lines = [
        f"当前 Source：{result.get('current_source')} ({result.get('current_revision') or 'unknown'})",
        f"目标 Source：{result.get('target_source')} ({result.get('target_revision') or 'unknown'})",
        f"数据根保持：{result.get('data_root')}",
        f"兼容声明：{'已提供' if result.get('ready') else result.get('reason')}",
        "只读预览；执行需 --apply 与 --compatibility-file，且无活动 writer。",
    ]
    return "\n".join(lines)


def render_install_plan(plan: dict[str, Any]) -> str:
    inst = plan.get("installation") or {}
    versions = plan.get("versions") or {}
    own = plan.get("ownership") or {}
    diff = plan.get("upgrade") or {}
    lines = [
        f"安装：{inst.get('descriptor', '')}",
        f"程序根：{inst.get('source_root', '')}",
        f"数据根：{inst.get('data_root', '')}",
        f"Source：{versions.get('source', {}).get('revision') or 'unknown'}",
        f"CLI：{versions.get('running_cli', {}).get('revision') or 'unknown'}",
        f"Core：{versions.get('core', {}).get('state', 'unknown')}",
        f"受管文件：{own.get('managed_count')}（{own.get('managed_state')}）",
    ]
    if diff.get("state") == "computed":
        lines.append(
            "升级差分：新增 {a} / 替换 {r} / 退出 {d}".format(
                a=diff.get("added_count", 0), r=diff.get("replaced_count", 0),
                d=diff.get("removed_count", 0),
            )
        )
    elif diff.get("state") == "unknown":
        lines.append("升级差分：未知（Source 不是可读 git 工作树）")
    if (plan.get("retire") or {}).get("requested"):
        lines.append("退出预览：已生成（只读，不执行）")
    lines.append("")
    lines.append("只读计划；不写安装、不停止服务、不删除文件。")
    return "\n".join(lines)


def render_install_homes(coverage: dict[str, Any]) -> str:
    scope = coverage.get("scope") or {}
    total = scope.get("total") or {}
    summary = coverage.get("summary") or {}
    support = summary.get("support") or {}
    lines = [
        "安装登记：Project {p} / Project Agent {a} / Rooter {r} / 身份 {i}".format(
            p=total.get("projects", 0), a=total.get("project_agents", 0),
            r=total.get("rooter", 0), i=total.get("identities", 0),
        ),
        "Home：存在 {a} / 缺失 {b} / 不可定位 {c}".format(
            a=summary.get("home_present", 0), b=summary.get("home_missing", 0),
            c=summary.get("home_unlocatable", 0),
        ),
        "联系包：absent {a} / partial {p} / matching {m} / modified {x} / unavailable {u}".format(
            a=(summary.get("contact_status") or {}).get("absent", 0),
            p=(summary.get("contact_status") or {}).get("partial", 0),
            m=(summary.get("contact_status") or {}).get("matching", 0),
            x=(summary.get("contact_status") or {}).get("modified", 0),
            u=(summary.get("contact_status") or {}).get("unavailable", 0),
        ),
        "直接提醒支持：conditional {c} / manual {m} / unsupported {u} / 未分类 {n}（automatic 0）".format(
            c=support.get("conditional", 0), m=support.get("manual", 0),
            u=support.get("unsupported", 0), n=summary.get("unclassified", 0),
        ),
        "",
        "kind        project  home              Home   联系包      支持            STOP",
    ]
    for row in coverage.get("homes") or []:
        lines.append("{kind:<11} {pid:<8} {hid:<17} {home:<6} {pack:<11} {cls:<15} {stop}".format(
            kind=row.get("home_kind", ""), pid=row.get("project_id") or "-",
            hid=row.get("home_id", ""), home=row.get("home", {}).get("state", ""),
            pack=row.get("contact_package", {}).get("status", ""),
            cls=row.get("contact", {}).get("classification") or "unclassified",
            stop=row.get("contact", {}).get("stop", ""),
        ))
    lines.append("")
    lines.append("只读观察；native_reachability=not_observed；业务接受未判定。")
    return "\n".join(lines)


def render_authority(authority: dict[str, Any], allowed_only: bool) -> str:
    lines = []
    for action in authority.get("actions", []):
        allowed = bool(action.get("allowed", True))
        if allowed_only and not allowed:
            continue
        prefix = "ALLOW" if allowed else "DENY "
        lines.append(
            f"{prefix} {action.get('action_id')}  "
            f"{action.get('method')} {action.get('path')}"
        )
    return "\n".join(lines)
