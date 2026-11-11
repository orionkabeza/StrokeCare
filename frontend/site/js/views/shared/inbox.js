// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Safety rule: messages are not an emergency service; the notice from the server says so.
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { emptyState, fmtDateTime, icon, pageHeader } from '../../ui.js'

export default async function inbox(ctx) {
  let data = null
  const view = () => html`<main class="page">
    ${pageHeader({ title: t('messages.inbox'), subtitle: data?.notice })}
    ${data && !data.results.length ? emptyState(t('messages.noThreads')) : ''}
    ${(data?.results ?? []).map(
      (th) => html`<a href="/p/${th.patient_ref}/messages" class="sc-card pad row" style="text-decoration: none; color: var(--ink); flex-wrap: nowrap">
        <span class="sc-iconbox">${icon('chat-circle-text', 26, 'duotone')}</span>
        <span class="stack-s" style="flex-grow: 1; min-width: 0">
          <strong>${th.patient_ref === 'me' ? t('messages.myTeam') : th.patient_name}</strong>
          <span class="small muted" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">${th.last_message?.body ?? t('messages.none')}</span>
          ${th.last_message ? html`<span class="tiny">${fmtDateTime(th.last_message.created_at)}</span>` : ''}
        </span>
        ${th.unread ? html`<span class="sc-chip" aria-pressed="true" style="min-height: 2rem">${th.unread}</span>` : ''}
      </a>`,
    )}
  </main>`
  ctx.draw(view())
  try {
    data = await ctx.api.get('/inbox/')
  } catch {
    /* an empty list is shown */
  }
  ctx.draw(view())
}
