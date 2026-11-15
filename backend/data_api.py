"""Dev's standalone data API and reusable router for Ved's future backend.app.
Run: python -m uvicorn backend.data_api:app --host 0.0.0.0 --port 8000
After seeding, all requests read the local database only.
"""
from fastapi import APIRouter, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from backend import db

ALIASES={'harrow':'power_harrow_point','harrow-power':'power_harrow_point','north':'power_north_point'}

def make_router(engine=None):
    engine=engine or db.get_engine()
    router=APIRouter(prefix='/api')
    def cell_or_404(conn,cell_id):
        cell_id=ALIASES.get(cell_id,cell_id)
        row=conn.execute(select(db.grid_cells).where(db.grid_cells.c.cell_id==cell_id)).mappings().first()
        if row is None: raise HTTPException(404,'Unknown cell')
        return row
    @router.get('/series/{cell_id}')
    def series(cell_id:str, variable:str=Query(default=None)):
        try:
            with engine.connect() as conn:
                cell=cell_or_404(conn,cell_id)
                stmt=select(db.monthly_climate).where(db.monthly_climate.c.cell_id==cell['cell_id'])
                if variable: stmt=stmt.where(db.monthly_climate.c.variable==variable)
                observations=[dict(r) for r in conn.execute(stmt.order_by(db.monthly_climate.c.date,db.monthly_climate.c.variable,db.monthly_climate.c.depth_top_cm)).mappings()]
                ids={r['source_id'] for r in observations}
                sources=[dict(r) for r in conn.execute(select(db.data_sources).where(db.data_sources.c.source_id.in_(ids))).mappings()]
                return dict(status='CACHED',cell=dict(cell),observations=observations,sources=sources)
        except SQLAlchemyError as exc: raise HTTPException(503,'Data cache unavailable; run python -m backend.seed') from exc
    @router.get('/trend/{cell_id}')
    def trend(cell_id:str):
        try:
            with engine.connect() as conn:
                cell=cell_or_404(conn,cell_id)
                results=[r[0] for r in conn.execute(select(db.trend_runs.c.result).where(db.trend_runs.c.cell_id==cell['cell_id']).order_by(db.trend_runs.c.variable,db.trend_runs.c.start_year))]
                if not results: raise HTTPException(404,'No trend calculated for this cell')
                source_ids=['power_monthly','power_north_monthly']
                sources=[dict(r) for r in conn.execute(select(db.data_sources).where(db.data_sources.c.source_id.in_(source_ids))).mappings()]
                return dict(status='CACHED',cell=dict(cell),trends=results,sources=sources)
        except SQLAlchemyError as exc: raise HTTPException(503,'Data cache unavailable; run python -m backend.seed') from exc
    return router

app=FastAPI(title='FieldShift cached data API')
app.include_router(make_router())
