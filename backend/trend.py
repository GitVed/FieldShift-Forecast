"""Cached monthly climate trends; run: python -m backend.trend.

Monthly climatologies are removed separately in each analysis window. Hamed–Rao
modified Mann–Kendall uses all significant autocorrelation lags (library default).
Sen slopes use actual elapsed days / 365.2425 and are reported per decade.
Rain slopes describe monthly totals, not annual/growing-season totals.
"""
from pathlib import Path
import csv
import datetime as dt
import math
import hashlib
import numpy as np
import pymannkendall as mk
from scipy.stats import theilslopes, norm
# Support both direct script execution and python -m invocation.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.provenance import ROOT, write_csv, load_manifest, save_manifest

FILES = {'power_harrow_point': ['power_t2m_harrow_1981_2025.csv','power_precip_harrow_1981_2025.csv'],
         'power_north_point': ['power_temperature_north_1981_2025.csv','power_precipitation_north_1981_2025.csv']}

def analyze(rows, variable, start_year=1981, end_year=2025):
    expected={f'{year:04d}-{month:02d}-01' for year in range(start_year,end_year+1) for month in range(1,13)}
    rows=[r for r in rows if r['variable']==variable and str(start_year)<=r['date'][:4]<=str(end_year)]
    result=dict(variable=variable,start_year=start_year,end_year=end_year,n=len(rows),
        slope_per_decade=None,p_value=None,confidence='inconclusive',
        slope_unit='degC/decade' if variable=='temperature' else 'mm/month/decade',
        direction='inconclusive',method='Hamed-Rao modified MK; all significant lags; monthly mean anomalies; elapsed-day Sen slope',
        status='CACHED',reason='')
    dates=[r['date'] for r in rows]
    if len(dates)!=len(expected) or set(dates)!=expected or len(set(dates))!=len(dates):
        result['reason']='incomplete_or_duplicate_months'; return result
    rows=sorted(rows,key=lambda r:r['date'])
    expected_unit='degC' if variable=='temperature' else 'mm/month'
    if any(r['quality_flag']!='valid' or r['unit']!=expected_unit or not r['value'] or not math.isfinite(float(r['value'])) for r in rows):
        result['reason']='invalid_quality_value_or_units'; return result
    y=np.array([float(r['value']) for r in rows])
    months=np.array([int(r['date'][5:7]) for r in rows])
    anomalies=y.copy()
    for month in range(1,13): anomalies[months==month] -= y[months==month].mean()
    dates=[dt.date.fromisoformat(r['date']) for r in rows]
    x=np.array([(d-dates[0]).days/365.2425 for d in dates])
    slope=float(theilslopes(anomalies,x)[0]*10)
    result['slope_per_decade']=slope
    if np.ptp(anomalies)<1e-10:
        result.update(p_value=1.0,direction='no significant trend',confidence='not significant at 95% threshold')
        return result
    test=mk.hamed_rao_modification_test(anomalies,alpha=0.05)
    if not math.isfinite(test.p) or not math.isfinite(test.var_s) or test.var_s<=0:
        result['reason']='undefined_autocorrelation_corrected_variance'; return result
    significant=bool(test.h)
    result.update(p_value=float(2*norm.sf(abs(test.z))),direction=('increasing' if slope>0 else 'decreasing') if significant else 'no significant trend',
                  confidence='significant at 95% threshold' if significant else 'not significant at 95% threshold')
    return result

def run(root=ROOT):
    results=[]
    manifest=load_manifest(root)
    for cell,files in FILES.items():
        rows=[]
        for name in files:
            path=Path(root)/'data/seed'/name
            info=manifest.get('derived_datasets',{}).get(str(path.relative_to(root)))
            if not info or hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
                raise ValueError('Changed or unregistered trend input: '+name)
            with path.open(newline='') as stream: rows.extend(csv.DictReader(stream))
        for variable in ['temperature','precipitation']:
            for start in [1981,1991]:
                result=analyze(rows,variable,start)
                results.append(dict(cell_id=cell,**result))
    for r in results:
        other=next(x for x in results if x['cell_id']!=r['cell_id'] and x['variable']==r['variable'] and x['start_year']==r['start_year'])
        sensitivity=next(x for x in results if x['cell_id']==r['cell_id'] and x['variable']==r['variable'] and x['start_year']!=r['start_year'])
        directional=r['direction'] in ['increasing','decreasing']
        r['buddy_check']='supported' if directional and other['direction']==r['direction'] else 'inconclusive'
        r['sensitivity_check']='supported' if directional and sensitivity['direction']==r['direction'] else 'inconclusive'
        r['verdict']=r['direction'] if r['buddy_check']=='supported' and r['sensitivity_check']=='supported' else 'inconclusive'
        r['confidence_note']='Statistical significance threshold; not a forecast probability. Nearby cells are spatially correlated.'
    output=Path(root)/'data/seed/trend_results.csv'
    write_csv(output,results)
    manifest.setdefault('derived_datasets',{})['data/seed/trend_results.csv']=dict(
        sha256=hashlib.sha256(output.read_bytes()).hexdigest(), rows=len(results),
        source_ids=['power_monthly','power_north_monthly'],status='CACHED',
        scientific_verdict='temperature_increasing_precipitation_inconclusive',
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_hashes={name:manifest['derived_datasets']['data/seed/'+name]['sha256'] for files in FILES.values() for name in files},
        processing='Monthly anomalies; Hamed-Rao MK; elapsed-day Sen slope; north and 1991 sensitivity')
    save_manifest(manifest,root)
    return results

if __name__=='__main__':
    for row in run():
        print(row)
