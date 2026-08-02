"""測尺記事のHTML解析。

サイトのマークアップ変更に耐えられるよう、CSSクラス名などの見た目には依存せず
table / thead / tbody / tr / td の構造とヘッダーセルの日本語テキストだけを
手がかりにデータ列を推定する。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger

from models import HorseMeasurement
from utils import clean_text, extract_number, extract_year_from_url, normalize_sex, parse_date
import config

# 見出しテキストに含まれる部分文字列でデータ列を判定する。
# 記事ごとに表記ゆれがあるため、想定される別名を列挙している。
COLUMN_ALIASES: List[Tuple[str, Tuple[str, ...]]] = [
    ("recruit_no", ("募集No", "募集番号", "No.", "No", "№", "番号")),
    ("name", ("馬名", "名前")),
    ("sire", ("父馬", "父")),
    ("dam", ("母馬", "母")),
    ("sex", ("性別", "性")),
    ("birth_date", ("生年月日", "生年", "誕生日")),
    ("measure_date", ("測尺日", "測定日", "計測日")),
    ("height_cm", ("体高",)),
    ("girth_cm", ("胸囲",)),
    ("cannon_cm", ("管囲",)),
    ("weight_kg", ("馬体重", "体重")),
]


def _match_column(header_text: str) -> Optional[str]:
    for canonical, aliases in COLUMN_ALIASES:
        if any(alias in header_text for alias in aliases):
            return canonical
    return None


def _map_columns(header_cells: List[Tag]) -> Dict[int, str]:
    mapping: Dict[int, str] = {}
    seen: Set[str] = set()
    for idx, cell in enumerate(header_cells):
        field = _match_column(clean_text(cell.get_text()))
        if field and field not in seen:
            mapping[idx] = field
            seen.add(field)
    return mapping


def _body_rows(table: Tag, header_row: Tag) -> List[Tag]:
    tbody = table.find("tbody")
    if tbody:
        return tbody.find_all("tr")
    return [tr for tr in table.find_all("tr") if tr is not header_row]


def _parse_table(table: Tag) -> List[Dict[str, str]]:
    thead = table.find("thead")
    if thead and thead.find("tr"):
        header_row = thead.find("tr")
    else:
        all_rows = table.find_all("tr")
        if not all_rows:
            return []
        header_row = all_rows[0]

    header_cells = header_row.find_all(["th", "td"])
    column_map = _map_columns(header_cells)
    # 意味のある列が3つ未満なら測尺表ではないと判断してスキップする。
    if len(column_map) < 3:
        return []

    records: List[Dict[str, str]] = []
    for row in _body_rows(table, header_row):
        cells = row.find_all(["td", "th"])
        if not cells or all(cell.get_text(strip=True) == "" for cell in cells):
            continue
        raw: Dict[str, str] = {}
        for idx, field in column_map.items():
            if idx < len(cells):
                value = clean_text(cells[idx].get_text())
                if value:
                    raw[field] = value
        if raw:
            records.append(raw)
    return records


def _build_measurement(
    raw: Dict[str, str], club: str, year: int, url: str
) -> Optional[HorseMeasurement]:
    name = raw.get("name")
    numeric_present = any(
        raw.get(field) for field in ("height_cm", "girth_cm", "cannon_cm", "weight_kg")
    )
    if not name and not numeric_present:
        return None
    return HorseMeasurement(
        club=club,
        year=year,
        recruit_no=raw.get("recruit_no"),
        name=name,
        sire=raw.get("sire"),
        dam=raw.get("dam"),
        sex=normalize_sex(raw.get("sex")),
        birth_date=parse_date(raw.get("birth_date")),
        measure_date=parse_date(raw.get("measure_date")),
        height_cm=extract_number(raw.get("height_cm")),
        girth_cm=extract_number(raw.get("girth_cm")),
        cannon_cm=extract_number(raw.get("cannon_cm")),
        weight_kg=extract_number(raw.get("weight_kg")),
        article_url=url,
    )


def _is_relevant_article(page_text: str, club_keywords: List[str]) -> bool:
    return config.MEASUREMENT_KEYWORD in page_text and any(
        kw in page_text for kw in club_keywords
    )


def _year_is_plausible(page_text: str, url: str, year: int) -> bool:
    url_year = extract_year_from_url(url)
    if url_year is not None:
        return url_year == year
    return str(year) in page_text or str(year)[2:] in page_text


def parse(
    html: str,
    url: str,
    club: str,
    year: int,
    club_keywords: Optional[List[str]] = None,
) -> List[HorseMeasurement]:
    """記事HTMLを解析し、当該クラブ・年度に関連する測尺データだけを抽出する。"""
    if club_keywords is None:
        club_keywords = config.CLUBS[club].search_keywords if club in config.CLUBS else []

    soup = BeautifulSoup(html, "lxml")
    page_text = clean_text(soup.get_text())

    if not _is_relevant_article(page_text, club_keywords):
        logger.debug(f"Not relevant (missing club/measurement keywords): {url}")
        return []
    if not _year_is_plausible(page_text, url, year):
        logger.debug(f"Not relevant (year {year} not plausible): {url}")
        return []

    tables = soup.find_all("table")
    if not tables:
        logger.debug(f"No <table> found: {url}")
        return []

    measurements: List[HorseMeasurement] = []
    seen_keys: Set[Tuple[Optional[str], Optional[str]]] = set()
    counter = 0
    for table in tables:
        for raw in _parse_table(table):
            counter += 1
            measurement = _build_measurement(raw, club, year, url)
            if measurement is None:
                continue
            if not measurement.recruit_no:
                measurement.recruit_no = str(counter)
            key = (measurement.name, measurement.recruit_no)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            measurements.append(measurement)

    if not measurements:
        logger.warning(f"Relevant article but no rows extracted (structure may differ): {url}")
    return measurements
