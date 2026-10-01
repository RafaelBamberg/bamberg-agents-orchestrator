import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
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

    def test_accounts_reject_shared_profiles(self):
        self.add_account("alice", "claude")
        from argparse import Namespace
        with self.assertRaises(cli.Error):
            cli.account_add(self.repo, Namespace(id="bob", provider="codex", home=str(Path(self.temp.name) / "alice" / "nested"), label=None))

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


if __name__ == "__main__":
    unittest.main()
