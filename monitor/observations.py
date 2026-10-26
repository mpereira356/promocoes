"""Local observed prices, separate from confirmed monitoring and alert history."""
import hashlib
import json
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from .identity import specific_part_number

SCHEMA = '''
CREATE TABLE IF NOT EXISTS price_observations (
 offer_key TEXT NOT NULL, at REAL NOT NULL, bucket INTEGER NOT NULL, price INTEGER NOT NULL,
 PRIMARY KEY(offer_key,bucket));
CREATE INDEX IF NOT EXISTS observations_at ON price_observations(at);
'''


def strong_identity(reading):
    ids = reading.identifiers
    return bool(ids.get('gtin') or (ids.get('brand') and specific_part_number(ids.get('mpn'))))


def key(url, reading):
    p = urlsplit(url)
    query = urlencode(sorted((k, v) for k, v in parse_qsl(p.query)
                             if not k.lower().startswith('utm_') and k.lower() not in ('ref', 'tag', 'gclid', 'fbclid')))
    canonical = urlunsplit((p.scheme, p.netloc.lower(), p.path, query, ''))
    identity = [canonical, reading.title, reading.seller, reading.condition, reading.payment,
                reading.currency, reading.identifiers]
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def record(conn, url, readings, now=None):
    now = time.time() if now is None else now
    rows = [(key(url, r), now, int(now // 21600), r.price) for r in readings
            if r.comparable and r.stock == 'in_stock' and strong_identity(r)]
    with conn:
        # One observation per six-hour slot prevents a single query from
        # fabricating a long history. Keep the lowest seen within that slot.
        conn.executemany('INSERT INTO price_observations VALUES (?,?,?,?) '
                         'ON CONFLICT(offer_key,bucket) DO UPDATE SET price=MIN(price,excluded.price)', rows)
        conn.execute('DELETE FROM price_observations WHERE at < ?', (now - 90 * 86400,))


def history(conn, url, reading, now=None):
    now = time.time() if now is None else now
    # At least a full day before this query; today's reads cannot validate themselves.
    row = conn.execute('SELECT MIN(price),COUNT(DISTINCT CAST(at / 86400 AS INTEGER)),MAX(at)-MIN(at) '
                       'FROM price_observations WHERE offer_key=? AND at>=? AND at<=?',
                       (key(url, reading), now - 30 * 86400, now - 86400)).fetchone()
    return {'lowest': row[0], 'days': row[1], 'span_seconds': row[2] or 0}
