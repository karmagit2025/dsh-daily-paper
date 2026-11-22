#!/usr/bin/env python3
"""
把 fetch_videos_v2.py 的输出转成「一栏」的 JSON，直接交给 publish.py。
不调用任何模型：有转录就用转录，没有就用标题 + 简介，先保证能出报。

    python3 scripts/bili_to_section.py --input /tmp/bili_daily.json --output /tmp/bili_section.json
"""

import argparse
import json
import re

SENTENCE = re.compile(r'(?<=[。！？!?；;])\s*')


def summarize(video, max_points=3):
    """从转录或简介里切出前几句，作为要点。"""
    text = (video.get("content") or "").strip()
    if not text or text == video.get("description"):
        text = (video.get("description") or "").strip()
    if not text:
        return []

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        points = lines[:max_points]
    else:
        points = [s.strip() for s in SENTENCE.split(text) if s.strip()][:max_points]

    out = []
    for point in points:
        if len(point) > 140:
            point = point[:139] + "…"
        out.append(point)
    return out


def to_item(video):
    return {
        "title": (video.get("title") or "(无标题)").strip(),
        "author": (video.get("up_name") or "").strip(),
        "url": video.get("url") or f"https://www.bilibili.com/video/{video.get('bvid', '')}",
        "duration": video.get("duration") or "",
        "publishedAt": video.get("pub_date") or video.get("published_at") or None,
        "summary": summarize(video),
        "todo": [],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", default="/tmp/bili_daily.json")
    parser.add_argument("--output", "-o", default="/tmp/bili_section.json")
    parser.add_argument("--max-videos", type=int, default=20)
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    videos = data.get("new_videos") or []
    items = [to_item(v) for v in videos][: args.max_videos]

    section = {"source": "bilibili", "label": "B站", "items": items}
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(section, handle, ensure_ascii=False, indent=2)
    print(f"bili: {len(items)} 条 → {args.output}")


if __name__ == "__main__":
    main()
