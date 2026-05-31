"""Migration runner.

Applies the SQL files in ``migrations/`` against Postgres, tracking what has
already run in a ``schema_migrations`` ledger so it is safe to run repeatedly.

The path resolution, checksum, and pending-selection logic are pure functions so
they can be unit-tested without a live database (see
``tests/unit/test_storage_migrations.py``).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import asyncpg

from ado_swarm.config import get_settings

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


@dataclass(frozen=True)
class Migration:
    """A single migration file: its filename, SQL body, and content checksum."""

    filename: str
    sql: str

    @property
    def checksum(self) -> str:
        return checksum_sql(self.sql)


def checksum_sql(sql: str) -> str:
    """Stable content hash of a migration's SQL (newline-normalised)."""
    normalised = sql.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(normalised).hexdigest()


def find_migrations_dir() -> Path:
    """Resolve the ``migrations/`` directory relative to the repo, not the CWD.

    Walks up from this module's location (``src/ado_swarm/storage``) looking for a
    sibling ``migrations`` directory at the repo root.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "migrations"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate a 'migrations' directory above " + str(here))


def load_migrations(migrations_dir: Path | None = None) -> list[Migration]:
    """Load every ``*.sql`` migration, sorted by filename."""
    directory = migrations_dir or find_migrations_dir()
    return [
        Migration(filename=path.name, sql=path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.sql"))
    ]


def pending_migrations(
    migrations: Iterable[Migration], applied_filenames: Iterable[str]
) -> list[Migration]:
    """Return migrations whose filename is not yet in ``applied_filenames``.

    Order is preserved from the input iterable (callers pass them sorted).
    """
    applied = set(applied_filenames)
    return [m for m in migrations if m.filename not in applied]


async def apply_migrations(
    database_url: str | None = None, migrations_dir: Path | None = None
) -> list[str]:
    """Apply all pending migrations idempotently. Returns the filenames applied."""
    url = database_url or get_settings().database_url
    migrations = load_migrations(migrations_dir)

    conn = await asyncpg.connect(url)
    applied_now: list[str] = []
    try:
        await conn.execute(SCHEMA_MIGRATIONS_DDL)
        rows = await conn.fetch("SELECT filename FROM schema_migrations")
        already_applied = [row["filename"] for row in rows]

        for migration in pending_migrations(migrations, already_applied):
            async with conn.transaction():
                await conn.execute(migration.sql)
                await conn.execute(
                    """
                    INSERT INTO schema_migrations (filename, checksum)
                    VALUES ($1, $2)
                    ON CONFLICT (filename) DO NOTHING
                    """,
                    migration.filename,
                    migration.checksum,
                )
            applied_now.append(migration.filename)
    finally:
        await conn.close()
    return applied_now


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["apply"])
    args = parser.parse_args()
    if args.command == "apply":
        applied = asyncio.run(apply_migrations())
        if applied:
            print("Applied migrations: " + ", ".join(applied))
        else:
            print("No pending migrations.")


if __name__ == "__main__":
    main()
