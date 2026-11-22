#!/usr/bin/env python3
"""
B站视频音频转录脚本
支持本地 Whisper 和 API 两种方式
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

# 配置
TEMP_DIR = Path(os.environ.get("BILI_DATA_DIR") or Path.home() / ".dsh/daily-paper/bili") / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
WHISPER_MODEL_DIR = Path.home() / ".cache/whisper"

# ---- 模型预加载（模块级缓存，只加载一次）----
_whisper_model = None

def _load_whisper_model(model_name="base"):
    """懒加载 Whisper 模型，全局缓存"""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        import whisper
        import torch
        model_path = Path.home() / f".cache/whisper/{model_name}.pt"
        if model_path.exists() and model_path.stat().st_size > 100000000:
            checkpoint = torch.load(str(model_path), map_location="cpu")
            from whisper.model import Whisper, ModelDimensions
            dims = ModelDimensions(**checkpoint["dims"])
            _whisper_model = Whisper(dims)
            _whisper_model.load_state_dict(checkpoint["model_state_dict"])
        else:
            _whisper_model = whisper.load_model(model_name)
        return _whisper_model
    except Exception as e:
        raise Exception(f"Whisper 模型加载失败: {e}")


def fetch_bilibili_subtitle(bvid, cid, cookie_str):
    """
    尝试获取 B站自带字幕（AI 字幕 / CC 字幕）
    返回字幕文本，没有则返回 None
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': f'https://www.bilibili.com/video/{bvid}',
            'Cookie': cookie_str,
        }
        url = f"https://api.bilibili.com/x/player/wbi/v2?cid={cid}&bvid={bvid}"
        req = urllib.request.Request(url, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        
        subtitles = data.get('data', {}).get('subtitle', {}).get('subtitles', [])
        if not subtitles:
            return None
        
        # 优先用中文字幕
        sub_url = None
        for s in subtitles:
            if 'zh' in s.get('lan', ''):
                sub_url = s.get('subtitle_url')
                break
        if not sub_url:
            sub_url = subtitles[0].get('subtitle_url')
        if not sub_url:
            return None
        
        if sub_url.startswith('//'):
            sub_url = 'https:' + sub_url
        
        req2 = urllib.request.Request(sub_url, headers=headers)
        with opener.open(req2, timeout=15) as resp:
            sub_data = json.loads(resp.read().decode('utf-8'))
        
        bodies = sub_data.get('body', [])
        if not bodies:
            return None
        
        text = ' '.join([b['content'] for b in bodies])
        return text
    except Exception:
        return None


def download_audio(bvid, cid, cookie_str, output_file):
    """下载视频音频"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://www.bilibili.com/video/{bvid}',
        'Cookie': cookie_str,
    }
    
    # 获取音频流地址
    play_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnver=0&fnval=16&fourk=1"
    req = urllib.request.Request(play_url, headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=15) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    if data.get('code') != 0:
        raise Exception(f"获取音频流失败: {data.get('message')}")
    
    dash = data['data']['dash']
    audio_list = dash.get('audio', [])
    
    if not audio_list:
        raise Exception("无音频流")
    
    audio_url = audio_list[0]['baseUrl']
    
    # 下载音频
    req = urllib.request.Request(audio_url, headers=headers)
    with opener.open(req, timeout=60) as resp:
        with open(output_file, 'wb') as f:
            f.write(resp.read())
    
    return output_file


def convert_to_mp3(input_file, output_file):
    """转换为 MP3"""
    result = subprocess.run([
        'ffmpeg', '-y', '-i', str(input_file),
        '-vn', '-ar', '16000', '-ac', '1', '-b:a', '32k',
        str(output_file)
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"ffmpeg 转换失败: {result.stderr}")
    
    return output_file


def transcribe_with_whisper(mp3_file, model_name="base"):
    """使用本地 Whisper 转录（使用预加载模型）"""
    try:
        model = _load_whisper_model(model_name)
        result = model.transcribe(str(mp3_file), language="zh", fp16=False)
        
        return {
            'text': result['text'],
            'segments': result['segments'],
        }
    except ImportError:
        raise Exception("Whisper 未安装，请运行: pip install openai-whisper")
    except Exception as e:
        raise Exception(f"Whisper 转录失败: {e}")


def transcribe_with_api(mp3_file, api_key=None):
    """使用 OpenAI API 转录（备用方案）"""
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        raise Exception("未设置 OPENAI_API_KEY")
    
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        with open(mp3_file, 'rb') as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="zh",
                response_format="verbose_json"
            )
        
        return {
            'text': transcript.text,
            'segments': transcript.segments if hasattr(transcript, 'segments') else [],
        }
    except ImportError:
        raise Exception("OpenAI 库未安装，请运行: pip install openai")
    except Exception as e:
        raise Exception(f"API 转录失败: {e}")


def transcribe_video(bvid, cid, cookie_str, use_api=True, api_key=None):
    """
    完整的视频转录流程（字幕优先）
    
    Args:
        bvid: 视频 BV 号
        cid: 视频 CID
        cookie_str: B站 Cookie
        use_api: 是否优先使用 API（默认 True，更稳定）
        api_key: OpenAI API Key（使用 API 时必需）
    
    Returns:
        dict: {text, segments, duration, source}
        source: 'subtitle' | 'api' | 'whisper'
    """
    # ---- 第一步：尝试 B站自带字幕（最快，无需下载音频）----
    print(f"[1/3] 检查 B站字幕...")
    sub_text = fetch_bilibili_subtitle(bvid, cid, cookie_str)
    if sub_text and len(sub_text) > 50:
        print(f"      ✅ 字幕获取成功 ({len(sub_text)} 字符)")
        return {
            'text': sub_text,
            'segments': [],
            'duration': 0,
            'source': 'subtitle',
        }
    print(f"      ⚠️ 无字幕，转音频转录")
    
    # ---- 第二步：音频下载 + 转录 ----
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    m4s_file = TEMP_DIR / f"{bvid}_audio.m4s"
    mp3_file = TEMP_DIR / f"{bvid}.mp3"
    
    print(f"[2/3] 下载音频...")
    download_audio(bvid, cid, cookie_str, m4s_file)
    print(f"      ✅ 完成: {m4s_file.stat().st_size / 1024:.1f} KB")
    
    print(f"      转换为 MP3...")
    convert_to_mp3(m4s_file, mp3_file)
    print(f"      ✅ 完成: {mp3_file.stat().st_size / 1024:.1f} KB")
    
    print(f"[3/3] 语音转文字...")
    result = None
    source = 'whisper'
    
    if use_api:
        try:
            result = transcribe_with_api(mp3_file, api_key)
            print(f"      ✅ API 转录完成")
            source = 'api'
        except Exception as e:
            print(f"      ⚠️ API 转录失败: {e}")
            print(f"      尝试本地 Whisper...")
    
    if not result:
        try:
            result = transcribe_with_whisper(mp3_file)
            print(f"      ✅ 本地转录完成")
            source = 'whisper'
        except Exception as e:
            print(f"      ❌ 本地转录也失败: {e}")
            raise
    
    text = result['text']
    segments = result['segments']
    print(f"      结果: {len(text)} 字符, {len(segments)} 段")
    
    # 清理临时文件
    m4s_file.unlink(missing_ok=True)
    mp3_file.unlink(missing_ok=True)
    
    return {
        'text': text,
        'segments': segments,
        'duration': sum(seg.get('end', 0) - seg.get('start', 0) for seg in segments) if segments else 0,
        'source': source,
    }


def main():
    """命令行入口"""
    if len(sys.argv) < 4:
        print("用法: python audio_transcribe.py <bvid> <cid> <cookie_str> [--api] [api_key]")
        sys.exit(1)
    
    bvid = sys.argv[1]
    cid = sys.argv[2]
    cookie_str = sys.argv[3]
    use_api = '--api' in sys.argv
    api_key = sys.argv[sys.argv.index('--api') + 1] if use_api and '--api' in sys.argv else None
    
    try:
        result = transcribe_video(bvid, cid, cookie_str, use_api, api_key)
        print("\n" + "="*60)
        print("转录结果:")
        print("="*60)
        print(result['text'])
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
