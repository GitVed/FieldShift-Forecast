"""Acquire tiny NASA NEX-GDDP-CMIP6 v2 point subsets, never global files.

Run: python -m scripts.fetch_projections [--workers 4]
The ignored .cache/nex directory permits safe restart. NetCDF parsing stays on
one thread because the native netCDF library is not thread safe.
"""
import argparse
import calendar
import concurrent.futures as cf
import datetime as dt
import hashlib
import math
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import netCDF4
import cftime
import numpy as np
from backend.provenance import ROOT,write_csv,load_manifest,save_manifest

MODELS=('ACCESS-CM2','CanESM5','MIROC6','MPI-ESM1-2-LR','MRI-ESM2-0')
VARIABLES={'tas':('temperature','degC'),'pr':('precipitation','mm/month'),'hurs':('humidity','%')}
HOST='https://ds.nccs.nasa.gov/thredds/'
LAT,LON=42.0356,-82.9183
END_YEAR=2040   # outlook end; 2040 matches the GAEZ 2021-2040 period (extended Sun Nov 15)


def get(url,limit=2000000):
    error=None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=100) as response:
                body=response.read(limit+1)
            if len(body)>limit:raise ValueError('Response too large for a point subset')
            return body
        except Exception as exc:
            error=exc
            if attempt<2:time.sleep(1+attempt*2)
    raise error


def catalog(model,scenario,var):
    prefix=f'AMES/NEX/GDDP-CMIP6/{model}/{scenario}/r1i1p1f1/{var}/'
    tree=ET.fromstring(get(HOST+'catalog/'+prefix+'catalog.xml'))
    entries={}
    for element in tree.iter():
        path=element.get('urlPath','')
        if path.endswith('_v2.0.nc'):
            year=int(path.rsplit('_',2)[-2]);entries[year]=path
    return entries


def subset_url(path,year,var):
    query=urllib.parse.urlencode(dict(var=var,latitude=LAT,longitude=LON,
        time_start=f'{year}-01-01T00:00:00Z',time_end=f'{year}-12-31T23:59:59Z',accept='netcdf3'))
    return HOST+'ncss/grid/'+path+'?'+query


def parse_point(body,model,var,year,url):
    with netCDF4.Dataset('point',memory=body) as ds:
        lat=float(ds.variables['latitude'][0]);lon=float(ds.variables['longitude'][0])
        if abs(lat-LAT)>.126 or abs(lon-LON)>.126:raise ValueError('Wrong point subset')
        data=ds.variables[var]
        expected={'tas':'K','pr':'kg m-2 s-1','hurs':'%'}[var]
        unit=str(data.units)
        if unit!=expected:raise ValueError(f'Unexpected {var} units: {unit}')
        raw=np.ma.asarray(data[:]).reshape(-1)
        t=ds.variables['time'];cal=getattr(t,'calendar','standard')
        dates=netCDF4.num2date(t[:],t.units,calendar=cal)
        if len(raw)!=len(dates) or np.ma.getmaskarray(raw).any():raise ValueError('Missing point values')
        seen=set();months=defaultdict(list);clipped=0
        for stamp,value in zip(dates,raw):
            key=(stamp.year,stamp.month,stamp.day)
            if stamp.year!=year or key in seen:raise ValueError('Unexpected or duplicate date')
            seen.add(key);value=float(value)
            if not math.isfinite(value):raise ValueError('Nonfinite source value')
            if var=='tas':value-=273.15
            elif var=='pr':
                if value<0:raise ValueError('Negative precipitation')
                value*=86400
            elif var=='hurs':
                # NASA's technical note documents values slightly outside 0–100.
                if not -2<=value<=103:raise ValueError('Extreme relative humidity')
                clipped+=int(not 0<=value<=100);value=max(0.,min(100.,value))
            months[stamp.month].append(value)
        rows=[]
        for month in range(1,13):
            days=cftime.DatetimeProlepticGregorian(year,month,1).daysinmonth if cal=='proleptic_gregorian' else None
            if cal in ('standard','gregorian'):days=calendar.monthrange(year,month)[1]
            if cal in ('noleap','365_day'):days=28 if month==2 else calendar.monthrange(2025,month)[1]
            if cal=='360_day':days=30
            if days is None:raise ValueError('Unsupported CF calendar: '+cal)
            if len(months[month])!=days:raise ValueError(f'Incomplete month {year}-{month}: {len(months[month])}/{days}')
            value=sum(months[month]) if var=='pr' else sum(months[month])/days
            rows.append(dict(model=model,scenario='historical' if year<2015 else 'ssp370',
                date=f'{year}-{month:02d}-01',variable=VARIABLES[var][0],value=value,unit=VARIABLES[var][1],
                latitude=lat,longitude=lon,source_id=f'nex_v2_{model}_{var}_{year}',quality_flag='valid'))
        entry=dict(source_id=f'nex_v2_{model}_{var}_{year}',model=model,variable=var,year=year,
            scenario='historical' if year<2015 else 'ssp370',url=url,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),
            latitude=lat,longitude=lon,native_unit=unit,calendar=cal,daily_rows=len(raw),humidity_clipped_days=clipped,version='2.0')
    return rows,entry


def reusable():
    """Rows and source records already published, if their hashes still match the manifest."""
    import csv
    info=load_manifest().get('projection_data',{});path=ROOT/'data/seed/nex_monthly_harrow.csv'
    inventory=ROOT/'data/metadata/projection_sources.csv'
    if not info or not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=info.get('sha256'):return [],[],0
    if hashlib.sha256(inventory.read_bytes()).hexdigest()!=info.get('source_inventory_sha256'):return [],[],0
    rows=list(csv.DictReader(path.open(newline='')));sources=list(csv.DictReader(inventory.open(newline='')))
    last=max(int(r['date'][:4]) for r in rows)
    for r in rows:r['value']=float(r['value']);r['latitude']=float(r['latitude']);r['longitude']=float(r['longitude'])
    return rows,sources,last


def run(workers=4):
    cache=ROOT/'.cache/nex';cache.mkdir(parents=True,exist_ok=True)
    kept_rows,kept_sources,kept_until=reusable()
    if kept_until:print(f'Reusing {len(kept_rows)} published monthly rows and {len(kept_sources)} source records to {kept_until} (hashes verified)',flush=True)
    jobs=[]
    for model in MODELS:
        for var in VARIABLES:
            for scenario,years in [('historical',range(1991,2015)),('ssp370',range(2015,END_YEAR+1))]:
                entries=catalog(model,scenario,var)
                for year in years:
                    if year<=kept_until:continue
                    if year not in entries:raise ValueError(f'No v2 source for {model} {var} {year}')
                    jobs.append((model,var,year,subset_url(entries[year],year,var)))
    print(f'{len(jobs)} small point subsets; calibration 1991–2014, comparison 2015–2025, outlook 2026–'+str(END_YEAR),flush=True)
    def fetch(job):
        model,var,year,url=job;path=cache/f'{model}_{var}_{year}.nc'
        if path.exists():body=path.read_bytes()
        else:
            body=get(url)
            if body[:3]!=b'CDF':raise ValueError('NASA did not return NetCDF3')
            temporary=path.with_suffix(".part");temporary.write_bytes(body);temporary.replace(path)
        return job,body
    rows=[];sources=[];failures=[]
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(fetch,j):j for j in jobs}
        for i,future in enumerate(cf.as_completed(futures),1):
            try:
                (model,var,year,url),body=future.result()
                values,source=parse_point(body,model,var,year,url)
                source['retrieved_at_utc']=dt.datetime.fromtimestamp((cache/f'{model}_{var}_{year}.nc').stat().st_mtime,dt.timezone.utc).isoformat()
                rows.extend(values);sources.append(source)
            except Exception as exc:
                job=futures[future];failures.append((job[:3],str(exc)));print('FAILED',job[:3],str(exc),flush=True)
            if i%15==0:print(f'{i}/{len(jobs)} complete; {len(failures)} failures',flush=True)
    rows=kept_rows+rows;sources=kept_sources+sources
    complete=[m for m in MODELS if sum(s['model']==m for s in sources)==len(VARIABLES)*(END_YEAR-1990)]
    rows=[r for r in rows if r['model'] in complete]
    write_csv(ROOT/'data/metadata/projection_sources.csv',sorted(sources,key=lambda r:r['source_id']))
    if len(complete)<3:raise RuntimeError(f'Only {len(complete)} complete models; do not publish an ensemble. Failures: {failures[:5]}')
    path=ROOT/'data/seed/nex_monthly_harrow.csv'
    write_csv(path,sorted(rows,key=lambda r:(r['model'],r['date'],r['variable'])))
    manifest=load_manifest();manifest.setdefault('projection_data',{}).update(dict(
        path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),models=complete,
        rows=len(rows),scenario='ssp370',version='2.0',requested_point=[LAT,LON],
        source_inventory='data/metadata/projection_sources.csv',
        source_inventory_sha256=hashlib.sha256((ROOT/'data/metadata/projection_sources.csv').read_bytes()).hexdigest(),
        acquisition_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),humidity_policy='Source RH bounded to 0–100 with daily clipping counts in inventory',
        calibration='1991–2014',validation='2015–2025',outlook=f'2026–{END_YEAR}'))
    save_manifest(manifest)
    print('Saved',len(rows),'monthly rows from',complete,flush=True)
    from backend.outlook import build_projection_cache
    print(build_projection_cache(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',type=int,default=4)
    run(p.parse_args().workers)
