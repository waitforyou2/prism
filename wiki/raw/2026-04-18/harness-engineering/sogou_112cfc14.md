---
title: "最近很火的 Harness Engineering，到底是什么？"
url: "http://mp.weixin.qq.com/s?src=11&timestamp=1776529407&ver=6668&signature=Qajy41aU4a6BY91xDLLS0gDSb0k7vsApF*ufBH*KlL3OF1azKUc9rc3RZEaOBj820MgqJiNPuucS3k9FoT8KEjuzGxF6QtiDuNrKtLfUq9Abs1wrjf0oZ9YMuq0D8Y0J&new=1"
source: sogou
keyword: "harness engineering"
relevance: 92
importance: urgent
isReal: true
summary: "微信公众号深度解析 Harness Engineering 是什么"
fetchedAt: 2026-04-18T16:36:20Z
fetchStatus: ok
wordCount: 177
author: "苏苏的AI航行志"
processed: false
---

# 最近很火的 Harness Engineering，到底是什么？

苏苏的AI航行志 苏苏的AI航行志

在小说阅读器读本章

去阅读

最近看 AI Agent 相关内容时，我发现一个词被反复提到：Harness Engineering。  
一开始我也以为，它只是 Prompt Engineering 的升级版。  
后来越看越觉得，不是。  
它解决的根本不是“AI 会不会回答”，而是“AI 能不能把复杂任务稳定做完”。  
我现在更愿意把 Harness 理解成：  
套在 AI Agent 外面的一整套控制系统。  
它让 AI 不只是“会答”，而是能被约束、被调度、被验证，也能在长任务里持续推进，而不是做着做着就跑偏。  

![](https://mmbiz.qpic.cn/sz_mmbiz_png/uj5bky9BibaP5htS91el7nclqa0Oouadibqq3QFCQYWDPs45U1bLibTE3z1PvDbBbia3f71YljWgZibGcqM8zFn9DvGJdrSu5rERn8lHkxD6AwZ8/640?wx_fmt=png&from=appmsg)

这个类比我觉得特别好记：  
模型是发动机，Prompt 是油门，Context 是导航，Harness 更像方向盘、刹车、仪表盘和安全带。  
也就是说，模型负责“能不能跑”，  
Prompt 负责“怎么催它跑”，  
Context 负责“该往哪跑”，  
而 Harness 负责的是：  
别失控、别跑偏、出了问题能发现、做完结果还能验。  
为什么这个词最近会变热？  
因为大家慢慢发现，AI 一旦开始做长任务，真正难的就不是回答本身了。  
而是这些问题：

任务怎么拆，不然一上来就乱做  
状态怎么记，不然做一半就忘了  
工具怎么接，不然很多动作根本完成不了  
结果怎么验，不然看起来像对，其实不靠谱  
做错之后怎么修，不然只能一次性输出然后听天由命

所以说，单靠 prompt 和上下文管理，其实撑不起真正的 long-running agents。  
你还得有一套外部系统，帮它拆任务、接状态、调工具、验结果、做反馈。  
我会把 Harness 先理解成 6 个关键模块：

1. 任务拆解  
	先把复杂目标拆成小任务，不然 AI 很容易一上来就做乱。
2. 上下文管理  
	让它知道自己现在做到哪、前面发生过什么、接下来该干嘛。
3. 工具调用  
	代码、浏览器、数据库、文件系统、API……很多任务不是“会说”就够了，而是真的要“会做”。
4. 验证机制  
	比如测试、lint、评分、截图检查、人工审核。  
	不验证，很多结果只是“看起来合理”。
5. 反馈循环  
	不是输出一次就结束，而是做错了能拉回来、继续修。
6. 角色分工  
	这个也很关键。  
	不要让 AI 既负责规划、又负责执行、还负责评价自己。  
	更稳的做法通常是拆成 planner、generator、evaluator 这类角色。  
	不然最容易出现的情况就是：它自己做完，再自己夸自己。  
	很多人会把它和 Prompt Engineering、Context Engineering、Tool Use 混在一起，但它们其实不是一个层级。

Prompt Engineering：研究的是指令怎么写清楚  
Context Engineering：研究的是该给 AI 什么信息  
Tool Use / Agent：研究的是 AI 能不能调用工具去做事  
Harness Engineering：研究的是怎么把这些能力组织起来，让 AI 稳定、可控、可验证地把任务完成

所以我现在的理解是：  
Prompt 决定 AI 怎么开始，  
Context 决定 AI 知道什么，  
Tool 决定 AI 能做什么，  
Harness 决定 AI 最后能不能真的把事做成。  
如果你只是让 AI 回答一个问题，Prompt 可能已经够用了。  
但只要你开始让 AI 连续做任务，比如查资料、写代码、调工具、反复修正结果，你就会发现：  
真正决定上限的，往往不是一句 prompt，  
而是背后那套 harness。  
你最近有开始明显感觉到吗？  
现在大家讨论 AI，重点已经慢慢从“怎么写提示词”，转到“怎么把任务控住”了。

继续滑动看下一个

苏苏的AI航行志

向上滑动看下一个

Got It

Scan with Weixin to  
use this Mini Program

: ， ， ， ， ， ， ， ， ， ， ， ，. Video Mini Program Like ，轻点两下取消赞 Wow ，轻点两下取消在看 Share