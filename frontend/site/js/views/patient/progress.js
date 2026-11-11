// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The progress dashboard: what was written down, day by day. Safety rule: counts only. No percentage, score,
// streak, target or colour that means good or bad, and a day with nothing recorded is just an empty day.
import { html } from '../../dom.js'
import { errorText } from '../../api.js'
import { locale, t } from '../../i18n.js'
import { barChart, icon, pageHeader } from '../../ui.js'

export default async function progress(ctx) {
  const { base } = ctx
  const s = { days: 7, data: null, loading: true, error: '' }
  const dayLabel = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString(locale.value, { weekday: 'short', day: 'numeric', month: 'short' })

  const view = () => {
    const d = s.data
    const series = (key) => (d?.days ?? []).map((x) => ({ date: x.date, value: x[key] }))
    const charts = d
      ? [
          { key: 'tasks_done', label: t('progress.tasks'), total: d.totals.tasks_done },
          { key: 'doses_taken', label: t('progress.doses'), total: d.totals.doses_taken },
          { key: 'mobility_minutes', label: t('progress.minutes'), total: d.totals.mobility_minutes },
        ]
      : []
    return html`<main class="page">
      ${pageHeader({ title: t('progress.title'), subtitle: t('progress.lead'), back: true })}
      <div class="row" role="group" aria-label="${t('progress.title')}">
        ${[7, 14, 30].map((n) => html`<button class="sc-chip" data-act="range" data-n="${n}" aria-pressed="${s.days === n ? 'true' : 'false'}">${t('progress.range', { n })}</button>`)}
      </div>
      ${d?.current_phase ? html`<section class="sc-card pad stack-s"><span class="sc-eyebrow">${t('recovery.stage')}</span><strong>${d.current_phase.name}</strong></section>` : ''}
      ${d
        ? html`${charts.map(
              (c) => html`<section class="sc-card pad stack-s">
                <div class="row-between"><strong>${c.label}</strong><span class="muted">${c.total}</span></div>
                ${barChart(series(c.key), t('progress.chartLabel', { what: c.label, n: s.days }))}
              </section>`,
            )}
            <p class="row small muted" style="flex-wrap: nowrap; align-items: flex-start">${icon('info', 18)}<span>${t('progress.chart')} ${d.note}</span></p>
            <section class="sc-card pad stack-s" style="overflow-x: auto">
              <h2>${t('progress.table')}</h2>
              <table class="small" style="width: 100%; border-collapse: collapse">
                <caption class="visually-hidden">${t('progress.table')}</caption>
                <thead><tr style="text-align: left">
                  <th scope="col">${t('progress.day')}</th><th scope="col">${t('progress.colTasks')}</th><th scope="col">${t('progress.colDoses')}</th>
                  <th scope="col">${t('progress.checked')}</th><th scope="col">${t('summary.readingsLabel')}</th><th scope="col">${t('progress.colMinutes')}</th>
                </tr></thead>
                <tbody>
                  ${[...d.days].reverse().map(
                    (r) => html`<tr style="border-top: 1px solid var(--line)">
                      <th scope="row" style="text-align: left; padding: 0.4rem 0.25rem; font-weight: 600">${dayLabel(r.date)}</th>
                      <td>${r.tasks_total ? `${r.tasks_done}/${r.tasks_total}` : r.tasks_done || '–'}</td><td>${r.doses_due ? `${r.doses_taken}/${r.doses_due}` : '–'}</td>
                      <td>${r.checked_in ? t('common.yes') : '–'}</td><td>${r.bp_readings || '–'}</td><td>${r.mobility_minutes || '–'}</td>
                    </tr>`,
                  )}
                </tbody>
              </table>
              <h3 class="sc-eyebrow" style="font-size: 0.85rem; margin-top: 0.5rem">${t('progress.totals', { n: s.days })}</h3>
              <dl class="grid-2 small" style="margin: 0; gap: 0.35rem 1rem">
                <div><dt class="muted">${t('progress.tasks')}</dt><dd style="margin: 0; font-weight: 700">${d.totals.tasks_done}</dd></div>
                <div><dt class="muted">${t('progress.doses')}</dt><dd style="margin: 0; font-weight: 700">${d.totals.doses_taken}${d.totals.doses_due ? ` / ${d.totals.doses_due}` : ''}</dd></div>
                <div><dt class="muted">${t('summary.checkins')}</dt><dd style="margin: 0; font-weight: 700">${d.totals.check_ins}</dd></div>
                <div><dt class="muted">${t('summary.readingsLabel')}</dt><dd style="margin: 0; font-weight: 700">${d.totals.bp_readings}</dd></div>
                <div><dt class="muted">${t('progress.minutes')}</dt><dd style="margin: 0; font-weight: 700">${d.totals.mobility_minutes}</dd></div>
              </dl>
            </section>
            <a href="${ctx.link('mobility')}" class="sc-btn sc-btn-ghost">${t('progress.openMovement')}</a>`
        : s.loading ? html`<p class="muted" aria-busy="true">…</p>` : ''}
      ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
    </main>`
  }
  const redraw = () => ctx.draw(view())
  async function load() {
    s.loading = true
    try {
      s.data = await ctx.api.get(`${base}/progress/`, { days: s.days })
      s.error = ''
    } catch (e) {
      s.error = errorText(e)
    }
    s.loading = false
    redraw()
  }
  redraw()
  load()
  ctx.on('click', '[data-act="range"]', (el) => {
    s.days = Number(el.dataset.n)
    load()
  })
}
