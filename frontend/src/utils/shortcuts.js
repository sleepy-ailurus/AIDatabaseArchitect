const handlers = new Map()

function normalizeKey(e) {
  const parts = []
  if (e.ctrlKey || e.metaKey) parts.push('Ctrl')
  if (e.shiftKey) parts.push('Shift')
  if (e.altKey) parts.push('Alt')
  if (!e.key) return null
  const key = e.key.toLowerCase()
  if (key === 'control' || key === 'meta' || key === 'shift' || key === 'alt') return null
  parts.push(key)
  return parts.join('+')
}

function handleKeydown(e) {
  const combo = normalizeKey(e)
  if (!combo) return
  const handler = handlers.get(combo)
  if (handler) {
    e.preventDefault()
    handler(e)
  }
}

let listenerAttached = false

function ensureListener() {
  if (!listenerAttached) {
    window.addEventListener('keydown', handleKeydown)
    listenerAttached = true
  }
}

export function registerShortcut(combo, handler) {
  ensureListener()
  handlers.set(combo.toLowerCase(), handler)
}

export function unregisterShortcut(combo) {
  handlers.delete(combo.toLowerCase())
}

export function clearShortcuts() {
  handlers.clear()
}
