# Prism Knowledge System - Project Handoff & Status

**更新时间：** 2026-04-19
**项目定位：** Prism 是一套 Agentic AI 辅助的自动化知识管理与萃取系统。核心流水线：`全网热点监听 (Harvest) → 智能过滤标注 → 全文抓取 (Defuddle) → AI 知识结晶化 (Prism)` 。支持多知识库工作区的智能路由问答 (Router)。

---

## ✅ 当前架构状态（2026-04-19 最新）

### 核心设计原则

1. **职责单一**：`harvest` = 纯数据猎人；`prism` = 知识库全权管家；`router` = 工作区级别前台。
2. **完全可移植**：技能包 `skills/` 可放置于任何目录，通过 `$SKILL_DIR` 自动定位。
3. **分形知识库架构**：每个热点主题独立一个目录，下含 `.cache/` 和 `wiki/`。
4. **宪法驱动**：所有决策由各知识库自己的 `WIKI.md` 宪法驱动。**单库问答直接由宪法接管，无需 skill。**
5. **智能探索 (Agentic Exploration)**：SubAgent 不再进行单次总结，而是具备递归检索能力，主动追踪 `[[双链]]` 以深入 Entity/Concept 细节。
6. **高密度结晶 (Rich Crystallization)**：坚持“榨干数据”原则，确保 Overview 页面反映 Data Pool 的全景。

### 心智模型（三 Skill 分工）

| 场景 | 机制 |
|------|------|
| 搜集原材料 | `harvest` skill |
| 编译知识库 | `prism` skill |
| **单库问答** | **直接打开知识库目录，WIKI.md 宪法自动驱动，无需任何 skill** |
| 跨库 / 根目录问答 | `router` v2.1 (Agent 语义扩充 + 本地 BM25) → SubAgent → 宪法驱动检索 |

### 目录结构（标准）

```
~/knowledge/              ← 用户的通用工作区
  .prism/
    registry.json         ← router 维护的注册表（含 BM25 语料库）
  claude/                 ← 某个主题的知识库
    .cache/               ← harvest 临时数据
    wiki/
      WIKI.md             宪法
      index.md            目录
      log.md              日志
      raw/                原始文档
      pages/              编译后的 Wiki 页面
  codex/wiki/             ← 另一个知识库
```

### 技能包结构

```
skills/
  harvest/
    SKILL.md              引导程序：搜索 → 过滤 → 抓取 → enriched.json
    scripts/
      search_web.py       Bing, HackerNews, GitHub, YouTube
      search_china.py     Bilibili, Weibo, Juejin
      fetch_content.mjs   全文抓取

  prism/
    SKILL.md              引导程序：入库 → 编译 → 索引 → 自动注册
    scripts/
      save_to_raw.py      入库
      scan_raw.py         扫描
      update_index.py     索引重建 (支持语义摘要)

  router/
    SKILL.md              引导程序：语义扩充契约 → BM25 打分 → SubAgent
    references/
      subagent_prompt.md  SubAgent 模板 (支持递归探索与链路追踪)
      routing_guide.md    路由策略与合并规则 (v2.1)
    scripts/
      discover.py         生成 BM25 语料
      route.py            BM25 评分引擎 (Bigram 分词, 零依赖)
```

---

## 🔑 关键设计决策

| 决策 | 结论 |
|------|------|
| 路由架构 v2.1 | **Agent 语义前置**：宿主 Agent 负责提问扩充，脚本负责纯文本 BM25 打分。 |
| 检索逻辑 | **智能探索**：SubAgent 具备 Link Discovery → Recursive Search → Synthesis 的能力。 |
| 结晶标准 | **高密度 Overview**：Overview 页面被定义为 Data Pool 的“最强综述”，支持多维度视角。 |
| 批量预审 | **Batch Intelligence**：编译前先全量扫描 metadata，建立全局视图后再下笔。 |
| 分词策略 | **混合分词**：英文单词切分 + 中文 Character Bigram（二元组），极大提升区分度。 |
| 检索算法 | **BM25Okapi**：本地化实现，零网络开销，零依赖。 |
| 节点命名 | `processed` → `compiled`（语义更准确）|
| 宪法文件名 | `WIKI.md` 为主，支持灵活识别 `CLAUDE.md`, `AGENTS.md` 等。 |
| 跨库引用 | `[[Page Title@kb_id]]` 语法 |

---

## ⚠️ 关键避坑指南

1. **PowerShell 管道之坑**：不允许使用 `<` `>` 做重定向。脚本均使用 `--in`/`--out` 参数。
2. **`$SKILL_DIR` 的推导**：通过 SKILL.md 绝对路径推导，不得硬编码。
3. **分词瓶颈**：中文单字分词 IDF 区分度极差，v2.1 已全面改用 Bigram。
4. **Router 适用范围**：仅在根目录跨库时使用。库内直接对话即可。

---

## 🎯 下一阶段可探索方向

- **Lint 模式**：定期检查 wiki 矛盾页面、孤立页面。
- **Obsidian 集成**：利用图谱视图可视化跨库引用。
- **CLI 工具**：基于 BM25 的本地极速搜索引擎。
