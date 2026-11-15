// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Personal talk-board phrases: the words this person needs most, added by them or by family, in any language.
// They appear first on the talk board. These are the person's own words, not medical advice.
import { errorText } from '../../api.js'
import { handleVoiceNotes, mountRecorder, recorderSlot, voiceNotes } from '../../components/voice.js'
import { html } from '../../dom.js'
import { t } from '../../i18n.js'
import { emptyState, icon, pageHeader, toast } from '../../ui.js'

// A short, friendly set of pictures. The server accepts these and a few more used by the built-in phrases.
const ICON_NAMES = ['chat-circle', 'drop', 'fork-knife', 'toilet', 'bed', 'hand-heart', 'phone-call', 'users-three']

export default async function phrases(ctx) {
  const { base, isSelf } = ctx
  const s = { list: null, icon: 'chat-circle', voice: [], urls: {} }
  const view = () => html`<main class="page">
    ${pageHeader({ title: isSelf ? t('phrases.title') : t('phrases.titleOther'), subtitle: t('phrases.lead'), back: true })}
    <form class="sc-card pad stack" data-form="phrase">
      <label class="field">${t('phrases.add')}<input name="text" class="sc-input" maxlength="80" placeholder="${t('phrases.placeholder')}" /></label>
      <strong>${t('phrases.picture')}</strong>
      <div class="row" role="radiogroup" aria-label="${t('phrases.picture')}">
        ${ICON_NAMES.map(
          (name) => html`<button type="button" role="radio" class="sc-chip" data-act="icon" data-value="${name}" aria-checked="${s.icon === name ? 'true' : 'false'}" aria-pressed="${s.icon === name ? 'true' : 'false'}">${icon(name, 20)}${t(`phrases.icons.${name}`)}</button>`,
        )}
      </div>
      <button class="sc-btn sc-btn-primary">${icon('plus', 20)}${t('phrases.add')}</button>
    </form>
    ${s.list && !s.list.length ? emptyState(t('phrases.none')) : ''}
    ${(s.list ?? []).map(
      (p) => html`<div class="sc-card list-row">
        <span class="sc-iconbox" style="width: 2.75rem; height: 2.75rem">${icon(ICON_NAMES.includes(p.icon) || p.icon ? safeIcon(p.icon) : 'chat-circle', 22, 'duotone')}</span>
        <strong style="flex-grow: 1">${p.text}</strong>
        <button class="icon-btn" data-act="delete" data-id="${p.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>
      </div>`,
    )}

    <h2>${t('phrases.practice')}</h2>
    <p class="small muted">${t('phrases.practiceLead')}</p>
    ${recorderSlot()}
    ${s.voice.length ? voiceNotes(s.voice, s.urls, true) : emptyState(t('phrases.practiceEmpty'))}
  </main>`
  const redraw = () => ctx.draw(view())
  const load = async () => {
    s.list = (await ctx.api.get(`${base}/phrases/`)).results ?? []
    redraw()
  }
  // Practice recordings are voice notes made from the talk board, filtered to context "general" so they never
  // mix with the separate voice notes recorded for the next clinic visit (context "visit").
  const loadVoice = async () => {
    const results = (await ctx.api.get(`${base}/voice-notes/`)).results ?? []
    s.voice = results.filter((n) => n.context === 'general')
    redraw()
  }
  ctx.afterDraw(() => mountRecorder(ctx.el, { base, context: 'general', onSaved: loadVoice }))
  redraw()
  Promise.allSettled([load(), loadVoice()]).then(() => redraw())
  handleVoiceNotes(ctx, { base, urls: s.urls, redraw, reload: loadVoice })

  ctx.on('click', '[data-act="icon"]', (el) => ((s.icon = el.dataset.value), redraw()))
  ctx.on('submit', 'form[data-form="phrase"]', async (form, event) => {
    event.preventDefault()
    const text = new FormData(form).get('text')?.toString().trim()
    if (!text) return
    try {
      await ctx.api.post(`${base}/phrases/`, { text, icon: s.icon })
      form.reset()
      await load()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="delete"]', async (el) => {
    try {
      await ctx.api.del(`${base}/phrases/${el.dataset.id}/`)
      load()
    } catch (e) {
      toast(errorText(e))
    }
  })
}

// Built-in phrases use a few more picture names than the chooser offers; anything unknown falls back to a speech bubble.
import { ICONS } from '../../icons.js'
function safeIcon(name) {
  return ICONS[name] ? name : 'chat-circle'
}
