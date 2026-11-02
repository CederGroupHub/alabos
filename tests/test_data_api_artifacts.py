"""Artifact routes for folder artifacts (one SEM sample is a folder, not a file)."""

from types import SimpleNamespace

import pytest
from bson import ObjectId
from flask import Flask

from alab_management.dashboard.routes import data_api

SAMPLE_ID = ObjectId()


@pytest.fixture()
def storage(tmp_path, monkeypatch):
    folder = tmp_path / "AppZr_163"
    (folder / "spectra").mkdir(parents=True)
    (folder / "ledger.json").write_text('{"spectra": []}')
    (folder / "spectra" / "1.msa").write_text("#FORMAT : EMSA/MAS")
    (tmp_path / "outside.txt").write_text("secret")
    (tmp_path / "scan.xrdml").write_text("<xrdMeasurements/>")

    doc = {
        "_id": SAMPLE_ID,
        "metadata": {
            "measurements": [
                {"kind": "sem_eds", "logical_key": "sem:AppZr_163", "content_hash": "h-sem"},
                {"kind": "xrd", "logical_key": "aeris:scan.xrdml", "content_hash": "h-xrd"},
            ]
        },
    }
    monkeypatch.setattr(data_api, "_find_sample_across_dbs", lambda _id: (doc, "working"))
    monkeypatch.setattr(data_api, "sample_view", SimpleNamespace(_sample_collection=SimpleNamespace(find_one=lambda q: doc)))
    monkeypatch.setattr(data_api, "resolve_logical_key", lambda key: (tmp_path / key.split(":", 1)[1]).resolve())
    return tmp_path


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(data_api.data_api_bp)
    return app.test_client()


def url(kind, **query):
    params = "&".join(f"{k}={v}" for k, v in query.items())
    return f"/api/data/samples/{SAMPLE_ID}/artifacts/{kind}" + (f"?{params}" if params else "")


def test_a_folder_artifact_lists_its_files(client, storage):
    response = client.get(url("sem_eds"))
    assert response.status_code == 200
    assert [f["path"] for f in response.get_json()["data"]["files"]] == ["ledger.json", "spectra/1.msa"]


def test_a_file_inside_a_folder_artifact_is_streamed(client, storage):
    response = client.get(url("sem_eds", path="spectra/1.msa"))
    assert response.status_code == 200
    assert response.data == b"#FORMAT : EMSA/MAS"


@pytest.mark.parametrize("member", ["../outside.txt", "/etc/passwd"])
def test_a_path_cannot_leave_the_folder(client, storage, member):
    assert client.get(url("sem_eds", path=member)).status_code == 400


def test_a_symlink_out_of_the_folder_is_refused(client, storage):
    (storage / "AppZr_163" / "link.txt").symlink_to(storage / "outside.txt")
    assert client.get(url("sem_eds", path="link.txt")).status_code == 400


def test_a_folder_artifact_by_hash(client, storage):
    response = client.get("/api/data/artifacts/by-hash/h-sem?path=ledger.json")
    assert response.status_code == 200
    assert response.headers["X-AlabOS-Sample-Id"] == str(SAMPLE_ID)


def test_a_missing_file_inside_the_folder_is_404(client, storage):
    assert client.get(url("sem_eds", path="nope.json")).status_code == 404


def test_a_file_artifact_is_unchanged_and_rejects_a_path(client, storage):
    assert client.get(url("xrd")).data == b"<xrdMeasurements/>"
    assert client.get(url("xrd", path="ledger.json")).status_code == 400
