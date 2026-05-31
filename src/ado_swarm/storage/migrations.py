from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import asyncpg

from ado_swarm.config import get_settings


def read_migration_sql() -> list[str]:
    return [migration.read_text() for migration in sorted(Path("migrations").glob("*.sql"))]


async def apply_migrations() -> None:
    settings = get_settings()
    migration_sql = read_migration_sql()
    conn = await asyncpg.connect(settings.database_url)
    try:
        for statement in migration_sql:
            await conn.execute(statement)
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["apply"])
    args = parser.parse_args()
    if args.command == "apply":
        asyncio.run(apply_migrations())


if __name__ == "__main__":
    main()
