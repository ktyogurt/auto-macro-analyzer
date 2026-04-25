#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_day(payload: dict) -> dict:
    inputs = payload.get("inputs", {})
    news = inputs.get("news", {}) if isinstance(inputs, dict) else {}
    market = inputs.get("market", {}) if isinstance(inputs, dict) else {}
    analysis = payload.get("analysis", {})

    if "news_summary" in payload and "analysis_summary" in payload:
        return {
            "date": payload.get("date"),
            "generated_at": payload.get("generated_at"),
            "news_summary": payload.get("news_summary"),
            "market_availability": payload.get("market_availability", "unavailable"),
            "analysis_summary": payload.get("analysis_summary"),
            "market_bias": payload.get("market_bias"),
            "confidence": payload.get("confidence"),
            "macro_drivers": payload.get("macro_drivers", []),
            "risks": payload.get("risks", []),
            "watch_items": payload.get("watch_items", []),
        }

    return {
        "date": payload.get("date"),
        "generated_at": payload.get("generated_at"),
        "news_summary": news.get("summary"),
        "market_availability": market.get("availability", "unavailable"),
        "analysis_summary": analysis.get("summary"),
        "market_bias": analysis.get("market_bias"),
        "confidence": analysis.get("confidence"),
        "macro_drivers": analysis.get("macro_drivers", []),
        "risks": analysis.get("risks", []),
        "watch_items": analysis.get("watch_items", []),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: roll_recent_7days.py <today_json_path> <recent_7days_json_path>",
            file=sys.stderr,
        )
        return 1

    today_path = Path(sys.argv[1])
    recent_path = Path(sys.argv[2])

    today_payload = load_json(today_path)
    if not isinstance(today_payload, dict):
        raise SystemExit("today.json must contain an object")

    today_date = today_payload.get("date")
    if not isinstance(today_date, str) or not today_date:
        raise SystemExit("today.json must contain a non-empty date")

    if recent_path.exists():
        recent_payload = load_json(recent_path)
    else:
        recent_payload = {"updated_at": None, "days": []}

    days = recent_payload.get("days", [])
    if not isinstance(days, list):
        raise SystemExit("recent_7days.json must contain a days array")

    filtered_days = []
    for day in days:
        if not isinstance(day, dict) or day.get("date") == today_date:
            continue
        filtered_days.append(compact_day(day))

    filtered_days.append(compact_day(today_payload))
    filtered_days.sort(key=lambda item: item["date"], reverse=True)
    filtered_days = filtered_days[:7]

    next_payload = {
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "days": filtered_days,
    }

    recent_path.write_text(
        json.dumps(next_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
