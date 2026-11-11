// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// Import this FIRST in a test file. The app keeps a few things in the browser's localStorage; Node has none, so this
// gives the tests a small stand-in that behaves the same way (including Object.keys(localStorage)).
class MemoryStorage {
  getItem(key) {
    return Object.hasOwn(this, key) ? this[key] : null
  }
  setItem(key, value) {
    this[key] = String(value)
  }
  removeItem(key) {
    delete this[key]
  }
  clear() {
    for (const key of Object.keys(this)) delete this[key]
  }
}

Object.defineProperty(globalThis, 'localStorage', { value: new MemoryStorage(), configurable: true, writable: true })
