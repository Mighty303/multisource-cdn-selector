// API client for the Python selector server (selector/server.py)
// Reads VITE_SELECTOR_BASE_URL from environment; falls back to no-op when unset.

export const SELECTOR_BASE_URL = (import.meta.env.VITE_SELECTOR_BASE_URL ?? '').replace(/\/$/, '');

// Shape of one origin's metrics returned by /api/status
export interface SelectorOriginMetrics {
  healthy: boolean;
  latency_ms: number | null;
  throughput_mbps: number | null;
  load: number;
  error: string | null;
}

export interface SelectorOrigin {
  id: string;
  base_url: string;
  region: string;
}

export interface SelectorDecision {
  timestamp: string;
  action: string;
  path: string;
  status: number;
  selected_server: string;
  selector_mode: string;
  decision_ms: number | null;
  score: number | null;
  target: string;
}

export interface SelectorLogEvent {
  ts: number;
  event_id: number;
  event_type: string;
  request_kind: string;
  timestamp: string;
  client_ip: string;
  method: string;
  path: string;
  action: string;
  status: number;
  selector_mode: string;
  selected_server?: string;
  target: string;
  decision_ms: number | null;
  reason: string;
  score: number | null;
  scores: Record<string, number | null>;
  metrics: Record<string, SelectorOriginMetrics>;
  duration_seconds?: number;
  previous_mode?: string;
}

export interface SelectorLogsResponse {
  events: SelectorLogEvent[];
  next_since_id: number;
}

// Full shape of GET /api/status on the selector server
export interface SelectorStatus {
  mode: string;
  public_base_url: string;
  origins: SelectorOrigin[];
  metrics: Record<string, SelectorOriginMetrics>;
  last_decision: SelectorDecision | null;
}

// Returns null when the selector is unreachable or VITE_SELECTOR_BASE_URL is unset
export async function fetchSelectorStatus(): Promise<SelectorStatus | null> {
  if (!SELECTOR_BASE_URL) return null;
  try {
    const res = await fetch(`${SELECTOR_BASE_URL}/api/status`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;
    return res.json() as Promise<SelectorStatus>;
  } catch {
    return null;
  }
}

export async function fetchSelectorLogs(limit = 100, sinceId?: number): Promise<SelectorLogsResponse | null> {
  if (!SELECTOR_BASE_URL) return null;
  try {
    const params = new URLSearchParams({ limit: String(limit) });
    if (sinceId !== undefined) params.set('since_id', String(sinceId));
    const res = await fetch(`${SELECTOR_BASE_URL}/api/logs?${params.toString()}`, {
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return null;
    return res.json() as Promise<SelectorLogsResponse>;
  } catch {
    return null;
  }
}

// Maps frontend algorithm display names to selector mode strings
const ALGORITHM_TO_MODE: Record<string, string> = {
  'Round Robin':      'round_robin',
  'Latency Weighted': 'adaptive',
  'Load Balanced':    'adaptive',
  'Random':           'random',
};

// Reverse: selector mode → nearest frontend algorithm name
export const MODE_TO_ALGORITHM: Record<string, string> = {
  round_robin: 'Round Robin',
  adaptive:    'Latency Weighted',
  random:      'Random',
};

// Best-effort: call /admin/failure on the selector to force an origin offline for a duration
export async function simulateOriginFailure(originId: string, durationSeconds = 8): Promise<void> {
  if (!SELECTOR_BASE_URL) return;
  try {
    await fetch(
      `${SELECTOR_BASE_URL}/admin/failure?origin=${originId}&duration=${durationSeconds}`,
      { signal: AbortSignal.timeout(3000) },
    );
  } catch { /* best-effort */ }
}

// Best-effort: call /admin/mode on the selector when the user switches algorithm
export async function setSelectorMode(algorithm: string): Promise<void> {
  if (!SELECTOR_BASE_URL) return;
  const mode = ALGORITHM_TO_MODE[algorithm] ?? 'adaptive';
  try {
    await fetch(`${SELECTOR_BASE_URL}/admin/mode?value=${mode}`, {
      signal: AbortSignal.timeout(3000),
    });
  } catch {
    // Network errors are ignored; the UI state already updated locally
  }
}
