import React, { useState, useEffect, useCallback } from 'react';
import * as h3 from 'h3-js';
import Map from './components/Map';
import SectorPanel from './components/SectorPanel';
import DispatchLog from './components/DispatchLog';
import StressConsole from './components/StressConsole';
import PrivacyPanel from './components/PrivacyPanel';
import initialMockData from './data/mock_cells.json';
import './App.css';

// API base URL — set VITE_API_URL in .env for deployment (Day 4)
// Default: localhost:8000 for local dev
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const SSE_URL = `${API_BASE}/sse/events`;

export default function App() {
  const [geojsonData, setGeojsonData] = useState(initialMockData);
  const [sseStatus, setSseStatus] = useState('connecting'); // connected | connecting | offline
  const [lastEvent, setLastEvent] = useState(null);
  const [selectedSector, setSelectedSector] = useState(null);
  const [isSectorPanelOpen, setIsSectorPanelOpen] = useState(false);
  const [isDispatchOpen, setIsDispatchOpen] = useState(false);
  const [isStressOpen, setIsStressOpen] = useState(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);

  // Apply a cell update to GeoJSON state
  const handleCellUpdate = useCallback((payload) => {
    setLastEvent({
      cell: payload.cell,
      risk: payload.risk,
      label: payload.label || (payload.risk >= 0.7 ? 'high' : payload.risk >= 0.4 ? 'medium' : 'low'),
      domain: payload.domain || 'sensor',
      timestamp: new Date().toLocaleTimeString(),
    });

    setGeojsonData((prevData) => {
      const cellId = payload.cell?.toLowerCase();
      let found = false;

      const updatedFeatures = prevData.features.map((feature) => {
        if (feature.properties.h3_cell?.toLowerCase() === cellId) {
          found = true;
          const status = payload.label || (payload.risk >= 0.7 ? 'high' : payload.risk >= 0.4 ? 'medium' : 'low');
          const newDrivers = payload.drivers || [
            `${(payload.domain || 'stress').toUpperCase()} stress +${Math.round((payload.severity || 0.8) * 100)}%`,
            `Dynamic recalculation (risk: ${Math.round(payload.risk * 100)}%)`,
          ];

          return {
            ...feature,
            properties: {
              ...feature.properties,
              risk: payload.risk,
              status: status,
              drivers: newDrivers,
              lastUpdated: new Date().toISOString(),
            },
          };
        }
        return feature;
      });

      // If cell not yet in feature collection, dynamically calculate boundary via h3-js
      if (!found && cellId && cellId.length === 15) {
        try {
          const boundary = h3.cellToBoundary(cellId, true);
          boundary.push(boundary[0]); // close polygon loop
          const status = payload.label || (payload.risk >= 0.7 ? 'high' : payload.risk >= 0.4 ? 'medium' : 'low');

          updatedFeatures.push({
            type: 'Feature',
            id: cellId,
            properties: {
              h3_cell: cellId,
              ward: payload.ward || 'Live Ingested Zone',
              risk: payload.risk,
              status: status,
              drivers: payload.drivers || [`Live Event Ingest: ${payload.domain || 'alert'}`],
              lastUpdated: new Date().toISOString(),
            },
            geometry: {
              type: 'Polygon',
              coordinates: [boundary],
            },
          });
        } catch (err) {
          console.warn('Could not derive boundary for H3 cell:', cellId, err);
        }
      }

      return {
        ...prevData,
        features: updatedFeatures,
      };
    });
  }, []);

  // EventSource listener for Alpha's FastAPI backend
  useEffect(() => {
    let eventSource = null;
    let reconnectTimeout = null;

    const connectSSE = () => {
      setSseStatus('connecting');
      try {
        eventSource = new EventSource(SSE_URL);

        eventSource.onopen = () => {
          setSseStatus('connected');
        };

        eventSource.addEventListener('connected', () => {
          setSseStatus('connected');
        });

        eventSource.addEventListener('cell_updated', (e) => {
          try {
            const data = JSON.parse(e.data);
            handleCellUpdate(data);
          } catch (err) {
            console.error('Failed to parse SSE cell_updated payload:', err);
          }
        });

        // Fallback for standard message events
        eventSource.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            if (data.event === 'cell_updated' || data.cell) {
              handleCellUpdate(data);
            }
          } catch {
            // heartbeat / comment
          }
        };

        eventSource.onerror = () => {
          setSseStatus('offline');
          eventSource.close();
          // Attempt retry every 5 seconds
          reconnectTimeout = setTimeout(connectSSE, 5000);
        };
      } catch {
        setSseStatus('offline');
        reconnectTimeout = setTimeout(connectSSE, 5000);
      }
    };

    connectSSE();

    return () => {
      if (eventSource) eventSource.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [handleCellUpdate]);

  // Dev simulation helper to test live cell updates on the map
  const simulateLiveEvent = () => {
    if (!geojsonData.features || geojsonData.features.length === 0) return;
    const randomIdx = Math.floor(Math.random() * geojsonData.features.length);
    const targetCell = geojsonData.features[randomIdx];
    const isCurrentlyHigh = targetCell.properties.status === 'high';

    const mockPayload = {
      event: 'cell_updated',
      cell: targetCell.properties.h3_cell,
      domain: isCurrentlyHigh ? 'transit' : 'power',
      severity: isCurrentlyHigh ? 0.2 : 0.92,
      risk: isCurrentlyHigh ? 0.22 : 0.89,
      label: isCurrentlyHigh ? 'low' : 'high',
      interval: isCurrentlyHigh ? [0.15, 0.3] : [0.78, 0.96],
      confidence: 0.95,
      drivers: isCurrentlyHigh
        ? ['Grid restored to normal', 'Route 4 transit operational']
        : ['Substation C voltage drop -40%', 'Emergency call drop spike (+180%)'],
      timestamp: new Date().toISOString(),
    };

    handleCellUpdate(mockPayload);
  };

  return (
    <div className="app-viewport">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-pulse-dot" />
          <span className="brand-name">UrbanPulse</span>
          <span className="brand-sub">Spatial Intelligence Engine • Pilot: Nagpur, Maharashtra (H3 Res-9)</span>
        </div>

        <div className="header-status-group">
          {lastEvent && (
            <div className="status-item last-event-chip" title="Last live event received">
              <span style={{ color: '#38bdf8' }}>⚡ Event:</span>
              <span style={{ fontFamily: 'monospace' }}>
                {lastEvent.cell?.slice(0, 7)}… &rarr; {lastEvent.label.toUpperCase()} ({Math.round(lastEvent.risk * 100)}%)
              </span>
            </div>
          )}

          <div className="status-item">
            <span
              className={`status-indicator ${
                sseStatus === 'connected'
                  ? 'status-online'
                  : sseStatus === 'connecting'
                  ? 'status-connecting'
                  : 'status-offline'
              }`}
            />
            <span style={{ textTransform: 'capitalize' }}>SSE: {sseStatus}</span>
          </div>

          <button
            type="button"
            className="nav-action-btn"
            onClick={() => setIsDispatchOpen(true)}
            title="Open Automated Intervention Log"
          >
            📋 Dispatch Log
          </button>

          <button
            type="button"
            className="nav-action-btn"
            onClick={() => setIsStressOpen(true)}
            title="Open Resilience Stress Console"
          >
            ⚡ Stress Console
          </button>

          <button
            type="button"
            className="nav-action-btn"
            onClick={() => setIsPrivacyOpen(true)}
            title="Open Privacy & Anonymity Panel"
          >
            🛡️ Privacy
          </button>

          <button
            type="button"
            className="dev-simulate-btn"
            onClick={simulateLiveEvent}
            title="Simulate incoming SSE cell update event"
          >
            ⚡ Test Event
          </button>
        </div>
      </header>

      {/* Main Map Area */}
      <main className="app-main">
        <Map
          geojsonData={geojsonData}
          onCellSelect={(cell) => {
            setSelectedSector(cell);
            setIsSectorPanelOpen(true);
          }}
        />
        <SectorPanel
          isOpen={isSectorPanelOpen}
          onClose={() => setIsSectorPanelOpen(false)}
          cellData={selectedSector}
        />
        <DispatchLog
          isOpen={isDispatchOpen}
          onClose={() => setIsDispatchOpen(false)}
        />
        <StressConsole
          isOpen={isStressOpen}
          onClose={() => setIsStressOpen(false)}
          onStressApplied={({ feedCut, lossPattern }) => {
            console.log(`Stress applied: ${feedCut}% under ${lossPattern}`);
          }}
        />
        <PrivacyPanel
          isOpen={isPrivacyOpen}
          onClose={() => setIsPrivacyOpen(false)}
        />
      </main>

      {/* Mandatory Footer (D4 & Locked Decisions) */}
      <footer className="app-footer">
        <span>Baseline data: real (OSM, WorldPop, Census 2011) | Live feeds: simulated</span>
      </footer>
    </div>
  );
}
