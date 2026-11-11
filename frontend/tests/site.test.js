// Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
// Checks on the files themselves: nothing the browser's security rules would block, an offline list that is complete,
// and a service worker that can never keep personal data.
import './setup.js'

import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { dirname, join, normalize } from 'node:path'
import { describe, it } from 'node:test'

import { read, SITE, walk } from './helpers.js'

const files = walk(SITE)
const scripts = files.filter((f) => f.startsWith('js/') && f.endsWith('.js'))
const sw = read('sw.js')

describe('the page and the scripts follow the content security policy', () => {
  it('index.html has no inline script and loads scripts only from this site', () => {
    const html = read('index.html')
    const tags = [...html.matchAll(/<script\b[^>]*>/g)].map((m) => m[0])
    assert.ok(tags.length >= 1)
    for (const tag of tags) assert.match(tag, /\ssrc="\/[^"]+"/, tag)
    assert.equal(/<script\b[^>]*>\s*\S/.test(html.replace(/<script\b[^>]*src=[^>]*><\/script>/g, '')), false)
  })

  it('no page or screen uses an inline event attribute such as onclick="..."', () => {
    for (const file of ['index.html', ...scripts]) assert.equal(/\son[a-z]+\s*=\s*["']/.test(read(file)), false, file)
  })

  it('the only outside addresses are Google Fonts', () => {
    for (const file of ['index.html', ...scripts, 'css/app.css', 'css/tokens.css']) {
      for (const m of read(file).matchAll(/https?:\/\/([a-z0-9.-]+)/g)) {
        if (/^(www\.)?w3\.org$/.test(m[1])) continue // XML namespace in SVG, not a request
        if (m[1] === 'localhost') continue // api.js: the base address used only when there is no browser (these tests)
        assert.ok(['fonts.googleapis.com', 'fonts.gstatic.com'].includes(m[1]), `${file}: ${m[0]}`)
      }
    }
  })

  it('every relative import points at a file that exists', () => {
    for (const file of scripts) {
      for (const m of read(file).matchAll(/(?:from\s+|import\(\s*)['"](\.{1,2}\/[^'"]+)['"]/g)) {
        assert.ok(existsSync(join(SITE, normalize(join(dirname(file), m[1])))), `${file} imports ${m[1]}`)
      }
    }
  })
})

describe('the service worker', () => {
  const list = [...sw.slice(sw.indexOf('// BEGIN PRECACHE'), sw.indexOf('// END PRECACHE')).matchAll(/^\s+'([^']+)',$/gm)].map((m) => m[1])

  it('lists every file the app needs to open offline, and only files that exist', () => {
    const wanted = files.filter((f) => f !== 'sw.js' && f !== 'index.html').map((f) => `/${f}`)
    assert.deepEqual(wanted.filter((u) => !list.includes(u)), [], 'files missing from the list (run python tools/make_precache.py)')
    assert.deepEqual(list.filter((u) => u !== '/' && !existsSync(join(SITE, u))), [], 'listed files that do not exist')
    assert.ok(list.includes('/'))
  })

  it('stores only public content: education, the talk board, emergency guidance and the visit checklist', () => {
    const source = /const PUBLIC_API = \/(.*)\/\n/.exec(sw)[1]
    const publicApi = new RegExp(source)
    for (const p of ['/api/v1/education/articles/', '/api/v1/talk-board/', '/api/v1/emergency/', '/api/v1/home-visit-checklist/'])
      assert.ok(publicApi.test(p), p)
    for (const p of [
      '/api/v1/me/',
      '/api/v1/patients/me/plan/',
      '/api/v1/patients/me/readings/',
      '/api/v1/patients/me/messages/',
      '/api/v1/inbox/',
      '/api/v1/auth/login/',
      '/api/v1/links/',
    ])
      assert.equal(publicApi.test(p), false, `${p} must never be stored by the service worker`)
  })

  it('never stores the API, the admin site or health checks in the app-shell cache', () => {
    const never = new RegExp(/const NEVER_CACHED = \/(.*)\/\n/.exec(sw)[1])
    for (const p of ['/api/v1/me/', '/admin/login/', '/static/admin/css/base.css', '/healthz']) assert.ok(never.test(p), p)
    assert.equal(never.test('/js/main.js'), false)
  })

  it('the app can be installed: a manifest with a name, a start page and an icon that exist', () => {
    const manifest = JSON.parse(read('manifest.webmanifest'))
    assert.ok(manifest.name && manifest.start_url === '/' && manifest.display)
    for (const icon of manifest.icons) assert.ok(existsSync(join(SITE, icon.src)), icon.src)
  })
})

describe('the page shell', () => {
  it('has a language, a title, a phone-sized viewport and the place screens are drawn into', () => {
    const html = read('index.html')
    assert.match(html, /<html[^>]*\slang=/)
    assert.match(html, /<title>[^<]+<\/title>/)
    assert.match(html, /name="viewport"[^>]*width=device-width/)
    assert.match(html, /id="view"/)
  })
})
