import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_DIR = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


normalize_raw = load_module("normalize_raw", SCRIPT_DIR / "normalize_raw.py")


class NormalizeRawTests(unittest.TestCase):
    def test_registers_manual_markdown_as_uncompiled_raw(self):
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "topic" / "wiki"
            raw_dir = wiki_dir / "raw"
            raw_dir.mkdir(parents=True)
            manual_file = raw_dir / "manual-note.md"
            manual_file.write_text("# Manual Note\n\nThis is hand uploaded content.", encoding="utf-8")

            summary = normalize_raw.normalize_raw(wiki_dir, keyword="topic")

            self.assertEqual(summary["registered"], 1)
            scan_output = subprocess.check_output(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "scan_raw.py"),
                    "--wiki-dir",
                    str(wiki_dir),
                    "--json",
                ],
                text=True,
            )
            pending = json.loads(scan_output)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["source"], "manual")
            self.assertFalse(pending[0]["compiled"])
            self.assertTrue((wiki_dir / pending[0]["path"]).exists())

    def test_preserves_existing_compiled_metadata(self):
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "topic" / "wiki"
            raw_dir = wiki_dir / "raw" / "20260510" / "manual"
            raw_dir.mkdir(parents=True)
            md_file = raw_dir / "already-compiled.md"
            md_file.write_text("# Already Compiled\n\nDo not reopen this.", encoding="utf-8")
            meta_file = raw_dir / "already-compiled.meta.json"
            meta_file.write_text(
                json.dumps(
                    {
                        "path": "raw/20260510/manual/already-compiled.md",
                        "title": "Already Compiled",
                        "source": "manual",
                        "keyword": "topic",
                        "compiled": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = normalize_raw.normalize_raw(wiki_dir, keyword="topic")

            self.assertEqual(summary["registered"], 0)
            metadata = json.loads(meta_file.read_text(encoding="utf-8"))
            self.assertTrue(metadata["compiled"])

    def test_scan_warns_about_orphan_markdown(self):
        with TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "topic" / "wiki"
            raw_dir = wiki_dir / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "orphan.md").write_text("# Orphan\n\nNo metadata yet.", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "scan_raw.py"),
                    "--wiki-dir",
                    str(wiki_dir),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual(json.loads(result.stdout), [])
            self.assertIn("orphan raw markdown", result.stderr)


if __name__ == "__main__":
    unittest.main()
