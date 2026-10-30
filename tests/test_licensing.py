import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from bokin_suno import app as app_mod  # noqa: E402
from bokin_suno.cli import main  # noqa: E402
from tests.conftest import signed_key  # noqa: E402

TOKEN = "test-token"
pytestmark = pytest.mark.unlicensed


@pytest.fixture
def client(tmp_path):
    app = app_mod.create_app(TOKEN, tmp_path / "out", extra_hosts=("testserver",))
    return TestClient(app, headers={"X-Bokin-Token": TOKEN})


def test_locked_until_a_key_for_this_computer_is_activated(client, request):
    assert client.get("/").status_code == 200
    refused = client.get("/api/jobs")
    assert refused.status_code == 403 and refused.json()["license"] is True
    for free in ("/api/info", "/api/license", "/api/update"):
        assert client.get(free).status_code == 200, free
    view = client.get("/api/license").json()
    assert view["licensed"] is False and len(view["machine"]) == 19

    assert client.post("/api/license", json={"key": "BOKIN-NOT-A-KEY"}).status_code == 400
    assert client.post("/api/license", json={}).status_code == 400
    other_app = client.post("/api/license", json={"key": signed_key(request, ["fx"])})
    assert other_app.status_code == 400 and "Bokin FX" in other_app.json()["detail"]

    done = client.post("/api/license", json={"key": signed_key(request)})
    assert done.status_code == 200 and done.json()["licensed"] is True
    assert client.get("/api/jobs").status_code == 200


def test_a_bundle_key_opens_it_too(client, request):
    assert client.post("/api/license", json={"key": signed_key(request, ["fx", "suno-master"])}).status_code == 200
    assert client.get("/api/license").json()["products"] == ["Bokin FX", "Bokin Suno Master"]


def test_the_token_is_still_needed(client):
    anonymous = TestClient(client.app)
    assert anonymous.get("/api/license").status_code == 403
    assert anonymous.get("/api/ping").status_code == 200  # who is there: no token, nothing private


def test_command_line_refuses_too(tmp_path, capsys):
    import soundfile as sf

    from tests.conftest import SR, music

    sf.write(tmp_path / "a.wav", music(2.0), SR)
    with pytest.raises(SystemExit) as exc:
        main(["master", str(tmp_path / "a.wav"), "--out", str(tmp_path / "out")])
    assert "Machine code" in str(exc.value.code)
    assert not (tmp_path / "out").exists()
