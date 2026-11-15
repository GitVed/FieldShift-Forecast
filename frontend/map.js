/* FieldShift: cached observations, explicit climate scenarios, transparent trial evidence. */
'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const state = {year:2026,layer:'temperature',mode:'recommendations',crop:null,target:null,timeline:null,pilot:null,detect:null,crops:null,cropFilter:{gaez:0},recommendations:null,map:null,cell:null,marker:null,request:0,controller:null,timer:null,pending:null,optionIndex:0,activeLocation:{id:'harrow',name:'Harrow, Ontario'},locations:[]};
const layers = {
 temperature:{name:'Growing-season temperature',short:'Temperature',unit:'°C',icon:'sun',decimals:1,low:'Cooler',high:'Warmer',palette:['#367fc2','#f1e9db','#cc4946']},
 precipitation:{name:'Growing-season rainfall',short:'Rainfall',unit:'mm',icon:'rain',decimals:0,low:'Drier',high:'Wetter',palette:['#e2dcf3','#a08bc9','#5d479c']},
 humidity:{name:'Average relative humidity',short:'Humidity',unit:'%',icon:'drop',decimals:0,low:'Lower',high:'Higher',palette:['#d9f0e7','#77b9ab','#237b79']},
 soil_moisture:{name:'July soil moisture · 0–10 cm',short:'Soil moisture',unit:'m³/m³',icon:'soil',decimals:3,low:'Drier',high:'Wetter',palette:['#ba8852','#e4d4af','#4778aa']},
 soil:{name:'Topsoil pH · 0–30 cm',short:'Soil profile',unit:'pH',icon:'leaf',decimals:1,low:'',high:'',palette:['#927957','#c8ad7f','#675333']}
};
const fmt=(value,places=1)=>value===null||value===undefined?'—':Number(value).toLocaleString('en-CA',{minimumFractionDigits:places,maximumFractionDigits:places});
// Bushels keep their decimal when the source has one (wheat 62.5 must not read as 63).
const bu=value=>value===null||value===undefined?'—':Number.isInteger(Number(value))?fmt(value,0):fmt(value,1);
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
 const polygon=field?.polygon;
 const width=polygon?.length>=4?Math.round(L.latLng(polygon[0]).distanceTo(L.latLng(polygon[1]))/10)*10:null;
 const height=polygon?.length>=4?Math.round(L.latLng(polygon[1]).distanceTo(L.latLng(polygon[2]))/10)*10:null;
 const fieldPopup=`<dl class="field-popup"><dt>Latitude</dt><dd>${fmt(location.lat,4)}°</dd><dt>Area</dt><dd>${width&&height?`${width} × ${height} m · ${fmt(width*height/10000,1)} ha`:'Not available'}</dd></dl>`;
 if(field?.polygon){L.polygon(field.polygon,{color:'#f4f1d0',weight:2,fillColor:'#d9e8a6',fillOpacity:.25}).addTo(state.map).bindPopup(fieldPopup);}
 if(field?.trial_site){L.circleMarker([field.trial_site.lat,field.trial_site.lon],{radius:7,color:'#fff',weight:2,fillColor:'#b5793b',fillOpacity:1}).addTo(state.map).bindTooltip('Woodslee rotation trial',{className:'grid-label',direction:'top'}).bindPopup(`<strong>Woodslee rotation trial</strong><br>${esc(field.trial_site.dms||'')}<br>A point, not a field boundary. About ${fmt(field.trial_site.distance_km,0)} km from the SAMPLE field. Trial yields come from here.`);}
 state.marker=L.marker([location.lat,location.lon],{icon:L.divIcon({className:'pilot-marker',html:`<div class="pilot-marker-body">${icon('leaf')}</div>`,iconSize:[32,32],iconAnchor:[16,30]})}).addTo(state.map);
 state.marker.bindTooltip('Harrow',{permanent:true,className:'grid-label',direction:'top',offset:[0,-24]});
 state.marker.bindPopup(fieldPopup);
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
function insightChart(id,points,unit,label,highlight=null){
 const rows=points.filter(p=>Number.isFinite(p[1])).sort((a,b)=>a[0]-b[0]);
 if(rows.length<2)return '<p>Not enough data to draw a chart.</p>';
 const w=640,h=180,left=48,right=18,top=18,bottom=34;
 const min=Math.min(...rows.map(p=>p[1])),max=Math.max(...rows.map(p=>p[1])),pad=(max-min)*.15||1,lo=min-pad,hi=max+pad;
 const x=y=>left+(y-rows[0][0])/(rows.at(-1)[0]-rows[0][0])*(w-left-right),y=v=>top+(hi-v)/(hi-lo)*(h-top-bottom);
 const path=rows.map((p,i)=>`${i?'L':'M'}${x(p[0]).toFixed(2)},${y(p[1]).toFixed(2)}`).join(' '),base=h-bottom;
 const active=rows.find(p=>p[0]===highlight);
 return `<figure class="insight-chart"><figcaption>${esc(label)}</figcaption><svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}, ${rows[0][0]} to ${rows.at(-1)[0]}, ${fmt(min,1)} to ${fmt(max,1)} ${esc(unit)}"><defs><linearGradient id="${id}-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#77a47a" stop-opacity=".4"/><stop offset="100%" stop-color="#77a47a" stop-opacity=".02"/></linearGradient></defs><path class="chart-area" d="${path} L${x(rows.at(-1)[0])},${base} L${left},${base} Z" fill="url(#${id}-fill)"/><path class="chart-line" d="${path}"/>${active?`<circle cx="${x(active[0])}" cy="${y(active[1])}" r="5" class="chart-point"><title>${active[0]}: ${fmt(active[1],1)} ${esc(unit)}</title></circle>`:''}<text x="${left-8}" y="${top+5}" text-anchor="end">${fmt(hi,0)}</text><text x="${left-8}" y="${base}" text-anchor="end">${fmt(lo,0)}</text><text x="${left}" y="${h-10}">${rows[0][0]}</text><text x="${w-right}" y="${h-10}" text-anchor="end">${rows.at(-1)[0]}</text></svg></figure>`;
}
function renderTrend(){const box=$('trend-card'),d=state.detect;if(!box||!d){if(box)box.hidden=true;return;}
 const t=d.trends.find(x=>x.id==='temperature'),up=t&&t.verdict==='increasing';
 box.hidden=false;
 box.innerHTML=`<div class="insight-stat"><span>Temperature since 1981</span><strong>${up?`+${fmt(t.value,2)} °C per decade`:'No clear trend'}</strong></div><p>Rain and July soil moisture show no clear trend.</p>`;
}
function seasonOptions(d){const driest=d.driest_years.power,all=Array.from({length:45},(_,i)=>2025-i);
 const label=y=>`${y}${y===d.highlight_year?' · 2012 dry year':''} · ${fmt(d.rain_by_year_mm.power[y],0)} mm`;
 return `<optgroup label="Driest May to September in NASA POWER">${driest.map(y=>`<option value="${y}" ${y===d.year?'selected':''}>${label(y)}</option>`).join('')}</optgroup><optgroup label="Every year, 1981 to 2025">${all.map(y=>`<option value="${y}" ${y===d.year&&!driest.includes(y)?'selected':''}>${label(y)}</option>`).join('')}</optgroup>`;}
function renderSeason(){const box=$('season-card'),d=state.season;if(!box||!d){if(box)box.hidden=true;return;}
 box.hidden=false;const p=d.sources.power,i=d.sources.imerg,r=d.root_zone_july_m3m3;
 box.innerHTML=`<div class="season-head"><strong>May to September ${d.year}</strong><label class="sr-only" for="season-year">Past year</label><select id="season-year">${seasonOptions(d)}</select></div>
 ${insightChart('season-rain',Object.entries(d.rain_by_year_mm.power).map(([year,value])=>[+year,value]),'mm','Growing-season rain · NASA POWER',d.year)}
 <div class="insight-numbers"><div><span>Rain · POWER</span><strong>${fmt(p.rain_mm,0)} mm</strong></div><div><span>Rain · IMERG</span><strong>${i?`${fmt(i.rain_mm,0)} mm`:'Not available before 1999'}</strong></div><div><span>Temperature</span><strong>${fmt(d.temp_c,1)} °C</strong></div><div><span>Longest dry spell</span><strong>${fmt(p.dry_spell_days,0)} days</strong></div><div><span>July soil moisture · 40–100 cm</span><strong>${r?`${fmt(r['40-100 cm'],3)} m³/m³`:'Not available before 2000'}</strong></div></div>`;
 $('season-year').onchange=e=>loadSeason(Number(e.target.value));}
function renderYieldModel(){const box=$('yield-model-card'),d=state.yieldModel;if(!box||!d){if(box)box.hidden=true;return;}
 box.hidden=false;const c=d.crops.corn,miss=c.held_out_2012;
 const points=Object.entries(d.projection_ranges_pct?.corn||{}).map(([year,v])=>[+year,v.median_pct]);
 box.innerHTML=`<p>Corn has a climate adjustment. Soybean and wheat keep their historical yields.</p>
 ${insightChart('corn-climate',points,'%','Corn yield change · median climate scenario')}
 <div class="insight-numbers"><div><span>Corn error on unseen years</span><strong>${fmt(c.rmse_model_pct,1)}%</strong></div><div><span>Without climate adjustment</span><strong>${fmt(c.rmse_no_change_pct,1)}%</strong></div><div><span>2012 model estimate</span><strong>${fmt(miss.predicted_pct,1)}%</strong></div><div><span>2012 observed change</span><strong>${miss.actual_pct>=0?'+':''}${fmt(miss.actual_pct,1)}%</strong></div></div><p class="insight-note">Derived climate scenario, not a yield guarantee. The model missed 2012.</p>`;
}
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
function checkLine(c,need){const label={trial:'Trial, 5-year average','long-term trial':'Trial, long-term average','regional average':'Essex regional average, not trial'}[c.label]||c.label;return `<li class="${c.meets?'meets':'misses'}">${esc(label)} ${bu(c.bu_ac)} bu/ac · ${c.meets?'meets':'short by '+fmt(c.shortfall_bu_ac,1)} · ${fmt(c.per_year_average_bu_ac,1)} bu/ac a year over the whole rotation</li>`;}
function targetAnswer(q){if(!q)return '';return {all:'Yes, every trial figure meets it',some:'Depends on the figure',none:`No, short by ${fmt(q.best_shortfall_bu_ac,1)} bu/ac`,'no evidence':'No trial yield for this crop here'}[q.target_support]||'';}
function targetBlock(r){
 const q=r.quantity;if(!q)return '';
 const figures=(q.checks||[]).map(c=>c.bu_ac),lo=Math.min(...figures),hi=Math.max(...figures);
 return `<div class="target-check ${q.target_support==='all'?'ok':q.target_support==='some'?'mixed':'miss'}"><div class="eyebrow">YOUR TARGET · ${bu(q.need_bu_ac)} BU/AC</div><strong>${esc(targetAnswer(q))}</strong>${figures.length?`<small>Historical yield: ${bu(lo)}${lo!==hi?'–'+bu(hi):''} bu/ac · ${q.checks.every(c=>c.label==='long-term trial')?'long-term average':'trial references'}</small>`:''}<small>Historical comparison is not a guaranteed yield.</small></div>`;
}
function rotationCard(r,index){
 const advice=r.water_advice||{},low=advice.low_pct,high=advice.high_pct;
 const valid=Number.isFinite(low)&&Number.isFinite(high),scale=valid?Math.max(100,high):100,lo=valid?Math.max(0,low)/scale*100:0,hi=valid?Math.max(low,high)/scale*100:0,full=100/scale*100;
 const waterCrops=(advice.assessed_crops||[]).map(c=>cropVisual(c)[1].toLowerCase()).join(' & ');
 return `<article data-rotation-id="${esc(r.id)}" class="rotation-card ${index===0?'top-pick':''}">
 <div class="rotation-card-top"><span class="rank-pill"><span class="rank-number">${index+1}</span>${r.order_basis==='2012 dry-year order'?'DRY-YEAR RANK':'TRIAL RANK'}</span><span class="trial-tag">HISTORICAL EVIDENCE</span></div>
 <div class="crop-sequence" aria-label="${esc(r.name)}">${r.crops.map((c,i)=>{const [id,label,cls]=cropVisual(c);return `${i?'<span class="sequence-arrow" aria-hidden="true">→</span>':''}<div class="crop-step ${cls}">${icon(id)}<span>${label}</span></div>`;}).join('')}</div>
 ${r.id.includes('clover')?'<span class="clover-tag">+ Red clover cover crop</span>':''}
 ${targetBlock(r)}
 <section class="rain-advice" aria-label="Rain supply compared with crop needs"><div class="water-row"><span>Rain vs ${esc(waterCrops||'crop')} needs</span></div><h3>${valid?`${low}–${high}% covered`:'Not assessed'}</h3><div class="water-track" role="img" aria-label="${esc(advice.meaning||'No water check available')}"><span class="water-base" style="width:${lo}%"></span><span class="water-range" style="left:${lo}%;width:${hi-lo}%"></span>${valid&&high>100?`<span class="water-need-mark" style="left:${full}%"></span>`:''}</div><p class="water-meaning">${valid?`${low}–${high} mm of rain for every 100 mm needed.`:'No compatible water check.'}</p><p class="water-action">${esc(advice.action||'')}</p></section>
 ${!r.quantity&&r.picked_crop_yield_bu_ac!=null?`<div class="rotation-card-bottom"><span>Your crop in the trial</span><strong>${bu(r.picked_crop_yield_bu_ac)} bu/ac</strong></div>`:''}
 <details><summary>Evidence &amp; details</summary><div class="detail-copy"><p>${esc(state.recommendations?.season_outlook?.text||r.reason)}</p><p>Yield-target comparisons take priority. Historical yields do not change with the year.</p>${r.tie_note?`<p class="tie-note">${esc(r.tie_note)}</p>`:''}<p>${esc(r.score_basis||'')}</p><p>${esc(advice.range_parts||'')}</p><p>Suitability · ${esc(r.gaez_period)}: ${Object.entries(r.suitability||{}).map(([crop,v])=>`${esc(cropVisual(crop)[1])} ${fmt(v.percent,1)}/100`).join(' · ')}. Not a success probability.</p><p>${esc(r.soil)} ${sourceAnchors(r.soil_source)}</p><ul>${(r.yields||[]).map(y=>`<li>${esc(y.crop)} · ${y.bu_ac==null?'not available':bu(y.bu_ac)+' bu/ac'} · ${esc(y.status)} ${sourceAnchors(y.source)}</li>`).join('')}</ul>${r.quantity?.checks?.length?`<ul>${r.quantity.checks.map(c=>checkLine(c,r.quantity.need_bu_ac)).join('')}</ul>`:''}${r.score_calc?`<p>${esc(r.score_calc)}</p>`:''}${r.quantity?.calc?`<p>${esc(r.quantity.calc)}</p>`:''}${r.revenue?`<p>${esc(r.revenue)}. Historical-price gross revenue, not profit.</p>`:''}</div></details></article>`;
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
function renderTargetSummary(){
 // The selected option already shows its target answer. Avoid a duplicate list.
 $('target-summary').hidden=true;
}

function renderRecommendations(){
 const data=state.recommendations;
 $('recommendation-year').textContent=state.mode==='others'?'SUITABILITY ONLY':`${state.year} OUTLOOK`;
 $('option-nav').hidden=true;
 if(state.mode==='others'){renderOtherCrops();return;}
 if(state.mode==='priority'&&!state.crop){renderTargetSummary([]);$('results-count').textContent='YOUR CROP COMES FIRST';$('panel-body').innerHTML=`<div class="empty-state">${icon('target')}<strong>Choose a crop.</strong>Add a yield target if you have one.</div>`;return;}
 if(!data)return;
 if(data.status==='unavailable'){$('results-count').textContent='OUTLOOK UNAVAILABLE';$('panel-body').innerHTML=`<div class="empty-state">${icon('info')}<strong>No invented predictions.</strong>${esc(data.message)}<button class="primary-button" data-view-history>Explore 2025 history</button></div>`;$('panel-body').querySelector('[data-view-history]').onclick=()=>setYear(2025);return;}
 const rows=data.rotations;{const note=$('panel-note');const text=data.season_outlook?`${state.year} · ${data.season_outlook.dry_leaning?'Dry-leaning · drought evidence first':'Typical rain · trial evidence first'}`:'Historical trial evidence';note.textContent=text;note.hidden=!text;}$('results-count').textContent=state.mode==='priority'?(state.target?`${rows.length} OPTIONS · CHECKED AGAINST ${state.target} BU/AC`:`${rows.length} OPTIONS FOR YOUR CROP`):`${rows.length} ROTATION OPTIONS`;renderTargetSummary(rows);
 if(rows.length){$('option-nav').hidden=false;showOption(state.optionIndex);}
 else $('panel-body').innerHTML='<div class="empty-state"><strong>No supported rotation.</strong>Try a different crop or reset your priority.</div>';
}
function cropGroup(c){if((c.group||'').startsWith('perennial')||c.ontario_status==='No')return 'collapsed';return 'open';}

function otherCropCard(c){const g=c.gaez;return `<article class="crop-card"><div class="crop-card-head"><strong>${esc(c.crop)}</strong><span class="trial-tag">SUITABILITY ONLY</span></div><dl><dt>Ontario growing</dt><dd>${esc(c.ontario_status)}</dd><dt>Current suitability</dt><dd>${g?`${fmt(g.si_2001_2020,0)} / 100`:'Not available'}</dd><dt>2035 suitability</dt><dd>${g?`${fmt(g.si_2021_2040_ssp370,0)} / 100`:'Not available'}</dd></dl><details><summary>Growing cautions &amp; sources</summary><div class="detail-copy">${g?.note?`<p>${esc(g.note)}</p>`:''}${c.evidence_note?`<p>${esc(c.evidence_note)}</p>`:''}${sourceAnchors(c.ontario_source)} ${sourceAnchors(c.evidence_source)}<p>GAEZ climate-period index, not a success rate. No verified rotation yield for this crop.</p></div></details></article>`;}

function renderOtherCrops(){
 $('option-nav').hidden=true;$('target-summary').hidden=true;$('panel-note').hidden=true;
 const d=state.crops;if(!d){$('panel-body').innerHTML='<div class="empty-state"><strong>Other crops are loading.</strong></div>';return;}
 const f=state.cropFilter,list=d.crops.filter(c=>!f.gaez||(c.gaez&&c.gaez.si_2001_2020>=f.gaez));
 const open=list.filter(c=>cropGroup(c)==='open'),closed=list.filter(c=>cropGroup(c)==='collapsed');
 $('results-count').textContent=`${list.length} OF ${d.crops.length} CROPS`;
 $('panel-body').innerHTML=`<div class="crop-filters"><label for="filter-gaez">Current suitability</label><select id="filter-gaez" aria-label="GAEZ suitability"><option value="0">Any</option><option value="50" ${f.gaez===50?'selected':''}>50 or more</option><option value="75" ${f.gaez===75?'selected':''}>75 or more</option></select></div><p class="crop-note">Suitability index, not yield or chance of success.</p>${open.map(otherCropCard).join('')||'<p class="crop-note">No annual crops match these filters.</p>'}${closed.length?`<details class="crop-collapsed"><summary>Perennials and crops not grown here (${closed.length})</summary>${closed.map(otherCropCard).join('')}</details>`:''}`;
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
 $('priority-form').hidden=!priority;$('target-summary').hidden=true;
 ['recommendations','priority','others'].forEach(name=>{const active=name===mode;$(`tab-${name}`).classList.toggle('active',active);$(`tab-${name}`).setAttribute('aria-selected',String(active));$(`tab-${name}`).tabIndex=active?0:-1;});
 $('panel-body').setAttribute('aria-labelledby',`tab-${mode}`);
 $('panel-title').textContent=priority?'Plan around your crop.':others?'Other crops.':'Compare your rotations.';
 $('panel-description').textContent=priority?'Choose a crop and an optional yield target.':others?'Explore climate suitability.':'Compare rotations for the selected year.';
 updateTargetControl();
 loadRecommendations();
}
function setCrop(crop){state.crop=crop;$('yield-target').value='';$('priority-error').hidden=true;document.querySelectorAll('[data-crop]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.crop===crop)));state.target=null;updateTargetControl();loadRecommendations();}
function renderSourceTab(tab='data'){
 document.querySelectorAll('[data-source-tab]').forEach(button=>{const active=button.dataset.sourceTab===tab;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
 const heading=state.activeLocation.id!=='harrow'?'Harrow pilot sources':state.year<=2025?'Observed history':'Climate scenarios';
 const content={
  data:`<section class="source-section"><h3>${heading} · ${state.year}</h3><p>${state.activeLocation.id!=='harrow'?'No datasets are connected for the selected location. These links describe the Harrow pilot. ':''}Temperature, rain and humidity: May–September. Soil moisture: July, 0–10 cm. Soil profile: static regional reference.</p><ul class="source-links">${state.timeline.sources.map(source=>`<li><a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.name)} <span>↗</span></a></li>`).join('')}</ul><p class="source-small">The focus outline stays the same for comparison. POWER uses a 0.5° × 0.625° grid; GLDAS and NEX use 0.25°. The smaller display outline does not increase data resolution.</p></section>`,
  ranking:`<section class="source-section"><h3>Why an option comes first</h3><p>${esc(state.recommendations?.season_outlook?.text||'NASA rain selects trial evidence order or dry-year order. Yield-target comparisons take priority.')}</p><p>Yield-target comparisons take priority. Dry-leaning years use drought evidence first; other years use historical trial yields. A repeated option can be the correct result.</p><p>Rain coverage compares regional rain with FAO crop water-need ranges. A range of 50–89% means roughly 50–89 mm supplied for each 100 mm needed. It is not a success rate.</p></section>`,
  limits:`<section class="source-section"><h3>What the data cannot promise</h3><ul><li>Future years are climate scenarios, not weather forecasts. Ranges show five-model spread, not probabilities.</li><li>Winter-wheat water is unassessed in the May–September window. Rain checks omit irrigation and soil storage.</li><li>Trial yields refer to Woodslee, about 26 km away. Soil values are regional estimates, not field tests.</li><li>Order follows the selected year’s rain classification and your crop target. Year-specific heat damage and repeat-cropping penalties are not independently calibrated.</li><li>No future soil moisture, field-level heatmap or annual crop yield is invented.</li></ul></section>`
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
