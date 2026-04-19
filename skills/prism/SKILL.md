---
name: prism
description: >
  Organize raw harvested content into structured Prism Wiki pages.
  Use when users ask to: organize wiki, process new content, update knowledge base,
  "整理 wiki", "更新知识库", "把最近抓的内容整理一下", "prism", "process raw layer",
  "organize new raw content", "build wiki pages", "知识整理", or after running the
  harvest skill and wanting to convert raw articles into structured knowledge.
---

# prism — Prism Wiki 整理技能

Read `wiki/raw/` unprocessed files, organize them into structured `wiki/pages/` following `wiki/CLAUDE.md`.

## Dependencies

```bash
# No extra dependencies — uses Python standard library only
python skills/prism/scripts/scan_raw.py  # should work immediately
```

## Core Workflow

### Phase 1: Environment Bootstrapping (Initialization)

Always check if `wiki/CLAUDE.md` exists in the workspace before starting.

**If `wiki/CLAUDE.md` does NOT exist:**
1. Determine that the knowledge base needs initialization.
2. Create the raw and pages directories: `wiki/raw/` and `wiki/pages/`.
3. Create `wiki/CLAUDE.md` by copying the exact system instructions found in `skills/prism/references/default_claude_template.md`.
4. Create a welcoming basic page `wiki/pages/concepts/Prism Wiki.md` introducing the initialized knowledge base.
5. Notify the user briefly about the initialization completion.
6. **Immediately PROCEED to Phase 2** to process any pending items.

**If `wiki/CLAUDE.md` DOES exist:**
Proceed directly to Phase 2.

### Phase 2: Crystallization (Data Processing)

### Step 1: Scan for unprocessed files

```bash
python skills/prism/scripts/scan_raw.py
```

This outputs a prioritized Markdown list of all unprocessed raw files, sorted by importance → relevance.

Read this output carefully to understand what's waiting to be organized.

### Step 2: Read each raw file

For each unprocessed file listed (start with Urgent and High importance):

1. Read the full `.md` file at the given path
2. Note the frontmatter: `keyword`, `relevance`, `importance`, `isReal`, `summary`
3. Read the full `fullContent` body

### Step 3: Decide how to organize

For each raw file, decide:

**Check existing pages first:**
- Look at `wiki/pages/` directory
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

### Step 4: Write or update wiki/pages/

Follow all conventions in `wiki/CLAUDE.md`:

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
python skills/prism/scripts/update_index.py
```

This regenerates `wiki/pages/_index.md` with all current pages.

## Reference Files

- [wiki/CLAUDE.md](../../wiki/CLAUDE.md) — **PRIMARY REFERENCE**: page formats, operation rules, tags
- [references/wiki-schema.md](references/wiki-schema.md) — Extended page templates
- [references/category-guide.md](references/category-guide.md) — When to use each category

## Script Reference

| Script | Purpose |
|--------|---------|
| `scan_raw.py` | List unprocessed files from `wiki/raw/_index.json`, sorted by priority |
| `update_index.py` | Rebuild `wiki/pages/_index.md` from existing page files |
