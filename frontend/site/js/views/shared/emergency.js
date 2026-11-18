// Owner: Emmanuel Happy Rangira (Frontend developer)
// Safety rule: no service number is shown until a named person has verified it. Without one, the screen says to
// contact local emergency services the usual way and never to wait for the app. The person's own contacts
// (usually relatives) come after the verified services, never before them.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { icon, toast } from '../../ui.js'

const callRow = ({ title, phone, note, danger, removeId }) => html`<div class="sc-card pad row" style="flex-wrap: nowrap">
  <a href="tel:${phone.replace(/[^\d+]/g, '')}" class="row" style="flex: 1; min-width: 0; flex-wrap: nowrap; text-decoration: none; color: var(--ink)">
    <span class="sc-iconbox">${icon('phone-call', 26, 'duotone')}</span>
    <span class="stack-s" style="flex: 1; min-width: 0">
      <strong style="font-size: 1.15rem">${title}</strong>
      <span style="font-variant-numeric: tabular-nums; white-space: nowrap">${phone}</span>
      ${note}
    </span>
    <span class="sc-btn ${danger ? 'sc-btn-danger' : 'sc-btn-primary'}" style="min-height: 3rem; padding: 0 1rem">${t('emergency.call')}</span>
  </a>
  ${removeId ? html`<button class="icon-btn" data-act="remove" data-id="${removeId}" aria-label="${t('emergency.remove', { name: title })}">${icon('trash', 20)}</button>` : ''}
</div>`

export default async function emergency(ctx) {
  const signedIn = ctx.auth.signedIn
  const s = { data: null, mine: [], adding: false, error: '', busy: false }

  const view = () => html`<main class="page">
    <section class="stack" style="background: var(--danger); color: var(--on-danger); padding: 1.5rem; border-radius: 1.5rem; gap: 0.75rem">
      <span class="sc-pop" style="width: 4.5rem; height: 4.5rem; border-radius: 1rem; display: grid; place-items: center; background: rgba(255,255,255,.16)">${icon('phone-call', 44, 'fill')}</span>
      <h1 style="font-size: 2rem">${t('emergency.title')}</h1>
      <p style="font-size: 1.3rem; font-weight: 700; line-height: 1.4">${s.data?.message ?? t('emergency.fallback')}</p>
    </section>
    ${s.data?.contacts?.length
      ? html`<section class="stack" aria-label="${t('emergency.numbers')}">
          ${s.data.contacts.map((c) => callRow({
            title: c.label, phone: c.phone, danger: true,
            note: html`<span class="tiny row" style="gap: 0.3rem; flex-wrap: nowrap; align-items: flex-start">${icon('check-circle', 16, 'fill')}<span>${t('emergency.verifiedBy', { name: c.verified_by })}${c.hours ? ` · ${c.hours}` : ''}</span></span>`,
          }))}
        </section>`
      : html`<section class="sc-card pad row" style="align-items: flex-start">
          <span class="sc-iconbox">${icon('phone-call', 26, 'duotone')}</span>
          <div class="stack-s"><h2>${t('emergency.numbers')}</h2><p class="muted">${t('emergency.noVerified')}</p></div>
        </section>`}
    ${signedIn
      ? html`<section class="stack" aria-labelledby="my-people">
          <div class="stack-s"><h2 id="my-people">${t('emergency.myPeople')}</h2><p class="small muted">${t('emergency.myPeopleHint')}</p></div>
          ${s.mine.map((c) => callRow({ title: c.name, phone: c.phone, removeId: c.id, note: c.relation ? html`<span class="tiny">${c.relation}</span>` : '' }))}
          ${s.adding
            ? html`<form class="sc-card pad-l stack" data-form="person">
                <label class="field">${t('emergency.name')}<input name="name" class="sc-input" maxlength="80" autocomplete="off" required /></label>
                <label class="field">${t('emergency.relation')}<input name="relation" class="sc-input" maxlength="40" placeholder="${t('emergency.relationExample')}" /></label>
                <label class="field">${t('emergency.phone')}<input name="phone" class="sc-input" type="tel" inputmode="tel" autocomplete="tel" maxlength="24" required /></label>
                ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
                <div class="grid-2">
                  <button type="button" class="sc-btn sc-btn-ghost" data-act="cancel">${t('common.cancel')}</button>
                  <button class="sc-btn sc-btn-primary" ${s.busy ? 'disabled' : ''}>${t('common.save')}</button>
                </div>
              </form>`
            : html`<button class="sc-btn sc-btn-ghost" data-act="add">${icon('user-plus', 22)}${t('emergency.addPerson')}</button>`}
        </section>`
      : ''}
  </main>`
  const redraw = () => ctx.draw(view())
  redraw()
  const [guidance, mine] = await Promise.allSettled([
    ctx.api.get('/emergency/'),
    signedIn ? ctx.api.get('/me/emergency-contacts/') : Promise.resolve({ results: [] }),
  ])
  if (guidance.status === 'fulfilled') s.data = guidance.value // otherwise the fallback message already says what to do
  if (mine.status === 'fulfilled') s.mine = mine.value.results ?? []
  redraw()

  ctx.on('click', '[data-act="add"]', () => {
    s.adding = true
    s.error = ''
    redraw()
    ctx.el.querySelector('[name="name"]')?.focus()
  })
  ctx.on('click', '[data-act="cancel"]', () => {
    s.adding = false
    redraw()
  })
  ctx.on('submit', 'form[data-form="person"]', async (form, event) => {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(form))
    s.busy = true
    try {
      s.mine = [...s.mine, await ctx.api.post('/me/emergency-contacts/', data)]
      s.adding = false
      s.error = ''
    } catch (e) {
      s.error = errorText(e)
    }
    s.busy = false
    redraw()
    if (s.error) Object.entries(data).forEach(([k, v]) => { const el = ctx.el.querySelector(`[name="${k}"]`); if (el) el.value = v })
  })
  ctx.on('click', '[data-act="remove"]', async (el) => {
    const person = s.mine.find((c) => c.id === el.dataset.id)
    if (!person || !confirm(t('emergency.removeConfirm', { name: person.name }))) return
    try {
      await ctx.api.del(`/me/emergency-contacts/${person.id}/`)
      s.mine = s.mine.filter((c) => c.id !== person.id)
      redraw()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
