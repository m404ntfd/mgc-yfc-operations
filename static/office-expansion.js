// Shared directory editing and report navigation.
if(!officeMode){
 const pin=document.createElement('form');pin.id='deskPinForm';pin.innerHTML='<h2>Staff PIN sign-in</h2><p>Enter your six-digit staff PIN. It is managed in OFFICE and shared with Time Clock.</p><label>PIN<input name="pin" type="password" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="off" required></label><div class="deskKeypad"></div><button class="primary">Sign in</button><button type="button" id="deskPasswordToggle">Username & password</button><p id="deskPinError" role="alert"></p>';$('login').before(pin);$('login').hidden=true;
 for(const n of ['1','2','3','4','5','6','7','8','9','Clear','0','⌫']){const b=document.createElement('button');b.type='button';b.textContent=n;b.onclick=()=>{const input=pin.elements.pin;input.value=n==='Clear'?'':n==='⌫'?input.value.slice(0,-1):(input.value+n).slice(0,6);};pin.querySelector('.deskKeypad').append(b);}
 $('deskPasswordToggle').onclick=()=>{$('login').hidden=!$('login').hidden;if($('login').hidden)restorePinFocus();else $('login').elements.name.focus();};
 pin.onsubmit=async e=>{e.preventDefault();try{await api('pos-pin-login',{pin:pin.elements.pin.value});pin.reset();$('deskPinError').textContent='';await boot();}catch(e){pin.reset();pin.elements.pin.focus();$('deskPinError').textContent=e.message;}};
 const previousBoot=boot;boot=async function(){await previousBoot();if(!user){$('login').hidden=true;pin.reset();restorePinFocus();}};
 window.deskPinReady=()=>!user&&!$('auth').hidden&&$('login').hidden&&pin.getClientRects().length>0&&!document.querySelector('dialog[open]');
 window.focusDeskPin=()=>{if(window.deskPinReady())pin.elements.pin.focus({preventScroll:true});};
 let nativePinFocusPending=false;
 function restorePinFocus(){window.focusDeskPin();requestAnimationFrame(()=>{if(!window.deskPinReady())return;window.focusDeskPin();const focus=window.pywebview?.api?.focus_pin;if(focus&&!nativePinFocusPending){nativePinFocusPending=true;Promise.resolve(focus()).catch(()=>{}).finally(()=>nativePinFocusPending=false);}});}
 for(const event of ['focus','pageshow','pywebviewready'])window.addEventListener(event,restorePinFocus);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)restorePinFocus();});
 new MutationObserver(restorePinFocus).observe($('auth'),{attributes:true,attributeFilter:['hidden']});restorePinFocus();
 // If startup or a keypad tap left focus on the page/button, accept the first
 // physical key immediately. Never intercept password fields or an open dialog.
 document.addEventListener('keydown',e=>{if(!window.deskPinReady()||e.ctrlKey||e.altKey||e.metaKey||e.isComposing||e.target===pin.elements.pin||e.target.closest?.('input,textarea,select,[contenteditable=true]'))return;
  if(!/^[0-9]$/.test(e.key)&&!['Backspace','Enter'].includes(e.key))return;
  e.preventDefault();window.focusDeskPin();if(e.key==='Enter'){if(!e.repeat)pin.requestSubmit();return;}
  const input=pin.elements.pin;input.value=e.key==='Backspace'?input.value.slice(0,-1):(input.value+e.key).slice(0,6);input.dispatchEvent(new Event('input',{bubbles:true}));
 });
}
officeCards.push({section:'accounts',title:'Employee cash advances',description:'Cash paid to employees by store, date and issuing staff member.',icon:'▤',action:'cash-advance-report',permission:'view_cash_advances'},{section:'sales',title:'Sales analysis',description:'Sales, cash, products, taxes and transaction reports.',icon:'▥',action:'report-center',permission:'view_pos_sales'},
 {section:'security',title:'Login security / unlock',description:'Review locked users and configure login attempt limits.',icon:'♙',action:'login-security',permission:'unlock_users'},
 {section:'timekeeping',title:'Labor & time reports',description:'Worked hours, breaks and time entries.',icon:'◷',action:'labor-reports',permission:'edit_time_cards'},
 {section:'timekeeping',title:'Print employee schedule',description:'Print staff shifts for a selected date range.',icon:'▦',action:'schedule-report',permission:'manage_staff_schedule'});
const originalOfficeAction=officeAction;
officeAction=async function(action){
 if(!['cash-advance-report','report-center','labor-reports','schedule-report','login-security'].includes(action))return originalOfficeAction(action);
 if(!navigationAllowed()||unfinished())return;
 $('officeTiles').hidden=true;$('officeWork').hidden=false;for(const id of ['officeForms','officeCatalog','officeUsers','retailEditor','flowOffice'])if($(id))$(id).hidden=true;
 let root=$('officeExpansion');if(!root){root=document.createElement('section');root.id='officeExpansion';$('officeWork').append(root);}root.hidden=false;$('officeWorkTitle').textContent='';
 if(action!=='login-security'){retailReportCenter(root,action==='cash-advance-report'?'cash-advances':action==='labor-reports'?'labor':action==='schedule-report'?'schedule':'sales');return;}
 try{const data=await api('admin/lockouts');root.innerHTML=`<h2>Login security / unlock</h2>${user.admin?'<form id="officeLoginLimit"><label>Failed attempts before account lock<input name="max_attempts" type="number" min="1" max="100" required></label><button>Save limit</button></form>':''}<div id="officeLockedUsers">${data.users.map(p=>`<p>${esc(p.name)} · ${p.failures} failed attempts <button data-office-unlock="${esc(p.name)}">Unlock</button></p>`).join('')||'<p>No locked accounts.</p>'}</div><p id="officeSecurityStatus" role="status"></p>`;
 if(user.admin){const settings=await api('admin/login-security');$('officeLoginLimit').elements.max_attempts.value=settings.max_attempts;$('officeLoginLimit').onsubmit=async e=>{e.preventDefault();try{await api('admin/login-security',{max_attempts:Number(e.target.elements.max_attempts.value)});changedForms.delete(e.target);$('officeSecurityStatus').textContent='Login limit saved.';}catch(e){$('officeSecurityStatus').textContent=e.message;}};}
 root.onclick=async e=>{const b=e.target.closest('[data-office-unlock]');if(b){try{await api('admin/unlock-user',{name:b.dataset.officeUnlock});officeAction('login-security');}catch(e){$('officeSecurityStatus').textContent=e.message;}}};
 }catch(e){root.textContent=e.message;}
};
const previousOfficeHome=officeHome;officeHome=function(...args){if($('officeExpansion'))$('officeExpansion').hidden=true;return previousOfficeHome(...args);};
const priorOfficeUsers=officeLoadUsers;officeLoadUsers=async function(){await priorOfficeUsers();for(const row of $('officeUserRows').rows){const name=row.cells[0].textContent;const b=document.createElement('button');b.textContent='Edit user';b.onclick=()=>officeEditUser(name);row.insertCell().append(b);}};
async function officeEditUser(name){
 const d=flowModal('Edit user · '+name,`<nav class="flowTabs">${['Properties','Role','Personal','User view'].map((s,i)=>`<button data-user-pane="${i}">${s}</button>`).join('')}</nav><section data-pane="0"><h3>Properties</h3><div class="officeProfileFields"><label>System name<input value="${esc(name)}" readonly></label><p>Shared account in Operations, DESK and OFFICE.</p></div><form id="officePasswordReset"><h3>Reset password</h3><label>New password<input name="password" type="password" minlength="4" maxlength="256" required></label><label>Confirm password<input name="confirm" type="password" required></label><button>Change password</button></form><form id="officeStaffPin"><h3>Staff PIN</h3><p>Used for DESK and Time Clock. PIN access requires the secure staff address.</p><label>New six-digit PIN<input name="pin" type="password" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required></label><button>Set PIN</button><button type="button" id="officePinClear">Clear PIN</button></form></section><section data-pane="1" hidden><h3>Shared role</h3><form id="officeEditRole"><label>Role<select name="role_id">${(officeRoleData?.roles||[]).map(r=>`<option value="${r.id}">${esc(r.name)}</option>`).join('')}</select></label><button>Save role</button></form><p>Role permissions apply across all applications.</p></section><section data-pane="2" hidden><form id="officePersonal"><h3>Personal</h3>${[['username','Login user name'],['first','First name'],['middle','Middle name'],['last','Last name']].map(([k,label])=>`<label>${label}<input name="${k}" maxlength="80" ${k==='username'?'required':''}></label>`).join('')}<button>Save personal details</button></form></section><section data-pane="3" hidden><h3>User view</h3><p id="officeAccessSummary">${esc(officeRoleData?.roles.find(r=>r.id===officeRoleData?.assignments?.[name])?.name||'Individual access or administrator')}</p><p>Access is controlled by the shared role and existing Operations permissions.</p></section><p id="officeUserSaveStatus" role="status"></p>`);
 d.classList.add('officeUserWizard');d.onclick=e=>{const b=e.target.closest('[data-user-pane]');if(b){d.querySelectorAll('[data-pane]').forEach(p=>p.hidden=p.dataset.pane!==b.dataset.userPane);d.querySelectorAll('[data-user-pane]').forEach(p=>p.setAttribute('aria-pressed',p===b));}};
 const save=async(path,body,form)=>{try{await api(path,{name,...body});changedForms.delete(form);$('officeUserSaveStatus').textContent='Saved to the shared user directory.';return true;}catch(e){$('officeUserSaveStatus').textContent=e.message;return false;}};
 $('officePasswordReset').hidden=!can('reset_passwords');$('officeStaffPin').hidden=!can('reset_passwords');$('officeEditRole').hidden=!can('manage_users');$('officePersonal').hidden=!can('rename_users');
 $('officePasswordReset').onsubmit=async e=>{e.preventDefault();if(await save('admin/password',Object.fromEntries(new FormData(e.target)),e.target))e.target.reset();};
 $('officeStaffPin').onsubmit=async e=>{e.preventDefault();if(await save('admin/clock-pin',{pin:e.target.elements.pin.value},e.target))e.target.reset();};
 $('officePinClear').onclick=()=>save('admin/clock-pin',{pin:''},$('officeStaffPin'));
 $('officeEditRole').elements.role_id.value=String(officeRoleData?.assignments?.[name]||'');$('officeEditRole').onsubmit=e=>{e.preventDefault();save('admin/user-role',{role_id:Number(e.target.elements.role_id.value)},e.target);};
 $('officePersonal').onsubmit=e=>{e.preventDefault();save('admin/user-identity',Object.fromEntries(new FormData(e.target)),e.target);};
 if(can('rename_users')){
  const extra=document.createElement('form');extra.id='officeContactDetails';extra.innerHTML='<h3>Contact details</h3>'+[['employee_code','Employee code'],['gender','Gender'],['address1','Address line 1'],['address2','Address line 2'],['city','City'],['region','State / province'],['postal','Postal code'],['country','Country'],['phone','Primary phone'],['alternate_phone','Alternate phone'],['email','Email'],['birthday','Birthday']].map(([key,label])=>`<label>${label}<input name="${key}" type="${key==='birthday'?'date':key==='email'?'email':'text'}" maxlength="300"></label>`).join('')+'<button>Save contact details</button>';d.querySelector('[data-pane="2"]').append(extra);let revision=0;
  try{const details=await api('admin/office-user-details?name='+encodeURIComponent(name));revision=details.revision;for(const el of extra.elements)if(el.name)el.value=details[el.name]||'';}catch(e){$('officeUserSaveStatus').textContent=e.message;}
  extra.onsubmit=async e=>{e.preventDefault();try{const r=await api('admin/office-user-details',{name,revision,...Object.fromEntries(new FormData(extra))});revision=r.revision;changedForms.delete(extra);$('officeUserSaveStatus').textContent='Contact details saved.';}catch(e){$('officeUserSaveStatus').textContent=e.message;}};
 }
 if(can('rename_users'))try{const profile=await api('admin/user-identity?name='+encodeURIComponent(name));for(const key of ['username','first','middle','last'])$('officePersonal').elements[key].value=profile[key];}catch(e){$('officeUserSaveStatus').textContent=e.message;}
}

officeCards.push({section:'communications',title:'Review staff communications',description:'Review retained conversations, files and saved messages.',icon:'✉',action:'review-communications',permission:'review_staff_communications'});
const beforeCommunicationReview=officeAction;
officeAction=async function(action){
 if(action!=='review-communications')return beforeCommunicationReview(action);
 if(!navigationAllowed()||unfinished())return;
 const dialog=document.createElement('dialog');dialog.innerHTML='<h2>Staff communications</h2><p>Restricted staff review. Messages hidden by participants remain retained.</p><button type="button" data-close>Close</button><div data-content></div>';document.body.append(dialog);dialog.querySelector('[data-close]').onclick=()=>{dialog.close();dialog.remove();};dialog.showModal();const content=dialog.querySelector('[data-content]');
 try{const data=await api('comms/review');content.innerHTML=data.threads.map(t=>`<p><button data-thread="${t.id}">${esc(t.title||'Private conversation')} #${t.id} · ${t.messages} messages</button></p>`).join('')||'<p>No conversations.</p>';
 content.onclick=async e=>{const b=e.target.closest('[data-thread]');if(!b)return;try{const r=await api('comms/review-messages?thread='+b.dataset.thread+(b.dataset.before?'&before='+b.dataset.before:''));content.innerHTML=r.messages.map(m=>`<article><strong>${esc(m.author_name)}</strong><p>${esc(m.text)}</p>${m.filename?`<a href="/api/comms/review-file/${m.id}" download="${esc(m.filename)}">${esc(m.filename)}</a>`:''}<p>Saved by: ${esc(m.saved_by.join(', ')||'None')} · Hidden by: ${esc(m.hidden_by.join(', ')||'None')}</p></article>`).join('')||'<p>No messages.</p>';if(r.older)content.insertAdjacentHTML('beforeend',`<button data-thread="${b.dataset.thread}" data-before="${r.messages[r.messages.length-1].id}">Older messages</button>`);}catch(err){content.textContent=err.message;}};
 }catch(err){content.textContent=err.message;}
};

officeCards.push({section:'timekeeping',title:'Timekeeping management',description:'Time cards, audit history, scheduling, requests, payroll and work sites.',icon:'◷',action:'timekeeping-manage',permission:'edit_time_cards'});
let officeTimeFrame=null;
const unfinishedBeforeTimekeeping=unfinished;
unfinished=function(){return unfinishedBeforeTimekeeping()||!!(officeTimeFrame?.contentWindow?.hasUnfinishedWork?.());};
const actionBeforeTimekeeping=officeAction;
officeAction=async function(action){
 if(action!=='timekeeping-manage'){if(officeTimeFrame&&!unfinished())officeTimeFrame.hidden=true;return actionBeforeTimekeeping(action);}
 if(!navigationAllowed()||unfinished())return;
 $('officeTiles').hidden=true;$('officeWork').hidden=false;
 for(const id of ['officeForms','officeCatalog','officeUsers','retailEditor','flowOffice','officeExpansion'])if($(id))$(id).hidden=true;
 $('officeWorkTitle').textContent='Timekeeping management';
 if(!officeTimeFrame){officeTimeFrame=document.createElement('iframe');officeTimeFrame.title='Timekeeping management';officeTimeFrame.src='/office-timekeeping#office-timekeeping';officeTimeFrame.style='width:100%;height:75vh;border:0';$('officeWork').append(officeTimeFrame);}
 officeTimeFrame.hidden=false;
};

// Computer registration and installed versions, backed by the shared server.
officeCards.push({section:'system',title:'Registered computers',description:'Approve discovered PCs and keep their names, roles and application inventory.',icon:'▣',action:'computer-register',permission:'admin'});
// BEGIN COMPUTER INVENTORY
const officeBeforeComputers=officeAction;
officeAction=async function(action){
 if(!['computer-register','computer-updates'].includes(action))return officeBeforeComputers(action);
 if(!navigationAllowed()||unfinished())return;
 const registration=action==='computer-register',dialog=flowModal(registration?'Registered computers':'Installed application versions','<p>Registration stays with the computer when its address changes. Applications check for updates on startup and hourly; restart an application to install an available update.</p><button id="computerRefresh" type="button">Refresh computers</button><p id="computerStatus" role="status"></p><div id="computerRows"></div>');
 dialog.classList.add('computerDialog');let busy=false;
 function render(data){
  dialog.querySelector('#computerStatus').textContent=`${data.computers.filter(p=>p.registered).length} registered computers · Server ${data.server_version}`;
  dialog.querySelector('#computerRows').innerHTML=data.computers.map(pc=>`<article class="computerCard"><h3>${esc(pc.name||pc.hostname)}</h3><p>${esc(pc.hostname)} · ${esc(pc.role)} · ${pc.registered?'Registered':'Awaiting registration'}</p>${pc.network?`<p>Server connection adapter: ${esc(pc.network.adapter)} · MAC ${esc(pc.network.mac)} · ${esc(pc.network.address)}</p>`:''}${registration?`<form data-register-computer="${pc.id}" data-revision="${pc.revision}"><label>Name<input name="name" maxlength="80" required value="${esc(pc.name||pc.hostname)}"></label><label>Role<select name="role">${[['pos','POS checkout'],['office','Office computer'],['server','Server computer'],['other','Other']].map(([v,t])=>`<option value="${v}" ${pc.role===v?'selected':''}>${t}</option>`).join('')}</select></label><button>Save registration</button></form>`:''}<div class="computerApps">${pc.apps.map(a=>`<div><strong>${a.app==='pos'?'DESK':a.app==='ops'?'STORE OPS desktop':'OFFICE'} · ${esc(a.version)}</strong><span>${a.online?'Connected':'Offline / closed'}</span><small>Last seen ${esc(new Date(a.seen*1000).toLocaleString())} · ${esc(a.ip)}</small></div>`).join('')}</div></article>`).join('')||'<p>No computers registered yet.</p>';
 }
 async function refresh(){if(busy||!dialog.open||[...changedForms.keys()].some(f=>dialog.contains(f)))return;busy=true;try{render(await api('computers/state'));}catch(e){dialog.querySelector('#computerStatus').textContent=e.message;}finally{busy=false;}}
 dialog.querySelector('#computerRefresh').onclick=refresh;
 dialog.querySelector('#computerRows').onsubmit=async e=>{e.preventDefault();if(busy)return;const f=e.target;busy=true;try{const data=await api('computers/register',{id:f.dataset.registerComputer,revision:Number(f.dataset.revision),name:f.elements.name.value,role:f.elements.role.value});changedForms.delete(f);render(data);}catch(error){dialog.querySelector('#computerStatus').textContent=error.message;}finally{busy=false;}};
 const timer=setInterval(refresh,15000);dialog.addEventListener('close',()=>clearInterval(timer),{once:true});await refresh();
};

// END COMPUTER INVENTORY
