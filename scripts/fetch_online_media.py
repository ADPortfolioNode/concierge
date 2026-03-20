#!/usr/bin/env python3
"""
Fetch images from RSS feeds (or provided URLs) and save into media/images
with sidecar JSON metadata compatible with the project's media contract.

Usage:
  python scripts/fetch_online_media.py [rss_url ...]

This script uses only the Python standard library so it can run without
extra dependencies.
"""

import os
import sys
import time
import hashlib
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re

DEFAULT_FEEDS = [
    "https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss",
]

BASE = os.path.dirname(os.path.dirname(__file__))
MEDIA_DIR = os.path.join(BASE, "media", "images")
os.makedirs(MEDIA_DIR, exist_ok=True)


def extract_image_urls_from_item(item):
    # 1) look for enclosure tags
    imgs = []
    for child in item:
        tag = child.tag.lower()
        if tag.endswith('enclosure'):
            url = child.attrib.get('url')
            if url:
                imgs.append(url)
    # 2) look in description HTML
    for desc in item.findall('description'):
        if desc is not None and desc.text:
            found = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', desc.text, flags=re.I)
            imgs.extend(found)
    # 3) media:content
    for m in item.findall('{http://search.yahoo.com/mrss/}content'):
        url = m.attrib.get('url')
        if url:
            imgs.append(url)
    return list(dict.fromkeys(imgs))


def download_and_save(url, title):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "concierge-fetcher/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            ctype = resp.headers.get_content_type() or 'image/jpeg'
            parsed = urllib.parse.urlparse(url)
            ext = os.path.splitext(parsed.path)[1] or ''
            if not ext:
                if ctype == 'image/png':
                    ext = '.png'
                else:
                    ext = '.jpg'
            h = hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]
            ts = int(time.time())
            fname = f"img_{h}_{ts}{ext}"
            path = os.path.join(MEDIA_DIR, fname)
            with open(path, 'wb') as f:
                f.write(content)
            sidecar = {
                "filename": fname,
                "prompt": title or '',
                "mime_type": ctype,
                "created_at": time.time(),
                "size": len(content),
                "source": "rss",
                "remote_url": url,
            }
            with open(path + '.json', 'w', encoding='utf-8') as s:
                json.dump(sidecar, s, indent=2)
            print('Saved', fname)
            return True
    except Exception as e:
        print('Failed', url, e)
        return False


def fetch_feed(url):
    print('Fetching', url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "concierge-fetcher/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            try:
                root = ET.fromstring(data)
            except Exception:
                print('Failed to parse feed XML for', url)
                return
            items = root.findall('.//item')
            for item in items[:20]:
                title_el = item.find('title')
                title = title_el.text if title_el is not None else ''
                imgs = extract_image_urls_from_item(item)
                for img in imgs:
                    download_and_save(img, title)
    except Exception as e:
        print('Failed to fetch feed', url, e)


def main():
    feeds = sys.argv[1:] or DEFAULT_FEEDS
    for f in feeds:
        fetch_feed(f)


if __name__ == '__main__':
    main()
