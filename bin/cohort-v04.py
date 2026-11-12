#!/usr/bin/env python3.13
"""Rebuild the paper-1 cohort from the pinned COVID-19 Forecast Hub commit.

Eligibility (v0.4): a forecast file counts for target week W (a Saturday) when its
forecast_date is the Sunday or the Monday that opens W. Under the Hub convention both
dates make W the "1 wk ahead" target_end_date. When both exist, the later (Monday) file
is used, matching the Hub ensemble's "latest submission by Monday" rule. Every selected
row must have location US, target "1 wk ahead inc death", type quantile, quantile 0.5
(compared numerically) and target_end_date W.

Usage:
  py bin/cohort-v04.py fetch-tree tree.json            # 2 GitHub API calls
  py bin/cohort-v04.py extract tree.json raw.json      # streams ~2.3 GB, run on a server
  py bin/cohort-v04.py convert raw.json papers/paper-1/data/cohort-v04.json

The extract step streams every eligible CSV, keeps only the selected rows, and recomputes
each file's git blob SHA-1 from the downloaded bytes. Stdlib only. It keeps no copy of the
raw files. The paper's extraction ran on a Linux server, not on the desktop.
"""
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from fractions import Fraction

COMMIT = "52f10b79f02af0af7940a0a9a02314a563c04569"
RAW = f"https://raw.githubusercontent.com/reichlab/covid19-forecast-hub/{COMMIT}/data-processed/"
WEEKS = ["2020-11-07", "2020-11-14", "2020-11-21", "2020-11-28",
         "2020-12-05", "2020-12-12", "2020-12-19", "2020-12-26"]


def plan(tree):
    opens = {}
    for w in WEEKS:
        sat = dt.date.fromisoformat(w)
        opens[str(sat - dt.timedelta(days=6))] = (w, 0)   # Sunday
        opens[str(sat - dt.timedelta(days=5))] = (w, 1)   # Monday
    chosen = {}
    for e in tree["tree"]:
        p = e["path"]
        if e["type"] != "blob" or p.count("/") != 1 or not p.endswith(".csv"):
            continue
        model, fname = p.split("/", 1)
        if fname[:10] not in opens or fname[11:-4] != model:
            continue
        w, rank = opens[fname[:10]]
        key = (model, w)
        if key not in chosen or rank > chosen[key][0]:
            chosen[key] = (rank, p, e["sha"], e["size"])
    return chosen


def fetch(model, week, path, sha, size):
    url = RAW + path
    h = hashlib.sha1()
    h.update(f"blob {size}\0".encode())
    found, rows_seen, hdr, buf = [], 0, None, b""
    req = urllib.request.Request(url, headers={"User-Agent": "research-client"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                h = hashlib.sha1(); h.update(f"blob {size}\0".encode())
                found, hdr, buf, rows_seen = [], None, b"", 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    h.update(chunk)
                    buf += chunk
                    *lines, buf = buf.split(b"\n")
                    for ln in lines:
                        s = ln.decode("utf-8", "replace").rstrip("\r")
                        if hdr is None:
                            hdr = [c.strip().strip('"') for c in s.split(",")]
                            ix = {k: hdr.index(k) for k in ("forecast_date", "target", "target_end_date",
                                                            "location", "type", "quantile", "value")}
                            continue
                        rows_seen += 1
                        if "US" not in s:
                            continue
                        c = [x.strip().strip('"') for x in s.split(",")]
                        if len(c) < len(hdr):
                            continue
                        if c[ix["location"]] != "US" or c[ix["target"]] != "1 wk ahead inc death":
                            continue
                        if c[ix["type"]] != "quantile":
                            continue
                        try:
                            if Fraction(c[ix["quantile"]]) != Fraction(1, 2):
                                continue
                        except (ValueError, ZeroDivisionError):
                            continue
                        found.append({"value": c[ix["value"]], "target_end_date": c[ix["target_end_date"]],
                                      "forecast_date": c[ix["forecast_date"]]})
                if buf:
                    pass  # trailing line without newline is handled below
            break
        except Exception as ex:  # noqa: BLE001
            err = repr(ex)
            if attempt == 3:
                return {"model": model, "week": week, "path": path, "error": err}
    # trailing partial line
    if buf.strip() and hdr is not None:
        c = [x.strip().strip('"') for x in buf.decode("utf-8", "replace").strip().split(",")]
        try:
            if (c[ix["location"]] == "US" and c[ix["target"]] == "1 wk ahead inc death"
                    and c[ix["type"]] == "quantile" and Fraction(c[ix["quantile"]]) == Fraction(1, 2)):
                found.append({"value": c[ix["value"]], "target_end_date": c[ix["target_end_date"]],
                              "forecast_date": c[ix["forecast_date"]]})
        except Exception:  # noqa: BLE001
            pass
    return {"model": model, "week": week, "path": path, "blob_sha_listed": sha,
            "blob_sha_computed": h.hexdigest(), "rows": rows_seen, "matches": found}


def extract(tree_path, out_path, prev_path=None):
    tree = json.load(open(tree_path, encoding="utf-8"))
    chosen = plan(tree)
    jobs = [(m, w, p, s, z) for (m, w), (_, p, s, z) in sorted(chosen.items())]
    keep = []
    if prev_path:   # rerun only files that produced no match last time
        prev = json.load(open(prev_path, encoding="utf-8"))["files"]
        keep = [f for f in prev if f.get("matches")]
        done = {f["path"] for f in keep}
        jobs = [j for j in jobs if j[2] not in done]
    print(f"files to stream: {len(jobs)}, MB {sum(j[4] for j in jobs) / 1e6:.1f}", flush=True)
    out = list(keep)
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch, *j) for j in jobs]
        for k, f in enumerate(cf.as_completed(futs), 1):
            out.append(f.result())
            if k % 25 == 0:
                print(f"{k}/{len(jobs)} done", flush=True)
    json.dump({"commit": COMMIT, "weeks": WEEKS, "rule": __doc__, "files": out},
              open(out_path, "w", encoding="utf-8"), indent=1, sort_keys=True)
    errs = [o for o in out if "error" in o]
    bad = [o for o in out if "error" not in o and o["blob_sha_listed"] != o["blob_sha_computed"]]
    print(f"done: {len(out)} files, {len(errs)} errors, {len(bad)} blob mismatches", flush=True)


def fetch_tree(out_path):
    api = "https://api.github.com/repos/reichlab/covid19-forecast-hub/git/trees/"
    hdr = {"User-Agent": "research-client", "Accept": "application/vnd.github+json"}
    top = json.load(urllib.request.urlopen(urllib.request.Request(api + COMMIT, headers=hdr), timeout=60))
    sha = next(e["sha"] for e in top["tree"] if e["path"] == "data-processed")
    sub = json.load(urllib.request.urlopen(urllib.request.Request(api + sha + "?recursive=1", headers=hdr), timeout=120))
    if sub.get("truncated"):
        raise SystemExit("tree listing truncated")
    json.dump(sub, open(out_path, "w", encoding="utf-8"))
    print(f"tree: {len(sub['tree'])} entries")


def convert(raw_path, out_path):
    d = json.load(open(raw_path, encoding="utf-8"))
    models = {}
    for f in d["files"]:
        ms = [x for x in f.get("matches", []) if x["target_end_date"] == f["week"]]
        models.setdefault(f["model"], {})[f["week"]] = {
            "path": "data-processed/" + f["path"], "blob_sha1": f.get("blob_sha_computed"),
            "blob_sha1_listed": f.get("blob_sha_listed"),
            "median": ms[0]["value"] if ms else None,
            "forecast_date": ms[0]["forecast_date"] if ms else None}
    out = {"schema": "fulcrum.paper1.cohort.v04", "commit": d["commit"], "weeks": d["weeks"],
           "target": "1 wk ahead inc death", "location": "US", "eligibility": (__doc__ or "").split("Usage:")[0].strip(),
           "models": {m: models[m] for m in sorted(models)}}
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=1, sort_keys=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch-tree":
        fetch_tree(sys.argv[2])
    elif cmd == "extract":
        extract(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "convert":
        convert(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
