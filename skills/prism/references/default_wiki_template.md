---
kb_id: ""
kb_name: ""
description: ""
tags: []
created: ""
---

# LLM Wiki — 知识库宪法

你是这个知识库的 AI 维护者。
你的职责是将 `raw/` 层的原始内容**编译**成 `pages/` 中结构化、互联的知识页面，并持续维护这个不断增长的知识网络。

> **核心理念**：知识被编译一次，然后持续更新——而不是每次查询时重新推导。
> Wiki 是一个持续积累的产物。交叉引用已经建好，矛盾已经被标记，综合分析已经反映了所有已读内容。

---

## 架构：三层分离

```
raw/              原始来源（只读层）
                  来自 harvest 技能或用户手动添加的文档。
                  LLM 只读取，不修改正文。仅在 .meta.json 中标记编译状态。

pages/            编译后的 Wiki 页面（LLM 所有层）
                  LLM 创建、更新、维护交叉引用。用户阅读和浏览。

WIKI.md           本文件（Schema 层）
                  定义规范、约定、工作流。你和 LLM 共同演进。
```

---

## 目录结构

```
wiki/
├── WIKI.md                本文件
├── index.md               内容目录：按分类列出所有页面及摘要
├── log.md                 操作日志：按时间记录所有 ingest/compile/query/lint 事件
├── raw/                   原始文档（只读）
│   ├── _index.json        所有 raw 文件的元数据索引
│   └── {date}/{keyword}/
│       ├── {src}_{hash}.md         全文 + frontmatter
│       └── {src}_{hash}.meta.json  元数据侧车（含 compiled 字段）
├── pages/                 编译后的 Wiki 页面
│   ├── concepts/          概念页（技术范式、方法论、抽象思想）
│   ├── entities/          实体页（人物、工具、公司、产品）
│   └── syntheses/         综合分析页（跨来源趋势判断）
└── signals/               低质量碎片（摘要、视频引用等）
    └── _index.json
```

---

## 操作模式

### 1. Compile（编译 raw → pages）

扫描 `raw/` 下所有 `.meta.json` 文件，找到 `"compiled": false` 的文档。

**对每个未编译文档：**

1. 阅读全文内容
2. 检查 `pages/` 中是否已有同主题页面
3. 按决策树处理：

```
relevance ≥ 80 AND importance = high/urgent
  → 已有页面？ → 追加到对应章节
  → 无已有页面 + wordCount ≥ 200？ → 创建新页面

relevance 50-79 OR importance = medium
  → 仅追加到相关已有页面
  → 不创建新独立页面

relevance < 50 OR importance = low
  → 跳过，仅标记为已编译
```

4. 编译后更新 `.meta.json`：
```json
{
  "compiled": true,
  "compiledAt": "YYYY-MM-DDT00:00:00Z",
  "compiledTo": "pages/concepts/Claude Code.md"
}
```

5. 追加日志条目到 `log.md`：
```markdown
## [YYYY-MM-DD] compile | {文档标题}
编译至 [[{目标页面}]]，来源: {source} | relevance: {relevance}
```

6. 所有文档编译完成后，更新 `index.md`。

### 2. Query（检索回答）

当用户提问时：

1. 阅读 `index.md` 定位相关页面
2. 阅读对应页面内容
3. 综合多页面信息回答，使用 `[[Page Title]]` 格式引用来源页面
4. 如果回答中发现了新的有价值的分析或比较，将其保存为新的 synthesis 页面
5. 追加日志条目到 `log.md`：
```markdown
## [YYYY-MM-DD] query | "用户问题"
回答引用: [[Page A]], [[Page B]]
```

### 3. Lint（健康检查）

定期检查 wiki 健康状况：

- 页面间是否存在矛盾信息
- 是否有被更新的来源覆盖的过时声明
- 是否有孤立页面（没有入站链接）
- 是否有被多次提及但缺少独立页面的重要概念
- 是否有缺失的交叉引用

### 4. 空库引导

如果 `raw/` 下没有任何文档：

> 📭 知识库为空，建议运行 `harvest` 技能搜索相关内容，例如：
> "帮我搜索 Claude Code 相关热点"

---

## 页面格式规范

### Concept 页（`pages/concepts/{Topic}.md`）

概念：技术范式、方法论、抽象思想。

```markdown
---
type: concept
title: "Topic Name"
aliases: ["别名1", "别名2"]
tags: [tag1, tag2]
sources: 3
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Topic Name

## 定义

[一句话核心定义]

## 核心思想

[2-4段，描述核心原理]

## 与其他概念的关系

- 与 [[Other Concept]] 的联系
- 属于 [[Parent Concept]] 的子领域

## 重要进展

- YYYY-MM-DD: 事件描述 [来源](url)

## 关键来源

- [标题](url) — 贡献了什么具体信息

## 变更记录

- YYYY-MM-DD: 初始建立，整合 N 篇来源
```

---

### Entity 页（`pages/entities/{Name}.md`）

实体：具体存在的人物、工具、公司、产品。

```markdown
---
type: entity
entity_type: person | tool | company | product
title: "Entity Name"
tags: [tag1, tag2]
sources: 2
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Entity Name

## 概述

[简短介绍]

## 核心特性

[关键功能/特点列表]

## 相关概念

- 应用了 [[Related Concept]]

## 参考链接

- [官方链接](url)

## 变更记录

- YYYY-MM-DD: 初始建立
```

---

### Synthesis 页（`pages/syntheses/{topic}-{YYYY-MM}.md`）

综合分析：跨多来源的趋势判断。仅在有充足素材时建立。

```markdown
---
type: synthesis
title: "分析标题 — YYYY-MM"
tags: [tag1, trend-analysis]
sources: 5
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 分析标题

## 核心趋势

## 证据汇总

## 结论

## 来源

## 变更记录
```

---

## 写作规则

1. **不修改 raw/**：raw 层只读，仅在 `.meta.json` 中标记 `compiled: true`
2. **追加不覆盖**：更新已有页面时在对应章节末尾追加，不删除历史内容
3. **信息冲突**：加注 `> ⚠️ 存疑 (YYYY-MM-DD): 新来源称...`
4. **链接规范**：提及其他 wiki 页面时使用 `[[Page Title]]`
5. **来源透明**：每段新信息都要在"关键来源"或"重要进展"中引用 URL
6. **更新时间戳**：修改页面后更新 frontmatter 的 `updated` 和 `sources` 计数
7. **跨库引用**：引用其他知识库的页面时使用 `[[Page Title@kb_id]]` 格式
   例：`[[Codex CLI@codex]]` 表示 codex 知识库中的 Codex CLI 页面

---

## index.md 格式

```markdown
# 知识目录

> 最后更新: YYYY-MM-DD | 共 N 个页面

## 📋 知识库概述

**标签**: tag1, tag2, tag3
**覆盖主题**: Topic A, Topic B, ...

## 📐 Concepts (N)

- [[Topic]] — 一句话摘要

## 👤 Entities (N)

- [[Name]] — 一句话摘要

## 🔬 Syntheses (N)

- [[Title]] — 一句话摘要
```

## log.md 格式

```markdown
# 操作日志

## [YYYY-MM-DD] ingest | 入库 N 篇文档
来源: harvest | keyword: "claude"

## [YYYY-MM-DD] compile | Claude Code 概述
编译至 [[Claude Code]]，整合 3 篇来源

## [YYYY-MM-DD] query | "Claude Code 最新变化？"
回答引用: [[Claude Code]], [[Anthropic]]

## [YYYY-MM-DD] route_query | "Codex 和 Claude Code 哪个好？"
路由策略: multi_kb | 匹配: claude (0.95), codex (0.90)
回答引用: [[Claude Code@claude]], [[Codex CLI@codex]]
```
