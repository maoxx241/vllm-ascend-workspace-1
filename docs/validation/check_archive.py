"""Read-only engineering evidence integrity checks; no runtime/task gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path


class InvalidArchive(ValueError):
    pass


class Reader:
    def __init__(self, *, seconds: float = 10, total_bytes: int = 64 * 1024 * 1024):
        self.started = time.monotonic()
        self.seconds = seconds
        self.remaining = total_bytes

    def read(self, path: Path, *, limit: int = 8 * 1024 * 1024) -> bytes:
        if time.monotonic() - self.started > self.seconds:
            raise InvalidArchive("archive read time budget reached")
        with path.open("rb") as stream:
            data = stream.read(min(limit, self.remaining) + 1)
        if len(data) > limit or len(data) > self.remaining:
            raise InvalidArchive("archive read byte budget reached")
        self.remaining -= len(data)
        return data


def _contained(root: Path, value: str) -> Path:
    path = Path(value)
    path = path if path.is_absolute() else root / path
    if not path.resolve().is_relative_to(root.resolve()):
        raise InvalidArchive("archive reference escapes its declared root")
    return path


def check_index(root: Path, index: Path | None = None) -> dict:
    reader = Reader()
    raw = reader.read(index or root / "docs/validation/coverage.json", limit=1024 * 1024)
    value = json.loads(raw)
    if not re.fullmatch(r"[a-f0-9]{40}", value.get("workspace_audit_revision", "")):
        raise InvalidArchive("archive must identify its audited workspace revision")
    families, evidence, gaps = (value.get(name, []) for name in ("families", "evidence", "gaps"))
    if not 1 <= len(families) <= 128 or len(evidence) > 128 or len(gaps) > 128:
        raise InvalidArchive("archive item count outside budget")
    def ids(rows):
        values = [row["id"] for row in rows]
        if len(values) != len(set(values)):
            raise InvalidArchive("duplicate archive identity")
        return set(values)
    family_ids, evidence_ids, gap_ids = ids(families), ids(evidence), ids(gaps)
    for record in evidence:
        if not record.get("version") or not record.get("scope") or not record.get("limits"):
            raise InvalidArchive("evidence needs version/provenance, scope and limitations")
        link = record.get("record", "").split("#", 1)[0]
        if not link.startswith("https://github.com/") and not _contained(root, link).is_file():
            raise InvalidArchive(f"missing evidence document: {record['id']}")
    for family in families:
        if not family.get("entries") or not family.get("sources") or not family.get("tests") or not family.get("evidence") or not family.get("gaps"):
            raise InvalidArchive(f"incomplete capability mapping: {family['id']}")
        if any(item not in evidence_ids for item in family["evidence"]) or any(item not in gap_ids for item in family["gaps"]):
            raise InvalidArchive(f"unknown evidence/gap reference: {family['id']}")
        for key in ("sources", "tests"):
            for name in family[key]:
                if not _contained(root, name).exists():
                    raise InvalidArchive(f"missing {key} path in family: {family['id']}")
    skill_root = root / ".agents/skills"
    skills = set()
    for count, path in enumerate(skill_root.iterdir(), 1):
        if count > 128:
            raise InvalidArchive("skill inventory scan budget reached")
        if path.is_dir() and (path / "SKILL.md").is_file():
            skills.add(path.name)
    mapped = {row["id"] for row in families if row.get("owner") == "workspace-business-skill"}
    if skills != mapped:
        raise InvalidArchive(f"skill coverage differs: missing={sorted(skills - mapped)}, removed={sorted(mapped - skills)}")
    return {"status": "ok", "claim": "archive structure and local references only; runtime claims retain their evidence limits", "families": len(family_ids), "business_skills": len(skills), "evidence_records": len(evidence_ids), "open_gaps": sorted(gap_ids), "archive_sha256": hashlib.sha256(raw).hexdigest()}


def verify_run_summary(path: Path) -> dict:
    reader = Reader()
    raw = reader.read(path, limit=2 * 1024 * 1024)
    value = json.loads(raw)
    rows = value.get("cases")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
        raise InvalidArchive("run summary must contain 1..200 bounded cases")
    totals = dict.fromkeys(("tests", "failures", "errors", "skipped"), 0)
    for row in rows:
        if row.get("status") != "passed" or row.get("pytest_exit_code") != 0:
            raise InvalidArchive("run includes a non-passing or unfinished case")
        for kind in ("junit", "log"):
            artifact = _contained(path.parent, row[kind])
            data = reader.read(artifact)
            if hashlib.sha256(data).hexdigest() != row.get(kind + "_sha256"):
                raise InvalidArchive(f"run {kind} artifact hash mismatch")
            if kind == "junit":
                document = ET.fromstring(data)
                counts = dict.fromkeys(totals, 0)
                suites = [document] if document.tag == "testsuite" else list(document.iter("testsuite"))
                for suite in suites:
                    for key in counts:
                        counts[key] += int(suite.get(key, 0))
                if counts["tests"] <= 0 or counts["failures"] or counts["errors"] or counts != row.get("counts"):
                    raise InvalidArchive("JUnit contents disagree with the successful summary")
                for key in totals:
                    totals[key] += counts[key]
    return {"status": "verified", "claim": "existing result integrity; no tests were rerun", "cases": len(rows), "junit_entries": totals,
            "source_revision": value.get("source_revision"), "runtime_revisions": value.get("runtime_revisions"),
            "provenance_note": "Missing source/runtime revisions stay unknown; a file hash is not a code revision.",
            "summary_sha256": hashlib.sha256(raw).hexdigest()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-run-summary", type=Path)
    args = parser.parse_args(argv)
    try:
        result = check_index(Path(__file__).resolve().parents[2])
        if args.verify_run_summary:
            result["existing_run"] = verify_run_summary(args.verify_run_summary.resolve())
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (InvalidArchive, OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
