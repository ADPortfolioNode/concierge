import React from 'react';
import SamplePrompt from '@/components/primitives/SamplePrompt';

const ALLOWED_TYPES = [
  { ext: '.txt', label: 'Plain text', color: '#6b7280' },
  { ext: '.csv', label: 'CSV / spreadsheet', color: '#059669' },
  { ext: '.json', label: 'JSON data', color: '#0891b2' },
  { ext: '.pdf', label: 'PDF document', color: '#dc2626' },
  { ext: '.docx', label: 'Word document', color: '#2563eb' },
  { ext: '.png / .jpg', label: 'Images', color: '#9333ea' },
  { ext: '.mp3 / .wav', label: 'Audio (Whisper)', color: '#d97706' },
  { ext: '.mp4 / .mov', label: 'Video (metadata)', color: '#be185d' },
];

const PROMPT_GROUPS = [
  {
    label: '📄 Document analysis',
    prompts: [
      'I uploaded a PDF spec — summarise the authentication requirements.',
      'Read the uploaded DOCX and extract all action items.',
      'Scan the uploaded requirements doc and flag any ambiguities.',
      'Compare the two uploaded specs and list the differences.',
    ],
  },
  {
    label: '📊 Data & CSVs',
    prompts: [
      'Analyse the uploaded CSV and give me a summary table of numeric columns.',
      'What are the top 10 rows by revenue in the uploaded sales file?',
      'Detect any missing values or obvious data-quality issues in the CSV.',
      'Generate a Python script to visualise the data in the uploaded CSV.',
    ],
  },
  {
    label: '🗂️ Projects & organisation',
    prompts: [
      'Create a project called "Q3 Product Launch" — attach the brief I uploaded.',
      'List all files attached to the current project.',
      'What projects exist? Show names and file counts.',
      'Delete the "Sandbox Test" project.',
      'Generate an image for the project logo.',
    ],
  },
  {
    label: '📸 Multimedia',
    prompts: [
      'Create an image of a friendly robot greeting me.',
      'Transcribe the audio file I just uploaded.',
      'Analyse the contents of the uploaded video and describe key scenes.',
    ],
  },
  {
    label: '🖼️ Images & media',
    prompts: [
      'I uploaded a UI screenshot — describe the layout and suggest UX improvements.',
      'What metadata was extracted from the uploaded image?',
      'Transcribe the audio file I just uploaded.',
    ],
  },
];

const WorkspacePage: React.FC = () => (
  <div style={{ padding: '28px 28px 60px', maxWidth: 950, margin: '0 auto', color: '#e2e8f0' }}>
    <h1 style={{ fontSize: 26, fontWeight: 800, margin: '0 0 8px', letterSpacing: '-0.01em' }}>📁 Workspace</h1>
    <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', margin: '0 0 28px', lineHeight: 1.7 }}>
      Upload files, organise them into Projects, and give the AI direct access to your content.
      Use the 📎 button in the chat to attach files mid-conversation.
    </p>

    {/* upload guide */}
    <div style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: '20px', marginBottom: 28 }}>
      <h2 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 14px', color: '#c4b8ff' }}>How to upload a file</h2>
      {[
        { n: '1', t: 'Click 📎 in the chat input', d: 'A drag-and-drop uploader appears inline. You can also click to pick a file.' },
        { n: '2', t: 'Select your file', d: 'Up to 50 MB. Allowed types listed below. The file is scanned for MIME type and text is extracted automatically.' },
        { n: '3', t: 'Send your message', d: 'A file:upload_id/filename reference is prepended to your message so the AI can use the content.' },
        { n: '4', t: '(Optional) Attach to a project', d: 'Provide a project_id in the upload form to group the file with related work.' },
      ].map(({ n, t, d }) => (
        <div key={n} style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ minWidth: 24, height: 24, borderRadius: '50%', background: '#7c6af7', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, color: '#fff', flexShrink: 0, marginTop: 1 }}>{n}</div>
          <div><div style={{ fontWeight: 600, fontSize: 13, color: '#e2e8f0', marginBottom: 2 }}>{t}</div><div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)' }}>{d}</div></div>
        </div>
      ))}
    </div>

    {/* allowed types */}
    <div style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.35)', margin: '0 0 10px', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>Allowed file types</h2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {ALLOWED_TYPES.map(({ ext, label, color }) => (
          <div key={ext} style={{ background: `${color}22`, border: `1px solid ${color}44`, borderRadius: 7, padding: '6px 12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 700, color }}>{ext}</span>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>{label}</span>
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

export default WorkspacePage;