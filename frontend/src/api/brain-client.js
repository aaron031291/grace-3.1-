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

import { API_BASE_URL } from '../config/api'
const BASE = API_BASE_URL

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

    let result
    try {
      result = await response.json()
    } catch (_) {
      return {
        ok: false,
        data: null,
        error: response.ok ? 'Invalid response' : `Request failed (${response.status})`,
        latency_ms: 0,
      }
    }
    const ok = result.ok ?? response.ok
    let errorMsg = result.error ?? null
    if (!errorMsg && result.detail != null) {
      errorMsg = Array.isArray(result.detail) ? result.detail.map(d => d.msg || d).join('; ') : String(result.detail)
    }
    if (!errorMsg && !ok) errorMsg = `Request failed (${response.status})`
    return {
      ok: !!ok,
      data: result.data ?? result,
      error: errorMsg,
      latency_ms: result.latency_ms ?? 0,
      genesis_key_id: result.genesis_key_id ?? null,
    }
  } catch (err) {
    const raw = err.message || 'Network error'
    const isNetwork = /failed to fetch|networkerror|network error|load failed|connection refused|econnrefused/i.test(raw)
    const error = isNetwork
      ? `Backend unreachable. Is the Grace backend running on port 8000? Start it (e.g. run_backend.bat or: cd backend && python -m uvicorn app:app --reload --port 8000), then try again. (${raw})`
      : raw
    return { ok: false, data: null, error, latency_ms: 0 }
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
    const raw = err.message || 'Network error'
    const isNetwork = /failed to fetch|networkerror|network error|load failed|connection refused|econnrefused/i.test(raw)
    const error = isNetwork
      ? `Backend unreachable. Start the Grace backend (e.g. run_backend.bat on port 8000), then try again. (${raw})`
      : raw
    return { error, steps: [], total: 0 }
  }
}

/**
 * Ask in natural language — routes to best brain + action (e.g. "what embedding model?", "trace path from pipeline to trust_engine").
 * @param {string} query - Natural language question or request
 * @param {object} payload - Optional extra payload for the routed action
 * @returns {Promise<{ok: boolean, data: any, error: string|null, routing?: object}>}
 */
export async function brainAsk(query, payload = {}) {
  try {
    const response = await fetch(`${BASE}/brain/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, payload }),
    })
    const result = await response.json().catch(() => ({}))
    const ok = result.ok ?? response.ok
    let errorMsg = result.error ?? null
    if (!errorMsg && result.detail != null) {
      errorMsg = Array.isArray(result.detail) ? result.detail.map(d => d.msg || d).join('; ') : String(result.detail)
    }
    if (!errorMsg && !ok) errorMsg = `Request failed (${response.status})`
    return {
      ok: !!ok,
      data: result.data ?? result,
      error: errorMsg,
      routing: result.routing ?? null,
    }
  } catch (err) {
    const raw = err.message || 'Network error'
    const isNetwork = /failed to fetch|networkerror|network error|load failed|connection refused|econnrefused/i.test(raw)
    const error = isNetwork
      ? `Backend unreachable. Is the Grace backend running on port 8000? Start it (e.g. run_backend.bat), then try again. (${raw})`
      : raw
    return { ok: false, data: null, error, routing: null }
  }
}

/**
 * Get the brain directory (all domains and actions).
 * @returns {Promise<object>}
 */
export async function brainDirectory() {
  try {
    const response = await fetch(`${BASE}/brain/directory`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      return { ok: false, error: data.detail || data.error || `Request failed (${response.status})`, brains: null, total_brains: 0 }
    }
    return {
      ok: true,
      brains: data.brains || {},
      total_brains: data.total_brains ?? 0,
      total_actions: data.total_actions ?? 0,
      error: null,
    }
  } catch (err) {
    const raw = err.message || 'Network error'
    const isNetwork = /failed to fetch|networkerror|network error|load failed|connection refused|econnrefused/i.test(raw)
    const error = isNetwork
      ? `Backend unreachable. Is the Grace backend running on port 8000? Start it (e.g. run_backend.bat), then try again. (${raw})`
      : raw
    return { ok: false, error, brains: null, total_brains: 0 }
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
 * Returns normalized { status, llm_running } so UI shows Connected whenever backend is reachable (2xx).
 */
export async function healthCheck() {
  try {
    const r = await fetch(`${BASE}/health`)
    let data = null
    try {
      data = await r.json()
    } catch (_) {
      data = {}
    }
    if (!r.ok) return null
    return {
      status: (data && data.status) || (r.ok ? 'healthy' : 'unhealthy'),
      llm_running: data && 'llm_running' in data ? data.llm_running : r.ok,
      ...data
    }
  } catch (err) {
    return null
  }
}

export default { brainCall, brainOrchestrate, brainAsk, brainDirectory, useBrain, healthCheck }
