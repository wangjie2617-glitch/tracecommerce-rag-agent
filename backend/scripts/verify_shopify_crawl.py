"""Verify live Shopify access and print trace metadata without storing page content."""

from __future__ import annotations

import asyncio
import hashlib
import json

from app.config import get_settings
from app.ingestion.crawler import CrawlPolicy, SafeWebCrawler


async def main() -> None:
    settings = get_settings()
    policy = CrawlPolicy(
        allowed_prefixes=tuple(settings.shopify_allowed_prefixes),
        user_agent=settings.crawler_user_agent,
        timeout_seconds=settings.crawler_timeout_seconds,
        delay_seconds=max(settings.crawler_delay_seconds, 1.0),
        max_pages=min(settings.crawler_max_pages, 5),
        max_depth=0,
    )
    pages = await SafeWebCrawler(policy).crawl(settings.shopify_allowed_prefixes[:5])
    records = [
        {
            "url": page.url,
            "title": page.title,
            "crawled_at": page.crawled_at.isoformat(),
            "content_chars": len(page.content),
            "sha256": hashlib.sha256(page.content.encode("utf-8")).hexdigest(),
        }
        for page in pages
    ]
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

