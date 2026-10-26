import { useAppStore } from '../store/useAppStore';
import DispatchLog from './DispatchLog';
import CausalGraph from './CausalGraph';
import PrivacyChart from './PrivacyChart';
import EvalChart from './EvalChart';

export default function BottomDock() {
  const dockCollapsed = useAppStore((s) => s.dockCollapsed);
  const toggleDock = useAppStore((s) => s.toggleDock);
  const dockTab = useAppStore((s) => s.dockTab);
  const setDockTab = useAppStore((s) => s.setDockTab);
  const dispatches = useAppStore((s) => s.dispatches);

  return (
    <div
      className="absolute bottom-0 left-0 right-0 z-20 flex flex-col transition-all duration-300 backdrop-blur-md shadow-2xl border-t overflow-hidden"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        height: dockCollapsed ? '42px' : '320px',
        maxHeight: 'calc(100% - 60px)',
      }}
    >
      {/* Dock Header & Tab Navigation */}
      <div
        className="flex items-center justify-between px-4 h-[42px] border-b select-none flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-muted)]">
            Intelligence Dock
          </span>
          <div className="flex items-center bg-[var(--color-raised)] p-0.5 rounded border border-[var(--color-border)] ml-3">
            <button
              type="button"
              onClick={() => { setDockTab('dispatch'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'dispatch'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              ⚡ Dispatch Actions ({dispatches.length})
            </button>
            <button
              type="button"
              onClick={() => { setDockTab('causal'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'causal'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              🕸️ Causal Graph
            </button>
            <button
              type="button"
              onClick={() => { setDockTab('privacy'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'privacy'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              🛡️ Privacy Red-Team
            </button>
            <button
              type="button"
              onClick={() => { setDockTab('evaluation'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'evaluation'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              🎯 IoU Evaluation
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={toggleDock}
          className="text-xs font-medium px-2 py-1 rounded bg-[var(--color-raised)] text-[var(--color-secondary)] hover:text-[var(--color-text)] border border-[var(--color-border)] flex items-center gap-1.5 transition-colors"
          title={dockCollapsed ? 'Expand dock' : 'Collapse dock'}
        >
          {dockCollapsed ? '▲ Expand' : '▼ Collapse'}
        </button>
      </div>

      {/* Dock Content Body with overflow-y: auto and min-h-0 */}
      {!dockCollapsed && (
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 text-[var(--color-text)] min-h-0">
          {dockTab === 'dispatch' && <DispatchLog />}
          {dockTab === 'causal' && (
            <div className="h-full w-full min-h-[220px]">
              <CausalGraph />
            </div>
          )}
          {dockTab === 'privacy' && <PrivacyChart />}
          {dockTab === 'evaluation' && <EvalChart />}
        </div>
      )}
    </div>
  );
}
