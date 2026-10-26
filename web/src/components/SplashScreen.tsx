import { useEffect, useState } from 'react';

interface SplashScreenProps {
  onDismiss?: () => void;
}

export default function SplashScreen({ onDismiss }: SplashScreenProps) {
  const [phase, setPhase] = useState<'loading' | 'fading' | 'hidden'>('loading');
  const [progress, setProgress] = useState(15);
  const [statusText, setStatusText] = useState('Initializing H3 spatial hex index (Res 8 & 9)...');

  useEffect(() => {
    const t1 = setTimeout(() => {
      setProgress(48);
      setStatusText('Loading Nagpur ward boundaries & critical transport corridors...');
    }, 400);

    const t2 = setTimeout(() => {
      setProgress(82);
      setStatusText('Connecting real-time SSE stream & Bayesian causal graph...');
    }, 900);

    const t3 = setTimeout(() => {
      setProgress(100);
      setStatusText('All spatial feeds calibrated & ready.');
    }, 1400);

    const t4 = setTimeout(() => {
      setPhase('fading');
    }, 1750);

    const t5 = setTimeout(() => {
      setPhase('hidden');
      if (onDismiss) onDismiss();
    }, 2350);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      clearTimeout(t5);
    };
  }, [onDismiss]);

  if (phase === 'hidden') return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Application loading screen"
      className={`fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-950/95 backdrop-blur-md transition-opacity duration-700 ease-out ${
        phase === 'fading' ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{
        backgroundImage: `radial-gradient(circle at 50% 30%, rgba(13, 110, 253, 0.15), transparent 70%), 
                          linear-gradient(rgba(10, 15, 26, 0.94), rgba(5, 8, 15, 0.98))`
      }}
    >
      <div className="relative max-w-md w-full bg-slate-900/90 border border-slate-700/60 rounded-xl p-8 shadow-2xl text-center flex flex-col items-center">
        {/* Glowing Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-5">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
          Nagpur Municipal Geospatial Engine
        </div>

        {/* Title */}
        <h1 className="text-2xl font-bold tracking-tight text-white mb-2 flex items-center gap-2">
          <span>URBANPULSE</span>
          <span className="text-blue-500 text-sm px-2 py-0.5 rounded bg-blue-500/20 font-mono">v1.2</span>
        </h1>
        <p className="text-xs text-slate-400 mb-6 leading-relaxed">
          Dynamic multi-hazard cascade modeling, real-time telemetry fusion, and autonomous emergency dispatch prioritization.
        </p>

        {/* Progress Bar */}
        <div className="w-full bg-slate-800 rounded-full h-2 mb-3 overflow-hidden border border-slate-700">
          <div
            className="bg-gradient-to-r from-blue-600 via-indigo-500 to-emerald-400 h-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Status Line */}
        <div className="text-[11px] text-slate-400 font-mono flex items-center justify-between w-full mb-6">
          <span className="truncate">{statusText}</span>
          <span className="ml-2 font-bold text-blue-400">{progress}%</span>
        </div>

        {/* Quick Skip Button */}
        <button
          type="button"
          onClick={() => {
            setPhase('fading');
            setTimeout(() => {
              setPhase('hidden');
              if (onDismiss) onDismiss();
            }, 600);
          }}
          className="text-xs text-slate-400 hover:text-slate-200 hover:underline transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
        >
          Skip Intro &rarr;
        </button>
      </div>
    </div>
  );
}
