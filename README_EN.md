# deep-research Skill

[🇨🇳 中文](README.md) · 🇬🇧 English

**Professional deep research report generation Skill · Supports 19 languages**

> **Current version:** [View updates](https://github.com/hoolulu/deep-research/commits/main)

---

### ✨ At a Glance

| | |
|---|---|
| 🎯 **One command** | `/research <topic>` → fully automated research, zero manual intervention |
| ⏱ **Report in ~10 min** | quick mode ~8–12 min, standard ~10–15 min |
| 🌍 **19 languages** | Auto-detects topic language, generates report in the same language |
| 🔧 **Not OpenCode-exclusive** | Adaptable for Claude Code, Cursor, Codex CLI, Windsurf, Cline and more |

| Command | Output |
|---------|--------|
| `/research 中国新能源汽车产业发展现状` | 中文报告 |
| `/research Competitive landscape of AI cloud computing` | English report |
| `/research Анализ рынка нефти и газа в России` | Отчёт на русском |
| `/research 日本のアニメ産業のグローバル市場戦略` | 日本語レポート |
| `/research 한국 반도체 산업의 글로벌 경쟁력 분석` | 한국어 보고서 |

> It interacts with you entirely in the language you set and searches for materials in that target language — not a simple translation pipeline.

---

## 1. Why You Need This

If you've ever asked AI to do research, you've likely hit these walls:

- Search + summarize → too shallow, just a few bullet points
- Industry reports at $50–500+ each → too expensive for individuals
- Overseas tools → can't search Chinese sources like Baidu Baike, Zhihu, 199IT, iResearch
- AI fabricates numbers → looks reasonable but has no traceable source

This skill follows a **4-stage pipeline** before delivering a report. Not search-and-dump — it's analyze → search+verify → write → verify.

## 2. Who It's For

**Indie developers**, **independent researchers**, **small teams**.
People who need professional-grade research capabilities without relying on paid databases or research institutions.

## 3. Typical Output (Standard Mode)

| Metric | Data (standard mode example) |
|--------|------------------------------|
| Report length | 500-700 lines / ~12,000-18,000 chars |
| Data tables | 15-25, covering market size, competitive landscape, technical specs |
| Analysis paragraphs | 80-120 (each with conclusion + data + causation + judgment) |
| Unique sources cited | 15-25 (Chinese and international institutions) |
| Opposing viewpoints | 3-8, at least one controversy per chapter |
| Data collection | ~1-3 min |
| Report generation | ~8-15 min |
| Total time | ~10-20 min |

> Above ranges for standard mode. Actual times vary by topic complexity and data availability.

📂 **[Browse all generated reports →](reports/)** — click to open and read.

## 4. How It Works

The pipeline runs in 4 automated stages:

```
① Analyze outline — Analyze topic, generate research framework and search plan
         ↓
② Collect data — SearXNG / Exa cascading search → Scrapling batch fetch → data pool extraction → quality check
         ↓
③ Parallel writing — Multiple chapters written simultaneously, facts embedded directly in prompts, no tool calls
         ↓
④ Validate & assemble — Batch validate → assemble-report → convert-citations → qa-report
```

## 5. Search Pipeline & Built-in Resources

All tools are built-in, no additional purchase needed. The system uses a **3-layer cascading search** strategy: SearXNG (author-deployed meta-search engine, 70+ engines including Baidu/Google/Brave) → Exa (OMO built-in cold standby) → 10+ free search engines + domestic Chinese sources (final fallback). Each layer stops probing further once a working engine is found.

```
Layer 1 — SearXNG (author-deployed, 70+ engines incl. Baidu/Google/Brave, ready out of the box)
  ↓ if unavailable
Layer 2 — Exa (OMO built-in cold standby, zero cost)
  ↓ if unavailable
Layer 3 — Free source reinforcement (fallback)
  ├─ Search line          │  Known-source line
  ├─ DuckDuckGo           │  Baidu Baike / Wikipedia
  ├─ Bing (China)         │  Zhihu / 36Kr / The Paper
  ├─ Brave / Mojeek       │  199IT / iResearch / East Money
  ├─ Semantic Scholar     │  National Bureau of Statistics / Weibo / CSDN
  └─ GDELT / arXiv        │  Douban / Huxiu
```

> The search reinforcement line can **dynamically discover** any website, not limited to the list above. All source URLs are ultimately batch-fetched by Scrapling.

## 6. Report Highlights

| Dimension | Description |
|-----------|-------------|
| **Multilingual native writing** | Auto-detects topic language, writes directly in 19 languages, no translation pipeline |
| **Every number has a source** | `(N)` clickable citations in text, full reference list at end. No source = no number |
| **Pros and cons coexist** | Every chapter presents controversies and opposing views |
| **Confidence grading** | Final summary table (high/medium/low) shows what's reliable vs. disputed |
| **Data anti-pitfall** | Auto-detects common data errors — wrong units, fabricated trends, misattributed sources |
| **Paragraphs over padding** | 8-12 substantive paragraphs per chapter as core, tables can't pad the length |

## 7. Three Depth Modes

| Command | Purpose | Min chapters | Min paragraphs/chapter | Max chars | Est. time |
|---------|---------|-------------|----------------------|-----------|-----------|
| `/research <topic>` | standard (default) | 8 | ≥ 5 | ≤ 12,000 | ~10–15 min |
| `/research <topic> -quick` | Quick insight | 5 | ≥ 4 | ≤ 8,000 | ~8–12 min |
| `/research <topic> -deep` | Maximum depth | 10 | ≥ 6 | ≤ 25,000 | ~15–25 min |

> Parameters in `profiles.json`, restart to apply. Char count excludes whitespace and Markdown syntax.

## 8. Screenshot

<img width="1086" height="879" alt="Screenshot 2026-06-08 at 20-51-58" src="https://github.com/user-attachments/assets/0d52a3df-19d3-4f2f-b8c4-6b8790387396" />

## 9. Installation

### 🧠 Method 1: AI Auto-Install (Recommended)

Copy this prompt into OpenCode chat, the AI will do everything automatically:

```text
Please read the https://github.com/hoolulu/deep-research project and follow the documentation to:
1. Install prerequisites (determine method based on Scrapling docs and your OS)
2. Register the Scrapling MCP Server, verify it works after CLI restart
3. Register the /research and /research-update commands
Confirm each step, then read VERSION and summarize the installation status.
```

The AI reads the docs → understands your system → installs step by step → verifies. No manual commands needed.

### 🔧 Method 2: Non-OpenCode Users (Claude Code / Codex CLI / Cursor etc.)

Paste this into your AI coding tool:

```text
Please read the https://github.com/hoolulu/deep-research project, auto-install prerequisites and adapt for the current CLI tool:
1. Install Python and Scrapling (refer to Scrapling docs and your system)
2. Register Scrapling MCP Server, verify after restart
3. Register equivalent entry points for /research and /research-update based on the current tool's capabilities:
   - **Codex CLI** → Register as a skill (the `command/` directory already contains command files; registration activates them)
   - **Claude Code** → Register as a slash command (Hook)
   - **Cursor** → Adapt per platform (custom commands / Agent rules)
   - Other tools: check for skill/command mechanisms first, then pick the best fit
4. Translate the multi-agent chain architecture (outline → data collection → parallel writing → assembly+QA) to the current tool's equivalent, preserving the sequential dependencies between stages
Confirm each step, then read VERSION and summarize.
```

Adaptation notes: Multi-agent orchestration needs to map to each platform's native mechanisms (Claude Code's sub-agent, Codex CLI's agent/skill mode, Cursor's agent mode, etc.). Entry point registration also varies by tool (OpenCode/Codex CLI use skills, Claude Code uses Hooks/commands, Cursor uses custom instructions). Search and scraping logic (python-scrapling + search API) can be reused as-is.

### Prerequisites

| Component | Purpose | How to get |
|-----------|---------|------------|
| **OpenCode (core)** | AI coding agent runtime | Visit [https://opencode.ai/](https://opencode.ai/) |
| **oh-my-openagent (required)** | Sub-agents for analysis/search + auto MCP setup | Ask AI to install via oh-my-openagent docs |
| **Scrapling (required)** | Web page full-text scraping | Ask AI to install and register MCP |
| **SearXNG** | Web search (primary, author-deployed 70+ engines) | Built into skill, ready out of the box |
| **Exa MCP** | Web search (cold standby) | Built into OMO, no setup needed |

> This skill depends on oh-my-openagent's sub-agent feature. Without it, `/research` won't work. Other coding tools have their own multi-agent frameworks.

## 10. Usage

After installation and restart, type in the chat:

| Command | Description | Est. time |
|---------|-------------|-----------|
| `/research <topic>` | standard mode | ~10-15 min |
| `/research <topic> -quick` | quick mode | ~8-12 min |
| `/research <topic> -deep` | deep mode | ~15-25 min |
| `/research-update` | Check for updates | — |

### What Happens After You Send It

The entire pipeline runs automatically — you don't need to do anything:

```
① Analyze outline — Analyze topic, generate framework and search plan
② Collect data — SearXNG/Exa cascade → Scrapling batch fetch → data pool → quality check
③ Parallel writing — Multiple chapters simultaneously, facts embedded in prompts
④ Validate & assemble — Batch validate → assemble → citations → QA
```

> Total ~10-20 minutes. Complex topics may take longer, simple ones may be faster.

### Output Files

Reports are saved as Markdown files in the skill's `reports/` directory, with date-timestamped filenames:

```
~/.opencode/skills/deep-research/reports/
```

Open with any Markdown reader (Typora / Obsidian / VS Code etc.).

You can also specify a custom output path — ask AI to configure it.

👉 **[Browse all generated reports](reports/)** — click to open and read.

## 11. Cost

| Component | Cost |
|-----------|------|
| **LLM (already using)** | **DeepSeek v4 Flash** baseline: quick ~100–150k tokens / < $0.03, standard ~150–300k / < $0.06, deep ~300–500k / < $0.10 |
| **SearXNG search (author-deployed)** | Deployed on VPS, zero cost, unlimited usage |
| **Exa search** | Built into OpenCode, zero additional cost (cold standby) |
| **Scrapling fetching** | Runs locally, zero cost |
| **Domestic sources** | Direct connection, zero cost, no proxy needed |
| **OpenCode runtime** | MIT open source, zero cost |

> Estimates based on DeepSeek v4 Flash ($0.14/1M input, $0.28/1M output, source: `https://api-docs.deepseek.com/quick_start/pricing`). Actual costs vary by cache hit rate and topic complexity.

## 12. FAQ

**1. Search quotas? How to ensure uninterrupted searching?**

The system uses a **3-layer cascading search** architecture, each layer independent, auto-degrades on failure:

- **Layer 1 — SearXNG (author-deployed)**: Meta-search engine aggregating 70+ engines (Baidu/Google/Brave), full coverage of Chinese and English. Built-in endpoint, ready out of the box, unlimited, no rate limits.
- **Layer 2 — Exa (cold standby)**: OpenCode built-in search, OMO auto-configures, zero cost. On rate limit, auto-falls to Layer 3.
- **Layer 3 — Free source reinforcement (final fallback)**: DuckDuckGo / Bing / Brave / Mojeek / Semantic Scholar / GDELT / arXiv + 20+ Chinese sources. No API keys required, always available.

**2. How to use local materials for report generation?**

After installing the skill, you can ask AI with these prompts:

- Scenario 1: Local materials + online supplement (recommended)
  ```
  Use the deep-research skill with my local files in D:\notes\projectA to generate a research report on XX (quick mode). Prioritize local content, search online for anything missing.
  ```

- Scenario 2: Local materials only, no internet
  ```
  Use the deep-research skill with my local files in D:\notes\projectA to generate a research report on XX (quick mode). Use only local materials, do not search online.
  ```

- Scenario 3: Pure local, lightweight (no professional format needed)
  ```
  Help me organize the materials in D:\notes\projectA into a structured research report with table of contents and chapter headings.
  ```

**3. How to update to the latest version?**

**Version strategy**: `main` branch always has the latest code. GitHub Releases are only for milestone markers.

OpenCode users:
- **Auto**: Type `/research-update`, AI auto-runs `git pull`
- **Manual**: `cd ~/.opencode/skills/deep-research && git pull`

Check version: `cat ~/.opencode/skills/deep-research/VERSION`

**4. Can non-OpenCode users auto-update?**

Yes — ask your AI to do a version comparison and apply updates:

```text
Compare the latest https://github.com/hoolulu/deep-research with your local version,
identify new features and fixes,
apply them one by one to your local adapted version,
preserving platform-specific changes.
```

**5. Is my data safe?**

All processing is done locally. No data is collected or uploaded.

## License

MIT

This project uses MIT instead of GPL/CC because its core value is a portable methodology and pipeline design, not a copyrighted product. MIT maximizes reuse and adaptation across different platforms and toolchains, consistent with the "not platform-exclusive" positioning.

---

**Created by [hoolulu](https://github.com/hoolulu)** · Repo: [github.com/hoolulu/deep-research](https://github.com/hoolulu/deep-research)

> Community discussion: [LINUX DO](https://linux.do/t/topic/2312664)
