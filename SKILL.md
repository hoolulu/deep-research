---
name: deep-research
description: "专业深度调研报告生成 — 5 阶段流水线：主 agent 调度 4 个子 agent Task + 1 轮主控并行派发，中间数据通过临时文件传递，不进主会话上下文。"
version: 1.1.0
updated: 2026-06-06
risk: medium
---

# deep-research

生成对标券商/第三方研究机构标准的深度调研报告。

- **架构**：主 agent 调度 4 个子 agent Task（大纲/数据/预检/装配）+ 1 轮主控并行派发章节，中间数据走临时文件
- **数据源**：Exa 搜索 → Scrapling 批量抓取（MCP，需注册，见安装说明）
- **安装**：见下方「安装与配置」
- **输出**：`$TMPDIR/outline.json`（临时，非最终报告）
- **最终报告**：保存到 skill 目录下的 `案例报告/`
- **参考文件**：`RULES.md`（硬约束/反模式）、`TYPES.md`（分类标准/编号规范）
- **容错原则**：调研不阻塞。所有脚本/命令调用必须有兜底路径。主路径失败 → 自动尝试替代方案（换 `sys.executable`/检查路径/直接 Python 实现）→ 三次失败后向用户报告具体问题。详见「容错原则」。

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
| 11 | **强制目录** | 报告正文前必须包含 `## 目录` 标题及自动目录（TOC），列出所有章节标题 |
| 12 | **元数据完整** | 报告头部必须包含 总字数、阅读时间、数据截至日期（精确到月）、报告生成具体时间（精确到秒）、调研模式、Skill版本 六个字段，用 ` · ` 隔开。另起一行 `> **参考来源**：{主要来源} 等 · 共引用 N 个来源`。报告末尾须附 `## 参考来源`（列出所有引用机构及链接）和 `## 免责声明`。版本号从本 skill 的 VERSION 文件读取。 |
| 13 | **篇幅达标** | quick ≥ 6 章 5 段/章 全文 ≤ 10,000 字｜standard ≥ 8 章 8 段/章 全文 ≤ 16,000 字｜deep ≥ 10 章 10 段/章 全文 ≤ 28,000 字 |
| 14 | **四段式结构** | 顺序固定为：报告标题 → 元数据块（含六字段 + 参考来源行） → `## 目录` → 正文各章 → 尾部（参考来源 + 免责声明） |
| 15 | **编码洁净** | 所有中间文件（outline.json / data-pool.json / chapter-*.md）必须使用 **UTF-8 无 BOM** 编码写入，不得出现替换字符（\ufffd）或 GBK→UTF-8 Mojibake。子 agent 在写入前必须自行验证编码洁净，不得将编码问题遗留到主 agent |

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
2. 记录任务开始时间：`Get-Date -Format "yyyy-MM-dd HH:mm:ss" > $TMPDIR/start_time.txt`（写入文件，后续所有 agent 均可读取）
3. 创建临时目录 TMPDIR（Windows: `New-Item -ItemType Directory -Path "$env:TEMP\dr-$([System.IO.Path]::GetRandomFileName())"`，Linux: `mktemp -d /tmp/dr-XXXX`）；同时确定 TOOLSDIR（tools/ 子目录）和 PROMPTSDIR（prompts/ 子目录），均相对于本 SKILL.md 所在目录
 4. todowrite 创建进度条目（标题只写"Task N — 目标"，不得包含 oracle/unspecified-high 等 agent 类型名）
 5. ══ Task 1 — 分析主题 + 生成大纲 ══
    → 读取 {PROMPTSDIR}/task1_oracle.md，替换 {TMPDIR} {TOOLSDIR}，注入 prompt
    → 等待返回 oracle 回答（不写文件，只输出 JSON 内容）
    → 从回答中提取 outline.json 内容，用 `write` 工具创建 {TMPDIR}/outline.json
    → 从回答中提取 manifest 内容，用 `write` 工具创建 {TMPDIR}/task1_manifest.json
    → 读取 {TMPDIR}/task1_manifest.json，提取 title + chapter_count
    → todowrite 标记完成
    → 向用户报告进度（"大纲已生成，N 章"）
 6. ══ Task 2 — 数据收集 + 结构化数据池 ══
    → 读取 {PROMPTSDIR}/task2_data_collection.md，替换 {TMPDIR} {TOOLSDIR}，注入 prompt
    → 等待返回 data-pool.json 路径
    → 读取 {TMPDIR}/task2_manifest.json，提取 source_count + fact_count + fetch_method
    → todowrite 标记完成
    → 向用户报告进度（"数据已收集，N 个来源，🔧 Scrapling/🌐 webfetch"）
 7. ══ Task 3 — 预检 + 验证 ══
    → 读取 {PROMPTSDIR}/task3_precheck.md，替换 {TMPDIR} {TOOLSDIR}，注入 prompt
    → 等待返回 cautions.json 路径
    → 读取 {TMPDIR}/task3_manifest.json + cautions.json，提取预检结果 + cautions 列表 + data_limited 标记
    → todowrite 标记完成
    → 向用户报告进度（"预检通过，开始撰写 N 章"）
 8. ══ Task 4 — 并行派发章节撰写 ══
    → 读取 {TMPDIR}/outline.json 获取 chapters 数组
    → 在一个循环内为每一章调用 task()，全部使用 run_in_background=true 一次性发出
    → 收集所有 background task ID
    → 发出所有章节后，统一等待全部完成
    → 汇总各章字数写入 {TMPDIR}/wordcounts.json（各章节 agent 返回时会输出 manifest JSON，其中含 word_count 字段。主 agent 已看到这些值，直接用 `write` 工具写入汇总 JSON，**禁止为做此事编写任何 Python 脚本**——`dr_tools.py` 未提供此聚合命令，正确的做法是用 `write` 直接写已知值。如果因为 manifest JSON 不标准而无法解析，责任在生成方，**不在主 agent**——主 agent 应直接回退到从 Task 4 子 agent 的返回输出中提取已知字数。如需验证，用 `python {TOOLSDIR}/dr_tools.py word-count {TMPDIR}/chapters/chapter-*.md` 逐个核验。）
    → todowrite 标记完成（每完成一章标记一个子项）
    → 向用户报告进度（"N 章撰写完成，进入装配"）
 9. ══ Task 5 — 装配 + QA + 清理 ══
    → 读取 {PROMPTSDIR}/task5_assembly.md，替换 {TMPDIR} {TOOLSDIR} {depth_mode} {target_year} {data_limited}，注入 prompt
    → 等待返回报告路径
    → 读取 {TMPDIR}/task5_manifest.json，提取 report_path + line_count + chapter_count + word_count + qa_passed
    → todowrite 标记完成
    → ⏱ **强制计算总耗时**（读取 start_time.txt + 当前时间算差值，不可跳过）：
      ```
      $start = Get-Content $TMPDIR/start_time.txt
      $end = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
      $totalMin = [math]::Round(([datetime]$end - [datetime]$start).TotalMinutes)
      ```
    → 从各 manifest 提取数据，按固定模板汇报最终结果（缺失任一字段即标为失败）：
      ```
      📋 大纲已生成：{task1_manifest.title} · {task1_manifest.chapter_count} 章 · {outline.json.depth_mode}
      📡 数据已收集：{task2_manifest.source_count} 个来源 · {task2_manifest.fact_count} 条事实 · {task2_manifest.fetch_method}
      📄 报告已生成：{task5_manifest.report_path} · {task5_manifest.line_count} 行 · {task5_manifest.chapter_count} 章 · {task5_manifest.word_count} 字 · ⏱ {totalMin} 分钟 · {task2_manifest.fetch_method}
      ```
    → todowrite 全部完成

**禁止**：不要在调度之间插入 Exa 搜索、数据读取、文件检查等操作。一切数据操作都在 Task 内部完成。

---

## 2. Task 1 — 主题分析 + 大纲（oracle）

**工具**：`task(subagent_type="oracle", ...)` | **一次调用**
**prompt 文件**：`prompts/task1_oracle.md`
**用法**：读取文件内容，替换 `{TMPDIR}` `{TOOLSDIR}` 为实际路径后注入 prompt。

**输出**：oracle 回答中包含 outline.json 和 manifest.json 的 JSON 内容，由主 agent 用 `write` 工具写入文件。oracle 自身不写文件（避免 PowerShell pipe 编码问题）。

---

## 3. Task 2 — 数据收集 + 结构化数据池（unspecified-high）

**工具**：`task(category="unspecified-high", load_skills=[], ...)`
**prompt 文件**：`prompts/task2_data_collection.md`
**用法**：读取文件内容，替换 `{TMPDIR}` `{TOOLSDIR}` 为实际路径后注入 prompt。

**输出**：{TMPDIR}/data-pool.json + {TMPDIR}/task2_manifest.json（使用 `write` 工具创建）

---

## 4. Task 3 — 预检 + 验证（unspecified-high）

**工具**：`task(category="unspecified-high", load_skills=[], ...)`

该子 agent 负责在章节撰写前对 data-pool.json 做数据质量检查，返回预检结果和注意事项。当数据量不足时标记 `data_limited=true`，传递给 Task 5 调整质量预期。

**prompt 文件**：`prompts/task3_precheck.md`
**用法**：读取文件内容，替换 `{TMPDIR}` `{TOOLSDIR}` 为实际路径后注入 prompt。

**输出**：{TMPDIR}/cautions.json + {TMPDIR}/task3_manifest.json（使用 `write` 工具创建）

### 章节 agent 指令模板（由 Task 4 主 agent 在派发时使用）

主 agent 在循环中为每章调用 `task()` 时，prompt 参数使用 `{PROMPTSDIR}/chapter_agent.md` 模板。

**用法**：读取 `{PROMPTSDIR}/chapter_agent.md`，替换以下变量：
- `[章节 title]` → 当前章的 title（从 outline.json chapters 数组读取）
- `[N]` → 当前章节编号（第 1 章为 1，第 2 章为 2...）
- `[total]` → chapters 数组总长度
- `[sections 列表]` → 当前章的 sections 数组（逗号分隔）
- `{模式对应段数}` → quick=5, standard=8, deep=10
- `{调研模式}` → quick / standard / deep（当前调研模式）
- `{TMPDIR}` → 运行时临时目录
- `{TOOLSDIR}` → tools 目录

**输出**：{TMPDIR}/chapters/chapter-{N}.md + {TMPDIR}/chapters/chapter-{N}-manifest.json（使用 `write` 工具创建）

---

## 5. Task 5 — 装配 + QA + 清理（unspecified-high）

**工具**：`task(category="unspecified-high", load_skills=[], ...)`

该子 agent 在所有章节写完后，负责装配最终报告、质量验收、清理中间文件。

**prompt 文件**：`prompts/task5_assembly.md`
**用法**：读取文件内容，替换 `{TMPDIR}` `{TOOLSDIR}` 为实际路径以及 `{depth_mode}` `{target_year}` `{data_limited}` 为对应值后注入 prompt。（`data_limited` 从 task3_manifest.json 读取，true/false）

**输出**：最终报告 + {TMPDIR}/task5_manifest.json（manifest 使用 `write` 工具创建）

---

## 6. 输出文件管理

### 路径优先级

最终报告保存路径按以下优先级判定：

1. **用户自定义路径** — 如果用户显式指定了输出目录（如 `D:\Reports\`），使用指定路径
2. **Skill 默认路径** — `案例报告/`（`~/.opencode/skills/deep-research/案例报告/`）

装配阶段（Step 3）根据实际使用的路径写入，文件名格式不变：`<主题>-YYYYMMDD-HHmmss.md`。

### QA 路径核验

Step 4 QA 必须确认报告文件的保存路径为上述两者之一，如果路径不属于默认目录且非用户指定目录，标记"路径异常"不通过。

### 日期锚定

文件名中的日期用当前年月日。

### 清理机制

```
Task 5 装配 + QA 通过后，内部已完成清理：
1. 清理中间文件 `{TMPDIR}` 目录：Windows 用 `Remove-Item -Recurse -Force "{TMPDIR}"`，Linux 用 `rm -rf {TMPDIR}`
2. 确认 tool-output/ 无残留
主 agent 不再独立执行清理步骤。
```

---

## 7. 工具依赖速查

| 工具 | 用途 | 免费？ | 国内源？ |
|:----|:-----|:-----:|:--------:|
| `websearch_web_search_exa` | 主搜索引擎 | ❌ 付费 | 部分 |
| `scrapling_bulk_get/stealthy/fetch` | 全文抓取（MCP，依赖 opencode.json 注册） | ✅ | **✅ 推荐，国内源主力** |
| `webfetch` | 抓取回退（Scrapling 不可用时替代） | ✅ | ❌ 远端受限，国内源效果一般 |
| `bash` | date 时间戳 / 文件操作 | ✅ | — |
| `write` | 写文件 | ✅ | — |

**补强链路**：
```
Exa → A类搜索（DuckDuckGo/Bing/Semantic Scholar/GDELT via webfetch）
     → B类国内源（百度百科/199IT/艾瑞/东方财富/知乎/国统局）
     → 全部 URL → 检测 Scrapling MCP 可用性
         ├─ 🔧 可用 → Scrapling 批量抓取全文 → 数据池
         └─ 🌐 不可用 → webfetch 逐个抓取全文（标注回退）→ 数据池
```

---

## 8. 安装与配置

### 前置条件

- Python 3.10+
- Scrapling（安装方式由 AI 根据官方文档和当前系统自动适配）
- Playwright（可选，用于 JS 渲染和反检测抓取）

### 注册 Scrapling MCP Server

Scrapling 通过 MCP（Model Context Protocol）与 AI agent 通信，需注册到 `opencode.json` 后才能被 agent 调用。

**推荐方式**：运行一次 `/research`，Task 2 在检测到 Scrapling 未注册时，会自动完成安装和注册。

**参考实现**：本项目提供了 `scrapling-mcp-server.py`（与本文件同目录），是一份标准 MCP Server 实现，覆盖了标准抓取、反检测抓取、JS 渲染抓取三种模式。AI 可根据本机环境参考此脚本，如有问题再参考 Scrapling 官方文档。

**手动注册格式**（在 `opencode.json` 的 `mcp` 中添加，供 AI 安装时参考）：
  ```json
  {
    "mcp": {
      "scrapling": {
        "type": "local",
        "command": ["<python-path>", "<mcp-server-script-path>"],
        "enabled": true
      }
    }
  }
  ```
  > 注意：OpenCode 使用 `"mcp"` 键（数组格式 `command`），非 Claude Desktop 的 `"mcpServers"`

### 重启 OpenCode

MCP Server 在 OpenCode 启动时加载，注册后**必须重启**才能生效。

### 验证是否生效

运行 `/research` 调研时，Task 2 阶段如显示 `🔧 Scrapling 抓取` 则表示 MCP 工作正常。若显示 `🌐 webfetch 抓取（Scrapling 已自动安装，重启后生效）` 则表示 Scrapling 已自动安装，重启 OC 后下次生效。若显示 `🌐 webfetch 抓取` 则表示安装失败，需检查 Python 环境和网络连接。

### 抓取回退说明

若 Scrapling 抓取某 URL 失败（WAF/超时/JS 渲染需求），会自动回退到 webfetch 孤立抓取该 URL，不影响其他 URL 的 Scrapling 抓取。若 Scrapling MCP 完全不可用，则全部走 webfetch。调研**不会阻塞**。
