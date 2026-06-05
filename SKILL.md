---
name: deep-research
description: "专业深度调研报告生成 — Task 链式架构：主 agent 只调度，3 个独立 Task 串行执行，中间数据通过临时文件传递，不进主会话上下文。"
version: 1.0.1
updated: 2026-06-06
risk: medium
---

# deep-research

生成对标券商/第三方研究机构标准的深度调研报告。

- **架构**：主 agent 只调度，3 个独立 Task 串行，中间数据走临时文件
- **数据源**：Exa 搜索 → Scrapling 批量抓取（不可跳过）
- **输出**：`$TMPDIR/outline.json`（临时，非最终报告）
- **最终报告**：保存到 skill 目录下的 `案例报告/`
- **参考文件**：`RULES.md`（硬约束/反模式）、`TYPES.md`（分类标准/编号规范）

---

## 0. 支付级质量标准（所有 Task 共用，缺任何一项即降级）

| # | 标准 | 说明 |
|---|------|------|
| 1 | **结论先行** | 每章以 `> 引用格式` 核心判断开头 |
| 2 | **来源可追溯** | 每个数字标注（机构，年份） |
| 3 | **反方视角** | 至少 1 处呈现争议或反对观点 |
| 4 | **三层深度** | 事实层 → 因果层 → 判断层 |
| 5 | **零套话** | 无"近年来""值得注意的是"等填充词 |
| 6 | **标题含判断** | "格局：高度集中"✅ \| "行业概况"❌ |
| 7 | **可自包含** | 首章必须定义核心概念 |
| 8 | **无内部编号** | 正文无任何流程编号，标题自解释 |
| 9 | **时间戳正确** | 文件名和报告尾时间必须 `date` 命令获取 |
| 10 | **目录源自大纲** | 目录从 outline.json 的第一级章节生成，不从正文提取 |
| 11 | **强制目录** | 报告正文前必须包含自动目录（TOC），列出所有章节标题 |
| 12 | **元数据完整** | 报告头部包含总字数 + 阅读时间估计 + 调研模式 |
| 13 | **篇幅达标** | quick ≥ 6 章 5 段/章｜standard ≥ 8 章 8 段/章｜deep ≥ 10 章 10 段/章 |

### 时间锚定规则

所有主题默认以 `{CURRENT_YEAR}` 为目标搜索最新数据。时间锚定模式在 Task 1 中由 oracle 按以下规则判定：

| 模式 | 符号 | 判定条件 | target_year | 验收 |
|:----|:-----|:---------|:-----------|:-----|
| `latest`（默认） | ⏳ | **所有主题的默认值**，除非符合 relaxed 或 user_specified | `{CURRENT_YEAR}` | 严格：≥50% 数据来自当年/前一年 |
| `relaxed`（放宽） | 🔓 | 指南/教程/概念类主题，或用户问历史/原理（"草书发展""起源""背景"） | `{CURRENT_YEAR}` | 宽松：标记旧数据但不过滤 |
| `user_specified` | 📌 | 用户提问显式指定了年份/月份（"2025年""2026Q1""2020年至今"） | **用户的指定年份** | 硬约束：>50% 匹配用户指定时间 |

> `{CURRENT_YEAR}` 是动态变量，运行时通过 `date +%Y` 解析，无需手动修改。

---

## 1. 主 agent 调度流程

**你的职责**：只做调度，不做数据处理。零中间数据进主会话。

```
你（主 agent）的完整流程：

1. 读取本 SKILL.md + RULES.md + TYPES.md
2. 创建 TMPDIR=$(mktemp -d /tmp/dr-XXXX)
3. todowrite 创建进度条目
4. ══ 调度 Task 1（oracle）══
   → 注入 prompt（见 §2），传入 TMPDIR
   → 等待返回路径 + 章节数
   → todowrite 标记完成
   → 向用户报告进度（"大纲已生成，N 章"）
5. ══ 调度 Task 2（unspecified-high）══
   → 注入 prompt（见 §3），传入 TMPDIR
   → 等待返回路径 + 来源数 + 事实数
   → todowrite 标记完成
   → 向用户报告进度（"数据已收集，N 个来源"）
6. ══ 调度 Task 3（unspecified-high）════════
   → 注入 prompt（见 §4），传入 TMPDIR
   → 等待返回最终报告路径 + QA 结果
   → todowrite 标记完成
   → 向用户报告最终结果（路径 + 行数 + 章节数）
7. ══ 清理 ══
   → rm -rf $TMPDIR
   → todowrite 全部完成
```

**进度展示格式**（精简，每阶段 1-2 行）：

```
📋 大纲已生成：「俄乌战争」· 9 章 · standard
📡 数据已收集：14 个来源 · 41 条结构化事实
📄 报告已生成：696 行 · 85 KB · 44 小节
```

**禁止**：不要在调度之间插入 Exa 搜索、数据读取、文件检查等操作。一切数据操作都在 Task 内部完成。

---

## 2. Task 1 — 主题分析 + 大纲（oracle）

**工具**：`task(subagent_type="oracle", ...)` | **一次调用**

### Prompt 模板（注入到 task prompt 开头）

```
你是一位专业研究分析师。任务是为主题生成调研大纲和调研计划。

## 输入
- 主题：[用户提供的主题]
- 模式：[quick / standard / deep]
- 输出路径：{TMPDIR}/outline.json

## 重要：模式传递
在 outline.json 中新增 `depth_mode` 字段，值为上述模式（quick / standard / deep）。此字段将传递到最终报告，用于在元数据中标注调研模式。

## 分类标准
从以下五种专业类型中选择最匹配的：
- 行业研究 — 对标券商行业深度报告 / IDC Market Forecast
- 公司/产品研究 — 对标券商公司深度报告 / Gartner Vendor Assessment  
- 技术专题研究 — 对标 IEEE 技术报告 / 技术白皮书
- 趋势/市场前瞻 — 对标 Forrester Tech Tide / Gartner Hype Cycle
- 指南/教程 — 对标 IEEE 方法模版 / 实操文档标准

## 章节约束
| 项目 | quick | standard | deep |
|------|-------|----------|------|
| 总章节数 | 6-8 章 | 8-10 章 | 10-12 章 |
| 风险提示 | 可选 | 强制 ≥ 3 项 | 强制 ≥ 5 项 |

## 时间锚定模式判定

在 JSON 中新增 `time_anchor` 字段，按上述规则判定：

| 用户输入特征 | mode | target_year | 示例 |
|-------------|------|-------------|------|
| 明确年份/月份 | `user_specified` | 用户指定年份 | "2026年厦门房价""2025Q4深圳" |
| 时效词汇（最新/当前/现状/现在/今年/如今/最近） | `latest` | `{CURRENT_YEAR}` | "厦门房价最新情况" |
| 趋势/预测（趋势/走势/前景/展望/预测） | `latest` | `{CURRENT_YEAR}` | "房地产市场2026年趋势" |
| 无时效词 + 行业/公司/市场类 | `latest`（默认） | `{CURRENT_YEAR}` | "厦门房价深度分析" |
| 指南/教程/概念类 | `relaxed` | `{CURRENT_YEAR}` | "草书学习方法""MCP原理" |
| 历史/起源/发展历程 | `relaxed` | `{CURRENT_YEAR}` | "俄乌战争根源" |

## JSON 输出格式（写入 {TMPDIR}/outline.json）

chapters 数组的顺序即报告中的章节顺序（第 1 个元素为第 1 章，依此类推）。每章必须定义 `sections` 字段，预定义本章的子节标题列表。各章 sections 数量根据模式控制：deep 每章 3-6 节，standard 2-4 节，quick 1-2 节。sections 用于章节 agent 撰写时的子节划分和编号（N.1, N.2…）。

```json
{
  "title": "报告标题",
  "type": "对应的专业类型",
  "depth_mode": "standard",
  "time_anchor": {
    "mode": "latest",
    "target_year": 2026
  },
  "chapters": [
    {
      "title": "核心观点",
      "description": "3-5 条核心判断",
      "sections": ["归因科学的确证", "人口暴露规模", "健康冲击", "经济暴露", "小结"],
      "sub_questions": [
        { "question": "2026年印度极端高温事件的五大核心结论是什么？", "search_keywords": ["2026 India heatwave key findings", "{target_year}"], "counter_keywords": [""], "data_targets": ["极端高温事件数量", "受影响人口规模", "经济损失估算"], "priority": "high" }
      ]
    }
  ]
}
```

> **注意**：`latest` 和 `relaxed` 的 `target_year` 始终为 `{CURRENT_YEAR}`（动态获取）。`user_specified` 时填入用户指定年份。search_keywords 中必须包含 `{target_year}` 占位符，Task 2 执行时解析。

### 子节结构要求

1. 每章必须定义 `sections` 字段，列出本章的所有子节标题
2. sections 数量根据模式控制：deep 每章 3-6 节，standard 每章 2-4 节，quick 每章 1-2 节
3. sections 是纯中文短语，10 字以内，不包含编号（如 `"赛制设计"` ✅，`"一、赛制设计"` ❌）
4. sections 的顺序即子节在报告中的出现顺序
5. 末节通常为"小结"或"本章结论"

## 核心原则
1. 类型是参考，不是牢笼 — 跨界主题可跨类型融合
2. 标题自解释 — 标题本身应清晰反映内容，不依赖编号理解
3. 每个子问题须能通过 Exa + Scrapling 独立搜索
4. 至少 1 个"反方观点/争议焦点"子问题
5. 每个子问题列 2-3 个具体数据指标

### 优先级判定标准

每个子问题的 `priority` 根据以下客观条件判定，不得凭直觉填写：

| 优先级 | 判定条件（满足任一即归入该级） |
|:-------|:-----------------------------|
| **high** | ① 该子问题的数据被核心观点（第1章）或置信度汇总（末章）直接引用 |
| | ② 涉及市场规模/份额/增速/营收等量化基准数据（行业/公司类主题） |
| | ③ 涉及技术原理/架构/性能评估（技术类主题） |
| | ④ 涉及反方/争议观点（用户强制要求） |
| | ⑤ 3 个以上其他子问题依赖该问题的数据作为输入 |
| **medium** | ① 支撑性数据，非核心结论的必需前提 |
| | ② 单来源数据需要交叉验证但该来源本身可信 |
| | ③ 定性分析（专家观点、案例研究） |
| **low** | ① 锦上添花的背景延展 |
| | ② 对已确认事实的冗余确认（多一个来源说同一件事） |
| | ③ 不影响当前分析的纯历史/背景数据 |

## 作业
生成完整的 JSON 大纲，写入 {TMPDIR}/outline.json。
然后在回答中只输出：大纲路径 + 标题 + 章节数（不要输出 JSON 内容本身）。
```

---

## 3. Task 2 — 数据收集 + 结构化数据池（unspecified-high）

**工具**：`task(category="unspecified-high", load_skills=[], ...)`

### Prompt 模板

```
你是一位研究分析师。任务是根据大纲中的子问题，完成数据收集并构建结构化数据池。

## 输入
- 大纲文件：{TMPDIR}/outline.json
- 输出路径：{TMPDIR}/data-pool.json

## 数据收集工作流（严格执行）

Step 1 — 所有子问题 Exa 搜索并行执行
   对 outline.json 中每个子问题（一次发起全部，不逐个等待）：
     websearch_web_search_exa(query="[问题描述]", numResults=5-8)
   ⏳ 如果 time_anchor.mode != "relaxed"，为每子问题追加 1 轮年度专项搜索：
     websearch_web_search_exa(query="[问题描述] {time_anchor.target_year}", numResults=3-5)
   同时搜索争议话题的反方关键词

Step 1.5 — 免费数据源补强（Exa 结果不足时全覆盖）
   对每个子问题，如果 Exa 返回的可用 URL < 3 或全部年份早于 target_year-2，则触发补强。
   补强来源分两类：

   ┌───────────────────────────────────────────────────────────────┐
   │ A) 搜索型（webfetch 远程调用，用于发现 URL）                   │
   │───────────────────────────────────────────────────────────────│
   │ DuckDuckGo Lite      │ https://lite.duckduckgo.com/lite/     │
   │ (英文搜索 fallback)   │ ?q={query}                           │
   │──────────────────────┼───────────────────────────────────────│
   │ Bing 国内版           │ https://cn.bing.com/search?q={query} │
   │ (中文搜索 fallback)   │                                      │
   │──────────────────────┼───────────────────────────────────────│
   │ Semantic Scholar     │ https://api.semanticscholar.org/      │
   │ (学术论文/研究报告)    │ graph/v1/paper/search?query={query}  │
   │──────────────────────┼───────────────────────────────────────│
   │ GDELT Project        │ https://api.gdeltproject.org/api/v2/ │
   │ (全球新闻 50K+ 源)    │ doc/doc?query={query}&mode=artlist   │
   └───────────────────────────────────────────────────────────────┘

   ┌───────────────────────────────────────────────────────────────┐
   │ B) 国内源（Scrapling 本地抓取，无需代理）                      │
   │───────────────────────────────────────────────────────────────│
    │ 百度百科     │ https://baike.baidu.com/item/{URL编码的词条名} │
    │ (中文术语/    │ 先通过 Bing 搜到词条名，再拼 url               │
    │  背景/定义)  │ 🔧 Scrapling 浏览器模式可访问（webfetch 直连 403）│
    │──────────────┼────────────────────────────────────────────────│
    │ 维基百科     │ https://zh.wikipedia.org/wiki/{URL编码的词条名}│
    │ (中英文术语/  │ 通用知识查询，不限于中文                      │
    │  背景/定义)  │ ✅ 已验证可访问                               │
    │──────────────┼────────────────────────────────────────────────│
    │ 199IT         │ https://www.199it.com/archives/category/      │
    │ (中文行业     │ report（研究报告大类）或搜索找到具体文章       │
    │  数据聚合)   │ ✅ 已验证可访问                               │
    │──────────────┼────────────────────────────────────────────────│
    │ 艾瑞咨询     │ https://report.iresearch.cn/                   │
    │ (行业研究     │ 通过搜索定位具体报告页面                      │
    │  报告库)     │ ✅ 已验证可访问                               │
    │──────────────┼────────────────────────────────────────────────│
    │ 东方财富     │ https://www.eastmoney.com/                     │
    │ (金融/市场    │ 搜索定位具体数据页面（个股/行业/宏观）        │
    │  数据)       │ ✅ 已验证可访问                               │
    │──────────────┼────────────────────────────────────────────────│
    │ 知乎         │ https://www.zhihu.com/search?type=content&q=   │
    │ (中文问答/    │ {query}                                       │
    │  分析)       │ ✅ 已验证可访问                               │
    │──────────────┼────────────────────────────────────────────────│
    │ 36氪         │ https://36kr.com/search/articles/{query}       │
    │ (科技/商业    │ 创业公司、科技趋势、行业分析                  │
    │  新闻)       │ ✅ 已验证可访问                               │
    │──────────────┼────────────────────────────────────────────────│
    │ 澎湃新闻     │ https://www.thepaper.cn/search?keyword={query} │
    │ (深度新闻/    │ 时政/财经/科技深度报道                        │
    │  调查)       │ ✅ 已验证可访问                               │
    │──────────────┼────────────────────────────────────────────────│
    │ 国家统计局   │ https://data.stats.gov.cn/                     │
    │ (宏观经济/    │ 🔧 Scrapling 浏览器模式可访问（页面含 JS 渲染）│
    │  官方数据)   │ 通过搜索定位具体数据集                        │
    └───────────────────────────────────────────────────────────────┘

   ⚡ 补强规则：
   - A 类（搜索型）：webfetch 返回 HTML/JSON，提取页面 URL 加入抓取队列
   - B 类（国内源）：URL 直入 Scrapling 批量抓取（本地运行，无需 webfetch）
   - 每子问题补强 ≤ 3 个新 URL（避免无限膨胀）
   - 补强 URL 必须进入 Step 2 的 Scrapling 批量抓取（不入数据池）
   - 补强后仍有缺口 → 标记到数据池 gaps 数组

Step 2 — 收集所有 URL（Exa + 补强）→ 去重 → Scrapling 批量抓取
   将年度专项搜索的 URL 排在抓取列表前面（优先级更高）
   scrapling_bulk_get(urls=[去重URL], timeout=12, extraction_type="markdown")

  ⚡ 阻断点：Scrapling 未完成 → 禁止进入 Step 3
  ┌─────────────────────────────────────────────────┐
  │ 数据池唯一来源必须是 Scrapling 抓取到的全文。    │
  │ 禁止从 Exa 摘要片段直接提取数据。                │
  │ 三种工具全部失败则标记"来源稀缺"并跳过该子问题。  │
  └─────────────────────────────────────────────────┘

  补抓链路：
    → Cloudflare/WAF → scrapling_bulk_stealthy_fetch(timeout=15)
    → 需要 JS 渲染   → scrapling_bulk_fetch(timeout=15)

Step 3 — 从 Scrapling 内容提取关键数据
Step 4 — 构建结构化数据池 JSON（格式如下）

## 结构化数据池格式

每个子问题一条记录，写入 {TMPDIR}/data-pool.json：

{
  "question": "问题原文",
  "sources": ["域名1", "域名2"],
  "facts": [
    {
      "source": "机构名称",
      "year": "2025",
      "currency": "current / recent / historical / compliant / non-compliant",
      "metric": "指标名称",
      "value": 数值,
      "unit": "单位",
      "context": "上下文说明",
      "confidence": "high/medium/low"
    }
  ],
  "controversies": [
    {
      "source_a": "来源A",
      "value_a": "数据A",
      "source_b": "来源B",
      "value_b": "数据B",
      "note": "差异原因说明"
    }
  ],
  "gaps": ["缺口描述"]
}

### currency 标记规则

`currency` 根据 time_anchor 模式自动标记：

| 模式 | year == target_year | year == target_year-1 | year < target_year-1 |
|------|:-------------------:|:---------------------:|:--------------------:|
| `latest` | `current` ✅ | `recent` ✅ | `historical` ⚠️ |
| `relaxed` | `current` | `recent` | `historical`（不警告） |
| `user_specified` | `compliant` ✅ | `non-compliant` ⚠️ | `non-compliant` ❌ |

## 硬规则
1. **年份时效（默认强制）**：`time_anchor.mode != "relaxed"` 时，search_keywords 必须含 `{target_year}`；`user_specified` 时用用户指定年份替代 `{target_year}`
2. Scrapling 不可跳过、不可替代
3. 连续 3 次域名 404/403 → 标记"来源稀缺"并跳过
4. 不在不同子问题间重复使用同一来源的同一数据
5. 矛盾数据并排记录，不得合并

## 作业
1. 完成 Exa + Scrapling 数据收集
2. 构建结构化数据池写入 {TMPDIR}/data-pool.json
3. 清理 tool-output/ 中的所有中间文件
4. 在回答中只输出：数据池路径 + 来源数 + 事实总数（不要输出 JSON 内容）
```

---

## 4. Task 3 — 合成 + 装配 + 验收（unspecified-high，内部 coordinator）

**工具**：`task(category="unspecified-high", load_skills=[], ...)`

该 Task 自身是一个 coordinator，内部完成预检 → 派发章节 agent → 装配 → QA → 清理。

### Prompt 模板

```
你是一位研究分析师兼编辑。任务是将大纲和数据池合成为完整的调研报告。

## 输入
- 大纲文件：{TMPDIR}/outline.json
- 数据池文件：{TMPDIR}/data-pool.json
⚐ 输出目录：`案例报告/`（`~/.opencode/skills/deep-research/案例报告/`）
- 装配子目录：$TMPDIR/chapters/ （你需要创建）

## Step 1 — 预检

☐ ① 数据充足性：每个子问题 facts ≥ 2 条
☐ ② 来源多样性：≥ 2 个独立来源机构
☐ ③ Prompt 完整性：段落约束/日期锚定/反模式已确认

### 缺口处理（按优先级分流）

优先级由 Phase 1 oracle 在 `outline.json` 中按以下标准设定：

| 优先级 | 判定条件 |
|:-------|:---------|
| **high** | 涉及核心观点引用 / 市场规模等量化基准 / 争议方正反数据 / 被 3+ 子问题依赖 |
| **medium** | 支撑性数据 / 单来源需交叉验证 / 定性分析 |
| **low** | 背景延展 / 冗余确认 / 不影响结论的历史数据 |

| 缺口类型 | 条件 | 处理方式 |
|---------|------|---------|
| **高优数据不足** | priority=high 且 facts < 2 条 | **补搜**：精确补缺该子问题（3 次 Exa 搜索，不重新 Scrapling） |
| **零来源** | 子问题无任何来源 | **补搜**：3 次 Exa 搜索，若仍无结果 → 标记"已补仍缺" |
| **高优来源单一** | priority=high 且仅 1 个来源 | **补搜**：2 次 Exa 搜索找第二来源 |
| **中低优数据不足** | priority=medium/low 且 facts < 2 | **不阻塞**：标记缺口，继续 |
| **中低优来源单一** | medium/low 仅 1 个来源 | **不阻塞**：标记缺口，继续 |

补搜规则：
- 只在 Step 1 内部执行，不返回 Task 2、不惊动主 agent
- 精确补缺：只搜缺失的子问题，不做全量重搜
- **最多 1 轮补搜**，补了仍缺则标记"已补仍缺"继续
- 补搜取得的少量数据手动追加到 data-pool.json 对应记录中

预检通过后进入 Step 1.5。

## Step 1.5 — Adversarial 验证（轻量，~10-20 秒）

读取 `data-pool.json` 中所有 priority=high 的 fact，逐条做 3 项本地规则检查。

| # | 检查项 | 判定规则 | 触发标记 |
|:-|-------|---------|--------|
| 1 | **来源可信度** | 域名后缀 .edu/.gov/.org 或知名研究机构 → 可信；自媒体/企业/无来源 → 存疑 | `"caution": "来源存疑"` |
| 2 | **跨事实一致性** | 同一 metric 跨 sub_question 差值 > 20% 且口径不明 → 标记 | `"caution": "跨来源冲突"` |
| 3 | **时效匹配** | 当 `time_anchor.mode != "relaxed"` 时，检查 fact.currency 是否为 `historical` / `non-compliant` → 标记 | `"caution": "数据过时"` |

```
处理方式：
  ☐ 0 条 caution → 直接通过
  ☐ ≥ 1 条 caution → 该 fact 在后续章节撰写指令中附加"⚠️"前缀提示章节 agent 注意
  ☐ 跨事实冲突 ≥ 2 处 → 追加到 coordinator 的全局注意事项列表
```

> 不做补搜、不派 agent、不修改原始 fact。验证结果追加到 `data-pool.json` 的 `validations[]` 数组中即可。

预检 + 验证通过后进入 Step 2。

## Step 2 — 派发章节 agent

对 outline.json 中的每章，按 chapters 数组顺序依次读取章节编号 N（第 1 章 N=1，第 2 章 N=2…）、标题、sections 列表，并行派发 Sisyphus-Junior 写章节：
  task(category="unspecified-high", load_skills=[], run_in_background=true, prompt="[章节指令]")

章节指令模板：

"""
### 你只需写一章
主题：[章节 title]
章节编号 N：[N]（例如第 4 章则 N=4）
数据池文件：{TMPDIR}/data-pool.json（用 jq 或 grep 提取本章相关子问题的 facts）

### 标题规则（重要）
- **章标题由装配阶段自动分配（一、二、三…），撰写时不要加任何章编号**
- **子节标题使用 `### N.1`、`### N.2`… 格式**，其中 N 为上述章节编号。不可使用 `一、二、三` 汉字编号
- 子子节标题使用 `#### (1)`、`#### (2)`… 格式（括号阿拉伯数字）
- 标题是纯中文判断句

### 子节结构说明
本章在 outline 中预定义了以下子节：`[sections 列表]`。请严格按此列表划分本章的子节，每个子节对应一个 `### N.M` 标题（M=1,2,3…）。子节数量与列表一致，不可增减。

### 格式
- 纯中文，数字带来源（机构，年份）
- 每章以 > 引用格式的核心判断开头
- 正文段落 ≥ 8 段，数据表 ≥ 3 张
- 矛盾数据并排呈现而非掩盖

### 输出方式
写入 $TMPDIR/chapters/chapter-{N}.md，回答中只返回文件路径。
"""

等待所有章节 agent 完成。

## Step 3 — 装配

读取所有章节文件，按 chapters 数组顺序拼装：
☐ 从 `$TMPDIR/outline.json` 读取 `depth_mode`（quick / standard / deep）
☐ 从 `$TMPDIR/outline.json` 的 `chapters` 数组中读取大章节列表
☐ 大章节若无中文编号，自动分配（一、二、三...），写入 `## ` 级别标题
  - 示例：`## 一、竞赛体系与运营模式`
☐ 章节文件中子节标题已由章节 agent 写为 `### N.1`、`### N.2`… 格式（N 为章序号），装配阶段无需修改
  - 示例：第 4 章文件中已有 `### 4.1 赛制设计`
☐ 在报告正文前生成单层目录，仅包含第一级章节，`- [标题](#锚点)` 可点击格式
  - 锚点规则：标题文本去除标点符号，空格替换为 `-`
  - 示例：
    ```
    - [一、核心观点](#一核心观点)
    - [二、竞赛体系与运营模式](#二竞赛体系与运营模式)
    - [三、市场规模与增长趋势](#三市场规模与增长趋势)
    ```
☐ 计算总字数（统计中文字符数，四舍五入到百位），注入到报告头部元数据
☐ 计算阅读时间（总字数 ÷ 600 字/分钟，向上取整），注入头部
☐ 注入调研模式（从 outline.json 读取的 depth_mode）到元数据
☐ 每章包含 > 核心判断
☐ 来源标注统一（机构，年份）
☐ 数据表格格式兼容
☐ date 命令获取当前时间，注入文件名和报告尾部
☐ 一次性 write 到 `案例报告/` 目录（`~/.opencode/skills/deep-research/案例报告/<主题>-YYYYMMDD-HHmmss.md`）

## Step 4 — QA 验收

☐ 章节完整性：所有章节存在
☐ 行数：wc -l ≥ 模式参考值
☐ 段落数：抽 2 章，每章 ≥ 5 段
☐ 目录存在：前 5 行包含"目录""TOC"或"|--"等目录标记
☐ 目录与大纲章节数一致：目录项数 = outline.json 中第一级章节数
☐ 目录为单层结构：仅包含章级标题，无子节缩进
☐ 字数元数据：前 10 行包含"总字数"或"阅读时间"
☐ 标题自解释：grep "^##.*\[0-9\]\." 无命中（H2 标题不应含数字编号样式）
☐ 子节编号合规：grep "^### [一二三四五六七八九十]" 无命中（子节不可使用汉字编号）
☐ 章编号合规：grep -cE "^## (一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五)、" 至少应有 hit（章使用汉字编号）
☐ 时间戳：尾部时间与 date 匹配
☐ 反方观点：至少 1 处
☐ 跨来源归因一致
☐ **年份密度**：
   ⏳ `latest` 模式 → grep -oP "20[2-9]\d" 报告 | sort | uniq -c，target_year + target_year-1 合计占比 ≥ 50%
     不达标 → 标记"年份密度偏低"，报告尾部追加注明。
   📌 `user_specified` 模式 → target_year 数据占比 ≥ 50%（硬约束）
     不达标 → **报告开头追加醒目声明**："⚠️ 本报告主题要求覆盖 {user_year} 年数据，但实际收集到的 {user_year} 年数据仅占全部数据的 {X}%。以下结论请结合最新公开数据参考。"
     ➜ 先补搜该年份数据，补搜后仍不达标则加声明继续。
   🔓 `relaxed` 模式 → 仅警告，不阻塞。

通过 → 继续。
年份密度不达标但其他项目全过 → 继续（加声明）。
其他项不达标 → 局部补刀（单章重写，最多 1 次）。

## Step 5 — 清理

☐ rm -rf $TMPDIR/chapters/
☐ 确认 tool-output/ 中无残留临时文件

## 作业
完成全部 5 步。在回答中只输出：
- 最终报告路径
- QA 结果（行数、章节数、是否通过）
```

---

## 5. 输出文件管理

- 输出目录：`案例报告/`（`~/.opencode/skills/deep-research/案例报告/`）
- 文件名：`<主题>-YYYYMMDD-HHmmss.md`
- 日期锚定主题用当前年月日

### 清理机制（主 agent 执行）

```
调研结束后：
1. Task 3 内部已清理 $TMPDIR/chapters/
2. 主 agent 执行 rm -rf {TMPDIR}（清理大纲、数据池、中间文件）
3. 主 agent 确认 tool-output/ 无残留
```

---

## 6. 工具依赖速查

| 工具 | 用途 | 免费？ | 国内源？ |
|:----|:-----|:-----:|:--------:|
| `websearch_web_search_exa` | 主搜索引擎 | ❌ 付费 | 部分 |
| `scrapling_bulk_get/stealthy/fetch` | 全文抓取（本地运行） | ✅ | **✅ 推荐，国内源主力** |
| `webfetch` | A 类免费搜索 API 调用 | ✅ | ❌ 远端受限 |
| `bash` | date 时间戳 / 文件操作 | ✅ | — |
| `write` | 写文件 | ✅ | — |

**补强链路**：
```
Exa → A类搜索（DuckDuckGo/Bing/Semantic Scholar/GDELT via webfetch）
     → B类国内源（百度百科/199IT/艾瑞/东方财富/知乎/国统局 via Scrapling）
     → 全部 URL → Scrapling 批量抓取全文 → 数据池
```
