from __future__ import annotations

import html
import json
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Iterable
from urllib.parse import quote
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_JSON = ROOT / "gptwords.json"
OUTPUT_HTML = ROOT / "index.html"
OUTPUT_LEVELS = ROOT / "word_levels.json"
OFFICIAL_CURRICULUM_JSON = ROOT / "data" / "official_curriculum_vocab.json"
OFFICIAL_SENIOR_HIGH_JSON = ROOT / "data" / "official_senior_high_vocab.json"

WORDLIST_REPO = "https://raw.githubusercontent.com/mahavivo/english-wordlists/master/"

LEVEL_SOURCES = OrderedDict(
    [
        ("cet4", "CET4_edited.txt"),
        ("cet6", "CET6_edited.txt"),
        ("toefl", "TOEFL_abridged.txt"),
        ("gre", "GRE_abridged.txt"),
    ]
)

LEVEL_META = OrderedDict(
    [
        ("primary", {"label": "小学", "description": "依据《义务教育英语课程标准（2022年版）》附录词汇规则匹配。"}),
        ("junior", {"label": "初中", "description": "依据《义务教育英语课程标准（2022年版）》三级词汇规则匹配。"}),
        ("senior", {"label": "高中", "description": "依据《普通高中英语课程标准（2017年版2020年修订）》附录2带星词汇匹配。"}),
        ("cet4", {"label": "大学四级", "description": "命中 CET-4 词表，但不在更早学段官方词表中的词汇。"}),
        ("cet6", {"label": "大学六级", "description": "命中 CET-6 词表，但不在更早学段官方词表中的词汇。"}),
        ("advanced", {"label": "更高阶", "description": "命中 TOEFL / GRE 词表的更高阶词汇。"}),
        ("extended", {"label": "扩展词汇", "description": "未命中公开词表的缩写、专有名词或扩展词汇。"}),
    ]
)


def fetch_wordlist(filename: str) -> str:
    url = WORDLIST_REPO + quote(filename)
    with urlopen(url) as response:  # nosec: source is a fixed public raw URL
        return response.read().decode("utf-8", errors="ignore")


def normalize_word(word: str) -> str:
    folded = unicodedata.normalize("NFKD", word)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return (
        folded.strip()
        .lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
    )


def slugify(word: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_word(word)).strip("-")
    return slug or "word"


def search_key(word: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_word(word))


def parse_wordlist(raw_text: str) -> set[str]:
    words: set[str] = set()
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9'./-]*)", stripped)
        if match:
            words.add(normalize_word(match.group(1)))
    return words


def load_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    with SOURCE_JSON.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            entries.append(json.loads(stripped))
    return entries


def load_official_curriculum_sets() -> tuple[set[str], set[str]]:
    if not OFFICIAL_CURRICULUM_JSON.exists():
        raise FileNotFoundError(
            f"Missing {OFFICIAL_CURRICULUM_JSON}. Run `python scripts/extract_official_curriculum_vocab.py` first."
        )

    payload = json.loads(OFFICIAL_CURRICULUM_JSON.read_text(encoding="utf-8"))
    level2 = {normalize_word(word) for word in payload["level2_match_forms"]}
    level3 = {normalize_word(word) for word in payload["level3_match_forms"]}
    return level2, level3


def load_official_senior_set() -> set[str]:
    if not OFFICIAL_SENIOR_HIGH_JSON.exists():
        raise FileNotFoundError(
            f"Missing {OFFICIAL_SENIOR_HIGH_JSON}. Run `python scripts/extract_official_senior_high_vocab.py` first."
        )

    payload = json.loads(OFFICIAL_SENIOR_HIGH_JSON.read_text(encoding="utf-8"))
    return {normalize_word(word) for word in payload["senior_match_forms"]}


def classify_word(
    word: str,
    official_level2: set[str],
    official_level3: set[str],
    official_senior: set[str],
    wordlists: dict[str, set[str]],
) -> str:
    normalized = normalize_word(word)

    if normalized in official_level2:
        return "primary"
    if normalized in official_level3:
        return "junior"
    if normalized in official_senior:
        return "senior"

    for level in ("cet4", "cet6"):
        if normalized in wordlists[level]:
            return level
    if normalized in wordlists["toefl"] or normalized in wordlists["gre"]:
        return "advanced"
    return "extended"


def inline_markdown(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    return escaped


def compact_lines(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = [line.rstrip() for line in text.split("\n")]
    compacted: list[str] = []
    last_blank = True
    for line in lines:
        if line.strip():
            compacted.append(line)
            last_blank = False
        elif not last_blank:
            compacted.append("")
            last_blank = True
    if compacted and not compacted[-1].strip():
        compacted.pop()
    return compacted


def render_paragraph(lines: Iterable[str]) -> str:
    raw = " ".join(line.strip() for line in lines).strip()
    if not raw:
        return ""

    strong_only = re.fullmatch(r"\*\*(.+?)\*\*", raw)
    if strong_only:
        return f"<h4>{html.escape(strong_only.group(1))}</h4>"

    short_label = re.fullmatch(r"(.{1,18}?)[：:]\s*", raw)
    if short_label:
        return f"<h4>{html.escape(short_label.group(1))}</h4>"

    parts = [inline_markdown(line.strip()) for line in lines if line.strip()]
    return f"<p>{'<br>'.join(parts)}</p>"


def render_list(lines: list[str], start: int, ordered: bool) -> tuple[str, int]:
    pattern = re.compile(r"^\d+\.\s+(.*)$") if ordered else re.compile(r"^[-*]\s+(.*)$")
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    cursor = start

    while cursor < len(lines):
        match = pattern.match(lines[cursor].strip())
        if not match:
            break

        item_lines = [match.group(1).strip()]
        cursor += 1
        while cursor < len(lines):
            current = lines[cursor]
            stripped = current.strip()
            if not stripped:
                cursor += 1
                break
            if pattern.match(stripped):
                break
            if re.match(r"^#{1,6}\s+", stripped):
                break
            if ordered and re.match(r"^[-*]\s+", stripped):
                break
            item_lines.append(stripped)
            cursor += 1

        items.append(f"<li>{'<br>'.join(inline_markdown(part) for part in item_lines if part)}</li>")

    return f"<{tag}>{''.join(items)}</{tag}>", cursor


def markdown_to_html(text: str) -> str:
    lines = compact_lines(text)
    blocks: list[str] = []
    cursor = 0

    while cursor < len(lines):
        line = lines[cursor]
        stripped = line.strip()

        if not stripped:
            cursor += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = min(len(heading_match.group(1)) + 1, 6)
            blocks.append(f"<h{level}>{inline_markdown(heading_match.group(2).strip())}</h{level}>")
            cursor += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            block, cursor = render_list(lines, cursor, ordered=True)
            blocks.append(block)
            continue

        if re.match(r"^[-*]\s+", stripped):
            block, cursor = render_list(lines, cursor, ordered=False)
            blocks.append(block)
            continue

        paragraph_lines = [line]
        cursor += 1
        while cursor < len(lines):
            current = lines[cursor]
            current_stripped = current.strip()
            if not current_stripped:
                break
            if re.match(r"^(#{1,6})\s+", current_stripped):
                break
            if re.match(r"^\d+\.\s+", current_stripped):
                break
            if re.match(r"^[-*]\s+", current_stripped):
                break
            paragraph_lines.append(current)
            cursor += 1

        blocks.append(render_paragraph(paragraph_lines))

    return "\n".join(block for block in blocks if block)


def render_entry(entry: dict[str, str], level_key: str) -> str:
    label = LEVEL_META[level_key]["label"]
    slug = slugify(entry["word"])
    body = markdown_to_html(entry["content"])
    word = html.escape(entry["word"])
    data_word = html.escape(normalize_word(entry["word"]))
    data_search = html.escape(search_key(entry["word"]))
    return f"""
<article class="entry" id="{slug}" data-word="{data_word}" data-search="{data_search}">
  <div class="entry-badge">{label}</div>
  <h3>{word}</h3>
  <div class="entry-content">
    {body}
  </div>
</article>
""".strip()


def render_page(grouped_entries: OrderedDict[str, list[dict[str, str]]]) -> str:
    nav_cards = []
    sections = []

    for level_key, entries in grouped_entries.items():
        meta = LEVEL_META[level_key]
        section_id = f"section-{level_key}"
        nav_cards.append(
            f"""
<a class="level-card" href="#{section_id}">
  <strong>{meta['label']}</strong>
  <span>{len(entries)} 词</span>
  <small>{meta['description']}</small>
</a>
""".strip()
        )

        entry_html = "\n".join(render_entry(entry, level_key) for entry in entries)
        sections.append(
            f"""
<section class="level-section" id="{section_id}">
  <div class="level-section-head">
    <h2>{meta['label']}</h2>
    <p>{meta['description']}</p>
    <span>{len(entries)} 词</span>
  </div>
  <div class="entry-list">
    {entry_html}
  </div>
</section>
""".strip()
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>威威的GPT单词本 · 正式课标分级版</title>
  <style>
    :root {{
      --bg: #f6f1e7;
      --paper: #fffdf7;
      --ink: #1f2d1e;
      --muted: #5d6d5c;
      --line: #d9d0c2;
      --accent: #2e6a57;
      --accent-soft: #dcebe4;
      --badge: #f1eadb;
      --shadow: 0 12px 36px rgba(31, 45, 30, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    html {{
      scroll-behavior: smooth;
    }}

    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(46, 106, 87, 0.10), transparent 26%),
        linear-gradient(180deg, #f3ead9 0%, var(--bg) 30%, #efe8db 100%);
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.7;
    }}

    .container {{
      width: min(1080px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 40px 0 64px;
    }}

    .hero {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 32px;
      box-shadow: var(--shadow);
    }}

    .hero h1 {{
      margin: 0 0 12px;
      font-size: clamp(32px, 4vw, 48px);
      line-height: 1.1;
    }}

    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}

    .toolbar {{
      display: grid;
      gap: 16px;
      margin-top: 24px;
    }}

    .search-box {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }}

    .search-box input {{
      flex: 1 1 280px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 14px 18px;
      font-size: 15px;
      background: #fff;
      color: var(--ink);
    }}

    .search-box button {{
      border: none;
      border-radius: 999px;
      padding: 14px 20px;
      background: var(--accent);
      color: #fff;
      cursor: pointer;
      font-size: 15px;
    }}

    .search-tip {{
      color: var(--muted);
      font-size: 14px;
    }}

    .level-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-top: 28px;
    }}

    .level-card {{
      display: grid;
      gap: 6px;
      padding: 18px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, #fff, #fbf7ee);
      color: inherit;
      text-decoration: none;
      box-shadow: 0 10px 24px rgba(31, 45, 30, 0.05);
    }}

    .level-card strong {{
      font-size: 18px;
    }}

    .level-card span,
    .level-card small {{
      color: var(--muted);
    }}

    .level-section {{
      margin-top: 32px;
      scroll-margin-top: 20px;
    }}

    .level-section-head {{
      position: sticky;
      top: 0;
      z-index: 5;
      display: flex;
      flex-wrap: wrap;
      gap: 10px 18px;
      align-items: baseline;
      padding: 16px 18px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255, 253, 247, 0.94);
      backdrop-filter: blur(8px);
      box-shadow: 0 6px 24px rgba(31, 45, 30, 0.05);
    }}

    .level-section-head h2 {{
      margin: 0;
      font-size: 24px;
    }}

    .level-section-head p,
    .level-section-head span {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}

    .entry-list {{
      display: grid;
      gap: 18px;
      margin-top: 18px;
    }}

    .entry {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 24px;
      box-shadow: var(--shadow);
      scroll-margin-top: 84px;
    }}

    .entry-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border-radius: 999px;
      background: var(--badge);
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
    }}

    .entry h3 {{
      margin: 12px 0 16px;
      font-size: 28px;
      line-height: 1.15;
      word-break: break-word;
    }}

    .entry-content h2,
    .entry-content h3,
    .entry-content h4 {{
      margin: 18px 0 8px;
      color: var(--accent);
    }}

    .entry-content p,
    .entry-content li {{
      margin: 0 0 10px;
      font-size: 15px;
    }}

    .entry-content ol,
    .entry-content ul {{
      margin: 0 0 12px 20px;
      padding: 0;
    }}

    .entry-content strong {{
      color: var(--ink);
    }}

    .footer {{
      margin-top: 40px;
      text-align: center;
      color: var(--muted);
      font-size: 14px;
    }}

    .footer a {{
      color: var(--accent);
    }}

    @media (max-width: 720px) {{
      .container {{
        width: min(100vw - 20px, 1080px);
        padding-top: 20px;
      }}

      .hero,
      .entry {{
        padding: 20px;
      }}

      .level-section-head {{
        position: static;
      }}

      .entry h3 {{
        font-size: 24px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <h1>威威的GPT单词本</h1>
      <p>当前页面按“小学 → 初中 → 高中 → 大学四级 → 大学六级 → 更高阶 → 扩展词汇”的顺序重排。小学和初中使用《义务教育英语课程标准（2022年版）》附录规则；高中使用《普通高中英语课程标准（2017年版2020年修订）》附录2的带星词汇；更高阶段继续使用公开词表。每个单词按命中的最早学段归类，组内再按字母顺序排列。</p>
      <div class="toolbar">
        <div class="search-box">
          <input id="word-search" type="search" placeholder="输入单词，快速跳转，比如: abandon / yesterday / IELTS">
          <button id="search-button" type="button">跳转到单词</button>
        </div>
        <div class="search-tip">分级依据：小学/初中采用 2022 版义务教育英语课标附录；高中采用 2017 年版 2020 年修订普通高中英语课标附录2；CET-4/CET-6/TOEFL/GRE 采用公开词表补充分层。</div>
      </div>
      <nav class="level-grid">
        {"".join(nav_cards)}
      </nav>
    </header>

    <main>
      {"".join(sections)}
    </main>

    <footer class="footer">
      <p>分级页面由仓库内脚本自动生成：<code>python scripts/build_leveled_index.py</code></p>
      <p>词表来源：小学/初中基于《义务教育英语课程标准（2022年版）》附录整理；高中基于《普通高中英语课程标准（2017年版2020年修订）》附录2整理；CET 与更高阶部分继续使用 <a href="https://github.com/mahavivo/english-wordlists">mahavivo/english-wordlists</a></p>
      <p>本页基于原项目 <a href="https://github.com/Ceelog/DictionaryByGPT4">CeeLog/DictionaryByGPT4</a> 调整，感谢原作者 @CeeLog 开源。</p>
    </footer>
  </div>

  <script>
    const normalizeWord = (value) =>
      value
        .trim()
        .toLowerCase()
        .normalize('NFKD')
        .replace(/[\\u0300-\\u036f]/g, '');
    const searchKey = (value) => normalizeWord(value).replace(/[^a-z0-9]+/g, '');
    const entries = Array.from(document.querySelectorAll('.entry'));
    const entryMap = new Map(entries.map((entry) => [entry.dataset.word, entry]));
    const input = document.getElementById('word-search');
    const button = document.getElementById('search-button');

    function jumpToWord() {{
      const rawKeyword = normalizeWord(input.value);
      const keyword = searchKey(input.value);
      if (!rawKeyword) {{
        return;
      }}

      const exact = entryMap.get(rawKeyword) || entries.find((entry) => entry.dataset.search === keyword);
      if (exact) {{
        exact.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        return;
      }}

      const prefixMatch = entries.find(
        (entry) => entry.dataset.word.startsWith(rawKeyword) || entry.dataset.search.startsWith(keyword)
      );
      if (prefixMatch) {{
        prefixMatch.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        return;
      }}

      alert('没有找到这个单词，请尝试换一种拼写。');
    }}

    button.addEventListener('click', jumpToWord);
    input.addEventListener('keydown', (event) => {{
      if (event.key === 'Enter') {{
        jumpToWord();
      }}
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    entries = load_entries()
    official_level2, official_level3 = load_official_curriculum_sets()
    official_senior = load_official_senior_set()
    wordlists = {key: parse_wordlist(fetch_wordlist(filename)) for key, filename in LEVEL_SOURCES.items()}

    level_map: dict[str, str] = {}
    grouped_entries: OrderedDict[str, list[dict[str, str]]] = OrderedDict((key, []) for key in LEVEL_META)

    for entry in entries:
        level_key = classify_word(entry["word"], official_level2, official_level3, official_senior, wordlists)
        level_map[entry["word"]] = level_key
        grouped_entries[level_key].append(entry)

    for items in grouped_entries.values():
        items.sort(key=lambda item: normalize_word(item["word"]))

    OUTPUT_LEVELS.write_text(json.dumps(level_map, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_HTML.write_text(render_page(grouped_entries), encoding="utf-8")

    summary = ", ".join(f"{LEVEL_META[key]['label']} {len(value)}" for key, value in grouped_entries.items())
    print(f"Generated {OUTPUT_HTML.name} and {OUTPUT_LEVELS.name}: {summary}")


if __name__ == "__main__":
    main()
