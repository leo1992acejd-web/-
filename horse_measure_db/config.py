"""horse_measure_db 全体の設定値。

環境依存の値は .env (python-dotenv) から読み込む。
クラブや年度の追加はこのファイルの CLUBS / DEFAULT_YEARS を編集するだけでよい。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"

for _dir in (CACHE_DIR, LOG_DIR, OUTPUT_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

BASE_URL = os.getenv("HORSE_DB_BASE_URL", "https://sports-keiba.com").rstrip("/")

USER_AGENT = os.getenv(
    "HORSE_DB_USER_AGENT",
    "horse-measure-db-bot/1.0 (+research use; contact via HORSE_DB_USER_AGENT env)",
)
REQUEST_INTERVAL_SECONDS = float(os.getenv("HORSE_DB_REQUEST_INTERVAL", "1.5"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("HORSE_DB_TIMEOUT", "15"))
MAX_RETRIES = int(os.getenv("HORSE_DB_MAX_RETRIES", "3"))
CACHE_TTL_SECONDS = int(os.getenv("HORSE_DB_CACHE_TTL", str(60 * 60 * 24 * 7)))
SEARCH_MAX_PAGES = int(os.getenv("HORSE_DB_SEARCH_MAX_PAGES", "5"))
LOG_LEVEL = os.getenv("HORSE_DB_LOG_LEVEL", "INFO")

DB_PATH = Path(os.getenv("HORSE_DB_SQLITE_PATH", str(OUTPUT_DIR / "horse_measure.db")))
EXCEL_PATH = Path(os.getenv("HORSE_DB_EXCEL_PATH", str(OUTPUT_DIR / "募集馬測尺DB.xlsx")))
CSV_PATH = Path(os.getenv("HORSE_DB_CSV_PATH", str(OUTPUT_DIR / "募集馬測尺DB.csv")))


@dataclass(frozen=True)
class ClubConfig:
    key: str
    display_name: str
    search_keywords: List[str]


# クラブを追加する場合はここにキーを1つ増やすだけでよい。
CLUBS: Dict[str, ClubConfig] = {
    "silk": ClubConfig("silk", "シルクホースクラブ", ["シルク"]),
    "carrot": ClubConfig("carrot", "キャロットクラブ", ["キャロット"]),
    "sunday": ClubConfig("sunday", "サンデーサラブレッドクラブ", ["サンデー"]),
    "shadai": ClubConfig("shadai", "社台サラブレッドクラブ", ["社台"]),
}

# 2027年度以降は末尾に年度を追加するだけで対応できる。
DEFAULT_YEARS: List[int] = [2024, 2025, 2026]

MEASUREMENT_KEYWORD = "測尺"

OUTPUT_COLUMNS: List[str] = [
    "クラブ",
    "募集年度",
    "募集No",
    "馬名",
    "父",
    "母",
    "性別",
    "生年月日",
    "測尺日",
    "体高(cm)",
    "胸囲(cm)",
    "管囲(cm)",
    "馬体重(kg)",
    "記事URL",
]
