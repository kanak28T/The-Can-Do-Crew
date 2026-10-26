import type { DispatchItem } from '../types';

export type LossPattern = 'random' | 'domain' | 'area';
export type DockTab = 'dispatch' | 'causal' | 'privacy' | 'evaluation';

export type VoiceAction =
  | { type: 'sim_start' }
  | { type: 'sim_pause' }
  | { type: 'sim_reset' }
  | { type: 'sim_speed'; value: number }
  | { type: 'feed_cut'; value: number }
  | { type: 'loss_pattern'; value: LossPattern }
  | { type: 'dock_tab'; value: DockTab }
  | { type: 'dock_expand' }
  | { type: 'dock_collapse' }
  | { type: 'theme'; value: 'dark' | 'light' | 'toggle' }
  | { type: 'dispatch'; status: 'approved' | 'rejected'; target: 'first' | 'all' | string }
  | { type: 'unknown' };

const NUMBER_WORDS: Record<string, number> = {
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5,
  six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  fifteen: 15, twenty: 20, twentyfive: 25, thirty: 30,
  forty: 40, fifty: 50, sixty: 60,
};

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9%.\s-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractNumber(text: string): number | null {
  const digit = text.match(/(\d+(?:\.\d+)?)/);
  if (digit) return Number(digit[1]);
  const compact = text.replace(/\s+/g, '');
  for (const [word, value] of Object.entries(NUMBER_WORDS)) {
    if (compact.includes(word)) return value;
  }
  return null;
}

export function parseVoiceCommand(raw: string): VoiceAction {
  const text = normalize(raw);
  if (!text) return { type: 'unknown' };

  if (/\b(start|run|begin|resume)\b/.test(text) && !/\bpause\b/.test(text)) {
    return { type: 'sim_start' };
  }
  if (/\b(pause|hold|stop sim)\b/.test(text) || text === 'pause' || text === 'stop') {
    return { type: 'sim_pause' };
  }
  if (/\b(reset|clear sim|restart)\b/.test(text)) {
    return { type: 'sim_reset' };
  }

  if (/\b(speed|playback)\b/.test(text)) {
    const value = extractNumber(text);
    if (value != null) {
      return { type: 'sim_speed', value: Math.min(5, Math.max(0.5, value)) };
    }
  }

  if (/\b(cut|feed|feeds|loss)\b/.test(text) && /\b(percent|%|cut|feeds?)\b/.test(text) && !/\bpattern\b/.test(text)) {
    const value = extractNumber(text);
    if (value != null) {
      return { type: 'feed_cut', value: Math.min(60, Math.max(0, Math.round(value))) };
    }
  }

  if (/\b(pattern|loss pattern|by domain|by area|random)\b/.test(text)) {
    if (/\bdomain\b/.test(text)) return { type: 'loss_pattern', value: 'domain' };
    if (/\barea\b/.test(text)) return { type: 'loss_pattern', value: 'area' };
    if (/\brandom\b/.test(text)) return { type: 'loss_pattern', value: 'random' };
  }

  if (/\b(causal|graph)\b/.test(text)) return { type: 'dock_tab', value: 'causal' };
  if (/\bprivacy\b/.test(text)) return { type: 'dock_tab', value: 'privacy' };
  if (/\b(evaluation|eval|iou)\b/.test(text)) return { type: 'dock_tab', value: 'evaluation' };
  if (/\bdispatch\b/.test(text) && !/\bapprove\b|\breject\b/.test(text)) {
    return { type: 'dock_tab', value: 'dispatch' };
  }

  if (/\bexpand\b/.test(text)) return { type: 'dock_expand' };
  if (/\bcollapse\b/.test(text)) return { type: 'dock_collapse' };

  if (/\bdark\b/.test(text)) return { type: 'theme', value: 'dark' };
  if (/\blight\b/.test(text)) return { type: 'theme', value: 'light' };
  if (/\btheme\b/.test(text)) return { type: 'theme', value: 'toggle' };

  if (/\b(approve|reject)\b/.test(text)) {
    const status = /\breject\b/.test(text) ? 'rejected' : 'approved';
    const idMatch = text.match(/\b(dsp[- ]?\d+)\b/);
    if (idMatch) {
      return { type: 'dispatch', status, target: idMatch[1].replace(/\s+/g, '-') };
    }
    if (/\ball\b/.test(text)) return { type: 'dispatch', status, target: 'all' };
    return { type: 'dispatch', status, target: 'first' };
  }

  return { type: 'unknown' };
}

export function describeAction(action: VoiceAction): string {
  switch (action.type) {
    case 'sim_start': return 'Starting simulation';
    case 'sim_pause': return 'Pausing simulation';
    case 'sim_reset': return 'Resetting simulation';
    case 'sim_speed': return `Speed set to ${action.value}x`;
    case 'feed_cut': return `Feed cut set to ${action.value}%`;
    case 'loss_pattern': return `Loss pattern: ${action.value}`;
    case 'dock_tab': return `Opened ${action.value}`;
    case 'dock_expand': return 'Dock expanded';
    case 'dock_collapse': return 'Dock collapsed';
    case 'theme': return action.value === 'toggle' ? 'Theme toggled' : `${action.value} theme`;
    case 'dispatch': return `${action.status === 'approved' ? 'Approved' : 'Rejected'} ${action.target === 'all' ? 'all proposed' : action.target === 'first' ? 'first proposed' : action.target}`;
    default: return 'Command not recognized. Try “start simulation” or “cut feeds 30 percent”.';
  }
}

export function resolveDispatchIds(
  dispatches: DispatchItem[],
  target: 'first' | 'all' | string,
): string[] {
  const proposed = dispatches.filter((d) => d.status === 'proposed');
  if (target === 'all') return proposed.map((d) => d.id);
  if (target === 'first') return proposed[0] ? [proposed[0].id] : [];
  const wanted = target.toLowerCase();
  const match = dispatches.find((d) => d.id.toLowerCase() === wanted);
  return match ? [match.id] : [];
}

export const VOICE_EXAMPLES = [
  'start simulation',
  'pause',
  'reset',
  'speed 2',
  'cut feeds 30 percent',
  'loss pattern by area',
  'open causal graph',
  'approve first',
  'dark mode',
];
