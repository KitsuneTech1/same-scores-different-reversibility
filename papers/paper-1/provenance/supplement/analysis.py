"""Descriptive, fixed-pair archive analysis. No prediction fitting or inference."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from audit import weekly_values, write_once
from prepare import api, TRUTH_PATH
from run_acquisition import acquire

ROOT = Path(__file__).resolve().parent
OUTCOME_REF = 'b276f442e33da33228bd97c393701221fa3a6273'


def compare(forecasts, truth):
    if len(forecasts) != 2 or not truth or any(len(v) != len(truth) for v in forecasts.values()):
        raise ValueError('two complete equal-length vectors required')
    scores = {model: sum(abs(x-y) for x,y in zip(values, truth)) / len(truth) for model, values in forecasts.items()}
    ranked = sorted(scores, key=scores.get)
    winner = ranked[0] if scores[ranked[0]] < scores[ranked[1]] else None
    gap = scores[ranked[1]] - scores[ranked[0]]
    return {'winner': winner, 'mae': {k: str(v) for k,v in scores.items()}, 'gap': str(gap), 'gap_cost_bound': str(len(truth)*gap/2)}


def paired_changes(records, weeks):
    pairs = []
    for old, new in zip(records, records[1:]):
        if any(record['weeks'][w]['status'] != 'complete' for record in (old, new) for w in weeks):
            continue
        delta = [Fraction(new['weeks'][w]['value']) - Fraction(old['weeks'][w]['value']) for w in weeks]
        pairs.append({'old': old['id'], 'new': new['id'], 'weeks': weeks, 'delta': list(map(str, delta)), 'l1_cost': str(sum(map(abs, delta)))})
    return pairs


def catalog_radius(forecasts, truth, initial_winner, scenarios):
    if initial_winner is None:
        return {'status': 'initial_tie', 'radius': None, 'ties': None}
    unique = sorted(set(tuple(vector) for vector in scenarios))
    results = []
    for delta in unique:
        revised = [x+d for x,d in zip(truth, delta)]
        if len(delta) != len(truth):
            raise ValueError('scenario dimension mismatch')
        if any(v < 0 for v in revised):
            results.append({'delta': list(map(str, delta)), 'status': 'excluded_negative_level'})
            continue
        ranking = compare(forecasts, revised)
        status = 'tie' if ranking['winner'] is None else ('reversal' if ranking['winner'] != initial_winner else 'same_winner')
        results.append({'delta': list(map(str, delta)), 'cost': str(sum(map(abs, delta))), 'status': status, 'ranking': ranking})
    reversing = [Fraction(row['cost']) for row in results if row['status'] == 'reversal']
    return {'status': 'attained_in_catalog' if reversing else 'no_reversal_in_catalog', 'radius': str(min(reversing)) if reversing else None, 'ties': sum(row['status'] == 'tie' for row in results), 'unique_scenarios': len(unique), 'scenarios': results}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze():
    if (ROOT / 'analysis-plan.json').exists():
        raise ValueError('analysis plan already frozen')
    acquisition = json.loads((ROOT / 'acquisition.json').read_text())
    extraction = json.loads((ROOT / 'extraction.json').read_text())
    if any(f['status'] != 'included' for f in extraction['forecasts']):
        raise ValueError('primary forecast coverage gate failed')
    common = [w for w in acquisition['weeks'] if all(t['weeks'][w]['status'] == 'complete' for t in extraction['truths'])]
    matches = api('commits?path=data-truth%2Ftruth-Incident%20Deaths.csv&until=2021-02-02T02%3A00%3A00Z&per_page=1')
    if len(matches) != 1 or matches[0]['sha'] != OUTCOME_REF:
        raise ValueError('outcome metadata selector changed')
    root = api('git/trees/' + OUTCOME_REF)
    truth_tree = next(item['sha'] for item in root['tree'] if item['path'] == 'data-truth')
    truth = api('git/trees/' + truth_tree)
    utils_tree = next(item['sha'] for item in truth['tree'] if item['path'] == 'truth_utils')
    utils = api('git/trees/' + utils_tree)
    if any(tree.get('truncated') for tree in (root, truth, utils)):
        raise ValueError('truncated metadata')
    producer = {item['path']: item['sha'] for item in truth['tree']}
    helpers = {item['path']: item['sha'] for item in utils['tree']}
    # Reviewed helper change only wraps visualization epidemiological week 54.
    # Daily truth is written before that visualization path; extraction is unchanged.
    if producer['get-truth-data.py'] != '6ba5076b6ebc2b299334bb7b00fe5f4b77b09a04' or helpers['_utils.py'] != 'f342403a1747da1fbc9afe76599b450997345df1':
        raise ValueError('outcome producer changed; inspect before extraction')
    source = {'id': 'truth-outcome-' + OUTCOME_REF[:12], 'path': TRUTH_PATH, 'ref': OUTCOME_REF, 'git_blob_sha1': producer['truth-Incident Deaths.csv'], 'git_time': matches[0]['commit']['committer']['date']}
    plan = {'schema': 'fulcrum.paper1.analysis.v1', 'frozen_at': datetime.now(timezone.utc).isoformat(), 'acquisition_sha256': digest(ROOT / 'acquisition.json'), 'extraction_sha256': digest(ROOT / 'extraction.json'), 'primary_weeks': acquisition['weeks'], 'secondary_weeks': common, 'secondary_status': 'post-extraction common-support sensitivity check; not a replacement primary cohort or confirmatory result', 'pair': ['CU-select', 'BPagano-RtDriven'], 'decision_truth_id': extraction['truths'][-1]['id'], 'scenario_rule': 'adjacent retained pre-cutoff vintage differences on identical record keys, only complete vectors; add zero and deduplicate; apply unchanged same-key vectors to decision truth as a historical replay stress assumption, not a validated revision distribution', 'box_rule': 'secondary only: symmetric coordinate widths equal maximum absolute adjacent complete revision per coordinate; continuous relaxation, not observed joint scenarios', 'cost': 'L1 sum of weekly reported-death changes; no scaling or inferred probabilities', 'outcome_source': source, 'outcome_rule': 'latest path commit by reported Git committer timestamp <=2021-02-02T02:00:00Z, from currently accessible repository history; release-relative later-vintage comparison, not proof of first publication within 28 days', 'reporting': 'fixed original model identities; initial winner chosen once by MAE, later ties distinct from reversals; all results descriptive; no predictors, p-values or confidence intervals; retain null results', 'contamination': 'all historical material treated as exposed development data; see exposure-correction.json'}
    print('ANALYSIS_PLAN_SHA256', write_once(ROOT / 'analysis-plan.json', plan))
    print(json.dumps({'primary_weeks': plan['primary_weeks'], 'secondary_weeks': common, 'outcome_source': source}, indent=2))


def acquire_outcome():
    plan = json.loads((ROOT / 'analysis-plan.json').read_text())
    text, identity = acquire(plan['outcome_source'])
    outcome = {'source': plan['outcome_source'], 'identity': identity, 'plan_sha256': digest(ROOT / 'analysis-plan.json'), 'weeks': weekly_values(text, plan['primary_weeks'])}
    print('OUTCOME_SHA256', write_once(ROOT / 'outcome.json', outcome))


def analyze():
    from exact import audit
    plan = json.loads((ROOT / 'analysis-plan.json').read_text())
    extraction = json.loads((ROOT / 'extraction.json').read_text())
    outcome = json.loads((ROOT / 'outcome.json').read_text())
    if digest(ROOT / 'extraction.json') != plan['extraction_sha256'] or digest(ROOT / 'analysis-plan.json') != outcome['plan_sha256']:
        raise ValueError('frozen artifact mismatch')
    groups = {}
    for label, weeks in (('primary', plan['primary_weeks']), ('common_support', plan['secondary_weeks'])):
        forecasts = {model: [Fraction(next(f['median'] for f in extraction['forecasts'] if f['model']==model and f['target_end']==w)) for w in weeks] for model in plan['pair']}
        decision = next(t for t in extraction['truths'] if t['id'] == plan['decision_truth_id'])
        truth = [Fraction(decision['weeks'][w]['value']) for w in weeks]
        if any(outcome['weeks'][w]['status'] != 'complete' for w in weeks):
            raise ValueError('later outcome incomplete; must report missingness')
        later = [Fraction(outcome['weeks'][w]['value']) for w in weeks]
        initial, final = compare(forecasts, truth), compare(forecasts, later)
        pairs = paired_changes(extraction['truths'], weeks)
        vectors = [[Fraction(d) for d in pair['delta']] for pair in pairs]
        catalog = catalog_radius(forecasts, truth, initial['winner'], [[Fraction()] * len(weeks), *vectors])
        endpoint = 'tie' if final['winner'] is None else ('initial_tie' if initial['winner'] is None else ('reversal' if final['winner'] != initial['winner'] else 'same_winner'))
        group = {'weeks': weeks, 'n': len(weeks), 'forecasts': {m: list(map(str, v)) for m,v in forecasts.items()}, 'decision_truth': list(map(str, truth)), 'later_truth': list(map(str, later)), 'initial': initial, 'later': final, 'later_status': endpoint, 'observed_later_delta': list(map(str, [b-a for a,b in zip(truth,later)])), 'observed_later_l1': str(sum(abs(b-a) for a,b in zip(truth,later))), 'adjacent_pairs': pairs, 'catalog': catalog}
        if label == 'common_support':
            widths = [max([abs(v[i]) for v in vectors], default=Fraction()) for i in range(len(weeks))]
            result = audit(forecasts[plan['pair'][0]], forecasts[plan['pair'][1]], truth, [-v for v in widths], widths)
            group['box'] = {'widths': list(map(str, widths)), 'maximum_l1': str(sum(widths)), 'strict_status': result.strict.status, 'strict_radius': None if result.strict.radius is None else str(result.strict.radius), 'tie_status': result.tie.status, 'tie_radius': None if result.tie.radius is None else str(result.tie.radius), 'gap_bound_alone_excludes_strict_reversal': sum(widths) <= Fraction(initial['gap_cost_bound'])}
        groups[label] = group
    output = {'schema': 'fulcrum.paper1.results.v1', 'plan_sha256': digest(ROOT / 'analysis-plan.json'), 'extraction_sha256': digest(ROOT / 'extraction.json'), 'outcome_sha256': digest(ROOT / 'outcome.json'), 'source_hashes': {p.name: digest(p) for p in sorted(ROOT.glob('*.py'))}, 'groups': groups}
    print('RESULTS_SHA256', write_once(ROOT / 'results.json', output))
    print(json.dumps({k:{'initial':v['initial'], 'later':v['later'], 'later_status':v['later_status'], 'later_l1':v['observed_later_l1'], 'catalog_status':v['catalog']['status'], 'scenarios':v['catalog']['unique_scenarios'], 'box':v.get('box')} for k,v in groups.items()}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'acquire-outcome', 'analyze'])
    {'freeze': freeze, 'acquire-outcome': acquire_outcome, 'analyze': analyze}[parser.parse_args().action]()
