#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

MAX_HEADLINES = 20


def text_or_empty(element: ElementTree.Element | None, tag: str) -> str:
    if element is None:
        return ""
    child = element.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: normalize_news.py <rss_input_path> <normalized_output_path>", file=sys.stderr)
        return 1

    rss_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    root = ElementTree.fromstring(rss_path.read_text(encoding="utf-8"))
    channel = root.find("channel")
    if channel is None:
        raise SystemExit("RSS feed does not contain a channel element")

    headlines: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for item in channel.findall("item"):
        title = text_or_empty(item, "title")
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)

        source = text_or_empty(item, "source")
        published_at = text_or_empty(item, "pubDate")

        headlines.append(
            {
                "title": title,
                "source": source,
                "published_at": published_at,
            }
        )

    normalized_headlines = headlines[:MAX_HEADLINES]

    payload = {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "headline_count": len(normalized_headlines),
        "notable_sources": [
            source
            for source, _ in Counter(
                headline["source"]
                for headline in normalized_headlines
                if headline["source"]
            ).most_common(5)
        ],
        "headlines": normalized_headlines,
    }

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
