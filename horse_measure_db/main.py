"""horse_measure_db CLIエントリポイント。

使用例:
    python main.py
    python main.py --club silk
    python main.py --club silk carrot
    python main.py --years 2024 2025
    python main.py --output csv
    python main.py --force-refresh
"""
from __future__ import annotations

import argparse
from typing import List

from loguru import logger
from tqdm import tqdm

import config
import excel_writer
from cache import HttpCache
from crawler import ArticleCrawler
from database import Database
from logger import setup_logger
from models import HorseMeasurement
from parser import parse as parse_article


def build_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description="募集馬測尺DB スクレイパー")
    arg_parser.add_argument(
        "--club",
        choices=sorted(config.CLUBS.keys()),
        nargs="+",
        default=None,
        help="対象クラブ (未指定なら全クラブ)",
    )
    arg_parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=None,
        help="対象募集年度 (未指定なら config.DEFAULT_YEARS)",
    )
    arg_parser.add_argument(
        "--output",
        choices=["excel", "csv", "sqlite"],
        default="excel",
        help="出力形式 (デフォルト: excel)",
    )
    arg_parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="キャッシュを無視してすべて再取得する",
    )
    return arg_parser


def run(clubs: List[str], years: List[int], output: str, force_refresh: bool) -> None:
    setup_logger()
    logger.info(f"Start: clubs={clubs} years={years} output={output} force_refresh={force_refresh}")

    cache = HttpCache(config.CACHE_DIR, config.CACHE_TTL_SECONDS)
    crawler = ArticleCrawler(cache=cache)
    db = Database()

    all_records: List[HorseMeasurement] = []
    tasks = [(club_key, year) for club_key in clubs for year in years]
    for club_key, year in tqdm(tasks, desc="クラブ×年度"):
        club = config.CLUBS[club_key]
        urls = crawler.discover_for_club_year(club, year, force_refresh=force_refresh)
        if not urls:
            logger.warning(f"No candidate articles found for {club.display_name} {year}年度")
            continue
        for url in tqdm(urls, desc=f"{club.display_name} {year}", leave=False):
            html = crawler.fetch(url, force_refresh=force_refresh)
            if not html:
                continue
            records = parse_article(html, url, club_key, year, club.search_keywords)
            all_records.extend(records)

    db.upsert_many(all_records)
    logger.info(f"Collected {len(all_records)} measurement rows in this run")

    df = db.fetch_dataframe(clubs=clubs, years=years)
    if output == "excel":
        excel_writer.write_excel(df)
    elif output == "csv":
        excel_writer.write_csv(df)
    elif output == "sqlite":
        logger.info(f"Data is stored in the SQLite database at {db.db_path}")

    db.close()
    logger.info("Done")


def main() -> None:
    args = build_arg_parser().parse_args()
    clubs = args.club or sorted(config.CLUBS.keys())
    years = args.years or config.DEFAULT_YEARS
    run(clubs=clubs, years=years, output=args.output, force_refresh=args.force_refresh)


if __name__ == "__main__":
    main()
