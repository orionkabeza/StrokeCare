// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Who is signed in, and the display and input preferences. Both announce changes so the page can redraw.
import { API_BASE, ApiError, api, onLogout, tokens } from './api.js'
import { setCopyOwner, wipeCopies } from './copy.js'
import { clearQueue, flush } from './offline.js'
import { signal } from './state.js'

// ---------------------------------------------------------------- who is signed in
const HOMES = { caregiver: '/care', clinician: '/doctor', chw: '/chw', admin: '/settings' }

export const auth = {
  user: null,
  consents: {},
  ready: false,
  /** Changes every time the signed-in person changes, so the page chrome can redraw. */
  changed: signal(0),

  get signedIn() {
    return !!this.user
  },
  get role() {
    return this.user?.role
  },
  get isPatient() {
    return this.role === 'survivor' || this.role === 'prevention'
  },
  get needsConsent() {
    return Object.values(this.consents).some((c) => !c.granted)
  },
  get home() {
    return HOMES[this.role] ?? '/today'
  },

  apply(data) {
    if (data.access && data.refresh) tokens.set(data.access, data.refresh)
    this.user = data.user
    this.consents = data.consents
    setCopyOwner(data.user.id) // a saved copy belongs to one person and is never shown to another
    this.changed.value++
  },

  async load() {
    if (tokens.access || tokens.refresh) {
      try {
        this.apply(await api.get('/me/'))
        this.syncOutbox()
      } catch (err) {
        // Only end the session when the server says the login is no longer valid. No signal, or a server that is
        // briefly down, must never sign someone out: they could not sign back in until they were online again.
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) tokens.clear()
      }
    }
    this.ready = true
  },

  async login(email, password) {
    this.apply(await api.post('/auth/login/', { email, password }, { auth: false }))
    this.syncOutbox()
  },

  async register(body) {
    this.apply(await api.post('/auth/register/', body, { auth: false }))
  },

  async giveConsent(kind, accept = true) {
    this.consents = await api.post('/me/consents/', { kind, accept })
    this.changed.value++
  },

  forget() {
    this.user = null
    this.consents = {}
    tokens.clear()
    clearQueue()
    setCopyOwner(null)
    wipeCopies() // the saved copy never outlives the sign-in
    this.changed.value++
  },

  async logout() {
    const refresh = tokens.refresh
    try {
      if (refresh) await api.post('/auth/logout/', { refresh })
    } finally {
      this.forget()
    }
  },

  async syncOutbox() {
    await flush((item) =>
      fetch(`${API_BASE}${item.path}`, {
        method: item.method,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokens.access}` },
        body: JSON.stringify(item.body),
      }),
    )
  },
}

onLogout(() => auth.forget())
if (globalThis.addEventListener) globalThis.addEventListener('online', () => auth.user && auth.syncOutbox())

// ---------------------------------------------------------------- preferences
// Saved to the account (so they follow the person) and to the phone (so they apply before signing in). Applied to
// <html> as data attributes the design tokens read.
const KEY = 'sc-prefs'
export const PREF_DEFAULTS = {
  theme: 'system',
  high_contrast: false,
  easy_read_font: false,
  reduce_motion: false,
  text_scale: 100,
  audio_first: false,
  one_question_at_a_time: false,
  one_handed_layout: false,
  low_data_mode: false,
}

function stored() {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '{}')
  } catch {
    return {}
  }
}

export const prefs = {
  values: { ...PREF_DEFAULTS, ...stored() },
  /** Changes every time a preference changes, so open screens can redraw. */
  changed: signal(0),

  applyToPage() {
    if (!globalThis.document) return
    const root = document.documentElement
    const v = this.values
    const dark = v.theme === 'dark' || (v.theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches)
    root.dataset.theme = v.high_contrast ? 'contrast' : dark ? 'dark' : 'light'
    root.dataset.font = v.easy_read_font ? 'easy' : 'standard'
    root.dataset.motion = v.reduce_motion ? 'reduce' : 'full'
    root.dataset.hand = v.one_handed_layout ? 'one' : 'two'
    root.style.fontSize = `${v.text_scale}%`
  },

  save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(this.values))
    } catch {
      /* not saved on this phone; the account still has them */
    }
    this.applyToPage()
    this.changed.value++
  },

  async loadFromAccount() {
    Object.assign(this.values, await api.get('/me/accessibility/'))
    this.save()
  },

  async set(key, value, signedIn) {
    this.values[key] = value
    this.save()
    if (signedIn) await api.patch('/me/accessibility/', { [key]: value })
  },
}

if (globalThis.document) {
  prefs.applyToPage()
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => prefs.applyToPage())
}
