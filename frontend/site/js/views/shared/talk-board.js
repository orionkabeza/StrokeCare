// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// For people who find speaking hard. Tap a tile: the words fill the screen and the phone says them, using its own
// voice for the language when it has one. Everyday needs only. Signed-in patients also get a "Mine" tab with the
// phrases they or their family added. It works before signing in, so it is there on a shared family phone.
import { ICONS } from '../../icons.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { canSpeak, speak } from '../../speech.js'
import { draftNote, icon, pageHeader } from '../../ui.js'

const CATEGORIES = ['needs', 'feelings', 'answers', 'people']
const iconName = (name) => (ICONS[name] ? name : 'chat-circle-text')

export default async function talkBoard(ctx) {
  const { auth } = ctx
  const s = { tab: 'needs', board: [], mine: [], shown: null }
  const tabs = () => [...(auth.isPatient ? ['mine'] : []), ...CATEGORIES]
  const tiles = () => (s.tab === 'mine' ? s.mine : s.board.filter((p) => p.category === s.tab))

  const view = () => html`<main class="page">
    ${pageHeader({ title: t('talk.title'), subtitle: t('talk.lead') })}
    <div role="tablist" class="row">
      ${tabs().map((c) => html`<button role="tab" class="sc-chip" data-act="tab" data-tab="${c}" aria-selected="${s.tab === c ? 'true' : 'false'}" aria-pressed="${s.tab === c ? 'true' : 'false'}">${c === 'mine' ? t('phrases.mine') : t(`talk.cat.${c}`)}</button>`)}
    </div>
    <div class="grid-2">
      ${tiles().map(
        (p, i) => html`<button class="sc-card sc-rise pad stack" data-act="say" data-code="${p.code}" style="animation-delay: ${i * 40}ms; min-height: 8.5rem; align-items: flex-start; text-align: left; cursor: pointer; color: var(--ink)">
          <span class="sc-iconbox" style="width: 3.75rem; height: 3.75rem">${icon(iconName(p.icon), 36, 'duotone')}</span>
          <span style="font-size: 1.2rem; font-weight: 800; line-height: 1.2">${p.label}</span>
        </button>`,
      )}
    </div>
    ${s.tab === 'mine' && !tiles().length ? html`<p class="muted">${t('phrases.none')}</p>` : ''}
    ${auth.isPatient && s.tab === 'mine' ? html`<a href="/p/me/phrases" class="sc-btn sc-btn-ghost">${t('phrases.manage')}</a>` : ''}
    <p class="tiny">${canSpeak() ? t('talk.voiceOn') : t('talk.voiceOff')}</p>
    ${draftNote()}

    ${s.shown
      ? html`<div role="dialog" aria-modal="true" aria-label="${s.shown.label}" class="sc-app sc-hero" style="position: fixed; inset: 0; z-index: 60; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.5rem; padding: 2rem; text-align: center">
          <span class="sc-glass sc-sheet" style="width: 8rem; height: 8rem; border-radius: 2.5rem; display: grid; place-items: center">${icon(iconName(s.shown.icon), 72, 'duotone')}</span>
          <span class="sc-sheet" style="font-size: 2.75rem; font-weight: 800; line-height: 1.1">${s.shown.label}</span>
          <div class="row" style="justify-content: center">
            ${canSpeak() ? html`<button class="sc-btn sc-glass" style="color: var(--on-hero)" data-act="again">${icon('speaker-high', 22)}${t('talk.again')}</button>` : ''}
            <button class="sc-btn" style="background: #fff; color: #312E81" data-act="close">${t('common.done')}</button>
          </div>
        </div>`
      : ''}
  </main>`
  const redraw = () => ctx.draw(view())
  redraw()

  const [board, mine] = await Promise.allSettled([
    ctx.api.get('/talk-board/', { lang: locale.value }),
    auth.isPatient ? ctx.api.get('/patients/me/phrases/') : Promise.resolve({ results: [] }),
  ])
  s.board = board.status === 'fulfilled' ? (board.value.results ?? []) : []
  s.mine = (mine.status === 'fulfilled' ? (mine.value.results ?? []) : []).map((p) => ({ code: p.id, label: p.text, icon: p.icon, category: 'mine' }))
  if (s.mine.length) s.tab = 'mine' // the person's own words first, when there are any
  redraw()

  ctx.on('click', '[data-act="tab"]', (el) => ((s.tab = el.dataset.tab), redraw()))
  ctx.on('click', '[data-act="say"]', (el) => {
    s.shown = tiles().find((p) => String(p.code) === el.dataset.code)
    redraw()
    speak(s.shown.label)
  })
  ctx.on('click', '[data-act="again"]', () => speak(s.shown.label))
  ctx.on('click', '[data-act="close"]', () => ((s.shown = null), redraw()))
}
