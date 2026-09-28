"""SQLite online backup/restore utility for the MVP runbook."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)


def restore(backup_path: Path, destination: Path) -> None:
    if destination.resolve() == backup_path.resolve():
        raise ValueError("restore destination must differ from backup")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(backup_path) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "restore"):
        command = sub.add_parser(name)
        command.add_argument("source" if name == "backup" else "backup_file", type=Path)
        command.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "backup":
        backup(args.source, args.destination)
    else:
        restore(args.backup_file, args.destination)
    print(f"{args.command} complete: {args.destination}")


if __name__ == "__main__":
    main()
