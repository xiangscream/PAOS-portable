#!/usr/bin/env python3
"""Lightweight structural lint for Markdown PRDs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


SECTION_GROUPS = {
    "document_control": ("更新记录", "变更记录", "文档控制", "版本记录"),
    "background": ("背景", "问题", "现状", "项目背景"),
    "definition": ("产品定义", "产品定位", "执行摘要", "一句话"),
    "users": ("用户", "场景", "角色", "用户旅程"),
    "goals": ("目标", "成功指标", "衡量指标"),
    "scope": ("范围", "非目标", "不做", "版本边界"),
    "requirements": ("需求", "功能规格", "详细功能"),
    "acceptance": ("验收", "测试标准", "完成标准"),
    "open_questions": ("开放问题", "待确认", "风险", "依赖"),
}

REQUIREMENT_ID = re.compile(
    r"\b(?:REQ|FR|NFR|HW|SW|AI)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b", re.IGNORECASE
)
TBD = re.compile(r"\bTBD\b|\bTODO\b|\bUNKNOWN\b|待定|待确认|待补充", re.IGNORECASE)
OWNER = re.compile(r"负责人|决策人|owner|@\S+", re.IGNORECASE)
DATE = re.compile(
    r"\b20\d{2}[-/.年]\d{1,2}(?:[-/.月]\d{1,2}日?)?\b|\bDDL\b|截止日期",
    re.IGNORECASE,
)
VAGUE = re.compile(
    r"快速|稳定|流畅|友好|智能|高性能|低延迟|轻量|极致|准确|及时|尽快|良好体验"
)
OBSERVABLE = re.compile(
    r"\d|默认|范围|枚举|开启|关闭|显示|提示|保存|恢复|失败|成功|超时|重试|"
    r"不支持|禁止|允许|P\d|Given|When|Then|AC\d",
    re.IGNORECASE,
)


def headings(text: str) -> list[str]:
    return [
        match.group(2).strip()
        for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text)
    ]


def make_issue(level: str, code: str, message: str, line: int | None = None) -> dict:
    issue = {"level": level, "code": code, "message": message}
    if line is not None:
        issue["line"] = line
    return issue


def lint(text: str) -> dict:
    issues: list[dict] = []
    doc_headings = headings(text)
    heading_blob = "\n".join(doc_headings).lower()

    for key, aliases in SECTION_GROUPS.items():
        if not any(alias.lower() in heading_blob for alias in aliases):
            level = "error" if key in {"requirements", "acceptance"} else "warning"
            issues.append(
                make_issue(
                    level,
                    f"missing_{key}",
                    f"未找到章节：{' / '.join(aliases)}",
                )
            )

    ids = [item.upper() for item in REQUIREMENT_ID.findall(text)]
    for req_id, count in Counter(ids).items():
        if count > 2:
            issues.append(
                make_issue(
                    "warning",
                    "frequent_requirement_id",
                    f"需求 ID {req_id} 出现 {count} 次；确认是否只是总表与正文引用。",
                )
            )

    lines = text.splitlines()
    for number, line in enumerate(lines, start=1):
        if TBD.search(line):
            context = " ".join(lines[max(0, number - 2) : min(len(lines), number + 2)])
            missing = []
            if not OWNER.search(context):
                missing.append("负责人/决策人")
            if not DATE.search(context):
                missing.append("截止日期")
            if missing:
                issues.append(
                    make_issue(
                        "warning",
                        "unowned_tbd",
                        f"待确认项缺少{'、'.join(missing)}：{line.strip()[:100]}",
                        number,
                    )
                )

        stripped = line.strip()
        is_requirement_like = (
            stripped.startswith(("-", "*", "|"))
            or bool(REQUIREMENT_ID.search(stripped))
            or stripped.startswith(("系统应", "设备应", "用户可", "支持"))
        )
        if is_requirement_like and VAGUE.search(stripped) and not OBSERVABLE.search(stripped):
            issues.append(
                make_issue(
                    "warning",
                    "vague_requirement",
                    f"可能不可验收的模糊表述：{stripped[:120]}",
                    number,
                )
            )

    acceptance_mentions = len(re.findall(r"验收标准|Given|When|Then|\bAC\d+\b", text, re.I))
    if ids and acceptance_mentions == 0:
        issues.append(
            make_issue(
                "error",
                "no_acceptance_coverage",
                "文档包含需求 ID，但未发现验收标准或 AC/Given-When-Then。",
            )
        )

    if len(ids) >= 5 and len(set(ids)) == 1:
        issues.append(
            make_issue(
                "warning",
                "low_id_coverage",
                "文档较长但只有一个唯一需求 ID；检查是否需要拆成原子需求。",
            )
        )

    errors = sum(issue["level"] == "error" for issue in issues)
    warnings = sum(issue["level"] == "warning" for issue in issues)
    return {
        "ok": errors == 0,
        "summary": {
            "errors": errors,
            "warnings": warnings,
            "headings": len(doc_headings),
            "requirement_ids": len(set(ids)),
        },
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a Markdown PRD for common gaps.")
    parser.add_argument("file", type=Path, help="Path to a Markdown PRD")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    try:
        text = args.file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2

    result = lint(text)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary = result["summary"]
        print(
            f"PRD lint: {summary['errors']} error(s), "
            f"{summary['warnings']} warning(s), "
            f"{summary['requirement_ids']} unique requirement ID(s)"
        )
        for issue in result["issues"]:
            location = f" line {issue['line']}" if "line" in issue else ""
            print(f"[{issue['level'].upper()}] {issue['code']}{location}: {issue['message']}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
