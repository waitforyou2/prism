---
name: router
description: >
  Smart knowledge base router — scan workspace, route user questions to the right
  knowledge base(s), and answer via SubAgent isolation with WIKI.md constitution driving retrieval.
  Use when users ask questions at the workspace root level, across multiple knowledge bases,
  "问一下XX", "在知识库里查一下", "XX和XX有什么区别", "查一查XX",
  or any question that could be answered from existing knowledge bases.
---

# router — 智能知识库路由技能

This skill operates at the **workspace level** (a directory containing multiple knowledge bases).
It discovers available KBs, routes the question, and dispatches SubAgents into each matching KB.

> **核心原则**：Router 只负责"找到对的书架"。读书和回答由每个 KB 自己的 WIKI.md 宪法完成。
> SubAgent 进入 KB 目录后，直接读取 WIKI.md 宪法并按其 Query 操作模式执行——无需调用任何 skill。

---

## Phase 0: Environment Setup (MUST DO FIRST)

Derive the skill root from this file's location:

```
SKILL_DIR = <directory containing this SKILL.md file>
```

Confirm the user's CWD — this is the **workspace root** (the directory containing multiple KB subdirectories).

---

## Phase 1: Discover Knowledge Bases

Run the discovery script to find all knowledge bases in the workspace and (re)build the registry:

```bash
python $SKILL_DIR/scripts/discover.py \
  --workspace . \
  --out .prism/registry.json \
  --verbose
```

Read the output registry at `.prism/registry.json`.

**If `knowledgeBases` is empty:**
> 📭 当前工作区没有找到任何知识库。
> 请先在某个主题子目录中运行 `harvest` + `prism` 技能建立知识库，然后再使用 router。

---

## Phase 2: Routing Decision

Run the routing script to match the user's question against the registry:

```bash
python $SKILL_DIR/scripts/route.py \
  --question "[用户问题]" \
  --registry .prism/registry.json \
  --verbose
```

Read the JSON output. The `strategy` field determines next steps:

```
strategy = "single_kb"  → one KB matched      → Phase 3A
strategy = "multi_kb"   → multiple KBs matched → Phase 3B
strategy = "no_match"   → no KB matched        → Phase 3C
```

---

## Phase 3A: Single KB — SubAgent Dispatch

One knowledge base matched. Construct a SubAgent prompt using the template at
`$SKILL_DIR/references/subagent_prompt.md`, filling in:

- `{kb_id}` — the matched KB's id
- `{wiki_abs_path}` — absolute path to the KB's wiki directory
- `{wiki_md_content}` — full text of `[wiki_abs_path]/WIKI.md`
- `{index_md_content}` — full text of `[wiki_abs_path]/index.md`
- `{question}` — the user's original question

Dispatch the SubAgent. The SubAgent will:
1. Read WIKI.md (its constitution — Query mode is fully defined there)
2. Read index.md to locate relevant pages
3. Read relevant page files
4. Return a structured answer

**After receiving the SubAgent result:**
- Present the answer to the user
- Append a log entry to `[wiki_abs_path]/log.md`:
  ```markdown
  ## [YYYY-MM-DD] route_query | "[用户问题]"
  路由策略: single_kb | 匹配: {kb_id} ({confidence})
  回答引用: {sources list}
  ```

---

## Phase 3B: Multi-KB — Parallel SubAgent Dispatch

Multiple knowledge bases matched. For each matched KB:

1. Construct a SubAgent prompt (same as Phase 3A)
2. Dispatch SubAgents (in parallel if the platform supports it; otherwise serially)
3. Collect all structured results

**After collecting all SubAgent results:**

Synthesize a unified answer:
- Group information by topic/claim, not by KB
- Label each piece with its source KB: `[[Page Title@kb_id]]`
- If multiple KBs agree on a claim → present as established fact
- If KBs disagree → highlight: `⚠️ 分歧: [kb_a] 称...，[kb_b] 称...`
- If a KB returned `confidence: low` → note that its data may be outdated

Append log entries to each involved KB's `log.md`:
```markdown
## [YYYY-MM-DD] route_query | "[用户问题]"
路由策略: multi_kb | 匹配: {kb_id_1} ({conf_1}), {kb_id_2} ({conf_2})
回答引用: [[Page A@kb_1]], [[Page B@kb_2]]
```

---

## Phase 3C: No Match

No knowledge base covers this topic. Respond to the user:

> 🔍 当前知识库中没有找到与 **"[用户问题]"** 相关的内容。
>
> 建议运行 `harvest` 技能搜索相关内容，例如：
> "帮我搜索 [主题关键词] 相关热点"
>
> 已有知识库：
> {列出 registry 中所有 KB 的 id 和 description}

---

## SubAgent Prompt Template

See `$SKILL_DIR/references/subagent_prompt.md` for the full template.

Key principle: **the SubAgent reads WIKI.md and lets the constitution drive everything**.
Do not inject additional instructions that override the constitution.

---

## Script Reference

| Script | Purpose | Key Options |
|--------|---------|-------------|
| `discover.py` | Scan workspace, build registry.json | `--workspace`, `--out`, `--verbose` |
| `route.py` | Match question to KB(s) | `--question`, `--registry`, `--verbose` |

## Notes

- **Platform adaptation**: If the AI platform supports parallel SubAgent dispatch (e.g., Claude Code `Task` tool), use it for `multi_kb`. Otherwise, dispatch serially — the end result is the same, only speed differs.
- **Registry freshness**: The registry is rebuilt on every router invocation (Phase 1), so it always reflects the current state of the workspace. No stale cache issues.
- **Single-KB shortcut**: If the user is already inside a KB directory (`claude/`) and asks a question, they don't need the router — the WIKI.md constitution handles it directly. Router is only needed at the **workspace root level**.
