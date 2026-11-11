// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Safety rule: no phone number is shown until a named person has verified it. Without one, the screen says to
// contact local emergency services the usual way and never to wait for the app.
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { icon } from '../../ui.js'

export default async function emergency(ctx) {
  let data = null
  const view = () => html`<main class="page">
    <section class="hero-head" style="background: var(--danger); color: var(--on-danger)">
      <span class="sc-pop" style="width: 4.5rem; height: 4.5rem; border-radius: 1.5rem; display: grid; place-items: center; background: rgba(255,255,255,.16)">${icon('siren', 44, 'duotone')}</span>
      <h1 style="font-size: 2rem">${t('emergency.title')}</h1>
      <p style="font-size: 1.3rem; font-weight: 700; line-height: 1.4">${data?.message ?? t('emergency.fallback')}</p>
    </section>
    ${data?.contacts?.length
      ? html`<section class="stack">
          ${data.contacts.map(
            (c) => html`<a href="tel:${c.phone}" class="sc-card pad row" style="text-decoration: none; color: var(--ink)">
              <span class="sc-iconbox">${icon('phone-call', 26, 'duotone')}</span>
              <span class="stack-s" style="flex-grow: 1">
                <strong style="font-size: 1.15rem">${c.label}</strong>
                <span>${c.phone}${c.hours ? ` · ${c.hours}` : ''}</span>
                <span class="tiny row" style="gap: 0.3rem">${icon('check-circle', 16, 'fill')}${t('emergency.verifiedBy', { name: c.verified_by })}</span>
              </span>
              <span class="sc-btn sc-btn-danger" style="min-height: 3rem">${t('emergency.call')}</span>
            </a>`,
          )}
        </section>`
      : html`<section class="sc-card pad row" style="align-items: flex-start">
          <span class="sc-iconbox">${icon('phone-call', 26, 'duotone')}</span>
          <div class="stack-s"><h2>${t('emergency.numbers')}</h2><p class="muted">${t('emergency.noVerified')}</p></div>
        </section>`}
  </main>`
  ctx.draw(view())
  try {
    data = await ctx.api.get('/emergency/')
    ctx.draw(view())
  } catch {
    /* the fallback message above already says what to do */
  }
}
