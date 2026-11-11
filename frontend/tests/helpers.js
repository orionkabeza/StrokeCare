// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
import { mock } from 'node:test'

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const SITE = join(dirname(fileURLToPath(import.meta.url)), '..', 'site')

/** A fetch Response with a JSON body, the way the API sends one. */
export const json = (status, body) =>
  new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

/** Replace fetch for one test. Returns the mock (calls are in `.mock.calls`). Call mock.restoreAll() afterwards. */
export const stubFetch = (impl) => mock.method(globalThis, 'fetch', impl)

/** The phone has no signal: every request fails the way a real fetch does. */
export const networkDown = async () => {
  throw new TypeError('Failed to fetch')
}

/** Every file under a folder, as paths relative to it, with forward slashes. */
export function walk(dir, base = dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? walk(path, base) : [path.slice(base.length + 1).split('\\').join('/')]
  })
}

export const read = (relative) => readFileSync(join(SITE, relative), 'utf8')
