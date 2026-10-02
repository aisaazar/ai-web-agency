"""Deployment provider contract and deterministic local-static implementation."""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


# A build directory is only publishable once this marker sits beside the exported pages.
# `shutil.copytree` into the final path is not atomic, so an interrupted copy (timeout, killed
# process, full disk) used to leave a half-populated directory that still contained index.html
# and therefore passed every existence check on its way to going live.
BUILD_COMPLETE_MARKER = ".build-complete"

_BUILD_HASH_PATTERN = re.compile(r"[a-f0-9]{64}")


def _require_build_hash(value: str) -> str:
    """A build reference is a hex digest, never a caller-supplied path fragment."""
    if not isinstance(value, str) or _BUILD_HASH_PATTERN.fullmatch(value) is None:
        raise ValueError("build_hash must be a 64-character lowercase hex digest")
    return value


def publish_directory_atomically(source: Path, destination: Path) -> Path:
    """Copy `source` into `destination` so readers only ever see a complete directory.

    The copy is staged in a sibling directory and the finished tree is moved into place, so a
    crash mid-copy cannot leave a partial directory at the published path. A previously published
    directory is only unlinked once its replacement is fully staged.
    """
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{destination.name}.staging"
    superseded = destination.parent / f".{destination.name}.superseded"
    for leftover in (staging, superseded):
        shutil.rmtree(leftover, ignore_errors=True)
    try:
        shutil.copytree(source, staging)
        (staging / BUILD_COMPLETE_MARKER).write_text("ok\n", encoding="utf-8")
        if destination.exists():
            os.replace(destination, superseded)
        try:
            os.replace(staging, destination)
        except OSError:
            # The destination is still occupied: put the previously published tree back rather
            # than leaving the site with no build at all.
            if superseded.exists() and not destination.exists():
                os.replace(superseded, destination)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(superseded, ignore_errors=True)
    return destination


def is_complete_build_directory(path: Path) -> bool:
    """A build directory counts as publishable only if it is marked complete and has an entry page."""
    path = Path(path)
    return (path / BUILD_COMPLETE_MARKER).is_file() and (path / "index.html").is_file()


@dataclass(frozen=True)
class BuildBundle:
    build_hash: str
    output_dir: Path


@dataclass(frozen=True)
class DeployResult:
    provider: str
    deploy_ref: str
    status: str
    url: str | None = None


@dataclass(frozen=True)
class DomainResult:
    provider: str
    fqdn: str
    status: str


class DeploymentProvider:
    name: str

    def create_preview(self, bundle: BuildBundle) -> DeployResult:
        raise NotImplementedError

    def promote(self, deploy_ref: str) -> DeployResult:
        raise NotImplementedError

    def rollback(self, site_id: str, to_build_hash: str) -> DeployResult:
        raise NotImplementedError

    def attach_domain(self, site_id: str, fqdn: str) -> DomainResult:
        raise NotImplementedError

    def logs(self, deploy_ref: str) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class LocalStaticDeploymentProvider(DeploymentProvider):
    """Copies immutable build output into a local preview directory.

    A separate static server can expose the generated directory during local development.
    The provider never mutates the source build output.
    """

    dist_root: Path
    name: str = "local_static"

    def create_preview(self, bundle: BuildBundle) -> DeployResult:
        _require_build_hash(bundle.build_hash)
        source = bundle.output_dir.resolve()
        if not source.is_dir():
            raise FileNotFoundError(f"build output directory does not exist: {source}")
        if not (source / "index.html").is_file():
            raise ValueError("build output has no index.html")
        destination = publish_directory_atomically(source, self.dist_root / bundle.build_hash)
        index = destination / "index.html"
        url = "file:///" + quote(str(index).replace("\\", "/"), safe="/:")
        return DeployResult(self.name, bundle.build_hash, "preview_ready", url)

    def promote(self, deploy_ref: str) -> DeployResult:
        _require_build_hash(deploy_ref)
        path = (self.dist_root / deploy_ref / "index.html").resolve()
        if not is_complete_build_directory(path.parent):
            raise FileNotFoundError(f"preview build not found: {deploy_ref}")
        url = "file:///" + quote(str(path).replace("\\", "/"), safe="/:")
        return DeployResult(self.name, deploy_ref, "live", url)

    def rollback(self, site_id: str, to_build_hash: str) -> DeployResult:
        return self.promote(to_build_hash)

    def attach_domain(self, site_id: str, fqdn: str) -> DomainResult:
        if not fqdn or "." not in fqdn:
            raise ValueError("fqdn must be a valid domain name")
        return DomainResult(self.name, fqdn, "attached")

    def logs(self, deploy_ref: str) -> str:
        return f"local_static build={deploy_ref}"
