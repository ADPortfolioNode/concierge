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
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, letterSpacing: '-0.01em' }}>🎬 Multimedia</h1>
          <p style={{ color: 'rgba(255,255,255,0.5)', marginTop: 8, fontSize: 14, lineHeight: 1.7 }}>Review all media attached to the current chat session.</p>
        </div>
        <div style={{ display: 'flex', gap: 10, flexShrink: 0 }}>
          <Link
            to="/"
            style={{ display: 'inline-flex', alignItems: 'center', padding: '8px 14px', borderRadius: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.09)', color: '#c4b8ff', textDecoration: 'none', fontWeight: 600, fontSize: 13 }}
          >
            ← Home
          </Link>
          <button
            onClick={() => clearMediaLayers()}
            style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.22)', color: '#fca5a5', borderRadius: 8, padding: '8px 14px', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
          >
            Clear all
          </button>
        </div>
      </div>

      {uniqueMediaItems.length === 0 ? (
        <div style={{ padding: 24, background: 'rgba(255,255,255,0.02)', borderRadius: 12, textAlign: 'center', color: 'rgba(255,255,255,0.65)' }}>
          No media is currently available. Trigger a response with images, video, or audio to see them here.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 24 }}>
          <div style={{ padding: 20, background: 'rgba(255,255,255,0.03)', borderRadius: 14, border: '1px solid rgba(255,255,255,0.08)' }}>
            <h2 style={{ margin: '0 0 18px 0', fontSize: 20 }}>Selected media</h2>
            {selected ? (
              <div>
                <div style={{ marginBottom: 16, color: 'rgba(255,255,255,0.7)' }}>
                  Showing the selected media item from the current response.
                </div>
                <MediaRenderer media={{ type: selected.type, url: selected.url, overlay_text: null, mime_type: null }} />
              </div>
            ) : (
              <div style={{ color: 'rgba(255,255,255,0.65)' }}>No active media selected.</div>
            )}
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
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
                  background: item.url === selected?.url ? 'rgba(124,106,247,0.16)' : 'rgba(255,255,255,0.03)',
                  border: item.url === selected?.url ? '1px solid rgba(124,106,247,0.45)' : '1px solid rgba(255,255,255,0.08)',
                  color: '#fff',
                  cursor: 'pointer',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700 }}>{item.type.toUpperCase()}</div>
                  <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.6)' }}>{item.url}</div>
                </div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.55)' }}>Select</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MediaPage;
