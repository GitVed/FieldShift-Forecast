/* FieldShift: cached observations, explicit climate scenarios, transparent trial evidence. */
'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const state = {year:2026,layer:'temperature',mode:'recommendations',crop:null,target:null,timeline:null,pilot:null,recommendations:null,map:null,cell:null,marker:null,request:0,controller:null,timer:null,pending:null,optionIndex:0};
const layers = {
 temperature:{name:'Growing-season temperature',short:'Temperature',unit:'°C',icon:'sun',decimals:1,low:'Cooler',high:'Warmer',palette:['#367fc2','#f1e9db','#cc4946']},
 precipitation:{name:'Growing-season rainfall',short:'Rainfall',unit:'mm',icon:'rain',decimals:0,low:'Drier',high:'Wetter',palette:['#e2dcf3','#a08bc9','#5d479c']},
 humidity:{name:'Average relative humidity',short:'Humidity',unit:'%',icon:'drop',decimals:0,low:'Lower',high:'Higher',palette:['#d9f0e7','#77b9ab','#237b79']},
 soil_moisture:{name:'July soil moisture · 0–10 cm',short:'Soil moisture',unit:'m³/m³',icon:'soil',decimals:3,low:'Drier',high:'Wetter',palette:['#ba8852','#e4d4af','#4778aa']},
 soil:{name:'Regional topsoil pH · 0–20 cm',short:'Soil profile',unit:'pH',icon:'leaf',decimals:1,low:'',high:'',palette:['#927957','#c8ad7f','#675333']}
};
const fmt=(value,places=1)=>value===null||value===undefined?'—':Number(value).toLocaleString('en-CA',{minimumFractionDigits:places,maximumFractionDigits:places});
// A display focus, not a native data cell or surveyed field boundary.
const FOCUS_BOUNDS=[[42.0056,-82.9583],[42.0656,-82.8783]];
const selected=()=>state.timeline?.years.find(r=>r.year===state.year);
function getMetric(year=selected(),layer=state.layer){
 if(layer==='soil')return {value:state.timeline?.soil.ph?.value,low:null,high:null,kind:'regional_estimate',source:'FAO HWSD2 regional estimate',window:'Static soil profile · 0–20 cm'};
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
 const tiles=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Imagery © <a href="https://www.esri.com/">Esri</a>, Vantor, Earthstar Geographics, GIS User Community'}).addTo(state.map);
 tiles.on('tileerror',()=>{$('basemap-note').hidden=false;});tiles.on('tileload',()=>{$('basemap-note').hidden=true;});
 state.marker=L.marker([location.lat,location.lon],{icon:L.divIcon({className:'pilot-marker',html:`<div class="pilot-marker-body">${icon('leaf')}</div>`,iconSize:[32,32],iconAnchor:[16,30]})}).addTo(state.map);
 state.marker.bindTooltip('Harrow, Ontario',{permanent:true,className:'grid-label',direction:'top',offset:[0,-24]});
 state.marker.bindPopup('<strong>Harrow pilot point</strong><br>42.0356° N, 82.9183° W<br>No surveyed field boundary is available.');
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
  $('map-unavailable').querySelector('span').textContent=state.layer==='soil_moisture'?'Explore measured July moisture in the historical view.':year.message||'Choose an observed year while the source data is unavailable.';
 }
 const detail=state.layer==='soil'?'FAO HWSD2 · regional estimate, not a field soil test':future?`${year.model_count}-model range ${fmt(m.low,meta.decimals)}–${fmt(m.high,meta.decimals)} ${meta.unit}`:`${m.source} · cached regional observation`;
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
 if(state.layer==='soil'){const soil=state.timeline.soil,sand=Number(soil.sand.value),silt=Number(soil.silt.value);$('legend-label').textContent='Soil texture';$('legend-right').textContent='0–20 cm';$('legend-ramp').style.background=`linear-gradient(90deg,#c5b88d 0% ${sand}%,#acbe8e ${sand}% ${sand+silt}%,#799777 ${sand+silt}% 100%)`;$('legend-min').textContent=`Sand ${fmt(sand,0)}%`;$('legend-max').textContent=`Silt ${fmt(silt,0)} · Clay ${fmt(soil.clay.value,0)}%`;}
 if(state.layer!=='soil'){
  const [lo,hi]=rangeFor(state.layer);$('legend-min').textContent=`${fmt(lo,meta.decimals)} ${meta.unit}`;$('legend-max').textContent=`${fmt(hi,meta.decimals)} ${meta.unit}`;
 }
 const grid=state.layer==='soil_moisture'?year.soil_moisture_footprint:year.footprint;
 $('grid-caption').textContent='Harrow focus area · regional point estimate, not a field scan';
 if(state.map){
  const color=missing||state.layer==='soil'?'#b4c3a7':colorFor(m.value,state.layer);
  const style={color,fillColor:color,fillOpacity:missing||state.layer==='soil'?0:.30,weight:2,dashArray:'5 5'};
  if(state.cell)state.cell.setStyle(style);
  else state.cell=L.rectangle(FOCUS_BOUNDS,style).addTo(state.map);
  if(!state.framed){state.map.fitBounds(FOCUS_BOUNDS,{padding:[48,48],maxZoom:12,animate:false});state.framed=true;}
  state.cell.bindPopup(`<strong>Harrow comparison focus</strong><br>${esc(meta.short)} · ${state.year}<br>${missing?'Data unavailable':`${fmt(m.value,meta.decimals)} ${esc(meta.unit)}`}<br>${esc(m.source||'Regional reference')}<br>The outline is a display area, not source-grid resolution or a surveyed farm.`);
 }
 $('outlook-footnote').textContent=state.layer==='soil'?'Soil properties stay static. This is a regional estimate, not a field soil test.':future?'Climate scenarios, not weather forecasts. The range is model spread, not a probability. No field-level hotspots are inferred.':'Observed regional data. May–September is a planning window, not the winter-wheat growing season.';
}
function updateMetrics(){
 const year=selected();
 $('metric-strip').innerHTML=['temperature','precipitation','humidity','soil_moisture'].map(key=>{
  const m=year.metrics[key],meta=layers[key],base=state.timeline.baseline[key],missing=m.value===null;
  const change=missing?null:m.value-base.value;
  const changeText=change===null?'Historical values available through 2025':`${change>=0?'+':''}${fmt(change,meta.decimals)} ${meta.unit} vs ${key==='soil_moisture'?'2000–20 July':'1991–2020'}`;
  const detail=missing?'Not forecast by current models':year.kind==='projection'?`${fmt(m.low,meta.decimals)}–${fmt(m.high,meta.decimals)} ${meta.unit} · model range`:key==='soil_moisture'?'July · 0–10 cm · GLDAS':'May–September · NASA POWER';
  return `<div class="metric-tile ${state.layer===key?'selected':''}" data-metric="${key}"><div class="metric-tile-heading">${icon(meta.icon)}${esc(meta.short)}</div><strong class="${missing?'unavailable':''}">${missing?'Not projected':fmt(m.value,meta.decimals)} ${missing?'':`<small>${esc(meta.unit)}</small>`}</strong><p>${esc(detail)}</p><span class="metric-change">${esc(changeText)}</span></div>`;
 }).join('');
 animateContent($('metric-strip'));
}
function updateChart(){
 const chart=$('timeline-chart');
 if(!chart.querySelector('#timeline-cursor'))chart.innerHTML='<svg viewBox="0 0 600 45" preserveAspectRatio="none"></svg><span id="timeline-cursor" class="timeline-cursor"><i></i></span>';
 const plot=chart.querySelector('svg'),cursor=$('timeline-cursor');cursor.style.left=((state.year-2021+.5)/10*100)+'%';
 if(state.layer==='soil'){plot.innerHTML='<path d="M0 25H600" stroke="#a5ba91" stroke-dasharray="4 5"/><text x="300" y="18" text-anchor="middle" fill="#93a080" stroke="none" font-family="DM Sans" font-size="9">Static soil reference · unchanged across years</text>';cursor.querySelector('i').style.top='55%';return;}
 const [min,max]=rangeFor(state.layer),x=i=>(i+.5)/10*600,y=v=>42-(v-min)/(max-min)*36;
 const series=state.timeline.years.map(r=>r.metrics[state.layer]);
 function path(indices,key){return indices.map((i,j)=>`${j?'L':'M'}${x(i).toFixed(2)},${y(series[i][key]).toFixed(2)}`).join(' ');}
 const historical=[0,1,2,3,4].filter(i=>series[i].value!==null),projected=[5,6,7,8,9].filter(i=>series[i].value!==null);
 const band=projected.length?path(projected,'low')+' '+projected.slice().reverse().map(i=>`L${x(i)},${y(series[i].high)}`).join(' ')+'Z':'';
 cursor.querySelector('i').style.top=(series[state.year-2021].value===null?50:y(series[state.year-2021].value)/45*100)+'%';
 plot.innerHTML=`<path d="M300 0V45" stroke="#d4dec9" stroke-dasharray="3 4"/>${band?`<path d="${band}" fill="#e4ebd7" stroke="none"/>`:''}<path d="${path(historical,'value')}" stroke="#7b9d65" fill="none"/>${projected.length?`<path d="${path(projected,'value')}" stroke="#a9a36e" stroke-dasharray="4 4" fill="none"/>`:''}${series.map((m,i)=>m.value===null?'':`<circle cx="${x(i)}" cy="${y(m.value)}" r="${state.year===2021+i?3.5:2}" fill="${state.year===2021+i?'#315b39':'#a7bc91'}" stroke="white"/>`).join('')}`;
}
function setYear(year,{stop=true}={}){
 state.year=Math.max(2021,Math.min(2030,Number(year)));if(stop)pause();
 state.request++;state.controller?.abort();markUpdating();
 $('year-range').value=state.year;$('year-range').setAttribute('aria-valuetext',`${state.year}, ${state.year<=2025?'observed history':'climate projection'}`);
 document.querySelectorAll('.year-tick').forEach(b=>{b.classList.toggle('active',+b.dataset.year===state.year);b.setAttribute('aria-pressed',String(+b.dataset.year===state.year));});
 $('previous-year').disabled=state.year===2021;$('next-year').disabled=state.year===2030;
 updateMap();updateMetrics();updateChart();clearTimeout(state.pending);state.pending=setTimeout(loadRecommendations,180);
}
function pause(){if(state.timer)clearInterval(state.timer);state.timer=null;$('play-icon').textContent='▶';$('play-label').textContent='Play';$('play-timeline').setAttribute('aria-pressed','false');$('play-timeline').setAttribute('aria-label','Play timeline');}
function play(){
 if(state.timer){pause();return;}
 if(state.year===2030)setYear(2021,{stop:false});
 $('play-icon').textContent='Ⅱ';$('play-label').textContent='Pause';$('play-timeline').setAttribute('aria-pressed','true');$('play-timeline').setAttribute('aria-label','Pause timeline');
 state.timer=setInterval(()=>{if(state.year===2030){pause();return;}setYear(state.year+1,{stop:false});},1800);
}
function cropVisual(name){const n=name.toLowerCase();return n.includes('corn')||n==='maize'?['corn','Corn','corn']:n.includes('soy')?['soy','Soybean','soybean']:['wheat','Wheat','wheat'];}
function sourceAnchors(text){return [...new Set((text||'').match(/https?:\/\/[^\s)]+/g)||[])].map((url,i)=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Source ${i+1} ↗</a>`).join(' · ');}
function rotationCard(r,index){
 const advice=r.water_advice||{},low=advice.low_pct,high=advice.high_pct;
 const valid=Number.isFinite(low)&&Number.isFinite(high),lo=valid?Math.max(0,Math.min(100,low)):0,hi=valid?Math.max(lo,Math.min(100,high)):0;
 const scope=(advice.assessed_crops||[]).map(c=>cropVisual(c)[1]).join(' & ');
 const quantity=r.quantity?`<p class="quantity-note ${r.quantity.meets===false?'shortfall':''}">${esc(r.quantity.text)}<br><small>Historical trial comparison, not a forecast.</small></p>`:'';
 const clover=r.id.includes('clover');
 return `<article data-rotation-id="${esc(r.id)}" class="rotation-card ${index===0?'top-pick':''}"><div class="rotation-card-top"><span class="rank-pill"><span class="rank-number">${index+1}</span>${index===0?'LEADING OPTION':'ALTERNATIVE'}</span><span class="trial-tag">RAIN-LED PLANNING</span></div><div class="crop-sequence" aria-label="${esc(r.name)}">${r.crops.map((c,i)=>{const [id,label,cls]=cropVisual(c);return `${i?'<span class="sequence-arrow" aria-hidden="true">→</span>':''}<div class="crop-step ${cls}">${icon(id)}<span>${label}</span></div>`;}).join('')}</div>${clover?'<span class="clover-tag">+ Red clover cover crop</span>':''}<section class="rain-advice" aria-label="Rain supply compared with crop needs"><div class="water-row"><span>Rain supply vs crop needs</span></div><h3>${valid?`${low}–${high}% covered`:'Not assessed'}</h3><div class="water-track" role="img" aria-label="${esc(advice.meaning||'No water check available')}"><span class="water-base" style="width:${lo}%"></span><span class="water-range" style="left:${lo}%;width:${hi-lo}%"></span></div><div class="water-labels"><span>Estimated rain supply</span><span>100% of needs</span></div><p class="water-meaning">${esc(advice.meaning||'No compatible water check.')}</p><p class="water-action">${esc(advice.action||'')}</p><p class="water-scope">${esc(scope)} assessed${advice.unassessed_crops?.length?' · wheat water not assessed':''}</p></section>${quantity}<details><summary>Why this option?</summary><div class="detail-copy"><p>${esc(r.rank_explanation)}</p><p>${esc(advice.range_explanation)} This is not a chance of crop success. Irrigation and stored soil water are excluded.</p><p>Trial soil evidence: ${esc(r.soil)} ${sourceAnchors(r.soil_source)}</p><ul>${r.yields.map(y=>`<li>${esc(y.crop)}: ${fmt(y.bu_ac,0)} bu/ac · ${esc(y.status)}. ${sourceAnchors(y.source)}</li>`).join('')}</ul><p>Trial yields and period-based GAEZ values are historical references, not annual yield predictions.</p></div></details></article>`;
}
function markUpdating(){
 $('panel-body').setAttribute('aria-busy','true');$('panel-body').classList.add('updating');
 $('results-count').textContent=`UPDATING ${state.year} OPTIONS`;
 $('option-nav').querySelectorAll('button').forEach(button=>button.disabled=true);
}
function showOption(index,direction=1){
 const rows=state.recommendations?.rotations.slice(0,3)||[];
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
function renderRecommendations(){
 const data=state.recommendations;
 $('recommendation-year').textContent=`${state.year} OUTLOOK`;
 $('option-nav').hidden=true;$('ranking-note').hidden=true;
 if(state.mode==='priority'&&!state.crop){$('results-count').textContent='YOUR CROP COMES FIRST';$('panel-body').innerHTML=`<div class="empty-state">${icon('target')}<strong>Start with your priority.</strong>Choose a crop above. We’ll find supported rotations that make room for it.</div>`;return;}
 if(!data)return;
 if(data.status==='unavailable'){$('results-count').textContent='OUTLOOK UNAVAILABLE';$('panel-body').innerHTML=`<div class="empty-state">${icon('info')}<strong>No invented predictions.</strong>${esc(data.message)}<button class="primary-button" data-view-history>Explore 2025 history</button></div>`;$('panel-body').querySelector('[data-view-history]').onclick=()=>setYear(2025);return;}
 const rows=data.rotations.slice(0,3);$('results-count').textContent=`${rows.length} DATA-LED OPTIONS`;
 if(rows.length){$('option-nav').hidden=false;showOption(state.optionIndex);}
 else $('panel-body').innerHTML='<div class="empty-state"><strong>No supported rotation.</strong>Try a different crop or reset your priority.</div>';
 $('ranking-note').textContent=data.ranking_summary||'';
 $('ranking-note').hidden=!data.rotations.length;

}
async function loadRecommendations(){
 if(!state.timeline)return;
 const request=++state.request;state.controller?.abort();state.controller=new AbortController();
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
 pause();state.mode=mode;const priority=mode==='priority';
 $('priority-form').hidden=!priority;
 ['recommendations','priority'].forEach(name=>{const active=name===mode;$(`tab-${name}`).classList.toggle('active',active);$(`tab-${name}`).setAttribute('aria-selected',String(active));$(`tab-${name}`).tabIndex=active?0:-1;});
 $('panel-body').setAttribute('aria-labelledby',`tab-${mode}`);
 $('nav-overview').classList.toggle('active',!priority);$('nav-priority').classList.toggle('active',priority);
 $('panel-eyebrow').textContent=priority?'YOUR CROP. A STRONGER PLAN.':'GROW WITH A PLAN';
 $('panel-title').textContent=priority?'Make room for your priority.':'A rotation for what’s next.';
 $('panel-description').textContent=priority?'Build a crop rotation around your choice.':'Evidence-led options for your next growing seasons.';
 loadRecommendations();
}
function setCrop(crop){state.crop=crop;$('yield-target').value='';$('priority-error').hidden=true;document.querySelectorAll('[data-crop]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.crop===crop)));state.target=null;loadRecommendations();}
function renderSourceTab(tab='data'){
 document.querySelectorAll('[data-source-tab]').forEach(button=>{const active=button.dataset.sourceTab===tab;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
 const heading=state.year<=2025?'Observed history':'Climate scenarios';
 const content={
  data:`<section class="source-section"><h3>${heading} · ${state.year}</h3><p>Temperature, rain and humidity: May–September. Soil moisture: July, 0–10 cm. Soil profile: static regional reference.</p><ul class="source-links">${state.timeline.sources.map(source=>`<li><a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.name)} <span>↗</span></a></li>`).join('')}</ul><p class="source-small">The focus outline stays the same for comparison. POWER uses a 0.5° × 0.625° grid; GLDAS and NEX use 0.25°. The smaller display outline does not increase data resolution.</p></section>`,
  ranking:`<section class="source-section"><h3>Why an option comes first</h3><p>${esc(state.recommendations?.ranking_summary||'Rain coverage, soil pH, historical trial evidence and any selected crop or yield target determine the planning order.')}</p><p>A repeated option can be a genuine result when years remain in the same water-limited range. No options are shuffled just to create variation.</p><p>Rain coverage compares regional rain with FAO crop water-need ranges. A range of 50–89% means roughly 50–89 mm supplied for each 100 mm needed. It is not a success rate.</p></section>`,
  limits:`<section class="source-section"><h3>What the data cannot promise</h3><ul><li>Future years are climate scenarios, not weather forecasts. Ranges show five-model spread, not probabilities.</li><li>Winter-wheat water is unassessed in the May–September window. Rain checks omit irrigation and soil storage.</li><li>Trial yields refer to Woodslee, about 25 km away. Soil values are regional estimates, not field tests.</li><li>Ranking is rain-led; year-specific heat damage and repeat-cropping penalties are not independently calibrated.</li><li>No future soil moisture, field-level heatmap or annual crop yield is invented.</li></ul></section>`
 };
 $('sources-content').innerHTML=content[tab];$('sources-content').scrollTop=0;
}
function openSources(){pause();renderSourceTab('data');$('sources-dialog').showModal();}
function connectControls(){
 document.querySelectorAll('[data-layer]').forEach(b=>b.addEventListener('click',()=>{
  state.layer=b.dataset.layer;document.querySelectorAll('[data-layer]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});updateMap();updateMetrics();updateChart();
 }));
 $('year-range').addEventListener('input',e=>setYear(e.target.value));
 $('previous-year').onclick=()=>setYear(state.year-1);$('next-year').onclick=()=>setYear(state.year+1);$('play-timeline').onclick=play;
 $('year-ticks').innerHTML=Array.from({length:10},(_,i)=>`<button class="year-tick ${2021+i===state.year?'active':''}" data-year="${2021+i}" aria-label="Show ${2021+i}">${2021+i}</button>`).join('');
 document.querySelectorAll('[data-year]').forEach(b=>b.onclick=()=>setYear(b.dataset.year));
 $('view-history').onclick=()=>setYear(2025);
 $('previous-option').onclick=()=>showOption(state.optionIndex-1,-1);$('next-option').onclick=()=>showOption(state.optionIndex+1,1);
 $('option-nav').addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();showOption(state.optionIndex+(event.key==='ArrowRight'?1:-1));}});
 $('tab-recommendations').onclick=()=>setMode('recommendations');$('nav-overview').onclick=()=>setMode('recommendations');
 $('tab-priority').onclick=()=>setMode('priority');$('nav-priority').onclick=()=>{setMode('priority');if(window.innerWidth<=940)document.querySelector('.recommendation-panel').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});};
 document.querySelectorAll('.panel-tab[role=tab]').forEach(b=>b.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();setMode(state.mode==='priority'?'recommendations':'priority');$(`tab-${state.mode}`).focus();}}));
 document.querySelectorAll('[data-crop]').forEach(b=>b.onclick=()=>setCrop(b.dataset.crop));
 $('priority-form').onsubmit=e=>{
  e.preventDefault();const value=$('yield-target').value,number=value===''?null:Number(value);
  if(!state.crop||number!==null&&(!Number.isFinite(number)||number<=0)){$('priority-error').textContent=!state.crop?'Choose a priority crop first.':'Enter a positive yield target in bu/ac.';$('priority-error').hidden=false;return;}
  state.target=number;$('priority-error').hidden=true;loadRecommendations();
 };
 $('reset-priority').onclick=()=>{state.crop=null;state.target=null;$('yield-target').value='';$('priority-error').hidden=true;document.querySelectorAll('[data-crop]').forEach(b=>b.setAttribute('aria-pressed','false'));loadRecommendations();};
 $('nav-sources').onclick=openSources;
 document.querySelectorAll('[data-source-tab]').forEach((button,index)=>{button.onclick=()=>renderSourceTab(button.dataset.sourceTab);button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const buttons=[...document.querySelectorAll('[data-source-tab]')],next=buttons[(index+(event.key==='ArrowRight'?1:2))%3];renderSourceTab(next.dataset.sourceTab);next.focus();}});});
 $('close-sources').onclick=()=>$('sources-dialog').close();
 $('sources-dialog').addEventListener('click',e=>{if(e.target===$('sources-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
 $('retry-load').onclick=load;
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
}
function dataControls(ready){
 document.querySelectorAll('.layer-button,.rail-button,.year-tick,#year-range,#previous-year,#next-year,#play-timeline,#view-history,.panel-tab,[data-crop],#yield-target,#priority-form button').forEach(el=>el.disabled=!ready);
}
async function load(){
 setError(null);
 try{
  const [timeline,pilot]=await Promise.all([jsonGet('/api/timeline/harrow'),jsonGet('/api/pilot')]);
  state.timeline=timeline;state.pilot=pilot;
  if(!state.map)initMap();dataControls(true);setYear(state.year);
 }catch(error){setError('The cached field data couldn’t be loaded. '+error.message);$('data-badge').textContent='Data unavailable';$('panel-body').innerHTML='<div class="empty-state"><strong>Your data stays honest.</strong>Reconnect to the local API and try again. No sample predictions are being substituted.</div>';}
}
connectControls();
// Disable controls until the dataset has loaded; the retry button stays available.
dataControls(false);
load();
