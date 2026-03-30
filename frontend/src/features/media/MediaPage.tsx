import React, { useEffect, useState } from 'react';
import { getMedia, cleanupMedia } from '@/api/conciergeService';
import { Link } from 'react-router-dom';

type MediaItem = {
  filename: string;
  url: string;
  size: number;
  mtime: string;
  metadata?: any;
};

const MediaPage: React.FC = () => {
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    getMedia()
      .then((res: any) => {
        const items = (res?.data?.data ?? res?.data ?? []) as MediaItem[];
        if (mounted) {
          setMedia(items);
          setError('');
        }
      })
      .catch((err) => {
        setError(err?.message ?? 'Failed to load media list');
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleCleanup = async () => {
    if (!window.confirm('This will delete your session-owned generated images from server storage. Continue?')) return;
    try {
      const res = await cleanupMedia();
      setNotice(`Deleted ${res?.data?.data?.removed?.length || 0} session image(s).`);
      setMedia([]);
      setError('');
    } catch (err: any) {
      setError(err?.message ?? 'Cleanup failed');
      setNotice('');
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: 1100, margin: '0 auto', color: '#e2e8f0' }}>
      <h1 style={{ fontSize: 28, fontWeight: 800 }}>🖼️ Media Library</h1>
      <p style={{ color: '#9ca3af', marginTop: 4, marginBottom: 16 }}>
        All generated images are ephemeral in this session. Save any image you want to keep, then clean up the current session content.
      </p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>{media.length} items found</div>
        <button onClick={handleCleanup} style={{ padding: '8px 11px', borderRadius: '6px', border: '1px solid #7c6af7', background: '#0f172a', color: '#c4b8ff', cursor: 'pointer' }}>
          Cleanup session images
        </button>
      </div>
      {notice && <div style={{ background: '#064e3b', border: '1px solid #064e3b', color: '#a7f3d0', padding: '8px 10px', borderRadius: 6, marginBottom: 12 }}>{notice}</div>}
      {error && <div style={{ background: '#881337', border: '1px solid #dc2626', color: '#fecaca', padding: '8px 10px', borderRadius: 6, marginBottom: 12 }}>{error}</div>}
      {loading && <div>Loading...</div>}
      {!loading && media.length === 0 && <div>No media found. Generate some images and refresh.</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 14 }}>
        {media.map((m) => (
          <article key={m.filename} style={{ background: '#111827', borderRadius: 12, border: '1px solid rgba(148,163,184,0.3)', overflow: 'hidden' }}>
            <div style={{ position: 'relative', paddingBottom: '70%', overflow: 'hidden' }}>
              <img src={m.url} alt={m.filename} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
            <div style={{ padding: '10px 10px 12px', fontSize: 13 }}>
              <div style={{ fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>{m.filename}</div>
              <div style={{ color: '#94a3b8', fontSize: 12 }}><strong>Size:</strong> {Math.round(m.size / 1024)} KB</div>
              <div style={{ color: '#94a3b8', fontSize: 12 }}><strong>Modified:</strong> {m.mtime}</div>
              <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                <a href={m.url} target="_blank" rel="noreferrer" style={{ color: '#60a5fa', fontSize: 12 }}>Open</a>
                <a href={m.url} download style={{ color: '#a78bfa', fontSize: 12 }}>Download</a>
              </div>
            </div>
          </article>
        ))}
      </div>
      <div style={{ marginTop: 20 }}>
        <Link to="/tasks" style={{ color: '#93c5fd' }}>← Back to Tasks</Link>
      </div>
    </div>
  );
};

export default MediaPage;
