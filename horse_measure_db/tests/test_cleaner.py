from datetime import date

from utils import (
    clean_text,
    extract_number,
    extract_year_from_url,
    is_article_url,
    normalize_sex,
    parse_date,
    to_halfwidth,
)


def test_to_halfwidth_converts_fullwidth_digits():
    assert to_halfwidth("１５８．２") == "158.2"


def test_clean_text_collapses_whitespace_and_fullwidth_spaces():
    assert clean_text("  馬名　　テスト号 \n") == "馬名 テスト号"


def test_clean_text_handles_none():
    assert clean_text(None) == ""


def test_extract_number_from_halfwidth():
    assert extract_number("158.2cm") == 158.2


def test_extract_number_from_fullwidth():
    assert extract_number("４６０ｋｇ") == 460.0


def test_extract_number_returns_none_when_absent():
    assert extract_number("未測定") is None
    assert extract_number(None) is None


def test_normalize_sex_variants():
    assert normalize_sex("牡") == "牡"
    assert normalize_sex("牝馬") == "牝"
    assert normalize_sex("セン") == "セ"
    assert normalize_sex(None) is None


def test_parse_date_with_kanji_separators():
    assert parse_date("2024年3月15日") == date(2024, 3, 15)


def test_parse_date_with_slash_separators():
    assert parse_date("2024/03/15 測尺") == date(2024, 3, 15)


def test_parse_date_returns_none_when_unparseable():
    assert parse_date("未定") is None


def test_is_article_url_matches_date_permalink():
    assert is_article_url("https://sports-keiba.com/2025/07/24/25silklist1/") is True


def test_is_article_url_rejects_non_article_paths():
    assert is_article_url("https://sports-keiba.com/category/silk/") is False
    assert is_article_url("https://sports-keiba.com/") is False


def test_extract_year_from_url():
    assert extract_year_from_url("https://sports-keiba.com/2024/09/09/24car_list0701/") == 2024
    assert extract_year_from_url("https://sports-keiba.com/about/") is None
