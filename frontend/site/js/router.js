// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// A small router on the browser's History API. Each screen is a module whose default export draws it.
// A screen receives a context: ctx.params, ctx.query, ctx.draw(html), ctx.on(event, selector, handler), ctx.go(path),
// plus ctx.base / ctx.isSelf / ctx.link() for screens that show someone's record (/p/:ref/...).
import { api } from './api.js'
import { $$, on } from './dom.js'
import { locale } from './i18n.js'
import { auth, prefs } from './store.js'
import { toast } from './ui.js'

const PATIENT = ['prevention', 'survivor']
const MEMBERS = ['caregiver', 'clinician', 'chw']

/** The route table. `public` screens need no sign-in; `roles` limits a screen to some kinds of account. */
export const ROUTES = [
  { path: '/welcome', view: () => import('./views/shared/welcome.js'), public: true },
  { path: '/login', view: () => import('./views/auth/login.js'), public: true },
  { path: '/register', view: () => import('./views/auth/register.js'), public: true },
  { path: '/emergency', view: () => import('./views/shared/emergency.js'), public: true },
  { path: '/talk', view: () => import('./views/shared/talk-board.js'), public: true },
  { path: '/learn', view: () => import('./views/shared/learn.js'), public: true },
  { path: '/learn/:slug', view: () => import('./views/shared/learn-item.js'), public: true },
  { path: '/consent', view: () => import('./views/auth/consent.js') },
  { path: '/today', view: () => import('./views/patient/today.js'), roles: PATIENT },
  { path: '/p/:ref/recovery', view: () => import('./views/patient/recovery.js') },
  { path: '/p/:ref/mobility', view: () => import('./views/patient/mobility.js') },
  { path: '/p/:ref/progress', view: () => import('./views/patient/progress.js') },
  { path: '/p/:ref/phrases', view: () => import('./views/patient/phrases.js') },
  { path: '/care-team', view: () => import('./views/patient/care-team.js'), roles: PATIENT },
  { path: '/reminders', view: () => import('./views/patient/reminders.js'), roles: PATIENT },
  { path: '/doctor', view: () => import('./views/clinician/doctor-home.js'), roles: ['clinician'] },
  { path: '/p/:ref/checkin', view: () => import('./views/patient/check-in.js') },
  { path: '/p/:ref/bp', view: () => import('./views/patient/blood-pressure.js') },
  { path: '/p/:ref/medicines', view: () => import('./views/patient/medicines.js') },
  { path: '/p/:ref/visit', view: () => import('./views/patient/visit-prep.js') },
  { path: '/p/:ref/calendar', view: () => import('./views/care/calendar.js') },
  { path: '/p/:ref/messages', view: () => import('./views/shared/thread.js') },
  { path: '/p/:ref/summary', view: () => import('./views/clinician/summary.js') },
  { path: '/p/:ref/home-visit', view: () => import('./views/chw/home-visit.js'), roles: ['chw'] },
  { path: '/care', view: () => import('./views/care/caregiver-home.js'), roles: ['caregiver'] },
  { path: '/caseload', view: () => import('./views/clinician/caseload.js'), roles: ['clinician'] },
  { path: '/templates', view: () => import('./views/clinician/templates.js'), roles: ['clinician'] },
  { path: '/chw', view: () => import('./views/chw/chw-home.js'), roles: ['chw'] },
  { path: '/inbox', view: () => import('./views/shared/inbox.js'), roles: [...PATIENT, ...MEMBERS] },
  { path: '/sharing', view: () => import('./views/shared/sharing.js') },
  { path: '/settings', view: () => import('./views/shared/settings.js') },
]

const compiled = ROUTES.map((route) => {
  const names = []
  const pattern = route.path.replace(/:(\w+)/g, (_, name) => {
    names.push(name)
    return '([^/]+)'
  })
  return { route, names, regex: new RegExp(`^${pattern}/?$`) }
})

export function match(pathname) {
  for (const { route, names, regex } of compiled) {
    const m = regex.exec(pathname)
    if (m) return { route, params: Object.fromEntries(names.map((n, i) => [n, decodeURIComponent(m[i + 1])])) }
  }
  return null
}

/** Where a signed-in or signed-out person should go instead, or null when they may see this screen. */
export function guard(pathname, found) {
  if (pathname === '/' || pathname === '/welcome') return auth.signedIn ? auth.home : null
  if (!found) return '/'
  if (found.route.public) return null
  if (!auth.signedIn) return `/login?next=${encodeURIComponent(pathname)}`
  if (auth.needsConsent && pathname !== '/consent' && pathname !== '/settings') return '/consent'
  if (found.route.roles && !found.route.roles.includes(auth.role)) return auth.home
  return null
}

let current = { path: '/', route: null }
const listeners = new Set()
export const onRouteChange = (fn) => listeners.add(fn)
export const currentPath = () => current.path

// ---------------------------------------------------------------- drawing a screen
const focusPath = (root, el) => {
  const path = []
  for (let n = el; n && n !== root; n = n.parentElement) path.unshift([...n.parentElement.children].indexOf(n))
  return path
}
const nodeAt = (root, path) => path.reduce((n, i) => n?.children[i], root)

/** Draw a screen's markup. Keeps what the person typed and which control had focus, so redrawing is invisible. */
function drawInto(el, fragment) {
  const active = document.activeElement
  const focus = active && el.contains(active) && active !== el ? { path: focusPath(el, active), tag: active.tagName } : null
  const typed = new Map()
  $$('input[name], textarea[name], select[name]', el).forEach((f) => {
    if (f.type === 'checkbox' || f.type === 'radio') typed.set(`${f.name}:${f.value}`, f.checked)
    else if (f.type !== 'file') typed.set(f.name, f.value)
  })
  el.innerHTML = String(fragment)
  $$('input[name], textarea[name], select[name]', el).forEach((f) => {
    if (f.type === 'checkbox' || f.type === 'radio') {
      const key = `${f.name}:${f.value}`
      if (typed.has(key)) f.checked = typed.get(key)
    } else if (typed.has(f.name) && !f.hasAttribute('data-fresh')) f.value = typed.get(f.name)
  })
  if (focus) {
    const target = nodeAt(el, focus.path)
    if (target && target.tagName === focus.tag) target.focus({ preventScroll: true })
  }
}

function makeContext(found, pathname, search, el) {
  const hooks = []
  const cleanups = []
  const params = found?.params ?? {}
  const ref = params.ref ?? 'me'
  return {
    el, params, path: pathname, query: Object.fromEntries(new URLSearchParams(search)),
    auth, prefs, api, toast,
    ref, base: `/patients/${ref}`, isSelf: ref === 'me', link: (page) => `/p/${ref}/${page}`,
    go: (path, options) => go(path, options),
    back: () => history.back(),
    draw: (fragment) => {
      drawInto(el, fragment)
      hooks.forEach((fn) => fn())
    },
    afterDraw: (fn) => hooks.push(fn),
    /** Run `fn` when the person leaves this screen (to stop a timer, for example). */
    onLeave: (fn) => cleanups.push(fn),
    cleanups,
    on: (type, selector, handler) => on(el, type, selector, handler),
  }
}

// ---------------------------------------------------------------- navigating
let navigation = 0
let leaving = [] // cleanup functions of the screen being shown
export async function render() {
  const id = ++navigation
  if (!auth.ready) await auth.load()
  const pathname = location.pathname.replace(/\/+$/, '') || '/'
  const found = match(pathname === '/' ? '/welcome' : pathname)
  const redirect = guard(pathname, found)
  if (redirect) {
    history.replaceState(null, '', redirect)
    return render()
  }
  if (pathname === '/') history.replaceState(null, '', '/welcome')

  const el = document.createElement('div')
  el.id = 'view'
  el.className = 'page-enter'
  const ctx = makeContext(found, pathname === '/' ? '/welcome' : pathname, location.search, el)
  try {
    const module = await found.route.view()
    if (id !== navigation) return // another navigation started while this screen was loading
    leaving.forEach((fn) => fn())
    leaving = ctx.cleanups
    document.getElementById('view').replaceWith(el)
    current = { path: ctx.path, route: found.route }
    listeners.forEach((fn) => fn(current))
    window.scrollTo(0, 0)
    await module.default(ctx)
  } catch (err) {
    console.error(err)
    el.innerHTML = '<main class="page"><p class="error" role="alert">Something went wrong. Please reload the page.</p></main>'
    if (!el.isConnected) document.getElementById('view')?.replaceWith(el)
  }
}

export function go(path, { replace = false } = {}) {
  if (replace) history.replaceState(null, '', path)
  else history.pushState(null, '', path)
  return render()
}

/** Redraw the current screen (after the language changes, for example). */
export const refresh = () => render()

export function startRouter() {
  window.addEventListener('popstate', () => render())
  // Links inside the app navigate without a page load.
  document.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    const target = event.target instanceof Element ? event.target : null
    const back = target?.closest('[data-act="back"]')
    if (back) {
      history.back()
      return
    }
    const a = target?.closest('a[href]')
    if (!a || a.target === '_blank' || a.hasAttribute('download')) return
    const url = new URL(a.href, location.href)
    if (url.origin !== location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/')) return
    event.preventDefault()
    go(url.pathname + url.search)
  })
  locale.subscribe(() => refresh())
  return render()
}
