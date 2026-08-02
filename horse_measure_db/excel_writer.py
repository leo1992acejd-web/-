"""Excel / CSV への出力。SQLiteから読み出したDataFrameを整形して書き出す。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

import config


def _to_output_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=config.OUTPUT_COLUMNS)

    frame = pd.DataFrame(index=df.index)
    frame["クラブ"] = df["club"].map(
        lambda c: config.CLUBS[c].display_name if c in config.CLUBS else c
    )
    frame["募集年度"] = df["year"]
    frame["募集No"] = df["recruit_no"]
    frame["馬名"] = df["name"]
    frame["父"] = df["sire"]
    frame["母"] = df["dam"]
    frame["性別"] = df["sex"]
    frame["生年月日"] = df["birth_date"]
    frame["測尺日"] = df["measure_date"]
    frame["体高(cm)"] = df["height_cm"]
    frame["胸囲(cm)"] = df["girth_cm"]
    frame["管囲(cm)"] = df["cannon_cm"]
    frame["馬体重(kg)"] = df["weight_kg"]
    frame["記事URL"] = df["article_url"]
    return frame[config.OUTPUT_COLUMNS]


def write_excel(df: pd.DataFrame, path: Path = config.EXCEL_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = _to_output_frame(df)
    sheet_name = "募集馬測尺DB"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        output.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        for col_idx, column in enumerate(output.columns, start=1):
            values = output[column].astype(str).tolist()
            max_len = max([len(str(column))] + [len(v) for v in values]) if values else len(str(column))
            letter = worksheet.cell(row=1, column=col_idx).column_letter
            worksheet.column_dimensions[letter].width = min(max_len + 2, 40)
    logger.info(f"Wrote {len(output)} rows to {path}")
    return path


def write_csv(df: pd.DataFrame, path: Path = config.CSV_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    output = _to_output_frame(df)
    output.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info(f"Wrote {len(output)} rows to {path}")
    return path
