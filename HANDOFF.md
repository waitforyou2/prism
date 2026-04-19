# Prism Knowledge System - Project Handoff & Status

**更新时间：** 2026-04-19
**项目定位：** Prism 是一套 Agentic AI 辅助的自动化知识管理与萃取系统。核心流水线：`全网热点监听 (Harvest) → 智能过滤标注 → 全文抓取 (Defuddle) → AI 知识结晶化 (Prism)` 。

---

## ✅ 当前架构状态（2026-04-19 最新）

### 核心设计原则（本次会话完成）

1. **职责单一**：`harvest` = 纯数据猎人（终止于 `.cache/enriched.json`）；`prism` = 知识库全权管家（从入库到编译到索引）。
2. **完全可移植**：技能包 `skills/` 可放置于任何目录（如 `~/.claude/skills/` 或 `~/.gemini/skills/`），通过 `$SKILL_DIR` 自动定位脚本；用户产出物基于 `CWD`，完全隔离。
3. **分形知识库架构**：每个热点主题独立一个目录 `[keyword]/`，下含 `.cache/`（harvest 临时数据）和 `wiki/`（知识库），互不干扰。
4. **宪法驱动**：`SKILL.md` 只是引导程序（Bootloader），所有知识整理决策由各知识库自己的 `WIKI.md` 宪法驱动。

### 目录结构（标准）

```
~/knowledge/              ← 用户的通用工作区（可任意命名）
  └── claude/             ← 某个主题的知识库（由 prism 初始化）
       ├── .cache/         ← harvest 的临时数据（enriched.json, .ingested 等）
       └── wiki/           ← 知识库（prism 完全所有）
            ├── WIKI.md                   宪法（格式规范、操作规则）
            ├── index.md                  内容目录（按分类列出所有 pages）
            ├── log.md                    操作日志（append-only 时间线）
            ├── raw/{date}/{keyword}/     原始文档层（只读）
            │    ├── {title-slug}_{hash}.md
            │    └── {title-slug}_{hash}.meta.json   含 "compiled": false/true
            ├── pages/concepts/           编译后的 Wiki 页面
            ├── pages/entities/
            ├── pages/syntheses/
            └── signals/                  低质量碎片（摘要、片段）
```

### 技能包结构

```
skills/
  harvest/
    SKILL.md                  引导程序：Phase 0 路径解析 → 搜索 → 过滤 → 抓取全文 → 输出 enriched.json
    .gitignore                屏蔽 node_modules/
    references/
      analysis-guide.md       AI 评分标准（isReal, relevance, importance）
      search-sources.md       各数据源说明、限制、注意事项
    scripts/
      search_web.py           搜索：Bing, HackerNews, GitHub, YouTube（--out 文件）
      search_china.py         搜索：Sogou, Bilibili, Weibo, Juejin（--out 文件）
      search_twitter.py       搜索：Twitter/X（可选，需 API Key）
      apply_filter.py         AI 标注过滤器（--raw --ann --out）
      fetch_content.mjs       Defuddle 全文抓取（.mjs 无需 package.json）

  prism/
    SKILL.md                  引导程序：Phase 0→1→2→3（不做编辑决策，读完宪法立即执行）
    references/
      default_wiki_template.md  宪法模板（初始化知识库时复制）
    scripts/
      save_to_raw.py          入库：enriched.json → wiki/raw/（文件名=title-slug_hash）
      scan_raw.py             扫描：列出所有 compiled:false 的文档
      update_index.py         重建：wiki/pages/_index.md（支持 --wiki-dir）
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

---

## ⚠️ 关键避坑指南

1. **PowerShell 管道之坑**：不允许使用 `<` `|` `>` 做 JSON 重定向。所有脚本均已升级为 `--in`/`--out` 文件参数，无需任何 shell 重定向。
2. **`$SKILL_DIR` 的推导**：AI 在读到 SKILL.md 时，必须用该文件的绝对路径推导 `$SKILL_DIR`，不得硬编码任何路径。
3. **知乎防御**：知乎使用 `x-zse-96` 签名防御，当前战术放弃，需 Playwright 才能突破。
4. **搜狗跳转链接**：`sogou.com/link` 强跳微信公众号链接，抓取失败自动降级入 signals 层。
5. **`--limit N`**：每个 source 独立限制，`--sources bing,hackernews --limit 15` = 最多 30 条。

---

## 🎯 下一阶段可探索方向

- **Lint 模式**：定期健康检查 wiki（矛盾页面、孤立页面、缺失交叉引用）
- **Obsidian 集成**：wiki 本身已是 Obsidian 兼容的 Markdown 文件夹，可直接打开使用图谱视图
- **多知识库联动**：不同主题的 wiki 未来可以相互引用（`[[Topic@claude]]` 语法扩展）
- **CLI 工具**：类似 `qmd` 的本地搜索引擎（BM25/向量混合），供知识库增长后的检索使用
