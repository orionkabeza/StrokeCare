// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The doctor's home: who may need a look, today's appointments and unread messages, at a glance.
// Safety rule: plain facts the patients entered, listed by NAME. No risk score and no ranking by importance.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { emptyState, fmtTime, icon } from '../../ui.js'

const COUNTS = ['urgent', 'no_check_in', 'doses_not_marked', 'unread_messages']

export default async function doctorHome(ctx) {
  let o = null
  let error = ''
  const dayTime = (iso) => new Date(iso).toLocaleString(locale.value, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  const view = () => html`<main class="page">
    <header class="stack-s sc-rise">
      <h1>${t('doctor.hello', { name: o?.display_name ?? '' })}</h1>
      ${o ? html`<p class="muted">${t('doctor.people', { n: o.patients_total }, o.patients_total)}</p>` : ''}
    </header>
    ${o
      ? html`<section class="stack-s">
            <h2>${t('doctor.glance')}</h2>
            <div class="grid-2">
              ${COUNTS.map(
                (c) => html`<a href="${c === 'unread_messages' ? '/inbox' : `/caseload?needs=${c}`}" class="sc-card pad stack-s" style="text-decoration: none; color: var(--ink)">
                  <strong style="font-size: 2rem">${o.counts[c]}</strong><span class="small muted">${t(`doctor.reasons.${c}`)}</span>
                </a>`,
              )}
            </div>
          </section>

          <section class="stack-s">
            <h2>${t('doctor.needs')}</h2>
            <p class="small muted">${t('doctor.needsLead')}</p>
            ${!o.needs_a_look.length ? emptyState(t('doctor.none')) : ''}
            ${o.needs_a_look.map(
              (p) => html`<a href="/p/${p.patient_id}/summary" class="sc-card list-row" style="text-decoration: none; color: var(--ink)">
                <span class="sc-iconbox" style="width: 2.75rem; height: 2.75rem">${icon('users-three', 22, 'duotone')}</span>
                <span class="stack-s" style="flex-grow: 1"><strong>${p.display_name}</strong>${p.reasons.map((r) => html`<span class="small muted">${t(`doctor.reasons.${r}`)}</span>`)}</span>
                ${icon('caret-right', 18)}
              </a>`,
            )}
          </section>

          <section class="stack-s">
            <h2 class="row">${icon('calendar-check', 24, 'duotone')}${t('doctor.today')}</h2>
            ${!o.appointments_today.length ? emptyState(t('doctor.noToday')) : ''}
            ${o.appointments_today.map(
              (e) => html`<a href="/p/${e.patient_id}/calendar" class="sc-card list-row" style="text-decoration: none; color: var(--ink)">
                <strong style="width: 3.5rem">${fmtTime(e.starts_at)}</strong>
                <span class="stack-s"><strong>${e.patient_name}</strong><span class="small muted">${e.title}${e.location ? ` · ${e.location}` : ''}</span></span>
              </a>`,
            )}
            ${o.appointments_next_days.length
              ? html`<h3 class="sc-eyebrow" style="font-size: 0.85rem">${t('doctor.next')}</h3>
                  ${o.appointments_next_days.map(
                    (e) => html`<a href="/p/${e.patient_id}/calendar" class="sc-card list-row" style="text-decoration: none; color: var(--ink)">
                      <span class="stack-s"><strong>${e.patient_name}</strong><span class="small muted">${dayTime(e.starts_at)} · ${e.title}</span></span>
                    </a>`,
                  )}`
              : ''}
          </section>

          <a href="/caseload" class="sc-btn sc-btn-primary">${t('doctor.openCaseload')}</a>
          <p class="row small muted" style="flex-wrap: nowrap; align-items: flex-start">${icon('info', 18)}<span>${o.note}</span></p>`
      : ''}
    ${error ? html`<p class="error" role="alert">${error}</p>` : ''}
  </main>`
  ctx.draw(view())
  try {
    o = await ctx.api.get('/doctor/overview/')
  } catch (e) {
    error = errorText(e)
  }
  ctx.draw(view())
}
