"""Acquire frozen inputs, record whole-file access, and emit only selected rows."""
import argparse
import hashlib
import json
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from audit import extract_median, weekly_values, source_identity, write_once

ROOT = Path(__file__).resolve().parent


def record_exposure():
    manifest = json.loads((ROOT / 'acquisition.json').read_text())
    inventory = subprocess.check_output(['git', '-C', '/opt/dev/hub-metadata', 'cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], text=True)
    blobs = {parts[0]: int(parts[2]) for row in inventory.splitlines() if (parts := row.split())[1] == 'blob'}
    matches = [source['id'] for source in manifest['forecasts'] + manifest['truths'] if source['git_blob_sha1'] in blobs]
    correction = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'supersedes': 'acquisition.json status phrase before_csv_access applies only to explicit selected CSV parsing, not all byte retrieval', 'observation': 'Git metadata operations unexpectedly hydrated blob objects. They were not numerically inspected. Acquisition before all raw access is not established.', 'object_count': len(blobs), 'object_bytes': sum(blobs.values()), 'selected_blobs_already_present': matches, 'handling': 'Treat entire historical archive as exposed development material. No blinding, preregistration, or held-out predictive inference claim. Raw Git object store excluded from reviewer package.', 'prior_exposure': 'January 2021 engineering fixtures and later outcomes had already been viewed in earlier sessions; new freeze does not erase that history.', 'blob_inventory': blobs}
    print('EXPOSURE_SHA256', write_once(ROOT / 'exposure-correction.json', correction))
    print(json.dumps({k: correction[k] for k in ('object_count', 'object_bytes', 'selected_blobs_already_present')}, indent=2))


def acquire(source):
    cache = ROOT / '.cache'
    cache.mkdir(exist_ok=True)
    path = cache / (source['id'] + '.csv')
    receipt_path = ROOT / 'access' / (source['id'] + '.json')
    if path.exists():
        body = path.read_bytes()
        if not receipt_path.exists():
            raise ValueError('orphan cache has no access receipt')
        receipt = json.loads(receipt_path.read_text())
        if source_identity(body) != receipt['identity']:
            raise ValueError('cached source differs from access receipt')
    else:
        url = 'https://raw.githubusercontent.com/reichlab/covid19-forecast-hub/' + source['ref'] + '/' + urllib.parse.quote(source['path'])
        started = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(url, headers={'User-Agent': 'archive-methods-research'})
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
        receipt = {'id': source['id'], 'url': url, 'access_started_at': started, 'access_finished_at': datetime.now(timezone.utc).isoformat(), 'access_scope': 'entire CSV including out-of-selector rows', 'identity': source_identity(body)}
        if receipt['identity']['git_blob_sha1'] != source['git_blob_sha1']:
            raise ValueError('downloaded source blob mismatch')
        write_once(receipt_path, receipt)
        path.write_bytes(body)
    if receipt['identity']['git_blob_sha1'] != source['git_blob_sha1']:
        raise ValueError('manifest blob mismatch')
    return body.decode('utf-8-sig'), receipt['identity']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--record-exposure', action='store_true')
    args = parser.parse_args()
    if args.record_exposure:
        record_exposure()
        return
    if not (ROOT / 'exposure-correction.json').exists():
        raise ValueError('record known exposure before extracting data')
    manifest_body = (ROOT / 'acquisition.json').read_bytes()
    manifest = json.loads(manifest_body)
    forecasts, truths = [], []
    for source in manifest['forecasts']:
        text, identity = acquire(source)
        row = {'id': source['id'], 'model': source['model'], 'target_end': source['target_end'], 'identity': identity}
        try:
            row.update(status='included', median=str(extract_median(text, source['origin'], source['target_end'])))
        except ValueError as error:
            row.update(status='excluded', reason=str(error))
        forecasts.append(row)
        print(row['id'], row['status'], flush=True)
    for source in manifest['truths']:
        text, identity = acquire(source)
        row = {'id': source['id'], 'identity': identity, 'weeks': weekly_values(text, manifest['weeks'])}
        truths.append(row)
        print(row['id'], 'complete weeks', sum(w['status'] == 'complete' for w in row['weeks'].values()), flush=True)
    result = {'schema': 'fulcrum.paper1.extraction.v1', 'manifest_sha256': hashlib.sha256(manifest_body).hexdigest(), 'exposure_correction_sha256': hashlib.sha256((ROOT / 'exposure-correction.json').read_bytes()).hexdigest(), 'forecasts': forecasts, 'truths': truths}
    print('EXTRACTION_SHA256', write_once(ROOT / 'extraction.json', result))


if __name__ == '__main__':
    main()
