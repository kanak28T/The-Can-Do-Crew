import { useAppStore } from '../store/useAppStore';

export default function LiveNumbers() {
  const { highZones, watchZones, unknownCells, eventDelay } = useAppStore();

  const items = [
    { label: 'High zones', value: highZones, color: 'var(--color-high)' },
    { label: 'Watch zones', value: watchZones, color: 'var(--color-watch)' },
    { label: 'Unknown cells', value: unknownCells, color: 'var(--color-unknown)' },
    { label: 'Event delay', value: eventDelay.toFixed(1) + 's', color: 'var(--color-accent)' },
  ];

  return (
    <div className="panel-surface" style={{ padding: 16 }}>
      <div className="panel-title" style={{ marginBottom: 12 }}>Live numbers</div>
      <div className="grid grid-cols-2 gap-3">
        {items.map((item) => (
          <div key={item.label} className="panel-raised" style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span className="text-muted" style={{ fontSize: 12.5 }}>{item.label}</span>
            <span className="text-big" style={{ color: item.color }}>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

