// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The service worker: keeps the app itself (pages, scripts, styles, texts) working without a connection.
// Privacy rule: ONLY public content is ever cached here (education, the talk board, emergency guidance, the visit
// checklist). Personal health data is never cached by the service worker. The person's own optional copy is a
// separate, opt-in feature of the app, wiped at sign-out (see js/copy.js).
//
// The list below is generated: run `python tools/make_precache.py` after changing any file under frontend/site.
// BEGIN PRECACHE
const VERSION = 'b6920215945e'
const PRECACHE = [
  '/',
  '/css/app.css',
  '/css/tokens.css',
  '/icon.svg',
  '/js/api.js',
  '/js/components/voice.js',
  '/js/copy.js',
  '/js/dom.js',
  '/js/i18n.js',
  '/js/icons.js',
  '/js/main.js',
  '/js/offline.js',
  '/js/router.js',
  '/js/shell.js',
  '/js/speech.js',
  '/js/state.js',
  '/js/store.js',
  '/js/ui.js',
  '/js/views/auth/consent.js',
  '/js/views/auth/login.js',
  '/js/views/auth/register.js',
  '/js/views/care/calendar.js',
  '/js/views/care/caregiver-home.js',
  '/js/views/chw/chw-home.js',
  '/js/views/chw/home-visit.js',
  '/js/views/clinician/caseload.js',
  '/js/views/clinician/doctor-home.js',
  '/js/views/clinician/summary.js',
  '/js/views/clinician/templates.js',
  '/js/views/patient/blood-pressure.js',
  '/js/views/patient/care-team.js',
  '/js/views/patient/check-in.js',
  '/js/views/patient/medicines.js',
  '/js/views/patient/mobility.js',
  '/js/views/patient/phrases.js',
  '/js/views/patient/progress.js',
  '/js/views/patient/recovery.js',
  '/js/views/patient/reminders.js',
  '/js/views/patient/today.js',
  '/js/views/patient/visit-prep.js',
  '/js/views/shared/emergency.js',
  '/js/views/shared/inbox.js',
  '/js/views/shared/learn-item.js',
  '/js/views/shared/learn.js',
  '/js/views/shared/settings.js',
  '/js/views/shared/sharing.js',
  '/js/views/shared/talk-board.js',
  '/js/views/shared/thread.js',
  '/js/views/shared/welcome.js',
  '/locales/en.json',
  '/locales/fr.json',
  '/locales/rw.json',
  '/manifest.webmanifest',
]
// END PRECACHE

const SHELL = `sc-shell-${VERSION}`
const PUBLIC = 'public-content'
const FONTS = 'fonts'
const PUBLIC_API = /^\/api\/v1\/(education|talk-board|emergency|home-visit-checklist)\//
const NEVER_CACHED = /^\/(api|admin|static|healthz)(\/|$)/

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('sc-shell-') && k !== SHELL).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

async function staleWhileRevalidate(cacheName, request) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  const refresh = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone())
      return response
    })
    .catch(() => null)
  return cached ?? (await refresh) ?? Response.error()
}

async function cacheFirst(cacheName, request) {
  const cache = await caches.open(cacheName)
  const cached = await cache.match(request)
  if (cached) return cached
  const response = await fetch(request)
  if (response.ok || response.type === 'opaque') cache.put(request, response.clone())
  return response
}

// Pages: ask the network first (so updates arrive), and fall back to the cached app shell when offline.
// The shell is cached as "/" (not "/index.html": the server redirects that, and a browser will not show a redirected
// response for a page load).
async function navigate(request) {
  try {
    return await fetch(request)
  } catch {
    return (await caches.match('/')) ?? Response.error()
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com') {
    event.respondWith(cacheFirst(FONTS, request))
    return
  }
  if (url.origin !== self.location.origin) return
  if (PUBLIC_API.test(url.pathname)) {
    event.respondWith(staleWhileRevalidate(PUBLIC, request))
    return
  }
  if (NEVER_CACHED.test(url.pathname)) return // network only: nothing personal is stored here
  if (request.mode === 'navigate') {
    event.respondWith(navigate(request))
    return
  }
  event.respondWith(staleWhileRevalidate(SHELL, request))
})
