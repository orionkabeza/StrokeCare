// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Safety rule: "needs a look" filters are plain facts (dates, counts). No risk score, no ranking.
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { emptyState, icon, pageHeader } from '../../ui.js'

const FILTERS = ['', 'urgent', 'no_check_in', 'doses_not_marked']

export default async function caseload(ctx) {
  const s = { needs: FILTERS.includes(ctx.query.needs ?? '') ? (ctx.query.needs ?? '') : '', search: '', data: null }
  const rows = () => (s.data ?? []).filter((p) => p.display_name.toLowerCase().includes(s.search.toLowerCase()))
  const lastCheckin = (f) =>
    f.days_since_check_in == null ? t('caseload.never') : f.days_since_check_in === 0 ? t('caseload.today') : t('caseload.daysAgo', { n: f.days_since_check_in })

  const view = () => html`<main class="page page-wide">
    ${pageHeader({ title: t('caseload.title'), subtitle: new Date().toLocaleDateString(locale.value, { weekday: 'long', day: 'numeric', month: 'long' }) })}
    <div class="row-between">
      <label class="sc-card row" style="padding: 0 0.9rem; min-height: 3rem; box-shadow: none; flex-wrap: nowrap; min-width: 16rem">
        ${icon('magnifying-glass', 20)}<span class="visually-hidden">${t('caseload.search')}</span>
        <input name="search" placeholder="${t('caseload.search')}" style="border: 0; outline: 0; background: transparent; color: var(--ink); font: inherit; flex-grow: 1" />
      </label>
      <a href="/sharing" class="sc-btn sc-btn-ghost" style="min-height: 3rem">${icon('key', 20)}${t('sharing.enterCode')}</a>
    </div>
    <div class="row" role="group" aria-label="${t('caseload.needs')}">
      <span class="row small muted" style="gap: 0.35rem; font-weight: 700">${icon('funnel', 18)}${t('caseload.needs')}</span>
      ${FILTERS.map((n) => html`<button class="sc-chip" data-act="filter" data-n="${n}" aria-pressed="${s.needs === n ? 'true' : 'false'}">${t(`caseload.filter.${n || 'all'}`)}</button>`)}
    </div>
    ${s.data && !rows().length
      ? emptyState(t('caseload.empty'))
      : html`<div class="sc-card table-wrap">
          <table class="data" style="min-width: 48rem">
            <thead><tr>
              <th scope="col">${t('caseload.person')}</th><th scope="col">${t('caseload.lastCheckin')}</th><th scope="col">${t('caseload.urgent')}</th>
              <th scope="col">${t('caseload.doses')}</th><th scope="col">${t('caseload.messages')}</th><th scope="col"><span class="visually-hidden">${t('common.open')}</span></th>
            </tr></thead>
            <tbody>
              ${rows().map(
                (p) => html`<tr>
                  <th scope="row" style="text-transform: none; letter-spacing: 0; font-size: 1rem; color: var(--ink)">${p.display_name}<br /><span class="tiny">${t(`roles.${p.patient_role}`)}</span></th>
                  <td>${'days_since_check_in' in p.facts ? lastCheckin(p.facts) : '—'}</td>
                  <td>${p.facts.urgent_yes_last_7_days ?? '—'}</td>
                  <td>${p.facts.doses_not_marked_yesterday ?? '—'}</td>
                  <td>${p.facts.unread_messages ?? '—'}</td>
                  <td style="text-align: right"><a href="/p/${p.patient_id}/summary" class="sc-chip" style="text-decoration: none">${t('caseload.open')}${icon('caret-right', 16)}</a></td>
                </tr>`,
              )}
            </tbody>
          </table>
        </div>`}
    <p class="tiny">${t('caseload.factsOnly')}</p>
  </main>`
  const redraw = () => ctx.draw(view())
  async function load() {
    s.data = await ctx.api.get('/patients/', { needs: s.needs })
    redraw()
  }
  redraw()
  await load().catch(() => redraw())

  ctx.on('click', '[data-act="filter"]', (el) => {
    s.needs = el.dataset.n
    load()
  })
  ctx.on('input', 'input[name="search"]', (el) => {
    s.search = el.value
    redraw()
  })
}
