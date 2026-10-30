#!/usr/bin/env python3
"""Advisory mechanical linter for clean professional writing.

This tool flags signals that deserve semantic review. It never auto-edits and
no flagged word is automatically wrong.

Limitation: the SIGNALS patterns below currently target Chinese text. This is a
starting, per-language signal set, not a language-complete checker. A language
with no matching patterns simply produces no signals from this script; that
absence is not a correctness verdict. Semantic review always has priority.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Finding:
    kind: str
    line: int
    excerpt: str
    note: str


SIGNALS = {
    "version_or_process": [
        r"上一版", r"本轮", r"这一轮", r"之前版本", r"原方案", r"原先", r"后来", r"经过.*讨论",
        r"讨论后", r"本次迭代", r"前期调研", r"经过.*研究", r"我们先", r"我们再",
    ],
    "author_meta": [
        r"本节.*(介绍|说明|讨论|讲)", r"下面.*(介绍|说明|讨论|讲)", r"这里.*(介绍|说明|讨论|讲)",
        r"本文.*(介绍|说明|讨论)", r"接下来.*(介绍|说明|讨论)",
    ],
    "defensive_or_audit": [
        r"为了.*佐证", r"进一步.*验证", r"充分.*证明", r"强有力.*证据", r"经过.*交叉验证",
        r"值得注意的是", r"需要注意的是", r"从.*角度来看", r"综合来看", r"总体而言",
    ],
    "hedging_stack": [
        r"可能.*潜在", r"可能.*一定程度", r"或许.*可能", r"预计.*可能", r"可能.*有望",
    ],
    "marketing_adjective": [
        r"无缝", r"强大", r"领先", r"创新性", r"革命性", r"全方位", r"极致", r"卓越", r"智能化体验",
    ],
}

SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])")
HEADING = re.compile(r"^(#{1,6})\s+\S")


def compact(text: str, limit: int = 96) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def lint(text: str, long_sentence_chars: int = 80, micro_section_chars: int = 90) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        for kind, patterns in SIGNALS.items():
            for pattern in patterns:
                if re.search(pattern, stripped, flags=re.I):
                    findings.append(
                        Finding(
                            kind=kind,
                            line=lineno,
                            excerpt=compact(stripped),
                            note="Signal only: decide semantically whether this belongs in the selected language mode.",
                        )
                    )
                    break

        if not HEADING.match(stripped) and not stripped.startswith("|"):
            for sentence in SENTENCE_SPLIT.split(stripped):
                content = re.sub(r"[\s`*_>#\-]", "", sentence)
                if len(content) > long_sentence_chars:
                    findings.append(
                        Finding(
                            kind="long_sentence",
                            line=lineno,
                            excerpt=compact(sentence),
                            note=f"Sentence is over {long_sentence_chars} non-formatting characters; check for multiple independent claims.",
                        )
                    )

    # Flag very small Markdown sections as possible fragmentation.
    heading_indices = [i for i, line in enumerate(lines) if HEADING.match(line.strip())]
    for pos, start in enumerate(heading_indices):
        end = heading_indices[pos + 1] if pos + 1 < len(heading_indices) else len(lines)
        body = "".join(line.strip() for line in lines[start + 1 : end] if line.strip())
        body = re.sub(r"[`*_>#|\-]", "", body)
        if 0 < len(body) < micro_section_chars:
            findings.append(
                Finding(
                    kind="micro_section",
                    line=start + 1,
                    excerpt=compact(lines[start].strip()),
                    note=f"Section body is under {micro_section_chars} characters; consider merging unless the heading aids navigation.",
                )
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Flag mechanical clean-writing risk signals.")
    parser.add_argument("path", type=Path, help="UTF-8 text or Markdown file")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON")
    parser.add_argument("--long-sentence", type=int, default=80, help="Long-sentence character threshold")
    parser.add_argument("--micro-section", type=int, default=90, help="Micro-section body threshold")
    args = parser.parse_args()

    text = args.path.read_text(encoding="utf-8")
    findings = lint(text, args.long_sentence, args.micro_section)

    if args.as_json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("No mechanical risk signals found. Semantic review is still required.")
            return 0
        for finding in findings:
            print(f"[{finding.kind}] line {finding.line}: {finding.excerpt}")
            print(f"  {finding.note}")
        print(f"\n{len(findings)} finding(s). These are review signals, not automatic violations.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
