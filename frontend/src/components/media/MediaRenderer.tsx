import React, { useState } from 'react';
import { MediaMeta } from '@/types/api';

interface MediaProps {
  media: MediaMeta;
}

const PLACEHOLDER_IMAGE_DATA_URI = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" preserveAspectRatio="xMidYMid meet">
  <rect width="320" height="180" fill="#111827" />
  <text x="160" y="95" text-anchor="middle" fill="#94a3b8" font-family="Inter,system-ui,sans-serif" font-size="18">Image unavailable</text>
</svg>
`)} `;

const normalizeMediaPath = (url: string) => {
  if (!url) return url;
  return url.startsWith('/') ? url : `/${url}`;
};

const MediaRenderer: React.FC<MediaProps> = ({ media }) => {
  const [loadFailed, setLoadFailed] = useState(false);
  const src = normalizeMediaPath(media.url || '');
  switch (media.type) {
    case 'image':
      return (
        <img
          src={loadFailed ? PLACEHOLDER_IMAGE_DATA_URI : src}
          alt={media.overlay_text || 'Image'}
          className="media-renderer__image"
          onError={() => setLoadFailed(true)}
        />
      );
    case 'video':
      return <video src={src} controls className="media-renderer__video" />;
    case 'audio':
      return <audio src={src} controls className="media-renderer__audio" />;
    case 'text':
      return <div>{media.overlay_text}</div>;
    default:
      return null;
  }
};

export default MediaRenderer;