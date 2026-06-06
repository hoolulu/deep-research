### 你只需写一章
主题：[章节 title]
章节编号 N：[N]（例如第 4 章则 N=4）
总章节数 total：[total]（报告共有 N 章，用于估算本章字数上限）
数据池文件：{TMPDIR}/data-pool.json（用 jq 或 grep 提取本章相关子问题的 facts；字段名统一为 src/yr/met/val/u/ctx，quick 模式无 cur/conf，standard/deep 有）
注意事项文件：{TMPDIR}/cautions.json（含 ⚠️ 标记的事实列表，阅读后留意存疑/过时/冲突数据）
QA 工具：{TOOLSDIR}/dr_tools.py（通用检查脚本，自检时替代临时写 grep）

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
 - 正文段落 ≥ {模式对应段数} 段，数据表 ≥ 3 张
 - 字数控制：全文总上限 quick 10,000 / standard 16,000 / deep 28,000 字，本章目标 ≈ 上限÷total 章（如 quick 10,000÷6≈1,700 字/章），浮动 ±30% 内无需修改，超出范围在回答中注明"字数 X（目标 Y），需要装配阶段调整"即可
- 矛盾数据并排呈现而非掩盖

### 输出方式

**Step A — 生成章节骨架**（脚本从 data-pool 预提取本章相关事实，避免你大海捞针）：
```bash
python {TOOLSDIR}/dr_tools.py prepare-chapter \
  --outline {TMPDIR}/outline.json \
  --datapool {TMPDIR}/data-pool.json \
  --chapter [N] \
  --total [total] \
  --mode {调研模式}
```
输出示例（骨架含预填充的数据表和事实）：
```markdown
### N.1 本节标题
<!-- 相关事实（从 data-pool 预提取） -->
- 数据点A → [来源，年份]
- 数据点B → [来源，年份]
```

**Step B — 在骨架基础上填充内容**：将上述骨架写入 Python 变量，补充分析、论证、润色表格，使其成为完整章节。

**Step C — 使用 write 工具写入章节文件**：使用 `write` 工具创建 `{TMPDIR}/chapters/chapter-{N}.md`，写入填充完成的完整正文。

**Step D — 写入后自检**（缺一不可）：
☐ 编码洁净：`python {TOOLSDIR}/dr_tools.py check-encoding {TMPDIR}/chapters/chapter-{N}.md` 返回 PASS
☐ 子节编号合规：`python {TOOLSDIR}/dr_tools.py check-headers {TMPDIR}/chapters/chapter-{N}.md` 返回 PASS；同时确认 sections 数量匹配
☐ 子节数量匹配：子节数与 outline 中 sections 列表长度一致
☐ 核心判断：首段以 `>` 引用格式开头
☐ 段落达标：正文段落 ≥ {模式对应段数} 段
☐ 数据表达标：数据表 ≥ 3 张
☐ 来源可追溯：每个数字标注（机构，年份）
☐ 字数参考：`python {TOOLSDIR}/dr_tools.py word-count {TMPDIR}/chapters/chapter-{N}.md` 返回值参考 上限÷total 章 ±30%（如 quick 10,000÷10=1,000±300 字），超出范围不必重写，在回答末尾注明"字数 X（目标 Y±Z），超出范围，装配阶段处理"即可

**Step E — 自检通过后，使用 write 工具写入 manifest**：
使用 `write` 工具创建 `{TMPDIR}/chapters/chapter-{N}-manifest.json`，写入以下 JSON：
```json
{"chapter":N,"word_count":3580,"file_path":"{TMPDIR}/chapters/chapter-{N}.md"}
```
⚠️ **JSON 编码洁净**：`file_path` 必须使用**正斜杠 `/`**（如 `"D:/TEMP/dr-xxx/chapters/chapter-1.md"`），禁止使用反斜杠 `\`——Windows 反斜杠在 JSON 中属于非法转义序列，会导致主 agent 解析失败。

在回答中只返回文件路径。
**关键**：字数数据在 manifest 文件中，**不得写入章节正文文件**。
