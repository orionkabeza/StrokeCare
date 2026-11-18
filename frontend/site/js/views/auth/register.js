// Owner: Emmanuel Happy Rangira (Frontend developer)
import { ApiError, errorText } from '../../api.js'
import { html } from '../../dom.js'
import { LOCALES, locale, t } from '../../i18n.js'

export default function register(ctx) {
  const s = { error: '', fields: {} }
  const view = () => html`<main class="page" style="max-width: 30rem; padding-top: 2rem">
    <h1>${t('auth.create')}</h1>
    <form class="sc-card pad-l stack" data-form="register">
      <fieldset class="stack-s" style="border: 0; padding: 0; margin: 0">
        <legend class="field" style="margin-bottom: 0.4rem">${t('auth.iAm')}</legend>
        ${['survivor', 'prevention', 'caregiver'].map(
          (r) => html`<label class="check" style="padding: 0.75rem; border: 1.5px solid var(--line-strong); border-radius: 12px">
            <input type="radio" name="role" value="${r}" ${r === 'survivor' ? 'checked' : ''} />
            <span class="stack-s"><strong>${t(`roles.${r}`)}</strong><span class="small muted">${t(`roles.${r}Hint`)}</span></span>
          </label>`,
        )}
      </fieldset>
      <label class="field">${t('auth.name')}<input name="display_name" class="sc-input" autocomplete="name" required /></label>
      <label class="field">${t('auth.email')}<input name="email" class="sc-input" type="email" autocomplete="email" required />
        ${s.fields.email ? html`<span class="error">${s.fields.email[0]}</span>` : ''}</label>
      <label class="field">${t('auth.password')}<input name="password" class="sc-input" type="password" autocomplete="new-password" required />
        <span class="tiny">${t('auth.passwordHint')}</span>${s.fields.password ? html`<span class="error">${s.fields.password[0]}</span>` : ''}</label>
      <label class="field">${t('settings.language')}
        <select name="preferred_language" class="sc-input">${LOCALES.map((l) => html`<option value="${l.code}" ${l.code === locale.value ? 'selected' : ''}>${l.name}</option>`)}</select></label>
      ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
      <button class="sc-btn sc-btn-primary">${t('auth.create')}</button>
    </form>
    <p class="muted">${t('auth.haveAccount')} <a href="/login">${t('auth.signIn')}</a></p>
  </main>`
  ctx.draw(view())

  ctx.on('submit', 'form[data-form="register"]', async (form, event) => {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(form).entries())
    s.error = ''
    s.fields = {}
    try {
      await ctx.auth.register({ ...data, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Africa/Kigali' })
      ctx.go('/consent', { replace: true })
    } catch (e) {
      if (e instanceof ApiError) s.fields = e.fields
      s.error = errorText(e)
      ctx.draw(view())
    }
  })
}
