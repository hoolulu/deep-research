#!/usr/bin/env python3
import json
import locale
import os
import re
import sys

from dr_check import check_encoding, load_profile
from lang_config import get_lang_config, CHINESE_NUMERALS


# ── Source Extraction ─────────────────────────────────────────────────────

SOURCE_PATTERN = re.compile(r'[（(]([^）)]+?)[，,]\s*(\d{4})[）)]')


def extract_sources(filepath: str) -> dict:
    with open(filepath, 'r', encoding='utf-8-sig') as f:
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


def _github_anchor(text: str) -> str:
    punct = r'''，。、：；？！""''（）【】《》—…·,:;.!?()[]{}"'<>  '''
    table = str.maketrans('', '', punct)
    return text.translate(table).replace(' ', '-').lower()


def generate_toc(outline_path: str) -> dict:
    with open(outline_path, 'r', encoding='utf-8-sig') as f:
        outline = json.load(f)
    chapters = outline.get('chapters', [])
    lang = outline.get('language', 'zh')
    cfg = get_lang_config(lang)
    lines = []
    for i, ch in enumerate(chapters):
        prefix = cfg['toc_prefix'](i + 1)
        title = ch.get('title', '')
        label = f"{prefix} {title}" if lang != 'zh' else f"{prefix}{title}"
        anchor = _github_anchor(label)
        lines.append(f"- [{label}](#{anchor})")
    return {
        "chapter_count": len(chapters),
        "toc_lines": lines,
        "toc_text": '\n'.join(lines),
    }


# ── Metadata Block Generation ─────────────────────────────────────────────


def generate_metadata(word_count: int, reading_time: int, data_until: str,
                       generate_time: str, depth_mode: str,
                       source_count: int, top_sources: list,
                       skill_version: str = "",
                       lang: str = "zh") -> dict:
    cfg = get_lang_config(lang)
    fields = cfg['metadata_fields']
    s = cfg['sep']
    fs = cfg['field_sep']
    version_str = f"{s}{fields[5]}{fs}{skill_version}" if skill_version else ""
    line1 = (
        f"> {cfg['metadata_label']}"
        f"{fields[0]}{fs}{word_count}"
        f"{s}{fields[1]}{fs}{reading_time} {cfg['minute_unit']}"
        f"{s}{fields[2]}{fs}{data_until}"
        f"{s}{fields[3]}{fs}{generate_time}"
        f"{s}{fields[4]}{fs}{depth_mode}{version_str}"
    )
    sorted_sources = sorted(top_sources)[:8]
    src_fmt = cfg['refs_count_format']
    count_text = src_fmt(source_count) if callable(src_fmt) else src_fmt.format(count=source_count)
    if lang == 'zh':
        source_str = "、".join(sorted_sources)
        line2 = f"> {cfg['references_label']}{source_str} 等 · {count_text}"
    else:
        source_str = ", ".join(sorted_sources)
        line2 = f"> {cfg['references_label']}{source_str} et al. · {count_text}"
    return {
        "metadata_line": line1,
        "source_line": line2,
        "full_block": line1 + '\n' + line2,
    }


# ── Chapter Mapping ───────────────────────────────────────────────────────


def map_chapters(outline_path: str) -> dict:
    with open(outline_path, 'r', encoding='utf-8-sig') as f:
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


def generate_refs(datapool_path: str, numbered: bool = False, lang: str = "zh") -> dict:
    data = _read_json_handle_bom(datapool_path)
    records = data if isinstance(data, list) else [data]
    cfg = get_lang_config(lang)
    seen_keys = set()
    entries = []
    for rec in records:
        for fact in rec.get('facts') or []:
            url = (fact.get('url') or '').strip()
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

    src_fmt = cfg['refs_count_format']
    count_text = src_fmt(len(entries)) if callable(src_fmt) else src_fmt.format(count=len(entries))
    lines = [f"{cfg['refs_prefix']}\n", f"{count_text}\n"]
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
    with open(path, 'r', encoding=_UTF8_SIG) as f:
        return json.load(f)


# ── Search Engine Detection ─────────────────────────────────────────────────


def detect_engine() -> dict:
    import json as _json
    import urllib.request as _req
    import urllib.error as _err

    try:
        r = _req.Request(
            "https://search.h33.top/search?q=test&format=json",
            headers={"User-Agent": "Mozilla/5.0"},
            method="GET",
        )
        with _req.urlopen(r, timeout=15) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and "results" in data:
                return {"engine": "searxng", "available": True}
    except Exception:
        pass

    return {"engine": "none", "available": False}


def convert_citations(report_path: str, datapool_path: str, output_path: str = None, lang: str = "zh") -> dict:
    with open(report_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    cfg = get_lang_config(lang)

    # Check: report should NOT contain （机构，年份） patterns
    legacy_cites = re.findall(r'[（(][^）)]+?[，,]\s*\d{4}[）)]', content)
    if legacy_cites:
        issues = [f"Found {len(legacy_cites)} legacy （机构，年份） citations — chapter agents must use (N) format"]
        return {"passed": False, "issues": issues, "changes": 0}

    # Load data-pool and build ref_map from first-appearance order
    data = _read_json_handle_bom(datapool_path)
    records = data if isinstance(data, list) else [data]

    seen = set()
    ordered_refs = []
    pool_map = {}
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

    # Scan body for [N] patterns
    split_marker = cfg['refs_prefix']
    body = content.split(split_marker)[0] if split_marker in content else content
    body_refs = set(re.findall(r'(?<!!)\[(\d+)\](?!\()', body))

    issues = []
    for num in sorted(body_refs, key=int):
        num_i = int(num)
        if num_i < 1 or num_i > len(ref_map):
            issues.append(f"Body references ({num}) which has no data-pool entry")

    # Build reference section
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

    ref_text = f'\n\n{cfg["refs_prefix"]}\n\n\n' + '\n\n'.join(entry_lines)

    # Insert/replace refs section
    old_section = re.search(rf'{cfg["refs_prefix"]}.*?(?=\n## |\Z)', content, re.DOTALL)
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

    # Convert [N] → [(N)](#refN)
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
    raw = sys.stdin.buffer.read()
    if not raw:
        return ''
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode(locale.getpreferredencoding())
    except (UnicodeDecodeError, LookupError):
        pass
    return raw.decode('utf-8', errors='replace')


# ── JSON Write (atomic, encoding-safe) ─────────────────────────────────────


def write_json(filepath: str) -> dict:
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
    with open(outline_path, 'r', encoding='utf-8-sig') as f:
        outline = json.load(f)
    with open(datapool_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    chapters = outline.get('chapters', [])
    lang = outline.get('language', 'zh')
    cfg = get_lang_config(lang)

    if chapter_num < 1 or chapter_num > len(chapters):
        return {"passed": False, "issues": [f"Chapter {chapter_num} out of range (1-{len(chapters)})"]}

    ch = chapters[chapter_num - 1]
    title = ch.get('title', '')
    sections = ch.get('sections', [])
    sub_questions = ch.get('sub_questions', [])

    prof = load_profile(mode)
    total_limit = prof.get('max_chars', 3000)
    per_chapter_target = total_limit // max(total_chapters, 1)

    pool_records = data if isinstance(data, list) else [data]
    sq_questions = [sq.get('question', '') for sq in sub_questions]

    relevant_facts = []
    for rec in pool_records:
        rec_q = rec.get('question', '')
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

    relevant_facts.sort(key=lambda x: x.get('year', ''), reverse=True)

    lines = []
    prefix_str = cfg['chapter_heading'](chapter_num, title)
    lines.append(f"# {title}")
    lines.append(f"\n> " + ("Core judgment for this chapter." if lang != 'zh' else "本章核心判断。") + "\n")
    per_section_est = per_chapter_target // max(len(sections), 1)
    char_note = "chars" if lang != 'zh' else "字"
    lines.append(f"> **{'Word target' if lang != 'zh' else '字数参考'}**：{'chapter target' if lang != 'zh' else '本章目标'} ≈ {per_chapter_target} {char_note}（{'per section' if lang != 'zh' else '每节'} ~{per_section_est} {char_note}）| sections: {len(sections)} | {'pre-matched facts' if lang != 'zh' else '预匹配事实'}: {len(relevant_facts)}\n")

    for idx, section in enumerate(sections):
        sec_num = idx + 1
        lines.append(f"### {chapter_num}.{sec_num} {section}\n")
        section_facts = [f for f in relevant_facts if section in f.get('context', '') or sec_num <= 2]
        if not section_facts:
            section_facts = relevant_facts[:2] if relevant_facts else []
            if section_facts:
                relevant_facts = relevant_facts[2:]
        for fact in section_facts[:3]:
            val_str = f"{fact['value']}{fact['unit']}" if fact['value'] is not None else fact['context']
            lines.append(f"- {fact['metric']}: {val_str}（{fact['source']}，{fact['year']}）")
        lines.append("")

    skeleton = '\n'.join(lines)
    return {
        "passed": True,
        "skeleton": skeleton,
        "chapter_title": title,
        "fact_count": len(relevant_facts),
        "estimated_words": per_chapter_target,
    }


# ── Assemble Final Report ─────────────────────────────────────────────────


def assemble_report(outline_path: str, chapters_dir: str,
                    datapool_path: str,
                    mode: str, target_year: int,
                    wordcount_path: str = None,
                    output_path: str = None) -> dict:
    from dr_check import word_count as wc_func
    import datetime
    issues = []

    try:
        with open(outline_path, 'r', encoding='utf-8-sig') as f:
            outline = json.load(f)
    except Exception as e:
        return {"passed": False, "issues": [f"Failed to read outline: {e}"]}

    title = outline.get('title', '报告')
    lang = outline.get('language', 'zh')
    cfg = get_lang_config(lang)
    now = datetime.datetime.now()

    # Sanitize title for filesystem: replace Windows-invalid chars with '-'
    # Invalid on Windows: < > : " / \ | ? *
    safe_title = re.sub(r'[<>:"/\\|?*]', '-', title)
    # Also trim trailing dots/spaces (Windows issue)
    safe_title = safe_title.rstrip('. ')

    if not output_path:
        output_path = f"reports/{safe_title}-{now.strftime('%Y%m%d-%H%M%S')}.md"
    elif os.path.isdir(output_path) or not output_path.endswith('.md'):
        base = os.path.join(output_path, f"{safe_title}-{now.strftime('%Y%m%d-%H%M%S')}.md")
        output_path = base
    chapters = outline.get('chapters', [])
    depth_mode = outline.get('depth_mode', mode)

    chapter_files = []
    for i in range(1, len(chapters) + 1):
        path = os.path.join(chapters_dir, f"chapter-{i}.md")
        if os.path.exists(path):
            chapter_files.append((i, path))
        else:
            issues.append(f"Missing chapter file: chapter-{i}.md")

    toc_result = generate_toc(outline_path)
    toc_text = toc_result['toc_text']

    chapter_texts = []
    for num, fpath in sorted(chapter_files):
        with open(fpath, 'r', encoding='utf-8-sig') as f:
            content = f.read().strip()
        content = re.sub(r'^#{1,2} .+?\n+', '', content, count=1)
        heading = cfg['chapter_heading'](num, chapters[num - 1].get('title', ''))
        chapter_texts.append(f'{heading}\n\n{content}')

    data_until = f"{target_year}" if lang != 'zh' else f"{target_year}年"
    generate_time = now.strftime("%Y-%m-%d %H:%M:%S")

    try:
        refs = generate_refs(datapool_path, lang=lang)
        total_sources = refs['source_count']
        ref_text = refs['ref_text']
    except Exception as e:
        total_sources = 0
        ref_text = f"{cfg['refs_prefix']}\n\n{'No source data' if lang != 'zh' else '无来源数据'}\n"
        issues.append(f"Source extraction failed: {e}")

    try:
        with open(datapool_path, 'r', encoding='utf-8-sig') as f:
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

    script_dir = os.path.dirname(os.path.abspath(__file__))
    version_path = os.path.join(script_dir, '..', 'VERSION')
    try:
        with open(version_path, 'r', encoding='utf-8-sig') as f:
            version = f.read().strip()
    except Exception:
        version = ""

    temp_meta = generate_metadata(
        word_count=0, reading_time=1,
        data_until=data_until, generate_time=generate_time,
        depth_mode=depth_mode, source_count=total_sources,
        top_sources=top_sources, skill_version=version, lang=lang,
    )
    toc_heading = cfg['toc_heading']
    temp_parts = [
        f"# {title}\n",
        f"{temp_meta['full_block']}\n",
        toc_heading, "\n", toc_text, "\n",
    ]
    temp_parts.append('\n\n'.join(chapter_texts))
    temp_parts.append("\n\n---\n\n")
    temp_parts.append(ref_text)
    temp_parts.append(f"\n\n{cfg['disclaimer_title']}\n\n{cfg['disclaimer_text']}\n")
    temp_parts.append(f"\n{cfg['report_generated'].format(time=generate_time)}\n")
    full_report = '\n'.join(temp_parts)

    total_wc = wc_func(output_path) if os.path.exists(output_path) else 0
    if total_wc == 0:
        total_wc = len(re.sub(r'\s+', '', full_report))
    reading_time = max(1, round(total_wc / 600))

    meta = generate_metadata(
        word_count=total_wc, reading_time=reading_time,
        data_until=data_until, generate_time=generate_time,
        depth_mode=depth_mode, source_count=total_sources,
        top_sources=top_sources, skill_version=version, lang=lang,
    )
    report_parts = [
        f"# {title}\n",
        f"{meta['full_block']}\n",
        toc_heading, "\n", toc_text, "\n",
    ]
    report_parts.append('\n\n'.join(chapter_texts))
    report_parts.append("\n\n---\n\n")
    report_parts.append(ref_text)
    report_parts.append(f"\n\n{cfg['disclaimer_title']}\n\n{cfg['disclaimer_text']}\n")
    report_parts.append(f"\n{cfg['report_generated'].format(time=generate_time)}\n")
    full_report = '\n'.join(report_parts)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Auto-dedup: delete older report files with same title in the same directory
    out_dir = os.path.dirname(output_path)
    pattern = re.compile(r'^' + re.escape(safe_title) + r'-\d{8}-\d{6}\.md$')
    for fname in os.listdir(out_dir):
        if pattern.match(fname) and fname != os.path.basename(output_path):
            old_path = os.path.join(out_dir, fname)
            try:
                os.remove(old_path)
            except OSError:
                pass

    tmp = output_path + '.tmp'
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(full_report)
        os.replace(tmp, output_path)
    except Exception as e:
        return {"passed": False, "issues": [f"Write failed: {e}"]}

    enc_check = check_encoding(output_path)
    if not enc_check['passed']:
        issues.append(f"Encoding issue in assembled report: {enc_check['issues']}")

    line_count = full_report.count('\n') + 1

    return {
        "passed": len(issues) == 0,
        "output_path": output_path,
        "line_count": line_count,
        "chapter_count": len(chapter_files),
        "word_count": total_wc,
        "issues": issues,
    }
