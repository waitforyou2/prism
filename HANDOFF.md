# Prism Knowledge System - Project Handoff & Status

**更新时间：** 2026-04-19
**项目定位：** Prism 是一套 Agentic AI 辅助的自动化知识管理与萃取系统。核心流水线：`全网热点监听 (Harvest) → 智能过滤标注 → 全文抓取 (Defuddle) → AI 知识结晶化 (Prism)` 。支持多知识库工作区的智能路由问答 (Router)。

---

## ✅ 当前架构状态（2026-04-19 最新）

### 核心设计原则

1. **职责单一**：`harvest` = 纯数据猎人（终止于 `.cache/enriched.json`）；`prism` = 知识库全权管家（从入库到编译到索引）；`router` = 工作区级别前台（跨库路由问答）。
2. **完全可移植**：技能包 `skills/` 可放置于任何目录，通过 `$SKILL_DIR` 自动定位脚本；用户产出物基于 `CWD`，完全隔离。
3. **分形知识库架构**：每个热点主题独立一个目录 `[keyword]/`，下含 `.cache/`（harvest 临时数据）和 `wiki/`（知识库），互不干扰。
4. **宪法驱动**：`SKILL.md` 只是引导程序（Bootloader），所有知识整理决策由各知识库自己的 `WIKI.md` 宪法驱动。**单库问答无需任何 skill，直接由 WIKI.md 宪法接管。**
5. **SubAgent 隔离**：Router 派发的 SubAgent 进入各知识库目录，WIKI.md 宪法自动驱动检索，上下文完全隔离。

### 心智模型（三 Skill 分工）

| 场景 | 机制 |
|------|------|
| 搜集原材料 | `harvest` skill |
| 编译知识库 | `prism` skill |
| **单库问答** | **直接打开知识库目录，WIKI.md 宪法自动驱动，无需任何 skill** |
| 跨库 / 根目录问答 | `router` skill → SubAgent → WIKI.md 宪法驱动检索 |

### 目录结构（标准）

```
~/knowledge/              ← 用户的通用工作区（可任意命名）
  .prism/
    registry.json         ← router 维护的知识库注册表（可再生）
  claude/                 ← 某个主题的知识库（由 prism 初始化）
    .cache/               ← harvest 的临时数据（enriched.json, .ingested 等）
    wiki/
      WIKI.md             宪法（frontmatter 含 kb_id/description/tags）
      index.md            目录（frontmatter 含 page_count/updated/tags）
      log.md              操作日志（append-only，含 route_query 记录）
      raw/{date}/{kw}/    原始文档层（只读）
      pages/concepts/     编译后的概念页
      pages/entities/     编译后的实体页
      pages/syntheses/    综合分析页
      signals/            低质量碎片
  codex/wiki/             ← 另一个知识库，同结构
  cursor/wiki/            ← 又一个知识库，同结构
```

### 技能包结构

```
skills/
  harvest/
    SKILL.md              引导程序：搜索 → 过滤 → 抓取 → enriched.json
    references/
      analysis-guide.md   AI 评分标准
      search-sources.md   各数据源说明
    scripts/
      search_web.py       Bing, HackerNews, GitHub, YouTube
      search_china.py     Bilibili, Weibo, Juejin
      search_twitter.py   Twitter/X（可选）
      apply_filter.py     AI 标注过滤器
      fetch_content.mjs   Defuddle 全文抓取

  prism/
    SKILL.md              引导程序：入库 → 编译 → 索引 → 自动注册
    references/
      default_wiki_template.md  宪法模板（含 frontmatter + 跨库引用规则）
    scripts/
      save_to_raw.py      入库：enriched.json → wiki/raw/
      scan_raw.py         扫描：列出所有 compiled:false 的文档
      update_index.py     重建：wiki/index.md（含知识库摘要 + frontmatter）

  router/
    SKILL.md              引导程序：发现 → 路由 → SubAgent → 合并
    references/
      subagent_prompt.md  SubAgent prompt 模板（宪法驱动）
      routing_guide.md    路由策略详细说明
    scripts/
      discover.py         扫描工作区，生成 .prism/registry.json
      route.py            路由决策（4 级关键词匹配，零 LLM 成本）
```

---

## 🔑 关键设计决策

| 决策 | 结论 |
|------|------|
| 节点命名 | `processed` → `compiled`（语义更准确：源码→产物的编译过程）|
| 宪法文件名 | `CLAUDE.md` → `WIKI.md`（脱离特定 AI 品牌绑定）|
| Node 依赖 | 删除 `package.json`，改用 `.mjs` 扩展名原生激活 ES Module |
| 数据源 | `--sources bing,hackernews,github,youtube`（4 个国际源全开）|
| 去重机制 | URL 级去重（跨 session） + `.ingested` hash 标记（防整批重入库）|
| 文件命名 | `{title-slug}_{8位hash}.md`（人类可读 + 防冲突）|
| Phase 3 | 强制立即执行，写明 `DO NOT STOP`，消除 AI 停下询问的歧义 |
| 单库问答 | **不经过任何 skill**，WIKI.md 宪法天然定义 Query 模式 |
| 路由算法 | 4 级关键词匹配（id+tag+topic+desc），零 LLM API 开销 |
| SubAgent 隔离 | Router 注入 WIKI.md+index.md 到 SubAgent prompt，宪法接管检索 |
| 跨库引用 | `[[Page Title@kb_id]]` 语法（已写入 WIKI.md 写作规则第 7 条）|

---

## ⚠️ 关键避坑指南

1. **PowerShell 管道之坑**：不允许使用 `<` `|` `>` 做 JSON 重定向。所有脚本均已升级为 `--in`/`--out` 文件参数，无需任何 shell 重定向。
2. **`$SKILL_DIR` 的推导**：AI 在读到 SKILL.md 时，必须用该文件的绝对路径推导 `$SKILL_DIR`，不得硬编码任何路径。
3. **知乎防御**：知乎使用 `x-zse-96` 签名防御，当前战术放弃，需 Playwright 才能突破。
4. **搜狗跳转链接**：`sogou.com/link` 强跳微信公众号链接，抓取失败自动降级入 signals 层。
5. **`--limit N`**：每个 source 独立限制，`--sources bing,hackernews --limit 15` = 最多 30 条。
6. **Router 只在工作区根目录使用**：如果用户已在具体知识库目录（如 `claude/`）内，直接对话即可，WIKI.md 宪法自动接管。

---

## 🎯 下一阶段可探索方向

- **LLM 辅助路由升级**：当知识库数量 >10 时，可在 route.py 基础上增加 LLM 语义路由（~500 tokens/次），进一步提升跨语言/同义词场景的路由精度
- **Lint 模式**：定期健康检查 wiki（矛盾页面、孤立页面、缺失交叉引用）
- **Obsidian 集成**：wiki 本身已是 Obsidian 兼容的 Markdown 文件夹，可直接打开使用图谱视图
- **多知识库联动**：`[[Topic@claude]]` 跨库引用语法已实现，Obsidian 图谱可视化待探索
- **CLI 工具**：类似 `qmd` 的本地搜索引擎（BM25/向量混合），供知识库增长后的本地检索使用
