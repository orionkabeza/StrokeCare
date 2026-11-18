// Owner: Emmanuel Happy Rangira (Frontend developer)
// The week cards: a header that opens the metric's screen, today's value, and a seven-day mini chart.
// Safety rule: each metric keeps one colour whatever the value, a day with nothing recorded is a blank column
// (never a zero bar), and nothing here grades, averages or sets a target. Exact numbers live on each screen.
import { html } from '../dom.js'
import { locale, t } from '../i18n.js'
import { icon } from '../ui.js'

const W = 150
const PLOT = 96
const COL = W / 7
const cx = (i) => COL * (i + 0.5)
let uid = 0

const weekday = (iso, style) => new Date(`${iso}T12:00:00`).toLocaleDateString(locale.value, { weekday: style })
const ariaWeek = (title, dates, say) => `${title}, ${dates.map((d, i) => `${weekday(d, 'long')} ${say(i) ?? t('week.none')}`).join(', ')}`

function frame(label, marks, dates, defs = '') {
  return html`<svg class="sc-metric-chart" viewBox="0 0 ${W} 116" role="img" aria-label="${label}">
    ${defs}${marks}
    ${dates.map((d, i) => html`<text class="day" x="${cx(i)}" y="114" text-anchor="middle">${weekday(d, 'narrow')}</text>`)}
  </svg>`
}

/** Movement minutes: a rounded track per day, the bar scaled to the week's own highest day. */
export function pillBars(dates, minutes, label) {
  const max = Math.max(1, ...minutes.map((m) => m ?? 0))
  const marks = minutes.map((m, i) => {
    const x = cx(i) - 6
    const h = m ? Math.max(12, (m / max) * PLOT) : 0
    return html`<rect class="track" x="${x}" y="0" width="12" height="${PLOT}" rx="6" fill="var(--m-move-track)" />
      ${h ? html`<rect class="grow" style="animation-delay: ${i * 40}ms" x="${x}" y="${PLOT - h}" width="12" height="${h}" rx="6" fill="var(--m-move)" />` : ''}`
  })
  return frame(ariaWeek(label, dates, (i) => (minutes[i] ? t('week.aria.minutes', { n: minutes[i] }) : null)), marks, dates)
}

/** Blood pressure: lowest bottom number to highest top number per day, on a fixed 40-220 mmHg scale. */
export function rangeBars(dates, days, label) {
  const y = (v) => PLOT - ((Math.min(220, Math.max(40, v)) - 40) / 180) * PLOT
  const marks = days.map((d, i) => {
    const x = cx(i) - 4
    return html`<rect class="track" x="${x}" y="0" width="8" height="${PLOT}" rx="4" fill="var(--m-bp-track)" />
      ${d ? html`<rect class="grow" style="animation-delay: ${i * 40}ms" x="${x}" y="${y(d.hi)}" width="8" height="${Math.max(8, y(d.lo) - y(d.hi))}" rx="4" fill="var(--m-bp)" />` : ''}`
  })
  return frame(ariaWeek(label, dates, (i) => (days[i] ? t('week.aria.bp', { lo: days[i].lo, hi: days[i].hi }) : null)), marks, dates)
}

/** Pulse: one line through every reading in time order, with a soft area under it. Gaps over a day break it. */
export function lineArea(dates, points, label) {
  const y = (v) => PLOT - ((Math.min(160, Math.max(40, v)) - 40) / 120) * PLOT
  const segments = []
  points.forEach((p, i) => {
    if (!i || p.at - points[i - 1].at > 24 * 3600 * 1000) segments.push([])
    segments.at(-1).push({ x: Math.min(W, Math.max(0, p.x * COL)), y: y(p.pulse) })
  })
  const id = `sc-pulse-${++uid}`
  const defs = html`<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="var(--m-pulse)" stop-opacity="0.22" /><stop offset="1" stop-color="var(--m-pulse)" stop-opacity="0" />
  </linearGradient></defs>`
  const marks = segments.map((s) => {
    const line = s.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
    const area = s.length > 1 ? `${line} L${s.at(-1).x.toFixed(1)} ${PLOT} L${s[0].x.toFixed(1)} ${PLOT} Z` : ''
    return html`${area ? html`<path d="${area}" fill="url(#${id})" />` : ''}
      ${s.length > 1
        ? html`<path class="sc-draw" pathLength="1" d="${line}" fill="none" stroke="var(--m-pulse)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />`
        : html`<circle cx="${s[0].x}" cy="${s[0].y}" r="2.5" fill="var(--m-pulse)" />`}`
  })
  const byDay = dates.map((d) => points.filter((p) => p.date === d).map((p) => p.pulse))
  return frame(ariaWeek(label, dates, (i) => (byDay[i].length ? t('week.aria.pulse', { list: byDay[i].join(', ') }) : null)), marks, dates, defs)
}

/** Medicine doses: morning, midday and evening rows. A dot only where something was scheduled; filled once every
 *  dose in that slot is marked. The shade shows the time of day, never how well the day went. */
export function dotMatrix(dates, days, label) {
  const shades = ['var(--m-meds-light)', 'var(--m-meds-mid)', 'var(--m-meds)']
  const marks = days.map((d, i) =>
    d.slots.map((s, row) =>
      s.due
        ? html`<circle class="${s.taken >= s.due ? 'pop' : 'track'}" style="animation-delay: ${i * 40}ms" cx="${cx(i)}" cy="${26 + row * 22}" r="6" fill="${s.taken >= s.due ? shades[row] : 'var(--m-meds-empty)'}" />`
        : '',
    ),
  )
  const say = (i) => {
    const due = days[i].slots.reduce((n, s) => n + s.due, 0)
    return due ? t('week.aria.doses', { taken: days[i].slots.reduce((n, s) => n + s.taken, 0), due }) : null
  }
  return frame(ariaWeek(label, dates, say), marks, dates)
}

/** Check-ins: a ring per day, drawn full when a check-in was sent. No ticks or crosses. */
export function rings(dates, sent, label) {
  const marks = sent.map((on, i) => html`<circle class="track" cx="${cx(i)}" cy="48" r="6.25" fill="none" stroke="var(--m-checkin-track)" stroke-width="3.5" />
    ${on ? html`<circle class="pop" style="animation-delay: ${i * 40}ms" cx="${cx(i)}" cy="48" r="6.25" fill="none" stroke="var(--m-checkin)" stroke-width="3.5" />` : ''}`)
  return frame(ariaWeek(label, dates, (i) => (sent[i] ? t('week.aria.checkin') : null)), marks, dates)
}

/** Plan tasks: one segment per task done, stacked; a faint track as tall as the plan was that day. */
export function stackedBars(dates, days, label) {
  const unit = PLOT / Math.max(1, ...days.map((d) => d.in_plan))
  const shades = ['var(--m-tasks)', 'var(--m-tasks-mid)', 'var(--m-tasks-light)']
  const base = ++uid
  const defs = html`<defs>${days.map((d, i) => html`<clipPath id="sc-tk-${base}-${i}"><rect x="${cx(i) - 9}" y="${PLOT - d.done * unit}" width="18" height="${d.done * unit}" rx="6" /></clipPath>`)}</defs>`
  const marks = days.map((d, i) => {
    const x = cx(i) - 9
    if (!d.in_plan) return ''
    const segments = Array.from({ length: d.done }, (_, k) => {
      const top = PLOT - (k + 1) * unit
      return html`<rect x="${x}" y="${top + (k === d.done - 1 ? 0 : 2)}" width="18" height="${unit - (k === d.done - 1 ? 0 : 2)}" fill="${shades[k % 3]}" />`
    })
    return html`<rect class="track" x="${x}" y="${PLOT - d.in_plan * unit}" width="18" height="${d.in_plan * unit}" rx="6" fill="var(--m-tasks-track)" opacity="0.4" />
      <g class="grow" style="animation-delay: ${i * 40}ms" clip-path="url(#sc-tk-${base}-${i})">${segments}</g>`
  })
  return frame(ariaWeek(label, dates, (i) => (days[i].in_plan ? t('week.aria.tasks', { done: days[i].done, n: days[i].in_plan }) : null)), marks, dates, defs)
}

export function metricCard({ metric, iconName, title, value, unit, caption, href, chart }) {
  return html`<article class="sc-metric-card" style="--m: var(--m-${metric})">
    <a class="sc-metric-head" href="${href}">
      ${icon(iconName, 28, 'fill')}<span class="sc-metric-title">${title}</span>
      <span class="sc-metric-today">${t('week.today')}${icon('caret-right', 20)}</span>
    </a>
    <div class="sc-metric-body">
      <div class="sc-metric-value">
        <span class="sc-metric-number"><strong>${value}</strong>${unit ? html`<span>${unit}</span>` : ''}</span>
        <span class="sc-metric-caption">${caption}</span>
      </div>
      ${chart}
    </div>
  </article>`
}

const clock = (iso) => new Date(iso).toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit' })

/** All the cards the week data allows, in the spec's order. A metric that was not shared is simply absent. */
export function weekCards(week, link) {
  const { dates } = week
  const today = dates.at(-1)
  const cards = []
  const latestCaption = (r) => t('week.latest', { when: r.date === today ? clock(r.taken_at) : `${weekday(r.date, 'short')} ${clock(r.taken_at)}` })

  if (week.readings) {
    const last = week.readings.at(-1)
    const days = dates.map((d) => {
      const rs = week.readings.filter((r) => r.date === d)
      return rs.length ? { lo: Math.min(...rs.map((r) => r.diastolic)), hi: Math.max(...rs.map((r) => r.systolic)) } : null
    })
    cards.push(metricCard({
      metric: 'bp', iconName: 'drop', title: t('week.bp'), href: link('bp'),
      value: last ? `${last.systolic}/${last.diastolic}` : '–', unit: 'mmHg',
      caption: last ? latestCaption(last) : t('week.noneThisWeek'),
      chart: rangeBars(dates, days, t('week.bp')),
    }))
    const withPulse = week.readings.filter((r) => r.pulse)
    if (withPulse.length) {
      const lastPulse = withPulse.at(-1)
      const points = withPulse.map((r) => {
        const at = new Date(r.taken_at)
        return { at: +at, date: r.date, pulse: r.pulse, x: dates.indexOf(r.date) + (at.getHours() * 60 + at.getMinutes()) / 1440 }
      })
      cards.push(metricCard({
        metric: 'pulse', iconName: 'heartbeat', title: t('week.pulse'), href: link('bp'),
        value: lastPulse.pulse, unit: 'bpm', caption: latestCaption(lastPulse), chart: lineArea(dates, points, t('week.pulse')),
      }))
    }
  }
  if (week.mobility) {
    const minutes = week.mobility.map((m) => m.minutes)
    cards.push(metricCard({
      metric: 'move', iconName: 'person-simple-walk', title: t('week.move'), href: link('mobility'),
      value: minutes.at(-1) ?? '–', unit: minutes.at(-1) ? t('week.min') : '', caption: t('week.today'),
      chart: pillBars(dates, minutes, t('week.move')),
    }))
  }
  if (week.doses) {
    const slots = week.doses.at(-1).slots
    const due = slots.reduce((n, s) => n + s.due, 0)
    cards.push(metricCard({
      metric: 'meds', iconName: 'pill', title: t('week.meds'), href: link('medicines'),
      value: due ? `${slots.reduce((n, s) => n + s.taken, 0)}/${due}` : '–', caption: t('week.dosesToday'),
      chart: dotMatrix(dates, week.doses, t('week.meds')),
    }))
  }
  if (week.checkins) {
    const sent = week.checkins.map((c) => c.sent)
    const n = sent.filter(Boolean).length
    cards.push(metricCard({
      metric: 'checkin', iconName: 'clipboard-text', title: t('week.checkin'), href: link('checkin'),
      value: n, unit: t(n === 1 ? 'week.day' : 'week.days'), caption: t('week.checkinsWeek'), chart: rings(dates, sent, t('week.checkin')),
    }))
  }
  if (week.tasks) {
    const last = week.tasks.at(-1)
    cards.push(metricCard({
      metric: 'tasks', iconName: 'check-square', title: t('week.tasks'), href: link('progress'),
      value: last.in_plan ? `${last.done}/${last.in_plan}` : '–', caption: t('week.tasksToday'),
      chart: stackedBars(dates, week.tasks, t('week.tasks')),
    }))
  }
  return html`<div class="sc-metric-grid">${cards}</div>`
}
