/**
 * useConnectionStatus Hook
 * =========================
 * Polls the connection validation API and updates the SystemStore
 * with comprehensive connection status for all system components.
 *
 * Usage:
 *   const { report, summary, loading, refresh, isConnected } = useConnectionStatus();
 */

import { useEffect, useCallback, useRef } from 'react';
import { useSystemStore } from '../store/index';
import { API_BASE_URL } from '../config/api';

const DEFAULT_POLL_INTERVAL_MS = 30000;

export function useConnectionStatus(pollIntervalMs = DEFAULT_POLL_INTERVAL_MS) {
  const setConnectionReport = useSystemStore((s) => s.setConnectionReport);
  const setConnectionLoading = useSystemStore((s) => s.setConnectionLoading);
  const setConnectionStatuses = useSystemStore((s) => s.setConnectionStatuses);
  const setConnectionSummary = useSystemStore((s) => s.setConnectionSummary);
  const updateServiceStatus = useSystemStore((s) => s.updateServiceStatus);

  const report = useSystemStore((s) => s.connectionReport);
  const summary = useSystemStore((s) => s.connectionSummary);
  const loading = useSystemStore((s) => s.connectionLoading);
  const lastChecked = useSystemStore((s) => s.connectionLastChecked);
  const connectionStatuses = useSystemStore((s) => s.connectionStatuses);

  const timerRef = useRef(null);

  const fetchConnectionStatus = useCallback(async () => {
    setConnectionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/connections/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setConnectionReport(data);

      const statuses = {};
      for (const conn of data.connections || []) {
        statuses[conn.name] = {
          status: conn.status,
          connected: conn.connected,
          category: conn.category,
          latency_ms: conn.latency_ms,
          message: conn.message,
        };
      }
      setConnectionStatuses(statuses);

      setConnectionSummary({
        total: data.total || 0,
        connected: data.connected || 0,
        disconnected: (data.total || 0) - (data.connected || 0),
        degraded: 0,
        status: data.status || 'unknown',
      });

      if (statuses.llm_provider) {
        updateServiceStatus('ollama', statuses.llm_provider.status);
      }
      if (statuses.database) {
        updateServiceStatus('database', statuses.database.status);
      }
      if (statuses.qdrant) {
        updateServiceStatus('qdrant', statuses.qdrant.status);
      }

    } catch (err) {
      console.error('[useConnectionStatus] Failed to fetch:', err);
      setConnectionLoading(false);
    }
  }, [setConnectionReport, setConnectionLoading, setConnectionStatuses, setConnectionSummary, updateServiceStatus]);

  const fetchFullValidation = useCallback(async () => {
    setConnectionLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/connections/validate`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setConnectionReport(data);

      const statuses = {};
      for (const conn of data.connections || []) {
        statuses[conn.name] = {
          status: conn.status,
          connected: conn.connected,
          category: conn.category,
          latency_ms: conn.latency_ms,
          message: conn.message,
          actions_passing: conn.actions_passing,
          actions_failing: conn.actions_failing,
          actions_total: conn.actions_total,
          action_validations: conn.action_validations,
        };
      }
      setConnectionStatuses(statuses);

      setConnectionSummary({
        total: data.total_connections || 0,
        connected: data.connected_count || 0,
        disconnected: data.disconnected_count || 0,
        degraded: data.degraded_count || 0,
        actionsValidated: data.total_actions_validated || 0,
        actionsPassing: data.total_actions_passing || 0,
        actionsFailing: data.total_actions_failing || 0,
        status: data.status || 'unknown',
      });

    } catch (err) {
      console.error('[useConnectionStatus] Full validation failed:', err);
      setConnectionLoading(false);
    }
  }, [setConnectionReport, setConnectionLoading, setConnectionStatuses, setConnectionSummary]);

  useEffect(() => {
    fetchConnectionStatus();

    if (pollIntervalMs > 0) {
      timerRef.current = setInterval(fetchConnectionStatus, pollIntervalMs);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [fetchConnectionStatus, pollIntervalMs]);

  const isConnected = useCallback(
    (connectionName) => connectionStatuses[connectionName]?.connected ?? false,
    [connectionStatuses]
  );

  const getStatus = useCallback(
    (connectionName) => connectionStatuses[connectionName]?.status ?? 'unknown',
    [connectionStatuses]
  );

  return {
    report,
    summary,
    loading,
    lastChecked,
    connectionStatuses,
    refresh: fetchConnectionStatus,
    refreshFull: fetchFullValidation,
    isConnected,
    getStatus,
  };
}

export default useConnectionStatus;
