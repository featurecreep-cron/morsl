"""Tests for database snapshots: daily, at startup, and before migrations."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from morsl import db
from morsl.db import (
    BACKUP_DIR_NAME,
    DAILY_BACKUPS_KEPT,
    SCHEMA_VERSION,
    backup_database,
    backup_if_stale,
    get_connection,
    latest_backup_time,
)
from morsl.services.scheduler_service import SchedulerService


@pytest.fixture
def data_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def db_file(data_dir):
    conn = get_connection(data_dir)
    conn.close()
    return os.path.join(data_dir, "morsl.db")


def _backup_dir(data_dir: str) -> str:
    return os.path.join(data_dir, BACKUP_DIR_NAME)


def _fake_backup(data_dir: str, when: datetime, reason: str = "daily") -> str:
    """An existing snapshot taken at `when` (content irrelevant to pruning)."""
    os.makedirs(_backup_dir(data_dir), exist_ok=True)
    name = f"morsl-{when.strftime('%Y%m%dT%H%M%SZ')}-{reason}.db"
    path = os.path.join(_backup_dir(data_dir), name)
    open(path, "wb").close()
    return path


class TestBackupDatabase:
    def test_snapshot_contains_uncheckpointed_wal_writes(self, data_dir, db_file):
        # A file copy of a WAL database misses writes still in the -wal file.
        # The online backup API must not.
        writer = sqlite3.connect(db_file)
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("INSERT INTO users (username, password_hash) VALUES ('alice', '')")
        writer.commit()
        assert os.path.getsize(db_file + "-wal") > 0

        path = backup_database(db_file)
        writer.close()

        snap = sqlite3.connect(path)
        names = [r[0] for r in snap.execute("SELECT username FROM users")]
        snap.close()
        assert names == ["alice"]

    def test_snapshot_is_named_by_utc_time_and_reason(self, data_dir, db_file):
        before = datetime.now(timezone.utc).replace(microsecond=0)
        path = backup_database(db_file, reason="daily")
        assert os.path.dirname(path) == _backup_dir(data_dir)
        assert path.endswith("-daily.db")
        assert latest_backup_time(data_dir) >= before

    def test_keeps_a_week_of_daily_snapshots(self, data_dir, db_file):
        now = datetime.now(timezone.utc)
        oldest = [_fake_backup(data_dir, now - timedelta(days=d)) for d in range(10, 0, -1)]

        newest = backup_database(db_file)

        kept = sorted(n for n in os.listdir(_backup_dir(data_dir)) if n.endswith("-daily.db"))
        assert len(kept) == DAILY_BACKUPS_KEPT
        assert kept[-1] == os.path.basename(newest)
        # The six youngest pre-existing ones survive, the four oldest are gone.
        assert kept[:-1] == [os.path.basename(p) for p in oldest[-6:]]

    def test_pruning_leaves_other_reasons_alone(self, data_dir, db_file):
        now = datetime.now(timezone.utc)
        migration = _fake_backup(data_dir, now - timedelta(days=60), reason="pre-v2")
        for d in range(10, 0, -1):
            _fake_backup(data_dir, now - timedelta(days=d))

        backup_database(db_file)

        assert os.path.exists(migration)

    def test_no_partial_file_is_left_behind(self, data_dir, db_file):
        backup_database(db_file)
        assert not [n for n in os.listdir(_backup_dir(data_dir)) if n.endswith(".partial")]

    def test_interrupted_backup_does_not_count_and_leaves_nothing(
        self, data_dir, db_file, monkeypatch
    ):
        def fail(src, dst):
            raise OSError("No space left on device")

        monkeypatch.setattr(db.os, "replace", fail)
        with pytest.raises(OSError, match="No space left"):
            backup_database(db_file)

        assert latest_backup_time(data_dir) is None
        assert os.listdir(_backup_dir(data_dir)) == []

    def test_missing_database_is_an_error_not_an_empty_snapshot(self, data_dir):
        missing = os.path.join(data_dir, "morsl.db")
        with pytest.raises(FileNotFoundError):
            backup_database(missing)
        assert not os.path.exists(missing)


class TestBackupIfStale:
    def test_takes_one_when_none_exists(self, data_dir, db_file):
        assert backup_if_stale(data_dir) is not None
        assert latest_backup_time(data_dir) is not None

    def test_skips_when_a_recent_one_exists(self, data_dir, db_file):
        _fake_backup(data_dir, datetime.now(timezone.utc) - timedelta(hours=2))
        assert backup_if_stale(data_dir) is None

    def test_takes_one_when_the_newest_is_over_a_day_old(self, data_dir, db_file):
        _fake_backup(data_dir, datetime.now(timezone.utc) - timedelta(days=2))
        assert backup_if_stale(data_dir) is not None

    def test_recent_migration_snapshot_does_not_count_as_daily(self, data_dir, db_file):
        _fake_backup(data_dir, datetime.now(timezone.utc), reason="pre-v2")
        assert backup_if_stale(data_dir) is not None

    def test_nothing_to_back_up_before_the_database_exists(self, data_dir):
        assert backup_if_stale(data_dir) is None
        assert not os.path.exists(_backup_dir(data_dir))


def _downgrade_to_v1(db_file: str) -> None:
    """Make an existing database look like it predates the latest migration."""
    conn = sqlite3.connect(db_file)
    conn.execute("DELETE FROM schema_version WHERE version > 1")
    conn.execute("DROP TABLE weekly_plans")
    conn.execute("INSERT INTO users (username, password_hash) VALUES ('bob', '')")
    conn.commit()
    conn.close()


class TestPreMigrationBackup:
    def test_snapshot_of_the_old_schema_is_taken_before_migrating(self, data_dir, db_file):
        _downgrade_to_v1(db_file)

        get_connection(data_dir).close()

        snaps = [
            n
            for n in os.listdir(_backup_dir(data_dir))
            if n.endswith(f"-pre-v{SCHEMA_VERSION}.db")
        ]
        assert len(snaps) == 1
        snap = sqlite3.connect(os.path.join(_backup_dir(data_dir), snaps[0]))
        version = snap.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        users = [r[0] for r in snap.execute("SELECT username FROM users")]
        snap.close()
        assert version == 1
        assert users == ["bob"]

    def test_new_database_takes_no_snapshot(self, data_dir):
        get_connection(data_dir).close()
        assert not os.path.exists(_backup_dir(data_dir))

    def test_up_to_date_database_takes_no_snapshot(self, data_dir, db_file):
        get_connection(data_dir).close()
        assert not os.path.exists(_backup_dir(data_dir))

    def test_failed_snapshot_blocks_the_migration(self, data_dir, db_file, monkeypatch):
        _downgrade_to_v1(db_file)

        def fail(*args, **kwargs):
            raise OSError("No space left on device")

        monkeypatch.setattr(db, "backup_database", fail)
        with pytest.raises(OSError, match="No space left"):
            get_connection(data_dir)

        conn = sqlite3.connect(db_file)
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        conn.close()
        assert version == 1


class TestDailyJob:
    def test_registered_at_the_given_time_and_not_listed_as_a_schedule(self, tmp_path):
        svc = SchedulerService(data_dir=str(tmp_path))
        svc.add_daily_job("system:db-backup", lambda: None, hour=3, minute=17)

        job = svc._scheduler.get_job("system:db-backup")
        fields = {f.name: str(f) for f in job.trigger.fields}
        assert (fields["hour"], fields["minute"]) == ("3", "17")
        assert fields["day"] == "*"
        assert svc.list_schedules() == []

    @pytest.mark.asyncio
    async def test_follows_a_timezone_change(self, tmp_path):
        # Started, as in the app: before start() APScheduler only queues jobs,
        # and a replaced job is still visible in that queue.
        from zoneinfo import ZoneInfo

        svc = SchedulerService(data_dir=str(tmp_path))
        svc.add_daily_job("system:db-backup", lambda: None, hour=3, minute=17)
        svc.start()
        try:
            svc.update_timezone(ZoneInfo("America/Chicago"))
            job = svc._scheduler.get_job("system:db-backup")
            assert str(job.trigger.timezone) == "America/Chicago"
        finally:
            svc.stop()

    def test_wired_up_by_app_startup(self, tmp_path, monkeypatch):
        from morsl.app import main

        svc = SchedulerService(data_dir=str(tmp_path))
        monkeypatch.setattr(main, "get_scheduler_service", lambda settings: svc)
        monkeypatch.setattr(main, "_build_scheduler_callbacks", lambda settings: (None,) * 4)
        monkeypatch.setattr(svc, "start", lambda: None)

        main._setup_scheduler(type("S", (), {"data_dir": str(tmp_path)})())

        assert svc._scheduler.get_job("system:db-backup") is not None

    def test_failed_daily_backup_is_logged_not_raised(self, tmp_path, caplog):
        from morsl.app import main

        missing = type("S", (), {"data_dir": str(tmp_path / "nope")})()
        main._daily_backup(missing)

        assert "Daily database backup failed" in caplog.text
