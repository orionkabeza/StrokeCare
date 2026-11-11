// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// An OPTIONAL copy of the person's own plan on this phone, so it can be read without a connection.
// Privacy rules, because phones are often shared:
//   * OFF by default. The person turns it on in Settings and is told it stays on the phone until sign-out.
//   * Only a short list of the person's OWN data is ever kept (see ALLOWED). Blood pressure, check-in answers and
//     messages are never copied. Other people's records are never copied.
//   * Wiped when the person signs out, when the session ends, and when they turn the setting off.
import { signal } from './state.js'

const FLAG = 'sc-offline-copy'
const PREFIX = 'sc-copy:'
const MAX_BYTES = 200_000

/** Paths the copy may hold: the person's own plan, medicines, appointments, goals, stages, phrases, movement, and
 *  who is signed in (`/me/`), so the app can open without a connection. */
const ALLOWED =
  /^\/(patients\/me\/(plan|medications|calendar|goals|phases|phrases|mobility|progress)|me\/(care-team|reminders\/upcoming)|me)\/?$/

let owner = null

function readFlag() {
  try {
    return localStorage.getItem(FLAG) === '1'
  } catch {
    return false
  }
}

export const copyEnabled = signal(readFlag())
/** True while the screen is showing a saved copy because the phone could not reach the server. */
export const showingCopy = signal(false)

export function setCopyOwner(userId) {
  owner = userId
}

export function setCopyEnabled(on) {
  copyEnabled.value = on
  try {
    if (on) localStorage.setItem(FLAG, '1')
    else localStorage.removeItem(FLAG)
  } catch {
    /* storage blocked: the setting simply will not stick */
  }
  if (!on) wipeCopies()
}

export function wipeCopies() {
  showingCopy.value = false
  try {
    for (const key of Object.keys(localStorage)) if (key.startsWith(PREFIX)) localStorage.removeItem(key)
  } catch {
    /* nothing to remove */
  }
}

// `/me/` is stored in one fixed slot: only one person is ever signed in on a phone, and sign-out wipes it.
const slotOwner = (path) => (path === '/me/' ? 'self' : owner)

function keyFor(path, query) {
  const q = Object.entries(query ?? {})
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${k}=${String(v)}`)
    .sort()
    .join('&')
  return `${PREFIX}${slotOwner(path)}:${path}?${q}`
}

const eligible = (path) => copyEnabled.value && (path === '/me/' || !!owner) && ALLOWED.test(path)

export function saveCopy(path, query, data) {
  if (!eligible(path)) return
  try {
    const text = JSON.stringify(data)
    if (text.length <= MAX_BYTES) localStorage.setItem(keyFor(path, query), text)
  } catch {
    /* full or blocked: skip the copy, the live data still works */
  }
}

export function readCopy(path, query) {
  if (!eligible(path)) return null
  try {
    const text = localStorage.getItem(keyFor(path, query))
    return text === null ? null : JSON.parse(text)
  } catch {
    return null
  }
}
