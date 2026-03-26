from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import textwrap
import wave
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_JSON = ROOT / "gptwords.json"
LEVELS_JSON = ROOT / "word_levels.json"
LESSONS_DIR = ROOT / "lessons"
LESSON_DATA_JSON = ROOT / "data" / "study_demo_catalog.json"
WORD_LOOKUP_JSON = ROOT / "data" / "study_demo_word_lookup.json"
LESSON_MEDIA_DIR = ROOT / "media" / "study-demo"

FPS = 24
WIDTH = 1280
HEIGHT = 720
SENTENCE_GAP_SECONDS = 0.9
STAGE_PRIORITY = ["primary", "junior", "senior", "cet4", "cet6", "advanced", "extended"]
SRT_TIMECODE_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)

STAGE_META = {
    "primary": {"label": "小学", "color": (84, 146, 112), "accent": "#549270"},
    "junior": {"label": "初中", "color": (94, 162, 126), "accent": "#5ea27e"},
    "senior": {"label": "高中", "color": (102, 137, 187), "accent": "#6689bb"},
    "cet4": {"label": "四级", "color": (124, 109, 177), "accent": "#7c6db1"},
    "cet6": {"label": "六级", "color": (144, 99, 170), "accent": "#9063aa"},
    "advanced": {"label": "更高阶", "color": (118, 90, 140), "accent": "#765a8c"},
    "extended": {"label": "扩展", "color": (117, 124, 130), "accent": "#757c82"},
}


def normalize_word(word: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", word.lower())


def tokenize(sentence: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)


def powershell_escape(value: str) -> str:
    return value.replace("'", "''")


def synthesize_wav(text: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    escaped_text = powershell_escape(text)
    escaped_path = powershell_escape(str(destination))
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$speaker.SelectVoice('Microsoft Zira Desktop'); "
        "$speaker.Rate = -1; "
        f"$speaker.SetOutputToWaveFile('{escaped_path}'); "
        f"$speaker.Speak('{escaped_text}'); "
        "$speaker.Dispose();"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def wrap_text(sentence: str, width: int = 34) -> list[str]:
    return textwrap.wrap(sentence, width=width) or [sentence]


def put_text(
    frame: np.ndarray,
    text: str,
    position: tuple[int, int],
    scale: float,
    color: tuple[int, int, int],
    thickness: int = 2,
) -> None:
    cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def build_frame(
    lesson: dict[str, Any],
    sentence: dict[str, Any],
    sentence_index: int,
    progress_ratio: float,
) -> np.ndarray:
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    top = np.array([245, 239, 224], dtype=np.uint8)
    bottom = np.array([231, 222, 206], dtype=np.uint8)
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        color = (top * (1 - ratio) + bottom * ratio).astype(np.uint8)
        frame[y, :] = color

    stage = STAGE_META[lesson["stage"]]
    accent = np.array(stage["color"], dtype=np.uint8)
    cv2.rectangle(frame, (0, 0), (WIDTH, 150), tuple(int(x) for x in accent.tolist()), thickness=-1)
    cv2.rectangle(frame, (70, 88), (610, 620), (250, 247, 240), thickness=-1)
    cv2.rectangle(frame, (700, 116), (1180, 604), (249, 245, 238), thickness=-1)

    cv2.rectangle(frame, (70, 88), (610, 620), (226, 216, 198), thickness=2)
    cv2.rectangle(frame, (700, 116), (1180, 604), (226, 216, 198), thickness=2)

    put_text(frame, "Curriculum Lesson", (90, 70), 1.0, (248, 248, 248), 2)
    put_text(frame, lesson["title"], (96, 168), 1.2, (33, 44, 40), 3)
    put_text(frame, stage["label"], (1000, 70), 1.05, (248, 248, 248), 2)
    put_text(frame, lesson["subtitle"], (930, 560), 0.9, (90, 100, 95), 2)

    badge_text = f"Sentence {sentence_index + 1}"
    cv2.rectangle(frame, (96, 206), (280, 252), tuple(int(min(255, x + 35)) for x in accent.tolist()), thickness=-1)
    put_text(frame, badge_text, (114, 238), 0.8, (250, 250, 250), 2)

    lines = wrap_text(sentence["en"], width=34)
    y = 320
    for line in lines:
        put_text(frame, line, (96, y), 0.98, (33, 44, 40), 2)
        y += 52

    put_text(frame, "Tap a sentence to replay it.", (96, 566), 0.72, (92, 106, 99), 2)
    put_text(frame, "Click a word to see its level and note.", (726, 186), 0.72, (92, 106, 99), 2)

    words = tokenize(sentence["en"])[:6]
    box_y = 244
    for word in words:
        width_box = max(140, 26 + len(word) * 16)
        cv2.rectangle(frame, (726, box_y), (726 + width_box, box_y + 56), tuple(int(min(255, x + 22)) for x in accent.tolist()), thickness=-1)
        put_text(frame, word, (746, box_y + 36), 0.78, (250, 250, 250), 2)
        box_y += 72

    progress_x = 96
    progress_y = 660
    progress_w = 1088
    cv2.rectangle(frame, (progress_x, progress_y), (progress_x + progress_w, progress_y + 16), (217, 211, 198), thickness=-1)
    cv2.rectangle(frame, (progress_x, progress_y), (progress_x + int(progress_w * progress_ratio), progress_y + 16), tuple(int(x) for x in accent.tolist()), thickness=-1)
    return frame


def create_video(lesson: dict[str, Any], video_path: Path) -> None:
    video_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create video: {video_path}")

    total_duration = lesson["sentences"][-1]["end"]
    for sentence_index, sentence in enumerate(lesson["sentences"]):
        start = sentence["start"]
        end = sentence["end"]
        frame_count = max(1, round((end - start) * FPS))
        for frame_index in range(frame_count):
            global_progress = min(1.0, (start + frame_index / FPS) / max(total_duration, 0.001))
            frame = build_frame(lesson, sentence, sentence_index, global_progress)
            writer.write(frame)
    writer.release()


def extract_brief(content: str) -> str:
    normalized = content.replace("\\n", "\n").replace("\r", "")
    match = re.search(r"### 分析词义\s*(.*?)(?:###|\Z)", normalized, flags=re.S)
    if match:
        text = re.sub(r"\s+", " ", match.group(1)).strip()
    else:
        text = re.sub(r"\s+", " ", normalized).strip()
    return text[:180].strip()


def load_word_sources() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    word_entries: dict[str, dict[str, Any]] = {}
    with SOURCE_JSON.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            entry = json.loads(stripped)
            key = normalize_word(entry["word"])
            word_entries.setdefault(key, entry)

    level_map_raw = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    level_map = {normalize_word(key): value for key, value in level_map_raw.items()}
    return word_entries, level_map


def create_word_lookup(lessons: list[dict[str, Any]]) -> dict[str, Any]:
    word_entries, level_map = load_word_sources()
    selected_words = sorted({normalize_word(word) for lesson in lessons for sentence in lesson["sentences"] for word in sentence["tokens"]})
    lookup: dict[str, Any] = {}

    for word in selected_words:
        entry = word_entries.get(word)
        lookup[word] = {
            "word": entry["word"] if entry else word,
            "level": level_map.get(word, "extended"),
            "brief": extract_brief(entry["content"]) if entry else "No local explanation found yet.",
        }
    return lookup


def stage_counts() -> dict[str, int]:
    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    counts = Counter(levels.values())
    return {key: counts.get(key, 0) for key in STAGE_META}


def validate_lesson_source(lesson: dict[str, Any], lesson_dir: Path) -> None:
    required = ["schemaVersion", "id", "stage", "title", "subtitle", "summary", "sentences"]
    missing = [key for key in required if key not in lesson]
    if missing:
        raise ValueError(f"{lesson_dir / 'lesson.json'} missing required fields: {', '.join(missing)}")
    if lesson["schemaVersion"] != 1:
        raise ValueError(f"{lesson_dir / 'lesson.json'} has unsupported schemaVersion: {lesson['schemaVersion']}")
    if lesson["id"] != lesson_dir.name:
        raise ValueError(f"{lesson_dir / 'lesson.json'} id must match directory name")
    if lesson["stage"] not in STAGE_META:
        raise ValueError(f"{lesson_dir / 'lesson.json'} has unsupported stage: {lesson['stage']}")
    if not isinstance(lesson["sentences"], list) or not lesson["sentences"]:
        raise ValueError(f"{lesson_dir / 'lesson.json'} must contain at least one sentence")

    seen_ids: set[str] = set()
    previous_end = -1.0
    for sentence in lesson["sentences"]:
        sentence_id = sentence.get("id")
        if not sentence_id:
            raise ValueError(f"{lesson_dir / 'lesson.json'} contains a sentence without id")
        if sentence_id in seen_ids:
            raise ValueError(f"{lesson_dir / 'lesson.json'} contains duplicate sentence id: {sentence_id}")
        seen_ids.add(sentence_id)
        if not sentence.get("en") or not sentence.get("zh"):
            raise ValueError(f"{lesson_dir / 'lesson.json'} sentence {sentence_id} must include en and zh")
        if "start" in sentence or "end" in sentence:
            start = float(sentence.get("start", -1))
            end = float(sentence.get("end", -1))
            if start < 0 or end <= start:
                raise ValueError(f"{lesson_dir / 'lesson.json'} sentence {sentence_id} has invalid start/end")
            if start < previous_end:
                raise ValueError(f"{lesson_dir / 'lesson.json'} sentence {sentence_id} timing overlaps previous sentence")
            previous_end = end


def optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    return float(stripped)


def parse_srt_timestamp(value: str) -> float:
    normalized = value.replace(",", ".")
    hours, minutes, seconds = normalized.split(":")
    return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)


def compact_subtitle_text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return text


def parse_srt_cues(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8-sig")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError(f"{path} is empty")

    blocks = re.split(r"\n\s*\n", normalized)
    cues: list[dict[str, Any]] = []

    for block_index, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        if len(lines) >= 2 and lines[0].isdigit():
            timing_line = lines[1]
            text_lines = lines[2:]
        else:
            timing_line = lines[0]
            text_lines = lines[1:]

        match = SRT_TIMECODE_RE.fullmatch(timing_line)
        if not match:
            raise ValueError(f"{path} cue {block_index} has invalid timecode: {timing_line}")
        text = compact_subtitle_text(text_lines)
        if not text:
            raise ValueError(f"{path} cue {block_index} does not contain subtitle text")

        cues.append(
            {
                "id": f"s{len(cues) + 1}",
                "start": parse_srt_timestamp(match.group("start")),
                "end": parse_srt_timestamp(match.group("end")),
                "text": text,
            }
        )

    if not cues:
        raise ValueError(f"{path} does not contain any valid subtitle cues")
    return cues


def load_csv_sentences(lesson_dir: Path, source: dict[str, Any]) -> list[dict[str, Any]]:
    source_file = source.get("file")
    if not source_file:
        raise ValueError(f"{lesson_dir / 'lesson.json'} csv-import source must include file")

    csv_path = lesson_dir / source_file
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV source not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        required_columns = {"id", "en", "zh"}
        missing_columns = sorted(required_columns - set(fieldnames))
        if missing_columns:
            raise ValueError(f"{csv_path} missing required columns: {', '.join(missing_columns)}")

        sentences: list[dict[str, Any]] = []
        for row_index, row in enumerate(reader, start=2):
            sentence_id = (row.get("id") or "").strip()
            en = (row.get("en") or "").strip()
            zh = (row.get("zh") or "").strip()
            if not sentence_id or not en or not zh:
                raise ValueError(f"{csv_path} row {row_index} must include non-empty id, en, zh")

            sentence: dict[str, Any] = {
                "id": sentence_id,
                "en": en,
                "zh": zh,
            }

            start = optional_float(row.get("start"))
            end = optional_float(row.get("end"))
            if start is not None:
                sentence["start"] = start
            if end is not None:
                sentence["end"] = end

            audio = (row.get("audio") or "").strip()
            if audio:
                sentence["audio"] = audio

            tokens = (row.get("tokens") or "").strip()
            if tokens:
                sentence["tokens"] = [part.strip() for part in re.split(r"[|,]", tokens) if part.strip()]

            notes = (row.get("notes") or "").strip()
            if notes:
                sentence["notes"] = notes

            sentences.append(sentence)

    if not sentences:
        raise ValueError(f"{csv_path} does not contain any sentence rows")
    return sentences


def load_srt_sentences(lesson_dir: Path, source: dict[str, Any]) -> list[dict[str, Any]]:
    en_file = source.get("enFile")
    zh_file = source.get("zhFile")
    if not en_file or not zh_file:
        raise ValueError(f"{lesson_dir / 'lesson.json'} srt-import source must include enFile and zhFile")

    en_path = lesson_dir / en_file
    zh_path = lesson_dir / zh_file
    if not en_path.exists():
        raise FileNotFoundError(f"SRT source not found: {en_path}")
    if not zh_path.exists():
        raise FileNotFoundError(f"SRT source not found: {zh_path}")

    en_cues = parse_srt_cues(en_path)
    zh_cues = parse_srt_cues(zh_path)
    if len(en_cues) != len(zh_cues):
        raise ValueError(f"{lesson_dir / 'lesson.json'} bilingual SRT files must contain the same number of cues")

    sentences: list[dict[str, Any]] = []
    for index, (en_cue, zh_cue) in enumerate(zip(en_cues, zh_cues), start=1):
        sentences.append(
            {
                "id": f"s{index}",
                "en": en_cue["text"],
                "zh": zh_cue["text"],
                "start": en_cue["start"],
                "end": en_cue["end"],
            }
        )
    return sentences


def materialize_lesson_source(lesson: dict[str, Any], lesson_dir: Path) -> dict[str, Any]:
    source = lesson.get("source") or {"type": "manual"}
    source_type = source.get("type", "manual")
    materialized = dict(lesson)

    if source_type == "manual":
        return materialized
    if source_type == "csv-import":
        materialized["sentences"] = load_csv_sentences(lesson_dir, source)
        return materialized
    if source_type == "srt-import":
        materialized["sentences"] = load_srt_sentences(lesson_dir, source)
        return materialized

    raise ValueError(f"{lesson_dir / 'lesson.json'} has unsupported source.type: {source_type}")


def load_lesson_sources() -> list[tuple[Path, dict[str, Any]]]:
    if not LESSONS_DIR.exists():
        raise FileNotFoundError(f"Lesson source directory not found: {LESSONS_DIR}")

    lesson_files = sorted(LESSONS_DIR.glob("*/lesson.json"))
    if not lesson_files:
        raise FileNotFoundError(f"No lesson source files found under: {LESSONS_DIR}")

    loaded: list[tuple[Path, dict[str, Any]]] = []
    for lesson_file in lesson_files:
        lesson_dir = lesson_file.parent
        lesson = json.loads(lesson_file.read_text(encoding="utf-8"))
        lesson = materialize_lesson_source(lesson, lesson_dir)
        validate_lesson_source(lesson, lesson_dir)
        loaded.append((lesson_dir, lesson))

    stage_index = {stage: index for index, stage in enumerate(STAGE_PRIORITY)}
    loaded.sort(key=lambda item: (stage_index.get(item[1]["stage"], 999), int(item[1].get("displayOrder", 9999)), item[1]["id"]))
    return loaded


def resolve_existing_audio(source_audio: str, lesson_dir: Path, sentence_index: int, output_dir: Path) -> Path:
    source_path = (lesson_dir / source_audio).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Audio source not found: {source_path}")
    target_path = output_dir / f"sentence-{sentence_index + 1:02d}{source_path.suffix.lower()}"
    if source_path != target_path.resolve():
        shutil.copy2(source_path, target_path)
    return target_path


def resolve_existing_video(source_video: str, lesson_dir: Path, output_dir: Path) -> Path:
    source_path = (lesson_dir / source_video).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Video source not found: {source_path}")
    target_path = output_dir / source_path.name
    if source_path != target_path.resolve():
        shutil.copy2(source_path, target_path)
    return target_path


def build_lessons() -> list[dict[str, Any]]:
    built: list[dict[str, Any]] = []
    for lesson_dir, lesson in load_lesson_sources():
        output_dir = LESSON_MEDIA_DIR / lesson["id"]
        output_dir.mkdir(parents=True, exist_ok=True)

        sentences: list[dict[str, Any]] = []
        current_time = 0.0

        for index, source_sentence in enumerate(lesson["sentences"]):
            output_audio_path = output_dir / f"sentence-{index + 1:02d}.wav"
            if source_sentence.get("audio"):
                resolved_audio = resolve_existing_audio(source_sentence["audio"], lesson_dir, index, output_dir)
            else:
                resolved_audio = output_audio_path
                synthesize_wav(source_sentence["en"], resolved_audio)

            audio_duration = wav_duration_seconds(resolved_audio)

            if "start" in source_sentence and "end" in source_sentence:
                start = round(float(source_sentence["start"]), 3)
                end = round(float(source_sentence["end"]), 3)
                duration = round(end - start, 3)
            else:
                duration = round(audio_duration + SENTENCE_GAP_SECONDS, 3)
                start = round(current_time, 3)
                end = round(current_time + duration, 3)

            tokens = source_sentence.get("tokens") or tokenize(source_sentence["en"])
            sentences.append(
                {
                    "id": f"{lesson['id']}-sentence-{index + 1}",
                    "index": index,
                    "en": source_sentence["en"],
                    "zh": source_sentence["zh"],
                    "start": start,
                    "end": end,
                    "duration": duration,
                    "audio": f"./media/study-demo/{lesson['id']}/{resolved_audio.name}",
                    "tokens": tokens,
                }
            )
            current_time = max(current_time, end)

        built_lesson = {
            "id": lesson["id"],
            "stage": lesson["stage"],
            "stageLabel": STAGE_META[lesson["stage"]]["label"],
            "title": lesson["title"],
            "subtitle": lesson["subtitle"],
            "summary": lesson["summary"],
            "videoMode": lesson.get("videoMode", "generated-slide-video"),
            "duration": round(current_time, 3),
            "video": f"./media/study-demo/{lesson['id']}/lesson.mp4",
            "sentences": sentences,
        }

        video_mode = lesson.get("videoMode", "generated-slide-video")
        if video_mode == "generated-slide-video":
            create_video(built_lesson, output_dir / "lesson.mp4")
        elif video_mode == "external-video":
            source = lesson.get("source") or {}
            source_video = source.get("video")
            if not source_video:
                raise ValueError(f"{lesson_dir / 'lesson.json'} with videoMode external-video must include source.video")
            resolved_video = resolve_existing_video(source_video, lesson_dir, output_dir)
            built_lesson["video"] = f"./media/study-demo/{lesson['id']}/{resolved_video.name}"
        else:
            raise ValueError(f"Unsupported videoMode for {lesson['id']}: {video_mode}")
        built.append(built_lesson)
    return built


def main() -> None:
    lessons = build_lessons()
    lookup = create_word_lookup(lessons)
    payload = {
        "meta": {
            "title": "Curriculum Stage + Sentence Study Demo",
            "stageCounts": stage_counts(),
        },
        "stages": {
            key: {"label": value["label"], "accent": value["accent"]}
            for key, value in STAGE_META.items()
        },
        "lessons": lessons,
    }

    LESSON_DATA_JSON.parent.mkdir(parents=True, exist_ok=True)
    LESSON_DATA_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    WORD_LOOKUP_JSON.write_text(json.dumps(lookup, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {LESSON_DATA_JSON} and {WORD_LOOKUP_JSON}")


if __name__ == "__main__":
    main()
