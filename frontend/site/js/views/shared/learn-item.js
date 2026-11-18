// Owner: Emmanuel Happy Rangira (Frontend developer)
// Safety rule: every item shows its source and its review state. Draft content says so.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { canSpeak, speak } from '../../speech.js'
import { draftNote, icon, pageHeader } from '../../ui.js'

// A rough download estimate for the low-data "tap to play" prompt: 480p video runs about 1 MB per 2.5 seconds.
const roughSizeMb = (seconds) => Math.max(1, Math.round(seconds / 2.5 / 1024))
const YT_ID = /^https:\/\/(?:www\.|m\.)?(?:youtube\.com\/watch\?(?:.*&)?v=|youtu\.be\/)([\w-]{11})/
export const youtubeId = (url) => YT_ID.exec(url ?? '')?.[1] ?? null

// YouTube's player loads only after a tap, from the no-cookie domain, so opening this page contacts nobody else.
const youtubePlayer = (id, title, playing) => playing
  ? html`<div style="position: relative; aspect-ratio: 16 / 9; border-radius: 1rem; overflow: hidden; background: #000">
      <iframe src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&cc_load_policy=1&hl=${locale.value}" title="${title}"
        allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"
        style="position: absolute; inset: 0; width: 100%; height: 100%; border: 0"></iframe>
    </div>`
  : html`<button type="button" class="sc-card" data-act="play-youtube" aria-label="${t('learn.playVideo')}: ${title}"
      style="position: relative; display: block; width: 100%; padding: 0; overflow: hidden; cursor: pointer; aspect-ratio: 16 / 9; background: var(--surface-2)">
      <img src="https://i.ytimg.com/vi/${id}/hqdefault.jpg" alt="" style="width: 100%; height: 100%; object-fit: cover; display: block" />
      <span aria-hidden="true" style="position: absolute; inset: 0; display: grid; place-items: center">
        <span style="width: 64px; height: 64px; border-radius: 999px; background: #fff; color: #111; display: grid; place-items: center; box-shadow: var(--shadow-2)">${icon('play', 28, 'fill')}</span>
      </span>
    </button>`

export default async function learnItem(ctx) {
  let data = null
  let error = ''
  let playRequested = false
  const video = () => {
    if (!data?.video_url) return ''
    if (!navigator.onLine) return html`<p class="sc-banner-info">${icon('wifi-slash', 20)}${t('learn.needsConnection')}</p>`
    const yt = youtubeId(data.video_url)
    if (yt) return youtubePlayer(yt, data.title, playRequested)
    if (ctx.prefs.values.low_data_mode && !playRequested) {
      const size = data.duration_seconds ? `${roughSizeMb(data.duration_seconds)} MB` : '?'
      return html`<button type="button" class="sc-card" style="position: relative; width: 100%; padding: 0; overflow: hidden; cursor: pointer; border: 0" data-act="play-anyway">
        ${data.poster_url ? html`<img src="${data.poster_url}" alt="" style="width: 100%; aspect-ratio: 16 / 9; object-fit: cover; display: block" />` : html`<span style="display: block; aspect-ratio: 16 / 9; background: var(--surface-2)"></span>`}
        <span class="sc-btn sc-btn-primary" style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%)">${icon('play', 20, 'fill')}${t('learn.playVideoSize', { size })}</span>
      </button>`
    }
    return html`<video src="${data.video_url}" poster="${data.poster_url || ''}" controls preload="none" style="width: 100%; border-radius: 1rem">
      ${data.captions_url ? html`<track kind="captions" src="${data.captions_url}" srclang="${data.locale_served}" default />` : ''}
    </video>`
  }
  const view = () => html`<main class="page">
    ${error ? html`<p class="error">${error}</p>` : ''}
    ${data
      ? html`${pageHeader({ title: data.title, subtitle: data.summary, back: true })}
          <div class="row">
            ${draftNote({ status: data.clinical_review.status, source: data.source.name })}
            ${data.source.url ? html`<a href="${data.source.url}" target="_blank" rel="noopener" class="small">${t('learn.source')}</a>` : ''}
          </div>
          ${canSpeak() ? html`<button class="sc-btn sc-btn-ghost" data-act="read">${icon('speaker-high', 22)}${t('common.readAloud')}</button>` : ''}
          ${video()}
          ${data.video_url ? html`<p class="tiny">${youtubeId(data.video_url) ? t('learn.fromYoutube', { source: data.source.name }) : t('learn.transcript')}</p>` : ''}
          <article class="sc-card pad-l" style="font-size: 1.1rem; line-height: 1.6; white-space: pre-line; max-width: 65ch">${data.body}</article>
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
  ctx.on('click', '[data-act="play-anyway"], [data-act="play-youtube"]', () => {
    playRequested = true
    ctx.draw(view())
  })
}
