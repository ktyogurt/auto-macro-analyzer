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

## セットアップ

1. 必要なら `.env.example` を `.env` にコピーして設定を上書きします
2. サーバー上で `codex login` が完了していることを確認します
3. `chmod +x scripts/*.sh scripts/*.py` を実行します

## 手動実行

```bash
./scripts/run_daily.sh
```

## 実行フロー

1. `scripts/fetch_news.sh` が RSS を取得します
2. `scripts/normalize_news.py` が RSS を中間JSONへ正規化します
3. `scripts/summarize_news.sh` が正規化JSONから `news_snapshot` を作ります
4. `scripts/build_market_snapshot.py` が `market_snapshot` を作ります
5. `scripts/run_final_analysis.sh` が `news_snapshot` と `market_snapshot` と `recent_7days.json` を Codex に渡します
6. Codex の出力を `data/today.json` に保存します
7. `scripts/roll_recent_7days.py` が `recent_7days.json` を更新します

## 将来拡張

- `news_snapshot` と `market_snapshot` を分けているため、ニュース要約と市場データ計算を独立に改善できます
- 将来的に `market_snapshot` へ指数騰落率、20MA判定、VIX、米10年金利などをコードで追加できます
- 最終段では複数スナップショットを統合し、リスク判定や注目点の抽出だけを LLM に任せる想定です

## 定期実行

- `infra/systemd/` に service と timer のサンプルがあります
- `infra/cron/auto-macro-analyzer.cron` に cron 設定例があります

どちらのサンプルも、リポジトリ配置先が `/home/kazuk/auto-macro-analyzer` である前提です。
