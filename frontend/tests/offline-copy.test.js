// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The optional "keep my plan on this phone" copy. Phones are often shared, so the rules are strict:
// off by default, only the person's own plan-type data, never health readings or messages, one owner, and wiped on sign-out.
import './setup.js'

import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it, mock } from 'node:test'

import { api, ApiError } from '../site/js/api.js'
import { copyEnabled, readCopy, saveCopy, setCopyEnabled, setCopyOwner, showingCopy, wipeCopies } from '../site/js/copy.js'
import { json, networkDown, stubFetch } from './helpers.js'

const copies = () => Object.keys(localStorage).filter((k) => k.startsWith('sc-copy:'))

beforeEach(() => {
  localStorage.clear()
  setCopyEnabled(false)
  setCopyOwner('person-a')
  showingCopy.value = false
})
afterEach(() => mock.restoreAll())

describe('offline copy', () => {
  it('is off by default and keeps nothing', async () => {
    assert.equal(copyEnabled.value, false)
    stubFetch(async () => json(200, { tasks: [1] }))
    await api.get('/patients/me/plan/')
    assert.equal(copies().length, 0)
  })

  it('when on, keeps the plan and serves it back when the phone is offline', async () => {
    setCopyEnabled(true)
    const fetchMock = stubFetch(async () => json(200, { tasks: ['walk'] }))
    await api.get('/patients/me/plan/')
    assert.equal(copies().length, 1)
    fetchMock.mock.mockImplementation(networkDown)
    assert.deepEqual(await api.get('/patients/me/plan/'), { tasks: ['walk'] })
    assert.equal(showingCopy.value, true)
    fetchMock.mock.mockImplementation(async () => json(200, { tasks: ['walk', 'rest'] })) // back online: live data replaces the copy
    await api.get('/patients/me/plan/')
    assert.equal(showingCopy.value, false)
  })

  it("never keeps blood pressure, check-ins, messages or anyone else's record", async () => {
    setCopyEnabled(true)
    const fetchMock = stubFetch(async () => json(200, { results: [] }))
    for (const path of [
      '/patients/me/readings/',
      '/patients/me/checkins/',
      '/patients/me/summary/',
      '/patients/me/messages/',
      '/patients/0b6f7c8e-1d2a-4c3b-9e8f-7a6b5c4d3e2f/plan/',
      '/inbox/',
      '/me/export/',
    ])
      await api.get(path)
    assert.equal(copies().length, 0)
    fetchMock.mock.mockImplementation(networkDown)
    const err = await api.get('/patients/me/readings/').catch((e) => e)
    assert.ok(err instanceof ApiError) // no copy to fall back on: the normal offline error
  })

  it('keeps the plan-type data it is allowed to', () => {
    setCopyEnabled(true)
    for (const path of [
      '/patients/me/plan/',
      '/patients/me/medications/',
      '/patients/me/calendar/',
      '/patients/me/goals/',
      '/patients/me/phases/',
      '/patients/me/phrases/',
      '/patients/me/mobility/',
      '/me/care-team/',
      '/me/reminders/upcoming/',
    ])
      saveCopy(path, undefined, { ok: true })
    assert.equal(copies().length, 9)
  })

  it('a saved copy belongs to one person and is not shown to another', () => {
    setCopyEnabled(true)
    saveCopy('/patients/me/plan/', undefined, { tasks: ['private'] })
    assert.deepEqual(readCopy('/patients/me/plan/'), { tasks: ['private'] })
    setCopyOwner('person-b')
    assert.equal(readCopy('/patients/me/plan/'), null)
  })

  it('turning it off, or signing out, removes everything', () => {
    setCopyEnabled(true)
    saveCopy('/patients/me/plan/', undefined, { a: 1 })
    saveCopy('/patients/me/goals/', undefined, { b: 2 })
    assert.equal(copies().length, 2)
    wipeCopies()
    assert.equal(copies().length, 0)
    saveCopy('/patients/me/plan/', undefined, { a: 1 })
    setCopyEnabled(false)
    assert.equal(copies().length, 0)
    assert.equal(localStorage.getItem('sc-offline-copy'), null)
  })

  it('does not keep anything without a signed-in owner', () => {
    setCopyEnabled(true)
    setCopyOwner(null)
    saveCopy('/patients/me/plan/', undefined, { a: 1 })
    assert.equal(copies().length, 0)
  })

  it('keeps separate copies for different query strings', () => {
    setCopyEnabled(true)
    saveCopy('/patients/me/mobility/', { days: 30 }, { n: 30 })
    saveCopy('/patients/me/progress/', { days: 7 }, { n: 7 })
    assert.deepEqual(readCopy('/patients/me/mobility/', { days: 30 }), { n: 30 })
    assert.equal(readCopy('/patients/me/mobility/', { days: 7 }), null)
  })

  it('does not keep a very large response', () => {
    setCopyEnabled(true)
    saveCopy('/patients/me/plan/', undefined, { text: 'x'.repeat(300_000) })
    assert.equal(copies().length, 0)
  })
})
