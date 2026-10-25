import { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import Header from './components/Header';
import LeftRail from './components/LeftRail';
import MapView from './components/MapView';
import RightPanel from './components/RightPanel';

export default function App() {
  const theme = useAppStore((s) => s.theme);

  useEffect(() => {
    document.documentElement.className = theme;
    console.log('App mounted, theme:', theme);
  }, [theme]);

  return (
    <div style={{ 
      width: '100vw', 
      height: '100vh', 
      display: 'grid',
      gridTemplateColumns: '280px 1fr 360px',
      gridTemplateRows: '56px 1fr',
      gap: '16px',
      padding: '16px',
      backgroundColor: 'var(--color-page)'
    }}>
      <Header />
      <LeftRail />
      <div style={{ gridRow: '2', gridColumn: '2', position: 'relative', backgroundColor: 'var(--color-surface)', borderRadius: '8px', border: '1px solid var(--color-border)', overflow: 'hidden' }}>
        <MapView />
      </div>
      <RightPanel />
    </div>
  );
}
