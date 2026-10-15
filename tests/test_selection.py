import asyncio
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock
from dataclasses import replace
import pytest

from monitor.adapters.base import StructuredAdapter, product_image
from monitor.db import DB, SCHEMA
from monitor.models import Reading
from monitor.selection import send_card, identity, handle_choice
from monitor.service import Monitor


def candidate_db(tmp_path):
    db = DB(str(tmp_path / "selection.sqlite"))
    config = SimpleNamespace(minimum=0, percent=0, target=None, user=42, chat=-1)
    pid = db.add("B550-F GAMING WIFI II", config)
    c = db.candidate(pid, "https://www.pichau.com.br/produto", "Pichau")
    r = Reading(
        "ROG STRIX B550-F GAMING WIFI II",
        "",
        "",
        "",
        None,
        image="https://cdn.example.org/product.jpg",
    )
    db.record(c, r)
    return db, config, db.rows("SELECT * FROM candidates")[0]


def update_for(c, user=42, chat=-1):
    query = SimpleNamespace(
        data=f"choose:{c['id']}:{identity(c)}",
        answer=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
    )
    return SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=user),
        effective_chat=SimpleNamespace(id=chat),
    )


def test_image_extracted_from_product():
    product = {
        "@type": "Product",
        "name": "Modelo simulado",
        "image": [{"@type": "ImageObject", "contentUrl": "/images/product.jpg"}],
    }
    html = '<script type="application/ld+json">' + json.dumps(product) + "</script>"
    r = StructuredAdapter().parse(html, "https://shop.example.org/product")[0]
    assert r.image == "https://shop.example.org/images/product.jpg"
    assert r.price is None


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/a.jpg",
        "https://127.0.0.1/a",
        "file:///tmp/a",
        "https://localhost/a",
        "https://u:p@example.org/a",
        "https://foo.internal/a",
        "https://example.org:90/a",
    ],
)
def test_unsafe_image_rejected(url):
    assert product_image(url, "https://shop.example.org/product") == ""


def test_photo_card_and_fallback(tmp_path):
    async def run():
        db, config, c = candidate_db(tmp_path)
        try:
            bot = SimpleNamespace(send_photo=AsyncMock(), send_message=AsyncMock())
            await send_card(bot, config.chat, c)
            bot.send_photo.assert_awaited_once()
            bot.send_message.assert_not_awaited()
            kwargs = bot.send_photo.await_args.kwargs
            assert len(kwargs["caption"]) <= 1024
            button = kwargs["reply_markup"].inline_keyboard[0][0]
            assert button.callback_data.startswith(f"choose:{c['id']}:")
            assert len(button.callback_data.encode()) <= 64
            bot.send_photo.side_effect = RuntimeError("image unavailable")
            await send_card(bot, config.chat, c)
            bot.send_message.assert_awaited_once()
            assert "Foto indisponivel" in bot.send_message.await_args.args[1]
        finally:
            db.conn.close()

    asyncio.run(run())


@pytest.mark.parametrize("user,chat", [(99, -1), (42, -2)])
def test_other_user_or_chat_cannot_choose(tmp_path, user, chat):
    async def run():
        db, config, c = candidate_db(tmp_path)
        try:
            update = update_for(c, user, chat)
            send = AsyncMock()
            await handle_choice(update, config, db, send)
            assert not db.rows("SELECT confirmed FROM candidates")[0]["confirmed"]
            send.assert_not_awaited()
        finally:
            db.conn.close()

    asyncio.run(run())


def test_select_only_clicked_offer_and_repeat_safe(tmp_path):
    async def run():
        db, config, c = candidate_db(tmp_path)
        try:
            other = db.candidate(
                c["product"], "https://www.pichau.com.br/other", "Pichau"
            )
            db.record(other, Reading("Versao sem wifi", "", "", "", None))
            send = AsyncMock()
            scheduled = []
            update = update_for(c)
            await handle_choice(update, config, db, send, scheduled.append)
            assert db.rows("SELECT confirmed FROM candidates WHERE id=?", (c["id"],))[
                0
            ]["confirmed"]
            assert not db.rows(
                "SELECT confirmed FROM candidates WHERE id=?", (other["id"],)
            )[0]["confirmed"]
            await handle_choice(update, config, db, send, scheduled.append)
            assert scheduled == [c["product"]]
            assert send.await_count == 1
        finally:
            db.conn.close()

    asyncio.run(run())


def test_stale_card_and_removed_offer(tmp_path):
    async def run():
        db, config, c = candidate_db(tmp_path)
        try:
            update = update_for(c)
            db.run(
                "UPDATE candidates SET title=? WHERE id=?",
                ("Modelo diferente", c["id"]),
            )
            send = AsyncMock()
            await handle_choice(update, config, db, send)
            assert not db.rows("SELECT confirmed FROM candidates")[0]["confirmed"]
            db.run("DELETE FROM products WHERE id=?", (c["product"],))
            await handle_choice(update, config, db, send)
            send.assert_not_awaited()
        finally:
            db.conn.close()

    asyncio.run(run())


def test_old_database_migration_preserves_products(tmp_path):
    path = str(tmp_path / "old.sqlite")
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO products(query,minimum,percent,next_due) VALUES ('produto',50,'5',123456)"
    )
    conn.commit()
    conn.close()
    db = DB(path)
    assert db.rows("SELECT next_due FROM products")[0]["next_due"] == 123456
    assert "image" in {r["name"] for r in db.rows("PRAGMA table_info(candidates)")}
    db.conn.close()
    db = DB(path)  # Migracao idempotente.
    assert len(db.rows("SELECT * FROM products")) == 1
    db.conn.close()


def test_cards_persist_and_resend_on_demand(tmp_path):
    async def run():
        db, config, c = candidate_db(tmp_path)
        try:
            card = AsyncMock()
            monitor = Monitor(db, config, None, None, AsyncMock(), card)
            assert await monitor.options(c["product"], only_new=True) == 1
            assert await monitor.options(c["product"], only_new=True) == 0
            assert await monitor.options(c["product"]) == 1
            assert card.await_count == 2
            assert card.await_args.args[0]["image"] == c["image"]
        finally:
            db.conn.close()

    asyncio.run(run())
