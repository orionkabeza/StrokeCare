// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Record a home visit. It works with no signal: the visit waits on the phone and is sent once when the phone is
// back online (the phone's client_id makes a repeat harmless). A health worker records; they never change the plan.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { draftNote, icon, pageHeader, toast } from '../../ui.js'

export default async function homeVisit(ctx) {
  const { base } = ctx
  const s = { items: [], done: {}, error: '' }
  const view = () => html`<main class="page">
    ${pageHeader({ title: t('visitLog.record'), subtitle: t('visitLog.lead'), back: true })}
    <form class="stack" data-form="visit">
      <section class="sc-card pad stack">
        <h2>${t('visitLog.whatDone')}</h2>
        ${s.items.map(
          (item) => html`<button type="button" class="row" data-act="item" data-code="${item.code}" aria-pressed="${s.done[item.code] ? 'true' : 'false'}" style="flex-wrap: nowrap; min-height: 3.5rem; border: 0; background: transparent; color: var(--ink); text-align: left; cursor: pointer; padding: 0">
            <span class="tick" style="width: 2.25rem; height: 2.25rem; border-radius: 0.7rem" aria-pressed="${s.done[item.code] ? 'true' : 'false'}">${s.done[item.code] ? icon('check', 18, 'bold') : ''}</span>
            <span style="font-weight: 600">${item.label}</span>
          </button>`,
        )}
        ${draftNote()}
      </section>
      <section class="sc-card pad stack">
        <h2>${t('visitLog.reading')}</h2>
        <div class="grid-2">
          <label class="field">${t('bp.top')}<input name="systolic" class="sc-input" inputmode="numeric" pattern="[0-9]*" /></label>
          <label class="field">${t('bp.bottom')}<input name="diastolic" class="sc-input" inputmode="numeric" pattern="[0-9]*" /></label>
        </div>
        <span class="tiny">${t('visitLog.readingHint')}</span>
      </section>
      <label class="field">${t('common.noteOptional')}<textarea name="note" class="sc-input" maxlength="1000"></textarea></label>
      ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
      <button class="sc-btn sc-btn-primary thumb-actions">${t('visitLog.save')}</button>
    </form>
  </main>`
  const redraw = () => ctx.draw(view())
  redraw()
  try {
    s.items = (await ctx.api.get('/home-visit-checklist/', { lang: locale.value })).results ?? []
  } catch {
    /* the checklist stays empty; the rest of the form still works */
  }
  redraw()

  ctx.on('click', '[data-act="item"]', (el) => {
    s.done[el.dataset.code] = !s.done[el.dataset.code]
    redraw()
  })
  ctx.on('submit', 'form[data-form="visit"]', async (form, event) => {
    event.preventDefault()
    const f = Object.fromEntries(new FormData(form).entries())
    s.error = ''
    const body = { client_id: crypto.randomUUID(), visited_at: new Date().toISOString(), checklist: s.done, note: f.note }
    if (f.systolic || f.diastolic) Object.assign(body, { systolic: +f.systolic, diastolic: +f.diastolic })
    try {
      const r = await ctx.api.post(`${base}/home-visits/`, body, { queueable: true })
      toast(r?.queued ? t('offline.saved') : t('visitLog.saved'))
      ctx.back()
    } catch (e) {
      s.error = errorText(e)
      redraw()
    }
  })
}
