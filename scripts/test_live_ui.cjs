// Development-only smoke test; no Node dependency is needed to run DriverGuard.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.join(__dirname,'../ui/assets');
const html = fs.readFileSync(path.join(root,'live.html'),'utf8');
const elements = new Map();
const context2d = {clearRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},setLineDash(){}};
function element() {return {textContent:'',style:{},hidden:false,disabled:false,children:[],value:'CAMERA',width:640,height:130,
    append(...values){this.children.push(...values)},replaceChildren(){this.children=[]},
    removeAttribute(name){delete this[name]},getContext(){return context2d}};}
for(const match of html.matchAll(/id="([^"]+)"/g))elements.set(match[1],element());
const scenarioButtons=[...html.matchAll(/data-action="([^"]+)"/g)].map(match=>({...element(),dataset:{action:match[1]}}));
const document={getElementById(id){assert(elements.has(id),'Missing DOM element: '+id);return elements.get(id)},
    createElement(){return element()},querySelectorAll(){return scenarioButtons}};
let current={active:false,status:'STOPPED',message:'Chưa bắt đầu',source:'CAMERA',session_id:null,session_seconds:0,
    face_detected:false,eye_state:'UNKNOWN',ear:null,eye_closure:0,mar:null,mouth_open:false,yawn_count:0,
    recent_yawns:0,rest_recommended:false,head_direction:'UNKNOWN',distraction_seconds:0,risk_score:0,
    risk_level:'SAFE',system_state:'NORMAL',confirmation_remaining:0,events:[],avg_risk:0,max_risk:0,
    emergency_count:0,fps:0,camera_ms:0,vision_ms:0,frame_time:null,has_frame:false,storage_message:'',
    audio_enabled:true,thresholds:{ear:.2,closure:5,timeout:10,yawn_count:3,yawn_window:60}};
const commands=[];
const sandbox={document,location:{protocol:'http:'},AbortSignal,Date,Math,console,setTimeout(){},async fetch(route,options){
    if(route==='command')commands.push(JSON.parse(options.body));
    return {ok:true,json:async()=>route==='state'?current:{ok:true}};}};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root,'live.js'),'utf8'),sandbox);
(async()=>{
  await vm.runInContext('refresh()',sandbox);
  assert.equal(elements.get('eye-state').textContent,'UNKNOWN');
  assert.equal(elements.get('start').disabled,false);
  current={...current,active:true,source:'DEMO',eye_state:'OPEN',ear:.3,mar:.1,head_direction:'CENTER',has_frame:true,frame_time:1,fps:20};
  await vm.runInContext('refresh()',sandbox);
  assert.equal(elements.get('video').hidden,false);
  assert.match(elements.get('video').src,/^video\?t=/);
  current={...current,system_state:'CONFIRMATION',risk_score:80,risk_level:'CRITICAL',confirmation_remaining:9.2};
  await vm.runInContext('refresh()',sandbox);
  assert.equal(elements.get('confirmation').hidden,false);
  await elements.get('awake').onclick();
  assert.equal(commands.at(-1).action,'CONFIRM');
  current={...current,system_state:'EMERGENCY',confirmation_remaining:0,emergency_count:1,rest_recommended:true,recent_yawns:3};
  await vm.runInContext('refresh()',sandbox);
  assert.equal(elements.get('emergency').hidden,false);
  assert.equal(elements.get('confirmation').hidden,true);
  assert.equal(elements.get('rest').hidden,false);
  current={...current,status:'ERROR',active:false,message:'Camera lỗi',has_frame:false};
  await vm.runInContext('refresh()',sandbox);
  assert.equal(elements.get('connection-error').hidden,false);
  assert.equal(elements.get('connection-error').textContent,'Camera lỗi');
  assert.equal(elements.get('video').hidden,true);
  console.log('PASS: actual live.js handles cold start, video, confirmation button, emergency, rest and error states.');
})().catch(error=>{console.error(error);process.exitCode=1});
