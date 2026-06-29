import React, { useEffect, useState } from 'react';
import { makeApiUrl } from '@/config/activeServer';

interface Job {
  id: string;
  label?: string;
  status?: string;
  statusObj?: { status?: string; state?: string };
  started_at?: string;
}

const POLL_INTERVAL = 3000;

const ProcessingBanner: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchJobs = async () => {
      try {
        const resp = await fetch(makeApiUrl('/api/v1/tasks'));
        if (!resp.ok) return;
        const body = (await resp.json()) as { data?: Job[] | unknown } | null;
        const raw = body?.data;
        const data: Job[] = Array.isArray(raw) ? raw : [];
        if (mounted) setJobs(data);
      } catch {
        // ignore network errors
      }
    };
    fetchJobs();
    const iv = setInterval(fetchJobs, POLL_INTERVAL);
    return () => {
      mounted = false;
      clearInterval(iv);
    };
  }, []);

  if (jobs.length === 0) return null;

  const runningJobs = jobs.filter((j) => {
    const s = j.status || j.statusObj?.status || j.statusObj?.state || '';
    return ['running', 'queued', 'PENDING', 'STARTED'].includes(s);
  });
  const running = runningJobs.length;
  const total = jobs.length;
  const percent = total ? Math.round(((total - running) / total) * 100) : 0;
  let elapsedText = '';
  const firstStarted = jobs.find((j) => j.started_at);
  if (firstStarted && firstStarted.started_at) {
    const delta = Math.max(0, Date.now() - new Date(firstStarted.started_at).getTime());
    const sec = Math.floor(delta / 1000);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    elapsedText = `${m}m${s}s elapsed`;
  }
  const firstLabel = jobs[0]?.label;

  return (
    <div
      style={{
        background: '#EFF6FF',
        border: '1px solid #BFDBFE',
        padding: '8px 16px',
        borderRadius: 8,
        marginBottom: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {firstLabel && <span style={{ fontSize: 13, color: '#0F172A', fontWeight: 600 }}>{firstLabel}</span>}
          <span style={{ fontSize: 13, color: '#0F172A' }}>
            {running} processing task{running !== 1 ? 's' : ''}
            {elapsedText && ` · ${elapsedText}`}
          </span>
        </div>
        <button
          onClick={() => setShowDetails((s) => !s)}
          style={{ fontSize: 12, background: 'none', border: 'none', color: '#2563EB', cursor: 'pointer', fontWeight: 600 }}
        >
          {showDetails ? 'hide' : 'show'} details
        </button>
      </div>
      <div
        style={{
          background: '#DBEAFE',
          height: 4,
          borderRadius: 2,
          overflow: 'hidden',
          marginTop: 6,
        }}
      >
        <div
          style={{
            width: `${percent}%`,
            height: '100%',
            background: '#2563EB',
            transition: 'width 0.3s',
          }}
        />
      </div>
      {showDetails && (
        <div style={{ marginTop: 8, fontSize: 11, color: '#475569' }}>
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
