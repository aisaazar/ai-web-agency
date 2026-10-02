import pytest

from agency.providers.deploy import (
    BUILD_COMPLETE_MARKER,
    BuildBundle,
    LocalStaticDeploymentProvider,
    is_complete_build_directory,
)


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


def test_local_static_promote_rejects_incomplete_build_directory(tmp_path):
    """A directory left behind by an interrupted copy must not be promotable.

    The copy used to happen straight into the published path, so a truncated tree still had an
    `index.html` and passed every existence check on its way to becoming the live site.
    """
    partial = tmp_path / "deploys" / ("d" * 64)
    partial.mkdir(parents=True)
    (partial / "index.html").write_text("half a site", encoding="utf-8")
    provider = LocalStaticDeploymentProvider(tmp_path / "deploys")

    with pytest.raises(FileNotFoundError, match="preview build"):
        provider.promote("d" * 64)


def test_local_static_promote_rejects_path_traversal_reference(tmp_path):
    """A build reference is a digest, never a caller-supplied path fragment."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "index.html").write_text("secret", encoding="utf-8")
    (outside / BUILD_COMPLETE_MARKER).write_text("ok\n", encoding="utf-8")
    provider = LocalStaticDeploymentProvider(tmp_path / "deploys")

    with pytest.raises(ValueError, match="64-character"):
        provider.promote("../outside")

    with pytest.raises(ValueError, match="64-character"):
        provider.rollback("site-1", "../outside")


def test_local_static_preview_is_publishable_after_copy(tmp_path):
    """The happy path still yields a complete, promotable preview directory."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("hello", encoding="utf-8")
    provider = LocalStaticDeploymentProvider(tmp_path / "deploys")
    build_hash = "e" * 64

    provider.create_preview(BuildBundle(build_hash, source))
    promoted = provider.promote(build_hash)

    assert promoted.status == "live"
    assert is_complete_build_directory(tmp_path / "deploys" / build_hash)
