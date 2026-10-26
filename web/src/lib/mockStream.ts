import type { CellData, ZoneData, DispatchItem, RiskLevel, ConnectionStatus } from '../types';

const NAGPUR_H3_CELLS = ['8926d4b608bffff', '8926d4b6097ffff', '8926d4b6083ffff', '8926d4b608fffff'];

const ZONE_DATA: ZoneData[] = [
  {
    id: 'Z01',
    name: 'Prabhag 12 (Sitabuldi Central)',
    cells: ['89609610037ffff', '896096101c7ffff'],
    polygon: [],
    risk: 0.88,
    lo: 0.65,
    hi: 0.92,
    confidence: 0.85,
    drivers: [
      { key: 'power', label: 'Feeder F-12 low voltage', delta: 0.22, evidence: 'Voltage drop -35% from substation' },
      { key: 'road', label: 'Road R-14 closed', delta: 0.18, evidence: 'Bus route 4 suspended, transit isolated' },
      { key: 'health', label: 'Distance to clinic > 2.2km', delta: 0.10, evidence: 'Nearest clinic closed for repairs' },
    ],
    actions: [
      { action: 'Deploy mobile generator to Substation C', risk_after: 0.44, lo: 0.35, hi: 0.50 },
      { action: 'Reroute Bus Route 4 via NH-7', risk_after: 0.52, lo: 0.44, hi: 0.60 },
    ],
  },
  {
    id: 'Z02',
    name: 'Prabhag 7 (Dhantoli East)',
    cells: ['89609610157ffff'],
    polygon: [],
    risk: 0.76,
    lo: 0.58,
    hi: 0.84,
    confidence: 0.80,
    drivers: [
      { key: 'health', label: 'Hospital isolation risk', delta: 0.25, evidence: 'Corridor congestion exceeds 80%' },
      { key: 'water', label: 'Booster pump failure', delta: 0.15, evidence: 'Pressure drop on Wardha main' },
    ],
    actions: [
      { action: 'Dispatch MSEDCL Mobile DG #03', risk_after: 0.38, lo: 0.32, hi: 0.45 },
    ],
  },
  {
    id: 'Z03',
    name: 'Prabhag 18 (Gandhibagh)',
    cells: ['8926d4b6083ffff'],
    polygon: [],
    risk: 0.62,
    lo: 0.48,
    hi: 0.71,
    confidence: 0.78,
    drivers: [
      { key: 'water', label: 'Water supply disruption', delta: 0.20, evidence: 'Main pipeline pressure failure' },
      { key: 'comms', label: 'Tower load surge', delta: 0.12, evidence: '30% packet loss on BTS-14' },
    ],
    actions: [
      { action: 'Water tanker diversion to community taps', risk_after: 0.51, lo: 0.46, hi: 0.58 },
    ],
  },
  {
    id: 'Z04',
    name: 'Prabhag 24 (Sadar West)',
    cells: ['8926d4b608fffff'],
    polygon: [],
    risk: 0.45,
    lo: 0.32,
    hi: 0.54,
    confidence: 0.82,
    drivers: [
      { key: 'comms', label: 'Cellular congestion spike', delta: 0.15, evidence: 'Tower load at 95% capacity' },
    ],
    actions: [
      { action: 'Cellular COW pre-positioning', risk_after: 0.31, lo: 0.26, hi: 0.37 },
    ],
  },
];

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

function makeDispatches(): DispatchItem[] {
  return [
    { id: 'DISP-001', priority: 'P1', zone: 'Prabhag 12 (Sitabuldi Central)', action: 'Reroute Bus Route 4 & deploy feeder transit', resource: 'NMC Transit #14', trigger: 'Transit frequency deficit (-42%)', expected_risk_drop: 0.28, risk_after: 0.44, lo: 0.38, hi: 0.51, eta: '12 mins', status: 'proposed' },
    { id: 'DISP-002', priority: 'P1', zone: 'Prabhag 7 (Dhantoli East)', action: 'Dispatch mobile diesel generator to Substation C', resource: 'MSEDCL Mobile DG #03', trigger: 'Voltage sag below 190V', expected_risk_drop: 0.35, risk_after: 0.38, lo: 0.32, hi: 0.45, eta: '18 mins', status: 'proposed' },
    { id: 'DISP-003', priority: 'P2', zone: 'Prabhag 18 (Gandhibagh)', action: 'Water tanker diversion to community taps', resource: 'OCW Tanker #08', trigger: 'Booster pump pressure failure', expected_risk_drop: 0.22, risk_after: 0.51, lo: 0.46, hi: 0.58, eta: '25 mins', status: 'approved' },
    { id: 'DISP-004', priority: 'P3', zone: 'Prabhag 24 (Sadar West)', action: 'Cellular COW (Cell On Wheels) pre-positioning', resource: 'Telecom COW #02', trigger: 'Tower load surge + 30% packet loss', expected_risk_drop: 0.15, risk_after: 0.31, lo: 0.26, hi: 0.37, eta: '40 mins', status: 'proposed' },
  ];
}

export function startMockStream(upsertCell: (c: CellData) => void, setZones: (z: ZoneData[]) => void, setDispatches: (d: DispatchItem[]) => void, setConnectionStatus: (s: ConnectionStatus) => void, setLastUpdateTime: (t: string) => void) {
  setConnectionStatus('live');
  setZones(ZONE_DATA);
  setDispatches(makeDispatches());
  NAGPUR_H3_CELLS.forEach((h3) => upsertCell(makeCell(h3)));
  setInterval(() => {
    const h3 = NAGPUR_H3_CELLS[Math.floor(Math.random() * NAGPUR_H3_CELLS.length)];
    upsertCell(makeCell(h3));
    setLastUpdateTime(new Date().toLocaleTimeString());
  }, 3000);
}
