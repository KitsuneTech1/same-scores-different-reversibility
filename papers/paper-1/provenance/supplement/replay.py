"""Offline verifier for frozen Paper 1 acquisition and analysis artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from audit import extract_median, source_identity, weekly_values
from exact import audit as exact_audit


FROZEN_SOURCE_HASH_KEYS = {
    "analysis.py", "audit.py", "exact.py", "prepare.py", "run_acquisition.py",
    "test_analysis.py", "test_audit.py", "test_exact.py",
}


class VerificationError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(root, name):
    return json.loads((root / name).read_text())


def compare(forecasts, truth):
    scores = {model: sum(abs(x - y) for x, y in zip(values, truth)) / len(truth)
              for model, values in forecasts.items()}
    ranked = sorted(scores, key=scores.get)
    winner = ranked[0] if scores[ranked[0]] < scores[ranked[1]] else None
    gap = scores[ranked[1]] - scores[ranked[0]]
    return {"winner": winner, "mae": {key: str(value) for key, value in scores.items()},
            "gap": str(gap), "gap_cost_bound": str(len(truth) * gap / 2)}


def truth_vector(record, weeks):
    values = []
    for week in weeks:
        entry = record["weeks"][week]
        if entry["status"] != "complete":
            raise VerificationError(f"incomplete truth: {record['id']} {week}")
        values.append(Fraction(entry["value"]))
    return values


def paired_changes(records, weeks):
    pairs = []
    for old, new in zip(records, records[1:]):
        if any(item["weeks"][week]["status"] != "complete"
               for item in (old, new) for week in weeks):
            continue
        delta = [Fraction(new["weeks"][week]["value"]) - Fraction(old["weeks"][week]["value"])
                 for week in weeks]
        pairs.append({"old": old["id"], "new": new["id"], "weeks": weeks,
                      "delta": [str(value) for value in delta],
                      "l1_cost": str(sum(map(abs, delta)))})
    return pairs


def catalog(forecasts, truth, initial_winner, scenarios):
    unique = sorted(set(tuple(vector) for vector in scenarios))
    rows = []
    for delta in unique:
        revised = [value + change for value, change in zip(truth, delta)]
        if any(value < 0 for value in revised):
            rows.append({"delta": [str(value) for value in delta], "status": "excluded_negative_level"})
            continue
        ranking = compare(forecasts, revised)
        status = "tie" if ranking["winner"] is None else (
            "reversal" if ranking["winner"] != initial_winner else "same_winner")
        rows.append({"delta": [str(value) for value in delta],
                     "cost": str(sum(map(abs, delta))), "status": status, "ranking": ranking})
    reversing = [Fraction(row["cost"]) for row in rows if row["status"] == "reversal"]
    return {"status": "attained_in_catalog" if reversing else "no_reversal_in_catalog",
            "radius": str(min(reversing)) if reversing else None,
            "ties": sum(row["status"] == "tie" for row in rows),
            "unique_scenarios": len(unique), "scenarios": rows}


def check_group(group, extraction, outcome, plan):
    weeks = group["weeks"]
    pair = plan["pair"]
    forecasts = {}
    for model in pair:
        forecasts[model] = [Fraction(next(item["median"] for item in extraction["forecasts"]
                                           if item["model"] == model and item["target_end"] == week))
                            for week in weeks]
    decision = next(item for item in extraction["truths"] if item["id"] == plan["decision_truth_id"])
    truth = truth_vector(decision, weeks)
    later = truth_vector(outcome, weeks)
    initial, final = compare(forecasts, truth), compare(forecasts, later)
    if initial["winner"] is None:
        raise VerificationError("initial ties are unsupported for this fixed executed cohort")
    pairs = paired_changes(extraction["truths"], weeks)
    vectors = [[Fraction(value) for value in pair["delta"]] for pair in pairs]
    expected = {
        "weeks": weeks,
        "n": len(weeks),
        "forecasts": {model: [str(value) for value in values] for model, values in forecasts.items()},
        "decision_truth": [str(value) for value in truth],
        "later_truth": [str(value) for value in later],
        "initial": initial,
        "later": final,
        "later_status": ("tie" if final["winner"] is None else
                         ("reversal" if final["winner"] != initial["winner"] else "same_winner")),
        "observed_later_delta": [str(new - old) for old, new in zip(truth, later)],
        "observed_later_l1": str(sum(abs(new - old) for old, new in zip(truth, later))),
        "adjacent_pairs": pairs,
        "catalog": catalog(forecasts, truth, initial["winner"],
                           [[Fraction()] * len(weeks), *vectors]),
    }
    if group is not None and "box" in group:
        widths = [max([abs(vector[index]) for vector in vectors], default=Fraction())
                  for index in range(len(weeks))]
        result = exact_audit(forecasts[pair[0]], forecasts[pair[1]], truth,
                             [-value for value in widths], widths)
        expected["box"] = {
            "widths": [str(value) for value in widths], "maximum_l1": str(sum(widths)),
            "strict_status": result.strict.status,
            "strict_radius": None if result.strict.radius is None else str(result.strict.radius),
            "tie_status": result.tie.status,
            "tie_radius": None if result.tie.radius is None else str(result.tie.radius),
            "gap_bound_alone_excludes_strict_reversal": sum(widths) <= Fraction(initial["gap_cost_bound"]),
        }
    return expected


def raw_errors(root, acquisition, extraction, outcome, plan):
    errors = []
    forecast_index = {item["id"]: item for item in extraction["forecasts"]}
    truth_index = {item["id"]: item for item in extraction["truths"]}
    sources = [(item, forecast_index[item["id"]], "forecast") for item in acquisition["forecasts"]]
    sources += [(item, truth_index[item["id"]], "truth") for item in acquisition["truths"]]
    sources.append((plan["outcome_source"], outcome, "outcome"))
    for source, emitted, kind in sources:
        path = root / ".cache" / (source["id"] + ".csv")
        receipt_path = root / "access" / (source["id"] + ".json")
        try:
            body = path.read_bytes()
            receipt = json.loads(receipt_path.read_text())
            identity = source_identity(body)
            if identity != receipt.get("identity") or identity["git_blob_sha1"] != source["git_blob_sha1"]:
                raise VerificationError("cache or pinned blob identity mismatch")
            if receipt.get("id") != source["id"] or emitted.get("identity") != identity:
                raise VerificationError("receipt or emitted identity mismatch")
            text = body.decode("utf-8-sig")
            if kind == "forecast":
                median = str(extract_median(text, source["origin"], source["target_end"]))
                if emitted.get("status") != "included" or emitted.get("median") != median:
                    raise VerificationError("selected median mismatch")
            else:
                weeks = weekly_values(text, acquisition["weeks"])
                if emitted.get("weeks") != weeks:
                    raise VerificationError("weekly truth extraction mismatch")
        except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as error:
            errors.append(f"{source['id']}: {error}")
    return errors


def verify(root=Path(__file__).resolve().parent, verify_raw=False):
    root = Path(root)
    acquisition = load(root, "acquisition.json")
    extraction = load(root, "extraction.json")
    plan = load(root, "analysis-plan.json")
    outcome = load(root, "outcome.json")
    results = load(root, "results.json")
    links, groups, source_hashes = [], [], []
    if extraction.get("manifest_sha256") != digest(root / "acquisition.json"):
        links.append("extraction manifest hash")
    if extraction.get("exposure_correction_sha256") != digest(root / "exposure-correction.json"):
        links.append("extraction exposure-correction hash")
    if plan.get("acquisition_sha256") != digest(root / "acquisition.json"):
        links.append("plan acquisition hash")
    if plan.get("extraction_sha256") != digest(root / "extraction.json"):
        links.append("plan extraction hash")
    if outcome.get("plan_sha256") != digest(root / "analysis-plan.json"):
        links.append("outcome plan hash")
    if outcome.get("source") != plan.get("outcome_source"):
        links.append("outcome source selector")
    for name in ("plan_sha256", "extraction_sha256", "outcome_sha256"):
        target = {"plan_sha256": "analysis-plan.json", "extraction_sha256": "extraction.json",
                  "outcome_sha256": "outcome.json"}[name]
        if results.get(name) != digest(root / target):
            links.append(f"results {name}")
    frozen_source_hashes = results.get("source_hashes", {})
    if set(frozen_source_hashes) != FROZEN_SOURCE_HASH_KEYS:
        source_hashes.append("frozen source hash key set")
    for name, expected in frozen_source_hashes.items():
        try:
            if digest(root / name) != expected:
                source_hashes.append(name)
        except OSError:
            source_hashes.append(name)
    expected_group_weeks = {"primary": plan["primary_weeks"],
                            "common_support": plan["secondary_weeks"]}
    result_groups = results.get("groups", {})
    if set(result_groups) != set(expected_group_weeks):
        groups.append("group key set")
    for name, weeks in expected_group_weeks.items():
        if name not in result_groups:
            continue
        group = result_groups[name]
        if group.get("weeks") != weeks or group.get("n") != len(weeks):
            groups.append(f"{name} plan-bound weeks")
        try:
            expected = check_group(group, extraction, outcome, plan)
            for field, value in expected.items():
                if group.get(field) != value:
                    groups.append(f"{name} {field}")
        except (KeyError, StopIteration, ValueError) as error:
            groups.append(f"{name}: {error}")
    raw = raw_errors(root, acquisition, extraction, outcome, plan) if verify_raw else []
    summary = {"link_errors": links, "source_hash_errors": source_hashes,
               "group_errors": groups, "raw_errors": raw,
               "groups": sorted(result_groups), "raw_checked": verify_raw}
    if links or source_hashes or groups or raw:
        raise VerificationError(json.dumps(summary, sort_keys=True))
    return summary


def main():
    parser = argparse.ArgumentParser(description="verify frozen Paper 1 artifacts without network access")
    parser.add_argument("--verify-raw", action="store_true", help="also parse cached CSVs and receipts")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        summary = verify(args.root, args.verify_raw)
    except VerificationError as error:
        print(f"verification failed: {error}")
        return 1
    print("verified: links, source hashes, groups" + (", raw cache" if summary["raw_checked"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
