import type { CellData, ZoneData, DispatchItem, RiskLevel, ConnectionStatus } from '../types';

const NAGPUR_H3_CELLS = ['8926d4b608bffff', '8926d4b6097ffff', '8926d4b6083ffff', '8926d4b608fffff'];
const ZONE_NAMES = ['Sitabuldi', 'Dharampeth', 'Mahal', 'Itwari'];

function randomRisk(): number { return Math.round(Math.random() * 100) / 100; }
function levelFromRisk(risk: number): RiskLevel {
  if (risk >= 0.7) return 'high';
  if (risk >= 0.4) return 'watch';
  if (risk > 0) return 'low';
  return 'unknown';
}

function makeCell(h3: string): CellData {
  const risk = randomRisk();
  const level = levelFromRisk(risk);
  const spread = 0.05;
  return { h3, risk, lo: Math.max(0, risk - spread), hi: Math.min(1, risk + spread), level, confidence: 0.85, imputed: false, updated_at: new Date().toISOString() };
}

function makeZones(): ZoneData[] {
  const zones: ZoneData[] = [];
  for (let i = 0; i < ZONE_NAMES.length; i++) {
    const zoneId = 'Z' + String(i + 1).padStart(2, '0');
    zones.push({ id: zoneId, name: ZONE_NAMES[i], cells: [NAGPUR_H3_CELLS[i]], polygon: [], risk: randomRisk(), lo: 0.6, hi: 0.9, confidence: 0.85 });
  }
  return zones;
}

function makeDispatches(): DispatchItem[] {
  return [
    { id: 'DISP-001', priority: 'P1', zone: 'Z07 Sitabuldi', action: 'Deploy Generator', resource: 'Gen #3', trigger: 'Outage', expected_risk_drop: 0.46, risk_after: 0.42, lo: 0.35, hi: 0.50, eta: '25 min', status: 'proposed' },
    { id: 'DISP-002', priority: 'P1', zone: 'Z12 Dharampeth', action: 'Clear Road R-14', resource: 'Crew #12', trigger: 'Road closed', expected_risk_drop: 0.44, risk_after: 0.38, lo: 0.30, hi: 0.45, eta: '18 min', status: 'approved' },
  ];
}

export function startMockStream(upsertCell: (c: CellData) => void, setZones: (z: ZoneData[]) => void, setDispatches: (d: DispatchItem[]) => void, setConnectionStatus: (s: ConnectionStatus) => void, setLastUpdateTime: (t: string) => void) {
  setConnectionStatus('live');
  setZones(makeZones());
  setDispatches(makeDispatches());
  NAGPUR_H3_CELLS.forEach((h3) => upsertCell(makeCell(h3)));
  setInterval(() => {
    const h3 = NAGPUR_H3_CELLS[Math.floor(Math.random() * NAGPUR_H3_CELLS.length)];
    upsertCell(makeCell(h3));
    setLastUpdateTime(new Date().toLocaleTimeString());
  }, 3000);
}
