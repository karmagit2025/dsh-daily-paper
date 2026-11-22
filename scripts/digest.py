#!/usr/bin/env python3
"""
把某一天的 UP 日报渲染成飞书 Markdown 摘要（整份，不只是 B站）。

    python3 digest.py --date 2026-11-14 --output /tmp/up_daily.md

输出按栏目顺序展开：导语 → 每个 section 的 note + 条目（标题、作者、要点、可执行、原链接）。
"""

import argparse
import json
import os

ISSUES = os.path.expanduser("~/DSH-work/daily-paper/issues")


def load(date):
    path = os.path.join(ISSUES, f"{date}.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def render(issue):
    lines = [f"**UP 日报 · {issue.get('date', '')}**"]
    lead = (issue.get("lead") or "").strip()
    if lead:
        lines += ["", lead]

    sections = issue.get("sections") or []
    for index, section in enumerate(sections):
        label = section.get("label") or section.get("source") or "未分类"
        items = section.get("items") or []
        lines += ["", f"**{index + 1:02d} · {label} · {len(items)} 篇**"]
        note = (section.get("note") or "").strip()
        if note:
            lines.append(f"_{note}_")
        for item in items:
            title = (item.get("title") or "(无标题)").strip()
            meta = " · ".join(str(x) for x in [
                item.get("author"),
                item.get("topic"),
                item.get("duration"),
            ] if x)
            lines += ["", f"**{title}**" + (f"  \n{meta}" if meta else "")]
            for point in (item.get("summary") or []):
                lines.append(f"- {point}")
            for todo in (item.get("todo") or []):
                lines.append(f"- ✅ {todo}")
            url = item.get("url")
            if url:
                lines.append(f"🔗 {url}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", "-o", default="/tmp/up_daily.md")
    parser.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args()

    text = render(load(args.date))
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")

    chunks = []
    current = []
    size = 0
    for block in text.split("\n\n"):
        if size + len(block) > args.max_chars and current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(block)
        size += len(block) + 2
    if current:
        chunks.append("\n\n".join(current))

    base = os.path.splitext(args.output)[0]
    for index, chunk in enumerate(chunks, start=1):
        with open(f"{base}.part{index}.md", "w", encoding="utf-8") as handle:
            handle.write(chunk + "\n")
    print(f"digest: {len(text)} chars → {args.output} ({len(chunks)} part(s))")


if __name__ == "__main__":
    main()
