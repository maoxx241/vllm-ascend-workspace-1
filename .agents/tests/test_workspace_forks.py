"""Personal-fork policy and setup integration, with local Git and mocked GitHub."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import vaws_github as forks


def payload(full_name="alice/vllm-ascend-workspace", upstream=None):
    upstream = upstream or forks.REPOSITORIES["workspace"]["upstream"]
    return {"full_name": full_name, "owner": {"login": full_name.split("/")[0], "type": "User"},
            "fork": True, "parent": {"full_name": upstream}, "source": {"full_name": upstream}}


class FakeGitHub:
    def __init__(self, *, exists=True):
        self.calls = []
        self.repos = {}
        if exists:
            for spec in forks.REPOSITORIES.values():
                name = f"alice/{spec['upstream'].split('/')[-1]}"
                self.repos[name] = payload(name, spec["upstream"])

    def api(self, endpoint, method="GET", fields=None):
        self.calls.append((endpoint, method, fields))
        if endpoint == "user":
            return {"login": "alice", "id": 42, "type": "User"}
        if method == "POST" and endpoint.endswith("/forks"):
            upstream = endpoint[len("repos/"):-len("/forks")]
            full_name = f"alice/{upstream.split('/')[-1]}"
            self.repos[full_name] = payload(full_name, upstream)
            return copy.deepcopy(self.repos[full_name])
        name = endpoint.removeprefix("repos/")
        if name not in self.repos:
            raise forks.GitHubAPIError("Not Found", 404)
        return copy.deepcopy(self.repos[name])


class ForkValidationTests(unittest.TestCase):
    def setUp(self):
        environment = mock.patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""})
        environment.start()
        self.addCleanup(environment.stop)

    def test_user_identity_requires_explicit_same_personal_login(self):
        self.assertEqual(forks.validate_github_user({"login": "Alice", "id": 42, "type": "User"}, "alice"), "Alice")
        for account, login in (({"login": "alice", "id": 42, "type": "Organization"}, "alice"),
                               ({"login": "alice", "id": 42, "type": "User"}, "bob"),
                               ({"login": "alice", "id": 42, "type": "Bot"}, "alice"),
                               ({"login": "alice", "type": "User"}, "alice")):
            with self.subTest(account=account), self.assertRaises(forks.ForkPolicyError):
                forks.validate_github_user(account, login)

    def test_rejects_redirects_organizations_independent_and_wrong_network(self):
        upstream = forks.REPOSITORIES["workspace"]["upstream"]
        examples = [
            {"full_name": upstream}, {"full_name": "another/vllm-ascend-workspace"},
            {"owner": {"login": "alice", "type": "Organization"}}, {"fork": False},
            {"parent": {"full_name": "unrelated/project"}, "source": {"full_name": "unrelated/project"}},
            {"owner": {"login": "someone-else", "type": "User"}},
        ]
        for changed in examples:
            with self.subTest(changed=changed), self.assertRaises(forks.ForkPolicyError):
                forks.validate_personal_fork({**payload(), **changed}, "alice", upstream)

    def test_allows_personal_fork_of_fork_in_official_network(self):
        data = payload()
        data["parent"]["full_name"] = "another-user/vllm-ascend-workspace"
        self.assertIs(forks.validate_personal_fork(data, "alice", data["source"]["full_name"]), data)

    def test_api_auth_failure_is_not_a_missing_fork(self):
        proc = mock.Mock(returncode=1, stderr="gh: Bad credentials (HTTP 401)", stdout="")
        with mock.patch.object(forks.subprocess, "run", return_value=proc):
            with self.assertRaises(forks.GitHubAPIError) as raised:
                forks.GitHubClient().api("repos/alice/test")
        self.assertEqual(raised.exception.status, 401)
        self.assertEqual(raised.exception.evidence["returncode"], 1)

    def test_api_machine_output_overrides_terminal_color_without_changing_parent(self):
        original = {"CLICOLOR_FORCE": "1", "FORCE_COLOR": "1", "GH_FORCE_TTY": "80"}
        result = mock.Mock(returncode=0, stdout='{"ok": true}', stderr="")
        with mock.patch.dict(os.environ, original), mock.patch.object(forks.subprocess, "run", return_value=result) as run:
            self.assertEqual(forks.GitHubClient().api("user"), {"ok": True})
            env = run.call_args.kwargs["env"]
            self.assertEqual((env["CLICOLOR_FORCE"], env["FORCE_COLOR"], env["NO_COLOR"]), ("0", "0", "1"))
            self.assertNotIn("GH_FORCE_TTY", env)
            self.assertEqual(env["GITHUB_TOKEN"], "")
            self.assertEqual(os.environ["CLICOLOR_FORCE"], "1")
            self.assertEqual(os.environ["GH_FORCE_TTY"], "80")
            run.assert_called_once()

    def test_invalid_json_keeps_redacted_raw_api_evidence_in_update_log(self):
        from vaws_workspace_update import WorkspaceUpdater

        token = "gh" + "p_" + "fixturecredential"
        header = "> Authorization: " + "Bearer " + "private-fixture"
        url = "https://" + "user:secret" + "@example.invalid/"
        stderr = "\n".join((header, token, url, ""))
        proc = mock.Mock(returncode=0, stdout="\x1b[32m{not-json}\x1b[0m", stderr=stderr)
        with mock.patch.object(forks.subprocess, "run", return_value=proc) as run:
            with self.assertRaises(forks.GitHubAPIError) as raised:
                forks.GitHubClient().api("repos/alice/test")
        facts = raised.exception.evidence
        self.assertEqual(facts["endpoint"], "repos/alice/test")
        self.assertEqual(facts["method"], "GET")
        self.assertEqual(facts["command"], ["gh", "api", "--hostname", "github.com", "repos/alice/test", "--method", "GET"])
        self.assertEqual(facts["stdout"], proc.stdout)
        self.assertEqual(facts["returncode"], 0)
        self.assertNotIn(token, facts["stderr"])
        self.assertNotIn("private-fixture", facts["stderr"])
        self.assertNotIn("user:secret", facts["stderr"])
        run.assert_called_once()
        with tempfile.TemporaryDirectory() as directory:
            result = WorkspaceUpdater(Path(directory)).failure(raised.exception)
            self.assertEqual(json.loads(Path(result["log"]).read_text()), facts)

    def test_api_timeout_keeps_captured_bytes_without_retry(self):
        timeout = forks.subprocess.TimeoutExpired(["gh"], 60, output=b"partial response", stderr=b"timeout detail")
        with mock.patch.object(forks.subprocess, "run", side_effect=timeout) as run:
            with self.assertRaises(forks.GitHubAPIError) as raised:
                forks.GitHubClient().api("user")
        self.assertEqual(raised.exception.evidence["stdout"], "partial response")
        self.assertEqual(raised.exception.evidence["stderr"], "timeout detail")
        self.assertIsNone(raised.exception.evidence["returncode"])
        run.assert_called_once()

    def test_api_non_object_keeps_original_response(self):
        with mock.patch.object(forks.subprocess, "run", return_value=mock.Mock(returncode=0, stdout="[]", stderr="")):
            with self.assertRaises(forks.GitHubAPIError) as raised:
                forks.GitHubClient().api("user")
        self.assertEqual(raised.exception.evidence["stdout"], "[]")


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                                                "GIT_TERMINAL_PROMPT": "0"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root = Path(self.tmp.name) / "工作区 with spaces"
        self.init(self.root)
        self.client = FakeGitHub()
        self.upstream = forks.REPOSITORIES["workspace"]["upstream"]

    def init(self, root):
        root.mkdir()
        forks.git(root, "init", "-b", "main")
        forks.git(root, "config", "user.name", "Fork Fixture")
        forks.git(root, "config", "user.email", "fixture@example.invalid")
        forks.git(root, "-c", f"core.hooksPath={os.devnull}", "commit", "--allow-empty", "-m", "fixture")

    def setup_forks(self, user="alice", apply=False, **kwargs):
        return forks.setup(self.root, user, roles=["workspace"], client=self.client, apply=apply, **kwargs)

    def test_first_setup_needs_user_without_mutation(self):
        before = forks.git(self.root, "config", "--local", "--list").stdout
        result = self.setup_forks(user=None, apply=True)
        self.assertEqual(result["status"], "needs_github_user")
        self.assertEqual(result["authenticated_login"], "alice")
        self.assertFalse((self.root / ".vaws-local").exists())
        self.assertEqual(self.client.calls, [("user", "GET", None)])
        self.assertEqual(forks.git(self.root, "config", "--local", "--list").stdout, before)

    def test_plan_does_not_create_state_forks_or_change_remotes(self):
        self.client = FakeGitHub(exists=False)
        result = self.setup_forks()
        self.assertEqual(result["status"], "planned")
        self.assertTrue(result["repositories"][0]["create_fork"])
        self.assertFalse((self.root / ".vaws-local").exists())
        self.assertFalse(forks.git(self.root, "remote").stdout.strip())
        self.assertFalse(any(method == "POST" for _, method, _ in self.client.calls))

    def test_apply_creates_only_personal_fork_and_preserves_dirty_head_extra_remote(self):
        self.client = FakeGitHub(exists=False)
        forks.git(self.root, "remote", "add", "origin", f"git@github.com:{self.upstream}.git")
        forks.git(self.root, "remote", "add", "upstream2", "https://example.invalid/mirror.git")
        head = forks.git(self.root, "rev-parse", "HEAD").stdout
        (self.root / "unfinished.txt").write_text("keep this", encoding="utf-8")
        result = self.setup_forks(apply=True)
        self.assertEqual(result["status"], "configured")
        self.assertEqual(forks.git(self.root, "remote", "get-url", "origin").stdout.strip(),
                         "git@github.com:alice/vllm-ascend-workspace.git")
        self.assertEqual(forks.git(self.root, "remote", "get-url", "upstream2").stdout.strip(),
                         "https://example.invalid/mirror.git")
        self.assertEqual(forks.git(self.root, "rev-parse", "HEAD").stdout, head)
        self.assertEqual((self.root / "unfinished.txt").read_text(), "keep this")
        identity = forks.load_github_identity(self.root)
        self.assertEqual(identity, {"schema": "vaws.github.v1", "login": "alice", "github_user_id": 42,
                                    "forks": {"workspace": "alice/vllm-ascend-workspace"}})
        self.assertEqual([fields for _, method, fields in self.client.calls if method == "POST"], [{}])
        self.assertTrue(Path(result["repositories"][0]["backup"]).is_file())
        self.client.calls.clear()
        second = self.setup_forks(user=None, apply=True)
        self.assertIsNone(second["repositories"][0]["backup"])
        self.assertFalse(any(method == "POST" for _, method, _ in self.client.calls))
        self.assertGreaterEqual(len(self.client.calls), 3)  # Auth and fork are revalidated for writes.

    def test_saved_stable_user_id_accepts_rename_and_rejects_reassigned_login(self):
        forks.atomic_json(self.root / ".vaws-local/github.json",
                          {"schema": "vaws.github.v1", "login": "former-alice", "github_user_id": 42})
        result = self.setup_forks(user=None, apply=True)
        self.assertEqual(result["github_user"], "alice")
        self.assertEqual(forks.load_github_identity(self.root)["login"], "alice")
        forks.atomic_json(self.root / ".vaws-local/github.json",
                          {"schema": "vaws.github.v1", "login": "alice", "github_user_id": 99})
        with self.assertRaisesRegex(forks.ForkPolicyError, "user ID differs"):
            self.setup_forks(user=None, apply=True)

    def test_existing_invalid_repo_blocks_before_any_local_or_remote_mutation(self):
        self.client.repos["alice/vllm-ascend-workspace"]["fork"] = False
        with self.assertRaises(forks.ForkPolicyError):
            self.setup_forks(apply=True)
        self.assertFalse((self.root / ".vaws-local").exists())
        self.assertFalse(forks.git(self.root, "remote").stdout.strip())

    def test_transferred_name_plan_marks_redirect_as_missing_personal_fork(self):
        self.client.repos["alice/vllm-ascend-workspace"] = {
            "full_name": self.upstream, "owner": {"login": self.upstream.split("/")[0], "type": "Organization"},
            "fork": False}
        result = self.setup_forks()
        item = result["repositories"][0]
        self.assertTrue(item["legacy_redirect"])
        self.assertEqual(item["resolved_full_name"], self.upstream)
        self.assertTrue(item["create_fork"])
        self.assertFalse(item["personal_fork"])
        self.assertFalse(any(method == "POST" for _, method, _ in self.client.calls))
        self.assertFalse((self.root / ".vaws-local").exists())
        self.assertFalse(forks.git(self.root, "remote").stdout.strip())

    def test_apply_replaces_legacy_redirect_with_verified_personal_fork(self):
        self.client.repos["alice/vllm-ascend-workspace"] = {"full_name": self.upstream, "fork": False}
        result = self.setup_forks(apply=True)
        self.assertEqual(result["status"], "configured")
        self.assertTrue(result["repositories"][0]["personal_fork"])
        self.assertEqual(result["repositories"][0]["verified_full_name"], "alice/vllm-ascend-workspace")
        self.assertEqual([call for call in self.client.calls if call[1] == "POST"],
                         [(f"repos/{self.upstream}/forks", "POST", {})])
        actual = self.client.repos["alice/vllm-ascend-workspace"]
        self.assertIs(forks.validate_personal_fork(actual, "alice", self.upstream), actual)
        self.assertEqual(forks.parse_github_url(forks.git(self.root, "remote", "get-url", "origin").stdout.strip()),
                         "alice/vllm-ascend-workspace")

    def test_created_fork_waits_for_exact_redirect_to_disappear(self):
        redirect = {"full_name": self.upstream, "fork": False}
        self.client.repos["alice/vllm-ascend-workspace"] = redirect
        original = self.client.api
        pending = False
        def api(endpoint, method="GET", fields=None):
            nonlocal pending
            if method == "POST":
                result = original(endpoint, method, fields)
                pending = True
                return result
            if pending and endpoint == "repos/alice/vllm-ascend-workspace":
                pending = False
                return redirect
            return original(endpoint, method, fields)
        self.client.api = api
        # Keep subprocess retry sleeps real and outside the fork-poll assertion.
        with mock.patch.object(forks, "time", wraps=forks.time) as local_time:
            local_time.sleep = mock.Mock()
            self.assertEqual(self.setup_forks(apply=True)["status"], "configured")
        local_time.sleep.assert_called_once_with(2)

    def test_github_assigned_fork_name_is_saved_and_reused(self):
        self.client.repos["alice/vllm-ascend-workspace"] = {"full_name": self.upstream, "fork": False}
        actual = "alice/vllm-ascend-workspace-1"
        original = self.client.api
        def api(endpoint, method="GET", fields=None):
            if method == "POST":
                self.client.calls.append((endpoint, method, fields))
                self.client.repos[actual] = payload(actual)
                return self.client.repos[actual]
            return original(endpoint, method, fields)
        self.client.api = api
        result = self.setup_forks(apply=True)
        self.assertEqual(result["repositories"][0]["personal"], actual)
        self.assertEqual(forks.load_github_identity(self.root)["forks"]["workspace"], actual)
        self.assertIn(actual, forks.git(self.root, "remote", "get-url", "origin").stdout)
        self.client.calls.clear()
        self.setup_forks(user=None, apply=True)
        self.assertFalse(any(method == "POST" for _, method, _ in self.client.calls))

    def test_persistent_redirect_is_not_accepted_as_created_fork(self):
        self.client.repos["alice/vllm-ascend-workspace"] = {"full_name": self.upstream, "fork": False}
        original = self.client.api
        def api(endpoint, method="GET", fields=None):
            if method == "POST":
                return {"full_name": self.upstream}
            return original(endpoint, method, fields)
        self.client.api = api
        with mock.patch.object(forks, "time", wraps=forks.time) as local_time, self.assertRaises(forks.ForkPolicyError):
            local_time.sleep = mock.Mock()
            self.setup_forks(apply=True)
        self.assertFalse(forks.git(self.root, "remote").stdout.strip())

    def test_other_redirects_remain_blocked_without_creating_repository(self):
        for name in ("another/workspace", "vllm-project/vllm"):
            with self.subTest(name=name):
                self.client.calls.clear()
                self.client.repos["alice/vllm-ascend-workspace"] = {"full_name": name, "fork": True}
                with self.assertRaises(forks.ForkPolicyError):
                    self.setup_forks(apply=True)
                self.assertFalse(any(method == "POST" for _, method, _ in self.client.calls))
                self.assertFalse((self.root / ".vaws-local").exists())

    def test_http_403_never_becomes_create_fork(self):
        original = self.client.api
        def api(endpoint, method="GET", fields=None):
            if endpoint.startswith("repos/"):
                raise forks.GitHubAPIError("Forbidden", 403)
            return original(endpoint, method, fields)
        self.client.api = api
        with self.assertRaises(forks.GitHubAPIError):
            self.setup_forks(apply=True)
        self.assertFalse((self.root / ".vaws-local").exists())

    def test_multiple_fetch_or_conflicting_push_urls_require_explicit_replacement(self):
        for kind in ("url", "pushurl"):
            with self.subTest(kind=kind):
                forks.replace_values(self.root, "remote.origin.url", [f"https://github.com/{self.upstream}.git"])
                forks.replace_values(self.root, "remote.origin.pushurl", [])
                forks.git(self.root, "config", "--local", "--add", f"remote.origin.{kind}",
                          "git@github.com:some-organization/vllm-ascend-workspace.git")
                before = forks.git(self.root, "config", "--local", "--list").stdout
                with self.assertRaises(forks.ForkPolicyError):
                    self.setup_forks(apply=True)
                self.assertEqual(forks.git(self.root, "config", "--local", "--list").stdout, before)
                result = self.setup_forks(apply=True, replace_primary_remotes=True)
                self.assertTrue(Path(result["repositories"][0]["backup"]).exists())
                for push in (False, True):
                    values = forks.git(self.root, "remote", "get-url", "--all", *(["--push"] if push else []), "origin").stdout.splitlines()
                    self.assertEqual(len(values), 1)
                    self.assertEqual(forks.parse_github_url(values[0]), "alice/vllm-ascend-workspace")

    def test_correct_explicit_protocol_split_is_preserved(self):
        forks.git(self.root, "remote", "add", "origin", "git@github.com:alice/vllm-ascend-workspace.git")
        forks.git(self.root, "config", "remote.origin.pushurl", "https://github.com/alice/vllm-ascend-workspace")
        self.setup_forks(apply=True)
        self.assertEqual(forks.config_values(self.root, "remote.origin.pushurl"),
                         ["https://github.com/alice/vllm-ascend-workspace"])

    def test_https_credentials_are_never_echoed_or_saved_in_a_backup(self):
        secret = "never-copy-this-fixture"
        forks.git(self.root, "remote", "add", "origin", f"https://alice:{secret}@github.com/{self.upstream}.git")
        for replace in (False, True):
            with self.subTest(replace=replace), self.assertRaisesRegex(forks.ForkPolicyError, "embedded credentials") as caught:
                self.setup_forks(apply=True, replace_primary_remotes=replace)
            self.assertNotIn(secret, str(caught.exception))
            self.assertFalse((self.root / ".vaws-local").exists())

    def test_url_rewrite_to_unverified_owner_is_rejected_before_changes(self):
        forks.git(self.root, "config", "url.https://github.com/other/.insteadOf", "https://github.com/alice/")
        with self.assertRaisesRegex(forks.ForkPolicyError, "URL rewriting"):
            self.setup_forks(apply=True)
        self.assertFalse((self.root / ".vaws-local").exists())

    def test_empty_source_directory_cannot_be_treated_as_workspace(self):
        (self.root / "vllm").mkdir()
        with self.assertRaises(forks.ForkPolicyError):
            forks.setup(self.root / "vllm", "alice", roles=["workspace"], apply=True, client=self.client)
        self.assertFalse(forks.git(self.root, "remote").stdout.strip())

    def source_inputs(self):
        from vaws_source_lock import write_source_lock
        donors, revisions = {}, {}
        for role in ("vllm", "vllm-ascend"):
            source = Path(self.tmp.name) / (role + "-upstream")
            self.init(source)
            (source / "README").write_text(role + " original code\n", encoding="utf-8")
            forks.git(source, "add", "README")
            forks.git(source, "-c", f"core.hooksPath={os.devnull}", "commit", "-m", "source")
            donors[role] = source
            revisions[role] = forks.git(source, "rev-parse", "HEAD").stdout.strip()
        value = {"schema_version": 1,
                 "vllm-ascend": {"repository": "vllm-project/vllm-ascend", "revision": revisions["vllm-ascend"]},
                 "vllm": {"repository": "vllm-project/vllm", "development": {"revision": revisions["vllm"]},
                          "release": {"tag": "v0.28.0", "revision": revisions["vllm"]}}}
        write_source_lock(self.root, value)
        return donors, revisions, value

    def local_source_preparer(self, donors):
        def prepare(destination, *, repository, revision):
            role = repository.removeprefix("vllm-project/")
            self.assertEqual(repository, forks.REPOSITORIES[role]["upstream"])
            forks.git(self.root, "clone", "--no-local", "--no-checkout", "--", str(donors[role]), str(destination))
            forks.git(destination, "checkout", "--detach", revision)
            forks.git(destination, "remote", "set-url", "origin", f"https://github.com/{repository}.git")
        return prepare

    def test_first_setup_initializes_independent_sources_at_exact_locked_revisions(self):
        import vaws_native_workspace as native
        donors, revisions, _ = self.source_inputs()
        with mock.patch.object(native, "prepare_source", side_effect=self.local_source_preparer(donors), create=True) as prepare:
            result = forks.setup(self.root, "alice", roles=["vllm", "vllm-ascend"], apply=True, client=self.client)
        self.assertEqual(result["status"], "configured")
        self.assertEqual(prepare.call_count, 2)
        for role in ("vllm", "vllm-ascend"):
            path = self.root / role
            self.assertTrue((path / ".git").is_dir())
            self.assertFalse((path / ".git/objects/info/alternates").exists())
            self.assertEqual(forks.git(path, "rev-parse", "HEAD").stdout.strip(), revisions[role])
            self.assertEqual((path / "README").read_text(encoding="utf-8"), role + " original code\n")
            self.assertEqual(forks.parse_github_url(forks.git(path, "remote", "get-url", "origin").stdout.strip()),
                             "alice/" + role)
            self.assertFalse(forks.git(self.root, "ls-files", "--", role).stdout.strip())
        self.assertFalse((self.root / ".gitmodules").exists())
        self.assertFalse(forks.git(self.root, "remote").stdout.strip())

    def test_first_setup_can_publish_into_an_existing_empty_source_directory(self):
        import vaws_native_workspace as native
        donors, revisions, _ = self.source_inputs()
        (self.root / "vllm").mkdir()
        with mock.patch.object(native, "prepare_source", side_effect=self.local_source_preparer(donors), create=True):
            forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        self.assertEqual(forks.git(self.root / "vllm", "rev-parse", "HEAD").stdout.strip(), revisions["vllm"])
        self.assertFalse((self.root / "vllm-ascend").exists())

    def test_existing_source_preserves_unpushed_commit_staged_dirty_and_untracked_work(self):
        import vaws_native_workspace as native
        from vaws_source_lock import write_source_lock
        donors, _, value = self.source_inputs()
        with mock.patch.object(native, "prepare_source", side_effect=self.local_source_preparer(donors), create=True):
            forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        source = self.root / "vllm"
        forks.git(source, "config", "user.name", "Fixture")
        forks.git(source, "config", "user.email", "fixture@example.invalid")
        forks.git(source, "-c", f"core.hooksPath={os.devnull}", "commit", "--allow-empty", "-m", "unpushed work")
        (source / "README").write_text("staged work\n", encoding="utf-8")
        forks.git(source, "add", "README")
        (source / "README").write_text("unfinished work\n", encoding="utf-8")
        (source / "untracked.txt").write_text("keep me\n", encoding="utf-8")
        commands = [("rev-parse", "HEAD"), ("diff", "--cached"), ("diff",), ("status", "--porcelain")]
        before = [forks.git(source, *args).stdout for args in commands]
        value["vllm"]["development"]["revision"] = "e" * 40
        write_source_lock(self.root, value)
        with mock.patch.object(native, "prepare_source", create=True) as prepare:
            forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        prepare.assert_not_called()
        self.assertEqual([forks.git(source, *args).stdout for args in commands], before)
        self.assertEqual((source / "untracked.txt").read_text(encoding="utf-8"), "keep me\n")

    def test_source_lock_change_during_preparation_does_not_publish_the_old_clone(self):
        import vaws_native_workspace as native
        from vaws_source_lock import write_source_lock
        donors, revisions, value = self.source_inputs()
        prepare = self.local_source_preparer(donors)
        def change_lock(destination, **kwargs):
            prepare(destination, **kwargs)
            value["vllm"]["development"]["revision"] = "e" * 40
            write_source_lock(self.root, value)
        with mock.patch.object(native, "prepare_source", side_effect=change_lock, create=True):
            with self.assertRaisesRegex(forks.ForkPolicyError, "selection changed"):
                forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        self.assertFalse((self.root / "vllm").exists())
        private = list((self.root / ".vaws-local/source-initialization").iterdir())
        self.assertEqual(len(private), 1)
        self.assertEqual(forks.git(private[0], "rev-parse", "HEAD").stdout.strip(), revisions["vllm"])
        self.assertFalse(forks.git(self.root, "remote").stdout.strip())

    def test_nonempty_source_destination_is_rejected_before_fork_or_clone_changes(self):
        import vaws_native_workspace as native
        self.source_inputs()
        target = self.root / "vllm"
        target.mkdir()
        (target / "keep.txt").write_text("user content\n", encoding="utf-8")
        with mock.patch.object(native, "prepare_source", create=True) as prepare:
            with self.assertRaisesRegex(forks.ForkPolicyError, "not empty"):
                forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        prepare.assert_not_called()
        self.assertFalse((self.root / ".vaws-local").exists())
        self.assertEqual((target / "keep.txt").read_text(encoding="utf-8"), "user content\n")
        self.assertFalse(any(method == "POST" for _, method, _ in self.client.calls))

    def test_source_destination_changed_during_clone_is_not_replaced(self):
        import vaws_native_workspace as native
        donors, _, _ = self.source_inputs()
        prepare = self.local_source_preparer(donors)
        target = self.root / "vllm"
        def concurrent_content(destination, **kwargs):
            prepare(destination, **kwargs)
            target.mkdir()
            (target / "keep.txt").write_text("concurrent user content\n", encoding="utf-8")
        with mock.patch.object(native, "prepare_source", side_effect=concurrent_content, create=True):
            with self.assertRaisesRegex(forks.ForkPolicyError, "not empty"):
                forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        self.assertFalse((target / ".git").exists())
        self.assertEqual((target / "keep.txt").read_text(encoding="utf-8"), "concurrent user content\n")

    def test_old_gitmodules_source_entry_is_not_accepted_without_a_gitlink(self):
        import vaws_native_workspace as native
        donors, _, _ = self.source_inputs()
        modules = self.root / ".gitmodules"
        modules.write_text('[submodule "vllm"]\n\tpath = vllm\n\turl = https://github.com/vllm-project/vllm.git\n',
                           encoding="utf-8")
        with mock.patch.object(native, "prepare_source", side_effect=self.local_source_preparer(donors), create=True) as prepare:
            with self.assertRaises(forks.ForkPolicyError):
                forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        prepare.assert_not_called()
        self.assertFalse((self.root / ".vaws-local").exists())

    def test_workspace_gitlink_residue_is_rejected_for_an_initialized_source(self):
        import vaws_native_workspace as native
        donors, revisions, _ = self.source_inputs()
        prepare = self.local_source_preparer(donors)
        prepare(self.root / "vllm", repository="vllm-project/vllm", revision=revisions["vllm"])
        forks.git(self.root, "update-index", "--add", "--cacheinfo", f"160000,{revisions['vllm']},vllm")
        before = forks.git(self.root / "vllm", "config", "--local", "--list").stdout
        with mock.patch.object(native, "prepare_source", create=True) as prepare_mock:
            with self.assertRaises(forks.ForkPolicyError):
                forks.setup(self.root, "alice", roles=["vllm"], apply=True, client=self.client)
        prepare_mock.assert_not_called()
        self.assertEqual(forks.git(self.root / "vllm", "config", "--local", "--list").stdout, before)
        self.assertFalse((self.root / ".vaws-local").exists())


if __name__ == "__main__":
    unittest.main()
