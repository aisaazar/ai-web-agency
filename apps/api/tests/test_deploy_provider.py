import pytest

from agency.providers.deploy import BuildBundle, LocalStaticDeploymentProvider


def test_local_static_preview_copies_exact_bundle(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("hello", encoding="utf-8")
    provider = LocalStaticDeploymentProvider(tmp_path / "deploys")
    build_hash = "a" * 64

    result = provider.create_preview(BuildBundle(build_hash, source))

    assert result.deploy_ref == build_hash
    assert result.status == "preview_ready"
    assert (tmp_path / "deploys" / build_hash / "index.html").read_text(encoding="utf-8") == "hello"


def test_local_static_rejects_invalid_build_hash(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("hello", encoding="utf-8")
    provider = LocalStaticDeploymentProvider(tmp_path / "deploys")

    with pytest.raises(ValueError, match="64-character"):
        provider.create_preview(BuildBundle("not-a-hash", source))

def test_local_static_requires_index_html(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    provider = LocalStaticDeploymentProvider(tmp_path / "deploys")

    with pytest.raises(ValueError, match="index.html"):
        provider.create_preview(BuildBundle("b" * 64, source))


def test_local_static_promote_requires_preview(tmp_path):
    provider = LocalStaticDeploymentProvider(tmp_path / "deploys")

    with pytest.raises(FileNotFoundError, match="preview build"):
        provider.promote("c" * 64)
