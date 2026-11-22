#!/usr/bin/env python3
"""
即刻（Jike）采集器：圈子（topic）+ 用户（user）两种来源。

数据来源是 m.okjike.com 的服务端渲染页，页面里 <script type="application/json">
的 props.pageProps.posts 就是动态列表 —— 不需要登录、不需要签名、不需要浏览器。

配置：~/.dsh/daily-paper/config.json 的 sources.jike
    { "enabled": true, "lookbackDays": 3, "maxPerTopic": 10,
      "interests": ["SEO/GEO 新技术", "AI 新玩具"],
      "topics": [{"id": "...", "name": "AI"}],
      "users":  [{"id": "...", "name": "某人"}] }

输出：{"source":"jike","label":"即刻","note":"...","items":[...]}
items 里同时保留原文 `content`（截断到 1200 字），供后续择稿用。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

CONFIG = os.path.expanduser("~/.dsh/daily-paper/config.json")
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
JSON_SCRIPT = re.compile(r'<script[^>]+type="application/json"[^>]*>(.*?)</script>', re.S)
LOCAL_TZ = timezone(timedelta(hours=8))


def load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def fetch_page(kind, ident):
    url = f"https://m.okjike.com/{kind}/{ident}"
    request = urllib.request.Request(url, headers={"User-Agent": MOBILE_UA, "Referer": url})
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", "replace")
    match = JSON_SCRIPT.search(html)
    if not match:
        raise RuntimeError("no application/json payload")
    page = (json.loads(match.group(1)).get("props") or {}).get("pageProps") or {}
    return page


def post_link(post):
    kind = post.get("type")
    post_id = post.get("id")
    if kind == "REPOST":
        return f"https://m.okjike.com/reposts/{post_id}"
    if kind == "MEDIUM":
        return f"https://www.okjike.com/medium/{post_id}"
    return f"https://m.okjike.com/originalPosts/{post_id}"


def to_item(post, author, topic=None):
    content = (post.get("content") or "").strip()
    raw = (post.get("rawContent") or "").strip()
    text = content or raw
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = ["（无正文）"]

    title = lines[0]
    if len(title) > 46:
        title = title[:45] + "…"
    summary = lines[1:4] if len(lines) > 1 else []

    counters = []
    if post.get("likeCount"):
        counters.append(f"{post['likeCount']} 赞")
    if post.get("commentCount"):
        counters.append(f"{post['commentCount']} 评论")
    pictures = post.get("pictures") or []
    if pictures:
        counters.append(f"{len(pictures)} 图")
    if counters:
        summary = summary + [" · ".join(counters)]

    created = post.get("createdAt")
    published_at = None
    when = None
    if created:
        try:
            when = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
            published_at = when.isoformat()
        except ValueError:
            when = None

    return {
        "title": title,
        "author": author,
        "topic": topic,
        "url": post_link(post),
        "publishedAt": published_at,
        "summary": summary,
        "todo": [],
        "kind": post.get("type") or "ORIGINAL_POST",
        # 供 agent 择稿时读原文，不进最终版面
        "content": text[:1200],
        "engagement": {
            "like": post.get("likeCount") or 0,
            "comment": post.get("commentCount") or 0,
        },
        "_when": when,
    }


def collect(entries, kind, lookback, cap, items, seen, note_bits):
    for entry in entries:
        ident = str(entry.get("id") or "").strip()
        if not ident:
            continue
        label = (entry.get("name") or ident).strip()
        try:
            page = fetch_page(kind, ident)
        except Exception as error:
            print(f"jike: {label} ({ident}) failed: {type(error).__name__}: {error}", file=sys.stderr)
            note_bits.append(f"{label} 抓取失败")
            continue

        if kind == "topics":
            topic = page.get("topic") or {}
            topic_name = topic.get("content") or label
            author_of = lambda post: (post.get("user") or {}).get("screenName") or ""
            posts = page.get("posts") or []
        else:
            topic_name = None
            profile = page.get("user") or {}
            author_of = lambda post, name=profile.get("screenName") or label: name
            posts = page.get("posts") or []

        kept = 0
        for post in posts:
            item = to_item(post, author_of(post), topic_name)
            when = item.pop("_when")
            if when is not None and when < lookback:
                continue
            key = post.get("id")
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
            kept += 1
            if kept >= cap:
                break
        print(f"jike: {kind[:-1]} «{topic_name or label}» → {kept} 条")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--config", default=CONFIG)
    parser.add_argument("--lookback-days", type=int, default=None)
    args = parser.parse_args()

    config = load_config(os.path.expanduser(args.config))
    jike = (config.get("sources") or {}).get("jike") or {}
    if not jike.get("enabled"):
        print("jike: disabled in config")
        write_output(args.output, [], "")
        return

    days = args.lookback_days or int(jike.get("lookbackDays") or 3)
    horizon = datetime.now(LOCAL_TZ) - timedelta(days=max(1, days))
    cap = int(jike.get("maxPerTopic") or 10)

    topics = jike.get("topics") or []
    users = jike.get("users") or []
    if not topics and not users:
        print("jike: no topics or users configured")
        write_output(args.output, [], "")
        return

    items, seen, note_bits = [], set(), []
    collect(topics, "topics", horizon, cap, items, seen, note_bits)
    collect(users, "users", horizon, 5, items, seen, note_bits)

    interests = jike.get("interests") or []
    note = f"{len(topics)} 个圈子" if topics else ""
    if users:
        note = (note + f" · {len(users)} 位关注" if note else f"{len(users)} 位关注")
    if interests:
        note += f" ｜ 关注点：{'、'.join(interests[:4])}" if note else f"关注点：{'、'.join(interests[:4])}"
    if note_bits:
        note += f" ｜ {'、'.join(note_bits)}"

    write_output(args.output, items, note)


def write_output(path, items, note):
    payload = {"source": "jike", "label": "即刻", "note": note, "items": items}
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"jike: wrote {len(items)} items → {path}")


if __name__ == "__main__":
    main()
