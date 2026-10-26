import { useCallback, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../lib/api';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import {
  VOICE_EXAMPLES,
  describeAction,
  parseVoiceCommand,
  resolveDispatchIds,
} from '../lib/voiceCommands';

export default function VoiceCommandBar() {
  const [draft, setDraft] = useState('');
  const [status, setStatus] = useState('Say a command, or type one and press Enter');
  const [failed, setFailed] = useState(false);

  const runCommand = useCallback(async (raw: string) => {
    const text = raw.trim();
    if (!text) return;
    const action = parseVoiceCommand(text);
    const message = describeAction(action);
    setFailed(action.type === 'unknown');
    setStatus(message);
    setDraft('');

    const s = useAppStore.getState();

    switch (action.type) {
      case 'sim_start':
        s.setSimRunning(true);
        s.setSimPaused(false);
        api.simStart().catch(() => {});
        break;
      case 'sim_pause':
        s.setSimPaused(true);
        api.simPause().catch(() => {});
        break;
      case 'sim_reset':
        s.setSimRunning(false);
        s.setSimPaused(false);
        s.setFeedCutPct(0);
        api.simReset().catch(() => {});
        break;
      case 'sim_speed':
        s.setSimSpeed(action.value);
        break;
      case 'feed_cut':
        s.setFeedCutPct(action.value);
        api.simFeedLoss(action.value, s.lossPattern).catch(() => {});
        break;
      case 'loss_pattern':
        s.setLossPattern(action.value);
        api.simFeedLoss(s.feedCutPct, action.value).catch(() => {});
        break;
      case 'dock_tab':
        if (s.dockCollapsed) s.toggleDock();
        s.setDockTab(action.value);
        break;
      case 'dock_expand':
        if (s.dockCollapsed) s.toggleDock();
        break;
      case 'dock_collapse':
        if (!s.dockCollapsed) s.toggleDock();
        break;
      case 'theme':
        if (action.value === 'toggle' || s.theme !== action.value) s.toggleTheme();
        break;
      case 'dispatch': {
        const ids = resolveDispatchIds(s.dispatches, action.target);
        if (ids.length === 0) {
          setFailed(true);
          setStatus('No matching proposed dispatch to update');
          break;
        }
        for (const id of ids) {
          s.updateDispatchStatus(id, action.status);
          if (action.status === 'approved') api.approveDispatch(id).catch(() => {});
          else api.rejectDispatch(id).catch(() => {});
        }
        break;
      }
      default:
        break;
    }
  }, []);

  const { supported, listening, interim, error, toggle } = useSpeechRecognition(runCommand);

  const displayValue = listening && interim ? interim : draft;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void runCommand(draft);
      }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        flex: 1,
        maxWidth: 520,
        margin: '0 16px',
      }}
    >
      <button
        type="button"
        onClick={toggle}
        disabled={!supported}
        title={supported ? (listening ? 'Stop listening' : 'Start voice input') : 'Voice input needs Chrome or Edge'}
        aria-pressed={listening}
        aria-label={listening ? 'Stop voice input' : 'Start voice input'}
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          border: 'none',
          cursor: supported ? 'pointer' : 'not-allowed',
          backgroundColor: listening ? '#DC3545' : '#0D6EFD',
          color: 'white',
          fontSize: 16,
          flexShrink: 0,
          boxShadow: listening ? '0 0 0 4px rgba(220,53,69,0.25)' : 'none',
        }}
      >
        {listening ? '■' : '🎤'}
      </button>
      <div style={{ flex: 1, minWidth: 0 }}>
        <input
          value={displayValue}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={supported ? 'Voice or type a command…' : 'Type a command…'}
          aria-label="Operator command"
          title={`Examples: ${VOICE_EXAMPLES.join(', ')}`}
          style={{
            width: '100%',
            height: 36,
            borderRadius: 8,
            border: `1px solid ${listening ? '#DC3545' : '#DEE2E6'}`,
            padding: '0 12px',
            fontSize: 13,
            backgroundColor: listening ? '#FFF5F5' : '#F8F9FA',
            color: '#212529',
            outline: 'none',
          }}
        />
        <div
          style={{
            fontSize: 11,
            marginTop: 2,
            color: failed || error ? '#DC3545' : '#6C757D',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {error || (listening ? 'Listening…' : status)}
        </div>
      </div>
    </form>
  );
}
