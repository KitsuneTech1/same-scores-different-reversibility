#!/usr/bin/env python3.13
"""Extract the US daily incident-death rows for the paper-1 window from every version of the
Forecast Hub truth file, data-truth/truth-Incident Deaths.csv.

Usage:
  py bin/truth-vintages.py list out-commits.txt          # needs an authenticated `gh`
  py bin/truth-vintages.py extract commits.txt raw.json  # streams every version (~10 GB);
                                                           # the paper's run used a Linux server
Input lines: "<commit sha> <committer time ISO>". Only commits on or after 2020-11-01 are read.
For each version the script streams the whole CSV, keeps the rows with location US and a date
from 2020-11-01 to 2020-12-26, and records the git blob SHA-1 and SHA-256 of the bytes it read.
Stdlib only. It keeps no copy of the raw files.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import subprocess
import sys
import urllib.parse
import urllib.request

REPO = "reichlab/covid19-forecast-hub"
PATH = "data-truth/truth-Incident Deaths.csv"
FIRST, LAST = "2020-11-01", "2020-12-26"


def list_commits(out):
    q = urllib.parse.quote(PATH)
    res = subprocess.run(["gh", "api", "--paginate", f"repos/{REPO}/commits?path={q}&per_page=100",
                          "--jq", '.[] | .sha + " " + .commit.committer.date'],
                         capture_output=True, text=True, check=True)
    lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{len(lines)} commits")


def fetch(sha, when):
    url = f"https://raw.githubusercontent.com/{REPO}/{sha}/" + urllib.parse.quote(PATH)
    req = urllib.request.Request(url, headers={"User-Agent": "research-client"})
    last = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                size = int(r.headers.get("Content-Length", "0"))
                h1 = hashlib.sha1(f"blob {size}\0".encode()) if size else None
                h2 = hashlib.sha256()
                total, buf, hdr, rows, dup = 0, b"", None, {}, []
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                    h2.update(chunk)
                    if h1:
                        h1.update(chunk)
                    buf += chunk
                    *lines, buf = buf.split(b"\n")
                    for ln in lines:
                        s = ln.decode("utf-8", "replace").rstrip("\r")
                        if hdr is None:
                            hdr = [c.strip().strip('"') for c in s.split(",")]
                            ix = {k: hdr.index(k) for k in ("date", "location", "value")}
                            continue
                        if "US" not in s:
                            continue
                        c = [x.strip().strip('"') for x in s.split(",")]
                        if len(c) < len(hdr) or c[ix["location"]] != "US":
                            continue
                        d = c[ix["date"]]
                        if FIRST <= d <= LAST:
                            if d in rows:
                                dup.append(d)
                            rows[d] = c[ix["value"]]
                if buf.strip() and hdr is not None:
                    c = [x.strip().strip('"') for x in buf.decode("utf-8", "replace").split(",")]
                    if len(c) >= len(hdr) and c[ix["location"]] == "US" and FIRST <= c[ix["date"]] <= LAST:
                        rows[c[ix["date"]]] = c[ix["value"]]
            return {"commit": sha, "time": when, "bytes": total, "content_length": size,
                    "git_blob_sha1": h1.hexdigest() if h1 and total == size else None,
                    "sha256": h2.hexdigest(), "header": hdr, "us_rows": dict(sorted(rows.items())),
                    "duplicate_dates": dup}
        except Exception as ex:  # noqa: BLE001
            last = repr(ex)
    return {"commit": sha, "time": when, "error": last}


def fetch_lfs_tail(sha, when, tail=250_000):
    """From May 2022 the truth file is stored in Git LFS. Rows are sorted by location, then
    date, and "US" sorts after every numeric FIPS code, so the US block is the end of the file.
    Read the LFS pointer, then only the last `tail` bytes of the content by HTTP range, and
    require the US block to start at the first date of the series so it is complete."""
    q = urllib.parse.quote(PATH)
    hdrs = {"User-Agent": "research-client"}
    ptr = urllib.request.urlopen(urllib.request.Request(
        f"https://raw.githubusercontent.com/{REPO}/{sha}/{q}", headers=hdrs), timeout=60).read().decode()
    meta = dict(ln.split(" ", 1) for ln in ptr.strip().splitlines())
    size = int(meta["size"])
    req = urllib.request.Request(f"https://media.githubusercontent.com/media/{REPO}/{sha}/{q}",
                                 headers={**hdrs, "Range": f"bytes={size - tail}-{size - 1}"})
    data = urllib.request.urlopen(req, timeout=120).read()
    lines = data.decode("utf-8", "replace").split("\n")[1:]            # drop the partial first line
    us = [ln.split(",") for ln in lines if ln.split(",")[1:2] == ["US"]]
    before = [ln for ln in lines if ln and ln.split(",")[1:2] != ["US"]]
    if not us or us[0][0] != "2020-01-22" or not before:
        return {"commit": sha, "time": when, "error": "US block not fully inside the tail read"}
    rows = {c[0]: c[3] for c in us if FIRST <= c[0] <= LAST}
    return {"commit": sha, "time": when, "lfs_oid": meta["oid"], "lfs_size": size,
            "read": f"last {tail} bytes by HTTP range", "header": ["date", "location", "location_name", "value"],
            "us_first_date": us[0][0], "us_last_date": us[-1][0], "us_rows": dict(sorted(rows.items())),
            "duplicate_dates": []}


def fix_lfs(raw):
    d = json.load(open(raw, encoding="utf-8"))
    for i, v in enumerate(d["versions"]):
        if "error" in v:
            d["versions"][i] = fetch_lfs_tail(v["commit"], v["time"])
    json.dump(d, open(raw, "w", encoding="utf-8"), indent=1)
    print(f"errors left: {sum(1 for v in d['versions'] if 'error' in v)}")


def extract(commits_path, out):
    todo = []
    for ln in open(commits_path, encoding="utf-8"):
        parts = ln.split()
        if len(parts) == 2 and parts[1] >= FIRST:
            todo.append((parts[0], parts[1]))
    print(f"versions to stream: {len(todo)}", flush=True)
    res = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch, s, w) for s, w in todo]
        for k, f in enumerate(cf.as_completed(futs), 1):
            res.append(f.result())
            if k % 20 == 0:
                print(f"{k}/{len(todo)}", flush=True)
    res.sort(key=lambda r: (r["time"], r["commit"]))
    json.dump({"repo": REPO, "path": PATH, "window": [FIRST, LAST], "versions": res},
              open(out, "w", encoding="utf-8"), indent=1)
    errs = [r for r in res if "error" in r]
    print(f"done: {len(res)} versions, {len(errs)} errors, "
          f"{sum(r.get('bytes', 0) for r in res) / 1e9:.2f} GB streamed", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "list":
        list_commits(sys.argv[2])
    elif cmd == "extract":
        extract(sys.argv[2], sys.argv[3])
        fix_lfs(sys.argv[3])
    else:
        raise SystemExit(__doc__)
