"""A forged successful summary and escaped files cannot establish evidence."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("check_archive", Path(__file__).with_name("check_archive.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvidenceTests(unittest.TestCase):
    def test_actual_junit_and_log_hashes_are_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            xml = b'<testsuites><testsuite tests="2" failures="0" errors="0" skipped="1"/></testsuites>'
            log = b"fixture-only retained log"
            (root / "result.xml").write_bytes(xml)
            (root / "result.log").write_bytes(log)
            row = {"status": "passed", "pytest_exit_code": 0, "junit": "result.xml", "log": "result.log", "junit_sha256": hashlib.sha256(xml).hexdigest(), "log_sha256": hashlib.sha256(log).hexdigest(), "counts": {"tests": 2, "failures": 0, "errors": 0, "skipped": 1}}
            path = root / "summary.json"
            path.write_text(json.dumps({"cases": [row]}), encoding="utf-8")
            result = module.verify_run_summary(path)
            self.assertEqual(result["junit_entries"]["tests"], 2)
            self.assertIsNone(result["source_revision"])
            (root / "result.xml").write_bytes(xml.replace(b'failures="0"', b'failures="1"'))
            with self.assertRaises(module.InvalidArchive):
                module.verify_run_summary(path)

    def test_external_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "run"
            nested.mkdir()
            (root / "outside.xml").write_text("outside", encoding="utf-8")
            path = nested / "summary.json"
            path.write_text(json.dumps({"cases": [{"status": "passed", "pytest_exit_code": 0, "junit": "../outside.xml"}]}), encoding="utf-8")
            with self.assertRaises(module.InvalidArchive):
                module.verify_run_summary(path)


if __name__ == "__main__":
    unittest.main()
