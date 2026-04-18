# Wiki Page Schema — Extended Templates

Complete page templates for all Prism Wiki page types. Use these as starting points when creating new pages.

---

## Concept Page

**File location**: `wiki/pages/concepts/{Topic Name}.md`  
**When to use**: Technical paradigms, methodologies, abstract ideas, frameworks

```markdown
---
type: concept
title: "Topic Name"
aliases: ["Alias 1", "别名", "缩写"]
tags: [primary-tag, secondary-tag]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Topic Name

## 定义

[核心定义，1-3句话。要求：精确、不含水分、可引用]

## 核心思想

[2-5段，描述核心原理和思维框架]

## 为什么重要

[在当前技术语境下的意义和价值]

## 与其他概念的关系

- 继承/演进自 [[Parent Concept]]
- 应用于 [[Related Domain]]
- 与 [[Sibling Concept]] 互补

## 主要组成部分

[如果概念有明确的子组件，列出并简述]

## 实践示例

[具体案例或代码示例，帮助理解]

## 重要进展

[按时间倒序，记录概念的发展里程碑]
- YYYY-MM-DD: [事件描述] — [来源](url)

## 关键来源

[直接支撑本页内容的来源，每条注明贡献了什么]
- [标题](url) — 提供了...的定义
- [标题](url) — 提供了...的实践案例

## 变更记录

- YYYY-MM-DD: 初始建立，整合 N 篇来源
```

---

## Entity Page — Person

**File location**: `wiki/pages/entities/{Full Name}.md`

```markdown
---
type: entity
entity_type: person
title: "Full Name"
aliases: ["Known As", "Twitter Handle"]
tags: [affiliation-tag, expertise-tag]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Full Name

## 简介

[身份、当前职位、在 AI 领域的主要贡献]

## 与 Prism 关键词的关联

[为什么这个人出现在 wiki 里，关联了哪些概念]

## 重要贡献

- [论文/博客/项目] — [对领域的影响]

## 参考链接

- Twitter/X: [handle](url)
- Blog: [url]

## 变更记录

- YYYY-MM-DD: 初始建立
```

---

## Entity Page — Tool

**File location**: `wiki/pages/entities/{Tool Name}.md`

```markdown
---
type: entity
entity_type: tool
title: "Tool Name"
aliases: ["npm-package-name"]
tags: [category-tag, language-tag]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Tool Name

## 概述

[一句话：是什么、做什么、谁创建的]

## 核心功能

- [功能 1]
- [功能 2]

## 安装与使用

```bash
# 安装
npm install -g tool-name

# 基本用法
tool-name [options]
```

## 在 Prism 中的角色

[这个工具如何被 harvest/prism skill 使用]

## 参考链接

- [GitHub](url)
- [文档](url)

## 变更记录

- YYYY-MM-DD: 初始建立
```

---

## Entity Page — Company / Organization

**File location**: `wiki/pages/entities/{Company Name}.md`

```markdown
---
type: entity
entity_type: company
title: "Company Name"
tags: [industry-tag, size-tag]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Company Name

## 概述

## 在本 wiki 关键词中的角色

## 重要动态

[按时间倒序，记录与 wiki 主题相关的公司动态]

## 关键产品 / 项目

## 参考链接

## 变更记录
```

---

## Synthesis Page

**File location**: `wiki/pages/syntheses/{topic-slug}-{YYYY-MM}.md`

```markdown
---
type: synthesis
title: "分析主题 — YYYY-MM"
keywords: [keyword-1, keyword-2]
source_count: N
tags: [trend-analysis, time-period-tag]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# 分析主题

## 核心判断

[本次分析的主要结论，3句以内]

## 证据汇总

### 支持证据

[从多个来源收集的支持结论的事实]
- [事实 1] — [来源](url)
- [事实 2] — [来源](url)

### 反驳或存疑证据

[可能挑战结论的信息]

## 趋势分析

[时间轴视角：过去 → 现在 → 预测]

## 影响范围

[这个趋势影响哪些领域/群体/工具/概念]

## 相关 wiki 页面

- [[关联概念 1]]
- [[关联实体 1]]

## 来源清单

[完整来源列表，含抓取时间]

## 变更记录

- YYYY-MM-DD: 初始建立，基于 N 篇 raw 文章
```
