// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Voice notes: record one from the phone's microphone, list them, play them and delete them.
// Only real audio is stored, with size and length limits enforced by the server.
import { api, errorText } from '../api.js'
import { html } from '../dom.js'
import { t } from '../i18n.js'
import { icon, toast } from '../ui.js'

const MAX_SECONDS = 180

function pickType() {
  for (const type of ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported?.(type)) return type
  }
  return ''
}
const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

/** The empty place the recorder draws itself. Call mountRecorder() after every redraw of the screen. */
export const recorderSlot = () => html`<div data-voice-recorder></div>`

/** Draws the record button into the slot and runs the recording. `context` is visit, check_in or general. */
export function mountRecorder(root, { base, context, onSaved }) {
  const slot = root.querySelector('[data-voice-recorder]')
  if (!slot || slot.dataset.ready) return
  slot.dataset.ready = '1'
  let recorder = null
  let timer = null
  let chunks = []
  let seconds = 0
  let error = ''

  const draw = (recording = false) => {
    slot.innerHTML = String(html`<div class="stack-s">
      ${!recording
        ? html`<button type="button" class="sc-btn sc-btn-ghost" data-start>${icon('microphone', 22, 'duotone')}${t('voice.record')}</button>`
        : html`<button type="button" class="sc-btn sc-btn-primary" data-stop>${icon('stop', 22, 'fill')}${t('voice.stop')} · ${mmss(seconds)}
            <span class="sc-wave" aria-hidden="true" style="display: inline-flex; gap: 3px; height: 18px; align-items: center">
              <span style="height: 10px"></span><span style="height: 18px; animation-delay: .1s"></span><span style="height: 12px; animation-delay: .2s"></span>
            </span></button>`}
      ${error ? html`<p class="error" role="alert">${error}</p>` : ''}
    </div>`)
  }

  async function upload(stream) {
    stream.getTracks().forEach((track) => track.stop())
    const blob = new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' })
    const form = new FormData()
    form.append('audio', blob, 'voice-note')
    form.append('duration_seconds', String(Math.max(1, seconds)))
    form.append('context', context)
    try {
      await api.upload(`${base}/voice-notes/`, form)
      toast(t('voice.saved'))
      onSaved?.()
    } catch (e) {
      error = errorText(e)
    }
    draw(false)
  }

  function stop() {
    clearInterval(timer)
    if (recorder?.state === 'recording') recorder.stop()
    draw(false)
  }

  async function start() {
    error = ''
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const type = pickType()
      recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined)
      chunks = []
      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data)
      recorder.onstop = () => upload(stream)
      recorder.start()
      seconds = 0
      draw(true)
      timer = setInterval(() => {
        seconds++
        if (seconds >= MAX_SECONDS) stop()
        else draw(true)
      }, 1000)
    } catch {
      error = t('voice.noMic')
      draw(false)
    }
  }

  slot.addEventListener('click', (event) => {
    if (event.target.closest('[data-start]')) start()
    else if (event.target.closest('[data-stop]')) stop()
  })
  draw(false)
}

/** The list of voice notes. `urls` maps a note id to a playable address once it has been fetched. */
export function voiceNotes(notes, urls, canDelete = false) {
  return html`<ul class="list">
    ${notes.map(
      (n) => html`<li class="sc-card list-row">
        <div class="stack-s" style="flex-grow: 1">
          <strong>${t('voice.note')} · ${n.duration_seconds ?? '?'} s</strong>
          <span class="tiny">${n.recorded_by_name} · ${new Date(n.created_at).toLocaleString()}</span>
          ${urls[n.id] ? html`<audio src="${urls[n.id]}" controls autoplay style="width: 100%"></audio>` : ''}
        </div>
        ${!urls[n.id] ? html`<button class="icon-btn" data-act="vn-play" data-id="${n.id}" aria-label="${t('voice.play')}">${icon('play', 22, 'fill')}</button>` : ''}
        ${canDelete ? html`<button class="icon-btn" data-act="vn-delete" data-id="${n.id}" aria-label="${t('common.delete')}">${icon('trash', 20)}</button>` : ''}
      </li>`,
    )}
  </ul>`
}

/** Wire the play and delete buttons of voiceNotes(). `redraw` redraws the screen; `reload` fetches the notes again. */
export function handleVoiceNotes(ctx, { base, urls, redraw, reload }) {
  ctx.on('click', '[data-act="vn-play"]', async (el) => {
    const id = el.dataset.id
    try {
      urls[id] ??= URL.createObjectURL(await api.blob(`${base}/voice-notes/${id}/`))
      redraw()
    } catch (e) {
      toast(errorText(e))
    }
  })
  ctx.on('click', '[data-act="vn-delete"]', async (el) => {
    try {
      await api.del(`${base}/voice-notes/${el.dataset.id}/`)
      reload()
    } catch (e) {
      toast(errorText(e))
    }
  })
}
