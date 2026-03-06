/**
 * FileUpload — drag-and-drop / click-to-pick file uploader.
 *
 * Calls POST /api/v1/workstation/upload and fires onUpload with the
 * returned file-context object when the upload succeeds.
 */

import React, { useCallback, useRef, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8001';
const UPLOAD_URL = `${API_BASE}/api/v1/workstation/upload`;

export interface FileContext {
  upload_id: string;
  filename: string;
  mime: string;
  size: number;
  extracted_text: string | null;
  metadata: Record<string, unknown>;
  type: 'file_context';
}

interface FileUploadProps {
  projectId?: string;
  onUpload: (ctx: FileContext) => void;
  onError?: (msg: string) => void;
}

const ACCEPTED = [
  '.txt', '.md', '.csv', '.json', '.py', '.js', '.ts',
  '.pdf', '.docx',
  '.png', '.jpg', '.jpeg', '.gif', '.webp',
  '.mp3', '.wav', '.m4a',
];

const FileUpload: React.FC<FileUploadProps> = ({ projectId, onUpload, onError }) => {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  // ------------------------------------------------------------------ //
  // Helpers                                                               //
  // ------------------------------------------------------------------ //

  const uploadFile = useCallback(
    async (file: File) => {
      setUploading(true);
      try {
        const form = new FormData();
        form.append('file', file);
        if (projectId) form.append('project_id', projectId);

        const resp = await fetch(UPLOAD_URL, { method: 'POST', body: form });
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(`Upload failed (${resp.status}): ${text}`);
        }

        const json = await resp.json();
        const ctx: FileContext = json?.data ?? json;
        onUpload(ctx);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        onError?.(msg);
      } finally {
        setUploading(false);
      }
    },
    [projectId, onUpload, onError]
  );

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      // Only process the first file per drop/pick.
      uploadFile(files[0]);
    },
    [uploadFile]
  );

  // ------------------------------------------------------------------ //
  // Drag-and-drop handlers                                                //
  // ------------------------------------------------------------------ //

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };
  const onDragLeave = () => setDragging(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  // ------------------------------------------------------------------ //
  // Render                                                                //
  // ------------------------------------------------------------------ //

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => !uploading && inputRef.current?.click()}
      style={{
        border: `1px dashed ${dragging ? '#7c6af7' : 'rgba(255,255,255,0.15)'}`,
        borderRadius: 6,
        padding: '8px 12px',
        cursor: uploading ? 'wait' : 'pointer',
        background: dragging ? 'rgba(124,106,247,0.08)' : 'transparent',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 13,
        color: 'rgba(255,255,255,0.55)',
        transition: 'border-color 0.15s, background 0.15s',
      }}
    >
      <span style={{ fontSize: 16 }}>{uploading ? '⏳' : '📎'}</span>
      <span>{uploading ? 'Uploading…' : 'Attach a file'}</span>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(',')}
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
};

export default FileUpload;
