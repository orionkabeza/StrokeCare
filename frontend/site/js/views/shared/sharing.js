// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Sharing. A patient makes a one-time code for a caregiver, clinician or health worker and can stop sharing at any
// time. Everyone else enters a code. Safety rule: the survivor decides who sees what.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { emptyState, icon, pageHeader, toast } from '../../ui.js'

export default async function sharing(ctx) {
  const { auth } = ctx
  const s = { links: null, relation: 'caregiver', created: null, error: '' }

  const invite = () => html`<form class="sc-card pad stack" data-form="invite">
    <h2 class="row">${icon('share-network', 24, 'duotone')}${t('sharing.invite')}</h2>
    <div class="row" role="group" aria-label="${t('sharing.who')}">
      ${['caregiver', 'clinician', 'chw'].map((r) => html`<button type="button" class="sc-chip" data-act="relation" data-value="${r}" aria-pressed="${s.relation === r ? 'true' : 'false'}">${t(`roles.${r}`)}</button>`)}
    </div>
    <label class="field">${t('sharing.label')}<input name="label" class="sc-input" maxlength="80" placeholder="${t('sharing.labelHint')}" /></label>
    <p class="small muted">${t(`sharing.scopes.${s.relation}`)}</p>
    <p class="small muted">${t(`sharing.more.${s.relation}`)}</p>
    <button class="sc-btn sc-btn-primary">${t('sharing.makeCode')}</button>
    ${s.created
      ? html`<div class="sc-card pad stack-s sc-sheet" style="text-align: center; background: var(--primary-soft)">
          <span class="small muted">${t('sharing.codeFor', { who: t(`roles.${s.created.relation}`) })}</span>
          <strong style="font-size: 2.4rem; letter-spacing: 0.12em">${s.created.code}</strong>
          <span class="tiny">${t('sharing.expires', { when: new Date(s.created.invite_expires_at).toLocaleString(locale.value, { dateStyle: 'medium', timeStyle: 'short' }) })}</span>
        </div>`
      : ''}
  </form>`

  const redeem = () => html`<form class="sc-card pad stack" data-form="redeem">
    <h2 class="row">${icon('key', 24, 'duotone')}${t('sharing.enterCode')}</h2>
    <input name="code" class="sc-input" placeholder="ABCD-EFGH" autocapitalize="characters" style="font-size: 1.6rem; letter-spacing: 0.1em" />
    <button class="sc-btn sc-btn-primary">${t('sharing.link')}</button>
  </form>`

  const view = () => html`<main class="page">
    ${pageHeader({ title: t('sharing.title'), subtitle: auth.isPatient ? t('sharing.leadPatient') : t('sharing.leadMember'), back: true })}
    ${auth.isPatient ? invite() : redeem()}
    ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
    <h2>${t('sharing.current')}</h2>
    ${s.links && !s.links.length ? emptyState(t('sharing.none')) : ''}
    <ul class="list">
      ${(s.links ?? []).map(
        (l) => html`<li class="sc-card list-row">
          <span class="stack-s" style="flex-grow: 1">
            <strong>${l.other_party?.display_name ?? l.label ?? t('sharing.waiting')}</strong>
            <span class="small muted">${t(`roles.${l.relation}`)} · ${t(`sharing.status.${l.status}`)}</span>
          </span>
          <button class="sc-btn sc-btn-ghost" style="min-height: 2.75rem" data-act="end" data-id="${l.id}">${icon('link-break', 18)}${t('sharing.end')}</button>
        </li>`,
      )}
    </ul>
  </main>`
  const redraw = () => ctx.draw(view())
  const load = async () => ((s.links = await ctx.api.get('/links/')), redraw())
  redraw()
  await load().catch(() => redraw())

  ctx.on('click', '[data-act="relation"]', (el) => ((s.relation = el.dataset.value), redraw()))
  ctx.on('submit', 'form[data-form="invite"]', async (form, event) => {
    event.preventDefault()
    s.error = ''
    try {
      s.created = await ctx.api.post('/links/invite/', { relation: s.relation, label: new FormData(form).get('label') })
      await load()
    } catch (e) {
      s.error = errorText(e)
      redraw()
    }
  })
  ctx.on('submit', 'form[data-form="redeem"]', async (form, event) => {
    event.preventDefault()
    s.error = ''
    try {
      await ctx.api.post('/links/redeem/', { code: new FormData(form).get('code') })
      toast(t('sharing.linked'))
      form.reset()
      await load()
    } catch (e) {
      s.error = errorText(e)
      redraw()
    }
  })
  ctx.on('click', '[data-act="end"]', async (el) => {
    if (!confirm(t('sharing.confirmEnd'))) return
    await ctx.api.del(`/links/${el.dataset.id}/`)
    load()
  })
}
