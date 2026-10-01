"""Deploy an already validated immutable site build to Vercel."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

API_SRC = Path(__file__).resolve().parents[1] / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from agency.providers.deploy import BuildBundle
from agency.providers.vercel_deploy import VercelDeploymentProvider


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = REPO_ROOT / ".artifacts" / "builds"
PRODUCTION_PREFLIGHT = REPO_ROOT / "scripts" / "validate-production-config.mjs"


def production_preflight() -> None:
    """Refuse direct Vercel deployment unless production runtime config is valid."""
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Node.js is required for production runtime preflight")
    result = subprocess.run([node, str(PRODUCTION_PREFLIGHT)], cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit("Production runtime preflight failed; deployment was not attempted.")


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
    production_preflight()

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
