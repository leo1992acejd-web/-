# horse_measure_db

[sports-keiba.com](https://sports-keiba.com/) に掲載されている募集馬測尺記事を自動収集し、
シルクホースクラブ／キャロットクラブ／サンデーサラブレッドクラブ／社台サラブレッドクラブの
測尺データをまとめた `募集馬測尺DB.xlsx`（またはCSV／SQLite）を生成するツールです。

## 特徴

- **記事URLを固定で持たない**: WordPress REST検索API → サイト内検索HTML → サイトマップ、
  の順にフォールバックしながら関連記事を自動探索します。
- **記事構造の変化に強いHTML解析**: CSSクラス名などの見た目情報には依存せず、
  `table > thead/tbody > tr > td` の構造とヘッダーセルの日本語テキスト
  （「体高」「胸囲」「管囲」「馬体重」など）だけで列を推定します。
- **年度追加だけで拡張可能**: `config.py` の `DEFAULT_YEARS` に年度を1行追加するだけで、
  2027年度以降にも対応できます。
- **robots.txt準拠 / アクセス間隔制御**: `RobotsChecker` が robots.txt を尊重し、
  リクエスト間には待機時間（デフォルト1.5秒 + ジッター）を挟みます。
- **キャッシュ**: 取得済みHTML/JSONはローカルにキャッシュし、再実行時の負荷を削減します
  (`--force-refresh` で無視可能)。
- **冪等な永続化**: SQLiteを正とするストアとし、`(club, year, name, article_url)` を
  一意キーとしたUPSERTで再実行しても重複しません。

## ディレクトリ構成

```
horse_measure_db/
    README.md
    requirements.txt
    .env.example
    .gitignore
    config.py          設定値（クラブ・年度・パス・リクエスト設定）
    main.py             CLIエントリポイント
    crawler.py          記事探索・HTTP取得（キャッシュ/リトライ/robots.txt対応）
    parser.py           HTML解析（table構造から測尺データを抽出）
    models.py           HorseMeasurement データクラス
    database.py         SQLite永続化層
    excel_writer.py      Excel/CSV出力
    cache.py            HTTPレスポンスのファイルキャッシュ
    logger.py           loguru設定
    utils.py            汎用ヘルパー（数値/日付/性別の正規化、robots.txt チェック等）
    tests/
        test_parser.py
        test_cleaner.py
    .github/workflows/run.yml   定期実行用GitHub Actions
    cache/    logs/    output/
```

## セットアップ

```bash
cd horse_measure_db
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 必要に応じて値を調整
```

## 使い方

```bash
# 全クラブ × config.DEFAULT_YEARS (2024, 2025, 2026) を収集し Excel を出力
python main.py

# クラブを絞り込む
python main.py --club silk
python main.py --club carrot
python main.py --club sunday
python main.py --club shadai
python main.py --club silk carrot

# 年度を絞り込む
python main.py --years 2024 2025
python main.py --years 2024 2025 2026

# 出力形式を選択（デフォルトは excel）
python main.py --output excel
python main.py --output csv
python main.py --output sqlite

# キャッシュを無視してすべて再取得
python main.py --force-refresh
```

出力先:
- Excel: `output/募集馬測尺DB.xlsx`
- CSV: `output/募集馬測尺DB.csv`
- SQLite: `output/horse_measure.db`（`--output` の値によらず常にここへ蓄積されます）

## 出力項目

| 列名 | 説明 |
|---|---|
| クラブ | クラブ名（シルクホースクラブ 等） |
| 募集年度 | 2024 / 2025 / 2026 など |
| 募集No | 記事内の募集番号（取得できない場合は記事内の出現順） |
| 馬名 | 馬名 |
| 父 | 父馬名 |
| 母 | 母馬名 |
| 性別 | 牡 / 牝 / セ に正規化 |
| 生年月日 | ISO形式 (YYYY-MM-DD) |
| 測尺日 | ISO形式 (YYYY-MM-DD) |
| 体高(cm) | 数値 |
| 胸囲(cm) | 数値 |
| 管囲(cm) | 数値 |
| 馬体重(kg) | 数値 |
| 記事URL | 出典記事のURL |

## 2027年度以降への対応方法

`config.py` の `DEFAULT_YEARS` に年度を追記するだけです。コード変更は不要です。

```python
DEFAULT_YEARS: List[int] = [2024, 2025, 2026, 2027]
```

または都度 `python main.py --years 2027` のようにCLIから指定することもできます。
クラブを追加したい場合も同様に `config.py` の `CLUBS` に1エントリ追加するだけです。

## アーキテクチャ概要

1. **crawler.py** がクラブ名＋「測尺」（＋年度）のキーワードで記事を探索します。
   - まず WordPress REST 検索API (`/wp-json/wp/v2/search`) を試行
   - 次にサイト内検索HTMLページ (`/?s=...`) をページングしながら走査
   - いずれも0件の場合のみ `sitemap_index.xml` 等のサイトマップにフォールバック
   - いずれの手法でも `/YYYY/MM/DD/slug/` という日付ベースパーマリンクの
     パターンに一致するリンクだけを記事URLとして採用します（テーマ変更の影響を受けにくい）。
2. **parser.py** が記事HTML内の全 `<table>` を走査し、ヘッダーセルのテキストから
   列を推定して測尺データを抽出します。あわせて、ページ本文にクラブ名・
   「測尺」というキーワードが含まれるか、年度がURL/本文と整合するかを検証し、
   無関係な検索ヒットを除外します。
3. **database.py** が抽出結果をSQLiteにUPSERTします（重複は自動的にマージ）。
4. **excel_writer.py** がSQLiteから読み出したデータを指定フォーマットで出力します。

## テスト

```bash
pytest -q
```

`tests/test_cleaner.py` は数値・日付・性別の正規化やURL判定ロジックを、
`tests/test_parser.py` はヘッダー表記ゆれや `thead` の有無が異なる複数パターンの
HTMLに対してパーサが正しく動作することを検証します。

## GitHub Actions での定期実行

`.github/workflows/run.yml` は毎週月曜03:00 JST（デフォルト無効化したい場合はcron行を削除）に
`pytest` → `python main.py` を実行し、生成物を Actions のアーティファクトとしてアップロードします。
`workflow_dispatch` から手動実行する際は `club` / `years` / `output` を入力パラメータとして指定できます。

## 既知の制約: データセンター系IPからのアクセスブロック

開発時の検証で、sports-keiba.com は **データセンター/クラウド系IPからのアクセスをブロック**して
いることが確認されています。

- 開発用サンドボックス環境からのアクセス: 403 Forbidden
- GitHub Actions のホステッドランナー(Azure上のクラウドIP)からのアクセス: 接続タイムアウト
- スマートフォンのモバイル回線からのアクセス: 正常に閲覧可能

一方、実際の記事(シルクHC 2026年度募集予定馬)を目視確認したところ、`table` の見出しは
`No. / 募集予定馬名 / 性別 / 一口 / 厩舎 / 父 / 体高 / 胸囲 / 管囲 / 体重` であり、
`parser.py` の列マッチングロジックはこの実物の見出しと正しく一致することを
`tests/test_parser.py::test_parse_matches_real_sports_keiba_table_structure` で確認済みです
(なお、この記事には「母」「生年月日」「測尺日」の列が存在しないため、これらは
記事によっては空欄になります)。つまり **パーサーのロジックは実データに対応済みだが、
クラウドIPからの接続自体がブロックされているため自動収集が実行できない** という状態です。

対応策:

1. **住宅用/モバイル系プロキシ経由でアクセスする**（推奨・最も簡単）
   `requests` は標準で `HTTPS_PROXY` / `HTTP_PROXY` 環境変数を自動的に参照するため、
   このツール側にプロキシ専用のコードは不要です。`.env` に設定するか、
   GitHub Actions で使う場合はリポジトリの Secrets に `HORSE_DB_HTTPS_PROXY`
   (例: `http://user:pass@residential-proxy.example.com:8080`) を登録してください。
   `.github/workflows/run.yml` は既にこのSecretsを `HTTPS_PROXY`/`HTTP_PROXY` として
   スクレイパーに渡すよう設定済みです。未設定の場合は従来通り直接アクセスを試みます。
2. **住宅用ネットワーク環境のマシンで直接実行する**（PC等がある場合）
   `python main.py` をそのまま実行するだけです。
3. **モバイル端末上のLinux環境(例: Android Termux)で実行する**
   モバイル回線であればブロックされないことを確認済みです。ただし `lxml` / `pandas`
   等のネイティブ依存パッケージのインストールに追加の手順が必要な場合があります。

## 運用上の注意

- `HORSE_DB_USER_AGENT` には連絡先を含めることを推奨します（サイト運営者が問い合わせやすくするため）。
- `HORSE_DB_REQUEST_INTERVAL` はサイトへの負荷を考慮し、1.0秒以上を維持してください。
- 本ツールは `robots.txt` を尊重します。robots.txt が取得できない場合は警告を出したうえで
  保守的に動作しますが、サイト運営者の利用規約も別途ご確認ください。
- サイトのマークアップが大きく変わった場合、`parser.py` の `COLUMN_ALIASES` に
  新しい見出し表記を追加することで多くの場合対応できます。
