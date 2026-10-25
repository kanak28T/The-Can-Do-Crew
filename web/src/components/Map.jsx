import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './Map.css';

// Default center: Zero Mile, Nagpur, Maharashtra
const NAGPUR_CENTER = [79.0882, 21.1458];

export default function Map({ geojsonData, wardGeojsonData, onCellSelect }) {
  const mapContainer = useRef(null);
  const mapInstance = useRef(null);
  const hoveredStateId = useRef(null);
  const [selectedCell, setSelectedCell] = useState(null);

  useEffect(() => {
    if (mapInstance.current) return; // initialize map only once

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: NAGPUR_CENTER,
      zoom: 13.2,
      pitch: 25,
      bearing: 0,
    });

    mapInstance.current = map;

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-left');

    map.on('load', () => {
      // Add H3 resolution-9 GeoJSON source
      map.addSource('h3-cells', {
        type: 'geojson',
        data: geojsonData,
        generateId: true
      });

      // Layer 1: Hexagon Fill with Dynamic Risk Color Coding
      map.addLayer({
        id: 'h3-cells-fill',
        type: 'fill',
        source: 'h3-cells',
        paint: {
          'fill-color': [
            'case',
            ['==', ['get', 'status'], 'high'], '#ef4444',
            ['==', ['get', 'status'], 'medium'], '#f59e0b',
            ['==', ['get', 'status'], 'low'], '#10b981',
            '#6b7280' // unknown / default
          ],
          'fill-opacity': [
            'case',
            ['boolean', ['feature-state', 'hover'], false], 0.85,
            0.62
          ]
        }
      });

      // Layer 2: Hexagon Boundaries
      map.addLayer({
        id: 'h3-cells-stroke',
        type: 'line',
        source: 'h3-cells',
        paint: {
          'line-color': [
            'case',
            ['boolean', ['feature-state', 'hover'], false], '#ffffff',
            'rgba(255, 255, 255, 0.25)'
          ],
          'line-width': [
            'case',
            ['boolean', ['feature-state', 'hover'], false], 2.5,
            1.0
          ]
        }
      });

      // Layer 3: Cell Labels (Risk %)
      map.addLayer({
        id: 'h3-cells-label',
        type: 'symbol',
        source: 'h3-cells',
        layout: {
          'text-field': [
            'case',
            ['has', 'risk'],
            ['concat', ['to-string', ['round', ['*', ['get', 'risk'], 100]]], '%'],
            'N/A'
          ],
          'text-size': 10,
          'text-anchor': 'center',
          'text-allow-overlap': false
        },
        paint: {
          'text-color': '#f8fafc',
          'text-halo-color': 'rgba(15, 23, 42, 0.85)',
          'text-halo-width': 1.5
        }
      });

      // Layer 4 & 5: Ward Boundaries Overlay (D2: Wards are display labels only)
      if (wardGeojsonData) {
        map.addSource('nagpur-wards', {
          type: 'geojson',
          data: wardGeojsonData,
        });

        map.addLayer({
          id: 'nagpur-wards-line',
          type: 'line',
          source: 'nagpur-wards',
          paint: {
            'line-color': '#38bdf8',
            'line-width': 2.2,
            'line-dasharray': [3, 2],
            'line-opacity': 0.85
          }
        });

        map.addLayer({
          id: 'nagpur-wards-label',
          type: 'symbol',
          source: 'nagpur-wards',
          layout: {
            'text-field': ['get', 'name'],
            'text-size': 13,
            'text-anchor': 'center',
            'text-allow-overlap': false
          },
          paint: {
            'text-color': '#ffffff',
            'text-halo-color': 'rgba(15, 23, 42, 0.95)',
            'text-halo-width': 2.0
          }
        });
      }

      // Initial cell selection if features exist
      if (geojsonData?.features?.length > 0) {
        setSelectedCell(geojsonData.features[0].properties);
      }
    });

    // Hover effect
    map.on('mousemove', 'h3-cells-fill', (e) => {
      if (e.features.length > 0) {
        if (hoveredStateId.current !== null) {
          map.setFeatureState(
            { source: 'h3-cells', id: hoveredStateId.current },
            { hover: false }
          );
        }
        hoveredStateId.current = e.features[0].id;
        map.setFeatureState(
          { source: 'h3-cells', id: hoveredStateId.current },
          { hover: true }
        );
        map.getCanvas().style.cursor = 'pointer';
      }
    });

    map.on('mouseleave', 'h3-cells-fill', () => {
      if (hoveredStateId.current !== null) {
        map.setFeatureState(
          { source: 'h3-cells', id: hoveredStateId.current },
          { hover: false }
        );
      }
      hoveredStateId.current = null;
      map.getCanvas().style.cursor = '';
    });

    // Click cell selection
    map.on('click', 'h3-cells-fill', (e) => {
      if (e.features.length > 0) {
        const props = e.features[0].properties;
        let drivers = props.drivers;
        if (typeof drivers === 'string') {
          try { drivers = JSON.parse(drivers); } catch (err) { drivers = [drivers]; }
        }
        const cellData = { ...props, drivers };
        setSelectedCell(cellData);
        if (onCellSelect) onCellSelect(cellData);
      }
    });

    return () => {
      map.remove();
      mapInstance.current = null;
    };
  }, []);

  // Update GeoJSON data dynamically when props change
  useEffect(() => {
    if (mapInstance.current && mapInstance.current.getSource('h3-cells') && geojsonData) {
      mapInstance.current.getSource('h3-cells').setData(geojsonData);
      // Update selected cell if it matches
      if (selectedCell) {
        const updated = geojsonData.features?.find(
          (f) => f.properties.h3_cell === selectedCell.h3_cell
        );
        if (updated) {
          setSelectedCell(updated.properties);
        }
      }
    }
  }, [geojsonData]);

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'high': return 'badge-high';
      case 'medium': return 'badge-medium';
      case 'low': return 'badge-low';
      default: return 'badge-unknown';
    }
  };

  const getRiskColor = (status) => {
    switch (status) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'low': return '#10b981';
      default: return '#9ca3af';
    }
  };

  return (
    <div className="map-container-root">
      <div ref={mapContainer} className="maplibre-viewport" />

      {/* Floating HUD Inspector */}
      {selectedCell && (
        <div className="map-hud-panel" role="region" aria-label="Selected Cell Inspection">
          <div className="map-hud-title">
            <span>Cell Inspector</span>
            <span className="map-hud-cell-id">{selectedCell.h3_cell}</span>
          </div>
          <div className="map-hud-ward">{selectedCell.ward || 'Nagpur Zone'}</div>

          <div className="map-hud-metric-row">
            <div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                Vulnerability (z)
              </div>
              <div className="map-hud-score" style={{ color: getRiskColor(selectedCell.status) }}>
                {selectedCell.risk !== null && selectedCell.risk !== undefined
                  ? `${Math.round(selectedCell.risk * 100)}%`
                  : 'UNKNOWN'}
              </div>
            </div>
            <div>
              <span className={`map-hud-badge ${getStatusBadgeClass(selectedCell.status)}`}>
                {selectedCell.status || 'UNKNOWN'}
              </span>
            </div>
          </div>

          <div className="map-hud-drivers-title">Causal Drivers (Top Contributors)</div>
          <ul className="map-hud-drivers-list">
            {Array.isArray(selectedCell.drivers) && selectedCell.drivers.length > 0 ? (
              selectedCell.drivers.map((driver, index) => (
                <li key={index}>{driver}</li>
              ))
            ) : (
              <li>No significant stressor detected</li>
            )}
          </ul>
        </div>
      )}

      {/* Color Legend */}
      <div className="map-legend" role="region" aria-label="Risk Map Legend">
        <span style={{ fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.72rem' }}>
          Risk (H3-Res9):
        </span>
        <div className="legend-item">
          <span className="legend-swatch swatch-high" />
          <span>High (&ge;0.7)</span>
        </div>
        <div className="legend-item">
          <span className="legend-swatch swatch-medium" />
          <span>Medium (0.4–0.7)</span>
        </div>
        <div className="legend-item">
          <span className="legend-swatch swatch-low" />
          <span>Low (&lt;0.4)</span>
        </div>
        <div className="legend-item">
          <span className="legend-swatch swatch-unknown" />
          <span>Unknown (Silence)</span>
        </div>
        <div className="legend-item" style={{ borderLeft: '1px solid rgba(255,255,255,0.15)', paddingLeft: '0.75rem' }}>
          <span style={{ display: 'inline-block', width: '16px', height: '0px', borderTop: '2px dashed #38bdf8' }} />
          <span style={{ color: '#38bdf8' }}>Ward Overlay</span>
        </div>
      </div>
    </div>
  );
}
