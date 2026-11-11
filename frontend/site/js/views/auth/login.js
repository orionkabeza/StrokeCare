// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { icon } from '../../ui.js'

export default function login(ctx) {
  const s = { error: '', busy: false }
  const view = () => html`<main class="page" style="max-width: 28rem; padding-top: 2.5rem">
    <span class="brand-mark sc-pop" style="width: 3.5rem; height: 3.5rem; border-radius: 1.1rem">${icon('heartbeat', 32, 'duotone')}</span>
    <h1>${t('auth.signIn')}</h1>
    <form class="stack" data-form="login">
      <label class="field">${t('auth.email')}<input name="email" class="sc-input" type="email" autocomplete="email" required /></label>
      <label class="field">${t('auth.password')}<input name="password" class="sc-input" type="password" autocomplete="current-password" required /></label>
      ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
      <button class="sc-btn sc-btn-primary" ${s.busy ? 'disabled' : ''}>${t('auth.signIn')}</button>
    </form>
    <p class="muted">${t('auth.noAccount')} <a href="/register">${t('auth.create')}</a></p>
    <a href="/emergency" class="sc-emergency" style="align-self: flex-start">${t('emergency.button')}</a>
  </main>`
  ctx.draw(view())

  ctx.on('submit', 'form[data-form="login"]', async (form, event) => {
    event.preventDefault()
    const data = new FormData(form)
    s.busy = true
    s.error = ''
    ctx.draw(view())
    try {
      await ctx.auth.login(String(data.get('email')), String(data.get('password')))
      ctx.go(ctx.auth.needsConsent ? '/consent' : (ctx.query.next ?? ctx.auth.home), { replace: true })
    } catch (e) {
      s.error = errorText(e)
      s.busy = false
      ctx.draw(view())
    }
  })
}
