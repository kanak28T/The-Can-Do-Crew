# UrbanPulse Frontend Status

## ✅ WORKING NOW (Mock Mode)
- TypeScript + React + Vite setup
- Tailwind CSS with design tokens
- Zustand store for state management  
- MapLibre GL map with H3 cells visualization
- Header with theme toggle, status indicator
- Left rail: Stress console + Live numbers cards
- Right panel: Zone details
- Mock data stream (updates every 3 seconds)
- Dark theme with proper color palette

## 🔧 NEEDS BACKEND INTEGRATION
To connect to your FastAPI backend at `http://localhost:8000`, update `.env`:

```
VITE_API_URL=http://localhost:8000
VITE_USE_MOCK=false
```

### Backend Endpoints Needed:
1. **GET /api/stream** - SSE stream for real-time updates
   - Events: `cell_update`, `zone_update`, `dispatch_update`, `heartbeat`
   
2. **GET /api/zones** - Get all zones
   - Returns: `[{id, name, cells, polygon, risk, lo, hi, confidence}]`

3. **GET /api/zones/{id}** - Get zone details
   - Returns drivers and recommended actions

4. **GET /api/scenarios** - List available scenarios

5. **POST /api/sim/start** - Start simulation

6. **POST /api/sim/feed-loss** - Apply feed degradation
   - Body: `{pct: number, pattern: string}`

## 🚧 TODO (Day 3 Requirements)
1. ✅ Wire sector panel to API `GET /zones/{cell_id}`
2. ❌ Build causal graph with Cytoscape.js  
3. ❌ Build dispatch log panel
4. ❌ Complete stress console UI
5. ❌ Add SSE reconnect with ring buffer
6. ❌ Add privacy panel

## 🎯 TO RUN NOW

### Frontend (Mock Mode)
```powershell
cd web
npm run dev
```
Open: http://localhost:5173

### Backend (for real integration)
```powershell
cd ..
uvicorn api.main:app --reload
```

## 📝 API Keys Needed
**None!** System uses:
- OpenFreeMap (free, no key)
- Local H3 data files
- Mock SSE in development mode

## 🐛 Known Issues
- MapLibre worker warning (non-critical, map works fine)
- Bottom dock not implemented yet
- Causal graph pending
- Real SSE integration pending (mock works)

## Next Steps
1. Test mock mode frontend works
2. Start FastAPI backend
3. Switch to `VITE_USE_MOCK=false`
4. Verify SSE connection
5. Implement remaining Day 3 components
