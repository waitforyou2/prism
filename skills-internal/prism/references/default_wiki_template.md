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
├── log.md                 操作日志：按时间记录事件
├── raw/                   原始文档（只读）
│   ├── _index.json        元数据索引
│   └── {YYYYMMDD}/{keyword}/
│       ├── {src}_{hash}.md         全文 + frontmatter
│       └── {src}_{hash}.meta.json  元数据侧车
├── pages/                 编译后的 Wiki 页面
│   ├── overview/          概览页（可包含多个维度，如：整体介绍视角、技术架构视角、用户手册视角等）
│   ├── concepts/          概念页（技术范式、方法论、抽象思想）
│   ├── entities/          实体页（人物、工具、公司、产品）
│   └── syntheses/         综合分析页（跨来源趋势判断、深度对比分析）
└── signals/               低质量碎片
```

---

## 操作模式

### 1. Compile（深度编译与原子化提取）

扫描 `raw/` 下所有 `.meta.json` 文件，找到 `"compiled": false` 的文档。

**对每个尚未编译的文档，你必须执行以下深度提取流程：**

1. **阅读全文**：理解文档的核心论点、提到的每一个具体工具(Entity)和技术名词(Concept)。
2. **主动拆解**：**严禁仅做全文总结**。你必须基于文档内容，识别出其中涉及的所有独立实体和概念。
3. **原子化写入**：
   - 对于文档中提到的每个重要 **实体**：在 `pages/entities/` 中创建或更新对应页面。
   - 对于文档中提到的每个重要 **概念**：在 `pages/concepts/` 中创建或更新对应页面。
   - 对于文档的整体价值：如果文档是综述性或具有极高引导价值，更新 `pages/overview/` 中的相关页面。
4. **强链接与高密度引用**：
   - 在新创建的内容中，使用 `[[Page Title]]` 将相关的实体与概念互相链接。
   - **充分利用 Data Pool**：不仅引用核心文档，还应主动搜索 `raw/` 中其他提及该知识点的文档。
   - **必须**在"关键来源"章节引用文档对应的本地 raw 路径，格式为 `[[raw/YYYYMMDD/filename.md]]`。
5. **更新进度**：更新 `.meta.json` 中的 `compiled: true` 并记录日志。

### 2. Query（检索回答）

1. 优先查阅 `pages/overview/` 了解全局，再通过 `[[ ]]` 链接跳转到细节页面。
2. 回答中引用的所有知识点必须以 `[[Page Title]]` 呈现。

---

## 页面格式规范

### Overview 页（`pages/overview/{Topic}_{Perspective}.md`）
*根据 Data Pool 的深度，可以从不同维度创建概览。例如：全景概览、技术深度概览、社区评价概览等。*

```markdown
---
type: overview
title: "{Topic} {Perspective} 概览"
tags: [overview, main]
created: YYYYMMDD
updated: YYYYMMDD
---

# {Topic} {Perspective} 概览

## 简介
[对该知识库主题的宏观定义]

## 知识图谱入口
- **核心实体**: [[Entity A]], [[Entity B]]
- **关键概念**: [[Concept A]], [[Concept B]]

## 核心内容与多维总结
[基于 raw 数据总结的当前状态、核心功能、技术亮点、或社区反馈。请保持高度的知识密度，尽可能整合所有已入库的相关 raw 资料。]

## 关键来源
- [[raw/YYYYMMDD/src_hash.md]] — {描述该文档对概览的贡献}
- [[raw/YYYYMMDD/other_src.md]] — {补充信息说明}
```

### Concept 页（`pages/concepts/{Topic}.md`）

```markdown
---
type: concept
title: "Topic Name"
aliases: ["别名1"]
tags: [tag1]
sources: N
created: YYYYMMDD
updated: YYYYMMDD
---

# Topic Name

## 定义与核心思想
[描述其原理，必须引用 [[Related Entity]] 或 [[Related Concept]]]

## 关键来源
- [[raw/YYYYMMDD/src_hash.md]] — 核心定义来源
```

### Entity 页（`pages/entities/{Name}.md`）

```markdown
---
type: entity
entity_type: person | tool | company | product
title: "Entity Name"
tags: [tag1]
sources: N
created: YYYYMMDD
updated: YYYYMMDD
---

# Entity Name

## 概述
[简短介绍]

## 核心特性
- 应用了 [[Concept A]]
- 属于 [[Entity B]] 的产品线

## 关键来源
- [[raw/YYYYMMDD/src_hash.md]] — 详细技术规格见此处
```

---

## 写作规则（铁律）

1. **禁止外部链接**：在“关键来源”章节，**严禁引用 http/https URL**。必须引用本地路径 `[[raw/YYYYMMDD/source_file.md]]`。
2. **充分收割 (Crystallization)**：如果 raw 文档提到了一个新的工具或观点，即使不是当前文档的主角，也应在对应页面追加信息，确保 raw 文档的价值被榨干。
3. **高密度多维概览**：Overview 页面不应只是简介，应作为该库的“最强综述”。当知识面很广时，应拆分为不同视角的多个 Overview（如 `openclaw_architecture` vs `openclaw_user_feedback`）。
4. **日期格式**：所有 frontmatter 和路径中的日期统一使用 `YYYYMMDD` 格式。
5. **双向链接**：创建页面时必须考虑“它属于谁”和“谁属于它”，通过双链构建网络。
