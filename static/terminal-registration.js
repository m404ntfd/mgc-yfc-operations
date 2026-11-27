// Shared native desktop registration; ordinary web browsers keep their current login flow.
(()=>{
 const get=id=>document.getElementById(id),safe=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let info=null,state=null,busy=false,dialog=null,button=null,lastStatus='Connected',setupRequested=new URLSearchParams(location.search).get('setup')==='1';
 const dirty=()=>typeof hasUnfinishedWork==='function'?hasUnfinishedWork():typeof unfinished==='function'&&unfinished();
 const clearForm=form=>{if(typeof changedForms!=='undefined')changedForms.delete(form);};
 const discard=()=>!get('nativeTerminalForm')||!changedForms.has(get('nativeTerminalForm'))||confirm('Discard unsaved terminal registration changes?');
 const required=()=>state&&(!state.computer.registered||(info.app==='pos'&&!state.terminal));
 const connectionButton=()=>window.pywebview?.api?.desktop_reconnect?'<button type="button" data-terminal-connection>Server address / reconnect</button>':'';
 const reportError=message=>{const target=get('nativeTerminalError');if(target&&dialog?.open)target.textContent=message;else (typeof posMessage==='function'?posMessage:toast)(message);};
 window.desktopConnectionCanChange=()=>{
  if(window.posUpdateInstalling)return false;
  const excluded=[];
  for(const id of ['nativeServerForm','nativeTerminalLogin',...(!user?['login']:[])]){const form=get(id);if(form&&changedForms.has(form)){excluded.push([form,changedForms.get(form)]);changedForms.delete(form);}}
  try{return !dirty();}finally{for(const [form,value]of excluded)changedForms.set(form,value);}
 };
 function bindConnection(){for(const b of dialog.querySelectorAll('[data-terminal-connection]'))b.onclick=serverEditor;}
 async function serverEditor(){
  if(!window.pywebview?.api?.desktop_reconnect)return;
  if(busy||dialog?.dataset.saving){reportError('Finish checking the connection, then try again.');return;}
  if(!discard())return;clearForm(get('nativeTerminalForm'));
  if(!window.desktopConnectionCanChange()){reportError('Finish or save current work before changing the server connection.');return;}
  dialog ||= document.createElement('dialog');dialog.id='nativeTerminalSetup';dialog.className='nativeTerminalSetup';
  if(!dialog.isConnected)document.body.append(dialog);
  clearForm(get('nativeTerminalLogin'));delete dialog.dataset.verifying;dialog.dataset.serverEditor='true';
  dialog.innerHTML=`<h2>Server connection & PC registration</h2><p>Connect to your CoastYouth server, then sign in with an administrator account to register this PC.</p><form id="nativeServerForm"><label>Server address<input name="server" type="text" required value="${safe(location.origin)}" autocomplete="url" autocapitalize="none" spellcheck="false"></label><p>Connection timeout: <strong>${window.ConnectionStatus.timeout} seconds</strong>. Managed in OFFICE and refreshed after a successful login.</p><p>Examples: https://operations.coastyfc.com or http://SERVER-PC:8080. Connect your VPN first if it is required.</p>${location.pathname.startsWith('/pos')?'<label>Admin exit passcode<input name="code" type="password" inputmode="numeric" autocomplete="off"></label><p>The existing exit passcode is needed only when changing the DESK server address.</p>':''}<p>Saved records and this computer’s identity are kept. An address is saved only after the server responds successfully.</p><button class="primary" type="submit">Connect & register PC</button></form><p id="nativeTerminalError" role="status"></p><button id="nativeServerCancel" type="button">Cancel</button>`;
  const back=async()=>{if(dialog.dataset.saving)return;clearForm(get('nativeServerForm'));delete dialog.dataset.serverEditor;dialog.close();await refresh(true);if(required())await show();};
  get('nativeServerCancel').onclick=back;dialog.oncancel=e=>{e.preventDefault();back();};
  get('nativeServerForm').onsubmit=async e=>{
   e.preventDefault();if(dialog.dataset.saving)return;dialog.dataset.saving='true';const form=e.target;
   const address=form.elements.server.value,code=form.elements.code?.value||'';if(form.elements.code)form.elements.code.value='';
   for(const control of dialog.querySelectorAll('button,input'))control.disabled=true;reportError('Checking the server connection…');
   try{dialog.close();await window.ConnectionStatus.run(async()=>{const result=await window.pywebview.api.desktop_reconnect(address,code);if(result?.error)throw Error(result.error);return result;});clearForm(form);}
   catch(error){reportError(error.message);}
   finally{delete dialog.dataset.saving;for(const control of dialog.querySelectorAll('button,input'))control.disabled=false;}
  };
  if(!dialog.open)dialog.showModal();
 }
 window.openServerConnection=serverEditor;
 function connectionEntry(){
  if(!window.pywebview?.api?.desktop_reconnect||get('desktopConnectionSetup'))return;
  const control=document.createElement('button');control.type='button';control.id='desktopConnectionSetup';control.textContent='Server connection / register PC';control.onclick=serverEditor;
  (get('auth')||document.querySelector('body>header')).append(control);
 }
 function label(){if(!button)return;button.disabled=false;button.textContent=state?.computer.registered&&!required()?'Terminal: '+state.computer.name+' · Registered':'Terminal setup · Registration required';}
 function recovery(message){
  window.ConnectionStatus.fail(message);
 }
 async function show(){
  if(dialog?.open||window.ConnectionStatus.visible)return;
  if(!state||!user)return;
  dialog ||= document.createElement('dialog');dialog.id='nativeTerminalSetup';dialog.className='nativeTerminalSetup';
  if(!dialog.isConnected)document.body.append(dialog);
  let choices=[],stores=[],editRevision=state.computer.revision;
  const removed=state.removed_terminal;
  if(user?.admin&&info.app==='pos'&&!state.terminal&&!removed){
   try{const config=await api('pos/retail-config');choices=config.terminals.filter(t=>!t.device&&t.enabled);stores=config.stores;}
   catch(error){
    recovery('Unable to load checkout assignments. '+error.message);return;
   }
  }
  dialog.innerHTML=`<h2>Terminal setup</h2><p><strong>${state.computer.registered?'Registered: '+safe(state.computer.name):'Register this computer'}</strong></p><p>Server: ${safe(location.origin)}<br>Computer: ${safe(state.computer.hostname)}</p>${state.terminal?`<p>Checkout terminal: <strong>${safe(state.terminal.name)}</strong> · Registered<br>Store: <strong>${safe(state.terminal.store_name)}</strong></p><p>Receipt settings, prices and taxes are shared with all checkouts in this store. Manage them in OFFICE.</p>`:''}<p>Registration stays on the shared server when this computer restarts, changes IP address or receives an update.</p>${user.admin?`<form id="nativeTerminalForm"><label>Registered computer name<input name="name" maxlength="60" required value="${safe(state.computer.name||state.terminal?.name||state.computer.hostname)}"></label><label>Computer role<select name="role">${[['pos','POS checkout'],['office','Office computer'],['server','Server computer'],['other','Other / STORE OPS']].map(([v,t])=>`<option value="${v}" ${v===(state.computer.registered?state.computer.role:info.app==='pos'?'pos':info.app==='ops'?'other':'office')?'selected':''}>${t}</option>`).join('')}</select></label>${info.app==='pos'&&!state.terminal?`<label>Checkout assignment<select name="terminal"><option value="">Create a checkout using this name</option>${choices.map(t=>`<option value="${safe(t.id)}">${safe(t.name)} · ${safe(t.store_name)}</option>`).join('')}</select></label><label>Store<select name="store_id">${stores.map(s=>`<option value="${safe(s.id)}">${safe(s.name)}</option>`).join('')}</select></label><p id="nativeStoreHelp">Receipt settings, prices and taxes come from this store.</p>`:''}<button class="primary">${state.computer.registered?'Save registration':'Register terminal'}</button></form>`:'<p>An administrator must sign in to complete registration before staff use this desktop application.</p>'}<p id="nativeTerminalError" role="status"></p><div class="actions"><button id="nativeTerminalSignOut" type="button">Sign out${user.admin?'':' and sign in as administrator'}</button>${required()?'':'<button id="nativeTerminalClose" type="button">Close</button>'}</div>`;
  if(removed){
   const note=document.createElement('section');note.className='nativeRegistrationNotice';note.innerHTML=`<h3>This checkout was removed</h3><p><strong>${safe(removed.name)}</strong> · ${safe(removed.store_name)}</p><p>Re-register the original terminal to keep its store, receipt settings, taxes and history. Previous sales and reports remain intact.</p>`;
   dialog.querySelector('h2').after(note);
   const form=get('nativeTerminalForm');
   if(form){
    for(const name of ['terminal','store_id'])form.elements[name]?.closest('label').remove();get('nativeStoreHelp')?.remove();
    const confirmation=document.createElement('label');confirmation.className='nativeRestoreConfirm';confirmation.innerHTML='<input name="confirm_restore" type="checkbox" required> Re-register this original terminal';form.querySelector('button').before(confirmation);form.querySelector('button').textContent='Re-register terminal';
   }
  }
  if(!user?.admin){
   const login=document.createElement('form');login.id='nativeTerminalLogin';login.innerHTML='<h3>Administrator sign-in</h3><label>Admin username<input name="name" required autocomplete="username"></label><label>Admin password<input name="password" type="password" required autocomplete="current-password"></label><button type="submit" class="primary">Sign in & register PC</button>';
   get('nativeTerminalError').before(login);
   login.onsubmit=async e=>{
    e.preventDefault();if(dialog.dataset.saving)return;dialog.dataset.saving='true';const submit=login.querySelector('button');submit.disabled=true;
    try{
     await api('login',{name:login.elements.name.value,password:login.elements.password.value});clearForm(login);
     const session=await api('session');user=session.user;
     if(!user?.admin)throw Error('This account is not an administrator. Enter an administrator account to register the PC.');
     // Boot also refreshes registration. Keep that refresh deferred until the
     // administrator handoff finishes, so it cannot redraw a newly edited form.
     dialog.close();await boot();delete dialog.dataset.saving;await refresh(true);await show();
    }catch(error){reportError(error.message);}
    finally{login.elements.password.value='';clearForm(login);delete dialog.dataset.saving;submit.disabled=false;}
   };
  }
  dialog.querySelector('.actions').insertAdjacentHTML('afterbegin',connectionButton()+'<button type="button" id="nativeRegistrationRefresh">Refresh registration</button>');bindConnection();
  get('nativeRegistrationRefresh').onclick=async()=>{if(dialog.dataset.saving||!discard())return;clearForm(get('nativeTerminalForm'));clearForm(get('nativeTerminalLogin'));dialog.close();await refresh(true);await show();};
  dialog.oncancel=e=>{if(required()||dialog.dataset.saving||!discard())e.preventDefault();else{clearForm(get('nativeTerminalForm'));clearForm(get('nativeTerminalLogin'));}};
  get('nativeTerminalSignOut').onclick=async()=>{if(dialog.dataset.saving||!discard())return;clearForm(get('nativeTerminalForm'));clearForm(get('nativeTerminalLogin'));try{await api('logout',{});location.reload();}catch(error){reportError(error.message);}};
  if(get('nativeTerminalClose'))get('nativeTerminalClose').onclick=()=>{if(dialog.dataset.saving||!discard())return;clearForm(get('nativeTerminalForm'));clearForm(get('nativeTerminalLogin'));dialog.close();};
  const setupForm=get('nativeTerminalForm');
  if(setupForm?.elements.terminal){
   const selection=setupForm.elements.terminal,store=setupForm.elements.store_id;
   selection.onchange=()=>{const terminal=choices.find(t=>t.id===selection.value);store.disabled=!!terminal;if(terminal)store.value=terminal.store_id;get('nativeStoreHelp').textContent=terminal?'This existing checkout keeps its registered store. Receipt settings and taxes follow that store.':'Receipt settings, prices and taxes come from this store.';};
  }
  if(user?.admin)get('nativeTerminalForm').onsubmit=async e=>{
   e.preventDefault();if(dialog.dataset.saving)return;dialog.dataset.saving='true';const form=e.target;const submit=form.querySelector('button');submit.disabled=true;
   try{await api('computers/register',{id:state.computer.id,revision:editRevision,name:form.elements.name.value,role:form.elements.role.value,app:info.app,device:info.device,terminal:form.elements.terminal?.value||'',store_id:form.elements.store_id?.value,...(removed?{restore_terminal:removed.id,terminal_revision:removed.revision,confirm_restore:form.elements.confirm_restore.checked}:{})});clearForm(form);dialog.close();delete dialog.dataset.saving;await refresh(true);if(info.app==='pos'&&typeof retailLoadTerminal==='function'){await posLoad();}}
   catch(error){reportError(error.message+(error.status===409?' Use Refresh registration to review the latest details.':''));}finally{delete dialog.dataset.saving;submit.disabled=false;}
  };
  dialog.showModal();
 }
 window.openTerminalRegistration=async()=>{if(dirty()){(typeof posMessage==='function'?posMessage:toast)('Save or finish your current work before opening terminal setup.');return;}if(await refresh(true))await show();};
 window.retryTerminalConnection=async()=>{delete dialog?.dataset.serverEditor;if(!user){await boot();return;}await refresh(true);};
 async function refresh(force=false){
  const native=window.pywebview?.api;connectionEntry();if(!native?.terminal_info||busy||window.posUpdateInstalling||dialog?.dataset.serverEditor||dialog?.dataset.saving||(!force&&window.ConnectionStatus.visible))return;
  if(!user){if(get('login')&&!get('desktopSetupHint')){const hint=document.createElement('p');hint.id='desktopSetupHint';hint.textContent='First-time computer setup: sign in with an administrator account to register this terminal.';get('login').append(hint);}return;}
  busy=true;
  try{
   const check=async signal=>{const nextInfo=await native.terminal_info();if(nextInfo.error)throw Error(nextInfo.error);if(signal.aborted)throw Error('Connection check was canceled.');const nextState=await api('computers/self',{...nextInfo,status:lastStatus},{signal});return {nextInfo,nextState};};
   const result=(!state||force)?await window.ConnectionStatus.run(check):await check(AbortSignal.timeout(window.ConnectionStatus.timeout*1000));
   info=result.nextInfo;window.nativeTerminalAvailable=true;
   if(!button){button=document.createElement('button');button.id='nativeTerminalStatus';button.type='button';button.textContent='Terminal setup';button.onclick=window.openTerminalRegistration;(document.querySelector('.headerRight')||document.querySelector('.connectionInfo')||document.querySelector('body>header')).append(button);}
   const wasRequired=required();state=result.nextState;window.terminalRegistration=state;label();
   if(wasRequired&&!required()&&dialog?.open&&!changedForms.has(get('nativeTerminalForm'))&&!changedForms.has(get('nativeTerminalLogin')))dialog.close();
   if(required()||setupRequested){setupRequested=false;if(!dialog?.open)await show();}return true;

  }catch(error){if(button)button.textContent='Terminal setup · Unable to verify';if(dialog?.open)reportError(error.message);else if(force&&!dirty())recovery(error.message);}
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
