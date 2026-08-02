"""クラブ・年度・記事構造に依存しない汎用ヘルパー群。"""
from __future__ import annotations

import random
import re
import time
import unicodedata
from datetime import date
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from loguru import logger

# WordPress の日付ベースパーマリンク /YYYY/MM/DD/slug/ のみを記事URLとみなす。
# サイト固有のCSSクラスやテーマ構造に依存しないため、デザイン変更に強い。
_ARTICLE_URL_RE = re.compile(r"/(\d{4})/\d{2}/\d{2}/[^/?#]+/?$")


def to_halfwidth(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    normalized = to_halfwidth(text)
    return re.sub(r"\s+", " ", normalized).strip()


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_number(text: Optional[str]) -> Optional[float]:
    """"158.2cm" や "４６０ｋｇ" のような文字列から数値だけを取り出す。"""
    if not text:
        return None
    normalized = to_halfwidth(text)
    match = _NUMBER_RE.search(normalized)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


_SEX_ALIASES = {
    "牡": "牡",
    "オス": "牡",
    "牝": "牝",
    "メス": "牝",
    "セン": "セ",
    "せん": "セ",
    "騙": "セ",
    "セ": "セ",
}


def normalize_sex(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    normalized = clean_text(text)
    for alias, canonical in _SEX_ALIASES.items():
        if alias in normalized:
            return canonical
    return normalized or None


_DATE_PATTERNS = [
    re.compile(r"(?P<y>\d{4})[年./\-](?P<m>\d{1,2})[月./\-](?P<d>\d{1,2})"),
    re.compile(r"(?P<y>\d{2})[./\-](?P<m>\d{1,2})[./\-](?P<d>\d{1,2})"),
]


def parse_date(text: Optional[str]) -> Optional[date]:
    if not text:
        return None
    normalized = to_halfwidth(text)
    for pattern in _DATE_PATTERNS:
        match = pattern.search(normalized)
        if not match:
            continue
        year = int(match.group("y"))
        if year < 100:
            year += 2000
        try:
            return date(year, int(match.group("m")), int(match.group("d")))
        except ValueError:
            continue
    return None


def is_article_url(url: str) -> bool:
    return bool(_ARTICLE_URL_RE.search(urlparse(url).path))


def extract_year_from_url(url: str) -> Optional[int]:
    match = _ARTICLE_URL_RE.search(urlparse(url).path)
    return int(match.group(1)) if match else None


def polite_sleep(interval: float) -> None:
    """アクセス間隔を確保する。多少のジッターを加えて負荷を分散する。"""
    if interval <= 0:
        return
    time.sleep(interval + random.uniform(0, interval * 0.2))


class RobotsChecker:
    """robots.txt を尊重するための薄いラッパー。

    robots.txt が取得できない場合は警告を出したうえで許可扱いとする
    (urllib.robotparser がルール未読込時に can_fetch=True を返す挙動に合わせる)。
    """

    def __init__(self, base_url: str, user_agent: str, session: requests.Session):
        self._user_agent = user_agent
        self._parser = RobotFileParser()
        self._parser.set_url(urljoin(base_url + "/", "robots.txt"))
        self._loaded = False
        self._load(session)

    def _load(self, session: requests.Session) -> None:
        try:
            response = session.get(self._parser.url, timeout=10)
            if response.status_code == 200:
                self._parser.parse(response.text.splitlines())
                self._loaded = True
                logger.debug(f"robots.txt loaded from {self._parser.url}")
            else:
                logger.warning(
                    f"robots.txt returned status {response.status_code}; "
                    "proceeding without robots rules"
                )
        except requests.RequestException as exc:
            logger.warning(f"Could not fetch robots.txt ({exc}); proceeding without robots rules")

    def can_fetch(self, url: str) -> bool:
        if not self._loaded:
            return True
        return self._parser.can_fetch(self._user_agent, url)
