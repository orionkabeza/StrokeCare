// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The frame around every screen: the top bar with the Emergency button, the side or bottom navigation for the
// signed-in role, and the offline notices. It redraws whenever the route, the person, the language or the
// connection changes.
import { showingCopy } from './copy.js'
import { html } from './dom.js'
import { locale, t } from './i18n.js'
import { pendingCount } from './offline.js'
import { currentPath, onRouteChange } from './router.js'
import { auth } from './store.js'
import { icon } from './ui.js'

const BARE = ['/login', '/register', '/consent']
let online = navigator.onLine
let beaconed = false

/** The tabs for this kind of account. */
function tabs() {
  const r = auth.role
  if (!auth.signedIn)
    return [
      { to: '/welcome', label: t('nav.home'), icon: 'house' },
      { to: '/talk', label: t('nav.talk'), icon: 'chat-circle-text' },
      { to: '/learn', label: t('nav.learn'), icon: 'book-open-text' },
    ]
  if (r === 'caregiver')
    return [
      { to: '/care', label: t('nav.home'), icon: 'house' },
      { to: '/inbox', label: t('nav.messages'), icon: 'chat-circle-text' },
      { to: '/talk', label: t('nav.talk'), icon: 'users-three' },
      { to: '/settings', label: t('nav.me'), icon: 'user-circle' },
    ]
  if (r === 'clinician')
    return [
      { to: '/doctor', label: t('nav.doctor'), icon: 'stethoscope' },
      { to: '/caseload', label: t('nav.caseload'), icon: 'users-three' },
      { to: '/inbox', label: t('nav.messages'), icon: 'chat-circle-text' },
      { to: '/templates', label: t('nav.templates'), icon: 'copy' },
      { to: '/settings', label: t('nav.me'), icon: 'user-circle' },
    ]
  if (r === 'chw')
    return [
      { to: '/chw', label: t('nav.visits'), icon: 'map-pin' },
      { to: '/inbox', label: t('nav.messages'), icon: 'chat-circle-text' },
      { to: '/learn', label: t('nav.learn'), icon: 'book-open-text' },
      { to: '/settings', label: t('nav.me'), icon: 'user-circle' },
    ]
  if (r === 'admin') return [{ to: '/settings', label: t('nav.me'), icon: 'user-circle' }]
  return [
    { to: '/today', label: t('nav.today'), icon: 'house' },
    { to: '/learn', label: t('nav.learn'), icon: 'book-open-text' },
    { to: '/p/me/visit', label: t('nav.myVisit'), icon: 'note-pencil' },
    { to: '/p/me/messages', label: t('nav.messages'), icon: 'chat-circle-text' },
    { to: '/settings', label: t('nav.me'), icon: 'user-circle' },
  ]
}

const isActive = (to) => currentPath() === to || currentPath().startsWith(`${to}/`)
const set = (id, markup) => {
  const el = document.getElementById(id)
  el.hidden = markup === ''
  el.innerHTML = String(markup)
}

export function renderChrome() {
  const path = currentPath()
  const bare = BARE.includes(path)
  const wide = auth.role === 'clinician'
  const list = tabs()
  document.getElementById('layout').className = wide ? 'layout-wide' : ''

  set(
    'side-nav',
    wide && !bare
      ? html`<a href="/doctor" class="brand" style="padding: 0 0.5rem 1.25rem">
            <span class="brand-mark">${icon('heartbeat', 22, 'duotone')}</span>StrokeCare
          </a>
          ${list.map((tab) => {
            const active = isActive(tab.to)
            return html`<a href="${tab.to}" class="side-link" aria-current="${active ? 'page' : 'false'}">
              <span class="sc-tab-icon">${icon(tab.icon, 22, active ? 'fill' : 'regular')}</span>${tab.label}
            </a>`
          })}`
      : '',
  )
  document.getElementById('side-nav').setAttribute('aria-label', t('nav.main'))

  set(
    'topbar',
    bare
      ? ''
      : html`<a href="${auth.signedIn ? auth.home : '/welcome'}" class="brand">
            <span class="brand-mark">${icon('heartbeat', 22, 'duotone')}</span><span>StrokeCare</span>
          </a>
          <a href="/emergency" class="sc-emergency${beaconed ? '' : ' sc-beacon'}">${icon('phone-call', 20, 'fill')}${t('emergency.button')}</a>`,
  )
  if (!bare) beaconed = true

  const notices = []
  if (!online || pendingCount.value)
    notices.push(html`<p class="banner" role="status" style="margin: 0.75rem 1rem 0">${icon('wifi-slash', 20)}
      ${!online ? html`<span>${t('offline.notice')}</span>` : ''}
      ${pendingCount.value ? html`<span>${t('offline.pending', { n: pendingCount.value })}</span>` : ''}</p>`)
  if (showingCopy.value)
    notices.push(html`<p class="banner" role="status" style="margin: 0.75rem 1rem 0">${icon('wifi-slash', 20)}<span>${t('offline.copyShown')}</span></p>`)
  set('notices', html`${notices}`)

  set(
    'tabbar',
    bare
      ? ''
      : html`${list.map((tab) => {
          const active = isActive(tab.to)
          return html`<a href="${tab.to}" class="sc-tab" aria-current="${active ? 'page' : 'false'}" title="${tab.label}">
            <span class="sc-tab-icon">${icon(tab.icon, 22, active ? 'fill' : 'regular')}</span><span class="sc-tab-label">${tab.label}</span>
          </a>`
        })}`,
  )
  document.getElementById('tabbar').setAttribute('aria-label', t('nav.main'))
}

export function mountShell() {
  window.addEventListener('online', () => ((online = true), renderChrome()))
  window.addEventListener('offline', () => ((online = false), renderChrome()))
  for (const source of [locale, pendingCount, showingCopy, auth.changed]) source.subscribe(renderChrome)
  onRouteChange(renderChrome)
  renderChrome()
}
