import csv
import tempfile
import unittest
import shutil
from unittest.mock import patch
from pathlib import Path
from sqlalchemy import create_engine, select, func
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend import db
from backend.seed import seed
from backend.data_api import make_router
from backend.trend import analyze
from backend.provenance import ROOT,load_manifest,save_manifest

class TrendTests(unittest.TestCase):
    def series(self):
        return [dict(date=f'{y}-{m:02d}-01',variable='temperature',value=str((y-1981)*0.1 + (m%12)*2),unit='degC',quality_flag='valid') for y in range(1981,2026) for m in range(1,13)]
    def test_known_warming_seasonality_and_shuffle(self):
        rows=self.series()[::-1]
        result=analyze(rows,'temperature')
        self.assertAlmostEqual(result['slope_per_decade'],1.,delta=.03)
        self.assertEqual(result['direction'],'increasing')
    def test_gaps_duplicates_bad_quality_and_wrong_units(self):
        rows=self.series()
        self.assertEqual(analyze(rows[:-1],'temperature')['reason'],'incomplete_or_duplicate_months')
        self.assertEqual(analyze(rows+[rows[0]],'temperature')['direction'],'inconclusive')
        rows[0]['quality_flag']='missing'
        self.assertEqual(analyze(rows,'temperature')['reason'],'invalid_quality_value_or_units')
        rows=self.series();rows[0]['unit']='K'
        self.assertEqual(analyze(rows,'temperature')['direction'],'inconclusive')
    def test_flat_seasonal_series_is_not_trend(self):
        rows=self.series()
        for r in rows: r['value']=str(int(r['date'][5:7])*2)
        result=analyze(rows,'temperature')
        self.assertEqual(result['p_value'],1.)
        self.assertEqual(result['direction'],'no significant trend')

class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        shutil.copytree(ROOT/'data/seed',cls.root/'data/seed')
        cls.engine=create_engine('sqlite:///'+str(cls.root/'test.db'))
        cls.counts=seed(cls.engine,cls.root)
        app=FastAPI();app.include_router(make_router(cls.engine))
        cls.client=TestClient(app)
    @classmethod
    def tearDownClass(cls): cls.engine.dispose();cls.tmp.cleanup()
    def test_real_cache_counts(self):
        self.assertEqual(self.counts,dict(monthly_climate=4819,soil_profiles=60,trend_runs=8))
    def test_seed_idempotence_preserves_rotation(self):
        with self.engine.begin() as c:
            c.execute(db.rotation_scores.insert().values(field_id='test',rotation='test',result={'status':'SAMPLE'}))
        seed(self.engine,self.root)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(db.monthly_climate)),4819)
            self.assertEqual(c.scalar(select(func.count()).select_from(db.rotation_scores)),1)
    def test_api_real_data_and_unknown_cell(self):
        response=self.client.get('/api/trend/harrow')
        self.assertEqual(response.status_code,200)
        trends=response.json()['trends'];self.assertEqual(len(trends),4)
        rain=next(r for r in trends if r['variable']=='precipitation' and r['start_year']==1981)
        self.assertEqual(rain['verdict'],'inconclusive')
        series=self.client.get('/api/series/harrow?variable=humidity').json()
        self.assertEqual(len(series['observations']),540)
        self.assertEqual(series['status'],'CACHED')
        self.assertEqual(self.client.get('/api/trend/missing').status_code,404)
    def test_changed_csv_is_rejected_before_database_changes(self):
        manifest=load_manifest(self.root)
        manifest['derived_datasets']['data/seed/power_t2m_harrow_1981_2025.csv']['sha256']='invalid'
        with patch('backend.seed.load_manifest',return_value=manifest):
            with self.assertRaisesRegex(ValueError,'changed CSV'):
                seed(self.engine,self.root)
        with self.engine.connect() as conn:
            self.assertEqual(conn.scalar(select(func.count()).select_from(db.monthly_climate)),4819)
    def test_unseeded_database_is_503(self):
        engine=create_engine('sqlite:///'+str(Path(self.tmp.name)/'empty.db'))
        app=FastAPI();app.include_router(make_router(engine))
        self.assertEqual(TestClient(app).get('/api/series/harrow').status_code,503)
        engine.dispose()
    def test_sources_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            original=load_manifest()
            save_manifest(original,root)
            self.assertEqual(load_manifest(root),original)

if __name__=='__main__': unittest.main()
