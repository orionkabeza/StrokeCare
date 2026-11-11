// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The route table: every screen loads, the right accounts reach the right screens, and nobody is let in by accident.
import './setup.js'

import assert from 'node:assert/strict'
import { beforeEach, describe, it } from 'node:test'

import { guard, match, ROUTES } from '../site/js/router.js'
import { auth } from '../site/js/store.js'

const ROLES = ['prevention', 'survivor', 'caregiver', 'clinician', 'chw', 'admin']
const signIn = (role, consents = {}) => {
  auth.user = role ? { id: 'u1', role } : null
  auth.consents = consents
}
const go = (path) => guard(path, match(path))

beforeEach(() => signIn(null))

describe('route table', () => {
  it('has the 31 screens, each path once', () => {
    assert.equal(ROUTES.length, 31)
    assert.equal(new Set(ROUTES.map((r) => r.path)).size, ROUTES.length)
  })

  it('every screen module loads and draws with a function (catches a wrong import in any screen)', async () => {
    for (const route of ROUTES) {
      const mod = await route.view()
      assert.equal(typeof mod.default, 'function', route.path)
    }
  })

  it('only names real kinds of account', () => {
    for (const route of ROUTES) for (const role of route.roles ?? []) assert.ok(ROLES.includes(role), `${route.path}: ${role}`)
  })
})

describe('matching', () => {
  it('reads the parts of a path', () => {
    assert.equal(match('/p/me/bp').params.ref, 'me')
    assert.equal(match('/learn/high-blood-pressure').params.slug, 'high-blood-pressure')
    assert.equal(match('/p/a%20b/bp').params.ref, 'a b')
  })

  it('allows a trailing slash and finds nothing for an unknown path', () => {
    assert.ok(match('/today/'))
    assert.equal(match('/nope'), null)
    assert.equal(match('/p/me'), null)
  })
})

describe('who may open what', () => {
  it('lets a signed-out visitor open the public screens and sends them to sign-in for the rest', () => {
    for (const p of ['/welcome', '/login', '/register', '/emergency', '/talk', '/learn', '/learn/stroke']) assert.equal(go(p), null, p)
    assert.equal(go('/today'), '/login?next=%2Ftoday')
    assert.equal(go('/p/me/medicines'), '/login?next=%2Fp%2Fme%2Fmedicines')
  })

  it('sends an unknown path home', () => {
    assert.equal(go('/nope'), '/')
  })

  it('sends a signed-in person from the front page to their own home', () => {
    const homes = { survivor: '/today', prevention: '/today', caregiver: '/care', clinician: '/doctor', chw: '/chw', admin: '/settings' }
    for (const [role, home] of Object.entries(homes)) {
      signIn(role)
      assert.equal(go('/'), home, role)
      assert.equal(go('/welcome'), home, role)
    }
  })

  it('keeps each kind of account out of the screens that are not theirs', () => {
    signIn('survivor')
    for (const p of ['/doctor', '/caseload', '/templates', '/care', '/chw']) assert.equal(go(p), '/today', p)
    signIn('caregiver')
    for (const p of ['/today', '/doctor', '/chw', '/reminders', '/care-team']) assert.equal(go(p), '/care', p)
    signIn('chw')
    for (const p of ['/today', '/doctor', '/care']) assert.equal(go(p), '/chw', p)
    signIn('clinician')
    for (const p of ['/today', '/care', '/chw']) assert.equal(go(p), '/doctor', p)
  })

  it('an admin sees no health screens', () => {
    signIn('admin')
    for (const p of ['/today', '/inbox', '/care', '/doctor', '/caseload', '/chw']) assert.equal(go(p), '/settings', p)
    assert.equal(go('/settings'), null)
  })

  it('home-visit entry is for community health workers only', () => {
    signIn('chw')
    assert.equal(go('/p/abc/home-visit'), null)
    for (const role of ['survivor', 'caregiver', 'clinician']) {
      signIn(role)
      assert.notEqual(go('/p/abc/home-visit'), null, role)
    }
  })

  it('sends someone who has not agreed yet to the consent page, but still lets them reach settings', () => {
    signIn('survivor', { health_data: { granted: false } })
    assert.equal(go('/today'), '/consent')
    assert.equal(go('/p/me/bp'), '/consent')
    assert.equal(go('/consent'), null)
    assert.equal(go('/settings'), null)
  })
})
