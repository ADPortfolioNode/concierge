import React from 'react';
import { MediaMeta } from '@/types/api';

interface MediaProps {
  media: MediaMeta;
}

const MediaRenderer: React.FC<MediaProps> = ({ media }) => {
  switch (media.type) {
    case 'image':
      return <img src={media.url || ''} alt={media.overlay_text || ''} />;
    case 'video':
      return <video src={media.url || ''} controls />;
    case 'audio':
      return <audio src={media.url || ''} controls />;
    case 'text':
      return <div>{media.overlay_text}</div>;
    default:
      return null;
  }
};

export default MediaRenderer;