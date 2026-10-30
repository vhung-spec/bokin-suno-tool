import pytest

pytest.importorskip("uvicorn")


@pytest.mark.unlicensed
def test_the_built_apps_self_test_passes_from_source(capsys):
    from bokin_suno import selftest

    assert selftest.run() == 0
    out = capsys.readouterr().out
    assert "self-test passed" in out and "FAILED" not in out
    assert "a key for this computer activates the app" in out
