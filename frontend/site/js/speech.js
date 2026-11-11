// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Reads text aloud with the phone's own voice. There are no recordings. If the phone has no voice for the chosen
// language (Kinyarwanda voices are rare), canSpeak() is false and the screen shows the words large instead.
import { locale } from './i18n.js'
import { signal } from './state.js'

const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
let voices = []
export const speaking = signal(false)
if (supported) {
  const load = () => (voices = window.speechSynthesis.getVoices())
  load()
  window.speechSynthesis.addEventListener?.('voiceschanged', load)
}

const voice = () => voices.find((v) => v.lang.toLowerCase().startsWith(locale.value)) ?? null
export const canSpeak = () => supported && !!voice()

export function speak(text) {
  const v = voice()
  if (!supported || !v) return false
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.voice = v
  u.lang = v.lang
  u.rate = 0.9
  u.onstart = () => (speaking.value = true)
  u.onend = u.onerror = () => (speaking.value = false)
  window.speechSynthesis.speak(u)
  return true
}

export function stopSpeaking() {
  if (supported) window.speechSynthesis.cancel()
  speaking.value = false
}
