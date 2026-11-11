// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Questions for the next visit, voice notes, and a printable one-page list to take to the clinic.
import { errorText } from '../../api.js'
import { handleVoiceNotes, mountRecorder, recorderSlot, voiceNotes } from '../../components/voice.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { byWho, emptyState, icon, pageHeader, toast } from '../../ui.js'

export default async function visitPrep(ctx) {
  const { base, isSelf } = ctx
  const s = { questions: [], voice: [], urls: {}, print: null }
  const open = () => s.questions.filter((q) => !q.discussed)

  const printSection = () => {
    const sum = s.print?.summary
    return html`<section class="print-only">
      <h1>${t('visit.printTitle')}</h1>
      <p>${new Date().toLocaleDateString(locale.value)}</p>
      <h2>${t('visit.toAsk', { n: open().length })}</h2>
      <ol>${open().map((q) => html`<li>${q.text}</li>`)}</ol>
      <h2>${t('meds.title')}</h2>
      <ul>${(s.print?.meds?.medications ?? []).map((m) => html`<li>${m.name} · ${m.dose} · ${m.times.join(', ')}</li>`)}</ul>
      ${sum
        ? html`<h2>${t('summary.title')}</h2>
            <p>${t('summary.readings', { n: sum.blood_pressure.readings })} · ${sum.blood_pressure.average_systolic ?? '-'} / ${sum.blood_pressure.average_diastolic ?? '-'} mmHg</p>
            <p>${sum.disclaimer}</p>`
        : ''}
    </section>`
  }

  const view = () => html`<main class="page">
    <div class="no-print stack">
      ${pageHeader({ title: t('visit.title'), subtitle: t('visit.lead'), back: true })}
      <form class="sc-card row pad" style="flex-wrap: nowrap" data-form="question">
        <label class="visually-hidden" for="q">${t('visit.new')}</label>
        <input id="q" name="text" class="sc-input" placeholder="${t('visit.placeholder')}" maxlength="500" style="border: 0; background: var(--surface-2)" />
        <button class="sc-btn sc-btn-primary" style="width: 3.5rem; padding: 0" aria-label="${t('visit.add')}">${icon('plus', 24)}</button>
      </form>
      ${recorderSlot()}

      <h2>${t('visit.toAsk', { n: open().length })}</h2>
      ${!s.questions.length ? emptyState(t('visit.empty')) : ''}
      <ul class="list">
        ${s.questions.map(
          (q) => html`<li class="sc-card list-row" style="opacity: ${q.discussed ? 0.6 : 1}">
            <button class="tick" style="width: 2rem; height: 2rem; border-radius: 0.6rem" data-act="toggle" data-id="${q.id}" aria-pressed="${q.discussed ? 'true' : 'false'}" aria-label="${t('visit.discussed')}">${q.discussed ? icon('check', 16, 'bold') : ''}</button>
            <span class="stack-s" style="flex-grow: 1">
              <strong style="text-decoration: ${q.discussed ? 'line-through' : 'none'}">${q.text}</strong>
              <span class="tiny">${t(`roles.by.${byWho(q.entered_by_role, isSelf)}`)} · ${new Date(q.created_at).toLocaleDateString(locale.value)}</span>
            </span>
            <button class="icon-btn" data-act="delete" data-id="${q.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>
          </li>`,
        )}
      </ul>

      ${s.voice.length ? html`<h2>${t('voice.notes')}</h2>` : ''}
      ${voiceNotes(s.voice, s.urls, true)}

      <button class="sc-btn sc-btn-ghost" data-act="print">${icon('printer', 22)}${t('visit.print')}</button>
    </div>
    ${printSection()}
  </main>`

  const redraw = () => ctx.draw(view())
  async function loadQuestions() {
    s.questions = (await ctx.api.get(`${base}/visit-questions/`)).results ?? []
    redraw()
  }
  async function loadVoice() {
    s.voice = (await ctx.api.get(`${base}/voice-notes/`)).results ?? []
    redraw()
  }
  ctx.afterDraw(() => mountRecorder(ctx.el, { base, context: 'visit', onSaved: loadVoice }))
  redraw()
  await Promise.allSettled([loadQuestions(), loadVoice()])

  handleVoiceNotes(ctx, { base, urls: s.urls, redraw, reload: loadVoice })
  ctx.on('submit', 'form[data-form="question"]', async (form, event) => {
    event.preventDefault()
    const text = new FormData(form).get('text')?.toString().trim()
    if (!text) return
    try {
      await ctx.api.post(`${base}/visit-questions/`, { text })
      form.reset()
      await loadQuestions()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="toggle"]', async (el) => {
    const q = s.questions.find((x) => x.id === el.dataset.id)
    await ctx.api.patch(`${base}/visit-questions/${q.id}/`, { discussed: !q.discussed })
    loadQuestions()
  })
  ctx.on('click', '[data-act="delete"]', async (el) => {
    try {
      await ctx.api.del(`${base}/visit-questions/${el.dataset.id}/`)
      loadQuestions()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="print"]', async () => {
    s.print = {
      summary: await ctx.api.get(`${base}/summary/`).catch(() => null),
      meds: await ctx.api.get(`${base}/medications/`).catch(() => null),
    }
    redraw()
    setTimeout(() => window.print(), 50)
  })
}
