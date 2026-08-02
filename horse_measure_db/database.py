"""SQLite (標準ライブラリ) による永続化層。

このDBが正となるストアであり、Excel/CSV出力はいずれもここから読み出す。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from loguru import logger

import config
from models import HorseMeasurement

SCHEMA = """
CREATE TABLE IF NOT EXISTS horse_measurements (
    club TEXT NOT NULL,
    year INTEGER NOT NULL,
    recruit_no TEXT,
    name TEXT,
    sire TEXT,
    dam TEXT,
    sex TEXT,
    birth_date TEXT,
    measure_date TEXT,
    height_cm REAL,
    girth_cm REAL,
    cannon_cm REAL,
    weight_kg REAL,
    article_url TEXT NOT NULL,
    UNIQUE(club, year, name, article_url)
);
"""

UPSERT_SQL = """
INSERT INTO horse_measurements
    (club, year, recruit_no, name, sire, dam, sex, birth_date,
     measure_date, height_cm, girth_cm, cannon_cm, weight_kg, article_url)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(club, year, name, article_url) DO UPDATE SET
    recruit_no=excluded.recruit_no,
    sire=excluded.sire,
    dam=excluded.dam,
    sex=excluded.sex,
    birth_date=excluded.birth_date,
    measure_date=excluded.measure_date,
    height_cm=excluded.height_cm,
    girth_cm=excluded.girth_cm,
    cannon_cm=excluded.cannon_cm,
    weight_kg=excluded.weight_kg
"""


class Database:
    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def upsert_many(self, records: Iterable[HorseMeasurement]) -> int:
        rows = [
            (
                r.club,
                r.year,
                r.recruit_no,
                r.name,
                r.sire,
                r.dam,
                r.sex,
                r.birth_date.isoformat() if r.birth_date else None,
                r.measure_date.isoformat() if r.measure_date else None,
                r.height_cm,
                r.girth_cm,
                r.cannon_cm,
                r.weight_kg,
                r.article_url,
            )
            for r in records
        ]
        if not rows:
            return 0
        self._conn.executemany(UPSERT_SQL, rows)
        self._conn.commit()
        logger.info(f"Upserted {len(rows)} rows into {self.db_path}")
        return len(rows)

    def fetch_dataframe(
        self, clubs: Optional[List[str]] = None, years: Optional[List[int]] = None
    ) -> pd.DataFrame:
        query = "SELECT * FROM horse_measurements"
        clauses: List[str] = []
        params: List = []
        if clubs:
            clauses.append(f"club IN ({','.join('?' for _ in clubs)})")
            params.extend(clubs)
        if years:
            clauses.append(f"year IN ({','.join('?' for _ in years)})")
            params.extend(years)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY year, club, recruit_no"
        return pd.read_sql_query(query, self._conn, params=params)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
