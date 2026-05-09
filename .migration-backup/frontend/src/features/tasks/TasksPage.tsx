import React, { useEffect, useRef, useState } from 'react';
import { getTasks } from '@/api/taskService';
import { submitAgentJob, getJobStatus } from '@/api/jobService';
import type { JobStatus } from '@/api/jobService';
import SamplePrompt from '@/components/primitives/SamplePrompt';
import TimelineHero from '@/components/TimelineHero';
import PageSection from '@/components/PageSection';

// Task type reference table
const TASK_TYPES = [
  { type: 'read_file',        badge: '#0891b2', payload: '{ "upload_id": "<id>", "filename": "notes.txt" }',                            desc: 'Read text from an uploaded file.' },
  { type: 'write_file',       badge: '#059669', payload: '{ "upload_id": "<id>", "filename": "out.txt", "content": "Hello" }',          desc: 'Write / overwrite a sandbox file.' },
  { type: 'append_file',      badge: '#059669', payload: '{ "upload_id": "<id>", "filename": "log.txt", "content": "new line" }',        desc: 'Append text to a sandbox file.' },
  { type: 'generate_code',    badge: '#7c3aed', payload: '{ "context": "parse CSV and plot bar chart", "language": "python" }',           desc: 'Generate code from a natural-language context.' },
  { type: 'dataset_analysis', badge: '#d97706', payload: '{ "upload_id": "<id>", "filename": "sales.csv" }',                             desc: 'Statistical analysis of a CSV file.' },
];

const PROMPT_GROUPS = [
  {
    label: '📄 File operations',
    prompts: [
      'Read the spec I uploaded and list every functional requirement.',
      'Read my uploaded README and suggest improvements to the Getting Started section.',
      'Append a timestamp and "task complete" to the log file in the current upload.',
    ],
  },
  {
    label: '💻 Code generation',
    prompts: [
      'Generate a Python script that reads a CSV and outputs a bar chart with matplotlib.',
      'Write a TypeScript utility function that deep-merges two objects.',
      'Generate a Bash script to tail all *.log files in /var/log and grep for ERROR.',
      'Create a SQL migration that adds a soft-delete column to a users table.',
    ],
  },
  {
    label: '📊 Dataset analysis',
    prompts: [
      'Analyse sales.csv — what are the top 5 product categories by revenue?',
      'Run a full statistical analysis on the uploaded CSV and highlight any anomalies.',
      'What is the column distribution in my uploaded dataset? Show numeric stats.',
      'Analyse financials.csv and identify the quarters with the highest variance.',
    ],
  },
  {
    label: '🔍 Status & management',
    prompts: [
      'What tasks are currently queued or running?',
      'Show me the result of the last completed task.',
      'How many tasks have failed in the current session?',
    ],
  },
  {
    label: '🎥 Multimedia tasks',
    prompts: [
      'Describe what is happening in the uploaded video.',
      'Transcribe the voice memo I attached.',
      'Create an image summarising the data analysis results.',
    ],
  },
];

const TASK_SUBNAV = [
  { label: 'Overview', key: 'overview' },
  { label: 'Sample tasks', key: 'samples' },
  { label: 'Job history', key: 'history' },
  { label: 'Quick prompts', key: 'prompts' },
];

const assetBase = import.meta.env.BASE_URL || '/';

const SAMPLE_LAYOUT_CARDS = [
  {
    title: 'Photo review workflow',
    caption: 'Use image-based tasks to summarize, tag, or clean up photos with realistic output.',
    src: `${assetBase}task-layout-1.svg`,
  },
  {
    title: 'Report generation',
    caption: 'Extract insights from uploads, create polished summaries, and generate final deliverables.',
    src: `${assetBase}task-layout-2.svg`,
  },
  {
    title: 'Data-driven decisions',
    caption: 'Turn spreadsheets and logs into actionable business recommendations.',
    src: `${assetBase}task-layout-3.svg`,
  },
];

type Task = { id: string; type: string; status: string; created_at?: string };

const statusColor: Record<string, string> = {
  queued:    '#6b7280',
  running:   '#0891b2',
  PENDING:   '#6b7280',
  STARTED:   '#0891b2',
  completed: '#059669',
  SUCCESS:   '#059669',
  failed:    '#dc2626',
  FAILURE:   '#dc2626',
};

// Active distributed jobs tracked by this page
type ActiveJob = { id: string; label: string; statusObj: JobStatus };

import ProcessingBanner from '@/components/ProcessingBanner';
import { useAppStore } from '@/state/appStore';

const TasksPage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  // Distributed job form
  const [jobGoal, setJobGoal] = useState('');

  // render live banner above the form
  const [jobContext, setJobContext] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  // Active jobs being polled
  const [activeJobs, setActiveJobs] = useState<ActiveJob[]>([]);
  const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getTasks()
      .then((res: any) => {
        const data = res?.data?.data ?? res?.data ?? [];
        if (Array.isArray(data)) setTasks(data);
        setOffline(false);
      })
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  // Poll active distributed jobs every 3 seconds
  useEffect(() => {
    if (activeJobs.length === 0) {
      if (pollerRef.current) clearInterval(pollerRef.current);
      pollerRef.current = null;
      return;
    }
    const poll = async () => {
      const updates = await Promise.all(
        activeJobs.map(async (job) => {
          const isTerminal =
            job.statusObj.status === 'completed' ||
            job.statusObj.status === 'failed' ||
            job.statusObj.state === 'SUCCESS' ||
            job.statusObj.state === 'FAILURE';
          if (isTerminal) return job;
          try {
            const fresh = await getJobStatus(job.id);
            return { ...job, statusObj: fresh };
          } catch {
            return job;
          }
        }),
      );
      setActiveJobs(updates);
    };
    pollerRef.current = setInterval(poll, 3000);
    return () => {
      if (pollerRef.current) clearInterval(pollerRef.current);
    };
  }, [activeJobs]);

  const handleSubmitJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobGoal.trim()) return;
    setSubmitting(true);
    setSubmitError('');
    try {
      const accepted = await submitAgentJob(jobGoal.trim(), jobContext.trim());
      const initial: JobStatus = { job_id: accepted.job_id, state: 'PENDING', status: 'queued' };
      setActiveJobs((prev) => [{ id: accepted.job_id, label: jobGoal.trim().slice(0, 60), statusObj: initial }, ...prev]);
      setJobGoal('');
      setJobContext('');
    } catch (err: any) {
      setSubmitError(err?.response?.data?.detail ?? err?.message ?? 'Failed to submit job');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: '28px 28px 60px', maxWidth: 950, margin: '0 auto', color: '#e2e8f0' }}>
      <ProcessingBanner />
      <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.01em' }}>✅ Tasks</h1>
      <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: '0 0 24px', lineHeight: 1.7 }}>
        Tasks run in the background — read files, generate code, analyse datasets. Enqueue via chat
        or the Postman collection, then poll for results. Click any prompt to try one now.
      </p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 12 }}>
        {TASK_SUBNAV.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setActiveTab(item.key)}
            style={{
              border: '1px solid rgba(255,255,255,0.14)',
              background: activeTab === item.key ? 'rgba(124,106,247,0.25)' : 'rgba(255,255,255,0.03)',
              color: '#e2e8f0',
              padding: '10px 16px',
              borderRadius: 999,
              fontSize: 13,
              cursor: 'pointer',
              transition: 'background 0.15s ease',
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div style={{ marginBottom: 28, color: 'rgba(255,255,255,0.6)', fontSize: 13, lineHeight: 1.7 }}>
        {activeTab === 'overview' && 'Overview: check the current task queue, review active jobs, and explore task examples for common automations.'}
        {activeTab === 'samples' && 'Sample tasks: explore curated task examples and launching patterns for reading files, generating code, and analysing datasets.'}
        {activeTab === 'history' && 'Job history: monitor queue status, inspect active jobs, and review past task activity across your session.'}
        {activeTab === 'prompts' && 'Quick prompts: use these prompt templates to get started with task automation and accelerate your workflow.'}
      </div>

    <PageSection title="Live timeline">
      <TimelineHero />
    </PageSection>

      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', marginBottom: 28 }}>
        {SAMPLE_LAYOUT_CARDS.map((card) => (
          <div key={card.title} style={{ borderRadius: 18, overflow: 'hidden', boxShadow: '0 18px 45px rgba(0,0,0,0.18)', background: '#0f172a' }}>
            <img src={card.src} alt={card.title} style={{ width: '100%', height: 190, objectFit: 'cover', display: 'block' }} />
            <div style={{ padding: 16 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#fff' }}>{card.title}</h3>
              <p style={{ margin: '10px 0 0', color: 'rgba(255,255,255,0.68)', fontSize: 13, lineHeight: 1.65 }}>{card.caption}</p>
            </div>
          </div>
        ))}
      </div>

      {/* backend offline notice */}
      {!loading && offline && (
        <div style={{ background: 'rgba(220,38,38,0.1)', border: '1px solid rgba(220,38,38,0.3)', borderRadius: 8, padding: '10px 16px', marginBottom: 24, fontSize: 13, color: '#fca5a5', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>⚠️</span>
          <span>Cannot reach the API backend. Make sure the backend is running (check your <code style={{ background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: 4 }}>VITE_API_URL</code> / local server) then refresh.</span>
        </div>
      )}

      {/* ---- Distributed job launcher ---- */}
      <div style={{ marginBottom: 32, background: 'rgba(124,106,247,0.06)', border: '1px solid rgba(124,106,247,0.2)', borderRadius: 12, padding: '20px 22px' }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, color: '#a78bfa', margin: '0 0 6px' }}>🚀 Distributed Agent Job</h2>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', margin: '0 0 16px', lineHeight: 1.6 }}>
          Jobs are queued via Celery + Redis and executed in a background worker. Results are polled every 3 seconds.
          Monitor the Flower dashboard at <code style={{ background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: 4 }}>localhost:5555</code>.
        </p>
        <form onSubmit={handleSubmitJob} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input
            value={jobGoal}
            onChange={(e) => setJobGoal(e.target.value)}
            placeholder="Goal — what should the agent do?"
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 7, padding: '9px 12px', color: '#e2e8f0', fontSize: 13, outline: 'none' }}
          />
          <input
            value={jobContext}
            onChange={(e) => setJobContext(e.target.value)}
            placeholder="Context (optional background information)"
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 7, padding: '9px 12px', color: '#e2e8f0', fontSize: 13, outline: 'none' }}
          />
          {submitError && (
            <div style={{ fontSize: 12, color: '#fca5a5', background: 'rgba(220,38,38,0.1)', border: '1px solid rgba(220,38,38,0.25)', borderRadius: 6, padding: '6px 10px' }}>{submitError}</div>
          )}
          <button
            type="submit"
            disabled={submitting || !jobGoal.trim()}
            style={{ alignSelf: 'flex-start', background: submitting || !jobGoal.trim() ? 'rgba(124,106,247,0.25)' : '#7c6af7', color: '#fff', border: 'none', borderRadius: 7, padding: '9px 20px', fontSize: 13, fontWeight: 600, cursor: submitting || !jobGoal.trim() ? 'default' : 'pointer', transition: 'background 0.15s' }}
          >
            {submitting ? 'Queuing…' : 'Submit Job'}
          </button>
        </form>

        {/* Active jobs list */}
        {activeJobs.length > 0 && (
          <div style={{ marginTop: 18 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'rgba(255,255,255,0.3)', marginBottom: 8 }}>Active / Recent Jobs</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {activeJobs.map((job) => {
                const st = job.statusObj.status ?? job.statusObj.state ?? 'queued';
                const isTerminal = st === 'completed' || st === 'failed' || st === 'SUCCESS' || st === 'FAILURE';
                return (
                  <div key={job.id} style={{ background: 'rgba(255,255,255,0.03)', border: `1px solid ${(statusColor[st] ?? '#6b7280')}33`, borderRadius: 8, padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: job.statusObj.result || job.statusObj.error ? 6 : 0 }}>
                      {!isTerminal && <span style={{ width: 8, height: 8, borderRadius: '50%', background: statusColor[st] ?? '#0891b2', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />}
                      <span style={{ fontSize: 12, color: '#e2e8f0', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{job.label}</span>
                      <span style={{ padding: '2px 8px', borderRadius: 99, background: (statusColor[st] ?? '#6b7280') + '33', color: statusColor[st] ?? '#9ca3af', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', flexShrink: 0 }}>{st}</span>
                    </div>
                    <div style={{ fontFamily: 'monospace', fontSize: 10, color: 'rgba(255,255,255,0.2)' }}>{job.id}</div>
                    {job.statusObj.error && (
                      <div style={{ fontSize: 12, color: '#fca5a5', marginTop: 6, background: 'rgba(220,38,38,0.08)', borderRadius: 5, padding: '4px 8px' }}>{job.statusObj.error}</div>
                    )}
                    {job.statusObj.result && (
                      <pre style={{ fontSize: 11, color: '#86efac', marginTop: 6, background: 'rgba(5,150,105,0.07)', borderRadius: 5, padding: '6px 8px', overflowX: 'auto', maxHeight: 120, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {typeof job.statusObj.result === 'string'
                          ? job.statusObj.result
                          : JSON.stringify(job.statusObj.result, null, 2)}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* live task list */}
      {!loading && tasks.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', margin: '0 0 10px', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>Recent tasks</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {tasks.slice(0, 8).map((t) => (
              <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 7, padding: '8px 14px', fontSize: 13 }}>
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#7c6af7', minWidth: 100, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.type}</span>
                <span style={{ padding: '2px 8px', borderRadius: 99, background: (statusColor[t.status] ?? '#6b7280') + '33', color: statusColor[t.status] ?? '#9ca3af', fontSize: 11, fontWeight: 600 }}>{t.status}</span>
                <span style={{ fontFamily: 'monospace', fontSize: 10, color: 'rgba(255,255,255,0.25)', marginLeft: 'auto' }}>{t.id.slice(0, 12)}…</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* task type reference */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', margin: '0 0 10px', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>Available task types</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {TASK_TYPES.map(({ type, badge, payload, desc }) => (
            <div key={type} style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '12px 14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 700, color: badge }}>{type}</span>
              </div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 6 }}>{desc}</div>
              <code style={{ fontSize: 11, color: '#94a3b8', background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: 5, display: 'block', overflowX: 'auto', whiteSpace: 'pre' }}>payload: {payload}</code>
            </div>
          ))}
        </div>
      </div>

      {/* sample prompts */}
      {PROMPT_GROUPS.map(({ label, prompts }) => (
        <div key={label} style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', margin: '0 0 12px', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>{label}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
            {prompts.map((p) => <SamplePrompt key={p} text={p} />)}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TasksPage;