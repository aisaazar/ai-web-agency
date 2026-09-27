"""Create and verify a portable AI Web Agency backup bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_sqlite(source: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(source)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()


def _integrity_check(database: Path) -> None:
    connection = sqlite3.connect(database)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    finally:
        connection.close()
    if result != ("ok",):
        raise RuntimeError(f"SQLite integrity check failed: {result}")


def create_backup(database: Path, artifacts: Path, output_dir: Path) -> Path:
    if not database.is_file():
        raise FileNotFoundError(f"database not found: {database}")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = output_dir / f"agency-backup-{timestamp}.zip"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db_copy = temp / "agency.db"
        _snapshot_sqlite(database, db_copy)
        _integrity_check(db_copy)
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database": {"path": str(database), "sha256": _sha256(db_copy)},
            "artifacts_root": str(artifacts),
        }
        manifest_path = temp / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(db_copy, "agency.db")
            bundle.write(manifest_path, "manifest.json")
            if artifacts.is_dir():
                for path in artifacts.rglob("*"):
                    if path.is_file():
                        bundle.write(path, Path("artifacts") / path.relative_to(artifacts))
    return archive


def verify_backup(archive: Path, restore_dir: Path) -> None:
    restore_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(temp)
        database = temp / "agency.db"
        manifest = json.loads((temp / "manifest.json").read_text(encoding="utf-8"))
        _integrity_check(database)
        if _sha256(database) != manifest["database"]["sha256"]:
            raise RuntimeError("restored database checksum does not match manifest")
        restored = restore_dir / "agency-restore-drill.db"
        shutil.copy2(database, restored)
    print(f"BACKUP OK: {archive}")
    print(f"RESTORE OK: {restored}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("agency.db"))
    parser.add_argument("--artifacts", type=Path, default=Path(".artifacts"))
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    parser.add_argument("--verify", type=Path, help="restore-drill output directory")
    args = parser.parse_args()
    archive = create_backup(args.database, args.artifacts, args.output_dir)
    if args.verify:
        verify_backup(archive, args.verify)
    else:
        print(f"BACKUP OK: {archive}")


if __name__ == "__main__":
    main()
