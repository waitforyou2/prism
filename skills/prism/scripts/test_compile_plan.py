import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_DIR = Path(__file__).resolve().parent


class CompilePlanTests(unittest.TestCase):
    def test_writes_raw_coverage_checklist_and_extraction_table(self):
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "topic" / "wiki"
            raw_dir = wiki_dir / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "_index.json").write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": "raw/20260510/topic/high-value.md",
                                "title": "High Value",
                                "source": "web",
                                "keyword": "topic",
                                "importance": "high",
                                "relevance": 95,
                                "wordCount": 1200,
                                "compiled": False,
                            },
                            {
                                "path": "raw/20260510/topic/done.md",
                                "title": "Done",
                                "source": "web",
                                "keyword": "topic",
                                "importance": "medium",
                                "relevance": 75,
                                "wordCount": 800,
                                "compiled": True,
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            subprocess.check_call(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "compile_plan.py"),
                    "--wiki-dir",
                    str(wiki_dir),
                ]
            )

            plan_path = wiki_dir / "compile_plan.md"
            self.assertTrue(plan_path.exists())
            plan = plan_path.read_text(encoding="utf-8")
            self.assertIn("## Raw Coverage Checklist", plan)
            self.assertIn("- [ ] `raw/20260510/topic/high-value.md`", plan)
            self.assertNotIn("raw/20260510/topic/done.md", plan)
            self.assertIn("## Extraction Table", plan)
            self.assertIn("| Raw Source | Entity | Concept | Claim / Detail | Target Page | Status |", plan)


if __name__ == "__main__":
    unittest.main()
