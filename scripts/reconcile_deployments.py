"""Converge deployments interrupted mid-promotion.

A publish or rollback that crashed between "intent committed" and "provider promoted" leaves a
single `promoting` row. This sweeps those rows to a deterministic terminal state. It is safe to run
repeatedly and is the operator-facing half of the two-phase promotion in
`agency.services.deploy_service`.

Usage:
    node scripts/py.mjs scripts/reconcile_deployments.py --database-url sqlite:///agency.db [--org-id <uuid>] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api" / "src"))

from agency.db.session import create_session_factory  # noqa: E402
from agency.services.deployment_reconcile import reconcile_deployments  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default="sqlite:///agency.db",
        help="SQLAlchemy database URL (default: sqlite:///agency.db)",
    )
    parser.add_argument(
        "--org-id",
        default=None,
        help="Limit the sweep to one organization; omit to sweep all organizations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be reconciled without writing anything.",
    )
    args = parser.parse_args(argv)

    session = create_session_factory(args.database_url)()
    try:
        if args.dry_run:
            from sqlalchemy import select

            from agency.db.models import Deploy
            from agency.services.deploy_service import RECONCILABLE_STATUSES

            query = select(Deploy).where(
                Deploy.environment == "production",
                Deploy.status.in_(RECONCILABLE_STATUSES),
            )
            if args.org_id:
                from uuid import UUID

                query = query.where(Deploy.org_id == UUID(args.org_id))
            pending = list(session.scalars(query))
            report = {"pending": [str(row.id) for row in pending], "dry_run": True}
        else:
            from uuid import UUID

            org_id = UUID(args.org_id) if args.org_id else None
            report = reconcile_deployments(session, org_id=org_id).as_dict()
    finally:
        session.close()

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())