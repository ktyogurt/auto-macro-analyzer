#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly DATA_DIR="$PROJECT_ROOT/data"
readonly TODAY_JSON_PATH="$DATA_DIR/today.json"
readonly RECENT_JSON_PATH="$DATA_DIR/recent_7days.json"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi

mkdir -p "$DATA_DIR" "$PROJECT_ROOT/logs"

if [[ ! -f "$TODAY_JSON_PATH" ]]; then
  printf '{}\n' > "$TODAY_JSON_PATH"
fi

if [[ ! -f "$RECENT_JSON_PATH" ]]; then
  printf '{\n  "updated_at": null,\n  "days": []\n}\n' > "$RECENT_JSON_PATH"
fi

tmp_rss="$(mktemp)"
tmp_news_json="$(mktemp)"
tmp_news_snapshot="$(mktemp)"
tmp_market_snapshot="$(mktemp)"
cleanup() {
  rm -f "$tmp_rss" "$tmp_news_json" "$tmp_news_snapshot" "$tmp_market_snapshot"
}
trap cleanup EXIT

printf '[%s] Fetching RSS feed\n' "$(date --iso-8601=seconds)"
"$SCRIPT_DIR/fetch_news.sh" > "$tmp_rss"

printf '[%s] Normalizing news feed\n' "$(date --iso-8601=seconds)"
python3 "$SCRIPT_DIR/normalize_news.py" "$tmp_rss" "$tmp_news_json"

printf '[%s] Summarizing news snapshot\n' "$(date --iso-8601=seconds)"
"$SCRIPT_DIR/summarize_news.sh" "$tmp_news_json" "$tmp_news_snapshot"

printf '[%s] Building market snapshot\n' "$(date --iso-8601=seconds)"
python3 "$SCRIPT_DIR/build_market_snapshot.py" "$tmp_market_snapshot"

printf '[%s] Running final analysis\n' "$(date --iso-8601=seconds)"
"$SCRIPT_DIR/run_final_analysis.sh" "$tmp_news_snapshot" "$tmp_market_snapshot" "$TODAY_JSON_PATH" "$RECENT_JSON_PATH"

printf '[%s] Rolling recent_7days.json\n' "$(date --iso-8601=seconds)"
python3 "$SCRIPT_DIR/roll_recent_7days.py" "$TODAY_JSON_PATH" "$RECENT_JSON_PATH"

if [[ -n "${DYNAMODB_TABLE:-}" ]]; then
  printf '[%s] Uploading today.json to DynamoDB\n' "$(date --iso-8601=seconds)"
  python3 "$SCRIPT_DIR/upload_today_to_dynamodb.py" "$TODAY_JSON_PATH"
else
  printf '[%s] Skipping DynamoDB upload (DYNAMODB_TABLE is not set)\n' "$(date --iso-8601=seconds)"
fi

printf '[%s] Completed\n' "$(date --iso-8601=seconds)"
