"""Freeze metadata and acquisition scope before any selected CSV is read."""
import hashlib
import json
import re
import subprocess
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from audit import write_once

ROOT = Path(__file__).resolve().parent
GIT = '/opt/dev/hub-metadata'
CUTOFF = '52f10b79f02af0af7940a0a9a02314a563c04569'
TRUTH_PATH = 'data-truth/truth-Incident Deaths.csv'
TRUTH_REFS = ['885931af4e0c65fa7a1b0bc1b01e99f06265285b', '5f052abd160a1d45c8b7402b7d65cadade11b96a', 'eefbf0e79039048138e9511b7e3a6489297e14a6', 'e4a9fe27c3c7d1393e15d8bb42baa8093b6d9636', 'ae770bdd7b5ddd22c7d7680f3504fd4690f55349', '80bf182e77a163ea142c48cefe99ab4558742ea9']


def git(*args):
    return subprocess.check_output(['git', '-C', GIT, *args], text=True).strip()


def blob(ref, path):
    row = git('ls-tree', ref, '--', path)
    if not row or row.split()[1] != 'blob':
        raise ValueError(f'missing blob: {ref} {path}')
    return row.split()[2]


def ancestor(old, new):
    subprocess.run(['git', '-C', GIT, 'merge-base', '--is-ancestor', old, new], check=True)


def api(path):
    request = urllib.request.Request('https://api.github.com/repos/reichlab/covid19-forecast-hub/' + path, headers={'User-Agent': 'archive-methods-research'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main():
    if (ROOT / 'acquisition.json').exists():
        raise ValueError('acquisition freeze already exists; do not regenerate')
    note = Path('/opt/dev/eligibility-note.md').read_text()
    matches = re.findall(r'`(data-processed/[^`]+\.csv)`; commit `([a-f0-9]{40})`.*?\[PR (\d+)\].*?merged ([0-9TZ:\-]+)', note)
    if len(matches) != 16:
        raise ValueError(f'expected 16 metadata receipts, got {len(matches)}')
    cutoff_pr = api('pulls/2510')
    if cutoff_pr['merge_commit_sha'] != CUTOFF or cutoff_pr['merged_at'] != '2021-01-05T01:57:23Z':
        raise ValueError('cutoff receipt changed')
    write_once(ROOT / 'metadata/cutoff-pr.json', {k: cutoff_pr[k] for k in ('number', 'html_url', 'merged_at', 'merge_commit_sha')})
    forecasts = []
    for path, ref, number, merged_at in matches:
        pr = api('pulls/' + number)
        if pr['merged_at'] != merged_at:
            raise ValueError('merge receipt mismatch')
        merge = pr['merge_commit_sha']
        ancestor(ref, merge)
        ancestor(merge, CUTOFF)
        object_id = blob(ref, path)
        if blob(merge, path) != object_id:
            raise ValueError(f'file not retained at own merge: {path}')
        origin = path.split('/')[-1][:10]
        end = (date.fromisoformat(origin) + timedelta(days=6)).isoformat()
        if not origin <= merged_at[:10] <= end:
            raise ValueError('merge outside target week')
        forecasts.append({'id': path.split('/')[1] + '-' + origin, 'model': path.split('/')[1], 'path': path, 'ref': ref, 'git_blob_sha1': object_id, 'origin': origin, 'target_end': end, 'merge_sha': merge, 'pr': int(number), 'merged_at': merged_at, 'cutoff_blob_same': blob(CUTOFF, path) == object_id})
        print('forecast metadata verified', path, flush=True)
    truths = []
    for index, ref in enumerate(TRUTH_REFS):
        ancestor(ref, CUTOFF)
        if index:
            ancestor(TRUTH_REFS[index - 1], ref)
        producers = {}
        for path in ('data-truth/get-truth-data.py', 'data-truth/truth_utils/_utils.py'):
            object_id = blob(ref, path)
            body = subprocess.check_output(['git', '-C', GIT, 'show', ref + ':' + path])
            target = ROOT / 'metadata' / (ref[:12] + '-' + Path(path).name)
            if target.exists() and target.read_bytes() != body:
                raise ValueError('producer evidence changed')
            target.write_bytes(body)
            producers[path] = {'git_blob_sha1': object_id, 'sha256': hashlib.sha256(body).hexdigest()}
        truths.append({'id': 'truth-' + ref[:12], 'ref': ref, 'path': TRUTH_PATH, 'git_blob_sha1': blob(ref, TRUTH_PATH), 'git_time': git('show', '-s', '--format=%cI', ref), 'available_by_receipt': cutoff_pr['merged_at'], 'receipt_class': 'reachable_historical_tree_in_public_merge_ancestry', 'producers': producers})
        print('truth metadata verified', ref, flush=True)
    manifest = {'schema': 'fulcrum.paper1.acquisition.v1', 'frozen_at': datetime.now(timezone.utc).isoformat(), 'status': 'acquisition_only_before_csv_access', 'cutoff_utc': '2021-01-05T02:00:00Z', 'cutoff_ref': CUTOFF, 'timing_claim': 'repository-receipt-backed retrospective audit, not first-publication reconstruction or ensemble-deadline compliance', 'forecast_rule': 'exact 0.5 quantile, US, 1 wk ahead inc death; original committed blob retained at own merge within target week', 'weeks': [(date(2020, 11, 7) + timedelta(days=7*i)).isoformat() for i in range(8)], 'truth_rule': 'seven unique daily US rows per Sunday-Saturday week; clipped reported levels; missing is not zero; signed cross-vintage differences', 'raw_access': 'whole CSV download is an access event; only selected rows emitted; no later outcome vintage in this manifest', 'forecasts': forecasts, 'truths': truths, 'rights': {'CU-select': 'Apache-2.0, retain source notices and license for redistribution', 'BPagano-RtDriven': 'CC-BY-4.0, Bob Pagano, retain attribution source and license', 'truth': 'JHU CSSE COVID-19 Data, CC-BY-4.0 declared, cited through Hub daily clipped product; raw datasets not in reviewer package'}}
    print('ACQUISITION_FREEZE_SHA256', write_once(ROOT / 'acquisition.json', manifest))


if __name__ == '__main__':
    main()
