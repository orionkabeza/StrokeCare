// Owner: Emmanuel Happy Rangira (Frontend developer)
// Runs synchronously, before first paint, so a returning visitor with dark or high-contrast saved never sees a
// flash of the light theme while the real app (loaded as a deferred module) starts up. A plain script with no
// defer/async/type=module, so the browser runs it in place while still parsing <head>, before the CSS below is
// matched against <html>. Mirrors store.js's applyToPage(); kept tiny and defensive since nothing else has
// loaded yet if this throws.
;(function () {
  try {
    var p = JSON.parse(localStorage.getItem('sc-prefs') || '{}')
    var theme = p.theme || 'system'
    var dark = theme === 'dark' || (theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches)
    var root = document.documentElement
    root.dataset.theme = p.high_contrast ? 'contrast' : dark ? 'dark' : 'light'
    if (p.easy_read_font) root.dataset.font = 'easy'
    if (p.reduce_motion) root.dataset.motion = 'reduce'
    if (p.one_handed_layout) root.dataset.hand = 'one'
    if (p.low_data_mode) root.dataset.lowData = 'true'
    if (p.text_scale) root.style.fontSize = p.text_scale + '%'
  } catch (e) {
    /* leave the CSS defaults (light theme) in place */
  }
})()
