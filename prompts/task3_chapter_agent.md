### 你只需写一章
主题：[章节 title]
章节编号 N：[N]
总章节数 total：[total]
本章字数上限：{per_chapter_chars} 字符（来自 profiles.json）

**严禁写内联代码**（`python -c`、PowerShell 等）。字数统计只能用 `dr_tools.py word-count`。

### 标题规则（重要）
- **不要写 `##` 章节标题**——`## 一、章节标题` 由装配阶段自动添加，你只需写正文
- **子节标题使用 `### N.1`、`### N.2`… 格式**，其中 N 为上述章节编号。不可使用汉字编号
- 正文第一行直接是 `>` 核心判断（不要在前面空行留白）
- 标题是判断句（使用与主题一致的语言，英文主题用英文，中文主题用中文）

### 子节结构说明
本章预定义了以下子节：`[sections 列表]`。请严格按此列表划分，不可增减。

### 格式
- 使用与主题一致的语言（英文主题用英文，中文主题用中文），引用来源使用 `(N)` 格式对最终读者显示，但在撰写时使用 `[N]` 占位。例：`该市场2025年估值145亿美元[3]` 或 `The market was valued at $145B in 2025[3]`
- **不要在 [N] 后加链接**——引用转换和参考章节由 `convert_citations` 自动处理
- 表格中的 `[N]` 同样只写编号，不加链接
- 不要在正文中使用 `（机构，年份）` 格式
- 每章以 `>` 引用格式的核心判断开头
- 正文段落 ≥ {min_paragraphs} 段（整章合计），数据表 ≥ 3 张
- 字数上限 {per_chapter_chars} 字符。如需确认字数，**只准运行** `python {TOOLSDIR}/dr_tools.py word-count {TMPDIR}/chapters/chapter-{N}.md`，禁止写 inline PowerShell/Python 去算。
- 矛盾数据并排呈现而非掩盖

### 作业
直接使用 `write` 工具创建 `{TMPDIR}/chapters/chapter-{N}.md`，写入填充完成的完整正文。不需要运行任何工具，不需要创建 manifest 文件。

在回答中只返回文件路径。