"""Bounded archive extraction. All arithmetic uses exact decimal-as-rational values."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def write_once(path, value):
    path = Path(path)
    body = canonical_bytes(value)
    if path.exists() and path.read_bytes() != body:
        raise ValueError(f'write-once conflict: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(body)
    return hashlib.sha256(body).hexdigest()


def source_identity(body):
    # Same Git-object identity convention as the preserved paper1_fixture harness.
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()}


def nonnegative(value):
    number = Fraction(value)
    if number < 0:
        raise ValueError('negative reported level')
    return number


def extract_median(text, origin, target_end):
    reader = csv.DictReader(io.StringIO(text))
    required = {'forecast_date', 'target', 'target_end_date', 'location', 'type', 'quantile', 'value'}
    if not required.issubset(reader.fieldnames or ()):
        raise ValueError('forecast schema mismatch')
    selected = []
    for row in reader:
        if (row['forecast_date'], row['target'], row['target_end_date'], row['location'], row['type']) != (origin, '1 wk ahead inc death', target_end, 'US', 'quantile'):
            continue
        if Fraction(row['quantile']) == Fraction(1, 2):
            selected.append(nonnegative(row['value']))
    if len(selected) != 1:
        raise ValueError(f'median count: {len(selected)}')
    return selected[0]


def weekly_values(text, weeks):
    ends = [date.fromisoformat(w) for w in weeks]
    if any(d.weekday() != 5 for d in ends):
        raise ValueError('target must be Saturday')
    selected_dates = {(end - timedelta(days=i)).isoformat() for end in ends for i in range(7)}
    reader = csv.DictReader(io.StringIO(text))
    if not {'date', 'location', 'value'}.issubset(reader.fieldnames or ()):
        raise ValueError('truth schema mismatch')
    daily = {}
    for row in reader:
        if row['location'] != 'US' or row['date'] not in selected_dates:
            continue
        if row['date'] in daily:
            raise ValueError('duplicate selected daily record')
        value = nonnegative(row['value'])
        if value.denominator != 1:
            raise ValueError('noninteger reported daily death count')
        daily[row['date']] = value
    result = {}
    for end in ends:
        keys = [(end - timedelta(days=i)).isoformat() for i in range(7)]
        present = [daily[key] for key in keys if key in daily]
        result[end.isoformat()] = ({'status': 'complete', 'days': 7, 'value': str(sum(present))}
                                  if len(present) == 7 else {'status': 'missing_days', 'days': len(present), 'missing': [k for k in keys if k not in daily]})
    return result
