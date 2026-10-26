import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  Panel
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useAppStore } from '../store/useAppStore';
import type { Driver } from '../types';

interface CausalGraphProps {
  drivers?: Driver[];
}

// Default expert hypothesis causal nodes
const INITIAL_NODES: Node[] = [
  {
    id: 'road_closure',
    type: 'input',
    position: { x: 50, y: 30 },
    data: {
      label: '🚧 Road Closure / Inundation',
      domain: 'road',
      baselineDelta: 0.35,
      description: 'Major arterial corridors submerged on Wardha Road'
    },
    style: {
      background: 'rgba(239, 68, 68, 0.12)',
      color: '#ef4444',
      border: '1.5px solid rgba(239, 68, 68, 0.5)',
      borderRadius: '8px',
      padding: '10px 14px',
      fontSize: '12px',
      fontWeight: 600,
      width: 220
    }
  },
  {
    id: 'power_outage',
    type: 'input',
    position: { x: 50, y: 160 },
    data: {
      label: '⚡ Substation 33kV Drop',
      domain: 'power',
      baselineDelta: 0.45,
      description: 'Grid feeder tripped, voltage sag < 190V'
    },
    style: {
      background: 'rgba(245, 158, 11, 0.12)',
      color: '#f59e0b',
      border: '1.5px solid rgba(245, 158, 11, 0.5)',
      borderRadius: '8px',
      padding: '10px 14px',
      fontSize: '12px',
      fontWeight: 600,
      width: 220
    }
  },
  {
    id: 'transit_loss',
    position: { x: 340, y: 30 },
    data: {
      label: '🚌 Transit Frequency Loss',
      domain: 'transit',
      baselineDelta: 0.40,
      description: 'Aapli Bus route 4 & 6 cancelled, bus headways +45m'
    },
    style: {
      background: 'rgba(56, 189, 248, 0.12)',
      color: '#38bdf8',
      border: '1.5px solid rgba(56, 189, 248, 0.5)',
      borderRadius: '8px',
      padding: '10px 14px',
      fontSize: '12px',
      fontWeight: 600,
      width: 220
    }
  },
  {
    id: 'water_failure',
    position: { x: 340, y: 160 },
    data: {
      label: '💧 Booster Pump Failure',
      domain: 'water',
      baselineDelta: 0.25,
      description: 'Submersible pumps offline due to voltage cutoff'
    },
    style: {
      background: 'rgba(16, 185, 129, 0.12)',
      color: '#10b981',
      border: '1.5px solid rgba(16, 185, 129, 0.5)',
      borderRadius: '8px',
      padding: '10px 14px',
      fontSize: '12px',
      fontWeight: 600,
      width: 220
    }
  },
  {
    id: 'comms_congestion',
    position: { x: 340, y: 280 },
    data: {
      label: '📡 Cellular BTS Congestion',
      domain: 'comms',
      baselineDelta: 0.20,
      description: 'Tower battery drain & packet loss > 35%'
    },
    style: {
      background: 'rgba(168, 85, 247, 0.12)',
      color: '#c084fc',
      border: '1.5px solid rgba(168, 85, 247, 0.5)',
      borderRadius: '8px',
      padding: '10px 14px',
      fontSize: '12px',
      fontWeight: 600,
      width: 220
    }
  },
  {
    id: 'hospital_isolation',
    type: 'output',
    position: { x: 640, y: 90 },
    data: {
      label: '🏥 Critical Healthcare Isolation',
      domain: 'health',
      baselineDelta: 0.65,
      description: 'Ambulance travel time > 30m, ICU supply risk'
    },
    style: {
      background: 'rgba(239, 68, 68, 0.18)',
      color: '#f87171',
      border: '2px solid rgba(239, 68, 68, 0.7)',
      borderRadius: '8px',
      padding: '12px 16px',
      fontSize: '13px',
      fontWeight: 700,
      width: 240,
      boxShadow: '0 4px 15px -1px rgba(239, 68, 68, 0.25)'
    }
  }
];

// Initial directed causal edges with expert weights
const INITIAL_EDGES: Edge[] = [
  {
    id: 'e-road-transit',
    source: 'road_closure',
    target: 'transit_loss',
    label: 'w = 0.52',
    animated: true,
    style: { stroke: '#ef4444', strokeWidth: 2 },
    labelStyle: { fill: '#ef4444', fontWeight: 600, fontSize: 11 },
    labelBgStyle: { fill: 'var(--color-surface)', fillOpacity: 0.85 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' }
  },
  {
    id: 'e-transit-hospital',
    source: 'transit_loss',
    target: 'hospital_isolation',
    label: 'w = 0.64',
    animated: true,
    style: { stroke: '#38bdf8', strokeWidth: 2.5 },
    labelStyle: { fill: '#38bdf8', fontWeight: 600, fontSize: 11 },
    labelBgStyle: { fill: 'var(--color-surface)', fillOpacity: 0.85 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#38bdf8' }
  },
  {
    id: 'e-power-water',
    source: 'power_outage',
    target: 'water_failure',
    label: 'w = 0.78',
    animated: true,
    style: { stroke: '#f59e0b', strokeWidth: 2.5 },
    labelStyle: { fill: '#f59e0b', fontWeight: 600, fontSize: 11 },
    labelBgStyle: { fill: 'var(--color-surface)', fillOpacity: 0.85 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' }
  },
  {
    id: 'e-power-hospital',
    source: 'power_outage',
    target: 'hospital_isolation',
    label: 'w = 0.71',
    animated: true,
    style: { stroke: '#f59e0b', strokeWidth: 2.5 },
    labelStyle: { fill: '#f59e0b', fontWeight: 600, fontSize: 11 },
    labelBgStyle: { fill: 'var(--color-surface)', fillOpacity: 0.85 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#f59e0b' }
  },
  {
    id: 'e-power-comms',
    source: 'power_outage',
    target: 'comms_congestion',
    label: 'w = 0.44',
    animated: true,
    style: { stroke: '#c084fc', strokeWidth: 1.5 },
    labelStyle: { fill: '#c084fc', fontWeight: 600, fontSize: 11 },
    labelBgStyle: { fill: 'var(--color-surface)', fillOpacity: 0.85 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#c084fc' }
  }
];

export default function CausalGraph({ drivers }: CausalGraphProps) {
  const theme = useAppStore((s) => s.theme);
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);

  const [selectedElement, setSelectedElement] = useState<string | null>(null);

  // Dynamically highlight edges if zone drivers are passed
  useEffect(() => {
    if (!drivers || drivers.length === 0) return;

    setEdges((currentEdges) =>
      currentEdges.map((edge) => {
        const matchingDriver = drivers.find((d) =>
          d.key.toLowerCase().includes(edge.source.replace('_', '')) ||
          d.label.toLowerCase().includes(edge.source.replace('_', ''))
        );
        if (matchingDriver) {
          return {
            ...edge,
            label: `w = ${matchingDriver.delta > 0 ? '+' : ''}${Math.round(matchingDriver.delta * 100)}%`,
            style: { ...edge.style, strokeWidth: 3.5 },
            animated: true
          };
        }
        return edge;
      })
    );
  }, [drivers, setEdges]);

  const onConnect = useCallback(
    (params: Connection) =>
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            animated: true,
            label: 'w = 0.50',
            style: { stroke: 'var(--color-accent)', strokeWidth: 2 },
            markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--color-accent)' }
          },
          eds
        )
      ),
    [setEdges]
  );

  return (
    <div className="w-full h-full relative rounded overflow-hidden bg-[var(--color-surface)] border border-[var(--color-border)]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node) => setSelectedElement(`Node: ${node.data.label}`)}
        onEdgeClick={(_, edge) => setSelectedElement(`Edge: ${edge.source} → ${edge.target} (${edge.label || 'No weight'})`)}
        fitView
        attributionPosition="bottom-right"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color={theme === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'}
        />
        <Controls className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded text-[var(--color-text)] shadow-sm" />
        <MiniMap
          nodeColor={(n) => (n.type === 'output' ? '#ef4444' : n.type === 'input' ? '#f59e0b' : '#38bdf8')}
          className="bg-[var(--color-raised)] border border-[var(--color-border)] rounded"
          maskColor={theme === 'dark' ? 'rgba(15, 23, 32, 0.65)' : 'rgba(240, 240, 240, 0.65)'}
        />
        
        <Panel position="top-left" className="bg-[var(--color-surface)]/95 backdrop-blur-md p-2.5 rounded border border-[var(--color-border)] text-xs shadow-md max-w-[420px]">
          <div className="flex items-center justify-between gap-2 mb-1">
            <div className="font-semibold text-[var(--color-text)] flex items-center gap-1.5 text-xs">
              <span>🕸️ Multi-Hop Causal Graph</span>
              <span className="text-[10px] text-emerald-400 bg-emerald-500/15 px-1.5 py-0.5 rounded font-mono">
                Editable DAG
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-[var(--color-secondary)] pt-1 border-t border-[var(--color-border)]">
            <span className="flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-red-500/80" />
              Root Stressor
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-sky-500/80" />
              Intermediary
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-2 h-2 rounded-full bg-rose-600" />
              Critical Impact
            </span>
          </div>
          {selectedElement && (
            <div className="mt-1 text-[10.5px] text-[var(--color-accent)] font-medium">
              Selected: {selectedElement}
            </div>
          )}
        </Panel>
      </ReactFlow>
    </div>
  );
}
