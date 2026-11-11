// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// The API client and the offline outbox: token refresh, readable errors, queued writes, and sending each entry once.
import './setup.js'

import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it, mock } from 'node:test'

import { api, ApiError, errorText, tokens } from '../site/js/api.js'
import { clearQueue, enqueue, flush, pendingCount } from '../site/js/offline.js'
import { json, networkDown, stubFetch } from './helpers.js'

beforeEach(() => {
  localStorage.clear()
  clearQueue()
})
afterEach(() => mock.restoreAll())

describe('api client', () => {
  it('refreshes an expired token once, stores the rotated pair, and retries', async () => {
    tokens.set('old-access', 'old-refresh')
    const calls = []
    stubFetch(async (url, init) => {
      const path = String(url).replace('http://localhost', '')
      calls.push(`${init?.method} ${path} ${init?.headers?.Authorization ?? ''}`.trim())
      if (path.endsWith('/auth/refresh/')) return json(200, { access: 'new-access', refresh: 'new-refresh' })
      if (init?.headers?.Authorization === 'Bearer old-access') return json(401, { error: { code: 'token_not_valid', message: 'expired' } })
      return json(200, { ok: true })
    })
    assert.deepEqual(await api.get('/me/'), { ok: true })
    assert.equal(tokens.access, 'new-access')
    assert.equal(tokens.refresh, 'new-refresh')
    assert.equal(calls.length, 3) // the first try, the refresh, the retry
  })

  it('turns the API error shape into a readable message', async () => {
    stubFetch(async () =>
      json(400, { error: { code: 'validation_error', message: 'Some details need fixing.', fields: { systolic: ['Please check this number.'] } } }),
    )
    const err = await api.post('/patients/me/readings/', {}).catch((e) => e)
    assert.ok(err instanceof ApiError)
    assert.equal(err.status, 400)
    assert.equal(errorText(err), 'Please check this number.')
    assert.equal(errorText(err, 'systolic'), 'Please check this number.')
  })

  it('does not ask for a refresh when signing in (a wrong password is just an error)', async () => {
    tokens.set('a', 'r')
    const seen = []
    stubFetch(async (url) => {
      seen.push(String(url))
      return json(401, { error: { code: 'no_account', message: 'Wrong email or password.' } })
    })
    const err = await api.post('/auth/login/', { email: 'x', password: 'y' }, { auth: false }).catch((e) => e)
    assert.equal(err.message, 'Wrong email or password.')
    assert.equal(seen.length, 1)
  })

  it('sends the chosen language and the token', async () => {
    tokens.set('abc', 'def')
    const mocked = stubFetch(async () => json(200, {}))
    await api.get('/me/')
    const headers = mocked.mock.calls[0].arguments[1].headers
    assert.equal(headers.Authorization, 'Bearer abc')
    assert.ok(headers['Accept-Language'])
  })

  it('queues a queueable write when the network is down, and not others', async () => {
    stubFetch(networkDown)
    assert.deepEqual(await api.post('/patients/me/checkins/', { answers: [] }, { queueable: true }), { queued: true })
    assert.equal(pendingCount.value, 1)
    await assert.rejects(api.post('/patients/me/messages/', { body: 'x' }), ApiError)
    assert.equal(pendingCount.value, 1)
  })

  it('says "offline" in plain words when there is nothing to fall back on', async () => {
    stubFetch(networkDown)
    const err = await api.get('/patients/me/readings/').catch((e) => e)
    assert.ok(err instanceof ApiError)
    assert.equal(err.code, 'offline')
  })
})

describe('offline outbox', () => {
  it('sends in order, keeps entries on a network failure, drops ones the server rejects', async () => {
    stubFetch(networkDown)
    for (const n of [1, 2, 3]) await api.post(`/x/${n}/`, { n }, { queueable: true })
    assert.equal(pendingCount.value, 3)

    const seen = []
    const result = await flush(async (item) => {
      seen.push(item.path)
      if (item.path === '/x/2/') return json(400, {})
      if (item.path === '/x/3/') throw new TypeError('offline again')
      return json(201, {})
    })
    assert.deepEqual(seen, ['/x/1/', '/x/2/', '/x/3/'])
    assert.deepEqual(result, { sent: 1, dropped: 1 })
    assert.equal(pendingCount.value, 1) // the third waits for the next connection
  })

  it('keeps an entry when the server is briefly down or the login expired', async () => {
    enqueue({ method: 'POST', path: '/a/', body: {} })
    enqueue({ method: 'POST', path: '/b/', body: {} })
    const result = await flush(async () => json(503, {}))
    assert.deepEqual(result, { sent: 0, dropped: 0 })
    assert.equal(pendingCount.value, 2)
    await flush(async () => json(401, {}))
    assert.equal(pendingCount.value, 2)
  })

  it('sends each waiting entry once even if two syncs start together', async () => {
    enqueue({ method: 'POST', path: '/patients/me/mobility/', body: { kind: 'walking' } })
    enqueue({ method: 'POST', path: '/patients/me/mobility/', body: { kind: 'standing' } })
    let sent = 0
    const send = async () => {
      sent++
      await new Promise((r) => setTimeout(r, 10)) // slow enough that the second sync starts while the first is running
      return new Response('{}', { status: 201 })
    }
    const [a, b] = await Promise.all([flush(send), flush(send)])
    assert.equal(sent, 2)
    assert.deepEqual(a, b)
    assert.equal(pendingCount.value, 0)
  })
})
