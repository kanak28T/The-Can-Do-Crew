import { useEffect, useRef, useState, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import nagpurH3Res8 from '../data/nagpur_h3_res8.json';
import nagpurH3Res9 from '../data/nagpur_h3_res9.json';
import nagpurWards from '../data/nagpur_wards.json';
import nagpurHospitals from '../data/nagpur_hospitals.json';
import nagpurClosedRoads from '../data/nagpur_closed_roads.json';
import { useAppStore } from '../store/useAppStore';

const NAGPUR_CENTER: [number, number] = [79.0882, 21.1458];
const ZOOM_SWITCH_THRESHOLD = 12.0;

// High-reliability Carto basemap styles with zero API key dependencies
const CARTO_DARK_STYLE: any = {
  version: 8,
  sources: {
    'carto-dark': {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    },
  },
  layers: [
    {
      id: 'carto-dark-tiles',
      type: 'raster',
      source: 'carto-dark',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const CARTO_LIGHT_STYLE: any = {
  version: 8,
  sources: {
    'carto-light': {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        'https://d.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    },
  },
  layers: [
    {
      id: 'carto-light-tiles',
      type: 'raster',
      source: 'carto-light',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

export default function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  const activeLayer = useAppStore((s) => s.activeLayer);
  const setActiveLayer = useAppStore((s) => s.setActiveLayer);
  const setSelectedCellH3 = useAppStore((s) => s.setSelectedCellH3);
  const setSelectedZoneId = useAppStore((s) => s.setSelectedZoneId);
  const theme = useAppStore((s) => s.theme);

  const [currentZoom, setCurrentZoom] = useState(11.2);
  const [activeResolution, setActiveResolution] = useState<'res8' | 'res9'>('res8');
  const [showA11yHelp, setShowA11yHelp] = useState(false);

  // Initialize Map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const baseStyle = theme === 'dark' ? CARTO_DARK_STYLE : CARTO_LIGHT_STYLE;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: baseStyle,
      center: NAGPUR_CENTER,
      zoom: 11.2,
      maxBounds: [[78.5, 20.5], [79.5, 21.5]],
      keyboard: true, // Enable native keyboard handling
    });
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-right');

    const updateZoomState = () => {
      const z = map.getZoom();
      setCurrentZoom(Number(z.toFixed(1)));
      setActiveResolution(z >= ZOOM_SWITCH_THRESHOLD ? 'res9' : 'res8');
    };

    map.on('zoom', updateZoomState);

    map.on('load', () => {
      updateZoomState();
      map.resize();

      // ── Layer 1: H3 Res 8 Grid (Zoomed Out / Macro, maxzoom: 12) ──
      map.addSource('h3-res8', {
        type: 'geojson',
        data: nagpurH3Res8 as any,
        generateId: true,
      });

      map.addLayer({
        id: 'h3-res8-fill',
        type: 'fill',
        source: 'h3-res8',
        maxzoom: ZOOM_SWITCH_THRESHOLD,
        paint: {
          'fill-color': [
            'case',
            ['==', ['get', 'status'], 'high'], '#DC3545',
            ['==', ['get', 'status'], 'medium'], '#FFC107',
            ['==', ['get', 'status'], 'low'], '#198754',
            '#6C757D',
          ],
          'fill-opacity': 0.38,
        },
      });

      map.addLayer({
        id: 'h3-res8-outline',
        type: 'line',
        source: 'h3-res8',
        maxzoom: ZOOM_SWITCH_THRESHOLD,
        paint: {
          'line-color': [
            'case',
            ['==', ['get', 'status'], 'high'], '#DC3545',
            'rgba(255, 255, 255, 0.25)',
          ],
          'line-width': ['case', ['==', ['get', 'status'], 'high'], 1.8, 0.8],
        },
      });

      // ── Layer 2: H3 Res 9 Grid (Zoomed In / Micro, minzoom: 12) ──
      map.addSource('h3-cells', {
        type: 'geojson',
        data: nagpurH3Res9 as any,
        generateId: true,
      });

      map.addLayer({
        id: 'h3-cells-fill',
        type: 'fill',
        source: 'h3-cells',
        minzoom: ZOOM_SWITCH_THRESHOLD,
        paint: {
          'fill-color': [
            'case',
            ['==', ['get', 'status'], 'high'], '#E8704F',
            ['==', ['get', 'status'], 'medium'], '#E3B341',
            ['==', ['get', 'status'], 'low'], '#5FA8A0',
            '#8A97A6',
          ],
          'fill-opacity': 0.42,
        },
      });

      map.addLayer({
        id: 'h3-cells-outline',
        type: 'line',
        source: 'h3-cells',
        minzoom: ZOOM_SWITCH_THRESHOLD,
        paint: {
          'line-color': [
            'case',
            ['==', ['get', 'status'], 'high'], '#E8704F',
            'rgba(255, 255, 255, 0.2)',
          ],
          'line-width': ['case', ['==', ['get', 'status'], 'high'], 1.6, 0.6],
        },
      });

      // ── Layer 3: Ward Boundaries Overlay (Prabhags 1-30) ──
      map.addSource('nagpur-wards', {
        type: 'geojson',
        data: nagpurWards as any,
      });

      map.addLayer({
        id: 'nagpur-wards-line',
        type: 'line',
        source: 'nagpur-wards',
        paint: {
          'line-color': '#38bdf8',
          'line-width': 2.0,
          'line-dasharray': [3, 2],
          'line-opacity': 0.85,
        },
      });

      map.addLayer({
        id: 'nagpur-wards-label',
        type: 'symbol',
        source: 'nagpur-wards',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 11,
          'text-anchor': 'center',
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': 'rgba(15, 23, 42, 0.95)',
          'text-halo-width': 2.0,
        },
      });

      // ── Layer 4: Closed-Road Dashed Lines (Step 1) ──
      map.addSource('nagpur-closed-roads', {
        type: 'geojson',
        data: nagpurClosedRoads as any,
      });

      // Crimson casing glow
      map.addLayer({
        id: 'closed-roads-casing',
        type: 'line',
        source: 'nagpur-closed-roads',
        paint: {
          'line-color': '#ef4444',
          'line-width': 7.0,
          'line-opacity': 0.35,
        },
      });

      // Distinct dashed pattern line
      map.addLayer({
        id: 'closed-roads-line',
        type: 'line',
        source: 'nagpur-closed-roads',
        paint: {
          'line-color': '#f43f5e',
          'line-width': 3.5,
          'line-dasharray': [3, 2],
          'line-opacity': 0.95,
        },
      });

      // Closed road symbol labels
      map.addLayer({
        id: 'closed-roads-label',
        type: 'symbol',
        source: 'nagpur-closed-roads',
        layout: {
          'text-field': ['concat', '⛔ ', ['get', 'name'], ' (CLOSED)'],
          'text-size': 10.5,
          'symbol-placement': 'line',
          'text-offset': [0, 1.2],
        },
        paint: {
          'text-color': '#fca5a5',
          'text-halo-color': '#450a0a',
          'text-halo-width': 2,
        },
      });

      // ── Layer 5: Hospital Icons & Point Markers (Step 1) ──
      map.addSource('nagpur-hospitals', {
        type: 'geojson',
        data: nagpurHospitals as any,
      });

      // Red circular hospital beacon
      map.addLayer({
        id: 'hospital-points-circle',
        type: 'circle',
        source: 'nagpur-hospitals',
        paint: {
          'circle-radius': 9,
          'circle-color': '#ef4444',
          'circle-stroke-width': 2.5,
          'circle-stroke-color': '#ffffff',
        },
      });

      // Cross symbol inside circle
      map.addLayer({
        id: 'hospital-points-cross',
        type: 'symbol',
        source: 'nagpur-hospitals',
        layout: {
          'text-field': '+',
          'text-size': 14,
          'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
          'text-anchor': 'center',
          'text-allow-overlap': true,
        },
        paint: {
          'text-color': '#ffffff',
        },
      });

      // Hospital text name label
      map.addLayer({
        id: 'hospital-points-label',
        type: 'symbol',
        source: 'nagpur-hospitals',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 11,
          'text-anchor': 'top',
          'text-offset': [0, 1.3],
          'text-allow-overlap': false,
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#0f172a',
          'text-halo-width': 2.5,
        },
      });
    });

    // ── Interaction: H3 Cell Click (Res 8 & Res 9) ──
    const handleCellClick = (e: any) => {
      if (e.features && e.features.length > 0) {
        const props = e.features[0].properties;
        const cellId = props.h3_cell || props.cell;
        setSelectedCellH3(cellId);
        if (props.ward) {
          setSelectedZoneId(props.ward);
        }
      }
    };

    map.on('click', 'h3-cells-fill', handleCellClick);
    map.on('click', 'h3-res8-fill', handleCellClick);

    map.on('mousemove', 'h3-cells-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'h3-cells-fill', () => { map.getCanvas().style.cursor = ''; });
    map.on('mousemove', 'h3-res8-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'h3-res8-fill', () => { map.getCanvas().style.cursor = ''; });

    // ── Interaction: Closed Road Click ──
    map.on('click', 'closed-roads-line', (e: any) => {
      if (!e.features || !e.features[0]) return;
      const feat = e.features[0];
      const p = feat.properties;
      const coords = e.lngLat;

      if (popupRef.current) popupRef.current.remove();
      popupRef.current = new maplibregl.Popup({ closeButton: true, offset: 12 })
        .setLngLat(coords)
        .setHTML(`
          <div style="font-family: sans-serif; padding: 4px; font-size: 12px; color: #1e293b;">
            <div style="font-weight: 700; color: #b91c1c; display: flex; align-items: center; gap: 4px;">
              <span>⛔</span> ${p.name || 'Closed Corridor'}
            </div>
            <div style="margin-top: 4px; font-size: 11px; color: #475569;">
              <strong>Hazard:</strong> ${p.reason || 'Waterlogging & Feeder Cable Hazard'}
            </div>
            <div style="margin-top: 4px; font-size: 10.5px; background: #fee2e2; padding: 2px 6px; border-radius: 4px; color: #991b1b; display: inline-block;">
              Severity: ${p.severity?.toUpperCase() || 'CRITICAL'} • Detour Active
            </div>
          </div>
        `)
        .addTo(map);
    });

    map.on('mousemove', 'closed-roads-line', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'closed-roads-line', () => { map.getCanvas().style.cursor = ''; });

    // ── Interaction: Hospital Icon Click ──
    map.on('click', 'hospital-points-circle', (e: any) => {
      if (!e.features || !e.features[0]) return;
      const feat = e.features[0];
      const p = feat.properties;
      const coords = feat.geometry.coordinates;

      if (popupRef.current) popupRef.current.remove();
      popupRef.current = new maplibregl.Popup({ closeButton: true, offset: 16 })
        .setLngLat(coords)
        .setHTML(`
          <div style="font-family: sans-serif; padding: 4px; font-size: 12px; color: #1e293b;">
            <div style="font-weight: 700; color: #0284c7; display: flex; align-items: center; gap: 4px;">
              <span>🏥</span> ${p.name || 'Medical Facility'}
            </div>
            <div style="margin-top: 4px; font-size: 11px; color: #475569;">
              <strong>Facility:</strong> Emergency Trauma & Inpatient Center
            </div>
            <div style="margin-top: 4px; font-size: 10.5px; background: #e0f2fe; padding: 2px 6px; border-radius: 4px; color: #0369a1; display: inline-block;">
              Catchment Status: High Priority Access
            </div>
          </div>
        `)
        .addTo(map);
    });

    map.on('mousemove', 'hospital-points-circle', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'hospital-points-circle', () => { map.getCanvas().style.cursor = ''; });

    // Handle container resize dynamically so map never collapses
    const resizeObserver = new ResizeObserver(() => {
      if (mapRef.current) {
        mapRef.current.resize();
      }
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    const t1 = setTimeout(() => { if (mapRef.current) mapRef.current.resize(); }, 150);
    const t2 = setTimeout(() => { if (mapRef.current) mapRef.current.resize(); }, 500);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      resizeObserver.disconnect();
      if (popupRef.current) popupRef.current.remove();
      map.remove();
      mapRef.current = null;
    };
  }, [theme]);

  // Update layer visibility when activeLayer changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // Road layer highlighting
    if (map.getLayer('closed-roads-line')) {
      const roadOpacity = activeLayer === 'roads' ? 1.0 : 0.75;
      const roadWidth = activeLayer === 'roads' ? 5.0 : 3.5;
      map.setPaintProperty('closed-roads-line', 'line-opacity', roadOpacity);
      map.setPaintProperty('closed-roads-line', 'line-width', roadWidth);
    }

    // Hospital layer highlighting
    if (map.getLayer('hospital-points-circle')) {
      const hospRadius = activeLayer === 'hospitals' ? 12 : 9;
      map.setPaintProperty('hospital-points-circle', 'circle-radius', hospRadius);
    }
  }, [activeLayer]);

  // ── Accessibility: Keyboard Navigation Handler ──
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    const map = mapRef.current;
    if (!map) return;

    const PAN_OFFSET = 90;
    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault();
        map.panBy([0, -PAN_OFFSET]);
        break;
      case 'ArrowDown':
        e.preventDefault();
        map.panBy([0, PAN_OFFSET]);
        break;
      case 'ArrowLeft':
        e.preventDefault();
        map.panBy([-PAN_OFFSET, 0]);
        break;
      case 'ArrowRight':
        e.preventDefault();
        map.panBy([PAN_OFFSET, 0]);
        break;
      case '+':
      case '=':
        e.preventDefault();
        map.zoomIn();
        break;
      case '-':
      case '_':
        e.preventDefault();
        map.zoomOut();
        break;
      case '0':
        e.preventDefault();
        map.flyTo({ center: NAGPUR_CENTER, zoom: 11.2 });
        break;
      case '?':
        setShowA11yHelp((prev) => !prev);
        break;
    }
  }, []);

  const layers = [
    { key: 'risk', label: 'Risk' },
    { key: 'roads', label: 'Roads' },
    { key: 'hospitals', label: 'Hospitals' },
    { key: 'feed_coverage', label: 'Feed' }
  ];

  const legendItems = [
    { label: 'High Risk', color: '#DC3545' },
    { label: 'Watch', color: '#FFC107' },
    { label: 'Low Risk', color: '#198754' },
    { label: 'Unknown', color: '#6C757D' }
  ];

  return (
    <div
      tabIndex={0}
      role="region"
      aria-label="Interactive Nagpur Geospatial Risk Map. Use arrow keys to pan, plus or minus to zoom."
      onKeyDown={handleKeyDown}
      className="relative focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg overflow-hidden"
      style={{
        width: '100%',
        height: '100%',
        minHeight: '400px',
        backgroundColor: '#0f172a',
        position: 'relative'
      }}
    >
      {/* Strict 100% full-height MapLibre container with minHeight 400px */}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '100%',
          minHeight: '400px',
          backgroundColor: '#0f172a'
        }}
      />

      {/* Top Left: Dynamic Zoom & Resolution Switch Pill */}
      <div className="panel-surface absolute top-3 left-3 px-3 py-1.5 flex items-center gap-2 z-10 text-xs backdrop-blur-md">
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        <span className="font-mono font-medium text-[var(--color-text)]">
          Zoom {currentZoom}
        </span>
        <span className="text-[var(--color-border)]">|</span>
        <span
          className={`font-semibold px-1.5 py-0.5 rounded text-[10px] ${
            activeResolution === 'res9'
              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
          }`}
        >
          {activeResolution === 'res9' ? 'H3 Res 9 (Micro)' : 'H3 Res 8 (Macro)'}
        </span>
      </div>

      {/* Top Right: Layer Switcher */}
      <div className="panel-surface absolute top-3 right-12 p-1.5 flex gap-1 z-10 backdrop-blur-md">
        {layers.map((l) => (
          <button
            key={l.key}
            type="button"
            onClick={() => setActiveLayer(l.key as any)}
            className="text-xs px-2.5 py-1 rounded transition-colors"
            style={{
              background: activeLayer === l.key ? 'var(--color-raised)' : 'transparent',
              color: activeLayer === l.key ? 'var(--color-text)' : 'var(--color-muted)',
              border: activeLayer === l.key ? '1px solid var(--color-border)' : '1px solid transparent',
              fontWeight: activeLayer === l.key ? 600 : 400
            }}
          >
            {l.label}
          </button>
        ))}
      </div>

      {/* Bottom Left: Comprehensive Map Legend (H3, Closed Roads, Hospitals) */}
      <div className="panel-surface absolute bottom-3 left-3 p-3 z-10 max-w-[220px] backdrop-blur-md">
        <div className="text-[11px] font-semibold text-[var(--color-muted)] uppercase tracking-wider mb-2">
          Spatial Overlays
        </div>

        {/* Risk Tiers */}
        <div className="space-y-1 mb-2.5">
          {legendItems.map((item) => (
            <div key={item.label} className="flex items-center gap-2">
              <span
                className="w-3.5 h-3.5 rounded-sm border border-[var(--color-border)]"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-xs text-[var(--color-secondary)]">{item.label}</span>
            </div>
          ))}
        </div>

        {/* Closed Roads Indicator */}
        <div className="flex items-center gap-2 pt-2 border-t border-[var(--color-border)] mb-1.5">
          <span className="inline-block w-4 h-0 border-t-2 border-dashed border-rose-500" />
          <span className="text-xs font-medium text-rose-500">Closed Road (R-14)</span>
        </div>

        {/* Hospital Indicator */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className="w-3.5 h-3.5 rounded-full bg-rose-500 border border-white text-white text-[9px] flex items-center justify-center font-bold">
            +
          </span>
          <span className="text-xs font-medium text-[var(--color-text)]">Hospital Catchment</span>
        </div>

        {/* Ward Boundary Indicator */}
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-0 border-t-2 border-dashed border-sky-400" />
          <span className="text-xs text-sky-400 font-medium">Ward Boundary</span>
        </div>

        {/* Keyboard Helper Toggle */}
        <button
          type="button"
          onClick={() => setShowA11yHelp((p) => !p)}
          className="mt-2.5 pt-2 border-t border-[var(--color-border)] w-full text-[10px] text-blue-400 hover:text-blue-300 flex items-center justify-between"
          aria-expanded={showA11yHelp}
        >
          <span>⌨️ Keyboard Nav Help</span>
          <span>{showA11yHelp ? '▲' : '▼'}</span>
        </button>

        {showA11yHelp && (
          <div className="mt-2 text-[10px] text-[var(--color-muted)] space-y-1 bg-[var(--color-raised)] p-2 rounded border border-[var(--color-border)]">
            <div><strong className="text-[var(--color-text)]">&uarr;&darr;&larr;&rarr;:</strong> Pan Map</div>
            <div><strong className="text-[var(--color-text)]">+/-:</strong> Zoom In / Out</div>
            <div><strong className="text-[var(--color-text)]">0:</strong> Recenter Nagpur</div>
          </div>
        )}
      </div>
    </div>
  );
}
