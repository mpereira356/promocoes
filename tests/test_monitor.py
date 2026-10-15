import json
import asyncio
import functools
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
import pytest
from monitor.models import Reading, money, qualifies, normalize
from monitor.db import DB
from monitor.adapters.base import StructuredAdapter, ReadError


def run_async(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return wrapped


@pytest.fixture
def config():
    return SimpleNamespace(minimum=0, percent=Decimal("0"), target=None, interval=18000)


@pytest.fixture
def setup(tmp_path, config):
    db = DB(str(tmp_path / "test.sqlite"))
    pid = db.add("ROG STRIX B550-F GAMING WIFI II", config)
    c = db.candidate(pid, "https://www.pichau.com.br/produto", "Pichau")
    reading = Reading(
        "ROG STRIX B550-F GAMING WIFI II",
        "Loja",
        "NewCondition",
        "Pix",
        100000,
        "in_stock",
    )
    db.record(c, reading)
    db.run("UPDATE candidates SET confirmed=1 WHERE id=?", (c["id"],))
    c = db.rows("SELECT * FROM candidates WHERE id=?", (c["id"],))[0]
    yield db, c, reading
    db.conn.close()


def count(db):
    return len(db.rows("SELECT * FROM alerts"))


def test_initial_new_drop_duplicate_and_return(setup):
    db, c, r = setup
    assert "Nova" in db.record(c, r)
    assert count(db) == 0
    low = replace(r, price=90000)
    db.record(c, low)
    db.record(c, low)
    assert count(db) == 1
    assert "Anterior: R$ 1000.00" in db.rows("SELECT message FROM alerts")[0]["message"]
    db.record(c, r)
    db.record(c, low)
    assert count(db) == 3  # Queda, aumento e nova queda: qualquer alteracao e avisada.
    assert db.rows("SELECT lowest FROM series")[0]["lowest"] == 90000


@pytest.mark.parametrize(
    "change",
    [
        {"payment": "Cartao 12x"},
        {"seller": "Marketplace"},
        {"condition": "UsedCondition"},
    ],
)
def test_variants_never_compare(setup, change):
    db, c, r = setup
    db.record(c, r)
    assert "Nova" in db.record(c, replace(r, price=50000, **change))
    assert count(db) == 0
    assert len(db.rows("SELECT * FROM series")) == 2


@pytest.mark.parametrize(
    "price", [None, 0, -1, "abc", "NaN", "Infinity", "1.000,50", "0"]
)
def test_invalid_prices(price):
    assert money(price) is None


def test_failures_preserve_last(setup):
    db, c, r = setup
    db.record(c, r)
    db.failure(c["id"], "network_or_rate_limit")
    db.record(c, replace(r, price=None))
    assert db.rows("SELECT last FROM series")[0]["last"] == 100000
    assert len(db.rows("SELECT * FROM prices")) == 1
    assert count(db) == 0
    db.record(c, replace(r, price=90000))
    assert count(db) == 1


@pytest.mark.parametrize("stock", ["unknown", "out_of_stock"])
def test_no_stock_no_alert(setup, stock):
    db, c, r = setup
    db.record(c, r)
    db.record(c, replace(r, price=80000, stock=stock))
    assert count(db) == 0


def test_model_change_reconfirmation(setup):
    db, c, r = setup
    db.record(c, r)
    db.record(c, replace(r, title="ROG STRIX B550-F GAMING", price=50000))
    assert not db.rows("SELECT confirmed FROM candidates")[0]["confirmed"]
    assert count(db) == 0
    assert db.rows("SELECT last FROM series")[0]["last"] == 100000
    assert normalize(r.title) != normalize("ROG STRIX B550-F GAMING WIFI")


def test_pending_no_base(tmp_path, config):
    db = DB(str(tmp_path / "db.sqlite"))
    c = db.candidate(
        db.add("placa", config), "https://www.kabum.com.br/produto/1", "KaBuM"
    )
    db.record(c, Reading("Outra placa", "Loja", "NewCondition", "Pix", 100, "in_stock"))
    assert not db.rows("SELECT * FROM series")


def test_thresholds():
    assert qualifies(100000, 90000, 10000, 10, 90000)
    assert not qualifies(100000, 90000, 10001, 10, 90000)
    assert not qualifies(100000, 90000, 0, 11, None)
    assert not qualifies(100000, 90000, 0, 0, 80000)
    assert not qualifies(None, 90000)
    assert not qualifies(90000, 90000)


def html(offer=None):
    p = {
        "@type": "Product",
        "name": "Produto simulado",
        "offers": offer
        or {
            "@type": "Offer",
            "price": "999.99",
            "priceCurrency": "BRL",
            "availability": "https://schema.org/InStock",
            "seller": {"name": "Loja simulada"},
            "itemCondition": "https://schema.org/NewCondition",
            "acceptedPaymentMethod": "Pix",
        },
    }
    return '<script type="application/ld+json">' + json.dumps(p) + "</script>"


def test_structured_fixture():
    r = StructuredAdapter().parse(html(), "https://example.org")[0]
    assert r.price == 99999 and r.stock == "in_stock" and r.comparable


def test_no_inferred_payment_stock_seller():
    r = StructuredAdapter().parse(
        html({"@type": "Offer", "price": "800", "priceCurrency": "BRL"}), ""
    )[0]
    assert r.price == 80000 and r.stock == "unknown" and not r.comparable


def test_corrupted_html_and_aggregate():
    with pytest.raises(ReadError):
        StructuredAdapter().parse("<h1>Access denied</h1>", "")
    with pytest.raises(ReadError):
        StructuredAdapter().parse(
            '<script type="application/ld+json">{broken</script>', ""
        )
    r = StructuredAdapter().parse(
        html({"@type": "AggregateOffer", "lowPrice": "1"}), ""
    )[0]
    assert r.price is None


def test_restart_and_cascade(tmp_path, config):
    path = str(tmp_path / "db.sqlite")
    db = DB(path)
    pid = db.add("produto", config)
    db.run("UPDATE products SET next_due=123456 WHERE id=?", (pid,))
    db.conn.close()
    db = DB(path)
    assert db.rows("SELECT next_due FROM products")[0]["next_due"] == 123456
    db.candidate(pid, "https://www.pichau.com.br/produto", "Pichau")
    db.run("DELETE FROM products WHERE id=?", (pid,))
    assert not db.rows("SELECT * FROM candidates")
    db.conn.close()


@run_async
async def test_concurrent_check_and_outbox(setup, config):
    import asyncio
    from monitor.service import Monitor

    db, c, r = setup
    db.record(c, r)
    db.record(c, replace(r, price=90000))
    sent = []

    async def send(msg):
        await asyncio.sleep(0.01)
        sent.append(msg)

    monitor = Monitor(db, config, None, None, send)
    await asyncio.gather(monitor.deliver(), monitor.deliver())
    assert len(sent) == 1
    assert db.rows("SELECT sent_at FROM alerts")[0]["sent_at"] is not None


@run_async
async def test_delivery_error_retries(setup, config):
    from monitor.service import Monitor

    db, c, r = setup
    db.record(c, r)
    db.record(c, replace(r, price=90000))

    async def fail(msg):
        raise OSError("offline")

    monitor = Monitor(db, config, None, None, fail)
    await monitor.deliver()
    assert db.rows("SELECT sent_at FROM alerts")[0]["sent_at"] is None


def test_url_allowlist():
    from monitor.network import Fetcher

    f = Fetcher(SimpleNamespace(domains=("kabum.com.br",), delay=1))
    for url in [
        "http://kabum.com.br/a",
        "https://evil.kabum.com.br/a",
        "https://kabum.com.br.evil.org/a",
        "https://127.0.0.1/a",
        "https://user:pass@kabum.com.br/a",
    ]:
        with pytest.raises(ReadError):
            f.canonical(url)
    assert (
        f.canonical("https://www.kabum.com.br/produto/1#x")[0]
        == "https://www.kabum.com.br/produto/1"
    )


@run_async
async def test_duplicate_product_check(setup, config):
    from monitor.service import Monitor

    db, c, r = setup
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    class Fetch:
        def canonical(self, url):
            return url, "pichau.com.br"

    class Search:
        async def links(self, q):
            return []

    async def send(msg):
        pass

    m = Monitor(db, config, Fetch(), Search(), send)

    async def read(url):
        calls.append(url)
        entered.set()
        await release.wait()
        return [r]

    m.read = read
    first = asyncio.create_task(m.check(c["product"]))
    await entered.wait()
    assert await m.check(c["product"]) == "Verificacao ja em andamento."
    release.set()
    await first
    assert len(calls) == 1
    assert db.rows("SELECT next_due FROM products")[0]["next_due"] > 0


@run_async
async def test_shared_url_inflight(config):
    from monitor.service import Monitor

    class Fetch:
        def canonical(self, url):
            return url, "pichau.com.br"

    m = Monitor(None, config, Fetch(), None, None)
    calls = []

    async def read(url):
        calls.append(url)
        await asyncio.sleep(0.01)
        return ["same"]

    m._read = read
    assert await asyncio.gather(
        m.read("https://www.pichau.com.br/a"), m.read("https://www.pichau.com.br/a")
    ) == [["same"], ["same"]]
    assert len(calls) == 1


def test_instance_lock(tmp_path):
    from monitor.instance import InstanceLock

    path = str(tmp_path / "db.sqlite")
    lock = InstanceLock(path)
    try:
        with pytest.raises(RuntimeError):
            InstanceLock(path)
    finally:
        lock.close()
    second = InstanceLock(path)
    second.close()


def test_reconfirmed_model_separate_series(setup):
    db, c, r = setup
    db.record(c, r)
    changed = replace(r, title="ROG STRIX B550-F GAMING WIFI", price=50000)
    db.record(c, changed)
    db.run("UPDATE candidates SET confirmed=1 WHERE id=?", (c["id"],))
    c = db.rows("SELECT * FROM candidates WHERE id=?", (c["id"],))[0]
    assert "Nova" in db.record(c, changed)
    assert count(db) == 0
    assert len(db.rows("SELECT * FROM series")) == 2


def test_multiple_payment_ambiguous():
    offer = {
        "@type": "Offer",
        "price": "1000",
        "priceCurrency": "BRL",
        "acceptedPaymentMethod": "Pix, Cartao",
    }
    r = StructuredAdapter().parse(html(offer), "")[0]
    assert r.payment == "" and not r.comparable


@run_async
async def test_http_removed_captcha_and_timeout():
    import httpx
    from monitor.network import Fetcher

    c = SimpleNamespace(domains=("pichau.com.br",), delay=1)
    f = Fetcher(c)
    await f.client.aclose()

    async def public(url):
        pass

    f.public = public

    def respond(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(404)

    f.client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    try:
        with pytest.raises(ReadError, match="page_removed"):
            await f.html("https://www.pichau.com.br/removed")
    finally:
        await f.close()
    f = Fetcher(c)
    await f.client.aclose()
    f.public = public

    async def allowed(url):
        pass

    f.allowed_by_robots = allowed
    f.client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, text='<div class="g-recaptcha">')
        )
    )
    try:
        with pytest.raises(ReadError, match="captcha_no_bypass"):
            await f.html("https://www.pichau.com.br/blocked")
    finally:
        await f.close()


@run_async
async def test_rate_limit_deferred():
    import httpx
    from monitor.network import Fetcher

    f = Fetcher(SimpleNamespace(domains=("pichau.com.br",), delay=1))
    await f.client.aclose()

    async def public(url):
        pass

    f.public = public
    f.client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(429, headers={"Retry-After": "3600"})
        )
    )
    try:
        with pytest.raises(ReadError, match="rate_limit_deferred"):
            await f.request("https://www.pichau.com.br/rate")
    finally:
        await f.close()
