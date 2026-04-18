# Prism Wiki — AI 维护手册

你是 **Prism Wiki** 的知识整理者。  
你的职责是将 `wiki/raw/` 层的原始抓取内容，整理成 `wiki/pages/` 中结构化、互联的知识页面。

---

## 目录结构

```
wiki/
  raw/              原始抓取内容（只读）
    _index.json     所有 raw 文件的元数据索引
    {date}/
      {keyword}/
        {source}_{hash}.md        含 frontmatter 的全文
        {source}_{hash}.meta.json 元数据（无正文）

  pages/            整理后的 wiki 页面（你写这里）
    concepts/       概念页  → Harness Engineering.md
    entities/       实体页  → Karpathy.md, Defuddle.md
    syntheses/      综合分析页 → ai-engineering-2026-04.md
    _index.md       目录总览（由 update_index.py 自动生成）

  CLAUDE.md         本文件
```

---

## 页面格式规范

### Concept 页（`pages/concepts/{Topic}.md`）

概念：技术范式、方法论、抽象思想（如 Harness Engineering、RAG、MCP）。

```markdown
---
type: concept
title: "Harness Engineering"
aliases: ["Agent Harness", "马鞍工程", "脚手架工程"]
tags: [ai-engineering, agent, production-ai]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Harness Engineering

## 定义

[一句话核心定义]

## 核心思想

[2-4段，描述核心原理]

## 与其他概念的关系

- 是 [[Prompt Engineering]] 之后的演进
- 应用于 [[AI Agent]] 的生产部署
- 与 [[Context Engineering]] 并列为 AI 工程三代范式

## 重要进展

[按时间倒序，记录关键事件]
- 2026-02: HarnessEngineering 从个人博客演变为行业共识 [来源](url)

## 关键来源

- [标题](url) — 贡献了什么具体信息

## 变更记录

- YYYY-MM-DD: 初始建立，整合 N 篇来源
```

---

### Entity 页（`pages/entities/{Name}.md`）

实体：具体存在的人物、工具、公司、产品（如 Karpathy、Defuddle、Anthropic）。

```markdown
---
type: entity
entity_type: person | tool | company | product
title: "Defuddle"
tags: [web-scraping, nodejs, content-extraction]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Defuddle

## 概述

[简短介绍：是什么、做什么、谁创建的]

## 核心特性

[关键功能列表]

## 与 Prism 的关联

[为什么出现在这个 wiki 里]

## 参考链接

- [GitHub](https://github.com/kepano/defuddle)

## 变更记录

- YYYY-MM-DD: 初始建立
```

---

### Synthesis 页（`pages/syntheses/{topic}-{YYYY-MM}.md`）

综合分析：跨多来源、多时间段的趋势判断和深度分析。仅在有足够素材时建立。

```markdown
---
type: synthesis
title: "AI 工程三代范式演进 — 2026-04"
keywords: [prompt-engineering, context-engineering, harness-engineering]
tags: [ai-engineering, trend-analysis]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# AI 工程三代范式演进

## 核心趋势

## 证据汇总

## 结论

## 来源

## 变更记录
```

---

## 操作规则

### 写之前必读

1. **先读 `scan_raw.py` 输出**，了解有哪些未处理文件及其重要性排序
2. **先检查 `pages/` 目录**，确认是否已有同主题页面再决定创建还是更新

### 写作规则

3. **不修改 `raw/`**：raw 层只读，只在 `.meta.json` 中标记 `processed: true`
4. **追加不覆盖**：更新现有页面时在对应小节末尾追加，不删除历史内容  
   信息冲突时加注：`> ⚠️ 存疑 (YYYY-MM-DD): 新来源说...`
5. **链接规范**：正文中提及其他 wiki 页面时使用 `[[Page Title]]` 格式
6. **来源透明**：每段新增信息都要在"关键来源"或"重要进展"小节中引用来源 URL

### 建立新页面的门槛

7. 满足以下任一条件才建新页面：
   - `importance = urgent` 或 `high`
   - `relevance ≥ 80` 且内容足够（wordCount ≥ 200）
   - 多个来源同时提及同一概念/实体
8. 不满足门槛的内容：追加到相关已有页面的"重要进展"或"关键来源"即可

### 处理完成后

9. **标记已处理**：在对应 `.meta.json` 文件中设置：
   ```json
   "processed": true,
   "processedAt": "YYYY-MM-DDT00:00:00Z"
   ```
10. **更新时间戳**：修改页面后更新 frontmatter 的 `updated` 字段
11. **运行索引更新**：处理完所有文件后执行：
    ```bash
    python skills/prism/scripts/update_index.py
    ```

---

## Tag 参考

| 领域 Tag | 说明 |
|----------|------|
| `ai-engineering` | AI 工程方法论（Prompt/Context/Harness Engineering）|
| `agent` | AI Agent 相关 |
| `production-ai` | 生产环境 AI 部署 |
| `llm` | 大语言模型 |
| `devops` | 软件交付、CI/CD |
| `knowledge-management` | 知识管理工具和方法 |
| `web-scraping` | 网页内容提取 |
| `nodejs` / `python` | 技术栈 |
| `trend-analysis` | 趋势分析类内容 |
