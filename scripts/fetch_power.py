"""Fetch small NASA POWER CSVs and validate Harrow/north grid equivalence.
Run from the repository root: python -m scripts.fetch_power
No authentication is needed. Existing registered responses are hash-checked.
"""
import argparse
import calendar
import datetime as dt
import urllib.parse
import urllib.request
from pathlib import Path
# Support both direct script execution and python -m invocation.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.data_pipeline import FIELDS, ROOT, clean, monthly_rate_total, power_reader, sha256
from backend.provenance import load_manifest, save_manifest, write_csv

POINTS = {'harrow_center': (42., -83.125), 'north': (42.5356, -82.9183),
          'north_center': (42.5, -83.125)}
PARAMETERS = [('T2M', 'temperature', 'degC'), ('PRECTOTCORR', 'precipitation', 'mm/month'), ('RH2M', 'humidity', '%')]

def url(lat, lon):
    return 'https://power.larc.nasa.gov/api/temporal/monthly/point?' + urllib.parse.urlencode(dict(
        parameters='T2M,PRECTOTCORR,RH2M', community='AG', longitude=lon, latitude=lat,
        start=1981, end=2025, format='CSV'))

def values(path):
    header, rows = power_reader(path)
    expected = {'T2M': '(C)', 'PRECTOTCORR': '(mm/day)', 'RH2M': '(%)'}
    for name, unit in expected.items():
        if not any(line.startswith(name+' ') and line.rstrip().endswith(unit) for line in header.splitlines()):
            raise ValueError('Unexpected POWER units: '+name)
    result = {}
    for r in rows:
        if r['PARAMETER'] in expected and 1981 <= int(r['YEAR']) <= 2025:
            for month in range(1,13):
                key=(r['PARAMETER'], int(r['YEAR']), month)
                if key in result: raise ValueError('Duplicate month')
                result[key] = float(r[calendar.month_abbr[month].upper()])
    if len(result) != 1620: raise ValueError('Incomplete POWER response')
    return result

def run():
    manifest = load_manifest()
    entries = manifest['downloads_and_attempts']
    for name, (lat, lon) in POINTS.items():
        path = ROOT/f'data/source/power_{name}_monthly_1981_2025.csv'
        old = next((e for e in entries if e['id'] == 'power_'+name+'_monthly'), None)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with urllib.request.urlopen(url(lat,lon), timeout=180) as response:
                body=response.read()
            path.write_bytes(body)
        elif old and sha256(path) != old['sha256']:
            raise ValueError('Source changed: '+str(path))
        values(path)
        record=dict(id='power_'+name+'_monthly',url=url(lat,lon),local_file=str(path.relative_to(ROOT)),
                    sha256=sha256(path),bytes=path.stat().st_size,status='validated_cached',
                    attempted_at_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        entries[:] = [e for e in entries if e['id'] != record['id']] + [record]
        save_manifest(manifest)
    primary=values(ROOT/'data/seed/power_harrow_monthly_1981_2025.csv')
    north=values(ROOT/'data/source/power_north_monthly_1981_2025.csv')
    checks=[]
    for name, series in [('harrow_center',primary),('north_center',north)]:
        center=values(ROOT/f'data/source/power_{name}_monthly_1981_2025.csv')
        matches=sum(series[k]==center[k] for k in series)
        checks.append(dict(check=name,matching_values=matches,total_values=len(series),
                           result='equal' if matches==len(series) else 'different',
                           interpretation='Empirical point/centre agreement; not an upstream cell identifier from NASA'))
        if matches!=len(series): raise ValueError('Native-grid centre does not match requested point')
    if all(primary[k]==north[k] for k in primary): raise ValueError('Buddy series is not distinct')
    for cell,lat,source in [('power_harrow_point',42.,'power_monthly'),('power_north_point',42.5,'power_north_monthly')]:
        manifest.setdefault('resolved_cells',{})[cell]=dict(requested_latitude=42.0356 if lat==42. else 42.5356,
            requested_longitude=-82.9183,center_latitude=lat,center_longitude=-83.125,
            resolved_cell_status='documented_merra2_nearest_center_and_1620_value_equivalence',
            native_cell_id='UNVERIFIED: API echoes request coordinates',time_standard='LST',source_id=source)
    write_csv(ROOT/'data/metadata/power_grid_checks.csv',checks)
    for parameter,variable,unit in PARAMETERS:
        rows=[]
        for (p,year,month), native in sorted(north.items()):
            if p != parameter: continue
            value, flag, reason=clean(native,variable)
            if p=='PRECTOTCORR' and value is not None: value=monthly_rate_total(value,year,month)
            row=dict.fromkeys(FIELDS,'')
            row.update(date=f'{year:04d}-{month:02d}-01',variable=variable,value=value,unit=unit,
                native_value=native,native_unit='mm/day' if p=='PRECTOTCORR' else unit,
                cell_id='power_north_point',source_id='power_north_monthly',quality_flag=flag,reason=reason)
            rows.append(row)
        path=ROOT/f'data/seed/power_{variable}_north_1981_2025.csv'
        write_csv(path,rows)
        manifest.setdefault('derived_datasets',{})[str(path.relative_to(ROOT))]=dict(
            sha256=sha256(path),rows=len(rows),source_ids=['power_north_monthly'],status='CACHED',
            scientific_verdict='usable',processing='Monthly NASA POWER; rain rate multiplied by calendar days')
    manifest['readiness']['trend_and_buddy']='distinct north CSVs cached; see trend_results.csv'
    save_manifest(manifest)
    print(checks)

if __name__=='__main__': run()
