# UrbanPulse Frontend - Progress Report

**Branch:** `ashlesha`  
**Last commit:** `499ddd5`  
**Date:** 26 Oct 2024

---

## DONE

### 1. Stack migrated (JSX to TypeScript)

Before: JavaScript .jsx, plain CSS, useState only
After: TypeScript .tsx, Tailwind CSS v3, Zustand + TanStack Query

New packages: typescript, zustand, @tanstack/react-query, recharts, reactflow, tailwindcss@3, postcss, autoprefixer

---

### 2. Config files created

- web/tsconfig.json - TypeScript strict ESNext
- web/tsconfig.node.json - TS config for vite
- web/vite.config.ts - Vite + worker.format:es for MapLibre
- web/tailwind.config.js - full design-token colour palette
- web/postcss.config.js - tailwindcss + autoprefixer
- web/.env - VITE_API_URL + VITE_USE_MOCK
- web/index.html - points to main.tsx, loads IBM Plex Sans font

---

### 3. Types - web/src/types/index.ts

Defines: CellData, ZoneData, DispatchItem, Driver, RecommendedAction
Scenario, FeedStatus, PrivacyRedTeam, EvalSummary
RiskLevel union: low|watch|high|unknown
ConnectionStatus union: live|reconnecting|offline

---

### 4. Zustand store - web/src/store/useAppStore.ts

Slices:
- Theme: light (default) / dark, toggleTheme()
- Connection: connectionStatus, lastUpdateTime
- Selection: selectedZoneId, selectedCellH3
- Map: activeLayer (risk/roads/hospitals/feed_coverage)
- Live numbers: highZones, watchZones, unknownCells, eventDelay
- Dock: dockCollapsed, dockTab (dispatch/causal/privacy/evaluation)
- Simulation: simRunning, simPaused, simSpeed, feedCutPct, lossPattern
- Data: cells Map, zones[], dispatches[]
- What-if: whatIfResult

---

### 5. API client - web/src/lib/api.ts

Typed fetch wrappers for all backend endpoints:
- GET /api/cells?bbox= -> getCells()
- GET /api/zones -> getZones()
- GET /api/zones/{id} -> getZone(id)
- POST /api/whatif -> postWhatIf(zone_id, change)
- GET /api/dispatch -> getDispatch()
- POST /api/dispatch/{id}/approve
- POST /api/dispatch/{id}/reject
- GET /api/scenarios
- POST /api/sim/start, /pause, /reset
- POST /api/sim/feed-loss {pct, pattern}
- GET /api/privacy/redteam
- GET /api/eval/summary

---

### 6. Mock stream - web/src/lib/mockStream.ts

- Seeds 4 Nagpur H3 cells + 4 named zones (Sitabuldi, Dharampeth, Mahal, Itwari)
- Seeds 2 dispatch items (P1 generator, P1 road clearance)
- Updates a random cell every 3 seconds with new risk values
- Used when VITE_USE_MOCK=true

---

### 7. SSE hook - web/src/hooks/useSSE.ts

- Mock mode: calls startMockStream()
- Real mode: EventSource to API_BASE + /api/stream
- Handles: cell_update, zone_update, dispatch_update, feed_status, heartbeat
- Sets connectionStatus: live / reconnecting / offline
- Reconnects on error (5s delay)

---

### 8. Components built

| Component | File | What it does |
|---|---|---|
| Header | Header.tsx | Logo, status pill, last-update time, SIMULATION badge, theme toggle |
| Left rail | LeftRail.tsx | Stress console (Start/Pause/Reset, speed, feed-cut slider, loss pattern) + Live numbers KPI grid |
| Live numbers | LiveNumbers.tsx | 2x2 KPI tiles: High zones, Watch zones, Unknown cells, Event delay |
| Map | MapView.tsx | MapLibre GL + H3 res-9 fill + outline layers, click to select cell, legend, layer toggle |
| Right panel | RightPanel.tsx | Zone name, risk%, range, confidence, driver bars, what-if, recommended actions |
| Vulnerability grid | VulnerabilityGrid.tsx | 12x8 heatmap grid: red=critical, amber=elevated, green=normal |

---

### 9. Layout - web/src/App.tsx

CSS Grid:
  columns: 280px left rail | 1fr map | 360px right panel
  rows:    56px header | 1fr main
  gap: 16px, padding: 16px

---

### 10. Design tokens - web/src/index.css

Light theme (default :root):
  page #F8F9FA, surface #FFFFFF, raised #F1F3F5, border #DEE2E6
  text #212529, secondary #495057, muted #6C757D, accent #0D6EFD
  low #198754, watch #FFC107, high #DC3545, unknown #6C757D

Dark theme (:root.dark):
  page #0F1720, surface #151F2B, raised #1B2735, border #2A3849
  text #E6EDF3, secondary #9FB0C0, muted #7F90A3, accent #6CA6E0
  low #5FA8A0, watch #E3B341, high #E8704F, unknown #8A97A6

---

### 11. Old files deleted

- web/src/App.jsx + App.css
- web/src/main.jsx
- web/vite.config.js
- web/src/components/Map.jsx/.css
- web/src/components/SectorPanel.jsx/.css
- web/src/components/DispatchLog.jsx/.css
- web/src/components/StressConsole.jsx/.css
- web/src/components/PrivacyPanel.jsx/.css

---

## NOT DONE YET

| Feature | Status |
|---|---|
| Bottom dock - Dispatch log table with Approve/Reject | Not built |
| Causal graph (React Flow) | Not built |
| Privacy red-team chart (Recharts) | Not built |
| Evaluation IoU chart | Not built |
| Feed status card in left rail | Not built |
| Real SSE ring-buffer reconnect | Simplified only |
| Map H3 res-8 to res-9 zoom switching | Static res-9 only |
| Map hospital icons | Not built |
| Map closed-road dashed lines | Not built |
| Background Unsplash photo | Not downloaded |
| Cover/splash screen | Not built |
| Keyboard navigation on map | Not built |
| Screen-reader table view | Not built |
| Wire GET /api/zones/{id} to right panel | Mock data only |
| Wire POST /api/whatif | Mock text only |

---

## How to run

### Mock mode (no backend needed)

    cd web
    npm install
    npm run dev
    # open http://localhost:5173

web/.env must have VITE_USE_MOCK=true

### Real backend mode

    # terminal 1
    uvicorn api.main:app --reload

    # terminal 2
    cd web
    # set VITE_USE_MOCK=false in web/.env
    npm run dev

---

## API keys needed

None. OpenFreeMap tiles are free, no key required.

---

*Last updated: 26 Oct 2024 - ashlesha branch*

