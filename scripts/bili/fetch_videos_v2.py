#!/usr/bin/env python3
"""
B站 UP 主视频抓取脚本 v2
支持混合策略：
- 短视频 (< 3分钟): 标题+描述总结
- 长视频 (>= 3分钟): 音频转录+深度总结
"""

import json
import os
import sys
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
import pathlib
pathlib_Path = Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置：默认读插件的 config.json（也可以 BILI_CONFIG 指到 yaml）
SKILL_DIR = Path(__file__).resolve().parent.parent.parent
HOME_DP = pathlib_Path(os.path.expanduser("~/.dsh/daily-paper"))
CONFIG_PATH = pathlib_Path(os.environ.get("BILI_CONFIG") or (HOME_DP / "config.json"))
DATA_DIR = pathlib_Path(os.environ.get("BILI_DATA_DIR") or (HOME_DP / "bili"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR = DATA_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# 关掉音频转录（没装 whisper 时用）：BILI_TRANSCRIBE=0
TRANSCRIBE_ENABLED = os.environ.get("BILI_TRANSCRIBE", "1") not in ("0", "false", "no")

PROCESSED_DB = DATA_DIR / "processed.json"

# 转录时长阈值（秒）
TRANSCRIBE_THRESHOLD = 180  # 3分钟

# ---- 网络请求重试装饰器 ----
from functools import wraps

def retry(max_retries=3, delay=2, exceptions=(Exception,)):
    """简单重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_retries - 1:
                        print(f"      ⚠️ 第{attempt+1}次失败，{delay}秒后重试...")
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


def _proxies():
    """系统代理（如果配置了），直连被 B 站风控时回退使用"""
    out = {}
    for scheme in ("http", "https"):
        val = os.environ.get(f"{scheme.upper()}_PROXY") or os.environ.get(f"{scheme}_proxy")
        if val:
            out[scheme] = val
    return out


@retry(max_retries=3, delay=2)
def fetch_url(url, headers, timeout=30):
    """带重试的 URL 请求：先直连，失败再走系统代理"""
    hdrs = dict(headers)
    hdrs.setdefault("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36")
    req = urllib.request.Request(url, headers=hdrs)
    proxy_map = _proxies()
    # 本机直连 B 站会被风控成“成功但空列表”，有系统代理时优先走代理，失败再直连
    attempts = [urllib.request.ProxyHandler(proxy_map)] if proxy_map else []
    attempts.append(urllib.request.ProxyHandler({}))
    last = None
    for handler in attempts:
        try:
            opener = urllib.request.build_opener(handler)
            with opener.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:  # 直连被拦截/超时就换代理
            last = e
            continue
    raise last


def load_config():
    """读配置：插件用 JSON（~/.dsh/daily-paper/config.json），也兼容老的 YAML。"""
    path = str(CONFIG_PATH)
    with open(path, 'r', encoding='utf-8') as f:
        if path.endswith('.json'):
            raw = json.load(f)
            sources = (raw.get('sources') or {}).get('bilibili') or {}
            if sources.get('enabled') is False:
                print("B站采集在配置里是关闭的（sources.bilibili.enabled = false）")
                sys.exit(0)
            monitor = raw.get('monitor') or {}
            return {
                'cookie': raw.get('cookie') or {},
                'up_masters': [
                    {'uid': u.get('uid'), 'name': u.get('name', ''), 'category': u.get('category', 'finance')}
                    for u in (raw.get('upMasters') or [])
                ],
                'monitor': {
                    'max_videos_per_up': monitor.get('maxVideosPerUp', 3),
                    'lookback_days': monitor.get('lookbackDays', 1),
                },
            }
        import yaml
        return yaml.safe_load(f)


def load_processed():
    """加载已处理的视频记录"""
    if PROCESSED_DB.exists():
        with open(PROCESSED_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_processed(processed):
    """保存已处理的视频记录"""
    with open(PROCESSED_DB, 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)


def build_cookie_string(cookie_dict):
    """构建 Cookie 字符串"""
    cookies = []
    for key, value in cookie_dict.items():
        if value:
            cookies.append(f"{key}={value}")
    return "; ".join(cookies)


def parse_duration(duration_text):
    """解析时长文本为秒数"""
    if not duration_text or duration_text == "未知":
        return 0
    
    parts = duration_text.split(':')
    if len(parts) == 2:
        # MM:SS
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        # HH:MM:SS
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def fetch_user_dynamics(uid, cookie_string, page=1):
    """
    获取 UP 主的动态列表（包含视频）
    v2.4 修复：增加空 items 二次重试，解决 B站 API 间歇性返回空的问题
    """
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}&page={page}&timezone_offset=-480"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://space.bilibili.com/{uid}/dynamic',
        'Cookie': cookie_string,
    }
    
    for attempt in range(2):  # 最多重试 1 次
        try:
            result = fetch_url(url, headers, timeout=30)
            if result and result.get('code') == 0:
                items = result.get('data', {}).get('items', [])
                if items:
                    return result
                # 返回成功但 items 为空，可能是 API 限流，尝试重试
                if attempt == 0:
                    print(f"      ⚠️ API 返回空 items，3秒后重试...")
                    time.sleep(3)
                    continue
            return result
        except Exception as e:
            if attempt == 0:
                print(f"      ⚠️ 请求失败: {e}，3秒后重试...")
                time.sleep(3)
                continue
            print(f"请求失败: {e}")
            return None
    return result


def fetch_video_detail(bvid, cookie_string):
    """获取视频详情"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': f'https://www.bilibili.com/video/{bvid}',
        'Cookie': cookie_string,
    }
    
    try:
        return fetch_url(url, headers, timeout=30)
    except Exception as e:
        print(f"获取视频详情失败: {e}")
        return None


def transcribe_audio(bvid, cid, cookie_string):
    """
    下载并转录视频音频（字幕优先）
    返回转录文本
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from audio_transcribe import fetch_bilibili_subtitle, transcribe_video
        
        # 第一步：尝试 B站字幕（最快）
        sub_text = fetch_bilibili_subtitle(bvid, cid, cookie_string)
        if sub_text and len(sub_text) > 50:
            print(f"     ✅ 字幕获取成功 ({len(sub_text)} 字符)")
            return sub_text
        
        # 第二步：音频转录
        result = transcribe_video(bvid, cid, cookie_string)
        return result.get('text', '')
    except Exception as e:
        print(f"    ⚠️ 转录失败: {e}")
        return None


def is_recent_video(pub_time_str, lookback_days=1):
    """检查视频是否在指定时间内发布
    
    B站动态API返回的pub_time格式示例：
    - "刚刚" / "1分钟前" / "3小时前"
    - "昨天 23:25"
    - "3天前"
    - "04月18日"
    """
    if not pub_time_str:
        return False
    
    # 1. "刚刚"
    if pub_time_str == '刚刚':
        return True
    
    # 2. "N分钟前" / "N小时前"
    if '分钟前' in pub_time_str or '小时前' in pub_time_str:
        return True
    
    # 3. "昨天 HH:MM"
    if pub_time_str.startswith('昨天'):
        return lookback_days >= 1
    
    # 4. "N天前"
    import re
    days_ago_match = re.match(r'(\d+)天前', pub_time_str)
    if days_ago_match:
        days = int(days_ago_match.group(1))
        return days <= lookback_days
    
    # 5. "MM月DD日" 格式
    try:
        now = datetime.now()
        for d in range(lookback_days + 1):
            check_day = (now - timedelta(days=d)).strftime('%m月%d日')
            if pub_time_str == check_day:
                return True
    except Exception:
        pass
    
    return False


def process_up_master(up, cookie_string, processed, session_processed, max_videos, lookback_days, lock=None):
    """处理单个 UP 主（用于并行执行）
    
    重要：processed.json 只作为日志/历史记录，不用于跨天去重。
    每次运行时只在 session_processed 本轮内去重，确保昨天的视频不会因为历史记录而被跳过。
    """
    uid = up.get('uid')
    name = up.get('name', uid)
    category = up.get('category', 'general')
    
    print(f"\n检查 UP 主: {name} (UID: {uid})")
    
    # 获取动态列表（fetch_user_dynamics 内部已带二次重试，解决B站API间歇性返回空items问题）
    result = fetch_user_dynamics(uid, cookie_string)
    
    if not result or result.get('code') != 0:
        err_msg = result.get('message', 'Unknown error') if result else 'No response'
        print(f"  ❌ 获取失败: {err_msg}")
        return []
    
    items = result.get('data', {}).get('items', [])
    
    videos = []
    
    for item in items:
        type_name = item.get('type', '')
        if type_name != 'DYNAMIC_TYPE_AV':
            continue
        
        pub_time = item.get('modules', {}).get('module_author', {}).get('pub_time', '')
        
        # 检查是否近期视频
        if not is_recent_video(pub_time, lookback_days):
            continue
        
        major = item.get('modules', {}).get('module_dynamic', {}).get('major', {})
        archive = major.get('archive', {})
        
        bvid = archive.get('bvid', '')
        title = archive.get('title', 'N/A')
        duration_text = archive.get('duration_text', '未知')
        
        # 本轮运行内去重（不检查 processed.json 的历史记录）
        with lock if lock else threading.Lock():
            if bvid in session_processed:
                print(f"  ⏭️ 本次已处理: {title[:40]}")
                continue
        
        print(f"  🆕 新视频: {title[:50]}")
        print(f"     时长: {duration_text}")
        
        # 获取视频详情
        detail = fetch_video_detail(bvid, cookie_string)
        desc = ""
        cid = None
        duration_sec = parse_duration(duration_text)
        
        if detail and detail.get('code') == 0:
            detail_data = detail.get('data', {})
            desc = detail_data.get('desc', '')
            cid = detail_data.get('cid')
            duration_sec = detail_data.get('duration', duration_sec)
        
        # 判断是否需要转录
        content = None
        if TRANSCRIBE_ENABLED and duration_sec >= TRANSCRIBE_THRESHOLD and cid:
            print(f"     📢 视频较长 ({duration_sec}秒)，开始内容提取...")
            content = transcribe_audio(bvid, cid, cookie_string)
            if content:
                print(f"     ✅ 内容提取完成 ({len(content)} 字符)")
            else:
                print(f"     ⚠️ 内容提取失败，使用描述")
                content = desc or title
        else:
            print(f"     📝 视频较短，使用标题+描述")
            content = desc or title
        
        video_info = {
            'bvid': bvid,
            'title': title,
            'description': desc,
            'content': content,
            'duration': duration_text,
            'duration_sec': duration_sec,
            'pub_time': pub_time,
            'up_name': name,
            'up_uid': uid,
            'category': category,
            'url': f"https://www.bilibili.com/video/{bvid}",
            'transcribed': TRANSCRIBE_ENABLED and duration_sec >= TRANSCRIBE_THRESHOLD and content != (desc or title),
        }
        
        videos.append(video_info)
        
        # 本轮去重标记
        with lock if lock else threading.Lock():
            session_processed.add(bvid)
        
        # 仍然写入 processed.json 作为日志/历史记录
        if lock:
            with lock:
                processed[bvid] = {
                    'title': title,
                    'processed_at': datetime.now().isoformat(),
                    'transcribed': video_info['transcribed'],
                }
        else:
            processed[bvid] = {
                'title': title,
                'processed_at': datetime.now().isoformat(),
                'transcribed': video_info['transcribed'],
            }
        
        # 限制每个 UP 主处理数量
        if len(videos) >= max_videos:
            break
    
    print(f"  ✅ 本次处理 {len(videos)} 个视频")
    return videos


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', help='JSON 输出文件路径')
    args = parser.parse_args()
    
    config = load_config()
    cookie_dict = config.get('cookie', {})
    cookie_string = build_cookie_string(cookie_dict)
    
    if not cookie_string or not cookie_dict.get('SESSDATA'):
        print("错误: Cookie 未设置")
        sys.exit(1)
    
    up_masters = config.get('up_masters', [])
    monitor_config = config.get('monitor', {})
    max_videos = monitor_config.get('max_videos_per_up', 3)
    lookback_days = monitor_config.get('lookback_days', 1)
    
    processed = load_processed()
    new_videos = []
    session_processed = set()  # 本轮运行内去重，不依赖 processed.json 的历史记录
    
    print(f"开始监控 {len(up_masters)} 个 UP 主...")
    print(f"转录: {'开' if TRANSCRIBE_ENABLED else '关'}（阈值 {TRANSCRIBE_THRESHOLD} 秒）")
    print("-" * 60)
    
    lock = threading.Lock()
    
    # ---- 串行处理 UP 主（避免并发触发B站限流）----
    for up in up_masters:
        try:
            videos = process_up_master(up, cookie_string, processed, session_processed, max_videos, lookback_days, lock)
            new_videos.extend(videos)
        except Exception as e:
            print(f"\n  ❌ {up.get('name', up.get('uid'))} 处理异常: {e}")
        time.sleep(2)  # 请求间延迟2秒，降低被限流概率
    
    # 并行版本（已废弃，并发触发B站API限流导致随机返回空items）
    # with ThreadPoolExecutor(max_workers=3) as executor:
    #     futures = {
    #         executor.submit(process_up_master, up, cookie_string, processed, session_processed, max_videos, lookback_days, lock): up
    #         for up in up_masters
    #     }
    #     for future in as_completed(futures):
    #         up = futures[future]
    #         try:
    #             videos = future.result()
    #             new_videos.extend(videos)
    #         except Exception as e:
    #             print(f"\n  ❌ {up.get('name', up.get('uid'))} 处理异常: {e}")
    
    # 保存处理记录
    save_processed(processed)
    
    print("\n" + "=" * 60)
    print(f"监控完成，发现 {len(new_videos)} 个新视频")
    
    # 统计
    transcribed_count = sum(1 for v in new_videos if v['transcribed'])
    print(f"  其中深度转录: {transcribed_count} 个")
    print(f"  标题+描述: {len(new_videos) - transcribed_count} 个")
    
    # 输出结果
    output = {
        'new_videos': new_videos,
        'total_processed': len(processed),
        'timestamp': datetime.now().isoformat(),
    }
    
    output_json = json.dumps(output, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"\n结果已写入: {args.output}")
    else:
        print(output_json)
    
    return output


if __name__ == '__main__':
    main()
