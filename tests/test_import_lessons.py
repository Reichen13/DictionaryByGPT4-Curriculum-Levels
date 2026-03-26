import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import import_lessons


class CsvImportLessonSourceTests(unittest.TestCase):
    def test_load_lesson_sources_expands_csv_import_into_sentences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lessons_dir = Path(tmp)
            lesson_dir = lessons_dir / "primary-weekend-market"
            lesson_dir.mkdir()

            (lesson_dir / "lesson.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "id": "primary-weekend-market",
                        "stage": "primary",
                        "title": "A Weekend Market",
                        "subtitle": "小学示范课",
                        "summary": "用周末买菜场景练习小学词汇。",
                        "displayOrder": 30,
                        "audioMode": "generated-per-sentence",
                        "videoMode": "generated-slide-video",
                        "source": {"type": "csv-import", "file": "sentences.csv"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (lesson_dir / "sentences.csv").write_text(
                "id,en,zh,start,end\n"
                "s1,We buy apples with grandma.,我们和奶奶一起买苹果。,0,3.2\n"
                "s2,The market is busy but very clean.,市场很热闹，但很干净。,3.2,6.8\n",
                encoding="utf-8",
            )

            with mock.patch.object(import_lessons, "LESSONS_DIR", lessons_dir):
                loaded = import_lessons.load_lesson_sources()

            self.assertEqual(len(loaded), 1)
            _, lesson = loaded[0]
            self.assertEqual(lesson["source"]["type"], "csv-import")
            self.assertEqual(len(lesson["sentences"]), 2)
            self.assertEqual(lesson["sentences"][0]["en"], "We buy apples with grandma.")
            self.assertEqual(lesson["sentences"][0]["zh"], "我们和奶奶一起买苹果。")
            self.assertEqual(lesson["sentences"][0]["start"], 0.0)
            self.assertEqual(lesson["sentences"][1]["end"], 6.8)

    def test_load_lesson_sources_rejects_csv_import_without_required_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lessons_dir = Path(tmp)
            lesson_dir = lessons_dir / "primary-broken-market"
            lesson_dir.mkdir()

            (lesson_dir / "lesson.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "id": "primary-broken-market",
                        "stage": "primary",
                        "title": "Broken Market Lesson",
                        "subtitle": "小学示范课",
                        "summary": "故意缺少列的坏数据。",
                        "displayOrder": 40,
                        "audioMode": "generated-per-sentence",
                        "videoMode": "generated-slide-video",
                        "source": {"type": "csv-import", "file": "sentences.csv"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (lesson_dir / "sentences.csv").write_text(
                "id,en\ns1,We buy apples with grandma.\n",
                encoding="utf-8",
            )

            with mock.patch.object(import_lessons, "LESSONS_DIR", lessons_dir):
                with self.assertRaisesRegex(ValueError, "missing required columns"):
                    import_lessons.load_lesson_sources()


class SrtImportLessonSourceTests(unittest.TestCase):
    def test_load_lesson_sources_expands_srt_import_into_sentences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lessons_dir = Path(tmp)
            lesson_dir = lessons_dir / "cet4-campus-podcast"
            lesson_dir.mkdir()

            (lesson_dir / "lesson.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "id": "cet4-campus-podcast",
                        "stage": "cet4",
                        "title": "A Campus Podcast",
                        "subtitle": "四级示范课",
                        "summary": "使用双语字幕导入一节四级阶段听说练习。",
                        "displayOrder": 10,
                        "audioMode": "generated-per-sentence",
                        "videoMode": "generated-slide-video",
                        "source": {
                            "type": "srt-import",
                            "enFile": "subtitles.en.srt",
                            "zhFile": "subtitles.zh.srt",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (lesson_dir / "subtitles.en.srt").write_text(
                "1\n"
                "00:00:00,000 --> 00:00:03,200\n"
                "Welcome back to our campus podcast.\n\n"
                "2\n"
                "00:00:03,200 --> 00:00:06,700\n"
                "Today we are talking about study habits and time planning.\n",
                encoding="utf-8",
            )
            (lesson_dir / "subtitles.zh.srt").write_text(
                "1\n"
                "00:00:00,000 --> 00:00:03,200\n"
                "欢迎回到我们的校园播客。\n\n"
                "2\n"
                "00:00:03,200 --> 00:00:06,700\n"
                "今天我们来聊学习习惯和时间规划。\n",
                encoding="utf-8",
            )

            with mock.patch.object(import_lessons, "LESSONS_DIR", lessons_dir):
                loaded = import_lessons.load_lesson_sources()

            self.assertEqual(len(loaded), 1)
            _, lesson = loaded[0]
            self.assertEqual(lesson["source"]["type"], "srt-import")
            self.assertEqual(len(lesson["sentences"]), 2)
            self.assertEqual(lesson["sentences"][0]["id"], "s1")
            self.assertEqual(lesson["sentences"][0]["en"], "Welcome back to our campus podcast.")
            self.assertEqual(lesson["sentences"][0]["zh"], "欢迎回到我们的校园播客。")
            self.assertEqual(lesson["sentences"][0]["start"], 0.0)
            self.assertEqual(lesson["sentences"][1]["end"], 6.7)

    def test_load_lesson_sources_rejects_srt_import_with_mismatched_cues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lessons_dir = Path(tmp)
            lesson_dir = lessons_dir / "cet4-broken-podcast"
            lesson_dir.mkdir()

            (lesson_dir / "lesson.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "id": "cet4-broken-podcast",
                        "stage": "cet4",
                        "title": "Broken Podcast Lesson",
                        "subtitle": "四级示范课",
                        "summary": "故意制造中英字幕条数不一致。",
                        "displayOrder": 20,
                        "audioMode": "generated-per-sentence",
                        "videoMode": "generated-slide-video",
                        "source": {
                            "type": "srt-import",
                            "enFile": "subtitles.en.srt",
                            "zhFile": "subtitles.zh.srt",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (lesson_dir / "subtitles.en.srt").write_text(
                "1\n"
                "00:00:00,000 --> 00:00:03,000\n"
                "Welcome back to our campus podcast.\n\n"
                "2\n"
                "00:00:03,000 --> 00:00:06,000\n"
                "Today we are talking about study habits.\n",
                encoding="utf-8",
            )
            (lesson_dir / "subtitles.zh.srt").write_text(
                "1\n"
                "00:00:00,000 --> 00:00:03,000\n"
                "欢迎回到我们的校园播客。\n",
                encoding="utf-8",
            )

            with mock.patch.object(import_lessons, "LESSONS_DIR", lessons_dir):
                with self.assertRaisesRegex(ValueError, "must contain the same number of cues"):
                    import_lessons.load_lesson_sources()


if __name__ == "__main__":
    unittest.main()
