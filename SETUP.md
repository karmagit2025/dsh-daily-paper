# 安装后引导（给 DSH agent 看的）

用户装完这个插件，说「帮我配好 UP 日报」时，按下面顺序做，**每一步都要验证通过再进下一步**。

## 1. 确认插件确实加载

```
plugin_manager list_plugins → 找 moduleName = dsh-daily-paper 的行，enabled 且 fiberPhase=active
```

不 active 就先 `set_plugin` 开关一次。

## 2. 建数据目录

```bash
mkdir -p ~/.dsh/daily-paper/issues
```

把仓库里的 `examples/sample-issue.json` 复制成 `~/.dsh/daily-paper/issues/2026-01-01.json`，
让用户先看到版式（**这一步能立刻给正反馈，别跳过**）。

## 3. 引导配置即刻

问用户要 5–10 个圈子 id（来自 `web.okjike.com/topic/<id>`）和 3–5 条「我想关注什么」。
填进 `~/.dsh/daily-paper/config.json`：

```json
"sources": { "jike": { "enabled": true, "lookbackDays": 3, "maxPerTopic": 10,
  "interests": ["…"], "topics": [{ "id": "…", "name": "…" }], "users": [] } }
```

也可以让用户在插件「配置」页填，效果一样。填完先手动跑一次验证：

```bash
cd <插件目录> && python3 scripts/jike_fetch.py --output /tmp/jike.json
```

条数为 0 时检查 id 对不对，别急着建任务。

## 4. 建定时任务

问用户几点出报（默认 09:00），然后用 DSH 的定时任务，提示词：

```
每天 09:00：
1. python3 scripts/jike_fetch.py --output /tmp/jike.json
2. 读 /tmp/jike.json，按 config 里的 interests 挑 3-8 条值得看的
   （高互动加权；丑闻/八卦/广告/灌水不占版面，最多在 note 里一句）
3. 写 /tmp/section.json = {"source":"jike","label":"即刻","note":"…","items":[…]}
4. python3 scripts/publish.py --source jike --items /tmp/section.json
5. 用 scripts/digest.py 渲染整期，推到用户指定的地方（飞书/邮件/不发）
```

## 5. 配 B站（可选，但大多数人都要）

1. 让用户自己从浏览器复制 `SESSDATA` / `bili_jct` / `DedeUserID`，填进插件「配置」页。
   **不要**替用户登录、也不要索取账号密码。
2. 让用户给出想跟的 UP 主 uid（`space.bilibili.com/<uid>`）。
3. 先验证抓取能跑通：

   ```bash
   cd <插件目录> && python3 scripts/bili/fetch_videos_v2.py --output /tmp/bili.json
   ```

   报 `-101` / `-352` 就是 cookie 失效，让用户重新复制，不要反复重试。
4. 没装 `openai-whisper` / `ffmpeg` 时，先加 `BILI_TRANSCRIBE=0` 跑通（只取字幕），再考虑装转录。

## 6. 收尾

- 让用户刷新页面，确认左侧「UP 日报」能看到示例期
- 说明：日报内容由采集器产出，插件只负责呈现和配置
