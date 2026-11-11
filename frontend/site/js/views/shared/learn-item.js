// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Safety rule: every item shows its source and its review state. Draft content says so.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { canSpeak, speak } from '../../speech.js'
import { draftNote, icon, pageHeader } from '../../ui.js'

export default async function learnItem(ctx) {
  let data = null
  let error = ''
  const view = () => html`<main class="page">
    ${error ? html`<p class="error">${error}</p>` : ''}
    ${data
      ? html`${pageHeader({ title: data.title, subtitle: data.summary, back: true })}
          <div class="row">
            ${draftNote({ status: data.clinical_review.status, source: data.source.name })}
            ${data.source.url ? html`<a href="${data.source.url}" target="_blank" rel="noopener" class="small">${t('learn.source')}</a>` : ''}
          </div>
          ${canSpeak() ? html`<button class="sc-btn sc-btn-ghost" data-act="read">${icon('speaker-high', 22)}${t('common.readAloud')}</button>` : ''}
          ${data.video_url && !ctx.prefs.values.low_data_mode ? html`<video src="${data.video_url}" controls preload="none" style="width: 100%; border-radius: 1rem"></video>` : ''}
          <article class="sc-card pad-l" style="font-size: 1.1rem; line-height: 1.6; white-space: pre-line">${data.body}</article>
          ${data.fell_back ? html`<p class="tiny">${t('learn.fellBack')}</p>` : ''}`
      : ''}
  </main>`
  ctx.draw(view())
  try {
    data = await ctx.api.get(`/education/${ctx.params.slug}/`, { lang: locale.value })
  } catch (e) {
    error = errorText(e)
  }
  ctx.draw(view())
  ctx.on('click', '[data-act="read"]', () => speak(`${data.title}. ${data.body}`))
}
