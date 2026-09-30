import os
import subprocess
from pathlib import Path

import agency.services.site_build_service as build_module
from agency.services.site_build_service import _build_environment


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
