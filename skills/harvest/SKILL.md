---
name: harvest
description: >
  Search and harvest full-text content from multiple sources into the Prism wiki raw layer.
  Use when users ask to: search for trending topics, monitor keywords, harvest content,
  discover hot news, "搜一下XX", "帮我关注XX动态", "收割XX相关内容", "harvest XX",
  "monitor XX for my wiki", "什么是XX最新进展", "track XX", "find latest news about XX",
  or any request to search/discover current events and save them to the knowledge base.
---

# harvest — Prism 内容收割技能

Search 8+ sources, filter by relevance, fetch full content via Defuddle, save to `wiki/raw/`.

## Dependencies

```bash
# Python (search scripts)
pip install requests beautifulsoup4

# Node.js (Defuddle content extraction)
cd /path/to/prism && npm install
```

Optional: set `TWITTER_API_KEY` env var for Twitter search.

## Core Workflow

### Step 1: Understand intent

Determine keyword(s) and scope:
- **Broad discovery**: "最近AI有什么热点" → use `AI`, `人工智能`, `大模型` as keywords
- **Specific tracking**: "帮我关注 Harness Engineering" → use `harness engineering` as keyword
- **Multi-keyword**: support multiple keywords, run sequentially with 3s delay

### Step 2: Search all sources (Reference `references/search-sources.md`)

Run in parallel (international + Chinese):

```bash
# International (Bing, HackerNews, DuckDuckGo)
python skills/harvest/scripts/search_web.py "keyword" --sources bing,hackernews --limit 15

# Chinese (Sogou, Bilibili, Weibo)
python skills/harvest/scripts/search_china.py "keyword" --sources sogou,bilibili,weibo --limit 15

# Optional: Twitter (requires TWITTER_API_KEY)
python skills/harvest/scripts/search_twitter.py "keyword" --limit 15
```

Merge all JSON arrays into one combined result set.

### Step 3: AI analysis (Reference `references/analysis-guide.md`)

For each result, evaluate:
1. **isReal** — genuine news or clickbait/spam?
2. **relevance** (0-100) — how closely related to the keyword?
3. **importance** — `low` / `medium` / `high` / `urgent`
4. **summary** — one-sentence Chinese summary of the relationship to keyword

**AI Action**: Create a minimal JSON file (`annotations.json`) mapping the array indices (or URLs) to your decisions. For example:
```json
{
  "0": { "isReal": true, "relevance": 90, "importance": "high", "summary": "..." },
  "4": { "isReal": false }
}
```
*Note: Any item omitted or with relevance < 70 (or isReal = false) will be automatically discarded.*

Apply the filter:
```bash
python skills/harvest/scripts/apply_filter.py --raw search_results_raw.json --ann annotations.json --out annotated_results.json --keyword "harness engineering"
```

Present top results in structured format:

```markdown
## 🔥 harvest 报告 — {keyword}
> 扫描时间: {timestamp} | 数据源: {sources_used}

### 🚨 Urgent
- **{title}** — {summary}
  来源: {source} | 相关性: {relevance}% | [{url}]({url})

### 🔴 High
...
```

### Step 5: Full-text fetch + save to raw layer

> [!WARNING]
> **Windows Users**: You MUST run these piping/redirection commands in **Command Prompt (`cmd.exe`)** (or Git Bash/WSL), NOT PowerShell. PowerShell native redirection `<` `>` modifies string encodings and will corrupt the JSON formatting!

```cmd
# Fetch full content via Defuddle (and follow redirects)
node skills/harvest/scripts/fetch_content.js < annotated_results.json > enriched.json

# Save to wiki/raw/ (full-text) or wiki/signals/ (snippets)
python skills/harvest/scripts/save_to_raw.py --keyword "harness engineering" < enriched.json
```

Report to user:
- How many articles were saved and to which path
- Suggest running `prism` skill to organize into wiki pages

## Script Reference

| Script | Sources | Key Options |
|--------|---------|-------------|
| `search_web.py` | Bing, Google, DuckDuckGo, HackerNews | `--sources`, `--limit` |
| `search_china.py` | Sogou, Bilibili, Weibo | `--sources`, `--limit`, `--detect-account` |
| `search_twitter.py` | Twitter/X | `--limit`, `--trends`, `--user` |
| `apply_filter.py` | — | `--raw`, `--ann`, `--out`, `--keyword` |
| `fetch_content.js` | Web (via Defuddle) | `--min-relevance`, `--concurrency`, `--timeout` |
| `save_to_raw.py` | — | `--wiki-dir`, `--keyword`, `--dry-run` |

## Notes

- **Bilibili & Weibo**: Defuddle has no extractor for these. Their content is saved as snippets only (still valuable for trend detection).
- **YouTube**: Defuddle automatically extracts subtitles/transcripts.
- **Rate limits**: search scripts enforce delays between requests automatically.

## References

- [analysis-guide.md](references/analysis-guide.md) — Scoring criteria for isReal, relevance, importance
- [search-sources.md](references/search-sources.md) — Per-source details, limits, quirks
