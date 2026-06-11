---
name: deep-research
description: "Professional deep research report generation — multi-agent collaboration with parallel chapter writing, automatic latest-data targeting, multilingual output, and built-in quality checks."
version: 3.0.0
updated: 2026-06-08
risk: medium
author: hoolulu
repository: https://github.com/hoolulu/deep-research
---


# deep-research

生成对标券商/第三方研究机构标准的深度调研报告。

- **架构**：主 agent 调度 4 个子 agent Task（大纲/数据/预检/装配）+ 1 轮主控并行派发章节，中间数据走临时文件
- **数据源**：在线模式 → SearXNG（Layer 1） + sources.json 优质源搜索（Layer 2）并行 → 按质量触发免费源补强（Layer 3 兜底）→ Scrapling 批量抓取；离线模式 → 用户指定的本地文件（md/txt/pdf/docx）
- **安装**：见下方「安装与配置」
- **输出**：`$TMPDIR/outline.json`（临时，非最终报告）
- **最终报告**：保存到 skill 目录下的 `reports/`
- **参考文件**：`RULES.md`（硬约束/反模式）、`TYPES.md`（分类标准/编号规范）、**`profiles.json`（三档模式参数，修改后重启软件即全局生效）**
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
| 13 | **篇幅达标** | 见项目根目录 [`profiles.json`](profiles.json)。所有模式限制以 `profiles.json` 为准，修改后重启软件即全局生效。 |
| 14 | **四段式结构** | 顺序固定为：报告标题 → 元数据块（含六字段 + 参考来源行） → `## 目录` → 正文各章 → 尾部（参考来源 + 免责声明） |
| 15 | **编码洁净** | 所有中间文件（outline.json / data-pool.json / chapter-*.md）必须使用 **UTF-8 无 BOM** 编码写入，不得出现替换字符（\ufffd）或 GBK→UTF-8 Mojibake。子 agent 在写入前必须自行验证编码洁净，不得将编码问题遗留到主 agent |
| 16 | **纯文本公式** | 报告中不得使用 LaTeX/math 公式语法（`$...$`、`$$...$$`、`\[...\]` 等）。公式必须用纯文本或 Unicode 符号表达，确保复制到任何编辑器都不产生渲染问题 |

### 时间锚定规则

所有主题默认以 `{CURRENT_YEAR}` 为目标搜索最新数据。时间锚定模式在 Task 1 中由大纲 agent 按以下规则判定：

| 模式 | 符号 | 判定条件 | target_year | 验收 |
|:----|:-----|:---------|:-----------|:-----|
| `latest`（默认） | ⏳ | **所有主题的默认值**，除非符合 relaxed 或 user_specified | `{CURRENT_YEAR}` | 严格：≥50% 数据来自当年/前一年 |
| `relaxed`（放宽） | 🔓 | 指南/教程/概念类主题，或用户问历史/原理（"草书发展""起源""背景"） | `{CURRENT_YEAR}` | 宽松：标记旧数据但不过滤 |
| `user_specified` | 📌 | 用户提问显式指定了年份/月份（"2025年""2026Q1""2020年至今"） | **用户的指定年份** | 硬约束：>50% 匹配用户指定时间 |

> `{CURRENT_YEAR}` 是动态变量，运行时通过 `date +%Y` 解析，无需手动修改。

---

## 1. 主 agent 调度流程

**⚠️ CRITICAL — DO NOT SPEAK BEFORE LANGUAGE DETECTION**
> Your VERY FIRST action (before anything else) must be: detect language → set `$LANG`.
> Output NOTHING to the user until `$LANG` is set — no thinking aloud, no status messages.
> After language is detected, ALL output must be in `$LANG`. Period.
>
> **IMPORTANT: Clean the topic before detection** — the user input may contain framework wrapper text (e.g. "请使用... skill 执行...用户输入如下："). Strip all wrapper text and pass ONLY the clean research topic. For example from "请使用...用户输入如下：Quantum computing market outlook -quick" extract only "Quantum computing market outlook".

```
你（主 agent）的完整流程：

══ Setup (必须先执行) ══

 → 创建一个带时间戳的临时目录作为 TMPDIR（例如 D:\TEMP\opencode\deep-research-YYYYMMDD-HHMMSS）
 → 同时确定 TOOLSDIR（本 skill 的 tools/ 目录）和 PROMPTSDIR（本 skill 的 prompts/ 目录）
 → 读取本 SKILL.md + RULES.md + TYPES.md

══ Step 0 — Language Detection (output nothing before detection) ══

 → Clean topic: strip wrapper text, keep only the user's actual research topic
 → Determine language: analyze the cleaned topic and pick the ISO 639-1 code:
   zh (Chinese), en (English), ja (Japanese), ko (Korean), ru (Russian),
   ar (Arabic), hi (Hindi), vi (Vietnamese), th (Thai), tr (Turkish),
   es (Spanish), fr (French), de (German), pt (Portuguese), it (Italian),
   nl (Dutch), sv (Swedish), pl (Polish), id (Indonesian)
   → If unsure, default to "en".
   → Do NOT output anything during this step.
 → Write language code: use `write` tool to create {TMPDIR}/language.txt with the ISO code
 → Set `$LANG` = language code from the step above
  → **从这一行开始，所有面向用户的输出必须使用 $LANG。SKILL.md 的指令是中文写的（为了让我读懂），但你的输出绝不能跟着用中文。你读到中文指令时意识上翻译一下再输出。**
  → Announce detected language to the user (single line, in $LANG, e.g. "🌐 Language detected: en")

══ 主流程 ══

 1. ══ 离线模式判定（Step 0.5） ══
    → 你已经读取了用户原始输入。用自然语言理解判断用户关于数据来源的意图，不要用关键词匹配：
      - 用户是否提到了本地文件/目录/资料？
      - 用户是否明确要求不要联网？
      - 用户是否明确要求联网补充？
    → 判断逻辑：
      - 提到本地文件 +（未说联网 / 不联网）→ 离线模式，跳过搜索
      - 提到本地文件 + 说"联网补充" → 正常流程（搜+读本地）
      - 未提本地文件 → 正常流程
    → 离线模式 + 有路径 → {TMPDIR}/offline_mode.txt，`offline_mode=true`，向用户报告单行说明
    → 离线模式 + 无路径 → 回复用户询问路径，不继续
    → 正常模式 → `offline_mode=false`
 2. 记录任务开始时间到 {TMPDIR}/start_time.txt
 3. todowrite 创建进度条目（使用 $LANG 语言）
  4. ══ Task 1 — 分析主题 + 生成大纲 ══
     → 读取 {PROMPTSDIR}/task1_outline.md，替换 {TMPDIR} {TOOLSDIR} {LANG} {CURRENT_YEAR}，注入 prompt
     → **只做变量替换，不添加语言、格式、报告结构等额外指令。语言已由 Step 0 判定为 $LANG 并在 prompt 中替换 {LANG}。**
     → 派发 task()，等待完成
     → 用 `read` 确认 {TMPDIR}/outline.json 存在
     → 从 outline.json 读取 title + chapter_count + depth_mode
    → todowrite 标记完成
    → 向用户报告进度（使用 $LANG 语言）
  6. ══ Task 2 — 数据收集 + 结构化数据池 ══
     → 读取 {PROMPTSDIR}/task2_data_collection.md
     → 替换标准变量 {TMPDIR} {TOOLSDIR} {LANG} {COUNTRY}
     → 如果 `offline_mode=true`，额外替换：
       {OFFLINE_MODE} → true
       {LOCAL_PATHS} → 读取 {TMPDIR}/offline_mode.txt 的内容（路径列表）
     → 如果 `offline_mode=false`，替换 {OFFLINE_MODE} → false，{LOCAL_PATHS} → 空字符串
     → 派发 task()，等待返回
    → 如失败（task 报错或 task2_manifest.json 不存在），**自动重试 1 次**，重新派发。第二次仍失败则向用户报告并终止
     → 读取 {TMPDIR}/task2_manifest.json，提取 source_count + fact_count + search_engine + fetch_method + engines + free_fallback + english_fallback + unique_domains
    → todowrite 标记完成
    → 向用户报告进度（使用 $LANG 语言）
     7. ══ Task 3 — 派发章节撰写 ══
     → 读取 {TMPDIR}/outline.json 获取 chapters 数组；读取 {TMPDIR}/data-pool.json
     → **读取 `profiles.json` 获取当前模式的 `max_chars`**，计算 `per_chapter_chars = max_chars ÷ chapters.length`
     → 从 data-pool.json 提取所有唯一 (src, yr) 组合，按首次出现顺序预分配引用编号 [1], [2], [3]...，写入 {TMPDIR}/citation_map.json
     → 读取 `{PROMPTSDIR}/task3_chapter_agent.md` 模板
     → **根据 $LANG 裁剪 prompt 中的多语言段落**：
       - prompt 中的 `[LANG_en]` 段落：仅当 $LANG=en 时保留，其他语言删除
       - prompt 中的 `[LANG_zh]` 段落：仅当 $LANG=zh 时保留，其他语言删除
       - 删除标记文本本身（`[LANG_en]` `[/LANG_en]` 占位符行）
       - 无标记的段落全部语言通用，保留
     → **平台检测并选择撰写模式**：
       - 执行 `uname -s` 检测操作系统
       - 输出包含 "Darwin" → macOS → 设 `$PLATFORM_MODE=serial`
       - 否则 → 其他平台 → 设 `$PLATFORM_MODE=parallel`
       - 向用户报告平台和采用的撰写模式（使用 $LANG 语言）
        - **章节 agent 不做任何工具调用**（不跑 prepare-chapter、validate、manifest、word-count），只写文件

     → [serial mode — 严格串行] 一次只写一章（依赖进度文件防续对话并行）：
        - 读取 {TMPDIR}/serial_progress.txt：
          - 文件不存在或为空 → 从第 1 章开始
          - 内容为 "N"（数字） → 从第 N+1 章开始
          - 如果 N ≥ chapters.length → 所有章节已完成，进入 Task 4
        - 当前章编号 = 上一步确定的值（命名为 C）
        - 只写这一章：
          - 读取 outline.chapters[C] 的 title、sections
          - 从 data-pool.json 中筛选该章 sub_questions 对应的事实条目
          - **将事实直接嵌入 prompt**：每条事实前标注预分配的 `[C]` 编号
          - 调用 task(run_in_background=false) 同步等待该章完成
          - 用 `read` 确认 {TMPDIR}/chapters/chapter-{C}.md 存在且非空
        - 完成后用 `write` 工具创建/更新 {TMPDIR}/serial_progress.txt，写入 C
        - todowrite 标记该章 completed
        - 如果 C < chapters.length → 结束 response，等待用户继续
        - 如果 C ≥ chapters.length → 删除 serial_progress.txt，进入 Task 4
        → **严禁一次发起多章 task() 调用，严禁使用 run_in_background=true**

     → [parallel mode — 非 macOS] 并行派发：
       - 初始化空列表 task_ids = []
       - For N = 1 to chapters.length:
         - 读取 outline.chapters[N] 的 title、sections
         - 从 data-pool.json 中筛选该章 sub_questions 对应的事实条目
         - **将事实直接嵌入 prompt**：每条事实前标注预分配的 `[N]` 编号
         - 调用 task(run_in_background=true) 并行派出每章
         - 从 task 返回的元数据中提取 background_task_id（格式 bg_xxx），追加到 task_ids
         - todowrite 标记该章 in_progress
       - 将 task_ids 写入 {TMPDIR}/task3_bg_ids.json（持久化，防止主 agent 中断后丢失状态）
       - 向用户报告："已并行派出 {N} 章，等待全部完成..."（使用 $LANG 语言）
       - **结束 response，等待系统通知。仅当收到 [ALL BACKGROUND TASKS COMPLETE] 通知时，才继续到 Round 2。中间的单章完成通知忽略不处理。**
       - 然后进入 Round 2：

       **Round 2 — 收集结果 + 失败重写**：
       - 读取 {TMPDIR}/task3_bg_ids.json 获取所有 background_task_id
       - For 每个 bg_task_id in task_ids:
         - 调用 background_output(task_id=bg_task_id) 收集章节结果
       - 用 `read` 逐一确认 {TMPDIR}/chapters/chapter-{N}.md 是否存在且非空
       - 如果有章节缺失或内容为空：
         - 记录失败章节编号列表
         - **串行重写**：对每个失败章节逐一重新派发 task(run_in_background=false)，同步等待完成
         - 再次用 `read` 确认
       - todowrite 标记每章 completed
       - 向用户报告最终章节完成情况（使用 $LANG 语言）
     8. ══ Task 4 — 验证 + 装配 + QA（**主 agent 直接执行**） ══
    → **Step 0 — 清理残留**：删除 reports/ 目录下所有 0 字节文件（前次装配失败的空壳）；创建 reports/$LANG/ 子目录（如果不存在）
     → **Step 1 — 批量验证**：`python {TOOLSDIR}/dr_tools.py validate-all-chapters --chapters-dir {TMPDIR}/chapters/ --chapters {chapter_count}`，内部 ThreadPoolExecutor 并行验证所有章节。从输出 JSON 的 `failed_chapters` 中找到失败章节，逐个重新生成（重新派发章节 agent → 重新验证该章）。
     → **Step 1b — 章节深度均衡检查**：`python {TOOLSDIR}/dr_tools.py depth-balance --chapters-dir {TMPDIR}/chapters/ --chapters {chapter_count}`。如果某章行数 < 平均值的 50%，标记告警（not blocking，仅提示）。
     → Step 1 或 Step 2 失败时，**先删除本次已写入的产物**（报告文件、中间文件等），再重新执行对应步骤，避免残留文件干扰下次运行
    → **Step 2 — 装配**：`python {TOOLSDIR}/dr_tools.py assemble-report --outline {TMPDIR}/outline.json --chapters-dir {TMPDIR}/chapters/ --datapool {TMPDIR}/data-pool.json --mode {depth_mode} --target-year {target_year} --output reports/$LANG/ --lang $LANG`
    → **Step 3 — 数据受限处理**：读取 {TMPDIR}/task2_manifest.json 的 `data_limited` 字段。如果为 true，在报告标题后插入数据说明声明，**使用 $LANG 语言**。
    → **Step 4 — 引用处理**：`python {TOOLSDIR}/dr_tools.py convert-citations --datapool {TMPDIR}/data-pool.json "$REPORT" --lang $LANG`（从 data-pool 构建参考章节，验证正文 `[N]` 引用均有对应条目）
     → **Step 5 — QA**：`python {TOOLSDIR}/dr_tools.py qa-report "$REPORT" --mode {depth_mode} --target-year {target_year} --lang $LANG`，解析 JSON 输出，从 `checks.word_count.count` 取字数，从 `checks.word_count.limit` 取上限
    → todowrite 标记完成
    → ⏱ **强制计算总耗时**（读取 start_time.txt + 当前时间算差值）
    → 从 outline.json + task2_manifest.json + qa-report 中提取数据，使用 $LANG 语言汇报最终结果。

      **语言自适应标签映射表**（以下所有 <词> 根据 $LANG 替换）：

      | 中文 | en | ja | ko | fr | de | es | 其余语言 |
      |------|----|----|----|----|----|----|---------|
      | 执行总结 | Execution Summary | 実行サマリー | 실행 요약 | Résumé exécutif | Zusammenfassung | Resumen ejecutivo | Execution Summary |
      | 阶段 | Stage | 段階 | 단계 | Phase | Phase | Fase | Stage |
      | 详情 | Detail | 詳細 | 세부 | Détail | Detail | Detalle | Detail |
      | 大纲/Plan | Plan | 概要 | 개요 | Plan | Plan | Plan | Plan |
      | 观点速览/Insight | Insight | 洞察 | 인사이트 | Aperçu | Einblick | Perspectiva | Insight |
      | 数据/Data | Data | データ | 데이터 | Données | Daten | Datos | Data |
      | 报告/Report | Report | レポート | 보고서 | Rapport | Bericht | Informe | Report |
      | 章 | ch | 章 | 장 | chap. | Kap. | cap. | ch |
      | 来源 | sources | ソース | 출처 | sources | Quellen | fuentes | sources |
      | 事实 | facts | 事実 | 사실 | faits | Fakten | datos | facts |
      | 独立域名 | domains | ドメイン | 도메인 | domaines | Domains | dominios | domains |
| 行 | lines | 行 | 줄 | lignes | Zeilen | líneas | lines |
| 字 | chars | 語 | 단어 | mots | Wörter | palabras | chars |
      | 分钟 | min | 分 | 분 | min | Min. | min | min |
      | 生成时间 | Generated | 生成時刻 | 생성 시간 | Généré le | Erzeugt | Generado | Generated |
      | 搜索 | Search | 検索 | 검색 | Recherche | Suche | Búsqueda | Search |
      | 数据充足 ✓ | Adequate ✓ | 十分 ✓ | 충분 ✓ | Suffisantes ✓ | Ausreichend ✓ | Adecuado ✓ | Adequate ✓ |
      | 数据受限 ⚠ | Limited ⚠ | 制限 ⚠ | 제한 ⚠ | Limitées ⚠ | Eingeschränkt ⚠ | Limitado ⚠ | Limited ⚠ |
      | 免费源补强 | free fallback | 無料補強 | 무료 보강 | sources gratuites | kostenlose Quellen | fuentes gratuitas | free fallback |
      | 本地文件 | local files | ローカル | 로컬 파일 | fichiers locaux | lokale Dateien | archivos locales | local files |

      **搜索策略描述拼接规则**（使用映射表中的翻译）：

      ```
      IF offline_mode=true:
        <搜索词>：{offline_$LANG}
      ELSE:
        engines_names = engines 数组元素大写（["searxng"] → "SearXNG"）
        desc = engines_names
        IF free_fallback=true: desc += " (+{free_fallback_$LANG})"
        IF english_fallback=true: desc += " (+EN)"
        <搜索词>：{desc}
      ```

      **数据质量徽标规则**：

      ```
      IF data_limited=true: <质量词> = {limited_$LANG}
      ELSE: <质量词> = {adequate_$LANG}
      ```

      严格按以下结构输出：

      ```
      📊 **<执行总结词>**

      | <阶段词> | <详情词> |
      |:----|:------|
      | 📋 <Plan词> | {outline.title} · {outline.chapter_count} <章词> · {outline.depth_mode} |
      | 🎯 <Insight词> | {outline.chapters[0].description} |
      | 📡 <Data词> | {task2_manifest.source_count} <来源词> · {task2_manifest.unique_domains} <独立域名词> · {task2_manifest.fact_count} <事实词> · <搜索词>：{search_desc} · {task2_manifest.fetch_method} · {data_quality_badge} |
      | 📄 <Report词> | {REPORT} |
      |       | {qa_report.line_count} <行词> · {qa_report.word_count} <字词> · ⏱ {totalMin} <分钟词> · <生成时间词>：{gen_time} |
      ```

      其中：
      - `{outline.chapters[0].description}` = 从 outline.json 读取第 1 章（核心观点）的 description 字段，作为观点速览摘要
      - `{gen_time}` = 读取 {TMPDIR}/start_time.txt 中的任务开始时间，格式化为 `YYYY-MM-DD HH:mm:ss`
      - `{REPORT}` 仅输出最终报告路径（`reports/{LANG}/xxx.md`），不包含任何 TMPDIR 中间路径
      - `{search_desc}` = 按搜索策略拼接规则生成，所有中文词根据 $LANG 翻译
      - `{data_quality_badge}` = 按数据质量徽标规则生成
    → todowrite 全部完成

**禁止**：主 agent 不得在 Task 调度之间自行执行搜索引擎调用或数据处理。搜索/抓取归 Task 2，大纲生成归 Task 1，章节撰写归 Task 3，装配验证归 Task 4。Task 间的 handoff 文件读取（outline.json、task2_manifest.json 等）不受此限。

---

## 2. Task 1 — 主题分析 + 大纲

**工具**：`task()` | **一次调用**
**prompt 文件**：`prompts/task1_outline.md`
**用法**：读取文件内容，替换 `{TMPDIR}` `{TOOLSDIR} {LANG} {CURRENT_YEAR}` 为实际值后注入 prompt。

**输出**：大纲 agent 直接用 `write` 工具创建 `{TMPDIR}/outline.json`。主 agent 通过 `read` 确认文件存在。

---

## 3. Task 2 — 数据收集 + 结构化数据池（unspecified-high）

**工具**：`task(category="unspecified-high", load_skills=[], ...)`
**prompt 文件**：`prompts/task2_data_collection.md`
**用法**：读取文件内容，替换 `{TMPDIR}` `{TOOLSDIR}` `{LANG}` `{COUNTRY}` `{OFFLINE_MODE}` `{LOCAL_PATHS}` 为实际值后注入 prompt。

**输出**：{TMPDIR}/data-pool.json + {TMPDIR}/task2_manifest.json（使用 `write` 工具创建）

**LANG→COUNTRY 映射**（用于替换 `{COUNTRY}`）：zh→CN, en→US, ru→RU, ja→JP, ko→KR, fr→FR, de→DE, es→ES, pt→PT, it→IT, nl→NL, sv→SE, pl→PL, id→ID, th→TH, tr→TR, vi→VN, ar→SA, hi→IN。未覆盖的语言用空字符串。

---

## 3. Task 3 — 章节撰写 & 章节 agent 指令模板

主 agent 在循环中为每章调用 `task()` 时，prompt 参数使用 `{PROMPTSDIR}/task3_chapter_agent.md` 模板。

**用法**：读取 `{PROMPTSDIR}/task3_chapter_agent.md`，替换以下变量：
- `[章节 title]` → 当前章的 title（从 outline.json chapters 数组读取）
- `[N]` → 当前章节编号（第 1 章为 1，第 2 章为 2...）
- `[total]` → chapters 数组总长度
- `[sections 列表]` → 当前章的 sections 数组（逗号分隔）
- `{per_chapter_chars}` → `profiles.json` 中当前模式的 `max_chars ÷ 总章数`（主 agent 一次性算好）
- `{min_paragraphs}` → `profiles.json` 中当前模式的 `min_paragraphs`
- `{调研模式}` → quick / standard / deep（当前调研模式）
- `{TMPDIR}` → 运行时临时目录
- `{TOOLSDIR}` → tools 目录

**输出**：{TMPDIR}/chapters/chapter-{N}.md（使用 `write` 工具创建）

---

## 4. Task 4 — 验证 + 装配 + QA（主 agent 直接执行）

装配、引用转换、QA 检查均由主 agent 通过 bash 命令直接执行 `{TOOLSDIR}/dr_tools.py` 完成：

1. `validate-all-chapters` → 批量结构验证（并行）
2. `assemble-report` → 生成报告
3. `convert-citations` → 引用转换
4. `qa-report` → 质量检查

**清理**：装配完成后主 agent 执行 `Remove-Item -Recurse -Force "{TMPDIR}"` 清理临时文件。

---

## 6. 输出文件管理

### 路径优先级

最终报告保存路径按以下优先级判定：

1. **用户自定义路径** — 如果用户显式指定了输出目录（如 `D:\Reports\`），使用指定路径
2. **Skill 默认路径** — `reports/`（`~/.opencode/skills/deep-research/reports/`）

装配阶段（Step 3）根据实际使用的路径写入，文件名格式不变：`<主题>-YYYYMMDD-HHmmss.md`。

### QA 路径核验

Step 4 QA 必须确认报告文件的保存路径为上述两者之一，如果路径不属于默认目录且非用户指定目录，标记"路径异常"不通过。

### 日期锚定

文件名中的日期用当前年月日。

### 清理机制

```
Task 4 装配 + QA 通过后，内部已完成清理：
1. 清理中间文件 `{TMPDIR}` 目录：Windows 用 `Remove-Item -Recurse -Force "{TMPDIR}"`，Linux 用 `rm -rf {TMPDIR}`
2. 确认 tool-output/ 无残留
```

---

## 7. 工具依赖速查

| 工具 | 用途 | 免费？ | 国内源？ |
|:----|:-----|:-----:|:--------:|
| SearXNG (webfetch) | 主搜索引擎（Layer 1，自建） | ✅ 自建零费用 | ✅ 70+引擎含百度/搜狗 |
| `scrapling_bulk_get/stealthy/fetch` | 全文抓取（MCP，依赖 opencode.json 注册） | ✅ | **✅ 推荐，国内源主力** |
| `webfetch` | 抓取回退（Scrapling 不可用时替代） | ✅ | ❌ 远端受限，国内源效果一般 |
| `bash` | date 时间戳 / 文件操作 | ✅ | — |
| `write` | 写文件 | ✅ | — |

**搜索链路**：
```
SearXNG（Layer 1 自建主力，70+引擎） + sources.json 优质源搜索（Layer 2）并行
     ↓ 搜索结果质量不足时触发
免费源补强（Layer 3 兜底）
     ↓
A类搜索（DuckDuckGo/Bing/Semantic Scholar/GDELT via webfetch）
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

---

## 9. 跨平台编码规范（Windows/macOS/Linux）

### 问题根因

Windows PowerShell 5.1 控制台编码为 CP936（GBK 中文编码），**无法表示 18 种非英语语言**：
俄语西里尔字母、日语假名/汉字、韩语谚文、阿拉伯语、泰语、印地语天城文、越南语调号、
以及德语 äöüß、法语 éèêç、西班牙语 ñ 等拉丁扩展字符——通过 shell 传参/pipe 时全部损坏。

macOS/Linux 的终端默认 UTF-8，无此问题。

### 硬性规则（所有 agent 必须遵守）

| # | 规则 | 正确做法 | 错误做法 |
|---|------|---------|---------|
| 1 | **非 ASCII 文本不进 shell argv/pipe** | 用 `write` 工具写文件 → Python `--file` 读取 | Python 脚本 argv 传非 ASCII 文本 ❌ |
| 2 | **所有文件读写用 UTF-8** | Python 统一 `encoding='utf-8-sig'`（BOM 容错） | 依赖 shell 编码 |
| 3 | **写文件只用 `write` 工具** | `write` 工具 → UTF-8 无 BOM | PowerShell `Set-Content -Encoding UTF8` ❌（会加 BOM） |
| 4 | **Python stdout 显式设 UTF-8** | `sys.stdout.reconfigure(encoding='utf-8')` | 依赖系统默认编码 |
| 5 | **Python 子进程输出用 `--output` 文件** | `python script.py --input file --output result` | shell 重定向 `> result.txt` ❌（CP936 编码输出） |

### 一劳永逸方案：全链路编码安全架构

```
 ┌─ 数据来源 ──────────────────────────────────┐
 │ write 工具 / Python open(..., 'w', encoding) │ ← UTF-8 无 BOM
 └──────────────┬──────────────────────────────┘
                ▼
 ┌─ 中间文件 ──────────────────────────────────┐
 │ *.json / *.md : 全部 UTF-8（BOM 容错读取）     │ ← utf-8-sig 代码编
 └──────────────┬──────────────────────────────┘
                ▼
 ┌─ Python 处理 ───────────────────────────────┐
 │ 所有脚本入口设 `stdout.reconfigure('utf-8')` │ ← 输出安全
 │ 所有文件读用 `encoding='utf-8-sig'`         │ ← 输入安全
  │ Python 脚本统一用 `--input`/`--output` 参数   │ ← 完全绕过 shell
 └──────────────┬──────────────────────────────┘
                ▼
 ┌─ 最终输出 ──────────────────────────────────┐
 │ 报告文件 : UTF-8 无 BOM，任意语言均可正确显示    │
 └─────────────────────────────────────────────┘
```

### 当前防护状态

| 文件 | 防护措施 | 状态 |
|------|---------|:----:|
| `dr_tools.py` | 入口 `stdout.reconfigure` + 所有读操作用 `utf-8-sig` | ✅ |
| `dr_check.py` | 所有读操作用 `utf-8-sig` | ✅ |
| `dr_gen.py` | 所有读操作用 `utf-8-sig`，写操作用 `utf-8`（无 BOM） | ✅ |

---

**Created by [hoolulu](https://github.com/hoolulu)** · [github.com/hoolulu/deep-research](https://github.com/hoolulu/deep-research)
