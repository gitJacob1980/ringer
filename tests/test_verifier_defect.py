"""Acceptance tests for the sanctioned verifier-defect exit (BLOCKED verdict).

Written by the orchestrator before implementation, independently of it. A worker that believes the
check itself is wrong writes VERIFIER-DEFECT.md in its task directory; when the task opts in and the
check fails, the task ends BLOCKED for orchestrator review with no automatic retry. Do not edit these
tests to make an implementation pass.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RINGER_PATH = ROOT / "ringer.py"
FIX_SWARM = ROOT / "templates" / "fix-swarm" / "checks" / "fix-swarm.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ringer as base  # noqa: E402  (reuse the CLI harness and the loaded module)

ringer = base.ringer

VALID_MARKER = (
    "# Verifier defect\\n"
    "Check assertion: scenario ok expects a UTC offset on filterStartDateTime\\n"
    "Why it is wrong: the fake round-trips JSON and ConvertFrom-Json turns the ISO string into a DateTime\\n"
    "Evidence: the request body carried 2026-10-15T11:01:46.0000000+00:00\\n"
)
FAILING_CHECK = 'test "$(cat out.txt 2>/dev/null)" = expected || { echo "expected=expected"; exit 1; }'
PASSING_CHECK = 'test "$(cat out.txt 2>/dev/null)" = done || { echo "expected=done"; exit 1; }'


class VerifierDefectTests(base.RingerCliTests):
    def setUp(self) -> None:
        super().setUp()
        self.write_config(
            {
                "write_done": ["-c", "printf done > out.txt"],
                "defect_valid": ["-c", f"printf done > out.txt; printf '{VALID_MARKER}' > VERIFIER-DEFECT.md"],
                "defect_thin": ["-c", "printf done > out.txt; printf 'the check is wrong' > VERIFIER-DEFECT.md"],
            }
        )

    def task(self, engine: str, check: str, **extra: object) -> dict[str, object]:
        data: dict[str, object] = {"key": "t1", "engine": engine, "spec": "Write done to out.txt.", "check": check}
        data.update(extra)
        return data

    def final_task(self) -> dict[str, object]:
        tasks = self.read_final_state()["tasks"]
        self.assertEqual(len(tasks), 1)
        return tasks[0]

    def test_valid_marker_with_failing_check_blocks_without_retry(self) -> None:
        manifest = self.write_manifest("blocked", self.manifest("blocked", self.task("defect_valid", FAILING_CHECK, allow_verifier_defect=True)))
        result = self.run_ringer(manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        rows = self.read_rows()
        self.assertEqual([row["verdict"] for row in rows], ["BLOCKED"], result.stdout)
        self.assertIn("ConvertFrom-Json", str(rows[0]["notes"]))
        task = self.final_task()
        self.assertEqual(task["status"], "blocked")
        self.assertEqual(task["verdict"], "BLOCKED")
        self.assertIn("BLOCKED", result.stdout)

    def test_passing_check_wins_over_a_marker(self) -> None:
        manifest = self.write_manifest("passwins", self.manifest("passwins", self.task("defect_valid", PASSING_CHECK, allow_verifier_defect=True)))
        result = self.run_ringer(manifest)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual([row["verdict"] for row in self.read_rows()], ["PASS"])
        self.assertEqual(self.final_task()["status"], "pass")

    def test_marker_without_required_fields_fails_and_retries(self) -> None:
        manifest = self.write_manifest("thin", self.manifest("thin", self.task("defect_thin", FAILING_CHECK, allow_verifier_defect=True)))
        result = self.run_ringer(manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual([row["verdict"] for row in self.read_rows()], ["FAIL", "FAIL"])
        self.assertEqual(self.final_task()["status"], "fail")

    def test_marker_is_ignored_when_task_did_not_opt_in(self) -> None:
        manifest = self.write_manifest("optout", self.manifest("optout", self.task("defect_valid", FAILING_CHECK)))
        result = self.run_ringer(manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual([row["verdict"] for row in self.read_rows()], ["FAIL", "FAIL"])

    def test_run_level_opt_in_applies_to_tasks(self) -> None:
        manifest = self.write_manifest(
            "runlevel", self.manifest("runlevel", self.task("defect_valid", FAILING_CHECK), allow_verifier_defect=True)
        )
        self.run_ringer(manifest)
        self.assertEqual([row["verdict"] for row in self.read_rows()], ["BLOCKED"])

    def test_opted_in_spec_tells_the_worker_about_the_marker_and_others_do_not(self) -> None:
        manifest = self.write_manifest("footer", self.manifest("footer", self.task("defect_valid", FAILING_CHECK, allow_verifier_defect=True)))
        self.run_ringer(manifest)
        spec = str(self.read_rows()[0]["spec"])
        self.assertIn("VERIFIER-DEFECT.md", spec)
        self.assertIn("Check assertion:", spec)
        self.assertIn("Why it is wrong:", spec)
        self.assertIn("Evidence:", spec)
        self.jsonl_path.unlink()
        manifest = self.write_manifest("nofooter", self.manifest("nofooter", self.task("write_done", PASSING_CHECK)))
        self.run_ringer(manifest)
        self.assertNotIn("VERIFIER-DEFECT", str(self.read_rows()[0]["spec"]))

    def test_stale_marker_from_an_earlier_run_does_not_block(self) -> None:
        taskdir = self.root / "work-stale" / "t1"
        taskdir.mkdir(parents=True)
        (taskdir / "VERIFIER-DEFECT.md").write_text(VALID_MARKER.replace("\\n", "\n"), encoding="utf-8")
        manifest = self.write_manifest("stale", self.manifest("stale", self.task("write_done", FAILING_CHECK, allow_verifier_defect=True)))
        self.run_ringer(manifest)
        self.assertEqual([row["verdict"] for row in self.read_rows()], ["FAIL", "FAIL"])

    def test_blocked_has_its_own_ringside_bucket(self) -> None:
        self.assertEqual(ringer.task_state_bucket("blocked"), "blocked")

    def test_scoreboard_counts_blocked_separately_and_out_of_the_rates(self) -> None:
        manifest = self.write_manifest("sb-blocked", self.manifest("sb-blocked", self.task("defect_valid", FAILING_CHECK, allow_verifier_defect=True)))
        self.run_ringer(manifest)
        manifest = self.write_manifest("sb-pass", self.manifest("sb-pass", self.task("write_done", PASSING_CHECK)))
        self.run_ringer(manifest)
        groups = ringer.aggregate_model_log_rows(self.read_rows())
        blocked = sum(int(g.get("blocked", 0)) for g in groups)
        self.assertEqual(blocked, 1, groups)
        self.assertEqual(sum(int(g["passed"]) for g in groups), 1)
        self.assertEqual(sum(int(g["failed"]) for g in groups), 0, "a BLOCKED task must not count as a model failure")
        for g in groups:
            if int(g.get("blocked", 0)):
                self.assertIn("block_rate", g)
            if int(g["passed"]):
                self.assertEqual(g["pass_rate"], 1.0, "BLOCKED tasks must not dilute the pass rate")


# Only this file's tests run here; the inherited CLI tests already run in test_ringer.py.
for _name in dir(base.RingerCliTests):
    if _name.startswith("test_") and _name not in VerifierDefectTests.__dict__:
        setattr(VerifierDefectTests, _name, None)


class FixSwarmMarkerTests(unittest.TestCase):
    def test_fix_swarm_keeps_the_marker_out_of_the_patch_and_ownership_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ringer-fixswarm-") as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
            (repo / "owned.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, env=env)
            (repo / "owned.txt").write_text("after\n", encoding="utf-8")
            (repo / "VERIFIER-DEFECT.md").write_text(VALID_MARKER.replace("\\n", "\n"), encoding="utf-8")
            (repo / "fix-summary.md").write_text(
                "# Fix Summary\n## Summary\nx\n## Files Changed\nx\n## Verification\nx\n## Assumptions\nx\n", encoding="utf-8"
            )
            patch = Path(tmp) / "out.patch"
            result = subprocess.run(
                [sys.executable, str(FIX_SWARM), "--verify-command", "true", "--patch", str(patch), "--summary", "fix-summary.md",
                 "--exported-summary", str(Path(tmp) / "summary.md"), "--owned-files", "owned.txt"],
                cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            text = patch.read_text(encoding="utf-8")
            self.assertIn("owned.txt", text)
            self.assertNotIn("VERIFIER-DEFECT", text)


if __name__ == "__main__":
    unittest.main()
