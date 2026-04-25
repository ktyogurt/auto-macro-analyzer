#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: build_market_snapshot.py <market_snapshot_output_path>", file=sys.stderr)
        return 1

    output_path = Path(sys.argv[1])
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "availability": "unavailable",
        "indices": {},
        "volatility": {},
        "rates": {},
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

