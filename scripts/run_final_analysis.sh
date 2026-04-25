#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "Usage: $0 <news_snapshot_json_path> <market_snapshot_json_path> <today_json_path> <recent_7days_json_path>" >&2
  exit 1
fi

readonly NEWS_SNAPSHOT_PATH="$1"
readonly MARKET_SNAPSHOT_PATH="$2"
readonly TODAY_JSON_PATH="$3"
readonly RECENT_JSON_PATH="$4"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly PROMPT_PATH="$PROJECT_ROOT/prompts/final_analysis.md"
readonly SCHEMA_PATH="$PROJECT_ROOT/schemas/daily_analysis.schema.json"

if [[ ! -f "$NEWS_SNAPSHOT_PATH" ]]; then
  echo "News snapshot input not found: $NEWS_SNAPSHOT_PATH" >&2
  exit 1
fi

if [[ ! -f "$MARKET_SNAPSHOT_PATH" ]]; then
  echo "Market snapshot input not found: $MARKET_SNAPSHOT_PATH" >&2
  exit 1
fi

if [[ ! -f "$RECENT_JSON_PATH" ]]; then
  echo '{"updated_at": null, "days": []}' > "$RECENT_JSON_PATH"
fi

tmp_prompt="$(mktemp)"
tmp_output="$(mktemp)"
cleanup() {
  rm -f "$tmp_prompt" "$tmp_output"
}
trap cleanup EXIT

analysis_date="$(date +%F)"
generated_at="$(date --iso-8601=seconds)"

{
  cat "$PROMPT_PATH"
  printf '\n\n'
  printf 'Target analysis date: %s\n' "$analysis_date"
  printf 'Generated at: %s\n\n' "$generated_at"
  printf '<recent_7days_json>\n'
  cat "$RECENT_JSON_PATH"
  printf '\n</recent_7days_json>\n\n'
  printf '<news_snapshot_json>\n'
  cat "$NEWS_SNAPSHOT_PATH"
  printf '\n</news_snapshot_json>\n\n'
  printf '<market_snapshot_json>\n'
  cat "$MARKET_SNAPSHOT_PATH"
  printf '\n</market_snapshot_json>\n'
} > "$tmp_prompt"

codex_args=(
  exec
  -C "$PROJECT_ROOT"
  -s workspace-write
  --output-schema "$SCHEMA_PATH"
  --output-last-message "$tmp_output"
  -
)

if [[ -n "${CODEX_MODEL:-}" ]]; then
  codex_args+=(-m "$CODEX_MODEL")
fi

codex "${codex_args[@]}" < "$tmp_prompt"

python3 - "$tmp_output" "$TODAY_JSON_PATH" <<'PY'
import json
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])

content = source_path.read_text(encoding="utf-8").strip()
if not content:
    raise SystemExit("Codex returned an empty response")

payload = json.loads(content)
target_path.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
PY

