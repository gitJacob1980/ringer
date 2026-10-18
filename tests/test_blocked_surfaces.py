from __future__ import annotations

import asyncio
import contextlib
import io
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tests import test_ringer as base

ringer = base.ringer


class BlockedSurfaceTests(unittest.TestCase):
    def task(self) -> ringer.TaskSpec:
        return ringer.TaskSpec(key="review-me", spec="Inspect the result.", check="false")

    def runtime(self, root: Path) -> ringer.TaskRuntime:
        marker = root / "logs" / "review-me.VERIFIER-DEFECT.md"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("Check assertion: x\nWhy it is wrong: y\nEvidence: z\n", encoding="utf-8")
        return ringer.TaskRuntime(
            task=self.task(),
            taskdir=root / "review-me",
            log_path=root / "review-me.log",
            status="blocked",
            final_verdict="BLOCKED",
            attempts=1,
            verifier_defect_path=marker,
        )

    def test_run_json_totals_count_blocked_as_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = self.runtime(root)
            writer = ringer.StateWriter(
                "run", "surface", "test", root / "state", {},
                datetime.now(timezone.utc), [runtime], threading.RLock(),
                artifact=ringer.ArtifactConfig(False, "", "", root / "index.html"),
            )
            state = writer.snapshot()
            self.assertEqual(state["totals"]["blocked"], 1)
            self.assertEqual(state["totals"]["done"], 1)
            self.assertEqual(state["tasks"][0]["status"], "blocked")
            self.assertEqual(state["tasks"][0]["verdict"], "BLOCKED")

    def test_terminal_summary_names_blocked_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = self.runtime(Path(tmp))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                ringer.print_summary("run", [runtime])
            text = out.getvalue()
            self.assertIn("blocked for review", text)
            self.assertIn("review-me.VERIFIER-DEFECT.md", text)

    def test_scoreboard_and_artifact_render_blocked_distinctly(self) -> None:
        rows = [{
            "run_id": "r", "task_key": "t", "worker_engine": "mock",
            "model": "real-model", "task_type": "code-fix", "retry": False,
            "verdict": "BLOCKED", "logged_at": "2026-10-18T00:00:00+00:00",
        }]
        score = ringer.aggregate_model_scoreboard_rows(rows)[0]
        self.assertEqual(score["blocked"], 1)
        self.assertEqual(score["failed"], 0)
        self.assertEqual(score["block_rate"], 1.0)
        state = {"run_name": "r", "identity": "i", "elapsed_s": 1, "tasks": [
            {"key": "t", "status": "blocked", "verdict": "BLOCKED", "elapsed_s": 1}
        ]}
        rendered = ringer.render_final_report_html(state)
        self.assertIn('class="blocked"', rendered)
        self.assertIn("blocked for review", rendered)

    def test_cancel_path_does_not_overwrite_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = ringer.Manifest(
                run_name="cancel", workdir=root / "work", max_parallel=1,
                worktrees=False, repo=None, tasks=(self.task(),),
            )
            config = ringer.AppConfig(
                path=None, identity_default=None, state_dir=root / "state",
                dashboard_port_base=18787, hud_port=18700, hud_app_path=None,
                allow_full_access=False,
                eval=ringer.EvalConfig("jsonl", root / "runs.jsonl"),
                engines={},
                artifact=ringer.ArtifactConfig(False, "", "", root / "index.html"),
            )
            runner = ringer.RingerRunner(manifest, config, "test", dashboard_enabled=False)
            runner.runtimes[0].status = "blocked"
            runner.runtimes[0].final_verdict = "BLOCKED"

            async def cancel(_runtime: ringer.TaskRuntime) -> None:
                raise asyncio.CancelledError

            runner._run_task = cancel  # type: ignore[method-assign]
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(runner.run())
            self.assertEqual(runner.runtimes[0].status, "blocked")
            self.assertEqual(runner.runtimes[0].final_verdict, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
