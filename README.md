# Prism

> Prism takes raw web signals and refracts them into structured, persistent knowledge.

## What it does

**Two skills, one knowledge base:**

```
harvest skill                    prism skill
(Search + Full-text Fetch)       (AI Wiki Organization)
         ↓                                ↑
      wiki/raw/   ──────────────→  wiki/pages/
   (Raw Articles)                (Structured Knowledge)
```

## Quick Start

### 1. Install dependencies

```bash
# Python deps (for search scripts)
pip install requests beautifulsoup4

# Node.js deps (for Defuddle content extraction)
npm install
```

### 2. Use the harvest skill

Ask your AI assistant (Cursor, Claude Code, Antigravity) to:
> "harvest harness engineering"
> "搜一下 LLM Wiki 相关内容"

The skill will search 8+ sources, filter by relevance, fetch full content via Defuddle, and save to `wiki/raw/`.

### 3. Use the prism skill

Ask your AI assistant to:
> "prism"
> "整理 wiki"
> "organize new raw content"

The skill scans `wiki/raw/` for unprocessed files and organizes them into `wiki/pages/`.

## Directory Structure

```
prism/
  skills/
    harvest/    Search + Defuddle content fetching → wiki/raw/
    prism/      AI wiki organization → wiki/pages/
  wiki/
    raw/        Raw full-text articles (written by harvest)
    pages/      Structured wiki pages (written by prism)
    CLAUDE.md   AI maintenance instructions
```

## Tech Stack

- **Search**: Python (requests + beautifulsoup4) — Bing, HackerNews, Sogou, Bilibili, Weibo, Twitter
- **Content Extraction**: Node.js + [Defuddle](https://github.com/kepano/defuddle) — supports YouTube transcripts
- **Knowledge Base**: Plain Markdown files with YAML frontmatter + wikilinks
