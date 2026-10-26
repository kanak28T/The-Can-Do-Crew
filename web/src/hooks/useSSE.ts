import { useEffect, useRef } from 'react';
import { useAppStore } from '../store/useAppStore';
import { SSE_URL } from '../lib/api';
import type { CellData, RiskLevel } from '../types';

const USE_MOCK = (import.meta as any).env.VITE_USE_MOCK === 'true';

export interface RingBufferItem<T> {
  id: string | number;
  timestamp: number;
  data: T;
}

/**
 * In-memory circular Ring Buffer with fixed capacity.
 * Preserves the most recent items and enables replay upon reconnect.
 */
export class RingBuffer<T> {
  private buffer: (RingBufferItem<T> | undefined)[];
  private capacity: number;
  private head: number = 0;
  private tail: number = 0;
  private count: number = 0;

  constructor(capacity: number = 250) {
    this.capacity = capacity;
    this.buffer = new Array(capacity);
  }

  push(item: RingBufferItem<T>): void {
    this.buffer[this.tail] = item;
    this.tail = (this.tail + 1) % this.capacity;
    if (this.count < this.capacity) {
      this.count++;
    } else {
      this.head = (this.head + 1) % this.capacity; // Evict oldest
    }
  }

  getAll(): RingBufferItem<T>[] {
    const items: RingBufferItem<T>[] = [];
    for (let i = 0; i < this.count; i++) {
      const idx = (this.head + i) % this.capacity;
      const item = this.buffer[idx];
      if (item !== undefined) {
        items.push(item);
      }
    }
    return items;
  }

  getSince(timestampOrId: number | string): RingBufferItem<T>[] {
    const all = this.getAll();
    if (typeof timestampOrId === 'number') {
      return all.filter((item) => item.timestamp > timestampOrId);
    }
    const idx = all.findIndex((item) => String(item.id) === String(timestampOrId));
    if (idx >= 0) {
      return all.slice(idx + 1);
    }
    return all;
  }

  clear(): void {
    this.buffer = new Array(this.capacity);
    this.head = 0;
    this.tail = 0;
    this.count = 0;
  }

  size(): number {
    return this.count;
  }
}

// Global in-memory ring buffer tracking incoming cell events across hook lifecycle
export const sseRingBuffer = new RingBuffer<CellData>(250);

function parseToCellData(raw: any): CellData | null {
  if (!raw) return null;
  const h3 = raw.cell || raw.h3;
  if (!h3) return null;

  const risk = typeof raw.risk === 'number' ? raw.risk : 0;
  const lo = Array.isArray(raw.interval) && raw.interval[0] !== undefined
    ? raw.interval[0]
    : (typeof raw.lo === 'number' ? raw.lo : Math.max(0, risk - 0.05));
  const hi = Array.isArray(raw.interval) && raw.interval[1] !== undefined
    ? raw.interval[1]
    : (typeof raw.hi === 'number' ? raw.hi : Math.min(1, risk + 0.05));

  let level: RiskLevel = 'low';
  if (raw.is_unknown || raw.label === 'unknown') {
    level = 'unknown';
  } else if (raw.label === 'high' || raw.label === 'watch' || raw.label === 'low') {
    level = raw.label;
  } else if (risk >= 0.7) {
    level = 'high';
  } else if (risk >= 0.4) {
    level = 'watch';
  }

  return {
    h3,
    risk,
    lo,
    hi,
    level,
    confidence: typeof raw.confidence === 'number' ? raw.confidence : 0.85,
    imputed: Boolean(raw.is_unknown || raw.imputed),
    updated_at: raw.timestamp || raw.updated_at || new Date().toISOString(),
  };
}

export function useSSE() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const retryCountRef = useRef(0);
  const lastEventIdRef = useRef<string | number | null>(null);
  const lastEventTimeRef = useRef<number>(Date.now());
  const isUnmountedRef = useRef(false);

  const upsertCell = useAppStore((s) => s.upsertCell);
  const setConnectionStatus = useAppStore((s) => s.setConnectionStatus);
  const setLastUpdateTime = useAppStore((s) => s.setLastUpdateTime);
  const setZones = useAppStore((s) => s.setZones);
  const setDispatches = useAppStore((s) => s.setDispatches);
  const setLiveNumbers = useAppStore((s) => s.setLiveNumbers);

  // Read cells from store snapshot and recount live KPIs — called after every upsert
  const recountLive = () => {
    const cells = useAppStore.getState().cells;
    let high = 0, watch = 0, unknown = 0;
    cells.forEach((c) => {
      if (c.level === 'high')         high++;
      else if (c.level === 'watch')   watch++;
      else if (c.level === 'unknown') unknown++;
      // Count low-risk active cells as "watch" for dashboard visibility
      else if (c.risk >= 0.25)        watch++;
    });
    setLiveNumbers(high, watch, unknown, 0);
  };

  useEffect(() => {
    isUnmountedRef.current = false;

    if (USE_MOCK) {
      import('../lib/mockStream').then(({ startMockStream }) => {
        if (!isUnmountedRef.current) {
          startMockStream(
            (cell) => {
              sseRingBuffer.push({
                id: Date.now() + '-' + cell.h3,
                timestamp: Date.now(),
                data: cell,
              });
              upsertCell(cell);
              setTimeout(recountLive, 0);
            },
            setZones,
            setDispatches,
            setConnectionStatus,
            setLastUpdateTime
          );
        }
      });
      return;
    }

    function replayMissedEvents() {
      // Replay all buffered items into the store to ensure 100% map state consistency
      const buffered = sseRingBuffer.getAll();
      if (buffered.length > 0) {
        buffered.forEach((item) => {
          upsertCell(item.data);
        });
      }
    }

    function connect() {
      if (isUnmountedRef.current) return;

      // Close previous connection if still hanging
      if (eventSourceRef.current) {
        try {
          eventSourceRef.current.close();
        } catch (_) {}
        eventSourceRef.current = null;
      }

      setConnectionStatus('reconnecting');

      // Build endpoint URL — uses SSE_URL from api.ts (relative in dev, proxied by Vite)
      const url = new URL(SSE_URL, window.location.href);

      if (lastEventIdRef.current !== null) {
        url.searchParams.set('last_event_id', String(lastEventIdRef.current));
      }
      if (lastEventTimeRef.current) {
        url.searchParams.set('since', String(lastEventTimeRef.current));
      }

      const es = new EventSource(url.toString());
      eventSourceRef.current = es;

      es.onopen = () => {
        if (isUnmountedRef.current) return;
        setConnectionStatus('live');
        retryCountRef.current = 0;
        // On successful reconnect, replay and ensure no state drop
        replayMissedEvents();
      };

      const handleEvent = (e: MessageEvent) => {
        if (isUnmountedRef.current) return;
        try {
          if (e.lastEventId) {
            lastEventIdRef.current = e.lastEventId;
          }
          lastEventTimeRef.current = Date.now();

          const parsed = JSON.parse(e.data);
          const cellData = parseToCellData(parsed);

          if (cellData) {
            // Push into in-memory ring buffer
            sseRingBuffer.push({
              id: e.lastEventId || cellData.h3 + '-' + Date.now(),
              timestamp: Date.now(),
              data: cellData,
            });

            // Persist into store (never clears existing map state)
            upsertCell(cellData);
            setLastUpdateTime(new Date().toLocaleTimeString());
            // Recount after store settles
            setTimeout(recountLive, 0);
          }
        } catch (err) {
          console.warn('[SSE] Failed to parse SSE event data:', err);
        }
      };

      es.addEventListener('cell_updated', handleEvent);
      es.addEventListener('cell_update', handleEvent);
      es.addEventListener('message', handleEvent);

      es.onerror = () => {
        if (isUnmountedRef.current) return;
        setConnectionStatus('reconnecting');
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }

        // Exponential backoff reconnect: 1s, 1.5s, 2.25s ... max 10s
        const backoff = Math.min(1000 * Math.pow(1.5, retryCountRef.current), 10000);
        const jitter = Math.floor(Math.random() * 300);
        const delay = backoff + jitter;
        retryCountRef.current += 1;

        if (reconnectTimeoutRef.current) {
          window.clearTimeout(reconnectTimeoutRef.current);
        }

        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, delay);
      };
    }

    connect();

    return () => {
      isUnmountedRef.current = true;
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [upsertCell, setConnectionStatus, setLastUpdateTime, setZones, setDispatches, setLiveNumbers]);
}

