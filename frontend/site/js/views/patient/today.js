// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The survivor's day on one screen: what is done so far, quick ways in, what is coming up and today's plan.
// Safety rule: it counts what is done. There are no streaks and no scores.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { icon, progressRing, toast } from '../../ui.js'

const tile = (to, delay, iconName, weight, accent, title, sub) => html`<a href="${to}" class="sc-card sc-rise pad stack-s" style="text-decoration: none; color: var(--ink); animation-delay: ${delay}ms">
  <span class="sc-iconbox ${accent ? 'sc-iconbox-accent' : ''}">${icon(iconName, 28, weight)}</span>
  <strong>${title}</strong><span class="small muted">${sub}</span>
</a>`
const more = (to, iconName, label) => html`<a href="${to}" class="sc-card pad row" style="text-decoration: none; color: var(--ink)">${icon(iconName, 24, 'duotone')}<strong>${label}</strong></a>`

export default async function today(ctx) {
  const s = { plan: null, meds: null, lastCheckin: null, lastReading: null, stage: null, comingUp: [], unread: 0, loaded: false }

  const view = () => {
    const todayDate = s.plan?.date
    const checkedIn = !!s.lastCheckin && s.lastCheckin.date === todayDate
    const tasks = s.plan?.tasks ?? []
    const tasksDone = tasks.filter((x) => x.done_today).length
    const done = tasksDone + (s.meds?.doses_marked_taken ?? 0) + (checkedIn ? 1 : 0)
    const total = tasks.length + (s.meds?.doses_due ?? 0) + 1
    const h = new Date().getHours()
    const greeting = t(h < 12 ? 'today.morning' : h < 18 ? 'today.afternoon' : 'today.evening', { name: ctx.auth.user?.display_name?.split(' ')[0] })
    const dateLabel = new Date().toLocaleDateString(locale.value, { weekday: 'long', day: 'numeric', month: 'long' })
    const dosesLine = t('today.dosesLine', { n: s.meds?.doses_marked_taken ?? 0, total: s.meds?.doses_due ?? 0 })
    return html`<main class="page">
      <section class="hero-head sc-hero">
        <div class="sc-rise stack-s"><p class="muted" style="font-weight: 600">${dateLabel}</p><h1 style="font-size: 1.9rem">${greeting}</h1></div>
        ${!s.loaded
          ? html`<div class="sc-glass row pad" style="flex-wrap: nowrap" aria-busy="true">
              <span class="sc-skeleton" style="width: 6rem; height: 6rem; border-radius: 50%; opacity: 0.35"></span>
              <span class="stack-s" style="flex-grow: 1"><span class="sc-skeleton" style="height: 1.1rem; opacity: 0.35"></span><span class="sc-skeleton" style="height: 0.9rem; width: 80%; opacity: 0.35"></span></span>
            </div>`
          : html`<div class="sc-glass sc-rise row pad" style="animation-delay: 80ms; flex-wrap: nowrap">
              ${progressRing(done, total)}
              <div class="stack-s">
                <strong style="font-size: 1.1rem">${t('today.soFar')}</strong>
                <span class="muted small">${t('today.tasksLine', { n: tasksDone, total: tasks.length })}</span>
                <span class="muted small">${dosesLine}</span>
                <span class="muted small">${checkedIn ? t('today.checkinDone') : t('today.checkinNotYet')}</span>
              </div>
            </div>`}
      </section>

      <nav class="grid-2" aria-label="${t('today.quick')}">
        ${tile('/p/me/checkin', 120, 'clipboard-text', 'duotone', false, t('checkin.title'), checkedIn ? t('today.checkinDone') : t('checkin.short'))}
        ${tile('/p/me/bp', 160, 'heartbeat', 'duotone', true, t('bp.title'), s.lastReading ? t('bp.last', { s: s.lastReading.systolic, d: s.lastReading.diastolic }) : t('bp.none'))}
        ${tile('/p/me/medicines', 200, 'pill', 'duotone', true, t('meds.title'), dosesLine)}
        ${tile('/talk', 240, 'chat-circle-text', 'duotone', false, t('talk.title'), t('talk.short'))}
      </nav>

      ${s.stage ? html`<a href="/p/me/recovery" class="banner" style="text-decoration: none; color: var(--ink)">${icon('target', 22)}${t('today.stage', { name: s.stage.name })}</a>` : ''}
      ${s.comingUp.length
        ? html`<section class="stack-s" aria-label="${t('today.comingUp')}">
            <h2 class="sc-eyebrow" style="font-size: 0.85rem">${t('today.comingUp')}</h2>
            ${s.comingUp.map(
              (u) => html`<a href="${u.kind === 'appointment' ? '/p/me/calendar' : '/reminders'}" class="sc-card pad row" style="text-decoration: none; color: var(--ink)">
                <span class="sc-iconbox">${icon(u.kind === 'appointment' ? 'calendar-check' : 'bell-ringing', 26, 'duotone')}</span>
                <span class="stack-s"><strong>${u.kind === 'appointment' ? u.title : t(`reminders.kinds.${u.kind}`)}</strong><span class="small muted">${new Date(u.next_at).toLocaleString(locale.value, { weekday: 'short', hour: '2-digit', minute: '2-digit' })}</span></span>
              </a>`,
            )}
          </section>`
        : ''}
      ${s.unread ? html`<a href="/p/me/messages" class="banner" style="text-decoration: none; color: var(--ink)">${icon('chat-circle-text', 22)}${t('today.unread', { n: s.unread })}</a>` : ''}

      <nav class="stack-s" aria-label="${t('today.more')}">
        <h2 class="sc-eyebrow" style="font-size: 0.85rem">${t('today.more')}</h2>
        <div class="grid-2">
          ${more('/p/me/recovery', 'target', t('recovery.title'))}${more('/p/me/mobility', 'person-simple-walk', t('mobility.title'))}
          ${more('/p/me/progress', 'chart-bar', t('progress.title'))}${more('/care-team', 'users-three', t('team.title'))}
        </div>
      </nav>

      ${s.plan?.has_plan
        ? html`<section class="stack sc-rise" style="animation-delay: 280ms">
            <div class="row-between"><h2>${t('today.plan')}</h2><span class="sc-eyebrow">${t('today.fromClinician')}</span></div>
            ${tasks.map(
              (task) => html`<button class="sc-card list-row" data-act="tick" data-id="${task.id}" aria-pressed="${task.done_today ? 'true' : 'false'}" style="color: var(--ink); cursor: pointer; text-align: left">
                <span class="tick" aria-pressed="${task.done_today ? 'true' : 'false'}" style="width: 2.25rem; height: 2.25rem">${task.done_today ? icon('check', 20, 'bold') : ''}</span>
                <span class="stack-s"><strong>${task.title}</strong>${task.instructions ? html`<span class="small muted">${task.instructions}</span>` : ''}</span>
              </button>`,
            )}
          </section>`
        : ''}
    </main>`
  }
  const redraw = () => ctx.draw(view())
  redraw()

  const results = await Promise.allSettled([
    ctx.api.get('/patients/me/plan/'),
    ctx.api.get('/patients/me/medications/'),
    ctx.api.get('/patients/me/checkins/', { limit: 1 }),
    ctx.api.get('/patients/me/readings/', { limit: 1 }),
    ctx.api.get('/patients/me/phases/'),
    ctx.api.get('/me/reminders/upcoming/'),
    ctx.api.get('/inbox/'),
  ])
  const [p, m, c, r, ph, up, inbox] = results.map((x) => (x.status === 'fulfilled' ? x.value : null))
  s.plan = p ?? { has_plan: false, tasks: [] }
  s.meds = m
  s.lastCheckin = c?.results?.[0] ?? null
  s.lastReading = r?.results?.[0] ?? null
  s.stage = (ph?.results ?? []).find((x) => x.is_current) ?? null
  // the next few things in the next 36 hours: appointments and reminders, soonest first
  const horizon = Date.now() + 36 * 3600 * 1000
  s.comingUp = (up?.results ?? []).filter((u) => new Date(u.next_at).getTime() <= horizon).slice(0, 4)
  s.unread = inbox?.results?.[0]?.unread ?? 0
  s.loaded = true
  redraw()

  ctx.on('click', '[data-act="tick"]', async (el) => {
    const task = s.plan.tasks.find((x) => x.id === el.dataset.id)
    try {
      if (task.done_today) await ctx.api.del(`/patients/me/plan/tasks/${task.id}/log/`)
      else await ctx.api.post(`/patients/me/plan/tasks/${task.id}/log/`, {}, { queueable: true })
      task.done_today = !task.done_today
      redraw()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
