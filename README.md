# UP 日报 · dsh-daily-paper

给 DeepSeek Harness（DSH）用的私人日报插件：**左侧导航里一页「UP 日报」**，把每天采集到的内容排成杂志版式，按信源分栏，往期可回翻；同一页里还能配置信源。

> 这是一个**阅读器 + 配置页**。报纸的内容由采集端产出（下面有格式说明），插件本身负责呈现。

## 长什么样

- **刊头**：衬线大字 + 期号 / 日期 / 篇数
- **分栏**：B站、即刻…… 每个信源一栏，带一句编者按（note）
- **条目**：编号 + 作者 / 时长 + 衬线标题 + 要点 + 可执行项 + 原文链接
- **回翻**：上一期 / 下一期，本地保留全部历史

## 安装

### 方式一：让 DSH 装（推荐）

在 DSH 里说：

```
帮我安装这个插件：github:karmagit2025/dsh-daily-paper
```

或者直接用插件管理器的 `install_bundle`，target 填：

```
github:karmagit2025/dsh-daily-paper
```

### 方式二：本地目录

```bash
git clone https://github.com/karmagit2025/dsh-daily-paper.git
```

然后在 DSH 的 **Plugins → Add plugin** 里选这个目录。

装好后左侧导航会多出「UP 日报」，设置里也有同名一项。

### 先看看效果（不用采集器）

仓库里带了示例期。装好插件后：

```bash
mkdir -p ~/.dsh/daily-paper/issues
cp examples/sample-issue.json ~/.dsh/daily-paper/issues/2026-01-01.json
```

刷新页面点「上一期」，就能看到完整版式。

## 数据放在哪

```
~/.dsh/daily-paper/
├── config.json            # 你的配置（账号、关注的 UP 主、兴趣）——只在本机
└── issues/
    ├── 2026-01-01.json    # 一期一个文件，文件名必须是 YYYY-MM-DD
    └── ...
```

期文件格式：

```json
{
  "date": "2026-01-01",
  "lead": "一句话导语，可省",
  "sections": [
    {
      "source": "bilibili",
      "label": "B站",
      "note": "这一栏的一句编者按，可省",
      "items": [
        {
          "title": "标题（必填）",
          "author": "作者",
          "url": "https://…",
          "duration": "03:36",
          "publishedAt": "2026-01-01T09:00:00+08:00",
          "summary": ["要点一", "要点二"],
          "todo": ["可执行的一条"]
        }
      ]
    }
  ]
}
```

只有 `items[].title` 是必填，其余缺了就不渲染对应部分。

## 采集器

插件自带 **即刻** 采集器（只读公开内容，不需要登录）：

```bash
cd <插件目录>
python3 scripts/jike_fetch.py --output /tmp/jike.json
python3 scripts/publish.py --source jike --items /tmp/jike.json
```

在「配置」页填 5–10 个圈子 id（`web.okjike.com/topic/<id>`）和几条兴趣，采集后会由 agent 按兴趣择稿，而不是把动态原样搬过来。

**B站** 需要另外的采集器（拉 UP 主动态、取字幕或转录、生成摘要）。这篇 README 不打包它，因为每个租户的 cookie 和转写环境不同；只要你的采集器能产出上面那种 JSON，就能接进来。

`scripts/publish.py` 负责把一栏合并进当期（同 source 覆盖、其它栏不动），`scripts/digest.py` 负责把整期渲染成 Markdown 发到飞书或别处。

## 配置

`~/.dsh/daily-paper/config.json`：

```json
{
  "enabled": true,
  "cookie": { "SESSDATA": "", "bili_jct": "", "DedeUserID": "" },
  "upMasters": [{ "uid": "30871030", "name": "某 UP 主", "category": "finance" }],
  "monitor": { "maxVideosPerUp": 3, "lookbackDays": 1 },
  "sources": {
    "bilibili": { "enabled": true },
    "jike": {
      "enabled": true,
      "lookbackDays": 3,
      "maxPerTopic": 10,
      "interests": ["SEO 新技术", "AI 新玩具"],
      "topics": [{ "id": "…", "name": "AI探索站" }],
      "users": []
    }
  }
}
```

也可以在插件的「配置」页改，保存后写回这个文件。

## 定时出报

用 DSH 的定时任务，每天跑一次采集 + 出版 + 推送。示例提示词：

```
每天 09:00：
1. 跑即刻采集：python3 scripts/jike_fetch.py --output /tmp/jike.json
2. 读 /tmp/jike.json，按 config.sources.jike.interests 挑 3-8 条，写 /tmp/jike_section.json
3. python3 scripts/publish.py --source jike --items /tmp/jike_section.json
4. 用 scripts/digest.py 生成 Markdown 推给我
```

## 隐私

- 插件代码里**没有任何数据**、没有任何人的 cookie。
- `config.json`（含 cookie）只在你本机，不进插件、不进 git。
- 即刻采集是匿名读公开页面；B站采集用你自己的登录态。

## License

MIT
