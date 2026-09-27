"""Deployment provider contract and deterministic local-static implementation."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


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
        source = bundle.output_dir.resolve()
        if not source.is_dir():
            raise FileNotFoundError(f"build output directory does not exist: {source}")
        destination = (self.dist_root / bundle.build_hash).resolve()
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        index = destination / "index.html"
        if not index.is_file():
            raise ValueError("build output has no index.html")
        url = "file:///" + quote(str(index).replace("\\", "/"), safe="/:")
        return DeployResult(self.name, bundle.build_hash, "preview_ready", url)

    def promote(self, deploy_ref: str) -> DeployResult:
        path = (self.dist_root / deploy_ref / "index.html").resolve()
        if not path.is_file():
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
