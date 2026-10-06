"use strict";
const el = id => document.getElementById(id);
const text = (id, value) => { el(id).textContent = value; };
const show = (id, visible) => { el(id).hidden = !visible; };
let state = null, pending = false, videoRunning = false, videoRetryAfter = 0;
let lastFrame = null;
const samples = [];
const clamp = value => Math.max(0, Math.min(100, value));
function bar(id, fraction) { el(id).style.width = clamp(fraction * 100) + "%"; }
function metric(value) { return value == null ? "—" : value.toFixed(3); }
function clock(seconds) { return String(Math.floor(seconds/60)).padStart(2,"0") + ":" + String(Math.floor(seconds%60)).padStart(2,"0"); }
function connectionError(message) { show("connection-error",true); text("connection-error", message); }
async function command(action, extra={}) {
  if (pending) return;
  pending = true;
  updateButtons();
  try {
    const response = await fetch("command", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action,...extra}),signal:AbortSignal.timeout(6000)});
    if (!response.ok) { const body = await response.json(); throw new Error(body.error || "Lệnh không được thực hiện"); }
    await refresh();
  } catch (error) { connectionError("Không thực hiện được lệnh: " + error.message + ". Kiểm tra Terminal đang chạy DriverGuard."); }
  finally { pending = false; updateButtons(); }
}
function updateButtons() {
  const active = state?.active || false;
  el("start").disabled = active || pending;
  el("stop").disabled = !active || pending;
  el("recenter").disabled = !active || pending;
  el("source").disabled = active || pending;
  el("awake").disabled = pending;
  el("reset").disabled = pending;
  document.querySelectorAll("[data-action]").forEach(button => button.disabled = !active || pending);
}
function drawChart(threshold) {
  const canvas=el("telemetry"),ctx=canvas.getContext("2d"),w=canvas.width,h=canvas.height;
  ctx.clearRect(0,0,w,h);
  ctx.strokeStyle="#22334a";ctx.lineWidth=1;
  for(let i=1;i<4;i++){ctx.beginPath();ctx.moveTo(0,h*i/4);ctx.lineTo(w,h*i/4);ctx.stroke();}
  const y=value=>h-10-Math.min(.6,Math.max(0,value))/.6*(h-20);
  ctx.strokeStyle="#fa726e";ctx.setLineDash([5,5]);ctx.beginPath();ctx.moveTo(0,y(threshold));ctx.lineTo(w,y(threshold));ctx.stroke();ctx.setLineDash([]);
  ctx.strokeStyle="#36d7e5";ctx.lineWidth=2;ctx.beginPath();let drawing=false;
  samples.forEach((point,i)=>{if(point==null){drawing=false;return;}const x=i/Math.max(1,80-1)*w;if(!drawing){ctx.moveTo(x,y(point));drawing=true;}else ctx.lineTo(x,y(point));});ctx.stroke();
}
function render(s) {
  state=s;
  show("connection-error",s.status==="ERROR");
  if(s.status==="ERROR")text("connection-error",s.message);
  const confirmation=s.active && s.system_state==="CONFIRMATION";
  const emergency=s.active && s.system_state==="EMERGENCY";
  show("confirmation",confirmation);show("emergency",emergency);
  text("countdown",s.confirmation_remaining.toFixed(1)+"s");
  text("source-pill",s.source==="DEMO" ? "DEMO / MÔ PHỎNG" : s.active ? "WEBCAM ACTIVE" : "CHƯA BẮT ĐẦU");
  text("fps",s.fps.toFixed(1)+" FPS");
  text("camera-source",s.source==="DEMO" ? "SIMULATED INPUT" : "CAMERA FEED");
  text("latency","VISION "+s.vision_ms.toFixed(0)+"ms");
  if(s.active)el("source").value=s.source;
  show("demo",s.active ? s.source==="DEMO" : el("source").value==="DEMO");
  text("audio",s.audio_enabled ? "Âm báo: bật" : "Âm báo: tắt");
  const hasVideo=s.active && s.has_frame;
  show("video",hasVideo);show("empty",!hasVideo);
  if(hasVideo && !videoRunning && Date.now()>=videoRetryAfter){videoRunning=true;el("video").src="video?t="+Date.now();}
  if(!s.active && videoRunning){el("video").removeAttribute("src");videoRunning=false;}
  text("face-state",s.source==="DEMO" ? "DỮ LIỆU MÔ PHỎNG" : s.calibrating ? "ĐANG TỰ HIỆU CHỈNH MẮT" : s.face_detected ? "ĐÃ PHÁT HIỆN KHUÔN MẶT" : "CHƯA CÓ DỮ LIỆU KHUÔN MẶT");
  text("status-text",s.message);text("system-state",s.system_state);
  const color=emergency||confirmation||s.risk_level==="CRITICAL" ? "#fa726e" : s.risk_level==="SAFE" ? "#35d09b" : "#f6b64c";
  text("risk-level",!s.face_detected && s.source==="CAMERA" && !confirmation && !emergency ? "NO DATA" : s.risk_level);
  el("risk-level").style.color=color;el("gauge").style.stroke=color;el("gauge").style.strokeDashoffset=364.42*(1-clamp(s.risk_score)/100);
  text("score",Math.round(s.risk_score));text("ear",metric(s.ear));text("mar",metric(s.mar));text("closure",s.eye_closure.toFixed(1)+"s");
  bar("ear-bar",(s.ear||0)/.4);bar("mar-bar",(s.mar||0)/.8);bar("closure-bar",s.eye_closure/s.thresholds.closure);
  text("eye-state",s.eye_state);text("head-state",s.head_direction);text("distraction",s.distraction_seconds.toFixed(1)+"s");
  text("duration",clock(s.session_seconds));text("session-id",s.session_id ? "Phiên #"+s.session_id : "Chưa bắt đầu");text("yawns",s.yawn_count);
  text("recent-yawns",s.recent_yawns+" lần / "+s.thresholds.yawn_window+"s");text("avg-risk",Math.round(s.avg_risk));text("max-risk",Math.round(s.max_risk));text("emergencies",s.emergency_count);
  show("rest",s.rest_recommended);text("rest-text",s.recent_yawns+" lần ngáp trong "+s.thresholds.yawn_window+" giây. Hãy dừng ở nơi an toàn và nghỉ ngơi nếu buồn ngủ.");
  show("storage-error",!!s.storage_message);text("storage-error",s.storage_message);
  text("advice",s.rest_recommended ? "Ngáp nhiều là tín hiệu cần chú ý. Đừng cố tiếp tục nếu cảm thấy buồn ngủ." : s.eye_state==="CLOSED" ? "Mắt đang nhắm. Hệ thống theo dõi thời gian liên tục để phân biệt chớp mắt và nhắm kéo dài." : "Đặt webcam ngang tầm mắt, đủ ánh sáng. Nhìn thẳng để lấy tư thế chuẩn và điều chỉnh EAR/MAR nếu cần.");
  text("diagnostics","Camera read: "+s.camera_ms.toFixed(0)+" ms · Vision: "+s.vision_ms.toFixed(0)+" ms · Processing: "+s.fps.toFixed(1)+" FPS");
  const actualEar=s.thresholds.calibrated_ear || s.thresholds.ear;
  text("ear-threshold",s.calibrating ? "ĐANG HIỆU CHỈNH "+Math.round(s.calibration_progress*100)+"%" : "NGƯỠNG "+actualEar.toFixed(2));
  if(s.frame_time!==lastFrame){samples.push(s.ear);while(samples.length>80)samples.shift();lastFrame=s.frame_time;drawChart(actualEar);}
  const logs=el("events");logs.replaceChildren();
  if(!s.events.length){const p=document.createElement("p");p.className="hint";p.textContent="Chưa có sự kiện.";logs.append(p);}
  [...s.events].reverse().forEach(event=>{const row=document.createElement("div");row.className="event";const time=document.createElement("time");time.textContent=new Date(event.timestamp).toLocaleTimeString("vi-VN");const content=document.createElement("div"),title=document.createElement("b"),description=document.createElement("p");title.textContent=event.event_type;description.textContent=event.description;content.append(title,description);row.append(time,content);logs.append(row);});
  updateButtons();
}
let refreshing=null;
async function refresh(){
  if(refreshing)return refreshing;
  refreshing=(async()=>{const response=await fetch("state",{cache:"no-store",signal:AbortSignal.timeout(4000)});if(!response.ok)throw new Error("HTTP "+response.status);render(await response.json());})();
  try{await refreshing;}finally{refreshing=null;}
}
async function poll(){try{await refresh();}catch(error){connectionError("Mất kết nối với DriverGuard. Kiểm tra Terminal, sau đó tải lại trang. "+error.message);}finally{setTimeout(poll,250);}}
el("start").onclick=()=>command("START",{source:el("source").value});el("stop").onclick=()=>command("STOP");el("recenter").onclick=()=>command("RECENTER");el("awake").onclick=()=>command("CONFIRM");el("reset").onclick=()=>command("RESET");el("audio").onclick=()=>command("AUDIO",{enabled:!(state?.audio_enabled??true)});
el("source").onchange=()=>show("demo",el("source").value==="DEMO");document.querySelectorAll("[data-action]").forEach(button=>button.onclick=()=>command(button.dataset.action));
el("video").onerror=()=>{videoRunning=false;videoRetryAfter=Date.now()+1000;show("video",false);show("empty",true);};
if(location.protocol==="file:"){
  connectionError("Xem trước bố cục. Chạy START_DRIVERGUARD.bat để kết nối webcam, bộ xử lý và các nút điều khiển.");
  el("connection-error").className="notice";
  text("source-pill","XEM TRƯỚC GIAO DIỆN");
  document.querySelectorAll("button,select").forEach(control=>control.disabled=true);
  drawChart(.2);
}else{poll();}
