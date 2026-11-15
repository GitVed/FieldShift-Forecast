"""Model 2, Vedant. No Model 1 import or third-party dependencies.

Rules v1 (sources and limitations: docs/EVIDENCE.md, docs/MODEL2.md):
- evidence_only is the default: no calibrated weights, no overall percent.
- trial_yield_index (used by the API): overall = mean over crops with a trial
  yield of (trial yield / best trial yield for that crop) x 100. The best
  yields are read from the CSV, not hard-coded. Crops without a verified or
  derived yield (wheat) are left out and listed. No benefit or penalty terms.
  Soil carbon is reported as its own line, never folded into the score.
- sample_diversity is opt-in, entirely SAMPLE: benefit 10 points per extra
  cash-crop species; penalty 10 times same-crop transition fraction in the
  repeating cycle; clamp 0..100. Arbitrary UI weights, not research results.
- Cash-crop years weight the mean. Underseeded red clover adds no cash year.
- Use only VERIFIED bu/ac references with URLs. Never invent missing yields.
- Trial references already contain rotation effects: multiplier stays 1.
- Climate adjustment stays 1; trial references do not change with scenarios.
- Gross annual revenue requires every crop yield and dated CAD/bu price:
  sum(year yield * price) / cash-crop years. No partial total or profit.
"""
import argparse
import csv
import json
import math
from numbers import Real
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAL_CSV = ROOT / 'data/seed/harrow_trial_yields.csv'
PRICE_JSON = ROOT / 'data/seed/model2_prices.json'
CROP_ALIASES = {'maize': 'corn', 'soy': 'soybean'}
ROTATIONS = {
    'continuous soybean': ['soybean'],
    'soy-soy-wheat': ['soybean', 'soybean', 'wheat'],
    'corn-soy-wheat': ['corn', 'soybean', 'wheat'],
    'corn-soy-wheat plus red clover': ['corn', 'soybean', 'wheat'],
    'continuous corn': ['corn'],
    'corn-soy': ['corn', 'soybean'],
}
SAMPLE_SUITABILITY = {c: {'percent': p, 'source': 'SAMPLE fixture', 'label': 'SAMPLE'}
                      for c, p in [('wheat', 82), ('soybean', 88), ('maize', 71)]}


def _number(value, name, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(value) or value < 0
            or (maximum is not None and value > maximum)):
        raise ValueError(f'{name} must be a finite number in the permitted range')
    return float(value)


def _normalise(suitability):
    if not isinstance(suitability, dict):
        raise ValueError('suitability must be a crop dictionary')
    result = {}
    for crop, entry in suitability.items():
        name = CROP_ALIASES.get(crop, crop)
        if name in result:
            raise ValueError(f'Duplicate crop alias for {name}')
        if not isinstance(entry, dict):
            raise ValueError(f'{crop} must contain percent and source')
        entry = dict(entry)
        if entry.get('percent') is not None:
            entry['percent'] = _number(entry['percent'], crop, 100)
            if not isinstance(entry.get('source'), str) or not entry['source'].strip():
                raise ValueError(f'{crop} needs a source')
        result[name] = entry
    return result


def load_trial_yields(path=TRIAL_CSV):
    result = {}
    with open(path, encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            if row.get('verification') not in ('VERIFIED', 'DERIVED') or row.get('unit') != 'bu/ac':
                continue
            if not row.get('source', '').startswith(('https://', 'http://')):
                raise ValueError('Verified trial yield needs a source URL')
            key = (row['rotation'], CROP_ALIASES.get(row['crop'], row['crop']))
            if key in result:
                raise ValueError(f'Ambiguous trial references for {key}')
            result[key] = {
                'value': _number(float(row['value']), str(key)),
                'source': row['source'], 'period': row['period'],
                'note': row.get('note', ''), 'label': 'CACHED',
                'kind': 'observed trial reference, not predicted yield',
                'verification': row['verification'],
            }
    return result


def load_soil_lines(path=TRIAL_CSV):
    """{rotation: {"soc_pct": text, ...}} from verified soil organic carbon rows."""
    out = {}
    with open(path, encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            if row.get('crop') != 'soil organic carbon' or row.get('verification') != 'VERIFIED':
                continue
            entry = out.setdefault(row['rotation'], {'source': row['source'], 'period': row['period'],
                                                     'label': 'CACHED', 'items': []})
            if row.get('baseline'):
                entry['items'].append(f"plus {row['value']} percent vs {row['baseline']}")
            else:
                entry['items'].insert(0, f"{row['value']} percent soil organic carbon")
    for entry in out.values():
        entry['text'] = ', '.join(entry.pop('items')) + f" ({entry['period']})"
    return out


def trial_index(trial):
    """Best trial yield per crop and each rotation's gain over continuous cropping."""
    best, continuous = {}, {}
    for (rot, crop), ref in trial.items():
        if rot not in ROTATIONS:
            continue
        best[crop] = max(best.get(crop, 0.0), ref['value'])
        if ROTATIONS[rot] == [crop]:
            continuous[crop] = ref['value']
    return best, continuous


def load_prices(path=PRICE_JSON):
    with open(path, encoding='utf-8-sig') as handle:
        return json.load(handle)


def _revenue(crops, yields, prices):
    missing_yields = sorted({c for c in crops if not isinstance(yields[c], Real)})
    missing_prices = sorted({c for c in crops if c not in prices})
    detail = {'currency': 'CAD', 'unit': 'CAD/ac/year', 'kind': 'gross revenue, not profit',
              'missing_yields': missing_yields, 'missing_prices': missing_prices,
              'prices': {}, 'by_crop_year': [], 'label': 'CACHED'}
    for crop in dict.fromkeys(crops):
        price = prices.get(crop)
        if price is None:
            continue
        if (price.get('currency') != 'CAD' or price.get('unit') != 'CAD/bu'
                or not price.get('period') or not price.get('source', '').startswith('https://')):
            raise ValueError(f'{crop} price needs CAD/bu, period and source URL')
        detail['prices'][crop] = {**price, 'value': _number(price.get('value'), f'{crop} price')}
    if missing_prices:
        return 'price not chosen', detail
    if missing_yields:
        return 'UNVERIFIED (missing crop yields)', detail
    detail['by_crop_year'] = [yields[c] * detail['prices'][c]['value'] for c in crops]
    return round(sum(detail['by_crop_year']) / len(crops), 2), detail


def rank_rotations(suitability, scenario='normal', label='SAMPLE', *,
                   scoring_policy='evidence_only', trial_path=TRIAL_CSV, price_path=PRICE_JSON):
    """V3 API contract, plus component provenance. Unknown labels default SAMPLE.

    Caller supplies scenario-specific Model 1 output. No climate is synthesized.
    evidence_only leaves scores pending. sample_diversity enables SAMPLE ranking.
    """
    if scenario not in {'normal', 'dry', '2035_dry', '2012_replay'}:
        raise ValueError(f'Unsupported scenario: {scenario}')
    if label not in {'LIVE', 'CACHED', 'SAMPLE'}:
        raise ValueError('Invalid label')
    if scoring_policy not in {'evidence_only', 'sample_diversity', 'trial_yield_index'}:
        raise ValueError('Unknown scoring policy')
    suit = _normalise(suitability)
    trial, prices = load_trial_yields(trial_path), load_prices(price_path)
    best, continuous = trial_index(trial)
    soil_lines = load_soil_lines(trial_path)
    out = []
    for name, crops in ROTATIONS.items():
        percents = [suit.get(c, {}).get('percent') for c in crops]
        missing = sorted({c for c, p in zip(crops, percents) if p is None})
        avg = None if missing else sum(percents) / len(crops)
        sample = scoring_policy == 'sample_diversity'
        benefit = 10.0 * (len(set(crops)) - 1) if sample else None
        repeats = sum(c == crops[(i + 1) % len(crops)] for i, c in enumerate(crops))
        penalty = 10.0 * repeats / len(crops) if sample else None
        raw = avg + benefit - penalty if avg is not None and sample else None
        score = None if raw is None else max(0.0, min(100.0, raw))
        refs = {c: trial.get((name, c)) for c in dict.fromkeys(crops)}
        index_parts = {c: round(100 * refs[c]['value'] / best[c], 1) for c in refs if refs[c] and best.get(c)}
        gains = {c: round(100 * (refs[c]['value'] - continuous[c]) / continuous[c], 1)
                 for c in refs if refs[c] and continuous.get(c) and ROTATIONS[name] != [c]}
        if scoring_policy == 'trial_yield_index':
            score = round(sum(index_parts.values()) / len(index_parts), 1) if index_parts else None
        yields = {c: ref['value'] if ref else 'UNVERIFIED' for c, ref in refs.items()}
        revenue, revenue_detail = _revenue(crops, yields, prices)
        inputs = {c: suit.get(c, {'percent': None, 'source': None}) for c in dict.fromkeys(crops)}
        sample_input = any(e.get('label', 'SAMPLE') == 'SAMPLE'
                           or 'SAMPLE' in str(e.get('source', '')).upper()
                           or 'UNVERIFIED' in str(e.get('source', '')).upper()
                           for e in inputs.values())
        out.append({
            'name': name, 'crops': list(crops),
            'status': ('scored' if score is not None else 'not scored') if scoring_policy == 'trial_yield_index'
                      else ('not scored' if missing else ('scored' if sample else 'pending rules')),
            'not_scored_crops': missing, 'overall_percent': score,
            'breakdown': {'average_suitability': avg, 'rotation_benefit': benefit,
                          'soil_penalty': penalty, 'unclamped_percent': raw,
                          'crop_suitability': inputs, 'policy': scoring_policy,
                          'policy_source': 'SAMPLE prototype assumptions' if sample
                          else ('Trial yield / best trial yield for that crop' if scoring_policy == 'trial_yield_index'
                                else 'No calibrated scoring weights available'),
                          'score_kind': 'prototype index, not probability of success',
                          'climate_adjustment': 1.0, 'rotation_multiplier': 1.0,
                          'trial_index_by_crop': index_parts,
                          'trial_index_excluded': [c for c in refs if c not in index_parts],
                          'trial_best_yield': {c: best[c] for c in index_parts},
                          'trial_gain_vs_continuous_pct': gains},
            'soil': soil_lines.get(name),
            'yield_bu_ac': yields, 'yield_references': refs,
            'revenue_per_ac': revenue, 'revenue_detail': revenue_detail,
            'scenario': scenario, 'label': 'SAMPLE' if sample or sample_input else label,
            'rank': None,
            'notes': ['Trial yields are historical references, unchanged across scenarios.',
                      'Climate adjustment 1 is an assumption, not evidence of no climate effect.',
                      'Red clover is underseeded, not an extra cash-crop year.',
                      'Trial location differs from the configured pilot point; see EVIDENCE.md.'],
        })
    out.sort(key=lambda r: (r['overall_percent'] is None, -(r['overall_percent'] or 0), r['name']))
    last_score, rank = None, None
    for index, row in enumerate(out, 1):
        score = row['overall_percent']
        if score is not None:
            if score != last_score:
                rank = index
            row['rank'] = rank
            last_score = score
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='Model 1 crop dictionary JSON')
    parser.add_argument('--scenario', default='normal')
    parser.add_argument('--policy', choices=['evidence_only', 'sample_diversity'], default='evidence_only')
    parser.add_argument('--output', type=Path, help='Save JSON for UI integration')
    args = parser.parse_args()
    if args.input:
        with args.input.open(encoding='utf-8-sig') as handle:
            suitability = json.load(handle)
    else:
        suitability = SAMPLE_SUITABILITY
    result = rank_rotations(suitability, args.scenario, scoring_policy=args.policy)
    payload = json.dumps(result, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + '\n', encoding='utf-8')
    print(payload)


if __name__ == '__main__':
    main()
