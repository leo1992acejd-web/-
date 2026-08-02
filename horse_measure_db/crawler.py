"""sports-keiba.com のクロール処理。

記事URLを固定で持たず、以下の順で関連記事を探索する。
    1. WordPress REST 検索API (/wp-json/wp/v2/search)
    2. サイト内検索のHTML結果ページ (/?s=...)
    3. サイトマップ (sitemap_index.xml 等) ※ 上記で0件だった場合の最終手段

いずれの手法でも、収集したURLは日付ベースパーマリンク
(/YYYY/MM/DD/slug/) のパターンに一致するものだけを「記事」として採用する。
"""
from __future__ import annotations

import json
from typing import Iterable, List, Set
from urllib.parse import urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

import config
from cache import HttpCache
from utils import RobotsChecker, extract_year_from_url, is_article_url, polite_sleep


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code >= 500
    return isinstance(exc, requests.RequestException)


class ArticleCrawler:
    def __init__(
        self,
        base_url: str = config.BASE_URL,
        cache: HttpCache | None = None,
        session: requests.Session | None = None,
        interval: float = config.REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache = cache or HttpCache(config.CACHE_DIR, config.CACHE_TTL_SECONDS)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        self.interval = interval
        self.robots = RobotsChecker(self.base_url, config.USER_AGENT, self.session)

    @retry(
        reraise=True,
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(_is_retryable),
    )
    def _get(self, url: str) -> requests.Response:
        polite_sleep(self.interval)
        response = self.session.get(url, timeout=config.REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    def fetch(self, url: str, force_refresh: bool = False) -> str | None:
        if not self.robots.can_fetch(url):
            logger.warning(f"robots.txt disallows fetching {url}; skipping")
            return None
        if not force_refresh:
            cached = self.cache.get(url)
            if cached is not None:
                logger.debug(f"cache hit: {url}")
                return cached
        try:
            response = self._get(url)
        except requests.RequestException as exc:
            logger.error(f"Failed to fetch {url}: {exc}")
            return None
        response.encoding = response.encoding or "utf-8"
        html = response.text
        self.cache.set(url, html)
        return html

    def _extract_article_links(self, html: str) -> Set[str]:
        soup = BeautifulSoup(html, "lxml")
        base_netloc = urlparse(self.base_url).netloc
        links: Set[str] = set()
        for a in soup.find_all("a", href=True):
            href = urljoin(self.base_url + "/", a["href"])
            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc != base_netloc:
                continue
            if is_article_url(href):
                links.add(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
        return links

    def _search_wp_api(self, query: str, force_refresh: bool) -> Set[str]:
        links: Set[str] = set()
        url = f"{self.base_url}/wp-json/wp/v2/search?" + urlencode(
            {"search": query, "per_page": 50, "subtype": "post"}
        )
        text = self.fetch(url, force_refresh=force_refresh)
        if not text:
            return links
        try:
            payload = json.loads(text)
        except ValueError as exc:
            logger.debug(f"WP search API not JSON for query={query!r}: {exc}")
            return links
        for item in payload if isinstance(payload, list) else []:
            href = item.get("url") if isinstance(item, dict) else None
            if href and is_article_url(href):
                links.add(href)
        return links

    def _search_html(self, query: str, force_refresh: bool) -> Set[str]:
        links: Set[str] = set()
        for page in range(1, config.SEARCH_MAX_PAGES + 1):
            params = {"s": query}
            if page > 1:
                params["paged"] = page
            search_url = f"{self.base_url}/?" + urlencode(params)
            html = self.fetch(search_url, force_refresh=force_refresh)
            if not html:
                break
            page_links = self._extract_article_links(html)
            new_links = page_links - links
            links |= page_links
            if not new_links:
                break
        return links

    def _search_sitemap(self, force_refresh: bool) -> Set[str]:
        links: Set[str] = set()
        for candidate in ("sitemap_index.xml", "sitemap.xml"):
            index_xml = self.fetch(f"{self.base_url}/{candidate}", force_refresh=force_refresh)
            if not index_xml:
                continue
            soup = BeautifulSoup(index_xml, "xml")
            locs = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
            direct_articles = {loc for loc in locs if is_article_url(loc)}
            links |= direct_articles

            sub_sitemaps = [loc for loc in locs if loc.endswith(".xml") and "post" in loc]
            for sub_url in sub_sitemaps:
                sub_xml = self.fetch(sub_url, force_refresh=force_refresh)
                if not sub_xml:
                    continue
                sub_soup = BeautifulSoup(sub_xml, "xml")
                for loc in sub_soup.find_all("loc"):
                    loc_text = loc.get_text(strip=True)
                    if is_article_url(loc_text):
                        links.add(loc_text)
            if links:
                break
        return links

    def discover(self, keywords: Iterable[str], year: int, force_refresh: bool = False) -> Set[str]:
        found: Set[str] = set()
        for keyword in keywords:
            found |= self._search_wp_api(keyword, force_refresh)
            found |= self._search_html(keyword, force_refresh)

        if not found:
            logger.info(f"No search hits for {list(keywords)}; falling back to sitemap discovery")
            found |= self._search_sitemap(force_refresh)

        year_matches = {url for url in found if extract_year_from_url(url) == year}
        if year_matches:
            return year_matches
        return found

    def discover_for_club_year(
        self, club: "config.ClubConfig", year: int, force_refresh: bool = False
    ) -> List[str]:
        queries: List[str] = []
        for keyword in club.search_keywords:
            queries.append(f"{keyword} {config.MEASUREMENT_KEYWORD}")
            queries.append(f"{keyword} {config.MEASUREMENT_KEYWORD} {year}")
        urls = self.discover(queries, year, force_refresh=force_refresh)
        logger.info(f"Discovered {len(urls)} candidate article(s) for {club.display_name} {year}")
        return sorted(urls)
