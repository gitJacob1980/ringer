#!/usr/bin/env python3
"""Backfill historical Ringer JSONL eval rows into Postgres."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TextIO


STANDARD_COLUMNS = (
    "run_id",
    "pattern",
    "task_key",
    "spec",
    "worker_engine",
    "shepherd_model",
    "verify_method",
    "verdict",
    "duration_ms",
    "worker_tokens",
    "notes",
    "orchestrator",
    "model",
    "reported_model",
    "expected_model",
    "reasoning_effort",
    "task_type",
    "retry",
)

REQUIRED_ENV_KEYS = (
    "SUPABASE_DB_HOST",
    "SUPABASE_DB_PORT",
    "SUPABASE_DB_USER",
    "SUPABASE_DB_PASSWORD",
    "SUPABASE_DB_NAME",
)

INSERT_SQL = """
INSERT INTO swarm_runs (
    logged_at, run_id, pattern, task_key, spec, worker_engine, shepherd_model,
    verify_method, verdict, duration_ms, worker_tokens, notes, orchestrator,
    model, reported_model, expected_model, reasoning_effort, task_type, retry,
    payload
)
VALUES (
    %(logged_at)s, %(run_id)s, %(pattern)s, %(task_key)s, %(spec)s,
    %(worker_engine)s, %(shepherd_model)s, %(verify_method)s, %(verdict)s,
    %(duration_ms)s, %(worker_tokens)s, %(notes)s, %(orchestrator)s, %(model)s,
    %(reported_model)s, %(expected_model)s, %(reasoning_effort)s,
    %(task_type)s, %(retry)s, %(payload)s::jsonb
)
"""


@dataclass(frozen=True)
class ParsedFile:
    path: Path
    rows: list[dict[str, Any]]
    skipped: int


def parse_env_file(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE credentials without depending on ringer.py."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def parse_jsonl(path: Path) -> ParsedFile:
    """Return object rows from *path*, counting malformed and non-object lines."""
    rows: list[dict[str, Any]] = []
    skipped = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, UnicodeError):
                skipped += 1
                continue
            if not isinstance(row, dict):
                skipped += 1
                continue
            rows.append(row)
    return ParsedFile(path=path, rows=rows, skipped=skipped)


def normalize_retry(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def insert_parameters(row: dict[str, Any]) -> dict[str, Any]:
    """Build database parameters while retaining the exact source object in payload."""
    parameters = {column: row.get(column) for column in STANDARD_COLUMNS}
    parameters["retry"] = normalize_retry(row.get("retry"))
    logged_at = row.get("logged_at")
    parameters["logged_at"] = (
        logged_at if isinstance(logged_at, str) and logged_at.strip() else None
    )
    parameters["payload"] = json.dumps(row, sort_keys=True, default=str)
    return parameters


def run_backfill(
    paths: list[Path],
    *,
    connection: Any | None,
    dry_run: bool,
    output: TextIO = sys.stdout,
) -> tuple[int, int]:
    """Parse all files and insert their rows in one transaction."""
    parsed_files = [parse_jsonl(path) for path in paths]
    total_rows = sum(len(parsed.rows) for parsed in parsed_files)
    total_skipped = sum(parsed.skipped for parsed in parsed_files)

    if not dry_run:
        if connection is None:
            raise ValueError("a database connection is required unless --dry-run is used")
        try:
            for parsed in parsed_files:
                for row in parsed.rows:
                    connection.execute(INSERT_SQL, insert_parameters(row))
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    for parsed in parsed_files:
        inserted = 0 if dry_run else len(parsed.rows)
        suffix = f", rows eligible: {len(parsed.rows)}" if dry_run else ""
        print(
            f"{parsed.path}: rows inserted: {inserted}, "
            f"lines skipped: {parsed.skipped}{suffix}",
            file=output,
        )
    inserted_total = 0 if dry_run else total_rows
    suffix = f", rows eligible: {total_rows}" if dry_run else ""
    print(
        f"grand total: rows inserted: {inserted_total}, "
        f"lines skipped: {total_skipped}{suffix}",
        file=output,
    )
    return inserted_total, total_skipped


def connect_postgres(env_file: Path) -> Any:
    credentials = parse_env_file(env_file)
    missing = [key for key in REQUIRED_ENV_KEYS if not credentials.get(key)]
    if missing:
        raise ValueError(f"missing database env keys: {', '.join(missing)}")

    try:
        import psycopg  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(f"psycopg import failed: {exc}") from exc

    return psycopg.connect(
        host=credentials["SUPABASE_DB_HOST"],
        port=int(credentials["SUPABASE_DB_PORT"]),
        user=credentials["SUPABASE_DB_USER"],
        password=credentials["SUPABASE_DB_PASSWORD"],
        dbname=credentials["SUPABASE_DB_NAME"],
        connect_timeout=5,
    )


def main(
    argv: list[str] | None = None,
    *,
    connection_factory: Callable[[Path], Any] = connect_postgres,
    output: TextIO = sys.stdout,
    error: TextIO = sys.stderr,
) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill Ringer JSONL eval logs into swarm_runs."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("~/.config/ringer/db.env"),
        help="database credentials file (default: ~/.config/ringer/db.env)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="parse and report without database writes"
    )
    parser.add_argument("jsonl_paths", type=Path, nargs="+")
    args = parser.parse_args(argv)

    connection = None
    try:
        if not args.dry_run:
            connection = connection_factory(args.env_file.expanduser())
        run_backfill(
            [path.expanduser() for path in args.jsonl_paths],
            connection=connection,
            dry_run=args.dry_run,
            output=output,
        )
    except Exception as exc:
        print(f"error: {exc}", file=error)
        return 1
    finally:
        if connection is not None:
            connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
