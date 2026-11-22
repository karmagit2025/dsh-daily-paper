#!/usr/bin/env python3
"""
把一批条目合并进今天的 UP 日报。

每个信源只写自己那一栏，互不覆盖：
    python3 publish.py --source jike --items /tmp/jike.json
    python3 publish.py --source bilibili --items /tmp/bili.json --lead "..."

--items 指向 {"source","label","items":[...]} 形状的文件（jike_fetch.py 就产出这个）。
同日重跑会替换同 source 的那一栏，其它栏保持不动。
"""

import argparse
import json
import os
from datetime import datetime

ISSUES = os.path.expanduser("~/DSH-work/daily-paper/issues")


def load(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return fallback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--items", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--lead", default=None)
    parser.add_argument("--date", default=None)
    args = parser.parse_args()

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    os.makedirs(ISSUES, exist_ok=True)
    path = os.path.join(ISSUES, f"{date}.json")

    issue = load(path, {"date": date, "title": "UP 日报", "lead": "", "sections": []})
    incoming = load(args.items, {"source": args.source, "label": args.label or args.source, "items": []})
    section = {
        "source": incoming.get("source") or args.source,
        "label": args.label or incoming.get("label") or args.source,
        "items": incoming.get("items") or [],
    }
    note = incoming.get("note")
    if note:
        section["note"] = note

    sections = [s for s in issue.get("sections", []) if s.get("source") != section["source"]]
    sections.append(section)
    issue["sections"] = sections
    issue["date"] = date
    issue.setdefault("title", "UP 日报")
    issue["generatedAt"] = datetime.now().astimezone().isoformat(timespec="seconds")
    if args.lead:
        issue["lead"] = args.lead
    elif not issue.get("lead"):
        total = sum(len(s.get("items") or []) for s in sections)
        issue["lead"] = f"本期 {total} 条：{'、'.join(s['label'] for s in sections)}。"

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(issue, handle, ensure_ascii=False, indent=2)

    # 面板读的是本机运行目录，顺手镜像一份，省得等下一轮同步
    local_dir = os.path.expanduser("~/.dsh/daily-paper/issues")
    try:
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, f"{date}.json"), "w", encoding="utf-8") as handle:
            json.dump(issue, handle, ensure_ascii=False, indent=2)
    except OSError:
        pass

    print(f"published {section['label']} ({len(section['items'])} 条) → {path}")


if __name__ == "__main__":
    main()
