// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Small pieces every screen uses: icons, the page header, empty and draft notices, the progress ring, a bar chart,
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

/** Title, optional subtitle and back button at the top of a screen. */
export function pageHeader({ title, subtitle, back = false, extra = '' }) {
  return html`<div class="row sc-rise" style="align-items: flex-start; flex-wrap: nowrap">
    ${back ? html`<button class="icon-btn" data-act="back" aria-label="${t('common.back')}">${icon('caret-left', 22)}</button>` : ''}
    <div class="stack-s" style="min-width: 0"><h1>${title}</h1>${subtitle ? html`<p class="muted">${subtitle}</p>` : ''}</div>
    ${extra}
  </div>`
}

export const emptyState = (text) =>
  html`<p class="sc-card pad muted" style="text-align: center; box-shadow: none; border-style: dashed">${text}</p>`

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
      <circle cx="48" cy="48" r="42" fill="none" stroke="rgba(255,255,255,0.22)" stroke-width="8" />
      <circle class="sc-ring" cx="48" cy="48" r="42" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round"
        stroke-dasharray="${C}" style="stroke-dashoffset: ${offset}; transition: stroke-dashoffset .6s cubic-bezier(.2,.7,.2,1)"
        transform="rotate(-90 48 48)" />
    </svg>
    <span style="position: absolute; inset: 0; display: grid; place-items: center; font-weight: 800; font-size: 1.5rem; white-space: nowrap">
      ${done}<small style="font-size: 0.9rem; opacity: 0.85">/${total}</small>
    </span>
  </div>`
}

/** Plain bars, one per day, one colour. Safety rule: counts only. No target line, no colour that means good or bad,
 *  and an empty day is just an empty bar. The same numbers are always available as a table next to it. */
export function barChart(days, label) {
  const W = 340 // about the width of a phone screen, so the labels stay readable instead of shrinking
  const H = 150
  const pad = { top: 12, right: 8, bottom: 26, left: 30 }
  const max = Math.max(1, ...days.map((d) => d.value))
  const step = (W - pad.left - pad.right) / Math.max(1, days.length)
  const every = Math.ceil(days.length / 6)
  const dayLabel = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString(locale.value, { day: 'numeric', month: 'numeric' })
  const bars = days.map((d, i) => {
    const h = (d.value / max) * (H - pad.top - pad.bottom)
    const x = pad.left + i * step + step * 0.18
    const w = step * 0.64
    return html`<g>
      <rect x="${x}" y="${d.value ? H - pad.bottom - h : H - pad.bottom - 1.5}" width="${w}" height="${d.value ? h : 1.5}" rx="3" fill="var(--primary)" opacity="${d.value ? 1 : 0.35}" />
      ${i % every === 0 ? html`<text x="${x + w / 2}" y="${H - 8}" text-anchor="middle" font-size="11" fill="var(--ink-2)">${dayLabel(d.date)}</text>` : ''}
    </g>`
  })
  return html`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${label}" style="width: 100%; height: auto; display: block">
    <line x1="${pad.left}" x2="${W - pad.right}" y1="${H - pad.bottom}" y2="${H - pad.bottom}" stroke="var(--line-strong)" />
    <text x="${pad.left - 6}" y="${pad.top + 4}" text-anchor="end" font-size="11" fill="var(--ink-2)">${max}</text>
    <text x="${pad.left - 6}" y="${H - pad.bottom}" text-anchor="end" font-size="11" fill="var(--ink-2)">0</text>
    ${bars}
  </svg>`
}

/** A short message at the bottom of the screen. */
export function toast(text, ms = 3500) {
  const host = document.querySelector('.toasts')
  if (!host) return
  const el = document.createElement('p')
  el.className = 'toast'
  el.textContent = text
  host.append(el)
  setTimeout(() => el.remove(), ms)
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
    <svg viewBox="0 0 ${W} ${H}" aria-hidden="true" style="width: 100%; height: auto; display: block">
      ${gridValues.map((v) => html`<g><line x1="${pad.left}" x2="${W - pad.right}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)" />
        <text x="${pad.left - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="var(--ink-3)">${v}</text></g>`)}
      ${ticks.map((ms) => html`<text x="${X(ms)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="var(--ink-3)">${dayLabel(ms)}</text>`)}
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
