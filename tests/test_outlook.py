"""Data integrity and public contracts for the annual Harrow explorer."""
import copy
import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import netCDF4
import numpy as np
from fastapi.testclient import TestClient
from backend.app import app
from backend import outlook
from backend.outlook import adjust,timeline_data
from scripts.fetch_projections import parse_point
from backend.provenance import ROOT,load_manifest


class PointTests(unittest.TestCase):
    def point(self,var='tas',value=300.,duplicate=False,lat=42.125,unit=None):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'point.nc'
            with netCDF4.Dataset(path,'w',format='NETCDF3_CLASSIC') as ds:
                ds.createDimension('obs',365);ds.createDimension('station',1)
                t=ds.createVariable('time','f8',('obs',));t.units='days since 2026-01-01';t.calendar='standard'
                t[:]=np.arange(365)
                if duplicate:t[1]=0
                ds.createVariable('latitude','f8',('station',))[:]=lat
                ds.createVariable('longitude','f8',('station',))[:]=-82.875
                v=ds.createVariable(var,'f8',('obs',));v.units=unit or {'tas':'K','pr':'kg m-2 s-1','hurs':'%'}[var];v[:]=value
            return path.read_bytes()
    def test_temperature_units_and_full_months(self):
        rows,source=parse_point(self.point(),'TEST','tas',2026,'fixture')
        self.assertEqual(len(rows),12)
        self.assertAlmostEqual(rows[0]['value'],26.85)
        self.assertEqual(source['daily_rows'],365)
    def test_precipitation_flux_becomes_monthly_total(self):
        rows,_=parse_point(self.point('pr',.00001),'TEST','pr',2026,'fixture')
        self.assertAlmostEqual(rows[0]['value'],.00001*86400*31)
    def test_humidity_bounding_is_audited(self):
        rows,source=parse_point(self.point('hurs',101),'TEST','hurs',2026,'fixture')
        self.assertEqual(rows[0]['value'],100)
        self.assertEqual(source['humidity_clipped_days'],365)
    def test_bad_dates_location_and_units_rejected(self):
        for kwargs in [dict(duplicate=True),dict(lat=43),dict(unit='C')]:
            with self.assertRaises(ValueError):parse_point(self.point(**kwargs),'TEST','tas',2026,'fixture')


class CalibrationTests(unittest.TestCase):
    def test_delta_and_ratio_adjustments(self):
        self.assertEqual(adjust(25,20,22,'temperature'),27)
        self.assertEqual(adjust(100,50,80,'precipitation'),160)
        self.assertEqual(adjust(99,50,60,'humidity'),100)
    def test_bad_denominator_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):adjust(100,0,80,'precipitation')
        for var in ['temperature','humidity','precipitation']:
            with self.assertRaises(ValueError):adjust(float('nan'),10,10,var)


class OutlookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=TestClient(app)
    def test_ten_year_timeline_and_distinct_kinds(self):
        data=self.client.get('/api/timeline/harrow').json()
        self.assertEqual([r['year'] for r in data['years']],list(range(2021,2031)))
        self.assertTrue(all(r['kind']=='observed' for r in data['years'][:5]))
        self.assertTrue(all(r['kind']=='projection' for r in data['years'][5:]))
        self.assertEqual(data['soil']['ph']['value'],6.7)
    def test_real_projection_ensemble_and_spread(self):
        manifest=load_manifest();info=manifest['projection_data']
        self.assertEqual(len(info['models']),5)
        for path_key,hash_key in [('path','sha256'),('adjusted_path','adjusted_sha256')]:
            self.assertEqual(hashlib.sha256((ROOT/info[path_key]).read_bytes()).hexdigest(),info[hash_key])
        for row in timeline_data()['years'][5:]:
            self.assertTrue(row['available']);self.assertEqual(row['model_count'],5)
            for name in ['temperature','precipitation','humidity']:
                m=row['metrics'][name];self.assertLessEqual(m['low'],m['value']);self.assertLessEqual(m['value'],m['high'])
                self.assertTrue(math.isfinite(m['value']))
            self.assertIsNone(row['metrics']['soil_moisture']['value'])
    def test_unknown_field_and_invalid_parameters(self):
        self.assertEqual(self.client.get('/api/timeline/other').status_code,404)
        for query in ['year=2035','year=2020','must_grow=rice','need_bu=10','must_grow=maize&need_bu=-1','must_grow=maize&need_bu=nan']:
            self.assertEqual(self.client.get('/api/recommendations/harrow?'+query).status_code,422,query)
    def test_priority_target_and_historical_evidence_preserved(self):
        response=self.client.get('/api/recommendations/harrow?year=2025&must_grow=maize&need_bu=150')
        self.assertEqual(response.status_code,200)
        rows=response.json()['rotations'];self.assertTrue(rows)
        for row in rows:
            self.assertIn('Corn',row['crops']);self.assertEqual(row['quantity']['need_bu_ac'],150)
            self.assertEqual(row['year'],2025)
    def test_future_values_do_not_invent_future_yields(self):
        old=self.client.get('/api/recommendations/harrow?year=2025').json()
        new=self.client.get('/api/recommendations/harrow?year=2026').json()
        self.assertEqual(new['status'],'PROJECTED')
        self.assertEqual({r['id']:(r['yields'],r['score']) for r in old['rotations']},
                         {r['id']:(r['yields'],r['score']) for r in new['rotations']})
    def test_rain_changes_recommendation_order_and_planning_scores(self):
        wet=self.client.get('/api/recommendations/harrow?year=2021').json()
        dry=self.client.get('/api/recommendations/harrow?year=2025').json()
        self.assertNotEqual(wet['rotations'][0]['id'],dry['rotations'][0]['id'])
        self.assertNotEqual(wet['rotations'][0]['planning_score'],dry['rotations'][0]['planning_score'])
        self.assertEqual(wet['climate_context']['year'],2021)
        self.assertEqual(dry['climate_context']['year'],2025)

    def test_priority_year_and_target_recompute_order(self):
        wet=self.client.get('/api/recommendations/harrow?year=2021&must_grow=soybean').json()
        dry=self.client.get('/api/recommendations/harrow?year=2025&must_grow=soybean').json()
        self.assertNotEqual(wet['rotations'][0]['id'],dry['rotations'][0]['id'])
        fifty=self.client.get('/api/recommendations/harrow?year=2025&must_grow=soybean&need_bu=50').json()
        sixty=self.client.get('/api/recommendations/harrow?year=2025&must_grow=soybean&need_bu=60').json()
        self.assertNotEqual(fifty['rotations'][0]['id'],sixty['rotations'][0]['id'])
        self.assertTrue(sixty['rotations'][0]['quantity']['meets'])

    def test_context_uses_temperature_humidity_and_real_soil_moisture(self):
        data=self.client.get('/api/recommendations/harrow?year=2025').json()['climate_context']
        self.assertTrue(data['drying_proxy_kpa']>0)
        self.assertIsNotNone(data['soil_moisture'])
        future=self.client.get('/api/recommendations/harrow?year=2026').json()['climate_context']
        self.assertIsNone(future['soil_moisture'])
        self.assertNotEqual(data['drying_proxy_kpa'],future['drying_proxy_kpa'])

    def test_water_percentages_have_plain_quantity_explanations(self):
        data=self.client.get('/api/recommendations/harrow?year=2026').json()
        for row in data['rotations']:
            advice=row['water_advice']
            self.assertEqual(advice['low_pct'],round(row['water']['ensemble_low_pct']))
            self.assertEqual(advice['high_pct'],round(row['water']['ensemble_high_pct']))
            self.assertIn('every 100 mm',advice['meaning'])
            self.assertIn('Not a chance of success',advice['caution'])
            self.assertNotIn('wheat',advice['assessed_crops'])

    def test_repeated_future_match_is_explained_and_priority_is_respected(self):
        future=[self.client.get(f'/api/recommendations/harrow?year={y}').json() for y in range(2026,2031)]
        self.assertTrue(all('similar dry conditions' in row['ranking_summary'] for row in future))
        for crop,label in [('maize','Corn'),('soybean','Soy'),('wheat','Wheat')]:
            rows=self.client.get(f'/api/recommendations/harrow?year=2026&must_grow={crop}').json()['rotations']
            self.assertTrue(all(any(label.lower() in c.lower() for c in row['crops']) for row in rows))

    def test_unsupported_wheat_target_is_rejected_instead_of_ignored(self):
        support=self.client.get('/api/timeline/harrow').json()['priority_crops']
        self.assertFalse(support['wheat']['supported'])
        self.assertTrue(support['maize']['supported'])
        for target in [50,100,200]:
            response=self.client.get(f'/api/recommendations/harrow?year=2026&must_grow=wheat&need_bu={target}')
            self.assertEqual(response.status_code,422)
            self.assertIn('wheat',response.json()['detail'].lower())
        response=self.client.get('/api/recommendations/harrow?year=2026&must_grow=wheat')
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()['rotations'])
        self.assertFalse(response.json()['target_support']['supported'])

    def test_missing_future_moisture_explains_the_connected_data_limit(self):
        for year in self.client.get('/api/timeline/harrow').json()['years'][5:]:
            moisture=year['metrics']['soil_moisture']
            self.assertIsNone(moisture['value'])
            self.assertIn('No future soil-moisture model',moisture['unavailable_reason'])

    def test_unavailable_projection_does_not_use_sample_profile(self):
        data=copy.deepcopy(timeline_data());data['years'][5].update(available=False,message='Projection cache unavailable')
        with patch('backend.outlook.timeline_data',return_value=data):
            r=self.client.get('/api/recommendations/harrow?year=2026').json()
        self.assertEqual(r['status'],'unavailable');self.assertEqual(r['rotations'],[])
    def test_home_opens_frontend(self):
        r=self.client.get('/')
        self.assertEqual(r.status_code,200);self.assertIn('year-range',r.text)

if __name__=='__main__':unittest.main()
