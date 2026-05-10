import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_DIR = Path(__file__).resolve().parent


class SaveToRawTests(unittest.TestCase):
    def test_saves_signal_index_for_snippet_items(self):
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "topic" / "wiki"
            input_file = Path(tmp) / "enriched.json"
            input_file.write_text(
                json.dumps(
                    [
                        {
                            "title": "Short Signal",
                            "url": "https://example.com/signal",
                            "source": "web",
                            "keyword": "topic",
                            "content": "short",
                            "fetchStatus": "snippet_only",
                            "wordCount": 1,
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            output = subprocess.check_output(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "save_to_raw.py"),
                    "--wiki-dir",
                    str(wiki_dir),
                    "--in",
                    str(input_file),
                ],
                text=True,
            )

            summary = json.loads(output)
            self.assertEqual(summary["saved_signals"], 1)
            signal_index = wiki_dir / "signals" / "_index.json"
            self.assertTrue(signal_index.exists())
            records = json.loads(signal_index.read_text(encoding="utf-8"))["files"]
            self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
