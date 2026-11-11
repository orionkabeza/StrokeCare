// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Start the app: language first, then the frame, then the first screen.
import { initialLocale, setLocale } from './i18n.js'
import { startRouter } from './router.js'
import { mountShell } from './shell.js'
import { auth, prefs } from './store.js'

await setLocale(initialLocale())
mountShell()

// When a person signs in (or the app finds them still signed in), use their language and display settings.
auth.changed.subscribe(async () => {
  if (!auth.user) return
  await setLocale(auth.user.preferred_language)
  try {
    await prefs.loadFromAccount()
  } catch {
    /* keep the phone's own settings */
  }
})

await startRouter()

// The service worker keeps the app (and only public content) working without a connection.
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {})
