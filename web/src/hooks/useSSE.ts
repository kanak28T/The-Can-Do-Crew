import { useEffect, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import type { CellData, ZoneData, DispatchItem } from '../types';

const API_BASE = (import.meta as any).env.VITE_API_URL || 'http://localhost:8000';
const USE_MOCK = (import.meta as any).env.VITE_USE_MOCK === 'true';

export function useSSE() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const upsertCell = useAppStore((s) => s.upsertCell);
  const setConnectionStatus = useAppStore((s) => s.setConnectionStatus);
  const setLastUpdateTime = useAppStore((s) => s.setLastUpdateTime);
  const setZones = useAppStore((s) => s.setZones);
  const setDispatches = useAppStore((s) => s.setDispatches);

  useEffect(() => {
    if (USE_MOCK) {
      import('../lib/mockStream').then(({ startMockStream }) => {
        startMockStream(upsertCell, setZones, setDispatches, setConnectionStatus, setLastUpdateTime);
      });
      return;
    }
    setConnectionStatus('reconnecting');
    const es = new EventSource(API_BASE + '/api/stream');
    eventSourceRef.current = es;
    es.onopen = () => setConnectionStatus('live');
    es.onerror = () => setConnectionStatus('offline');
    es.addEventListener('cell_update', (e: MessageEvent) => {
      try {
        const data: CellData = JSON.parse(e.data);
        upsertCell(data);
        setLastUpdateTime(new Date().toLocaleTimeString());
      } catch (err) { console.error(err); }
    });
    return () => { if (eventSourceRef.current) eventSourceRef.current.close(); };
  }, [upsertCell, setConnectionStatus, setLastUpdateTime, setZones, setDispatches]);
}
