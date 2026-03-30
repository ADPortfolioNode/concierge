import React, { useEffect, useState } from 'react';
import { makeApiUrl } from '@/config/activeServer';

interface Job {
  id: string;
  label?: string;
  status?: string;
  statusObj?: { status?: string; state?: string };
}

const POLL_INTERVAL = 3000;

const ProcessingBanner: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [showDetails, setShowDetails] = useState(false);
  const [offline, setOffline] = useState(false);
  const failCountRef = React.useRef(0);

  useEffect(() => {
    let mounted = true;
    const fetchJobs = async () => {
      try {
        const resp = await fetch(makeApiUrl('/api/v1/tasks'));
        if (!resp.ok) throw new Error(`Bad status ${resp.status}`);
        const body = await resp.json();
        const data: Job[] = (body.data as any) || [];
        if (mounted) {
          setJobs(data);
          setOffline(false);
        }
        failCountRef.current = 0;
      } catch {
        failCountRef.current += 1;
        if (mounted && failCountRef.current >= 3) {
          setOffline(true);
          setJobs([]);
        }
      }
    };
    fetchJobs();
    const iv = setInterval(fetchJobs, POLL_INTERVAL);
    return () => {
      mounted = false;
      clearInterval(iv);
    };
  }, []);

  if (offline) {
    return (
      <div style={{ background: 'rgba(220,38,38,0.1)', padding: '8px 16px', borderRadius: 6, marginBottom: 16 }}>
        <span style={{ color: '#f87171', fontSize: 13 }}>API backend unreachable. Please check server status and refresh.</span>
      </div>
    );
  }

  if (jobs.length === 0) return null;

  const runningJobs = jobs.filter((j) => {
    const status = j.status || j.statusObj?.status || j.statusObj?.state || '';
    return ['running', 'queued', 'PENDING', 'STARTED'].includes(status);
  });
  const running = runningJobs.length;
  const total = jobs.length;
  const percent = total ? Math.round(((total - running) / total) * 100) : 0;
  // elapsed time of first started job
  let elapsedText = '';
  const firstStarted = jobs.find((j) => j.started_at);
  if (firstStarted && firstStarted.started_at) {
    const delta = Math.max(0, Date.now() - new Date(firstStarted.started_at).getTime());
    const sec = Math.floor(delta / 1000);
    const minutes = Math.floor(sec / 60);
    const seconds = sec % 60;
    elapsedText = `${minutes}m${seconds}s elapsed`;
  }
  // first job label to show as title
  const firstLabel = jobs[0]?.label;

  return (
    <div
      style={{
        background: 'rgba(124,106,247,0.08)',
        padding: '8px 16px',
        borderRadius: 6,
        marginBottom: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {firstLabel && <span style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 600 }}>{firstLabel}</span>}
          <span style={{ fontSize: 13, color: '#e2e8f0' }}>
            {running} processing task{running !== 1 ? 's' : ''}
            {elapsedText && ` · ${elapsedText}`}
          </span>
        </div>
        <button
          onClick={() => setShowDetails((prev) => !prev)}
          style={{ fontSize: 12, background: 'none', border: 'none', color: '#7c6af7', cursor: 'pointer' }}
        >
          {showDetails ? 'hide' : 'show'} details
        </button>
      </div>
      <div
        style={{
          background: '#fff',
          height: 4,
          borderRadius: 2,
          overflow: 'hidden',
          marginTop: 4,
        }}
      >
        <div
          style={{
            width: `${percent}%`,
            height: '100%',
            background: '#7c6af7',
            transition: 'width 0.3s',
          }}
        />
      </div>
      {showDetails && (
        <div style={{ marginTop: 8, fontSize: 11, color: '#e2e8f0' }}>
          {jobs.map((j) => {
            const s = j.status || j.statusObj?.status || j.statusObj?.state || 'unknown';
            return (
              <div key={j.id} style={{ marginBottom: 2, wordBreak: 'break-word' }}>
                {j.label || j.id} – {s}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ProcessingBanner;
