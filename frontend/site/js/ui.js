// Owner: Emmanuel Happy Rangira (Frontend developer)
// Small pieces every screen uses: icons, the page header, empty and draft notices, the progress ring,
// toasts and date helpers. Each returns markup built with html``, so anything passed in is escaped.
import { ICONS } from './icons.js'
import { html, raw } from './dom.js'
import { locale, t } from './i18n.js'

/** An inline Phosphor icon. weight: regular | duotone | fill | bold. */
export function icon(name, size = 24, weight = 'regular') {
  const set = ICONS[name]
  if (!set) throw new Error(`Unknown icon: ${name}`)
  return raw(
    `<svg class="ph" width="${size}" height="${size}" viewBox="0 0 256 256" fill="currentColor" aria-hidden="true" focusable="false">${set[weight] ?? set.regular}</svg>`,
  )
}

/** Title, optional subtitle and back button at the top of a screen. The back button stays top-left and the
 *  title is centred beside it. A screen that needs variable-width `extra` content (summary.js's day-range
 *  chips) keeps the earlier left-flowing layout instead, since that content does not fit a fixed column. */
export function pageHeader({ title, subtitle, back = false, extra = '' }) {
  if (extra) {
    return html`<div class="stack sc-rise">
      <div class="row" style="align-items: flex-start; flex-wrap: nowrap">
        ${back ? html`<button class="icon-btn" data-act="back" aria-label="${t('common.back')}">${icon('caret-left', 22)}</button>` : ''}
        <div class="stack-s" style="min-width: 0; overflow-wrap: anywhere"><h1>${title}</h1>${subtitle ? html`<p class="muted">${subtitle}</p>` : ''}</div>
      </div>
      ${extra}
    </div>`
  }
  return html`<div class="page-header sc-rise">
    ${back ? html`<button class="icon-btn" data-act="back" aria-label="${t('common.back')}">${icon('caret-left', 22)}</button>` : html`<span aria-hidden="true"></span>`}
    <div class="stack-s" style="min-width: 0; text-align: center"><h1>${title}</h1>${subtitle ? html`<p class="muted">${subtitle}</p>` : ''}</div>
    <span aria-hidden="true"></span>
  </div>`
}

export const emptyState = (text) => html`<p class="sc-card pad muted" style="text-align: center">${text}</p>`

/** Pause the hero illustration's idle float while it's off-screen. Call once after the first draw on any
 *  screen that uses .hero-illustration. */
export function pauseHeroOffscreen(ctx) {
  if (typeof IntersectionObserver === 'undefined') return
  const el = ctx.el.querySelector('.hero-illustration')
  if (!el) return
  const io = new IntersectionObserver(([entry]) => {
    el.style.animationPlayState = entry.isIntersecting ? 'running' : 'paused'
  })
  io.observe(el)
  ctx.onLeave(() => io.disconnect())
}

/** Safety rule: draft content always says so, and names its source when it has one. */
export function draftNote({ source = '', status = '' } = {}) {
  if (!status || status === 'draft')
    return html`<span class="sc-draft">${icon('info', 16)}${t('common.draft')}${source ? ` · ${source}` : ''}</span>`
  return html`<span class="sc-draft">${t('common.reviewed')}</span>`
}

/** How much of today is done. A count, never a score, and it never shames. */
export function progressRing(done, total) {
  const C = 2 * Math.PI * 42
  const offset = total ? C * (1 - done / total) : C
  return html`<div style="position: relative; width: 6rem; height: 6rem; flex-shrink: 0">
    <svg viewBox="0 0 96 96" width="100%" height="100%" aria-hidden="true">
      <circle cx="48" cy="48" r="42" fill="none" stroke="var(--line-strong)" stroke-width="8" />
      <circle class="sc-ring" cx="48" cy="48" r="42" fill="none" stroke="var(--primary)" stroke-width="8" stroke-linecap="round"
        stroke-dasharray="${C}" style="stroke-dashoffset: ${offset}; transition: stroke-dashoffset .6s cubic-bezier(.2,.7,.2,1)"
        transform="rotate(-90 48 48)" />
    </svg>
    <span style="position: absolute; inset: 0; display: grid; place-items: center; font-weight: 600; font-size: 1.5rem; white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--ink)">
      ${done}<small style="font-size: 0.9rem; color: var(--ink-2)">/${total}</small>
    </span>
  </div>`
}

/** A short message at the bottom of the screen. Fixed-time enter/exit (not animationend) so it still
 *  disappears on schedule when reduced motion turns the animation itself off. */
export function toast(text, ms = 3500) {
  const host = document.querySelector('.toasts')
  if (!host) return
  const el = document.createElement('p')
  el.className = 'toast sc-toast-in'
  el.textContent = text
  host.append(el)
  setTimeout(() => {
    el.classList.replace('sc-toast-in', 'sc-toast-out')
    setTimeout(() => el.remove(), 180)
  }, ms)
}

/** Key under roles.by.* for "who entered this", from the viewer's side: "you" on your own record, "the patient"
 *  for the patient's entries when someone else looks, otherwise the enterer's role. */
export function byWho(role, isSelf) {
  if (!role) return isSelf ? 'self' : 'patient'
  if (role === 'survivor' || role === 'prevention') return isSelf ? 'self' : 'patient'
  return role
}

// Dates and times in the person's language. Day strings are noon-anchored so the time zone cannot shift the date.
export const fmtDay = (iso, opts = { day: 'numeric', month: 'long', year: 'numeric' }) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString(locale.value, opts)
export const fmtTime = (iso, opts = { hour: '2-digit', minute: '2-digit' }) => new Date(iso).toLocaleTimeString(locale.value, opts)
export const fmtDateTime = (iso, opts = { dateStyle: 'medium', timeStyle: 'short' }) => new Date(iso).toLocaleString(locale.value, opts)

/** Blood pressure over time as two plain lines: top number solid, bottom number dashed. Safety rule: numbers only.
 *  The vertical scale is just an axis (60 to 150 or wider); there are no bands, no "normal range" and no colour that
 *  means good or bad. A table of the same numbers is read out for screen readers. */
export function bpChart(readings) {
  const rows = [...readings].sort((a, b) => +new Date(a.taken_at) - +new Date(b.taken_at))
  const W = 340
  const H = 190
  const pad = { top: 12, right: 10, bottom: 28, left: 36 }
  const times = rows.map((r) => +new Date(r.taken_at))
  const t0 = times[0]
  const span = (times[times.length - 1] - t0) || 1
  const values = rows.flatMap((r) => [r.systolic, r.diastolic])
  const lo = Math.min(60, Math.min(...values) - 5)
  const hi = Math.max(150, Math.max(...values) + 5)
  const X = (time) => pad.left + ((time - t0) / span) * (W - pad.left - pad.right)
  const Y = (v) => pad.top + (1 - (v - lo) / (hi - lo)) * (H - pad.top - pad.bottom)
  const line = (key) => rows.map((r, i) => `${i ? 'L' : 'M'}${X(times[i]).toFixed(1)} ${Y(r[key]).toFixed(1)}`).join(' ')
  const gridValues = []
  for (let v = Math.ceil(lo / 30) * 30; v <= hi; v += 30) gridValues.push(v)
  const ticks = [0, 1, 2, 3].map((i) => t0 + (span * i) / 3)
  const dayLabel = (ms) => new Date(ms).toLocaleDateString(locale.value, { weekday: 'short', day: 'numeric' })
  const dots = (key, color) => rows.map((r, i) => html`<circle cx="${X(times[i])}" cy="${Y(r[key])}" r="3.5" fill="${color}" />`)
  return html`<figure style="margin: 0; overflow: hidden">
    <svg viewBox="0 0 ${W} ${H}" aria-hidden="true" style="width: 100%; height: auto; display: block; font-family: var(--font); font-variant-numeric: tabular-nums">
      ${gridValues.map((v) => html`<g><line x1="${pad.left}" x2="${W - pad.right}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" />
        <text x="${pad.left - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="var(--ink-3)">${v}</text></g>`)}
      ${ticks.map((ms, i) => html`<text x="${X(ms)}" y="${H - 8}" text-anchor="${i === 0 ? 'start' : i === ticks.length - 1 ? 'end' : 'middle'}" font-size="11" fill="var(--ink-3)">${dayLabel(ms)}</text>`)}
      <path d="${line('systolic')}" fill="none" stroke="var(--primary)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" />
      <path d="${line('diastolic')}" fill="none" stroke="var(--accent-ink)" stroke-width="3" stroke-dasharray="6 5" stroke-linejoin="round" stroke-linecap="round" />
      ${dots('systolic', 'var(--primary)')}${dots('diastolic', 'var(--accent-ink)')}
    </svg>
    <figcaption class="row small muted" style="gap: 1rem; margin-top: 0.25rem">
      <span class="row" style="gap: 0.4rem"><svg width="18" height="4" aria-hidden="true"><line x1="0" y1="2" x2="18" y2="2" stroke="var(--primary)" stroke-width="3" /></svg>${t('bp.top')}</span>
      <span class="row" style="gap: 0.4rem"><svg width="18" height="4" aria-hidden="true"><line x1="0" y1="2" x2="18" y2="2" stroke="var(--accent-ink)" stroke-width="3" stroke-dasharray="4 3" /></svg>${t('bp.bottom')}</span>
      <span class="visually-hidden">${rows.map((r) => `${new Date(r.taken_at).toLocaleString(locale.value)}: ${r.systolic} / ${r.diastolic} mmHg. `)}</span>
    </figcaption>
  </figure>`
}
