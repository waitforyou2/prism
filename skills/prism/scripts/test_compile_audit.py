import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_DIR = Path(__file__).resolve().parent


class CompileAuditTests(unittest.TestCase):
    def test_flags_uncited_compiled_raw_and_high_value_missing_from_overview(self):
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "topic" / "wiki"
            raw_dir = wiki_dir / "raw"
            pages_dir = wiki_dir / "pages"
            (pages_dir / "overview").mkdir(parents=True)
            (pages_dir / "entities").mkdir(parents=True)
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "_index.json").write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": "raw/20260510/topic/high-value.md",
                                "title": "High Value",
                                "importance": "high",
                                "relevance": 95,
                                "compiled": True,
                            },
                            {
                                "path": "raw/20260510/topic/cited.md",
                                "title": "Cited",
                                "importance": "medium",
                                "relevance": 75,
                                "compiled": True,
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (pages_dir / "overview" / "topic.md").write_text(
                "---\ntype: overview\ntitle: Topic\n---\n\n# Topic\n\nNo source yet.",
                encoding="utf-8",
            )
            (pages_dir / "entities" / "tool.md").write_text(
                "---\ntype: entity\ntitle: Tool\n---\n\n# Tool\n\n来源 [[raw/20260510/topic/cited.md]]",
                encoding="utf-8",
            )

            output = subprocess.check_output(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "compile_audit.py"),
                    "--wiki-dir",
                    str(wiki_dir),
                    "--json",
                ],
                text=True,
            )

            report = json.loads(output)
            self.assertEqual(report["status"], "fail")
            self.assertIn("raw/20260510/topic/high-value.md", report["uncited_compiled_raw"])
            self.assertIn("raw/20260510/topic/high-value.md", report["high_value_missing_from_overview"])
            self.assertNotIn("raw/20260510/topic/cited.md", report["uncited_compiled_raw"])

    def test_passes_when_compiled_raw_is_cited_and_high_value_is_in_overview(self):
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "topic" / "wiki"
            raw_dir = wiki_dir / "raw"
            overview_dir = wiki_dir / "pages" / "overview"
            overview_dir.mkdir(parents=True)
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "_index.json").write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": "raw/20260510/topic/high-value.md",
                                "title": "High Value",
                                "importance": "urgent",
                                "relevance": 98,
                                "compiled": True,
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (overview_dir / "topic.md").write_text(
                "---\ntype: overview\ntitle: Topic\n---\n\n# Topic\n\n覆盖 [[raw/20260510/topic/high-value.md]]",
                encoding="utf-8",
            )

            output = subprocess.check_output(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "compile_audit.py"),
                    "--wiki-dir",
                    str(wiki_dir),
                    "--json",
                ],
                text=True,
            )

            report = json.loads(output)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["uncited_compiled_raw"], [])
            self.assertEqual(report["high_value_missing_from_overview"], [])


if __name__ == "__main__":
    unittest.main()
