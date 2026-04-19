---
name: prism
description: >
  Manage LLM Wiki knowledge bases — ingest harvested content and compile into structured pages.
  Use when users ask to: organize wiki, process new content, update knowledge base,
  "整理 wiki", "更新知识库", "把最近抓的内容整理一下", "prism", "process raw layer",
  "organize new raw content", "build wiki pages", "知识整理", or after running the
  harvest skill and wanting to convert raw articles into structured knowledge.
---

# prism — LLM Wiki 知识管理技能

This skill is the **bootloader** for LLM Wiki knowledge bases. It handles environment setup and data ingestion, then delegates all knowledge work to the wiki's own constitution (`WIKI.md`).

**Prism does NOT make editorial decisions.** It only:
1. Bootstraps new knowledge bases
2. Ingests harvest data into `wiki/raw/`
3. Hands control to `WIKI.md` for all compile/query/lint operations

## Phase 0: Environment Setup (MUST DO FIRST)

### 1. Locate this skill's installation directory

Since you are reading this file right now, derive the skill root:

```
SKILL_DIR = <directory containing this SKILL.md file>
```

**All script paths below use `$SKILL_DIR` as prefix.**

### 2. Confirm the user's working directory

All wiki data is read/written relative to the **user's CWD**, not `$SKILL_DIR`.

## Phase 1: Target Identification & Bootstrapping

Determine the target topic from the user's request (e.g., "organize the claude wiki" → topic = `claude`). If no specific topic is mentioned, ask the user.

```
Does [topic]/wiki/WIKI.md exist?
├── NO → Bootstrap:
│   1. Create directories: [topic]/wiki/raw/, [topic]/wiki/pages/concepts/,
│      [topic]/wiki/pages/entities/, [topic]/wiki/pages/syntheses/, [topic]/wiki/signals/
│   2. Copy $SKILL_DIR/references/default_wiki_template.md → [topic]/wiki/WIKI.md
│   3. Create empty [topic]/wiki/index.md and [topic]/wiki/log.md
│   4. Notify user: "知识库已初始化"
│   5. Proceed to Phase 2
└── YES → Proceed to Phase 2
```

## Phase 2: Incremental Ingestion (Conditional)

```
Does [topic]/.cache/ exist?
├── NO → Skip (user hasn't run harvest) → Proceed to Phase 3
└── YES → Does [topic]/.cache/enriched.json exist?
     ├── NO → Skip → Proceed to Phase 3
     └── YES → Does [topic]/.cache/.ingested exist?
          ├── YES → Read .ingested, compute sha256 of current enriched.json
          │    ├── Hash matches → Skip (already ingested) → Proceed to Phase 3
          │    └── Hash differs → Re-ingest (save_to_raw.py handles URL dedup internally)
          └── NO → First-time ingestion
```

**When ingesting:**

```bash
python $SKILL_DIR/scripts/save_to_raw.py \
  --keyword "[topic]" \
  --in [topic]/.cache/enriched.json \
  --wiki-dir [topic]/wiki
```

After successful ingestion, write `[topic]/.cache/.ingested`:
```json
{
  "ingestedAt": "YYYY-MM-DDTHH:MM:SSZ",
  "sourceHash": "<sha256 of enriched.json>",
  "itemCount": <number of items ingested>
}
```

Append to `[topic]/wiki/log.md`:
```markdown
## [YYYY-MM-DD] ingest | 入库 N 篇文档
来源: harvest | keyword: "[topic]"
```

## Phase 3: Execute Constitution (DO NOT STOP — continue immediately)

**You MUST now read and execute the constitution. Do not ask the user for permission.**

1. Read `[topic]/wiki/WIKI.md` in full
2. Run the scan to find all uncompiled documents:

```bash
python $SKILL_DIR/scripts/scan_raw.py --wiki-dir [topic]/wiki/
```

3. **If there are uncompiled documents** → immediately proceed with the **Compile** operation as defined in WIKI.md:
   - Read each uncompiled raw file
   - Decide: create new page or update existing page (follow WIKI.md decision tree)
   - Write/update pages in `[topic]/wiki/pages/`
   - Mark each `.meta.json` as `"compiled": true`
   - Append entries to `[topic]/wiki/log.md`
   - After all done, run:
     ```bash
     python $SKILL_DIR/scripts/update_index.py --wiki-dir [topic]/wiki/ --kb-id [topic]
     ```
   - Update `[topic]/wiki/index.md`
   - **Auto-register** (only if router skill is installed): infer `$ROUTER_SKILL_DIR` as a sibling of this skill's parent `skills/` directory, then run:
     ```bash
     python $ROUTER_SKILL_DIR/scripts/discover.py --workspace . --out .prism/registry.json
     ```
     If `$ROUTER_SKILL_DIR/scripts/discover.py` does not exist, skip silently.

4. **If raw/ is empty or all compiled** → the WIKI.md constitution handles Query mode directly. No action needed from this skill.

5. **If user asked for a health check** → run **Lint** as defined in WIKI.md.

> The constitution (WIKI.md) is the authoritative guide. Follow it exactly for all formatting, classification, and writing conventions.

## Script Reference

| Script | Purpose | Key Options |
|--------|---------|-------------|
| `save_to_raw.py` | Ingest enriched JSON into `wiki/raw/` and `wiki/signals/` | `--in`, `--wiki-dir`, `--keyword` |
| `scan_raw.py` | List uncompiled files from `wiki/raw/_index.json` | `--wiki-dir`, `--keyword`, `--json` |
| `update_index.py` | Rebuild `wiki/index.md` from page files | `--wiki-dir`, `--kb-id` |

