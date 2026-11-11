// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The screens are built from html`` templates. Text from people or the server must never turn into markup.
import './setup.js'

import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { esc, flag, html, isoDay, raw } from '../site/js/dom.js'

describe('html templates', () => {
  it('escapes everything that could become markup', () => {
    assert.equal(esc(`<b a="1" b='2'>&`), '&lt;b a=&quot;1&quot; b=&#39;2&#39;&gt;&amp;')
    assert.equal(esc(null), '')
    assert.equal(esc(undefined), '')
    assert.equal(esc(0), '0')
  })

  it('a name or message with a script in it is shown as text, not run', () => {
    const evil = '<img src=x onerror=alert(1)><script>alert(2)</script>'
    const out = String(html`<p>${evil}</p>`)
    assert.equal(out.includes('<img'), false)
    assert.equal(out.includes('<script'), false)
    assert.ok(out.includes('&lt;img'))
  })

  it('cannot break out of an attribute', () => {
    const out = String(html`<input value="${'" onfocus="alert(1)'}" />`)
    assert.equal(out, '<input value="&quot; onfocus=&quot;alert(1)" />')
  })

  it('keeps nested templates and lists as markup, and drops false, null and undefined', () => {
    const items = ['a', 'b<'].map((x) => html`<li>${x}</li>`)
    assert.equal(String(html`<ul>${items}</ul>`), '<ul><li>a</li><li>b&lt;</li></ul>')
    assert.equal(String(html`<p>${false}${null}${undefined}${0}</p>`), '<p>0</p>')
  })

  it('raw() is the only way to insert markup as written', () => {
    assert.equal(String(html`<p>${raw('<b>x</b>')}</p>`), '<p><b>x</b></p>')
    assert.equal(String(html`<p>${'<b>x</b>'}</p>`), '<p>&lt;b&gt;x&lt;/b&gt;</p>')
  })

  it('flag() gives "true" or "false" for aria attributes', () => {
    assert.equal(flag(1), 'true')
    assert.equal(flag(0), 'false')
  })
})

describe('isoDay', () => {
  it('writes the local date as YYYY-MM-DD with leading zeros', () => {
    assert.equal(isoDay(new Date(2026, 0, 5)), '2026-01-05')
    assert.equal(isoDay(new Date(2026, 11, 31)), '2026-12-31')
  })
})
