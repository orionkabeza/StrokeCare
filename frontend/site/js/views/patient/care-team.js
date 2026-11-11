// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// "My care team": who may see my records, my current stage and my next appointment. The person always knows who
// can see their information, and can change it under Sharing.
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { emptyState, fmtDateTime, fmtDay, icon, pageHeader } from '../../ui.js'

export default async function careTeam(ctx) {
  let data = null
  const view = () => html`<main class="page">
    ${pageHeader({ title: t('team.title'), subtitle: t('team.lead'), back: true })}
    ${data?.current_phase
      ? html`<section class="sc-card pad stack-s"><span class="sc-eyebrow">${t('recovery.stage')}</span>
          <strong style="font-size: 1.2rem">${data.current_phase.name}</strong><a href="/p/me/recovery" class="small">${t('recovery.title')}</a></section>`
      : ''}
    <a href="/p/me/calendar" class="sc-card pad row" style="text-decoration: none; color: var(--ink)">
      <span class="sc-iconbox">${icon('calendar-check', 26, 'duotone')}</span>
      <span class="stack-s">
        <span class="sc-eyebrow">${t('team.next')}</span>
        ${data?.next_appointment
          ? html`<strong>${data.next_appointment.title}</strong><span class="small muted">${fmtDateTime(data.next_appointment.starts_at)}</span>`
          : html`<span class="muted">${t('team.noNext')}</span>`}
      </span>
    </a>
    ${data && !data.team.length ? emptyState(t('team.none')) : ''}
    ${(data?.team ?? []).map(
      (m) => html`<div class="sc-card list-row">
        <span class="sc-iconbox">${icon(m.relation === 'clinician' ? 'stethoscope' : 'users-three', 24, 'duotone')}</span>
        <span class="stack-s" style="flex-grow: 1">
          <strong>${m.display_name}</strong>
          <span class="small muted">${t(`roles.${m.relation}`)}${m.since ? ` · ${t('team.since', { date: fmtDay(m.since) })}` : ''}</span>
        </span>
      </div>`,
    )}
    <div class="grid-2">
      <a href="/p/me/messages" class="sc-btn sc-btn-primary">${icon('chat-circle-text', 20)}${t('team.message')}</a>
      <a href="/sharing" class="sc-btn sc-btn-ghost">${icon('share-network', 20)}${t('team.manage')}</a>
    </div>
  </main>`
  ctx.draw(view())
  try {
    data = await ctx.api.get('/me/care-team/')
  } catch {
    /* the page stays as it is */
  }
  ctx.draw(view())
}
