import React from 'react';
import { Link } from 'react-router-dom';
import { useAppStore } from '@/state/appStore';
import MediaRenderer from '@/components/media/MediaRenderer';

const MediaPage: React.FC = () => {
  const imageLayers = useAppStore((s) => s.imageLayers);
  const videoLayers = useAppStore((s) => s.videoLayers);
  const audioLayers = useAppStore((s) => s.audioLayers);
  const activeMedia = useAppStore((s) => s.activeMedia);
  const setActiveMedia = useAppStore((s) => s.setActiveMedia);
  const clearMediaLayers = useAppStore((s) => s.clearMediaLayers);

  const mediaItems = [
    ...imageLayers.map((item) => ({ ...item, type: 'image' as const })),
    ...videoLayers.map((item) => ({ ...item, type: 'video' as const })),
    ...audioLayers.map((item) => ({ ...item, type: 'audio' as const })),
  ];

  const uniqueMediaItems = Array.from(
    new Map(mediaItems.map((item) => [`${item.type}-${item.url}`, item])).values()
  );

  const selected = uniqueMediaItems.find((item) => item.url === activeMedia) || uniqueMediaItems[0] || null;

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 32 }}>Multimedia</h1>
          <p style={{ color: 'rgba(255,255,255,0.65)', marginTop: 8 }}>Review all media attached to the current chat session.</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link to="/" style={{ color: '#c4b8ff', textDecoration: 'none', fontWeight: 600 }}>Back to chat</Link>
          <button
            onClick={() => clearMediaLayers()}
            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: 8, padding: '8px 12px', cursor: 'pointer' }}
          >
            Clear media
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
                <MediaRenderer media={{ type: selected.type, url: selected.url }} />
              </div>
            ) : (
              <div style={{ color: 'rgba(255,255,255,0.65)' }}>No active media selected.</div>
            )}
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            {uniqueMediaItems.map((item) => (
              <button
                key={`${item.type}-${item.id}-${encodeURIComponent(item.url)}`}
                onClick={() => setActiveMedia(item.url)}
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
