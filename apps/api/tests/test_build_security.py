import os
import subprocess
from pathlib import Path

import pytest

import agency.services.site_build_service as build_module
from agency.providers.deploy import (
    BUILD_COMPLETE_MARKER,
    is_complete_build_directory,
    publish_directory_atomically,
)
from agency.services.site_build_service import _build_environment


def test_interrupted_bundle_copy_never_publishes_a_partial_directory(tmp_path, monkeypatch):
    """A copy that dies partway must not leave a directory that looks publishable.

    Before this guarantee the partial tree still contained `index.html`, so every downstream
    existence check passed and a truncated site could reach preview and then production.
    """
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("home", encoding="utf-8")
    destination = tmp_path / "deploys" / ("a" * 64)

    def exploding_copytree(*args, **kwargs):
        # Simulate a full disk / killed process: some files land, then the copy dies.
        staging = Path(args[1])
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "index.html").write_text("home", encoding="utf-8")
        raise OSError("no space left on device")

    monkeypatch.setattr("agency.providers.deploy.shutil.copytree", exploding_copytree)

    with pytest.raises(OSError):
        publish_directory_atomically(source, destination)

    assert not destination.exists(), "a partial build must never appear at the published path"
    assert not is_complete_build_directory(destination)


def test_previous_build_survives_a_failed_republish(tmp_path, monkeypatch):
    """Rollback safety: a failed republish must leave the earlier build intact."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("new", encoding="utf-8")
    destination = tmp_path / "deploys" / ("a" * 64)
    publish_directory_atomically(source, destination)

    def boom(*args, **kwargs):
        raise OSError("interrupted")

    monkeypatch.setattr("agency.providers.deploy.shutil.copytree", boom)
    with pytest.raises(OSError):
        publish_directory_atomically(source, destination)

    assert (destination / "index.html").read_text(encoding="utf-8") == "new"
    assert is_complete_build_directory(destination), "the last good build must stay publishable"


def test_build_bundle_lifecycle_marks_completion(tmp_path, monkeypatch):
    template_root = tmp_path / "_template-base"
    out = template_root / "out"
    out.mkdir(parents=True)
    (out / "index.html").write_text("home", encoding="utf-8")
    builds = tmp_path / "builds"
    monkeypatch.setattr(build_module, "TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(build_module, "BUILD_ROOT", builds)

    stored = build_module._persist_build_bundle("b" * 64)

    assert is_complete_build_directory(stored)
    assert (stored / BUILD_COMPLETE_MARKER).is_file()


def test_persist_build_bundle_rejects_output_without_entry_page(tmp_path, monkeypatch):
    template_root = tmp_path / "_template-base"
    (template_root / "out").mkdir(parents=True)
    monkeypatch.setattr(build_module, "TEMPLATE_ROOT", template_root)
    monkeypatch.setattr(build_module, "BUILD_ROOT", tmp_path / "builds")

    with pytest.raises(build_module.SiteBuildError, match="index.html"):
        build_module._persist_build_bundle("c" * 64)
    assert not (tmp_path / "builds" / ("c" * 64)).exists()


def test_lock_budget_outlasts_the_commands_it_serializes():
    """A second client must not time out on a build that is still progressing normally."""
    assert build_module.BUILD_LOCK_TIMEOUT_SECONDS > (
        build_module.COMMAND_TIMEOUT_SECONDS * build_module.BUILD_COMMANDS_PER_BUILD
    )


def test_stale_export_directory_is_cleared_before_the_gates_read_it(tmp_path, monkeypatch):
    """A failed build must not leave the previous client's pages in `out/` for the gates.

    `next build` does not reliably clear the export directory when it fails. If a stale tree
    survived, the smoke/SEO/perf checks would run against another client's site and a failed
    build could still produce a publishable bundle.
    """
    template_root = tmp_path / "_template-base"
    stale = template_root / "out"
    stale.mkdir(parents=True)
    (stale / "index.html").write_text("previous client", encoding="utf-8")
    monkeypatch.setattr(build_module, "TEMPLATE_ROOT", template_root)

    seen: dict[str, bool] = {}

    def fake_run(command, *, cwd, env):
        # The stale tree must already be gone by the time the first build command is invoked.
        seen["out_exists"] = (template_root / "out").exists()
        raise AssertionError("stop after the pre-build cleanup")

    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "BUILD_ROOT", tmp_path / "builds")
    monkeypatch.setattr(build_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(build_module, "BUILD_LOCK_PATH", tmp_path / "build.lock")
    monkeypatch.setattr(build_module, "_serialize_template_build", lambda func: func)

    from agency.db import create_all, create_session_factory
    from agency.db.models import Artifact, Client, Org
    from agency.db.workflow_models import PipelineRun

    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    facts = Artifact(
        org_id=org.id, artifact_type="business_facts", schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []}, revision=1, is_active=True,
    )
    session.add(facts)
    session.flush()
    content = Artifact(
        org_id=org.id, artifact_type="content_model", schema_version="1.0.0",
        payload_json={"client_id": str(client.id)}, input_artifact_id=facts.id,
        revision=1, is_active=True,
    )
    design = Artifact(
        org_id=org.id, artifact_type="design_plan", schema_version="1.0.0",
        payload_json={
            "client_id": str(client.id), "template_version": "1.0.0",
            "design_preset_id": "health",
        },
        revision=1, is_active=True,
    )
    session.add_all([content, design])
    session.flush()
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state="DESIGN_APPROVED"))
    session.commit()

    with pytest.raises(AssertionError):
        build_module.build_site(
            session,
            org_id=org.id,
            client_id=client.id,
            content_artifact_id=content.id,
            design_artifact_id=design.id,
        )

    assert seen["out_exists"] is False, (
        "the previous client's export output must not survive into the gates"
    )
    session.close()


def test_run_reports_timeout_as_a_diagnosable_failure(monkeypatch):
    def timeout_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"partially built")

    monkeypatch.setattr(build_module.subprocess, "run", timeout_run)

    ok, detail = build_module._run(["npm", "run", "build:site"], cwd=Path("."), env={})

    assert ok is False
    assert "timed out" in detail
    assert "build:site" in detail
    assert "partially built" in detail


def test_run_reports_timeout_with_no_output(monkeypatch):
    def timeout_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=None)

    monkeypatch.setattr(build_module.subprocess, "run", timeout_run)

    ok, detail = build_module._run(["npm", "run", "build:site"], cwd=Path("."), env={})

    assert ok is False
    assert "timed out" in detail


def test_run_reports_missing_interpreter_as_a_failure(monkeypatch):
    def missing_run(command, **kwargs):
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(build_module.subprocess, "run", missing_run)

    ok, detail = build_module._run(["npm", "run", "build:site"], cwd=Path("."), env={})

    assert ok is False
    assert "could not start" in detail


def test_run_reports_silent_nonzero_exit(monkeypatch):
    def silent_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, None, None)

    monkeypatch.setattr(build_module.subprocess, "run", silent_run)

    ok, detail = build_module._run(["npm", "run", "build:site"], cwd=Path("."), env={})

    assert ok is False
    assert "exited with code 1" in detail


def test_decode_stream_handles_bytes_text_and_none():
    assert build_module._decode_stream(None) == ""
    assert build_module._decode_stream(b"ok") == "ok"
    assert build_module._decode_stream("ok") == "ok"
    # A Windows console code page must not raise; undecodable bytes are replaced.
    assert build_module._decode_stream(b"Gr\xfc\xdfe") != ""


def test_static_build_environment_excludes_secret_like_variables(monkeypatch):
    monkeypatch.setenv("EXAMPLE_API_KEY", "synthetic-key")
    monkeypatch.setenv("EXAMPLE_TOKEN", "synthetic-token")
    monkeypatch.setenv("EXAMPLE_PASSWORD", "synthetic-password")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_AGENT_API_URL", "https://api.example.test")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_SITE_ID", "site-123")

    env = _build_environment()

    assert "EXAMPLE_API_KEY" not in env
    assert "EXAMPLE_TOKEN" not in env
    assert "EXAMPLE_PASSWORD" not in env
    assert env["NEXT_PUBLIC_AGENCY_AGENT_API_URL"] == "https://api.example.test"
    assert env["NEXT_PUBLIC_AGENCY_SITE_ID"] == "site-123"
    assert env["PRODUCTION_BUILD"] == "1"


def test_build_environment_keeps_runtime_tooling(monkeypatch):
    monkeypatch.setenv("PATH", "synthetic-path")

    env = _build_environment()

    assert env["PATH"] == "synthetic-path"
    assert "PRODUCTION_BUILD" in env


def test_build_environment_canonicalizes_windows_path_key(monkeypatch):
    # A raw Windows environment block is case-insensitive but keeps the spelling each writer
    # used. os.environ folds case on Windows, which is why the block is injected rather than
    # setenv'd: against the real os.environ this assertion holds with or without
    # canonicalization, so it would prove nothing.
    monkeypatch.setattr(os, "environ", {"Path": "C:/Windows/System32", "SYSTEMROOT": "C:/Windows"})

    env = _build_environment()

    path_keys = [key for key in env if key.casefold() == "path"]
    assert path_keys == ["PATH"]
    assert env["PATH"] == "C:/Windows/System32"


def test_build_environment_drops_conflicting_path_spellings(monkeypatch):
    monkeypatch.setattr(
        os,
        "environ",
        {
            "Path": "C:/Windows/System32",
            "PATH": "C:/Program Files/nodejs",
            "pATh": "C:/stray",
            "SYSTEMROOT": "C:/Windows",
        },
    )

    env = _build_environment()

    # One search path, canonical spelling, value taken from the block - never merged, never
    # dropped: two entries would let cmd.exe and Node resolve npm differently.
    assert [key for key in env if key.casefold() == "path"] == ["PATH"]
    assert env["PATH"] in {"C:/Windows/System32", "C:/Program Files/nodejs", "C:/stray"}
    assert env["SYSTEMROOT"] == "C:/Windows"


def test_run_uses_the_configured_npm_command(monkeypatch):
    captured = {}

    def fake_subprocess_run(command, **kwargs):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(build_module.subprocess, "run", fake_subprocess_run)

    ok, _ = build_module._run(
        ["npm", "run", "build:site"],
        cwd=Path("."),
        env={"PATH": "C:/Program Files/nodejs", "AGENCY_NPM_COMMAND": "C:/nodejs/npm.cmd"},
    )

    assert ok is True
    assert captured["command"] == ["C:/nodejs/npm.cmd", "run", "build:site"]
