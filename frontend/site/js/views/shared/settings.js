// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Language, look, accessibility switches, the optional offline copy, sharing, export and account deletion.
// Every setting follows the person to any phone because it is saved to their account.
import { errorText } from '../../api.js'
import { copyEnabled, setCopyEnabled } from '../../copy.js'
import { html, raw } from '../../dom.js'
import { LOCALES, locale, setLocale, t } from '../../i18n.js'
import { icon, pageHeader, toast } from '../../ui.js'

const SWITCHES = [
  ['high_contrast', 'circle-half'], ['easy_read_font', 'text-aa'], ['reduce_motion', 'person-simple-walk'],
  ['audio_first', 'speaker-high'], ['one_question_at_a_time', 'list-checks'], ['one_handed_layout', 'hand-pointing'],
  ['low_data_mode', 'wifi-slash'],
]
const THEMES = [['system', 'circle-half'], ['light', 'sun'], ['dark', 'moon-stars']]
const SIZES = [100, 125, 150, 200]

const toggleRow = (on, attrs, iconName, title, hint, border = true) => html`<button role="switch" aria-checked="${on ? 'true' : 'false'}" ${raw(attrs)} class="row full"
  style="flex-wrap: nowrap; min-height: 4rem; padding: 0.5rem 0; border: 0; ${border ? 'border-bottom: 1px solid var(--line);' : ''} background: transparent; color: var(--ink); text-align: left; cursor: pointer">
  <span class="sc-iconbox" style="width: 2.6rem; height: 2.6rem">${icon(iconName, 22)}</span>
  <span class="stack-s" style="flex-grow: 1"><strong>${title}</strong><span class="tiny">${hint}</span></span>
  <span style="width: 3.25rem; height: 1.9rem; border-radius: 1rem; background: ${on ? 'var(--primary)' : 'var(--line-strong)'}; position: relative; flex-shrink: 0; transition: background-color .2s">
    <span style="position: absolute; top: 0.2rem; left: ${on ? '1.55rem' : '0.2rem'}; width: 1.5rem; height: 1.5rem; border-radius: 50%; background: #fff; transition: left .2s"></span>
  </span>
</button>`

export default async function settings(ctx) {
  const { auth, prefs } = ctx
  const view = () => {
    const user = auth.user
    return html`<main class="page">
      ${pageHeader({ title: t('settings.title'), subtitle: user ? `${user.display_name} · ${t(`roles.${user.role}`)}` : '' })}
      ${user && ['clinician', 'chw'].includes(user.role) ? html`<p class="banner">${user.is_verified_professional ? t('settings.verified') : t('settings.notVerified')}</p>` : ''}

      <section class="sc-card pad stack">
        <h2>${t('settings.language')}</h2>
        <div class="row" role="group" aria-label="${t('settings.language')}">
          ${LOCALES.map((l) => html`<button class="sc-chip" data-act="language" data-code="${l.code}" aria-pressed="${locale.value === l.code ? 'true' : 'false'}">${l.name}</button>`)}
        </div>
        <p class="tiny">${t('settings.translationNote')}</p>
      </section>

      <section class="sc-card pad stack">
        <h2>${t('settings.look')}</h2>
        <div class="grid-2" style="grid-template-columns: repeat(3, minmax(0, 1fr))">
          ${THEMES.map(([v, ic]) => html`<button class="sc-chip" style="flex-direction: column; min-height: 4.5rem; justify-content: center" data-act="pref" data-key="theme" data-value="${v}" aria-pressed="${prefs.values.theme === v ? 'true' : 'false'}">${icon(ic, 22)}${t(`settings.theme.${v}`)}</button>`)}
        </div>
        <div class="row" role="group" aria-label="${t('settings.textSize')}" style="flex-wrap: nowrap">
          ${SIZES.map((v, i) => html`<button class="sc-chip" style="flex: 1; justify-content: center; font-weight: 800; font-size: ${1 + i * 0.25}rem" data-act="pref" data-key="text_scale" data-value="${v}" aria-pressed="${prefs.values.text_scale === v ? 'true' : 'false'}" aria-label="${t(`settings.size.${v}`)}">A</button>`)}
        </div>
      </section>

      <section class="sc-card" style="padding: 0.25rem 1rem">
        ${SWITCHES.map(([key, ic]) => toggleRow(prefs.values[key], `data-act="switch" data-key="${key}"`, ic, t(`settings.pref.${key}`), t(`settings.prefHint.${key}`)))}
      </section>

      ${auth.isPatient
        ? html`<section class="sc-card" style="padding: 0.25rem 1rem">${toggleRow(copyEnabled.value, 'data-act="copy"', 'cloud-arrow-down', t('settings.offlineCopy'), t('settings.offlineCopyHint'), false)}</section>`
        : ''}

      ${auth.signedIn
        ? html`${auth.isPatient ? html`<a href="/reminders" class="sc-btn sc-btn-ghost">${icon('bell-ringing', 22)}${t('reminders.title')}</a><a href="/care-team" class="sc-btn sc-btn-ghost">${icon('users-three', 22)}${t('team.title')}</a>` : ''}
          ${auth.role !== 'admin' ? html`<a href="/sharing" class="sc-btn sc-btn-ghost">${icon('share-network', 22)}${t('sharing.title')}</a>` : ''}
          <button class="sc-btn sc-btn-ghost" data-act="export">${icon('download-simple', 22)}${t('settings.export')}</button>
          <button class="sc-btn sc-btn-ghost" data-act="signout">${icon('sign-out', 22)}${t('auth.signOut')}</button>
          <details class="sc-card pad">
            <summary style="cursor: pointer; font-weight: 700">${t('settings.delete')}</summary>
            <div class="stack" style="margin-top: 0.75rem">
              <p class="small muted">${t('settings.deleteHint')}</p>
              <label class="field">${t('auth.password')}<input name="delete_password" class="sc-input" type="password" autocomplete="current-password" /></label>
              <button class="sc-btn sc-btn-danger" data-act="delete">${icon('trash', 20)}${t('settings.deleteButton')}</button>
            </div>
          </details>`
        : ''}
    </main>`
  }
  const redraw = () => ctx.draw(view())
  redraw()
  // Keep the open details panel open when the screen redraws.
  const pick = async (key, value) => {
    try {
      await prefs.set(key, value, auth.signedIn)
    } catch (e) {
      toast(errorText(e))
    }
    redraw()
  }

  ctx.on('click', '[data-act="language"]', async (el) => {
    await setLocale(el.dataset.code) // the router redraws this screen in the new language
    if (auth.signedIn) {
      try {
        auth.user = await ctx.api.patch('/me/', { preferred_language: el.dataset.code })
      } catch (e) {
        toast(errorText(e))
      }
    }
  })
  ctx.on('click', '[data-act="pref"]', (el) => pick(el.dataset.key, el.dataset.key === 'text_scale' ? Number(el.dataset.value) : el.dataset.value))
  ctx.on('click', '[data-act="switch"]', (el) => pick(el.dataset.key, !prefs.values[el.dataset.key]))
  ctx.on('click', '[data-act="copy"]', () => {
    const turningOff = copyEnabled.value
    setCopyEnabled(!copyEnabled.value)
    if (turningOff) toast(t('settings.offlineCopyRemoved'))
    redraw()
  })
  ctx.on('click', '[data-act="export"]', async () => {
    try {
      const blob = await ctx.api.blob('/me/export/')
      const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'strokecare-my-data.json' })
      a.click()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="signout"]', async () => {
    await auth.logout()
    ctx.go('/welcome', { replace: true })
  })
  ctx.on('click', '[data-act="delete"]', async () => {
    const password = ctx.el.querySelector('[name="delete_password"]')?.value
    if (!password || !confirm(t('settings.deleteConfirm'))) return
    try {
      await ctx.api.del('/me/', { password })
      auth.forget()
      ctx.go('/welcome', { replace: true })
    } catch (e) {
      toast(errorText(e))
    }
  })
}
