import type { CellData, ZoneData, DispatchItem, Scenario, PrivacyRedTeam, EvalSummary } from '../types';

const API_BASE = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error('API ' + res.status + ': ' + res.statusText);
  return res.json();
}

async function postJSON<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error('API ' + res.status + ': ' + res.statusText);
  return res.json();
}

export const api = {
  getCells: (bbox?: string) => fetchJSON<CellData[]>('/api/cells' + (bbox ? '?bbox=' + bbox : '')),
  getZones: () => fetchJSON<ZoneData[]>('/api/zones'),
  getZone: (id: string) => fetchJSON<ZoneData & { drivers: ZoneData['drivers']; actions: ZoneData['actions'] }>('/api/zones/' + id),
  postWhatIf: (zone_id: string, change: string) => postJSON<{ risk_before: number; risk_after: number; lo: number; hi: number }>('/api/whatif', { zone_id, change }),
  getDispatch: () => fetchJSON<DispatchItem[]>('/api/dispatch'),
  approveDispatch: (id: string) => postJSON('/api/dispatch/' + id + '/approve'),
  rejectDispatch: (id: string) => postJSON('/api/dispatch/' + id + '/reject'),
  getScenarios: () => fetchJSON<Scenario[]>('/api/scenarios'),
  simStart: () => postJSON('/api/sim/start'),
  simPause: () => postJSON('/api/sim/pause'),
  simReset: () => postJSON('/api/sim/reset'),
  simFeedLoss: (pct: number, pattern: string) => postJSON('/api/sim/feed-loss', { pct, pattern }),
  getPrivacyRedTeam: () => fetchJSON<PrivacyRedTeam>('/api/privacy/redteam'),
  getEvalSummary: () => fetchJSON<EvalSummary[]>('/api/eval/summary'),
};
