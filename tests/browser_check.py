"""Exercise the real frontend with Chromium.

python tests/browser_check.py --url http://127.0.0.1:8001
Requires requirements-dev.txt and python -m playwright install chromium.
Artifacts are written only to ignored .cache/browser/.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect


def run(url,historical_preview=False):
    root=Path(__file__).resolve().parents[1];artifacts=root/'.cache/browser';artifacts.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':1440,'height':1080},device_scale_factor=1)
        # Prove the map/UI survives unavailable online tiles; libraries/fonts are local.
        context.route('**/World_Imagery/MapServer/tile/**',lambda route:route.abort())
        page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(url,wait_until='networkidle')
        expect(page.locator('#year-range')).to_be_enabled()
        if historical_preview:page.locator('[data-year="2025"]').click()
        expect(page.locator('.rotation-card')).to_have_count(1)
        expect(page.locator('#data-badge')).to_contain_text('observation' if historical_preview else 'projected')
        assert page.locator('.leaflet-overlay-pane > svg').evaluate('(e)=>e.getBoundingClientRect().width')>200, 'Map overlay SVG clipped by icon CSS'
        expect(page.locator('#option-count')).to_have_text('Option 1 of 3')
        first=page.locator('.rotation-card').get_attribute('data-rotation-id')
        page.locator('#next-option').click();expect(page.locator('#option-count')).to_have_text('Option 2 of 3')
        assert page.locator('.rotation-card').get_attribute('data-rotation-id')!=first
        page.locator('#next-option').click();expect(page.locator('#next-option')).to_be_disabled()
        page.locator('[data-option="0"]').click();expect(page.locator('#previous-option')).to_be_disabled()
        expect(page.locator('#locate-field,#reset-map')).to_have_count(0)
        page.screenshot(path=str(artifacts/'desktop.png'),full_page=True)
        page.locator('[data-year="2021"]').click();expect(page.locator('#heading-year')).to_have_text('2021')
        expect(page.locator('#panel-body')).to_have_attribute('aria-busy','false')
        wet_first=page.locator('.rotation-card').get_attribute('data-rotation-id')
        expected=next(y for y in page.request.get(url.rstrip('/')+'/api/timeline/harrow').json()['years'] if y['year']==2021)['metrics']['temperature']['value']
        expect(page.locator('#map-reading strong')).to_contain_text(f'{expected:.1f}')
        page.locator('#year-range').focus();page.keyboard.press('ArrowRight');expect(page.locator('#heading-year')).to_have_text('2022')
        legends=[]
        for layer in ['precipitation','humidity','soil_moisture','soil']:
            page.locator(f'[data-layer="{layer}"]').click();expect(page.locator('#map-reading')).to_be_visible()
            legends.append(page.locator('#legend-ramp').get_attribute('style'))
        assert len(set(legends))==4
        assert page.evaluate('colorFor(rangeFor("temperature")[0],"temperature")')=='#367fc2'
        assert page.evaluate('colorFor(rangeFor("temperature")[1],"temperature")')=='#cc4946'
        expect(page.locator('#map-reading strong')).to_contain_text('6.6')  # SoilGrids at the cropland field
        static=page.locator('#map-reading strong').inner_text();page.locator('[data-year="2030"]').click()
        expect(page.locator('#map-reading strong')).to_have_text(static)
        page.locator('[data-layer="soil_moisture"]').click();expect(page.locator('#map-unavailable')).to_be_visible()
        page.locator('#view-history').click();expect(page.locator('#heading-year')).to_have_text('2025')
        expect(page.locator('#map-unavailable')).to_be_hidden()
        expect(page.locator('#panel-body')).to_have_attribute('aria-busy','false')
        assert page.locator('.rotation-card').get_attribute('data-rotation-id')==wet_first  # trial evidence first; the year changes the rain check, not the order
        page.locator('[data-layer="temperature"]').click()
        page.locator('#tab-priority').click();expect(page.locator('#priority-form')).to_be_visible()
        expect(page.locator('#panel-body')).to_contain_text('Choose a crop')
        for crop,label in [('maize','Corn'),('soybean','Soybean'),('wheat','Wheat')]:
            page.locator(f'[data-crop="{crop}"]').click()
            expect(page.locator('#panel-body[aria-busy="false"]')).to_be_visible()
            for card in page.locator('.rotation-card').all():assert label in card.locator('.crop-sequence').inner_text()
        page.locator('[data-crop="maize"]').click();page.locator('#yield-target').fill('150');page.locator('#priority-form [type=submit]').click()
        expect(page.locator('.target-check').first).to_be_visible()
        assert '150' in page.locator('.target-check').first.inner_text()
        expect(page.locator('#target-summary')).to_contain_text('150')
        page.locator('[data-crop="soybean"]').click();page.locator('#yield-target').fill('50');page.locator('#priority-form [type=submit]').click()
        expect(page.locator('#panel-body')).to_have_attribute('aria-busy','false')
        fifty=page.locator('.rotation-card').get_attribute('data-rotation-id')
        page.locator('#yield-target').fill('60');page.locator('#priority-form [type=submit]').click()
        expect(page.locator('#panel-body')).to_have_attribute('aria-busy','false')
        assert page.locator('.rotation-card').get_attribute('data-rotation-id')=='corn-soy-wheat'  # 64 meets 60, must not rank last
        expect(page.locator('.target-check')).to_contain_text('Depends on the figure')
        page.locator('#yield-target').fill('-5');assert not page.locator('#yield-target').evaluate('(el)=>el.checkValidity()')
        page.locator('#reset-priority').click();expect(page.locator('#yield-target')).to_have_value('')
        expect(page.locator('#panel-body')).to_contain_text('Choose a crop')
        # Detect evidence, field overlays and other crops (added Sun Nov 15).
        expect(page.locator('#trend-card')).to_contain_text('per decade')
        assert page.locator('.leaflet-interactive').count()>=3,'field square, trial point and grid cell expected'
        # Past-season replay (P1): any year 1981 to 2025, driest years from the data.
        expect(page.locator('#season-card')).to_contain_text('2012')
        page.locator('#season-year').select_option('1988');expect(page.locator('#season-card')).to_contain_text('May to September 1988')
        expect(page.locator('#season-card')).to_contain_text('Not available before 1999')
        # P2: climate yield check shows the 2012 miss and the DERIVED 2028 example on screen.
        expect(page.locator('#yield-model-card')).to_contain_text('13.7');expect(page.locator('#yield-model-card')).to_contain_text('2.7')
        expect(page.locator('#yield-model-card')).to_contain_text('145 to 173 bu/ac');expect(page.locator('#yield-model-card')).to_contain_text('DERIVED')
        page.locator('#tab-others').click();expect(page.locator('.crop-card').first).to_be_visible()
        expect(page.locator('#panel-body')).to_contain_text('Kidney beans');expect(page.locator('#panel-body')).to_contain_text('white mould')
        before=page.locator('.crop-card').count();page.locator('#filter-grown').check()
        assert page.locator('.crop-card').count()<before,'Ontario filter should narrow the list'
        page.locator('#tab-priority').click()
        page.locator('#tab-priority').focus();page.keyboard.press('ArrowLeft');expect(page.locator('#tab-recommendations')).to_have_attribute('aria-selected','true')
        expect(page.locator('.rotation-card')).to_have_count(1)
        page.locator('.rotation-card summary').first.click();expect(page.locator('.rotation-card details').first).to_have_attribute('open','')
        page.locator('#recommendation-method').click();expect(page.locator('#sources-dialog')).to_be_visible()
        page.keyboard.press('Escape');expect(page.locator('#sources-dialog')).to_be_hidden()
        page.locator('#play-timeline').click();expect(page.locator('#play-timeline')).to_have_attribute('aria-pressed','true')
        expect(page.locator('#heading-year')).to_have_text('2026',timeout=4000)
        page.locator('#play-timeline').click();expect(page.locator('#play-timeline')).to_have_attribute('aria-pressed','false')
        page.locator('.leaflet-control-zoom-in').click();page.locator('.leaflet-control-zoom-out').click()
        # Cursor, native range thumb and year labels share one axis.
        for year in [2021,2025,2030,int(page.locator('#year-range').get_attribute('max'))]:
            page.locator(f'[data-year="{year}"]').click()
            page.wait_for_function("""(year)=>{const c=document.querySelector('#timeline-cursor').getBoundingClientRect();const y=document.querySelector(`[data-year="${year}"]`).getBoundingClientRect();return Math.abs(c.x+c.width/2-y.x-y.width/2)<2;}""",arg=year)
            alignment=page.evaluate("""(year)=>{const r=document.querySelector('#year-range').getBoundingClientRect();const y=document.querySelector(`[data-year="${year}"]`).getBoundingClientRect();const lo=+document.querySelector('#year-range').min,hi=+document.querySelector('#year-range').max;return Math.abs(r.x+8.5+(year-lo)/(hi-lo)*(r.width-17)-y.x-y.width/2);} """,year)
            assert alignment<2,(year,alignment)
        # A failed recommendation request must expose a functional retry.
        page.route('**/api/recommendations/**',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'Temporary test outage'})))
        page.locator('[data-year="2024"]').click();expect(page.locator('#retry-recommendations')).to_be_visible()
        page.unroute('**/api/recommendations/**');page.locator('#retry-recommendations').click();expect(page.locator('.rotation-card')).to_have_count(1)
        page.evaluate('window.print=()=>{window.__printed=true}')
        page.locator('#print-plan').click();assert page.evaluate('window.__printed')
        page.pdf(path=str(artifacts/'plan.pdf'),format='A4',print_background=True)
        # Mobile: no horizontal clipping; tabs and touch-sized crop controls work.
        page.set_viewport_size({'width':390,'height':844})
        page.locator('#tab-priority').click();page.locator('[data-crop="soybean"]').click()
        expect(page.locator('.rotation-card').first).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),'Mobile horizontal overflow'
        page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(250)
        page.screenshot(path=str(artifacts/'mobile.png'),full_page=True)
        page.emulate_media(reduced_motion='reduce')
        assert page.locator('.leaflet-interactive').first.evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s'
        assert not errors,errors
        # Initial API failure has an honest error state and a working retry.
        other=context.new_page();other.route('**/api/timeline/**',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Unavailable"}'))
        other.goto(url);expect(other.locator('#load-error')).to_be_visible();expect(other.locator('#year-range')).to_be_disabled()
        other.unroute('**/api/timeline/**');other.locator('#retry-load').click();expect(other.locator('#year-range')).to_be_enabled()
        other.close();browser.close()
        print('Browser checks passed: map, all layers, history/projections, Priority crops/target/reset, keyboard, play/pause, details, sources, retries, offline tiles, mobile, reduced motion and print.')
        print('Artifacts:',artifacts)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',default='http://127.0.0.1:8001');parser.add_argument('--historical-preview',action='store_true');args=parser.parse_args()
    run(args.url,args.historical_preview)
