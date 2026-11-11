// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// By default every question is on ONE screen with one Send button, so a tired person makes as few taps as possible.
// With the "One question at a time" setting it goes step by step. Either way every question can be skipped.
// Safety rule: an answer listed in a question's urgent_values shows emergency guidance AT ONCE, before anything is
// sent, and nothing is ever pre-answered for the person. A question left empty is sent as skipped.
import { errorText } from '../../api.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { canSpeak, speak } from '../../speech.js'
import { draftNote, icon, pageHeader, toast } from '../../ui.js'

/** The answer buttons for one question. Values are carried in data-v as JSON so true, 3 and "better" stay distinct. */
function questionInput(q, answer) {
  const pressed = (value) => (answer && !answer.skipped && answer.value === value ? 'true' : 'false')
  const button = (value, cls, style, content) =>
    html`<button type="button" class="${cls}" style="${style}" data-act="answer" data-q="${q.code}" data-v="${JSON.stringify(value)}" aria-pressed="${pressed(value)}">${content}</button>`
  if (q.answer_type === 'yes_no')
    return html`<div class="grid-2">
      ${button(true, 'sc-card choice', '', html`${icon('check', 40, 'duotone')}${t('common.yes')}`)}
      ${button(false, 'sc-card choice', '', html`${icon('x', 40, 'duotone')}${t('common.no')}`)}
    </div>`
  if (q.answer_type === 'choice')
    return html`<div class="stack">${q.choices.map((c) => button(c.value, 'sc-card choice choice-row', '', c.label))}</div>`
  if (q.answer_type === 'scale_5')
    return html`<div class="row" style="flex-wrap: nowrap">${[1, 2, 3, 4, 5].map((n) => button(n, 'sc-card choice', 'flex: 1; min-height: 4.5rem', String(n)))}</div>`
  return html`<label class="field">${t('checkin.yourWords')}
    <textarea class="sc-input" data-q="${q.code}" data-text>${answer && !answer.skipped ? (answer.value ?? '') : ''}</textarea></label>`
}

const urgentBanner = () => html`<section role="alert" class="sc-card banner-urgent pad stack sc-sheet">
  <p class="row" style="flex-wrap: nowrap; align-items: flex-start; font-weight: 700; font-size: 1.1rem">${icon('siren', 30, 'duotone')}${t('emergency.message')}</p>
  <a href="/emergency" class="sc-btn sc-btn-danger">${t('emergency.open')}</a>
</section>`

export default async function checkIn(ctx) {
  const { base, isSelf } = ctx
  const s = { questions: [], step: 0, answers: {}, guidance: null, finished: false, error: '' }
  const stepByStep = () => !!ctx.prefs.values.one_question_at_a_time
  const isUrgent = (q) => !!q && !!q.urgent_values?.includes(s.answers[q.code]?.value)
  const anyUrgent = () => s.questions.some(isUrgent)

  const header = html`${pageHeader({ title: t('checkin.title'), subtitle: isSelf ? t('checkin.lead') : t('checkin.leadOther'), back: true })}`
  const readAloud = (text) => (canSpeak() ? html`<button type="button" class="sc-btn sc-btn-ghost" style="align-self: flex-start; min-height: 2.75rem" data-act="speak" data-text="${text}">${icon('speaker-high', 20)}${t('common.readAloud')}</button>` : '')
  const skipLink = (q, style = 'background: transparent; color: var(--ink-2); text-decoration: underline') =>
    html`<button type="button" class="sc-btn" style="${style}" data-act="skip" data-q="${q.code}">${t('checkin.skip')}</button>`

  const oneScreen = () => html`
    <p class="small muted">${t('checkin.oneScreen')}</p>
    ${s.questions.map(
      (q) => html`<section class="sc-card pad stack">
        <h2 style="font-size: 1.35rem; line-height: 1.3">${q.prompt}</h2>
        ${readAloud(q.prompt)}
        ${questionInput(q, s.answers[q.code])}
        ${isUrgent(q) ? urgentBanner() : ''}
        ${!s.answers[q.code]?.skipped ? skipLink(q, 'background: transparent; color: var(--ink-2); text-decoration: underline; min-height: 2.5rem') : ''}
      </section>`,
    )}
    <div class="thumb-actions"><button class="sc-btn sc-btn-primary" style="width: 100%" data-act="send">${t('checkin.send')}${icon('caret-right', 20)}</button></div>
    ${draftNote({ source: t('checkin.source') })}`

  const stepView = () => {
    const q = s.questions[s.step]
    const last = s.step === s.questions.length - 1
    return html`
      <div role="img" aria-label="${t('checkin.progress', { n: s.step + 1, total: s.questions.length })}" style="display: grid; grid-template-columns: repeat(${s.questions.length}, 1fr); gap: 6px">
        ${s.questions.map((x, i) => html`<span style="height: 6px; border-radius: 3px; background: ${i <= s.step ? 'var(--primary)' : 'var(--line-strong)'}"></span>`)}
      </div>
      <p class="small muted">${t('checkin.progress', { n: s.step + 1, total: s.questions.length })}</p>
      <div class="stack sc-rise">
        <h2 style="font-size: 1.7rem; line-height: 1.25">${q.prompt}</h2>
        ${readAloud(q.prompt)}
        ${questionInput(q, s.answers[q.code])}
        ${isUrgent(q) ? urgentBanner() : ''}
        ${skipLink(q)}
      </div>
      <div class="grid-2 thumb-actions">
        <button class="sc-btn sc-btn-ghost" data-act="back-step" ${s.step === 0 ? 'disabled' : ''}>${t('common.back')}</button>
        <button class="sc-btn sc-btn-primary" data-act="next" ${s.answers[q.code] ? '' : 'disabled'}>${last ? t('checkin.send') : t('common.next')}${icon('caret-right', 20)}</button>
      </div>
      ${draftNote({ source: t('checkin.source') })}`
  }

  const doneView = () => html`<section class="stack sc-rise">
    <div class="sc-card pad-l stack" style="text-align: center; align-items: center">
      <span class="tick sc-pop" aria-pressed="true" style="width: 4rem; height: 4rem">${icon('check', 34, 'bold')}</span>
      <h2>${t('checkin.thanks')}</h2>
    </div>
    ${s.guidance || anyUrgent()
      ? html`<section role="alert" class="sc-card banner-urgent pad stack">
          <p style="font-weight: 700; font-size: 1.1rem">${s.guidance?.message ?? t('emergency.message')}</p>
          <a href="/emergency" class="sc-btn sc-btn-danger">${t('emergency.open')}</a>
        </section>`
      : ''}
    <button class="sc-btn sc-btn-primary" data-act="done">${t('common.done')}</button>
  </section>`

  const view = () => html`<main class="page">
    ${header}
    ${!s.finished && s.questions.length ? (stepByStep() ? stepView() : oneScreen()) : ''}
    ${s.finished ? doneView() : ''}
    ${s.error ? html`<p class="error" role="alert">${s.error}</p>` : ''}
  </main>`
  const redraw = () => ctx.draw(view())

  async function submit() {
    s.error = ''
    // Anything the person left empty is sent as skipped. Nothing is ever answered for them.
    const body = { answers: s.questions.map((q) => ({ question: q.code, ...(s.answers[q.code] ?? { value: null, skipped: true }) })) }
    try {
      const r = await ctx.api.post(`${base}/checkins/`, body, { queueable: true })
      s.guidance = r?.emergency_guidance ?? null
      s.finished = true
      toast(r?.queued ? t('offline.saved') : t('checkin.thanks'))
    } catch (e) {
      s.error = errorText(e)
    }
    redraw()
  }
  const next = () => (s.step < s.questions.length - 1 ? (s.step++, redraw()) : submit())

  redraw()
  try {
    s.questions = (await ctx.api.get('/checkin-questions/', { lang: locale.value })).results ?? []
  } catch (e) {
    s.error = errorText(e)
  }
  redraw()

  ctx.on('click', '[data-act="answer"]', (el) => {
    s.answers[el.dataset.q] = { value: JSON.parse(el.dataset.v), skipped: false }
    redraw()
  })
  ctx.on('input', 'textarea[data-text]', (el) => {
    s.answers[el.dataset.q] = { value: el.value, skipped: false }
    const nextButton = ctx.el.querySelector('[data-act="next"]')
    if (nextButton) nextButton.disabled = false
  })
  ctx.on('click', '[data-act="skip"]', (el) => {
    s.answers[el.dataset.q] = { value: null, skipped: true }
    if (stepByStep()) next()
    else redraw()
  })
  ctx.on('click', '[data-act="next"]', next)
  ctx.on('click', '[data-act="send"]', submit)
  ctx.on('click', '[data-act="back-step"]', () => {
    s.step--
    redraw()
  })
  ctx.on('click', '[data-act="speak"]', (el) => speak(el.dataset.text))
  ctx.on('click', '[data-act="done"]', () => ctx.back())
}
