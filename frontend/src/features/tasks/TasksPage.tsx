import React, { useEffect, useState } from 'react';
import { getTasks } from '@/api/taskService';
import SamplePrompt from '@/components/primitives/SamplePrompt';

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
];

type Task = { id: string; type: string; status: string; created_at?: string };

const statusColor: Record<string, string> = {
  queued:    '#6b7280',
  running:   '#0891b2',
  completed: '#059669',
  failed:    '#dc2626',
};

const TasksPage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

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

  return (
    <div style={{ padding: '28px 28px 60px', maxWidth: 950, margin: '0 auto', color: '#e2e8f0' }}>
      <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.01em' }}>✅ Tasks</h1>
      <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: '0 0 28px', lineHeight: 1.7 }}>
        Tasks run in the background — read files, generate code, analyse datasets. Enqueue via chat
        or the Postman collection, then poll for results. Click any prompt to try one now.
      </p>

      {/* backend offline notice */}
      {!loading && offline && (
        <div style={{ background: 'rgba(220,38,38,0.1)', border: '1px solid rgba(220,38,38,0.3)', borderRadius: 8, padding: '10px 16px', marginBottom: 24, fontSize: 13, color: '#fca5a5', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>⚠️</span>
          <span>Cannot reach the API backend. Make sure the server is running on <code style={{ background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: 4 }}>localhost:8001</code> (run <code style={{ background: 'rgba(255,255,255,0.07)', padding: '1px 5px', borderRadius: 4 }}>./start.sh</code>) then refresh.</span>
        </div>
      )}

      {/* live task list */}
      {!loading && tasks.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', margin: '0 0 10px', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>Recent tasks</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {tasks.slice(0, 8).map((t) => (
              <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 7, padding: '8px 14px', fontSize: 13 }}>
                <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#7c6af7', minWidth: 120 }}>{t.type}</span>
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