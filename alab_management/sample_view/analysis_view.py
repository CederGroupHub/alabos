"""Analysis results and analysis claims on samples: the one implementation behind the Data API.

This is the in-process half of decision D7/D9 in alab_one's ``docs/data-architecture.md``: an offline analysis
service consumes artifacts and writes its results back *through AlabOS* onto the sample, and the HTTP routes in
``alab_management/dashboard/routes/analysis.py`` are only an adapter over this class, so an in-process AlabOS
caller and a remote client go through the same rules.

What "one write path" does and does not mean here, spelled out because the distinction is exactly what a reviewer
should check:

- This class never builds a Mongo client of its own. Every write to the live database uses the collection handle
  of the ``SampleView`` the caller hands in.
- The unconditional result write (no ``owner``) goes through ``SampleView.update_sample_metadata``.
- The claim-conditional result write, and every claim operation, issue their own ``update_one`` on that same
  collection handle, because ``update_sample_metadata`` is unconditional and cannot express "only if I still hold
  the claim". They stamp ``last_updated`` the same way it does.
- ``_mirror_to_completed`` writes the *completed* database through ``CompletedSampleView``, which is a second
  collection the caller did not hand in, and is the one place this class reaches past the given ``SampleView``.

Three operations, matching what an analysis worker needs each cycle:

- ``pending_samples``  which samples have input data for a technique but no result matching my config
- ``claim`` / ``release``  so two workers never analyze the same sample (a crashed worker's claim expires on its own)
- ``write_result``  store ``metadata.analysis.<kind>`` additively, optionally only while still holding the claim

Both documents live under ``metadata``, side by side and never nested in each other::

    metadata.analysis.<kind>         = {...the result...}
    metadata.analysis_claims.<kind>  = {claimed_by, claimed_at, expires_at, ttl_s}
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId  # type: ignore

from alab_management.config import AlabOSConfig

from .sample_view import SampleView

ANALYSIS_FIELD = "analysis"
CLAIM_FIELD = "analysis_claims"
REQUEST_FIELD = "analysis_request"  # written by whoever submits the sample; passed back to the caller untouched

DEFAULT_CLAIM_TTL_S = 2 * 3600
MAX_CLAIM_TTL_S = 24 * 3600
DEFAULT_PENDING_LIMIT = 50
MAX_PENDING_LIMIT = 500

# A claim document written before ``expires_at`` existed (an analysis worker on the older shape writes only
# ``claimed_by`` / ``claimed_at``) is treated as expired this long after ``claimed_at``. Kept equal to
# ``DEFAULT_CLAIM_TTL_S`` so that a deployment running both shapes applies the same lease either way.
LEGACY_CLAIM_TTL_S = DEFAULT_CLAIM_TTL_S

# Where the input data for a technique lives. This is per-deployment knowledge -- which field a lab writes its
# patterns to is a fact about that lab, not about AlabOS -- so it comes from the config file, under
# ``[data_api.input_sources.<name>]``:
#
#     [data_api.input_sources.xrd_pattern]
#     kind = "xrd"
#     field = "metadata.xrd_measurement.xrdml"
#     type = "string"                                  # optional; omit for a plain existence check
#     description = "raw .xrdml text on the sample"
#
# A source declares a *field path*, not a Mongo filter. The caller sends a name, AlabOS builds the query. Neither
# the HTTP client nor the config can hand in an arbitrary filter, which would be the same surface as handing out
# the Mongo connection string.
CONFIG_SECTION = "data_api"
INPUT_SOURCES_KEY = "input_sources"

_IDENTIFIER = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")


class SampleNotFoundError(ValueError):
    """No sample with the given id exists in the live database.

    A subclass of ``ValueError`` on purpose, so in-process code written against
    ``SampleView.update_sample_metadata`` -- which raises a plain ``ValueError`` for the same situation -- keeps
    working, while the HTTP adapter can still answer 404 instead of lumping it in with a validation error.
    """


def check_kind(kind: Any) -> str:
    """A ``kind`` becomes part of a Mongo field path, so only a plain identifier is accepted."""
    if not isinstance(kind, str) or not _IDENTIFIER.match(kind):
        raise ValueError(
            f"kind must be a plain identifier (letters, digits, underscore; not starting with a digit), got {kind!r}"
        )
    return kind


def check_result_document(result: Any) -> dict[str, Any]:
    """The stored result must be a non-empty JSON object whose keys are safe as Mongo field names."""
    if not isinstance(result, dict):
        raise ValueError(f"result must be a JSON object, got {type(result).__name__}")
    if not result:
        # An empty block would still read as "a result exists" to every reader, and carries no ``params_hash``,
        # so the sample would silently never be offered for this kind again.
        raise ValueError("result must not be an empty object")
    _check_keys(result, ANALYSIS_FIELD)
    return result


def _check_keys(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: object keys must be strings, got {key!r}")
            if "." in key or key.startswith("$"):
                raise ValueError(
                    f"{path}.{key}: keys must not contain '.' or start with '$'"
                )
            _check_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_keys(child, f"{path}[{index}]")


def input_data_sources() -> dict[str, dict[str, Any]]:
    """The configured sources, keyed by name, read fresh so a config edit needs no restart.

    Returns ``{}`` when the section is absent, which is the default: a deployment that has not declared where its
    patterns live gets no ``pending`` query rather than a guess.
    """
    try:
        section = AlabOSConfig().get(CONFIG_SECTION) or {}
    except FileNotFoundError:
        return {}
    sources = section.get(INPUT_SOURCES_KEY) or {}
    # The config is frozen into MappingProxyType, which is a Mapping but not a dict, so test for the former.
    return {
        name: dict(source)
        for name, source in sources.items()
        if isinstance(source, Mapping)
    }


def data_source_query(data_source: str) -> dict[str, Any]:
    """The query that says "this sample carries the input data for that source".

    Built here from the source's declared ``field`` (and optional BSON ``type``), so a config file cannot inject a
    filter: the worst a bad entry can do is name a field that matches nothing.
    """
    sources = input_data_sources()
    source = sources.get(data_source)
    if source is None:
        known = sorted(sources)
        raise ValueError(
            f"unknown data_source {data_source!r}; "
            + (f"configured sources: {known}" if known else
               f"no sources are configured under [{CONFIG_SECTION}.{INPUT_SOURCES_KEY}] in the AlabOS config")
        )
    field = source.get("field")
    if not isinstance(field, str) or not field:
        raise ValueError(f"data_source {data_source!r} declares no 'field' in the AlabOS config")
    bson_type = source.get("type")
    if bson_type is not None and not isinstance(bson_type, str):
        raise ValueError(f"data_source {data_source!r}: 'type' must be a string if given")
    return {field: {"$type": bson_type} if bson_type else {"$exists": True}}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    """Claim timestamps as fixed-width ISO-8601 UTC strings, so Mongo's string comparison orders them correctly.

    Fixed width is what makes ``$lte`` on ``expires_at`` work without a BSON date: the UTC offset is always
    ``+00:00`` and the fraction always six digits. Everything that writes a claim must use this, since a BSON
    ``Date`` would never compare equal-or-less against these strings.
    """
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds")


class AnalysisView:
    """Read and write the analysis blocks of samples through an existing ``SampleView``."""

    def __init__(self, sample_view: SampleView | None = None):
        self.sample_view = sample_view or SampleView()
        # Same collection handle the rest of AlabOS writes samples with; no second Mongo client here.
        self._samples = self.sample_view._sample_collection

    # ---- field paths ----

    @staticmethod
    def result_field(kind: str) -> str:
        """Field path of one kind's stored result."""
        return f"metadata.{ANALYSIS_FIELD}.{check_kind(kind)}"

    @staticmethod
    def claim_field(kind: str) -> str:
        """Field path of one kind's claim document."""
        return f"metadata.{CLAIM_FIELD}.{check_kind(kind)}"

    # ---- claims ----

    def _require_sample(self, sample_id: ObjectId) -> None:
        """Raise ``SampleNotFoundError`` if there is no such sample.

        Only ever called after an update matched nothing, so the happy path costs no extra query and the caller
        can still tell "another worker holds this" from "there is no such sample".
        """
        if self._samples.find_one({"_id": sample_id}, {"_id": 1}) is None:
            raise SampleNotFoundError(f"Cannot find sample with id: {sample_id}")

    def _claimable_query(self, kind: str, owner: str | None) -> dict[str, Any]:
        """A claim is available when nobody holds it, this owner already holds it, or it has expired.

        Expiry is a stored timestamp rather than a background cleaner, which is what makes a crashed worker's claim
        free itself: nothing has to notice the crash.
        """
        claim = self.claim_field(kind)
        now = _now()
        legacy_cutoff = _stamp(now - timedelta(seconds=LEGACY_CLAIM_TTL_S))
        clauses: list[dict[str, Any]] = [
            {claim: {"$exists": False}},
            {f"{claim}.expires_at": {"$lte": _stamp(now)}},
            # claims written before expires_at existed
            {
                f"{claim}.expires_at": {"$exists": False},
                f"{claim}.claimed_at": {"$lte": legacy_cutoff},
            },
        ]
        if owner is not None:
            clauses.insert(1, {f"{claim}.claimed_by": owner})
        return {"$or": clauses}

    def claim(
        self,
        sample_id: ObjectId,
        kind: str,
        owner: str,
        ttl_s: float = DEFAULT_CLAIM_TTL_S,
    ) -> dict[str, Any] | None:
        """Take (or renew) this kind's claim on one sample; ``None`` when another live worker holds it.

        Renewing is the same call from the same owner, so a heartbeat is just a repeat: there is no separate renew
        operation to get wrong, and a claim nobody renews expires at ``expires_at``. Raises
        ``SampleNotFoundError`` when there is no such sample, which is a different thing from losing the race.
        """
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("owner must be a non-empty string")
        if not 0 < ttl_s <= MAX_CLAIM_TTL_S:
            raise ValueError(f"ttl_s must be between 0 and {MAX_CLAIM_TTL_S} seconds")

        now = _now()
        claim = {
            "claimed_by": owner,
            "claimed_at": _stamp(now),
            "expires_at": _stamp(now + timedelta(seconds=ttl_s)),
            "ttl_s": ttl_s,
        }
        # One conditional update against one document. Mongo re-evaluates the filter while it holds that document,
        # so of two workers racing for an unclaimed sample exactly one update matches; the loser's filter no longer
        # holds by the time it runs and it matches nothing.
        taken = self._samples.update_one(
            {"$and": [{"_id": sample_id}, self._claimable_query(kind, owner)]},
            {"$set": {self.claim_field(kind): claim}},
        )
        if not taken.matched_count:
            self._require_sample(sample_id)
            return None
        return claim

    def release(self, sample_id: ObjectId, kind: str, owner: str) -> bool:
        """Drop this kind's claim if ``owner`` still holds it. False when it was already taken over."""
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("owner must be a non-empty string")
        claim = self.claim_field(kind)
        result = self._samples.update_one(
            {"_id": sample_id, f"{claim}.claimed_by": owner}, {"$unset": {claim: ""}}
        )
        if not result.matched_count:
            self._require_sample(sample_id)
            return False
        return True

    def get_claim(self, sample_id: ObjectId, kind: str) -> dict[str, Any] | None:
        """The claim document currently stored for this kind, if any."""
        doc = self._samples.find_one({"_id": sample_id}, {self.claim_field(kind): 1})
        return _at_path(doc, self.claim_field(kind))

    # ---- selection ----

    def pending_samples(
        self,
        kind: str,
        data_source: str,
        params_hash: str,
        limit: int = DEFAULT_PENDING_LIMIT,
        owner: str | None = None,
        include_errors: bool = False,
        include_claimed: bool = False,
    ) -> list[dict[str, Any]]:
        """Samples that carry ``data_source``'s input data but no result whose ``params_hash`` is the caller's.

        ``params_hash`` is the caller's own identifier for its analysis configuration; AlabOS only compares it for
        equality with what is stored, and never interprets it. A stored block without ``params_hash`` (a
        hand-written result) counts as fresh and is left alone. Errors are skipped unless ``include_errors``,
        because when to retry an error is the caller's policy, not AlabOS's.
        """
        field = self.result_field(kind)
        if not isinstance(params_hash, str) or not params_hash.strip():
            raise ValueError("params_hash must be a non-empty string")
        limit = max(1, min(int(limit), MAX_PENDING_LIMIT))

        stale: list[dict[str, Any]] = [
            {field: {"$exists": False}},
            {f"{field}.params_hash": {"$exists": True, "$ne": params_hash}},
        ]
        if include_errors:
            stale.append({f"{field}.status": "error"})

        query: dict[str, Any] = {
            "$and": [data_source_query(data_source), {"$or": stale}]
        }
        if not include_claimed:
            query["$and"].append(self._claimable_query(kind, owner))

        projection = {
            "name": 1,
            field: 1,
            self.claim_field(kind): 1,
            f"metadata.{REQUEST_FIELD}.{kind}": 1,
        }
        return [
            {
                "sample_id": str(doc["_id"]),
                "name": doc.get("name"),
                "analysis": _at_path(doc, field),
                "analysis_request": _at_path(doc, f"metadata.{REQUEST_FIELD}.{kind}"),
                "claim": _at_path(doc, self.claim_field(kind)),
            }
            for doc in self._samples.find(query, projection).sort("_id", 1).limit(limit)
        ]

    # ---- writing a result ----

    def write_result(
        self,
        sample_id: ObjectId,
        kind: str,
        result: dict[str, Any],
        owner: str | None = None,
        release_claim: bool = True,
        mirror_completed: bool = True,
    ) -> dict[str, Any]:
        """Store ``metadata.analysis.<kind>`` on one sample.

        Returns ``{"written": ..., "mirrored": ...}``. ``written`` is False only when ``owner`` was given and that
        owner no longer holds the claim; ``mirrored`` says whether the same key was also set on this sample's
        document in the completed database. ``SampleNotFoundError`` is raised when there is no such sample, on
        both paths.

        The write is additive: it replaces that one key and touches no other metadata. Without ``owner`` it goes
        through ``SampleView.update_sample_metadata``, which turns ``{"analysis.<kind>": ...}`` into a ``$set`` of
        the field path ``metadata.analysis.<kind>``.

        With ``owner`` the update is conditional, and it is worth being precise about what it checks: it matches on
        the claim's current *holder*, not on ``expires_at``. So a worker that overran its lease still stores its
        result when nobody took the sample over -- deliberate, because a finished analysis should not be discarded
        just because a lease lapsed -- while a worker whose claim was taken over, or whose successor has already
        released it, matches no claim and gets ``written: False``. The case this cannot defend against is a writer
        that passes no ``owner`` at all, since such a write opts out of claim arbitration by definition.
        """
        check_kind(kind)
        check_result_document(result)
        update = {f"{ANALYSIS_FIELD}.{kind}": result}

        if owner is None:
            try:
                self.sample_view.update_sample_metadata(sample_id, update)
            except ValueError:
                # ``update_sample_metadata`` raises a plain ValueError for a sample that does not exist; narrow it
                # so both write paths report a missing sample the same way, and let anything else through.
                self._require_sample(sample_id)
                raise
        else:
            claim = self.claim_field(kind)
            # Naive ``datetime.now()`` to match what ``update_sample_metadata`` stamps, not UTC-aware.
            change: dict[str, Any] = {
                "$set": {
                    self.result_field(kind): result,
                    "last_updated": datetime.now(),
                }
            }
            if release_claim:
                change["$unset"] = {claim: ""}
            written = self._samples.update_one(
                {"_id": sample_id, f"{claim}.claimed_by": owner}, change
            )
            if not written.matched_count:
                self._require_sample(sample_id)
                return {"written": False, "mirrored": False}

        mirrored = (
            self._mirror_to_completed(sample_id, update) if mirror_completed else False
        )
        return {"written": True, "mirrored": mirrored}

    def _mirror_to_completed(self, sample_id: ObjectId, update: dict[str, Any]) -> bool:
        """Copy the same metadata into ``Alab(completed)`` when the sample is already archived there.

        An experiment that finished before its analysis ran has been copied to the completed database, and readers
        such as the Data page prefer that copy, so a result written only to the live database would be invisible to
        them (and lost when the live document is pruned). This never creates a document there: archiving stays the
        archiver's job. It writes only the result key, so the archived copy's claim block, if the snapshot caught
        one, is left as it was.

        This is the one write in this class that does not use the given ``SampleView``'s collection, and a failure
        here is deliberately not swallowed: the live write has already landed, so the caller must see the error
        rather than believe both copies are in step.
        """
        completed = self._completed_samples()
        if completed is None:
            return False
        update_dict = {f"metadata.{key}": value for key, value in update.items()}
        update_dict["last_updated"] = datetime.now()
        return bool(
            completed.update_one(
                {"_id": sample_id}, {"$set": update_dict}
            ).matched_count
        )

    def _completed_samples(self):
        """The completed samples collection, or None when this deployment has no completed database."""
        if not hasattr(self, "_completed_collection"):
            try:
                from .completed_sample_view import CompletedSampleView

                self._completed_collection = (
                    CompletedSampleView()._completed_sample_collection
                )
            except (ValueError, KeyError):  # mongodb_completed not configured
                self._completed_collection = None
        return self._completed_collection


def _at_path(doc: dict[str, Any] | None, path: str) -> Any:
    """Follow a dotted field path into a Mongo document; None when any step is missing."""
    value: Any = doc
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value
