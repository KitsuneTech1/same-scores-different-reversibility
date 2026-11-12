"""Opt-in cache re-acquisition for frozen Paper 1 sources.

Importing this module performs no network access. The CLI downloads complete CSV
objects only when a pinned cache entry is absent, and never changes receipts or
frozen analysis artifacts.
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

from audit import source_identity


ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 120


class ValidationError(ValueError):
    pass


def load(root, name):
    return json.loads((root / name).read_text())


def validate_blob(source, receipt, emitted, body):
    identity = source_identity(body)
    if receipt.get("id") != source.get("id"):
        raise ValidationError("receipt id mismatch")
    if identity != receipt.get("identity"):
        raise ValidationError("receipt identity mismatch")
    if identity.get("git_blob_sha1") != source.get("git_blob_sha1"):
        raise ValidationError("pinned blob mismatch")
    if emitted.get("identity") != identity:
        raise ValidationError("emitted identity mismatch")
    return identity


def source_url(source):
    return ("https://raw.githubusercontent.com/reichlab/covid19-forecast-hub/" +
            source["ref"] + "/" + urllib.parse.quote(source["path"], safe="/"))


def download(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": "paper1-replay-fetch"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_source(root, source, receipt, emitted, fetcher=download, timeout=TIMEOUT_SECONDS):
    root = Path(root)
    path = root / ".cache" / (source["id"] + ".csv")
    if path.exists():
        validate_blob(source, receipt, emitted, path.read_bytes())
        return "existing"
    body = fetcher(source_url(source), timeout)
    validate_blob(source, receipt, emitted, body)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValidationError(f"cache appeared during fetch: {path}")
    path.write_bytes(body)
    return "fetched"


def inventory(root):
    root = Path(root)
    acquisition = load(root, "acquisition.json")
    extraction = load(root, "extraction.json")
    plan = load(root, "analysis-plan.json")
    outcome = load(root, "outcome.json")
    forecast_emitted = {item["id"]: item for item in extraction["forecasts"]}
    truth_emitted = {item["id"]: item for item in extraction["truths"]}
    records = []
    for source in acquisition["forecasts"]:
        records.append((source, forecast_emitted[source["id"]]))
    for source in acquisition["truths"]:
        records.append((source, truth_emitted[source["id"]]))
    if outcome.get("source") != plan.get("outcome_source"):
        raise ValidationError("outcome source selector mismatch")
    records.append((plan["outcome_source"], outcome))
    return records


def fetch_all(root=ROOT, fetcher=download, timeout=TIMEOUT_SECONDS):
    root = Path(root)
    existing = fetched = 0
    total_bytes = 0
    for source, emitted in inventory(root):
        receipt = load(root / "access", source["id"] + ".json")
        total_bytes += receipt["identity"]["bytes"]
        action = fetch_source(root, source, receipt, emitted, fetcher, timeout)
        if action == "existing":
            existing += 1
        else:
            fetched += 1
    return {"sources": existing + fetched, "existing": existing, "fetched": fetched,
            "whole_csv_bytes": total_bytes}


def main():
    parser = argparse.ArgumentParser(description="opt-in complete-CSV cache re-acquisition")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        summary = fetch_all(args.root)
    except (OSError, UnicodeError, ValueError, urllib.error.URLError) as error:
        print(f"fetch validation failed: {error}")
        return 1
    mib = summary["whole_csv_bytes"] / (1024 * 1024)
    print(f"validated {summary['sources']} whole CSV sources: {summary['existing']} existing, "
          f"{summary['fetched']} fetched; full transfer set is about {mib:.0f} MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
