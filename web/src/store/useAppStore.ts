import { create } from 'zustand';
import type { CellData, ZoneData, DispatchItem, ConnectionStatus, InterventionLogEntry } from '../types';

interface AppState {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  connectionStatus: ConnectionStatus;
  setConnectionStatus: (s: ConnectionStatus) => void;
  lastUpdateTime: string | null;
  setLastUpdateTime: (t: string) => void;

  selectedZoneId: string | null;
  setSelectedZoneId: (id: string | null) => void;
  selectedCellH3: string | null;
  setSelectedCellH3: (h3: string | null) => void;

  activeLayer: 'risk' | 'roads' | 'hospitals' | 'feed_coverage';
  setActiveLayer: (l: 'risk' | 'roads' | 'hospitals' | 'feed_coverage') => void;

  highZones: number;
  watchZones: number;
  unknownCells: number;
  eventDelay: number;
  setLiveNumbers: (h: number, w: number, u: number, d: number) => void;

  dockCollapsed: boolean;
  toggleDock: () => void;
  dockTab: 'dispatch' | 'causal' | 'privacy' | 'evaluation';
  setDockTab: (t: 'dispatch' | 'causal' | 'privacy' | 'evaluation') => void;

  simRunning: boolean;
  simPaused: boolean;
  simSpeed: number;
  feedCutPct: number;
  lossPattern: 'random' | 'domain' | 'area';
  selectedScenario: string | null;
  setSimRunning: (v: boolean) => void;
  setSimPaused: (v: boolean) => void;
  setSimSpeed: (v: number) => void;
  setFeedCutPct: (v: number) => void;
  setLossPattern: (p: 'random' | 'domain' | 'area') => void;
  setSelectedScenario: (id: string | null) => void;

  cells: Map<string, CellData>;
  upsertCell: (cell: CellData) => void;
  zones: ZoneData[];
  setZones: (z: ZoneData[]) => void;
  dispatches: DispatchItem[];
  setDispatches: (d: DispatchItem[]) => void;
  updateDispatchStatus: (id: string, status: DispatchItem['status']) => void;

  whatIfResult: { risk_before: number; risk_after: number; lo: number; hi: number } | null;
  setWhatIfResult: (r: { risk_before: number; risk_after: number; lo: number; hi: number } | null) => void;

  // Intervention audit log
  interventionLog: InterventionLogEntry[];
  addInterventionLog: (entry: InterventionLogEntry) => void;
  clearInterventionLog: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  theme: 'light',
  toggleTheme: () => set((s) => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),
  connectionStatus: 'reconnecting',
  setConnectionStatus: (s) => set({ connectionStatus: s }),
  lastUpdateTime: null,
  setLastUpdateTime: (t) => set({ lastUpdateTime: t }),

  selectedZoneId: null,
  setSelectedZoneId: (id) => set({ selectedZoneId: id }),
  selectedCellH3: null,
  setSelectedCellH3: (h3) => set({ selectedCellH3: h3 }),

  activeLayer: 'risk',
  setActiveLayer: (l) => set({ activeLayer: l }),

  highZones: 0,
  watchZones: 0,
  unknownCells: 0,
  eventDelay: 0,
  setLiveNumbers: (h, w, u, d) => set({ highZones: h, watchZones: w, unknownCells: u, eventDelay: d }),

  dockCollapsed: false,
  toggleDock: () => set((s) => ({ dockCollapsed: !s.dockCollapsed })),
  dockTab: 'dispatch',
  setDockTab: (t) => set({ dockTab: t }),

  simRunning: false,
  simPaused: false,
  simSpeed: 1,
  feedCutPct: 0,
  lossPattern: 'random',
  selectedScenario: null,
  setSimRunning: (v) => set({ simRunning: v }),
  setSimPaused: (v) => set({ simPaused: v }),
  setSimSpeed: (v) => set({ simSpeed: v }),
  setFeedCutPct: (v) => set({ feedCutPct: v }),
  setLossPattern: (p) => set({ lossPattern: p }),
  setSelectedScenario: (id) => set({ selectedScenario: id }),

  cells: new Map(),
  upsertCell: (cell) => set((s) => {
    const cells = new Map(s.cells);
    cells.set(cell.h3, cell);
    return { cells };
  }),
  zones: [],
  setZones: (z) => set({ zones: z }),
  dispatches: [],
  setDispatches: (d) => set({ dispatches: d }),
  updateDispatchStatus: (id, status) => set((s) => ({
    dispatches: s.dispatches.map((d) => d.id === id ? { ...d, status } : d),
  })),

  whatIfResult: null,
  setWhatIfResult: (r) => set({ whatIfResult: r }),

  interventionLog: [],
  addInterventionLog: (entry) => set((s) => ({ interventionLog: [entry, ...s.interventionLog] })),
  clearInterventionLog: () => set({ interventionLog: [] }),
}));
