import { makeApiUrl } from '@/config/activeServer';

/** Resolve `/media/images/...` paths to a fetchable URL on the active API host. */
export function resolveMediaUrl(url: string): string {
  if (!url) return url;
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://') || trimmed.startsWith('data:')) {
    return trimmed;
  }
  const path = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  if (path.startsWith('/media/')) {
    return makeApiUrl(path);
  }
  return path;
}