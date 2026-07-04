/** LM-generated images saved under /media/images/ — not stock placeholder hosts. */
const PLACEHOLDER_HOST_RE =
  /picsum\.photos|images\.unsplash\.com|placehold\.co|placeholder\.com|via\.placeholder|loremflickr\.com/i;

export const IMAGE_URL_RE =
  /(?:https?:\/\/[^\s\)'"<>]*\/media\/images\/[^\s\)'"<>]+\.(?:png|jpg|jpeg|gif|webp|svg|avif)(?:\?\S*)?|\/media\/images\/[^\s\)'"<>]+\.(?:png|jpg|jpeg|gif|webp|svg|avif)(?:\?\S*)?)/gi;

export interface ContentSegment {
  kind: 'text' | 'image';
  value: string;
}

export function isPlaceholderImageUrl(url: string): boolean {
  return PLACEHOLDER_HOST_RE.test(url);
}

export function splitContentIntoSegments(content: string): ContentSegment[] {
  const segments: ContentSegment[] = [];
  let lastIndex = 0;
  IMAGE_URL_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = IMAGE_URL_RE.exec(content)) !== null) {
    if (isPlaceholderImageUrl(match[0])) continue;
    if (match.index > lastIndex) {
      segments.push({ kind: 'text', value: content.slice(lastIndex, match.index) });
    }
    segments.push({ kind: 'image', value: match[0] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < content.length) {
    segments.push({ kind: 'text', value: content.slice(lastIndex) });
  }
  return segments.length > 0 ? segments : [{ kind: 'text', value: content }];
}

export function extractImageUrls(content: string): string[] {
  IMAGE_URL_RE.lastIndex = 0;
  const found = content.match(IMAGE_URL_RE) || [];
  return [...new Set(found.filter((u) => !isPlaceholderImageUrl(u)))];
}

export function isLocalMediaPath(url: string): boolean {
  return url.includes('/media/images/') || url.includes('media/images/');
}

export function normalizeLocalMediaPath(url: string): string {
  if (url.startsWith('/')) return url;
  if (url.startsWith('media/')) return `/${url}`;
  return url;
}

/** Prefer the newest local image path mentioned in workflow output text. */
export function primaryImageFromText(...parts: Array<string | undefined | null>): string | null {
  const list = parts.filter((p): p is string => Boolean(p));
  for (let i = list.length - 1; i >= 0; i--) {
    const urls = extractImageUrls(list[i]).filter(isLocalMediaPath);
    if (urls.length) return normalizeLocalMediaPath(urls[urls.length - 1]);
  }
  return null;
}