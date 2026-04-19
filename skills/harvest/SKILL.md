---
name: harvest
description: >
  Search and harvest full-text content from multiple web sources.
  Use when users ask to: search for trending topics, monitor keywords, harvest content,
  discover hot news, "搜一下XX", "帮我关注XX动态", "收割XX相关内容", "harvest XX",
  "什么是XX最新进展", "track XX", "find latest news about XX",
  or any request to search/discover current events from the web.
---

# harvest — 全网内容收割技能

Search 8+ sources, filter by AI relevance scoring, fetch full-text content via Defuddle.
Outputs a single enriched JSON file ready for downstream consumption (e.g., by the `prism` skill).

## Phase 0: Environment Setup (MUST DO FIRST)

Before running ANY commands, you must resolve two critical paths:

### 1. Locate this skill's installation directory

Since you are reading this file right now, you already know where it lives. Derive the skill root:

```
SKILL_DIR = <directory containing this SKILL.md file>
```

For example, if you are reading from `/home/user/.gemini/skills/harvest/SKILL.md`, then `SKILL_DIR=/home/user/.gemini/skills/harvest`.

**All script paths below use `$SKILL_DIR` as prefix.** Replace it with the actual absolute path you derived.

### 2. Confirm the user's working directory

All output files are created relative to the **user's current working directory (CWD)**, NOT relative to `$SKILL_DIR`.

### 3. Install dependencies (first run only)

Check if dependencies are already available. If not, install them:

```bash
# Python
pip install requests beautifulsoup4

# Node.js (install into SKILL_DIR so scripts can find them)
cd $SKILL_DIR && npm install defuddle jsdom --no-save
```

Optional: set `TWITTER_API_KEY` env var for Twitter search.

## Core Workflow

### Step 1: Understand intent & Create Cache

Determine keyword(s) and scope. Then create the cache workspace for this keyword (slugified) in the **user's CWD**:

```bash
mkdir -p [keyword]/.cache
```

### Step 2: Search all sources

Run search scripts using `$SKILL_DIR` for script paths, CWD-relative for output:

```bash
# International (Bing, HackerNews, GitHub, YouTube)
python $SKILL_DIR/scripts/search_web.py "keyword" --sources bing,hackernews,github,youtube --limit 15 --out [keyword]/.cache/web.json

# Chinese (Bilibili, Weibo, Juejin)
python $SKILL_DIR/scripts/search_china.py "keyword" --sources bilibili,weibo,juejin --limit 15 --out [keyword]/.cache/zh.json

# Optional: Twitter (requires TWITTER_API_KEY)
python $SKILL_DIR/scripts/search_twitter.py "keyword" --limit 15 --out [keyword]/.cache/twitter.json
```

Merge all JSON arrays into one combined result set as `[keyword]/.cache/search_results_raw.json`.

### Step 3: AI analysis (Reference `$SKILL_DIR/references/analysis-guide.md`)

For each result, evaluate:
1. **isReal** — genuine news or clickbait/spam?
2. **relevance** (0-100) — how closely related to the keyword?
3. **importance** — `low` / `medium` / `high` / `urgent`
4. **summary** — one-sentence Chinese summary of the relationship to keyword

**AI Action**: Create `[keyword]/.cache/annotations.json`:
```json
{
  "0": { "isReal": true, "relevance": 90, "importance": "high", "summary": "..." },
  "4": { "isReal": false }
}
```
*Any item omitted or with relevance < 70 (or isReal = false) will be automatically discarded.*

Apply the filter:
```bash
python $SKILL_DIR/scripts/apply_filter.py --raw [keyword]/.cache/search_results_raw.json --ann [keyword]/.cache/annotations.json --out [keyword]/.cache/annotated_results.json --keyword "keyword"
```

### Step 4: Full-text fetch

```bash
node $SKILL_DIR/scripts/fetch_content.mjs --in [keyword]/.cache/annotated_results.json --out [keyword]/.cache/enriched.json
```

### Step 5: Report results

Present top results in structured format to the user:

```markdown
## 🔥 harvest 报告 — {keyword}
> 扫描时间: {timestamp} | 数据源: {sources_used} | 收录: {count} 篇

### 🚨 Urgent / 🔴 High
- **{title}** — {summary}
  来源: {source} | 相关性: {relevance}% | [链接]({url})
```

**Final output**: `[keyword]/.cache/enriched.json`

Suggest to the user: *"数据已就绪，是否要运行 `prism` 技能将内容整理到知识库？"*

## Script Reference

| Script | Sources | Key Options |
|--------|---------|-------------|
| `search_web.py` | Bing, DuckDuckGo, HackerNews | `--sources`, `--limit`, `--out` |
| `search_china.py` | Sogou, Bilibili, Weibo, Juejin | `--sources`, `--limit`, `--out`, `--detect-account` |
| `search_twitter.py` | Twitter/X | `--limit`, `--out`, `--trends`, `--user` |
| `apply_filter.py` | — | `--raw`, `--ann`, `--out`, `--keyword` |
| `fetch_content.mjs` | Web (via Defuddle) | `--in`, `--out`, `--min-relevance`, `--concurrency` |

## Notes

- **Bilibili & Weibo**: No full-text extractor. Saved as snippets only (still valuable for trend detection).
- **YouTube**: Defuddle automatically extracts subtitles/transcripts.
- **Rate limits**: search scripts enforce delays between requests automatically.
- **`--limit N`**: limits results **per source**, not total. E.g., `--sources bing,hackernews --limit 15` yields up to 30 results.
- **This skill does NOT write to any wiki structure.** It only produces `.cache/enriched.json`. Use the `prism` skill to ingest into a knowledge base.

## References

- [analysis-guide.md](references/analysis-guide.md) — Scoring criteria for isReal, relevance, importance
- [search-sources.md](references/search-sources.md) — Per-source details, limits, quirks
