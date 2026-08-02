from datetime import date

from parser import parse

ARTICLE_URL = "https://sports-keiba.com/2025/07/24/25silklist1/"

TABLE_WITH_THEAD = """
<html>
<body>
<h1>シルクホースクラブ 2025年度募集馬 測尺情報</h1>
<p>2025年度の募集馬について測尺データを掲載します。</p>
<table>
  <thead>
    <tr>
      <th>募集No</th><th>馬名</th><th>父</th><th>母</th><th>性別</th>
      <th>生年月日</th><th>測尺日</th><th>体高(cm)</th><th>胸囲(cm)</th>
      <th>管囲(cm)</th><th>馬体重(kg)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>1</td><td>テストホース</td><td>テストサイアー</td><td>テストマザー</td><td>牡</td>
      <td>2023年3月15日</td><td>2025年4月1日</td><td>158.2</td><td>180.5</td>
      <td>19.8</td><td>460</td>
    </tr>
    <tr>
      <td>2</td><td>サンプルガール</td><td>ダミーサイアー</td><td>ダミーマザー</td><td>牝</td>
      <td>2023年4月20日</td><td>2025年4月2日</td><td>152.0</td><td>175.0</td>
      <td>18.5</td><td>420</td>
    </tr>
  </tbody>
</table>
</body>
</html>
"""

TABLE_NO_THEAD_ALT_HEADERS = """
<html>
<body>
<h1>キャロットクラブ 2024年度募集馬（測尺追加）</h1>
<table>
  <tr>
    <td>No</td><td>馬名</td><td>父馬</td><td>母馬</td><td>性</td>
    <td>生年月日</td><td>測定日</td><td>体高</td><td>胸囲</td><td>管囲</td><td>体重</td>
  </tr>
  <tr>
    <td>A1</td><td>キャロ号</td><td>父キャロ</td><td>母キャロ</td><td>セン</td>
    <td>2022/03/10</td><td>2024/05/01</td><td>160.1cm</td><td>182.3cm</td>
    <td>20.1cm</td><td>470kg</td>
  </tr>
</table>
</body>
</html>
"""

# 実際のsports-keiba.com記事(2026年8月時点)で確認された、シルクHC募集予定馬の
# 表構造。母・生年月日・測尺日の列は存在せず、一口/厩舎という無関係な列が挟まる。
REAL_SILK_TABLE = """
<html>
<body>
<h1>シルクHC 2026年度 募集予定馬 測尺情報</h1>
<p>馬名のリンクはnetkeiba</p>
<table>
  <tr>
    <td>No.</td><td>募集予定馬名</td><td>性別</td><td>一口</td><td>厩舎</td>
    <td>父</td><td>体高</td><td>胸囲</td><td>管囲</td><td>体重</td>
  </tr>
  <tr>
    <td>1</td><td><a href="https://db.netkeiba.com/horse/dummy1">アーモンドアイの25</a></td>
    <td>牡</td><td>60</td><td>木村哲也</td><td>イクイノックス</td>
    <td>153</td><td>174</td><td>20.9</td><td>435</td>
  </tr>
  <tr>
    <td>2</td><td><a href="https://db.netkeiba.com/horse/dummy2">ソーディヴァインの25</a></td>
    <td>牝</td><td>13</td><td>鹿戸雄一</td><td>イクイノックス</td>
    <td>154</td><td>172.5</td><td>19.2</td><td>424</td>
  </tr>
</table>
</body>
</html>
"""


def test_parse_matches_real_sports_keiba_table_structure():
    url = "https://sports-keiba.com/2026/07/01/26silklist1/"
    records = parse(REAL_SILK_TABLE, url, "silk", 2026, ["シルク"])
    assert len(records) == 2

    first = records[0]
    assert first.recruit_no == "1"
    assert first.name == "アーモンドアイの25"
    assert first.sex == "牡"
    assert first.sire == "イクイノックス"
    assert first.height_cm == 153.0
    assert first.girth_cm == 174.0
    assert first.cannon_cm == 20.9
    assert first.weight_kg == 435.0
    # サイト側に列が存在しない項目はNoneのままでよい
    assert first.dam is None
    assert first.birth_date is None
    assert first.measure_date is None

    second = records[1]
    assert second.name == "ソーディヴァインの25"
    assert second.sex == "牝"
    assert second.weight_kg == 424.0


IRRELEVANT_ARTICLE = """
<html>
<body>
<h1>本日のレース結果</h1>
<table>
  <tr><th>着順</th><th>馬名</th></tr>
  <tr><td>1</td><td>ダミー</td></tr>
</table>
</body>
</html>
"""


def test_parse_extracts_rows_with_thead_structure():
    records = parse(TABLE_WITH_THEAD, ARTICLE_URL, "silk", 2025, ["シルク"])
    assert len(records) == 2

    first = records[0]
    assert first.recruit_no == "1"
    assert first.name == "テストホース"
    assert first.sire == "テストサイアー"
    assert first.dam == "テストマザー"
    assert first.sex == "牡"
    assert first.birth_date == date(2023, 3, 15)
    assert first.measure_date == date(2025, 4, 1)
    assert first.height_cm == 158.2
    assert first.girth_cm == 180.5
    assert first.cannon_cm == 19.8
    assert first.weight_kg == 460.0
    assert first.article_url == ARTICLE_URL
    assert first.club == "silk"
    assert first.year == 2025


def test_parse_handles_missing_thead_and_alternate_headers():
    url = "https://sports-keiba.com/2024/09/09/24car_list0701/"
    records = parse(TABLE_NO_THEAD_ALT_HEADERS, url, "carrot", 2024, ["キャロット"])
    assert len(records) == 1

    record = records[0]
    assert record.name == "キャロ号"
    assert record.sex == "セ"
    assert record.height_cm == 160.1
    assert record.weight_kg == 470.0
    assert record.birth_date == date(2022, 3, 10)


def test_parse_returns_empty_for_irrelevant_article():
    records = parse(IRRELEVANT_ARTICLE, ARTICLE_URL, "silk", 2025, ["シルク"])
    assert records == []


def test_parse_returns_empty_when_year_mismatches_url():
    # URLは2025年だが year=2026 を要求しているのでスキップされるべき
    records = parse(TABLE_WITH_THEAD, ARTICLE_URL, "silk", 2026, ["シルク"])
    assert records == []
