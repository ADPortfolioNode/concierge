import React, { useState } from 'react';
import { MediaMeta } from '@/types/api';
import { resolveMediaUrl } from '@/utils/mediaUrl';

interface MediaProps {
  media: MediaMeta;
}

const MediaRenderer: React.FC<MediaProps> = ({ media }) => {
  const [loadFailed, setLoadFailed] = useState(false);
  const src = resolveMediaUrl(media.url || '');
  switch (media.type) {
    case 'image':
      if (!src) {
        return <div className="media-renderer__error">No image path provided.</div>;
      }
      if (loadFailed) {
        return (
          <div className="media-renderer__error">
            Could not load <code>{media.url}</code>
          </div>
        );
      }
      return (
        <img
          src={src}
          alt={media.overlay_text || 'Generated image'}
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