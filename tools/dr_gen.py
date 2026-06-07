#!/usr/bin/env python3
"""
Deep Research Tools — Generate subcommands (write, assemble, skeleton, refs, etc.)
"""
import json
import locale
import os
import re
import sys

from dr_check import check_encoding, load_profile


# ── Source Extraction ─────────────────────────────────────────────────────

SOURCE_PATTERN = re.compile(r'[（(]([^）)]+?)[，,]\s*(\d{4})[）)]')


def extract_sources(filepath: str) -> dict:
    """Extract unique (机构，年份) patterns from report text."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    matches = SOURCE_PATTERN.findall(content)
    seen = set()
    unique = []
    for inst, year in matches:
        key = inst.strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(key)
    return {
        "source_count": len(unique),
        "sources": unique,
        "sources_joined": "、".join(sorted(unique)),
        "total_mentions": len(matches),
    }


# ── TOC Generation ─────────────────────────────────────────────────────────

CHINESE_NUMERALS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                    '十一', '十二', '十三', '十四', '十五']


def _github_anchor(text: str) -> str:
    """Generate GitHub-compatible anchor from heading text.
    
    GitHub strips all Chinese/ASCII punctuation, keeps CJK chars and digits.
    """
    punct = r'''，。、：；？！""''（）【】《》—…·,:;.!?()[]{}"'<>  '''
    table = str.maketrans('', '', punct)
    return text.translate(table).replace(' ', '-').lower()


def generate_toc(outline_path: str) -> dict:
    """Generate single-level chapter TOC from outline.json."""
    with open(outline_path, 'r', encoding='utf-8') as f:
        outline = json.load(f)
    chapters = outline.get('chapters', [])
    lines = []
    for i, ch in enumerate(chapters):
        prefix = CHINESE_NUMERALS[i] if i < len(CHINESE_NUMERALS) else str(i + 1)
        title = ch.get('title', '')
        label = f"{prefix}、{title}"
        anchor = _github_anchor(label)
        lines.append(f"- [{label}](#{anchor})")
    return {
        "chapter_count": len(chapters),
        "toc_lines": lines,
        "toc_text": '\n'.join(lines),
        "prefixes": [CHINESE_NUMERALS[i] if i < len(CHINESE_NUMERALS) else str(i + 1)
                     for i in range(len(chapters))],
    }


# ── Metadata Block Generation ─────────────────────────────────────────────

def generate_metadata(word_count: int, reading_time: int, data_until: str,
                       generate_time: str, depth_mode: str,
                       source_count: int, top_sources: list,
                       skill_version: str = "") -> dict:
    """Generate the two-line metadata block for report header."""
    version_str = f" · Skill版本：{skill_version}" if skill_version else ""
    line1 = (
        f"> **元数据**：总字数：{word_count} 字 · 阅读时间：{reading_time} 分钟"
        f" · 数据截至：{data_until} · 生成时间：{generate_time}"
        f" · 调研模式：{depth_mode}{version_str}"
    )
    sorted_sources = sorted(top_sources)[:8]
    source_str = "、".join(sorted_sources)
    line2 = f"> **参考来源**：{source_str} 等 · 共引用 {source_count} 个来源"
    return {
        "metadata_line": line1,
        "source_line": line2,
        "full_block": line1 + '\n' + line2,
    }


# ── Chapter Mapping ───────────────────────────────────────────────────────

def map_chapters(outline_path: str) -> dict:
    """Map each chapter to its sub_questions for chapter agent dispatch."""
    with open(outline_path, 'r', encoding='utf-8') as f:
        outline = json.load(f)
    chapters = outline.get('chapters', [])
    mapping = {}
    for i, ch in enumerate(chapters):
        sqs = ch.get('sub_questions', [])
        chapter_num = i + 1
        mapping[chapter_num] = {
            "title": ch.get('title', ''),
            "sections": ch.get('sections', []),
            "sub_questions": [
                {"question": sq.get('question', ''), "priority": sq.get('priority', 'medium')}
                for sq in sqs
            ],
            "sub_question_count": len(sqs),
        }
    return {"chapter_count": len(chapters), "mapping": mapping, "chapter_numbers": list(mapping.keys())}


# ── Hyperlinked Reference List ────────────────────────────────────────────

def generate_refs(datapool_path: str, numbered: bool = False) -> dict:
    """Generate reference list from data-pool.json with titles.

    plain:   - [标题 · 机构 · 年](url)
    numbered: (1) [标题 · 机构 · 年](url)
    """
    data = _read_json_handle_bom(datapool_path)
    records = data if isinstance(data, list) else [data]
    seen_keys = set()
    entries = []
    for rec in records:
        for fact in rec.get('facts') or []:
            url = fact.get('url', '').strip()
            inst = fact.get('src', '').strip()
            yr = fact.get('yr', '')
            title = fact.get('title', '').strip()
            if not url or not inst:
                continue
            key = (inst, yr, url)
            if key not in seen_keys:
                seen_keys.add(key)
                entries.append((inst, yr, title or inst, url))
    entries.sort(key=lambda x: (x[0].lower(), x[2]))

    lines = [f"## 参考来源\n", f"共引用 {len(entries)} 个来源\n"]
    if numbered:
        for i, (inst, yr, title, url) in enumerate(entries, 1):
            label = f"{title} · {inst}" + (f" · {yr}" if yr else "")
            lines.append(f"({i}) [{label}]({url})")
        ref_text = '\n'.join(lines[:2]) + '\n\n' + '\n\n'.join(lines[2:])
    else:
        for inst, yr, title, url in entries:
            label = f"{title} · {inst}" + (f" · {yr}" if yr else "")
            lines.append(f"- [{label}]({url})")
        ref_text = '\n'.join(lines)
    return {"source_count": len(entries), "ref_lines": lines, "ref_text": ref_text}


# ── Convert Citations to Numeric Index ────────────────────────────────────

CITATION_RE = re.compile(r'[（(]([^）)]+?)[，,]\s*(\d{4})[）)]')

_UTF8_SIG = 'utf-8-sig'

def _read_json_handle_bom(path: str):
    """Read JSON file, auto-handling UTF-8 BOM."""
    with open(path, 'r', encoding=_UTF8_SIG) as f:
        return json.load(f)


def convert_citations(report_path: str, datapool_path: str, output_path: str = None) -> dict:
    """Build reference section from data-pool, validate (N) citations in body.

    Chapter agents write [N] directly (N pre-assigned from data-pool),
    then convert_citations transforms [N] → [(N)](#refN) (clickable).
    This function:
       1. Builds ref_map from data-pool (first-appearance order of src+yr)
       2. Scans body for [N] references
       3. Validates every [N] has a matching ref entry
       4. Transforms [N] → [(N)](#refN) in body for clickability
       5. Appends/replaces the ## 参考来源 section with (N) format
    """
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check: report should NOT contain （机构，年份） patterns
    legacy_cites = re.findall(r'[（(][^）)]+?[，,]\s*\d{4}[）)]', content)
    if legacy_cites:
        issues = [f"Found {len(legacy_cites)} legacy （机构，年份） citations — chapter agents must use (N) format"]
        return {"passed": False, "issues": issues, "changes": 0}

    # Load data-pool and build ref_map from first-appearance order
    data = _read_json_handle_bom(datapool_path)
    records = data if isinstance(data, list) else [data]

    seen = set()
    ordered_refs = []  # (inst, yr) in first-appearance order
    pool_map = {}  # (inst, yr) → (title, url)
    for rec in records:
        for fact in rec.get('facts') or []:
            inst = fact.get('src', '').strip()
            yr = fact.get('yr', '')
            key = (inst, yr)
            if key not in seen and inst and yr:
                seen.add(key)
                ordered_refs.append(key)
            url = fact.get('url', '').strip()
            title = fact.get('title', '').strip()
            if inst and yr and url:
                pool_map[key] = (title or inst, url)

    ref_map = {pair: i + 1 for i, pair in enumerate(ordered_refs)}

    # Scan body for [N] patterns (chapter agents write these directly)
    body = content.split('## 参考来源')[0] if '## 参考来源' in content else content
    body_refs = set(re.findall(r'(?<!!)\[(\d+)\](?!\()', body))

    issues = []
    for num in sorted(body_refs, key=int):
        num_i = int(num)
        if num_i < 1 or num_i > len(ref_map):
            issues.append(f"Body references ({num}) which has no data-pool entry")

    # Build reference section (blank line between each entry for GFM rendering)
    entry_lines = []
    for (inst, yr), num in sorted(ref_map.items(), key=lambda x: x[1]):
        title, url = pool_map.get((inst, yr), (inst, ''))
        label = title if title == inst else f"{title} · {inst}"
        label = label + (f" · {yr}" if yr else "")
        anchor = f'<a id="ref{num}"></a>'
        if url:
            entry_lines.append(f'{anchor}({num}) [{label}]({url})')
        else:
            entry_lines.append(f'{anchor}({num}) {label}')

    ref_text = '\n\n## 参考来源\n\n\n' + '\n\n'.join(entry_lines)

    # Insert/replace ## 参考来源 section
    old_section = re.search(r'## 参考来源.*?(?=\n## |\Z)', content, re.DOTALL)
    if old_section:
        new_content = content[:old_section.start()] + ref_text + content[old_section.end():]
    else:
        new_content = content + ref_text

    # Validate: every [N] in body has matching ref anchor
    ref_anchors = set(re.findall(r'<a id="ref(\d+)"></a>', new_content))
    missing_in_refs = body_refs - ref_anchors
    orphan_anchors = ref_anchors - body_refs
    if missing_in_refs:
        issues.append(
            f"Citations without matching reference: [{', '.join(sorted(missing_in_refs, key=int))}]")

    # Convert [N] → [(N)](#refN) in body for clickable reference links
    BODY_CITE_RE = re.compile(r'(?<!!)\[(\d+)\](?!\()')
    new_content = BODY_CITE_RE.sub(r'[(\1)](#ref\1)', new_content)

    # Write output
    output = output_path or report_path
    tmp = output + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(new_content)
    os.replace(tmp, output)

    return {
        "passed": len(issues) == 0,
        "changes": len(ref_map),
        "output": output,
        "issues": issues,
        "citation_count": len(body_refs),
        "ref_count": len(ref_anchors),
    }


# ── Encoding-safe stdin reader (cross-platform) ─────────────────────────────

def _read_stdin() -> str:
    """Read stdin with auto-detected encoding.

    Cross-platform strategy:
      1. Try UTF-8 (macOS/Linux/WSL, PowerShell 7+, modern terminals)
      2. Fallback to locale encoding (PowerShell 5.1 on Windows, e.g. cp936)
      3. Last resort: UTF-8 with replacement characters
    """
    raw = sys.stdin.buffer.read()
    if not raw:
        return ''
    # 1. UTF-8 (modern terminals, Unix, PS7+)
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        pass
    # 2. Locale encoding (PS5.1 on Windows → cp936, etc.)
    try:
        return raw.decode(locale.getpreferredencoding())
    except (UnicodeDecodeError, LookupError):
        pass
    # 3. Last resort
    return raw.decode('utf-8', errors='replace')


# ── JSON Write (atomic, encoding-safe) ─────────────────────────────────────

def write_json(filepath: str) -> dict:
    """Read JSON from stdin, validate, write UTF-8 no BOM atomically."""
    raw = _read_stdin()
    if not raw.strip():
        return {"passed": False, "issues": ["Empty input from stdin"]}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"passed": False, "issues": [f"JSON parse error: {e}"]}
    tmp = filepath + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(tmp, filepath)
    except (OSError, IOError) as e:
        return {"passed": False, "issues": [f"Write failed: {e}"]}
    return {"passed": True, "issues": [], "size": os.path.getsize(filepath)}


# ── Markdown Write (encoding-safe, Mojibake-free) ─────────────────────────

def write_md(filepath: str) -> dict:
    """Read markdown from stdin, write UTF-8 no BOM, check Mojibake after."""
    raw = _read_stdin()
    if not raw.strip():
        return {"passed": False, "issues": ["Empty input from stdin"]}
    tmp = filepath + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(raw)
        os.replace(tmp, filepath)
    except (OSError, IOError) as e:
        return {"passed": False, "issues": [f"Write failed: {e}"]}
    enc_check = check_encoding(filepath)
    if not enc_check['passed']:
        return {"passed": False, "issues": [f"Write succeeded but Mojibake detected: {enc_check['issues']}"]}
    return {"passed": True, "issues": [], "size": os.path.getsize(filepath)}


# ── Prepare Chapter Skeleton ──────────────────────────────────────────────

def prepare_chapter(outline_path: str, datapool_path: str,
                    chapter_num: int, total_chapters: int, mode: str) -> dict:
    """Generate chapter skeleton with pre-extracted facts from data-pool."""
    with open(outline_path, 'r', encoding='utf-8') as f:
        outline = json.load(f)
    with open(datapool_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chapters = outline.get('chapters', [])
    if chapter_num < 1 or chapter_num > len(chapters):
        return {"passed": False, "issues": [f"Chapter {chapter_num} out of range (1-{len(chapters)})"]}

    ch = chapters[chapter_num - 1]
    title = ch.get('title', '')
    sections = ch.get('sections', [])
    sub_questions = ch.get('sub_questions', [])

    # Word limit estimate
    prof = load_profile(mode)
    total_limit = prof.get('max_chars', 3000)
    per_chapter_target = total_limit // max(total_chapters, 1)

    # Match data-pool records to this chapter's sub_questions
    pool_records = data if isinstance(data, list) else [data]
    sq_questions = [sq.get('question', '') for sq in sub_questions]

    relevant_facts = []
    for rec in pool_records:
        rec_q = rec.get('question', '')
        # Match if any keyword from sub_questions appears in record question
        match_score = sum(1 for sq in sq_questions if any(
            kw.lower() in rec_q.lower() for kw in sq.split() if len(kw) > 2
        ))
        if match_score > 0:
            facts = rec.get('facts') or []
            for fact in facts:
                relevant_facts.append({
                    "source": fact.get('src', ''),
                    "year": fact.get('yr', ''),
                    "metric": fact.get('met', ''),
                    "value": fact.get('val'),
                    "unit": fact.get('u', ''),
                    "context": fact.get('ctx', ''),
                })

    # Sort facts: prioritize by match score
    relevant_facts.sort(key=lambda x: x.get('year', ''), reverse=True)

    # Build skeleton markdown
    lines = []
    prefix = CHINESE_NUMERALS[chapter_num - 1] if chapter_num - 1 < len(CHINESE_NUMERALS) else str(chapter_num)
    lines.append(f"# {prefix}、{title}")
    lines.append(f"\n> 本章核心判断。\n")
    per_section_est = per_chapter_target // max(len(sections), 1)
    lines.append(f"> **字数参考**：本章目标 ≈ {per_chapter_target} 字（每节 ~{per_section_est} 字）| sections: {len(sections)} | 预匹配事实: {len(relevant_facts)} 条\n")

    for idx, section in enumerate(sections):
        sec_num = idx + 1
        lines.append(f"### {chapter_num}.{sec_num} {section}\n")
        # Add pre-matched facts for this section
        section_facts = [f for f in relevant_facts if section in f.get('context', '') or sec_num <= 2]
        if not section_facts:
            section_facts = relevant_facts[:2] if relevant_facts else []
            if section_facts:
                relevant_facts = relevant_facts[2:]
        for fact in section_facts[:3]:
            val_str = f"{fact['value']}{fact['unit']}" if fact['value'] is not None else fact['context']
            lines.append(f"- {fact['metric']}: {val_str}（{fact['source']}，{fact['year']}）")
        lines.append("")  # blank line for LLM to fill

    skeleton = '\n'.join(lines)
    return {
        "passed": True,
        "skeleton": skeleton,
        "chapter_title": title,
        "fact_count": len(relevant_facts),
        "estimated_words": per_chapter_target,
    }


# ── Assemble Final Report ─────────────────────────────────────────────────

DISCLAIMER = (
    "本报告基于公开数据整理，不构成投资建议。"
    "部分存疑数据已标明，请自行谨慎判断。"
)


def assemble_report(outline_path: str, chapters_dir: str,
                    datapool_path: str,
                    mode: str, target_year: int,
                    wordcount_path: str = None,
                    output_path: str = None) -> dict:
    """Assemble final report from chapter files, outline, and metadata.
    
    wordcount_path is no longer used — word count is computed from the
    assembled report text at the end. Kept as optional param for backward compat.
    """
    from dr_check import word_count as wc_func
    issues = []

    # 1. Read outline
    try:
        with open(outline_path, 'r', encoding='utf-8') as f:
            outline = json.load(f)
    except Exception as e:
        return {"passed": False, "issues": [f"Failed to read outline: {e}"]}

    title = outline.get('title', '报告')
    from datetime import datetime
    now = datetime.now()
    # Auto-generate output path if not provided or is a directory
    if not output_path:
        output_path = f"案例报告/{title}-{now.strftime('%Y%m%d-%H%M%S')}.md"
    elif os.path.isdir(output_path) or not output_path.endswith('.md'):
        base = os.path.join(output_path, f"{title}-{now.strftime('%Y%m%d-%H%M%S')}.md")
        output_path = base
    chapters = outline.get('chapters', [])
    depth_mode = outline.get('depth_mode', mode)

    # 3. Collect and order chapter files
    chapter_files = []
    for i in range(1, len(chapters) + 1):
        path = os.path.join(chapters_dir, f"chapter-{i}.md")
        if os.path.exists(path):
            chapter_files.append((i, path))
        else:
            issues.append(f"Missing chapter file: chapter-{i}.md")

    # 4. Generate TOC
    toc_result = generate_toc(outline_path)
    toc_text = toc_result['toc_text']

    # 5. Read chapter contents
    chapter_texts = []
    for num, fpath in sorted(chapter_files):
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        # Strip any H1/H2 heading the agent might have written (agents are told not to)
        content = re.sub(r'^#{1,2} .+?\n+', '', content, count=1)
        # Prepend correct H2 heading from outline
        prefix = CHINESE_NUMERALS[num - 1] if num - 1 < len(CHINESE_NUMERALS) else str(num)
        ch_title = chapters[num - 1].get('title', '未知')
        heading = f'## {prefix}、{ch_title}'
        chapter_texts.append(f'{heading}\n\n{content}')

    # 6. Build report body first (without metadata — word count unknown yet)
    data_until = f"{target_year}年"
    from datetime import datetime
    generate_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read data-pool for source info
    try:
        refs = generate_refs(datapool_path)
        total_sources = refs['source_count']
        ref_text = refs['ref_text']
    except Exception as e:
        total_sources = 0
        ref_text = "## 参考来源\n\n无来源数据\n"
        issues.append(f"Source extraction failed: {e}")

    # Top sources from data-pool
    try:
        with open(datapool_path, 'r', encoding='utf-8') as f:
            dp_data = json.load(f)
        records = dp_data if isinstance(dp_data, list) else [dp_data]
        source_freq = {}
        for rec in records:
            for fact in rec.get('facts') or []:
                src = fact.get('src', '')
                if src:
                    source_freq[src] = source_freq.get(src, 0) + 1
        top_sources = sorted(source_freq, key=source_freq.get, reverse=True)[:8]
    except Exception:
        top_sources = []

    # Read skill version from VERSION file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    version_path = os.path.join(script_dir, '..', 'VERSION')
    try:
        with open(version_path, 'r', encoding='utf-8') as f:
            version = f.read().strip()
    except Exception:
        version = ""

    # Assemble temporary report with placeholder word count to compute actual word count
    temp_meta = generate_metadata(
        word_count=0, reading_time=1,
        data_until=data_until, generate_time=generate_time,
        depth_mode=depth_mode, source_count=total_sources,
        top_sources=top_sources, skill_version=version,
    )
    temp_parts = [
        f"# {title}\n",
        f"{temp_meta['full_block']}\n",
        "## 目录\n", toc_text, "\n",
    ]
    temp_parts.append('\n\n'.join(chapter_texts))
    temp_parts.append("\n\n---\n\n")
    temp_parts.append(ref_text)
    temp_parts.append(f"\n\n## 免责声明\n\n{DISCLAIMER}\n")
    temp_parts.append(f"\n*报告生成时间：{generate_time}*\n")
    full_report = '\n'.join(temp_parts)

    # 7. Compute word count from assembled report
    total_wc = wc_func(output_path) if os.path.exists(output_path) else 0
    if total_wc == 0:
        total_wc = len(re.sub(r'\s+', '', full_report))
    reading_time = max(1, round(total_wc / 600))

    # 8. Re-generate metadata with real word count, then assemble final
    meta = generate_metadata(
        word_count=total_wc, reading_time=reading_time,
        data_until=data_until, generate_time=generate_time,
        depth_mode=depth_mode, source_count=total_sources,
        top_sources=top_sources, skill_version=version,
    )
    report_parts = [
        f"# {title}\n",
        f"{meta['full_block']}\n",
        "## 目录\n", toc_text, "\n",
    ]
    report_parts.append('\n\n'.join(chapter_texts))
    report_parts.append("\n\n---\n\n")
    report_parts.append(ref_text)
    report_parts.append(f"\n\n## 免责声明\n\n{DISCLAIMER}\n")
    report_parts.append(f"\n*报告生成时间：{generate_time}*\n")
    full_report = '\n'.join(report_parts)

    # 9. Write via write_md logic (UTF-8 no BOM)
    tmp = output_path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(full_report)
        os.replace(tmp, output_path)
    except Exception as e:
        return {"passed": False, "issues": [f"Write failed: {e}"]}

    # 10. Verify writing
    enc_check = check_encoding(output_path)
    if not enc_check['passed']:
        issues.append(f"Encoding issue in assembled report: {enc_check['issues']}")

    # Count lines
    line_count = full_report.count('\n') + 1

    return {
        "passed": len(issues) == 0,
        "output_path": output_path,
        "line_count": line_count,
        "chapter_count": len(chapter_files),
        "word_count": total_wc,
        "issues": issues,
    }
