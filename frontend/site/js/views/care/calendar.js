// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The family care calendar: who does what, and handover notes from one carer to the next. An appointment can carry
// a reminder time (15 minutes to 2 days before) that shows on the person's Today screen and alerts caregivers.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { emptyState, fmtDateTime, icon, pageHeader, toast } from '../../ui.js'

const KINDS = ['appointment', 'therapy', 'medicine_pickup', 'transport', 'visit', 'other']
const LEADS = [15, 30, 60, 120, 1440, 2880]

export default async function calendar(ctx) {
  const { base } = ctx
  const s = { cal: null, notes: null, adding: false, kind: 'appointment' }

  const byDay = () => {
    const groups = {}
    for (const e of s.cal?.results ?? []) {
      const day = new Date(e.starts_at).toLocaleDateString(locale.value, { weekday: 'long', day: 'numeric', month: 'long' })
      ;(groups[day] ??= []).push(e)
    }
    return Object.entries(groups)
  }

  const view = () => html`<main class="page">
    ${pageHeader({ title: t('calendar.title'), subtitle: t('calendar.lead'), back: true })}
    ${!s.adding
      ? html`<button class="sc-btn sc-btn-primary" data-act="open-form">${icon('plus', 20)}${t('calendar.add')}</button>`
      : html`<form class="sc-card pad stack sc-sheet" data-form="event">
          <label class="field">${t('calendar.what')}<input name="title" class="sc-input" required maxlength="120" /></label>
          <div class="row" role="group" aria-label="${t('calendar.kind')}">
            ${KINDS.map((k) => html`<button type="button" class="sc-chip" data-act="kind" data-value="${k}" aria-pressed="${s.kind === k ? 'true' : 'false'}">${t(`calendar.kinds.${k}`)}</button>`)}
          </div>
          <div class="grid-2">
            <label class="field">${t('calendar.date')}<input name="date" class="sc-input" type="date" required /></label>
            <label class="field">${t('calendar.time')}<input name="time" class="sc-input" type="time" value="09:00" required /></label>
          </div>
          <label class="field">${t('calendar.who')}
            <select name="assigned_to" class="sc-input">
              <option value="">${t('calendar.nobody')}</option>
              ${(s.cal?.team ?? []).map((m) => html`<option value="${m.id}">${m.display_name} · ${t(`roles.${m.relation === 'patient' ? 'patient' : m.relation}`)}</option>`)}
            </select>
          </label>
          <label class="field">${t('calendar.remind')}
            <select name="remind" class="sc-input">
              <option value="">${t('calendar.remindNone')}</option>
              ${LEADS.map((m) => html`<option value="${m}">${t(`calendar.remindOptions.${m}`)}</option>`)}
            </select>
          </label>
          <label class="field">${t('calendar.where')}<input name="location" class="sc-input" maxlength="120" /></label>
          <label class="field">${t('common.noteOptional')}<input name="notes" class="sc-input" maxlength="500" /></label>
          <div class="grid-2">
            <button type="button" class="sc-btn sc-btn-ghost" data-act="cancel">${t('common.cancel')}</button>
            <button class="sc-btn sc-btn-primary">${t('common.save')}</button>
          </div>
        </form>`}

    ${s.cal && !s.cal.results.length ? emptyState(t('calendar.empty')) : ''}
    ${byDay().map(
      ([day, events]) => html`<section class="stack-s">
        <h2 class="sc-eyebrow" style="font-size: 0.85rem">${day}</h2>
        ${events.map(
          (e) => html`<div class="sc-card list-row" style="opacity: ${e.is_done ? 0.6 : 1}">
            <span class="sc-iconbox" style="width: 2.75rem; height: 2.75rem">${icon('calendar-check', 22, 'duotone')}</span>
            <span class="stack-s" style="flex-grow: 1">
              <strong>${new Date(e.starts_at).toLocaleTimeString(locale.value, { hour: '2-digit', minute: '2-digit' })} · ${e.title}</strong>
              <span class="small muted">${t(`calendar.kinds.${e.kind}`)}${e.location ? ` · ${e.location}` : ''}${e.assigned_to_name ? ` · ${e.assigned_to_name}` : ''}${e.remind_minutes_before ? ` · ${t('calendar.reminderSet', { when: t(`calendar.remindOptions.${e.remind_minutes_before}`) })}` : ''}</span>
            </span>
            <button class="tick" style="width: 2.5rem; height: 2.5rem" data-act="done" data-id="${e.id}" aria-pressed="${e.is_done ? 'true' : 'false'}" aria-label="${t('calendar.done')}">${e.is_done ? icon('check', 18, 'bold') : ''}</button>
            <button class="icon-btn" data-act="delete" data-id="${e.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>
          </div>`,
        )}
      </section>`,
    )}

    <section class="stack">
      <h2>${t('calendar.handover')}</h2>
      <form class="row" style="flex-wrap: nowrap" data-form="note">
        <label class="visually-hidden" for="ho">${t('calendar.handoverWrite')}</label>
        <input id="ho" name="text" class="sc-input" placeholder="${t('calendar.handoverWrite')}" maxlength="1000" />
        <button class="sc-btn sc-btn-primary" style="width: 3.5rem; padding: 0" aria-label="${t('calendar.handoverAdd')}">${icon('plus', 22)}</button>
      </form>
      ${(s.notes?.results ?? []).map(
        (n) => html`<div class="sc-card pad stack-s"><p>${n.text}</p><span class="tiny">${n.author_name} · ${fmtDateTime(n.created_at)}</span></div>`,
      )}
    </section>
  </main>`
  const redraw = () => ctx.draw(view())
  const loadCal = async () => ((s.cal = await ctx.api.get(`${base}/calendar/`)), redraw())
  const loadNotes = async () => ((s.notes = await ctx.api.get(`${base}/handover/`)), redraw())
  redraw()
  await Promise.allSettled([loadCal(), loadNotes()])

  ctx.on('click', '[data-act="open-form"]', () => ((s.adding = true), redraw()))
  ctx.on('click', '[data-act="cancel"]', () => ((s.adding = false), redraw()))
  ctx.on('click', '[data-act="kind"]', (el) => ((s.kind = el.dataset.value), redraw()))
  ctx.on('submit', 'form[data-form="event"]', async (form, event) => {
    event.preventDefault()
    const f = Object.fromEntries(new FormData(form).entries())
    try {
      await ctx.api.post(`${base}/calendar/`, {
        title: f.title, kind: s.kind, location: f.location, notes: f.notes,
        starts_at: new Date(`${f.date}T${f.time}`).toISOString(), assigned_to: f.assigned_to || null,
        remind_minutes_before: f.remind ? Number(f.remind) : null,
      })
      s.adding = false
      loadCal()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="done"]', async (el) => {
    const e = s.cal.results.find((x) => x.id === el.dataset.id)
    await ctx.api.patch(`${base}/calendar/${e.id}/`, { done: !e.is_done })
    loadCal()
  })
  ctx.on('click', '[data-act="delete"]', async (el) => (await ctx.api.del(`${base}/calendar/${el.dataset.id}/`), loadCal()))
  ctx.on('submit', 'form[data-form="note"]', async (form, event) => {
    event.preventDefault()
    const text = new FormData(form).get('text')?.toString().trim()
    if (!text) return
    try {
      await ctx.api.post(`${base}/handover/`, { text })
      form.reset()
      loadNotes()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
