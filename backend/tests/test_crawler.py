"""Crawler whitelist, redirect, and HTML extraction tests."""

from app.ingestion.crawler import CrawlPolicy, SafeWebCrawler


def test_crawler_only_accepts_shopify_whitelist() -> None:
    crawler = SafeWebCrawler(
        CrawlPolicy(
            allowed_prefixes=("https://help.shopify.com/en/manual/international",),
            user_agent="TraceCommerceTest/1.0",
        )
    )
    assert crawler.is_allowed_url("https://help.shopify.com/en/manual/international")
    assert not crawler.is_allowed_url("https://help.shopify.com/en/manual/taxes")
    assert not crawler.is_allowed_url("http://help.shopify.com/en/manual/international")
    assert not crawler.is_allowed_url("https://example.com/en/manual/international")


def test_html_extraction_preserves_headings_and_source_text() -> None:
    html = """
    <html><head><title>Markets</title></head><body>
    <nav>Ignore navigation</nav>
    <main><h1>Markets</h1><h2>Overview</h2>
    <p>Markets help merchants customize international experiences.</p></main>
    </body></html>
    """
    page, _ = SafeWebCrawler._extract_page(
        "https://help.shopify.com/en/manual/international",
        html,
    )
    assert page.title == "Markets"
    assert "## Overview" in page.content
    assert "Ignore navigation" not in page.content

