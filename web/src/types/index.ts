export type RiskLevel = 'low' | 'watch' | 'high' | 'unknown';

export interface CellData {
  h3: string;
  risk: number;
  lo: number;
  hi: number;
  level: RiskLevel;
  confidence: number;
  imputed: boolean;
  updated_at: string;
}

export interface Driver {
  key: string;
  label: string;
  delta: number;
  evidence: string;
}

export interface RecommendedAction {
  action: string;
  risk_after: number;
  lo: number;
  hi: number;
}

export interface ZoneData {
  id: string;
  name: string;
  cells: string[];
  polygon: number[][];
  risk: number;
  lo: number;
  hi: number;
  confidence: number;
  drivers?: Driver[];
  actions?: RecommendedAction[];
}

export interface DispatchItem {
  id: string;
  priority: 'P1' | 'P2' | 'P3';
  zone: string;
  action: string;
  resource: string;
  trigger: string;
  expected_risk_drop: number;
  risk_after: number;
  lo: number;
  hi: number;
  eta: string;
  status: 'proposed' | 'approved' | 'rejected' | 'dispatched';
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
}

export interface FeedStatus {
  domain: string;
  status: 'ok' | 'stale' | 'missing';
  lag_seconds: number | null;
}

export interface PrivacyRedTeam {
  attack_auc: number;
  iou: number;
}

export interface EvalSummary {
  scenario: string;
  iou: number;
  lo: number;
  hi: number;
}

export type ConnectionStatus = 'live' | 'reconnecting' | 'offline';
