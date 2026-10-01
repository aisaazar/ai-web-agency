import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

from agency.db import Base


REPO_ROOT = Path(__file__).resolve().parents[3]


def _alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["AGENCY_DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_initial_migration_round_trip_matches_metadata(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"

    upgrade = _alembic(database_url, "upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr

    inspector = inspect(create_engine(database_url))
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}

    check = _alembic(database_url, "check")
    assert check.returncode == 0, check.stdout + check.stderr

    downgrade = _alembic(database_url, "downgrade", "base")
    assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr

    assert inspect(create_engine(database_url)).get_table_names() == ["alembic_version"]
