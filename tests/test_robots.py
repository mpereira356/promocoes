from monitor.robots import RobotsPolicy


def test_wildcard_query_disallow():
    p = RobotsPolicy("User-agent: *\nAllow: /\nDisallow: /*?*")
    assert not p.can_fetch("PriceMonitor", "https://example.org/search?q=b550")
    assert p.can_fetch("PriceMonitor", "https://example.org/produto/1")


def test_longest_rule_allow_tie_and_end_anchor():
    p = RobotsPolicy("User-agent: *\nDisallow: /\nAllow: /produto/\nDisallow: /busca$")
    assert p.can_fetch("PriceMonitor", "https://example.org/produto/1")
    assert not p.can_fetch("PriceMonitor", "https://example.org/busca")
    p = RobotsPolicy("User-agent: *\nDisallow: /a\nAllow: /a")
    assert p.can_fetch("PriceMonitor", "https://example.org/a")


def test_specific_agent_merge_and_delay():
    p = RobotsPolicy(
        "User-agent: *\nDisallow: /\nUser-agent: PriceMonitor\nAllow: /produto\nCrawl-delay: 10\nUser-agent: PriceMonitor\nDisallow: /secret"
    )
    assert p.can_fetch("PriceMonitor", "https://example.org/produto")
    assert not p.can_fetch("PriceMonitor", "https://example.org/secret")
    assert p.crawl_delay("PriceMonitor") == 10
    assert not p.can_fetch("Other", "https://example.org/produto")


def test_empty_disallow_and_comments():
    p = RobotsPolicy("User-agent: *\nDisallow: # empty\nAllow: /")
    assert p.can_fetch("PriceMonitor", "https://example.org/anything")
