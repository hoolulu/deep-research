# Opencode deep-research Skill

**OpenCode 深度调研报告生成 Skill。**

> **当前版本：** 见 [`VERSION`](VERSION) · [查看更新](https://github.com/hoolulu/deep-research/commits/main)

**一个命令，十几分钟，一份深度专业的调研报告。**

---

**非 OpenCode 独占。** Claude Code、Codex CLI、Cursor、Windsurf、Cline、Aider、Continue.dev 等主流 AI 编码工具读取本项目后稍作改造即可使用。

多 agent 编排（OpenCode 的 `task()`）思路通用，各平台有自己的等价机制，照猫画虎就行。Scrapling（Python 抓取库）和搜索 API 都是标准 Python/HTTP 工具，不绑定平台。Scrapling 是保证抓取效率和质量的核心依赖，推荐必装。

本 skill 的核心价值在于实现思路，而非适配某个特定工具。

如果你用不同的 CLI 工具，你可以定义任何搜索工具，或者在 Rules.md 和 Types.md 中修改对特定行业的需求。

注意，适配调研任何主题，不光是能做行业研报哦！看我出的案例报告就知道啦。

---

## 一、为什么你需要这个

让 AI 帮你做调研，你大概率碰过这些坑：

搜索 + 总结 → 太浅，出来几条摘要，没有纵深。  
行业报告按份收费 $50–500+ → 太贵，个人用不起。  
海外工具 → 搜不到国内资源如：百度百科、知乎、199IT、艾瑞。  
AI 编数字 → 看起来合理，但找不到来源。

这个 skill 走完 **4 层流程**才交报告。不是搜完就出，是析→搜验→写→验。

## 二、谁适合用

**独立开发者**、**独立研究者**、**小团队**。  
需要专业级调研能力，但不想依赖付费数据库或研究机构的人。

## 三、一次标准模式调研的输出

| 指标 | 数据（standard 模式示例） |
|------|-------------------------|
| 报告长度 | 500-700 行 / 约 12,000-18,000 字 |
| 数据表 | 15-25 张，覆盖市场规模、竞争格局、技术参数等多个维度 |
| 分析段落 | 80-120 段（每段含结论 + 数据 + 因果 + 判断） |
| 引用的独立机构 | 15-25 家（中国信通院、艾瑞咨询、国家统计局、百度百科、知乎、36氪、澎湃新闻等） |
| 反方观点 | 3-8 处，每章至少呈现一个争议或反对角度 |
| 数据收集 | ~1-3 分钟 |
| 报告生成 | ~8-15 分钟 |
| 总耗时 | ~10-20 分钟 |

> 以上为 standard 模式典型范围，实际因主题复杂度、数据可获取性、搜索引擎响应等因素有所浮动。|

📂 **[查看全部案例报告 →](案例报告/)** 点此浏览所有已生成的调研报告，可直接点击打开阅读。

## 四、工作逻辑

整个流程分 4 个阶段，按顺序自动执行：

```
① 分析大纲 — 分析主题，生成调研框架和搜索计划
         ↓
② 采集数据 — SearXNG / Exa 级联搜索 → Scrapling 批量抓取 → 数据池提取 → 数据质检
         ↓
③ 并行撰写 — 多章节同时撰写，事实直接嵌入 prompt，不做工具调用
         ↓
④ 验收装配 — 批量 validate → assemble-report → convert-citations → qa-report（主 agent 内联执行）
```

## 五、搜索链路与内置资源

所有工具已内置，无需额外购买。系统采用 **三层级联搜索** 策略：SearXNG（作者已部署的元搜索引擎，70+ 引擎含百度/Google/Brave）→ Exa（OMO 内置冷备）→ 十多个免费搜索引擎 + 国内数据源（最终兜底）。每层引擎检测通过即用，不继续探测下级，确保响应速度。整个流程如下：

```
Layer 1 — SearXNG（作者部署，70+ 引擎含百度/Google/Brave，开箱即用）
  ↓ 不可用时
Layer 2 — Exa（OMO 内置冷备，零费用）
  ↓ 不可用时
Layer 3 — 免费源补强（兜底）
  ├─ 搜索补强线      │  已知源补强线
  ├─ DuckDuckGo      │  百度百科 / 维基百科
  ├─ Bing 国内版     │  知乎 / 36氪 / 澎湃新闻
  ├─ Brave / Mojeek  │  199IT / 艾瑞咨询 / 东方财富
  ├─ Semantic Scholar│  国家统计局 / 微博 / CSDN
  └─ GDELT / arXiv   │  豆瓣 / 虎嗅
```

> 搜索补强线可**动态发现**任意其他网站，不限于上述列表。所有来源的 URL 最终统一由 Scrapling 批量抓取全文。

> 个人和机构的差距以前是"调研团队 + 付费数据库"。现在一个人 + 一个命令可以覆盖海内外全网公开信息。

## 六、报告独特亮点


| 维度          | 说明                         |
| ----------- | -------------------------- |
| **纯中文专业行文** | Oracle 直接写中文，不是英译中         |
| **每个数字有来源** | 正文标注 `[(N)](#refN)` 可点击引用，文末附参考来源列表。找不到来源的数字不写     |
| **正反观点并存**  | 每章呈现争议和反对观点，不回避矛盾             |
| **置信度分级**   | 末章汇总表（高/中/低），什么可靠什么有争议一目了然 |
| **数据防坑机制**    | 自动识别常见数据错误——单位搞混、数据造假、张冠李戴，不让有问题的数据混进报告 |
| **段落重于行数**  | 每章 8-12 段正文为核心，表格和空行灌不了水   |


## 七、三种深度


| 命令 | 用途 | 最少章数 | 最少段落/章 | 字数上限（字符） | 参考耗时 |
|------|------|---------|------------|----------------|---------|
| `/research 主题` | standard 默认 | 8 | ≥ 5 | ≤ 12,000 | ~10–15 min |
| `/research 主题 -quick` | 快速洞察 | 5 | ≥ 4 | ≤ 8,000 | ~8–12 min |
| `/research 主题 -deep` | 极致深度 | 10 | ≥ 6 | ≤ 25,000 | ~15–25 min |
> 以上参数见 `profiles.json`，修改该文件后重启软件即全局生效。字数 = 去掉空格和 Markdown 语法的纯字符数。

## 八、运行截图
<img width="1807" height="1449" alt="image" src="https://github.com/user-attachments/assets/f13fccef-dee1-43ef-a1bc-1aabda02b86f" />



## 九、安装

### 🧠 方式一：AI 傻瓜安装（推荐）

把下面这段提示词复制到 OpenCode 聊天框发送，AI 会自动完成一切：

```text
请调研 https://github.com/hoolulu/deep-research 项目，根据文档要求，依次完成：

1. 安装所有前置依赖（根据 Scrapling 官方文档和你当前的操作系统，自行确定安装方式并验证成功）
2. 注册 Scrapling MCP Server，并确保用户重启 CLI 工具后正常使用
3. 注册 /research 和 /research-update 命令

每完成一步都确认结果，所有步骤完成后读取 VERSION 文件确认版本号，并总结安装状态（哪些成功、哪些失败、下一步需要用户做什么）。
```

AI 会读取项目文档→理解系统类型→逐项安装→验证可用性。不需要手动执行任何命令。

### 🔧 方式二：非 OpenCode 用户（Claude Code / Codex CLI / Cursor 等）

把这段提示词粘贴到你的 AI 编码工具中：

```text
请调研 https://github.com/hoolulu/deep-research 项目，根据文档要求自动安装前置依赖，适配我的 CLI 工具。需要完成：

1. 安装 Python 和 Scrapling（根据 Scrapling 官方文档和你当前的操作系统自行确定安装方式并验证）
2. 注册 Scrapling MCP Server，并确保用户重启 CLI 工具后正常使用
3. 注册等价于 /research 和 /research-update 的自定义命令
4. 核心是理解多 agent 编排管道设计思路，把 Task 链式架构翻译成当前工具的等价实现

每完成一步确认结果，安装完成后读取 VERSION 文件确认版本号，并总结安装状态（哪些成功、哪些失败、下一步需要用户做什么）。
```

不同工具的适配点：多 agent 编排需映射到各自的原生机制（Claude Code 的 sub-agent、Codex CLI 的多文件任务、Cursor 的 agent 模式等），搜索和抓取逻辑（python-scrapling + 搜索 API）可原样复用。

### 还没有 OpenCode？

```bash
curl -fsSL https://opencode.ai/install | bash
```

装完再选上面的方式安装。

### 前置依赖


| 组件                                   | 用途                                       | 获取方式                                                                   |
| ------------------------------------ | ---------------------------------------- | ---------------------------------------------------------------------- |
| **OpenCode**                         | AI 编码 agent 运行时                          | `curl -fsSL [https://opencode.ai/install](https://opencode.ai/install) |
| **oh-my-openagent（OH-MY-OPENAGENT）** | 提供分析/搜索等子 agent + 自动配置 MCP | `opencode plugins add oh-my-openagent`                                 |
| **SearXNG**                         | 网页搜索（主力，作者已部署 70+ 引擎含百度/Google/Brave） | 内置默认端点，开箱即用                                      |
| **Exa MCP**                          | 网页搜索（冷备）                             | 由 OMO 自动配置                                                             |
| **Scrapling + MCP Server**           | 网页全文抓取                                   | `pip install scrapling` + AI 自动在 `opencode.json` 中注册 MCP 配置 |


> 本 skill 依赖 OH-MY-OPENAGENT 插件提供的子 agent。如果没有安装，`/research` 命令无法执行。

## 十、使用方法

安装并重启 OpenCode 后，在聊天框输入：

```
/research 你的主题             # standard 模式，~10-15 分钟
/research 你的主题 -quick       # quick 模式，~8-12 分钟
/research 你的主题 -deep        # deep 模式，~15-25 分钟
```

检查更新：`/research-update`

### 发送后会发生什么

整个流程自动运行，你不需要做任何操作：

```
① 分析大纲 — 分析主题，生成调研框架和搜索计划
② 采集数据 — SearXNG / Exa 级联搜索 → Scrapling 批量抓取 → 数据池提取 → 数据质检
③ 并行撰写 — 多章节同时撰写，事实直接嵌入 prompt，不做额外工具调用
④ 装配验收 — 批量 validate → assemble-report → convert-citations → qa-report（主 agent 直接执行，不派 sub-agent）
```

> 以上累计 ~10-20 分钟。复杂主题可能延长，简单主题可能缩短。

### 输出文件

报告以 Markdown 格式保存到 skill 目录下的 `案例报告/` 文件夹，文件名包含日期时间戳：

```
~/.opencode/skills/deep-research/案例报告/
```

可以用任何 Markdown 阅读器（Typora / Obsidian / VS Code 等）打开。

你也可以指定报告的存放路径，让 AI 帮你修改。

👉 **[浏览所有已生成的案例报告](案例报告/)** — 点击即可查看历史报告列表。

## 十一、成本


| 组件                       | 费用                                                                                                              |
| ------------------------ | --------------------------------------------------------------------------------------------------------------- |
| **LLM（你已经在用的）**          | **DeepSeek v4 Flash** 基准：quick 约 10–20 万 token / < 0.15 元，standard 约 15–35 万 / < 0.3 元，deep 约 30–60 万 / < 0.6 元 |
| **SearXNG 搜索（作者部署）** | 已部署在 VPS，零费用，无限畅用                                                                              |
| **Exa 搜索**               | OpenCode 内置，零额外费用（冷备引擎）                                                                                   |
| **Scrapling 抓取**         | 纯本地运行，零费用                                                                                                       |
| **国内源（百度百科/维基百科/知乎/36氪/澎湃/199IT/艾瑞/东方财富/国统局等）** | 直连零费用，不要代理                                                                                                      |
| **OpenCode 运行时**         | MIT 开源，零费用                                                                                                      |


> 以上 token 估算基于 DeepSeek v4 Flash。不同模型、不同复杂度的主题，Token 消耗和费用会有差异。仅供参考。

## 十二、FAQ

**1. 搜索额度？怎么保证搜索不中断？**

系统采用 **三层级联搜索** 架构，每层引擎各自独立，上层失效自动降级到下层：

- **Layer 1 — SearXNG（作者部署）**：作者在 VPS 上部署的元搜索引擎，聚合 70+ 搜索引擎（含百度/Google/Brave），中文英文全覆盖。内置默认端点，开箱即用，无限畅用、不限速、无额度限制。
- **Layer 2 — Exa（冷备）**：OpenCode 内置的搜索引擎，OMO 插件自动配置，零费用。如触发 rate limit，自动跳到 Layer 3。
- **Layer 3 — 免费源补强（最终兜底）**：DuckDuckGo / Bing / Brave / Mojeek / Semantic Scholar / GDELT / arXiv + 百度百科 / 知乎 / 199IT / 艾瑞 / 36氪 / 澎湃 / 东方财富 / 微博 / CSDN / 虎嗅 / 豆瓣 等 20+ 源。不依赖任何 API Key，永远可用。

**如果自己注册 Exa 的 API Key：**

免费注册 Exa（https://dashboard.exa.ai/api-keys），每月 1,000 次，不绑卡。设置环境变量：
```
$env:EXA_API_KEY = "你的exa-key"
```
设置后 Exa 额度变为你的个人配额（1,000次/月），绕过共享 Key 的 rate limit。

**2. 数据安全吗？**

所有处理在本地完成。不收集、不上传任何用户数据。

**3. 如何更新到最新版本？**

OpenCode 用户有两种方式：

- **AI 命令**：输入 `/research-update`，AI 自动对比本地和远程版本号，如有更新则执行 `git pull`
- **手动**：`cd ~/.opencode/skills/deep-research && git pull`

版本号可通过 `cat ~/.opencode/skills/deep-research/VERSION` 查看。

**4. 非 OpenCode 用户能自动更新吗？**

不能。`/research-update` 是 OpenCode 专属功能，其他 AI 编程工具没有对应的命令系统，没法一键更新。

你可以让 AI 帮你做版本对比和更新适配。把下面这段提示词粘贴到你的 AI 编码工具中：

```text
请调研 https://github.com/hoolulu/deep-research 项目的最新版本代码，对比当前本地已有代码的差异，找出自上次安装以来上游新增了哪些功能、修复了哪些问题，然后逐项应用到本地的适配版本中。注意保持你所在平台的适配改动不变，只合并上游的通用改进。
```

## License

MIT

本项目采用 MIT 协议。选择 MIT 而非 GPL/CC 等更严格的协议，是因为本项目的核心是一套可移植的方法论和管道设计，而非需要保护版权的成品库。MIT 能让它在不同平台和工具链中被最大化地复用和改造，与"非 OpenCode 独占"的定位一致。

---

> 社区讨论帖子：[LINUX DO](https://linux.do/t/topic/2312664)
