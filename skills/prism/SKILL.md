---
name: prism
description: >
  Organize raw harvested content into structured Prism Wiki pages.
  Use when users ask to: organize wiki, process new content, update knowledge base,
  "整理 wiki", "更新知识库", "把最近抓的内容整理一下", "prism", "process raw layer",
  "organize new raw content", "build wiki pages", "知识整理", or after running the
  harvest skill and wanting to convert raw articles into structured knowledge.
---

# prism — Prism Wiki 知识管理技能

Ingest harvested data into `wiki/raw/`, then organize into structured `wiki/pages/` following `wiki/CLAUDE.md`.

This skill is the **sole owner** of the `wiki/` directory structure. It handles both:
- **Ingestion**: `.cache/enriched.json` → `wiki/raw/` (from harvest output)
- **Crystallization**: `wiki/raw/` → `wiki/pages/` (structured knowledge)

## Phase 0: Environment Setup (MUST DO FIRST)

### 1. Locate this skill's installation directory

Since you are reading this file right now, derive the skill root:

```
SKILL_DIR = <directory containing this SKILL.md file>
```

**All script paths below use `$SKILL_DIR` as prefix.** Replace it with the actual absolute path.

### 2. Confirm the user's working directory

All wiki data is read/written relative to the **user's CWD**, not `$SKILL_DIR`.

## Core Workflow

### Phase 1: Target Identification & Bootstrapping

Determine the target topic workspace from the user's request (e.g., "organize the claude wiki" → topic is `claude`). If no specific topic is mentioned, ask the user.

Always check if `[topic]/wiki/CLAUDE.md` exists before starting.

**If `[topic]/wiki/CLAUDE.md` does NOT exist:**
1. Create the directory structure: `[topic]/wiki/raw/`, `[topic]/wiki/pages/`, `[topic]/wiki/signals/`.
2. Create `[topic]/wiki/CLAUDE.md` by copying from `$SKILL_DIR/references/default_claude_template.md`.
3. Create a welcoming page `[topic]/wiki/pages/concepts/Prism Wiki.md`.
4. Notify the user, then **proceed to Phase 2**.

**If `[topic]/wiki/CLAUDE.md` DOES exist:**
Proceed directly to Phase 2.

### Phase 2: Ingestion (Harvest Data → wiki/raw/)

Check if `[topic]/.cache/enriched.json` exists (output from the `harvest` skill).

**If it exists and has not been ingested yet:**

```bash
python $SKILL_DIR/scripts/save_to_raw.py --keyword "[topic]" --in [topic]/.cache/enriched.json --wiki-dir [topic]/wiki
```

This routes each item to:
- `wiki/raw/` — full-text articles (fetchStatus=ok, wordCount ≥ 100)
- `wiki/signals/` — snippets, failed fetches, video references

**If no `.cache/enriched.json` exists:**
Skip to Phase 3 (process any existing unprocessed raw files).

### Phase 3: Crystallization (wiki/raw/ → wiki/pages/)

### Step 1: Scan for unprocessed files

```bash
python $SKILL_DIR/scripts/scan_raw.py --wiki-dir [topic]/wiki/
```

This outputs a prioritized Markdown list of all unprocessed raw files, sorted by importance → relevance.

### Step 2: Read each raw file

For each unprocessed file listed (start with Urgent and High importance):

1. Read the full `.md` file at the given path
2. Note the frontmatter: `keyword`, `relevance`, `importance`, `isReal`, `summary`
3. Read the full `fullContent` body

### Step 3: Decide how to organize

For each raw file, decide:

**Check existing pages first:**
- Look at `[topic]/wiki/pages/` directory
- Is there already a `concepts/` or `entities/` page about this topic?

**Decision tree:**
```
relevance ≥ 80 AND importance = high/urgent
  → worth adding to wiki
  → existing page exists? → update it
  → no existing page + wordCount ≥ 200? → create new page

relevance 50-79 OR importance = medium
  → add brief entry to related existing page only
  → don't create new standalone page

relevance < 50 OR importance = low
  → skip, just mark as processed
```

### Step 4: Write or update [topic]/wiki/pages/

Follow all conventions in `[topic]/wiki/CLAUDE.md`:

- **Page format**: Use the exact frontmatter schema from CLAUDE.md
- **Wikilinks**: Use `[[Page Title]]` when referencing other wiki pages
- **Sources section**: Always cite the raw file's URL in "关键来源" or "重要进展"
- **Append only**: When updating existing pages, add to the bottom of relevant sections

### Step 5: Mark files as processed

After processing each raw file, update its `.meta.json` sidecar:

```json
{
  "processed": true,
  "processedAt": "YYYY-MM-DDT00:00:00Z"
}
```

### Step 6: Rebuild index

After all files are processed:

```bash
python $SKILL_DIR/scripts/update_index.py --wiki-dir [topic]/wiki/
```

This regenerates `[topic]/wiki/pages/_index.md` with all current pages.

## Reference Files

- `[topic]/wiki/CLAUDE.md` — **PRIMARY REFERENCE**: page formats, operation rules, tags
- `$SKILL_DIR/references/default_claude_template.md` — Template for new knowledge bases
- `$SKILL_DIR/references/wiki-schema.md` — Extended page templates
- `$SKILL_DIR/references/category-guide.md` — When to use each category

## Script Reference

| Script | Purpose |
|--------|---------|
| `save_to_raw.py` | Ingest enriched JSON into `wiki/raw/` and `wiki/signals/` |
| `scan_raw.py` | List unprocessed files from `wiki/raw/_index.json`, sorted by priority |
| `update_index.py` | Rebuild `wiki/pages/_index.md` from existing page files |
