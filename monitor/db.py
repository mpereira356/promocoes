import json
import sqlite3
import time
from pathlib import Path
from dataclasses import asdict
from .models import normalize, qualifies

SCHEMA = """
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (
 id INTEGER PRIMARY KEY, query TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 next_due REAL NOT NULL DEFAULT 0, minimum INTEGER NOT NULL, percent TEXT NOT NULL, target INTEGER);
CREATE TABLE IF NOT EXISTS candidates (
 id INTEGER PRIMARY KEY, product INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 url TEXT NOT NULL, store TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
 confirmed INTEGER NOT NULL DEFAULT 0, notified INTEGER NOT NULL DEFAULT 0, UNIQUE(product,url));
CREATE TABLE IF NOT EXISTS checks (
 id INTEGER PRIMARY KEY, candidate INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
 at REAL NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS series (
 id INTEGER PRIMARY KEY, candidate INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
 title TEXT NOT NULL, seller TEXT NOT NULL, condition TEXT NOT NULL, payment TEXT NOT NULL, currency TEXT NOT NULL,
 last INTEGER NOT NULL, lowest INTEGER NOT NULL, episode INTEGER NOT NULL DEFAULT 0,
 UNIQUE(candidate,title,seller,condition,payment,currency));
CREATE TABLE IF NOT EXISTS prices (
 id INTEGER PRIMARY KEY, series INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
 at REAL NOT NULL, price INTEGER NOT NULL, stock TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alerts (
 id INTEGER PRIMARY KEY, series INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
 episode INTEGER NOT NULL, message TEXT NOT NULL, sent_at REAL,
 UNIQUE(series,episode));
CREATE TABLE IF NOT EXISTS ads (
 id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, title TEXT NOT NULL,
 title_key TEXT NOT NULL, store TEXT NOT NULL, reading TEXT NOT NULL, observed_at REAL NOT NULL,
 UNIQUE(url,title_key));
CREATE TABLE IF NOT EXISTS scope_requests (
 token TEXT PRIMARY KEY, ad INTEGER NOT NULL REFERENCES ads(id), fingerprint TEXT NOT NULL,
 product INTEGER REFERENCES products(id) ON DELETE SET NULL, completed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS subscriptions (
 ad INTEGER NOT NULL REFERENCES ads(id), scope TEXT NOT NULL,
 product INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 PRIMARY KEY(ad,scope));
"""


class DB:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        from .observations import SCHEMA as OBSERVATIONS_SCHEMA
        self.conn.executescript(OBSERVATIONS_SCHEMA)
        # Migracao aditiva: preserva bancos de instalacoes anteriores.
        if "image" not in {
            r["name"] for r in self.rows("PRAGMA table_info(candidates)")
        }:
            self.run("ALTER TABLE candidates ADD COLUMN image TEXT NOT NULL DEFAULT ''")
            self.run("UPDATE candidates SET notified=0 WHERE confirmed=0")
        for table, columns in {
            "products": [
                ("scope", "TEXT NOT NULL DEFAULT 'legacy'"),
                ("seed_ad", "INTEGER"),
                ("alert_mode", "TEXT NOT NULL DEFAULT 'all'"),
            ],
            "candidates": [("ad_id", "INTEGER")],
        }.items():
            existing = {r["name"] for r in self.rows(f"PRAGMA table_info({table})")}
            for column, definition in columns:
                if column not in existing:
                    self.run(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def save_ad(self, url, store, reading):
        title_key = (
            normalize(reading.title)
            + "|"
            + json.dumps(reading.identifiers, sort_keys=True, ensure_ascii=False)
        )
        with self.conn:
            self.conn.execute(
                """INSERT INTO ads(url,title,title_key,store,reading,observed_at)
                VALUES (?,?,?,?,?,?) ON CONFLICT(url,title_key) DO UPDATE SET
                reading=excluded.reading,observed_at=excluded.observed_at,store=excluded.store""",
                (
                    url,
                    reading.title,
                    title_key,
                    store,
                    json.dumps(asdict(reading), ensure_ascii=False),
                    time.time(),
                ),
            )
        return self.rows(
            "SELECT * FROM ads WHERE url=? AND title_key=?",
            (url, title_key),
        )[0]

    def observe_prices(self, url, readings, now=None):
        from .observations import record
        record(self.conn, url, readings, now)

    def observed_history(self, url, reading, now=None):
        from .observations import history
        return history(self.conn, url, reading, now)

    def get_ad(self, ad_id):
        rows = self.rows("SELECT * FROM ads WHERE id=?", (ad_id,))
        return rows[0] if rows else None

    def request_scope(self, ad_id):
        import uuid
        from .subscriptions import ad_fingerprint

        ad = self.get_ad(ad_id)
        if ad is None:
            return None
        token = uuid.uuid4().hex[:24]
        self.run(
            "INSERT INTO scope_requests(token,ad,fingerprint) VALUES (?,?,?)",
            (token, ad_id, ad_fingerprint(ad)),
        )
        return token

    def subscribe(self, token, scope, config):
        from .subscriptions import ad_fingerprint

        if scope not in ("site", "all"):
            return None
        with self.conn:
            requests = self.rows("SELECT * FROM scope_requests WHERE token=?", (token,))
            if not requests:
                return None
            request = requests[0]
            if request["completed"]:
                return request["product"], False
            ad = self.get_ad(request["ad"])
            if ad is None or ad_fingerprint(ad) != request["fingerprint"]:
                return None
            rows = self.rows(
                "SELECT product FROM subscriptions WHERE ad=? AND scope=?",
                (ad["id"], scope),
            )
            if rows:
                pid = rows[0]["product"]
                created = False
            else:
                query = ad["url"] if scope == "site" else ad["title"]
                cursor = self.conn.execute(
                    """INSERT INTO products(query,minimum,percent,target,scope,seed_ad,alert_mode)
                    VALUES (?,?,?,?,?,?,'all')""",
                    (
                        query,
                        config.minimum,
                        str(config.percent),
                        config.target,
                        scope,
                        ad["id"],
                    ),
                )
                pid = cursor.lastrowid
                self.conn.execute(
                    """INSERT INTO candidates(product,url,store,title,confirmed,image,ad_id)
                    VALUES (?,?,?,?,1,?,?)""",
                    (
                        pid,
                        ad["url"],
                        ad["store"],
                        ad["title"],
                        json.loads(ad["reading"]).get("image", ""),
                        ad["id"],
                    ),
                )
                self.conn.execute(
                    "INSERT INTO subscriptions(ad,scope,product) VALUES (?,?,?)",
                    (ad["id"], scope, pid),
                )
                created = True
            self.conn.execute(
                "UPDATE scope_requests SET completed=1,product=? WHERE token=?",
                (pid, token),
            )
        return pid, created

    def defer_candidate(self, cid, fingerprint):
        from .selection import identity

        rows = self.rows('SELECT * FROM candidates WHERE id=?', (cid,))
        if not rows or not rows[0]['title'] or identity(rows[0]) != fingerprint:
            return None
        candidate = rows[0]
        if not candidate['confirmed']:
            self.run('UPDATE candidates SET notified=1 WHERE id=?', (cid,))
        return candidate

    def confirm_candidate(self, cid, fingerprint=None):
        from .selection import identity

        rows = self.rows("SELECT * FROM candidates WHERE id=?", (cid,))
        if not rows or not rows[0]["title"]:
            return None
        candidate = rows[0]
        if fingerprint is not None and fingerprint != identity(candidate):
            return None
        self.run("UPDATE candidates SET confirmed=1 WHERE id=?", (cid,))
        return candidate

    def rows(self, sql, args=()):
        return self.conn.execute(sql, args).fetchall()

    def run(self, sql, args=()):
        with self.conn:
            return self.conn.execute(sql, args).lastrowid

    def add(self, query, config):
        return self.run(
            "INSERT INTO products(query,minimum,percent,target) VALUES (?,?,?,?)",
            (query, config.minimum, str(config.percent), config.target),
        )

    def candidate(self, product, url, store):
        self.run(
            "INSERT OR IGNORE INTO candidates(product,url,store) VALUES (?,?,?)",
            (product, url, store),
        )
        return self.rows(
            "SELECT * FROM candidates WHERE product=? AND url=?", (product, url)
        )[0]

    def failure(self, cid, code):
        self.run(
            "INSERT INTO checks(candidate,at,status,detail) VALUES (?,?,?,?)",
            (cid, time.time(), code, ""),
        )

    def record(self, candidate, reading):
        now = time.time()
        with self.conn:
            self.conn.execute(
                "UPDATE candidates SET image=? WHERE id=?",
                (reading.image, candidate["id"]),
            )
            self.conn.execute(
                "INSERT INTO checks(candidate,at,status,detail) VALUES (?,?,?,?)",
                (
                    candidate["id"],
                    now,
                    "ok",
                    json.dumps(asdict(reading), ensure_ascii=False),
                ),
            )
            if not candidate["confirmed"]:
                self.conn.execute(
                    "UPDATE candidates SET title=? WHERE id=?",
                    (reading.title, candidate["id"]),
                )
                return 'Confirme o modelo com /confirmar %s' % candidate["id"]
            if normalize(candidate["title"]) != normalize(reading.title):
                self.conn.execute(
                    "UPDATE candidates SET confirmed=0,notified=0,title=? WHERE id=?",
                    (reading.title, candidate["id"]),
                )
                return (
                    'O título da oferta mudou. É necessária uma nova confirmação com /confirmar %s'
                    % candidate["id"]
                )
            if not reading.comparable:
                missing = []
                if not reading.seller:
                    missing.append('vendedor')
                if not reading.condition:
                    missing.append('condição')
                if not reading.payment:
                    missing.append('forma de pagamento')
                if not isinstance(reading.price, int) or isinstance(reading.price, bool) or reading.price <= 0:
                    missing.append('preço válido')
                if reading.currency != 'BRL':
                    missing.append('moeda BRL')
                return 'Leitura registrada; comparação suspensa por falta de: ' + ', '.join(missing) + '.'
            key = (
                candidate["id"],
                normalize(reading.title),
                reading.seller,
                reading.condition,
                reading.payment,
                reading.currency,
            )
            row = self.conn.execute(
                "SELECT * FROM series WHERE candidate=? AND title=? AND seller=? AND condition=? AND payment=? AND currency=?",
                key,
            ).fetchone()
            if row is None:
                cursor = self.conn.execute(
                    "INSERT INTO series(candidate,title,seller,condition,payment,currency,last,lowest) VALUES (?,?,?,?,?,?,?,?)",
                    key + (reading.price, reading.price),
                )
                sid = cursor.lastrowid
                result = 'Nova oferta ou condição: preço inicial registrado. Ainda não há preço anterior comparável.'
            else:
                sid = row["id"]
                episode = row["episode"] + int(row["last"] != reading.price)
                self.conn.execute(
                    "UPDATE series SET last=?,lowest=MIN(lowest,?),episode=? WHERE id=?",
                    (reading.price, reading.price, episode, sid),
                )
                p = self.conn.execute(
                    "SELECT * FROM products WHERE id=?", (candidate["product"],)
                ).fetchone()
                changed = reading.price != row["last"]
                notify = changed and (
                    p["alert_mode"] == "all"
                    or qualifies(
                        row["last"],
                        reading.price,
                        p["minimum"],
                        p["percent"],
                        p["target"],
                    )
                )
                if reading.stock == "in_stock" and notify:
                    delta = row["last"] - reading.price
                    from datetime import datetime
                    from zoneinfo import ZoneInfo

                    direction = (
                        "📉 Queda de preço" if delta > 0 else "📈 Aumento de preço"
                    )
                    variation = "Economia" if delta > 0 else "Aumento"
                    unit = '/kg' if reading.public_unit_price else ''
                    payment_label = reading.payment or ('não confirmado; preço público por kg' if reading.public_unit_price else '')
                    msg = (
                        f"{'📉 QUEDA DE PREÇO' if delta > 0 else '📈 AUMENTO DE PREÇO'}\n\n{direction}: {reading.title}\nMonitoramento {candidate['product']} · Oferta {candidate['id']}\n\n🏪 Loja: {candidate['store']}\n👤 Vendedor: {reading.seller}\n"
                        f"📦 Condição: {reading.condition}\n\n💰 Preço anterior: R$ {row['last']/100:.2f}{unit}\n💰 Preço atual: R$ {reading.price/100:.2f}{unit}\n"
                        f"{variation}: R$ {abs(delta)/100:.2f} ({abs(delta)/row['last']*100:.2f}%)\n"
                        f"📉 Menor preço registrado: R$ {min(row['lowest'],reading.price)/100:.2f}{unit}\n💳 Pagamento: {payment_label}\n"
                        f"📊 Estoque: disponível segundo a página\n🚚 Frete não incluído.\n"
                        f"\nConsulta: {datetime.fromtimestamp(now,ZoneInfo('America/Sao_Paulo')).isoformat(timespec='seconds')}\n{candidate['url']}"
                    )
                    if reading.public_unit_price:
                        msg += ('\n\nPreço público por kg na loja e no CEP indicados. '
                                'Pagamento não confirmado; total depende da pesagem. '
                                'A queda observada não comprova desconto sobre o mercado.')
                    self.conn.execute(
                        "INSERT OR IGNORE INTO alerts(series,episode,message) VALUES (?,?,?)",
                        (sid, episode, msg),
                    )
                result = f'Preço atual: R$ {reading.price/100:.2f} · Menor registrado: R$ {min(row["lowest"],reading.price)/100:.2f}'
            self.conn.execute(
                "INSERT INTO prices(series,at,price,stock) VALUES (?,?,?,?)",
                (sid, now, reading.price, reading.stock),
            )
        return result
