import { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import Header from './components/Header';
import LeftRail from './components/LeftRail';
import MapView from './components/MapView';
import RightPanel from './components/RightPanel';
import BottomDock from './components/BottomDock';
import SplashScreen from './components/SplashScreen';

export default function App() {
  const theme = useAppStore((s) => s.theme);

  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);

  return (
    <>
      {/* Initial load splash screen with animated progress and fade-out */}
      <SplashScreen />

      {/* Main Grid Application Layout */}
      <div
        className="app-container"
        style={{
          width: '100vw',
          height: '100vh',
          display: 'grid',
          gridTemplateColumns: '280px 1fr 360px',
          gridTemplateRows: '56px minmax(0, 1fr)',
          gap: '16px',
          padding: '16px',
          backgroundColor: 'transparent',
          position: 'relative',
          zIndex: 1,
          overflow: 'hidden',
          boxSizing: 'border-box',
        }}
      >
        <Header />

        {/* Column 1: Left Rail with overflow-y containment */}
        <div
          style={{
            gridRow: '2',
            gridColumn: '1',
            minHeight: 0,
            height: '100%',
            overflowY: 'auto',
            overflowX: 'hidden',
          }}
        >
          <LeftRail />
        </div>

        {/* Column 2: Center Dashboard Map + Bottom Dock */}
        <div
          style={{
            gridRow: '2',
            gridColumn: '2',
            position: 'relative',
            width: '100%',
            height: '100%',
            minHeight: '400px',
            backgroundColor: 'var(--color-surface)',
            borderRadius: '8px',
            border: '1px solid var(--color-border)',
            overflow: 'hidden',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Strict full-height map viewport container */}
          <div
            style={{
              width: '100%',
              height: '100%',
              minHeight: '400px',
              position: 'relative',
              flex: 1,
            }}
          >
            <MapView />
          </div>
          <BottomDock />
        </div>

        {/* Column 3: Right Panel with overflow-y containment */}
        <div
          style={{
            gridRow: '2',
            gridColumn: '3',
            minHeight: 0,
            height: '100%',
            overflowY: 'auto',
            overflowX: 'hidden',
          }}
        >
          <RightPanel />
        </div>
      </div>
    </>
  );
}
