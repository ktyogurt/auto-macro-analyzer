#!/usr/bin/env bash

set -euo pipefail

readonly DEFAULT_NEWS_RSS_URL='https://news.google.com/rss/search?q=US+stock+market+OR+S%26P+500+OR+Nasdaq&hl=en-US&gl=US&ceid=US:en'
NEWS_RSS_URL="${NEWS_RSS_URL:-$DEFAULT_NEWS_RSS_URL}"

curl \
  --fail \
  --silent \
  --show-error \
  --location \
  "$NEWS_RSS_URL"

