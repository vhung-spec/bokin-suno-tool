import pytest


@pytest.fixture(autouse=True)
def studio_isolated(tmp_path, monkeypatch):
    """Every Bokin Suno Studio test: its own data and results folders, no browser window. The app counts as
    activated, except in tests marked `unlicensed` (tests/conftest.py gives those a test signing key)."""
    from bokin_studio import licensing

    monkeypatch.setenv("BOKIN_STUDIO_DATA", str(tmp_path / "studio-data"))
    monkeypatch.setenv("BOKIN_STUDIO_OUT", str(tmp_path / "studio-out"))
    monkeypatch.setattr(licensing, "_last", (0.0, None))
    yield
