"""Collapse replicate sample names and collate dosing + related-task info."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# AppZr_66_1 / Foo_12_3 -> AppZr_66 / Foo_12. Letter suffixes (BM, OldAluminaCru) stay.
NUMERIC_REPLICATE_SUFFIX = re.compile(r"^(.+_\d+)(?:_\d+)+$")


def canonical_sample_name(name: str | None) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    match = NUMERIC_REPLICATE_SUFFIX.match(raw)
    return match.group(1) if match else raw


def extract_actual_heating(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Return heating that actually ran (temperature log and/or recorded setpoint)."""
    heating = (metadata or {}).get("heating_results") or {}
    if not heating:
        return {}
    temps = (heating.get("temperature_log") or {}).get("temperature_celsius") or []
    if (
        not temps
        and heating.get("heating_temperature") is None
        and heating.get("heating_time") is None
    ):
        return {}
    if not temps and heating.get("heating_temperature") is None:
        return {}

    if temps:
        max_temp = max(float(temp) for temp in temps)
        max_temp = int(max_temp) if float(max_temp).is_integer() else max_temp
    else:
        max_temp = heating.get("heating_temperature")

    dwell_h = None
    if heating.get("heating_time") is not None:
        dwell_h = float(heating["heating_time"]) / 60.0
        if float(dwell_h).is_integer():
            dwell_h = int(dwell_h)

    return {
        "heating_temperature": max_temp,
        "dwell_hours": dwell_h,
        "heating_done": max_temp is not None,
    }


def powders_from_dosing(dosing: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for powder in (dosing or {}).get("Powders") or []:
        doses = powder.get("Doses") or []
        dose_masses = [
            dose.get("Mass")
            for dose in doses
            if isinstance(dose, dict) and isinstance(dose.get("Mass"), int | float)
        ]
        actual = sum(dose_masses) if dose_masses else None
        target = powder.get("TargetMass")
        delta = None
        if isinstance(target, int | float) and actual is not None:
            delta = actual - target
        rows.append(
            {
                "powder_name": powder.get("PowderName"),
                "target_mass": target,
                "actual_mass": actual,
                "delta_mass": delta,
                "dose_count": len(dose_masses),
                "dose_masses": dose_masses,
            }
        )
    return rows


def format_crucible(sub_rack: Any, position: Any) -> str | None:
    if sub_rack is None or position is None:
        return None
    match = re.search(r"([A-Za-z])\s*$", str(sub_rack))
    if not match:
        match = re.search(r"SubRack([A-Za-z])", str(sub_rack), re.I)
    if not match:
        return f"{sub_rack}{position}"
    return f"{match.group(1).upper()}{int(position)}"


def _sample_sort_ts(sample: dict[str, Any]) -> datetime:
    return sample.get("last_updated") or sample.get("created_at") or datetime.min


def sample_has_dosing(sample: dict[str, Any] | None) -> bool:
    """True when Labman dosing results are present on the sample document."""
    dosing = ((sample or {}).get("metadata") or {}).get("powderdosing_results") or {}
    return bool(dosing.get("Powders") or dosing.get("CruciblePosition") is not None)


def same_name_mongo_filter(canonical: str) -> dict[str, Any]:
    """Match canonical name and numeric replicates (AppZr_66, AppZr_66_1, ...)."""
    name = str(canonical or "").strip()
    if not name:
        return {"name": {"$in": []}}
    return {
        "$or": [
            {"name": name},
            {"name": {"$regex": f"^{re.escape(name)}_\\d+$"}},
        ]
    }


def choose_best_sample(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not samples:
        return None

    def score(sample: dict[str, Any]) -> tuple:
        metadata = sample.get("metadata") or {}
        powders = (metadata.get("powderdosing_results") or {}).get("Powders") or []
        heating = extract_actual_heating(metadata)
        return (
            1 if powders else 0,
            1 if heating.get("heating_done") else 0,
            _sample_sort_ts(sample),
        )

    return max(samples, key=score)


def enrich_groups_with_historical_dosing(
    groups: dict[str, list[dict[str, Any]]],
    historical_samples: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Attach older same-name samples that carry dosing into month-scoped groups.

    Re-submits (e.g. September Starting/Diffraction) create new sample IDs without
    ``powderdosing_results``. Dosing still lives on the earlier archived sample with
    the same collapsed name — fold those docs in so powders/crucible/mixing pot fill.
    """
    by_canonical: dict[str, list[dict[str, Any]]] = {}
    for sample in historical_samples:
        if not sample_has_dosing(sample):
            continue
        name = canonical_sample_name(sample.get("name"))
        if not name:
            continue
        by_canonical.setdefault(name, []).append(sample)

    for name, group in groups.items():
        if any(sample_has_dosing(sample) for sample in group):
            continue
        existing_ids = {str(sample["_id"]) for sample in group if sample.get("_id") is not None}
        for hist in by_canonical.get(name, []):
            hist_id = str(hist["_id"]) if hist.get("_id") is not None else ""
            if not hist_id or hist_id in existing_ids:
                continue
            group.append(hist)
            existing_ids.add(hist_id)
    return groups


def _dosing_from_tasks(sample_name: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    for task in tasks:
        if task.get("type") != "PowderDosing":
            continue
        results = ((task.get("result") or {}) if isinstance(task.get("result"), dict) else {})
        per_sample = results.get("results_per_sample") or {}
        if sample_name in per_sample and isinstance(per_sample[sample_name], dict):
            return per_sample[sample_name]
        for dosing in per_sample.values():
            if isinstance(dosing, dict) and dosing.get("Powders"):
                return dosing
    return {}


def _planned_heating(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    for task in tasks:
        if task.get("type") != "Heating":
            continue
        params = task.get("parameters") or {}
        return {
            "heating_temperature": params.get("heating_temperature"),
            "heating_time_min": params.get("heating_time"),
            "ramping_rate": params.get("ramping_rate"),
            "cooling_rate": params.get("cooling_rate"),
        }
    return {}


def build_sample_report_row(
    canonical: str,
    samples: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """One collapsed sample row: aliases, dosing actuals, heating, related tasks."""
    aliases = sorted({str(sample.get("name") or "") for sample in samples if sample.get("name")})
    sample_ids = [str(sample["_id"]) for sample in samples if sample.get("_id") is not None]
    best = choose_best_sample(samples) or {}
    metadata = best.get("metadata") or {}
    dosing = metadata.get("powderdosing_results") or {}
    if not (dosing.get("Powders") or dosing.get("CruciblePosition") is not None):
        dosing = _dosing_from_tasks(best.get("name") or canonical, tasks) or dosing

    powders = powders_from_dosing(dosing)
    heating = extract_actual_heating(metadata)
    planned = _planned_heating(tasks)
    if not heating.get("heating_done") and planned.get("heating_temperature") is not None:
        dwell = planned.get("heating_time_min")
        heating = {
            "heating_temperature": planned.get("heating_temperature"),
            "dwell_hours": (float(dwell) / 60.0) if dwell is not None else None,
            "heating_done": False,
            "heating_source": "Heating task parameters (planned)",
        }
    elif heating.get("heating_done"):
        heating["heating_source"] = "heating_results"
    else:
        heating["heating_source"] = None

    related = []
    seen = set()
    for task in sorted(tasks, key=lambda item: item.get("created_at") or datetime.min):
        task_id = str(task.get("_id") or "")
        if not task_id or task_id in seen:
            continue
        seen.add(task_id)
        related.append(
            {
                "task_id": task_id,
                "type": task.get("type"),
                "status": task.get("status"),
                "created_at": task.get("created_at"),
                "completed_at": task.get("completed_at"),
            }
        )

    target_masses = "\n".join(
        f"{row['powder_name'] or '?'} {'' if row['target_mass'] is None else row['target_mass']}".rstrip()
        for row in powders
    )
    actual_masses = "\n".join(
        f"{row['powder_name'] or '?'} {'' if row['actual_mass'] is None else row['actual_mass']}".rstrip()
        for row in powders
    )
    powder_summary = "; ".join(
        (
            f"{row['powder_name'] or '?'}"
            f" target={row['target_mass']}"
            f" actual={row['actual_mass']}"
        )
        for row in powders
    )
    task_summary = "; ".join(
        f"{item['type']}:{item['status']}" for item in related if item.get("type")
    )

    return {
        "name": canonical,
        "aliases": aliases,
        "sample_ids": sample_ids,
        "source_count": len(samples),
        "target": metadata.get("target"),
        "powders": powders,
        "target_masses": target_masses,
        "actual_masses": actual_masses,
        "powder_summary": powder_summary,
        "crucible": format_crucible(
            dosing.get("CrucibleSubRack"), dosing.get("CruciblePosition")
        ),
        "mixing_pot": dosing.get("MixingPotPosition"),
        "actual_transfer_mass": dosing.get("ActualTransferMass"),
        "heating_temperature": heating.get("heating_temperature"),
        "dwell_hours": heating.get("dwell_hours"),
        "heating_done": bool(heating.get("heating_done")),
        "heating_source": heating.get("heating_source"),
        "related_tasks": related,
        "task_summary": task_summary,
        "created_at": best.get("created_at"),
        "last_updated": best.get("last_updated"),
    }
