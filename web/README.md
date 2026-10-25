# UrbanPulse Web Dashboard

Real-time crisis management dashboard for Nagpur showing community vulnerability from live city signals.

## Quick Start

```powershell
# Install dependencies
npm install

# Run in development mode (mock data)
npm run dev
```

Open http://localhost:5173

## Environment Variables

Create `.env` file:

```env
# API backend URL
VITE_API_URL=http://localhost:8000

# Mock mode (true = fake data, false = real backend)
VITE_USE_MOCK=true
```

## Mock vs Real Mode

**Mock Mode** (`VITE_USE_MOCK=true`):
- Uses simulated data
- Updates every 3 seconds
- No backend required
- Perfect for frontend development

**Real Mode** (`VITE_USE_MOCK=false`):
- Connects to FastAPI backend at `VITE_API_URL`
- Receives SSE events
- Requires backend running on port 8000

## Tech Stack

- **React 19** + **TypeScript**
- **Vite** - Build tool
- **Tailwind CSS** - Styling with design tokens
- **MapLibre GL JS** - Interactive maps
- **Zustand** - State management
- **TanStack Query** - Data fetching
- **h3-js** - Hexagonal hierarchical geospatial indexing

## Project Structure

```
web/
├── src/
│   ├── components/     # React components
│   │   ├── Header.tsx
│   │   ├── LeftRail.tsx
│   │   ├── MapView.tsx
│   │   └── RightPanel.tsx
│   ├── store/          # Zustand stores
│   │   └── useAppStore.ts
│   ├── lib/            # Utilities
│   │   ├── api.ts      # API client
│   │   └── mockStream.ts  # Mock data
│   ├── hooks/          # Custom hooks
│   │   └── useSSE.ts   # Server-Sent Events
│   ├── types/          # TypeScript types
│   │   └── index.ts
│   ├── data/           # Static data
│   │   ├── nagpur_h3_res9.json
│   │   └── nagpur_wards.json
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── index.css       # Global styles
├── public/             # Static assets
├── .env               # Environment config
└── package.json
```

## Available Scripts

- `npm run dev` - Start dev server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run linter

## Features

### Implemented
- ✅ Real-time H3 cell visualization
- ✅ Interactive map with click/hover
- ✅ Theme toggle (dark/light)
- ✅ Mock data streaming
- ✅ Stress console controls
- ✅ Live statistics dashboard
- ✅ Zone selection panel

### Pending
- ❌ Causal graph visualization
- ❌ Dispatch log table
- ❌ Privacy panel
- ❌ Evaluation metrics
- ❌ Real SSE with reconnection

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Development Notes

- Map uses OpenFreeMap tiles (free, no API key)
- H3 resolution 9 cells for Nagpur
- SSE reconnection with exponential backoff
- Accessibility: WCAG AA compliant
