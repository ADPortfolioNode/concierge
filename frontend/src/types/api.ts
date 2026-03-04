export interface MediaMeta {
  type: 'image' | 'video' | 'audio' | 'text' | 'none';
  url: string | null;
  overlay_text: string | null;
  mime_type: string | null;
}

export interface ApiResponse<T = any> {
  status: 'success' | 'error';
  timestamp: string;
  request_id: string;
  data: T;
  meta: {
    confidence: number;
    priority: number;
    media: MediaMeta;
  };
  errors: null | any[];
}
