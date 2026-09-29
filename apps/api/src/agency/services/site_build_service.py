"""Create immutable site versions and execute the static template build."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact, BuildValidation, Site, SiteVersion
from agency.domain.claims_policy import assert_claims_allowed
from agency.domain.content_model import ContentModel
from agency.repositories import PipelineRepository
from agency.services.build_gate import (
    REQUIRED_CHECKS,
    ValidationResult,
    evaluate_build_gate,
)
from agency.services.pipeline_service import transition


class SiteBuildError(RuntimeError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[5]
TEMPLATE_ROOT = REPO_ROOT / "sites" / "_template-base"
BUILD_ROOT = REPO_ROOT / ".artifacts" / "builds"


def _build_hash(content: Artifact, design: Artifact) -> str:
    payload = (
        f"{content.id}:{content.schema_version}:"
        f"{design.payload_json.get('template_version')}:"
        f"{design.payload_json.get('design_preset_id')}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _strings(child)]
    return []


def _rows(org_id, site_version_id, checks: list[ValidationResult]) -> list[BuildValidation]:
    return [
        BuildValidation(
            org_id=org_id,
            site_version_id=site_version_id,
            check_name=item.check_name,
            passed=item.passed,
            detail_json={"detail": item.detail},
        )
        for item in checks
    ]


def _persist_build_bundle(build_hash: str) -> Path:
    source = TEMPLATE_ROOT / "out"
    if not source.is_dir():
        raise SiteBuildError("site build output directory does not exist")
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    destination = BUILD_ROOT / build_hash
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    return destination


_SECRET_ENV_MARKERS = ("API_KEY", "_TOKEN", "_SECRET", "PASSWORD", "_CREDENTIAL")


def _build_environment() -> dict[str, str]:
    """Give the static-site build only non-secret process configuration."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in _SECRET_ENV_MARKERS)
    }
    env["PRODUCTION_BUILD"] = "1"
    return env


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    detail = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, detail[-2000:]


def build_site(session: Session, *, org_id, client_id, content_artifact_id, design_artifact_id) -> SiteVersion:
    pipeline = PipelineRepository(session, org_id).latest_for_client(client_id)
    content = session.scalar(select(Artifact).where(
        Artifact.id == content_artifact_id,
        Artifact.org_id == org_id,
        Artifact.artifact_type == "content_model",
        Artifact.is_active.is_(True),
    ))
    design = session.scalar(select(Artifact).where(
        Artifact.id == design_artifact_id,
        Artifact.org_id == org_id,
        Artifact.artifact_type == "design_plan",
        Artifact.is_active.is_(True),
    ))
    if pipeline is None or pipeline.state != "DESIGN_APPROVED" or content is None or design is None:
        raise SiteBuildError("site is not ready for build")

    pipeline.state = transition(pipeline.state, "BUILDING").to_state
    site = session.scalar(select(Site).where(Site.org_id == org_id, Site.client_id == client_id))
    if site is None:
        site = Site(
            org_id=org_id,
            client_id=client_id,
            template_id="_template-base",
            design_preset_id=str(design.payload_json["design_preset_id"]),
        )
        session.add(site)
        session.flush()

    build_hash = _build_hash(content, design)
    version = SiteVersion(
        org_id=org_id,
        site_id=site.id,
        build_hash=build_hash,
        content_artifact_id=content.id,
        content_schema_version=content.schema_version,
        template_version=str(design.payload_json["template_version"]),
        design_preset_id=str(design.payload_json["design_preset_id"]),
    )
    session.add(version)
    session.flush()

    content_file = TEMPLATE_ROOT / f"content.generated.{client_id}.json"
    content_file.write_text(
        json.dumps(content.payload_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    env = _build_environment()
    env["CONTENT_FILE"] = content_file.name
    env["NEXT_PUBLIC_AGENCY_CLIENT_ID"] = str(client_id)
    env["NEXT_PUBLIC_AGENCY_SITE_ID"] = str(site.id)
    public_api_url = (
        env.get("NEXT_PUBLIC_AGENCY_LEAD_API_URL")
        or env.get("NEXT_PUBLIC_AGENCY_AGENT_API_URL")
        or env.get("AGENCY_PUBLIC_API_URL")
    )
    if public_api_url:
        lead_api_url = env.get("NEXT_PUBLIC_AGENCY_LEAD_API_URL") or public_api_url
        agent_api_url = env.get("NEXT_PUBLIC_AGENCY_AGENT_API_URL") or public_api_url
        env["NEXT_PUBLIC_AGENCY_LEAD_API_URL"] = lead_api_url.rstrip("/")
        env["NEXT_PUBLIC_AGENCY_AGENT_API_URL"] = agent_api_url.rstrip("/")
    try:
        passed_build, build_detail = _run(["npm", "run", "build:site"], cwd=REPO_ROOT, env=env)
    finally:
        content_file.unlink(missing_ok=True)

    legal_paths = {page.path for page in ContentModel.model_validate(content.payload_json).seo.pages}
    facts_source = session.scalar(select(Artifact).where(
        Artifact.id == content.input_artifact_id,
        Artifact.org_id == org_id,
        Artifact.artifact_type == "business_facts",
        Artifact.is_active.is_(True),
    ))
    facts_ok = facts_source is not None and facts_source.payload_json.get("client_id") == str(client_id)

    claim_texts = []
    for value in content.payload_json.values():
        if isinstance(value, (dict, list, str)):
            claim_texts.extend(_strings(value))
    try:
        assert_claims_allowed(claim_texts)
        claims_ok = True
        claims_detail = "claims policy passed"
    except ValueError as exc:
        claims_ok = False
        claims_detail = str(exc)

    checks = [
        ValidationResult("content_schema", passed_build, build_detail),
        ValidationResult(
            "facts_provenance",
            facts_ok,
            "content input_artifact_id resolves to approved business_facts",
        ),
        ValidationResult("claims_policy", claims_ok, claims_detail),
        ValidationResult(
            "required_legal_pages",
            {"/impressum", "/datenschutz"} <= legal_paths,
            "required legal SEO paths",
        ),
        ValidationResult("typecheck", passed_build, "covered by Next build"),
        ValidationResult("next_build", passed_build, build_detail),
    ]

    smoke_ok, smoke_detail = _run(["npm", "run", "qa:smoke"], cwd=REPO_ROOT, env=env)
    checks.extend([
        ValidationResult("linkcheck", smoke_ok, smoke_detail),
        ValidationResult("a11y_budget", smoke_ok, smoke_detail),
        ValidationResult("playwright_smoke", smoke_ok, smoke_detail),
    ])

    seo_ok, seo_detail = _run(["npm", "run", "validate:output"], cwd=REPO_ROOT, env=env)
    checks.append(ValidationResult("seo_manifest", seo_ok, seo_detail))

    perf_ok, perf_detail = _run(
        ["node", "scripts/lighthouse-check.mjs"],
        cwd=REPO_ROOT,
        env=env,
    )
    checks.append(ValidationResult("perf_budget", perf_ok, perf_detail))

    session.add_all(_rows(org_id, version.id, checks))
    try:
        evaluate_build_gate(checks)
    except Exception as exc:
        pipeline.state = transition("BUILDING", "BUILD_FAILED").to_state
        raise SiteBuildError(str(exc)) from exc

    try:
        _persist_build_bundle(build_hash)
    except Exception as exc:
        pipeline.state = transition("BUILDING", "BUILD_FAILED").to_state
        raise SiteBuildError(str(exc)) from exc

    build_artifact = Artifact(
        org_id=org_id,
        artifact_type="site_build",
        schema_version="1.0.0",
        payload_json={
            "client_id": str(client_id),
            "site_version_id": str(version.id),
            "build_hash": build_hash,
            "template_version": version.template_version,
            "design_preset_id": version.design_preset_id,
        },
        build_hash=build_hash,
        input_artifact_id=content.id,
        revision=1,
        is_active=True,
    )
    session.add(build_artifact)
    session.flush()

    site.current_build_hash = build_hash
    pipeline.state = transition(pipeline.state, "BUILD_COMPLETE").to_state
    pipeline.state = transition(pipeline.state, "PREVIEW_READY").to_state
    return version
