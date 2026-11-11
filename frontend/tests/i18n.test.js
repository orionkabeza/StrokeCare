// Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md
// Every text the app shows exists in English, Kinyarwanda and French, and none is blank.
import './setup.js'

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, it } from 'node:test'

import { locale, t, useMessages } from '../site/js/i18n.js'
import { read, SITE, walk } from './helpers.js'

const load = (code) => JSON.parse(readFileSync(`${SITE}/locales/${code}.json`, 'utf8'))
const en = load('en')
const fr = load('fr')
const rw = load('rw')

function flatten(obj, prefix = '') {
  const out = {}
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object') Object.assign(out, flatten(v, key))
    else out[key] = String(v)
  }
  return out
}
const E = flatten(en)
const holes = (s) => (s.match(/\{\w+\}/g) ?? []).sort()
// The code of every screen and helper, without whole-line comments (a comment may mention t('a.b') as an example).
const sources = () =>
  walk(`${SITE}/js`)
    .filter((f) => f.endsWith('.js') && f !== 'icons.js')
    .map((f) => read(`js/${f}`).split('\n').filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line)).join('\n'))

// Messages that deliberately have a singular and a plural form ("1 person | 2 people"), written as `one | other`.
const PLURAL = new Set(['doctor.people', 'mobility.entries'])

describe('translations', () => {
  for (const [name, messages] of [['fr', fr], ['rw', rw]]) {
    it(`${name} has every English key, none empty, same placeholders`, () => {
      const other = flatten(messages)
      assert.deepEqual(Object.keys(other).sort(), Object.keys(E).sort())
      for (const [key, text] of Object.entries(E)) {
        assert.notEqual(other[key].trim(), '', key)
        assert.deepEqual(holes(other[key]), holes(text), key)
      }
    })
  }

  it('every static key used in the code exists', () => {
    const used = new Set()
    for (const src of sources()) for (const m of src.matchAll(/\bt\(\s*'([a-zA-Z0-9_.]+)'/g)) used.add(m[1])
    assert.ok(used.size > 200, `only found ${used.size} keys: is the pattern still right?`)
    assert.deepEqual([...used].filter((k) => !(k in E)), [])
  })

  it('every computed key (t(`group.${x}`)) points at a group that exists', () => {
    const groups = new Set()
    for (const src of sources()) for (const m of src.matchAll(/\bt\(\s*`([a-zA-Z0-9_.]+)\.\$\{/g)) groups.add(m[1])
    assert.ok(groups.size > 5)
    const has = (prefix) => Object.keys(E).some((k) => k.startsWith(`${prefix}.`))
    assert.deepEqual([...groups].filter((g) => !has(g)), [])
  })

  it('a "|" appears only in the messages that are meant to have a singular and a plural form', () => {
    for (const [key, text] of Object.entries({ ...E, ...flatten(fr), ...flatten(rw) })) {
      if (PLURAL.has(key)) assert.equal(text.split('|').length, 2, key) // exactly one separator
      else assert.equal(text.includes('|'), false, key)
    }
    for (const messages of [E, flatten(fr), flatten(rw)])
      for (const key of Object.keys(messages)) if (PLURAL.has(key)) for (const form of messages[key].split('|')) assert.ok(form.includes('{n}'), key)
  })

  it('emergency guidance never contains a phone number', () => {
    for (const m of [en, fr, rw]) assert.equal(/\d/.test(m.emergency.message), false)
  })
})

describe('t()', () => {
  useMessages('en', { hello: 'Hello {name}', only: { english: 'Only in English' }, people: '{n} person | {n} people' })
  useMessages('fr', { hello: 'Bonjour {name}' })

  it('fills placeholders and leaves unknown ones visible', () => {
    locale.value = 'en'
    assert.equal(t('hello', { name: 'Amina' }), 'Hello Amina')
    assert.equal(t('hello'), 'Hello {name}')
  })

  it('falls back to English, then to the key, so nothing is ever blank', () => {
    locale.value = 'fr'
    assert.equal(t('hello', { name: 'Amina' }), 'Bonjour Amina')
    assert.equal(t('only.english'), 'Only in English')
    assert.equal(t('no.such.key'), 'no.such.key')
    locale.value = 'en'
  })

  it('picks the singular or plural form from the count', () => {
    assert.equal(t('people', { n: 1 }, 1), '1 person')
    assert.equal(t('people', { n: 3 }, 3), '3 people')
    assert.equal(t('people', { n: 0 }, 0), '0 people')
  })
})
