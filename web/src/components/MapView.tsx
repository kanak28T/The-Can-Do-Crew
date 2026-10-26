import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import nagpurH3Grid from '../data/nagpur_h3_res9.json';
import nagpurWards from '../data/nagpur_wards.json';
import { useAppStore } from '../store/useAppStore';

const NAGPUR_CENTER: [number, number] = [79.0882, 21.1458];
const MAPTILER_KEY = (import.meta as any).env.VITE_MAPTILER_KEY || 'ZLrsbWlEexU5e2aU0mZB';

const getRasterMapStyle = (theme: 'dark' | 'light'): maplibregl.StyleSpecification => {
  const isDark = theme === 'dark';
  const tileUrl = `https://api.maptiler.com/maps/${isDark ? 'dataviz-dark' : 'streets-v2'}/256/{z}/{x}/{y}.png?key=${MAPTILER_KEY}`;

  return {
    version: 8,
    sources: {
      'maptiler-raster': {
        type: 'raster',
        tiles: [tileUrl],
        tileSize: 256,
        attribution: '&copy; <a href="https://www.maptiler.com/copyright/" target="_blank">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
      },
    },
    layers: [
      {
        id: 'maptiler-raster-layer',
        type: 'raster',
        source: 'maptiler-raster',
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  };
};

/* ── Layer color configurations ─────────────────────────────── */

type LayerKey = 'risk' | 'roads' | 'hospitals' | 'feed_coverage';

interface LayerConfig {
  fillColor: maplibregl.ExpressionSpecification;
  fillOpacity: number;
  outlineColor: maplibregl.ExpressionSpecification;
  outlineWidth: maplibregl.ExpressionSpecification;
  legend: { label: string; color: string }[];
  legendTitle: string;
}

const LAYER_CONFIGS: Record<LayerKey, LayerConfig> = {
  risk: {
    fillColor: [
      'case',
      ['==', ['get', 'status'], 'high'], '#ef4444',
      ['==', ['get', 'status'], 'medium'], '#f59e0b',
      ['==', ['get', 'status'], 'low'], '#10b981',
      '#94a3b8',
    ],
    fillOpacity: 0.45,
    outlineColor: [
      'case',
      ['==', ['get', 'status'], 'high'], '#ef4444',
      'rgba(0, 0, 0, 0.25)',
    ],
    outlineWidth: [
      'case',
      ['==', ['get', 'status'], 'high'], 1.8,
      0.6,
    ],
    legend: [
      { label: 'High Risk', color: '#ef4444' },
      { label: 'Watch', color: '#f59e0b' },
      { label: 'Low Risk', color: '#10b981' },
      { label: 'Unknown', color: '#94a3b8' },
    ],
    legendTitle: 'Risk Levels',
  },
  roads: {
    fillColor: [
      'interpolate', ['linear'],
      ['coalesce', ['get', 'risk'], 0.5],
      0, '#a7f3d0',
      0.3, '#6ee7b7',
      0.5, '#fbbf24',
      0.7, '#f97316',
      1.0, '#dc2626',
    ],
    fillOpacity: 0.5,
    outlineColor: [
      'interpolate', ['linear'],
      ['coalesce', ['get', 'risk'], 0.5],
      0, '#059669',
      0.5, '#d97706',
      1.0, '#b91c1c',
    ],
    outlineWidth: ['literal', 1.2] as any,
    legend: [
      { label: 'Clear', color: '#6ee7b7' },
      { label: 'Congested', color: '#fbbf24' },
      { label: 'Disrupted', color: '#f97316' },
      { label: 'Blocked', color: '#dc2626' },
    ],
    legendTitle: 'Road Stress',
  },
  hospitals: {
    fillColor: [
      'interpolate', ['linear'],
      ['coalesce', ['get', 'risk'], 0.5],
      0, '#dbeafe',
      0.3, '#60a5fa',
      0.5, '#a78bfa',
      0.7, '#c084fc',
      1.0, '#e879f9',
    ],
    fillOpacity: 0.5,
    outlineColor: [
      'interpolate', ['linear'],
      ['coalesce', ['get', 'risk'], 0.5],
      0, '#3b82f6',
      0.5, '#7c3aed',
      1.0, '#c026d3',
    ],
    outlineWidth: ['literal', 1.0] as any,
    legend: [
      { label: '< 1 km', color: '#60a5fa' },
      { label: '1-2 km', color: '#a78bfa' },
      { label: '2-3 km', color: '#c084fc' },
      { label: '> 3 km (Isolated)', color: '#e879f9' },
    ],
    legendTitle: 'Hospital Proximity',
  },
  feed_coverage: {
    fillColor: [
      'case',
      ['>=', ['coalesce', ['get', 'risk'], 0.5], 0.7], '#f87171',
      ['>=', ['coalesce', ['get', 'risk'], 0.5], 0.4], '#fbbf24',
      '#4ade80',
    ],
    fillOpacity: 0.4,
    outlineColor: [
      'case',
      ['>=', ['coalesce', ['get', 'risk'], 0.5], 0.7], '#ef4444',
      ['>=', ['coalesce', ['get', 'risk'], 0.5], 0.4], '#f59e0b',
      '#22c55e',
    ],
    outlineWidth: ['literal', 0.8] as any,
    legend: [
      { label: 'All Feeds Active', color: '#4ade80' },
      { label: 'Some Missing', color: '#fbbf24' },
      { label: 'Critical Gaps', color: '#f87171' },
    ],
    legendTitle: 'Feed Coverage',
  },
};

function addOverlays(map: maplibregl.Map) {
  try {
    if (!map.getSource('h3-cells')) {
      map.addSource('h3-cells', { 
        type: 'geojson', 
        data: nagpurH3Grid as any, 
        generateId: true 
      });

      map.addLayer({
        id: 'h3-cells-fill',
        type: 'fill',
        source: 'h3-cells',
        paint: {
          'fill-color': LAYER_CONFIGS.risk.fillColor,
          'fill-opacity': LAYER_CONFIGS.risk.fillOpacity,
        },
      });

      map.addLayer({
        id: 'h3-cells-outline',
        type: 'line',
        source: 'h3-cells',
        paint: {
          'line-color': LAYER_CONFIGS.risk.outlineColor,
          'line-width': LAYER_CONFIGS.risk.outlineWidth,
        },
      });
    }

    if (!map.getSource('nagpur-wards')) {
      map.addSource('nagpur-wards', {
        type: 'geojson',
        data: nagpurWards as any
      });

      map.addLayer({
        id: 'nagpur-wards-line',
        type: 'line',
        source: 'nagpur-wards',
        paint: {
          'line-color': '#0284c7',
          'line-width': 2.4,
          'line-dasharray': [3, 2],
          'line-opacity': 0.95
        }
      });

      map.addLayer({
        id: 'nagpur-wards-label',
        type: 'symbol',
        source: 'nagpur-wards',
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 11,
          'text-anchor': 'center',
          'text-allow-overlap': false
        },
        paint: {
          'text-color': '#0f172a',
          'text-halo-color': '#ffffff',
          'text-halo-width': 2.0
        }
      });
    }
  } catch (err) {
    console.warn('[Map Overlays] Notice:', err);
  }
}

function applyLayerStyle(map: maplibregl.Map, layer: LayerKey) {
  const config = LAYER_CONFIGS[layer];
  try {
    if (map.getLayer('h3-cells-fill')) {
      map.setPaintProperty('h3-cells-fill', 'fill-color', config.fillColor);
      map.setPaintProperty('h3-cells-fill', 'fill-opacity', config.fillOpacity);
    }
    if (map.getLayer('h3-cells-outline')) {
      map.setPaintProperty('h3-cells-outline', 'line-color', config.outlineColor);
      map.setPaintProperty('h3-cells-outline', 'line-width', config.outlineWidth);
    }
  } catch (err) {
    console.warn('[Map Layer Switch]', err);
  }
}

export default function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const activeLayer = useAppStore((s) => s.activeLayer);
  const setActiveLayer = useAppStore((s) => s.setActiveLayer);
  const setSelectedCellH3 = useAppStore((s) => s.setSelectedCellH3);
  const theme = useAppStore((s) => s.theme);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: getRasterMapStyle(theme),
      center: NAGPUR_CENTER,
      zoom: 12,
      minZoom: 9,
      maxBounds: [[78.5, 20.5], [79.6, 21.6]],
    });
    mapRef.current = map;

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    const ro = new ResizeObserver(() => {
      if (mapRef.current) mapRef.current.resize();
    });
    ro.observe(containerRef.current);

    map.on('load', () => {
      addOverlays(map);
    });

    map.on('style.load', () => {
      addOverlays(map);
    });

    map.on('click', 'h3-cells-fill', (e: any) => {
      if (e.features && e.features.length > 0) {
        const props = e.features[0].properties;
        const cellId = props.h3_cell || props.cell;
        setSelectedCellH3(cellId);

        // Show popup with cell info
        const risk = props.risk ?? 0;
        const status = props.status ?? 'unknown';
        new maplibregl.Popup({ closeOnClick: true, maxWidth: '220px' })
          .setLngLat(e.lngLat)
          .setHTML(`
            <div style="font-family:Inter,system-ui,sans-serif;font-size:12px;line-height:1.5">
              <div style="font-weight:700;margin-bottom:4px">${cellId.substring(0,12)}…</div>
              <div>Status: <strong style="color:${status === 'high' ? '#ef4444' : status === 'medium' ? '#f59e0b' : '#10b981'}">${status.toUpperCase()}</strong></div>
              <div>Risk: <strong>${(risk * 100).toFixed(0)}%</strong></div>
              ${props.ward ? `<div style="color:#64748b;margin-top:2px">${props.ward}</div>` : ''}
            </div>
          `)
          .addTo(map);
      }
    });

    map.on('mousemove', 'h3-cells-fill', () => { 
      map.getCanvas().style.cursor = 'pointer'; 
    });
    map.on('mouseleave', 'h3-cells-fill', () => { 
      map.getCanvas().style.cursor = ''; 
    });

    return () => { 
      ro.disconnect();
      map.remove(); 
      mapRef.current = null; 
    };
  }, []);

  // Update style when theme changes
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.setStyle(getRasterMapStyle(theme));
  }, [theme]);

  // ── Apply layer coloring when activeLayer changes ──
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    
    // If map is loaded and layers exist, apply immediately
    if (map.isStyleLoaded() && map.getLayer('h3-cells-fill')) {
      applyLayerStyle(map, activeLayer);
    } else {
      // Otherwise wait for style to load
      const handler = () => {
        if (map.getLayer('h3-cells-fill')) {
          applyLayerStyle(map, activeLayer);
        }
      };
      map.once('idle', handler);
    }
  }, [activeLayer]);

  const layers: { key: LayerKey; label: string; icon: string }[] = [
    { key: 'risk', label: 'Risk', icon: '🔴' }, 
    { key: 'roads', label: 'Roads', icon: '🛣️' }, 
    { key: 'hospitals', label: 'Hospitals', icon: '🏥' }, 
    { key: 'feed_coverage', label: 'Feed', icon: '📡' }
  ];

  const currentConfig = LAYER_CONFIGS[activeLayer];
  
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: '#e2e8f0' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Layer selector on top left (away from nav controls) */}
      <div 
        style={{ 
          position: 'absolute', 
          top: 10, 
          left: 10, 
          padding: '3px 4px', 
          display: 'flex', 
          gap: 3, 
          zIndex: 10,
          borderRadius: '8px',
          border: '1px solid rgba(0,0,0,0.12)',
          backgroundColor: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}
      >
        {layers.map((l) => (
          <button 
            key={l.key} 
            type="button"
            onClick={() => setActiveLayer(l.key)} 
            style={{ 
              background: activeLayer === l.key ? '#1d4ed8' : 'transparent', 
              border: 'none',
              borderRadius: '5px', 
              padding: '5px 10px', 
              fontSize: '11px',
              fontWeight: 600,
              color: activeLayer === l.key ? '#fff' : '#374151',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <span style={{ fontSize: '10px' }}>{l.icon}</span>
            {l.label}
          </button>
        ))}
      </div>

      {/* Dynamic Legend based on active layer */}
      <div 
        style={{ 
          position: 'absolute', 
          bottom: 10, 
          left: 10, 
          padding: '8px 10px', 
          zIndex: 10,
          borderRadius: '8px',
          border: '1px solid rgba(0,0,0,0.1)',
          backgroundColor: 'rgba(255,255,255,0.95)',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          minWidth: '110px',
        }}
      >
        <div style={{ marginBottom: 4, fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', color: '#64748b', letterSpacing: '0.04em' }}>
          {currentConfig.legendTitle}
        </div>
        {currentConfig.legend.map((item) => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: item.color, flexShrink: 0 }} />
            <span style={{ fontSize: '10.5px', color: '#475569' }}>{item.label}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, paddingTop: 4, borderTop: '1px solid rgba(0,0,0,0.08)' }}>
          <span style={{ display: 'inline-block', width: 10, height: 0, borderTop: '2px dashed #0284c7' }} />
          <span style={{ fontSize: '10.5px', color: '#0284c7', fontWeight: 600 }}>Ward Overlay</span>
        </div>
      </div>
    </div>
  );
}
