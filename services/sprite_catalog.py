"""Small attributed catalog of sprite facts, refreshed from a public community list."""
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from time import monotonic
from threading import Lock
from urllib.parse import urlsplit
import requests

SOURCE = 'https://fortnite.bte.ar/it'
SNAPSHOT = Path(__file__).resolve().parent.parent / 'data' / 'sprites.json'
STYLES = {'base': 'Base', 'gold': 'Dorato', 'gummy': 'Gommoso',
          'galaxy': 'Galattico', 'gem': 'Gemma', 'cube': 'Cubo',
          'holo': 'Olografico', 'quack': 'Quack', 'cheatmaster': 'Maestro dei trucchi',
          'hacker': 'Hacker del bottino', 'bounty': 'Cacciatore di taglie',
          'trick': 'Dolcetto o scherzetto'}
_cache = None
_next_refresh = 0
_lock = Lock()


def parse_catalog(document):
    match = re.search(r'const\s+SPIRITS\s*=\s*', document)
    if not match:
        raise ValueError('Catalog data missing')
    raw, _ = json.JSONDecoder().raw_decode(document[match.end():])
    if not isinstance(raw, list) or not 20 <= len(raw) <= 2000:
        raise ValueError('Unexpected catalog size')
    items = []
    seen = set()
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError('Invalid catalog entry')
        key = row.get('key', '')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9-]{1,100}', key) or key in seen:
            raise ValueError('Invalid or duplicate sprite id')
        seen.add(key)
        icon = row.get('icon', '')
        if not isinstance(icon, str) or urlsplit(icon).scheme != 'https' or urlsplit(icon).hostname != 'fortnite.bte.ar':
            icon = ''
        items.append({'id': key, 'name': str(row.get('name') or key)[:150],
                      'family': str(row.get('familyLabel') or row.get('family') or key)[:100],
                      'style': str(row.get('style') or 'base')[:40],
                      'rarity': str(row.get('rarity') or '')[:40], 'image': icon,
                      'active': row.get('active') is True,
                      'archived': row.get('archived') is True,
                      'released': row.get('released') is True,
                      'name_official': row.get('nameOfficial') is True})
    return items


def get_catalog():
    global _cache, _next_refresh
    if _cache is None:
        _cache = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        _cache['stale'] = True
    if monotonic() < _next_refresh or not _lock.acquire(blocking=False):
        return _cache
    try:
        response = requests.get(SOURCE, timeout=(3, 8))
        response.raise_for_status()
        items = parse_catalog(response.text)
        # A partial upstream page must not wipe most of the known catalog.
        if len(items) < len(_cache['items']) * .8:
            raise ValueError('Incomplete catalog')
        _cache = {'items': items, 'checked_at': datetime.now(timezone.utc).isoformat(),
                  'source': SOURCE, 'stale': False}
        _next_refresh = monotonic() + 3600
    except (requests.RequestException, ValueError, TypeError):
        _cache = {**_cache, 'stale': True}
        _next_refresh = monotonic() + 300
    finally:
        _lock.release()
    return _cache
