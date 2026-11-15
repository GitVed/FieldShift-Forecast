import csv
import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
import netCDF4
from rasterio.transform import from_origin

from backend.data_pipeline import (FIELDS, LAT, LON, Pipeline, SOILS, choose_hwsd_component, clean,
                                   monthly_rate_total, power_reader, validate_power_header, verify_imerg_json, water_volume)


class ConversionTests(unittest.TestCase):
    def test_precipitation_rate_handles_leap_year(self):
        self.assertEqual(monthly_rate_total(2, 2020, 2), 58)
        self.assertEqual(monthly_rate_total(2, 2019, 2), 56)
        self.assertEqual(monthly_rate_total(0, 2020, 1), 0)

    def test_wrong_power_unit_or_location_is_rejected(self):
        valid=f'Location: Latitude {LAT} Longitude {LON}\nT2M Temperature (C)\nPRECTOTCORR Precipitation (mm/day)\nRH2M Humidity (%)'
        validate_power_header(valid)
        with self.assertRaisesRegex(ValueError,'unit'):
            validate_power_header(valid.replace('(mm/day)','(mm)'))
        with self.assertRaisesRegex(ValueError,'location'):
            validate_power_header(valid.replace(str(LAT),'45'))

    def test_water_conversion_depends_on_layer_thickness(self):
        self.assertAlmostEqual(water_volume(30, 0, 10), .3)
        self.assertAlmostEqual(water_volume(90, 10, 40), .3)
        with self.assertRaises(ValueError):
            water_volume(30, 10, 10)

    def test_missing_and_impossible_values_remain_null(self):
        for value in [-999, -9999, float('nan'), None]:
            self.assertIsNone(clean(value, 'temperature')[0])
        for value, variable in [(110, 'humidity'), (-1, 'precipitation'), (0, 'ph'), (1.1, 'soil_moisture')]:
            self.assertEqual(clean(value, variable)[1], 'invalid')
        self.assertEqual(clean(0, 'precipitation')[1], 'valid')


class SourceVerificationTests(unittest.TestCase):
    def proof(self):
        rows=[{'YEAR':'2012','DOY':'183','IMERG_PRECTOT':'2.5'},
              {'YEAR':'2012','DOY':'184','IMERG_PRECTOT':'0'}]
        payload={'geometry':{'coordinates':[round(LON,3),round(LAT,3)]},
                 'header':{'sources':['IMERG'],'time_standard':'UTC','start':'20120701','end':'20120702'},
                 'parameters':{'IMERG_PRECTOT':{'units':'mm/day'}},
                 'properties':{'parameter':{'IMERG_PRECTOT':{'20120701':2.5,'20120702':0}}}}
        return payload,rows

    def test_daily_rate_is_verified_without_month_length_scaling(self):
        proof,rows=self.proof()
        self.assertEqual(verify_imerg_json(proof,rows)['matching_daily_values'],2)
        proof['parameters']['IMERG_PRECTOT']['units']='mm'
        self.assertEqual(verify_imerg_json(proof,rows)['status'],'verified')

    def test_wrong_source_or_modified_record_is_not_verified(self):
        proof,rows=self.proof();proof['header']['sources']=['MERRA2']
        with self.assertRaisesRegex(ValueError,'IMERG-only'):verify_imerg_json(proof,rows)
        proof,rows=self.proof();proof['properties']['parameter']['IMERG_PRECTOT']['20120701']=2.6
        with self.assertRaisesRegex(ValueError,'values differ'):verify_imerg_json(proof,rows)

    def test_wrong_point_and_missing_dates_are_rejected(self):
        proof,rows=self.proof();proof['geometry']['coordinates']=[0,0]
        with self.assertRaisesRegex(ValueError,'location'):verify_imerg_json(proof,rows)
        proof,rows=self.proof();del proof['properties']['parameter']['IMERG_PRECTOT']['20120702']
        with self.assertRaisesRegex(ValueError,'coverage differs'):verify_imerg_json(proof,rows)
        proof,rows=self.proof()
        with self.assertRaisesRegex(ValueError,'Duplicate'):verify_imerg_json(proof,rows+rows[:1])

    def test_hwsd_uses_documented_component_and_original_depths(self):
        rows=[dict(SEQUENCE=1,SHARE=100,TOPDEP=a,BOTDEP=b) for a,b in
              [(0,20),(20,40),(40,60),(60,80),(80,100),(100,150),(150,200)]]
        selected,sequence,shares=choose_hwsd_component(rows)
        self.assertEqual(sequence,1);self.assertEqual(shares,{1:100});self.assertEqual(len(selected),7)
        with self.assertRaisesRegex(ValueError,'layers missing'):choose_hwsd_component(rows[:-1])
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            choose_hwsd_component([dict(r,SEQUENCE=sequence,SHARE=50) for sequence in [1,2] for r in rows])


class PipelineFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'data/seed').mkdir(parents=True)
        self.manifest = {'downloads_and_attempts': []}

    def tearDown(self):
        self.temp.cleanup()

    def register(self, p):
        self.manifest['downloads_and_attempts'].append({
            'id': p.stem, 'local_file': str(p.relative_to(self.root)),
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
        (self.root/'data/seed/sources.json').write_text(json.dumps(self.manifest))

    def monthly_fixture(self, duplicate=False):
        p = self.root/'data/seed/power_harrow_monthly_1981_2025.csv'
        with p.open('w', newline='') as stream:
            stream.write(f'-BEGIN HEADER-\nLocation: Latitude {LAT} Longitude {LON}\nT2M Temperature (C)\nPRECTOTCORR Precipitation (mm/day)\nRH2M Humidity (%)\n-END HEADER-\n')
            writer = csv.writer(stream)
            writer.writerow(['PARAMETER','YEAR','JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC','ANN'])
            for year in range(1981,2026):
                for param,value in [('T2M',10),('PRECTOTCORR',2),('RH2M',50)]:
                    writer.writerow([param,year]+[value]*12+[999])
            if duplicate: writer.writerow(['T2M',2020]+[12]*12+[999])
        self.register(p)
        return p

    def test_monthly_output_drops_annual_field_and_preserves_input(self):
        p = self.monthly_fixture(); original = p.read_bytes()
        pipeline = Pipeline(self.root)
        with patch.object(pipeline,'daily_power'), patch.object(pipeline,'imerg'):
            pipeline.climate()
        with (self.root/'data/seed/power_precip_harrow_1981_2025.csv').open() as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),540)
        self.assertEqual(float(next(r['value'] for r in rows if r['date']=='2020-02-01')),58)
        self.assertEqual(list(rows[0]),FIELDS)
        self.assertEqual(p.read_bytes(),original)
        self.assertIsNone(pipeline.cells['power_harrow_point']['center_latitude'])

    def test_duplicate_month_is_rejected_instead_of_choosing_first(self):
        self.monthly_fixture(duplicate=True)
        pipeline=Pipeline(self.root)
        with patch.object(pipeline,'daily_power'), patch.object(pipeline,'imerg'):
            pipeline.climate()
        with (self.root/'data/seed/power_t2m_harrow_1981_2025.csv').open() as f:
            rows=[r for r in csv.DictReader(f) if r['date'].startswith('2020')]
        self.assertEqual(len(rows),12)
        self.assertTrue(all(r['value']=='' and r['reason']=='duplicate_record' for r in rows))

    def soil_fixture(self, invalid=False):
        values={'phh2o':65,'nitrogen':400,'soc':150,'sand':400,'silt':300,'clay':300}
        for prop in SOILS:
            for top,bottom in [(0,5),(5,15),(15,30)]:
                p=self.root/f'data/raw/soilgrids/{prop}_{top}-{bottom}cm_mean_harrow.tif'
                p.parent.mkdir(parents=True,exist_ok=True)
                with rasterio.open(p,'w',driver='GTiff',height=1,width=1,count=1,dtype='int16',
                                   crs='EPSG:4326',transform=from_origin(LON-.001,LAT+.001,.002,.002)) as ds:
                    ds.write(np.array([[0 if invalid else values[prop]]],dtype='int16'),1)
                self.register(p)

    def test_valid_soil_scales_each_depth_without_averaging(self):
        self.soil_fixture();pipeline=Pipeline(self.root);pipeline.soil()
        with (self.root/'data/seed/soilgrids_harrow.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),18)
        self.assertEqual({float(r['value']) for r in rows if r['variable']=='ph'},{6.5})
        self.assertEqual({float(r['value']) for r in rows if r['variable']=='total_nitrogen'},{4})
        self.assertEqual({float(r['value']) for r in rows if r['variable']=='sand'},{40})
        self.assertTrue(all(r['quality_flag']=='valid' for r in rows))

    def test_zero_soil_pixel_never_becomes_a_real_profile(self):
        self.soil_fixture(invalid=True);pipeline=Pipeline(self.root);pipeline.soil()
        with (self.root/'data/seed/soilgrids_harrow.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertTrue(all(r['value']=='' and r['quality_flag']=='invalid' for r in rows))
        self.assertTrue(all(float(r['native_value'])==0 for r in rows))

    def test_input_hash_mismatch_fails_before_processing(self):
        p=self.monthly_fixture();p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'changed since acquisition'):
            Pipeline(self.root).source(p)

    def test_imerg_conflicting_header_blocks_numeric_monthly_output(self):
        p=self.root/'data/raw/imerg_harrow_daily_19980601_20251231.csv';p.parent.mkdir(parents=True)
        with p.open('w') as f:
            f.write('-BEGIN HEADER-\nIMERG_PRECTOT MERRA-2 Total Precipitation (mm/day)\n-END HEADER-\nYEAR,DOY,IMERG_PRECTOT\n')
            for day in range(1,31):
                doy=dt.date(1998,6,day).timetuple().tm_yday
                f.write(f'1998,{doy},2\n')
        self.register(p);pipeline=Pipeline(self.root);pipeline.imerg()
        with (self.root/'data/seed/imerg_precip_harrow.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(rows[0]['value'],'')
        self.assertEqual(rows[0]['quality_flag'],'unverified')
        self.assertTrue(all(r['value']=='' for r in rows))

    def gldas_fixture(self, year, month, wrong_time=False, bad_unit=False, masked=False):
        p=self.root/f'data/raw/glda/GLDAS_NOAH025_M.A{year}{month:02d}.021.nc4'
        p.parent.mkdir(parents=True,exist_ok=True)
        with netCDF4.Dataset(p,'w') as ds:
            for name,size in [('time',1),('lat',1),('lon',1)]:ds.createDimension(name,size)
            for name,value in [('lat',LAT),('lon',LON)]:
                ds.createVariable(name,'f8',(name,))[:]=[value]
            time=ds.createVariable('time','f8',('time',));time.units='days since 2000-01-01'
            time[:]=[0 if wrong_time else netCDF4.date2num(dt.datetime(year,month,1),time.units)]
            for top,bottom in [(0,10),(10,40),(40,100),(100,200)]:
                v=ds.createVariable(f'SoilMoi{top}_{bottom}cm_inst','f4',('time','lat','lon'),fill_value=-9999)
                v.units='unknown' if bad_unit else 'kg m-2'
                v[:]=[[[-9999 if masked else .3*1000*(bottom-top)/100]]]
        self.register(p)
        return p

    def test_internal_timestamp_mismatch_is_not_hidden_by_filename(self):
        self.gldas_fixture(2012,7,wrong_time=True)
        with self.assertRaisesRegex(ValueError,'timestamp mismatch'):
            Pipeline(self.root).water()

    def test_unexpected_glDAS_units_are_not_converted(self):
        self.gldas_fixture(2012,7,bad_unit=True)
        with self.assertRaisesRegex(ValueError,'Unexpected GLDAS water unit'):
            Pipeline(self.root).water()

    def test_complete_water_record_masks_fill_and_reruns_idempotently(self):
        for year in range(2000,2026):
            for month in range(1,13):
                self.gldas_fixture(year,month,masked=(year,month)==(2012,7))
        self.gldas_fixture(2026,1)
        pipeline=Pipeline(self.root);pipeline.water();report=pipeline.save('water_fixture')
        path=self.root/'data/seed/gldas_soil_moisture_harrow.csv'
        original=path.read_bytes()
        with path.open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),1248)
        self.assertEqual(sum(r['quality_flag']=='missing' for r in rows),4)
        self.assertTrue(all(abs(float(r['value'])-.3)<1e-6 for r in rows if r['quality_flag']=='valid'))
        self.assertFalse(any(r['date'].startswith('2026') for r in rows))
        pipeline=Pipeline(self.root);pipeline.water();second=pipeline.save('water_fixture')
        self.assertEqual(original,path.read_bytes())
        self.assertEqual(report['run_id'],second['run_id'])
        manifest=json.loads((self.root/'data/seed/sources.json').read_text())
        self.assertEqual(len(manifest['processing_runs']),1)

    def test_verified_imerg_month_sums_daily_amounts_once(self):
        p=self.root/'data/raw/imerg_harrow_daily_19980601_20251231.csv';p.parent.mkdir(parents=True)
        values={}
        with p.open('w') as f:
            f.write('-BEGIN HEADER-\nIMERG_PRECTOT MERRA-2 Total Precipitation (mm/day)\n-END HEADER-\nYEAR,DOY,IMERG_PRECTOT\n')
            for day in range(1,31):
                date=dt.date(1998,6,day);f.write(f'1998,{date.timetuple().tm_yday},2\n')
                values[date.strftime('%Y%m%d')]=2
        self.register(p)
        proof=self.root/'data/raw/verification/imerg_power_full_daily.json';proof.parent.mkdir()
        proof.write_text(json.dumps({'geometry':{'coordinates':[LON,LAT]},
            'header':{'sources':['IMERG'],'time_standard':'UTC','start':'19980601','end':'19980630'},
            'parameters':{'IMERG_PRECTOT':{'units':'mm/day'}},'properties':{'parameter':{'IMERG_PRECTOT':values}}}))
        self.register(proof)
        self.manifest['downloads_and_attempts'][-1]['url']=f'https://power.larc.nasa.gov/api/temporal/daily/point?parameters=IMERG_PRECTOT&latitude={LAT}&longitude={LON}'
        (self.root/'data/seed/sources.json').write_text(json.dumps(self.manifest))
        pipeline=Pipeline(self.root);pipeline.imerg()
        with (self.root/'data/seed/imerg_precip_harrow.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(float(rows[0]['value']),60)
        self.assertEqual(rows[0]['quality_flag'],'valid')
        self.assertEqual(rows[1]['value'],'')
        self.assertEqual(rows[1]['quality_flag'],'missing')

    def test_original_soil_nodata_is_not_zero_or_a_nearby_value(self):
        (self.root/'data/seed/sources.json').write_text(json.dumps(self.manifest))
        p=self.root/'original.tif'
        with rasterio.open(p,'w',driver='GTiff',height=1,width=1,count=1,dtype='int16',nodata=-32768,
                           crs='EPSG:4326',transform=from_origin(LON-.001,LAT+.001,.002,.002)) as ds:
            ds.write(np.array([[-32768]],dtype='int16'),1)
        value,cell=Pipeline(self.root).raster_point(p)
        self.assertIsNone(value)

    def test_missing_provenance_is_an_error(self):
        (self.root/'data/seed/sources.json').write_text(json.dumps(self.manifest))
        p=self.root/'unregistered.csv';p.write_text('x')
        with self.assertRaisesRegex(ValueError,'missing from acquisition provenance'):
            Pipeline(self.root).source(p)


if __name__=='__main__':
    unittest.main()
