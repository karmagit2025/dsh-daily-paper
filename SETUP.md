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

## 5. 告诉用户 B站 怎么办

插件不自带 B站 采集。要接的话，让用户提供一个能产出同格式 JSON 的采集器，
或者按 README 的「采集器」一节自己搭。**不要**替用户找 cookie、也不要代他登录。

## 6. 收尾

- 让用户刷新页面，确认左侧「UP 日报」能看到示例期
- 说明：日报内容由采集器产出，插件只负责呈现和配置
