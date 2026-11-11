// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The movement log: what the person did, for how long and with what help. Plain facts the person enters.
// Safety rule: there is no right amount, no target, no score, and no streak. Fewer taps: "same as last time".
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { byWho, emptyState, icon, pageHeader, toast } from '../../ui.js'

const KINDS = ['walking', 'standing', 'stretching', 'wheelchair', 'other']
const HELPS = ['alone', 'with_aid', 'with_person']
const QUICK = [5, 10, 15, 20, 30, 45, 60]

export default async function mobility(ctx) {
  const { base, isSelf } = ctx
  const s = { entries: [], loaded: false, kind: 'walking', minutes: '', help: '', saving: false }
  const last = () => s.entries[0] ?? null
  const dayLabel = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString(locale.value, { weekday: 'short', day: 'numeric', month: 'short' })
  const week = () => {
    const d = new Date()
    d.setDate(d.getDate() - 6)
    const start = d.toISOString().slice(0, 10)
    const rows = s.entries.filter((e) => e.date >= start)
    return { n: rows.length, minutes: rows.reduce((sum, e) => sum + (e.minutes ?? 0), 0) }
  }

  const view = () => {
    const l = last()
    const w = week()
    return html`<main class="page">
      ${pageHeader({ title: t('mobility.title'), subtitle: isSelf ? t('mobility.lead') : t('mobility.leadOther'), back: true })}
      ${l
        ? html`<button class="sc-card pad row" style="color: var(--ink); cursor: pointer; text-align: left" data-act="repeat" ${s.saving ? 'disabled' : ''}>
            <span class="sc-iconbox">${icon('arrow-counter-clockwise', 24, 'duotone')}</span>
            <span class="stack-s">
              <strong>${t('mobility.repeat')}</strong>
              <span class="small muted">${t('mobility.repeatHint', { what: `${t(`mobility.kinds.${l.kind}`)}${l.minutes ? ', ' + t('mobility.min', { n: l.minutes }) : ''}` })}</span>
            </span>
          </button>`
        : ''}

      <form class="sc-card pad stack" data-form="mobility">
        <strong>${t('mobility.what')}</strong>
        <div class="row" role="group" aria-label="${t('mobility.what')}">
          ${KINDS.map((k) => html`<button type="button" class="sc-chip" data-act="kind" data-value="${k}" aria-pressed="${s.kind === k ? 'true' : 'false'}">${t(`mobility.kinds.${k}`)}</button>`)}
        </div>
        <strong>${t('mobility.minutes')}</strong>
        <div class="row" role="group" aria-label="${t('mobility.minutes')}">
          ${QUICK.map((m) => html`<button type="button" class="sc-chip" data-act="minutes" data-value="${m}" aria-pressed="${s.minutes === m ? 'true' : 'false'}">${t('mobility.min', { n: m })}</button>`)}
        </div>
        <strong>${t('mobility.helpQ')}</strong>
        <div class="row" role="group" aria-label="${t('mobility.helpQ')}">
          ${HELPS.map((h) => html`<button type="button" class="sc-chip" data-act="help" data-value="${h}" aria-pressed="${s.help === h ? 'true' : 'false'}">${t(`mobility.help.${h}`)}</button>`)}
        </div>
        <label class="field">${t('common.noteOptional')}<input name="note" class="sc-input" maxlength="500" /></label>
        <button class="sc-btn sc-btn-primary" ${s.saving ? 'disabled' : ''}>${t('common.save')}</button>
      </form>

      ${s.entries.length
        ? html`<section class="sc-card pad stack-s"><strong>${t('mobility.week')}</strong>
            <span class="muted">${t('mobility.entries', { n: w.n }, w.n)} · ${t('mobility.total', { n: w.minutes })}</span></section>`
        : ''}
      ${s.loaded && !s.entries.length ? emptyState(t('mobility.none')) : ''}
      ${s.entries.map(
        (e) => html`<div class="sc-card list-row">
          <span class="stack-s" style="flex-grow: 1">
            <strong>${t(`mobility.kinds.${e.kind}`)}${e.minutes ? html` · ${t('mobility.min', { n: e.minutes })}` : ''}</strong>
            <span class="small muted">${dayLabel(e.date)}${e.help ? html` · ${t(`mobility.help.${e.help}`)}` : ''} · ${t(`roles.by.${byWho(e.entered_by_role, isSelf)}`)}</span>
            ${e.note ? html`<span class="small">${e.note}</span>` : ''}
          </span>
          <button class="icon-btn" data-act="delete" data-id="${e.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>
        </div>`,
      )}
    </main>`
  }
  const redraw = () => ctx.draw(view())
  async function load() {
    try {
      s.entries = (await ctx.api.get(`${base}/mobility/`, { days: 30 })).results ?? []
    } catch (e) {
      toast(errorText(e))
    }
    s.loaded = true
    redraw()
  }
  redraw()
  load()

  async function send(body) {
    s.saving = true
    try {
      // client_id lets the server keep one entry even if the phone retries after being offline
      const r = await ctx.api.post(`${base}/mobility/`, { ...body, client_id: crypto.randomUUID() }, { queueable: true })
      toast(r?.queued ? t('offline.saved') : t('mobility.added'))
      s.saving = false
      await load()
      return true
    } catch (e) {
      toast(errorText(e))
      s.saving = false
      redraw()
      return false
    }
  }

  ctx.on('click', '[data-act="kind"]', (el) => ((s.kind = el.dataset.value), redraw()))
  ctx.on('click', '[data-act="minutes"]', (el) => ((s.minutes = s.minutes === +el.dataset.value ? '' : +el.dataset.value), redraw()))
  ctx.on('click', '[data-act="help"]', (el) => ((s.help = s.help === el.dataset.value ? '' : el.dataset.value), redraw()))
  ctx.on('submit', 'form[data-form="mobility"]', async (form, event) => {
    event.preventDefault()
    const note = new FormData(form).get('note')
    const ok = await send({ kind: s.kind, minutes: s.minutes === '' ? null : Number(s.minutes), help: s.help, note })
    if (ok) {
      s.minutes = ''
      ctx.el.querySelector('input[name="note"]').value = ''
    }
  })
  ctx.on('click', '[data-act="repeat"]', () => {
    const l = last()
    if (l) send({ kind: l.kind, minutes: l.minutes, help: l.help, note: '' })
  })
  ctx.on('click', '[data-act="delete"]', async (el) => {
    try {
      await ctx.api.del(`${base}/mobility/${el.dataset.id}/`)
      load()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
