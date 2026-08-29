#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import backfill_jsonl_to_postgres as backfill


class FakeConnection:
    def __init__(self) -> None:
        self.executions: list[tuple[str, dict[str, object]]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, sql: str, parameters: dict[str, object]) -> None:
        self.executions.append((sql, parameters))

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


class BackfillJsonlToPostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_jsonl(self, name: str, contents: str) -> Path:
        path = self.root / name
        path.write_text(contents, encoding="utf-8")
        return path

    def run_main(
        self, path: Path, connection: FakeConnection, *extra: str
    ) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        result = backfill.main(
            [*extra, str(path)],
            connection_factory=lambda _path: connection,
            output=stdout,
            error=stderr,
        )
        return result, stdout.getvalue(), stderr.getvalue()

    def test_well_formed_row_preserves_fields_timestamp_and_payload(self) -> None:
        row = {
            "run_id": "run-1",
            "model": "gpt-example",
            "task_type": "code-feature",
            "retry": "true",
            "logged_at": "2026-08-27T12:34:56+00:00",
            "extra": {"source": "historical"},
        }
        path = self.write_jsonl("runs.jsonl", json.dumps(row) + "\n")
        connection = FakeConnection()

        result, stdout, stderr = self.run_main(path, connection)

        self.assertEqual(0, result, stderr)
        self.assertEqual(1, len(connection.executions))
        sql, parameters = connection.executions[0]
        self.assertIn("%(payload)s::jsonb", sql)
        self.assertEqual("gpt-example", parameters["model"])
        self.assertEqual("code-feature", parameters["task_type"])
        self.assertIs(True, parameters["retry"])
        self.assertEqual("2026-08-27T12:34:56+00:00", parameters["logged_at"])
        self.assertEqual(row, json.loads(str(parameters["payload"])))
        self.assertEqual(1, connection.commits)
        self.assertEqual(0, connection.rollbacks)
        self.assertTrue(connection.closed)
        self.assertIn("rows inserted: 1, lines skipped: 0", stdout)

    def test_malformed_and_non_dict_lines_are_skipped(self) -> None:
        path = self.write_jsonl(
            "mixed.jsonl",
            'not json\n["not", "an", "object"]\n{"run_id": "valid"}\n',
        )
        connection = FakeConnection()

        result, stdout, stderr = self.run_main(path, connection)

        self.assertEqual(0, result, stderr)
        self.assertEqual(1, len(connection.executions))
        self.assertIn("rows inserted: 1, lines skipped: 2", stdout)

    def test_dry_run_does_not_connect_or_execute(self) -> None:
        path = self.write_jsonl("dry.jsonl", '{"run_id": "dry"}\n')
        connection = FakeConnection()
        factory_calls = 0

        def connection_factory(_path: Path) -> FakeConnection:
            nonlocal factory_calls
            factory_calls += 1
            return connection

        stdout = io.StringIO()
        result = backfill.main(
            ["--dry-run", str(path)],
            connection_factory=connection_factory,
            output=stdout,
            error=io.StringIO(),
        )

        self.assertEqual(0, result)
        self.assertEqual(0, factory_calls)
        self.assertEqual([], connection.executions)
        self.assertEqual(0, connection.commits)
        self.assertIn("rows inserted: 0, lines skipped: 0, rows eligible: 1", stdout.getvalue())

    def test_missing_logged_at_is_inserted_as_null(self) -> None:
        path = self.write_jsonl("undated.jsonl", '{"run_id": "old"}\n')
        connection = FakeConnection()

        result, _stdout, stderr = self.run_main(path, connection)

        self.assertEqual(0, result, stderr)
        self.assertIsNone(connection.executions[0][1]["logged_at"])


if __name__ == "__main__":
    unittest.main()
