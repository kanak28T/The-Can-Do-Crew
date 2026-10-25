import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import nagpurH3Grid from '../data/nagpur_h3_res9.json';
import { useAppStore } from '../store/useAppStore';

const NAGPUR_CENTER: [number, number] = [79.0882, 21.1458];

export default function MapView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const activeLayer = useAppStore((s) => s.activeLayer);
  const setActiveLayer = useAppStore((s) => s.setActiveLayer);
  const setSelectedCellH3 = useAppStore((s) => s.setSelectedCellH3);
  const theme = useAppStore((s) => s.theme);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    
    const styleUrl = theme === 'dark' 
      ? 'https://tiles.openfreemap.org/styles/dark'
      : 'https://tiles.openfreemap.org/styles/positron';
    
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center: NAGPUR_CENTER,
      zoom: 11,
      maxBounds: [[78.5, 20.5], [79.5, 21.5]],
    });
    mapRef.current = map;
    
    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    
    const recolourMap = () => {
      const style = map.getStyle();
      if (!style || !style.layers) return;
      
      if (theme === 'light') {
        style.layers.forEach((layer: any) => {
          if (layer.type === 'background') {
            map.setPaintProperty(layer.id, 'background-color', '#F8F9FA');
          } else if (layer.type === 'fill' && !layer.id.includes('h3-cells')) {
            map.setPaintProperty(layer.id, 'fill-color', '#E9ECEF');
          } else if (layer.type === 'line' && !layer.id.includes('h3-cells')) {
            map.setPaintProperty(layer.id, 'line-color', '#ADB5BD');
          } else if (layer.type === 'symbol' && layer.layout && layer.layout['text-field']) {
            map.setPaintProperty(layer.id, 'text-color', '#495057');
          }
        });
      }
    };
    
    map.on('load', () => {
      recolourMap();
      map.addSource('h3-cells', { type: 'geojson', data: nagpurH3Grid as any, generateId: true });
      map.addLayer({
        id: 'h3-cells-fill',
        type: 'fill',
        source: 'h3-cells',
        paint: {
          'fill-color': [
            'case',
            ['==', ['get', 'status'], 'high'], '#E8704F',
            ['==', ['get', 'status'], 'medium'], '#E3B341',
            ['==', ['get', 'status'], 'low'], '#5FA8A0',
            '#8A97A6',
          ],
          'fill-opacity': 0.35,
        },
      });
      map.addLayer({
        id: 'h3-cells-outline',
        type: 'line',
        source: 'h3-cells',
        paint: {
          'line-color': ['case', ['==', ['get', 'status'], 'high'], '#E8704F', 'rgba(255,255,255,0.15)'],
          'line-width': ['case', ['==', ['get', 'status'], 'high'], 1.5, 0.5],
        },
      });
    });
    map.on('click', 'h3-cells-fill', (e: any) => {
      if (e.features && e.features.length > 0) {
        const props = e.features[0].properties;
        setSelectedCellH3(props.h3_cell || props.cell);
      }
    });
    map.on('mousemove', 'h3-cells-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'h3-cells-fill', () => { map.getCanvas().style.cursor = ''; });
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  const layers = [{ key: 'risk', label: 'Risk' }, { key: 'roads', label: 'Roads' }, { key: 'hospitals', label: 'Hospitals' }, { key: 'feed_coverage', label: 'Feed' }];
  const legendItems = [{ label: 'High Risk', color: '#DC3545' }, { label: 'Watch', color: '#FFC107' }, { label: 'Low Risk', color: '#198754' }, { label: 'Unknown', color: '#6C757D' }];

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', backgroundColor: '#F8F9FA' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%', backgroundColor: '#F8F9FA' }} />
      <div className='panel-surface' style={{ position: 'absolute', top: 12, right: 12, padding: 8, display: 'flex', gap: 4, zIndex: 10 }}>
        {layers.map((l) => (
          <button key={l.key} onClick={() => setActiveLayer(l.key as any)} className='text-secondary' style={{ background: activeLayer === l.key ? 'var(--color-raised)' : 'none', border: '1px solid var(--color-border)', borderRadius: 4, padding: '4px 8px', fontSize: 12.5 }}>{l.label}</button>
        ))}
      </div>
      <div className='panel-surface' style={{ position: 'absolute', bottom: 12, left: 12, padding: 12, zIndex: 10 }}>
        <div className='text-muted' style={{ marginBottom: 8, fontWeight: 600 }}>Risk levels</div>
        {legendItems.map((item) => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ width: 16, height: 16, borderRadius: 2, backgroundColor: item.color, border: '1px solid var(--color-border)' }} />
            <span className='text-secondary' style={{ fontSize: 12.5 }}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
