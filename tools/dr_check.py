#!/usr/bin/env python3
"""
Deep Research Tools — Check subcommands (encoding, headers, metadata, etc.)
"""
import json
import os
import re

# ── Profile loader ────────────────────────────────────────────────────────

_PROFILES_CACHE = None

def load_profile(mode: str) -> dict:
    """Load mode profile from profiles.json. Returns dict with min_chapters,
    min_paragraphs, max_chars for the given mode ('quick'/'standard'/'deep')."""
    global _PROFILES_CACHE
    if _PROFILES_CACHE is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, 'profiles.json')
        with open(path, 'r', encoding='utf-8') as f:
            _PROFILES_CACHE = json.load(f)
    return _PROFILES_CACHE.get(mode, _PROFILES_CACHE.get('quick', {}))


# ── Mojibake & Encoding ──────────────────────────────────────────────────

MOJIBAKE_PATTERNS = [
    '\ufffd',           # replacement character
    '涓枃', '绯荤粺', '鍦ㄧ嚎',  # GBK→UTF-8 typical
    'ç³»', 'å·²',       # Latin-1→UTF-8 typical
]


def check_encoding(filepath: str) -> dict:
    """Check UTF-8 without BOM, no replacement chars, no Mojibake."""
    issues = []
    with open(filepath, 'rb') as f:
        raw = f.read()
    if raw[:3] == b'\xef\xbb\xbf':
        issues.append("BOM detected at byte 0-2: EF BB BF")
        return {"passed": False, "issues": issues}
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        return {"passed": False, "issues": [f"Invalid UTF-8: {e}"]}
    for i, ch in enumerate(text):
        if ch == '\ufffd':
            line = text[:i].count('\n') + 1
            issues.append(f"Replacement character U+FFFD at line {line}")
            break
    for pattern in MOJIBAKE_PATTERNS[1:]:
        if pattern in text:
            lines = [i + 1 for i, line in enumerate(text.split('\n')) if pattern in line]
            issues.append(f"Mojibake pattern '{pattern}' at lines {lines[:3]}")
    return {"passed": len(issues) == 0, "issues": issues}


# ── Word Count ────────────────────────────────────────────────────────────

def _clean_text(filepath: str) -> str:
    """Read file and strip markdown syntax, return cleaned text."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    text = text.replace('|', '')
    text = text.replace('`', '')
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'!\[(.+?)\]\(.+?\)', r'\1', text)
    return text


def word_count(filepath: str) -> int:
    """Count all meaningful non-whitespace chars (total chars)."""
    cleaned = re.sub(r'\s+', '', _clean_text(filepath))
    return len(cleaned)





# ── JSON Validation ───────────────────────────────────────────────────────

def json_validate(filepath: str) -> dict:
    """Check file is valid JSON."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        return {"passed": True, "issues": []}
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"passed": False, "issues": [str(e)]}


# ── Header Format Checks ──────────────────────────────────────────────────

def check_headers(filepath: str) -> dict:
    """Validate ## and ### header formats."""
    issues = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        stripped = line.rstrip('\n\r')
        if re.match(r'^## .*[0-9]\.', stripped):
            issues.append(f"Line {i + 1}: ## header should not contain number: '{stripped[:60]}'")
        if re.match(r'^### [一二三四五六七八九十]', stripped):
            issues.append(f"Line {i + 1}: ### header uses Chinese numeral: '{stripped[:60]}'")
    return {"passed": len(issues) == 0, "issues": issues}


# ── Chapter Number Compliance ─────────────────────────────────────────────

CHINESE_NUMS = '一二三四五六七八九十十一十二十三十四十五'


def check_chapter_numbers(filepath: str) -> dict:
    """Check ## chapter headers use Chinese numerals (一、二、三...)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    pattern = re.compile(r'^## ([' + CHINESE_NUMS + r']+)、')
    hits = [i + 1 for i, line in enumerate(lines) if pattern.match(line.rstrip('\n\r'))]
    return {"passed": len(hits) >= 1, "chapter_lines": hits, "count": len(hits)}


# ── Metadata Check ────────────────────────────────────────────────────────

META_FIELDS = ['总字数', '阅读时间', '数据截至', '生成时间', '调研模式', 'Skill版本']


def check_metadata(filepath: str) -> dict:
    """Check metadata line has all 6 fields + 参考来源 line exists."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    issues = []
    meta_match = re.search(r'> \*\*元数据\*\*：(.+)', content)
    if not meta_match:
        return {"passed": False, "issues": ["Metadata line '> **元数据**：' not found"]}
    meta_line = meta_match.group(1)
    for field in META_FIELDS:
        if field not in meta_line:
            issues.append(f"Metadata field '{field}' missing")
    if not re.search(r'> \*\*参考来源\*\*', content):
        issues.append("Reference source line '> **参考来源**：' not found")
    return {"passed": len(issues) == 0, "issues": issues}


# ── TOC Check ─────────────────────────────────────────────────────────────

def check_toc(filepath: str, expected: int = None) -> dict:
    """Check TOC exists, is unique, matches expected count."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    issues = []
    toc_headings = [i for i, line in enumerate(lines) if line.strip() == '## 目录']
    if len(toc_headings) == 0:
        return {"passed": False, "issues": ["'## 目录' heading not found"], "count": 0}
    elif len(toc_headings) > 1:
        issues.append(f"'## 目录' appears {len(toc_headings)} times (should be 1)")
    toc_start = toc_headings[0]
    toc_entries = 0
    for line in lines[toc_start + 1:]:
        stripped = line.strip()
        if stripped.startswith('## '):
            break
        if stripped.startswith('- [') or stripped.startswith('- '):
            toc_entries += 1
    if expected is not None and toc_entries != expected:
        issues.append(f"TOC has {toc_entries} entries, expected {expected}")
    return {"passed": len(issues) == 0, "issues": issues, "count": toc_entries}


# ── Tail Check ────────────────────────────────────────────────────────────


def check_tail(filepath: str) -> dict:
    """Check tail sections exist (## 参考来源 + ## 免责声明)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []
    # Backward compat: also accept old ## 数据来源 for unconverted reports
    if '## 参考来源' not in content and '## 数据来源' not in content:
        issues.append("Tail section '## 参考来源' not found")
    if '## 免责声明' not in content:
        issues.append("'## 免责声明' not found")
    return {"passed": len(issues) == 0, "issues": issues}


# ── Year Density ──────────────────────────────────────────────────────────

def year_density(filepath: str, target_year: int) -> dict:
    """Calculate percentage of target_year + target_year-1 data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    years = re.findall(r'20[2-9]\d', content)
    if not years:
        return {"passed": False, "issues": ["No year data found"], "density": 0, "total": 0}
    total = len(years)
    target_count = sum(1 for y in years if int(y) in (target_year, target_year - 1))
    density = target_count / total
    return {
        "passed": density >= 0.5,
        "density": round(density, 3),
        "target_count": target_count,
        "total": total,
        "issues": [] if density >= 0.5 else [f"Year density {density:.1%} < 50% (target={target_year})"],
    }


# ── Data Pool Check ───────────────────────────────────────────────────────

def check_datapool(filepath: str, mode: str) -> dict:
    """Validate data-pool.json structure (unified field names for all modes)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            return {"passed": False, "issues": [f"Invalid JSON: {e}"]}
    issues = []
    required_fields = {'question': str, 'src': list, 'facts': list}
    records = data if isinstance(data, list) else [data]
    for i, rec in enumerate(records):
        for field, ftype in required_fields.items():
            if field not in rec:
                issues.append(f"Record {i}: missing field '{field}'")
            elif not isinstance(rec[field], ftype):
                issues.append(f"Record {i}: '{field}' should be {ftype.__name__}")
        facts = rec.get('facts') or []
        if len(facts) < 1:
            issues.append(f"Record {i}: no facts")
        priority = rec.get('priority', 'medium')
        if priority == 'high' and len(facts) < 2:
            issues.append(f"Record {i}: priority=high but only {len(facts)} fact(s)")
        fact_required = ['src', 'yr', 'met', 'val', 'u', 'ctx']
        for j, fact in enumerate(facts):
            for field in fact_required:
                if field not in fact:
                    issues.append(f"Record {i} fact {j}: missing '{field}'")
            if mode == 'quick':
                if 'cur' in fact:
                    issues.append(f"Record {i} fact {j}: quick mode should not have 'cur'")
                if 'conf' in fact:
                    issues.append(f"Record {i} fact {j}: quick mode should not have 'conf'")
            else:
                if 'cur' not in fact:
                    issues.append(f"Record {i} fact {j}: {mode} mode should have 'cur'")
                if 'conf' not in fact:
                    issues.append(f"Record {i} fact {j}: {mode} mode should have 'conf'")
    all_srcs = set()
    total_facts = 0
    for rec in records:
        for s in rec.get('src', []):
            all_srcs.add(s)
        total_facts += len(rec.get('facts', []))
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "record_count": len(records),
        "source_count": len(all_srcs),
        "fact_count": total_facts,
    }


# ── Chapter Validation (single-command for sub-agents) ─────────────────

def validate_chapter(filepath: str, expected_sections: int = 0) -> dict:
    """Run all chapter-level checks and return single JSON result.
    
    This is the ONE command chapter agents should run instead of
    calling 5+ separate check-* commands. Keeps sub-agents from
    writing inline validation code.
    """
    results = {}
    
    # encoding
    enc = check_encoding(filepath)
    results['encoding'] = enc['passed']
    
    # headers
    hdr = check_headers(filepath)
    results['headers'] = hdr['passed']
    
    # word count
    try:
        wc = word_count(filepath)
    except Exception:
        wc = 0
    results['word_count'] = wc
    
    # blockquote at start (skip optional heading on line 1)
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    # If first line is a heading (# ...), check second line
    check_lines = lines[1:] if lines and lines[0].startswith('#') else lines
    has_bq = len(check_lines) > 0 and check_lines[0].startswith('>')
    results['has_blockquote'] = has_bq
    
    # paragraph count (non-heading, non-table, non-empty, non-quote lines)
    para_count = 0
    in_table = False
    for line in lines:
        if line.startswith('|') and line.endswith('|'):
            in_table = True
            continue
        if in_table and not (line.startswith('|') and line.endswith('|')):
            in_table = False
        if in_table:
            continue
        if line.startswith('#'):
            continue
        if line.startswith('>'):
            continue
        if line.startswith('|---'):
            continue
        if line.startswith('|'):
            continue
        para_count += 1
    results['paragraphs'] = para_count
    
    # table count
    table_count = sum(1 for l in lines if l.startswith('|---'))
    results['tables'] = table_count
    
    # section headers found
    section_headers = [l.lstrip('#').strip() for l in lines if l.startswith('###')]
    results['sections'] = section_headers
    results['section_count'] = len(section_headers)
    results['sections_ok'] = expected_sections == 0 or len(section_headers) == expected_sections
    
    # overall
    checks = [results['encoding'], results['headers'], results['has_blockquote'],
              results['sections_ok']]
    results['passed'] = all(checks)
    
    return results


# ── Full QA Report ────────────────────────────────────────────────────────

def _run_checks_concurrent(filepath: str, target_year: int) -> dict:
    """Run all file-level checks concurrently using ThreadPoolExecutor.
    
    Independent checks (encoding, word_count, headers, chapter_numbers,
    metadata, tail, year_density) run in parallel via threads since they
    are all I/O-bound (reading same file independently).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _wc(p):
        wc = word_count(p)
        return {'word_count': wc}

    def _toc(p, expected):
        return {'toc': check_toc(p, expected=expected)}

    results = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {
            ex.submit(check_encoding, filepath): 'encoding',
            ex.submit(_wc, filepath): 'word_count_raw',
            ex.submit(check_headers, filepath): 'headers',
            ex.submit(check_chapter_numbers, filepath): 'chapter_numbers',
            ex.submit(check_metadata, filepath): 'metadata',
            ex.submit(check_tail, filepath): 'tail',
            ex.submit(year_density, filepath, target_year): 'year_density',
        }
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                result = fut.result()
                if key == 'word_count_raw':
                    results['word_count_raw'] = result['word_count']
                else:
                    results[key] = result
            except Exception as e:
                results[key] = {"passed": False, "issues": [f"Check error: {e}"]}

    # chapter_numbers needed for TOC expected count, so TOC must be done after
    expected = results.get('chapter_numbers', {}).get('count', 0)
    results['toc'] = check_toc(filepath, expected=expected)

    return results


def qa_report(filepath: str, mode: str, target_year: int) -> dict:
    """Run all checks and return aggregated result."""
    raw = _run_checks_concurrent(filepath, target_year)

    # Build results dict in the expected schema
    results = {}
    results['encoding'] = raw.get('encoding', {"passed": False, "issues": ["missing"]})
    results['headers'] = raw.get('headers', {"passed": False, "issues": ["missing"]})
    results['chapter_numbers'] = raw.get('chapter_numbers', {"passed": False, "issues": ["missing"]})
    results['metadata'] = raw.get('metadata', {"passed": False, "issues": ["missing"]})
    results['toc'] = raw.get('toc', {"passed": False, "issues": ["missing"]})
    results['tail'] = raw.get('tail', {"passed": False, "issues": ["missing"]})
    results['year_density'] = raw.get('year_density', {"passed": False, "issues": ["missing"]})

    wc = raw.get('word_count_raw', 0)
    prof = load_profile(mode)
    limit = prof.get('max_chars', 3000)
    # word_count is informational — does NOT block qa_report passed
    results['word_count'] = {"passed": True, "count": wc, "limit": limit, "exceeded": wc > limit,
                              "issues": [] if wc <= limit else [f"{wc} > {limit} limit (informational)"]}

    all_passed = all(r.get('passed', False) for r in results.values())
    failures = {name: r.get('issues', []) for name, r in results.items()
                if not r.get('passed', False) and r.get('issues')}
    return {
        "passed": all_passed,
        "file": filepath,
        "mode": mode,
        "target_year": target_year,
        "checks": results,
        "failures": failures,
    }
