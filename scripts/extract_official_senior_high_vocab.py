from __future__ import annotations

import json
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "official_senior_high_english_curriculum_2020.pdf"
SOURCE_JSON = ROOT / "gptwords.json"
OUTPUT_JSON = ROOT / "data" / "official_senior_high_vocab.json"

VOCAB_PAGE_RANGE = range(128, 183)
COUNTRY_PAGE_RANGE = range(183, 186)
STARRED_ENTRY_RE = re.compile(r"^[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 ()'.,/&+=:-]*\*{1,2}$")


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


def load_project_words() -> set[str]:
    words: set[str] = set()
    with SOURCE_JSON.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            words.add(normalize_word(json.loads(stripped)["word"]))
    return words


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def clean_entry(entry: str) -> str:
    value = re.sub(r"\s+", " ", entry.strip())
    return value.replace(" / ", "/")


def split_starred_entries() -> tuple[list[str], list[str]]:
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(f"Missing source PDF: {SOURCE_PDF}")

    required: list[str] = []
    selective_required: list[str] = []
    reader = PdfReader(str(SOURCE_PDF))

    for page_index in VOCAB_PAGE_RANGE:
        text = reader.pages[page_index].extract_text() or ""
        for line in text.splitlines():
            stripped = line.strip()
            if not STARRED_ENTRY_RE.fullmatch(stripped):
                continue

            entry = clean_entry(re.sub(r"\*+$", "", stripped))
            stars = len(re.search(r"(\*+)$", stripped).group(1))
            if stars == 1:
                required.append(entry)
            elif stars == 2:
                selective_required.append(entry)

    return dedupe_keep_order(required), dedupe_keep_order(selective_required)


def extract_country_reference() -> list[str]:
    reader = PdfReader(str(SOURCE_PDF))
    rows: list[str] = []

    for page_index in COUNTRY_PAGE_RANGE:
        text = reader.pages[page_index].extract_text() or ""
        for line in text.splitlines():
            stripped = re.sub(r"\s+", " ", line.strip())
            if not stripped:
                continue
            if any(
                token in stripped
                for token in (
                    "主要国家名称及相关信息",
                    "续表",
                    "COUNTRY",
                    "RELATED ADJECTIVES",
                    "普通高中英语课程标准",
                )
            ):
                continue
            if re.fullmatch(r"\d+", stripped):
                continue
            if re.search(r"[\u4e00-\u9fff]", stripped) and not re.search(r"[A-Za-z]", stripped):
                continue

            match = re.match(r"^[\u4e00-\u9fff]+ (?P<english>.+)$", stripped)
            if match:
                rows.append(match.group("english"))

    return rows


def add_form(forms: set[str], value: str) -> None:
    cleaned = re.sub(r"\s+", " ", value.strip().strip("*"))
    if cleaned:
        forms.add(normalize_word(cleaned))


def line_to_forms(entry: str) -> set[str]:
    forms: set[str] = set()
    text = clean_entry(entry)
    add_form(forms, text)

    base = re.sub(r"\(.*?\)", "", text).strip()
    if base:
        add_form(forms, base)

    for piece in re.split(r"/", base):
        add_form(forms, piece)

    optional_suffix = re.fullmatch(r"(.+?)\(([^)]+)\)$", text)
    if optional_suffix:
        left, inside = optional_suffix.groups()
        if re.fullmatch(r"[A-Za-z]+", inside):
            add_form(forms, left + inside)

    for bracket in re.findall(r"\((.*?)\)", text):
        bracket = (
            bracket.replace("AmE", "")
            .replace("BrE", "")
            .replace("pl.", "")
            .replace("=", " ")
        )
        for token in re.split(r"[ /,]+", bracket):
            add_form(forms, token)

    return {form for form in forms if re.search(r"[a-z]", form) and len(form) > 1}


def resolve_entries(entries: list[str], project_words: set[str]) -> list[str]:
    resolved: set[str] = set()
    for entry in entries:
        for form in line_to_forms(entry):
            if form in project_words:
                resolved.add(form)
    return sorted(resolved)


def count_split_words(entries: list[str]) -> int:
    total = 0
    for entry in entries:
        total += len([piece for piece in re.split(r"/", entry) if piece.strip()])
    return total


def main() -> None:
    required_entries, selective_required_entries = split_starred_entries()
    project_words = load_project_words()

    required_match_forms = resolve_entries(required_entries, project_words)
    selective_required_match_forms = resolve_entries(selective_required_entries, project_words)
    senior_match_forms = sorted(set(required_match_forms) | set(selective_required_match_forms))

    payload = OrderedDict(
        [
            (
                "source",
                OrderedDict(
                    [
                        ("pdf", SOURCE_PDF.name),
                        ("official_issue_date", "2020-05-11"),
                        ("official_notice_date", "2020-06-03"),
                        (
                            "notes",
                            [
                                "Senior-high matching is derived from Appendix 2 of the official Senior High School English Curriculum Standard (2017 edition, 2020 revision).",
                                "The high-school bucket uses starred entries only: one-star entries are required senior-high vocabulary and two-star entries are selective-required senior-high vocabulary.",
                                "The searchable PDF text exposes 1497 starred lines. Slash-combined entries such as salesman/saleswoman share single lines, so raw extracted line counts and split form counts are stored separately.",
                                "Country-name reference tables are preserved separately for auditability but are not used to drive stage matching because the appendix marks them as teaching reference material.",
                            ],
                        ),
                    ]
                ),
            ),
            ("required_entries", required_entries),
            ("required_entry_line_count", len(required_entries)),
            ("required_split_form_count", count_split_words(required_entries)),
            ("required_match_forms", required_match_forms),
            ("selective_required_entries", selective_required_entries),
            ("selective_required_entry_line_count", len(selective_required_entries)),
            ("selective_required_split_form_count", count_split_words(selective_required_entries)),
            ("selective_required_match_forms", selective_required_match_forms),
            ("senior_match_forms", senior_match_forms),
            ("country_reference_rows", extract_country_reference()),
        ]
    )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        "Wrote"
        f" {OUTPUT_JSON} with {len(required_entries)} one-star lines,"
        f" {len(selective_required_entries)} two-star lines,"
        f" {len(senior_match_forms)} matched project forms."
    )


if __name__ == "__main__":
    main()
