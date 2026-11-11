// Owner: Emmanuel Happy Rangira (Frontend developer) · AI-assisted draft, see AI_USE_LOG.md
// A value that tells you when it changes. The only "reactivity" the app needs.
export function signal(initial) {
  let current = initial
  const listeners = new Set()
  return {
    get value() {
      return current
    },
    set value(next) {
      if (next === current) return
      current = next
      listeners.forEach((fn) => fn(next))
    },
    subscribe(fn) {
      listeners.add(fn)
      return () => listeners.delete(fn)
    },
  }
}
