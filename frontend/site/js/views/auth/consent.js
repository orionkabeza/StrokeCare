// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { icon } from '../../ui.js'

export default function consent(ctx) {
  const { auth } = ctx
  const s = { ticked: {}, error: '' }
  const kinds = () => Object.keys(auth.consents)
  const ready = () => kinds().every((k) => s.ticked[k] || auth.consents[k].granted)
  const view = () => html`<main class="page" style="max-width: 34rem; padding-top: 2rem">
    <span class="sc-iconbox">${icon('shield-check', 28, 'duotone')}</span>
    <h1>${t('consent.title')}</h1>
    <p class="banner">${t('consent.draft')}</p>
    ${kinds().map(
      (k) => html`<div class="sc-card pad stack">
        <h2>${t(`consent.${k}.title`)}</h2>
        <p class="muted">${t(`consent.${k}.body`)}</p>
        ${!auth.consents[k].granted
          ? html`<label class="check"><input type="checkbox" name="agree" value="${k}" ${s.ticked[k] ? 'checked' : ''} data-act="tick" data-kind="${k}" />${t(`consent.${k}.agree`)}</label>`
          : html`<p class="small muted">${t('consent.given')}</p>`}
      </div>`,
    )}
    ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
    <button class="sc-btn sc-btn-primary" data-act="accept" ${ready() ? '' : 'disabled'}>${t('consent.continue')}</button>
    <button class="sc-btn sc-btn-ghost" data-act="signout">${t('auth.signOut')}</button>
  </main>`
  ctx.draw(view())

  ctx.on('change', '[data-act="tick"]', (el) => {
    s.ticked[el.dataset.kind] = el.checked
    ctx.draw(view())
  })
  ctx.on('click', '[data-act="accept"]', async () => {
    try {
      for (const k of kinds()) if (!auth.consents[k].granted) await auth.giveConsent(k)
      ctx.go(auth.home, { replace: true })
    } catch (e) {
      s.error = errorText(e)
      ctx.draw(view())
    }
  })
  ctx.on('click', '[data-act="signout"]', async () => {
    await auth.logout()
    ctx.go('/welcome', { replace: true })
  })
}
