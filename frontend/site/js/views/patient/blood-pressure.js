// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Safety rule: blood pressure is shown as plain numbers. No colour, label, band, arrow or warning ever says whether a
// reading is good or bad. The only message is a typing check (the top number cannot be below the bottom one).
import { ApiError, errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { bpChart, byWho, emptyState, icon, pageHeader, toast } from '../../ui.js'

const CONTEXTS = ['resting', 'morning', 'evening', 'after_activity', 'other']

export default async function bloodPressure(ctx) {
  const { base, isSelf } = ctx
  const s = { rows: [], context: 'resting', fields: {}, busy: false, showAll: false }

  const view = () => {
    const shown = s.showAll ? s.rows : s.rows.slice(0, 10)
    return html`<main class="page">
      ${pageHeader({ title: t('bp.title'), back: true })}
      <section class="sc-card pad stack-s">
        <div class="row-between"><h2>${t('bp.recent')}</h2><span class="tiny">${t('bp.numbersOnly')}</span></div>
        ${s.rows.length > 1 ? bpChart(s.rows) : !s.rows.length ? emptyState(t('bp.none')) : ''}
      </section>

      <form class="sc-card pad stack" data-form="bp">
        <h2>${t('bp.add')}</h2>
        <div class="grid-2">
          <label class="field">${t('bp.top')}<input name="systolic" class="sc-input" inputmode="numeric" pattern="[0-9]*" required style="font-size: 1.9rem; font-weight: 800; min-height: 4.25rem" /></label>
          <label class="field">${t('bp.bottom')}<input name="diastolic" class="sc-input" inputmode="numeric" pattern="[0-9]*" required style="font-size: 1.9rem; font-weight: 800; min-height: 4.25rem" /></label>
        </div>
        <p class="tiny">${t('bp.hint')}</p>
        <p class="banner" role="alert" data-warn hidden>${t('bp.topAboveBottom')}</p>
        ${Object.values(s.fields).map((msgs) => html`<p class="error">${msgs[0]}</p>`)}
        <div class="row" role="group" aria-label="${t('bp.when')}">
          ${CONTEXTS.map((c) => html`<button type="button" class="sc-chip" data-act="context" data-value="${c}" aria-pressed="${s.context === c ? 'true' : 'false'}">${t(`bp.ctx.${c}`)}</button>`)}
        </div>
        <label class="field">${t('common.noteOptional')}<input name="note" class="sc-input" maxlength="500" /></label>
        <button class="sc-btn sc-btn-primary thumb-actions" ${s.busy ? 'disabled' : ''}>${icon('check', 20)}${t('bp.save')}</button>
      </form>

      <section class="stack">
        <h2>${t('bp.history')}</h2>
        <ul class="list">
          ${shown.map(
            (r) => html`<li class="sc-card list-row">
              <span style="font-size: 1.4rem; font-weight: 800">${r.systolic} / ${r.diastolic} <span class="tiny">mmHg</span></span>
              <span class="small muted" style="flex-grow: 1; text-align: right">${new Date(r.taken_at).toLocaleString(locale.value, { dateStyle: 'medium', timeStyle: 'short' })} · ${t(`roles.by.${byWho(r.entered_by_self ? 'survivor' : r.entered_by_role, isSelf)}`)}</span>
              ${isSelf || !r.entered_by_self ? html`<button class="icon-btn" data-act="delete" data-id="${r.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>` : ''}
            </li>`,
          )}
        </ul>
        ${s.rows.length > 10 && !s.showAll ? html`<button class="sc-btn sc-btn-ghost" data-act="all">${t('bp.showAll', { n: s.rows.length })}</button>` : ''}
      </section>
    </main>`
  }

  async function load() {
    try {
      s.rows = (await ctx.api.get(`${base}/readings/`, { limit: 30 })).results ?? []
    } catch (e) {
      toast(errorText(e))
    }
    ctx.draw(view())
  }
  ctx.draw(view())
  load()

  // A typing check only: the top number must be larger than the bottom number.
  ctx.on('input', 'input[name="systolic"], input[name="diastolic"]', () => {
    const top = ctx.el.querySelector('[name="systolic"]').value
    const bottom = ctx.el.querySelector('[name="diastolic"]').value
    ctx.el.querySelector('[data-warn]').hidden = !(top && bottom && +top <= +bottom)
  })
  ctx.on('click', '[data-act="context"]', (el) => {
    s.context = el.dataset.value
    ctx.draw(view())
  })
  ctx.on('click', '[data-act="all"]', () => {
    s.showAll = true
    ctx.draw(view())
  })
  ctx.on('submit', 'form[data-form="bp"]', async (form, event) => {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(form).entries())
    s.fields = {}
    s.busy = true
    try {
      const r = await ctx.api.post(`${base}/readings/`, { systolic: +data.systolic, diastolic: +data.diastolic, context: s.context, note: data.note }, { queueable: true })
      toast(r?.queued ? t('offline.saved') : t('bp.saved'))
      form.reset()
      s.busy = false
      await load()
    } catch (e) {
      if (e instanceof ApiError) s.fields = e.fields
      toast(errorText(e))
      s.busy = false
      ctx.draw(view())
    }
  })
  ctx.on('click', '[data-act="delete"]', async (el) => {
    try {
      await ctx.api.del(`${base}/readings/${el.dataset.id}/`)
      load()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
