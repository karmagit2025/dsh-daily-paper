/**
 * Host half of dsh-daily-paper.
 *
 * Owns two things:
 *  - the issue files the daily collector writes (~/.dsh/daily-paper/issues/<YYYY-MM-DD>.json);
 *  - the plugin's own config (~/.dsh/daily-paper/config.json): B站 cookie, the UP
 *    master list, and monitor knobs the Settings page edits.
 *
 * Both are served over /api/daily-paper/* for the browser half.
 */
import { promises as fsp } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

export const inject = ['webServer']

const ROUTE_PREFIX = '/api/daily-paper'
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

const DEFAULT_CONFIG = {
  enabled: true,
  cookie: { SESSDATA: '', bili_jct: '', DedeUserID: '' },
  upMasters: [],
  monitor: { maxVideosPerUp: 3, lookbackDays: 1 },
  sources: {
    bilibili: { enabled: true },
    jike: { enabled: false, lookbackDays: 3, maxPerTopic: 10, interests: [], topics: [], users: [] },
  },
}

/// 期文件（可以放进 git 仓库，两台机器共享）
/// 期文件目录（本机运行目录；仓库里那份由 sync 脚本镜像回这里）
function issuesRoot(config) {
  const configured = typeof config?.dataDir === 'string' ? config.dataDir.trim() : ''
  return configured || join(homedir(), '.dsh', 'daily-paper')
}

/// 本机配置（B站 cookie、UP 名单）——永远只在本机，不进仓库
function configFile(config) {
  const configured = typeof config?.configPath === 'string' ? config.configPath.trim() : ''
  return configured || join(homedir(), '.dsh', 'daily-paper', 'config.json')
}

function sendJson(res, status, value) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.setHeader('Cache-Control', 'no-store')
  res.end(JSON.stringify(value))
}

async function readJsonFile(file, fallback) {
  try {
    const text = await fsp.readFile(file, 'utf8')
    return JSON.parse(text)
  } catch (error) {
    if (error?.code === 'ENOENT') return fallback
    throw error
  }
}

async function writeJsonFile(file, value) {
  await fsp.mkdir(join(file, '..'), { recursive: true })
  await fsp.writeFile(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8')
}

async function readBody(req) {
  const chunks = []
  let size = 0
  for await (const chunk of req) {
    size += chunk.length
    if (size > 1024 * 1024) throw new Error('body too large')
    chunks.push(chunk)
  }
  if (chunks.length === 0) return {}
  return JSON.parse(Buffer.concat(chunks).toString('utf8'))
}

function normalizeConfig(input, previous) {
  const base = { ...DEFAULT_CONFIG, ...(previous || {}) }
  const next = { ...base }

  if (typeof input.enabled === 'boolean') next.enabled = input.enabled

  if (input.cookie && typeof input.cookie === 'object') {
    const cookie = { ...base.cookie }
    for (const key of ['SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5', 'sid', 'buvid3', 'buvid4']) {
      const value = input.cookie[key]
      if (typeof value === 'string') cookie[key] = value.trim()
    }
    next.cookie = cookie
  }

  if (Array.isArray(input.upMasters)) {
    next.upMasters = input.upMasters
      .map((entry) => ({
        uid: String(entry?.uid ?? '').trim(),
        name: String(entry?.name ?? '').trim(),
        category: String(entry?.category ?? 'finance').trim() || 'finance',
      }))
      .filter((entry) => /^\d{1,20}$/.test(entry.uid))
  }

  if (input.sources && typeof input.sources === 'object') {
    const sources = { ...base.sources }
    if (input.sources.bilibili && typeof input.sources.bilibili === 'object') {
      sources.bilibili = { enabled: input.sources.bilibili.enabled !== false }
    }
    if (input.sources.jike && typeof input.sources.jike === 'object') {
      const jike = input.sources.jike
      const rows = (list) => (Array.isArray(list) ? list : [])
        .map((entry) => ({
          id: String(entry?.id ?? '').trim(),
          name: String(entry?.name ?? '').trim(),
        }))
        .filter((entry) => entry.id.length > 0 && entry.id.length <= 64)
      const interests = (Array.isArray(jike.interests) ? jike.interests : [])
        .map((line) => String(line ?? '').trim())
        .filter((line) => line.length > 0 && line.length <= 120)
      const lookback = Number(jike.lookbackDays)
      const cap = Number(jike.maxPerTopic)
      sources.jike = {
        enabled: jike.enabled === true,
        lookbackDays: Number.isFinite(lookback) && lookback >= 1 && lookback <= 30 ? Math.floor(lookback) : 3,
        maxPerTopic: Number.isFinite(cap) && cap >= 1 && cap <= 30 ? Math.floor(cap) : 10,
        interests: interests.slice(0, 12),
        topics: rows(jike.topics),
        users: rows(jike.users),
      }
    }
    next.sources = sources
  }

  if (input.monitor && typeof input.monitor === 'object') {
    const monitor = { ...base.monitor }
    const max = Number(input.monitor.maxVideosPerUp)
    const lookback = Number(input.monitor.lookbackDays)
    if (Number.isFinite(max) && max >= 1 && max <= 20) monitor.maxVideosPerUp = Math.floor(max)
    if (Number.isFinite(lookback) && lookback >= 1 && lookback <= 30) monitor.lookbackDays = Math.floor(lookback)
    next.monitor = monitor
  }

  return next
}

export function apply(ctx, config) {
  const issuesDir = join(issuesRoot(config), 'issues')
  const configPath = configFile(config)

  // Index render is synchronous, so the newest issues are kept in memory and
  // pushed into the page as a global at startup. The routes stay the live
  // source; this seed covers a renderer that cannot fetch them.
  const seed = { index: { dates: [], latest: null }, issues: {}, config: DEFAULT_CONFIG }

  const loadConfig = async () => normalizeConfig(await readJsonFile(configPath, DEFAULT_CONFIG), DEFAULT_CONFIG)

  const listDates = async () => {
    let names
    try {
      names = await fsp.readdir(issuesDir)
    } catch (error) {
      if (error?.code === 'ENOENT') return []
      throw error
    }
    return names
      .filter((name) => name.endsWith('.json') && DATE_RE.test(name.slice(0, -5)))
      .map((name) => name.slice(0, -5))
      .sort()
      .reverse()
  }

  const refreshSeed = async () => {
    try {
      const dates = await listDates()
      seed.index = { dates: dates.slice(0, 30), latest: dates[0] ?? null }
      const issues = {}
      for (const date of dates.slice(0, 5)) issues[date] = await readJsonFile(join(issuesDir, `${date}.json`), null)
      seed.issues = issues
      seed.config = await loadConfig()
    } catch {
      /* keep the previous seed */
    }
  }

  ctx.effect(() => {
    void refreshSeed()
    const timer = setInterval(() => { void refreshSeed() }, 5 * 60 * 1000)
    return () => clearInterval(timer)
  }, 'daily-paper: issue cache')

  ctx.effect(() => ctx.on('webserver/index-inject', (table) => {
    table.push({ kind: 'global', name: '__DAILY_PAPER__', value: seed })
  }), 'daily-paper: index seed')

  ctx.effect(() => ctx.webServer.register({
    kind: 'prefix',
    path: ROUTE_PREFIX,
    handler: async (req, res) => {
      const pathname = new URL(String(req.url), 'http://localhost').pathname
      const rest = pathname.slice(ROUTE_PREFIX.length).replace(/^\//, '')
      const method = req.method || 'GET'

      try {
        // --- config -----------------------------------------------------
        if (rest === 'config') {
          if (method === 'GET' || method === 'HEAD') {
            sendJson(res, 200, await loadConfig())
            return
          }
          if (method === 'POST') {
            const body = await readBody(req)
            const previous = await loadConfig()
            const next = normalizeConfig(body, previous)
            await writeJsonFile(configPath, next)
            seed.config = next
            sendJson(res, 200, { ok: true, config: next })
            return
          }
          res.statusCode = 405
          res.setHeader('Allow', 'GET, HEAD, POST')
          res.end()
          return
        }

        if (method !== 'GET' && method !== 'HEAD') {
          res.statusCode = 405
          res.setHeader('Allow', 'GET, HEAD')
          res.end()
          return
        }

        // --- issues -----------------------------------------------------
        if (rest === 'issues' || rest === '') {
          const dates = await listDates()
          sendJson(res, 200, { dates, latest: dates[0] ?? null })
          return
        }

        const match = /^issue\/(\d{4}-\d{2}-\d{2})$/.exec(rest)
        if (!match) {
          sendJson(res, 404, { error: 'not-found' })
          return
        }

        const issue = await readJsonFile(join(issuesDir, `${match[1]}.json`), null)
        if (!issue) {
          sendJson(res, 404, { error: 'no-issue', date: match[1] })
          return
        }
        sendJson(res, 200, issue)
      } catch (error) {
        sendJson(res, 500, { error: 'failed', detail: String(error?.message ?? error) })
      }
    },
  }), 'daily-paper: routes')
}
