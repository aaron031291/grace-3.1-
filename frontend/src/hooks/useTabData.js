/**
 * useTabData — React hook for fetching + validating tab API responses.
 *
 * Uses lightweight runtime validation against an expected shape.
 * On schema mismatch: fills defaults + logs structured warning.
 * On network error: returns last good data + error state.
 *
 * Usage:
 *   const { data, loading, error, refresh } = useTabData('/api/bi/dashboard', BI_DASHBOARD_SCHEMA);
 *   const { data } = useTabData('/api/system-health/dashboard', HEALTH_SCHEMA, { poll: 10000 });
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '../config/api';
import { graceFetch } from '../api/graceFetch';

/**
 * Validate data against a schema shape and fill in defaults for missing fields.
 * Schema is a plain object where keys map to default values.
 *
 * Example schema:
 *   { uptime: { days: 0, hours: 0 }, documents: { total: 0 } }
 *
 * Returns { validated, warnings } where validated has all keys filled.
 */
function validateAndFill(data, schema, path = '') {
  if (!schema || typeof schema !== 'object') return { validated: data, warnings: [] };
  if (!data || typeof data !== 'object') {
    return { validated: structuredClone(schema), warnings: [`${path || 'root'}: expected object, got ${typeof data}`] };
  }

  const warnings = [];
  const validated = Array.isArray(schema) ? (Array.isArray(data) ? data : []) : {};

  if (Array.isArray(schema)) {
    return { validated: Array.isArray(data) ? data : [], warnings: Array.isArray(data) ? [] : [`${path}: expected array`] };
  }

  for (const key of Object.keys(schema)) {
    const fullPath = path ? `${path}.${key}` : key;
    const defaultVal = schema[key];
    const actual = data[key];

    if (actual === undefined || actual === null) {
      warnings.push(`${fullPath}: missing, using default`);
      validated[key] = structuredClone(defaultVal);
    } else if (typeof defaultVal === 'object' && !Array.isArray(defaultVal) && defaultVal !== null) {
      const nested = validateAndFill(actual, defaultVal, fullPath);
      validated[key] = nested.validated;
      warnings.push(...nested.warnings);
    } else {
      validated[key] = actual;
    }
  }

  // Pass through extra keys from data that aren't in schema (forward-compat)
  for (const key of Object.keys(data)) {
    if (!(key in validated)) {
      validated[key] = data[key];
    }
  }

  return { validated, warnings };
}

/**
 * @param {string} endpoint - API path (e.g. '/api/bi/dashboard')
 * @param {Object} schema - Expected shape with default values
 * @param {Object} [options]
 * @param {number} [options.poll] - Polling interval in ms (0 = no polling)
 * @param {number} [options.timeout] - Fetch timeout in ms (default 15000)
 * @param {boolean} [options.eager] - Fetch immediately on mount (default true)
 */
export function useTabData(endpoint, schema = null, options = {}) {
  const { poll = 0, timeout = 15000, eager = true } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(eager);
  const [error, setError] = useState(null);
  const lastGoodRef = useRef(null);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    if (!mountedRef.current) return;
    setLoading(true);
    setError(null);

    try {
      const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
      const res = await graceFetch(url, { timeout });

      if (!res.ok) {
        throw new Error(`API ${res.status}: ${res.statusText}`);
      }

      let json = await res.json();

      // Runtime validation
      if (schema) {
        const { validated, warnings } = validateAndFill(json, schema);
        if (warnings.length > 0) {
          console.warn(`[useTabData] ${endpoint} schema warnings:`, warnings);
        }
        json = validated;
      }

      if (mountedRef.current) {
        lastGoodRef.current = json;
        setData(json);
        setLoading(false);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err.message);
        // Keep last good data visible instead of blank screen
        if (lastGoodRef.current) {
          setData(lastGoodRef.current);
        } else if (schema) {
          // First load failed — use schema defaults so UI has something
          setData(structuredClone(schema));
        }
        setLoading(false);
      }
    }
  }, [endpoint, schema, timeout]);

  useEffect(() => {
    mountedRef.current = true;
    if (eager) refresh();
    return () => { mountedRef.current = false; };
  }, [refresh, eager]);

  // Polling
  useEffect(() => {
    if (!poll || poll <= 0) return;
    const id = setInterval(() => {
      if (!document.hidden) refresh();
    }, poll);
    return () => clearInterval(id);
  }, [poll, refresh]);

  return { data, loading, error, refresh };
}


// ==================== Pre-built schemas for each tab ====================
// These mirror the Pydantic models in backend/api/tab_schemas.py

export const BI_DASHBOARD_SCHEMA = {
  uptime: { days: 0, hours: 0 },
  documents: { total: 0, total_size_mb: 0, growth: 'flat', this_week: 0, avg_confidence: 0 },
  chats: { total_chats: 0, total_messages: 0, avg_per_chat: 0 },
  genesis_keys: { total: 0, today: 0, error_rate: 0 },
  learning: { examples: 0, skills: 0, avg_trust: 0 },
  tasks: { total: 0, by_status: { completed: 0, active: 0, failed: 0 } },
};

export const BI_TRENDS_SCHEMA = {
  days: [],
};

export const ORACLE_DASHBOARD_SCHEMA = {
  learning_examples: { total: 0, avg_trust: 0 },
  learning_patterns: { total: 0, avg_success_rate: 0 },
  procedures: { total: 0, avg_success_rate: 0 },
  episodes: { total: 0, avg_trust: 0 },
  documents: { total: 0, total_chunks: 0 },
  vector_store: { vectors: 0 },
  federated: { status: 'unavailable', nodes: 0, rounds: 0 },
};

export const LEARN_HEAL_DASHBOARD_SCHEMA = {
  health_snapshot: { status: 'unknown', cpu: 0, memory: 0 },
  learning: {
    examples: { total: 0, avg_trust: 0 },
    patterns: { total: 0, avg_success: 0 },
    procedures: { total: 0, avg_success: 0 },
    episodes: 0,
    last_24h: 0,
    trust_distribution: {},
    top_types: [],
  },
  healing: { available_actions: [] },
};

export const SKILLS_SCHEMA = {
  skills: [],
};

export const SYSTEM_HEALTH_SCHEMA = {
  overall: 'unknown',
  resources: {
    cpu_total: 0, cpu_per_core: [], cpu_cores: 0,
    memory_percent: 0, memory_used_gb: 0, memory_total_gb: 0,
    disk_percent: 0, disk_used_gb: 0, disk_total_gb: 0,
  },
  services: {
    api: { status: 'unknown' },
    database: { status: 'unknown' },
    qdrant: { status: 'unknown' },
    ollama: { status: 'unknown' },
    ml_engine: { status: 'unknown' },
  },
  organs: [],
};

export const GOVERNANCE_STATS_SCHEMA = { status: 'ok' };
export const GOVERNANCE_RULES_SCHEMA = { rules: [] };
export const GOVERNANCE_DECISIONS_SCHEMA = { decisions: [] };
export const GOVERNANCE_PILLARS_SCHEMA = { pillars: [] };

export const COGNITIVE_STATS_SCHEMA = { status: 'ok', stats: {} };
export const COGNITIVE_DECISIONS_SCHEMA = { decisions: [] };

export default useTabData;
