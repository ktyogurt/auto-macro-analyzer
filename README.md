# auto-macro-analyzer

米国株分析向けの、最小構成の日次マクロ分析パイプラインです。

## 概要

- Google News RSS から米国株関連ニュースを取得します
- RSS を正規化JSONへ変換します
- 正規化JSONからニュース要約用の `news_snapshot` を作ります
- 別途 `market_snapshot` を作る構成にしており、今はプレースホルダーを出力します
- `news_snapshot` と `market_snapshot` と `data/recent_7days.json` を入力として最終分析を作成します
- 当日の分析結果を `data/today.json` に保存します
- 直近7日分の分析結果を `data/recent_7days.json` に保持します

生の RSS レスポンスも各スナップショットも永続保存しません。各実行時に一時ファイルとして扱い、処理後に削除します。
正規化JSONには、トークン消費を抑えるため最新20件までの見出しを残します。
正規化JSONには長いURLを含めず、見出し・ソース・時刻だけを残します。

## 出力仕様

- JSON のキー名は英語のまま固定です
- 入力由来の要約は `inputs.news` 配下に置きます
- `inputs.market` は常に持ち、今は `availability` で利用可否だけを表現します
- `market_bias` は `bullish` / `neutral` / `bearish` のいずれかです
- `confidence` は `low` / `medium` / `high` のいずれかです
- 人が読む本文は日本語で出力します
- 日本語になるのは主に `inputs.news.summary`, `inputs.news.detailed_summary`, `inputs.news.top_headlines`, `inputs.news.notable_sources`, `inputs.news.macro_themes`, `summary`, `macro_drivers`, `risks`, `watch_items` です
- `summary` は短い日本語1文です
- `inputs.news.detailed_summary` はニュース専用の詳しめ要約で、250-400字を目安にしています
- `macro_drivers`, `risks`, `watch_items` は短いキーワード寄りの名詞句です
- `recent_7days.json` は最終分析入力を軽く保つため、短縮版の履歴だけを保持します

## ディレクトリ構成

```text
.
├── data/
│   ├── recent_7days.json
│   └── today.json
├── infra/
│   ├── cron/
│   └── systemd/
├── prompts/
│   ├── final_analysis.md
│   └── news_summary.md
├── schemas/
│   ├── daily_analysis.schema.json
│   ├── market_snapshot.schema.json
│   ├── news_snapshot.schema.json
│   └── normalized_news.schema.json
└── scripts/
    ├── build_market_snapshot.py
    ├── fetch_news.sh
    ├── normalize_news.py
    ├── roll_recent_7days.py
    ├── run_daily.sh
    ├── run_final_analysis.sh
    └── summarize_news.sh
```

## 必要環境

- `bash`
- `curl`
- `python3`
- `codex`
- `boto3`（DynamoDB 連携を使う場合）

## セットアップ

1. 必要なら `.env.example` を `.env` にコピーして設定を上書きします
2. サーバー上で `codex login` が完了していることを確認します
3. DynamoDB 連携を使う場合は `pip install boto3` を実行します
4. `chmod +x scripts/*.sh scripts/*.py` を実行します

## 手動実行

```bash
./scripts/run_daily.sh
```

`.env` を現在のシェルへ手動で読み込む場合は、URL を含む値のためクォート付きで記述し、変数を export するため次の形を使ってください。

```bash
set -a
source .env
set +a
```

`venv` で `boto3` を入れている場合は、`.env` に `PYTHON_BIN` を設定すると `run_daily.sh` からその Python を使えます。

```bash
PYTHON_BIN=/home/ktyogurt/myenv/bin/python
```

## 実行フロー

1. `scripts/fetch_news.sh` が RSS を取得します
2. `scripts/normalize_news.py` が RSS を中間JSONへ正規化します
3. `scripts/summarize_news.sh` が正規化JSONから `news_snapshot` を作ります
4. `scripts/build_market_snapshot.py` が `market_snapshot` を作ります
5. `scripts/run_final_analysis.sh` が `news_snapshot` と `market_snapshot` と `recent_7days.json` を Codex に渡します
6. Codex の出力を `data/today.json` に保存します
7. `scripts/roll_recent_7days.py` が `recent_7days.json` を更新します
8. `DYNAMODB_TABLE` が設定されていれば `scripts/upload_today_to_dynamodb.py` が `today.json` を DynamoDB に保存します

## DynamoDB 連携

ローカルで `./scripts/run_daily.sh` を実行した際に、`data/today.json` を DynamoDB に自動保存できます。
アップロードは `.env` に `DYNAMODB_TABLE` を設定した場合だけ有効です。

### 推奨テーブル設計

- Partition key: `pk`（String）
- Sort key: `sk`（String）

`.env.example` のデフォルト設定では、次の 2 件を書き込みます。

- 履歴 item: `pk=daily_analysis`, `sk=DATE#YYYY-MM-DD`
- 最新 item: `pk=daily_analysis`, `sk=META#LATEST`

どちらの item にも `date`, `generated_at`, `market_bias`, `confidence`, `summary`, `payload` を保存します。
`payload` には `today.json` 全体がそのまま入るため、AWS 側アプリは必要に応じて本文まで読めます。

### 環境変数

- `DYNAMODB_TABLE`: アップロード先テーブル名
- `AWS_REGION`: 使用リージョン。未設定時は AWS SDK の既定値を利用
- `AWS_PROFILE`: ローカルの AWS プロファイル名
- `PYTHON_BIN`: 使用する Python 実行ファイル。`venv` を使う場合はその絶対パス
- `DYNAMODB_ENDPOINT_URL`: 任意。DynamoDB Local などに向ける場合に利用
- `DYNAMODB_PK_NAME`: パーティションキー属性名。既定値は `pk`
- `DYNAMODB_SK_NAME`: ソートキー属性名。既定値は `sk`
- `DYNAMODB_PK_VALUE`: パーティションキー値。既定値は `daily_analysis`
- `DYNAMODB_DATE_PREFIX`: 日別 item のソートキー接頭辞。既定値は `DATE#`
- `DYNAMODB_LATEST_KEY`: 最新 item のソートキー値。既定値は `META#LATEST`

### 動作確認

実際に書き込む前に item 形状だけ確認したい場合は、次のように dry-run できます。

```bash
DYNAMODB_TABLE=your-table DYNAMODB_DRY_RUN=1 \
/home/ktyogurt/myenv/bin/python scripts/upload_today_to_dynamodb.py data/today.json
```

## cron 例

`infra/cron/auto-macro-analyzer.cron` は日本時間 11:00 実行の例です。`CRON_TZ=Asia/Tokyo` を付けているため、サーバー自体が UTC でも 11:00 JST 基準で動かせます。

## 将来拡張

- `news_snapshot` と `market_snapshot` を分けているため、ニュース要約と市場データ計算を独立に改善できます
- 将来的に `market_snapshot` へ指数騰落率、20MA判定、VIX、米10年金利などをコードで追加できます
- 最終段では複数スナップショットを統合し、リスク判定や注目点の抽出だけを LLM に任せる想定です

## 定期実行

- `infra/systemd/` に service と timer のサンプルがあります
- `infra/cron/auto-macro-analyzer.cron` に cron 設定例があります

どちらのサンプルも、リポジトリ配置先が `/home/kazuk/auto-macro-analyzer` である前提です。
