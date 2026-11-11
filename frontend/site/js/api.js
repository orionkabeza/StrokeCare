// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// One way to talk to the API: adds the token, refreshes it once when it expires, turns errors into plain sentences,
// and queues a few kinds of entries when the phone is offline so nothing typed is lost.
import { readCopy, saveCopy, showingCopy } from './copy.js'
import { enqueue } from './offline.js'

export const API_BASE = '/api/v1'
const ACCESS = 'sc-access'
const REFRESH = 'sc-refresh'

export class ApiError extends Error {
  constructor(status, code, message, fields = {}) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

/** Set by the app so requests carry the chosen language. */
let currentLocale = 'en'
export function setApiLocale(locale) {
  currentLocale = locale
}

let onSessionLost = () => {}
export function onLogout(callback) {
  onSessionLost = callback
}

function safeGet(key) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
function safeSet(key, value) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* private mode: the session lasts until the tab closes */
  }
}

export const tokens = {
  get access() {
    return safeGet(ACCESS)
  },
  get refresh() {
    return safeGet(REFRESH)
  },
  set(access, refresh) {
    safeSet(ACCESS, access)
    safeSet(REFRESH, refresh)
  },
  clear() {
    safeSet(ACCESS, null)
    safeSet(REFRESH, null)
  },
}

let refreshing = null
async function refreshTokens() {
  const refresh = tokens.refresh
  if (!refresh) return false
  refreshing ??= (async () => {
    try {
      const r = await fetch(`${API_BASE}/auth/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      })
      if (!r.ok) return false
      const data = await r.json()
      tokens.set(data.access, data.refresh ?? refresh) // the server rotates refresh tokens
      return true
    } catch {
      return false
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

function buildUrl(path, query) {
  const origin = globalThis.location?.origin ?? 'http://localhost'
  const url = new URL(`${API_BASE}${path}`, origin)
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v))
  }
  return url.toString()
}

/**
 * options: { body, query, form, queueable (queue this write if the phone is offline), raw (return the Response),
 *            auth (false for sign-in) }
 */
export async function request(method, path, opts = {}, retried = false) {
  const headers = { 'Accept-Language': currentLocale }
  if (opts.auth !== false && tokens.access) headers.Authorization = `Bearer ${tokens.access}`
  let body
  if (opts.form) body = opts.form
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }

  let response
  try {
    response = await fetch(buildUrl(path, opts.query), { method, headers, body })
  } catch {
    if (method === 'GET' && !opts.raw) {
      const copy = readCopy(path, opts.query) // only when the person turned on "keep my plan on this phone"
      if (copy !== null) {
        showingCopy.value = true
        return copy
      }
    }
    if (opts.queueable && method !== 'GET') {
      enqueue({ method, path, body: opts.body })
      return { queued: true }
    }
    throw new ApiError(0, 'offline', 'You seem to be offline. Please try again when you have a connection.')
  }

  if (response.status === 401 && !retried && opts.auth !== false && tokens.refresh) {
    if (await refreshTokens()) return request(method, path, opts, true)
    tokens.clear()
    onSessionLost()
  }
  if (opts.raw && response.ok) return response
  if (response.status === 204) return undefined
  const data = await response.json().catch(() => ({}))
  if (response.ok && method === 'GET') {
    showingCopy.value = false
    saveCopy(path, opts.query, data)
  }
  if (!response.ok) {
    const e = data?.error ?? {}
    throw new ApiError(response.status, e.code ?? 'error', e.message ?? 'Something went wrong.', e.fields ?? {})
  }
  return data
}

export const api = {
  get: (path, query) => request('GET', path, { query }),
  post: (path, body, opts = {}) => request('POST', path, { ...opts, body }),
  patch: (path, body) => request('PATCH', path, { body }),
  del: (path, body, query) => request('DELETE', path, { body, query }),
  upload: (path, form) => request('POST', path, { form }),
  /** Fetch a protected file (audio, export) as a Blob, with the token. */
  async blob(path) {
    const r = await request('GET', path, { raw: true })
    return r.blob()
  },
}

/** First message for a field, or the general message, for showing under a form. */
export function errorText(err, field) {
  if (err instanceof ApiError) {
    if (field && err.fields[field]?.length) return err.fields[field][0]
    const first = Object.values(err.fields)[0]
    if (!field && first?.length) return Array.isArray(first) ? String(first[0]) : String(first)
    return err.message
  }
  return 'Something went wrong.'
}
