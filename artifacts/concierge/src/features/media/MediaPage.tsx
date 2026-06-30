import React from 'react';
import { Link } from 'react-router-dom';
import { useAppStore } from '@/state/appStore';
import MediaRenderer from '@/components/media/MediaRenderer';
import * as ConciergeAPI from '@/api/conciergeService';

const normalizeMediaUrl = (url: string) => {
  if (!url) return url;
  return url.startsWith('/') ? url : `/${url}`;
};

const MediaPage: React.FC = () => {
  const imageLayers = useAppStore((s) => s.imageLayers);
  const videoLayers = useAppStore((s) => s.videoLayers);
  const audioLayers = useAppStore((s) => s.audioLayers);
  const activeMedia = useAppStore((s) => s.activeMedia);
  const setActiveMedia = useAppStore((s) => s.setActiveMedia);
  const clearMediaLayers = useAppStore((s) => s.clearMediaLayers);
  const fetchMedia = useAppStore((s) => s.fetchMedia);

  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [apiCount, setApiCount] = React.useState(0);

  const loadMedia = React.useCallback(async (opts?: { silent?: boolean }) => {
    if (!opts?.silent) setRefreshing(true);
    try {
      const list = await ConciergeAPI.getMedia();
      setApiCount(list.length);
      setError(null);
      await fetchMedia();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      try {
        await fetchMedia();
      } catch {
        // store sync is best-effort
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchMedia]);

  React.useEffect(() => {
    loadMedia();
    const interval = window.setInterval(() => loadMedia({ silent: true }), 15000);
    return () => window.clearInterval(interval);
  }, [loadMedia]);

  const uniqueMediaItems = React.useMemo(() => {
    const items = [
      ...imageLayers.map((item) => ({ ...item, type: 'image' as const })),
      ...videoLayers.map((item) => ({ ...item, type: 'video' as const })),
      ...audioLayers.map((item) => ({ ...item, type: 'audio' as const })),
    ];
    return Array.from(new Map(items.map((item) => [`${item.type}-${item.url}`, item])).values());
  }, [imageLayers, videoLayers, audioLayers]);

  const selected = React.useMemo(
    () => {
      const normalizedActive = activeMedia ? normalizeMediaUrl(activeMedia) : null;
      return uniqueMediaItems.find((item) => normalizeMediaUrl(item.url) === normalizedActive) || uniqueMediaItems[0] || null;
    },
    [uniqueMediaItems, activeMedia]
  );

  return (
    <div className="page-content" style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, letterSpacing: '-0.01em', color: '#0F172A' }}>🎬 Multimedia</h1>
          <p style={{ color: '#475569', marginTop: 8, fontSize: 14, lineHeight: 1.7 }}>
            Generated images and media saved by Concierge ({uniqueMediaItems.length} shown
            {apiCount > 0 ? ` · ${apiCount} on server` : ''}).
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
          <Link
            to="/"
            style={{ display: 'inline-flex', alignItems: 'center', padding: '8px 14px', borderRadius: 8, background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#2563EB', textDecoration: 'none', fontWeight: 600, fontSize: 13 }}
          >
            ← Home
          </Link>
          <button
            onClick={() => loadMedia()}
            disabled={refreshing}
            style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#2563EB', borderRadius: 8, padding: '8px 14px', cursor: refreshing ? 'wait' : 'pointer', fontSize: 13, fontWeight: 600 }}
          >
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
          <button
            onClick={() => clearMediaLayers()}
            style={{ background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)', color: '#B91C1C', borderRadius: 8, padding: '8px 14px', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
          >
            Clear view
          </button>
        </div>
      </div>

      {error ? (
        <div style={{ padding: 16, marginBottom: 16, background: '#FEF2F2', borderRadius: 10, color: '#B91C1C', border: '1px solid #FECACA', fontSize: 14 }}>
          Could not load media list: {error}. Click Refresh to retry.
        </div>
      ) : null}

      {loading ? (
        <div style={{ padding: 28, background: '#F0F8FF', borderRadius: 14, textAlign: 'center', color: '#475569', border: '1px solid #DBEAFE' }}>
          Loading media gallery…
        </div>
      ) : uniqueMediaItems.length === 0 ? (
        <div style={{ padding: 28, background: '#F0F8FF', borderRadius: 14, textAlign: 'center', color: '#475569', border: '1px solid #DBEAFE' }}>
          No media is currently available. Ask Concierge to generate an image, or run an image plugin job — saved files will appear here automatically.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 24 }}>
          <div style={{ padding: 20, background: '#FFFFFF', borderRadius: 14, border: '1px solid #DBEAFE', boxShadow: '0 2px 8px rgba(37,99,235,0.07)' }}>
            <h2 style={{ margin: '0 0 18px 0', fontSize: 20, color: '#0F172A' }}>Selected media</h2>
            {selected ? (
              <div>
                {selected.prompt ? (
                  <div style={{ marginBottom: 12, color: '#475569', fontSize: 14 }}>
                    <strong>Prompt:</strong> {selected.prompt}
                  </div>
                ) : null}
                {selected.source ? (
                  <div style={{ marginBottom: 12, color: '#64748B', fontSize: 12 }}>
                    Source: {selected.source}
                  </div>
                ) : null}
                <MediaRenderer media={{ type: selected.type, url: selected.url, overlay_text: null, mime_type: null }} />
              </div>
            ) : (
              <div style={{ color: '#64748B' }}>No active media selected.</div>
            )}
          </div>

          <div style={{ display: 'grid', gap: 10 }}>
            {uniqueMediaItems.map((item) => (
              <button
                key={`${item.type}-${item.id}-${encodeURIComponent(item.url)}`}
                onClick={() => setActiveMedia(normalizeMediaUrl(item.url))}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  borderRadius: 10,
                  background: item.url === selected?.url ? '#EFF6FF' : '#FFFFFF',
                  border: item.url === selected?.url ? '1px solid #93C5FD' : '1px solid #DBEAFE',
                  color: '#0F172A',
                  cursor: 'pointer',
                  boxShadow: '0 1px 4px rgba(37,99,235,0.06)',
                  textAlign: 'left',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, color: '#0F172A' }}>{item.type.toUpperCase()}</div>
                  <div style={{ fontSize: 13, color: '#64748B' }}>
                    {item.prompt || item.filename || item.url}
                  </div>
                  {item.source ? (
                    <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>{item.source}</div>
                  ) : null}
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#2563EB' }}>Select →</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MediaPage;