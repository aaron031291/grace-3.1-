/**
 * Grace Brain Client — single interface for all 8 brain domains.
 *
 * Usage:
 *   import { brainCall, useBrain } from '../api/brain-client'
 *
 *   // Direct call
 *   const chats = await brainCall('chat', 'list', { limit: 50 })
 *
 *   // React hook
 *   const { data, loading, error, call } = useBrain('system', 'runtime')
 */

import { useState, useCallback } from 'react'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Call a brain domain action.
 * @param {string} domain - Brain domain (chat, files, govern, ai, system, data, tasks, code)
 * @param {string} action - Action name within the domain
 * @param {object} payload - Action payload
 * @returns {Promise<{ok: boolean, data: any, error: string|null, latency_ms: number}>}
 */
export async function brainCall(domain, action, payload = {}) {
  try {
    const response = await fetch(`${BASE}/brain/${domain}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, payload }),
    })

    const result = await response.json()
    return {
      ok: result.ok ?? response.ok,
      data: result.data ?? result,
      error: result.error ?? null,
      latency_ms: result.latency_ms ?? 0,
      genesis_key_id: result.genesis_key_id ?? null,
    }
  } catch (err) {
    return { ok: false, data: null, error: err.message, latency_ms: 0 }
  }
}

/**
 * Call multiple brain actions in sequence.
 * @param {Array<{domain: string, action: string, payload?: object}>} steps
 * @returns {Promise<Array>}
 */
export async function brainOrchestrate(steps) {
  try {
    const response = await fetch(`${BASE}/brain/orchestrate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ steps }),
    })
    return await response.json()
  } catch (err) {
    return { error: err.message, steps: [], total: 0 }
  }
}

/**
 * Get the brain directory (all domains and actions).
 * @returns {Promise<object>}
 */
export async function brainDirectory() {
  try {
    const response = await fetch(`${BASE}/brain/directory`)
    return await response.json()
  } catch (err) {
    return { error: err.message }
  }
}

/**
 * React hook for brain calls.
 * @param {string} domain - Brain domain
 * @param {string} action - Action name
 * @param {boolean} autoFetch - Fetch on mount (default: false)
 */
export function useBrain(domain, action, autoFetch = false) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const call = useCallback(async (payload = {}) => {
    setLoading(true)
    setError(null)
    const result = await brainCall(domain, action, payload)
    setLoading(false)
    if (result.ok) {
      setData(result.data)
    } else {
      setError(result.error)
    }
    return result
  }, [domain, action])

  // Auto-fetch on mount
  if (autoFetch && !data && !loading && !error) {
    call()
  }

  return { data, loading, error, call }
}

/**
 * Simple health check.
 */
export async function healthCheck() {
  try {
    const r = await fetch(`${BASE}/health`)
    return await r.json()
  } catch {
    return null
  }
}

export default { brainCall, brainOrchestrate, brainDirectory, useBrain, healthCheck }
