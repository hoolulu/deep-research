### 你只需写一章
主题：[章节 title]
章节编号 N：[N]
总章节数 total：[total]
本章字数上限：{per_chapter_chars} 字（来自 profiles.json）

### 标题规则
- **章标题由装配阶段自动分配（一、二、三…），撰写时不要加任何章编号**
- **子节标题使用 `### N.1`、`### N.2`… 格式**，其中 N 为上述章节编号。不可使用汉字编号
- 标题是纯中文判断句

### 子节结构说明
本章预定义了以下子节：`[sections 列表]`。请严格按此列表划分，不可增减。

### 格式
- 纯中文，数字带来源（机构，年份）
- 每章以 `>` 引用格式的核心判断开头
- 正文段落 ≤ {max_paragraphs} 段（整章合计），数据表 ≥ 3 张
- 字数上限 {per_chapter_chars} 字，段落上限 {max_paragraphs} 段。如需确认字数，**只准运行** `python {TOOLSDIR}/dr_tools.py word-count {TMPDIR}/chapters/chapter-{N}.md`，禁止写 inline PowerShell/Python 去算。
- 矛盾数据并排呈现而非掩盖

### 作业
直接使用 `write` 工具创建 `{TMPDIR}/chapters/chapter-{N}.md`，写入填充完成的完整正文。不需要运行任何工具，不需要创建 manifest 文件。

在回答中只返回文件路径。