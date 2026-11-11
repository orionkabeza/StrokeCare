// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Opening the app with no signal must never sign the person out, and with the optional saved copy it opens offline.
import './setup.js'

import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it, mock } from 'node:test'

import { tokens } from '../site/js/api.js'
import { saveCopy, setCopyEnabled, setCopyOwner } from '../site/js/copy.js'
import { auth } from '../site/js/store.js'
import { json, networkDown, stubFetch } from './helpers.js'

const ME = {
  user: { id: 'u1', role: 'survivor', display_name: 'Demo', preferred_language: 'en', timezone: 'Africa/Kigali', email: 'd@example.org' },
  consents: {},
}
const copies = () => Object.keys(localStorage).filter((k) => k.startsWith('sc-copy:'))

beforeEach(() => {
  localStorage.clear()
  auth.user = null
  auth.consents = {}
  auth.ready = false
  setCopyEnabled(false)
  setCopyOwner(null)
  tokens.set('access-1', 'refresh-1')
})
afterEach(() => mock.restoreAll())

describe('starting the app without a connection', () => {
  it('keeps the person signed in when the network is down', async () => {
    stubFetch(networkDown)
    await auth.load()
    assert.equal(auth.ready, true)
    assert.equal(tokens.refresh, 'refresh-1') // still signed in on the phone, ready for when the signal returns
  })

  it('keeps the person signed in when the server is briefly down', async () => {
    stubFetch(async () => json(503, { error: { code: 'unavailable', message: 'Try again soon.' } }))
    await auth.load()
    assert.equal(tokens.refresh, 'refresh-1')
  })

  it('does end the session when the server says the login is no longer valid', async () => {
    stubFetch(async () => json(401, { error: { code: 'token_not_valid', message: 'x' } }))
    await auth.load()
    assert.equal(tokens.refresh, null)
    assert.equal(auth.signedIn, false)
  })

  it('opens from the saved copy when the person turned it on', async () => {
    setCopyEnabled(true)
    saveCopy('/me/', undefined, ME)
    stubFetch(networkDown)
    await auth.load()
    assert.equal(auth.signedIn, true)
    assert.equal(auth.user.display_name, 'Demo')
  })

  it('without the saved copy, nothing about the person is available offline', async () => {
    stubFetch(networkDown)
    await auth.load()
    assert.equal(auth.signedIn, false)
    assert.equal(copies().length, 0)
  })

  it('signing out removes the saved copy, including who was signed in', () => {
    setCopyEnabled(true)
    saveCopy('/me/', undefined, ME)
    assert.equal(copies().length, 1)
    auth.forget()
    assert.equal(copies().length, 0)
    assert.equal(tokens.access, null)
  })

  it('knows which screen is home for each kind of account', () => {
    const homes = { survivor: '/today', prevention: '/today', caregiver: '/care', clinician: '/doctor', chw: '/chw', admin: '/settings' }
    for (const [role, home] of Object.entries(homes)) {
      auth.user = { role }
      assert.equal(auth.home, home, role)
    }
  })
})
