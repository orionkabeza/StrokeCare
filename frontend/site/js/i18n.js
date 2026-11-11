// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// English, Kinyarwanda and French. English is the fallback, so a missing translation never shows a blank.
// The French and Kinyarwanda texts are AI drafts: a native speaker must review them (docs/OPEN_QUESTIONS.md).
// The texts live in /locales/<code>.json (Erica owns them). t('a.b') finds a text; "{n}" is filled from the params;
// a text written as "one | other" picks a form by the count passed as the third argument.
import { setApiLocale } from './api.js'
import { signal } from './state.js'

export const LOCALES = [
  { code: 'en', name: 'English' },
  { code: 'rw', name: 'Ikinyarwanda' },
  { code: 'fr', name: 'Français' },
]

const messages = { en: {}, fr: {}, rw: {} }
export const locale = signal('en')

function lookup(table, key) {
  let node = table
  for (const part of key.split('.')) {
    if (node === null || typeof node !== 'object') return undefined
    node = node[part]
  }
  return typeof node === 'string' ? node : undefined
}

export function t(key, params = {}, count) {
  let text = lookup(messages[locale.value], key) ?? lookup(messages.en, key) ?? key
  if (count !== undefined && text.includes('|')) {
    const forms = text.split('|').map((s) => s.trim())
    text = forms[count === 1 ? 0 : 1] ?? forms[0]
  }
  return text.replace(/\{(\w+)\}/g, (whole, name) => (name in params ? String(params[name]) : whole))
}

export function initialLocale() {
  let saved = null
  try {
    saved = localStorage.getItem('sc-locale')
  } catch {
    /* ignore */
  }
  const guess = saved ?? globalThis.navigator?.language?.slice(0, 2)
  return LOCALES.some((l) => l.code === guess) ? guess : 'en'
}

async function load(code) {
  if (Object.keys(messages[code]).length) return
  const response = await fetch(`/locales/${code}.json`)
  if (response.ok) messages[code] = await response.json()
}

/** Use a language. Loads its texts (and English, the fallback) first. */
export async function setLocale(code) {
  await Promise.all([load('en'), load(code)])
  if (globalThis.document) document.documentElement.lang = code
  setApiLocale(code)
  try {
    localStorage.setItem('sc-locale', code)
  } catch {
    /* ignore */
  }
  locale.value = code
}

/** For tests: put texts in without fetching. */
export function useMessages(code, table) {
  messages[code] = table
}
