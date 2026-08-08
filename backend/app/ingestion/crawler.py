"""Controlled Shopify Help Center crawler with robots and SSRF safeguards."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import AppError


@dataclass(frozen=True)
class CrawlPolicy:
    """Explicit limits for a single controlled crawl."""

    allowed_prefixes: tuple[str, ...]
    user_agent: str
    timeout_seconds: float = 20.0
    delay_seconds: float = 1.0
    max_pages: int = 30
    max_depth: int = 2
    max_retries: int = 3


@dataclass(frozen=True)
class CrawledPage:
    url: str
    title: str
    content: str
    crawled_at: datetime
    published_at: datetime | None = None


class SafeWebCrawler:
    """Crawl only approved public Shopify documentation pages."""

    def __init__(self, policy: CrawlPolicy, client: httpx.AsyncClient | None = None) -> None:
        self.policy = policy
        self._external_client = client
        self._robots: RobotFileParser | None = None

    def is_allowed_url(self, url: str) -> bool:
        normalized, _ = urldefrag(url)
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or parsed.hostname != "help.shopify.com":
            return False
        if parsed.username or parsed.password or parsed.port not in (None, 443):
            return False
        return any(normalized.startswith(prefix) for prefix in self.policy.allowed_prefixes)

    async def _assert_public_host(self, hostname: str) -> None:
        addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, 443, type=socket.SOCK_STREAM)
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise AppError("知识源解析到非公网地址，已阻止请求", code="ssrf_blocked", status_code=400)

    async def _load_robots(self, client: httpx.AsyncClient) -> RobotFileParser:
        if self._robots is not None:
            return self._robots
        response = await client.get("https://help.shopify.com/robots.txt")
        response.raise_for_status()
        parser = RobotFileParser("https://help.shopify.com/robots.txt")
        parser.parse(response.text.splitlines())
        self._robots = parser
        return parser

    async def _fetch(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        if not self.is_allowed_url(url):
            raise AppError("URL 不在 Shopify 知识源白名单中", code="url_not_allowed", status_code=400)
        await self._assert_public_host("help.shopify.com")
        robots = await self._load_robots(client)
        if not robots.can_fetch(self.policy.user_agent, url):
            raise AppError("robots.txt 不允许访问该页面", code="robots_denied", status_code=400)
        last_error: Exception | None = None
        for attempt in range(self.policy.max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                if not self.is_allowed_url(str(response.url)):
                    raise AppError("重定向目标不在白名单中", code="redirect_not_allowed", status_code=400)
                return response
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt + 1 < self.policy.max_retries:
                    await asyncio.sleep(min(2**attempt, 4))
        raise AppError(f"网页采集失败: {last_error}", code="crawl_failed", status_code=502)

    @staticmethod
    def _extract_page(url: str, html: str) -> tuple[CrawledPage, list[str]]:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "form"]):
            tag.decompose()
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else url
        root = soup.find("main") or soup.find("article") or soup.body or soup
        lines: list[str] = []
        for element in root.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            text = " ".join(element.get_text(" ", strip=True).split())
            if not text:
                continue
            if element.name and element.name.startswith("h"):
                level = min(int(element.name[1]), 4)
                lines.append(f"{'#' * level} {text}")
            elif element.name == "li":
                lines.append(f"- {text}")
            else:
                lines.append(text)
        content = "\n\n".join(dict.fromkeys(lines))
        links = [urljoin(url, anchor.get("href")) for anchor in root.find_all("a", href=True)]
        modified = soup.find("meta", attrs={"property": "article:modified_time"})
        published_at = None
        if modified and modified.get("content"):
            try:
                published_at = datetime.fromisoformat(str(modified["content"]).replace("Z", "+00:00"))
            except ValueError:
                published_at = None
        return (
            CrawledPage(
                url=url,
                title=title,
                content=content,
                crawled_at=datetime.now(UTC),
                published_at=published_at,
            ),
            links,
        )

    async def crawl(self, start_urls: list[str]) -> list[CrawledPage]:
        """Breadth-first crawl within whitelist, page count, and depth limits."""
        queue: deque[tuple[str, int]] = deque((urldefrag(url)[0], 0) for url in start_urls)
        visited: set[str] = set()
        pages: list[CrawledPage] = []
        client = self._external_client or httpx.AsyncClient(
            headers={"User-Agent": self.policy.user_agent},
            timeout=httpx.Timeout(self.policy.timeout_seconds),
            follow_redirects=True,
        )
        should_close = self._external_client is None
        try:
            while queue and len(pages) < self.policy.max_pages:
                url, depth = queue.popleft()
                if url in visited or depth > self.policy.max_depth or not self.is_allowed_url(url):
                    continue
                visited.add(url)
                response = await self._fetch(client, url)
                page, links = self._extract_page(str(response.url), response.text)
                if page.content:
                    pages.append(page)
                if depth < self.policy.max_depth:
                    for link in links:
                        normalized = urldefrag(link)[0]
                        if normalized not in visited and self.is_allowed_url(normalized):
                            queue.append((normalized, depth + 1))
                if queue and len(pages) < self.policy.max_pages:
                    await asyncio.sleep(max(self.policy.delay_seconds, 1.0))
        finally:
            if should_close:
                await client.aclose()
        return pages

