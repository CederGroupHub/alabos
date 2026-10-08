"""Tests for the analysis Data API (``/api/data/analysis/...``) and the AnalysisView behind it."""

from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from flask import Flask

from alab_management.dashboard.lab_views import analysis_view, sample_view
from alab_management.dashboard.routes import data_api as analysis_routes
from alab_management.sample_view import analysis_view as analysis_view_module
from alab_management.sample_view.analysis_view import _stamp
from alab_management.sample_view.completed_sample_view import CompletedSampleView

ALAB_ONE_DATA = {
    "diffraction_results": {
        "logical_key": "aeris:sample.xrdml",
        "content_hash": "abc123",
        "sampleid_in_aeris": "sample",
    }
}
# Legacy GPSS shape kept only so pending still understands older configs in tests.
GPSS_DATA = {"xrd_measurement": {"xrdml": "<xrdMeasurements/>"}}
RESULT = {"status": "success", "params_hash": "h1"}


# The sources a lab declares in its config. Supplied here so the tests below name them without depending on a
# particular deployment's config file; `test_input_sources_come_from_the_config_file` covers the real read.
TEST_SOURCES = {
    "alab_one_diffraction": {
        "kind": "xrd",
        "field": "metadata.diffraction_results.logical_key",
        "description": "XRD measurement ref (logical_key) on the sample (alab_one)",
    },
    "gpss_xrdml": {
        "kind": "xrd",
        "field": "metadata.xrd_measurement.xrdml",
        "type": "string",
        "description": "legacy raw .xrdml text on the sample (alab-gpss)",
    },
}


# Captured before the autouse fixture replaces the module attribute, so the config test can call the real thing.
_read_sources_from_config = analysis_view_module.input_data_sources


@pytest.fixture(autouse=True)
def configured_sources(monkeypatch):
    """`routes/data_api.py` imports the name directly, so both bindings have to be replaced."""
    for module in (analysis_view_module, analysis_routes):
        monkeypatch.setattr(module, "input_data_sources", lambda: dict(TEST_SOURCES))


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(analysis_routes.data_api_bp)
    return app.test_client()


@pytest.fixture()
def samples():
    """Create samples on request and remove them (and their completed-DB copies) afterwards."""
    created: list[ObjectId] = []

    def make(name: str, metadata: dict) -> ObjectId:
        sample_id = sample_view.create_sample(name=name, metadata=metadata)
        created.append(sample_id)
        return sample_id

    yield make

    sample_view._sample_collection.delete_many({"_id": {"$in": created}})
    completed = analysis_view._completed_samples()
    if completed is not None:
        completed.delete_many({"_id": {"$in": created}})


@pytest.fixture()
def completed_view():
    """The completed-DB view, skipping the test when this deployment has no ``[mongodb_completed]`` section."""
    if analysis_view._completed_samples() is None:
        pytest.skip(
            "no [mongodb_completed] in the AlabOS config, so there is no completed database to mirror into"
        )
    return CompletedSampleView()


def _doc(sample_id: ObjectId) -> dict:
    return sample_view._sample_collection.find_one({"_id": sample_id})


def _pending_ids(client, **params) -> list[str]:
    query = {
        "kind": "xrd",
        "data_source": "alab_one_diffraction",
        "params_hash": "h1",
        **params,
    }
    response = client.get("/api/data/analysis/pending", query_string=query)
    assert response.status_code == 200, response.get_json()
    return [sample["sample_id"] for sample in response.get_json()["data"]["samples"]]


def test_pending_needs_input_data_and_a_stale_result(client, samples):
    no_data = samples("api_no_data", {})
    never_analyzed = samples("api_never_analyzed", ALAB_ONE_DATA)
    other_hash = samples(
        "api_other_hash",
        {
            **ALAB_ONE_DATA,
            "analysis": {"xrd": {"status": "success", "params_hash": "h0"}},
        },
    )
    fresh = samples("api_fresh", {**ALAB_ONE_DATA, "analysis": {"xrd": RESULT}})
    hand_written = samples(
        "api_hand_written",
        {**ALAB_ONE_DATA, "analysis": {"xrd": {"status": "success"}}},
    )
    errored = samples(
        "api_errored",
        {
            **ALAB_ONE_DATA,
            "analysis": {"xrd": {"status": "error", "params_hash": "h1"}},
        },
    )

    listed = _pending_ids(client, limit=500)
    assert str(never_analyzed) in listed
    assert str(other_hash) in listed
    assert str(no_data) not in listed
    assert str(fresh) not in listed
    assert str(hand_written) not in listed
    assert str(errored) not in listed

    assert str(errored) in _pending_ids(client, limit=500, include_errors="true")


def test_pending_input_data_location_is_per_lab(client, samples):
    alab_one = samples("api_src_alab_one", ALAB_ONE_DATA)
    gpss = samples("api_src_gpss", GPSS_DATA)

    assert str(alab_one) in _pending_ids(client, limit=500)
    assert str(gpss) not in _pending_ids(client, limit=500)

    gpss_listed = _pending_ids(client, limit=500, data_source="gpss_xrdml")
    assert str(gpss) in gpss_listed
    assert str(alab_one) not in gpss_listed


def test_pending_rejects_unknown_source_and_bad_kind(client):
    assert (
        client.get(
            "/api/data/analysis/pending",
            query_string={
                "kind": "xrd",
                "data_source": "somewhere_else",
                "params_hash": "h1",
            },
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/data/analysis/pending",
            query_string={
                "kind": "metadata.target",
                "data_source": "alab_one_diffraction",
                "params_hash": "h1",
            },
        ).status_code
        == 400
    )


def test_pending_returns_what_the_caller_needs_to_decide(client, samples):
    sample_id = samples(
        "api_pending_row",
        {**ALAB_ONE_DATA, "analysis_request": {"xrd": {"template_id": "spinel:abc"}}},
    )
    rows = client.get(
        "/api/data/analysis/pending",
        query_string={
            "kind": "xrd",
            "data_source": "alab_one_diffraction",
            "params_hash": "h1",
            "limit": 500,
        },
    ).get_json()["data"]["samples"]
    row = next(row for row in rows if row["sample_id"] == str(sample_id))
    assert row["name"] == "api_pending_row"
    assert row["analysis"] is None
    assert row["analysis_request"] == {"template_id": "spinel:abc"}
    assert row["claim"] is None


def test_write_result_is_additive(client, samples):
    sample_id = samples(
        "api_additive",
        {
            "target": "LiMnO2",
            **ALAB_ONE_DATA,
            "analysis": {"sem_eds": {"status": "success", "params_hash": "s1"}},
        },
    )
    response = client.post(
        f"/api/data/analysis/results/{sample_id}", json={"kind": "xrd", "result": RESULT}
    )
    assert response.status_code == 200
    metadata = _doc(sample_id)["metadata"]
    assert metadata["analysis"]["xrd"] == RESULT
    assert metadata["analysis"]["sem_eds"] == {"status": "success", "params_hash": "s1"}
    assert metadata["target"] == "LiMnO2"
    assert metadata["diffraction_results"]["logical_key"] == "aeris:sample.xrdml"


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "analysis.xrd", "result": {"ok": 1}},
        {"kind": "$xrd", "result": {"ok": 1}},
        {"kind": "2xrd", "result": {"ok": 1}},
        {"kind": "xrd", "result": ["not", "an", "object"]},
        {"kind": "xrd", "result": "not an object"},
        {"kind": "xrd", "result": None},
        {"kind": "xrd", "result": {}},
        {"kind": "xrd", "result": {"nested": {"a.b": 1}}},
        {"kind": "xrd", "result": {"$set": 1}},
    ],
)
def test_write_result_rejects_bad_kind_or_body(client, samples, body):
    sample_id = samples("api_reject", ALAB_ONE_DATA)
    response = client.post(f"/api/data/analysis/results/{sample_id}", json=body)
    assert response.status_code == 400
    assert _doc(sample_id)["metadata"].get("analysis") is None


def test_write_result_rejects_a_body_that_is_not_an_object(client, samples):
    sample_id = samples("api_reject_body", ALAB_ONE_DATA)
    assert (
        client.post(
            f"/api/data/analysis/results/{sample_id}", json=["kind", "xrd"]
        ).status_code
        == 400
    )


def test_a_sample_that_does_not_exist_is_404_not_a_claim_conflict(client):
    """A missing sample must not look like "someone else holds the claim"; every route says 404."""
    gone = ObjectId()
    claimed = client.post(
        f"/api/data/analysis/claim/{gone}", json={"kind": "xrd", "owner": "worker-1"}
    )
    assert claimed.status_code == 404

    released = client.post(
        f"/api/data/analysis/claim/{gone}/release", json={"kind": "xrd", "owner": "worker-1"}
    )
    assert released.status_code == 404

    unowned = client.post(
        f"/api/data/analysis/results/{gone}", json={"kind": "xrd", "result": RESULT}
    )
    assert unowned.status_code == 404
    owned = client.post(
        f"/api/data/analysis/results/{gone}",
        json={"kind": "xrd", "owner": "worker-1", "result": RESULT},
    )
    assert owned.status_code == 404


def test_an_unparseable_sample_id_is_400(client):
    assert (
        client.post(
            "/api/data/analysis/claim/not-an-objectid", json={"kind": "xrd", "owner": "w"}
        ).status_code
        == 400
    )


def test_claim_is_exclusive_and_hides_the_sample_from_pending(client, samples):
    sample_id = samples("api_claim", ALAB_ONE_DATA)

    first = client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-1"}
    )
    assert first.status_code == 200
    assert first.get_json()["data"]["claim"]["claimed_by"] == "worker-1"

    second = client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-2"}
    )
    assert second.status_code == 409
    assert second.get_json()["data"]["claim"]["claimed_by"] == "worker-1"

    assert str(sample_id) not in _pending_ids(client, limit=500, owner="worker-2")
    assert str(sample_id) in _pending_ids(client, limit=500, owner="worker-1")
    assert str(sample_id) in _pending_ids(client, limit=500, include_claimed="true")


def test_claim_and_release_need_an_owner(client, samples):
    sample_id = samples("api_no_owner", ALAB_ONE_DATA)
    assert (
        client.post(
            f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/data/analysis/claim/{sample_id}/release", json={"kind": "xrd"}
        ).status_code
        == 400
    )


def test_renewing_a_claim_is_the_same_call(client, samples):
    sample_id = samples("api_renew", ALAB_ONE_DATA)
    first = client.post(
        f"/api/data/analysis/claim/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1", "ttl_s": 60},
    ).get_json()["data"]["claim"]
    renewed = client.post(
        f"/api/data/analysis/claim/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1", "ttl_s": 600},
    )
    assert renewed.status_code == 200
    assert renewed.get_json()["data"]["claim"]["expires_at"] > first["expires_at"]


def _expire_claim(sample_id: ObjectId) -> None:
    """Make an existing claim look like one left behind by a worker that crashed."""
    past = _stamp(datetime.now(timezone.utc) - timedelta(seconds=10))
    sample_view._sample_collection.update_one(
        {"_id": sample_id}, {"$set": {"metadata.analysis_claims.xrd.expires_at": past}}
    )


def test_a_crashed_workers_claim_expires_on_its_own(client, samples):
    sample_id = samples("api_expiry", ALAB_ONE_DATA)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "dead-worker"}
    )
    _expire_claim(sample_id)

    assert str(sample_id) in _pending_ids(client, limit=500, owner="worker-2")
    taken_over = client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-2"}
    )
    assert taken_over.status_code == 200
    assert taken_over.get_json()["data"]["claim"]["claimed_by"] == "worker-2"


def test_claim_without_expires_at_still_expires(client, samples):
    """A claim document on the older shape, written by an analysis worker that predates ``expires_at``."""
    sample_id = samples("api_legacy_claim", ALAB_ONE_DATA)
    sample_view._sample_collection.update_one(
        {"_id": sample_id},
        {
            "$set": {
                "metadata.analysis_claims.xrd": {
                    "claimed_by": "legacy-worker",
                    "claimed_at": _stamp(
                        datetime.now(timezone.utc) - timedelta(days=1)
                    ),
                }
            }
        },
    )
    response = client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-2"}
    )
    assert response.status_code == 200


def test_release_frees_the_sample(client, samples):
    sample_id = samples("api_release", ALAB_ONE_DATA)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-1"}
    )

    released = client.post(
        f"/api/data/analysis/claim/{sample_id}/release",
        json={"kind": "xrd", "owner": "worker-1"},
    )
    assert released.status_code == 200
    assert released.get_json()["data"]["released"] is True
    assert _doc(sample_id)["metadata"].get("analysis_claims", {}).get("xrd") is None

    # releasing a claim someone else holds is reported, not an error
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-2"}
    )
    other = client.post(
        f"/api/data/analysis/claim/{sample_id}/release",
        json={"kind": "xrd", "owner": "worker-1"},
    )
    assert other.status_code == 200
    assert other.get_json()["data"]["released"] is False


def test_write_with_owner_needs_the_claim_and_releases_it(client, samples):
    sample_id = samples("api_write_claimed", ALAB_ONE_DATA)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-1"}
    )

    written = client.post(
        f"/api/data/analysis/results/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1", "result": RESULT},
    )
    assert written.status_code == 200
    assert written.get_json()["data"]["written"] is True
    metadata = _doc(sample_id)["metadata"]
    assert metadata["analysis"]["xrd"]["params_hash"] == "h1"
    assert metadata.get("analysis_claims", {}).get("xrd") is None


def test_write_is_discarded_when_the_claim_was_taken_over(client, samples):
    sample_id = samples("api_write_lost_claim", ALAB_ONE_DATA)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-1"}
    )
    _expire_claim(sample_id)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-2"}
    )

    lost = client.post(
        f"/api/data/analysis/results/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1", "result": RESULT},
    )
    assert lost.status_code == 409
    assert lost.get_json()["data"]["written"] is False
    assert _doc(sample_id)["metadata"].get("analysis") is None


def test_write_is_discarded_once_the_successor_released_the_claim(client, samples):
    """The overtaken worker must not overwrite a newer result even after the new holder has finished."""
    sample_id = samples("api_write_after_successor", ALAB_ONE_DATA)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-1"}
    )
    _expire_claim(sample_id)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-2"}
    )
    client.post(
        f"/api/data/analysis/results/{sample_id}",
        json={
            "kind": "xrd",
            "owner": "worker-2",
            "result": {"status": "success", "params_hash": "h2"},
        },
    )

    late = client.post(
        f"/api/data/analysis/results/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1", "result": RESULT},
    )
    assert late.status_code == 409
    assert _doc(sample_id)["metadata"]["analysis"]["xrd"]["params_hash"] == "h2"


def test_write_still_lands_when_the_lease_lapsed_and_nobody_took_over(client, samples):
    """Deliberate: the conditional write matches on the claim holder, not on ``expires_at``.

    A worker that overran its lease keeps its result as long as no other worker claimed the sample in the
    meantime. The claim is still cleared, so the sample is not left locked.
    """
    sample_id = samples("api_write_lapsed_lease", ALAB_ONE_DATA)
    client.post(
        f"/api/data/analysis/claim/{sample_id}", json={"kind": "xrd", "owner": "worker-1"}
    )
    _expire_claim(sample_id)

    written = client.post(
        f"/api/data/analysis/results/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1", "result": RESULT},
    )
    assert written.status_code == 200
    metadata = _doc(sample_id)["metadata"]
    assert metadata["analysis"]["xrd"]["params_hash"] == "h1"
    assert metadata.get("analysis_claims", {}).get("xrd") is None


def test_result_is_mirrored_into_the_completed_database(
    client, samples, completed_view
):
    archived = samples("api_mirror", ALAB_ONE_DATA)
    live_only = samples("api_no_mirror", ALAB_ONE_DATA)
    completed_view.save_sample(archived)

    mirrored_flags = {}
    for sample_id in (archived, live_only):
        response = client.post(
            f"/api/data/analysis/results/{sample_id}", json={"kind": "xrd", "result": RESULT}
        )
        assert response.status_code == 200
        mirrored_flags[sample_id] = response.get_json()["data"]["mirrored"]

    assert mirrored_flags[archived] is True
    assert mirrored_flags[live_only] is False

    mirrored = completed_view._completed_sample_collection.find_one({"_id": archived})
    assert mirrored["metadata"]["analysis"]["xrd"]["params_hash"] == "h1"
    # a sample that was never archived is not created in the completed database by a result write
    assert (
        completed_view._completed_sample_collection.find_one({"_id": live_only}) is None
    )


def test_mirror_can_be_turned_off_per_request(client, samples, completed_view):
    sample_id = samples("api_mirror_off", ALAB_ONE_DATA)
    completed_view.save_sample(sample_id)

    response = client.post(
        f"/api/data/analysis/results/{sample_id}",
        json={"kind": "xrd", "result": RESULT, "mirror_completed": False},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["mirrored"] is False
    mirrored = completed_view._completed_sample_collection.find_one({"_id": sample_id})
    assert mirrored["metadata"].get("analysis") is None


def test_token_check_is_off_by_default(client, samples):
    sample_id = samples("api_token_off", ALAB_ONE_DATA)
    assert (
        client.post(
            f"/api/data/analysis/claim/{sample_id}",
            json={"kind": "xrd", "owner": "worker-1"},
        ).status_code
        == 200
    )


def test_token_check_is_enforced_when_configured(client, samples, monkeypatch):
    sample_id = samples("api_token_on", ALAB_ONE_DATA)
    monkeypatch.setenv(analysis_routes.TOKEN_ENV, "s3cret-token")

    without = client.get(
        "/api/data/analysis/pending",
        query_string={
            "kind": "xrd",
            "data_source": "alab_one_diffraction",
            "params_hash": "h1",
        },
    )
    assert without.status_code == 401

    wrong = client.post(
        f"/api/data/analysis/claim/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1"},
        headers={analysis_routes.TOKEN_HEADER: "wrong-but-memorable"},
    )
    assert wrong.status_code == 401

    # the rejection must not tell the caller anything about the token, theirs or the server's
    for rejected in (without, wrong):
        body = rejected.get_data(as_text=True)
        assert "s3cret-token" not in body
        assert "wrong-but-memorable" not in body
        assert rejected.get_json()["errors"] == "missing or invalid API token"

    allowed = client.post(
        f"/api/data/analysis/claim/{sample_id}",
        json={"kind": "xrd", "owner": "worker-1"},
        headers={analysis_routes.TOKEN_HEADER: "s3cret-token"},
    )
    assert allowed.status_code == 200
    assert "s3cret-token" not in allowed.get_data(as_text=True)


def test_a_non_ascii_token_header_is_rejected_not_an_error(client, monkeypatch):
    """``hmac.compare_digest`` raises on non-ASCII ``str``, so the comparison must be done on bytes."""
    monkeypatch.setenv(analysis_routes.TOKEN_ENV, "s3cret-token")
    response = client.get(
        "/api/data/analysis/pending",
        query_string={
            "kind": "xrd",
            "data_source": "alab_one_diffraction",
            "params_hash": "h1",
        },
        headers={analysis_routes.TOKEN_HEADER: "s3cret-tokén"},
    )
    assert response.status_code == 401


def test_input_sources_come_from_the_config_file(tmp_path, monkeypatch):
    """The registry is per-deployment knowledge, so it is read from the AlabOS config, not from this source tree."""
    config = tmp_path / "alabos_config.toml"
    config.write_text(
        "[general]\nname = 'Scratch'\nworking_dir = '.'\n"
        "[data_api.input_sources.xrd_pattern]\n"
        "kind = 'xrd'\n"
        "field = 'metadata.xrd_measurement.xrdml'\n"
        "type = 'string'\n"
    )
    monkeypatch.setenv("ALABOS_CONFIG_PATH", str(config))
    # the real reader, not the one the autouse fixture substitutes for the rest of this file
    monkeypatch.setattr(analysis_view_module, "input_data_sources", _read_sources_from_config)

    assert _read_sources_from_config() == {
        "xrd_pattern": {"kind": "xrd", "field": "metadata.xrd_measurement.xrdml", "type": "string"}
    }
    assert analysis_view_module.data_source_query("xrd_pattern") == {
        "metadata.xrd_measurement.xrdml": {"$type": "string"}
    }
    with pytest.raises(ValueError, match="unknown data_source"):
        analysis_view_module.data_source_query("not_declared")


def test_a_source_without_a_type_is_an_existence_check(monkeypatch):
    monkeypatch.setattr(
        analysis_view_module, "input_data_sources",
        lambda: {"arrays": {"kind": "xrd", "field": "metadata.diffraction_results.twotheta.0"}},
    )
    assert analysis_view_module.data_source_query("arrays") == {
        "metadata.diffraction_results.twotheta.0": {"$exists": True}
    }


def test_data_sources_lists_the_configured_registry(client):
    response = client.get("/api/data/analysis/data-sources")
    assert response.status_code == 200
    names = [source["name"] for source in response.get_json()["data"]["data_sources"]]
    assert names == ["alab_one_diffraction", "gpss_xrdml"]
