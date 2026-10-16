import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from monitor.db import DB
from monitor.models import Reading
from monitor.identity import same_product
from monitor.presentation import offer_text
from monitor.service import Monitor
from monitor.subscriptions import ask_scope, handle_subscription


@pytest.fixture
def data(tmp_path):
    path = str(tmp_path / "subscriptions.sqlite")
    db = DB(path)
    config = SimpleNamespace(
        minimum=999999, percent=99, target=1, interval=18000, user=42, chat=-1
    )
    r = Reading(
        "ROG STRIX B550-F GAMING WIFI II",
        "KaBuM!",
        "NewCondition",
        "Pix",
        100000,
        "in_stock",
        identifiers={"mpn": "rog strix b550 f gaming wifi ii", "brand": "asus"},
    )
    ad = db.save_ad("https://www.kabum.com.br/produto/42", "KaBuM", r)
    yield db, config, r, ad, path
    db.conn.close()


def test_id_stable_search_is_not_monitoring_and_restart(data):
    db, c, r, ad, path = data
    again = db.save_ad(ad["url"], ad["store"], replace(r, price=90000))
    assert ad["id"] == again["id"]
    assert not db.rows("SELECT * FROM products")
    assert f"🆔 ID do anúncio: {ad['id']}\n" in offer_text(r, "KaBuM", ad_id=ad["id"])
    token = db.request_scope(ad["id"])
    other = DB(path)
    try:
        assert other.get_ad(ad["id"])["url"] == ad["url"]
        pid, created = other.subscribe(token, "site", c)
        assert created
        assert (
            other.rows("SELECT query FROM products WHERE id=?", (pid,))[0]["query"]
            == ad["url"]
        )
    finally:
        other.conn.close()


def test_scopes_persistent_and_duplicate_click_idempotent(data):
    db, c, r, ad, path = data
    token = db.request_scope(ad["id"])
    pid, created = db.subscribe(token, "all", c)
    assert created
    assert db.subscribe(token, "site", c) == (pid, False)  # Primeiro clique vence.
    assert db.subscribe(db.request_scope(ad["id"]), "all", c) == (pid, False)
    p = db.rows("SELECT * FROM products WHERE id=?", (pid,))[0]
    assert p["scope"] == "all" and p["query"] == r.title and p["alert_mode"] == "all"
    assert not db.rows(
        "SELECT * FROM prices"
    )  # Base sera uma consulta fresca, nao o preco antigo da busca.
    assert db.rows("SELECT confirmed FROM candidates")[0]["confirmed"] == 1
    db.run("DELETE FROM products WHERE id=?", (pid,))
    assert db.subscribe(token, "all", c) == (None, False)
    assert db.get_ad(ad["id"])  # ID de busca continua disponivel para nova assinatura.


def test_model_change_new_ad_id_and_stale_prompt_rejected(data):
    db, c, r, ad, path = data
    changed = db.save_ad(
        ad["url"],
        ad["store"],
        replace(r, identifiers={"mpn": "other", "brand": "asus"}),
    )
    assert changed["id"] != ad["id"]
    token = db.request_scope(ad["id"])
    db.run("UPDATE ads SET title=? WHERE id=?", ("Changed title", ad["id"]))
    assert db.subscribe(token, "site", c) is None


def test_all_changes_up_down_repeat_and_failure(data):
    db, c, r, ad, path = data
    pid, _ = db.subscribe(db.request_scope(ad["id"]), "site", c)
    candidate = db.rows("SELECT * FROM candidates WHERE product=?", (pid,))[0]
    db.record(candidate, r)
    assert not db.rows("SELECT * FROM alerts")
    db.record(candidate, replace(r, price=110000))
    db.record(candidate, replace(r, price=110000))
    db.failure(candidate["id"], "reading_error")
    db.record(candidate, replace(r, price=None))
    db.record(candidate, replace(r, price=90000))
    alerts = db.rows("SELECT * FROM alerts")
    assert len(alerts) == 2
    assert "Aumento de preço" in alerts[0]["message"]
    assert "Queda de preço" in alerts[1]["message"] and "📉 QUEDA DE PREÇO" in alerts[1]["message"]
    assert "Preço anterior: R$ 1100.00" in alerts[1]["message"]
    assert db.rows("SELECT active FROM products")[0]["active"] == 1
    # Limites de queda/preco alvo sao ignorados intencionalmente no modo todas.


def test_filtered_drop_mode_remains_available(data):
    db, c, r, ad, path = data
    pid, _ = db.subscribe(db.request_scope(ad["id"]), "site", c)
    db.run(
        "UPDATE products SET alert_mode='drops',minimum=0,percent='0',target=NULL WHERE id=?",
        (pid,),
    )
    candidate = db.rows("SELECT * FROM candidates WHERE product=?", (pid,))[0]
    db.record(candidate, r)
    db.record(candidate, replace(r, price=110000))
    assert not db.rows("SELECT * FROM alerts")
    db.record(candidate, replace(r, price=90000))
    assert len(db.rows("SELECT * FROM alerts")) == 1


def test_cross_store_identity_strict_and_ambiguous(data):
    _, _, r, _, _ = data
    assert (
        same_product(r, replace(r, title="ASUS placa variante com mesmo MPN")) is True
    )
    assert (
        same_product(
            r, replace(r, identifiers={"mpn": "b550 f gaming wifi", "brand": "asus"})
        )
        is False
    )
    assert (
        same_product(
            r, replace(r, title="ROG STRIX B550-F GAMING WIFI", identifiers={})
        )
        is None
    )
    assert same_product(replace(r, identifiers={}), replace(r, identifiers={})) is True
    assert (
        same_product(
            Reading("Placa mae", "", "", "", None),
            Reading("Placa mae", "", "", "", None),
        )
        is None
    )


def test_single_site_never_searches_and_all_discovers_exact_only(data):
    async def run():
        db, c, r, ad, _ = data

        class Fetch:
            def canonical(self, url):
                return url, url.split("/")[2].removeprefix("www.")

        search = SimpleNamespace(links=AsyncMock(return_value=[]))
        send = AsyncMock()
        monitor = Monitor(db, c, Fetch(), search, send)
        monitor.read = AsyncMock(return_value=[r])
        pid, _ = db.subscribe(db.request_scope(ad["id"]), "site", c)
        await monitor.check(pid)
        search.links.assert_not_awaited()
        assert monitor.read.await_count == 1
        pid, _ = db.subscribe(db.request_scope(ad["id"]), "all", c)
        matched = "https://www.pichau.com.br/same"
        unknown = "https://www.pichau.com.br/ambiguous"
        wrong = "https://www.pichau.com.br/wrong"
        search.links = AsyncMock(return_value=[matched, unknown, wrong])

        async def read(url):
            if url == matched:
                return [replace(r, title="ASUS ROG outro titulo", seller="Pichau")]
            if url == unknown:
                return [
                    replace(
                        r,
                        title="ROG STRIX B550-F GAMING WIFI",
                        identifiers={},
                        seller="Pichau",
                    )
                ]
            if url == wrong:
                return [replace(r, identifiers={"mpn": "b650", "brand": "asus"})]
            return [r]

        monitor.read = read
        await monitor.check(pid)
        search.links.assert_awaited_once_with('asus rog strix b550 f gaming wifi ii')
        indexed = {
            x["url"]: x
            for x in db.rows("SELECT * FROM candidates WHERE product=?", (pid,))
        }
        assert indexed[matched]["confirmed"] == 1
        assert indexed[unknown]["confirmed"] == 0
        assert indexed[wrong]["title"] == ""
        assert (
            len(
                db.rows(
                    "SELECT * FROM series s JOIN candidates c ON c.id=s.candidate WHERE c.product=?",
                    (pid,),
                )
            )
            == 2
        )

    asyncio.run(run())


def test_monitor_failure_is_readable_and_preserves_last_price(data):
    from monitor.adapters.base import ReadError
    async def run():
        db, config, reading, ad, _ = data
        pid, _ = db.subscribe(db.request_scope(ad['id']), 'site', config)
        candidate = db.rows('SELECT * FROM candidates WHERE product=?', (pid,))[0]
        db.record(candidate, reading)
        before = db.rows('SELECT last FROM series')[0]['last']
        fetcher = SimpleNamespace(canonical=lambda url: (url, 'kabum.com.br'))
        monitor = Monitor(db, config, fetcher, None, AsyncMock())
        monitor.read = AsyncMock(side_effect=ReadError('blocked_no_bypass'))
        message = await monitor.check(pid)
        assert 'A loja bloqueou o acesso' in message
        assert 'blocked_no_bypass' not in message
        assert ad['url'] in message
        assert db.rows('SELECT last FROM series')[0]['last'] == before
        assert db.rows('SELECT status FROM checks ORDER BY id DESC')[0]['status'] == 'blocked_no_bypass'
    asyncio.run(run())


def test_missing_comparison_fields_are_identified(data):
    db, config, reading, ad, _ = data
    pid, _ = db.subscribe(db.request_scope(ad['id']), 'site', config)
    candidate = db.rows('SELECT * FROM candidates WHERE product=?', (pid,))[0]
    message = db.record(candidate, replace(reading, condition='', seller=''))
    assert 'vendedor' in message and 'condição' in message
    assert 'pagamento' not in message
    assert not db.rows('SELECT * FROM alerts')


def test_monitor_rejects_changed_brand_without_updating_last_price(data):
    async def run():
        db, config, reading, ad, _ = data
        pid = db.add('Teclado Mecânico Logitech G PRO RGB', config)
        candidate = db.candidate(pid, 'https://www.pichau.com.br/keyboard', 'Pichau')
        fetcher = SimpleNamespace(canonical=lambda url: (url, 'pichau.com.br'))
        monitor = Monitor(db, config, fetcher, SimpleNamespace(links=AsyncMock(return_value=[])), AsyncMock())
        monitor.read = AsyncMock(return_value=[replace(reading, title='Teclado Corsair K65 Pro Mini RGB')])
        message = await monitor.check(pid)
        assert 'produto incompatível' in message
        assert not db.rows('SELECT * FROM series')
        assert db.rows('SELECT status FROM checks WHERE candidate=?', (candidate['id'],))[0]['status'] == 'different_model'
    asyncio.run(run())


def test_scope_buttons_and_callback_authorization(data):
    async def run():
        db, c, r, ad, _ = data
        bot = SimpleNamespace(send_message=AsyncMock())
        await ask_scope(bot, c.chat, db, ad["id"])
        markup = bot.send_message.await_args.kwargs["reply_markup"]
        assert len(markup.inline_keyboard) == 3
        assert markup.inline_keyboard[-1][0].callback_data == 'ui:home'
        callback = markup.inline_keyboard[0][0].callback_data
        assert len(callback.encode()) <= 64
        q = SimpleNamespace(
            data=callback, answer=AsyncMock(), edit_message_reply_markup=AsyncMock()
        )
        update = SimpleNamespace(
            callback_query=q,
            effective_user=SimpleNamespace(id=99),
            effective_chat=SimpleNamespace(id=-1),
        )
        send = AsyncMock()
        scheduled = []
        await handle_subscription(update, c, db, bot, send, scheduled.append)
        assert not db.rows("SELECT * FROM products")
        update.effective_user.id = 42
        await handle_subscription(update, c, db, bot, send, scheduled.append)
        await handle_subscription(update, c, db, bot, send, scheduled.append)
        assert len(scheduled) == 1 and len(db.rows("SELECT * FROM products")) == 1

    asyncio.run(run())


def test_schema_identifiers_validated_and_sku_not_model():
    from monitor.adapters.base import StructuredAdapter

    product = {
        "@type": "Product",
        "name": "Placa modelo B550-F",
        "gtin13": "4006381333931",
        "mpn": "ROG-STRIX-B550-F-GAMING-WIFI-II",
        "brand": {"name": "ASUS"},
        "sku": "1234",
    }
    html = '<script type="application/ld+json">' + json.dumps(product) + "</script>"
    r = StructuredAdapter().parse(html, "https://example.org/")[0]
    assert r.identifiers["gtin"] == "04006381333931"
    assert r.identifiers["mpn"] == "rog strix b550 f gaming wifi ii"
    assert "sku" not in r.identifiers
    product["gtin13"] = "4006381333932"
    r = StructuredAdapter().parse(
        '<script type="application/ld+json">' + json.dumps(product) + "</script>", ""
    )[0]
    assert "gtin" not in r.identifiers


def test_legacy_schema_migration_keeps_schedule_and_enables_all(tmp_path):
    import sqlite3

    path = str(tmp_path / "legacy.sqlite")
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE products(id INTEGER PRIMARY KEY,query TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,next_due REAL NOT NULL DEFAULT 0,minimum INTEGER NOT NULL,percent TEXT NOT NULL,target INTEGER)"
    )
    conn.execute(
        "INSERT INTO products(query,active,next_due,minimum,percent) VALUES ('produto',0,123456,0,'0')"
    )
    conn.commit()
    conn.close()
    db = DB(path)
    try:
        p = db.rows("SELECT * FROM products")[0]
        assert p["active"] == 0 and p["next_due"] == 123456
        assert p["alert_mode"] == "all" and p["scope"] == "legacy"
    finally:
        db.conn.close()
