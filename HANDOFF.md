# Prism Knowledge System - Project Handoff & Status

**更新时间：** 2026-04-19
**项目定位：** Prism 是一套 Agentic AI 辅助的自动化知识管理与萃取系统。它的终极目标是打造一条：`全网热点/干货监听 (Harvest) -> 智能打假过滤 -> 全文脱水抓取 (Defuddle) -> AI 知识提纯结晶化 (Prism)` 的终极智库流水线。

---

## 🚀 已完成里程碑 (Completed: Harvest Skill)

当前我们已经将系统管线的前半部分——**收割机系统（Harvest）** 打磨到了极致。

### 1. 超强十核全网雷达（已接入）
- **国际阵列** (`search_web.py`)：`Bing`, `Google`*, `DuckDuckGo`, `HackerNews`, `GitHub`, `YouTube`
- **国内生态** (`search_china.py`)：`Sogou` (综合网页), `Bilibili`, `Weibo` (自带热搜), `Juejin` (掘金优质文章)
- *特殊能力*：自动脱水 GitHub 开源仓库的 `README.md`，自动抓取 YouTube 视频的原声隐藏英文字幕。

### 2. 双轨落盘架构 (Dual-Layer Storage)
- **`wiki/raw/` (原石层)**：凡是通过 AI 打分审核（Relevance ≥ 70，isReal = true），且通过工具成功抓取 >100 字 Markdown 全文的长篇文章/视频带字稿都会落入这里。
- **`wiki/signals/` (线索层)**：无法拉取全文的平台（B站、微博）、被限流报错的对象，以及低于 100 字的短摘要，将自动安全降级存入此处，只保留元数据。

### 3. “水管”数据流改造 (Standard IO Pipeline)
完全删除了临时拼接脚本，实现了原生优雅的流式通信：
```cmd
# 过滤 -> 抓取 -> 落盘 的极简流转
node fetch_content.js < annotated_results.json > enriched.json
python save_to_raw.py --keyword "{keyword}" < enriched.json
```

---

## ⚠️ 关键知识积累与避坑指南 (For Next AI Context)

下次你将此文档丢给新的我时，请务必留意以下底线禁忌：

1. **PowerShell 管道之坑**：在 Windows 环境中，**绝不允许使用 PowerShell 执行带有 `<` `|` `>` 的 JSON 流重定向操作**，这会导致文件编码被强行转码（生出大量乱码和控制符）。**必须在原生 CMD (`cmd.exe /c`) 中，或直接用 Python 的 `subprocess` 传递二进制 `stdin`。**
2. **知乎防御机制**：知乎的 API 启用了 `x-zse-96` 客户端签名防御。当前我们处于“战术放弃”状态，请勿盲目编写 HTTP 请求试图破解知乎，除非后续引入完整的无头浏览器（Playwright）。
3. **搜狗链接的陷阱**：遇到 `sogou.com/link` 这类强行跳转链接（多为搜索出来的微信公众号外部链接），当前采取**直接降级丢入 signals 工具池**的策略，防止 HTTP 抓取器阻塞假死。
4. **防重复器**：保存操作具备本地基于 URL 的防重复字典机制，可以尽情增量去跑。

---

## 🎯 下一阶段核心任务 (Next Steps)

收割任务已圆满完成（目前已积累了大量高质量的关于 "Harness Engineering", "Claude Code" 和 "Agent Framework" 的测试数据文稿存放于 `wiki/raw/` 中）。

**第二大核心模组：Prism 结晶化 亟待启动！**
下一次的核心工作，是开始编写 **`Prism` 整理技能**。
- **目标**：我们需要编写一套极其聪明的大模型编排逻辑，让它读取本地 `raw/` 目录中杂乱无章的原始深度文章。
- **过程**：进行信息合并、冲突消解、重点提炼。
- **产出**：输出结构化、有清晰目录树、高信噪比的永久维基长页（Concept Wiki Pages），正式存入 `wiki/pages/` 目录。（而不是让它们像新闻稿一样一直躺在硬盘里吃灰）。

> **给下一个 AI 的留言 (Message to self)**
> 兄弟，前面探路的苦活累活（全网爬虫、风控规避、环境调试、文件存储分配）已经被我们铺得像大理石地板一样平整了。接下来接手的人，请直接开启顶级的 LLM 认知模式，大胆围绕 `Prism` 来设计最强悍的知识结晶算法，给人类用户构建属于他的专属真理大百科！
