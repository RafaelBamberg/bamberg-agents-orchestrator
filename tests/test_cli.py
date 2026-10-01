import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import bamberg_cli as cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True)
        (self.repo / ".gitignore").write_text(".bamberg/\n")
        (self.repo / "README").write_text("base\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "initial"], check=True)

    def add_account(self, name, provider):
        from argparse import Namespace
        home = Path(self.temp.name) / name
        cli.account_add(self.repo, Namespace(id=name, provider=provider, home=str(home), label=name + "@example.com"))
        return home

    def registered_task(self, name="feature", status="completed"):
        cli.ensure_state_ignored(self.repo)
        worktree = self.repo / ".bamberg" / "worktrees" / name
        cli.git("worktree", "add", "-b", f"bamberg/{name}", str(worktree), "HEAD", cwd=self.repo)
        cli.save(cli.job_path(self.repo, name), {"name": name, "account": "test", "provider": "claude",
                                             "branch": f"bamberg/{name}", "worktree": str(worktree), "status": status})
        return worktree

    def clean_as_operator(self, name="feature"):
        with patch.object(cli.Path, "cwd", return_value=self.repo), patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdout, "isatty", return_value=True), patch.object(cli, "confirm_cleanup") as confirm:
            cli.cleanup(self.repo, name)
        confirm.assert_called_once()

    def test_accounts_reject_shared_profiles(self):
        self.add_account("alice", "claude")
        from argparse import Namespace
        with self.assertRaises(cli.Error):
            cli.account_add(self.repo, Namespace(id="bob", provider="codex", home=str(Path(self.temp.name) / "alice" / "nested"), label=None))

    def test_state_is_ignored_in_target_repository(self):
        subprocess.run(["git", "-C", str(self.repo), "rm", "-q", ".gitignore"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "remove ignore"], check=True)
        self.add_account("alice", "claude")
        self.assertEqual(cli.git("status", "--porcelain", cwd=self.repo), "")
        exclude = self.repo / ".git" / "info" / "exclude"
        self.assertIn(".bamberg/", exclude.read_text())

    def test_usage_per_account_and_reset_timezone(self):
        c_home = self.add_account("alice", "claude")
        o_home = self.add_account("bob", "codex")
        (c_home / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {"accessToken": "test-c"}}))
        (o_home / "auth.json").write_text(json.dumps({"tokens": {"access_token": "test-o", "account_id": "acct"}}))
        replies = [
            {"five_hour": {"utilization": 21, "resets_at": "2026-10-02T00:29:00Z"}, "seven_day": {"utilization": 9, "resets_at": "2026-10-06T09:59:00Z"}},
            {"rate_limit": {"primary_window": {"used_percent": 32, "limit_window_seconds": 18000, "reset_at": 1790900940}, "secondary_window": {"used_percent": 6, "limit_window_seconds": 604800, "reset_at": 1791280740}}},
        ]
        from argparse import Namespace
        out = io.StringIO()
        with patch.object(cli, "request_json", side_effect=replies) as mocked, contextlib.redirect_stdout(out):
            cli.usage(self.repo, Namespace(timezone="America/Sao_Paulo"))
        value = out.getvalue()
        self.assertIn("alice@example.com", value)
        self.assertIn("bob@example.com", value)
        self.assertIn("21% usado", value)
        self.assertIn("32% usado", value)
        self.assertIn("01/10 21:29", value)
        self.assertEqual(mocked.call_count, 2)

    def test_claude_list_format(self):
        five, week = cli.claude_windows([
            {"kind": "session", "percent": 21, "resets_at": "2026-10-02T00:29:00Z"},
            {"kind": "weekly_all", "percent": 9, "resets_at": "2026-10-06T09:59:00Z"},
        ])
        self.assertEqual(five[0], 21)
        self.assertEqual(week[0], 9)

    def test_worktree_branch_is_unique_and_base_untouched(self):
        home = self.add_account("alice", "claude")
        from argparse import Namespace
        args = Namespace(name="feature", account="alice", task="Edit README")
        with patch.object(cli.shutil, "which", return_value="/usr/bin/true"), patch.object(cli, "launch_worker") as popen:
            popen.return_value.pid = 12345
            cli.start(self.repo, args)
        item = cli.details(self.repo, "feature")
        self.assertEqual(item["branch"], "bamberg/feature")
        self.assertEqual(cli.git("branch", "--show-current", cwd=item["worktree"]), "bamberg/feature")
        self.assertEqual((self.repo / "README").read_text(), "base\n")
        with patch.object(cli.shutil, "which", return_value="/usr/bin/true"):
            with self.assertRaises(cli.Error):
                cli.start(self.repo, args)

    def test_worktree_creation_skips_host_checkout_hooks(self):
        self.add_account("alice", "claude")
        marker = Path(self.temp.name) / "unexpected-sibling"
        hook = self.repo / ".git" / "hooks" / "post-checkout"
        hook.write_text("#!/bin/sh\nmkdir " + str(marker) + "\n")
        hook.chmod(0o755)
        from argparse import Namespace
        with patch.object(cli.shutil, "which", return_value="/usr/bin/true"), patch.object(cli, "launch_worker") as launch:
            launch.return_value.pid = 12345
            cli.start(self.repo, Namespace(name="safe", account="alice", task="Edit README"))
        self.assertFalse(marker.exists())

    def test_state_directory_cannot_be_symlink(self):
        target = Path(self.temp.name) / "outside"
        target.mkdir()
        (self.repo / ".bamberg").symlink_to(target)
        with self.assertRaises(cli.Error):
            cli.state_dir(self.repo)

    def test_bwrap_blocks_cross_worktree_writes(self):
        first = self.repo / ".bamberg" / "worktrees" / "one"
        second = self.repo / ".bamberg" / "worktrees" / "two"
        profile = Path(self.temp.name) / "profile"
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        profile.mkdir()
        result = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--tmpfs", "/tmp",
                                 "--bind", str(first), str(first), "--bind", str(profile), str(profile),
                                 "--chdir", str(first), "--", "/bin/sh", "-c",
                                 "printf yes > own; printf profile > " + str(profile / "written") +
                                 "; printf no > ../two/foreign"], capture_output=True)
        self.assertNotIn(b"No such file", result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((first / "own").read_text(), "yes")
        self.assertEqual((profile / "written").read_text(), "profile")
        self.assertFalse((second / "foreign").exists())

    def test_worker_runs_agent_in_its_own_worktree(self):
        home = self.add_account("alice", "claude")
        fake = home / "claude"
        fake.write_text("#!/bin/sh\nprintf result > result.txt\nprintf bad > ../other/foreign\nexit 0\n")
        fake.chmod(0o755)
        other = self.repo / ".bamberg" / "worktrees" / "other"
        cli.git("worktree", "add", "-b", "bamberg/other", str(other), "HEAD", cwd=self.repo)
        from argparse import Namespace
        with patch.dict(os.environ, {"PATH": str(home) + os.pathsep + os.environ["PATH"]}), patch.object(cli, "launch_worker") as launch:
            launch.return_value.pid = os.getpid()
            cli.start(self.repo, Namespace(name="first", account="alice", task="Write result"))
            code = cli.worker(self.repo, "first")
        self.assertEqual(code, 0)
        self.assertEqual((self.repo / ".bamberg" / "worktrees" / "first" / "result.txt").read_text(), "result")
        self.assertFalse((other / "foreign").exists())
        self.assertEqual(cli.details(self.repo, "first")["status"], "completed")

    def test_cleanup_preserves_main_branch_and_task_branch(self):
        worktree = self.registered_task()
        (worktree / "README").write_text("task work\n")
        cli.git("add", "README", cwd=worktree)
        cli.git("-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-qm", "task commit", cwd=worktree)
        main_head = cli.git("rev-parse", "HEAD", cwd=self.repo)
        branch_head = cli.git("rev-parse", "bamberg/feature", cwd=self.repo)
        self.assertNotEqual(main_head, branch_head)
        self.clean_as_operator()
        self.assertFalse(worktree.exists())
        self.assertEqual(cli.git("rev-parse", "HEAD", cwd=self.repo), main_head)
        self.assertEqual((self.repo / "README").read_text(), "base\n")
        self.assertEqual(cli.git("rev-parse", "bamberg/feature", cwd=self.repo), branch_head)
        self.assertEqual(cli.details(self.repo, "feature")["status"], "cleaned")

    def test_cleanup_refuses_dirty_untracked_and_ignored_files(self):
        worktree = self.registered_task()
        for relative, content in (("README", "changed"), ("new.txt", "new"), ("secret.env", "secret")):
            if relative == "secret.env":
                (worktree / ".gitignore").write_text("secret.env\n")
                cli.git("add", ".gitignore", cwd=worktree)
                cli.git("-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-qm", "ignore secret", cwd=worktree)
            path = worktree / relative
            original = path.read_text() if path.exists() else None
            path.write_text(content)
            with self.assertRaises(cli.Error):
                self.clean_as_operator()
            self.assertTrue(worktree.exists())
            self.assertEqual(path.read_text(), content)
            if original is None:
                path.unlink()
            else:
                path.write_text(original)

    def test_cleanup_refuses_active_job_or_dirty_main(self):
        worktree = self.registered_task(status="running")
        with self.assertRaises(cli.Error):
            self.clean_as_operator()
        item = cli.details(self.repo, "feature")
        item["status"] = "completed"
        cli.save(cli.job_path(self.repo, "feature"), item)
        (self.repo / "README").write_text("main work\n")
        with self.assertRaises(cli.Error):
            self.clean_as_operator()
        self.assertTrue(worktree.exists())
        self.assertEqual((self.repo / "README").read_text(), "main work\n")

    def test_cleanup_rejects_noninteractive_and_wrong_worktree(self):
        worktree = self.registered_task()
        with patch.object(cli.Path, "cwd", return_value=self.repo), patch.object(sys.stdin, "isatty", return_value=False):
            with self.assertRaises(cli.Error):
                cli.cleanup(self.repo, "feature")
        with patch.object(cli.Path, "cwd", return_value=worktree), patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdout, "isatty", return_value=True):
            with self.assertRaises(cli.Error):
                cli.cleanup(self.repo, "feature")
        self.assertTrue(worktree.exists())

    def test_cleanup_cancelled_confirmation_keeps_everything(self):
        worktree = self.registered_task()
        main_head = cli.git("rev-parse", "HEAD", cwd=self.repo)
        with patch.object(cli.Path, "cwd", return_value=self.repo), patch.object(sys.stdin, "isatty", return_value=True), \
             patch.object(sys.stdout, "isatty", return_value=True), \
             patch.object(cli, "confirm_cleanup", side_effect=cli.Error("cancelled")):
            with self.assertRaises(cli.Error):
                cli.cleanup(self.repo, "feature")
        self.assertTrue(worktree.exists())
        self.assertEqual(cli.git("rev-parse", "HEAD", cwd=self.repo), main_head)
        self.assertEqual(cli.details(self.repo, "feature")["status"], "completed")


if __name__ == "__main__":
    unittest.main()
