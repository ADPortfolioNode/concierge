import React from 'react';
import { MediaMeta } from '@/types/api';

interface MediaProps {
  media: MediaMeta;
}

const MediaRenderer: React.FC<MediaProps> = ({ media }) => {
  switch (media.type) {
    case 'image':
      return (
        <img
          src={media.url || ''}
          alt={media.overlay_text || 'Image'}
          style={{
            maxWidth: '100%',
            maxHeight: 400,
            borderRadius: 6,
            display: 'block',
            border: '1px solid rgba(255,255,255,0.1)',
            resize: 'both',
            overflow: 'auto',
          }}
        />
      );
    case 'video':
      return <video src={media.url || ''} controls style={{ maxWidth: '100%', borderRadius: 6 }} />;
    case 'audio':
      return <audio src={media.url || ''} controls style={{ width: '100%' }} />;
    case 'text':
      return <div>{media.overlay_text}</div>;
    default:
      return null;
  }
};

export default MediaRenderer;