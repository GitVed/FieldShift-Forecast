"""Annual Harrow outlook. Observations, model projections and trial evidence stay distinct."""
import csv
import functools
import hashlib
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Optional
from fastapi import APIRouter,HTTPException,Query
from backend import field_profile,stress,suitability
from backend.provenance import ROOT,load_manifest,save_manifest,write_csv

router=APIRouter(prefix='/api')
MONTHS=(5,6,7,8,9)
UNITS={'temperature':'degC','precipitation':'mm','humidity':'%','soil_moisture':'m3/m3'}
NASA_URL='https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/'


def read_rows(path):
    with Path(path).open(newline='') as stream:return list(csv.DictReader(stream))


def seasonal(values,variable):
    selected=[values[m] for m in MONTHS]
    return sum(selected) if variable=='precipitation' else statistics.mean(selected)


def adjust(value,model_baseline,observed_baseline,variable):
    """Monthly delta-change alignment, not a fitted weather forecasting model."""
    if not all(math.isfinite(x) for x in (value,model_baseline,observed_baseline)):
        raise ValueError('Nonfinite adjustment input')
    if variable=='precipitation':
        if model_baseline<=0:raise ValueError('Cannot use a zero precipitation calibration denominator')
        result=value/model_baseline*observed_baseline
    else:result=value-model_baseline+observed_baseline
    if variable=='humidity':result=max(0.,min(100.,result))
    if not math.isfinite(result):raise ValueError('Nonfinite adjusted value')
    return result


def build_projection_cache(root=ROOT):
    root=Path(root);manifest=load_manifest(root);info=manifest['projection_data']
    path=root/info['path']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:raise ValueError('Projection source CSV changed')
    raw=read_rows(path);lookup={}
    coordinates={(float(r['latitude']),float(r['longitude'])) for r in raw}
    if len(coordinates)!=1:raise ValueError('Projection files do not share a verified point grid')
    for row in raw:
        key=(row['model'],row['variable'],int(row['date'][:4]),int(row['date'][5:7]))
        if key in lookup:raise ValueError('Duplicate projection month')
        value=float(row['value'])
        if not math.isfinite(value) or row['quality_flag']!='valid':raise ValueError('Invalid projection month')
        lookup[key]=value
    last_year=max(k[2] for k in lookup)   # projection end comes from the data (2040 since Sun Nov 15)
    observations={}
    for var,name in field_profile.FILES.items():
        source=root/'data/seed'/name
        expected=manifest['derived_datasets'][source.relative_to(root).as_posix()]['sha256']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('Changed observed input')
        observations[var]={(int(r['date'][:4]),int(r['date'][5:7])):float(r['value']) for r in read_rows(source)
                           if r['quality_flag']=='valid' and r['value']!=''}
    results=[];validation=[];complete=[];errors=[]
    for model in info['models']:
        try:
            model_rows=[];model_validation=[]
            for variable in field_profile.FILES:
                aligned={}
                for month in range(1,13):
                    mb=statistics.mean(lookup[(model,variable,y,month)] for y in range(1991,2015))
                    ob=statistics.mean(observations[variable][(y,month)] for y in range(1991,2015))
                    for year in range(2015,last_year+1):
                        original=lookup[(model,variable,year,month)]
                        value=adjust(original,mb,ob,variable)
                        aligned[(year,month)]=value
                        model_rows.append(dict(model=model,scenario='ssp370',date=f'{year}-{month:02d}-01',variable=variable,
                            value=value,unit='mm/month' if variable=='precipitation' else UNITS[variable],
                            source_id=f'nex_v2_{model}_'+{'temperature':'tas','precipitation':'pr','humidity':'hurs'}[variable]+f'_{year}',
                            quality_flag='model_projection',humidity_adjustment_clipped=(variable=='humidity' and not 0<=original-mb+ob<=100),calibration='1991-2014 monthly delta change',
                            latitude=raw[0]['latitude'],longitude=raw[0]['longitude']))
                simulated=[statistics.mean(aligned[(y,m)] for y in range(2015,2026)) for m in range(1,13)]
                observed=[statistics.mean(observations[variable][(y,m)] for y in range(2015,2026)) for m in range(1,13)]
                differences=[a-b for a,b in zip(simulated,observed)]
                model_validation.append(dict(model=model,variable=variable,period='2015-2025',
                    metric='12 monthly climatology comparison; not annual forecast skill',
                    mean_bias=statistics.mean(differences),climatology_rmse=math.sqrt(statistics.mean(d*d for d in differences)),
                    unit='mm/month' if variable=='precipitation' else UNITS[variable]))
            complete.append(model);results.extend(model_rows);validation.extend(model_validation)
        except (KeyError,ValueError) as exc:errors.append(f'{model}: {exc}')
    if len(complete)<3:raise ValueError('Need at least 3 complete calibrated models: '+str(errors))
    output=root/'data/seed/nex_adjusted_harrow.csv'
    write_csv(output,sorted(results,key=lambda r:(r['model'],r['date'],r['variable'])))
    report=root/'data/metadata/projection_validation.csv';write_csv(report,validation)
    manifest['projection_data'].update(adjusted_path=output.relative_to(root).as_posix(),
        adjusted_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),models=complete,
        validation_path=report.relative_to(root).as_posix(),
        validation_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
        observed_input_hashes={name:manifest['derived_datasets']['data/seed/'+name]['sha256'] for name in field_profile.FILES.values()},
        calibration_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        calibration_method='Monthly additive change for temperature/humidity, multiplicative precipitation; align 1991-2014 to POWER; bound humidity to 0-100',
        caution='Uninitialized climate scenarios, not predictions of actual weather in individual years; model spread is not a confidence interval')
    save_manifest(manifest,root)
    return dict(rows=len(results),models=complete,comparison_rows=len(validation))


def metric(value,variable,kind,source,low=None,high=None,window='May–September'):
    return dict(value=value,low=low if low is not None else value,high=high if high is not None else value,
                unit=UNITS[variable],kind=kind,source=source,window=window)


def footprint(lat,lon,dy,dx,source):
    return dict(center=[lat,lon],bounds=[[lat-dy/2,lon-dx/2],[lat+dy/2,lon+dx/2]],source=source)


def crop_target_support():
    """Which crops have a yield reference a target can be checked against.
    Counts the 5-year trial, the long-term trial (Agomoh et al.) and the regional
    Essex line, the same evidence the target check in app._quantity uses."""
    from backend.rotation import load_trial_yields
    from backend.app import longterm_yields,regional_yields
    names={name for (_,name) in load_trial_yields()}|{crop for (_,crop) in longterm_yields()}|set(regional_yields())
    result={}
    for api_name,crop in [('maize','corn'),('soybean','soybean'),('wheat','wheat')]:
        supported=crop in names
        label={'maize':'Corn','soybean':'Soybean','wheat':'Wheat'}[api_name]
        result[api_name]=dict(supported=supported,message='' if supported else
            f'{label} yield targets are not available. No {crop} yield reference is connected.')
    return result


@functools.lru_cache(maxsize=1)
def timeline_data():
    observations={v:field_profile.monthly(v) for v in field_profile.FILES}
    moisture=field_profile.gldas_july();manifest=load_manifest()
    primary=manifest['resolved_cells']['power_harrow_point']
    power=footprint(primary['center_latitude'],primary['center_longitude'],.5,.625,'NASA POWER / MERRA-2')
    gldas=footprint(42.125,-82.875,.25,.25,'NASA GLDAS, 0–10 cm')
    baseline={v:metric(statistics.mean(seasonal({m:observations[v][(y,m)] for m in MONTHS},v)
                    for y in range(1991,2021)),v,'baseline','NASA POWER, 1991–2020') for v in observations}
    baseline['soil_moisture']=metric(statistics.mean(moisture[y] for y in range(2000,2021)),
        'soil_moisture','baseline','NASA GLDAS, 2000–2020',window='July, 0–10 cm')
    by_year={};model_info=manifest.get('projection_data',{});projection_error='Projection data has not been acquired.'
    projected={};nex=None
    if model_info.get('adjusted_path'):
        path=ROOT/model_info['adjusted_path']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==model_info.get('adjusted_sha256'):
            for row in read_rows(path):
                key=(int(row['date'][:4]),row['model'],row['variable'])
                projected.setdefault(key,{})[int(row['date'][5:7])]=float(row['value'])
            first=read_rows(path)[0];nex=footprint(float(first['latitude']),float(first['longitude']),.25,.25,'NASA NEX-GDDP-CMIP6 v2 / SSP370')
            projection_error='Fewer than three complete climate models for this year.'
        else:projection_error='Projection cache failed its integrity check.'
    last_projected=max((k[0] for k in projected),default=2030)
    for year in range(2021,last_projected+1):
        historical=year<=2025;metrics={};model_names=[]
        if historical:
            for var,series in observations.items():
                try:val=seasonal({m:series[(year,m)] for m in MONTHS},var)
                except KeyError:val=None
                metrics[var]=metric(val,var,'observed' if val is not None else 'unavailable','NASA POWER')
            for var in observations:metrics[var]['source_ids']=['power_monthly']
            metrics['soil_moisture']=metric(moisture.get(year),'soil_moisture','observed','NASA GLDAS',window='July, 0–10 cm')
        else:
            model_names=[model for model in model_info.get('models',[]) if all(
                len(projected.get((year,model,var),{}))==12 for var in observations)]
            for var in observations:
                values=[seasonal(projected[(year,model,var)],var) for model in model_names] if len(model_names)>=3 else []
                metrics[var]=metric(statistics.median(values) if values else None,var,'projection' if values else 'unavailable',
                    'NASA NEX-GDDP-CMIP6 v2, SSP370',min(values) if values else None,max(values) if values else None)
                metrics[var]['source_ids']=[f"nex_v2_{model}_{ {'temperature':'tas','precipitation':'pr','humidity':'hurs'}[var]}_{year}" for model in model_names] if values else []
            metrics['soil_moisture']=metric(None,'soil_moisture','unavailable','Not projected',window='July, 0–10 cm')
            metrics['soil_moisture']['unavailable_reason']='No future soil-moisture model is connected. Cached GLDAS observations end in 2025.'
        available=all(metrics[v]['value'] is not None for v in observations)
        by_year[year]=dict(year=year,kind='observed' if historical else 'projection',available=available,
            message='' if available else projection_error,model_count=len(model_names),metrics=metrics,
            footprint=power if historical else nex,soil_moisture_footprint=gldas if historical else None)
    import json
    field=json.loads((ROOT/'backend'/'field_config.json').read_text(encoding='utf-8'))
    return dict(field_id='harrow',location=dict(lat=field['lat'],lon=field['lon'],name='Harrow, Ontario',
            note='SAMPLE cropland square, not a surveyed field. Climate data cells are unchanged from the earlier town point.'),
        years=list(by_year.values()),baseline=baseline,soil=field_profile.soil(),priority_crops=crop_target_support(),
        period='May–September planning window; winter-wheat water checks excluded',
        projection=dict(scenario='SSP370',models=model_info.get('models',[]),
            calibration='1991–2014 monthly change alignment to NASA POWER',comparison='2015–2025 monthly climatologies, not annual forecast skill',
            data_sha256=model_info.get('adjusted_sha256'),source_inventory=model_info.get('source_inventory'),
            note='Climate scenarios, not weather forecasts. Ranges show model spread, not probabilities.'),
        trend=field_profile.temperature_trend(),sources=[
            dict(name='NASA POWER',url='https://power.larc.nasa.gov/'),dict(name='NASA GLDAS',url='https://ldas.gsfc.nasa.gov/gldas'),
            dict(name='NASA NEX-GDDP-CMIP6',url=NASA_URL),dict(name='ISRIC SoilGrids 250 m (field soil)',url='https://www.isric.org/explore/soilgrids'),
            dict(name='ESA WorldCover 2021 (cropland check)',url='https://esa-worldcover.org/'),
            dict(name='AAFC Woodslee rotation trial (Top Crop Manager, Drury 2021)',url='https://www.topcropmanager.com/the-benefits-of-crop-rotation-and-diversification/'),
            dict(name='FAO HWSD2 soil (cross-check)',url='https://www.fao.org/land-water/resources/tools/databases/hwsd/en'),
            dict(name='FAO GAEZ',url='https://www.fao.org/gaez/en')])


@router.get('/timeline/{field_id}')
def timeline(field_id:str):
    if field_id!='harrow':raise HTTPException(404,'Unknown field')
    return timeline_data()


def drying_proxy(temperature,humidity):
    """Season-mean atmospheric dryness proxy, not daily VPD or evapotranspiration.

    Saturation pressure follows FAO-56 equation 11. Applying it to seasonal
    means is only a relative planning flag; it is not an irrigation model.
    """
    return .6108*math.exp(17.27*temperature/(temperature+237.3))*(1-humidity/100)


@functools.lru_cache(maxsize=1)
def _may_sep_rain():
    """May-Sep rain totals: POWER by year (observed) and NEX by (model, year) (projected)."""
    power=defaultdict(float)
    with open(ROOT/'data/seed/power_precip_harrow_1981_2025.csv',encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            if r['value'] and r.get('quality_flag','valid')=='valid' and 5<=int(r['date'][5:7])<=9:
                power[int(r['date'][:4])]+=float(r['value'])
    nex=defaultdict(float)
    path=ROOT/'data/seed/nex_adjusted_harrow.csv'
    if path.exists():
        with open(path,encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                if r['variable']=='precipitation' and 5<=int(r['date'][5:7])<=9:
                    nex[(r['model'],int(r['date'][:4]))]+=float(r['value'])
    return dict(power),dict(nex)


def season_outlook(year):
    """Is this year dry-leaning? The driest third of POWER May-Sep rain 1991-2020 is the
    usual "below normal" tercile. Observed years use measured POWER rain. Projected years
    use a majority vote of the NASA NEX models. Dry-leaning years use the 2012 dry-year order."""
    power,nex=_may_sep_rain()
    base=sorted(power[y] for y in range(1991,2021))
    cutoff=base[len(base)//3-1]
    if year<=2025:
        rain=power[year];votes=int(rain<=cutoff);models=1;dry=bool(votes)
        detail=f"Measured NASA POWER May to September rain {rain:.0f} mm"
    else:
        values=[v for (m,y),v in nex.items() if y==year]
        votes=sum(v<=cutoff for v in values);models=len(values);dry=votes*2>models
        detail=f"{votes} of {models} NASA climate models"
    third=f"the driest third of 1991-2020 (at or below {cutoff:.0f} mm)"
    if year<=2025:
        text=(f"{year} was dry-leaning. Measured NASA POWER May to September rain was {rain:.0f} mm, in {third}, so this year uses the 2012 dry-year order." if dry else
              f"{year} was not dry-leaning. Measured NASA POWER May to September rain was {rain:.0f} mm, above {third}, so this year uses the trial evidence order.")
    else:
        text=(f"{year} looks dry-leaning. {votes} of {models} NASA climate models put May to September rain in {third}, so this year uses the 2012 dry-year order." if dry else
              f"{year} is not dry-leaning. Only {votes} of {models} NASA climate models put May to September rain in {third}, so this year uses the trial evidence order.")
    return dict(year=year,dry_leaning=dry,votes=votes,models=models,cutoff_mm=round(cutoff,1),
        baseline='NASA POWER May to September rain, 1991-2020, driest third',
        order='2012 dry-year order' if dry else 'trial evidence order',text=text,
        limits='The 2012 dry-year order uses drought results from US sites (Bowles et al. 2020) and how much crop water need the 2012 rain covered. No dry-year bushels are invented. Trial yields do not change.')


def rank_annual_options(rows,crop_sequences,selected,baseline,soil,dry_leaning=False):
    """Explicit decision rules, not fitted crop-response weights or yield forecasts.

    Trial evidence first (decided Sun Nov 15): target support (all, some or none
    of the trial figures meet the target) -> picked crop's trial yield, or the
    trial yield index when no crop is picked -> pH constraints -> this year's
    rain fit -> sourced drought resilience -> period GAEZ fit. Rain fit is shown
    on every option as a check. Missing wheat water is disclosed.
    """
    metrics=selected['metrics'];rain=metrics['precipitation']['value']
    temperature=metrics['temperature']['value'];humidity=metrics['humidity']['value']
    proxy=drying_proxy(temperature,humidity)
    reference=drying_proxy(baseline['temperature']['value'],baseline['humidity']['value'])
    moisture=metrics['soil_moisture']['value']
    low_moisture=moisture is not None and moisture<baseline['soil_moisture']['value']
    dry_air=proxy>reference
    context=dict(year=selected['year'],rain_mm=rain,temperature_c=temperature,humidity_pct=humidity,
        temperature_delta_c=temperature-baseline['temperature']['value'],humidity_delta_pct=humidity-baseline['humidity']['value'],
        soil_moisture=moisture,soil_moisture_below_reference=low_moisture,
        drying_proxy_kpa=proxy,drying_proxy_reference_kpa=reference,drying_proxy_above_reference=dry_air,
        note='Drying proxy uses seasonal means, not daily VPD or ET. Static soil stays unchanged. No annual yield response is calibrated.')
    keys={}
    for row in rows:
        crops=crop_sequences[row['id']];checked=[c for c in crops if c in ('corn','soybean')]
        fits=[min(1.,rain/suitability.FAO_WATER_NEED_MM['maize' if c=='corn' else c][0]) for c in checked]
        rain_fit=statistics.mean(fits)*100 if fits else None
        shortfall=any(f<1 for f in fits)
        ph_failures=sum(row['suitability'][c]['checks']['ph']['status']=='below target' for c in set(crops))
        gaez=[row['suitability'][c]['percent'] for c in crops if row['suitability'][c]['percent'] is not None]
        gaez_fit=statistics.mean(gaez) if gaez else -1
        resilience=(row['dry']['drought'].get('loss_reduction_low_pct') or 0) if shortfall or dry_air or low_moisture else 0
        quantity=row.get('quantity');target_group=0;target_gap=0
        if quantity:
            target_group={'all':0,'some':1,'none':2}.get(quantity.get('target_support'),3)
            target_gap=quantity.get('best_shortfall_bu_ac') or 0
        picked=row.get('picked_crop_yield_bu_ac')
        trial=picked if picked is not None else row['score']
        # Coverage is capped at the sourced lower water-need bound; no bonus for
        # excess rain. Unassessed wheat is never treated as a zero-water crop.
        # A tie on the picked crop (wheat 62.5 in both corn-soy-wheat rotations, the same
        # 4.2 t/ha in Agomoh et al. 2020) is broken by the trial score of the whole rotation.
        # Exact ties only (no invented closeness threshold): this year's rain fit, then the
        # midpoint of the DERIVED corn climate range in projected years, then the trial score.
        adj=row.get('climate_adjustment');corn_mid=((adj['low_bu_ac']+adj['high_bu_ac'])/2) if adj else -1
        # Dry-leaning years (season_outlook) put the 2012 dry-year rank ahead of the trial yield.
        dry_rank=(row.get('rank_dry') or 99) if dry_leaning else 0
        key=(target_group,target_gap,dry_rank,-(trial if trial is not None else -1),-(rain_fit if rain_fit is not None else -1),-corn_mid,-(row['score'] if row['score'] is not None else -1),ph_failures,
             -(rain_fit if rain_fit is not None else -1),-resilience,-gaez_fit,row['id'])
        keys[row['id']]=key
        row['planning_score']=round(rain_fit,1) if rain_fit is not None else None
        row['planning_score_kind']='Rain-fit check: mean rain / lower FAO need, capped at 100, over assessed corn/soy crop years. A check, not the ranking basis, and not a success probability.'
        row['planning_factors']=dict(rain_fit_pct=row['planning_score'],ph_constraints=ph_failures,gaez_period_index=round(gaez_fit,1),
            assessed_crop_years=len(checked),unassessed_crops=sorted(set(crops)-set(checked)),
            drought_resilience_reference_pct=resilience,priority_target_group=target_group)
        issue='rain below the lower FAO need for at least one assessed crop' if shortfall else 'rain meets the lower FAO need for assessed crops'
        target_text=(' Ordered first by whether trial figures meet your target.' if quantity else '')
        basis=(f"trial yield of your crop {picked:g} bu/ac" if picked is not None else f"trial yield index {row['score']}")
        row['reason']=f"Ordered by {basis}.{target_text} {selected['year']} check: {rain:.0f} mm May to September rain; {issue}; rain fit {row['planning_score']}/100. Period GAEZ {gaez_fit:.1f}. Winter-wheat water is not assessed. No future yields are invented."
    rows.sort(key=lambda row:keys[row['id']])
    for index,row in enumerate(rows,1):row['rank']=index
    return context


def water_advice(row,selected,crops):
    """Translate rain coverage into quantities a farmer can interpret.

    This compares regional rain with FAO crop-water ranges, not effective soil
    water, irrigation demand, crop survival probability or a yield prediction.
    """
    projected=selected['kind']=='projection'
    low=row['water']['ensemble_low_pct'] if projected else row['water']['low_pct']
    high=row['water']['ensemble_high_pct'] if projected else row['water']['high_pct']
    assessed=sorted(set(crops)&{'corn','soybean'});unassessed=sorted(set(crops)-set(assessed))
    if low is None or high is None:
        return dict(low_pct=None,high_pct=None,status='Water check unavailable',
                    meaning='No compatible growing-window water comparison is available.',assessed_crops=assessed,unassessed_crops=unassessed)
    status='Rainfall alone may fall short' if high<100 else 'Check your water supply' if low<100 else 'Rain may cover estimated needs'
    display_low=round(low);display_high=round(high)
    return dict(low_pct=display_low,high_pct=display_high,status=status,
        meaning=f'About {display_low}–{display_high} mm of rain for every 100 mm the assessed crops may need.',
        action='Check soil water and irrigation before committing to this rotation.' if low<100 else 'Check soil storage and drainage before relying on rainfall alone.',
        range_explanation=('Range combines different crop water needs and climate-model spread.' if projected else 'Range reflects different crop water needs.'),
        range_parts=(f'The low end, {display_low}%, compares rain with the top of the FAO water-need range of the thirstiest assessed crop. '
                     f'The high end, {display_high}%, compares it with the bottom of the range of the least thirsty one'
                     +(', across the 5 climate models. ' if projected else '. ')
                     +('Above 100% means rain alone may cover that need. ' if display_high>=100 else '')
                     +'It is not a cap and not a chance of success.'),
        assessed_crops=assessed,unassessed_crops=unassessed,
        caution='Rain only; excludes soil water storage and irrigation. Not a chance of success.')


@router.get('/recommendations/{field_id}')
def recommendations(field_id:str,year:int=Query(2026,ge=2021,le=2040),
                    must_grow:Optional[str]=None,need_bu:Optional[float]=Query(None,gt=0)):
    if field_id!='harrow':raise HTTPException(404,'Unknown field')
    if need_bu is not None and not math.isfinite(need_bu):raise HTTPException(422,'Yield target must be finite')
    if need_bu is not None and not must_grow:raise HTTPException(422,'Choose a crop for the yield target')
    if must_grow and stress.normalise_crop(must_grow) is None:raise HTTPException(422,'Choose corn, soybean or wheat')
    support=crop_target_support().get('maize' if stress.normalise_crop(must_grow)=='corn' else stress.normalise_crop(must_grow)) if must_grow else None
    if need_bu is not None and support and not support['supported']:
        raise HTTPException(422,support['message']+' Choose wheat without a target to view compatible rotations.')
    data=timeline_data();selected=next(r for r in data['years'] if r['year']==year)
    if not selected['available']:
        return dict(year=year,status='unavailable',rotations=[],message=selected['message'],must_grow=must_grow)
    # Import only after app startup, avoiding circular initialization.
    from backend.app import rotation_scores,ROTATION_DISPLAY
    from backend import rotation
    result=rotation_scores('harrow',scenario='normal',must_grow=must_grow,need_bu=need_bu)
    values=selected['metrics'];profile=dict(temp_c=values['temperature']['value'],rain_mm=values['precipitation']['value'],
        humidity_pct=values['humidity']['value'],ph=data['soil']['ph']['value'])
    score=suitability.score_crops(profile,'normal' if year<=2025 else '2035_dry')
    names={rid:name for name,(rid,display,crops) in ROTATION_DISPLAY.items()}
    for row in result['rotations']:
        crops=rotation.ROTATIONS[names[row['id']]]
        row['water']=stress.water_range(crops,score)
        row['suitability']={c:score['maize' if c=='corn' else c] for c in dict.fromkeys(crops)}
        limits=[]
        for crop in dict.fromkeys(crops):
            need=suitability.FAO_WATER_NEED_MM.get('maize' if crop=='corn' else crop)
            if need and crop!='wheat':limits.append((values['precipitation']['low']/need[1]*100,values['precipitation']['high']/need[0]*100))
        row['water']['ensemble_low_pct']=round(min(x[0] for x in limits),1) if limits else None
        row['water']['ensemble_high_pct']=round(max(x[1] for x in limits),1) if limits else None
        row['year']=year
        row['climate_adjustment']=None
        if year>2025:
            from backend import climate_yield
            for y in row['yields']:
                if y['crop']=='Corn' and y.get('evidence')=='trial' and y.get('bu_ac') is not None:
                    adj=climate_yield.adjust('corn',year,y['bu_ac'])
                    if adj:row['climate_adjustment']={'crop':'corn','year':year,'trial_bu_ac':y['bu_ac'],**adj}
        row['gaez_period']='2001–2020 historical climate' if year<=2025 else '2021–2040 SSP370 climate'
        row['reference_reason']=row['reason']
        row['reason']=f"Historical trial index {row['score']}; ranking also considers published drought-resilience evidence. {year} rain coverage is a separate check. Trial yields are historical references, not projected yields."
    sequences={row['id']:rotation.ROTATIONS[names[row['id']]] for row in result['rotations']}
    outlook=season_outlook(year)
    context=rank_annual_options(result['rotations'],sequences,selected,data['baseline'],data['soil'],dry_leaning=outlook['dry_leaning'])
    for row in result['rotations']:
        row['order_basis']=outlook['order']
    for row in result['rotations']:
        row['water_advice']=water_advice(row,selected,sequences[row['id']])
        assessed=row['water_advice']['assessed_crops']
        row['rank_explanation']=('Placed by trial evidence first. '+('Rain is checked against soybean water need only. ' if assessed==['soybean'] else 'Rain is checked against corn and soybean water need. ')+'Winter-wheat water is not assessed. Rain is a check, not the ranking.')
    below_need=profile['rain_mm']<min(suitability.FAO_WATER_NEED_MM[c][0] for c in ('maize','soybean'))
    summary='Ordered by trial evidence first. '+('This year’s rain is below the lower water need of the assessed crops, so check water before you commit.' if below_need else 'This year’s rain meets at least one assessed crop’s lower water need.')+' Rain is a check, not the ranking.'
    if must_grow:summary=f"Only rotations containing {stress.normalise_crop(must_grow)} are considered. "+summary
    rows=result['rotations'];crop=stress.normalise_crop(must_grow) if must_grow else None
    label={'corn':'corn','soybean':'soybean','wheat':'wheat'}.get(crop)
    # Ties on the picked crop's trial yield, said out loud instead of hidden.
    for row in rows:
        row['tie_note']=None
        if crop and row.get('picked_crop_yield_bu_ac') is not None:
            same=[r for r in rows if r is not row and r.get('picked_crop_yield_bu_ac')==row['picked_crop_yield_bu_ac']]
            if same:
                row['tie_note']=(f"Tie on {label}: {row['picked_crop_yield_bu_ac']:g} bu/ac here and in "
                                 +', '.join(r['name'] for r in same)+". Same trial figure, so the tie is broken by this year’s rain check, then the corn climate range from 2026, then the trial score of the whole rotation.")
    # Corn target against the DERIVED climate range for a projected year (P2 corn model, unchanged).
    for row in rows:
        q=row.get('quantity');adj=row.get('climate_adjustment')
        if q and crop=='corn' and adj and need_bu is not None:
            # Whole bushels, the same rounding the card's climate note uses, so the two always agree.
            lo,hi=round(adj['low_bu_ac']),round(adj['high_bu_ac'])
            where='above the whole range' if need_bu>hi else 'below the whole range' if need_bu<lo else 'inside the range'
            q['climate_range_check']=dict(year=year,low_bu_ac=lo,high_bu_ac=hi,position=where,status='DERIVED',
                text=f"{year} climate-adjusted corn {lo:g} to {hi:g} bu/ac across {adj['models']} NASA models. Your {need_bu:g} is {where}.")
    # Where the target falls among the trial figures for that crop.
    target_position=None
    if crop and need_bu is not None:
        figs=sorted(((r['quantity']['best_bu_ac'],r['name']) for r in rows if r.get('quantity') and r['quantity'].get('best_bu_ac') is not None),reverse=True)
        if figs:
            above=[f for f in figs if f[0]>=need_bu];below=[f for f in figs if f[0]<need_bu]
            if not below:text=f"Your {need_bu:g} bu/ac is at or below every {label} figure. The lowest is {figs[-1][0]:g} ({figs[-1][1]})."
            elif not above:text=f"Your {need_bu:g} bu/ac is above every {label} figure. The highest is {figs[0][0]:g} ({figs[0][1]})."
            else:text=f"Your {need_bu:g} bu/ac falls between {above[-1][0]:g} ({above[-1][1]}) and {below[0][0]:g} ({below[0][1]})."
            target_position=dict(target_bu_ac=need_bu,crop=label,figures=[dict(name=n,bu_ac=v,meets=v>=need_bu) for v,n in figs],
                low_bu_ac=figs[-1][0],high_bu_ac=figs[0][0],text=text+' Best trial or long-term figure per rotation. Historical, not a forecast.')
    count_note=(f"Only {len(rows)} trial rotations{(' include '+label) if crop else ''}. These are the rotations with Harrow trial yields. Other crops have suitability only, in the Other crops tab.")
    year_note=('Trial yields are historical, so they stay the same from 2021 to 2040. The year changes the rain check'
               +(', and from 2026 the climate range for corn in rotations that grow it' if any('corn' in sequences[r['id']] for r in rows) else '')+'.')
    summary=outlook['text']+' '+summary
    result.update(season_outlook=outlook,target_support=support,target_position=target_position,rotation_count_note=count_note,year_note=year_note,ranking_summary=summary,climate_context=context,year=year,status='CACHED' if year<=2025 else 'PROJECTED',climate_kind=selected['kind'],
        model_count=selected['model_count'],message=None,
        ranking='Trial evidence first: target support, then the trial yield of your crop or the trial yield index, then pH, then the selected year rain fit, sourced drought resilience and period GAEZ suitability. Rule-based, not a trained yield forecast.',
        suitability_note='GAEZ is period-based suitability, not annual prediction accuracy or a probability.',
        model_range_note='Projected water ranges include climate-model spread and crop water-need ranges; rain only, not irrigation or soil storage.')
    return result
