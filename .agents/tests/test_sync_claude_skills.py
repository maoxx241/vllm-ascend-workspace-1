#!/usr/bin/env python3
"""Tests for generated Claude shims and canonical ModelScope metadata/help."""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".agents" / "scripts" / "sync_claude_skills.py"
CATALOG_SCRIPT = ROOT / ".agents" / "scripts" / "skill_catalog.py"
CANONICAL_MODELSCOPE = ROOT / ".agents" / "skills" / "modelscope"
MODELSCOPE_SCRIPTS = (
    "modelscope_auto.py",
    "download_from_modelscope.py",
    "modelscope_download_status.py",
    "verify_modelscope_sha256.py",
)
HELP_MARKERS = {
    "modelscope_auto.py": ("ensure", "status", "verify", "worker"),
    "download_from_modelscope.py": ("--model-id", "--local-dir", "--revision"),
    "modelscope_download_status.py": ("--model", "--revision"),
    "verify_modelscope_sha256.py": ("--model", "--output-dir"),
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sync = load_module(SCRIPT, "_sync_claude_skills_test")
catalog = load_module(CATALOG_SCRIPT, "_skill_catalog_for_sync_test")


def frontmatter_yaml(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening YAML frontmatter delimiter")
    try:
        end = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValueError("missing closing YAML frontmatter delimiter") from exc
    return "\n".join(lines[1:end]) + "\n"


def deny_network_pythonpath(root: Path) -> str:
    package = root / "requests"
    package.mkdir()
    (package / "__init__.py").write_text(
        "class Session:\n"
        "    def get(self, *args, **kwargs):\n"
        "        raise RuntimeError("
        "'network and ModelScope provider calls are denied in this fixture')\n",
        encoding="utf-8",
    )
    return str(root)


class ClaudeShimTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.agents_skills = self.root / "agents-skills"
        self.claude_skills = self.root / "claude-skills"
        self.canonical = self.agents_skills / "modelscope"
        self.agents_skills.mkdir()
        self.claude_skills.mkdir()
        self.canonical.mkdir()
        (self.canonical / "SKILL.md").write_text(
            "---\nname: modelscope\ndescription: ModelScope fixture\n---\n\n# ModelScope\n",
            encoding="utf-8",
        )
        sync.AGENTS_SKILLS = self.agents_skills
        sync.CLAUDE_SKILLS = self.claude_skills
        shim_dir = self.claude_skills / "modelscope"
        shim_dir.mkdir()
        (shim_dir / "SKILL.md").write_text(
            sync.expected_skill_body(self.canonical),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        sync.AGENTS_SKILLS = ROOT / ".agents" / "skills"
        sync.CLAUDE_SKILLS = ROOT / ".claude" / "skills"
        self._tmp.cleanup()

    def test_shim_cleanup_only_removes_unextended_generated_shims(self) -> None:
        for name in ("removed-skill", "extended-skill", "foreign-skill"):
            directory = self.claude_skills / name
            directory.mkdir()
            body = (
                f"<!-- Generated from .agents/skills/{name}/SKILL.md. Do not edit. -->\n"
                if name != "foreign-skill"
                else "# My personal skill\n"
            )
            (directory / "SKILL.md").write_text(body, encoding="utf-8")
        extra = self.claude_skills / "extended-skill" / "notes.txt"
        extra.write_text("user-owned notes\n", encoding="utf-8")

        sync.sync_shims()

        self.assertFalse((self.claude_skills / "removed-skill").exists())
        self.assertEqual(extra.read_text(encoding="utf-8"), "user-owned notes\n")
        self.assertEqual(
            (self.claude_skills / "foreign-skill" / "SKILL.md").read_text(encoding="utf-8"),
            "# My personal skill\n",
        )
        self.assertIn("extra Claude skill shim: foreign-skill", sync.check_shims())
        self.assertIn("extra Claude skill shim: extended-skill", sync.check_shims())


    def test_foreign_skill_at_canonical_name_is_preserved_and_reported(self) -> None:
        target = self.claude_skills / "modelscope" / "SKILL.md"
        target.write_text("# My personal ModelScope skill\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()) as error:
            self.assertEqual(sync.main([]), 1)
        self.assertIn("not a generated shim", error.getvalue())
        self.assertEqual(target.read_text(encoding="utf-8"), "# My personal ModelScope skill\n")

    def test_projection_rejects_linked_directories_without_writing_outside(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "SKILL.md"
        sentinel.write_text("outside content\n", encoding="utf-8")
        target = self.claude_skills / "modelscope"
        (target / "SKILL.md").unlink()
        target.rmdir()
        if os.name == "nt":
            proc = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(target), str(outside)],
                capture_output=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
        else:
            target.symlink_to(outside, target_is_directory=True)
        try:
            with self.assertRaisesRegex(sync.ProjectionConflict, "linked projection path"):
                sync.sync_shims()
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside content\n")
            self.assertEqual(list(outside.iterdir()), [sentinel])
        finally:
            if os.name == "nt":
                target.rmdir()
            else:
                target.unlink()


class CurrentTreeProjectionTests(unittest.TestCase):

    def test_check_passes_on_current_tree(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_all_claude_shims_expose_the_canonical_metadata(self) -> None:
        for source in sync.source_skill_dirs():
            target = ROOT / ".claude/skills" / source.name / "SKILL.md"
            with self.subTest(skill=source.name):
                expected = yaml.safe_load(frontmatter_yaml((source / "SKILL.md").read_text(encoding="utf-8")))
                actual = yaml.safe_load(frontmatter_yaml(target.read_text(encoding="utf-8")))
                self.assertEqual(actual, expected)

    def test_skill_frontmatter_parses_through_catalog(self) -> None:
        record = catalog.parse_skill(CANONICAL_MODELSCOPE / "SKILL.md", ROOT)
        self.assertEqual(record.name, "modelscope")
        self.assertIn("ModelScope", record.description)
        self.assertGreater(len(record.description), 20)

    def test_modelscope_yaml_documents_parse(self) -> None:
        skill_file = CANONICAL_MODELSCOPE / "SKILL.md"
        frontmatter = frontmatter_yaml(skill_file.read_text(encoding="utf-8"))
        metadata = yaml.safe_load(frontmatter)
        self.assertEqual(metadata["name"], "modelscope")
        self.assertIsInstance(metadata["description"], str)
        self.assertIn("ModelScope", metadata["description"])
        text = (CANONICAL_MODELSCOPE / "agents" / "openai.yaml").read_text(encoding="utf-8")
        document = yaml.safe_load(text)
        interface = document["interface"]
        self.assertIsInstance(interface, dict)
        self.assertEqual(interface["display_name"], "ModelScope")
        self.assertIn("ModelScope", interface["short_description"])
        self.assertIn("$modelscope", interface["default_prompt"])

    def test_generator_help_names_claude_output(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Claude Code skill shims", proc.stdout)
        self.assertIn(".claude/skills", proc.stdout)
        self.assertIn("--check", proc.stdout)


class ModelScopeHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.pythonpath = deny_network_pythonpath(Path(cls._tmpdir.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmpdir.cleanup()

    def _run_help(
        self, script: Path, *args: str
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            self.pythonpath if not existing else self.pythonpath + os.pathsep + existing
        )
        for name in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "MODELSCOPE_TOKEN",
            "MODELSCOPE_API_TOKEN",
        ):
            env.pop(name, None)
        return subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=20,
        )

    def test_canonical_help_without_network(self) -> None:
        for name in MODELSCOPE_SCRIPTS:
            with self.subTest(script=name):
                canonical = self._run_help(
                    CANONICAL_MODELSCOPE / "scripts" / name, "--help"
                )
                self.assertEqual(canonical.returncode, 0, canonical.stderr)
                self.assertIn("usage:", canonical.stdout)
                for marker in HELP_MARKERS[name]:
                    self.assertIn(marker, canonical.stdout)
                if name == "modelscope_auto.py":
                    for command in ("ensure", "status", "verify"):
                        canonical_sub = self._run_help(
                            CANONICAL_MODELSCOPE / "scripts" / name,
                            command,
                            "--help",
                        )
                        self.assertEqual(canonical_sub.returncode, 0, canonical_sub.stderr)
                        self.assertIn("--model", canonical_sub.stdout)


if __name__ == "__main__":
    unittest.main()
