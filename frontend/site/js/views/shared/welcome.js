// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
import { html } from '../../dom.js'
import { LOCALES, locale, setLocale, t } from '../../i18n.js'
import { icon } from '../../ui.js'

export default function welcome(ctx) {
  ctx.draw(html`<main class="page">
    <section class="hero-head sc-hero">
      <div class="sc-rise stack-s">
        <h1 style="font-size: 2rem">${t('welcome.title')}</h1>
        <p class="muted" style="font-size: 1.05rem">${t('welcome.lead')}</p>
      </div>
      <div role="group" aria-label="${t('settings.language')}" class="row">
        ${LOCALES.map((l) => html`<button class="sc-chip" data-lang="${l.code}" aria-pressed="${locale.value === l.code ? 'true' : 'false'}">${l.name}</button>`)}
      </div>
    </section>
    <div class="stack sc-rise" style="animation-delay: 80ms">
      <a href="/login" class="sc-btn sc-btn-primary">${icon('sign-in', 22)}${t('auth.signIn')}</a>
      <a href="/register" class="sc-btn sc-btn-ghost">${icon('user-plus', 22)}${t('auth.create')}</a>
    </div>
    <div class="grid-2 sc-rise" style="animation-delay: 140ms">
      <a href="/talk" class="sc-card pad stack-s" style="text-decoration: none; color: var(--ink)">
        <span class="sc-iconbox">${icon('chat-circle-text', 28, 'duotone')}</span>
        <strong>${t('talk.title')}</strong><span class="small muted">${t('talk.short')}</span>
      </a>
      <a href="/learn" class="sc-card pad stack-s" style="text-decoration: none; color: var(--ink)">
        <span class="sc-iconbox sc-iconbox-accent">${icon('book-open-text', 28, 'duotone')}</span>
        <strong>${t('learn.title')}</strong><span class="small muted">${t('learn.short')}</span>
      </a>
    </div>
    <p class="tiny">${t('welcome.safety')}</p>
  </main>`)
  // Choosing a language redraws the app in that language (the router listens for the change).
  ctx.on('click', '[data-lang]', (el) => setLocale(el.dataset.lang))
}
