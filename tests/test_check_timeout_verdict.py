#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import ringer


ROOT = Path(__file__).resolve().parents[1]


def worker(*, timed_out: bool = False, error: str | None = None) -> ringer.WorkerResult:
    return ringer.WorkerResult(0, timed_out, None, error)


def verify(*, timed_out: bool = False, ok: bool = False) -> ringer.VerifyResult:
    return ringer.VerifyResult(ok, 0 if ok else 1, timed_out, "check output")


def row(task: str, verdict: str, *, retry: bool = False) -> dict[str, object]:
    return {
        "run_id": "run",
        "task_key": task,
        "logged_at": f"2026-10-24T00:00:0{len(task)}+00:00",
        "worker_engine": "mock",
        "model": "unit-model",
        "task_type": "code",
        "retry": retry,
        "verdict": verdict,
    }


class VerdictTests(unittest.TestCase):
    def test_precedence(self) -> None:
        self.assertEqual("PASS", ringer.verdict_for(worker(), verify(ok=True)))
        self.assertEqual("CHECK_TIMEOUT", ringer.verdict_for(worker(), verify(timed_out=True)))
        self.assertEqual("TIMEOUT", ringer.verdict_for(worker(timed_out=True), verify(timed_out=True)))
        self.assertEqual("ERROR", ringer.verdict_for(worker(error="boom"), verify(timed_out=True)))


class OfflineRunTests(unittest.TestCase):
    def test_check_timeout_is_not_retried(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            manifest = root / "manifest.json"
            config.write_text(
                "\n".join(
                    [
                        f"state_dir = {json.dumps(str(root / 'state'))}",
                        "[eval]",
                        'backend = "jsonl"',
                        f"jsonl_path = {json.dumps(str(root / 'runs.jsonl'))}",
                        "[artifact]",
                        "enabled = false",
                        "[engines.mock]",
                        f"bin = {json.dumps(sys.executable)}",
                        "args_template = [",
                        f"  {json.dumps(str(ROOT / 'engines' / 'mock_worker.py'))},",
                        '  "{spec}",',
                        "]",
                        "sandbox_args = []",
                        "full_access_args = []",
                    ]
                ),
                encoding="utf-8",
            )
            manifest.write_text(
                json.dumps(
                    {
                        "run_name": "check-timeout",
                        "workdir": str(root / "work"),
                        "worktrees": False,
                        "tasks": [
                            {
                                "key": "slow-check",
                                "engine": "mock",
                                "spec": "MOCK_FILE: done.txt\ndone\nMOCK_END",
                                "check": "sleep 5",
                                "check_timeout_s": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.update(
                {
                    "RINGER_NO_SELF_UPDATE": "1",
                    "HOME": str(root / "home"),
                    "RINGER_HOME": str(root / "ringer-home"),
                }
            )
            (root / "home").mkdir()
            (root / "ringer-home").mkdir()
            proc = subprocess.run(
                [
                    sys.executable,
                    "ringer.py",
                    "run",
                    str(manifest),
                    "--config",
                    str(config),
                    "--no-dashboard",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
            attempts = [json.loads(line) for line in (root / "runs.jsonl").read_text().splitlines()]
            self.assertEqual(1, len(attempts))
            self.assertEqual("CHECK_TIMEOUT", attempts[0]["verdict"])
            self.assertIn("check_timed_out=true check_timeout_s=1", attempts[0]["notes"])


class ScoreboardTests(unittest.TestCase):
    def test_check_timeout_is_unscored(self) -> None:
        rows = [
            row("a", "PASS"),
            row("b", "FAIL"),
            row("b", "PASS", retry=True),
            row("c", "FAIL"),
            row("d", "CHECK_TIMEOUT"),
        ]
        group = ringer.aggregate_model_log_rows(rows)[0]
        self.assertEqual(4, group["tasks"])
        self.assertEqual(1, group["check_timeouts"])
        self.assertEqual(2 / 3, group["pass_rate"])
        self.assertEqual(1 / 3, group["first_try_pass_rate"])
        self.assertEqual(3, group["scored_tasks"])
        rollup = ringer.aggregate_model_scoreboard_rows(rows)[0]
        self.assertEqual(1, rollup["check_timeouts"])
        self.assertEqual(3, rollup["scored_tasks"])
        self.assertEqual("probation", rollup["tier"])

        insufficient_evidence = ringer.aggregate_model_scoreboard_rows(
            [row("a", "PASS"), row("b", "PASS"), row("d", "CHECK_TIMEOUT")]
        )[0]
        self.assertEqual(3, insufficient_evidence["tasks"])
        self.assertEqual(2, insufficient_evidence["scored_tasks"])
        self.assertEqual("probation", insufficient_evidence["tier"])


class JsonlRepairTests(unittest.TestCase):
    def test_dry_run_apply_idempotence_and_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "runs.jsonl"
            candidate = row("slow", "TIMEOUT") | {
                "notes": "prefix [ringer.py] check timed out after 60s\nsuffix"
            }
            untouched = b'{"verdict":"TIMEOUT","notes":"worker timeout","odd":  spacing}\n'
            log.write_bytes(json.dumps(candidate).encode() + b"\n" + untouched + b"not-json\n")
            command = [
                sys.executable,
                "ringer.py",
                "reclassify-check-timeouts",
                "--log",
                str(log),
                "--no-postgres",
                "--no-db",
            ]
            before = log.read_bytes()
            dry = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(0, dry.returncode, dry.stderr)
            self.assertEqual(before, log.read_bytes())
            self.assertIn("Dry run - nothing written", dry.stdout)

            applied = subprocess.run(command + ["--apply"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(0, applied.returncode, applied.stderr)
            lines = log.read_bytes().splitlines(keepends=True)
            self.assertEqual("CHECK_TIMEOUT", json.loads(lines[0])["verdict"])
            self.assertEqual(untouched, lines[1])
            after_first = log.read_bytes()
            again = subprocess.run(command + ["--apply"], cwd=ROOT, text=True, capture_output=True)
            self.assertIn("jsonl: before=0 after=0 changed=0", again.stdout)
            self.assertEqual(after_first, log.read_bytes())


class FakeCursor:
    def __init__(self, rows: list[dict[str, object]], rowcount: int = 0) -> None:
        self.rows = rows
        self.rowcount = rowcount

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows


class FakePostgres:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.commits = 0

    def execute(self, sql: str, parameters: tuple[object, ...]) -> FakeCursor:
        self.calls.append((sql, parameters))
        if sql.lstrip().startswith("SELECT"):
            return FakeCursor(
                [
                    {
                        "id": 7,
                        "run_id": "run",
                        "task_key": "slow",
                        "retry": False,
                        "logged_at": "2026-10-24T00:00:00+00:00",
                        "model": "unit-model",
                        "notes": "[ringer.py] check timed out after 60s",
                    }
                ]
            )
        return FakeCursor([], 1)

    def commit(self) -> None:
        self.commits += 1


class PostgresRepairTests(unittest.TestCase):
    def test_updates_verdict_and_payload_by_id(self) -> None:
        conn = FakePostgres()
        candidates, changed = ringer.reclassify_postgres_check_timeouts(conn, apply=True)
        self.assertEqual(1, len(candidates))
        self.assertEqual(1, changed)
        self.assertIn("jsonb_set", conn.calls[1][0])
        self.assertIn("WHERE id = %s", conn.calls[1][0])
        self.assertEqual(("CHECK_TIMEOUT", "CHECK_TIMEOUT", 7), conn.calls[1][1][:3])
        self.assertEqual(1, conn.commits)


class SqliteRepairTests(unittest.TestCase):
    def test_real_schema_updates_only_matching_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ringer.db"
            conn = sqlite3.connect(db)
            ringer.create_read_model_schema(conn)
            source = row("slow", "TIMEOUT")
            ringer.insert_attempt_rows(conn, [source, row("other", "TIMEOUT")])
            conn.commit()
            conn.close()

            candidates, changed = ringer.reclassify_sqlite_check_timeouts(
                db, [source], apply=True
            )
            self.assertEqual(1, len(candidates))
            self.assertEqual(1, changed)
            conn = sqlite3.connect(db)
            verdicts = dict(conn.execute("SELECT task_key, verdict FROM attempts"))
            conn.close()
            self.assertEqual("CHECK_TIMEOUT", verdicts["slow"])
            self.assertEqual("TIMEOUT", verdicts["other"])


if __name__ == "__main__":
    unittest.main()
