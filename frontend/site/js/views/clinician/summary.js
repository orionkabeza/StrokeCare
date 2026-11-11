// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// One person's last days, for whoever they shared it with. Clinicians also write the plan, the medicine list and the
// recovery stages here. Safety rule: counts, averages and their own words. The disclaimer is always shown.
import { errorText } from '../../api.js'
import { handleVoiceNotes, voiceNotes } from '../../components/voice.js'
import { html } from '../../dom.js'
import { locale, t } from '../../i18n.js'
import { bpChart, byWho, fmtDateTime, icon, pageHeader, toast } from '../../ui.js'

const SELF = ['view_readings', 'view_plan', 'view_checkins', 'view_summary', 'view_meds', 'view_notes', 'message', 'view_calendar']
const chipLink = (to, iconName, label) => html`<a href="${to}" class="sc-chip" style="text-decoration: none">${icon(iconName, 18)}${label}</a>`

export default async function summary(ctx) {
  const { auth, base, isSelf, link } = ctx
  const s = {
    days: 7, access: null, summary: null, readings: [], plan: null, meds: null, questions: [], voice: [], urls: {},
    visits: [], qtext: {}, templates: [], phases: [], addingPhase: false,
  }
  const can = (scope) => (s.access?.scopes ?? []).includes(scope)
  const recent = () => {
    const since = Date.now() - s.days * 86400000
    return s.readings.filter((r) => +new Date(r.taken_at) >= since)
  }
  const answerLabel = (code, v) => (v === 'yes' ? t('common.yes') : v === 'no' ? t('common.no') : (s.qtext[code]?.choices[v] ?? v))
  const fmtRange = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString(locale.value, { day: 'numeric', month: 'short', year: 'numeric' })

  const phasesEditor = () => html`<section class="sc-card pad stack">
    <h2>${t('phase.title')}</h2>
    <p class="small muted">${t('phase.lead')}</p>
    ${!s.phases.length ? html`<p class="muted small">${t('phase.none')}</p>` : ''}
    ${s.phases.map(
      (p) => html`<div class="list-row" style="border-top: 1px solid var(--line); padding-top: 0.5rem">
        <span class="stack-s" style="flex-grow: 1">
          <strong>${p.name} ${p.is_current ? html`<span class="sc-chip" style="min-height: 1.6rem; padding: 0 0.5rem; font-size: 0.8rem">${t('phase.now')}</span>` : ''}</strong>
          <span class="small muted">${p.ends_on ? t('recovery.range', { from: fmtRange(p.starts_on), to: fmtRange(p.ends_on) }) : t('recovery.since', { from: fmtRange(p.starts_on) })}</span>
          ${p.care_needed ? html`<span class="small" style="white-space: pre-line">${p.care_needed}</span>` : ''}
        </span>
        <button class="icon-btn" data-act="phase-delete" data-id="${p.id}" aria-label="${t('common.delete')}">${icon('trash', 18)}</button>
      </div>`,
    )}
    ${!s.addingPhase
      ? html`<button class="sc-btn sc-btn-ghost" data-act="phase-open">${icon('plus', 20)}${t('phase.add')}</button>`
      : html`<form class="stack sc-sheet" data-form="phase">
          <label class="field">${t('phase.name')}<input name="name" class="sc-input" required maxlength="80" /></label>
          <div class="grid-2">
            <label class="field">${t('phase.from')}<input name="starts_on" class="sc-input" type="date" required /></label>
            <label class="field">${t('phase.to')}<input name="ends_on" class="sc-input" type="date" /></label>
          </div>
          <label class="field">${t('recovery.careNeeded')}<textarea name="care_needed" class="sc-input" maxlength="1000"></textarea></label>
          <div class="grid-2"><button type="button" class="sc-btn sc-btn-ghost" data-act="phase-cancel">${t('common.cancel')}</button><button class="sc-btn sc-btn-primary">${t('common.save')}</button></div>
        </form>`}
  </section>`

  const view = () => {
    const d = s.summary
    const openQuestions = s.questions.filter((q) => !q.discussed).length
    return html`<main class="page page-wide">
      ${pageHeader({
        title: s.access?.display_name ?? t('summary.title'), subtitle: d ? `${d.period.from} → ${d.period.to}` : '', back: true,
        extra: html`<div class="row" style="margin-left: auto">
          ${[7, 14, 30].map((n) => html`<button class="sc-chip" data-act="days" data-n="${n}" aria-pressed="${s.days === n ? 'true' : 'false'}">${t('summary.days', { n })}</button>`)}
          <button class="sc-btn sc-btn-ghost" style="min-height: 2.75rem" data-act="print">${icon('printer', 20)}${t('summary.print')}</button>
        </div>`,
      })}

      <p class="banner">${icon('info', 20)}${d?.disclaimer ?? t('summary.disclaimer')}</p>
      <nav class="row" aria-label="${t('summary.title')}">
        ${chipLink(link('recovery'), 'target', t('recovery.titleOther'))}${chipLink(link('mobility'), 'person-simple-walk', t('mobility.title'))}${chipLink(link('progress'), 'chart-bar', t('progress.title'))}
      </nav>
      ${can('manage_plan') ? phasesEditor() : ''}
      <div class="row">
        ${can('message') ? chipLink(link('messages'), 'chat-circle-text', t('messages.title')) : ''}
        ${can('view_calendar') ? chipLink(link('calendar'), 'calendar-check', t('calendar.title')) : ''}
        ${auth.role === 'chw' ? chipLink(link('home-visit'), 'map-pin', t('visitLog.record')) : ''}
      </div>

      ${d
        ? html`<div class="grid-auto">
            <section class="sc-card pad stack-s sc-rise"><span class="row small muted">${icon('heartbeat', 18)}${t('summary.readingsLabel')}</span>
              <span class="big-number">${d.blood_pressure.readings}</span><span class="small muted">${t('summary.onDays', { n: d.blood_pressure.days_with_a_reading, total: d.period.days })}</span></section>
            <section class="sc-card pad stack-s sc-rise"><span class="row small muted">${icon('heartbeat', 18)}${t('summary.average')}</span>
              <span class="big-number">${d.blood_pressure.average_systolic ?? '—'} / ${d.blood_pressure.average_diastolic ?? '—'}</span><span class="small muted">mmHg</span></section>
            <section class="sc-card pad stack-s sc-rise"><span class="row small muted">${icon('pill', 18)}${t('summary.doses')}</span>
              <span class="big-number">${d.medicines.doses_marked_taken}<small class="muted" style="font-size: 1.1rem"> / ${d.medicines.doses_due}</small></span><span class="small muted">${t('summary.medsActive', { n: d.medicines.active })}</span></section>
            <section class="sc-card pad stack-s sc-rise"><span class="row small muted">${icon('clipboard-text', 18)}${t('summary.checkins')}</span>
              <span class="big-number">${d.daily_check_ins.submitted}</span><span class="small muted">${t('summary.urgentDays', { n: d.daily_check_ins.days_urgent_question_answered_yes })}</span></section>
          </div>`
        : ''}

      <div class="grid-auto" style="grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr))">
        <section class="sc-card pad stack-s"><h2>${t('bp.recent')}</h2>${recent().length > 1 ? bpChart(recent()) : html`<p class="muted small">${t('bp.none')}</p>`}</section>
        ${d
          ? html`<section class="sc-card pad stack">
              <h2>${t('summary.answers')}</h2>
              ${d.daily_check_ins.by_question.map(
                (q) => html`<div class="stack-s">
                  <strong class="small">${s.qtext[q.question]?.prompt ?? q.prompt}</strong>
                  ${Object.entries(q.value_counts).map(
                    ([v, n]) => html`<div style="display: grid; grid-template-columns: 10rem 1fr 2rem; gap: 0.5rem; align-items: center" class="small">
                      <span>${answerLabel(q.question, String(v))}</span>
                      <span style="height: 0.6rem; border-radius: 0.3rem; background: var(--primary); width: ${(100 * n) / Math.max(1, q.answered)}%"></span><span>${n}</span>
                    </div>`,
                  )}
                  <span class="tiny">${t('summary.skipped', { n: q.skipped })}</span>
                </div>`,
              )}
            </section>`
          : ''}
      </div>

      <div class="grid-auto" style="grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr))">
        <section class="sc-card pad stack">
          <h2>${t('summary.plan')}</h2>
          ${!s.plan?.tasks?.length ? html`<p class="muted small">${t('summary.noPlan')}</p>` : ''}
          ${(s.plan?.tasks ?? []).map(
            (task) => html`<div class="row-between" style="flex-wrap: nowrap">
              <span class="stack-s"><strong>${task.title}</strong><span class="tiny">${task.done_today ? t('summary.doneToday') : ''}</span></span>
              ${can('manage_plan') ? html`<button class="sc-chip" data-act="retire" data-id="${task.id}">${t('summary.retire')}</button>` : ''}
            </div>`,
          )}
          ${can('manage_plan')
            ? html`<form class="stack-s" data-form="task">
                  <label class="field">${t('summary.newTask')}<input name="title" class="sc-input" required maxlength="200" /></label>
                  <label class="field">${t('summary.instructions')}<textarea name="instructions" class="sc-input"></textarea></label>
                  <button class="sc-btn sc-btn-primary">${t('summary.addTask')}</button>
                </form>
                ${s.templates.length
                  ? html`<form class="row" style="flex-wrap: nowrap" data-form="template">
                      <select name="template" class="sc-input" required aria-label="${t('templates.use')}"><option value="" disabled selected>${t('templates.use')}</option>
                        ${s.templates.map((x) => html`<option value="${x.id}">${x.name} · ${x.tasks.length}</option>`)}</select>
                      <button class="sc-btn sc-btn-ghost">${t('common.add')}</button>
                    </form>`
                  : ''}`
            : ''}
        </section>

        <section class="sc-card pad stack">
          <h2>${t('meds.title')}</h2>
          ${(s.meds?.medications ?? []).map(
            (m) => html`<div class="row-between" style="flex-wrap: nowrap; opacity: ${m.is_active ? 1 : 0.55}">
              <span class="stack-s"><strong>${m.name}</strong><span class="tiny">${m.dose} · ${m.times.map((x) => x.slice(0, 5)).join(', ')}</span></span>
              ${can('manage_meds') ? html`<button class="sc-chip" data-act="stop-med" data-id="${m.id}">${m.is_active ? t('summary.stopMed') : t('summary.restartMed')}</button>` : ''}
            </div>`,
          )}
          ${can('manage_meds')
            ? html`<form class="stack-s" data-form="med">
                <label class="field">${t('summary.medName')}<input name="name" class="sc-input" required maxlength="120" /></label>
                <div class="grid-2">
                  <label class="field">${t('summary.medDose')}<input name="dose" class="sc-input" maxlength="120" /></label>
                  <label class="field">${t('summary.medTimes')}<input name="times" class="sc-input" placeholder="08:00, 20:00" value="08:00" required /></label>
                </div>
                <button class="sc-btn sc-btn-primary">${t('summary.addMed')}</button>
              </form>`
            : ''}
        </section>

        <section class="sc-card pad stack">
          <h2>${t('visit.toAsk', { n: openQuestions })}</h2>
          ${s.questions.map(
            (q) => html`<label class="check"><input type="checkbox" data-act="discussed" data-id="${q.id}" ${q.discussed ? 'checked' : ''} />
              <span><span style="text-decoration: ${q.discussed ? 'line-through' : 'none'}">${q.text}</span><br /><span class="tiny">${t(`roles.by.${byWho(q.entered_by_role, isSelf)}`)}</span></span></label>`,
          )}
          ${s.voice.length ? html`<h3>${t('voice.notes')}</h3>` : ''}
          ${voiceNotes(s.voice, s.urls, false)}
        </section>

        ${d
          ? html`<section class="sc-card pad stack">
              <h2>${t('summary.ownWords')}</h2>
              ${!d.notes_in_their_own_words.length ? html`<p class="muted small">${t('summary.noNotes')}</p>` : ''}
              ${d.notes_in_their_own_words.map(
                (n) => html`<blockquote style="margin: 0; padding: 0.6rem 0.9rem; border-left: 3px solid var(--primary); background: var(--surface-2); border-radius: 0 0.75rem 0.75rem 0">
                  “${n.text}”<br /><span class="tiny">${fmtDateTime(n.at)}</span></blockquote>`,
              )}
            </section>`
          : ''}

        ${s.visits.length
          ? html`<section class="sc-card pad stack">
              <h2>${t('visitLog.recent')}</h2>
              ${s.visits.map(
                (v) => html`<div class="stack-s">
                  <strong>${fmtDateTime(v.visited_at)} · ${v.chw_name}</strong>
                  <span class="small">${Object.entries(v.checklist).filter(([, on]) => on).map(([code]) => html`<span>${icon('check', 14)} ${t(`visitLog.items.${code}`)} </span>`)}</span>
                  ${v.reading ? html`<span class="small">${v.reading.systolic} / ${v.reading.diastolic} mmHg</span>` : ''}
                  ${v.note ? html`<span class="small muted">${v.note}</span>` : ''}
                </div>`,
              )}
            </section>`
          : ''}
      </div>
    </main>`
  }
  const redraw = () => ctx.draw(view())

  // --- loading
  const safe = (promise, fallback) => promise.catch(() => fallback)
  const loaders = {
    summary: async () => (s.summary = await ctx.api.get(`${base}/summary/`, { days: s.days })),
    plan: async () => (s.plan = await safe(ctx.api.get(`${base}/plan/`), null)),
    meds: async () => (s.meds = await safe(ctx.api.get(`${base}/medications/`, { include_inactive: 1 }), null)),
    questions: async () => (s.questions = (await safe(ctx.api.get(`${base}/visit-questions/`), { results: [] })).results ?? []),
    voice: async () => (s.voice = (await safe(ctx.api.get(`${base}/voice-notes/`), { results: [] })).results ?? []),
    phases: async () => (s.phases = (await safe(ctx.api.get(`${base}/phases/`), { results: [] })).results ?? []),
  }
  const reloadAnd = (name) => async () => {
    await loaders[name]()
    redraw()
  }
  redraw()
  const access = isSelf
    ? Promise.resolve({ display_name: auth.user?.display_name, scopes: SELF })
    : ctx.api.get('/patients/').then((rows) => rows.find((p) => p.patient_id === ctx.params.ref) ?? { scopes: [] })
  await Promise.allSettled([
    access.then((a) => (s.access = a)),
    ...Object.values(loaders).map((load) => load().catch(() => {})),
    safe(ctx.api.get(`${base}/readings/`, { limit: 60 }), { results: [] }).then((r) => (s.readings = r.results ?? [])),
    safe(ctx.api.get(`${base}/home-visits/`), { results: [] }).then((r) => (s.visits = r.results ?? [])),
    ctx.api.get('/checkin-questions/', { lang: locale.value }).then((r) => {
      for (const q of r.results ?? []) s.qtext[q.code] = { prompt: q.prompt, choices: Object.fromEntries(q.choices.map((c) => [String(c.value), c.label])) }
    }),
    auth.role === 'clinician' ? ctx.api.get('/plan-templates/').then((r) => (s.templates = r.results ?? [])) : Promise.resolve(),
  ])
  redraw()

  // --- actions
  const run = async (fn, reload) => {
    try {
      await fn()
      await reload()
    } catch (e) {
      toast(errorText(e))
    }
  }
  handleVoiceNotes(ctx, { base, urls: s.urls, redraw, reload: reloadAnd('voice') })
  ctx.on('click', '[data-act="days"]', async (el) => {
    s.days = Number(el.dataset.n)
    await loaders.summary()
    redraw()
  })
  ctx.on('click', '[data-act="print"]', () => window.print())
  ctx.on('submit', 'form[data-form="task"]', (form, event) => {
    event.preventDefault()
    const f = Object.fromEntries(new FormData(form).entries())
    run(() => ctx.api.post(`${base}/plan/tasks/`, { title: f.title, instructions: f.instructions }), async () => (form.reset(), await reloadAnd('plan')()))
  })
  ctx.on('click', '[data-act="retire"]', (el) => run(() => ctx.api.patch(`${base}/plan/tasks/${el.dataset.id}/`, { is_active: false }), reloadAnd('plan')))
  ctx.on('submit', 'form[data-form="template"]', (form, event) => {
    event.preventDefault()
    run(() => ctx.api.post(`${base}/plan/apply-template/`, { template: new FormData(form).get('template') }), reloadAnd('plan'))
  })
  ctx.on('submit', 'form[data-form="med"]', (form, event) => {
    event.preventDefault()
    const f = Object.fromEntries(new FormData(form).entries())
    const times = String(f.times).split(',').map((x) => x.trim()).filter(Boolean)
    run(() => ctx.api.post(`${base}/medications/`, { name: f.name, dose: f.dose, times, instructions: '' }), async () => (form.reset(), await reloadAnd('meds')()))
  })
  ctx.on('click', '[data-act="stop-med"]', (el) => {
    const m = s.meds.medications.find((x) => x.id === el.dataset.id)
    run(() => ctx.api.patch(`${base}/medications/${m.id}/`, { is_active: !m.is_active }), reloadAnd('meds'))
  })
  ctx.on('change', '[data-act="discussed"]', (el) => {
    const q = s.questions.find((x) => x.id === el.dataset.id)
    run(() => ctx.api.patch(`${base}/visit-questions/${q.id}/`, { discussed: !q.discussed }), reloadAnd('questions'))
  })
  // recovery stages (a verified clinician only)
  ctx.on('click', '[data-act="phase-open"]', () => ((s.addingPhase = true), redraw()))
  ctx.on('click', '[data-act="phase-cancel"]', () => ((s.addingPhase = false), redraw()))
  ctx.on('submit', 'form[data-form="phase"]', (form, event) => {
    event.preventDefault()
    const f = Object.fromEntries(new FormData(form).entries())
    run(
      () => ctx.api.post(`${base}/phases/`, { name: f.name, starts_on: f.starts_on, ends_on: f.ends_on || null, care_needed: f.care_needed }),
      async () => ((s.addingPhase = false), await reloadAnd('phases')()),
    )
  })
  ctx.on('click', '[data-act="phase-delete"]', (el) => {
    if (confirm(t('phase.confirmDelete'))) run(() => ctx.api.del(`${base}/phases/${el.dataset.id}/`), reloadAnd('phases'))
  })
}
