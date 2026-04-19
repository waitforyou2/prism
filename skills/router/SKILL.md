---
name: router
description: >
  Smart knowledge base router — scan workspace, route user questions to the right
  knowledge base(s), and answer via SubAgent isolation with WIKI.md constitution driving retrieval.
  Use when users ask questions at the workspace root level, across multiple knowledge bases,
  "问一下XX", "在知识库里查一下", "XX和XX有什么区别", "查一查XX",
  or any question that could be answered from existing knowledge bases.
---

# router — 智能知识库路由技能 v2.1

This skill operates at the **workspace level** (a directory containing multiple knowledge bases).
It discovers available KBs, routes the question, and dispatches SubAgents into each matching KB.

> **核心原则**：Router 只负责"找到对的书架"。读书和回答由每个 KB 自己的 WIKI.md 宪法完成。
> SubAgent 进入 KB 目录后，直接读取 WIKI.md 宪法并按其 Query 操作模式执行——无需调用任何 skill。

> **v2.1 架构**：Agent 前置语义扩充 + 纯本地 BM25 打分。零 API 网络开销。

---

## Phase 0: Environment Setup (MUST DO FIRST)

Derive the skill root from this file's location:

```
SKILL_DIR = <directory containing this SKILL.md file>
```

Confirm the user's CWD — this is the **workspace root** (the directory containing multiple KB subdirectories).

---

## Phase 1: Discover Knowledge Bases

Run the discovery script to build/refresh the registry (includes BM25 corpus for each KB):

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

## Phase 2: Agent Query Expansion (YOU, the Agent, must do this)

**Before calling route.py, you MUST expand the user's raw question.**

This is the most critical step. The BM25 engine is a pure text matcher — it cannot understand semantics. YOU are the semantic layer.

**Expansion rules:**

1. **Extract core intent**: What is the user really asking about?
2. **Add synonyms**: Both Chinese and English
3. **Add domain terms**: Technical terminology related to the question
4. **Add proper nouns**: Product names, company names, person names
5. **Flatten to a space-separated string**

**Examples:**

| User's raw question | Your expanded query |
|---------------------|-------------------|
| "AI编程工具的最新趋势？" | `AI编程 编程工具 coding tools agentic programming claude codex cursor agent 自动化 代码` |
| "Claude Code 怎么用？" | `claude claude-code anthropic AI编程 agentic coding CLI terminal 命令行` |
| "Codex 和 Claude 哪个好？" | `codex claude comparison 对比 openai anthropic code generation 代码生成 AI编程` |
| "最近有什么新产品发布？" | `新产品 product release launch 发布 更新 update 工具 tool announcement` |

**The richer and more precise your expansion, the better the routing accuracy.**

---

## Phase 3: Route

Call the routing script with your expanded query:

```bash
python $SKILL_DIR/scripts/route.py \
  --query "<your expanded query string>" \
  --registry .prism/registry.json \
  --out .prism/route_result.json \
  --verbose
```

Read `.prism/route_result.json`. The `strategy` field determines next steps:

```
strategy = "single_kb"  → one KB matched      → Phase 4A
strategy = "multi_kb"   → multiple KBs matched → Phase 4B
strategy = "no_match"   → no KB matched        → Phase 4C
```

---

## Phase 4A: Single KB — SubAgent Dispatch

One knowledge base matched. Construct a SubAgent prompt using the template at
`$SKILL_DIR/references/subagent_prompt.md`, filling in:

- `{kb_id}` — the matched KB's id
- `{wiki_abs_path}` — absolute path to the KB's wiki directory
- `{const_filename}` — the constitution filename (e.g., `WIKI.md`, `CLAUDE.md`) from registry
- `{const_content}` — full text of `[wiki_abs_path]/{const_filename}`
- `{index_md_content}` — full text of `[wiki_abs_path]/index.md`
- `{question}` — the user's **original** question (NOT the expanded query)

Dispatch the SubAgent. The SubAgent will:
1. Read the constitution document (e.g., `WIKI.md` or `CLAUDE.md`) to understand its Query mode.
2. Read index.md to locate initial candidate pages (Overviews, Entities, Concepts).
3. **Recursive Exploration**: Read candidate files and proactively follow internal `[[Wiki Links]]` to pivot or drill down into related details.
4. Return a structured answer with high source density.

**After receiving the SubAgent result:**
- Present the answer to the user
- Append a log entry to `[wiki_abs_path]/log.md` (or the operational log specified in the constitution):
  ```markdown
  ## [YYYY-MM-DD] route_query | "[用户原始问题]"
  路由策略: single_kb | 匹配: {kb_id} (score={score})
  回答引用: {sources list}
  ```

---

## Phase 4B: Multi-KB — Parallel SubAgent Dispatch

Multiple knowledge bases matched. For each matched KB:

1. Construct a SubAgent prompt (same as Phase 4A)
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
## [YYYY-MM-DD] route_query | "[用户原始问题]"
路由策略: multi_kb | 匹配: {kb_id_1} (score={s1}), {kb_id_2} (score={s2})
回答引用: [[Page A@kb_1]], [[Page B@kb_2]]
```

---

## Phase 4C: No Match

No knowledge base covers this topic. Respond to the user:

> 🔍 当前知识库中没有找到与 **"[用户原始问题]"** 相关的内容。
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
| `discover.py` | Scan workspace, build registry.json (with BM25 corpus) | `--workspace`, `--out`, `--verbose` |
| `route.py` | BM25 scoring against Agent-expanded query | `--query`, `--registry`, `--out`, `--verbose` |

## Architecture Notes

- **Agent = Semantic Layer**: The Agent running this skill IS the language understanding component. It expands the query for free (no extra API call — it's already thinking).
- **route.py = Scoring Layer**: Pure math. BM25Okapi with character bigrams for Chinese, word tokens for English. Inlined implementation, zero pip dependency.
- **Fast-path**: If a KB id appears as a substring in the expanded query, route.py short-circuits BM25 and returns immediately (single-KB case).
- **Platform adaptation**: If the AI platform supports parallel SubAgent dispatch, use it for `multi_kb`. Otherwise, dispatch serially.
- **Registry freshness**: The registry is rebuilt on every router invocation (Phase 1), so it always reflects the current state of the workspace.
- **Single-KB shortcut**: If the user is already inside a KB directory, they don't need the router — the WIKI.md constitution handles it directly.
