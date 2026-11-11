// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Entries made without signal wait here and are sent, in order, when the phone reconnects.
// Privacy: only the waiting entries are kept on the phone, and each is deleted as soon as the server accepts it.
import { signal } from './state.js'

const KEY = 'sc-outbox'

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]')
  } catch {
    return []
  }
}

/** How many entries are waiting to be sent. */
export const pendingCount = signal(read().length)

function write(items) {
  try {
    localStorage.setItem(KEY, JSON.stringify(items))
  } catch {
    /* storage full or blocked: nothing more we can do offline */
  }
  pendingCount.value = items.length
}

export function enqueue(item) {
  const items = read()
  items.push({ ...item, id: crypto.randomUUID(), created: new Date().toISOString() })
  write(items)
}

export function clearQueue() {
  write([])
}

let inFlight = null

/** Send waiting entries. Only one sync runs at a time, so an entry is never sent twice when the phone reconnects and
 *  the app starts at the same moment. Stops at the first network failure; drops entries the server rejects as invalid. */
export function flush(send) {
  inFlight ??= sendAll(send).finally(() => {
    inFlight = null
  })
  return inFlight
}

async function sendAll(send) {
  let sent = 0
  let dropped = 0
  for (const item of read()) {
    let r
    try {
      r = await send(item)
    } catch {
      break
    }
    if (r.status >= 500 || r.status === 401) break
    write(read().filter((i) => i.id !== item.id))
    if (r.ok) sent++
    else dropped++
  }
  return { sent, dropped }
}
