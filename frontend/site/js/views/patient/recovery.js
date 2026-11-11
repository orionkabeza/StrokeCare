// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Personal recovery in one place: the stage the clinician named, the person's own goals, and ways into the
// movement log and progress. Safety rule: no score, no target, no judgement. The stage is the clinician's wording.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { emptyState, fmtDay, icon, pageHeader, toast } from '../../ui.js'

export default async function recovery(ctx) {
  const { base, isSelf, auth } = ctx
  const s = { phases: [], goals: null }
  const canWrite = auth.role !== 'clinician' // goals are the person's own words

  const view = () => {
    const current = s.phases.find((p) => p.is_current) ?? null
    return html`<main class="page">
      ${pageHeader({ title: isSelf ? t('recovery.title') : t('recovery.titleOther'), subtitle: t('recovery.lead'), back: true })}
      <section class="sc-card pad stack sc-rise">
        <span class="sc-eyebrow">${t('recovery.stage')}</span>
        ${current
          ? html`<h2 style="font-size: 1.5rem">${current.name}</h2>
              <span class="small muted">${current.ends_on ? t('recovery.range', { from: fmtDay(current.starts_on), to: fmtDay(current.ends_on) }) : t('recovery.since', { from: fmtDay(current.starts_on) })} · ${t('recovery.stageFrom')}</span>
              ${current.care_needed ? html`<div class="stack-s"><strong class="small">${t('recovery.careNeeded')}</strong><p style="white-space: pre-line">${current.care_needed}</p></div>` : ''}`
          : html`<p class="muted">${isSelf ? t('recovery.noStage') : t('recovery.noStageOther')}</p>`}
      </section>

      <section class="stack">
        <h2 class="row">${icon('target', 24, 'duotone')}${isSelf ? t('recovery.goals') : t('recovery.goalsOther')}</h2>
        ${canWrite
          ? html`<form class="sc-card pad stack-s" data-form="goal">
              <p class="small muted">${t('recovery.goalLead')}</p>
              <label class="visually-hidden" for="goal">${t('recovery.goals')}</label>
              <input id="goal" name="text" class="sc-input" maxlength="200" placeholder="${t('recovery.goalPlaceholder')}" />
              <label class="field">${t('recovery.goalDate')}<input name="target_date" class="sc-input" type="date" /></label>
              <span class="tiny">${t('recovery.goalWish')}</span>
              <button class="sc-btn sc-btn-primary">${icon('plus', 20)}${t('recovery.goalAdd')}</button>
            </form>`
          : ''}
        ${s.goals && !s.goals.length ? emptyState(t('recovery.goalNone')) : ''}
        ${(s.goals ?? []).map(
          (g) => html`<div class="sc-card list-row" style="opacity: ${g.done ? 0.7 : 1}">
            <button class="tick" data-act="toggle" data-id="${g.id}" aria-pressed="${g.done ? 'true' : 'false'}" aria-label="${g.done ? t('recovery.goalUnmark') : t('recovery.goalMark')}">${g.done ? icon('check', 22, 'bold') : ''}</button>
            <span class="stack-s" style="flex-grow: 1">
              <strong style="text-decoration: ${g.done ? 'line-through' : 'none'}">${g.text}</strong>
              ${g.target_date ? html`<span class="small muted">${fmtDay(g.target_date)}</span>` : ''}
            </span>
            ${canWrite ? html`<button class="icon-btn" data-act="delete" data-id="${g.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>` : ''}
          </div>`,
        )}
      </section>

      <nav class="stack-s">
        <a href="${ctx.link('mobility')}" class="sc-card pad row" style="text-decoration: none; color: var(--ink)">${icon('person-simple-walk', 26, 'duotone')}<strong style="flex-grow: 1">${t('mobility.title')}</strong>${icon('caret-right', 18)}</a>
        <a href="${ctx.link('progress')}" class="sc-card pad row" style="text-decoration: none; color: var(--ink)">${icon('chart-bar', 26, 'duotone')}<strong style="flex-grow: 1">${t('progress.title')}</strong>${icon('caret-right', 18)}</a>
      </nav>
    </main>`
  }
  const redraw = () => ctx.draw(view())
  const loadGoals = async () => {
    s.goals = (await ctx.api.get(`${base}/goals/`)).results ?? []
    redraw()
  }
  redraw()
  await Promise.allSettled([
    ctx.api.get(`${base}/phases/`).then((r) => ((s.phases = r.results ?? []), redraw())),
    loadGoals(),
  ])

  ctx.on('submit', 'form[data-form="goal"]', async (form, event) => {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(form).entries())
    if (!String(data.text).trim()) return
    try {
      await ctx.api.post(`${base}/goals/`, { text: data.text, target_date: data.target_date || null })
      form.reset()
      await loadGoals()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="toggle"]', async (el) => {
    const g = s.goals.find((x) => x.id === el.dataset.id)
    try {
      await ctx.api.patch(`${base}/goals/${g.id}/`, { done: !g.done })
      loadGoals()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="delete"]', async (el) => {
    try {
      await ctx.api.del(`${base}/goals/${el.dataset.id}/`)
      loadGoals()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
