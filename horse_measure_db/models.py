"""測尺データ1頭分を表すドメインモデル。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class HorseMeasurement:
    club: str
    year: int
    recruit_no: Optional[str]
    name: Optional[str]
    sire: Optional[str]
    dam: Optional[str]
    sex: Optional[str]
    birth_date: Optional[date]
    measure_date: Optional[date]
    height_cm: Optional[float]
    girth_cm: Optional[float]
    cannon_cm: Optional[float]
    weight_kg: Optional[float]
    article_url: str
