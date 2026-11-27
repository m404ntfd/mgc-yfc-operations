// Connection checks only. Never retry a sale, payment, or sign-in submission.
(()=>{
 const app=location.pathname.startsWith('/office')?'office':location.pathname.startsWith('/pos')?'pos':'ops';
 const key='coastyouth-connection-'+app,logoutKey=key+'-logout';
 const read=()=>{try{return JSON.parse(localStorage.getItem(key)||'{}');}catch{return {};}};
 let preferences=read(),dialog=null,sequence=0,active=null,failed=false,logoutPending=false;
 try{logoutPending=localStorage.getItem(logoutKey)==='1';}catch{}
 const timeout=()=>Number.isInteger(preferences.timeout_seconds)&&preferences.timeout_seconds>=1&&preferences.timeout_seconds<=120?preferences.timeout_seconds:10;
 const rings='<span class="connectionRings" role="img" aria-label="Youth for Christ three rings"><i></i><i></i><i></i></span>';
 const bars='<div class="connectionTrack" role="progressbar" aria-label="Connecting to Server">'+Array.from({length:22},()=>'<i></i>').join('')+'</div>';
 const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 if(/^(glass-(blue|teal|violet|rose|graphite)|classic-gray|harbor-blue|coastal-teal|midnight|coastyouth-red)$/.test(preferences.theme||''))document.body.dataset.retailTheme=preferences.theme;
 function make(){
  if(!dialog){dialog=document.createElement('dialog');dialog.id='serverConnectionDialog';dialog.className='serverConnectionDialog';dialog.setAttribute('aria-labelledby','serverConnectionTitle');dialog.addEventListener('cancel',e=>e.preventDefault());document.body.append(dialog);}
  return dialog;
 }
 function stop(abort=true){if(active){clearTimeout(active.timer);clearInterval(active.animation);if(abort)active.controller.abort();active=null;}sequence++;}
 function clearConnectionForm(){const form=document.getElementById('browserServerConnection');if(form&&typeof changedForms!=='undefined')changedForms.delete(form);}
 function close(abort=true){stop(abort);failed=false;clearConnectionForm();dialog?.close();}
 function paint(message,error=false){
  make();clearConnectionForm();dialog.dataset.state=error?'failed':'connecting';
  dialog.innerHTML=rings+(error?'':bars)+'<h2 id="serverConnectionTitle">'+(error?'Can Not Connect to Operations Server':'Connecting to Server')+'</h2>'+(error?'<p id="serverConnectionDetail"></p><div class="connectionActions"><button type="button" id="serverConnectionRetry" class="primary">Retry Connection</button><button type="button" id="serverConnectionConfigure">Configure Server Connection</button><button type="button" id="serverConnectionLogout">Log Out</button></div>':'');
  dialog.setAttribute('aria-busy',String(!error));if(!dialog.open)dialog.showModal();
  if(error){dialog.querySelector('#serverConnectionDetail').textContent=message||'Check that the server and your network or VPN are available.';dialog.querySelector('#serverConnectionRetry').onclick=retry;dialog.querySelector('#serverConnectionConfigure').onclick=configure;dialog.querySelector('#serverConnectionLogout').onclick=logout;dialog.querySelector('#serverConnectionRetry').focus();}
 }
 function fail(message){stop();failed=true;paint(message,true);}
 async function run(task){
  if(active)throw Error('A connection check is already running.');
  failed=false;paint();const id=++sequence,controller=new AbortController();let position=0,direction=1;
  const cells=[...dialog.querySelectorAll('.connectionTrack i')];
  function animate(){for(let i=0;i<cells.length;i++)cells[i].classList.toggle('lit',i>=position&&i<position+7);if(!matchMedia('(prefers-reduced-motion: reduce)').matches){position+=direction;if(position===15||position===0)direction*=-1;}}
  animate();const current={controller,animation:setInterval(animate,80),timer:null};active=current;
  try{
   const result=await Promise.race([Promise.resolve().then(()=>task(controller.signal)),new Promise((_,reject)=>{current.timer=setTimeout(()=>{reject(Error('No response within '+timeout()+' seconds. Check the server address or retry the connection.'));controller.abort();},timeout()*1000);})]);
   if(sequence!==id)throw Object.assign(Error('Connection check was canceled.'),{connectionCanceled:true});
   close(false);return result;
  }catch(error){if(sequence===id){if(error.status&&error.status<500)close();else fail(error.message);}throw error;}
 }
 async function verified(signal){
  const response=await fetch('/api/session',{cache:'no-store',signal,redirect:'error'});
  if(!response.ok)throw Error('The Operations server is unavailable.');
  const data=await response.json();if(data.application!=='thrift-mart-dispatch')throw Error('This address is not an Operations server.');return data;
 }
 async function finishLogout(signal){
  const response=await fetch('/api/logout',{method:'POST',headers:{'Content-Type':'application/json','X-Dispatch':'1'},body:'{}',signal,redirect:'error'});
  if(!response.ok)throw Error('Reconnect to finish signing out of the server.');
  logoutPending=false;try{localStorage.removeItem(logoutKey);}catch{}
 }
 async function retry(){
  try{await run(async signal=>{await verified(signal);if(logoutPending)await finishLogout(signal);});if(window.retryTerminalConnection)await window.retryTerminalConnection();else if(typeof boot==='function')await boot();}catch{}
 }
 async function logout(){
  if(window.desktopConnectionCanChange&&!window.desktopConnectionCanChange()){dialog.querySelector('#serverConnectionDetail').textContent='Save or finish current work before logging out.';return;}
  logoutPending=true;try{localStorage.setItem(logoutKey,'1');}catch{try{await run(finishLogout);}catch{return;}}
  if(typeof changedForms!=='undefined')for(const id of ['nativeServerForm','nativeTerminalLogin',...(typeof user==='undefined'||!user?['login']:[])])changedForms.delete(document.getElementById(id));
  // Reload clears this screen immediately. A pending logout must finish before
  // the next session/sign-in response can expose an authenticated application.
  location.reload();
 }
 function configure(){
  if(window.desktopConnectionCanChange&&!window.desktopConnectionCanChange()){dialog.querySelector('#serverConnectionDetail').textContent='Save or finish current work before changing the connection.';return;}
  close();if(window.pywebview?.api?.desktop_reconnect&&window.openServerConnection){window.openServerConnection();return;}browserEditor();
 }
 function browserEditor(){
  make();dialog.dataset.state='configure';dialog.innerHTML=rings+'<h2 id="serverConnectionTitle">Configure Server Connection</h2><form id="browserServerConnection"><label>Server address<input name="server" value="'+safe(location.origin)+'" required></label><label>Connection timeout (seconds)<input name="timeout" type="number" min="1" max="120" step="1" value="'+timeout()+'" required></label><p>Default: 10 seconds. Saved on this device. Opening another server requires signing in there.</p><p id="connectionConfigError" role="status"></p><div class="connectionActions"><button class="primary">Connect</button><button type="button" id="connectionConfigCancel">Cancel</button></div></form>';dialog.showModal();
  dialog.querySelector('#connectionConfigCancel').onclick=()=>{close();fail();};
  dialog.querySelector('form').onsubmit=async e=>{e.preventDefault();const f=e.target;try{let text=f.elements.server.value.trim();if(!text.includes('://'))text=(text.split('/')[0].split(':')[0]==='operations.coastyfc.com'?'https://':'http://')+text;const url=new URL(text);if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash||!['','/'].includes(url.pathname))throw Error('Enter only the HTTP or HTTPS server address.');await saveTimeout(Number(f.elements.timeout.value));if(url.origin===location.origin){close();await retry();}else location.assign(url.origin+location.pathname);}catch(error){dialog.querySelector('#connectionConfigError').textContent=error.message;}};
 }
 function hex(color,fallback){const values=color.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)/);return values?'#'+values.slice(1,4).map(n=>(+n).toString(16).padStart(2,'0')).join(''):fallback;}
 function remember(required=false){
  const body=getComputedStyle(document.body),probe=document.createElement('dialog');probe.className='serverConnectionDialog';document.body.append(probe);const panel=getComputedStyle(probe);
  const button=document.createElement('button');button.className='primary';probe.append(button);const primary=getComputedStyle(button);
  const value={...preferences,timeout_seconds:timeout(),theme:document.body.dataset.retailTheme||preferences.theme,background:hex(body.backgroundColor,'#eef3f8'),panel:hex(panel.backgroundColor,'#ffffff'),text:hex(panel.color,'#19334a'),muted:hex(panel.color,'#41586c'),accent:hex(primary.backgroundColor,'#245c8e'),border:hex(panel.borderTopColor,'#8da4ba')};probe.remove();preferences=value;
  try{localStorage.setItem(key,JSON.stringify(value));}catch{}
  return Promise.resolve(window.pywebview?.api?.connection_preferences?.(value)).then(result=>{if(result?.error)throw Error(result.error);}).catch(error=>{if(required)throw error;});
 }
 async function saveTimeout(value){if(!Number.isInteger(value)||value<1||value>120)throw Error('Use a whole number from 1 to 120 seconds.');preferences.timeout_seconds=value;await remember(true);return value;}
 const ordinaryFetch=window.fetch.bind(window);
 async function request(path,options){
  const isLogin=['session','login','pos-pin-login'].includes(path);
  if(!isLogin)return ordinaryFetch('/api/'+path,options);
  // API response parsing remains with its existing caller. Invalid credentials
  // are an authentication error, not a lost server connection.
  const task=async signal=>{if(logoutPending)await finishLogout(signal);const response=await ordinaryFetch('/api/'+path,{...options,signal,redirect:'error'});if(response.status>=500)throw Error('The Operations server is unavailable.');const body=await response.clone().text();if(path==='session'&&response.ok&&JSON.parse(body).application!=='thrift-mart-dispatch')throw Error('This address is not an Operations server.');return response;};
  if(active)return task(AbortSignal.timeout(timeout()*1000));
  return run(task);
 }
 window.ConnectionStatus={run,fail,close,retry,configure,request,saveTimeout,get timeout(){return timeout();},get visible(){return !!dialog?.open;},get failed(){return failed;}};
 new MutationObserver(()=>remember()).observe(document.body,{attributes:true,attributeFilter:['data-retail-theme']});
 new MutationObserver(()=>remember()).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
 window.addEventListener('pywebviewready',async()=>{try{const value=await window.pywebview.api.connection_preferences?.();if(value&&!value.error){preferences={...preferences,...value};}remember();}catch{}});
 window.addEventListener('pagehide',stop);
})();
