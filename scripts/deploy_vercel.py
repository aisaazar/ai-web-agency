"""Deploy an already validated immutable site build to Vercel."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_SRC = Path(__file__).resolve().parents[1] / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from agency.providers.deploy import BuildBundle
from agency.providers.vercel_deploy import VercelDeploymentProvider


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = REPO_ROOT / ".artifacts" / "builds"


def latest_build_hash() -> str:
    builds = sorted(
        (path for path in BUILD_ROOT.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not builds:
        raise SystemExit("No immutable build bundles found. Run the site build pipeline first.")
    return builds[0].name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-hash", help="64-character immutable build hash")
    parser.add_argument("--domain", help="Optional custom domain to attach to the Vercel project")
    args = parser.parse_args()

    build_hash = args.build_hash or latest_build_hash()
    output_dir = BUILD_ROOT / build_hash
    if not output_dir.is_dir():
        raise SystemExit(f"Build bundle not found: {build_hash}")

    provider = VercelDeploymentProvider()
    result = provider.create_preview(BuildBundle(build_hash=build_hash, output_dir=output_dir))
    print(f"preview_status={result.status}")
    print(f"deployment_ref={result.deploy_ref}")
    print(f"preview_url={result.url}")

    if args.domain:
        domain = provider.attach_domain("site", args.domain)
        print(f"domain_status={domain.status}")
        print(f"domain={domain.fqdn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
