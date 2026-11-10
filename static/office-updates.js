// OFFICE manages desktop rollouts and the existing coordinated server/web updater.
let officeWebRelease=null;
function officeWebUpdateMarkup(){return `<section class="officeWebUpdate" aria-labelledby="officeWebHeading">
 <div class="officeUpdateHeading"><div><span class="eyebrow">SHARED WEBSITE</span><h3 id="officeWebHeading">STORE OPS web app &amp; server</h3></div><span class="officeUpdateTag">One shared update</span></div>
 <p>Updates operations.coastyfc.com and the shared server used by every application. The server briefly restarts; users will sign in again. The existing backup and recovery process protects saved data.</p>
 <div class="computerVersions"><article><span>Installed version</span><strong id="officeWebCurrent">Loading…</strong></article><article><span>Latest release</span><strong id="officeWebLatest">Not checked</strong></article><article><span>Other active users</span><strong id="officeWebActive">Checking…</strong></article></div>
 <p id="officeWebStatus" role="status">Loading server status…</p><p id="officeWebError" role="alert"></p>
 <details><summary>Connections &amp; release notes</summary><div id="officeWebConnections"></div><pre id="officeWebNotes"></pre></details>
 <div class="officeUpdateButtons"><button id="officeWebCheck" type="button">Check web app update</button><button id="officeWebNotify" class="primary" type="button" disabled>Notify users &amp; update when ready</button><button id="officeWebInstall" type="button" disabled>Install &amp; restart</button><button id="officeWebCancel" type="button" hidden>Cancel pending web update</button></div>
 <p class="muted">Your current session and the background server are excluded. Install &amp; restart is available when no other users are active. Updates wait for active users to finish and acknowledge.</p>
 </section>`;}

function officeAttachWebUpdates(dialog){
 const get=id=>dialog.querySelector('#'+id);
 let installed=null,connections=null,pending=null,reading=false,acting=false,checking=false;
 const alive=()=>dialog.isConnected&&dialog.open&&user?.admin;
 function render(){
  if(!alive())return;
  const release=officeWebRelease,available=!!release?.available&&release.current===installed?.current;
  get('officeWebCurrent').textContent=installed?.current||'Unavailable';
  get('officeWebLatest').textContent=checking?'Checking…':release?.latest||'Not checked';
  get('officeWebActive').textContent=connections?String(connections.other_connections):'Unavailable';
  get('officeWebNotes').textContent=release?.notes||'Check for updates to view the latest release notes.';
  get('officeWebConnections').replaceChildren();
  for(const row of connections?.connections||[]){const p=document.createElement('p');p.textContent=row.name+(row.current?' · You (this session)':'')+' · '+row.kind+' · '+(row.status==='active'?'Active':'Inactive');get('officeWebConnections').append(p);}
  if(connections&&!connections.connections.length)get('officeWebConnections').textContent='No other signed-in connections.';
  const unavailable=!installed?.launcher,blocked=acting||checking||pending?.active||!available||unavailable||!connections;
  get('officeWebCheck').disabled=acting||checking||!!pending?.active;
  get('officeWebNotify').disabled=blocked;
  get('officeWebInstall').disabled=blocked||connections.other_connections>0;
  get('officeWebCancel').hidden=!pending?.active;
  get('officeWebCancel').disabled=acting||pending?.phase!=='waiting';
  get('officeWebStatus').textContent=pending?.active?`Web update ${pending.version}: ${pending.phase==='preparing'?'preparing update':pending.phase==='applying'?'installing and restarting':`waiting for ${pending.waiting} user(s)`}.`:unavailable?'Start the managed server to enable installation.':available?`Version ${release.latest} is available. ${connections?.other_connections?'Notify users so they can finish their work.':'Ready to update when your work is saved.'}`:release?.current===installed?.current?'The STORE OPS web app and server are up to date.':'Check for the latest STORE OPS web app and server release.';
 }
 async function refresh(){
  if(!alive()||reading||acting)return;reading=true;
  try{const values=await Promise.all([api('updates'),api('admin/update-connections'),api('update-flow')]);[installed,connections,pending]=values;}
  catch(e){connections=null;if(alive())get('officeWebError').textContent='Could not verify server readiness: '+e.message;}
  finally{reading=false;render();}
 }
 async function check(){
  if(!alive()||checking||acting)return;checking=true;officeWebRelease=null;get('officeWebError').textContent='';render();
  try{officeWebRelease=await api('update-check',{});}
  catch(e){if(alive())get('officeWebError').textContent='Update check failed: '+e.message;}
  finally{checking=false;await refresh();render();}
 }
 async function start(direct){
  if(acting||checking||!alive())return;
  if(unfinished()){get('officeWebError').textContent='Save or clear your unfinished entries before requesting a web app update.';return;}
  await refresh();
  if(!alive()||!connections||!installed?.launcher||!officeWebRelease?.available||officeWebRelease.current!==installed.current||pending?.active)return;
  if(direct&&connections.other_connections){get('officeWebError').textContent='Other users are active. Choose Notify users & update when ready.';return;}
  if(!confirm(direct?'Install the STORE OPS web app and server update? The server will restart and everyone will sign in again.':'Notify active users to finish their work, then update the STORE OPS web app and server? The server will restart after they are ready.'))return;
  acting=true;get('officeWebError').textContent='';render();
  try{
   // Both entry points use the coordinator. A connection arriving after the check
   // must still finish and acknowledge before the server can restart.
   flow=await api('update-flow/start',{version:officeWebRelease.latest,ready:true});
   if(flow.receipt)sessionStorage.setItem('yfc-pos-update-receipt',flow.receipt);
   flowSeen=flow.id;flowMandatory=true;
   dialog.close();dialog.remove();showFlow(true);
  }catch(e){if(alive())get('officeWebError').textContent=e.message;}
  finally{acting=false;render();}
 }
 get('officeWebCheck').onclick=check;
 get('officeWebNotify').onclick=()=>start(false);get('officeWebInstall').onclick=()=>start(true);
 get('officeWebCancel').onclick=async()=>{
  if(acting||!pending?.active||!confirm('Cancel the pending STORE OPS web app and server update?'))return;
  acting=true;render();try{await api('update-flow/cancel',{id:pending.id});get('officeWebError').textContent='';}catch(e){if(alive())get('officeWebError').textContent=e.message;}finally{acting=false;await refresh();}
 };
 const timer=setInterval(refresh,5000);dialog.addEventListener('close',()=>clearInterval(timer),{once:true});refresh();return {check};
}

if(officeMode){
 const progress=document.createElement('p');progress.id='officeWebProgress';progress.setAttribute('role','status');$('updateText').after(progress);
 const cancel=document.createElement('button');cancel.id='officeWebFlowCancel';cancel.type='button';cancel.textContent='Cancel pending web update';cancel.hidden=true;$('updateReady').after(cancel);
 let cancelBusy=false;
 const previousShowFlow=showFlow;
 showFlow=function(mandatory=false){
  previousShowFlow(mandatory);
  const admin=!!user?.admin,active=!!flow?.active;
  progress.hidden=!admin||!active;
  if(admin&&active){
   progress.textContent=flow.phase==='preparing'?'Preparing the STORE OPS web app and server update…':flow.phase==='applying'?'Installing the STORE OPS web app and server update. Reconnecting…':`Waiting for ${flow.waiting} active user(s) to finish and acknowledge.`;
   if(flow.connections?.length)progress.textContent+=' '+flow.connections.map(p=>p.name+': '+p.status).join(' · ');
   if(flow.requester){$('updateReady').hidden=true;$('updateText').textContent='Your update request is ready. Staff can finish their current work before the shared server restarts.';}
  }
  cancel.hidden=!admin||!active;cancel.disabled=cancelBusy||flow?.phase!=='waiting';
 };
 cancel.onclick=async()=>{
  if(cancelBusy||!flow?.active||!confirm('Cancel the pending STORE OPS web app and server update?'))return;
  cancelBusy=true;cancel.disabled=true;$('updateError').textContent='';
  try{flow=await api('update-flow/cancel',{id:flow.id});showFlow(true);}catch(e){$('updateError').textContent=e.message;}finally{cancelBusy=false;showFlow(true);}
 };
}
