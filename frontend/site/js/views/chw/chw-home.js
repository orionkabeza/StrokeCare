// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// A community health worker's home: the people who invited them, and a way to send visits recorded without signal.
import { html } from '../../dom.js'
import { pendingCount } from '../../offline.js'
import { t } from '../../i18n.js'
import { emptyState, icon } from '../../ui.js'

export default async function chwHome(ctx) {
  let data = null
  const view = () => html`<main class="page">
    <section class="hero-head sc-hero">
      <h1 style="font-size: 1.9rem">${t('chw.title')}</h1>
      <p class="muted">${t('chw.lead')}</p>
      ${pendingCount.value ? html`<button class="sc-btn sc-glass" style="color: var(--on-hero)" data-act="send-now">${icon('cloud-arrow-up', 22)}${t('offline.sendNow', { n: pendingCount.value })}</button>` : ''}
    </section>
    ${data && !data.length ? emptyState(t('chw.empty')) : ''}
    ${data && !data.length ? html`<a href="/sharing" class="sc-btn sc-btn-primary">${icon('key', 22)}${t('sharing.enterCode')}</a>` : ''}
    ${(data ?? []).map(
      (p) => html`<div class="sc-card pad stack-s sc-rise">
        <div class="row-between"><strong style="font-size: 1.15rem">${p.display_name}</strong><span class="tiny">${t(`roles.${p.patient_role}`)}</span></div>
        <span class="small muted">${p.facts.days_since_check_in == null ? t('caseload.never') : t('caseload.daysAgo', { n: p.facts.days_since_check_in })} · ${t('caseload.lastCheckin')}</span>
        <div class="grid-2">
          <a href="/p/${p.patient_id}/home-visit" class="sc-btn sc-btn-primary">${icon('map-pin', 20)}${t('visitLog.record')}</a>
          <a href="/p/${p.patient_id}/summary" class="sc-btn sc-btn-ghost">${t('caseload.open')}${icon('caret-right', 18)}</a>
        </div>
      </div>`,
    )}
  </main>`
  const redraw = () => ctx.draw(view())
  redraw()
  ctx.onLeave(pendingCount.subscribe(redraw))
  ctx.on('click', '[data-act="send-now"]', () => ctx.auth.syncOutbox())
  try {
    data = await ctx.api.get('/patients/')
  } catch {
    /* an empty list is shown */
  }
  redraw()
}
