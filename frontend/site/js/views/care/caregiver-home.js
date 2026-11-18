// Owner: Emmanuel Happy Rangira (Frontend developer)
// Safety rule: alerts are facts, not an emergency service; the notice says so.
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { weekCards } from '../../components/metric-card.js'
import { icon, pauseHeroOffscreen } from '../../ui.js'

const LINKS = [
  ['bp', 'heartbeat', 'bp.add'], ['medicines', 'pill', 'meds.title'], ['checkin', 'clipboard-text', 'checkin.title'],
  ['calendar', 'calendar-check', 'calendar.title'], ['mobility', 'person-simple-walk', 'mobility.title'],
  ['recovery', 'target', 'recovery.titleOther'], ['progress', 'chart-bar', 'progress.title'], ['phrases', 'users-three', 'phrases.titleOther'],
  ['visit', 'note-pencil', 'visit.title'], ['messages', 'chat-circle-text', 'messages.title'],
]

export default async function caregiverHome(ctx) {
  // alertsEntered: the rise-in plays once, for the alerts' first real appearance; marking one (or all) read
  // redraws this same list and must not replay the entrance on every card.
  const s = { alerts: null, people: null, chosen: '', today: null, alertsEntered: false }
  const person = () => (s.people ?? []).find((p) => p.patient_id === s.chosen)
  const alertParams = (a) => ({
    ...a.detail, name: a.patient_name,
    date: a.detail?.date ? new Date(`${a.detail.date}T12:00:00`).toLocaleDateString(locale.value, { weekday: 'long', day: 'numeric', month: 'long' }) : '',
    title: a.detail?.title ?? '',
    when: a.detail?.starts_at ? new Date(a.detail.starts_at).toLocaleString(locale.value, { weekday: 'long', hour: '2-digit', minute: '2-digit' }) : '',
  })
  const chipLink = (a) => {
    const to = a.kind === 'urgent_answer' ? '/emergency'
      : a.kind === 'appointment_soon' ? `/p/${a.patient_id}/calendar`
      : a.kind === 'doses_not_marked' ? `/p/${a.patient_id}/medicines` : `/p/${a.patient_id}/checkin`
    const label = a.kind === 'urgent_answer' ? t('emergency.open')
      : a.kind === 'appointment_soon' ? t('calendar.title')
      : a.kind === 'doses_not_marked' ? t('meds.title') : t('checkin.title')
    return html`<a href="${to}" class="sc-chip" style="text-decoration: none">${label}</a>`
  }

  const view = () => {
    const p = person()
    const tasks = s.today?.plan?.tasks ?? []
    const unread = s.alerts?.unread
    const nobody = s.people && !s.people.length
    return html`<main class="page">
      <section class="hero-head">
        <img src="/img/hero-heart.svg" alt="" class="hero-illustration" />
        <p class="muted" style="font-size: 1.1rem; font-weight: 500">${t('care.caringFor')}</p>
        ${(s.people ?? []).length > 1
          ? html`<select name="chosen" class="sc-input" style="max-width: 16rem; border-radius: 999px; font-weight: 700; font-size: 1.25rem" aria-label="${t('care.choose')}" data-act="choose">
              ${s.people.map((x) => html`<option value="${x.patient_id}" ${x.patient_id === s.chosen ? 'selected' : ''}>${x.display_name}</option>`)}
            </select>`
          : html`<h1 style="font-size: 1.75rem">${p?.display_name ?? '—'}</h1>`}
      </section>

      ${nobody
        ? html`<section class="sc-card pad-l stack" style="align-items: center; text-align: center">
            <span class="sc-iconbox sc-iconbox-accent" style="width: 3rem; height: 3rem">${icon('key', 24, 'duotone')}</span>
            <p>${t('care.noPeople')}</p>
            <a href="/sharing" class="sc-btn sc-btn-primary full">${icon('key', 22)}${t('sharing.enterCode')}</a>
          </section>`
        : ''}

      ${s.chosen
        ? html`
          <section class="grid-2" style="grid-template-columns: repeat(3, minmax(0, 1fr))">
            <div class="sc-card pad stack-s"><span class="card-value">${tasks.filter((x) => x.done_today).length}/${tasks.length || '–'}</span><span class="small muted">${t('care.tasks')}</span></div>
            <div class="sc-card pad stack-s"><span class="card-value">${s.today ? `${s.today.meds?.doses_marked_taken ?? 0}/${s.today.meds?.doses_due ?? 0}` : '–'}</span><span class="small muted">${t('care.doses')}</span></div>
            <div class="sc-card pad stack-s"><span class="card-value">${p?.facts?.days_since_check_in === 0 ? '✓' : '–'}</span><span class="small muted">${t('care.checkin')}</span></div>
          </section>

          ${s.today?.week ? html`<section class="stack" aria-label="${t('week.title')}"><h2>${t('week.title')}</h2>${weekCards(s.today.week, (page) => `/p/${s.chosen}/${page}`)}</section>` : ''}

          <section class="stack">
            <div class="row-between">
              <h2 class="row">${icon('bell', 24)}${unread ? t('care.newAlerts', { n: unread }) : t('care.caughtUp')}</h2>
              ${unread ? html`<button class="sc-btn sc-btn-ghost" style="min-height: 2.75rem" data-act="read-all">${t('care.markAllRead')}</button>` : ''}
            </div>
            ${(s.alerts?.results ?? []).map(
              (a) => html`<div class="sc-card pad stack-s${s.alertsEntered ? '' : ' sc-rise'}" style="opacity: ${a.read ? 0.6 : 1}">
                <strong>${t(`alerts.${a.kind}`, alertParams(a))}</strong>
                <span class="tiny">${new Date(a.created_at).toLocaleString(locale.value, { dateStyle: 'medium', timeStyle: 'short' })}</span>
                <div class="row">${chipLink(a)}${!a.read ? html`<button class="sc-chip" data-act="read" data-id="${a.id}">${t('care.markRead')}</button>` : ''}</div>
              </div>`,
            )}
            <p class="sc-banner-info">${icon('info', 18)}${s.alerts?.note ?? t('care.alertNote')}</p>
          </section>

          <nav class="actions-grid" aria-label="${t('care.actions')}">
            ${LINKS.map(([page, ic, label]) => html`<a href="/p/${s.chosen}/${page}" class="sc-card pad row" style="text-decoration: none; color: var(--ink)">
              <span class="sc-iconbox" style="width: 2.75rem; height: 2.75rem">${icon(ic, 22, 'duotone')}</span>${t(label)}
            </a>`)}
          </nav>`
        : ''}
    </main>`
  }
  const redraw = () => ctx.draw(view())
  ctx.afterDraw(() => pauseHeroOffscreen(ctx))
  const loadAlerts = async () => ((s.alerts = await ctx.api.get('/alerts/')), redraw())
  async function loadToday() {
    if (!s.chosen) return
    const [plan, meds, week] = await Promise.all([
      ctx.api.get(`/patients/${s.chosen}/plan/`).catch(() => null),
      ctx.api.get(`/patients/${s.chosen}/medications/`).catch(() => null),
      ctx.api.get(`/patients/${s.chosen}/week/`).catch(() => null),
    ])
    s.today = { plan, meds, week }
    redraw()
  }
  redraw()
  await Promise.allSettled([loadAlerts(), ctx.api.get('/patients/').then((rows) => (s.people = rows))])
  s.alertsEntered = true
  s.chosen ||= s.people?.[0]?.patient_id ?? ''
  redraw()
  loadToday()

  ctx.on('change', '[data-act="choose"]', (el) => {
    s.chosen = el.value
    s.today = null
    loadToday()
  })
  ctx.on('click', '[data-act="read"]', async (el) => (await ctx.api.post(`/alerts/${el.dataset.id}/read/`), loadAlerts()))
  ctx.on('click', '[data-act="read-all"]', async () => (await ctx.api.post('/alerts/read-all/'), loadAlerts()))
}
