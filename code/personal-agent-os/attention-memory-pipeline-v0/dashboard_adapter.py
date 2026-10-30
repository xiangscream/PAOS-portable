from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DASHBOARD_SCHEMA = "attention-dashboard-data/v0"


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def adapt_task(task: dict[str, Any]) -> dict[str, Any]:
    source_ref = task["source_refs"][0]
    return {
        "id": task["id"],
        "title": task["title"],
        "domain": task["domain"],
        "domainCode": task["domain_code"],
        "project": task["project"],
        "thread": task["thread"],
        "status": task["status"],
        "kind": "task",
        "summary": task["summary"],
        "currentQuestion": task.get("current_question", ""),
        "deliverable": task.get("deliverable", ""),
        "doneWhen": task.get("done_when", ""),
        "source": source_ref["path"],
        "sourceRefs": task["source_refs"],
        "sensitivity": task["sensitivity"],
        "reviewState": task["review_state"],
        "blocking": task["blocking"],
        "externalCommitment": task["external_commitment"],
        "longTerm": task["long_term"],
        "dueAt": task["due_at"],
        "lastProgressAt": task["last_progress_at"],
        "weeklyTarget": task["weekly_target"],
        "weeklyProgress": task["weekly_progress"],
        "context": task["context"],
    }


def adapt_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": candidate["id"],
        "candidateType": candidate["candidate_type"],
        "status": "candidate",
        "title": candidate_title(candidate["candidate_type"], candidate["project"]),
        "summary": candidate["reason"],
        "domain": candidate["domain"],
        "domainCode": candidate["domain_code"],
        "project": candidate["project"],
        "sourceRefs": candidate["source_refs"],
        "details": candidate["details"],
    }


def candidate_title(candidate_type: str, project: str) -> str:
    labels = {
        "conflict": "发现相互冲突的未失效决策",
        "duplicate": "发现可能重复的记忆对象",
        "progress_debt": "长期项目存在推进债务",
        "scope_missing": "对象缺少明确项目作用域",
        "source_declared_candidate": "来源声明仍待人工审核",
        "overdue": "活动任务已经超过截止时间",
    }
    return f"{project} · {labels.get(candidate_type, candidate_type)}"


def adapt_archive(archive: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": archive["id"],
        "title": archive["title"],
        "domain": archive["domain"],
        "domainCode": archive["domain_code"],
        "project": archive["project"],
        "status": archive["status"],
        "epitaph": archive["epitaph"],
        "whyStopped": archive["why_stopped"],
        "reusable": archive["reusable"],
        "restartWhen": archive["restart_when"],
        "firstHour": archive["first_hour"],
        "sourceRefs": archive["source_refs"],
    }


def priority_tuple(item: dict[str, Any], now: datetime) -> tuple[Any, ...]:
    if item["blocking"]:
        return (0, due_timestamp(item), item["title"])

    due_at = parse_datetime(item["dueAt"])
    if due_at:
        hours_until_due = (due_at - now).total_seconds() / 3600
        if hours_until_due <= 48:
            return (1, due_at.timestamp(), item["title"])
        if hours_until_due <= 7 * 24:
            return (2, due_at.timestamp(), item["title"])

    if item["externalCommitment"]:
        return (2, due_timestamp(item), item["title"])

    last_progress = parse_datetime(item["lastProgressAt"])
    debt_days = (now - last_progress).days if last_progress else 0
    weekly_debt = (item["weeklyTarget"] or 0) > (item["weeklyProgress"] or 0)
    if item["longTerm"] and (debt_days >= 7 or weekly_debt):
        return (3, -debt_days, item["title"])

    return (4, due_timestamp(item), item["title"])


def due_timestamp(item: dict[str, Any]) -> float:
    due_at = parse_datetime(item.get("dueAt"))
    return due_at.timestamp() if due_at else float("inf")


def rank_items(
    items: list[dict[str, Any]],
    now: datetime,
    completed_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    completed = set(completed_ids or [])
    return sorted(
        [
            item
            for item in items
            if item["status"] == "active" and item["id"] not in completed
        ],
        key=lambda item: priority_tuple(item, now),
    )


def adapt_state(
    state: dict[str, Any], now: datetime
) -> dict[str, Any]:
    items = [adapt_task(task) for task in state["tasks"]]
    ranked = rank_items(items, now)
    return {
        "schema": DASHBOARD_SCHEMA,
        "generatedAt": state["generated_at"],
        "referenceNow": now.isoformat(),
        "dataScope": state["data_scope"],
        "items": items,
        "defaultTopThree": [item["id"] for item in ranked[:3]],
        "nightCandidates": [
            adapt_candidate(candidate) for candidate in state["review_candidates"]
        ],
        "archives": [adapt_archive(archive) for archive in state["archives"]],
        "sourceSummary": state["scan_summary"],
        "changes": state["changes"],
        "warnings": state["warnings"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="把 attention-state/v0 转换成 Dashboard 数据契约。"
    )
    parser.add_argument(
        "--input", type=Path, default=Path("build/attention-state.json")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("build/dashboard-data.json")
    )
    parser.add_argument(
        "--now", default="2026-07-29T09:00:00+08:00"
    )
    args = parser.parse_args()

    state = json.loads(args.input.read_text(encoding="utf-8"))
    if state.get("schema") != "attention-state/v0":
        raise ValueError("输入必须是 attention-state/v0")
    now = parse_datetime(args.now)
    if now is None:
        raise ValueError("--now 必须是合法 ISO 8601 时间")
    dashboard = adapt_state(state, now)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "schema": dashboard["schema"],
            "items": len(dashboard["items"]),
            "nightCandidates": len(dashboard["nightCandidates"]),
            "archives": len(dashboard["archives"]),
            "defaultTopThree": dashboard["defaultTopThree"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

