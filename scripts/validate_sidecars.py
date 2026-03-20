#!/usr/bin/env python3
"""
Validate that each image sidecar JSON in media/images contains
the required keys and prints a short report.
"""
import os
import json

BASE = os.path.dirname(os.path.dirname(__file__))
MEDIA_DIR = os.path.join(BASE, "media", "images")
REQUIRED_KEYS = ["filename", "prompt", "mime_type", "created_at", "size", "source", "remote_url"]

errors = []
count = 0
missing_counts = {k:0 for k in REQUIRED_KEYS}

for name in sorted(os.listdir(MEDIA_DIR)):
    if not name.lower().endswith('.json'):
        continue
    path = os.path.join(MEDIA_DIR, name)
    count += 1
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        errors.append((name, f'INVALID_JSON: {e}'))
        continue
    for k in REQUIRED_KEYS:
        if k not in data or data.get(k) in (None, ""):
            missing_counts[k] += 1
            errors.append((name, f'MISSING_KEY: {k}'))

print(f'Total sidecars checked: {count}')
if errors:
    print('\nErrors / missing keys:')
    for e in errors[:200]:
        print('-', e[0], e[1])
    if len(errors) > 200:
        print('... (truncated)')
else:
    print('All sidecars contain required keys.')

print('\nSummary missing counts:')
for k,v in missing_counts.items():
    print(f'  {k}: {v}')

if errors:
    raise SystemExit(1)
