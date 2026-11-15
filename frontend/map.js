/* FieldShift: cached observations, explicit climate scenarios, transparent trial evidence. */
'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const state = {year:2026,layer:'temperature',mode:'recommendations',crop:null,target:null,timeline:null,pilot:null,detect:null,crops:null,cropFilter:{grown:false,gaez:0},recommendations:null,map:null,cell:null,marker:null,request:0,controller:null,timer:null,pending:null,optionIndex:0,activeLocation:{id:'harrow',name:'Harrow, Ontario'},locations:[]};
const layers = {
 temperature:{name:'Growing-season temperature',short:'Temperature',unit:'°C',icon:'sun',decimals:1,low:'Cooler',high:'Warmer',palette:['#367fc2','#f1e9db','#cc4946']},
 precipitation:{name:'Growing-season rainfall',short:'Rainfall',unit:'mm',icon:'rain',decimals:0,low:'Drier',high:'Wetter',palette:['#e2dcf3','#a08bc9','#5d479c']},
 humidity:{name:'Average relative humidity',short:'Humidity',unit:'%',icon:'drop',decimals:0,low:'Lower',high:'Higher',palette:['#d9f0e7','#77b9ab','#237b79']},
 soil_moisture:{name:'July soil moisture · 0–10 cm',short:'Soil moisture',unit:'m³/m³',icon:'soil',decimals:3,low:'Drier',high:'Wetter',palette:['#ba8852','#e4d4af','#4778aa']},
 soil:{name:'Topsoil pH · 0–30 cm',short:'Soil profile',unit:'pH',icon:'leaf',decimals:1,low:'',high:'',palette:['#927957','#c8ad7f','#675333']}
};
const fmt=(value,places=1)=>value===null||value===undefined?'—':Number(value).toLocaleString('en-CA',{minimumFractionDigits:places,maximumFractionDigits:places});
// A display focus, not a native data cell or surveyed field boundary.
const FOCUS_BOUNDS=[[42.0056,-82.9583],[42.0656,-82.8783]];
const selected=()=>state.timeline?.years.find(r=>r.year===state.year);
const FIRST_YEAR=2021,LAST_OBSERVED=2025;
const lastYear=()=>state.timeline?.years.at(-1)?.year||2030;
const yearCount=()=>lastYear()-FIRST_YEAR+1;
// Horizontal position of a year inside the tick row, matched to the native range thumb (8.5 px half-thumb).
function axisX(year){const r=$('year-range').getBoundingClientRect(),t=$('year-ticks').getBoundingClientRect(),span=Math.max(1,lastYear()-FIRST_YEAR);
 return (r.x-t.x)+8.5+(year-FIRST_YEAR)/span*(r.width-17);}
function layoutAxis(){document.querySelectorAll('#year-ticks .year-tick').forEach(b=>{b.style.left=axisX(+b.dataset.year)+'px';});}
function getMetric(year=selected(),layer=state.layer){
 if(layer==='soil')return {value:state.timeline?.soil.ph?.value,low:null,high:null,kind:'regional_estimate',source:'ISRIC SoilGrids 250 m at the field',window:'Static soil profile · 0–30 cm'};
 return year?.metrics[layer]||{value:null,kind:'unavailable'};
}
function rangeFor(layer){
 const values=state.timeline.years.flatMap(y=>[y.metrics[layer]?.low,y.metrics[layer]?.high]).filter(v=>Number.isFinite(v));
 if(!values.length)return [0,1];
 const min=Math.min(...values),max=Math.max(...values),padding=(max-min)*.08||1;
 return [min-padding,max+padding];
}
function colorFor(value,layer){
 if(value===null||value===undefined)return '#d9e0d1';
 const [lo,hi]=rangeFor(layer),t=Math.max(0,Math.min(1,(value-lo)/(hi-lo)))*2;
 const p=layers[layer].palette,i=Math.min(1,Math.floor(t)),f=t-i;
 const a=p[i].match(/\w\w/g).map(x=>parseInt(x,16)),b=p[i+1].match(/\w\w/g).map(x=>parseInt(x,16));
 return '#'+a.map((v,j)=>Math.round(v+(b[j]-v)*f).toString(16).padStart(2,'0')).join('');
}
function setError(message){$('load-error').hidden=!message;$('error-message').textContent=message||'';}
async function jsonGet(url,signal){const r=await fetch(url,{signal,cache:'no-store'});if(!r.ok){const error=await r.json().catch(()=>({}));throw new Error(typeof error.detail==='string'?error.detail:`Data service returned ${r.status}`);}return r.json();}
function initMap(){
 if(!window.L){$('basemap-note').hidden=false;$('basemap-note').textContent='Map library unavailable. Timeline and recommendations remain available.';return;}
 const location=state.timeline.location;
 state.map=L.map('map',{zoomControl:false,scrollWheelZoom:false,zoomSnap:.25}).setView([location.lat,location.lon],10);
 L.control.zoom({position:'topright'}).addTo(state.map);
 state.resizeObserver=new ResizeObserver(()=>state.map.invalidateSize({pan:false}));state.resizeObserver.observe($('map'));
 const tiles=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Imagery © <a href="https://www.esri.com/">Esri</a>, Vantor, Earthstar Geographics, GIS User Community'}).addTo(state.map);
 tiles.on('tileerror',()=>{$('basemap-note').hidden=false;});tiles.on('tileload',()=>{$('basemap-note').hidden=true;});
 const field=state.pilot;
 if(field?.polygon){L.polygon(field.polygon,{color:'#f4f1d0',weight:2,fillColor:'#d9e8a6',fillOpacity:.25}).addTo(state.map).bindPopup(`<strong>SAMPLE field</strong><br>${esc(field.polygon_note||'Not a surveyed field boundary.')}`);}
 if(field?.trial_site){L.circleMarker([field.trial_site.lat,field.trial_site.lon],{radius:7,color:'#fff',weight:2,fillColor:'#b5793b',fillOpacity:1}).addTo(state.map).bindTooltip('Woodslee rotation trial',{className:'grid-label',direction:'top'}).bindPopup(`<strong>Woodslee rotation trial</strong><br>${esc(field.trial_site.dms||'')}<br>A point, not a field boundary. About ${fmt(field.trial_site.distance_km,0)} km from the SAMPLE field. Trial yields come from here.`);}
 state.marker=L.marker([location.lat,location.lon],{icon:L.divIcon({className:'pilot-marker',html:`<div class="pilot-marker-body">${icon('leaf')}</div>`,iconSize:[32,32],iconAnchor:[16,30]})}).addTo(state.map);
 state.marker.bindTooltip('SAMPLE field',{permanent:true,className:'grid-label',direction:'top',offset:[0,-24]});
 state.marker.bindPopup(`<strong>SAMPLE field near Harrow</strong><br>${fmt(location.lat,4)}° N, ${fmt(Math.abs(location.lon),4)}° W<br>300 m square of cropland on ESA WorldCover 2021. Not a surveyed field boundary.`);
 state.marker.on('click',()=>animateContent($('map-reading')));
}
function animateContent(node,direction=1){
 if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
 node.getAnimations().forEach(animation=>animation.cancel());
 node.animate([{opacity:.35,transform:`translateY(${direction*5}px)`},{opacity:1,transform:'translateY(0)'}],{duration:480,easing:'cubic-bezier(.2,.7,.2,1)'});
}
function updateMap(){
 if(!state.timeline)return;
 const year=selected(),meta=layers[state.layer],m=getMetric(),future=year.kind==='projection';
 $('heading-year').textContent=state.year;
 const badge=state.layer==='soil'?'Regional soil estimate':m.kind==='unavailable'?'Data unavailable':future?`${year.model_count} models · projected`:'Cached observation';
 $('data-badge').textContent=badge;$('data-badge').classList.toggle('observed',!future||state.layer==='soil');
 $('map-period').textContent=state.layer==='soil'?'Static regional soil reference':state.layer==='soil_moisture'?'July · topsoil, 0–10 cm':`May–September ${state.year} · ${future?'climate scenario':'observed'}`;
 const missing=m.value===null||m.value===undefined;
 $('map-unavailable').hidden=!missing;
 if(missing){
  $('map-unavailable').querySelector('strong').textContent=state.layer==='soil_moisture'?'Soil moisture isn’t projected.':'Climate projection unavailable.';
  $('map-unavailable').querySelector('span').textContent=state.layer==='soil_moisture'?(m.unavailable_reason||'No future soil-moisture model is connected.'):year.message||'Choose an observed year while the source data is unavailable.';
 }
 const detail=state.layer==='soil'?'SoilGrids 250 m at the field · modelled, not a lab soil test':future?`${year.model_count}-model range ${fmt(m.low,meta.decimals)}–${fmt(m.high,meta.decimals)} ${meta.unit}`:`${m.source} · cached regional observation`;
 let extra='';
 if(state.layer==='soil'){
  const soils=state.timeline.soil;
  extra=`<div class="soil-composition" title="Sand / silt / clay"><span style="width:${Number(soils.sand?.value||0)}%;background:#c5b88d"></span><span style="width:${Number(soils.silt?.value||0)}%;background:#acbe8e"></span><span style="width:${Number(soils.clay?.value||0)}%;background:#799777"></span></div><p>${fmt(soils.sand?.value,0)}% sand · ${fmt(soils.silt?.value,0)}% silt · ${fmt(soils.clay?.value,0)}% clay</p>`;
 }
 $('map-reading').innerHTML=`<span class="eyebrow">${esc(meta.name)}</span><strong>${fmt(m.value,meta.decimals)} <small>${esc(meta.unit)}</small></strong><p>${esc(detail)}</p>${extra}`;
 $('map-reading').hidden=state.layer!=='soil'||missing;if(state.layer==='soil')animateContent($('map-reading'));
 $('legend-label').textContent=meta.low;$('legend-right').textContent=meta.high;
 $('legend-ramp').style.background=`linear-gradient(90deg,${meta.palette.join(',')})`;
 $('legend-ramp').parentElement.hidden=missing;
 if(state.layer==='soil'){const soil=state.timeline.soil,sand=Number(soil.sand.value),silt=Number(soil.silt.value);$('legend-label').textContent='Soil texture';$('legend-right').textContent='0–30 cm';$('legend-ramp').style.background=`linear-gradient(90deg,#c5b88d 0% ${sand}%,#acbe8e ${sand}% ${sand+silt}%,#799777 ${sand+silt}% 100%)`;$('legend-min').textContent=`Sand ${fmt(sand,0)}%`;$('legend-max').textContent=`Silt ${fmt(silt,0)} · Clay ${fmt(soil.clay.value,0)}%`;}
 if(state.layer!=='soil'){
  const [lo,hi]=rangeFor(state.layer);$('legend-min').textContent=`${fmt(lo,meta.decimals)} ${meta.unit}`;$('legend-max').textContent=`${fmt(hi,meta.decimals)} ${meta.unit}`;
 }
 const grid=state.layer==='soil_moisture'?year.soil_moisture_footprint:year.footprint;
 $('grid-caption').textContent=state.layer==='soil'?'Point reference · SoilGrids 250 m at the field':'Harrow focus area · regional point estimate, not a field scan';
 if(state.map){
  const color=missing||state.layer==='soil'?'#b4c3a7':colorFor(m.value,state.layer);
  const style={color,fillColor:color,fillOpacity:missing||state.layer==='soil'?0:.30,weight:2,dashArray:'5 5'};
  if(state.cell)state.cell.setStyle(style);
  else state.cell=L.rectangle(FOCUS_BOUNDS,style).addTo(state.map);
  if(!state.framed){state.map.fitBounds(FOCUS_BOUNDS,{padding:[48,48],maxZoom:12,animate:false});state.framed=true;}
  state.cell.bindPopup(`<strong>Harrow comparison focus</strong><br>${esc(meta.short)} · ${state.year}<br>${missing?'Data unavailable':`${fmt(m.value,meta.decimals)} ${esc(meta.unit)}`}<br>${esc(m.source||'Regional reference')}<br>The outline is a display area, not source-grid resolution or a surveyed farm.`);
 }
 $('outlook-footnote').textContent=state.layer==='soil'?'Soil properties stay static. SoilGrids is a 250 m model estimate, not a field soil test.':future?'Climate scenarios, not weather forecasts. The range is model spread, not a probability. No field-level hotspots are inferred.':'Observed regional data. May–September is a planning window, not the winter-wheat growing season.';
}
function renderTrend(){const box=$('trend-card'),d=state.detect;if(!box||!d){if(box)box.hidden=true;return;}
 const t=d.trends.find(x=>x.id==='temperature'),r=d.trends.find(x=>x.id==='rainfall'),m=d.trends.find(x=>x.id==='soil_moisture');
 const up=t&&t.verdict==='increasing',confirmed=/Temperature supported/.test(d.buddy_check||'');
 box.hidden=false;
 box.innerHTML=`<div><span class="eyebrow">MEASURED SINCE 1981 · NASA POWER</span><strong>${up?`Temperature up ${fmt(t.value,2)} °C per decade`:'No clear temperature trend'}</strong><p>${up&&confirmed?'Confirmed by the grid cell 0.5° north and by starting the test in 1991. ':''}Rain and July soil moisture show no clear trend.</p></div><details><summary>How we know</summary><div class="detail-copy"><p>Temperature p-value ${esc(t?.p_value)} · rain p-value ${esc(r?.p_value)} · July soil moisture p-value ${esc(m?.p_value)}.</p><p>${esc(d.source)}</p><p>${esc(m?.source||'')}</p><p>${esc(d.note)}</p>${d.data_quality?`<p>Data quality · ${esc(d.data_quality.text)}</p>`:''}</div></details>`;}
function seasonOptions(d){const driest=d.driest_years.power,all=Array.from({length:45},(_,i)=>2025-i);
 const label=y=>`${y}${y===d.highlight_year?' · 2012 dry year':''} · ${fmt(d.rain_by_year_mm.power[y],0)} mm`;
 return `<optgroup label="Driest May to September in NASA POWER">${driest.map(y=>`<option value="${y}" ${y===d.year?'selected':''}>${label(y)}</option>`).join('')}</optgroup><optgroup label="Every year, 1981 to 2025">${all.map(y=>`<option value="${y}" ${y===d.year&&!driest.includes(y)?'selected':''}>${label(y)}</option>`).join('')}</optgroup>`;}
function renderSeason(){const box=$('season-card'),d=state.season;if(!box||!d){if(box)box.hidden=true;return;}
 box.hidden=false;const p=d.sources.power,i=d.sources.imerg,r=d.root_zone_july_m3m3,nr=d.normal_root_zone_july_m3m3;
 const sign=v=>v==null?'':(v>=0?'+':'')+fmt(v,0);
 box.innerHTML=`<div class="season-head"><div><span class="eyebrow">REPLAY A PAST SEASON · MEASURED, NOT MODELLED</span><strong>May to September ${d.year}${d.year===d.highlight_year?' · the 2012 dry year':''}</strong></div><label class="sr-only" for="season-year">Past year</label><select id="season-year">${seasonOptions(d)}</select></div>
 <ul class="season-facts"><li><span>Rain, NASA POWER</span><strong>${fmt(p.rain_mm,0)} mm · ${sign(p.rain_change_mm)} mm vs normal · driest rank ${p.dryness_rank} of ${p.dryness_of}</strong></li>
 <li><span>Rain, GPM IMERG</span><strong>${i?`${fmt(i.rain_mm,0)} mm · ${sign(i.rain_change_mm)} mm vs normal · driest rank ${i.dryness_rank} of ${i.dryness_of}`:'Not available before 1999'}</strong></li>
 <li><span>Temperature</span><strong>${fmt(d.temp_c,1)} °C · ${d.temp_change_c>=0?'+':''}${fmt(d.temp_change_c,2)} °C vs normal</strong></li>
 <li><span>Degree days above 10 °C</span><strong>${fmt(d.degree_days_above_10c,0)} vs ${fmt(d.normal_degree_days_above_10c,0)} normal</strong></li>
 <li><span>Longest dry spell</span><strong>${fmt(p.dry_spell_days,0)} days vs ${fmt(p.normal_dry_spell_days,0)} normal (POWER)</strong></li>
 <li><span>July soil moisture, 40 to 100 cm</span><strong>${r?`${fmt(r['40-100 cm'],3)} vs ${fmt(nr['40-100 cm'],3)} m³/m³ (GLDAS)`:'Not available before 2000'}</strong></li></ul>
 <details><summary>How we know</summary><div class="detail-copy"><p>${esc(d.note)}</p><p>${esc(d.method)}</p></div></details>`;
 $('season-year').onchange=e=>loadSeason(Number(e.target.value));}
function renderYieldModel(){const box=$('yield-model-card'),d=state.yieldModel;if(!box||!d){if(box)box.hidden=true;return;}
 box.hidden=false;const c=d.crops.corn,ex=d.example,miss=c.held_out_2012;
 const row=k=>{const x=d.crops[k];return `<li><span>${k==='corn'?'Corn':k==='soybean'?'Soybean':'Winter wheat'} (${esc(x.window)})</span><strong>${x.beats_no_change?`Beats no change · skill ${fmt(x.skill_leave_one_year_out,3)} and ${fmt(x.skill_5_year_blocks,3)}`:`Does not beat no change · adjustment stays 1`}</strong></li>`;};
 box.innerHTML=`<div><span class="eyebrow">CLIMATE YIELD CHECK · DERIVED · TESTED ON ESSEX COUNTY 1981 TO 2025</span><strong>Corn yield adjusted for climate, soybean and wheat not</strong><p>We fit Essex County yields against NASA rain and heat, then tested on years the model had not seen. Only corn did better than assuming no change, and only modestly.</p></div>
 <ul class="season-facts">${['corn','soybean','wheat'].map(row).join('')}</ul>
 <div class="climate-note miss"><div class="eyebrow">WHERE IT WAS WRONG</div><strong>2012 · predicted ${fmt(miss.predicted_pct,1)}% for Essex corn, real ${miss.actual_pct>=0?'+':''}${fmt(miss.actual_pct,1)}%</strong><small>The model expected a dry-year loss. Essex corn finished above its trend. Rain and heat alone do not explain every season.</small></div>
 ${ex&&ex.low_bu_ac!=null?`<div class="climate-note mixed"><div class="eyebrow">EXAMPLE · ${ex.year} · DERIVED</div><strong>Corn in ${esc(ex.rotation)} · ${fmt(ex.low_bu_ac,0)} to ${fmt(ex.high_bu_ac,0)} bu/ac</strong><small>${esc(ex.calc)}. A climate scenario range, not a forecast.</small></div>`:''}
 <details><summary>How we know</summary><div class="detail-copy"><p>Error on unseen years ${fmt(c.rmse_model_pct,1)}% for corn against ${fmt(c.rmse_no_change_pct,1)}% for no change. About ${fmt(c.per_100mm_rain_pct,1)}% more corn per extra 100 mm of May to September rain, ${fmt(c.per_100_degree_days_pct,2)}% per 100 extra degree days.</p><p>${esc(d.method)}</p><p>${esc(d.source)}</p><p>${esc(d.limits)}</p></div></details>`;}
async function loadSeason(year){try{state.season=await jsonGet(`/api/season/harrow?year=${year}`);}catch(e){state.season=null;}renderSeason();}
function updateMetrics(){
 const year=selected();
 $('metric-strip').innerHTML=['temperature','precipitation','humidity','soil_moisture'].map(key=>{
  const m=year.metrics[key],meta=layers[key],base=state.timeline.baseline[key],missing=m.value===null;
  const change=missing?null:m.value-base.value;
  const changeText=change===null?'Historical values available through 2025':`${change>=0?'+':''}${fmt(change,meta.decimals)} ${meta.unit} vs ${key==='soil_moisture'?'2000–20 July':'1991–2020'}`;
  const detail=missing?'No future soil-moisture model connected':year.kind==='projection'?`${fmt(m.low,meta.decimals)}–${fmt(m.high,meta.decimals)} ${meta.unit} · model range`:key==='soil_moisture'?'July · 0–10 cm · GLDAS':'May–September · NASA POWER';
  return `<div class="metric-tile ${state.layer===key?'selected':''}" data-metric="${key}"><div class="metric-tile-heading">${icon(meta.icon)}${esc(meta.short)}</div><strong class="${missing?'unavailable':''}">${missing?'Not projected':fmt(m.value,meta.decimals)} ${missing?'':`<small>${esc(meta.unit)}</small>`}</strong><p>${esc(detail)}</p>${missing?'':`<span class="metric-change">${esc(changeText)}</span>`}</div>`;
 }).join('');
 animateContent($('metric-strip'));
}
function updateChart(){
 const chart=$('timeline-chart');
 if(!chart.querySelector('#timeline-cursor'))chart.innerHTML='<svg viewBox="0 0 600 45" preserveAspectRatio="none"></svg><span id="timeline-cursor" class="timeline-cursor"><i></i></span>';
 const plot=chart.querySelector('svg'),cursor=$('timeline-cursor');layoutAxis();cursor.style.left=axisX(state.year)+'px';
 if(state.layer==='soil'){plot.innerHTML='<path d="M0 25H600" stroke="#a5ba91" stroke-dasharray="4 5"/><text x="300" y="18" text-anchor="middle" fill="#93a080" stroke="none" font-family="DM Sans" font-size="9">Static soil reference · unchanged across years</text>';cursor.querySelector('i').style.top='55%';return;}
 const [min,max]=rangeFor(state.layer),x=i=>axisX(FIRST_YEAR+i)/Math.max(1,chart.getBoundingClientRect().width)*600,y=v=>42-(v-min)/(max-min)*36;
 const series=state.timeline.years.map(r=>r.metrics[state.layer]);
 function path(indices,key){return indices.map((i,j)=>`${j?'L':'M'}${x(i).toFixed(2)},${y(series[i][key]).toFixed(2)}`).join(' ');}
 const historical=series.map((m,i)=>i).filter(i=>FIRST_YEAR+i<=LAST_OBSERVED&&series[i].value!==null),projected=series.map((m,i)=>i).filter(i=>FIRST_YEAR+i>LAST_OBSERVED&&series[i].value!==null);
 const band=projected.length?path(projected,'low')+' '+projected.slice().reverse().map(i=>`L${x(i)},${y(series[i].high)}`).join(' ')+'Z':'';
 cursor.querySelector('i').style.top=(series[state.year-FIRST_YEAR].value===null?50:y(series[state.year-FIRST_YEAR].value)/45*100)+'%';
 const divider=((axisX(LAST_OBSERVED)+axisX(LAST_OBSERVED+1))/2/Math.max(1,chart.getBoundingClientRect().width)*600).toFixed(1);
 plot.innerHTML=`<path d="M${divider} 0V45" stroke="#d4dec9" stroke-dasharray="3 4"/>${band?`<path d="${band}" fill="#e4ebd7" stroke="none"/>`:''}<path d="${path(historical,'value')}" stroke="#7b9d65" fill="none"/>${projected.length?`<path d="${path(projected,'value')}" stroke="#a9a36e" stroke-dasharray="4 4" fill="none"/>`:''}${series.map((m,i)=>m.value===null?'':`<circle cx="${x(i)}" cy="${y(m.value)}" r="${state.year===FIRST_YEAR+i?3.5:2}" fill="${state.year===FIRST_YEAR+i?'#315b39':'#a7bc91'}" stroke="white"/>`).join('')}`;
}
function setYear(year,{stop=true}={}){
 state.year=Math.max(FIRST_YEAR,Math.min(lastYear(),Number(year)));if(stop)pause();
 state.request++;state.controller?.abort();markUpdating();
 $('year-range').value=state.year;$('year-range').setAttribute('aria-valuetext',`${state.year}, ${state.year<=2025?'observed history':'climate projection'}`);
 document.querySelectorAll('.year-tick').forEach(b=>{b.classList.toggle('active',+b.dataset.year===state.year);b.setAttribute('aria-pressed',String(+b.dataset.year===state.year));});
 $('previous-year').disabled=state.year===FIRST_YEAR;$('next-year').disabled=state.year===lastYear();
 updateMap();updateMetrics();updateChart();clearTimeout(state.pending);state.pending=setTimeout(loadRecommendations,180);
}
function pause(){if(state.timer)clearInterval(state.timer);state.timer=null;$('play-icon').textContent='▶';$('play-label').textContent='Play';$('play-timeline').setAttribute('aria-pressed','false');$('play-timeline').setAttribute('aria-label','Play timeline');}
function play(){
 if(state.timer){pause();return;}
 if(state.year===lastYear())setYear(FIRST_YEAR,{stop:false});
 $('play-icon').textContent='Ⅱ';$('play-label').textContent='Pause';$('play-timeline').setAttribute('aria-pressed','true');$('play-timeline').setAttribute('aria-label','Pause timeline');
 state.timer=setInterval(()=>{if(state.year===lastYear()){pause();return;}setYear(state.year+1,{stop:false});},1800);
}
function cropVisual(name){const n=name.toLowerCase();return n.includes('corn')||n==='maize'?['corn','Corn','corn']:n.includes('soy')?['soy','Soybean','soybean']:['wheat','Wheat','wheat'];}
function sourceAnchors(text){return [...new Set((text||'').match(/https?:\/\/[^\s)]+/g)||[])].map((url,i)=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Source ${i+1} ↗</a>`).join(' · ');}
function checkLine(c,need){const label={trial:'Trial, 5-year average','long-term trial':'Trial, long-term average','regional average':'Essex regional average, not trial'}[c.label]||c.label;return `<li class="${c.meets?'meets':'misses'}">${esc(label)} ${fmt(c.bu_ac,1)} bu/ac · ${c.meets?'meets':'short by '+fmt(c.shortfall_bu_ac,1)} · ${fmt(c.per_year_average_bu_ac,1)} bu/ac a year over the whole rotation</li>`;}
function targetAnswer(q){if(!q)return '';return {all:'Yes, every trial figure meets it',some:'Depends on the figure',none:`No, short by ${fmt(q.best_shortfall_bu_ac,1)} bu/ac`,'no evidence':'No trial yield for this crop here'}[q.target_support]||'';}
function targetBlock(r){const q=r.quantity;if(!q)return '';return `<div class="target-check ${q.target_support==='all'?'ok':q.target_support==='some'?'mixed':'miss'}"><div class="eyebrow">WILL THIS ROTATION MEET MY TARGET OF ${fmt(q.need_bu_ac,0)} BU/AC?</div><strong>${esc(targetAnswer(q))}</strong>${q.checks?.length?`<ul>${q.checks.map(c=>checkLine(c,q.need_bu_ac)).join('')}</ul>`:''}<small>Compared with trial history only, in a year you grow ${esc(q.crop==='maize'?'corn':q.crop)} (${esc(q.crop_years||'')} years). Not a forecast.</small></div>`;}
function rotationCard(r,index){
 const advice=r.water_advice||{},low=advice.low_pct,high=advice.high_pct;
 const valid=Number.isFinite(low)&&Number.isFinite(high),scale=valid?Math.max(100,high):100,lo=valid?Math.max(0,low)/scale*100:0,hi=valid?Math.max(low,high)/scale*100:0,full=100/scale*100;
 const waterCrops=(advice.assessed_crops||[]).map(c=>cropVisual(c)[1].toLowerCase()).join(' & ');
 const quantity=targetBlock(r);
 const clover=r.id.includes('clover');
 return `<article data-rotation-id="${esc(r.id)}" class="rotation-card ${index===0?'top-pick':''}"><div class="rotation-card-top"><span class="rank-pill"><span class="rank-number">${index+1}</span>BY TRIAL EVIDENCE</span><span class="trial-tag">TRIAL-BASED ROTATION</span></div><div class="crop-sequence" aria-label="${esc(r.name)}">${r.crops.map((c,i)=>{const [id,label,cls]=cropVisual(c);return `${i?'<span class="sequence-arrow" aria-hidden="true">→</span>':''}<div class="crop-step ${cls}">${icon(id)}<span>${label}</span></div>`;}).join('')}</div>${clover?'<span class="clover-tag">+ Red clover cover crop</span>':''}<p class="rotation-label">${clover?'A cover crop fits after winter wheat.':r.crops.length===2?'A simple two-crop rotation.':'A diversified crop sequence.'}</p><section class="rain-advice" aria-label="Rain supply compared with crop needs"><div class="water-row"><span>Rain vs ${esc(waterCrops||'crop')} needs</span></div><h3>${valid?`${low}–${high}% covered`:'Not assessed'}</h3><div class="water-track" role="img" aria-label="${esc(advice.meaning||'No water check available')}"><span class="water-base" style="width:${lo}%"></span><span class="water-range" style="left:${lo}%;width:${hi-lo}%"></span>${valid&&high>100?`<span class="water-need-mark" style="left:${full}%"></span>`:''}</div><p class="water-parts">${esc(advice.range_parts||'')}</p><p class="water-meaning">${esc(advice.meaning||'No compatible water check.')}</p><p class="water-action">${esc(advice.action||'')}</p></section><div class="rotation-card-bottom"><span>${r.picked_crop_yield_bu_ac!=null?`Your crop in the trial <strong>${fmt(r.picked_crop_yield_bu_ac,0)} bu/ac</strong>`:`Trial score <strong>${fmt(r.score,1)}</strong>`}</span><span>${esc(state.year)} rain fit check ${fmt(r.planning_score,0)} / 100</span></div><p class="score-basis">${esc(r.score_basis||'')}</p>${r.rank_dry?`<p class="dry-rank"><strong>2012 dry-year rank ${r.rank_dry} of ${r.rank_dry_of}</strong> · this list is ordered by trial evidence. ${esc(r.rank_dry_reason||'')}</p>`:''}${r.climate_adjustment?`<div class="climate-note mixed"><div class="eyebrow">CORN IN ${esc(r.climate_adjustment.year)} · CLIMATE ADJUSTED · DERIVED</div><strong>${fmt(r.climate_adjustment.low_bu_ac,0)} to ${fmt(r.climate_adjustment.high_bu_ac,0)} bu/ac</strong><small>${esc(r.climate_adjustment.calc)}. Modest skill, tested on Essex 1981 to 2025. Not a forecast.</small></div>`:''}${quantity}<details><summary>Why this rotation?</summary><div class="detail-copy"><p>${esc(r.reason)}</p><p>GAEZ suitability index · ${esc(r.gaez_period)}: ${Object.entries(r.suitability||{}).map(([crop,s])=>`${esc(cropVisual(crop)[1])} ${fmt(s.percent,1)}`).join(' · ')}. Period-based, not an annual success probability.</p><p>${esc(r.soil)} ${sourceAnchors(r.soil_source)}</p><p>${esc(advice.range_explanation||'')} Rain only; irrigation and stored soil water are excluded. Winter-wheat water need is not evaluated over May–September.</p><ul>${r.yields.map(y=>`<li>${esc(y.crop)} · ${y.bu_ac==null?'not available':fmt(y.bu_ac,1)+' bu/ac'} · ${esc(y.status)}. ${y.calc&&y.status!=='MISSING'?esc(y.calc)+' ':''}${sourceAnchors(y.source)}</li>`).join('')}</ul>${(r.score_breakdown||[]).length?`<p>Trial score by crop · ${r.score_breakdown.map(b=>`${esc(b.crop)} ${fmt(b.trial_bu_ac,0)} of best ${fmt(b.best_bu_ac,0)} bu/ac = ${fmt(b.index,1)}`).join(' · ')}${(r.score_crops_missing||[]).length?` · not in score ${esc(r.score_crops_missing.join(', '))}`:''}</p>`:''}<p>Order follows trial evidence. Rain fit is a check on this year, not crop success probability. Historical trial index ${fmt(r.score,1)} out of 100. Crops with missing trial yields are left out of the index.</p>${r.score_calc?`<p>How the index is calculated · ${esc(r.score_calc)}</p>`:''}${r.quantity?.calc?`<p>How the target check is calculated · ${esc(r.quantity.calc)}</p>`:''}${r.revenue_calc?`<p>How revenue is calculated · ${esc(r.revenue_calc)}</p>`:''}${r.revenue?`<p>Historical-price reference ${esc(r.revenue)}. Gross revenue, not profit or future earnings.</p>`:''}</div></details></article>`;
}
function markUpdating(){
 $('panel-body').setAttribute('aria-busy','true');$('panel-body').classList.add('updating');
 $('results-count').textContent=`UPDATING ${state.year} OPTIONS`;
 $('option-nav').querySelectorAll('button').forEach(button=>button.disabled=true);
}
function showOption(index,direction=1){
 const rows=state.recommendations?.rotations||[];
 state.optionIndex=Math.max(0,Math.min(rows.length-1,index));
 if(!rows.length)return;
 const row=rows[state.optionIndex];
 $('panel-body').innerHTML=rotationCard(row,state.optionIndex);
 $('panel-body').querySelector('article').setAttribute('aria-label',`Recommendation ${state.optionIndex+1} of ${rows.length}`);
 $('option-count').textContent=`Option ${state.optionIndex+1} of ${rows.length}`;
 $('previous-option').disabled=state.optionIndex===0;$('next-option').disabled=state.optionIndex===rows.length-1;
 $('option-dots').innerHTML=rows.map((r,i)=>`<button class="option-dot ${i===state.optionIndex?'active':''}" aria-label="Show recommendation ${i+1}" aria-pressed="${i===state.optionIndex}" data-option="${i}"></button>`).join('');
 $('option-dots').querySelectorAll('button').forEach(button=>button.onclick=()=>showOption(+button.dataset.option,+button.dataset.option>state.optionIndex?1:-1));
 animateContent($('panel-body'),direction);
}
function renderTargetSummary(rows){const box=$('target-summary');if(!box)return;
 if(state.mode!=='priority'){box.hidden=true;return;}
 box.hidden=false;
 if(!state.crop){box.innerHTML='<div class="eyebrow">WILL THIS ROTATION MEET MY TARGET?</div><p>Pick a crop, then add a bu/ac target. Every option answers it at once.</p>';return;}
 if(state.target===null){box.innerHTML='<div class="eyebrow">WILL THIS ROTATION MEET MY TARGET?</div><p>Add a bu/ac target above to check every option at once.</p>';return;}
 box.innerHTML=`<div class="eyebrow">WILL THIS ROTATION MEET ${fmt(state.target,0)} BU/AC?</div><ul>${(rows||[]).map(r=>`<li><span>${esc(r.name)}</span><strong>${esc(targetAnswer(r.quantity))}</strong></li>`).join('')}</ul><small>Trial history only. Not a forecast.</small>`;}
function renderRecommendations(){
 const data=state.recommendations;
 $('recommendation-year').textContent=`${state.year} OUTLOOK`;
 $('option-nav').hidden=true;
 if(state.mode==='others'){renderOtherCrops();return;}
 if(state.mode==='priority'&&!state.crop){renderTargetSummary([]);$('results-count').textContent='YOUR CROP COMES FIRST';$('panel-body').innerHTML=`<div class="empty-state">${icon('target')}<strong>Start with your priority.</strong>Choose a crop above. Rotations show right away, ordered by trial yield. The target check is optional.</div>`;return;}
 if(!data)return;
 if(data.status==='unavailable'){$('results-count').textContent='OUTLOOK UNAVAILABLE';$('panel-body').innerHTML=`<div class="empty-state">${icon('info')}<strong>No invented predictions.</strong>${esc(data.message)}<button class="primary-button" data-view-history>Explore 2025 history</button></div>`;$('panel-body').querySelector('[data-view-history]').onclick=()=>setYear(2025);return;}
 const rows=data.rotations;$('results-count').textContent=state.mode==='priority'?(state.target?`${rows.length} OPTIONS · CHECKED AGAINST ${state.target} BU/AC`:`${rows.length} OPTIONS BY TRIAL YIELD · NO TARGET SET`):`${rows.length} OPTIONS BY TRIAL EVIDENCE`;renderTargetSummary(rows);
 if(rows.length){$('option-nav').hidden=false;showOption(state.optionIndex);}
 else $('panel-body').innerHTML='<div class="empty-state"><strong>No supported rotation.</strong>Try a different crop or reset your priority.</div>';
}
function cropGroup(c){if((c.group||'').startsWith('perennial')||c.ontario_status==='No')return 'collapsed';return 'open';}
function grownHere(c){return /^(Yes|Partly|Emerging|Pilots)/.test(c.ontario_status||'');}
function otherCropCard(c){const g=c.gaez,k=c.kaggle_climate_check;return `<article class="crop-card"><div class="crop-card-head"><strong>${esc(c.crop)}</strong><span class="trial-tag">SUITABILITY ONLY</span></div><dl><dt>Grown in Ontario</dt><dd>${esc(c.ontario_status)}</dd><dt>FAO GAEZ now and 2035</dt><dd>${g?`${fmt(g.si_2001_2020,0)} and ${fmt(g.si_2021_2040_ssp370,0)} out of 100`:'Not available'}</dd><dt>Kaggle climate check</dt><dd>${k?`${k.inside_count} of ${k.of} inside`:'Not in Kaggle'}</dd><dt>Rotation crop</dt><dd>${esc(c.rotation_crop)}</dd></dl>${g?.note?`<p class="crop-advice">GAEZ note · ${esc(g.note)}</p>`:''}${c.evidence_note?`<p class="crop-advice">${esc(c.evidence_note)}</p>`:''}<details><summary>Sources and notes</summary><div class="detail-copy">${g?.note?`<p>${esc(g.note)}</p>`:''}${c.ontario_source?`<p>${esc(c.ontario_source.replace(/https?:\/\/\S+/g,''))} ${sourceAnchors(c.ontario_source)}</p>`:''}${c.evidence_source?`<p>${sourceAnchors(c.evidence_source)}</p>`:''}${k?`<p>${esc(k.note)}</p>`:''}<p>${esc(c.label)}</p></div></details></article>`;}
function renderOtherCrops(){
 $('option-nav').hidden=true;$('target-summary').hidden=true;
 const d=state.crops;if(!d){$('panel-body').innerHTML='<div class="empty-state"><strong>Other crops are loading.</strong></div>';return;}
 const f=state.cropFilter,list=d.crops.filter(c=>(!f.grown||grownHere(c))&&(!f.gaez||(c.gaez&&c.gaez.si_2001_2020>=f.gaez)));
 const open=list.filter(c=>cropGroup(c)==='open'),closed=list.filter(c=>cropGroup(c)==='collapsed');
 $('results-count').textContent=`${list.length} OF ${d.crops.length} CROPS`;
 $('panel-body').innerHTML=`<div class="crop-filters"><label><input type="checkbox" id="filter-grown" ${f.grown?'checked':''}> Grown in Ontario</label><label>GAEZ suitability <select id="filter-gaez"><option value="0">Any</option><option value="50" ${f.gaez===50?'selected':''}>50 or more</option><option value="75" ${f.gaez===75?'selected':''}>75 or more</option></select></label></div><p class="crop-note">Rotation picks stay corn, soybean and wheat, the crops with Ontario trial yields. These crops show suitability only, with no bushels or revenue.</p>${open.map(otherCropCard).join('')||'<p class="crop-note">No annual crops match these filters.</p>'}${closed.length?`<details class="crop-collapsed"><summary>Perennials and crops not grown here (${closed.length})</summary>${closed.map(otherCropCard).join('')}</details>`:''}`;
 $('filter-grown').onchange=e=>{state.cropFilter.grown=e.target.checked;renderOtherCrops();};
 $('filter-gaez').onchange=e=>{state.cropFilter.gaez=Number(e.target.value);renderOtherCrops();};
}
async function loadRecommendations(){
 if(!state.timeline||state.activeLocation.id!=='harrow')return;
 const request=++state.request;state.controller?.abort();state.controller=new AbortController();
 if(state.mode==='others'){$('panel-body').setAttribute('aria-busy','false');$('panel-body').classList.remove('updating');renderRecommendations();return;}
 if(state.mode==='priority'&&!state.crop){state.recommendations=null;$('panel-body').setAttribute('aria-busy','false');$('panel-body').classList.remove('updating');renderRecommendations();return;}
 const params=new URLSearchParams({year:state.year});
 if(state.mode==='priority'&&state.crop)params.set('must_grow',state.crop);
 if(state.mode==='priority'&&state.target!==null)params.set('need_bu',state.target);
 markUpdating();
 try{
  const data=await jsonGet(`/api/recommendations/harrow?${params}`,state.controller.signal);
  if(request!==state.request)return;
  state.recommendations=data;state.optionIndex=0;renderRecommendations();
 }catch(error){
  if(error.name==='AbortError'||request!==state.request)return;
  state.recommendations=null;$('results-count').textContent='CONNECTION INTERRUPTED';
  $('panel-body').innerHTML=`<div class="empty-state">${icon('info')}<strong>Couldn’t load recommendations.</strong>${esc(error.message)}<button class="primary-button" id="retry-recommendations">Try again</button></div>`;
  $('retry-recommendations').onclick=loadRecommendations;
 }finally{if(request===state.request){$('panel-body').setAttribute('aria-busy','false');$('panel-body').classList.remove('updating');}}
}
function setMode(mode){
 pause();state.mode=mode;const priority=mode==='priority',others=mode==='others';
 $('priority-form').hidden=!priority;$('target-summary').hidden=!priority;
 ['recommendations','priority','others'].forEach(name=>{const active=name===mode;$(`tab-${name}`).classList.toggle('active',active);$(`tab-${name}`).setAttribute('aria-selected',String(active));$(`tab-${name}`).tabIndex=active?0:-1;});
 $('panel-body').setAttribute('aria-labelledby',`tab-${mode}`);
 $('panel-title').textContent=priority?'Will this rotation meet my target?':others?'What else could grow here?':'Rotations that held up in the trial.';
 $('panel-description').textContent=priority?'Pick a crop. Rotations with it show right away, ordered by its trial yield. A bu/ac target is optional and adds a check against trial history.':others?'Suitability only. No bushels, rotations or revenue for these crops.':'Ordered by trial evidence. This year’s rain is a check. We do not predict bushels.';
 updateTargetControl();
 loadRecommendations();
}
function setCrop(crop){state.crop=crop;$('yield-target').value='';$('priority-error').hidden=true;document.querySelectorAll('[data-crop]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.crop===crop)));state.target=null;updateTargetControl();loadRecommendations();}
function renderSourceTab(tab='data'){
 document.querySelectorAll('[data-source-tab]').forEach(button=>{const active=button.dataset.sourceTab===tab;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
 const heading=state.activeLocation.id!=='harrow'?'Harrow pilot sources':state.year<=2025?'Observed history':'Climate scenarios';
 const content={
  data:`<section class="source-section"><h3>${heading} · ${state.year}</h3><p>${state.activeLocation.id!=='harrow'?'No datasets are connected for the selected location. These links describe the Harrow pilot. ':''}Temperature, rain and humidity: May–September. Soil moisture: July, 0–10 cm. Soil profile: static regional reference.</p><ul class="source-links">${state.timeline.sources.map(source=>`<li><a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.name)} <span>↗</span></a></li>`).join('')}</ul><p class="source-small">The focus outline stays the same for comparison. POWER uses a 0.5° × 0.625° grid; GLDAS and NEX use 0.25°. The smaller display outline does not increase data resolution.</p></section>`,
  ranking:`<section class="source-section"><h3>Why an option comes first</h3><p>${esc(state.recommendations?.ranking_summary||'Trial evidence first, then your crop and target. Rain coverage and soil pH are checks.')}</p><p>A repeated option can be a genuine result when years remain in the same water-limited range. No options are shuffled just to create variation.</p><p>Rain coverage compares regional rain with FAO crop water-need ranges. A range of 50–89% means roughly 50–89 mm supplied for each 100 mm needed. It is not a success rate.</p></section>`,
  limits:`<section class="source-section"><h3>What the data cannot promise</h3><ul><li>Future years are climate scenarios, not weather forecasts. Ranges show five-model spread, not probabilities.</li><li>Winter-wheat water is unassessed in the May–September window. Rain checks omit irrigation and soil storage.</li><li>Trial yields refer to Woodslee, about 26 km away. Soil values are regional estimates, not field tests.</li><li>Order follows trial evidence first. Rain fit is a check. Year-specific heat damage and repeat-cropping penalties are not independently calibrated.</li><li>No future soil moisture, field-level heatmap or annual crop yield is invented.</li></ul></section>`
 };
 $('sources-content').innerHTML=content[tab];$('sources-content').scrollTop=0;
}
function openSources(){pause();renderSourceTab('data');$('sources-dialog').showModal();}
function updateTargetControl(){
 const support=state.timeline?.priority_crops?.[state.crop],unsupported=support&&!support.supported;
 $('yield-target').disabled=!state.crop||Boolean(unsupported);
 $('yield-target').placeholder=unsupported?'Yield reference unavailable':'e.g. 150';
 document.querySelector('label[for="yield-target"]').hidden=Boolean(unsupported);document.querySelector('.target-input').hidden=Boolean(unsupported);
 $('priority-form').querySelector('[type=submit]').innerHTML=(unsupported?'Show compatible rotations':'Check my target')+icon('arrow');
 $('priority-notice').hidden=!unsupported;
 $('priority-notice').textContent=unsupported?support.message+' Compatible rotations are shown without a yield target.':'';
 if(unsupported){state.target=null;$('yield-target').value='';}
}
function refreshLocations(){
 const select=$('location-select');select.querySelectorAll('option[data-custom]').forEach(option=>option.remove());
 for(const location of state.locations){const option=new Option(location.name,location.id);option.dataset.custom='true';select.add(option,select.querySelector('[value=add]'));}
}
function chooseLocation(id){
 const location=id==='harrow'?{id:'harrow',name:'Harrow, Ontario'}:state.locations.find(item=>item.id===id);
 if(!location)return;
 pause();clearTimeout(state.pending);state.request++;state.controller?.abort();state.activeLocation=location;
 $('location-select').value=id;$('add-location-panel').hidden=true;
 const connected=id==='harrow';$('dashboard').hidden=!connected;$('location-empty').hidden=connected;
 if(!connected){$('location-empty-title').textContent=location.name;return;}
 if(state.timeline){if(!state.map)initMap();requestAnimationFrame(()=>state.map?.invalidateSize({pan:false}));setYear(state.year);}
 else load();
}
function closeLocationForm(){ $('add-location-panel').hidden=true;$('location-select').value=state.activeLocation.id; }
function connectLocations(){
 try{const saved=JSON.parse(localStorage.getItem('fieldshift.locations')||'[]');state.locations=Array.isArray(saved)?saved.filter(item=>typeof item.id==='string'&&item.id.startsWith('custom-')&&typeof item.name==='string'&&Number.isFinite(item.lat)&&Number.isFinite(item.lon)&&Math.abs(item.lat)<=90&&Math.abs(item.lon)<=180):[];}catch{state.locations=[];}
 refreshLocations();
 $('location-select').onchange=()=>{const id=$('location-select').value;if(id==='add'){$('add-location-panel').hidden=false;$('location-form-error').hidden=true;$('location-name').focus();}else chooseLocation(id);};
 $('cancel-location').onclick=closeLocationForm;$('return-harrow').onclick=()=>chooseLocation('harrow');
 $('add-location-form').onsubmit=event=>{
  event.preventDefault();const name=$('location-name').value.trim(),lat=Number($('location-lat').value),lon=Number($('location-lon').value);
  const duplicate=[{name:'Harrow, Ontario'},...state.locations].some(location=>location.name.toLowerCase()===name.toLowerCase());
  if(!name||!$('location-lat').value||!$('location-lon').value||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180||duplicate){$('location-form-error').textContent=duplicate?'Choose a different location name.':'Enter a name and valid latitude/longitude.';$('location-form-error').hidden=false;return;}
  const location={id:'custom-'+crypto.randomUUID(),name,lat,lon};state.locations.push(location);
  try{localStorage.setItem('fieldshift.locations',JSON.stringify(state.locations));}catch{/* Session-only bookmarks remain usable. */}
  refreshLocations();$('add-location-form').reset();chooseLocation(location.id);
 };
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('add-location-panel').hidden){closeLocationForm();$('location-select').focus();}});
 document.addEventListener('click',event=>{if(!event.target.closest('.location-control')&&!$('add-location-panel').hidden)closeLocationForm();});
}
function buildYearTicks(){const n=yearCount(),labelled=y=>y===FIRST_YEAR||y===lastYear()||y%5===0;
 $('year-range').min=FIRST_YEAR;$('year-range').max=lastYear();$('year-ticks').style.setProperty('--years',n);
 $('year-ticks').innerHTML=Array.from({length:n},(_,i)=>FIRST_YEAR+i).map(y=>`<button class="year-tick ${y===state.year?'active':''} ${labelled(y)?'':'unlabelled'}" data-year="${y}" aria-label="Show ${y}">${labelled(y)?y:'<span aria-hidden="true">·</span>'}</button>`).join('');
 document.querySelectorAll('[data-year]').forEach(b=>b.onclick=()=>setYear(b.dataset.year));
 layoutAxis();window.addEventListener('resize',()=>{layoutAxis();updateChart();});
 const head=document.querySelector('.timeline-heading h3');if(head)head.textContent=`Five years back. ${lastYear()-LAST_OBSERVED} years ahead.`;}
function connectControls(){
 document.querySelectorAll('[data-layer]').forEach(b=>b.addEventListener('click',()=>{
  state.layer=b.dataset.layer;document.querySelectorAll('[data-layer]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});updateMap();updateMetrics();updateChart();
 }));
 $('year-range').addEventListener('input',e=>setYear(e.target.value));
 $('previous-year').onclick=()=>setYear(state.year-1);$('next-year').onclick=()=>setYear(state.year+1);$('play-timeline').onclick=play;
 $('view-history').onclick=()=>setYear(2025);
 $('previous-option').onclick=()=>showOption(state.optionIndex-1,-1);$('next-option').onclick=()=>showOption(state.optionIndex+1,1);
 $('option-nav').addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();showOption(state.optionIndex+(event.key==='ArrowRight'?1:-1));}});
 $('tab-recommendations').onclick=()=>setMode('recommendations');
 $('tab-priority').onclick=()=>setMode('priority');$('tab-others').onclick=()=>setMode('others');
 document.querySelectorAll('.panel-tab[role=tab]').forEach(b=>b.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const order=['recommendations','priority','others'];setMode(order[(order.indexOf(state.mode)+(e.key==='ArrowRight'?1:2))%3]);$(`tab-${state.mode}`).focus();}}));
 document.querySelectorAll('[data-crop]').forEach(b=>b.onclick=()=>setCrop(b.dataset.crop));
 $('priority-form').onsubmit=e=>{
  e.preventDefault();const value=$('yield-target').value,number=value===''?null:Number(value);
  if(!state.crop||number!==null&&(!Number.isFinite(number)||number<=0)){$('priority-error').textContent=!state.crop?'Choose a priority crop first.':'Enter a positive yield target in bu/ac.';$('priority-error').hidden=false;return;}
  state.target=number;$('priority-error').hidden=true;loadRecommendations();
 };
 $('reset-priority').onclick=()=>{state.crop=null;state.target=null;$('yield-target').value='';$('priority-error').hidden=true;document.querySelectorAll('[data-crop]').forEach(b=>b.setAttribute('aria-pressed','false'));updateTargetControl();loadRecommendations();};
 $('nav-sources').onclick=openSources;
 document.querySelectorAll('[data-source-tab]').forEach((button,index)=>{button.onclick=()=>renderSourceTab(button.dataset.sourceTab);button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const buttons=[...document.querySelectorAll('[data-source-tab]')],next=buttons[(index+(event.key==='ArrowRight'?1:2))%3];renderSourceTab(next.dataset.sourceTab);next.focus();}});});
 $('close-sources').onclick=()=>$('sources-dialog').close();
 $('sources-dialog').addEventListener('click',e=>{if(e.target===$('sources-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
 $('retry-load').onclick=load;
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
}
function dataControls(ready){
 document.querySelectorAll('.layer-button,#nav-sources,#tab-others,.year-tick,#year-range,#previous-year,#next-year,#play-timeline,#view-history,.panel-tab,[data-crop],#yield-target,#priority-form button').forEach(el=>el.disabled=!ready);
 if(ready)updateTargetControl();
}
async function load(){
 setError(null);
 try{
  const [timeline,pilot]=await Promise.all([jsonGet('/api/timeline/harrow'),jsonGet('/api/pilot')]);
  state.timeline=timeline;state.pilot=pilot;
  try{state.detect=await jsonGet('/api/detect/harrow');}catch(e){state.detect=null;}renderTrend();
  loadSeason(2012);
  try{state.yieldModel=await jsonGet('/api/climate-yield/harrow');}catch(e){state.yieldModel=null;}renderYieldModel();
  try{state.crops=await jsonGet('/api/crops/harrow');}catch(e){state.crops=null;}
  buildYearTicks();
  dataControls(true);if(state.activeLocation.id==='harrow'){if(!state.map)initMap();setYear(state.year);}
 }catch(error){setError('The cached field data couldn’t be loaded. '+error.message);$('data-badge').textContent='Data unavailable';$('panel-body').innerHTML='<div class="empty-state"><strong>Your data stays honest.</strong>Reconnect to the local API and try again. No sample predictions are being substituted.</div>';}
}
connectControls();
connectLocations();
// Disable controls until the dataset has loaded; the retry button stays available.
dataControls(false);
load();
