// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Safe HTML templates and a few DOM helpers. There is no framework: a screen is a function that returns HTML.
// Every value placed in a template is escaped automatically, so text from people or the server can never become
// markup. To insert markup you wrote yourself (an icon, a nested template), wrap it with raw() or build it with html``.
const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }

export const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ENTITIES[c])

class Raw {
  constructor(text) {
    this.text = text
  }
  toString() {
    return this.text
  }
}

/** Mark a string as trusted markup. Only use it on markup this code built. */
export const raw = (text) => new Raw(String(text))

function part(value) {
  if (value instanceof Raw) return value.text
  if (Array.isArray(value)) return value.map(part).join('')
  if (value === false || value === null || value === undefined) return ''
  return esc(value)
}

/** Tagged template: html`<p>${text}</p>`. Values are escaped; nested html`` and arrays are kept as markup. */
export function html(strings, ...values) {
  let out = strings[0]
  values.forEach((v, i) => {
    out += part(v) + strings[i + 1]
  })
  return new Raw(out)
}

/** "true" or "false" for an aria attribute (a plain false would be dropped). */
export const flag = (value) => (value ? 'true' : 'false')

export const $ = (selector, root = document) => root.querySelector(selector)
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)]

/** One listener on `root` for every matching child, now and after the screen is redrawn. */
export function on(root, type, selector, handler) {
  root.addEventListener(type, (event) => {
    const el = event.target instanceof Element ? event.target.closest(selector) : null
    if (el && root.contains(el)) handler(el, event)
  })
}

export const formObject = (form) => Object.fromEntries(new FormData(form).entries())

/** Today as YYYY-MM-DD in the browser's own time zone. */
export function isoDay(date = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}`
}
