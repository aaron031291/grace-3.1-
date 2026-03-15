/**
 * useOrchestrator — Real-time system state via WebSocket.
 *
 * Connects to /api/orchestrator/ws and pushes state changes
 * into the Zustand useSystemStore, eliminating polling.
 *
 * Usage:
 *   import { useOrchestrator } from '../hooks/useOrchestrator';
 *   // In App.jsx or a top-level provider:
 *   useOrchestrator();  // connects once, updates store globally
 */

import { useEffect, useRef, useCallback } from 'react';
import { useSystemStore } from '../store';
import { API_BASE_URL } from '../config/api';

const RECONNECT_BASE_DELAY = 1000;
const RECONNECT_MAX_DELAY = 30000;

export function useOrchestrator() {
  const wsRef = useRef(null);
  const reconnectDelay = useRef(RECONNECT_BASE_DELAY);
  const mountedRef = useRef(true);

  const setSystemHealth = useSystemStore((s) => s.setSystemHealth);
  const setWsConnected = useSystemStore((s) => s.setWsConnected);
  const addServerNotification = useSystemStore((s) => s.addServerNotification);
  const updateServiceStatus = useSystemStore((s) => s.updateServiceStatus);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const base = API_BASE_URL || window.location.origin;
    const wsUrl = base.replace(/^http/, 'ws') + '/api/orchestrator/ws';

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectDelay.current = RECONNECT_BASE_DELAY;
      setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === 'state_snapshot' && msg.state) {
          // Update system health from orchestrator state
          const s = msg.state;
          setSystemHealth({
            status: s.summary?.error > 0 ? 'degraded' : 'healthy',
            components: s.components || {},
            summary: s.summary || {},
            activeTasks: s.active_tasks || 0,
            lastSync: s.ts,
          });

          // Update individual service statuses
          const comps = s.components || {};
          if (comps.llm) updateServiceStatus('ollama', comps.llm.status || 'unknown');
          if (comps.memory) updateServiceStatus('database', comps.memory.status || 'unknown');
          if (comps.flash_cache) updateServiceStatus('qdrant', comps.flash_cache.status || 'unknown');
        }

        if (msg.type === 'event') {
          // Push significant events as server notifications
          const topic = msg.topic || '';
          if (
            topic.startsWith('healing.') ||
            topic.startsWith('consensus.') ||
            topic.startsWith('system.') ||
            topic.startsWith('trust.threshold') ||
            topic.startsWith('hallucination.')
          ) {
            addServerNotification({
              topic: msg.topic,
              data: msg.data,
              source: msg.source,
              timestamp: msg.timestamp || new Date().toISOString(),
            });
          }
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      if (mountedRef.current) {
        const delay = reconnectDelay.current;
        reconnectDelay.current = Math.min(delay * 2, RECONNECT_MAX_DELAY);
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [setSystemHealth, setWsConnected, addServerNotification, updateServiceStatus]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, [connect]);
}

export default useOrchestrator;
