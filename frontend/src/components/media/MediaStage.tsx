/**
 * MediaStage — floating, draggable panel with independent z-indexed layers.
 *
 * Layer stack (bottom → top):
 *   z-1  Image   — fills stage background (object-fit: cover)
 *   z-2  Video   — centred player with native controls
 *   z-3  Text    — semi-transparent card at top of stage
 *   z-4  Audio   — bar docked to stage bottom
 *
 * Auto-shows when new content is routed from appStore.sendMessage.
 * Draggable via the header handle.  Each layer can be toggled.
 */

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useAppStore } from '@/state/appStore';

const STAGE_W = 380;
const STAGE_H = 306;
const HEADER_H = 40;
const BODY_H = STAGE_H - HEADER_H;
// resizing limits
const MIN_W = 200;
const MIN_H = 150;
const MAX_W = 800;
const MAX_H = 600;

type LayerKey = 'image' | 'video' | 'audio' | 'text';

// ── tiny helpers ────────────────────────────────────────────────────────────

const DragDots: React.FC = () => (
  <svg
    width="10"
    height="16"
    viewBox="0 0 10 16"
    fill="rgba(255,255,255,0.22)"
    style={{ flexShrink: 0, cursor: 'grab' }}
    aria-hidden
  >
    {([0, 4, 8, 12] as const).flatMap((y) =>
      ([0, 4] as const).map((x) => (
        <circle key={`${x}-${y}`} cx={x + 1} cy={y + 2} r={1} />
      )),
    )}
  </svg>
);

const iconBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'rgba(255,255,255,0.4)',
  cursor: 'pointer',
  fontSize: 11,
  padding: '3px 5px',
  lineHeight: 1,
  borderRadius: 3,
  flexShrink: 0,
  transition: 'color 0.12s',
};

interface LayerToggleProps {
  label: string;
  active: boolean;
  onClick: () => void;
  title: string;
}

const LayerToggle: React.FC<LayerToggleProps> = ({ label, active, onClick, title }) => (
  <button
    onClick={onClick}
    title={title}
    style={{
      background: active ? 'rgba(124,106,247,0.22)' : 'rgba(255,255,255,0.04)',
      border: `1px solid ${active ? 'rgba(124,106,247,0.45)' : 'rgba(255,255,255,0.08)'}`,
      borderRadius: 4,
      color: active ? '#c4b8ff' : 'rgba(255,255,255,0.28)',
      cursor: 'pointer',
      fontSize: 11,
      fontWeight: 600,
      padding: '2px 7px',
      lineHeight: 1.5,
      flexShrink: 0,
      transition: 'background 0.12s, border-color 0.12s, color 0.12s',
    }}
  >
    {label}
  </button>
);

// ── main component ───────────────────────────────────────────────────────────

const MediaStage: React.FC = () => {
  const imageLayers = useAppStore((s) => s.imageLayers);
  const videoLayers = useAppStore((s) => s.videoLayers);
  const audioLayers = useAppStore((s) => s.audioLayers);
  const textHighlights = useAppStore((s) => s.textHighlights);
  const clearMediaLayers = useAppStore((s) => s.clearMediaLayers);

  const hasContent =
    imageLayers.length > 0 ||
    videoLayers.length > 0 ||
    audioLayers.length > 0 ||
    textHighlights.length > 0;

  const [dismissed, setDismissed] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [hiddenLayers, setHiddenLayers] = useState<Set<LayerKey>>(new Set());
  const [fullWidth, setFullWidth] = useState(false);
  const prevSize = useRef<{width: number; height: number}>({width: STAGE_W, height: STAGE_H});

  // Position: left/top in px; initialised once layout is known
  const [pos, setPos] = useState({ left: 0, top: 0 });
  // width/height can change when user resizes
  const [size, setSize] = useState({ width: STAGE_W, height: STAGE_H });
  const posInitialised = useRef(false);

  useLayoutEffect(() => {
    if (!posInitialised.current) {
      posInitialised.current = true;
      setPos({
        left: Math.max(20, window.innerWidth - size.width - 24),
        top: Math.max(60, window.innerHeight - size.height - 90),
      });
    }
  }, []);

  // Auto-show whenever new layers arrive
  const layerCount =
    imageLayers.length + videoLayers.length + audioLayers.length + textHighlights.length;
  // if we're in fullWidth mode, keep size updated when window resizes
  useEffect(() => {
    if (!fullWidth) return;
    const onResize = () => {
      setSize((s) => ({
        ...s,
        width: Math.min(MAX_W, window.innerWidth - 40),
      }));
      setPos((p) => ({ ...p, left: 20 }));
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [fullWidth]);
  const prevCount = useRef(0);
  useEffect(() => {
    if (layerCount > prevCount.current) {
      setDismissed(false);
      // Auto-expand if we get image/video/audio (media worth seeing)
      if (imageLayers.length > 0 || videoLayers.length > 0 || audioLayers.length > 0) {
        setMinimized(false);
      }
    }
    prevCount.current = layerCount;
  }, [layerCount, imageLayers.length, videoLayers.length, audioLayers.length]);

  // ── drag ──────────────────────────────────────────────────────────────────
  const lastMouse = useRef({ x: 0, y: 0 });

  const onDragStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      lastMouse.current = { x: e.clientX, y: e.clientY };

      const onMove = (ev: MouseEvent) => {
        const dx = ev.clientX - lastMouse.current.x;
        const dy = ev.clientY - lastMouse.current.y;
        lastMouse.current = { x: ev.clientX, y: ev.clientY };
        setPos((prev) => ({
          left: Math.max(0, Math.min(window.innerWidth - size.width, prev.left + dx)),
          top: Math.max(0, Math.min(window.innerHeight - HEADER_H - 8, prev.top + dy)),
        }));
      };
      const onUp = () => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    [],
  );

  // ── layer helpers ─────────────────────────────────────────────────────────
  const toggleLayer = (key: LayerKey) =>
    setHiddenLayers((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  const latestImage = imageLayers[imageLayers.length - 1];
  const latestVideo = videoLayers[videoLayers.length - 1];
  const latestAudio = audioLayers[audioLayers.length - 1];
  const latestText = textHighlights[textHighlights.length - 1];

  const showImage = !!latestImage && !hiddenLayers.has('image');
  const showVideo = !!latestVideo && !hiddenLayers.has('video');
  const showAudio = !!latestAudio && !hiddenLayers.has('audio');
  const showText = !!latestText && !hiddenLayers.has('text');

  if (!hasContent || dismissed) return null;

  return (
    <div
      role="region"
      aria-label="Media output stage"
      style={{
        position: 'fixed',
        left: pos.left,
        top: pos.top,
        width: size.width,
        zIndex: 300,
        borderRadius: 12,
        overflow: 'hidden',
        background: 'rgba(6, 6, 12, 0.88)',
        backdropFilter: 'blur(28px)',
        WebkitBackdropFilter: 'blur(28px)',
        border: '1px solid rgba(255,255,255,0.09)',
        boxShadow: '0 12px 48px rgba(0,0,0,0.6), 0 0 0 0.5px rgba(255,255,255,0.04)',
      }}
    >
      {/* ── Header / drag handle ──────────────────────────────────────────── */}
      <div
        onMouseDown={onDragStart}
        style={{
          height: HEADER_H,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '0 10px',
          cursor: 'grab',
          background: 'rgba(255,255,255,0.025)',
          borderBottom: minimized ? 'none' : '1px solid rgba(255,255,255,0.06)',
          userSelect: 'none',
        }}
      >
        <DragDots />
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: 'rgba(255,255,255,0.35)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            flex: 1,
          }}
        >
          Media Output
        </span>
        {/* full width toggle */}
        <button
          onClick={() => {
            if (!fullWidth) {
              prevSize.current = size;
              setSize((s) => ({
                width: Math.min(MAX_W, window.innerWidth - 40),
                height: s.height,
              }));
              setPos((p) => ({ ...p, left: 20 }));
            } else {
              setSize(prevSize.current);
            }
            setFullWidth((f) => !f);
          }}
          title={fullWidth ? 'Restore width' : 'Full width'}
          style={iconBtn}
        >
          ⇔
        </button>

        {/* Layer toggles — only show for layers that have content */}
        {latestImage && (
          <LayerToggle label="🖼" active={!hiddenLayers.has('image')} onClick={() => toggleLayer('image')} title="Toggle image layer" />
        )}
        {latestVideo && (
          <LayerToggle label="🎬" active={!hiddenLayers.has('video')} onClick={() => toggleLayer('video')} title="Toggle video layer" />
        )}
        {latestAudio && (
          <LayerToggle label="🎵" active={!hiddenLayers.has('audio')} onClick={() => toggleLayer('audio')} title="Toggle audio layer" />
        )}
        {latestText && (
          <LayerToggle label="T" active={!hiddenLayers.has('text')} onClick={() => toggleLayer('text')} title="Toggle text layer" />
        )}

        <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.08)', flexShrink: 0, margin: '0 2px' }} />

        {/* Minimise */}
        <button
          onClick={() => setMinimized((m) => !m)}
          title={minimized ? 'Expand' : 'Minimise'}
          style={iconBtn}
        >
          {minimized ? '▲' : '▼'}
        </button>

        {/* Close */}
        <button
          onClick={() => { clearMediaLayers(); setDismissed(true); }}
          title="Close and clear media"
          style={{ ...iconBtn, color: 'rgba(255,255,255,0.3)' }}
        >
          ✕
        </button>
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      {!minimized && (
        <div
          style={{
            height: size.height - HEADER_H,
            position: 'relative',
            overflow: 'hidden',
            background: showImage ? 'transparent' : 'rgba(0,0,0,0.4)',
          }}
        >
          {/* ── Layer 1: Image (background) — z:1 ───────────────────────── */}
          {showImage && (
            <div
              style={{ position: 'absolute', inset: 0, zIndex: 1 }}
              aria-label="Image layer"
            >
              <img
                src={latestImage.url}
                alt="AI-generated output"
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              />
              {/* readability gradient */}
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  background:
                    'linear-gradient(to bottom, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.5) 100%)',
                }}
              />
            </div>
          )}

          {/* ── Layer 2: Video — z:2 ────────────────────────────────────── */}
          {showVideo && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                zIndex: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: showImage ? 'rgba(0,0,0,0.35)' : 'rgba(0,0,0,0.6)',
              }}
              aria-label="Video layer"
            >
              <video
                src={latestVideo.url}
                controls
                style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: 6 }}
              />
            </div>
          )}

          {/* ── Layer 3: Text — z:3 ─────────────────────────────────────── */}
          {showText && (
            <div
              style={{
                position: 'absolute',
                top: 10,
                left: 10,
                right: 10,
                zIndex: 3,
                background: showImage
                  ? 'rgba(6,6,12,0.72)'
                  : 'rgba(255,255,255,0.04)',
                backdropFilter: showImage ? 'blur(10px)' : 'none',
                WebkitBackdropFilter: showImage ? 'blur(10px)' : 'none',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 8,
                padding: '10px 12px',
                maxHeight: showAudio ? '52%' : '65%',
                overflow: 'auto',
              }}
              aria-label="Text layer"
            >
              <div
                style={{
                  fontSize: 12,
                  color: 'rgba(255,255,255,0.82)',
                  lineHeight: 1.55,
                  whiteSpace: 'pre-wrap',
                  overflowWrap: 'break-word',
                  wordBreak: 'break-word',
                }}
              >
                {latestText}
              </div>
              {textHighlights.length > 1 && (
                <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 8 }}>
                  {textHighlights.length} response{textHighlights.length > 1 ? 's' : ''} in layer
                </div>
              )}
            </div>
          )}

          {/* ── Layer 4: Audio — z:4 (always docked to bottom) ──────────── */}
          {showAudio && (
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                zIndex: 4,
                background: 'rgba(6,6,12,0.82)',
                backdropFilter: 'blur(10px)',
                WebkitBackdropFilter: 'blur(10px)',
                padding: '8px 12px 10px',
                borderTop: '1px solid rgba(255,255,255,0.07)',
              }}
              aria-label="Audio layer"
            >
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginBottom: 4, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                Audio
              </div>
              <audio src={latestAudio.url} controls style={{ width: '100%', height: 28, outline: 'none' }} />
            </div>
          )}

          {/* Empty state */}
          {!showImage && !showVideo && !showText && !showAudio && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                color: 'rgba(255,255,255,0.18)',
              }}
            >
              <span style={{ fontSize: 22 }}>◻</span>
              <span style={{ fontSize: 11 }}>All layers hidden</span>
            </div>
          )}

          {/* resize handle */}
          <div
            onMouseDown={(e) => {
              e.preventDefault();
              const startX = e.clientX;
              const startY = e.clientY;
              const startW = size.width;
              const startH = size.height;
              const onMove = (ev: MouseEvent) => {
                const dw = ev.clientX - startX;
                const dh = ev.clientY - startY;
                setSize({
                  width: Math.min(fullWidth ? window.innerWidth - 40 : MAX_W, Math.max(MIN_W, startW + dw)),
                  height: Math.min(MAX_H, Math.max(MIN_H, startH + dh)),
                });
              };
              const onUp = () => {
                window.removeEventListener('mousemove', onMove);
                window.removeEventListener('mouseup', onUp);
              };
              window.addEventListener('mousemove', onMove);
              window.addEventListener('mouseup', onUp);
            }}
            style={{
              position: 'absolute',
              width: 16,
              height: 16,
              bottom: 0,
              right: 0,
              cursor: 'nwse-resize',
              zIndex: 6,
            }}
          />
          {/* Layer count badge (bottom-right corner) */}
          {(imageLayers.length > 1 || videoLayers.length > 1 || audioLayers.length > 1) && (
            <div
              style={{
                position: 'absolute',
                bottom: showAudio ? 60 : 8,
                right: 8,
                zIndex: 5,
                display: 'flex',
                gap: 4,
              }}
            >
              {imageLayers.length > 1 && (
                <LayerCount label="🖼" count={imageLayers.length} />
              )}
              {videoLayers.length > 1 && (
                <LayerCount label="🎬" count={videoLayers.length} />
              )}
              {audioLayers.length > 1 && (
                <LayerCount label="🎵" count={audioLayers.length} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const LayerCount: React.FC<{ label: string; count: number }> = ({ label, count }) => (
  <div
    style={{
      background: 'rgba(0,0,0,0.6)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: 20,
      padding: '2px 7px',
      fontSize: 10,
      color: 'rgba(255,255,255,0.45)',
      display: 'flex',
      alignItems: 'center',
      gap: 3,
    }}
  >
    <span>{label}</span>
    <span>{count}</span>
  </div>
);

export default MediaStage;
