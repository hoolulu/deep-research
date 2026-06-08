#!/usr/bin/env python3
"""
Deterministic language detection for deep-research Step 0.

Reads a topic string from --file, argv, or stdin, outputs the best-matching
language code from LANG_CONFIG keys. Uses Unicode ranges + common word
matching — no ML, no LLM, no ambiguity.

Usage:
    python3 detect_lang.py "日本の半導体産業の競争力"
    echo "Analyse der deutschen Automobilindustrie" | python3 detect_lang.py
    python3 detect_lang.py --file topic.txt
    python3 detect_lang.py --file topic.txt --output result.txt

Notes:
    On Windows (PowerShell with legacy code pages like CP936/GBK), passing
    non-ASCII characters via argv will corrupt the input. Use --file instead:
        1. Write topic to UTF-8 file via `write` tool
        2. Run: python detect_lang.py --file path/to/topic.txt --output path/to/lang.txt
        3. Read result from output file
    This completely bypasses shell encoding issues.
"""
import sys
import unicodedata

LANG_KEYS = ['zh', 'en', 'ja', 'ko', 'es', 'fr', 'de', 'pt', 'it', 'nl',
             'sv', 'ru', 'ar', 'hi', 'vi', 'id', 'th', 'tr', 'pl']


def _has_any(text: str, chars: str) -> bool:
    return any(c in text for c in chars)


def detect_language(topic: str) -> str:
    topic_stripped = topic.strip()
    if not topic_stripped:
        return 'en'

    # Character-range detection (deterministic, highest priority)
    has_hiragana = any('\u3040' <= c <= '\u309f' for c in topic_stripped)
    has_katakana = any('\u30a0' <= c <= '\u30ff' for c in topic_stripped)
    has_hangul = any('\uac00' <= c <= '\ud7af' for c in topic_stripped) or \
                 any('\u3130' <= c <= '\u318f' for c in topic_stripped)
    has_arabic = any('\u0600' <= c <= '\u06ff' for c in topic_stripped) or \
                 any('\u0750' <= c <= '\u077f' for c in topic_stripped)
    has_devanagari = any('\u0900' <= c <= '\u097f' for c in topic_stripped)
    has_thai = any('\u0e00' <= c <= '\u0e7f' for c in topic_stripped)
    has_cyrillic = any('\u0400' <= c <= '\u04ff' for c in topic_stripped)
    has_cjk = any('\u4e00' <= c <= '\u9fff' for c in topic_stripped)
    # Vietnamese: Latin + tone marks in specific ranges
    has_vietnamese = any('\u1ea0' <= c <= '\u1ef9' for c in topic_stripped)

    # Script-based dispatch
    if has_hiragana or has_katakana:
        return 'ja'
    if has_hangul:
        return 'ko'
    if has_arabic:
        return 'ar'
    if has_devanagari:
        return 'hi'
    if has_thai:
        return 'th'
    if has_cyrillic:
        return 'ru'

    # CJK without Japanese/Korean scripts → distinguish zh vs ja (kanji-only)
    if has_cjk:
        jp_particles = 'の は が を に へ と や ね よ か も ので ない さん ちゃん'
        if any(p in topic_stripped for p in jp_particles.split()):
            return 'ja'
        if has_vietnamese:
            return 'vi'
        return 'zh'

    # Vietnamese (Latin + tone marks, no CJK)
    if has_vietnamese:
        return 'vi'

    # Latin-script languages: use special chars + common word matching
    lower = topic_stripped.lower()
    words = lower.split()

    # Special characters (distinctive for specific languages)
    has_german_ss = 'ß' in topic_stripped
    has_german_umlaut = _has_any(topic_stripped, 'äöüÄÖÜ')
    has_swedish_aa = 'å' in topic_stripped or 'Å' in topic_stripped
    has_turkish = _has_any(topic_stripped, 'ğşışĞŞİ')
    has_spanish = _has_any(topic_stripped, 'ñÑ¿¡')
    has_portuguese = _has_any(topic_stripped, 'ãõÃÕ')
    has_french = _has_any(topic_stripped, 'éèêàâùûçÉÈÊÀÂÙÛ')
    has_italian = _has_any(topic_stripped, 'ìîòù') and not has_french

    # Strong special-char signals
    if has_german_ss:
        return 'de'
    if has_swedish_aa:
        return 'sv'
    if has_turkish:
        return 'tr'

    # Common-word matching for Latin languages
    WORD_SETS = {
        'de': ['der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'und',
               'oder', 'aber', 'mit', 'von', 'für', 'auf', 'ist', 'sind',
               'nicht', 'auch', 'werden', 'analyse', 'markt', 'industrie',
               'deutschland', 'deutsche', 'deutschen', 'untersuchung',
               'forschung', 'studie'],
        'fr': ['le', 'la', 'les', 'des', 'une', 'sur', 'dans', 'avec', 'est',
               'sont', 'pour', 'analyse', 'étude', 'recherche', 'marché',
               'français', 'france', 'entre', 'secteur', 'concurrence',
               'développement'],
        'es': ['el', 'la', 'los', 'las', 'un', 'una', 'y', 'en', 'con', 'por',
               'para', 'del', 'más', 'análisis', 'mercado', 'español',
               'españa', 'industria', 'competitividad'],
        'pt': ['o', 'a', 'os', 'as', 'um', 'uma', 'e', 'em', 'com', 'por',
               'para', 'do', 'da', 'análise', 'mercado', 'brasil', 'indústria',
               'português'],
        'it': ['il', 'la', 'le', 'gli', 'un', 'una', 'e', 'in', 'con', 'per',
               'del', 'della', 'analisi', 'mercato', 'italia', 'italiano',
               'settore', 'industria'],
        'nl': ['de', 'het', 'een', 'en', 'op', 'in', 'van', 'met', 'voor',
               'door', 'ook', 'maar', 'zijn', 'wordt', 'deze', 'dit', 'die',
               'analyse', 'markt', 'onderzoek', 'rapport',
               'nederland', 'nederlands', 'nederlandse', 'industrie',
               'sector', 'financieel', 'financiële', 'ontwikkeling',
               'economie', 'economische'],
        'sv': ['och', 'det', 'en', 'ett', 'att', 'på', 'för', 'med', 'av',
               'är', 'marknad', 'analys', 'sverige', 'industri'],
        'pl': ['i', 'w', 'na', 'z', 'do', 'się', 'analiza', 'rynek', 'polska',
               'polski', 'przemysł', 'badanie'],
        'id': ['dan', 'di', 'ke', 'dengan', 'untuk', 'analisis', 'pasar',
               'indonesia', 'industri', 'penelitian'],
        'tr': ['ve', 'bir', 'ile', 'için', 'olarak', 'olan', 'analiz', 'pazar',
               'türkiye', 'türk', 'sanayi', 'araştırma'],
    }

    # Score each language by common word matches
    scores = {}
    for lang, wordlist in WORD_SETS.items():
        score = sum(1 for w in words if w in wordlist)
        if score > 0:
            # Bonus for special characters
            if lang == 'es' and has_spanish:
                score += 2
            if lang == 'pt' and has_portuguese:
                score += 2
            if lang == 'fr' and has_french:
                score += 2
            if lang == 'it' and has_italian:
                score += 2
            if lang == 'de' and has_german_umlaut:
                score += 2
            scores[lang] = score

    if scores:
        best = max(scores, key=scores.get)
        if scores[best] >= 1:
            return best

    # Default fallback
    return 'en'


if __name__ == '__main__':
    # Ensure UTF-8 stdout (especially needed on Windows with legacy code pages)
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Parse args: --file <path> or --output <path>
    input_topic = ''
    output_path = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--file' and i + 1 < len(sys.argv):
            filepath = sys.argv[i + 1]
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    input_topic = f.read().strip()
            except Exception as e:
                print(f"detect_lang.py: error reading --file '{filepath}': {e}", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]
            i += 2
        else:
            # Accumulate non-flag args as topic (avoid relying on shell to keep them as one arg)
            if not input_topic:
                input_topic = sys.argv[i]
            i += 1

    # If no --file, try stdin (byte-level for cross-platform safety)
    if not input_topic:
        raw = sys.stdin.buffer.read()
        if raw:
            input_topic = raw.decode('utf-8', errors='replace').strip()

    result = detect_language(input_topic)

    # Write result: to --output file (cross-platform safe) or to stdout
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(result + '\n')
        except Exception as e:
            print(f"detect_lang.py: error writing --output '{output_path}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(result)
