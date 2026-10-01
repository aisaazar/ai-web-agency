"""Vercel deployment provider for immutable static build bundles."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from agency.providers.deploy import BuildBundle, DeploymentProvider, DeployResult, DomainResult


class VercelDeploymentError(RuntimeError):
    """Raised when Vercel cannot create or promote a deployment."""


@dataclass(frozen=True)
class VercelDeploymentProvider(DeploymentProvider):
    name: str = "vercel"
    api_base: str = "https://api.vercel.com"
    timeout_seconds: float = 45.0
    max_files: int = 200
    max_bundle_bytes: int = 5_000_000
    ready_timeout_seconds: float = 120.0
    ready_poll_seconds: float = 2.0

    def _token(self) -> str:
        token = os.getenv("VERCEL_TOKEN")
        if not token:
            raise VercelDeploymentError("VERCEL_TOKEN is not configured")
        return token

    def _project_id(self) -> str:
        project_id = os.getenv("VERCEL_PROJECT_ID")
        if not project_id:
            raise VercelDeploymentError("VERCEL_PROJECT_ID is not configured")
        return project_id

    def _url(self, path: str) -> str:
        team_id = os.getenv("VERCEL_TEAM_ID")
        if not team_id:
            return f"{self.api_base}{path}"
        separator = "&" if "?" in path else "?"
        return f"{self.api_base}{path}{separator}teamId={quote(team_id)}"

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None
        headers = {"Authorization": f"Bearer {self._token()}"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self._url(path), data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(2_000_001)
        except HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise VercelDeploymentError(f"Vercel HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise VercelDeploymentError(f"Vercel request failed: {exc.reason}") from exc
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise VercelDeploymentError("Vercel returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise VercelDeploymentError("Vercel returned a non-object response")
        if "error" in data:
            raise VercelDeploymentError(str(data["error"]))
        return data

    def _wait_until_ready(self, deployment_id: str) -> dict:
        """Wait for Vercel to finish the staged deployment before exposing it to publish."""
        deadline = time.monotonic() + self.ready_timeout_seconds
        encoded = quote(deployment_id, safe="")
        while True:
            data = self._request("GET", f"/v13/deployments/{encoded}")
            state = str(data.get("readyState") or data.get("state") or "").upper()
            if state == "READY":
                return data
            if state in {"ERROR", "CANCELED", "DELETED"}:
                raise VercelDeploymentError(
                    f"Vercel deployment {deployment_id} ended in {state.lower()} state"
                )
            if time.monotonic() >= deadline:
                raise VercelDeploymentError(
                    f"Vercel deployment {deployment_id} did not become ready within "
                    f"{self.ready_timeout_seconds:g}s"
                )
            time.sleep(self.ready_poll_seconds)

    @staticmethod
    def _safe_files(bundle: BuildBundle) -> list[tuple[str, Path]]:
        source = bundle.output_dir.resolve()
        if not source.is_dir():
            raise VercelDeploymentError(f"build output directory does not exist: {source}")
        files: list[tuple[str, Path]] = []
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            try:
                relative = resolved.relative_to(source)
            except ValueError as exc:
                raise VercelDeploymentError("build contains a file outside the bundle") from exc
            files.append((relative.as_posix(), resolved))
        return files

    def create_preview(self, bundle: BuildBundle) -> DeployResult:
        if re.fullmatch(r"[a-f0-9]{64}", bundle.build_hash) is None:
            raise VercelDeploymentError("build_hash must be a 64-character lowercase hex digest")
        files = self._safe_files(bundle)
        if not files:
            raise VercelDeploymentError("build bundle is empty")
        if len(files) > self.max_files:
            raise VercelDeploymentError(f"build contains more than {self.max_files} files")

        encoded_files = []
        total_bytes = 0
        for relative, path in files:
            data = path.read_bytes()
            total_bytes += len(data)
            if total_bytes > self.max_bundle_bytes:
                raise VercelDeploymentError(
                    f"build bundle exceeds {self.max_bundle_bytes} byte limit"
                )
            encoded_files.append({
                "file": relative,
                "data": base64.b64encode(data).decode("ascii"),
                "encoding": "base64",
            })

        project_id = self._project_id()
        project_name = os.getenv("VERCEL_PROJECT_NAME") or project_id
        response = self._request(
            "POST",
            "/v13/deployments",
            {
                "name": project_name,
                "project": project_id,
                "files": encoded_files,
                "meta": {"ai_web_agency_build_hash": bundle.build_hash},
            },
        )
        deployment_id = response.get("id")
        deployment_url = response.get("url")
        if not isinstance(deployment_id, str) or not deployment_id:
            raise VercelDeploymentError("Vercel deployment response has no id")
        if not isinstance(deployment_url, str) or not deployment_url:
            raise VercelDeploymentError("Vercel deployment response has no url")
        self._wait_until_ready(deployment_id)
        return DeployResult(
            self.name,
            deployment_id,
            "preview_ready",
            f"https://{deployment_url}" if not deployment_url.startswith("http") else deployment_url,
        )

    def promote(self, deploy_ref: str) -> DeployResult:
        project_id = self._project_id()
        if not deploy_ref.strip():
            raise VercelDeploymentError("deployment reference must not be empty")
        resolved_ref = deploy_ref.strip()
        if resolved_ref.startswith("http"):
            deployment = self._request("GET", f"/v13/deployments/{quote(resolved_ref, safe='')}")
            deployment_id = deployment.get("id")
            deployment_url = deployment.get("url")
            if not isinstance(deployment_id, str) or not deployment_id:
                raise VercelDeploymentError("Vercel deployment lookup returned no id")
            if not isinstance(deployment_url, str) or not deployment_url:
                raise VercelDeploymentError("Vercel deployment lookup returned no url")
            resolved_ref = deployment_id
            url = deployment_url if deployment_url.startswith("http") else f"https://{deployment_url}"
        else:
            url = f"https://{resolved_ref}.vercel.app"
        encoded = quote(resolved_ref, safe="")
        self._request("POST", f"/v10/projects/{project_id}/promote/{encoded}")
        return DeployResult(self.name, resolved_ref, "live", url)

    def rollback(self, site_id: str, to_build_hash: str) -> DeployResult:
        deployments = self._request(
            "GET",
            f"/v13/deployments?projectId={quote(self._project_id())}&limit=100",
        )
        items = deployments.get("deployments")
        if not isinstance(items, list):
            raise VercelDeploymentError("Vercel deployment list has no deployments")
        match = None
        for item in items:
            if not isinstance(item, dict):
                continue
            meta = item.get("meta") or {}
            if isinstance(meta, dict) and meta.get("ai_web_agency_build_hash") == to_build_hash:
                match = item
                break
        if not match:
            raise VercelDeploymentError(f"Vercel deployment for build {to_build_hash} not found")
        deployment_ref = match.get("id") or match.get("url")
        if not isinstance(deployment_ref, str):
            raise VercelDeploymentError("matched Vercel deployment has no reference")
        deployment_url = match.get("url")
        if not isinstance(deployment_url, str) or not deployment_url:
            raise VercelDeploymentError("matched Vercel deployment has no url")
        result = self.promote(deployment_ref)
        return DeployResult(
            self.name,
            result.deploy_ref,
            result.status,
            deployment_url if deployment_url.startswith("http") else f"https://{deployment_url}",
        )

    def attach_domain(self, site_id: str, fqdn: str) -> DomainResult:
        domain = fqdn.strip().lower().rstrip(".")
        if not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", domain):
            raise VercelDeploymentError("fqdn must be a valid DNS hostname")
        response = self._request(
            "POST",
            f"/v10/projects/{self._project_id()}/domains",
            {"name": domain},
        )
        configured = bool(response.get("verified"))
        return DomainResult(self.name, domain, "attached" if configured else "pending_verification")

    def logs(self, deploy_ref: str) -> str:
        encoded = quote(deploy_ref, safe="")
        data = self._request("GET", f"/v13/deployments/{encoded}")
        return f"vercel deployment={deploy_ref} readyState={data.get('readyState', 'unknown')}"
