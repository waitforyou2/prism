# Category & Tag Guide

Decision rules for categorizing content and assigning tags in Prism Wiki.

---

## Page Type Decision Tree

```
新内容是关于...

├── 抽象思想 / 方法论 / 技术范式
│   → concepts/
│   示例: Harness Engineering, RAG, MCP, Context Engineering
│
├── 具体存在的事物
│   ├── 人物 (person)      → entities/  entity_type: person
│   ├── 工具/库 (tool)     → entities/  entity_type: tool
│   ├── 公司/组织 (company)→ entities/  entity_type: company  
│   └── 产品 (product)     → entities/  entity_type: product
│
└── 跨来源的趋势分析 / 深度综合
    → syntheses/
    条件: 至少 3 个独立来源，有明确的分析视角
```

---

## Concept vs Entity 判断

| 问题 | 是 → | 否 → |
|------|------|------|
| 这是一种可以被"应用"的方法或范式吗？ | concept | 继续判断 |
| 这是一个具体命名的工具/人/公司吗？ | entity | 继续判断 |
| 这是多个现象的综合分析吗？ | synthesis | other（暂不建页）|

---

## Tag 命名规范

### 格式规则
- 全小写，用连字符分隔：`ai-engineering`（不是 `AI_Engineering`）
- 优先用已有 tag，避免同义近义词泛滥
- 每个页面 2-5 个 tag，不要超过 8 个

### 领域 Tag（必选其一）

| Tag | 适用范围 |
|-----|----------|
| `ai-engineering` | AI 工程方法论（Prompt/Context/Harness Engineering 等）|
| `agent` | AI Agent 架构、设计、部署 |
| `llm` | 大语言模型本身（模型能力、训练、评测）|
| `devops` | 软件交付、CI/CD、部署自动化 |
| `knowledge-management` | 知识库、PKM、wiki 工具 |
| `web-scraping` | 网页内容提取技术 |
| `security` | 安全、漏洞、合规 |
| `data-engineering` | 数据管道、数仓、ETL |

### 技术 Tag（按需添加）

| Tag | 适用范围 |
|-----|----------|
| `nodejs` | Node.js 生态工具 |
| `python` | Python 生态工具 |
| `open-source` | 开源项目 |
| `production-ai` | 生产环境 AI 部署 |
| `research` | 学术研究类内容 |

### 分析 Tag（synthesis 页专用）

| Tag | 适用范围 |
|-----|----------|
| `trend-analysis` | 行业趋势分析 |
| `comparison` | 工具/方法对比 |
| `timeline` | 历史演进梳理 |

---

## Synthesis 建立门槛

满足以下**全部条件**才建 synthesis 页：
1. 至少 **3 个独立来源**（不同网站/媒体）
2. 内容跨越 **一个明确的分析维度**（时间维度、观点对比、影响范围）
3. AI 有充分信息可以形成**不同于单篇来源**的综合判断

不满足时：把内容追加到对应 concept/entity 页的"重要进展"小节。

---

## 文件命名规范

### concepts/
- 使用 Title Case，空格替换为空格（Markdown 文件名允许空格）
- 示例：`Harness Engineering.md`, `Context Engineering.md`

### entities/
- 人物：`{Full Name}.md` → `Andrej Karpathy.md`
- 工具：`{Tool Name}.md` → `Defuddle.md`
- 公司：`{Company Name}.md` → `Anthropic.md`

### syntheses/
- 格式：`{topic-slug}-{YYYY-MM}.md`
- 示例：`ai-engineering-evolution-2026-04.md`
- topic-slug：全小写，连字符分隔，描述性强
