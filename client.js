/**
 * Client half of dsh-daily-paper: "UP 日报" — a magazine-style page that lives
 * both in the left sidebar navigation and in Settings, with the paper and its
 * configuration on the same page.
 *
 * Self-registering classic script for window.__ModuleLoader__.
 */
window.__ModuleLoader__.load({
  id: 'dsh-daily-paper',
  factory(require) {
    const React = require('react')
    const h = React.createElement
    const { useEffect, useMemo, useState } = React

    const API = '/api/daily-paper'
    const SEED = () => globalThis.__DAILY_PAPER__
    const TITLE = 'UP 日报'

    const CSS = `
/* ---- page shell -------------------------------------------------------- */
.dp-root { --dp-ink: var(--dsw-alias-label-primary, currentColor);
  --dp-muted: var(--dsw-alias-label-tertiary, currentColor);
  --dp-rule: var(--dsw-alias-border-l2, color-mix(in srgb, currentColor 22%, transparent));
  --dp-rule-strong: var(--dsw-alias-border-l3, color-mix(in srgb, currentColor 38%, transparent));
  --dp-accent: var(--dsw-alias-brand-primary, #9c3a2f);
  --dp-hover: var(--dsw-alias-interactive-bg-hover, color-mix(in srgb, currentColor 9%, transparent));
  --dp-input-bg: var(--dsw-alias-fill-l1, transparent);
  --dp-on-accent: var(--dsw-alias-label-on-color, #fff);
  --dp-serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, "Songti SC", "Noto Serif SC", serif;
  --dp-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", sans-serif;
  box-sizing: border-box; padding: 22px 26px 40px; color: var(--dp-ink); font-family: var(--dp-sans);
  font-size: 13px; line-height: 1.62; background: transparent;
  /* 宿主给的是定高容器且 overflow:hidden 时，靠这两行自己滚 */
  max-height: 100%; overflow-y: auto; overscroll-behavior: contain; }
.dp-root * { box-sizing: border-box; }

/* ---- masthead ---------------------------------------------------------- */
.dp-masthead { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px;
  padding-bottom: 8px; border-bottom: 3px double var(--dp-rule-strong); }
.dp-mast { display: flex; flex-direction: column; gap: 2px; }
.dp-wordmark { font-family: var(--dp-serif); font-size: 27px; font-weight: 700; letter-spacing: .16em;
  line-height: 1.05; text-transform: uppercase; }
.dp-edition { font-family: var(--dp-sans); font-size: 10.5px; letter-spacing: .16em; text-transform: uppercase;
  color: var(--dp-muted); }
.dp-tools { display: flex; align-items: center; gap: 6px; padding-bottom: 3px; }

/* ---- buttons ----------------------------------------------------------- */
.dp-btn { appearance: none; border: 1px solid var(--dp-rule); background: transparent; color: inherit;
  border-radius: 2px; padding: 3px 9px; font-size: 11px; letter-spacing: .06em; text-transform: uppercase;
  cursor: pointer; font-family: var(--dp-sans); }
.dp-btn:hover:not(:disabled) { border-color: var(--dp-rule-strong); background: var(--dp-hover); }
.dp-btn:disabled { opacity: .35; cursor: default; }
.dp-primary { border-color: var(--dp-accent); background: var(--dp-accent); color: var(--dp-on-accent); }
.dp-primary:hover:not(:disabled) { background: var(--dp-accent); filter: brightness(1.08); }

/* ---- tabs -------------------------------------------------------------- */
.dp-tabs { display: flex; gap: 18px; margin: 14px 0 18px; border-bottom: 1px solid var(--dp-rule);
  position: sticky; top: -22px; z-index: 2; padding-top: 4px;
  background: var(--dsw-alias-bg-base, var(--dsw-alias-bg-layer-1, transparent)); }
.dp-tab { appearance: none; border: 0; background: transparent; color: var(--dp-muted); cursor: pointer;
  padding: 0 0 7px; font-size: 11px; letter-spacing: .18em; text-transform: uppercase;
  border-bottom: 2px solid transparent; margin-bottom: -1px; font-family: var(--dp-sans); }
.dp-tab[data-on="1"] { color: var(--dp-ink); border-bottom-color: var(--dp-accent); font-weight: 700; }
.dp-tab:hover { color: var(--dp-ink); }

/* ---- lead -------------------------------------------------------------- */
.dp-lead { font-family: var(--dp-serif); font-size: 17px; line-height: 1.5; font-style: italic;
  margin: 18px 0 6px; padding-left: 14px; border-left: 2px solid var(--dp-accent); color: var(--dp-ink); }

/* ---- section ----------------------------------------------------------- */
.dp-sec { margin: 26px 0 0; }
.dp-sec-head { display: flex; align-items: center; gap: 10px; margin: 0 0 14px; }
.dp-sec-no { font-family: var(--dp-serif); font-size: 12px; font-weight: 700; color: var(--dp-accent);
  letter-spacing: .06em; }
.dp-sec-name { font-size: 11px; font-weight: 700; letter-spacing: .22em; text-transform: uppercase; }
.dp-sec-rule { flex: 1; height: 1px; background: var(--dp-rule); }
.dp-sec-count { font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--dp-muted); }
.dp-sec-note { margin: -6px 0 14px; font-size: 11.5px; color: var(--dp-muted); font-style: italic; }

/* ---- item grid --------------------------------------------------------- */
.dp-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 22px 30px; }
.dp-card { display: flex; flex-direction: column; gap: 7px; }
.dp-kicker { display: flex; align-items: center; gap: 7px; font-size: 10px; letter-spacing: .18em;
  text-transform: uppercase; color: var(--dp-accent); font-weight: 700; }
.dp-kicker .dp-dot { width: 3px; height: 3px; background: var(--dp-accent); border-radius: 50%; }
.dp-kicker .dp-by { color: var(--dp-muted); font-weight: 500; }
.dp-h { margin: 0; font-family: var(--dp-serif); font-size: 18px; line-height: 1.3; font-weight: 700;
  letter-spacing: -.005em; }
.dp-h a { color: inherit; text-decoration: none; }
.dp-h a:hover { color: var(--dp-accent); }
.dp-points { margin: 0; padding: 0; list-style: none; }
.dp-points li { position: relative; padding-left: 12px; margin: 0 0 5px; }
.dp-points li::before { content: ""; position: absolute; left: 0; top: .68em; width: 5px; height: 1px;
  background: var(--dp-rule-strong); }
.dp-todo { margin: 2px 0 0; padding: 6px 0 2px 10px; border-left: 2px solid var(--dp-accent); }
.dp-todo-label { font-size: 9.5px; letter-spacing: .18em; text-transform: uppercase; color: var(--dp-accent);
  font-weight: 700; margin-bottom: 3px; }
.dp-todo ul { margin: 0; padding-left: 14px; }
.dp-todo li { margin: 1px 0; font-family: var(--dp-serif); font-size: 13px; }
.dp-link { align-self: flex-start; margin-top: 2px; font-size: 10px; letter-spacing: .16em;
  text-transform: uppercase; color: var(--dp-accent); text-decoration: none; font-weight: 700; }
.dp-link:hover { text-decoration: underline; }

/* ---- states ------------------------------------------------------------ */
.dp-empty { padding: 46px 12px; text-align: center; font-family: var(--dp-serif); font-style: italic;
  color: var(--dp-muted); border-top: 1px solid var(--dp-rule); border-bottom: 1px solid var(--dp-rule); }
.dp-error { padding: 10px 12px; border-left: 2px solid var(--dsw-alias-state-error-primary, currentColor); color: var(--dsw-alias-state-error-primary, currentColor); }

/* ---- config ------------------------------------------------------------ */
.dp-form { max-width: 620px; }
.dp-field { display: flex; flex-direction: column; gap: 4px; margin: 0 0 13px; }
.dp-field > label { font-size: 10.5px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--dp-muted); }
.dp-hint { font-size: 11.5px; color: var(--dp-muted); }
.dp-input { width: 100%; padding: 5px 8px; font-size: 12.5px; border-radius: 2px; font-family: var(--dp-sans);
  border: 1px solid var(--dp-rule); background: var(--dp-input-bg); color: inherit; }
.dp-row { display: flex; align-items: center; gap: 8px; margin: 0 0 7px; }
.dp-row .dp-input { width: auto; }
.dp-row .dp-uid { width: 150px; }
.dp-row .dp-name { width: 160px; }
.dp-row .dp-cat { width: 108px; }
.dp-section-title { display: flex; align-items: baseline; gap: 10px; font-size: 10.5px; font-weight: 700;
  letter-spacing: .2em; text-transform: uppercase; margin: 24px 0 10px; color: var(--dp-ink); }
.dp-section-title::after { content: ""; flex: 1; height: 1px; background: var(--dp-rule); }
.dp-save { display: flex; align-items: center; gap: 10px; margin-top: 16px; padding-top: 14px;
  border-top: 1px solid var(--dp-rule); }
.dp-ok { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--dsw-alias-state-success-primary, currentColor); }
.dp-spacer { flex: 1; }
`

    async function api(path, init) {
      const response = await fetch(`${API}${path}`, { credentials: 'same-origin', cache: 'no-store', ...init })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.detail || body.error || `HTTP ${response.status}`)
      return body
    }

    const EMPTY_CONFIG = {
      enabled: true,
      cookie: { SESSDATA: '', bili_jct: '', DedeUserID: '' },
      upMasters: [],
      monitor: { maxVideosPerUp: 3, lookbackDays: 1 },
      sources: {
        bilibili: { enabled: true },
        jike: { enabled: false, lookbackDays: 3, maxPerTopic: 10, interests: [], topics: [], users: [] },
      },
    }

    function mergeConfig(value) {
      const base = JSON.parse(JSON.stringify(EMPTY_CONFIG))
      if (!value || typeof value !== 'object') return base
      return {
        ...base,
        ...value,
        cookie: { ...base.cookie, ...(value.cookie || {}) },
        monitor: { ...base.monitor, ...(value.monitor || {}) },
        upMasters: Array.isArray(value.upMasters) ? value.upMasters.map((item) => ({ ...item })) : [],
        sources: {
          bilibili: { ...base.sources.bilibili, ...((value.sources || {}).bilibili || {}) },
          jike: {
            ...base.sources.jike,
            ...((value.sources || {}).jike || {}),
            interests: Array.isArray(((value.sources || {}).jike || {}).interests)
              ? value.sources.jike.interests.slice()
              : [],
            topics: Array.isArray(((value.sources || {}).jike || {}).topics)
              ? value.sources.jike.topics.map((item) => ({ ...item }))
              : [],
            users: Array.isArray(((value.sources || {}).jike || {}).users)
              ? value.sources.jike.users.map((item) => ({ ...item }))
              : [],
          },
        },
      }
    }

    function shortTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    }

    function longDate(value) {
      if (!value) return ''
      const date = new Date(`${value}T00:00:00`)
      if (Number.isNaN(date.getTime())) return value
      return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
    }

    const pad = (n) => String(n).padStart(2, '0')

    function Item(props) {
      const { item, index, source } = props
      const data = item || {}
      const summary = Array.isArray(data.summary) ? data.summary : data.summary ? [data.summary] : []
      const todo = Array.isArray(data.todo) ? data.todo : data.todo ? [data.todo] : []
      const by = [data.author, data.duration, shortTime(data.publishedAt)].filter(Boolean)
      return h('article', { className: 'dp-card' },
        h('div', { className: 'dp-kicker' },
          h('span', null, pad(index + 1)),
          h('span', { className: 'dp-dot' }),
          by.length ? h('span', { className: 'dp-by' }, by.join('  ·  ')) : null),
        h('h3', { className: 'dp-h' },
          data.url
            ? h('a', { href: data.url, target: '_blank', rel: 'noreferrer' }, data.title || '(无标题)')
            : (data.title || '(无标题)')),
        summary.length
          ? h('ul', { className: 'dp-points' }, summary.map((line, i) => h('li', { key: i }, line)))
          : null,
        todo.length
          ? h('div', { className: 'dp-todo' },
            h('div', { className: 'dp-todo-label' }, '可执行'),
            h('ul', null, todo.map((line, i) => h('li', { key: i }, line))))
          : null,
        data.url
          ? h('a', {
            className: 'dp-link', href: data.url, target: '_blank', rel: 'noreferrer',
          }, source === 'bilibili' ? '看视频 ↗' : source === 'jike' ? '查看原动态 ↗' : '查看原文 ↗')
          : null)
    }

    function Paper() {
      const [index, setIndex] = useState({ dates: [], latest: null })
      const [date, setDate] = useState(null)
      const [issue, setIssue] = useState(null)
      const [status, setStatus] = useState({ phase: 'loading', message: '' })

      const loadIndex = () => {
        api('/issues')
          .then((value) => {
            setIndex(value)
            setDate((current) => current || value.latest)
            if (!value.latest) setStatus({ phase: 'empty', message: '' })
          })
          .catch((error) => {
            const seed = SEED()
            if (seed && seed.index) {
              setIndex(seed.index)
              setDate((current) => current || seed.index.latest)
              return
            }
            setStatus({ phase: 'error', message: String(error.message || error) })
          })
      }

      useEffect(() => { loadIndex() }, [])

      useEffect(() => {
        if (!date) return
        let cancelled = false
        setStatus({ phase: 'loading', message: '' })
        setIssue(null)
        api(`/issue/${date}`)
          .then((value) => { if (!cancelled) { setIssue(value); setStatus({ phase: 'ready', message: '' }) } })
          .catch((error) => {
            if (cancelled) return
            const seed = SEED()
            const seeded = seed && seed.issues ? seed.issues[date] : null
            if (seeded) { setIssue(seeded); setStatus({ phase: 'ready', message: '' }); return }
            setStatus({ phase: error.message.includes('no-issue') ? 'empty' : 'error', message: String(error.message || error) })
          })
        return () => { cancelled = true }
      }, [date])

      const dates = index.dates || []
      const position = date ? dates.indexOf(date) : -1
      const newer = position > 0 ? dates[position - 1] : null
      const older = position >= 0 && position < dates.length - 1 ? dates[position + 1] : null
      const sections = useMemo(() => (issue && Array.isArray(issue.sections) ? issue.sections : []), [issue])
      const total = sections.reduce((sum, section) => sum + (section.items || []).length, 0)
      const edition = position >= 0 ? `第 ${dates.length - position} 期` : ''

      return h('div', null,
        h('header', { className: 'dp-masthead' },
          h('div', { className: 'dp-mast' },
            h('div', { className: 'dp-wordmark' }, TITLE),
            h('div', { className: 'dp-edition' },
              [edition, longDate(date), total ? `${total} 篇` : null].filter(Boolean).join('  ·  '))),
          h('div', { className: 'dp-tools' },
            h('button', { className: 'dp-btn', type: 'button', disabled: !newer, onClick: () => newer && setDate(newer) }, '上一期'),
            h('button', { className: 'dp-btn', type: 'button', disabled: !older, onClick: () => older && setDate(older) }, '下一期'),
            h('button', { className: 'dp-btn', type: 'button', onClick: () => { setDate(null); loadIndex() } }, '刷新'))),

        status.phase === 'error' ? h('div', { className: 'dp-error', style: { marginTop: '16px' } }, `读取失败：${status.message}`) : null,
        status.phase === 'loading' && !issue ? h('div', { className: 'dp-empty', style: { marginTop: '16px' } }, '正在排版…') : null,
        status.phase === 'empty' && !issue
          ? h('div', { className: 'dp-empty', style: { marginTop: '16px' } },
            date ? `${date} 休刊` : '还没有出版，等第一次采集。')
          : null,

        issue && issue.lead ? h('p', { className: 'dp-lead' }, issue.lead) : null,

        sections.map((section, sectionIndex) => h('section', { className: 'dp-sec', key: sectionIndex },
          h('div', { className: 'dp-sec-head' },
            h('span', { className: 'dp-sec-no' }, pad(sectionIndex + 1)),
            h('span', { className: 'dp-sec-name' }, section.label || section.source || '未分类'),
            h('span', { className: 'dp-sec-rule' }),
            h('span', { className: 'dp-sec-count' }, `${(section.items || []).length} 篇`)),
          section.note ? h('p', { className: 'dp-sec-note' }, section.note) : null,
          h('div', { className: 'dp-grid' },
            (section.items || []).map((item, itemIndex) => h(Item, { key: itemIndex, item, index: itemIndex, source: section.source }))))))
    }

    function Config() {
      const [config, setConfig] = useState(mergeConfig(null))
      const [state, setState] = useState({ phase: 'loading', message: '' })
      const [saved, setSaved] = useState('')

      useEffect(() => {
        api('/config')
          .then((value) => { setConfig(mergeConfig(value)); setState({ phase: 'ready', message: '' }) })
          .catch((error) => {
            const seed = SEED()
            if (seed && seed.config) { setConfig(mergeConfig(seed.config)); setState({ phase: 'seed', message: '' }); return }
            setState({ phase: 'error', message: String(error.message || error) })
          })
      }, [])

      const patch = (next) => setConfig((current) => ({ ...current, ...next }))
      const patchCookie = (key, value) =>
        setConfig((current) => ({ ...current, cookie: { ...current.cookie, [key]: value } }))
      const patchMonitor = (key, value) =>
        setConfig((current) => ({ ...current, monitor: { ...current.monitor, [key]: value } }))
      const setRow = (rowIndex, key, value) =>
        setConfig((current) => ({
          ...current,
          upMasters: current.upMasters.map((row, i) => (i === rowIndex ? { ...row, [key]: value } : row)),
        }))
      const addRow = () =>
        setConfig((current) => ({ ...current, upMasters: [...current.upMasters, { uid: '', name: '', category: 'finance' }] }))
      const removeRow = (rowIndex) =>
        setConfig((current) => ({ ...current, upMasters: current.upMasters.filter((_, i) => i !== rowIndex) }))

      const patchJike = (next) =>
        setConfig((current) => ({ ...current, sources: { ...current.sources, jike: { ...current.sources.jike, ...next } } }))
      const setJikeUser = (userIndex, key, value) =>
        patchJike({ users: config.sources.jike.users.map((row, i) => (i === userIndex ? { ...row, [key]: value } : row)) })
      const addJikeUser = () => patchJike({ users: [...config.sources.jike.users, { id: '', name: '' }] })
      const removeJikeUser = (userIndex) =>
        patchJike({ users: config.sources.jike.users.filter((_, i) => i !== userIndex) })
      const setTopic = (topicIndex, key, value) =>
        patchJike({ topics: config.sources.jike.topics.map((row, i) => (i === topicIndex ? { ...row, [key]: value } : row)) })
      const addTopic = () => patchJike({ topics: [...config.sources.jike.topics, { id: '', name: '' }] })
      const removeTopic = (topicIndex) =>
        patchJike({ topics: config.sources.jike.topics.filter((_, i) => i !== topicIndex) })

      const save = async () => {
        setState({ phase: 'saving', message: '' })
        setSaved('')
        try {
          const result = await api('/config', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(config),
          })
          setConfig(mergeConfig(result.config))
          setState({ phase: 'ready', message: '' })
          setSaved(`已保存 ${new Date().toLocaleTimeString()}`)
        } catch (error) {
          setState({ phase: 'error', message: String(error.message || error) })
        }
      }

      return h('div', { className: 'dp-form' },
        h('div', { className: 'dp-section-title' }, '出版'),
        h('label', { className: 'dp-row', style: { gap: '8px' } },
          h('input', {
            type: 'checkbox', checked: config.enabled,
            onChange: (event) => patch({ enabled: event.target.checked }),
          }),
          h('span', null, '每天 09:00 采集并出版')),

        h('div', { className: 'dp-section-title' }, 'B站账号'),
        h('div', { className: 'dp-field' },
          h('label', null, 'SESSDATA'),
          h('input', {
            className: 'dp-input', type: 'password', value: config.cookie.SESSDATA || '',
            placeholder: '浏览器 Cookie 里的 SESSDATA',
            onChange: (event) => patchCookie('SESSDATA', event.target.value),
          }),
          h('span', { className: 'dp-hint' }, '登录态，只存在本机 ~/.dsh/daily-paper/config.json。')),
        h('div', { className: 'dp-field' },
          h('label', null, 'bili_jct'),
          h('input', {
            className: 'dp-input', type: 'password', value: config.cookie.bili_jct || '',
            placeholder: 'CSRF token', onChange: (event) => patchCookie('bili_jct', event.target.value),
          })),
        h('div', { className: 'dp-field' },
          h('label', null, 'DedeUserID'),
          h('input', {
            className: 'dp-input', value: config.cookie.DedeUserID || '',
            placeholder: '你的 B站 uid', onChange: (event) => patchCookie('DedeUserID', event.target.value),
          })),

        h('div', { className: 'dp-section-title' }, `关注的 UP 主（${config.upMasters.length}）`),
        config.upMasters.length === 0
          ? h('div', { className: 'dp-hint' }, '还没有，点「添加一行」填 uid。')
          : config.upMasters.map((row, index) => h('div', { className: 'dp-row', key: index },
            h('input', {
              className: 'dp-input dp-uid', placeholder: 'uid', value: row.uid,
              onChange: (event) => setRow(index, 'uid', event.target.value),
            }),
            h('input', {
              className: 'dp-input dp-name', placeholder: '备注名', value: row.name,
              onChange: (event) => setRow(index, 'name', event.target.value),
            }),
            h('select', {
              className: 'dp-input dp-cat', value: row.category || 'finance',
              onChange: (event) => setRow(index, 'category', event.target.value),
            },
              h('option', { value: 'finance' }, '财经'),
              h('option', { value: 'ai_tools' }, 'AI 工具'),
              h('option', { value: 'other' }, '其他')),
            h('button', { className: 'dp-btn', type: 'button', onClick: () => removeRow(index) }, '删除'))),
        h('div', { className: 'dp-row' },
          h('button', { className: 'dp-btn', type: 'button', onClick: addRow }, '添加一行')),

        h('div', { className: 'dp-section-title' }, '即刻'),
        h('label', { className: 'dp-row', style: { gap: '8px' } },
          h('input', {
            type: 'checkbox', checked: config.sources.jike.enabled,
            onChange: (event) => patchJike({ enabled: event.target.checked }),
          }),
          h('span', null, '把即刻圈子/关注的人收进日报')),
        h('div', { className: 'dp-hint', style: { marginBottom: '10px' } },
          '只读公开内容，不需要登录态；圈子 id 在 web.okjike.com/topic/<id> 里，抓取时名字会自动补全。'),

        h('div', { className: 'dp-field' },
          h('label', null, '我想关注什么（每行一条）'),
          h('textarea', {
            className: 'dp-input', rows: 3,
            value: config.sources.jike.interests.join('\n'),
            placeholder: 'SEO/GEO 有哪些新技术\nAI 又出了什么新玩具\n股市里大家在赚钱还是亏钱',
            onChange: (event) => patchJike({ interests: event.target.value.split('\n').map((line) => line.trim()).filter(Boolean) }),
          }),
          h('span', { className: 'dp-hint' }, '采集后由模型按这几行挑值得看的，不是把圈子动态原样搬过来。')),

        h('div', { className: 'dp-section-title' }, `圈子（${config.sources.jike.topics.length}）`),
        config.sources.jike.topics.length === 0
          ? h('div', { className: 'dp-hint' }, '还没有，点「添加圈子」填 id。')
          : config.sources.jike.topics.map((row, index) => h('div', { className: 'dp-row', key: index },
            h('input', {
              className: 'dp-input dp-uid', placeholder: '圈子 id', value: row.id,
              onChange: (event) => setTopic(index, 'id', event.target.value),
            }),
            h('input', {
              className: 'dp-input dp-name', placeholder: '备注名（可留空）', value: row.name,
              onChange: (event) => setTopic(index, 'name', event.target.value),
            }),
            h('button', { className: 'dp-btn', type: 'button', onClick: () => removeTopic(index) }, '删除'))),
        h('div', { className: 'dp-row' },
          h('button', { className: 'dp-btn', type: 'button', onClick: addTopic }, '添加圈子')),

        h('div', { className: 'dp-section-title' }, `关注的人（${config.sources.jike.users.length}，可留空）`),
        config.sources.jike.users.map((row, index) => h('div', { className: 'dp-row', key: index },
          h('input', {
            className: 'dp-input dp-uid', placeholder: '用户 id', value: row.id,
            onChange: (event) => setJikeUser(index, 'id', event.target.value),
          }),
          h('input', {
            className: 'dp-input dp-name', placeholder: '备注名', value: row.name,
            onChange: (event) => setJikeUser(index, 'name', event.target.value),
          }),
          h('button', { className: 'dp-btn', type: 'button', onClick: () => removeJikeUser(index) }, '删除'))),
        h('div', { className: 'dp-row' },
          h('button', { className: 'dp-btn', type: 'button', onClick: addJikeUser }, '添加一位')),

        h('div', { className: 'dp-row', style: { gap: '6px', marginTop: '8px' } },
          h('span', { className: 'dp-hint' }, '每个圈子取最近'),
          h('input', {
            className: 'dp-input', type: 'number', min: 1, max: 30, style: { width: '72px' },
            value: config.sources.jike.maxPerTopic,
            onChange: (event) => patchJike({ maxPerTopic: Number(event.target.value) }),
          }),
          h('span', { className: 'dp-hint' }, '条，回看'),
          h('input', {
            className: 'dp-input', type: 'number', min: 1, max: 30, style: { width: '72px' },
            value: config.sources.jike.lookbackDays,
            onChange: (event) => patchJike({ lookbackDays: Number(event.target.value) }),
          }),
          h('span', { className: 'dp-hint' }, '天')),

        h('div', { className: 'dp-section-title' }, '采集参数'),
        h('div', { className: 'dp-row' },
          h('span', { className: 'dp-hint' }, '每个 UP 主取最近'),
          h('input', {
            className: 'dp-input', type: 'number', min: 1, max: 20, style: { width: '72px' },
            value: config.monitor.maxVideosPerUp,
            onChange: (event) => patchMonitor('maxVideosPerUp', Number(event.target.value)),
          }),
          h('span', { className: 'dp-hint' }, '条，回看'),
          h('input', {
            className: 'dp-input', type: 'number', min: 1, max: 30, style: { width: '72px' },
            value: config.monitor.lookbackDays,
            onChange: (event) => patchMonitor('lookbackDays', Number(event.target.value)),
          }),
          h('span', { className: 'dp-hint' }, '天')),

        h('div', { className: 'dp-save' },
          h('button', { className: 'dp-btn dp-primary', type: 'button', disabled: state.phase === 'saving', onClick: save },
            state.phase === 'saving' ? '保存中…' : '保存'),
          saved ? h('span', { className: 'dp-ok' }, saved) : null,
          state.phase === 'error' ? h('span', { className: 'dp-error', style: { padding: 0, border: 0 } }, state.message) : null))
    }

    function Panel() {
      const [tab, setTab] = useState('paper')
      return h('div', { className: 'dp-root' },
        h('div', { className: 'dp-tabs' },
          h('button', { className: 'dp-tab', type: 'button', 'data-on': tab === 'paper' ? '1' : '0', onClick: () => setTab('paper') }, '本期'),
          h('button', { className: 'dp-tab', type: 'button', 'data-on': tab === 'config' ? '1' : '0', onClick: () => setTab('config') }, '配置')),
        tab === 'paper' ? h(Paper) : h(Config))
    }

    function PaperIcon(props) {
      const size = props && typeof props.size === 'number' ? props.size : 16
      return h('svg', {
        width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
        strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true,
        style: { display: 'block' },
      },
        h('rect', { x: 3.5, y: 4.5, width: 17, height: 15, rx: 2.2 }),
        h('path', { d: 'M7 8.5h6M7 12h6M7 15.5h4' }),
        h('rect', { x: 15, y: 9, width: 3.2, height: 6.5, rx: 0.8 }))
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        const style = document.createElement('style')
        style.setAttribute('data-plugin-css', 'dsh-daily-paper')
        style.textContent = CSS
        document.head.appendChild(style)
        ctx.effect(() => () => style.remove(), 'daily-paper: 页面样式')

        const slots = (typeof ctx.get === 'function' ? ctx.get('slots') : undefined) || ctx.slots
        if (!slots) return

        slots.inject('sidebar.panellist', () => slots.register({
          name: 'sidebar.panellist',
          id: 'daily-paper',
          order: 30,
          label: TITLE,
        }, PaperIcon))

        slots.inject('main', () => slots.register({
          name: 'main',
          key: 'daily-paper',
        }, Panel))

        slots.inject('settings.section', () => slots.register(
          { name: 'settings.section', id: 'daily-paper', order: 35, label: TITLE },
          () => h(Panel),
        ))
      },
    }
  },
})
