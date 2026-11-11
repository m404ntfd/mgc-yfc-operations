// Shared native desktop registration; ordinary web browsers keep their current login flow.
(()=>{
 const get=id=>document.getElementById(id),safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let info=null,state=null,busy=false,dialog=null,button=null,lastStatus='Connected';
 const dirty=()=>typeof hasUnfinishedWork==='function'?hasUnfinishedWork():typeof unfinished==='function'&&unfinished();
 const clearForm=form=>{if(typeof changedForms!=='undefined')changedForms.delete(form);};
 const discard=()=>!get('nativeTerminalForm')||!changedForms.has(get('nativeTerminalForm'))||confirm('Discard unsaved terminal registration changes?');
 const required=()=>state&&(!state.computer.registered||(info.app==='pos'&&!state.terminal));
 function label(){if(!button)return;button.textContent=state?.computer.registered?'Terminal: '+state.computer.name+' · Registered':'Terminal setup · Registration required';}
 async function show(){
  if(dialog?.open)return;
  if(!state)return;
  dialog ||= document.createElement('dialog');dialog.id='nativeTerminalSetup';dialog.className='nativeTerminalSetup';
  if(!dialog.isConnected)document.body.append(dialog);
  let choices=[],stores=[],editRevision=state.computer.revision;
  if(user.admin&&info.app==='pos'&&!state.terminal){
   try{const config=await api('pos/retail-config');choices=config.terminals.filter(t=>!t.device&&t.enabled);stores=config.stores;}
   catch(error){
    dialog.dataset.verifying='true';dialog.innerHTML='<h2>Terminal setup</h2><p>Unable to load checkout assignments. Reconnect to the server to finish registration.</p><p id="nativeTerminalError" role="status"></p><button id="nativeTerminalRetry" type="button">Retry connection</button><button id="nativeTerminalSignOut" type="button">Sign out</button>';
    get('nativeTerminalError').textContent=error.message;dialog.oncancel=e=>e.preventDefault();get('nativeTerminalRetry').onclick=()=>refresh(true);get('nativeTerminalSignOut').onclick=async()=>{await api('logout',{});location.reload();};dialog.showModal();return;
   }
  }
  dialog.innerHTML=`<h2>Terminal setup</h2><p><strong>${state.computer.registered?'Registered: '+safe(state.computer.name):'Register this computer'}</strong></p><p>Server: ${safe(location.origin)}<br>Computer: ${safe(state.computer.hostname)}</p>${state.terminal?`<p>Checkout terminal: <strong>${safe(state.terminal.name)}</strong> · Registered<br>Store: <strong>${safe(state.terminal.store_name)}</strong></p><p>Receipt settings, prices and taxes are shared with all checkouts in this store. Manage them in OFFICE.</p>`:''}<p>Registration stays on the shared server when this computer restarts, changes IP address or receives an update.</p>${user.admin?`<form id="nativeTerminalForm"><label>Registered computer name<input name="name" maxlength="60" required value="${safe(state.computer.name||state.terminal?.name||state.computer.hostname)}"></label><label>Computer role<select name="role">${[['pos','POS checkout'],['office','Office computer'],['server','Server computer'],['other','Other / STORE OPS']].map(([v,t])=>`<option value="${v}" ${v===(state.computer.registered?state.computer.role:info.app==='pos'?'pos':info.app==='ops'?'other':'office')?'selected':''}>${t}</option>`).join('')}</select></label>${info.app==='pos'&&!state.terminal?`<label>Checkout assignment<select name="terminal"><option value="">Create a checkout using this name</option>${choices.map(t=>`<option value="${safe(t.id)}">${safe(t.name)} · ${safe(t.store_name)}</option>`).join('')}</select></label><label>Store<select name="store_id">${stores.map(s=>`<option value="${safe(s.id)}">${safe(s.name)}</option>`).join('')}</select></label><p id="nativeStoreHelp">Receipt settings, prices and taxes come from this store.</p>`:''}<button class="primary">${state.computer.registered?'Save registration':'Register terminal'}</button></form>`:'<p>An administrator must sign in to complete registration before staff use this desktop application.</p>'}<p id="nativeTerminalError" role="status"></p><div class="actions"><button id="nativeTerminalSignOut" type="button">Sign out${user.admin?'':' and sign in as administrator'}</button>${required()?'':'<button id="nativeTerminalClose" type="button">Close</button>'}</div>`;
  dialog.oncancel=e=>{if(required()||!discard())e.preventDefault();else clearForm(get('nativeTerminalForm'));};
  get('nativeTerminalSignOut').onclick=async()=>{if(!discard())return;const form=get('nativeTerminalForm');if(form)clearForm(form);await api('logout',{});location.reload();};
  if(get('nativeTerminalClose'))get('nativeTerminalClose').onclick=()=>{if(!discard())return;const form=get('nativeTerminalForm');if(form)clearForm(form);dialog.close();};
  const setupForm=get('nativeTerminalForm');
  if(setupForm?.elements.terminal){
   const selection=setupForm.elements.terminal,store=setupForm.elements.store_id;
   selection.onchange=()=>{const terminal=choices.find(t=>t.id===selection.value);store.disabled=!!terminal;if(terminal)store.value=terminal.store_id;get('nativeStoreHelp').textContent=terminal?'This existing checkout keeps its registered store. Receipt settings and taxes follow that store.':'Receipt settings, prices and taxes come from this store.';};
  }
  if(user.admin)get('nativeTerminalForm').onsubmit=async e=>{
   e.preventDefault();const form=e.target;const submit=form.querySelector('button');submit.disabled=true;
   try{await api('computers/register',{id:state.computer.id,revision:editRevision,name:form.elements.name.value,role:form.elements.role.value,app:info.app,device:info.device,terminal:form.elements.terminal?.value||'',store_id:form.elements.store_id?.value});clearForm(form);dialog.close();await refresh(true);if(info.app==='pos'&&typeof retailLoadTerminal==='function'){await posLoad();}}
   catch(error){get('nativeTerminalError').textContent=error.message;if(error.status===409){try{state=await api('computers/self',{...info,status:lastStatus});editRevision=state.computer.revision;label();}catch{}}}finally{submit.disabled=false;}
  };
  dialog.showModal();
 }
 window.openTerminalRegistration=async()=>{if(dirty()){(typeof posMessage==='function'?posMessage:toast)('Save or finish your current work before opening terminal setup.');return;}await refresh(true);await show();};
 async function refresh(force=false){
  const native=window.pywebview?.api;if(!native?.terminal_info||busy||window.posUpdateInstalling)return;
  if(!user){if(get('login')&&!get('desktopSetupHint')){const hint=document.createElement('p');hint.id='desktopSetupHint';hint.textContent='First-time computer setup: sign in with an administrator account to register this terminal.';get('login').append(hint);}return;}
  busy=true;
  if(!state){
   dialog ||= document.createElement('dialog');dialog.id='nativeTerminalSetup';dialog.className='nativeTerminalSetup';dialog.dataset.verifying='true';
   if(!dialog.isConnected)document.body.append(dialog);
   dialog.innerHTML='<h2>Terminal setup</h2><p>Checking this computer’s registration with the server…</p><p id="nativeTerminalError" role="status"></p><button id="nativeTerminalRetry" type="button">Retry connection</button><button id="nativeTerminalSignOut" type="button">Sign out</button>';
   dialog.oncancel=e=>e.preventDefault();get('nativeTerminalRetry').onclick=()=>refresh(true);get('nativeTerminalSignOut').onclick=async()=>{await api('logout',{});location.reload();};
   if(!dialog.open)dialog.showModal();
  }
  try{
   info=await native.terminal_info();if(info.error)throw Error(info.error);window.nativeTerminalAvailable=true;
   if(!button){button=document.createElement('button');button.id='nativeTerminalStatus';button.type='button';button.textContent='Terminal setup';button.onclick=window.openTerminalRegistration;(document.querySelector('.headerRight')||document.querySelector('.connectionInfo')||document.querySelector('body>header')).append(button);}
   state=await api('computers/self',{...info,status:lastStatus});window.terminalRegistration=state;label();if(dialog?.dataset.verifying){delete dialog.dataset.verifying;dialog.close();}
   if(required()){if(!dialog?.open)await show();return;}
   if(info.app==='ops'&&native.ops_update_status){
    const job=state.campaign,update=await native.ops_update_status(job?.id||null);
    let banner=get('opsComputerUpdateBanner');if(!banner){banner=document.createElement('aside');banner.id='opsComputerUpdateBanner';banner.setAttribute('role','status');document.body.prepend(banner);}
    banner.hidden=!job||update.state==='complete';lastStatus=update.error||update.state||'Connected';
    banner.textContent=update.error||('STORE OPS update pending. Finish and save your work. '+(update.seconds?'Update in '+update.seconds+' seconds.':'Waiting for unfinished work to be saved.'));
    if(job&&update.state==='ready'&&!update.seconds&&!dirty()&&!dialog?.open){const result=await native.ops_install_update();if(result.error)banner.textContent=result.error;}
   }
  }catch(error){if(button)button.textContent='Terminal setup · Unable to verify';if(dialog?.open)get('nativeTerminalError').textContent=error.message;}
  finally{busy=false;}
 }
 if(typeof officeMode==='undefined'){
  window.posUpdateFreeze=()=>{if(dirty()||dialog?.open)return false;window.posUpdateInstalling=true;document.body.inert=true;return true;};
  window.posUpdateUnfreeze=()=>{window.posUpdateInstalling=false;document.body.inert=false;};
 }
 // STORE OPS may finish fetching its starting-page choice after desktop setup opens.
 // Keep required registration above that chooser without discarding either form.
 if(typeof chooseLanding==='function'){
  const landing=chooseLanding;chooseLanding=async function(...args){await landing(...args);if(dialog?.open){dialog.close();dialog.showModal();}};
 }
 const before=boot;boot=async function(...args){await before(...args);await refresh();};
 window.addEventListener('pywebviewready',()=>refresh());setTimeout(()=>refresh(),300);setInterval(()=>refresh(),5000);
})();
