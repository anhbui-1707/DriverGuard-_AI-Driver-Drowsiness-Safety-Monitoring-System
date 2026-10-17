"use strict";
const el=id=>document.getElementById(id), show=(id,on)=>{el(id).hidden=!on}, put=(id,value)=>{el(id).textContent=value};
const number=n=>n==null||!Number.isFinite(Number(n))?'—':Number(n).toFixed(3);
const two=n=>String(n).padStart(2,'0');
let state=null,pending=false,videoOn=false,generation=0,objectURL=null,lastFrameTime=null,frames=[],retryAt=0,countdownAt=0,countdownValue=0;
function stopVideo(){videoOn=false;generation++;el('video').removeAttribute('src');if(objectURL)URL.revokeObjectURL(objectURL);objectURL=null;lastFrameTime=null;frames=[];}
async function pullFrame(id){if(!videoOn||id!==generation)return;let url=null;try{
  const response=await fetch('frame',{cache:'no-store',headers:lastFrameTime==null?{}:{'X-Last-Frame-Time':String(lastFrameTime)},signal:AbortSignal.timeout(1800)});
  if(response.status===204)return;
  if(!response.ok)throw new Error('HTTP '+response.status);
  const frameTime=Number(response.headers.get('X-Frame-Time'));
  url=URL.createObjectURL(await response.blob());const decoded=new Image();decoded.src=url;await decoded.decode();
  if(id!==generation||!videoOn)return;
  const old=objectURL;objectURL=url;url=null;el('video').src=objectURL;if(old)URL.revokeObjectURL(old);
  lastFrameTime=frameTime;frames.push(performance.now());while(frames.length&&performance.now()-frames[0]>1000)frames.shift();
  const fps=frames.length>1?(frames.length-1)*1000/(frames.at(-1)-frames[0]):0;
  put('fps',fps.toFixed(1)+' FPS');
}catch(error){if(id===generation){stopVideo();retryAt=Date.now()+1000;put('status-text','Video tạm gián đoạn: '+error.message)}}
finally{if(url)URL.revokeObjectURL(url);if(videoOn&&id===generation)setTimeout(()=>pullFrame(id),33)}}
function buttons(){el('start').disabled=!!state?.active||pending;el('stop').disabled=!state?.active||pending;el('alarm-circle').disabled=pending}
async function command(action){if(pending)return;pending=true;buttons();try{
 const r=await fetch('command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action}),signal:AbortSignal.timeout(6000)});
 if(!r.ok){const body=await r.json();throw new Error(body.error||'Không thực hiện được lệnh')}
 await refresh();
}catch(error){show('connection-error',true);put('connection-error',error.message)}finally{pending=false;buttons()}}
function render(s){state=s;window.DriverVoice?.update?.(s);show('connection-error',s.status==='ERROR');if(s.status==='ERROR')put('connection-error',s.message);
 const alert=s.active&&(s.system_state==='CONFIRMATION'||s.system_state==='EMERGENCY');const emergency=s.system_state==='EMERGENCY';show('alarm-overlay',alert);el('alarm-overlay').classList.toggle('emergency',emergency);put('alarm-title',emergency?'KHẨN CẤP MÔ PHỎNG':'BẠN CÓ TỈNH KHÔNG?');put('alarm-action',emergency?'CHẠM ĐỂ KẾT THÚC':'CHẠM VÀO ĐÂY ĐỂ XÁC NHẬN');show('countdown',!emergency);countdownAt=performance.now();countdownValue=s.confirmation_remaining||0;
 put('ai-status',!s.active?'● AI SẴN SÀNG':alert?'● CẢNH BÁO':'● ĐANG GIÁM SÁT');const seconds=Math.floor(s.session_seconds||0);put('duration',`${two(Math.floor(seconds/3600))}:${two(Math.floor(seconds/60)%60)}:${two(seconds%60)}`);
 const hasVideo=s.active&&s.has_frame;show('video',hasVideo);show('empty',!hasVideo);if(hasVideo&&!videoOn&&Date.now()>=retryAt){videoOn=true;pullFrame(++generation)}if(!hasVideo&&videoOn)stopVideo();if(!hasVideo)put('fps','— FPS');
 put('camera-info',s.source==='DEMO'?'MÔ PHỎNG':hasVideo?'CAMERA 01 · TRỰC TIẾP':'CAMERA 01 · ĐANG CHỜ');
 put('empty-title',s.status==='ERROR'?'Không mở được camera':s.status==='STARTING'?'Đang kết nối camera':'Camera chưa bật');put('empty-detail',s.status==='ERROR'?s.message:s.status==='STARTING'?'Chờ webcam gửi khung hình đầu tiên':'Nhấn Bắt đầu giám sát để mở webcam');put('status-text',s.active?(s.message||''):s.status==='ERROR'?s.message:'');
 const valid=s.active&&(s.face_detected||s.source==='DEMO');put('ear',valid?number(s.ear):'—');put('mar',valid?number(s.mar):'—');put('head-state',valid?(s.head_direction==='UNKNOWN'?'Chưa xác định':s.head_direction):'—');put('closure',valid?s.eye_closure.toFixed(1)+' giây':'—');
 put('drowsiness',two(s.drowsiness_count||0));put('yawns',two(s.yawn_count||0));put('distractions',two(s.distraction_count||0));const score=s.active?Math.round(s.risk_score):0;put('score',score);el('gauge').style.strokeDashoffset=364.42*(1-score/100);
 const level=alert?'Nguy hiểm':!valid?'Chưa có dữ liệu':score>=60?'Nguy hiểm':score>=30?'Cảnh báo':'Bình thường';put('risk-level',!s.active?'Chưa bắt đầu':level);el('risk-level').style.color=level==='Nguy hiểm'?'var(--red)':level==='Cảnh báo'?'#ffbb58':'var(--green)';put('risk-note',emergency?'Chỉ mô phỏng, không gọi khẩn cấp thật.':!s.active?'Nhấn Bắt đầu giám sát để kích hoạt camera.':!valid?'Đang chờ nhận diện khuôn mặt.':s.rest_recommended?'Ngáp nhiều: nên nghỉ ngơi ở nơi an toàn.':'Đang theo dõi trong thời gian thực.');buttons();}
let refreshing=null;async function refresh(){if(refreshing)return refreshing;refreshing=(async()=>{const r=await fetch('state',{cache:'no-store',signal:AbortSignal.timeout(4000)});if(!r.ok)throw new Error('HTTP '+r.status);render(await r.json())})();try{await refreshing}finally{refreshing=null}}
async function poll(){try{await refresh()}catch(e){show('connection-error',true);put('connection-error','Mất kết nối DriverGuard: '+e.message)}finally{setTimeout(poll,200)}}
setInterval(()=>{if(state?.system_state==='CONFIRMATION')put('countdown',Math.max(0,countdownValue-(performance.now()-countdownAt)/1000).toFixed(1)+'s')},100);
el('start').onclick=()=>{window.DriverVoice?.unlock();command('START')};el('stop').onclick=()=>{window.DriverVoice?.silence();command('STOP')};el('alarm-circle').onclick=()=>{window.DriverVoice?.silence();command(state?.system_state==='EMERGENCY'?'RESET':'CONFIRM')};el('theme').onclick=()=>{const light=document.documentElement.dataset.theme!=='light';document.documentElement.dataset.theme=light?'light':'dark';put('theme',light?'☀ Chế độ tối':'☾ Chế độ sáng')};el('video').onerror=()=>{stopVideo();retryAt=Date.now()+1000};
if(location.protocol==='file:'){show('connection-error',true);put('connection-error','Chạy START_DRIVERGUARD.bat để mở ứng dụng, không mở file HTML trực tiếp.');el('start').disabled=true}else poll();
