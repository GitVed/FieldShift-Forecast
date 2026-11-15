"""Portable SQLAlchemy schema. Docker uses PostgreSQL; SQLite supports local previews."""
import os
from pathlib import Path
from sqlalchemy.engine import URL
from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, Integer, ForeignKey, JSON
from backend.provenance import ROOT

metadata=MetaData()
data_sources=Table('data_sources',metadata,
    Column('source_id',String,primary_key=True),Column('url',String),Column('sha256',String),Column('details',JSON,nullable=False))
grid_cells=Table('grid_cells',metadata,
    Column('cell_id',String,primary_key=True),Column('latitude',Float),Column('longitude',Float),Column('details',JSON,nullable=False))
monthly_climate=Table('monthly_climate',metadata,
    Column('cell_id',String,ForeignKey('grid_cells.cell_id'),primary_key=True),Column('date',String,primary_key=True),
    Column('variable',String,primary_key=True),Column('depth_top_cm',Integer,primary_key=True,default=-1),
    Column('depth_bottom_cm',Integer,nullable=False,default=-1),Column('source_id',String,ForeignKey('data_sources.source_id'),primary_key=True),
    Column('value',Float),Column('unit',String,nullable=False),Column('quality_flag',String,nullable=False),Column('reason',String),Column('status',String,nullable=False))
soil_profiles=Table('soil_profiles',metadata,
    Column('cell_id',String,ForeignKey('grid_cells.cell_id'),primary_key=True),Column('variable',String,primary_key=True),
    Column('depth_top_cm',Integer,primary_key=True),Column('depth_bottom_cm',Integer,nullable=False),
    Column('source_id',String,ForeignKey('data_sources.source_id'),primary_key=True),Column('value',Float),
    Column('unit',String,nullable=False),Column('quality_flag',String,nullable=False),Column('reason',String),Column('status',String,nullable=False))
trend_runs=Table('trend_runs',metadata,
    Column('cell_id',String,ForeignKey('grid_cells.cell_id'),primary_key=True),Column('variable',String,primary_key=True),
    Column('start_year',Integer,primary_key=True),Column('end_year',Integer,primary_key=True),Column('result',JSON,nullable=False))
rotation_scores=Table('rotation_scores',metadata,
    Column('field_id',String,primary_key=True),Column('rotation',String,primary_key=True),Column('result',JSON,nullable=False))

def get_engine(url=None):
    url=url or os.getenv('DATABASE_URL')
    if not url and os.getenv('DB_HOST'):
        url=URL.create('postgresql+psycopg', username=os.getenv('DB_USER','fieldshift'),
            password=os.environ['DB_PASSWORD'], host=os.environ['DB_HOST'],
            database=os.getenv('DB_NAME','fieldshift'))
    if not url:
        cache=ROOT/'.cache'; cache.mkdir(exist_ok=True)
        url='sqlite:///'+str(cache/'fieldshift.db')
    return create_engine(url, pool_pre_ping=True)
