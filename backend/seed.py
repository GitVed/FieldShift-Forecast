"""Idempotently load the explicit cached CSV inventory, with hash/provenance checks.
Run: python -m backend.seed. DATABASE_URL selects PostgreSQL or SQLite.
No remote service is contacted. Rotation outputs remain owned by Ved.
"""
import csv
import hashlib
from pathlib import Path
from sqlalchemy import select, and_
# Support both direct script execution and python -m invocation.
if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import db
from backend.provenance import ROOT, load_manifest
from backend.trend import run as build_trends

CLIMATE=['power_t2m_harrow_1981_2025.csv','power_precip_harrow_1981_2025.csv',
    'power_humidity_harrow_1981_2025.csv','power_temperature_north_1981_2025.csv',
    'power_precipitation_north_1981_2025.csv','power_humidity_north_1981_2025.csv',
    'imerg_precip_harrow.csv','gldas_soil_moisture_harrow.csv']
SOILS=['soilgrids_harrow.csv','hwsd_soil_harrow.csv']

def rows(path):
    with Path(path).open(newline='') as stream: return list(csv.DictReader(stream))

def upsert(conn,table,row):
    predicate=and_(*(table.c[c.name]==row[c.name] for c in table.primary_key.columns))
    if conn.execute(select(table).where(predicate)).first(): conn.execute(table.update().where(predicate).values(**row))
    else: conn.execute(table.insert().values(**row))

def seed(engine=None, root=ROOT):
    engine=engine or db.get_engine()
    root=Path(root)
    manifest=load_manifest(root)
    sources={r['id']:r for r in manifest['downloads_and_attempts']}
    inventories=[]
    # Validate everything before touching the database.
    for name in CLIMATE+SOILS:
        path=root/'data/seed'/name
        info=manifest['derived_datasets'].get(path.relative_to(root).as_posix())
        if not info or hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
            raise ValueError('Missing provenance or changed CSV: '+name)
        records=rows(path)
        for r in records:
            if r['source_id'] not in sources: raise ValueError('Unknown source: '+r['source_id'])
            if r['cell_id'] not in manifest['resolved_cells']: raise ValueError('Unknown cell: '+r['cell_id'])
        inventories.append((name,records))
    trends=build_trends(root, write=False)  # never rewrite tracked CSVs during seeding
    db.metadata.create_all(engine)
    with engine.begin() as conn:
        for sid,details in sources.items():
            upsert(conn,db.data_sources,dict(source_id=sid,url=details.get('url'),sha256=details.get('sha256'),details=details))
        for cell,details in manifest['resolved_cells'].items():
            upsert(conn,db.grid_cells,dict(cell_id=cell,latitude=details.get('center_latitude'),longitude=details.get('center_longitude'),details=details))
        # Refresh only Dev-owned observations; preserve Ved's rotation_scores.
        for table in [db.monthly_climate,db.soil_profiles,db.trend_runs]: conn.execute(table.delete())
        for name,records in inventories:
            table=db.monthly_climate if name in CLIMATE else db.soil_profiles
            values=[]
            for r in records:
                value=dict(cell_id=r['cell_id'],variable=r['variable'],source_id=r['source_id'],
                    depth_top_cm=int(r['depth_top_cm']) if r['depth_top_cm'] else -1,
                    depth_bottom_cm=int(r['depth_bottom_cm']) if r['depth_bottom_cm'] else -1,
                    value=float(r['value']) if r['value'] else None,unit=r['unit'],quality_flag=r['quality_flag'],reason=r['reason'],status='CACHED')
                if name in CLIMATE: value['date']=r['date']
                values.append(value)
            conn.execute(table.insert(),values)
        for result in trends:
            conn.execute(db.trend_runs.insert().values(**{k:result[k] for k in ['cell_id','variable','start_year','end_year']},result=result))
    return {'monthly_climate':sum(len(r) for n,r in inventories if n in CLIMATE),
            'soil_profiles':sum(len(r) for n,r in inventories if n in SOILS),'trend_runs':len(trends)}

if __name__=='__main__': print(seed())
