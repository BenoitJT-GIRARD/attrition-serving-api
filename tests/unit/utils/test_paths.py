"""Where the project's files are, answered once.

Every path in this repository hangs off `utils/paths.py`. Three scripts and two modules used
to compute a root of their own, and one of them counted directories upward — which works from
a checkout and silently writes into `site-packages` from a wheel.
"""

from __future__ import annotations

import importlib

import pytest

from attrition_serving.utils import paths


def test_the_root_is_the_directory_that_holds_the_project_file() -> None:
    assert (paths.ROOT_DIR / "pyproject.toml").exists()
    assert paths.SRC_DIR.name == paths.PACKAGE == "attrition_serving"


def test_every_named_directory_hangs_off_that_root() -> None:
    named = (
        paths.TESTS_DIR,
        paths.SCRIPTS_DIR,
        paths.NOTEBOOKS_DIR,
        paths.DOCS_DIR,
        paths.IMAGES_DIR,
        paths.REPORTS_DIR,
        paths.FIGURES_DIR,
        paths.DATA_DIR,
        paths.MODELS_DIR,
        paths.VAR_DIR,
    )
    for path in named:
        assert paths.ROOT_DIR in path.parents


def test_an_explicit_override_wins_over_the_marker(monkeypatch, tmp_path) -> None:
    """A container mounts the project somewhere else, and says so with one variable."""
    monkeypatch.setenv(paths.ROOT_ENV, str(tmp_path))

    reloaded = importlib.reload(paths)
    try:
        assert reloaded.ROOT_DIR == tmp_path.resolve()
        assert reloaded.REPORTS_DIR == tmp_path.resolve() / "reports"
    finally:
        monkeypatch.delenv(paths.ROOT_ENV, raising=False)
        importlib.reload(paths)


def test_only_the_directories_a_run_writes_into_are_created(monkeypatch, tmp_path) -> None:
    """Reading is never a reason to create a directory: a missing input must fail loudly."""
    monkeypatch.setenv(paths.ROOT_ENV, str(tmp_path))
    reloaded = importlib.reload(paths)
    try:
        reloaded.ensure_dirs()

        assert reloaded.REPORTS_DIR.is_dir()
        assert reloaded.FIGURES_DIR.is_dir()
        assert reloaded.MODELS_DIR.is_dir()
        assert not reloaded.DATA_DIR.exists()
        assert not reloaded.NOTEBOOKS_DIR.exists()
    finally:
        monkeypatch.delenv(paths.ROOT_ENV, raising=False)
        importlib.reload(paths)


@pytest.mark.parametrize(
    ("name", "expected"),
    [("SRC_DIR", "src"), ("IMAGES_DIR", "docs"), ("FIGURES_DIR", "reports")],
)
def test_the_nested_directories_sit_where_the_vocabulary_says(name, expected) -> None:
    assert getattr(paths, name).parent.name == expected
