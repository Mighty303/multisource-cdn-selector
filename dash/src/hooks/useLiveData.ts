import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Camera, ServerNode, IncidentEntry, Algorithm,
  initialCameras, initialServers, initialIncidents,
  randomVariation,
} from '@/lib/mockData';
import {
  fetchSelectorLogs,
  fetchSelectorStatus,
  setSelectorMode,
  simulateOriginFailure,
  MODE_TO_ALGORITHM,
  type SelectorLogEvent,
} from '@/lib/selectorApi';

export function useLiveData() {
  const [cameras] = useState<Camera[]>(initialCameras);
  const [servers, setServers] = useState<ServerNode[]>(initialServers);
  const [incidents, setIncidents] = useState<IncidentEntry[]>(initialIncidents);
  const [algorithm, setAlgorithmState] = useState<Algorithm>('Latency Weighted');
  const [systemStatus, setSystemStatus] = useState<'nominal' | 'warning' | 'critical'>('nominal');
  const [expandedCamera, setExpandedCamera] = useState<string | null>(null);

  const algorithmRef = useRef<Algorithm>('Latency Weighted');
  const lastSelectedIdRef = useRef<string | null>(null);
  const lastLogEventIdRef = useRef<number | null>(null);

  // Wraps the local state update with a best-effort API call to the selector
  const setAlgorithm = useCallback((value: Algorithm) => {
    setAlgorithmState(value);
    algorithmRef.current = value;
    setSelectorMode(value);
  }, []);

  const simulateFailure = useCallback((serverId: string) => {
    // Optimistic local update — real state arrives on next /api/status poll
    setServers(prev => prev.map(s =>
      s.id === serverId ? { ...s, status: 'offline' as const } : s
    ));
    setSystemStatus('warning');
    simulateOriginFailure(serverId, 8);
  }, []);

  const formatIncident = useCallback((event: SelectorLogEvent): IncidentEntry | null => {
    const timestamp = event.timestamp
      ? event.timestamp.slice(-8)
      : new Date(event.ts * 1000).toLocaleTimeString('en-US', { hour12: false });

    if (event.event_type === 'decision_redirect' && event.selected_server) {
      const metrics = event.metrics[event.selected_server];
      const rttStr = metrics?.latency_ms !== null && metrics?.latency_ms !== undefined
        ? ` RTT ${metrics.latency_ms}ms`
        : '';
      const loadStr = metrics?.load !== null && metrics?.load !== undefined
        ? ` load ${metrics.load.toFixed(2)}`
        : '';
      const serverChanged = lastSelectedIdRef.current !== null && lastSelectedIdRef.current !== event.selected_server;
      lastSelectedIdRef.current = event.selected_server;
      return {
        id: `selector-${event.event_id}`,
        timestamp,
        message: `SELECTOR → ${event.selected_server} [${event.selector_mode.replace('_', '-')}]${rttStr}${loadStr}`,
        severity: serverChanged ? 'reroute' : 'nominal',
      };
    }

    if (event.event_type === 'decision_manifest' && event.selected_server) {
      return {
        id: `selector-${event.event_id}`,
        timestamp,
        message: `MANIFEST → ${event.selected_server} [${event.selector_mode.replace('_', '-')}]`,
        severity: 'nominal',
      };
    }

    if (event.event_type === 'admin_failure' && event.selected_server) {
      return {
        id: `selector-${event.event_id}`,
        timestamp,
        message: `FAILURE injected → ${event.selected_server} for ${event.duration_seconds ?? 0}s`,
        severity: 'failure',
      };
    }

    if (event.event_type === 'mode_change') {
      return {
        id: `selector-${event.event_id}`,
        timestamp,
        message: `ALGORITHM switched → ${event.selector_mode.replace('_', '-')}`,
        severity: 'nominal',
      };
    }

    return null;
  }, []);

  // Poll the selector's /api/status every 5 s.
  useEffect(() => {
    const syncSelector = async () => {
      const status = await fetchSelectorStatus();

      if (status) {
        // --- Real selector path ---
        setServers(prev => prev.map(server => {
          const m = status.metrics[server.id];
          if (!m) return server;
          return {
            ...server,
            latency:     m.latency_ms ?? server.latency,
            connections: Math.max(0, Math.round(m.load * 10)),
            bandwidth:   m.throughput_mbps !== null ? Math.round(m.throughput_mbps) : server.bandwidth,
            status:      server.status === 'offline' ? 'offline' : m.healthy ? 'online' : 'degraded',
          };
        }));

        const mapped = MODE_TO_ALGORITHM[status.mode] as Algorithm | undefined;
        if (mapped) { setAlgorithmState(mapped); algorithmRef.current = mapped; }
      }
    };

    syncSelector();
    const pollInterval = setInterval(syncSelector, 5000);
    return () => clearInterval(pollInterval);
  }, []);

  useEffect(() => {
    const syncLogs = async () => {
      const response = await fetchSelectorLogs(100, lastLogEventIdRef.current ?? undefined);
      if (!response) return;

      lastLogEventIdRef.current = response.next_since_id;
      const mapped = response.events
        .map(formatIncident)
        .filter((entry): entry is IncidentEntry => entry !== null);

      if (mapped.length === 0) return;
      mapped.reverse();
      setIncidents(prev => [...mapped, ...prev].slice(0, 50));
    };

    syncLogs();
    const pollInterval = setInterval(syncLogs, 5000);
    return () => clearInterval(pollInterval);
  }, [formatIncident]);

  // Local animation loop: add small jitter to server metrics every 2.5 s to show liveness.
  // Only runs on fields that have been populated by the selector (non-null).
  // Camera metrics have no real source so they are not jittered.
  useEffect(() => {
    const interval = setInterval(() => {
      setServers(prev => prev.map(s => {
        if (s.status === 'offline') return s;
        return {
          ...s,
          latency:     s.latency     !== null ? Math.max(1, randomVariation(s.latency, 4))               : null,
          connections: s.connections !== null ? Math.max(0, Math.round(randomVariation(s.connections, 3))) : null,
          bandwidth:   s.bandwidth   !== null ? Math.max(0, randomVariation(s.bandwidth, 50))             : null,
          packetLoss:  s.packetLoss  !== null ? Math.max(0, randomVariation(s.packetLoss, 0.02))          : null,
        };
      }));
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  return {
    cameras, servers, incidents, algorithm, systemStatus, expandedCamera,
    setAlgorithm, simulateFailure, setExpandedCamera,
  };
}
