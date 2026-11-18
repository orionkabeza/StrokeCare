// Owner: Emmanuel Happy Rangira (Frontend developer)
// Education grouped by stroke topic, with videos and text side by side. Topic names and every item in them are
// medical content: they come from the API, draft items stay marked, and nothing here is written in the UI.
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { draftNote, emptyState, icon, pageHeader } from '../../ui.js'

const fmtDuration = (seconds) => t('learn.minutes', { n: Math.max(1, Math.round(seconds / 60)) })

export default async function learn(ctx) {
  const s = { topics: [], items: [], active: 'all', loading: true }

  const videoCard = (item, delay) => html`<a href="/learn/${item.slug}" class="sc-card sc-rise stack-s" style="animation-delay: ${delay}ms; text-decoration: none; color: var(--ink); overflow: hidden; padding: 0">
    <div style="position: relative; aspect-ratio: 16 / 9; background: var(--surface-2)">
      ${item.poster_url ? html`<img src="${item.poster_url}" alt="" style="width: 100%; height: 100%; object-fit: cover; display: block" />` : ''}
      <span aria-hidden="true" style="position: absolute; inset: 0; display: grid; place-items: center">
        <span style="width: 56px; height: 56px; border-radius: 999px; background: #fff; display: grid; place-items: center; box-shadow: var(--shadow-2)">${icon('play', 24, 'fill')}</span>
      </span>
      ${item.duration_seconds ? html`<span class="tiny" style="position: absolute; right: 0.6rem; bottom: 0.6rem; background: rgba(0,0,0,0.6); color: #fff; padding: 0.15rem 0.6rem; border-radius: 999px">${fmtDuration(item.duration_seconds)}</span>` : ''}
    </div>
    <div class="pad stack-s" style="padding-top: 0.25rem">
      <strong style="font-size: 1.1rem">${item.title}</strong>
      <span class="muted small">${item.summary}</span>
      <span class="row" style="gap: 0.5rem">${icon('play', 14, 'fill')}<span class="tiny">${t('learn.video')}</span>${draftNote({ status: item.clinical_review.status, source: item.source.name })}</span>
    </div>
  </a>`

  const textCard = (item, delay) => html`<a href="/learn/${item.slug}" class="sc-card sc-rise pad row" style="animation-delay: ${delay}ms; text-decoration: none; color: var(--ink); align-items: flex-start">
    <span class="sc-iconbox">${icon('book-open-text', 26, 'duotone')}</span>
    <span class="stack-s">
      <strong style="font-size: 1.1rem">${item.title}</strong>
      <span class="muted small">${item.summary}</span>
      <span class="row" style="gap: 0.5rem"><span class="tiny">${t('learn.read')}</span>${draftNote({ status: item.clinical_review.status, source: item.source.name })}${item.fell_back ? html`<span class="tiny">${t('learn.fellBack')}</span>` : ''}</span>
    </span>
  </a>`

  const topicSection = (name, items) => {
    const videos = items.filter((i) => i.kind === 'video').length
    const toRead = items.length - videos
    const count = [videos ? t('learn.videosCount', { n: videos }, videos) : '', toRead ? t('learn.toReadCount', { n: toRead }) : ''].filter(Boolean).join(' · ')
    return html`<section class="sc-card pad stack">
      <div class="stack-s"><h2>${name}</h2>${count ? html`<span class="small muted">${count}</span>` : ''}</div>
      <div class="stack">${items.map((item, i) => (item.kind === 'video' ? videoCard(item, i * 40) : textCard(item, i * 40)))}</div>
    </section>`
  }

  const view = () => {
    const byTopic = s.topics
      .map((topic) => ({ topic, items: s.items.filter((i) => i.topic?.slug === topic.slug) }))
      .filter((g) => (s.active === 'all' ? g.items.length : g.topic.slug === s.active))
    const loose = s.active === 'all' ? s.items.filter((i) => !i.topic) : []
    return html`<main class="page">
      ${pageHeader({ title: t('learn.title'), subtitle: t('learn.lead') })}
      <div class="row" role="tablist" aria-label="${t('learn.topics')}" style="flex-wrap: nowrap; overflow-x: auto; padding-bottom: 0.25rem">
        <button role="tab" class="sc-chip" style="flex-shrink: 0" aria-selected="${s.active === 'all' ? 'true' : 'false'}" aria-pressed="${s.active === 'all' ? 'true' : 'false'}" data-act="topic" data-slug="all">${t('learn.allTopics')}</button>
        ${s.topics.map((topic) => html`<button role="tab" class="sc-chip" style="flex-shrink: 0; white-space: nowrap" aria-selected="${s.active === topic.slug ? 'true' : 'false'}" aria-pressed="${s.active === topic.slug ? 'true' : 'false'}" data-act="topic" data-slug="${topic.slug}">${topic.name}</button>`)}
      </div>
      ${!s.loading && !s.items.length ? emptyState(t('learn.empty')) : ''}
      ${byTopic.map((g) => topicSection(g.topic.name, g.items))}
      ${loose.length ? topicSection(t('learn.moreTopics'), loose) : ''}
    </main>`
  }
  ctx.draw(view())

  const [topicsRes, itemsRes] = await Promise.allSettled([
    ctx.api.get('/education/topics/', { lang: locale.value }),
    ctx.api.get('/education/', { lang: locale.value }),
  ])
  s.topics = topicsRes.status === 'fulfilled' ? (topicsRes.value.results ?? []) : []
  s.items = itemsRes.status === 'fulfilled' ? (itemsRes.value.results ?? []) : []
  s.loading = false
  ctx.draw(view())

  ctx.on('click', '[data-act="topic"]', (el) => {
    s.active = el.dataset.slug
    ctx.draw(view())
  })
}
