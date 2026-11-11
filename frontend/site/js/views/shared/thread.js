// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The care-team conversation for one person. It checks for new messages every 20 seconds while it is open.
// Safety rule: messages are not an emergency service; the notice says so.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { emptyState, fmtDateTime, icon, pageHeader, toast } from '../../ui.js'

export default async function thread(ctx) {
  const { base } = ctx
  const s = { messages: [], notice: '' }
  const view = () => html`<main class="page">
    ${pageHeader({ title: t('messages.title'), back: true })}
    <p class="banner">${icon('info', 20)}${s.notice || t('messages.notice')}</p>
    ${!s.messages.length ? emptyState(t('messages.none')) : ''}
    <ol class="list" aria-live="polite" data-list>
      ${s.messages.map(
        (m) => html`<li style="align-self: ${m.mine ? 'flex-end' : 'flex-start'}; max-width: 85%">
          <div class="sc-card pad" style="${m.mine ? 'background: var(--primary); color: var(--on-primary); border-color: var(--primary)' : ''}"><p style="white-space: pre-line">${m.body}</p></div>
          <p class="tiny" style="text-align: ${m.mine ? 'right' : 'left'}; margin-top: 0.25rem">
            ${m.mine ? t('messages.you') : `${m.sender_name} · ${t(`roles.${m.sender_role}`)}`} · ${fmtDateTime(m.created_at)}
          </p>
        </li>`,
      )}
    </ol>
    <form class="row thumb-actions" style="flex-wrap: nowrap; position: sticky; bottom: 5.75rem" data-form="message">
      <label class="visually-hidden" for="msg">${t('messages.write')}</label>
      <textarea id="msg" name="body" class="sc-input" placeholder="${t('messages.write')}" maxlength="2000" rows="2" style="min-height: 3.5rem"></textarea>
      <button class="sc-btn sc-btn-primary" style="width: 3.5rem; padding: 0" aria-label="${t('messages.send')}">${icon('paper-plane-right', 22, 'fill')}</button>
    </form>
  </main>`
  const redraw = () => ctx.draw(view())

  async function load() {
    try {
      const r = await ctx.api.get(`${base}/messages/`)
      const grew = r.results.length !== s.messages.length
      s.messages = r.results
      s.notice = r.notice
      redraw()
      await ctx.api.post(`${base}/messages/read/`)
      if (grew) ctx.el.querySelector('[data-list]')?.lastElementChild?.scrollIntoView({ block: 'end' })
    } catch (e) {
      toast(errorText(e))
    }
  }
  redraw()
  load()
  const timer = setInterval(load, 20000)
  ctx.onLeave(() => clearInterval(timer))

  ctx.on('submit', 'form[data-form="message"]', async (form, event) => {
    event.preventDefault()
    const body = new FormData(form).get('body')?.toString().trim()
    if (!body) return
    try {
      await ctx.api.post(`${base}/messages/`, { body })
      form.reset()
      load()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
