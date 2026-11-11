// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Reminders and what is coming up, including appointments from the care calendar. Reminders show inside the app.
// Phone alerts (SMS, push) are not built yet and the screen says so.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { emptyState, icon, pageHeader, toast } from '../../ui.js'

const KINDS = ['tasks', 'blood_pressure', 'checkin', 'medicines', 'mobility']
// Monday is 0, as the server counts. 1 January 2024 was a Monday.
const dayName = (i) => new Date(2024, 0, 1 + i).toLocaleDateString(locale.value, { weekday: 'short' })

export default async function reminders(ctx) {
  const s = { list: null, upcoming: null, adding: false, kind: 'checkin', days: [0, 1, 2, 3, 4, 5, 6] }
  const when = (iso) => new Date(iso).toLocaleString(locale.value, { weekday: 'short', hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })
  const daysText = (r) => (r.days_of_week.length === 7 ? t('reminders.everyDay') : r.days_of_week.map(dayName).join(', '))

  const view = () => html`<main class="page">
    ${pageHeader({ title: t('reminders.title'), subtitle: t('reminders.lead'), back: true })}
    <section class="stack-s">
      <h2>${t('reminders.upcoming')}</h2>
      ${s.upcoming && !s.upcoming.length ? emptyState(t('reminders.none')) : ''}
      ${(s.upcoming ?? []).map(
        (u) => html`<div class="sc-card list-row">
          <span class="sc-iconbox" style="width: 2.75rem; height: 2.75rem">${icon(u.kind === 'appointment' ? 'calendar-check' : 'bell-ringing', 22, 'duotone')}</span>
          <span class="stack-s">
            <strong>${u.kind === 'appointment' ? u.title : t(`reminders.kinds.${u.kind}`)}</strong>
            <span class="small muted">${when(u.next_at)}${u.location ? ` · ${u.location}` : ''}</span>
          </span>
        </div>`,
      )}
    </section>

    ${!s.adding
      ? html`<button class="sc-btn sc-btn-primary" data-act="open-form">${icon('plus', 20)}${t('reminders.add')}</button>`
      : html`<form class="sc-card pad stack sc-sheet" data-form="reminder">
          <strong>${t('reminders.kind')}</strong>
          <div class="row" role="group" aria-label="${t('reminders.kind')}">
            ${KINDS.map((k) => html`<button type="button" class="sc-chip" data-act="kind" data-value="${k}" aria-pressed="${s.kind === k ? 'true' : 'false'}">${t(`reminders.kinds.${k}`)}</button>`)}
          </div>
          <label class="field">${t('reminders.at')}<input name="time" class="sc-input" type="time" value="08:00" required /></label>
          <strong>${t('reminders.days')}</strong>
          <div class="row" role="group" aria-label="${t('reminders.days')}">
            ${[0, 1, 2, 3, 4, 5, 6].map((i) => html`<button type="button" class="sc-chip" data-act="day" data-value="${i}" aria-pressed="${s.days.includes(i) ? 'true' : 'false'}">${dayName(i)}</button>`)}
          </div>
          <div class="grid-2">
            <button type="button" class="sc-btn sc-btn-ghost" data-act="cancel">${t('common.cancel')}</button>
            <button class="sc-btn sc-btn-primary" ${s.days.length ? '' : 'disabled'}>${t('common.save')}</button>
          </div>
        </form>`}

    <section class="stack-s">
      ${(s.list ?? []).map(
        (r) => html`<div class="sc-card list-row" style="opacity: ${r.is_active ? 1 : 0.6}">
          <span class="stack-s" style="flex-grow: 1">
            <strong>${t(`reminders.kinds.${r.kind}`)} · ${String(r.time_of_day).slice(0, 5)}</strong>
            <span class="small muted">${daysText(r)}</span>
          </span>
          <button class="sc-chip" data-act="toggle" data-id="${r.id}" aria-pressed="${r.is_active ? 'true' : 'false'}">${r.is_active ? t('reminders.active') : t('reminders.inactive')}</button>
          <button class="icon-btn" data-act="delete" data-id="${r.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>
        </div>`,
      )}
    </section>
  </main>`
  const redraw = () => ctx.draw(view())
  async function load() {
    const [a, b] = await Promise.allSettled([ctx.api.get('/me/reminders/'), ctx.api.get('/me/reminders/upcoming/')])
    s.list = a.status === 'fulfilled' ? (a.value.results ?? []) : []
    s.upcoming = b.status === 'fulfilled' ? (b.value.results ?? []) : []
    redraw()
  }
  redraw()
  load()

  const act = async (fn) => {
    try {
      await fn()
      load()
    } catch (e) {
      toast(errorText(e))
    }
  }
  ctx.on('click', '[data-act="open-form"]', () => ((s.adding = true), redraw()))
  ctx.on('click', '[data-act="cancel"]', () => ((s.adding = false), redraw()))
  ctx.on('click', '[data-act="kind"]', (el) => ((s.kind = el.dataset.value), redraw()))
  ctx.on('click', '[data-act="day"]', (el) => {
    const i = Number(el.dataset.value)
    s.days = s.days.includes(i) ? s.days.filter((d) => d !== i) : [...s.days, i].sort()
    redraw()
  })
  ctx.on('submit', 'form[data-form="reminder"]', (form, event) => {
    event.preventDefault()
    const time = new FormData(form).get('time')
    act(async () => {
      await ctx.api.post('/me/reminders/', { kind: s.kind, time_of_day: time, days_of_week: s.days })
      s.adding = false
    })
  })
  ctx.on('click', '[data-act="toggle"]', (el) => {
    const r = s.list.find((x) => x.id === el.dataset.id)
    act(() => ctx.api.patch(`/me/reminders/${r.id}/`, { is_active: !r.is_active }))
  })
  ctx.on('click', '[data-act="delete"]', (el) => act(() => ctx.api.del(`/me/reminders/${el.dataset.id}/`)))
}
