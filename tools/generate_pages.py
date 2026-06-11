#!/usr/bin/env python3
"""Scan reports/ and generate gh-pages index (index.html + reports.json).

Local mode:  python tools/generate_pages.py
API mode:    python tools/generate_pages.py --api
               (fetches files via GitHub API, no git checkout needed)
"""
import os, json, re, sys, base64, urllib.request
from datetime import datetime, timezone

REPORTS_DIR = 'reports'
OUTPUT_DIR = 'gh-pages'

LANG_NAMES = {
    'zh': '中文', 'en': 'English', 'ja': '日本語', 'ko': '한국어',
    'es': 'Español', 'fr': 'Français', 'de': 'Deutsch', 'pt': 'Português',
    'it': 'Italiano', 'nl': 'Nederlands', 'sv': 'Svenska', 'ru': 'Русский',
    'ar': 'العربية', 'hi': 'हिन्दी', 'vi': 'Tiếng Việt', 'id': 'Bahasa Indonesia',
    'th': 'ไทย', 'tr': 'Türkçe', 'pl': 'Polski',
}
MODE_LABELS = {'quick': 'Quick', 'standard': 'Standard', 'deep': 'Deep'}
API_BASE = 'https://api.github.com'


def _api_get(path):
    """GitHub API GET request. Uses GITHUB_TOKEN env var."""
    token = os.environ.get('GITHUB_TOKEN', '')
    repo = os.environ.get('GITHUB_REPOSITORY', 'hoolulu/deep-research')
    url = f'{API_BASE}/repos/{repo}/{path}'
    req = urllib.request.Request(url)
    req.add_header('Accept', 'application/vnd.github.v3+json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def parse_content(content: str, path: str) -> dict:
    """Parse a report's markdown content into metadata dict."""
    t = re.search(r'^# (.+)', content)
    title = t.group(1).strip() if t else os.path.basename(path)
    rel = path.replace('\\', '/')
    lang = rel.split('/')[1] if rel.startswith('reports/') else 'en'
    d = re.search(r'(\d{4})(\d{2})(\d{2})', path)
    date = f'{d.group(1)}-{d.group(2)}-{d.group(3)}' if d else ''
    mm = re.search(r'> \*\*(?:元数据|Metadata|メタデータ|메타데이터|Metadatos|Métadonnées|Metadaten|Metadados|Metadati)\*\*[:：]\s*(.+)', content)
    mode, wc = 'standard', 0
    if mm:
        mt = mm.group(1)
        m = re.search(r'(?:调研模式|Mode|mode|Modo|モード|모드|Modus|Режим|الوضع|मोड|Chế độ)\s*[:：]\s*(\w+)', mt)
        if m:
            mode = m.group(1).lower()
        for p in [
            r'(?:字数|总字数|文字数|글자|عدد الكلمات|शब्द|Số từ|จำนวนคำ)\s*[:：]\s*([\d,]+)',
            r'(?:Word Count|Wortanzahl|Contagem|Recuento|Kelime|Jumlah kata)\s*[:：]?\s*([\d,]+)',
        ]:
            m = re.search(p, mt, re.IGNORECASE)
            if m:
                wc = int(m.group(1).replace(',', ''))
                break
    if wc == 0:
        wc = len(re.sub(r'\s+', '', content))
    src = 0
    sm = re.search(
        r'(?:共引用|Total|Totalt|Totale|総計|合计|总共|합계|إجمالي|कुल|Tổng|Total de)\s+(\d+)\s*'
        r'(?:个来源|sources|件の出典|개 출처|fuentes|fontes|Bronnen|källor|источников|'
        r'مصدرًا|स्रोत|nguồn|sumber|แหล่งที่มา|kaynak|źródeł|fonti)', content)
    if sm:
        src = int(sm.group(1))
    else:
        a = re.findall(r'<a id="ref(\d+)"></a>', content)
        src = max(int(x) for x in a) if a else 0
    return {'title': title, 'path': rel, 'lang': lang,
            'lang_name': LANG_NAMES.get(lang, lang),
            'mode': mode, 'word_count': wc, 'date': date, 'sources': src}


def fmt(n):
    if n >= 10000:
        return f'{round(n/10000,1)}w' if n % 10000 else f'{n//10000}w'
    if n >= 1000:
        return f'{round(n/1000,1)}k' if n % 1000 else f'{n//1000}k'
    return str(n)


def gen_html(reports):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    seen = set()
    lo = ''.join(f'<option value="{c}">{n}</option>' for c, n in LANG_NAMES.items() if (c in seen or seen.add(c) is None) and any(r['lang'] == c for r in reports))
    mo = ''.join(f'<option value="{m}">{MODE_LABELS.get(m,m.title())}</option>' for m in sorted(set(r['mode'] for r in reports)))
    rows = ''
    for i, r in enumerate(reports, 1):
        mc = r['mode'] if r['mode'] in MODE_LABELS else 'standard'
        rows += f'<tr data-lang="{r["lang"]}" data-mode="{r["mode"]}"><td class="n">{i}</td><td class="tc"><a href="{r["path"]}" target="_blank">{r["title"]}</a></td><td>{r["lang_name"]}</td><td><span class="mb mb-{mc}">{MODE_LABELS.get(r["mode"],r["mode"].title())}</span></td><td class="m">{fmt(r["word_count"])}</td><td class="m">{r["sources"]}</td><td class="m">{r["date"]}</td></tr>'
    h = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Deep Research Reports</title><link rel="icon" type="image/svg+xml" href="favicon.svg"><style>
:root{{--fg:#1f2328;--bg:#fff;--canvas:#f6f8fa;--border:#d0d7de;--bm:#d8dee4;--accent:#0969da;--green:#1a7f37;--orange:#9a6700;--muted:#656d76;--radius:6px;--f:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif;--fm:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace}}
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:var(--f);color:var(--fg);background:var(--bg);line-height:1.5}}.w{{max-width:1100px;margin:0 auto;padding:24px 16px}}.hd{{display:flex;align-items:center;gap:12px;margin-bottom:4px}}.hd h1{{font-size:24px;font-weight:600;letter-spacing:-.02em}}.hd h1 a{{color:inherit;text-decoration:none}}.hd h1 a:hover{{color:var(--accent)}}.st{{color:var(--muted);font-size:14px;margin-bottom:20px}}.tb{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;align-items:center}}.sw{{position:relative;flex:1;min-width:200px}}.sw svg{{position:absolute;left:10px;top:50%;transform:translateY(-50%);pointer-events:none;color:var(--muted)}}.sw input{{width:100%;padding:6px 12px 6px 34px;font-size:14px;border:1px solid var(--border);border-radius:var(--radius);outline:none;font-family:inherit}}.sw input:focus{{border-color:var(--accent);box-shadow:0 0 0 3px rgba(9,105,218,.15)}}.fs{{padding:6px 32px 6px 12px;font-size:14px;border:1px solid var(--border);border-radius:var(--radius);cursor:pointer;outline:none;font-family:inherit;appearance:none;background:var(--bg);background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16'%3E%3Cpath fill='%23656d76' d='M4.43 6.43l3.4 3.4a.25.25 0 00.35 0l3.4-3.4A.25.25 0 0011.4 6H4.6a.25.25 0 00-.18.43z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center}}
.fs:focus{{border-color:var(--accent);box-shadow:0 0 0 3px rgba(9,105,218,.15)}}.bg{{font-size:12px;white-space:nowrap;color:var(--muted)}}
.tw{{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}}table{{width:100%;border-collapse:collapse;font-size:14px}}thead{{background:var(--canvas)}}
th{{padding:8px 12px;text-align:left;font-weight:600;border-bottom:1px solid var(--bm);white-space:nowrap;cursor:pointer;user-select:none}}th:hover{{color:var(--accent)}}th .si{{display:inline-block;width:16px;margin-left:4px;opacity:.3;vertical-align:middle}}th.s .si{{opacity:1;color:var(--accent)}}
td{{padding:8px 12px;border-bottom:1px solid var(--bm);vertical-align:middle}}tbody tr{{transition:background .1s}}tbody tr:hover{{background:#f3f4f6}}tr:last-child td{{border-bottom:none}}
.n{{color:var(--muted);font-size:12px;width:30px;text-align:right}}.tc a{{color:var(--accent);text-decoration:none;font-weight:500}}.tc a:hover{{text-decoration:underline}}.m{{font-family:var(--fm);font-size:12px;color:var(--muted);white-space:nowrap}}
.mb{{display:inline-block;padding:2px 7px;font-size:11px;font-weight:600;border-radius:20px;line-height:1.4;white-space:nowrap}}.mb-quick{{color:var(--green);background:#dafbe1}}.mb-standard{{color:var(--accent);background:#ddf4ff}}.mb-deep{{color:var(--orange);background:#fff8c5}}
.hidden{{display:none!important}}.ft{{margin-top:16px;font-size:12px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}}.ft a{{color:var(--accent);text-decoration:none}}.ft a:hover{{text-decoration:underline}}
@media(max-width:700px){{.w{{padding:16px 8px}}.tb{{flex-direction:column}}.sw{{min-width:100%}}thead{{display:none}}tbody tr{{display:block;padding:12px;border-bottom:1px solid var(--bm)}}td{{display:block;padding:3px 0;border:none}}td.n{{display:none}}td.tc{{font-size:15px;margin-bottom:4px}}td::before{{content:attr(data-l);font-size:11px;color:var(--muted);display:inline-block;width:60px;font-weight:500}}}}
</style></head><body><div class="w">
<div class="hd"><svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="8" fill="#0969da"/><text x="18" y="25" text-anchor="middle" font-size="20" font-weight="bold" fill="white" font-family="sans-serif">DR</text></svg><h1><a href=".">Deep Research Reports</a></h1></div>
<p class="st">Browse all generated reports — filter by language, depth, or keywords</p>
<div class="tb">
<div class="sw"><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M10.68 11.74a6 6 0 1 1 1.06-1.06l3.04 3.04a.75.75 0 1 1-1.06 1.06l-3.04-3.04z" fill="currentColor"/><circle cx="7" cy="7" r="5.25" stroke="currentColor" stroke-width="1.5" fill="none"/></svg><input type="text" id="q" placeholder="Search reports&hellip;" oninput="f()" autocomplete="off"></div>
<select class="fs" id="l" onchange="f()"><option value="">All languages</option>{lo}</select>
<select class="fs" id="m" onchange="f()"><option value="">All depths</option>{mo}</select>
<span class="bg" id="c">{len(reports)} reports</span>
</div>
<div class="tw"><table><thead><tr><th style="width:30px">#</th><th onclick="s(0)" class="s">Report <span class="si">&#8595;</span></th><th onclick="s(1)">Language <span class="si">&#8597;</span></th><th onclick="s(2)">Depth <span class="si">&#8597;</span></th><th onclick="s(3)">Words <span class="si">&#8597;</span></th><th onclick="s(4)">Sources <span class="si">&#8597;</span></th><th onclick="s(5)">Date <span class="si">&#8597;</span></th></tr></thead><tbody id="b">{rows}</tbody></table></div>
<div class="ft"><span>Last updated: {now}</span><span><a href="https://github.com/hoolulu/deep-research" target="_blank">deep-research</a> &mdash; Open source</span></div>
</div>
<script>
var D=[];(function(){{var r=document.getElementById('b');for(var i=0;i<r.children.length;i++)D.push(r.children[i]);}})();
function f(){{var q=document.getElementById('q').value.toLowerCase(),l=document.getElementById('l').value,m=document.getElementById('m').value,c=0;for(var i=0;i<D.length;i++){{var x=D[i];var ok=(!l||x.dataset.lang==l)&&(!m||x.dataset.mode==m)&&(!q||x.querySelector('a').textContent.toLowerCase().indexOf(q)>=0);x.classList.toggle('hidden',!ok);if(ok)c++;}}document.getElementById('c').textContent=c+' reports';}}
var sd={{}};
function s(k){{var h=event.currentTarget;sd[k]=sd[k]==='asc'?'desc':'asc';document.querySelectorAll('thead th').forEach(function(t){{t.classList.remove('s')}});h.classList.add('s');var d=sd[k];h.querySelector('.si').innerHTML=d==='asc'?'&#8593;':'&#8595;';D.sort(function(a,b){{var va,vb,ca=a.children[k+1],cb=b.children[k+1];if(k===0){{va=a.querySelector('a').textContent;vb=b.querySelector('a').textContent;}}else if(k===3){{va=p(ca.textContent);vb=p(cb.textContent);}}else if(k===4){{va=parseInt(ca.textContent)||0;vb=parseInt(cb.textContent)||0;}}else{{va=ca.textContent;vb=cb.textContent;}}var c=typeof va==='number'?va-vb:String(va).localeCompare(String(vb));return d==='asc'?c:-c;}});var tb=document.getElementById('b');for(var i=0;i<D.length;i++)tb.appendChild(D[i]);f();}}
function p(s){{var m=s.match(/([\\d.]+)([wk]?)/);if(!m)return 0;var n=parseFloat(m[1]);if(m[2]==='w')return n*10000;if(m[2]==='k')return n*1000;return n||0;}}
</script></body></html>'''
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(h)


def gen_favicon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0969da"/><text x="32" y="44" text-anchor="middle" font-size="36" font-weight="bold" fill="white" font-family="sans-serif">DR</text></svg>'
    with open(os.path.join(OUTPUT_DIR, 'favicon.svg'), 'w', encoding='utf-8') as f:
        f.write(svg)


def main():
    use_fallback = '--fallback' in sys.argv
    reports = []

    # Walk reports/ directory (checkout may have skipped long filenames)
    for root, dirs, files in os.walk(REPORTS_DIR):
        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, encoding='utf-8') as f:
                    reports.append(parse_content(f.read(), path))
            except (FileNotFoundError, OSError) as e:
                if use_fallback:
                    # File not on disk (too long filename) — fetch via API
                    rel = os.path.relpath(path, REPORTS_DIR).lstrip('./')
                    full_path = f'reports/{rel}'
                    try:
                        resp = _api_get(f'contents/{full_path}')
                        text = base64.b64decode(resp['content']).decode('utf-8')
                        reports.append(parse_content(text, full_path))
                        print(f'  API fallback: {full_path}')
                    except Exception as e2:
                        print(f'  BOTH FAILED {fname}: {e2}')
                else:
                    print(f'  SKIP (not found): {fname}')

    reports.sort(key=lambda r: r['date'], reverse=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, 'reports.json'), 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
    gen_html(reports)
    gen_favicon()
    print(f'Done: {len(reports)} reports -> {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()
