from __future__ import annotations

import json
import re
from difflib import get_close_matches
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = ROOT / "official_english_curriculum_2022.pdf"
SOURCE_JSON = ROOT / "gptwords.json"
OUTPUT_JSON = ROOT / "data" / "official_curriculum_vocab.json"

PRIMARY_PAGE_RANGE = range(94, 104)
JUNIOR_PAGE_RANGE = range(104, 139)
COLUMN_BOUNDS = ((40, 60, 210, 690), (230, 60, 390, 690))

PRIMARY_FIXES = {
    "aple": "apple",
    "bg": "bag",
    "basketall": "basketball",
    "coOw": "cow",
    "dol": "doll",
    "ifty": "fifty",
    "gif": "gift",
    "goodbye (bye)": "goodbye(bye)",
    "grandfather (grandpa)": "grandfather(grandpa)",
    "grandmother (grandma)": "grandmother(grandma)",
    "hppy": "happy",
    "maths (=mathematics, AmE": "maths(=mathematics, AmE math)",
    "mother (mum AmE mom)": "mother(mum AmE mom)",
    "nty": "city",
    "o'clock": "o'clock",
    "oclock": "o'clock",
    "offr": "offer",
    "to0": "too",
    "toP": "top",
    "盈": "sad",
    "客召": "see",
}

JUNIOR_FIXES = {
    "AI(=artificial intelligenc": "AI(=artificial intelligence)",
    "activiy": "activity",
    "a.m": "a.m.",
    "arive": "arrive",
    "blod": "blood",
    "borm": "born",
    "bow/l": "bowl",
    "buly": "busy",
    "ccoolmoeu r(AmE color)": "colour(AmE color)",
    "ccoolmoeur(AmE color)": "colour(AmE color)",
    "centre(AmE center)": "centre(AmE center)",
    "classoom": "classroom",
    "coffe": "coffee",
    "cousin": "cousin",
    "crtain": "curtain",
    "dialogue(AmE dialog)": "dialogue(AmE dialog)",
    "dffence": "difference",
    "diffcult": "difficult",
    "dol": "doll",
    "ear": "ear",
    "emperor/empress": "emperor/empress",
    "eveningt": "evening",
    "exam (=examination)": "exam(=examination)",
    "fal": "fall",
    "father (dad)": "father(dad)",
    "fim": "film",
    "fireman (pl. firemen)": "fireman(pl. firemen)",
    "fooball": "football",
    "fridge(=refrigerator)": "fridge(=refrigerator)",
    "fuit": "fruit",
    "g0al": "goal",
    "gentleman(pl. gentlemen)": "gentleman(pl. gentlemen)",
    "gif": "gift",
    "ginl": "girl",
    "goodbye(bye)": "goodbye(bye)",
    "grandfather(grandpa)": "grandfather(grandpa)",
    "grandmother(grandma)": "grandmother(grandma)",
    "grey (AmE gray)": "grey(AmE gray)",
    "gym (=gymnasium)": "gym(=gymnasium)",
    "have (has)": "have(has)",
    "honour (AmE honor)": "honour(AmE honor)",
    "host/hostess": "host/hostess",
    "humour(AmE humor)": "humour(AmE humor)",
    "hury": "hurry",
    "ice cream": "ice cream",
    "ice cream*": "ice cream",
    "illess": "illness",
    "kilo (=kilogram)": "kilo(=kilogram)",
    "kilometre(AmE kilometer)": "kilometre(AmE kilometer)",
    "knife(pl. knives)": "knife(pl. knives)",
    "lab(=laboratory)": "lab(=laboratory)",
    "leaf (pl. leaves)": "leaf(pl. leaves)",
    "lef": "left",
    "leter": "letter",
    "lif": "lift",
    "man (pl. men)": "man(pl. men)",
    "maths(=mathematics, A": "maths(=mathematics, AmE math)",
    "math)minute": "minute",
    "medium(pl. media)": "medium(pl. media)",
    "metre(AmE meter)": "metre(AmE meter)",
    "mother(mum AmE mo": "mother(mum AmE mom)",
    "mouse (pl. mice)": "mouse(pl. mice)",
    "Mr(AmE Mr.)": "Mr(AmE Mr.)",
    "Mrs(AmE Mrs.)": "Mrs(AmE Mrs.)",
    "Ms(AmE Ms.)": "Ms(AmE Ms.)",
    "necesary": "necessary",
    "neighbour(AmE neighbor)": "neighbour(AmE neighbor)",
    "ninetieth": "ninetieth",
    "oclock": "o'clock",
    "offr": "offer",
    "OK": "OK",
    "pai": "pair",
    "PE(=physical education)": "PE(=physical education)",
    "peper": "pepper",
    "per cent(AmE percent)": "per cent(AmE percent)",
    "photo (=photograph)": "photo(=photograph)",
    "p.m": "p.m.",
    "policeman/policewoman (pl.": "policeman/policewoman(pl. policemen/policewomen)",
    "policemen/policewomen": "policemen/policewomen",
    "postman (pl. postmen)": "postman(pl. postmen)",
    "prince/princess": "prince/princess",
    "programme(AmE progra": "programme(AmE program)",
    "put": "put",
    "realise(AmE realize)": "realise(AmE realize)",
    "recognise(AmE recogniz": "recognise(AmE recognize)",
    "recyele": "recycle",
    "sad t": "sad",
    "scholbag": "schoolbag",
    "sheep (pl.sheep)": "sheep(pl. sheep)",
    "shelf(pl.shelves)": "shelf(pl. shelves)",
    "sthip": "ship",
    "sily": "silly",
    "somebody / someone": "somebody/someone",
    "sory": "sorry",
    "spech": "speech",
    "spig": "spring",
    "stil": "still",
    "uffer": "suffer",
    "tenis": "tennis",
    "terible": "terrible",
    "theatre(AmE theater)": "theatre(AmE theater)",
    "toilt": "toilet",
    "tooth (pl. teeth)": "tooth(pl. teeth)",
    "towards(AmE toward)": "towards(AmE toward)",
    "trafic": "traffic",
    "TV(=television)": "TV(=television)",
    "ty": "try",
    "until(tilI)": "until(till)",
    "wife(pl. wives)": "wife(pl. wives)",
    "wil": "will",
    "wolf(pl. wolves)": "wolf(pl. wolves)",
    "woman(pl. women)": "woman(pl. women)",
    "wory": "worry",
    "yourself (pl. yourselves": "yourself(pl. yourselves)",
    "z0o": "zoo",
    "Wednesay": "Wednesday",
    "Septembe": "September",
    "Novembe": "November",
    "Decembe": "December",
    "fth": "fifth",
    "cighth": "eighth",
    "seventee": "seventeen",
    "fteenth": "fifteenth",
    "thrtieth": "thirtieth",
    "fftieth": "fiftieth",
}

PRIMARY_SKIP = {
    "88",
    "92",
    "93",
    "94",
    "95",
    "96",
    "97",
    "200",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "?",
    "人",
}

JUNIOR_SKIP_PREFIXES = (
    "说明",
    "1.根据核心素养的培",
    "2.本词汇表采用英式",
    "3.为体现在具体语境",
    "4.名词复数特殊变化",
    "5.数词",
    "6.部分地理名称",
    "7.不规则动词表",
    "8.本词汇表不列词组",
    "9.本词汇表不列语法",
    "10.本词汇表不列可根",
    "目标和课程内容六要素的要求",
    "表共收录1600个单词",
    "据实际情况在本词汇表的基础上",
    "语拼写形式",
    "学习和使用单词的理念",
    "动词特殊人称变化",
    "词）、月份、星期等单独列出",
    "信息，部分国家、重要组织机",
    "国文化专有名词单独列出",
    "部分国家、",
    "部分重要节日",
    "重要组织机构名称缩写",
    "名称、中国文化专有名词",
    "景点 其他专有名词",
    "Childrens Day Mo",
)

PRIMARY_SUPPLEMENTS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
    "million",
    "first",
    "second",
    "third",
    "fourth",
    "fifth",
    "sixth",
    "seventh",
    "eighth",
    "ninth",
    "tenth",
    "eleventh",
    "twelfth",
    "thirteenth",
    "fourteenth",
    "fifteenth",
    "sixteenth",
    "seventeenth",
    "eighteenth",
    "nineteenth",
    "twentieth",
    "thirtieth",
    "fortieth",
    "fiftieth",
    "sixtieth",
    "seventieth",
    "eightieth",
    "ninetieth",
    "hundredth",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

JUNIOR_SPECIALS = [
    "Africa",
    "African",
    "America",
    "American",
    "Antarctica",
    "Asia",
    "Asian",
    "Australia",
    "Australian",
    "Britain",
    "British",
    "Canada",
    "Canadian",
    "China",
    "Chinese",
    "England",
    "English",
    "Europe",
    "European",
    "France",
    "French",
    "Germany",
    "German",
    "India",
    "Indian",
    "Italy",
    "Italian",
    "Japan",
    "Japanese",
    "London",
    "New York",
    "New Zealand",
    "New Zealander",
    "Paris",
    "Russia",
    "Russian",
    "Singapore",
    "Singaporean",
    "South Africa",
    "South African",
    "The Atlantic Ocean",
    "The Indian Ocean",
    "The Pacific Ocean",
    "The United Kingdom",
    "UK",
    "The United States of America",
    "USA",
    "CPC",
    "PLA",
    "PRC",
    "UN",
    "UNESCO",
    "WHO",
    "WTO",
    "Children's Day",
    "Double Ninth Festival",
    "Dragon Boat Festival",
    "Labour Day",
    "Lantern Festival",
    "Mid-Autumn Festival",
    "National Day",
    "New Year's Day",
    "PLA Day",
    "Spring Festival",
    "Teachers' Day",
    "Tomb-sweeping Day",
    "Women's Day",
    "Mount Huangshan",
    "Mount Qomolangma",
    "Mount Taishan",
    "The Changjiang River",
    "The Yangtze River",
    "The Great Wall",
    "The Palace Museum",
    "The Yellow River",
    "Tian'anmen Square",
    "Beijing opera",
    "Peking opera",
    "Beijing roast duck",
    "hot pot",
    "lunar calendar",
    "mooncake",
    "paper-cut",
    "qipao",
    "Spring Festival couplets",
    "spring roll",
    "The Silk Road",
    "Traditional Chinese Medicine",
    "TCM",
]


def normalize_word(word: str) -> str:
    return (
        word.strip()
        .lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("‐", "-")
        .replace("–", "-")
        .replace("—", "-")
    )


def load_project_words() -> set[str]:
    words: set[str] = set()
    with SOURCE_JSON.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                words.add(normalize_word(json.loads(line)["word"]))
    return words


def extract_lines(page_range: range) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_index in page_range:
            page = pdf.pages[page_index]
            for bounds in COLUMN_BOUNDS:
                text = page.crop(bounds).extract_text() or ""
                lines.extend(line.strip() for line in text.splitlines() if line.strip())
    return lines


def clean_line(line: str) -> str:
    text = line.strip().strip(' "\'“”‘’。，,.;:[]{}')
    text = text.replace("（", "(").replace("）", ")").replace("，", ",")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def apply_fixes(lines: list[str], fixes: dict[str, str], skip_values: set[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        value = fixes.get(clean_line(line), clean_line(line))
        if not value:
            continue
        if value in skip_values:
            continue
        if not re.search(r"[A-Za-z]", value):
            continue
        cleaned.append(value)
    return cleaned


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def should_skip_junior(line: str) -> bool:
    if not re.search(r"[A-Za-z]", line):
        return True
    if line in {"98", "127", "128", "129", "130", "131", "132"}:
        return True
    if line in {"Y", "Z", "Q", "R", "S", "T", "U", "V", "W", "X"}:
        return True
    if any(line.startswith(prefix) for prefix in JUNIOR_SKIP_PREFIXES):
        return True
    return False


def line_to_forms(entry: str) -> set[str]:
    forms: set[str] = set()
    text = entry.strip().strip('"').strip("'").strip("*")
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" /", "/").replace("/ ", "/")
    text = re.sub(r"\s+n\.,?\s*adj\.$", "", text)
    text = re.sub(r"\s+n\.$", "", text)
    text = re.sub(r"\s+adj\.$", "", text)
    text = text.strip()

    if not text:
        return forms

    def add_form(value: str) -> None:
        value = value.strip().strip('"').strip("'").strip("*")
        value = re.sub(r"\s+", " ", value)
        if value:
            forms.add(normalize_word(value))

    add_form(text)

    base = re.sub(r"\(.*?\)", "", text).strip()
    if base:
        add_form(base)

    for piece in re.split(r"/", base):
        add_form(piece)

    for bracket in re.findall(r"\((.*?)\)", text):
        bracket = bracket.replace("AmE", "").replace("pl.", "").replace("=", "")
        bracket = bracket.replace(",", " ")
        for token in re.split(r"[ /]+", bracket):
            add_form(token)

    return {form for form in forms if re.search(r"[a-z]", form)}


def fuzzy_project_match(token: str, project_words: set[str]) -> set[str]:
    if token in project_words:
        return {token}

    if len(token) <= 2:
        return set()

    candidates = sorted(word for word in project_words if word[:1] == token[:1] and abs(len(word) - len(token)) <= 3)
    matches = get_close_matches(token, candidates, n=3, cutoff=0.82)
    return set(matches)


def resolve_entries(entries: list[str], project_words: set[str]) -> set[str]:
    resolved: set[str] = set()
    for entry in entries:
        for form in line_to_forms(entry):
            if form in project_words:
                resolved.add(form)
            else:
                resolved.update(fuzzy_project_match(form, project_words))
    return resolved


def main() -> None:
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(f"Missing source PDF: {SOURCE_PDF}")

    project_words = load_project_words()

    primary_raw = extract_lines(PRIMARY_PAGE_RANGE)
    primary_entries = dedupe_keep_order(
        apply_fixes(primary_raw, PRIMARY_FIXES, PRIMARY_SKIP) + PRIMARY_SUPPLEMENTS
    )

    junior_raw = extract_lines(JUNIOR_PAGE_RANGE)
    junior_cleaned = []
    for line in junior_raw:
        cleaned = JUNIOR_FIXES.get(clean_line(line), clean_line(line))
        if should_skip_junior(cleaned):
            continue
        junior_cleaned.append(cleaned)

    junior_entries = dedupe_keep_order(junior_cleaned + PRIMARY_SUPPLEMENTS + JUNIOR_SPECIALS)

    primary_matches = sorted(resolve_entries(primary_entries, project_words))
    junior_matches = sorted(resolve_entries(junior_entries, project_words))

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {
            "pdf": SOURCE_PDF.name,
            "official_release_date": "2022-04-21",
            "notes": [
                "Primary/junior matching is derived from the official 2022 compulsory education English curriculum standard appendix.",
                "Primary matching includes explicit supplements for number/month/week vocabulary because these are listed separately in the official appendix notes and are fundamental to the project classification goal.",
                "Later buckets such as senior/CET/TOEFL/GRE remain handled by the existing public wordlists in the build script.",
            ],
        },
        "level2_entries": primary_entries,
        "level2_match_forms": primary_matches,
        "level3_entries": junior_entries,
        "level3_match_forms": junior_matches,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Wrote {OUTPUT_JSON} with {len(primary_matches)} primary project matches and {len(junior_matches)} junior project matches."
    )


if __name__ == "__main__":
    main()
