import React from 'react';
import { Link } from 'react-router-dom';
import { useAppStore } from '@/state/appStore';
import MediaRenderer from '@/components/media/MediaRenderer';

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
          <p style={{ color: '#475569', marginTop: 8, fontSize: 14, lineHeight: 1.7 }}>Review all media attached to the current chat session.</p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
          <Link
            to="/"
            style={{ display: 'inline-flex', alignItems: 'center', padding: '8px 14px', borderRadius: 8, background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#2563EB', textDecoration: 'none', fontWeight: 600, fontSize: 13 }}
          >
            ← Home
          </Link>
          <button
            onClick={() => clearMediaLayers()}
            style={{ background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)', color: '#B91C1C', borderRadius: 8, padding: '8px 14px', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
          >
            Clear all
          </button>
        </div>
      </div>

      {uniqueMediaItems.length === 0 ? (
        <div style={{ padding: 28, background: '#F0F8FF', borderRadius: 14, textAlign: 'center', color: '#475569', border: '1px solid #DBEAFE' }}>
          No media is currently available. Trigger a response with images, video, or audio to see them here.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 24 }}>
          <div style={{ padding: 20, background: '#FFFFFF', borderRadius: 14, border: '1px solid #DBEAFE', boxShadow: '0 2px 8px rgba(37,99,235,0.07)' }}>
            <h2 style={{ margin: '0 0 18px 0', fontSize: 20, color: '#0F172A' }}>Selected media</h2>
            {selected ? (
              <div>
                <div style={{ marginBottom: 16, color: '#475569' }}>
                  Showing the selected media item from the current response.
                </div>
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
                  <div style={{ fontSize: 13, color: '#64748B' }}>{item.url}</div>
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
