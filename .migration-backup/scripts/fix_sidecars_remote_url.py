#!/usr/bin/env python3
"""
Populate missing `remote_url` in sidecar JSON files with the local
`/media/images/<filename>` URL.
"""
import os
import json

BASE = os.path.dirname(os.path.dirname(__file__))
MEDIA_DIR = os.path.join(BASE, "media", "images")

updated = []
errors = []

for name in sorted(os.listdir(MEDIA_DIR)):
    if not name.lower().endswith('.json'):
        continue
    path = os.path.join(MEDIA_DIR, name)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        errors.append((name, f'INVALID_JSON: {e}'))
        continue
    # image filename (strip .json)
    image_name = name[:-5]
    if not data.get('remote_url'):
        data['remote_url'] = f"/media/images/{image_name}"
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            updated.append(name)
        except Exception as e:
            errors.append((name, f'WRITE_ERROR: {e}'))

print(f'Updated {len(updated)} sidecars')
for u in updated[:100]:
    print('-', u)
if errors:
    print('\nErrors:')
    for e in errors[:100]:
        print('-', e[0], e[1])
    raise SystemExit(1)
