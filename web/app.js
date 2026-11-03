'use strict';
const $ = id => document.getElementById(id);
const fmt = (v, n=1) => v == null || !Number.isFinite(Number(v)) ? '—' : Number(v).toFixed(n);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const roles = {fixed:'固定角点',pursuer:'追捕车',evader:'逃逸车',robot:'小车',unknown:'未配置标签'};
const colors = ['#18a87b','#e4a125','#438de0','#b87acb'];
let selected=10, state=null, familiesKey='', toastTimer, lastEvent='', sourceInitialized=false;
function toast(message, error=false){$('toast').textContent=message;$('toast').className=error?'error':'';$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4500);}
async function control(action, extra={}){
  try{const r=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})});const v=await r.json();if(!r.ok)throw Error(v.error||r.status);toast('操作已提交，执行结果见实验事件');}
  catch(e){toast(e.message,true);}
}
$('connect').onclick=()=>control('source',{source:$('source').value});
$('apply-detector').onclick=()=>control('detector',{family:$('family').value,decimate:Number($('decimate').value)});
$('record').onclick=()=>control('record');
$('calibrate-world').onclick=()=>control('calibrate');
$('reset-world').onclick=()=>control('reset_world');
$('clear-tracks').onclick=()=>control('clear_tracks');
$('selected-tag').onchange=e=>{selected=Number(e.target.value);if(state)render(state);};
function dl(id, pairs){$(id).innerHTML=pairs.map(([a,b])=>`<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`).join('');}
function tagList(s){
  const configured=s.configured_tags||{};const map=new Map((s.tags||[]).map(t=>[t.id,t]));
  for(const [id,t] of Object.entries(configured))if(!map.has(Number(id)))map.set(Number(id),{id:Number(id),name:t.name,role:t.role,status:'unseen',size_m:t.size_m});
  return [...map.values()].sort((a,b)=>a.id-b.id);
}
function statusText(t){return {visible:'可见',stale:'暂失',lost:'丢失',unseen:'未出现'}[t.status]||'—';}
function vec(v,n=2){return v?v.map(x=>fmt(x,n)).join(', '):'未标定';}
function render(s){
  state=s;const healthy=s.status==='running'&&s.state_age_ms<500;
  if(!healthy)s={...s,tags:(s.tags||[]).map(t=>({...t,status:'lost',speed_px_s:null,speed_m_s:null}))};
  if(!sourceInitialized&&s.source){const option=[...$('source').options].find(o=>o.value===s.source);if(option)$('source').value=s.source;sourceInitialized=true;}
  $('clock').textContent=new Date().toLocaleTimeString('zh-CN',{hour12:false});
  $('connection').textContent=healthy?(s.demo?'演示运行中':'实时连接中'):'等待输入源';$('connection').className='pill '+(healthy?'good':'bad');
  $('fps').textContent=healthy?fmt(s.fps):'0.0';$('visible').textContent=healthy?(s.visible_count??0):0;
  $('fleet-count').textContent=`已配置 ${s.known_count??12} 个身份`;
  $('detect-time').textContent=fmt(s.detection_ms);$('frame-age').textContent=fmt(s.frame_age_ms??s.state_age_ms,0);
  $('resolution').textContent=s.width?`${s.width} × ${s.height}`:'—';
  $('image-quality').textContent=`亮度 ${fmt(s.mean_brightness,0)} / 255 · 清晰度 ${fmt(s.laplacian_variance,0)}`;
  $('calibration').textContent=s.world_calibrated?'场地已标定':s.calibrated?'内参已标定':'像素观测';
  $('calibration-detail').textContent=s.demo?'演示参数 · 不代表实机精度':s.world_calibrated?'已补偿标签安装高度':'内参与场地外参分别配置';
  $('source-label').textContent=s.demo?'合成场景 · 非实物相机':s.source?`输入源 ${s.source}`:'未连接';
  $('backend').textContent=s.backend||'AprilTag 3';$('frame-number').textContent=`FRAME ${String(s.frame_id||0).padStart(6,'0')}`;
  $('image-offline').hidden=healthy;
  const warnings=s.warnings||[];
  $('notice').textContent=s.error||warnings.join('　 · 　')||'定位正常。标签中心位置与车体控制点之间的偏移需另行标定。';
  $('notice').className='notice '+(!healthy?'error':warnings.some(w=>!w.startsWith('合成演示'))?'warning':'');
  $('record').className=s.recording?'active':'';$('record').innerHTML=`<span class="record-dot"></span> ${s.recording?'停止记录':'开始记录'}`;
  $('record-path').textContent=s.recording?s.record_path:'点击“开始记录”保存逐帧 JSONL，含未检出帧';
  const fkey=(s.families||[]).join(',');if(fkey&&fkey!==familiesKey){familiesKey=fkey;$('family').innerHTML=s.families.map(f=>`<option ${f===s.family?'selected':''}>${esc(f)}</option>`).join('');}
  const tags=tagList(s);const select=$('selected-tag');const key=tags.map(t=>t.id).join(',');
  if(select.dataset.key!==key){select.innerHTML=tags.map(t=>`<option value="${t.id}">ID ${t.id}</option>`).join('');select.dataset.key=key;}select.value=selected;
  $('tag-table').innerHTML=tags.map(t=>{const live=t.status==='visible'&&healthy;return `<tr data-id="${t.id}" class="${t.id===selected?'selected ':''}${live?'':'dim'}"><td><strong>${t.id}</strong> · ${esc(t.name)}</td><td><i class="status-dot ${live?'':t.status==='stale'?'stale':'lost'}"></i>${statusText(t)}<small>${t.age_ms==null?'等待首次识别':fmt(t.age_ms,0)+' ms 前'}</small></td><td>${t.center_px?vec(t.center_px,1):'—'}</td><td>${fmt(t.heading_image_deg)}</td><td>${fmt(t.pose?.range_m,3)}</td><td>${t.world_xyz_m?vec(t.world_xyz_m.slice(0,2),3):'未标定'}</td><td>${t.speed_m_s!=null?fmt(t.speed_m_s,3)+' m/s':t.speed_px_s!=null?fmt(t.speed_px_s,1)+' px/s':'—'}</td><td>${fmt(t.decision_margin)} / ${fmt(t.hamming,0)}</td><td>${fmt(t.min_edge_px)}</td><td>${t.seen_ratio==null?'—':fmt(t.seen_ratio*100,1)+'%'}</td></tr>`;}).join('');
  $('tag-table').querySelectorAll('tr').forEach(row=>row.onclick=()=>{selected=Number(row.dataset.id);render(s);});
  renderDetails(tags.find(t=>t.id===selected),s);drawMap(s,healthy);renderPursuit(s,healthy);
  $('world-rms').textContent=s.world_info?`四角 RMS ${fmt(s.world_info.rms_px,3)} px · 相机高度 ${fmt(s.world_info.camera_world_xyz_m[2],2)} m`:'';
  $('map-mode').textContent=s.world_calibrated?'米制俯视图':'图像平面 · px';$('map-mode').className='pill '+(s.world_calibrated?'good':'warn');
  $('events').innerHTML=(s.events||[]).slice(0,10).map(e=>`<div class="event ${e.level==='error'?'error':''}"><time>${esc(e.time)}</time><span>${esc(e.text)}</span></div>`).join('')||'<div class="muted">等待实验事件</div>';
  const e=s.events?.[0];if(e&&e.time+e.text!==lastEvent){lastEvent=e.time+e.text;if(e.level==='error')toast(e.text,true);}
}
function renderDetails(t,s){
  const seen=!!t?.center_px;$('details').hidden=!seen;$('detail-empty').hidden=seen;
  $('tag-title').textContent=t?`ID ${t.id} · ${t.name}`:'等待标签';$('tag-role').textContent=t?`${roles[t.role]||'标签'} · ${s.family||'tag36h11'}`:'从表格选择标签';
  $('tag-status').textContent=t?statusText(t):'—';$('tag-status').className='pill '+(t?.status==='visible'?'good':t?.status==='stale'?'warn':'bad');if(!seen)return;
  dl('pixel-details',[['中心 (u, v)',vec(t.center_px,2)+' px'],['图像朝向',fmt(t.heading_image_deg,1)+'°'],['短边 / 长边',fmt(t.min_edge_px,1)+' / '+fmt(t.max_edge_px,1)+' px'],['投影面积',fmt(t.area_px2,0)+' px²'],['图像速度',fmt(t.speed_px_s,1)+' px/s'],['跟踪时长',fmt(t.track_seconds,1)+' s']]);
  $('quality-bar').style.width=Math.max(0,Math.min(100,t.decision_margin??0))+'%';
  dl('quality-details',[['Decision margin',fmt(t.decision_margin,2)],['Hamming 纠错位数',fmt(t.hamming,0)],['可见帧 / 出现后帧数',fmt(t.seen_frames,0)+' / '+fmt(t.seen_ratio*100,1)+'%'],['最近观测',fmt(t.age_ms,0)+' ms 前']]);
  const p=t.pose;dl('pose-details',p?[['标签实际边长',fmt(t.size_m*1000,0)+' mm'],['平移 X, Y, Z',vec(p.camera_xyz_m,3)+' m'],['直线距离',fmt(p.range_m,3)+' m'],['RPY · ZYX',vec(p.rpy_deg,1)+'°'],['离轴倾角',fmt(p.tilt_deg,1)+'°'],['重投影 RMS',fmt(p.reprojection_rms_px,3)+' px'],['另一解 RMS',fmt(p.alternative_rms_px,3)+' px'],['平面位姿歧义',p.ambiguous?'两解接近，谨慎使用':'当前最小重投影解']]:[['状态','需要相机内参与实际标签尺寸']]);
  dl('world-details',t.world_xyz_m?[['标签中心 X, Y, Z',vec(t.world_xyz_m,3)+' m'],['安装高度',fmt(t.height_m,3)+' m'],['标签前向角',fmt(t.heading_world_deg,1)+'°'],['平面速度 · 滤波',fmt(t.speed_m_s,3)+' m/s']]:[['状态','需要四角外参及标签安装高度']]);
  $('raw-details').textContent='角点 0,1,2,3 (px)\n'+t.corners_px.map((v,i)=>`${i}: [${vec(v,2)}]`).join('\n')+(p?'\n\n旋转矩阵 · tag → camera\n'+p.rotation_matrix.map(r=>vec(r,4)).join('\n'):'');
}
function drawMap(s,healthy){
  const canvas=$('map'),ctx=canvas.getContext('2d'),w=700,h=440;ctx.clearRect(0,0,w,h);ctx.fillStyle='#f8fafc';ctx.fillRect(0,0,w,h);
  const metric=s.world_calibrated;const bounds=s.boundary_xy_m||[[0,0],[3,0],[3,3],[0,3]];
  const xs=bounds.map(p=>p[0]),ys=bounds.map(p=>p[1]);let x0=metric?Math.min(...xs):0,x1=metric?Math.max(...xs):(s.width||1440),y0=metric?Math.min(...ys):0,y1=metric?Math.max(...ys):(s.height||1000);
  const pad=45,scale=Math.min((w-pad*2)/(x1-x0||1),(h-pad*2)/(y1-y0||1));const ox=(w-(x1-x0)*scale)/2,oy=(h-(y1-y0)*scale)/2;
  const xy=p=>[ox+(p[0]-x0)*scale,metric?h-oy-(p[1]-y0)*scale:oy+(p[1]-y0)*scale];
  const path=(pts,close=false)=>{ctx.beginPath();pts.forEach((p,i)=>{const q=xy(p);i?ctx.lineTo(...q):ctx.moveTo(...q);});if(close)ctx.closePath();};
  ctx.lineWidth=1;ctx.strokeStyle='#e1e8ef';const steps=6;
  for(let i=0;i<=steps;i++){const x=x0+(x1-x0)*i/steps,y=y0+(y1-y0)*i/steps;path([[x,y0],[x,y1]]);ctx.stroke();path([[x0,y],[x1,y]]);ctx.stroke();ctx.fillStyle='#91a1b0';ctx.font='11px system-ui';const q=xy([x,y0]);ctx.fillText(fmt(x,metric?1:0),q[0]-8,metric?q[1]+20:q[1]-12);}
  path(metric?bounds:[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],true);ctx.strokeStyle='#bdcbd8';ctx.stroke();
  const tags=(s.tags||[]).filter(t=>metric?t.world_xyz_m:t.center_px);
  const active=tags.filter(t=>t.status==='visible'&&healthy);const pursuers=active.filter(t=>t.role==='pursuer');
  if(pursuers.length===3){path(pursuers.map(t=>metric?t.world_xyz_m:t.center_px),true);ctx.fillStyle='#378bd00d';ctx.strokeStyle='#84b4da';ctx.setLineDash([5,5]);ctx.fill();ctx.stroke();ctx.setLineDash([]);}
  for(const t of tags){const p=metric?t.world_xyz_m:t.center_px,q=xy(p),live=t.status==='visible'&&healthy;const color=live?colors[t.id%4]:'#acbac6';ctx.strokeStyle=color;ctx.lineWidth=1.5;
    const history=(t.history||[]).map(a=>metric?a.world:a.pixel).filter(Boolean);if(history.length>1&&t.role!=='fixed'){path(history);ctx.globalAlpha=.5;ctx.stroke();ctx.globalAlpha=1;}
    if(t.id===selected){ctx.beginPath();ctx.arc(...q,13,0,Math.PI*2);ctx.fillStyle='#1d75c51a';ctx.fill();ctx.strokeStyle='#a2c7e5';ctx.stroke();}
    ctx.fillStyle=color;if(t.role==='fixed')ctx.fillRect(q[0]-4,q[1]-4,8,8);else{ctx.beginPath();ctx.arc(...q,t.role==='evader'?7:5.5,0,Math.PI*2);ctx.fill();}
    const angle=metric?t.heading_world_deg:t.heading_image_deg;if(angle!=null){const a=-angle*Math.PI/180;ctx.strokeStyle=color;ctx.beginPath();ctx.moveTo(...q);ctx.lineTo(q[0]+19*Math.cos(a),q[1]+19*Math.sin(a));ctx.stroke();}
    ctx.fillStyle=live?'#38536b':'#a0afbb';ctx.font=t.id===selected?'bold 12px system-ui':'11px system-ui';ctx.fillText(`ID ${t.id}${live?'':' · 旧'}`,q[0]+10,q[1]-10);
  }
  ctx.fillStyle='#8b9dad';ctx.font='11px system-ui';ctx.fillText(metric?'WORLD X →  /  Y ↑ · m':'IMAGE u →  /  v ↓ · px',18,h-12);
  if(!metric){ctx.fillStyle='#8a9dad';ctx.font='12px system-ui';ctx.fillText('未标定：显示图像平面位置，透视会压缩距离',30,23);}
}
function renderPursuit(s,healthy){
  const metric=s.world_calibrated;const tags=(s.tags||[]).filter(t=>t.status==='visible'&&healthy&&(metric?t.world_xyz_m:t.center_px));const ps=tags.filter(t=>t.role==='pursuer'),e=tags.find(t=>t.role==='evader');
  const point=t=>metric?t.world_xyz_m:t.center_px,unit=metric?'m':'px';let inside='数据不足';
  if(ps.length===3&&e){const pp=ps.map(point),ep=point(e);const cross=(a,b,p)=>(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]);const area=Math.abs(cross(pp[0],pp[1],pp[2]));if(area<1e-8)inside='追捕点共线';else{const cs=pp.map((p,i)=>cross(p,pp[(i+1)%3],ep));inside=(cs.every(x=>x>0)||cs.every(x=>x<0))?'在凸包内':'在凸包外 / 边界';}}
  const pairs=[['追捕 / 逃逸可见',`${ps.length} / ${e?'1':'0'}`],['几何包围',inside]];
  if(e)for(const p of ps){const a=point(p),b=point(e);pairs.push([`ID ${p.id} → ${e.id}`,`${fmt(Math.hypot(a[0]-b[0],a[1]-b[1]),metric?3:0)} ${unit}`]);}
  const robots=tags.filter(t=>['pursuer','evader','robot'].includes(t.role));let minimum=Infinity;for(let i=0;i<robots.length;i++)for(let j=i+1;j<robots.length;j++){const a=point(robots[i]),b=point(robots[j]);minimum=Math.min(minimum,Math.hypot(a[0]-b[0],a[1]-b[1]));}
  pairs.push(['车间最小中心距',Number.isFinite(minimum)?fmt(minimum,metric?3:0)+' '+unit:'—']);dl('pursuit-details',pairs);
}
async function poll(){
  try{const response=await fetch('/api/state',{cache:'no-store'});if(!response.ok)throw Error('状态服务暂不可用');render(await response.json());}
  catch(e){if(state)render({...state,status:'error',error:'无法连接本地识别服务，请检查终端中的程序是否运行。'});$('connection').textContent='服务已断开';$('connection').className='pill bad';$('image-offline').hidden=false;$('notice').textContent='无法连接本地识别服务，请检查终端中的程序是否运行。';$('notice').className='notice error';}
  setTimeout(poll,200);
}
poll();
