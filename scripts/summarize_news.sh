#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <normalized_news_json_path> <news_snapshot_output_path>" >&2
  exit 1
fi

readonly NORMALIZED_NEWS_PATH="$1"
readonly NEWS_SNAPSHOT_PATH="$2"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
readonly PROMPT_PATH="$PROJECT_ROOT/prompts/news_summary.md"
readonly SCHEMA_PATH="$PROJECT_ROOT/schemas/news_snapshot.schema.json"
readonly PYTHON_BIN="${PYTHON_BIN:-python3}"
readonly CODEX_BIN="${CODEX_BIN:-codex}"

if [[ ! -f "$NORMALIZED_NEWS_PATH" ]]; then
  echo "Normalized news input not found: $NORMALIZED_NEWS_PATH" >&2
  exit 1
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
  printf '<normalized_news_json>\n'
  cat "$NORMALIZED_NEWS_PATH"
  printf '\n</normalized_news_json>\n'
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

"$CODEX_BIN" "${codex_args[@]}" < "$tmp_prompt"

"$PYTHON_BIN" - "$tmp_output" "$NEWS_SNAPSHOT_PATH" <<'PY'
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
