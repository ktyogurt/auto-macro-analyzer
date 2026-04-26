#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
    if not isinstance(payload, dict):
        raise SystemExit("today.json must contain an object")
    return payload


def require_string(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"today.json must contain a non-empty {key}")
    return value


def build_item(
    *,
    payload: dict,
    pk_name: str,
    sk_name: str,
    pk_value: str,
    sk_value: str,
) -> dict:
    analysis = payload.get("analysis", {})
    if not isinstance(analysis, dict):
        raise SystemExit("today.json must contain an analysis object")

    item = {
        pk_name: pk_value,
        sk_name: sk_value,
        "date": require_string(payload, "date"),
        "generated_at": require_string(payload, "generated_at"),
        "market_bias": analysis.get("market_bias"),
        "confidence": analysis.get("confidence"),
        "summary": analysis.get("summary"),
        "payload": payload,
    }
    return item


def is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def getenv_nonempty(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def json_default(value: object) -> int | float:
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: upload_today_to_dynamodb.py <today_json_path>", file=sys.stderr)
        return 1

    table_name = getenv_nonempty("DYNAMODB_TABLE")
    if not table_name:
        print("DYNAMODB_TABLE is not set", file=sys.stderr)
        return 1

    today_path = Path(sys.argv[1])
    payload = load_json(today_path)

    pk_name = getenv_nonempty("DYNAMODB_PK_NAME") or "pk"
    sk_name = getenv_nonempty("DYNAMODB_SK_NAME") or "sk"
    pk_value = getenv_nonempty("DYNAMODB_PK_VALUE") or "daily_analysis"
    date_prefix = getenv_nonempty("DYNAMODB_DATE_PREFIX") or "DATE#"
    latest_key = getenv_nonempty("DYNAMODB_LATEST_KEY") or "META#LATEST"

    date_value = require_string(payload, "date")
    history_key = f"{date_prefix}{date_value}"

    history_item = build_item(
        payload=payload,
        pk_name=pk_name,
        sk_name=sk_name,
        pk_value=pk_value,
        sk_value=history_key,
    )
    latest_item = build_item(
        payload=payload,
        pk_name=pk_name,
        sk_name=sk_name,
        pk_value=pk_value,
        sk_value=latest_key,
    )
    latest_item["latest_date"] = date_value
    latest_item["source_report_key"] = history_key

    if is_truthy(os.getenv("DYNAMODB_DRY_RUN")):
        print(
            json.dumps(
                {
                    "table_name": table_name,
                    "history_item": history_item,
                    "latest_item": latest_item,
                },
                ensure_ascii=False,
                indent=2,
                default=json_default,
            )
        )
        return 0

    try:
        import boto3
    except ImportError as exc:
        raise SystemExit(
            "boto3 is required for DynamoDB upload. Install it with: pip install boto3"
        ) from exc

    session_kwargs: dict[str, str] = {}
    aws_profile = getenv_nonempty("AWS_PROFILE")
    aws_region = getenv_nonempty("AWS_REGION")
    if aws_profile:
        session_kwargs["profile_name"] = aws_profile
    if aws_region:
        session_kwargs["region_name"] = aws_region

    endpoint_url = getenv_nonempty("DYNAMODB_ENDPOINT_URL")

    session = boto3.session.Session(**session_kwargs)
    dynamodb = session.resource("dynamodb", endpoint_url=endpoint_url)
    table = dynamodb.Table(table_name)

    table.put_item(Item=history_item)
    table.put_item(Item=latest_item)

    print(
        f"Uploaded {date_value} to DynamoDB table {table_name} "
        f"({pk_name}={pk_value}, {sk_name}={history_key})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
