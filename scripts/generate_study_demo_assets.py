from __future__ import annotations

import json
import math
import re
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
LESSON_DATA_JSON = ROOT / "data" / "study_demo_catalog.json"
WORD_LOOKUP_JSON = ROOT / "data" / "study_demo_word_lookup.json"
LESSON_MEDIA_DIR = ROOT / "media" / "study-demo"

FPS = 24
WIDTH = 1280
HEIGHT = 720

STAGE_META = {
    "primary": {"label": "小学", "color": (84, 146, 112), "accent": "#549270"},
    "junior": {"label": "初中", "color": (94, 162, 126), "accent": "#5ea27e"},
    "senior": {"label": "高中", "color": (102, 137, 187), "accent": "#6689bb"},
    "cet4": {"label": "四级", "color": (124, 109, 177), "accent": "#7c6db1"},
    "cet6": {"label": "六级", "color": (144, 99, 170), "accent": "#9063aa"},
    "advanced": {"label": "更高阶", "color": (118, 90, 140), "accent": "#765a8c"},
    "extended": {"label": "扩展", "color": (117, 124, 130), "accent": "#757c82"},
}

LESSONS = [
    {
        "id": "primary-school-morning",
        "stage": "primary",
        "title": "My School Morning",
        "subtitle": "小学示范课",
        "summary": "用小学阶段高频词做一个早晨上学场景练习。",
        "sentences": [
            {"en": "I walk to school with my best friend.", "zh": "我和我最好的朋友走路去学校。"},
            {"en": "Our teacher opens the classroom at eight.", "zh": "我们的老师八点打开教室。"},
            {"en": "We read a short story and answer easy questions.", "zh": "我们读一个小故事，并回答简单的问题。"},
            {"en": "After class, we play basketball in the sun.", "zh": "下课后，我们在阳光下打篮球。"},
        ],
    },
    {
        "id": "junior-spring-city",
        "stage": "junior",
        "title": "Spring in the City",
        "subtitle": "初中示范课",
        "summary": "围绕天气、出行和周末计划做句子学习。",
        "sentences": [
            {"en": "The weather changes quickly in this city.", "zh": "这座城市的天气变化很快。"},
            {"en": "I usually carry an umbrella in spring.", "zh": "春天我通常会带一把伞。"},
            {"en": "My parents and I sometimes travel by underground.", "zh": "我和父母有时乘地铁出行。"},
            {"en": "At night, we talk about our plans for the weekend.", "zh": "到了晚上，我们会聊周末计划。"},
        ],
    },
    {
        "id": "senior-learning-doors",
        "stage": "senior",
        "title": "Learning Opens Doors",
        "subtitle": "高中示范课",
        "summary": "围绕学习习惯、自我成长和长期目标组织句子练习。",
        "sentences": [
            {"en": "Learning English gives us access to new ideas.", "zh": "学习英语让我们接触到新的想法。"},
            {"en": "A good habit can change your future step by step.", "zh": "一个好习惯可以一步一步改变你的未来。"},
            {"en": "Every challenge becomes smaller after steady practice.", "zh": "经过稳定练习后，每个挑战都会变得更小。"},
            {"en": "With patience, you can achieve more than you expect.", "zh": "有了耐心，你能做到比预期更多的事情。"},
        ],
    },
]


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


def put_text(frame: np.ndarray, text: str, position: tuple[int, int], scale: float, color: tuple[int, int, int], thickness: int = 2) -> None:
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


def build_lessons() -> list[dict[str, Any]]:
    built: list[dict[str, Any]] = []
    for lesson in LESSONS:
        lesson_dir = LESSON_MEDIA_DIR / lesson["id"]
        sentences: list[dict[str, Any]] = []
        current_time = 0.0

        for index, source_sentence in enumerate(lesson["sentences"]):
            audio_path = lesson_dir / f"sentence-{index + 1:02d}.wav"
            synthesize_wav(source_sentence["en"], audio_path)
            audio_duration = wav_duration_seconds(audio_path)
            duration = round(audio_duration + 0.9, 3)
            start = round(current_time, 3)
            end = round(current_time + duration, 3)
            tokens = tokenize(source_sentence["en"])
            sentences.append(
                {
                    "id": f"{lesson['id']}-sentence-{index + 1}",
                    "index": index,
                    "en": source_sentence["en"],
                    "zh": source_sentence["zh"],
                    "start": start,
                    "end": end,
                    "duration": duration,
                    "audio": f"./media/study-demo/{lesson['id']}/sentence-{index + 1:02d}.wav",
                    "tokens": tokens,
                }
            )
            current_time = end

        built_lesson = {
            "id": lesson["id"],
            "stage": lesson["stage"],
            "stageLabel": STAGE_META[lesson["stage"]]["label"],
            "title": lesson["title"],
            "subtitle": lesson["subtitle"],
            "summary": lesson["summary"],
            "duration": round(current_time, 3),
            "video": f"./media/study-demo/{lesson['id']}/lesson.mp4",
            "sentences": sentences,
        }
        create_video(built_lesson, lesson_dir / "lesson.mp4")
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
