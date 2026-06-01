"""Hermetic tests for the migration runner's pure logic (no live Postgres)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ado_swarm.storage.migrations import (
    Migration,
    MigrationChecksumMismatchError,
    checksum_sql,
    find_migrations_dir,
    load_migrations,
    pending_migrations,
    validate_applied_checksums,
)


def _migration(name: str, sql: str = "SELECT 1;") -> Migration:
    return Migration(filename=name, sql=sql)


def test_checksum_is_stable_for_same_content() -> None:
    assert checksum_sql("CREATE TABLE foo();") == checksum_sql("CREATE TABLE foo();")


def test_checksum_normalises_line_endings() -> None:
    assert checksum_sql("a\r\nb") == checksum_sql("a\nb")


def test_checksum_changes_with_content() -> None:
    assert checksum_sql("CREATE TABLE foo();") != checksum_sql("CREATE TABLE bar();")


def test_migration_checksum_property_matches_function() -> None:
    migration = _migration("0001_x.sql", "CREATE TABLE foo();")
    assert migration.checksum == checksum_sql("CREATE TABLE foo();")


def test_pending_selects_only_unapplied() -> None:
    migrations = [
        _migration("0001_a.sql"),
        _migration("0002_b.sql"),
        _migration("0003_c.sql"),
    ]
    pending = pending_migrations(migrations, applied_filenames=["0001_a.sql"])
    assert [m.filename for m in pending] == ["0002_b.sql", "0003_c.sql"]


def test_pending_empty_when_all_applied() -> None:
    migrations = [_migration("0001_a.sql"), _migration("0002_b.sql")]
    pending = pending_migrations(migrations, applied_filenames=["0001_a.sql", "0002_b.sql"])
    assert pending == []


def test_pending_returns_all_when_none_applied() -> None:
    migrations = [_migration("0001_a.sql"), _migration("0002_b.sql")]
    pending = pending_migrations(migrations, applied_filenames=[])
    assert [m.filename for m in pending] == ["0001_a.sql", "0002_b.sql"]


def test_pending_preserves_input_order() -> None:
    migrations = [_migration("0002_b.sql"), _migration("0001_a.sql")]
    pending = pending_migrations(migrations, applied_filenames=[])
    assert [m.filename for m in pending] == ["0002_b.sql", "0001_a.sql"]


def test_pending_ignores_extra_applied_filenames() -> None:
    migrations = [_migration("0001_a.sql")]
    pending = pending_migrations(migrations, applied_filenames=["0001_a.sql", "9999_gone.sql"])
    assert pending == []


def test_validate_applied_checksums_accepts_matching_files() -> None:
    migration = _migration("0001_a.sql", "CREATE TABLE a();")
    validate_applied_checksums([migration], {migration.filename: migration.checksum})


def test_validate_applied_checksums_ignores_missing_local_files() -> None:
    validate_applied_checksums([], {"9999_removed.sql": checksum_sql("SELECT 1;")})


def test_validate_applied_checksums_rejects_changed_file() -> None:
    migration = _migration("0001_a.sql", "CREATE TABLE changed();")
    applied_checksum = checksum_sql("CREATE TABLE original();")
    with pytest.raises(MigrationChecksumMismatchError) as exc:
        validate_applied_checksums([migration], {migration.filename: applied_checksum})
    assert exc.value.filename == "0001_a.sql"
    assert exc.value.applied_checksum == applied_checksum
    assert exc.value.current_checksum == migration.checksum


def test_find_migrations_dir_is_cwd_independent(tmp_path: Path) -> None:
    original = os.getcwd()
    resolved_from_repo = find_migrations_dir()
    try:
        os.chdir(tmp_path)
        resolved_from_tmp = find_migrations_dir()
    finally:
        os.chdir(original)
    assert resolved_from_repo == resolved_from_tmp
    assert resolved_from_repo.is_dir()
    assert resolved_from_repo.name == "migrations"


def test_find_migrations_dir_points_at_real_sql_files() -> None:
    directory = find_migrations_dir()
    sql_files = sorted(p.name for p in directory.glob("*.sql"))
    assert sql_files, "expected at least one migration file in the repo"


def test_load_migrations_sorted_with_checksums(tmp_path: Path) -> None:
    (tmp_path / "0002_b.sql").write_text("CREATE TABLE b();", encoding="utf-8")
    (tmp_path / "0001_a.sql").write_text("CREATE TABLE a();", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    migrations = load_migrations(tmp_path)

    assert [m.filename for m in migrations] == ["0001_a.sql", "0002_b.sql"]
    assert migrations[0].checksum == checksum_sql("CREATE TABLE a();")


def test_load_migrations_real_repo_dir() -> None:
    migrations = load_migrations()
    names = [m.filename for m in migrations]
    assert names == sorted(names)
    assert all(m.checksum for m in migrations)


def test_find_migrations_dir_raises_when_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    import ado_swarm.storage.migrations as mod

    fake_file = Path("/nonexistent-root/pkg/storage/migrations.py")
    monkeypatch.setattr(mod, "__file__", str(fake_file))
    with pytest.raises(FileNotFoundError):
        find_migrations_dir()
