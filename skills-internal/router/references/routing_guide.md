# 路由策略指南 — Router 决策规则

Router 使用 `route.py` 的纯关键词匹配算法（四级评分，零 LLM API 开销）来决定将问题路由到哪个知识库。

---

## 评分算法

每个知识库独立计分，按权重叠加：

| 级别 | 匹配对象 | 权重 | 说明 |
|------|---------|------|------|
| L1 精确 | KB 的 `id` 字段 | +0.60 | 最强信号。问题中直接出现了知识库 ID |
| L2 标签 | KB 的 `tags` 列表 | +0.30 | 任意一个 tag 出现在问题中 |
| L3 主题 | KB 的 `topics` 列表 | +0.40 | 任意一个主题短语出现在问题中 |
| L4 模糊 | KB 的 `description` 词重叠 | 0~+0.25 | 兜底，仅在前三级均无命中时启用 |

**阈值**：score ≥ 0.10 才纳入候选，candidates 按分数降序排列。

---

## Strategy 决策

| 候选数量 | Strategy | 后续动作 |
|---------|----------|---------|
| 0 | `no_match` | 告知用户，建议运行 harvest |
| 1 | `single_kb` | 单 SubAgent 派发，直接呈现结果 |
| ≥2 | `multi_kb` | 多 SubAgent 并发（或串行），合并结果 |

---

## 典型场景示例

| 用户问题 | 匹配知识库 | Strategy | 原因 |
|---------|-----------|---------|------|
| "Claude Code 最新功能？" | claude | single_kb | id_match: 'claude' |
| "Codex 和 Claude Code 哪个好？" | codex + claude | multi_kb | id_match: 'codex'; topic_match: 'Claude Code' |
| "AI 编程工具的最新趋势？" | claude + codex + cursor | multi_kb | tag_match: 'ai-coding' 等（各库分数接近） |
| "今天天气怎么样？" | （无） | no_match | 无任何知识库覆盖 |
| "anthropic 最近有什么新闻？" | claude | single_kb | tag_match: 'anthropic' |

---

## 跨库合并规则（multi_kb 时）

当多个 SubAgent 返回结果后，Router 按以下规则合并：

### 1. 按主题聚合，不按 KB 聚合

❌ 错误方式：
> **Claude 知识库的答案：**... **Codex 知识库的答案：**...

✅ 正确方式：
> **性能表现**：[[Claude Code@claude]] 在大型代码库中表现...；[[Codex CLI@codex]] 则...
> **价格**：...

### 2. 跨库引用格式

使用 `[[Page Title@kb_id]]` 格式，例如：
- `[[Claude Code@claude]]` — claude 知识库中的 Claude Code 页面
- `[[Codex CLI@codex]]` — codex 知识库中的 Codex CLI 页面

### 3. 共识与分歧处理

- **多库一致** → 作为已确立的事实呈现，注明多来源印证
- **多库矛盾** → 标注 `⚠️ 分歧`，并分别引用来源：
  ```
  ⚠️ 分歧：[[Claude Code@claude]] 称每月订阅费为 $20，
  而 [[Cursor@cursor]] 称竞争对手有免费套餐。
  数据可能存在时效差异。
  ```
- **某库 confidence=low** → 在引用前注明"该数据可能过时"

### 4. 置信度降级传导

若某 SubAgent 返回 `confidence: low`，该库的内容在合并结果中：
- 仍然呈现（信息有参考价值）
- 但在结尾标注：`*注：[kb_id] 知识库数据可能不是最新，建议重新运行 harvest 更新。*`

---

## 边界情况处理

| 情况 | 处理方式 |
|------|---------|
| SubAgent 返回"本库无法回答" | confidence=low，note 注明原因，合并时降权 |
| 某个 KB 的 wiki/WIKI.md 不可读 | 跳过该 KB，在结果中注明 |
| registry.json 不存在 | 触发 discover.py 重新生成，再继续 |
| 问题极短（如"codex"，单词） | 同样走正常流程（L1 可命中） |
| 问题涉及所有已知主题 | 全部纳入 multi_kb，按置信度排序 |

---

## 路由日志格式（写入各 KB 的 log.md）

```markdown
## [YYYY-MM-DD] route_query | "用户问题原文"
路由策略: single_kb | 匹配: claude (0.90)
回答引用: [[Claude Code]], [[Anthropic]]
```

```markdown
## [YYYY-MM-DD] route_query | "Codex 和 Claude Code 哪个好？"
路由策略: multi_kb | 匹配: codex (0.95), claude (0.90)
回答引用: [[Codex CLI@codex]], [[Claude Code@claude]]
```
