// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { draftNote, emptyState, icon, pageHeader } from '../../ui.js'

export default async function learn(ctx) {
  let data = null
  let loading = true
  const view = () => html`<main class="page">
    ${pageHeader({ title: t('learn.title'), subtitle: t('learn.lead') })}
    ${!loading && !data?.results?.length ? emptyState(t('learn.empty')) : ''}
    ${(data?.results ?? []).map(
      (item, i) => html`<a href="/learn/${item.slug}" class="sc-card sc-rise pad row" style="animation-delay: ${i * 40}ms; text-decoration: none; color: var(--ink); align-items: flex-start">
        <span class="sc-iconbox sc-iconbox-accent">${icon('book-open-text', 26, 'duotone')}</span>
        <span class="stack-s">
          <strong style="font-size: 1.1rem">${item.title}</strong>
          <span class="muted small">${item.summary}</span>
          <span class="row" style="gap: 0.4rem">${draftNote({ status: item.clinical_review.status, source: item.source.name })}${item.fell_back ? html`<span class="tiny">${t('learn.fellBack')}</span>` : ''}</span>
        </span>
      </a>`,
    )}
  </main>`
  ctx.draw(view())
  try {
    data = await ctx.api.get('/education/', { lang: locale.value })
  } catch {
    /* an empty list is shown */
  }
  loading = false
  ctx.draw(view())
}
