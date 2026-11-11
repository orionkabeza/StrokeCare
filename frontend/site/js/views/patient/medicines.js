// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Safety rule: the list is written by the clinician. Here a dose can only be marked as taken. No advice.
// Doses are grouped by part of the day (a display grouping by clock time, not medical guidance), each course shows
// its dates, and one tap marks everything in a part of the day, so a tired person makes fewer taps.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { byWho, emptyState, fmtDay, icon, pageHeader, toast } from '../../ui.js'

const PERIODS = ['morning', 'afternoon', 'evening', 'night']
const periodOf = (time) => {
  const h = Number(time.slice(0, 2))
  return h < 12 ? 'morning' : h < 17 ? 'afternoon' : h < 21 ? 'evening' : 'night'
}

export default async function medicines(ctx) {
  const { base, isSelf } = ctx
  let data = null
  const doses = () =>
    (data?.medications ?? []).flatMap((m) => m.doses_on_day.map((d) => ({ ...d, med: m }))).sort((a, b) => a.time.localeCompare(b.time))
  const nextDose = () => {
    const now = new Date()
    const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    const open = doses().filter((d) => !d.taken)
    return open.find((d) => d.time >= hhmm) ?? open[0] ?? null
  }
  const course = (m) =>
    m.end_date ? t('meds.courseFromTo', { from: fmtDay(m.start_date, { day: 'numeric', month: 'short', year: 'numeric' }), to: fmtDay(m.end_date, { day: 'numeric', month: 'short', year: 'numeric' }) })
      : t('meds.courseFrom', { from: fmtDay(m.start_date, { day: 'numeric', month: 'short', year: 'numeric' }) })

  const view = () => {
    const all = doses()
    const next = nextDose()
    const groups = PERIODS.map((period) => ({ period, doses: all.filter((d) => periodOf(d.time) === period) })).filter((g) => g.doses.length)
    return html`<main class="page">
      ${pageHeader({ title: t('meds.title'), subtitle: t('meds.fromClinician'), back: true })}
      ${data ? html`<p class="sc-card pad" style="font-weight: 700">${t('meds.summary', { n: data.doses_marked_taken, total: data.doses_due })}</p>` : ''}
      ${data && all.length ? html`<p class="small muted">${next ? t('meds.next', { time: next.time, name: next.med.name }) : t('meds.allDone')}</p>` : ''}
      ${data && !all.length ? emptyState(t('meds.none')) : ''}
      ${groups.map(
        (g) => html`<section class="stack-s">
          <div class="row-between">
            <h2 class="sc-eyebrow" style="font-size: 0.9rem">${t(`meds.periods.${g.period}`)}</h2>
            ${g.doses.some((d) => !d.taken) ? html`<button class="sc-chip" data-act="mark-all" data-period="${g.period}">${icon('check-circle', 18)}${t('meds.markAll')}</button>` : ''}
          </div>
          ${g.doses.map(
            (d, i) => html`<div class="sc-card sc-rise list-row" style="animation-delay: ${i * 40}ms">
              <strong style="width: 3.5rem; font-size: 1.15rem">${d.time}</strong>
              <span class="stack-s" style="flex-grow: 1">
                <strong>${d.med.name}</strong>
                <span class="small muted">${d.taken ? t('meds.marked', { who: t(`roles.by.${byWho(d.entered_by_role, isSelf)}`) }) : d.med.dose}</span>
                <span class="tiny">${course(d.med)}</span>
              </span>
              <button class="tick" data-act="toggle" data-med="${d.med.id}" data-time="${d.time}" aria-pressed="${d.taken ? 'true' : 'false'}" aria-label="${d.taken ? t('meds.undo') : t('meds.mark')}">${d.taken ? icon('check', 26, 'bold') : ''}</button>
            </div>`,
          )}
        </section>`,
      )}
      <p class="row small muted" style="flex-wrap: nowrap; align-items: flex-start">${icon('info', 18)}<span>${t('meds.onlyClinician')} <a href="${ctx.link('visit')}">${t('visit.title')}</a></span></p>
    </main>`
  }

  async function load() {
    try {
      data = await ctx.api.get(`${base}/medications/`)
    } catch (e) {
      toast(errorText(e))
    }
    ctx.draw(view())
  }
  ctx.draw(view())
  load()

  ctx.on('click', '[data-act="toggle"]', async (el) => {
    const { med, time } = el.dataset
    const taken = el.getAttribute('aria-pressed') === 'true'
    try {
      if (taken) await ctx.api.del(`${base}/medications/${med}/doses/`, undefined, { time })
      else {
        const r = await ctx.api.post(`${base}/medications/${med}/doses/`, { time }, { queueable: true })
        if (r?.queued) toast(t('offline.saved'))
      }
      load()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="mark-all"]', async (el) => {
    const todo = doses().filter((d) => periodOf(d.time) === el.dataset.period && !d.taken)
    if (!todo.length) return
    try {
      const r = await ctx.api.post(`${base}/medications/doses/bulk/`, { doses: todo.map((d) => ({ medication: d.med.id, time: d.time })) }, { queueable: true })
      toast(r?.queued ? t('offline.saved') : t('meds.markedAll', { n: r?.newly_marked ?? todo.length }))
      load()
    } catch (e) {
      toast(errorText(e))
    }
  })
  void locale
}
