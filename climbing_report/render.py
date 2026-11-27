"""리포트 데이터를 한 장짜리 HTML로 만든다. 지도는 Leaflet + OpenStreetMap(키 불필요)."""
from __future__ import annotations

import html
import json

_CSS = """
:root{--bg:#f4f5f2;--card:#fff;--fg:#1d211f;--muted:#69706b;--line:#e2e5e0;--chip:#eef1ec;
--day:#d97706;--eve:#0f766e;--mix:#7c3aed;--new:#dc2626;--link:#0f5f9e}
@media(prefers-color-scheme:dark){:root{--bg:#101312;--card:#181c1a;--fg:#e6e9e6;--muted:#9aa29c;
--line:#2a302d;--chip:#222825;--day:#f59e0b;--eve:#2dd4bf;--mix:#a78bfa;--new:#f87171;--link:#7cc0f5}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",system-ui,sans-serif}
main{max-width:760px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:1.4rem;margin:0 0 2px;letter-spacing:-.01em}
.meta{color:var(--muted);font-size:.85rem}
.regions{display:flex;gap:4px;margin:16px 0 0;padding:4px;background:var(--chip);border-radius:12px}
.regions button{flex:1;border:0;background:transparent;color:var(--muted);border-radius:9px;padding:9px 8px;
font:inherit;font-weight:700;font-size:1rem;cursor:pointer}
.regions button small{font-weight:400;font-size:.8rem;margin-left:6px;opacity:.8}
.regions button[aria-selected=true]{background:var(--card);color:var(--fg);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:8px;margin:16px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.stat b{display:block;font-size:1.25rem;font-variant-numeric:tabular-nums}
.stat span{color:var(--muted);font-size:.8rem}
.bar{position:sticky;top:0;z-index:1100;background:var(--bg);padding:8px 0;margin:0 -2px}
.row{display:flex;gap:6px;overflow-x:auto;padding:2px;scrollbar-width:none}
.row::-webkit-scrollbar{display:none}
.row+.row{margin-top:6px}
button.pill{flex:0 0 auto;border:1px solid var(--line);background:var(--card);color:var(--muted);
border-radius:999px;padding:6px 12px;font:inherit;font-size:.85rem;cursor:pointer;white-space:nowrap}
button.pill[aria-pressed=true]{background:var(--fg);border-color:var(--fg);color:var(--bg);font-weight:700}
button.pill small{opacity:.7;margin-left:4px;font-weight:400}
button.pill i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:0}
.mapbox{position:relative;margin:8px 0 4px}
#map{height:440px;border-radius:12px;border:1px solid var(--line);background:var(--card)}
@media(max-width:600px){#map{height:380px}}
.mapbox.full{position:fixed;inset:0;z-index:3000;margin:0;background:var(--bg)}
.mapbox.full #map{height:100%;border-radius:0;border:0}
.wheelhint{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;
z-index:900;border-radius:12px;background:rgba(0,0,0,.45);color:#fff;font-weight:700;opacity:0;transition:opacity .2s}
.wheelhint.on{opacity:1}
.mapbtns a{font-size:16px;font-weight:700;cursor:pointer}
.leaflet-tooltip.gymlabel{display:none;background:rgba(255,255,255,.92);border:0;box-shadow:0 1px 3px rgba(0,0,0,.25);
padding:1px 6px;font-size:11px;font-weight:700;color:#1d211f}
.leaflet-tooltip.gymlabel::before{display:none}
.mapbox.labels .leaflet-tooltip.gymlabel{display:block}
.pop h4{margin:0;font-size:.95rem}.pop .sub{color:#69706b;font-size:.8rem;margin-bottom:4px}
.pop ul{list-style:none;margin:0;padding:0;max-height:220px;overflow:auto}
.pop li{display:grid;grid-template-columns:40px 1fr auto;gap:6px;padding:4px 0;border-top:1px dashed #e2e5e0;font-size:.82rem}
.pop li .t,.pop li .j{color:#69706b;font-variant-numeric:tabular-nums}
.pop li a{color:#0f5f9e;text-decoration:none}.pop li small{display:block;color:#69706b}
.leaflet-popup-content{margin:10px 12px}
button.pin{border:0;background:transparent;cursor:pointer;padding:0 0 0 6px;font-size:.9rem;line-height:1}
.maphint{color:var(--muted);font-size:.78rem;margin-bottom:14px}
.dot{border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;
border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);font-size:12px}
section.slot{margin-top:18px}
section.slot h2{font-size:.95rem;margin:0 0 8px;display:flex;align-items:center;gap:8px}
section.slot h2 i{width:10px;height:10px;border-radius:50%;display:inline-block}
section.slot h2 small{color:var(--muted);font-weight:400}
.list{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
details{border-top:1px solid var(--line)}details:first-child{border-top:0}
summary{list-style:none;display:flex;justify-content:space-between;gap:10px;padding:10px 14px;cursor:pointer}
summary::-webkit-details-marker{display:none}
summary b{font-weight:600}summary .n{color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}
.badge{color:var(--new);font-size:.7rem;font-weight:700;margin-left:6px;vertical-align:1px}
.nomap{color:var(--muted);font-size:.72rem;margin-left:6px}
ul.ev{list-style:none;margin:0;padding:0 14px 10px}
ul.ev li{display:grid;grid-template-columns:48px 1fr auto;gap:8px;padding:5px 0;font-size:.88rem;border-top:1px dashed var(--line)}
ul.ev li:first-child{border-top:0}
ul.ev .t{color:var(--muted);font-variant-numeric:tabular-nums}
ul.ev a{color:var(--link);text-decoration:none}ul.ev a:hover{text-decoration:underline}
ul.ev .g{display:block;color:var(--muted);font-size:.8rem}
ul.ev .j{color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}
.empty{color:var(--muted);padding:12px 14px}
footer{color:var(--muted);font-size:.8rem;margin-top:28px;line-height:1.7}
footer a{color:var(--link)}
"""

_JS = r"""
(function(){
var R = window.REPORT, state = {day:0, slot:{day:true, eve:true}, region:null};
var C = {day:getVar('--day'), eve:getVar('--eve'), mix:getVar('--mix')};
function getVar(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function el(tag, attrs, kids){
  var e = document.createElement(tag);
  for (var k in (attrs||{})) { if (k === 'text') e.textContent = attrs[k]; else e.setAttribute(k, attrs[k]); }
  (kids||[]).forEach(function(c){ if (c) e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
  return e;
}
function inRegion(r){ return !state.region || r.region === state.region; }
function rows(dayIdx){
  return R.days[dayIdx].rows.filter(function(r){ return state.slot[r.slot] && inRegion(r); });
}
function count(list){ return list.reduce(function(s,r){return s + r.events.length;}, 0); }
function regionRows(d){ return d.rows.filter(inRegion); }
function short(rg){ return rg.replace(/(특별자치시|특별자치도|특별시|광역시|도)$/,''); }

// 지역 탭 (경기권 / 서울권 …): 주소 #경기, #서울 로 바로 열 수 있다
var allRows = R.days.reduce(function(a,d){return a.concat(d.rows);}, []);
var present = R.regions.filter(function(rg){ return allRows.some(function(r){return r.region===rg;}); });
var regionBox = document.getElementById('regions'), regionBtns = [];
var hashRegion = present.filter(function(rg){ return short(rg) === decodeURIComponent(location.hash.slice(1)); })[0];
function setRegion(rg, updateHash){
  state.region = rg;
  regionBtns.forEach(function(x){ x.setAttribute('aria-selected', String(x.dataset.region === rg)); });
  if (updateHash) { try { history.replaceState(null, '', '#' + short(rg)); } catch (e) {} }
  refresh();
}
if (present.length > 1) {
  state.region = hashRegion || present[0];
  present.forEach(function(rg){
    var n = count(allRows.filter(function(r){return r.region===rg;}));
    var b = el('button',{'role':'tab','aria-selected':String(rg===state.region),'data-region':rg},[short(rg)+'권', el('small',{text:n+'건'})]);
    b.onclick = function(){ setRegion(rg, true); };
    regionBtns.push(b); regionBox.appendChild(b);
  });
} else {
  regionBox.style.display = 'none';
  state.region = present[0] || null;
}

// 요약 (선택한 지역 기준)
var st = document.getElementById('stats');
function drawStats(){
  var rs = R.days.reduce(function(a,d){return a.concat(regionRows(d));}, []);
  var news = rs.reduce(function(s,r){return s + r.events.filter(function(e){return e.new;}).length;}, 0);
  var gyms = {}; rs.forEach(function(r){ gyms[r.gym] = 1; });
  var stats = [[count(regionRows(R.days[0])),'오늘 정모'],[R.days[1]?count(regionRows(R.days[1])):0,'내일 정모'],
    [count(rs), R.days.length+'일 합계'],[Object.keys(gyms).length,'암장'],[news,'새로 올라옴']];
  st.textContent = '';
  stats.forEach(function(s){ st.appendChild(el('div',{'class':'stat'},[el('b',{text:String(s[0])}), el('span',{text:s[1]})])); });
}

// 날짜 탭
var tabs = document.getElementById('days');
var dayCounts = [];
R.days.forEach(function(d,i){
  var small = el('small');
  dayCounts.push(small);
  var b = el('button',{'class':'pill','aria-pressed':String(i===0)},[d.rel ? d.rel+' ' : '', d.label, small]);
  b.onclick = function(){ state.day = i; Array.prototype.forEach.call(tabs.children,function(c,j){c.setAttribute('aria-pressed',String(j===i));}); draw(); };
  tabs.appendChild(b);
});
function drawDayCounts(){ R.days.forEach(function(d,i){ dayCounts[i].textContent = String(count(regionRows(d))); }); }

// 시간대 필터
var f = document.getElementById('filters');
[['day','낮클'],['eve','퇴근클']].forEach(function(s){
  var b = el('button',{'class':'pill','aria-pressed':'true'},[el('i',{style:'background:'+C[s[0]]}), s[1]]);
  b.onclick = function(){ state.slot[s[0]] = !state.slot[s[0]]; b.setAttribute('aria-pressed',String(state.slot[s[0]])); draw(); };
  f.appendChild(b);
});

// 지도
var map = null, layer = null, markers = {}, bounds = null, LABEL_ZOOM = 13;
var me = null, meMarker = null, NEAR_KM = 40;  // 내 위치: 가장 가까운 암장이 40km 안일 때만 쓴다
var mapbox = document.getElementById('mapbox'), wheelhint = document.getElementById('wheelhint');
if (window.L) {
  map = L.map('map', {scrollWheelZoom:true, zoomSnap:0.5, wheelPxPerZoomLevel:90}).setView([37.54, 126.99], 11);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19,
    attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
  layer = L.layerGroup().addTo(map);

  // 휠 확대: 페이지 스크롤을 빼앗지 않도록, 지도를 한 번 누른 뒤나 Ctrl/⌘ + 휠일 때만 확대한다.
  var wheelOn = false, hintTimer = null;
  map.on('click', function(){ wheelOn = true; });
  mapbox.addEventListener('mouseleave', function(){ wheelOn = false; });
  map.getContainer().addEventListener('wheel', function(e){
    if (wheelOn || e.ctrlKey || e.metaKey || mapbox.classList.contains('full')) return;
    e.stopPropagation();  // Leaflet 확대를 막고 페이지는 그대로 스크롤
    wheelhint.classList.add('on'); clearTimeout(hintTimer);
    hintTimer = setTimeout(function(){ wheelhint.classList.remove('on'); }, 1200);
  }, true);

  // 확대하면 암장 이름 표시
  function labels(){ mapbox.classList.toggle('labels', map.getZoom() >= LABEL_ZOOM); }
  map.on('zoomend', labels);

  // 오른쪽 위 버튼: 크게 보기 / 전체 보기
  var Ctl = L.Control.extend({options:{position:'topright'}, onAdd:function(){
    var box = L.DomUtil.create('div', 'leaflet-bar mapbtns');
    var full = L.DomUtil.create('a', '', box); full.href = '#'; full.title = '크게 보기'; full.textContent = '⤢';
    var fit = L.DomUtil.create('a', '', box); fit.href = '#'; fit.title = '전체 보기'; fit.textContent = '◎';
    var loc = L.DomUtil.create('a', '', box); loc.href = '#'; loc.title = '내 위치 근처'; loc.setAttribute('aria-label', '내 위치 근처');
    loc.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" style="vertical-align:-3px" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="8" cy="8" r="4.5"/><circle cx="8" cy="8" r="1.2" fill="currentColor"/><path d="M8 0v3M8 13v3M0 8h3M13 8h3"/></svg>';
    L.DomEvent.on(loc, 'click', function(e){ L.DomEvent.preventDefault(e); if (me) homeView(); else locate(true); });
    L.DomEvent.disableClickPropagation(box);
    L.DomEvent.on(full, 'click', function(e){ L.DomEvent.preventDefault(e); toggleFull(); full.textContent = mapbox.classList.contains('full') ? '✕' : '⤢'; full.title = mapbox.classList.contains('full') ? '닫기' : '크게 보기'; });
    L.DomEvent.on(fit, 'click', function(e){ L.DomEvent.preventDefault(e); fitAll(); });
    return box;
  }});
  map.addControl(new Ctl());
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape' && mapbox.classList.contains('full')) document.querySelector('.mapbtns a').click(); });
} else {
  mapbox.style.display = 'none';
  document.getElementById('maphint').textContent = '지도를 불러오지 못했습니다. 목록은 아래에 있습니다.';
}
function toggleFull(){
  var on = !mapbox.classList.contains('full');
  mapbox.classList.toggle('full', on);
  document.body.style.overflow = on ? 'hidden' : '';
  setTimeout(function(){ map.invalidateSize(); }, 50);
}
function fitAll(){ if (bounds) map.fitBounds(bounds, {padding:[36,36], maxZoom:14}); }

// 내 위치: 허용하면 내 위치와 가까운 암장 3곳이 보이게 지도를 맞춘다. 거부하거나 멀면 전체 보기.
function km(a, b){
  var x = (b[1]-a[1]) * Math.cos((a[0]+b[0]) / 2 * Math.PI / 180), y = b[0]-a[0];
  return Math.sqrt(x*x + y*y) * 111.32;
}
function homeView(){
  if (!map) return;
  if (me && bounds) {
    var near = bounds.slice().sort(function(a,b){ return km(me,a) - km(me,b); }).slice(0, 3);
    map.fitBounds([me].concat(near), {padding:[36,36], maxZoom:14});
  } else if (me) map.setView(me, 13);
  else fitAll();
}
function locate(asked){
  if (!map || !navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(function(p){
    var here = [p.coords.latitude, p.coords.longitude];
    var gymRows = allRows.filter(function(r){ return r.lat != null; });
    var nearest = gymRows.sort(function(a,b){ return km(here,[a.lat,a.lng]) - km(here,[b.lat,b.lng]); })[0];
    if (!nearest || km(here, [nearest.lat, nearest.lng]) > NEAR_KM) {
      if (asked) alert('가까운 암장이 없어서 전체 지도를 보여 줍니다.');
      return;
    }
    me = here;
    if (!meMarker) {
      meMarker = L.circleMarker(me, {radius:7, color:'#fff', weight:2, fillColor:'#2563eb', fillOpacity:1}).addTo(map);
      meMarker.bindTooltip('내 위치', {direction:'top', offset:[0,-6]});
    } else meMarker.setLatLng(me);
    // 주소에 #서울 같은 지역이 없으면, 가장 가까운 암장의 지역 탭으로 연다
    if (!hashRegion && regionBtns.length && nearest.region && nearest.region !== state.region) setRegion(nearest.region, false);
    else homeView();
  }, function(){
    if (asked) alert('위치를 가져오지 못했습니다. 브라우저에서 위치 권한을 허용해 주세요.');
  }, {enableHighAccuracy:false, timeout:10000, maximumAge:600000});
}

function popupFor(g){
  var box = el('div',{'class':'pop'},[el('h4',{text:g.name}),
    el('div',{'class':'sub',text:'정모 '+g.n+'건 · 참석 '+g.joined+'명'})]);
  var ul = el('ul');
  g.events.sort(function(a,b){ return a.time < b.time ? -1 : 1; }).forEach(function(e){
    ul.appendChild(el('li',{},[el('span',{'class':'t',text:e.time}),
      el('span',{},[el('a',{href:e.url,target:'_blank',rel:'noopener',text:e.title||'(제목 없음)'}), el('small',{text:e.group})]),
      el('span',{'class':'j',text:(e.joined==null?'?':e.joined)+(e.capacity?'/'+e.capacity:'')})]));
  });
  box.appendChild(ul);
  return box;
}
function drawMap(list){
  if (!map) return;
  map.invalidateSize();
  layer.clearLayers(); markers = {};
  var byGym = {}, pts = [];
  list.forEach(function(r){
    if (r.lat == null) return;
    var g = byGym[r.gym] || (byGym[r.gym] = {name:r.gym, lat:r.lat, lng:r.lng, joined:0, n:0, slots:{}, events:[]});
    g.joined += r.joined; g.n += r.events.length; g.slots[r.slot] = true;
    g.events = g.events.concat(r.events);
  });
  Object.keys(byGym).forEach(function(k){
    var g = byGym[k], size = Math.max(26, Math.min(52, 22 + g.joined * 2));
    var color = g.slots.day && g.slots.eve ? C.mix : (g.slots.day ? C.day : C.eve);
    var icon = L.divIcon({className:'', iconSize:[size,size],
      html:'<div class="dot" style="width:'+size+'px;height:'+size+'px;background:'+color+'">'+g.joined+'</div>'});
    var m = L.marker([g.lat, g.lng], {icon:icon, title:k, riseOnHover:true}).addTo(layer);
    m.bindPopup(popupFor(g), {maxWidth:300, autoPanPadding:[20,20]});
    m.bindTooltip(k, {permanent:true, direction:'right', offset:[size/2, 0], className:'gymlabel'});
    markers[k] = m;
    pts.push([g.lat, g.lng]);
  });
  bounds = pts.length ? pts : null;
  homeView();
  mapbox.classList.toggle('labels', map.getZoom() >= LABEL_ZOOM);
}
function showOnMap(gym){
  var m = markers[gym]; if (!m) return;
  mapbox.scrollIntoView({behavior:'smooth', block:'center'});
  map.setView(m.getLatLng(), Math.max(map.getZoom(), 15));
  setTimeout(function(){ m.openPopup(); }, 300);
}

// 목록
function drawList(list){
  var box = document.getElementById('list'); box.textContent = '';
  var labels = {day:'낮클 · '+R.evening_from+' 전', eve:'퇴근클 · '+R.evening_from+' 부터'};
  ['day','eve'].forEach(function(slot){
    if (!state.slot[slot]) return;
    var rs = list.filter(function(r){return r.slot===slot;});
    var sec = el('section',{'class':'slot'},[el('h2',{},[el('i',{style:'background:'+C[slot]}), labels[slot],
      el('small',{text:'정모 '+count(rs)+'건 · 암장 '+rs.length+'곳'})])]);
    var ul = el('div',{'class':'list'});
    if (!rs.length) ul.appendChild(el('div',{'class':'empty',text:'이 시간대에는 정모가 없습니다.'}));
    rs.forEach(function(r){
      var head = el('summary',{},[
        el('span',{},[el('b',{text:r.gym}), r.new ? el('span',{'class':'badge',text:'NEW'}) : null,
          r.lat == null ? el('span',{'class':'nomap',text:'지도 없음'}) : null]),
        el('span',{'class':'n'},['정모 '+r.events.length+'건 · 참석 '+r.joined+'명',
          r.lat != null ? (function(){ var b = el('button',{'class':'pin',type:'button',title:'지도에서 보기','aria-label':r.gym+' 지도에서 보기',text:'📍'});
            b.onclick = function(ev){ ev.preventDefault(); ev.stopPropagation(); showOnMap(r.gym); }; return b; })() : null])]);
      var evs = el('ul',{'class':'ev'});
      r.events.forEach(function(e){
        evs.appendChild(el('li',{},[
          el('span',{'class':'t',text:e.time}),
          el('span',{},[el('a',{href:e.url,target:'_blank',rel:'noopener',text:e.title||'(제목 없음)'}),
            e.new ? el('span',{'class':'badge',text:'NEW'}) : null, el('span',{'class':'g',text:e.group})]),
          el('span',{'class':'j',text:(e.joined==null?'?':e.joined)+(e.capacity?' / '+e.capacity:'')+'명'})]));
      });
      ul.appendChild(el('details',{},[head, evs]));
    });
    sec.appendChild(ul); box.appendChild(sec);
  });
}
function draw(){ var list = rows(state.day); drawMap(list); drawList(list); }
function refresh(){ drawStats(); drawDayCounts(); draw(); }
drawStats(); drawDayCounts(); drawList(rows(state.day));
function start(){ draw(); locate(false); }
if (document.readyState === 'complete') start(); else window.addEventListener('load', start);
})();
"""


def _page(title: str, body: str, head_extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>{head_extra}<style>{_CSS}</style></head>
<body><main>{body}</main></body></html>
"""


def short_region(name: str) -> str:
    for suffix in ("특별자치시", "특별자치도", "특별시", "광역시"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def render_report(report: dict, archive_href: str = "archive.html") -> str:
    data = {k: report[k] for k in ("days", "regions", "evening_from", "groups_count")}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    regions = " · ".join(short_region(r) for r in report["regions"]) or "전국"
    head = ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>')
    body = f"""
<h1>🧗 {html.escape(report['title'])}</h1>
<div class="meta">{html.escape(regions)} · {report['generated']} 기준 · 소모임 공개 정모 일정</div>
<div class="regions" id="regions" role="tablist" aria-label="지역"></div>
<div class="stats" id="stats"></div>
<div class="bar"><div class="row" id="days"></div><div class="row" id="filters"></div></div>
<div class="mapbox" id="mapbox"><div id="map"></div><div class="wheelhint" id="wheelhint">지도를 한 번 누르거나 Ctrl + 스크롤로 확대</div></div>
<div class="maphint" id="maphint">원 숫자 = 참석 신청 인원 · 보라색 = 낮클·퇴근클 모두 · 원을 누르면 정모 목록 · 확대하면 암장 이름 · ⤢ 크게 보기 · ◎ 전체 보기 · ⌖ 내 위치 근처(위치 권한 허용 시) · 목록의 📍로 위치 찾기</div>
<div id="list"></div>
<noscript><p>이 페이지는 JavaScript가 필요합니다.</p></noscript>
<footer>
같은 날·같은 시간대·같은 암장의 정모는 한 줄로 묶습니다. 참석 = 소모임 참석 신청 인원(정원).<br>
'NEW'는 지난 리포트 이후 새로 올라온 정모입니다. '지도 없음'은 암장 사전(gyms.json)에 아직 없는 장소입니다.<br>
<a href="{archive_href}">지난 리포트</a>
</footer>
<script>window.REPORT={blob};</script>
<script>{_JS}</script>
"""
    return _page(f"{report['title']} {report['date']}", body, head)


def render_archive(title: str, dates: list[str]) -> str:
    items = "".join(f'<li><a href="reports/{d}.html">{d}</a></li>' for d in dates)
    body = f"""<h1>{html.escape(title)} · 지난 리포트</h1>
<div class="meta"><a href="index.html">← 최신 리포트</a></div>
<ul style="line-height:2">{items}</ul>"""
    return _page(f"{title} · 지난 리포트", body)
