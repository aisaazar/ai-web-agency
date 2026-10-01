import sqlite3
import zipfile

from scripts.backup_agency import create_backup, verify_backup


def _seed_database(path):
    connection = sqlite3.connect(path)
    try:
        connection.execute("create table clients (id integer primary key, name text not null)")
        connection.execute("insert into clients(name) values ('Backup Drill')")
        connection.commit()
    finally:
        connection.close()


def test_backup_skips_nested_output_tree(tmp_path):
    database = tmp_path / "agency.db"
    artifacts = tmp_path / "artifacts"
    output_dir = artifacts / "backups"
    restore_dir = tmp_path / "restore"
    artifacts.mkdir()
    output_dir.mkdir()
    (artifacts / "sample.txt").write_text("artifact", encoding="utf-8")
    (output_dir / "old.txt").write_text("must stay outside", encoding="utf-8")
    _seed_database(database)

    archive = create_backup(database, artifacts, output_dir)
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())

    assert "artifacts/sample.txt" in names
    assert not any(name.startswith("artifacts/backups/") for name in names)
    verify_backup(archive, restore_dir)
    assert (restore_dir / "agency-restore-drill.db").is_file()
