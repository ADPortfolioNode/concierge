import React from 'react';
import { Link } from 'react-router-dom';
import * as ConciergeAPI from '@/api/conciergeService';
import MediaRenderer from '@/components/media/MediaRenderer';
import { useAppStore } from '@/state/appStore';

const formatBytes = (n?: number) => {
  if (n == null || Number.isNaN(n)) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
};

const formatWhen = (iso?: string) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

type MediaEntry = ConciergeAPI.MediaListItem & { created_at?: string };

const MediaPage: React.FC = () => {
  const setActiveMedia = useAppStore((s) => s.setActiveMedia);
  const fetchMedia = useAppStore((s) => s.fetchMedia);

  const [entries, setEntries] = React.useState<MediaEntry[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [selectedUrl, setSelectedUrl] = React.useState<string | null>(null);

  const loadIndex = React.useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) setRefreshing(true);
    try {
      const list = await ConciergeAPI.getMedia();
      const images = (Array.isArray(list) ? list : []).filter((item) => {
        if (!item?.url) return false;
        const mime = String(item.metadata?.mime_type || '');
        if (mime.startsWith('image')) return true;
        return /\.(png|jpe?g|gif|webp|avif|svg)$/i.test(String(item.url));
      });
      setEntries(images);
      setError(null);
      setSelectedUrl((prev) => prev || images[0]?.url || null);
      fetchMedia().catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchMedia]);

  React.useEffect(() => {
    loadIndex();
    const interval = window.setInterval(() => loadIndex({ silent: true }), 15000);
    return () => window.clearInterval(interval);
  }, [loadIndex]);

  const selected = React.useMemo(
    () => entries.find((e) => e.url === selectedUrl) || entries[0] || null,
    [entries, selectedUrl],
  );

  const totalBytes = React.useMemo(
    () => entries.reduce((sum, e) => sum + (e.size || 0), 0),
    [entries],
  );

  return (
    <div className="page-content" style={{ maxWidth: 1280, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 20 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: '#0F172A' }}>🖼️ Media library</h1>
          <p style={{ color: '#475569', marginTop: 8, fontSize: 14 }}>
            Index of saved files in <code style={{ background: '#EFF6FF', padding: '2px 6px', borderRadius: 4 }}>media/images/</code>
            {' '}— {entries.length} file{entries.length === 1 ? '' : 's'}, {formatBytes(totalBytes)} total
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link to="/" style={{ padding: '8px 14px', borderRadius: 8, background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#2563EB', textDecoration: 'none', fontWeight: 600, fontSize: 13 }}>
            ← Home
          </Link>
          <button
            type="button"
            onClick={() => loadIndex()}
            disabled={refreshing}
            style={{ padding: '8px 14px', borderRadius: 8, background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#2563EB', fontWeight: 600, fontSize: 13, cursor: refreshing ? 'wait' : 'pointer' }}
          >
            {refreshing ? 'Refreshing…' : 'Refresh index'}
          </button>
        </div>
      </div>

      {error ? (
        <div style={{ padding: 14, marginBottom: 16, background: '#FEF2F2', borderRadius: 8, color: '#B91C1C', border: '1px solid #FECACA' }}>
          Could not load media index: {error}
        </div>
      ) : null}

      {loading ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#64748B', background: '#F8FAFC', borderRadius: 12 }}>Loading media index…</div>
      ) : entries.length === 0 ? (
        <div style={{ padding: 32, textAlign: 'center', color: '#64748B', background: '#F0F8FF', borderRadius: 12, border: '1px solid #DBEAFE' }}>
          No images in <strong>media/images/</strong> yet. Generate one via chat or Tasks → plugin job.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 20 }}>
          {selected ? (
            <div style={{ padding: 18, background: '#fff', borderRadius: 12, border: '1px solid #DBEAFE' }}>
              <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Preview — {selected.filename || selected.url}</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginBottom: 12, fontSize: 13, color: '#64748B' }}>
                <span>Size: {formatBytes(selected.size)}</span>
                <span>Modified: {formatWhen(selected.created_at || selected.mtime || selected.metadata?.created_at)}</span>
                {selected.metadata?.source ? <span>Source: {selected.metadata.source}</span> : null}
              </div>
              {selected.metadata?.prompt ? (
                <p style={{ fontSize: 14, color: '#475569', margin: '0 0 12px' }}><strong>Prompt:</strong> {selected.metadata.prompt}</p>
              ) : null}
              <MediaRenderer media={{ type: 'image', url: selected.url, overlay_text: null, mime_type: selected.metadata?.mime_type || null }} />
            </div>
          ) : null}

          <div style={{ overflowX: 'auto', background: '#fff', borderRadius: 12, border: '1px solid #DBEAFE' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#F8FAFC', textAlign: 'left', borderBottom: '1px solid #E2E8F0' }}>
                  <th style={{ padding: '10px 12px' }}>Preview</th>
                  <th style={{ padding: '10px 12px' }}>Filename</th>
                  <th style={{ padding: '10px 12px' }}>Size</th>
                  <th style={{ padding: '10px 12px' }}>Modified</th>
                  <th style={{ padding: '10px 12px' }}>Source</th>
                  <th style={{ padding: '10px 12px' }}>Prompt</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((item) => {
                  const active = item.url === (selected?.url || selectedUrl);
                  return (
                    <tr
                      key={item.filename || item.url}
                      onClick={() => {
                        setSelectedUrl(item.url);
                        setActiveMedia(item.url);
                      }}
                      style={{
                        cursor: 'pointer',
                        background: active ? '#EFF6FF' : 'transparent',
                        borderBottom: '1px solid #F1F5F9',
                      }}
                    >
                      <td style={{ padding: '8px 12px', width: 72 }}>
                        <img
                          src={item.url}
                          alt={item.filename || ''}
                          style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 6, border: '1px solid #E2E8F0', background: '#F1F5F9' }}
                          loading="lazy"
                        />
                      </td>
                      <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 12, color: '#0F172A' }}>
                        <a href={item.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} style={{ color: '#2563EB' }}>
                          {item.filename || item.url}
                        </a>
                      </td>
                      <td style={{ padding: '8px 12px', color: '#64748B' }}>{formatBytes(item.size)}</td>
                      <td style={{ padding: '8px 12px', color: '#64748B', whiteSpace: 'nowrap' }}>
                        {formatWhen(item.created_at || item.mtime || item.metadata?.created_at)}
                      </td>
                      <td style={{ padding: '8px 12px', color: '#64748B' }}>{item.metadata?.source || '—'}</td>
                      <td style={{ padding: '8px 12px', color: '#475569', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.metadata?.prompt || '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default MediaPage;