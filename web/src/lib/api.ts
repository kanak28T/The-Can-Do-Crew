import type { CellData, ZoneData, DispatchItem, Scenario, PrivacyRedTeam, EvalSummary } from '../types';

/**
 * In dev (Vite proxy): VITE_API_URL is set to http://localhost:8000 but calls
 * use relative paths (/api/*) which Vite proxies to http://localhost:8000/api/*
 *
 * In production: set VITE_API_URL=https://your-backend.com — same /api/* paths apply.
 *
 * Backend serves all frontend endpoints at /api/* directly.
 */
const _BASE = (import.meta as any).env.VITE_API_URL as string | undefined;

// In dev, use relative paths so Vite proxy handles CORS.
// In prod (when served from a different origin), use the full URL.
const API = _BASE && !_BASE.includes('localhost') ? _BASE : '';

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error('API ' + res.status + ': ' + path);
  return res.json();
}

async function postJSON<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error('API ' + res.status + ': ' + path);
  return res.json();
}

export const api = {
  // Zones & cells
  getCells:      (bbox?: string) => fetchJSON<CellData[]>('/api/cells' + (bbox ? '?bbox=' + bbox : '')),
  getZones:      ()              => fetchJSON<ZoneData[]>('/api/zones'),
  getZone:       (id: string)    => fetchJSON<ZoneData & { drivers: ZoneData['drivers']; actions: ZoneData['actions'] }>('/api/zones/' + id),
  getCellDetail: (h3: string)    => fetchJSON<any>('/cell/' + h3),

  // What-if analysis
  postWhatIf: (zone_id: string, change: string) =>
    postJSON<{ risk_before: number; risk_after: number; lo: number; hi: number }>('/api/whatif', { zone_id, change }),

  // Dispatch
  getDispatch:     ()           => fetchJSON<DispatchItem[]>('/api/dispatch'),
  approveDispatch: (id: string) => postJSON<any>('/api/dispatch/' + id + '/approve'),
  rejectDispatch:  (id: string) => postJSON<any>('/api/dispatch/' + id + '/reject'),

  // Scenarios
  getScenarios: () => fetchJSON<Scenario[]>('/api/scenarios'),

  // Simulation control
  simStart:    ()                               => postJSON<any>('/api/sim/start'),
  simPause:    ()                               => postJSON<any>('/api/sim/pause'),
  simReset:    ()                               => postJSON<any>('/api/sim/reset'),
  simFeedLoss: (pct: number, pattern: string)   => postJSON<any>('/api/sim/feed-loss', { pct, pattern }),

  // Privacy & eval
  getPrivacyRedTeam: () => fetchJSON<PrivacyRedTeam>('/api/privacy/redteam'),
  getEvalSummary:    () => fetchJSON<EvalSummary[]>('/api/eval/summary'),

  // Health
  health:      () => fetchJSON<any>('/health'),
  healthFeeds: () => fetchJSON<any>('/health/feeds'),
};

// SSE URL — relative path in dev, Vite proxy forwards to backend
export const SSE_URL = '/sse/events';
