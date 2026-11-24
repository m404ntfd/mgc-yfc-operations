// Read-only server reachability; never replays a sale or modifies a session.
const deskConnectionDefaults={interval_seconds:10,warning_seconds:20,offline_seconds:30};
officeCards.push({section:'system',action:'desk-connection',title:'Register connection indicator',description:'Check frequency and yellow/red connection warnings for DESK.',icon:'●',permission:'manage_pos',keywords:'ping server network connection offline status'});
officeNavigationGroups.find(g=>g.id==='computers').actions.push('desk-connection');
const beforeDeskConnectionOffice=officeAction;
officeAction=async function(action){
 if(action!=='desk-connection')return beforeDeskConnectionOffice(action);
 if(!officeMode||!can('manage_pos')||!navigationAllowed()||unfinished())return;
 try{
  const {settings}=await checkoutQuery('checkout-settings'),timing=settings.connection_monitor||deskConnectionDefaults;
  const d=checkoutModal('Register connection indicator',`<p>Applies to registers assigned to this store. Changes reach open registers within one minute.</p><form id="deskConnectionSettings"><label>Check server every (seconds)<input name="interval_seconds" type="number" min="5" max="60" step="1" required value="${timing.interval_seconds}"></label><label>Yellow after no successful check for (seconds)<input name="warning_seconds" type="number" min="10" max="300" step="1" required value="${timing.warning_seconds}"></label><label>Red after no successful check for (seconds)<input name="offline_seconds" type="number" min="15" max="600" step="1" required value="${timing.offline_seconds}"></label><p>Defaults: check every 10 seconds, yellow after 20 seconds, red after 30 seconds. Yellow must allow at least two checks; red must allow at least one further check. A reported network disconnect turns red immediately.</p><p>Green means the server answered a verified connection check. It does not confirm a payment. A restored connection never submits a transaction automatically.</p><button class="primary">Save connection timings</button></form>`);
  let saving=false;
  d.querySelector('form').onsubmit=async e=>{
   e.preventDefault();if(saving)return;
   const f=e.target,connection_monitor=Object.fromEntries(Object.keys(deskConnectionDefaults).map(k=>[k,Number(f.elements[k].value)]));
   try{saving=true;await retailSave('checkout-settings-save',{...settings,connection_monitor});changedForms.delete(f);checkoutClose(d);posMessage('Register connection timings saved for this store.');}
   catch(error){checkoutError(d,error);}finally{saving=false;}
  };
 }catch(error){posMessage(error.message);}
};

if(!officeMode)(()=>{
 const register=$('navCheckout'),label=$('connection');
 register.innerHTML='<span id="deskConnectionIndicator" aria-hidden="true"></span><span>Register</span>';
 const light=$('deskConnectionIndicator');label.setAttribute('role','status');label.setAttribute('aria-live','polite');
 let timing={...deskConnectionDefaults},started=Date.now(),startedTick=performance.now(),lastSuccess=null,lastSuccessTick=null,lastSuccessLabel='',offlineObserved=!navigator.onLine;
 let nextCheck=0,inflight=null,controller=null,timeout=null,ticker=null,stopped=false;
 let configStore=null,configOwner=null,nextConfig=0,configLoading=false;
 const labels={checking:'Checking server connection…',connected:'Connected to Operations',delayed:'Connection delayed',disconnected:'Server unreachable'};
 function render(){
  // A PC clock correction must not keep a stale connection green. Wall time
  // also catches platforms whose monotonic clock pauses while the PC sleeps.
  const age=Math.max(0,Date.now()-(lastSuccess??started),performance.now()-(lastSuccessTick??startedTick));
  const state=offlineObserved||!navigator.onLine||age>=timing.offline_seconds*1000?'disconnected':lastSuccess===null?'checking':age>=timing.warning_seconds*1000?'delayed':'connected';
  light.dataset.state=state;light.textContent={checking:'…',connected:'✓',delayed:'!',disconnected:'×'}[state];
  if(label.textContent!==labels[state])label.textContent=labels[state];
  label.dataset.connectionState=state;
  const detail=labels[state]+'. Last successful check: '+(lastSuccess===null?'none yet':lastSuccessLabel+' ('+Math.floor(age/1000)+' seconds ago)')+'. Checks every '+timing.interval_seconds+' seconds.';
  register.title=detail;label.title=detail;register.setAttribute('aria-label','Register — '+labels[state]);
 }
 function checkNow(){
  if(stopped||inflight)return inflight;
  nextCheck=performance.now()+timing.interval_seconds*1000;
  if(!navigator.onLine){offlineObserved=true;render();return Promise.resolve();}
  const nonce=crypto.randomUUID().replaceAll('-','');controller=new AbortController();
  timeout=setTimeout(()=>controller?.abort(),Math.min(5000,timing.interval_seconds*500));
  inflight=(async()=>{
   try{
    const response=await fetch('/api/desk-connection?nonce='+nonce,{cache:'no-store',credentials:'omit',redirect:'error',signal:controller.signal});
    if(!response.ok||!response.headers.get('content-type')?.includes('application/json'))throw Error('No verified server response');
    const result=await response.json();
    if(result.service!=='coastyouth-operations'||result.online!==true||result.nonce!==nonce)throw Error('Unexpected server response');
    if(stopped)return;
    lastSuccess=Date.now();lastSuccessTick=performance.now();lastSuccessLabel=new Date(lastSuccess).toLocaleTimeString();offlineObserved=false;
   }catch{}finally{clearTimeout(timeout);timeout=null;controller=null;inflight=null;render();}
  })();
  return inflight;
 }
 async function loadConfig(){
  if(!user||configLoading)return;
  const store=checkoutStore(),owner=user.name,now=performance.now();
  if(store===configStore&&owner===configOwner&&now<nextConfig)return;
  if(store!==configStore||owner!==configOwner){timing={...deskConnectionDefaults};configStore=store;configOwner=owner;nextCheck=0;}
  configLoading=true;nextConfig=now+60000;
  try{
   const {settings}=await checkoutQuery('checkout-settings');
   if(user?.name!==owner||checkoutStore()!==store)return;
   const candidate=settings.connection_monitor;
   if(candidate&&Object.keys(deskConnectionDefaults).every(k=>Number.isInteger(candidate[k]))&&candidate.interval_seconds>=5&&candidate.interval_seconds<=60&&candidate.warning_seconds>=candidate.interval_seconds*2&&candidate.warning_seconds<=300&&candidate.offline_seconds>=candidate.warning_seconds+candidate.interval_seconds&&candidate.offline_seconds<=600){
    const changed=JSON.stringify(timing)!==JSON.stringify(candidate);timing={...candidate};if(changed)nextCheck=0;
   }
  }catch{}finally{configLoading=false;render();}
 }
 function tick(){render();if(performance.now()>=nextCheck)checkNow();loadConfig();}
 function start(){stopped=false;clearInterval(ticker);render();checkNow();loadConfig();ticker=setInterval(tick,1000);}
 window.deskConnectionMonitor={checkNow};
 window.addEventListener('offline',()=>{offlineObserved=true;render();});
 window.addEventListener('online',()=>{render();checkNow();});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden){render();checkNow();loadConfig();}});
 window.addEventListener('pagehide',()=>{stopped=true;clearInterval(ticker);clearTimeout(timeout);controller?.abort();});
 window.addEventListener('pageshow',e=>{if(e.persisted)start();});
 start();
})();
