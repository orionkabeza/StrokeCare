<!-- Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md -->
# Frontend

Plain HTML, CSS and JavaScript. No framework, no packages to install, no build step. The files in `site/` are served
exactly as they are by Django (WhiteNoise) at `/`, with the API under `/api/`.

Design: https://claude.ai/artifact/4Vokfg2stQ1X6iAQnUSvdE (private until shared).

## Run it

Start the backend (see the main README), then open <http://localhost:8001/> (or whichever port you started it on).
Edit a file under `site/`, reload the page. That is the whole loop.

```bash
cd frontend
npm test                           # Node's built-in test runner: needs Node 22 or newer, installs nothing
python ../tools/make_precache.py   # after adding, removing or changing any file under site/ (see "Offline" below)
```

## Layout

| Path | What |
|---|---|
| `site/index.html` | the page shell: side navigation, top bar, the area every screen is drawn into, bottom tabs |
| `site/js/main.js` | starts the app: language, signed-in person, router, service worker |
| `site/js/router.js` | the route table (31 screens), who may open which, links and the Back button |
| `site/js/dom.js` | `html` templates that escape everything automatically, `raw()` for markup the code built itself |
| `site/js/api.js` | every API call: token, one refresh on expiry, plain error messages, offline queueing |
| `site/js/offline.js` | entries made without signal wait here and are sent once, in order, when back online |
| `site/js/copy.js` | the optional "keep my plan on this phone" copy (off by default, see the rules inside) |
| `site/js/store.js` | the signed-in person (`auth`) and display preferences (`prefs`, saved to the account) |
| `site/js/i18n.js`, `site/locales/*.json` | English, Kinyarwanda, French. English is the fallback |
| `site/js/ui.js`, `site/js/icons.js` | shared pieces (headers, charts, toasts) and the icon set |
| `site/js/views/` | the screens, by audience: `patient`, `care`, `clinician`, `chw`, `shared`, `auth` |
| `site/css/tokens.css`, `app.css` | design tokens (light, dark, high contrast, easy-read font, motion) and components |
| `site/sw.js` | the service worker: keeps the app itself working offline |
| `tests/` | `node --test` tests: translations, API client, offline queue, saved copy, routes, HTML safety, site checks |

## How a screen works

A screen is a file that exports one function. It draws with `ctx.draw(html\`...\`)`, listens with
`ctx.on('click', '[data-act="save"]', handler)`, and navigates with `ctx.go('/path')`. Typed text and focus survive a
redraw. To add a screen: write the file in `site/js/views/`, add a line to `ROUTES` in `site/js/router.js`, add any
new texts to all three files in `site/locales/`, then run `python ../tools/make_precache.py` and `npm test`.

## Offline

The service worker keeps the app's own files (and public education content) so the app opens without a connection. It
needs the list of those files, which is generated, so run `python tools/make_precache.py` after any change under
`site/`; a test and CI fail if the list is out of date. Personal health data is never stored by the service worker.

## Rules the UI follows (from docs/SAFETY.md)

- Blood pressure is plain numbers. No colour, badge, arrow or "normal range".
- The Emergency button is on every screen, and red is used for nothing else.
- An answer in a question's `urgent_values` shows emergency guidance at once, before anything is sent.
- Draft content says it is a draft. Messages and alerts say they are not an emergency service.
- No streaks, scores or confetti.
- Personal health data is never cached by the service worker. Only public content (education, talk board,
  emergency, CHW checklist) is cached for offline use. The person's own optional copy is separate and opt-in.
- Nothing from people or the server is ever inserted as markup: use `html` templates, and `raw()` only for markup
  this code built.

## Known limits

- Tokens are kept in `localStorage` so people stay signed in on their own phone. The strict Content Security
  Policy (scripts from this site only, no inline scripts or event attributes) is the main protection against them
  being read by injected code. A test fails if an inline script or `onclick="..."` is added.
- Read-aloud depends on the phone having a voice for the language. Kinyarwanda voices are rare; the app then
  shows the words large instead.
- Some browsers cannot format dates in Kinyarwanda and show English dates instead.
- The icons are generated from Phosphor's open-source icon set by `tools/make_icons.py`. Only someone adding an icon
  needs that: the steps (they use `npm pack`, so Node and an internet connection) are at the top of the script.
- The app uses the browser's own modules (`import`), so it needs a current browser (any from the last few years).
