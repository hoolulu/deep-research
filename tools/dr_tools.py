#!/usr/bin/env python3
"""
Deep Research Tools — Unified CLI entry point.
All functions live in dr_check.py (quality checks) and dr_gen.py (generation).
"""
import argparse
import json
import sys

from dr_check import (
    check_encoding, word_count, json_validate,
    check_headers, check_chapter_numbers, check_metadata,
    check_toc, check_tail, year_density, check_datapool,
    validate_chapter, qa_report,
)
from dr_gen import (
    extract_sources, generate_toc, generate_metadata,
    generate_refs, map_chapters,
    write_json, write_md,
    prepare_chapter, assemble_report, convert_citations,
)


def _exit(result: dict):
    """Print result and exit."""
    passed = result.get('passed', False)
    issues = result.get('issues', [])
    # Stats first (always printed, even on failure — agent can still use partial data)
    stats = {k: result[k] for k in ('record_count', 'source_count', 'fact_count') if k in result}
    if stats:
        import json
        print(f"STATS: {json.dumps(stats)}")
    print("PASS" if passed else "FAIL")
    if not passed:
        for issue in issues:
            print(f"  - {issue}")
    sys.exit(0 if passed else 1)


def main():
    # Fix Windows console encoding
    for stream in (sys.stdout, sys.stderr):
        enc = getattr(stream, 'encoding', None)
        if enc and enc.upper() not in ('UTF-8', 'UTF8'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

    parser = argparse.ArgumentParser(description='Deep Research Tools — QA & utilities')
    sub = parser.add_subparsers(dest='command', required=True)

    # ── Check subcommands ──
    p = sub.add_parser('check-encoding', help='Check UTF-8, BOM, Mojibake')
    p.add_argument('file')
    p = sub.add_parser('word-count', help='Count all chars (excl whitespace/markdown)')
    p.add_argument('file')
    p = sub.add_parser('json-validate', help='Validate JSON')
    p.add_argument('file')
    p = sub.add_parser('check-headers', help='Check ##/### header format')
    p.add_argument('file')
    p = sub.add_parser('check-chapter-numbers', help='Check ## Chinese numeral chapters')
    p.add_argument('file')
    p = sub.add_parser('check-metadata', help='Check metadata line completeness')
    p.add_argument('file')
    p = sub.add_parser('check-toc', help='Check TOC existence and count')
    p.add_argument('file')
    p.add_argument('--expected', type=int, default=None)
    p = sub.add_parser('check-tail', help='Check data source + disclaimer')
    p.add_argument('file')
    p = sub.add_parser('year-density', help='Calculate year density')
    p.add_argument('file')
    p.add_argument('--target-year', type=int, required=True)
    p = sub.add_parser('check-datapool', help='Validate data-pool.json structure')
    p.add_argument('file')
    p.add_argument('--mode', choices=['quick', 'standard', 'deep'], required=True)
    p = sub.add_parser('validate-chapter', help='Single-command: all chapter checks at once')
    p.add_argument('file')
    p.add_argument('--expected-sections', type=int, default=0)
    p = sub.add_parser('qa-report', help='Full report quality check')
    p.add_argument('file')
    p.add_argument('--mode', choices=['quick', 'standard', 'deep'], required=True)
    p.add_argument('--target-year', type=int, required=True)

    # ── Generate subcommands ──
    p = sub.add_parser('extract-sources', help='Extract unique (机构，年份) from report')
    p.add_argument('file')
    p.add_argument('--format', choices=['text', 'json'], default='text')
    p = sub.add_parser('generate-toc', help='Generate TOC from outline.json')
    p.add_argument('outline')
    p = sub.add_parser('generate-metadata', help='Generate metadata block')
    p.add_argument('--word-count', type=int, required=True)
    p.add_argument('--reading-time', type=int, required=True)
    p.add_argument('--data-until', required=True)
    p.add_argument('--generate-time', required=True)
    p.add_argument('--mode', required=True, choices=['quick', 'standard', 'deep'])
    p.add_argument('--source-count', type=int, required=True)
    p.add_argument('--top-sources', nargs='*', default=[])
    p.add_argument('--version', default='', help='Skill version (auto-read from VERSION if omitted)')
    p = sub.add_parser('map-chapters', help='Map chapters to sub_questions')
    p.add_argument('outline')
    p = sub.add_parser('generate-refs', help='Generate source list with titles')
    p.add_argument('datapool')
    p.add_argument('--numbered', action='store_true', help='Output as (N) numbered list')

    # convert-citations
    p = sub.add_parser('convert-citations', help='Convert [N] → [(N)](#refN) clickable citations')
    p.add_argument('report', help='Path to assembled report')
    p.add_argument('--datapool', required=True, help='Path to data-pool.json')
    p.add_argument('--output', default=None, help='Output path (default: in-place)')

    # ── Write subcommands ──
    p = sub.add_parser('write-json', help='Read JSON from stdin, write UTF-8 no BOM')
    p.add_argument('filepath')
    p = sub.add_parser('write-md', help='Read markdown from stdin, write UTF-8 no BOM')
    p.add_argument('filepath')

    # ── Chapter skeleton + Report assembly ──
    p = sub.add_parser('prepare-chapter', help='Generate chapter skeleton with pre-matched facts')
    p.add_argument('--outline', required=True)
    p.add_argument('--datapool', required=True)
    p.add_argument('--chapter', type=int, required=True)
    p.add_argument('--total', type=int, default=1)
    p.add_argument('--mode', choices=['quick', 'standard', 'deep'], default='standard')
    p = sub.add_parser('assemble-report', help='Assemble final report from chapters + metadata')
    p.add_argument('--outline', required=True)
    p.add_argument('--chapters-dir', required=True)
    p.add_argument('--wordcount', default=None, help='Deprecated, word count computed from report')
    p.add_argument('--datapool', required=True)
    p.add_argument('--mode', choices=['quick', 'standard', 'deep'], required=True)
    p.add_argument('--target-year', type=int, required=True)
    p.add_argument('--output', default=None,
                   help='Output file path. If omitted, auto-generates from title+date')

    args = parser.parse_args()

    # ── Dispatch: checks ──
    if args.command == 'check-encoding':
        _exit(check_encoding(args.file))
    elif args.command == 'word-count':
        print(word_count(args.file))
        sys.exit(0)
    elif args.command == 'json-validate':
        _exit(json_validate(args.file))
    elif args.command == 'check-headers':
        _exit(check_headers(args.file))
    elif args.command == 'check-chapter-numbers':
        _exit(check_chapter_numbers(args.file))
    elif args.command == 'check-metadata':
        _exit(check_metadata(args.file))
    elif args.command == 'check-toc':
        _exit(check_toc(args.file, expected=args.expected))
    elif args.command == 'check-tail':
        _exit(check_tail(args.file))
    elif args.command == 'year-density':
        _exit(year_density(args.file, target_year=args.target_year))
    elif args.command == 'check-datapool':
        _exit(check_datapool(args.file, mode=args.mode))
    elif args.command == 'validate-chapter':
        result = validate_chapter(args.file, expected_sections=args.expected_sections)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    elif args.command == 'qa-report':
        result = qa_report(args.file, mode=args.mode, target_year=args.target_year)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result['passed'] else 1)

    # ── Dispatch: generate ──
    elif args.command == 'extract-sources':
        result = extract_sources(args.file)
        if args.format == 'json':
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for s in sorted(result['sources']):
                print(s)
        sys.exit(0)
    elif args.command == 'generate-toc':
        print(generate_toc(args.outline)['toc_text'])
        sys.exit(0)
    elif args.command == 'generate-metadata':
        # Auto-read version from VERSION file if not provided
        version = args.version
        if not version:
            vpath = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
            try:
                with open(vpath) as f:
                    version = f.read().strip()
            except Exception:
                pass
        print(generate_metadata(
            word_count=args.word_count, reading_time=args.reading_time,
            data_until=args.data_until, generate_time=args.generate_time,
            depth_mode=args.mode, source_count=args.source_count,
            top_sources=args.top_sources, skill_version=version)['full_block'])
        sys.exit(0)
    elif args.command == 'map-chapters':
        print(json.dumps(map_chapters(args.outline), ensure_ascii=False, indent=2))
        sys.exit(0)
    elif args.command == 'generate-refs':
        result = generate_refs(args.datapool, numbered=args.numbered)
        print(result['ref_text'])
        sys.exit(0)

    elif args.command == 'convert-citations':
        result = convert_citations(args.report, args.datapool, args.output)
        _exit(result)

    #     ── Dispatch: write ──
    elif args.command == 'write-json':
        _exit(write_json(args.filepath))
    elif args.command == 'write-md':
        _exit(write_md(args.filepath))

    # ── Dispatch: skeleton + assembly ──
    elif args.command == 'prepare-chapter':
        result = prepare_chapter(
            outline_path=args.outline, datapool_path=args.datapool,
            chapter_num=args.chapter, total_chapters=args.total, mode=args.mode)
        if result['passed']:
            print(result['skeleton'])
        _exit(result)
    elif args.command == 'assemble-report':
        result = assemble_report(
            outline_path=args.outline, chapters_dir=args.chapters_dir,
            datapool_path=args.datapool,
            mode=args.mode, target_year=args.target_year,
            wordcount_path=args.wordcount,
            output_path=args.output)
        if result['passed']:
            print(f"Report assembled: {result['output_path']} ({result['line_count']} lines, {result['chapter_count']} chapters, {result['word_count']} chars)")
        _exit(result)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        print(f"Type: {type(e).__name__}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        print("\n---", file=sys.stderr)
        print("Fallback: This script crashed. The LLM can:", file=sys.stderr)
        print("  1. Check Python version: python --version", file=sys.stderr)
        print("  2. Check file existence: os.path.exists(path)", file=sys.stderr)
        print("  3. Run with traceback: PYTHONTRACEMALLOC=1", file=sys.stderr)
        print("  4. Use sys.executable to find the correct Python path", file=sys.stderr)
        sys.exit(1)
