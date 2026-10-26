import { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import Header from './components/Header';
import LeftRail from './components/LeftRail';
import MapView from './components/MapView';
import LandscapeDrivers from './components/LandscapeDrivers';
import RightIntelligencePanel from './components/RightIntelligencePanel';
import SplashScreen from './components/SplashScreen';

export default function App() {
  const theme = useAppStore((s) => s.theme);

  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);

  return (
    <>
      {/* Initial load splash screen */}
      <SplashScreen />

      <div style={{ 
        width: '100vw', 
        height: '100vh', 
        display: 'grid',
        gridTemplateColumns: '260px 1fr 460px',
        gridTemplateRows: '56px 1fr',
        gap: '12px',
        padding: '12px',
        backgroundColor: 'var(--color-page)',
        boxSizing: 'border-box',
        overflow: 'hidden'
      }}>
        {/* Top Header */}
        <Header />

        {/* Left Column: Stress Console & Live Numbers */}
        <div style={{ gridRow: '2', gridColumn: '1', overflowY: 'auto' }}>
          <LeftRail />
        </div>

        {/* Center Column: Unobstructed Map on Top + Drivers Landscape at Bottom */}
        <div style={{ 
          gridRow: '2', 
          gridColumn: '2', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '12px',
          height: '100%',
          minWidth: 0,
          overflow: 'hidden'
        }}>
          {/* Map Container */}
          <div style={{ 
            flex: 1, 
            position: 'relative', 
            backgroundColor: 'var(--color-surface)', 
            borderRadius: '8px', 
            border: '1px solid var(--color-border)', 
            overflow: 'hidden',
            minHeight: '340px'
          }}>
            <MapView />
          </div>

          {/* Drivers & Zone Analysis in Landscape at Bottom */}
          <LandscapeDrivers />
        </div>

        {/* Right Column: Dedicated Full-Height Intelligence Workspace (Causal Graph, Dispatch, Privacy, Eval) */}
        <div style={{ gridRow: '2', gridColumn: '3', height: '100%', minWidth: 0, overflow: 'hidden' }}>
          <RightIntelligencePanel />
        </div>
      </div>
    </>
  );
}
