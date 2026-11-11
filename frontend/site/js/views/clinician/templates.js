// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// A clinician's reusable task lists, private to them. One task per line.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { emptyState, icon, pageHeader, toast } from '../../ui.js'

export default async function templates(ctx) {
  let data = null
  const view = () => html`<main class="page page-wide">
    ${pageHeader({ title: t('templates.title'), subtitle: t('templates.lead') })}
    <form class="sc-card pad stack" style="max-width: 40rem" data-form="template">
      <label class="field">${t('templates.name')}<input name="name" class="sc-input" required maxlength="120" /></label>
      <label class="field">${t('templates.tasks')}<textarea name="tasks" class="sc-input" rows="6" required></textarea><span class="tiny">${t('templates.oneLine')}</span></label>
      <button class="sc-btn sc-btn-primary">${t('common.save')}</button>
    </form>
    ${data && !data.results.length ? emptyState(t('templates.empty')) : ''}
    <div class="grid-auto">
      ${(data?.results ?? []).map(
        (x) => html`<div class="sc-card pad stack-s">
          <div class="row-between"><strong class="row">${icon('copy', 20)}${x.name}</strong>
            <button class="icon-btn" data-act="delete" data-id="${x.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button></div>
          <ol class="small" style="margin: 0; padding-left: 1.2rem">${x.tasks.map((task) => html`<li>${task.title}</li>`)}</ol>
        </div>`,
      )}
    </div>
  </main>`
  const load = async () => ((data = await ctx.api.get('/plan-templates/')), ctx.draw(view()))
  ctx.draw(view())
  await load().catch(() => {})

  ctx.on('submit', 'form[data-form="template"]', async (form, event) => {
    event.preventDefault()
    const f = Object.fromEntries(new FormData(form).entries())
    try {
      const tasks = String(f.tasks).split('\n').map((l) => l.trim()).filter(Boolean).map((title) => ({ title }))
      await ctx.api.post('/plan-templates/', { name: f.name, tasks })
      form.reset()
      load()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="delete"]', async (el) => (await ctx.api.del(`/plan-templates/${el.dataset.id}/`), load()))
}
