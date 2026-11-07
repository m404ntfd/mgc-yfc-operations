// Restore this device’s appearance before initializing the application.
(()=>{
 'use strict';
 const key='yfc-appearance', media=matchMedia('(prefers-color-scheme: dark)');
 let preference='system';
 try{const saved=localStorage.getItem(key);if(['light','dark','system'].includes(saved))preference=saved;}catch{}
 function apply(){const mode=preference==='system'?(media.matches?'dark':'light'):preference;document.documentElement.dataset.theme=mode;document.documentElement.style.colorScheme=mode;}
 window.appAppearance={get preference(){return preference;},set(value){preference=['light','dark','system'].includes(value)?value:'system';apply();try{localStorage.setItem(key,preference);return true;}catch{return false;}}};
 media.addEventListener('change',apply);
 window.addEventListener('storage',e=>{if(e.key===key||e.key===null){preference=['light','dark','system'].includes(e.newValue)?e.newValue:'system';apply();const select=document.getElementById('appearanceMode');if(select)select.value=preference;}});
 apply();
})();

'use strict';
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state={jobs:[],vehicles:[],users:[]},user,setup=false,mode='day',editing=null,timer;
const connectionId=Array.from(crypto.getRandomValues(new Uint8Array(16)),value=>value.toString(16).padStart(2,'0')).join('');
$('login').elements.name.labels[0].firstChild.textContent='Username';
const loginAttempts=document.createElement('p');loginAttempts.id='loginAttempts';loginAttempts.setAttribute('role','status');$('authError').after(loginAttempts);
const operationsTitle=document.createElement('div');operationsTitle.className='operationsTitle';operationsTitle.textContent='MGC YFC Operations';$('storeMenuButton').before(operationsTitle);const pageLabel=$('currentSection');$('storeMenuButton').replaceChildren(pageLabel,document.createTextNode(' ▾'));
const menuDivider=document.createElement('hr');menuDivider.className='menuDivider';$('chooseStartSection').before(menuDivider);
const journalLabel=$('journalEnabled').parentElement;for(const node of [...journalLabel.childNodes])if(node.nodeType===Node.TEXT_NODE)node.textContent=' Automatically archive old pickups and deliveries';
const journalDaysLabel=document.createElement('label');journalDaysLabel.innerHTML='Keep dispatch entries on the server for (days)<input id="journalDays" type="number" min="1" max="3650" value="30" required>';journalLabel.after(journalDaysLabel);
$('backupConfig').querySelector('p').textContent='All pickups and deliveries older than this period are archived regardless of status. Future and undated entries remain active. Records, photos and history are verified in Dispatch Journal before removal from the active database.';

$('offline').id='legacyOffline';$('legacyOffline').hidden=true;$('retry').id='legacyRetry';
const offlineOverlay=document.createElement('dialog');offlineOverlay.id='offline';offlineOverlay.hidden=true;offlineOverlay.setAttribute('aria-labelledby','offlineTitle');offlineOverlay.innerHTML='<div class="offlineMessage"><img id="offlineGraphic" src="/offline.gif" alt="Disconnected plug"><h1 id="offlineTitle">NO INTERNET CONNECTION OR SERVER IS OFFLINE</h1><p>PLEASE TRY AGAIN LATER</p><button id="retry" type="button">Try again</button></div>';document.body.append(offlineOverlay);offlineOverlay.addEventListener('cancel',e=>e.preventDefault());
let serverOnline=true,serverUpdateAvailable=false;
const connectionDot=document.createElement('span');connectionDot.id='connectionDot';connectionDot.className='statusDot';connectionDot.setAttribute('aria-hidden','true');const connectionLine=document.createElement('div');connectionLine.id='connectionLine';$('connection').before(connectionLine);connectionLine.append(connectionDot,$('connection'));
const loggedOutStatus=document.createElement('div');loggedOutStatus.id='loggedOutStatus';loggedOutStatus.innerHTML='<span class="statusDot signedOutDot" aria-hidden="true"></span>No User Currently Logged In';connectionLine.after(loggedOutStatus);
function setServerConnection(online){serverOnline=online;if(online){if(offlineOverlay.open)offlineOverlay.close();offlineOverlay.hidden=true;}else if(!$('addUserStatus')?.open){offlineOverlay.hidden=false;if(!offlineOverlay.open)offlineOverlay.showModal();}connectionDot.dataset.connectionState=online?(serverUpdateAvailable?'update':'online'):'offline';connectionDot.title=online?(serverUpdateAvailable?'Server online — update available':'Server online'):'Server offline';if(!online)$('connection').textContent='Server offline';}
async function pollServerConnection(){try{const r=await api('connection-status');serverUpdateAvailable=!!r.update_available;setServerConnection(true);$('connection').textContent=serverUpdateAvailable?'Store server online · Update available':'Store server online';}catch{setServerConnection(false);}}
setServerConnection(true);setInterval(pollServerConnection,15000);pollServerConnection();
const localDate=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
$('date').value=localDate(new Date());
$('mobileLink').href=location.origin+'/mobile';$('mobileLink').textContent=location.origin+'/mobile';
async function api(path,data){let r;try{r=await fetch('/api/'+path,{method:data?'POST':'GET',headers:{'X-Dispatch-Connection':connectionId,...(data?{'Content-Type':'application/json','X-Dispatch':'1'}:{})},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(20000)});if(r.status>=500)throw Error('Server unavailable');setServerConnection(true);}catch(e){setServerConnection(false);throw e;}const v=await r.json();if(!r.ok){if(r.status===401&&user){user=null;updateSignedInUser();clearInterval(timer);$('app').hidden=true;$('paging').hidden=true;$('receipts').hidden=true;$('receiptHistory')?.setAttribute('hidden','');$('printPurpose')?.setAttribute('hidden','');setSectionHeader('Sign in','signin');$('auth').hidden=false;$('editor').close();$('passwordDialog').close();$('statusDialog').close();}throw Object.assign(Error(v.error||'Request failed'),{status:r.status,attemptsRemaining:v.attempts_remaining});}return v;}
let toastTimer;
function toast(message,action){
 const notice=$('toast');
 clearTimeout(toastTimer);
 notice.textContent=message;
 if(action){
  const button=document.createElement('button');
  button.type='button';
  button.textContent=message;
  button.onclick=action;
  notice.replaceChildren(button);
 }else toastTimer=setTimeout(()=>notice.hidden=true,5000);
 notice.hidden=false;
}
function requireSignIn(){
 if(user)return true;
 closeStoreMenu();
 toast('Log in first',showSignIn);
 return false;
}
function showSignIn(){
 $('toast').hidden=true;
 if(user)return;
 workCloseQuick();
 for(const id of ['app','paging','receipts','receiptUpload','receiptHistory','printPurpose'])$(id).hidden=true;
 document.body.classList.remove('settingsView');
 setSectionHeader('Sign in','signin');
 $('auth').hidden=false;
 $('login').elements.name.focus();
}
async function boot(){try{const s=await api('session');if(location.hash==='#login'){if(s.user){await api('logout',{pushDevice:commPushId()});s.user=null;}history.replaceState(null,'',location.pathname+location.search);}setup=s.setup;user=s.user;if(user){if($('toast').querySelector('button'))$('toast').hidden=true;const pref=await api('account/appearance');window.appAppearance.set(pref.mode);$('appearanceMode').value=pref.mode;}lockRepository();if(!user){if(typeof stopPaging==='function')stopPaging();$('paging').hidden=true;$('receipts').hidden=true;$('receiptHistory')?.setAttribute('hidden','');$('printPurpose')?.setAttribute('hidden','');setSectionHeader('Sign in','signin');$('sectionChooser').close();expandedAppointments.clear();$('requestsList').hidden=true;}updateSignedInUser();$('authTitle').textContent=setup?'Set up your store':'Welcome back';$('authHelp').textContent=setup?(s.local?'Create the administrator account. Then add your vehicles and employees.':'Open http://localhost:8080 on the server computer to create the first account.'):'Sign in to your operations workspace.';$('auth').hidden=!!user;$('app').hidden=!user;$('connection').textContent=user?'Connected to store':'Store server online';if(user){$('settingsTab').hidden=false;$('serverUpdateButton').hidden=!user.admin;if(!user.admin)tab('day');if(can('view_schedule'))await refresh();else applyPermissions();clearInterval(timer);timer=setInterval(()=>{if(can('view_schedule'))refresh().catch(()=>{});},10000);if(location.hash==='#settings'){tab('settings');if(can('check_updates'))settingsSection(2);history.replaceState(null,'',location.pathname+location.search);}else if(location.hash==='#comms'){history.replaceState(null,'',location.pathname+location.search);await commOpen();}else await chooseLanding();}}catch(e){$('connection').textContent='Server unavailable';$('offline').hidden=false;toast(e.message);}}
async function refresh(){try{state=await api('state');user.can_create=state.permissions.can_create;user.see_requests=state.permissions.see_requests;user.grants=state.permissions.grants;renderRequests();$('connection').textContent='Connected · '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});$('offline').hidden=true;const value=$('filter').value;$('filter').innerHTML='<option value="">All vehicles</option>'+state.vehicles.map(v=>`<option>${esc(v)}</option>`).join('');$('filter').value=value;render();applyPermissions();checkUpdateNotice();$('vehicles').innerHTML=state.vehicles.map(v=>`<div class="listRow">${esc(v)}</div>`).join('')||'<p>No vehicles yet.</p>';renderUserList();}catch(e){if(e.message.includes('Schedule access required')){$('connection').textContent='Connected · schedule permission required';$('offline').hidden=true;toast('Ask an administrator to enable View schedule, search and filter in your employee permissions.');}else{$('connection').textContent='Disconnected';$('offline').hidden=false;}throw e;}}
function filtered(){const q=can('show_search')?$('search').value.toLowerCase():'';return state.jobs.filter(j=>(!$('statusFilter').value||j.status===$('statusFilter').value)&&(!can('show_vehicle_filter')||!$('filter').value||j.vehicle===$('filter').value)&&(!q||Object.values(j).join(' ').toLowerCase().includes(q)));}
function timeLabel(s){return new Date(s).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});}
function shiftDate(date,days){const d=new Date(date+'T12:00');d.setDate(d.getDate()+days);return localDate(d);}
function weekStart(date){return shiftDate(date,-new Date(date+'T12:00').getDay());}
function dateLabel(date){return new Date(date+'T12:00').toLocaleDateString([],{weekday:'long',month:'short',day:'numeric',year:'numeric'});}
function renderTotals(){
 const today=localDate(new Date()),tomorrow=shiftDate(today,1),start=weekStart(today);
 $('totals').innerHTML=[['Today',today,today],['Tomorrow',tomorrow,tomorrow],['This week',start,shiftDate(start,6)]].map(([label,from,to])=>{
 const jobs=state.jobs.filter(j=>j.status!=='Canceled'&&j.start.slice(0,10)>=from&&j.start.slice(0,10)<=to);
 const pending=(state.requests||[]).filter(j=>j.status!=='Canceled'&&j.start&&j.start.slice(0,10)>=from&&j.start.slice(0,10)<=to);
 const pendingCount=type=>state.pendingCounts?Object.entries(state.pendingCounts).filter(([date])=>date&&date>=from&&date<=to).reduce((total,[date,counts])=>total+(counts[type]||0),0):pending.filter(j=>j.type===type).length;
 return `<article class="totalCard"><h2>${label}</h2><p class="totalDates">${esc(dateLabel(from))}${from===to?'':' – '+esc(dateLabel(to))}</p><div class="totalNumbers"><span><strong>${jobs.filter(j=>j.type==='Pickup').length}</strong> Pickups</span><span><strong>${jobs.filter(j=>j.type==='Delivery').length}</strong> Deliveries</span></div></article>`;
 }).join('');
 const counts=state.pendingCounts?Object.values(state.pendingCounts).reduce((a,c)=>({Pickup:a.Pickup+(c.Pickup||0),Delivery:a.Delivery+(c.Delivery||0)}),{Pickup:0,Delivery:0}):{Pickup:(state.requests||[]).filter(j=>j.status!=='Canceled'&&j.type==='Pickup').length,Delivery:(state.requests||[]).filter(j=>j.status!=='Canceled'&&j.type==='Delivery').length};
 $('pendingOverview').innerHTML=`<h2>Pending Requests <span class="pendingBadge">${counts.Pickup+counts.Delivery}</span></h2><div class="pendingBreakdown"><span><strong>${counts.Pickup}</strong> Pickups</span><span><strong>${counts.Delivery}</strong> Deliveries</span></div><p>All dates, including requests without a date. Approved and cancelled requests excluded.</p>`;
}
// Use directions links rather than a location search. The OS/browser controls app handoff.
function navigationUrl(address,ua=navigator.userAgent,platform=navigator.platform,touch=navigator.maxTouchPoints){
 const destination=encodeURIComponent(address);
 const apple=/iPhone|iPad|iPod/i.test(ua)||(platform==='MacIntel'&&touch>1);
 return apple?`https://maps.apple.com/?daddr=${destination}&dirflg=d`:`https://www.google.com/maps/dir/?api=1&destination=${destination}&travelmode=driving&dir_action=navigate`;
}
function smsUrl(j,ua=navigator.userAgent,platform=navigator.platform,touch=navigator.maxTouchPoints){
 const number=String(j.phone||'').replace(/[^+0-9]/g,'');
 const message=`Hi ${j.customer}, this is Thrift Mart. Our team is on the way for your scheduled ${j.type.toLowerCase()}. Please let us know if anything has changed. Thank you!`;
 const apple=/iPhone|iPad|iPod/i.test(ua)||(platform==='MacIntel'&&touch>1);
 return `sms:${number}${apple?'&':'?'}body=${encodeURIComponent(message)}`;
}
const expandedAppointments=new Set();
function jobCard(j){return `<article data-appointment="${esc(j.id)}" class="job ${expandedAppointments.has(j.id)?'expanded':'collapsed'} status-${j.status==='In Route / In Progress'?'in-progress':esc(j.status.toLowerCase())}"><span class="statusBarText">${esc(j.status==='Canceled'?'Cancelled':j.status)}</span><div role="button" tabindex="0" data-toggle-appointment="${esc(j.id)}" aria-expanded="${expandedAppointments.has(j.id)}" aria-label="${expandedAppointments.has(j.id)?'Collapse':'Expand'} appointment for ${esc(j.customer)}" class="appointmentType ${j.type==='Delivery'?'typeDelivery':'typePickup'}"><span aria-hidden="true">${j.type==='Delivery'?'📦 ←':'→ 🏬'}</span> ${j.type==='Delivery'?'DELIVERY':'PICKUP'}</div><button class="expandAppointment" data-expand="${esc(j.id)}" aria-expanded="${expandedAppointments.has(j.id)}" aria-label="${expandedAppointments.has(j.id)?'Collapse':'Expand'} appointment for ${esc(j.customer)}">${expandedAppointments.has(j.id)?'▴ ▴ ▴':'▾ ▾ ▾'}</button><button class="editIcon" data-edit="${esc(j.id)}" aria-label="Edit appointment for ${esc(j.customer)}" title="Edit appointment">✎</button><div class="time">${esc(timeLabel(j.start))}<div class="muted">to ${esc(timeLabel(j.end))}${j.end.slice(0,10)!==j.start.slice(0,10)?' · '+esc(j.end.slice(0,10)):''}</div></div><div><span class="tag">${esc(j.request?'Request':j.status)}</span><h2>${esc(j.customer)}</h2><p>${esc(j.items)}</p><p>${esc(j.address)}</p><div class="contactActions"><a target="_blank" rel="noopener noreferrer" href="${esc(navigationUrl(j.address))}" aria-label="Navigate to ${esc(j.address)}">Navigate ↗</a>${j.phone?`<a href="tel:${esc(j.phone.replace(/[^+0-9*#,;]/g,''))}">Call ${esc(j.phone)}</a><a class="textCustomer" href="${esc(smsUrl(j))}" aria-label="Text ${esc(j.customer)} that staff are on the way">Text: On Our Way</a>`:''}</div><p class="meta">${esc(j.vehicle)}${j.staff?' · '+esc(j.staff):''}</p>${j.notes?`<p class="muted">${esc(j.notes)}</p>`:''}${photoLinks(j)}</div><button class="statusUpdate" data-status="${esc(j.id)}">Status Update</button><div class="statusHistory">${j.statusUpdatedBy&&j.statusUpdatedAt?`Last updated by ‘<strong><em>${esc(j.statusUpdatedBy)}</em></strong>’ at ‘<strong><em>${esc(new Date(j.statusUpdatedAt).toLocaleString([],{month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit'}))}</em></strong>’`:'Status update details unavailable for this older appointment.'}</div></article>`;}
function render(){
 setTimeout(()=>{if(user)applyPermissions();},0);
 renderTotals();
 const day=$('date').value,today=localDate(new Date()),weekly=mode==='week';
 const from=weekly?weekStart(day):day,to=weekly?shiftDate(from,6):day;
 const jobs=filtered().filter(j=>j.start.slice(0,10)<=to&&j.end.slice(0,10)>=from).sort((a,b)=>a.start.localeCompare(b.start));
 $('summary').textContent=`${dateLabel(from)}${weekly?' – '+dateLabel(to):''} · ${jobs.length} appointment${jobs.length===1?'':'s'}`;
 if(weekly){let html='';for(let i=0;i<7;i++){const date=shiftDate(from,i),daily=jobs.filter(j=>j.start.slice(0,10)<=date&&j.end.slice(0,10)>=date);html+=`<section class="weekDay"><h2>${esc(dateLabel(date))}</h2>${daily.map(jobCard).join('')||'<p class="dayEmpty">No appointments.</p>'}</section>`;}$('jobs').innerHTML=html;}
 else $('jobs').innerHTML=jobs.map(jobCard).join('')||'<div class="empty"><h2>No appointments to show.</h2><p>Choose another date or filter, or add a pickup or delivery.</p></div>';
 for(const [id,selected]of [['dayTab',mode==='day'&&day===today],['weekTab',weekly&&from===weekStart(today)],['nextWeekTab',weekly&&from===shiftDate(weekStart(today),7)],['settingsTab',mode==='settings']]){$(id).classList.toggle('selected',selected);$(id).setAttribute('aria-pressed',String(selected));}
 $('prev').setAttribute('aria-label',weekly?'Previous week':'Previous day');$('next').setAttribute('aria-label',weekly?'Next week':'Next day');
}
function tab(t){mode=t;document.body.classList.toggle('settingsView',t==='settings');if(t==='settings'){setSectionHeader('Settings','settings');$('app').hidden=false;$('paging').hidden=true;$('receipts').hidden=true;$('receiptUpload').hidden=true;if($('receiptHistory'))$('receiptHistory').hidden=true;printPage.hidden=true;}else if(user)setSectionHeader('Thrift Mart Dispatch','dispatch');if(t==='settings'){if(can('check_updates'))loadUpdates();if(can('backup_settings')||can('create_backups'))loadBackups();if(can('unlock_users'))loadLoginSecurity();if(user.admin)loadReceiptSettings();settingsCategory(null);}$('schedule').hidden=['settings','reports'].includes(t);$('settings').hidden=t!=='settings';$('reports').hidden=t!=='reports';if(t==='reports')loadReport();render();}
function quickView(offset){const today=localDate(new Date());$('date').value=offset===null?today:shiftDate(weekStart(today),offset);tab(offset===null?'day':'week');}
function openJob(id,type){if(user.can_create&&!state.vehicles.length){toast('Add a vehicle in Settings first.');if(user.admin)tab('settings');return;}editing=id?[...state.jobs,...(state.requests||[])].find(j=>j.id===id):null;$('jobForm').reset();$('jobForm').elements.status.innerHTML=(user.can_create?['Scheduled','In Route / In Progress','Completed','Canceled']:['Requested','Canceled']).map(v=>`<option value="${v}">${v==='Canceled'?'Cancelled':v}</option>`).join('');$('jobVehicle').innerHTML=state.vehicles.map(v=>`<option>${esc(v)}</option>`).join('');const j=editing||{state:'MS',type:type||'Pickup',status:user.can_create?'Scheduled':'Requested',start:$('date').value+'T09:00',end:$('date').value+'T10:00'};for(const [k,v]of Object.entries(j))if($('jobForm').elements[k])$('jobForm').elements[k].value=v;
$('jobForm').elements.street.value=Object.hasOwn(j,'street')?j.street:(j.address||'');$('legacyAddress').hidden=!editing||!!j.street;
const assigned=j.staffNames|| (j.staff?[j.staff]:[]);const names=[...new Set([...state.users.map(u=>u.name),...assigned])];$('employeeOptions').innerHTML=names.map(n=>`<label><input type="checkbox" name="staffNames" value="${esc(n)}" ${assigned.includes(n)?'checked':''}> ${esc(n)}${state.users.some(u=>u.name===n)?'':' (previous assignment)'}</label>`).join('');$('employeeDropdown').open=false;employeeSummary();$('editTitle').textContent=editing?(editing.request?'Review request':'Appointment details'):(user.can_create?'New appointment':'Submit appointment request');$('save').textContent=editing?.request?'Approve & schedule':user.can_create?'Save appointment':'Submit request';$('remove').hidden=!editing;$('formError').textContent='';const form=$('jobForm');$('startLabel').textContent=user.can_create?'Start *':'Requested Date & Time';form.elements.start.required=!!user.can_create;
for(const name of ['end','vehicle']){form.elements[name].closest('label').hidden=!user.can_create;form.elements[name].disabled=!user.can_create;form.elements[name].required=!!user.can_create;}
$('employeeDropdown').closest('.employeeField').hidden=!user.can_create;
if(!user.can_create){form.elements.start.value='';form.elements.end.value='';}
layoutRequestForm();renderReviewPhotos();$('editor').showModal();}
$('login').onsubmit=async e=>{e.preventDefault();try{const wasSetup=setup;loginAttempts.textContent='';$('authError').textContent='';await api(setup?'setup':'login',Object.fromEntries(new FormData(e.target)));e.target.reset();await boot();if(wasSetup){tab('settings');settingsSection(3);}}catch(err){$('authError').textContent=err.message;loginAttempts.textContent=Number.isInteger(err.attemptsRemaining)?'Attempts Remaining Until Account Lock: '+err.attemptsRemaining:'';}};
$('logout').onclick=async()=>{try{await api('logout',{pushDevice:commPushId()});clearInterval(timer);await boot();}catch(e){toast(e.message);}};
$('dayTab').onclick=()=>quickView(null);$('weekTab').onclick=()=>quickView(0);$('nextWeekTab').onclick=()=>quickView(7);$('settingsTab').onclick=()=>tab('settings');$('addPickup').onclick=()=>openJob(null,'Pickup');$('addDelivery').onclick=()=>openJob(null,'Delivery');$('close').onclick=()=>$('editor').close();$('date').onchange=()=>{if(!$('date').value)$('date').value=localDate(new Date());tab('day');};$('filter').onchange=render;$('statusFilter').onchange=render;$('search').oninput=render;
for(const [id,step]of [['prev',-1],['next',1]])$(id).onclick=()=>{$('date').value=shiftDate($('date').value,step*(mode==='week'?7:1));render();};
$('jobs').onclick=e=>{const edit=e.target.closest('[data-edit]');const expand=!edit&&(e.target.closest('[data-expand],[data-toggle-appointment]')||e.target.closest('.job.collapsed'));if(expand){const id=expand.dataset.expand||expand.dataset.toggleAppointment||expand.dataset.appointment;if(expandedAppointments.has(id))expandedAppointments.delete(id);else expandedAppointments.add(id);render();return;}const b=e.target.closest('[data-edit]');if(b&&can('edit_appointments'))openJob(b.dataset.edit);const status=e.target.closest('[data-status]');if(status)openStatus(status.dataset.status);};
$('jobForm').onsubmit=async e=>{e.preventDefault();$('save').disabled=true;bottomRequestSubmit.disabled=true;try{await api('save',{...Object.fromEntries(new FormData(e.target)),staffNames:new FormData(e.target).getAll('staffNames'),photos:requestPhotos,...(editing?{id:editing.id,revision:editing.revision}:{})});$('editor').close();toast('Appointment saved.');await refresh().catch(()=>toast('Saved. Reconnect to refresh the schedule.'));}catch(err){$('formError').textContent=err.message;}finally{$('save').disabled=false;bottomRequestSubmit.disabled=false;}};
$('remove').onclick=async()=>{if(!editing||!confirm('Remove this appointment from the schedule? Use Canceled status instead if you want to keep its details.'))return;try{await api('delete',{id:editing.id,revision:editing.revision});$('editor').close();toast('Appointment removed.');await refresh().catch(()=>toast('Removed. Reconnect to refresh the schedule.'));}catch(e){$('formError').textContent=e.message;}};
$('vehicleForm').onsubmit=async e=>{e.preventDefault();try{await api('vehicle',Object.fromEntries(new FormData(e.target)));e.target.reset();await refresh();toast('Vehicle added.');}catch(err){toast(err.message);}};
$('auditButton').onclick=async()=>{try{const a=await api('audit');$('audit').innerHTML=a.map(r=>`<div class="listRow">${esc(r.action)}<div class="muted">${esc(r.actor)} · ${esc(r.at.replace('T',' '))}</div></div>`).join('')||'<p>No changes yet.</p>';}catch(e){toast(e.message);}};

let repositoryUnlockTimer;
const repositorySave=$('updateConfig').querySelector('button');
function lockRepository(){clearTimeout(repositoryUnlockTimer);$('updateRepo').disabled=true;repositorySave.disabled=true;}
const unlockRepository=document.createElement('button');unlockRepository.type='button';unlockRepository.id='unlockRepository';unlockRepository.textContent='Unlock repository';$('updateConfig').after(unlockRepository);
const unlockDialog=document.createElement('dialog');unlockDialog.id='repositoryUnlockDialog';unlockDialog.innerHTML='<form id="repositoryUnlockForm"><h2>Administrator approval</h2><p>Enter administrator credentials to change the update repository.</p><label>Administrator username<input name="name" autocomplete="username" required></label><label>Administrator password<input name="password" type="password" autocomplete="current-password" required></label><p id="repositoryUnlockError" role="alert"></p><button type="submit">Unlock</button> <button type="button" id="cancelRepositoryUnlock">Cancel</button></form>';document.body.append(unlockDialog);
unlockRepository.onclick=()=>{ $('repositoryUnlockError').textContent='';unlockDialog.showModal();};$('cancelRepositoryUnlock').onclick=()=>unlockDialog.close();unlockDialog.onclose=()=>$('repositoryUnlockForm').reset();
$('repositoryUnlockForm').onsubmit=async e=>{e.preventDefault();try{await api('repository-unlock',Object.fromEntries(new FormData(e.target)));unlockDialog.close();$('updateRepo').disabled=false;repositorySave.disabled=false;repositoryUnlockTimer=setTimeout(lockRepository,300000);$('updateStatus').textContent='Unlocked for one change, for up to five minutes.';}catch(err){$('repositoryUnlockError').textContent=err.message;e.target.elements.password.value='';}};
lockRepository();

let updateVersion=null,updateBusy=false;
async function loadUpdates(){lockRepository();refreshUpdateConnections();try{const r=await api('updates');$('updateVersion').textContent='Installed version: '+r.current;$('updateRepo').value=r.repository;$('lastUpdate').textContent=r.last?(r.last.error||'Last installed: '+r.last.version+' · '+r.last.at):'';if(!r.launcher)$('updateStatus').textContent='Use Start-Store-Dispatch.bat on the server to enable update installation.';}catch(e){toast(e.message);}}
$('updateConfig').onsubmit=async e=>{e.preventDefault();if(updateBusy)return;try{await api('update-config',{repository:$('updateRepo').value});updateVersion=null;$('installUpdate').hidden=true;$('releaseNotes').textContent='';$('updateStatus').textContent='Repository saved. Ready to check.';}catch(err){$('updateStatus').textContent=err.message;}finally{lockRepository();}};
$('checkUpdate').onclick=async()=>{if(updateBusy)return;updateBusy=true;$('checkUpdate').disabled=true;$('installUpdate').hidden=true;$('updateStatus').textContent='Checking GitHub…';try{const r=await api('update-check',{});updateVersion=r.available?r.latest:null;serverUpdateAvailable=!!r.available;setServerConnection(true);$('updateStatus').textContent=r.available?'Version '+r.latest+' is available.':'You are up to date (version '+r.current+').';$('releaseNotes').textContent=r.notes;$('installUpdate').hidden=!r.available;}catch(e){$('updateStatus').textContent=e.message;}finally{updateBusy=false;$('checkUpdate').disabled=false;refreshUpdateConnections();}};
$('installUpdate').onclick=async()=>{
 if(updateBusy||!updateVersion)return;
 if(user?.admin&&!(await refreshUpdateConnections()))return;
 if(!confirm('Install version '+updateVersion+' and restart? Save your own work first and confirm guest/kiosk activity is finished. All users will be signed out. The server will recheck other signed-in connections before installing.'))return;
 updateBusy=true;updateInstallButton();$('updateStatus').textContent='Checking connections, then downloading and verifying the update…';
 try{await api('update-install',{version:updateVersion});clearInterval(timer);$('updateStatus').textContent='Restarting. This page will reload when the server is ready.';
  let tries=0;const poll=setInterval(async()=>{tries++;try{const r=await api('session');if(!r.user){clearInterval(poll);location.reload();}}catch{}if(tries>=45){clearInterval(poll);$('updateStatus').textContent='The server has not returned yet. Check its window on the Windows computer, then reload this page.';}},2000);
 }catch(e){$('updateStatus').textContent=e.message;await refreshUpdateConnections();}
 finally{updateBusy=false;updateInstallButton();}
};

async function loadBackups(){try{const r=await api('admin/backup-settings');$('backupFolder').value=r.config.folder;$('backupEnabled').checked=r.config.enabled;$('journalEnabled').checked=r.config.journal_enabled!==false;$('journalDays').value=r.config.journal_days||30;const s=r.status;$('backupStatus').textContent=s?(s.error?'Last backup error: '+s.error:s.verified?`Verified backup: ${s.at} · ${s.counts.Pickup} pickups · ${s.counts.Delivery} deliveries · ${s.counts.photos} photos. ${s.file}. Confirm OneDrive is synced.`:'Previous backup has not been read-back verified. Use Back up now.'):'No complete backup saved yet.';$('journalStatus').textContent=`Dispatch Journal: ${r.journal.records} archived entries in ${r.journal.archives} files. `+(r.journal.status?.error?'Archiving paused: '+r.journal.status.error:'Records are archived only after a complete backup and successful read-back checks.');}catch(e){$('backupStatus').textContent=e.message;}}
$('backupConfig').onsubmit=async e=>{e.preventDefault();try{await api('admin/backup-settings',{folder:$('backupFolder').value,enabled:$('backupEnabled').checked,journal_enabled:$('journalEnabled').checked,journal_days:Number($('journalDays').value)});$('backupStatus').textContent='Settings saved. Use Back up now to verify the destination.';}catch(err){$('backupStatus').textContent=err.message;}};
$('cloudBackup').onclick=async()=>{$('cloudBackup').disabled=true;$('backupStatus').textContent='Creating a complete backup…';try{const r=await api('admin/backup-now',{});await loadBackups();}catch(e){$('backupStatus').textContent=e.message;}finally{$('cloudBackup').disabled=false;}};

$('serverUpdateButton').onclick=()=>{tab('settings');settingsSection(2);$('updatePanel').scrollIntoView({behavior:'smooth',block:'start'});$('checkUpdate').click();};
$('users').onclick=e=>{const b=e.target.closest('[data-password]');if(!b)return;$('passwordForm').reset();$('passwordUser').value=b.dataset.password;$('passwordError').textContent='';const person=state.users.find(u=>u.name===b.dataset.password);$('canCreate').checked=!!person.can_create;$('seeRequests').checked=!!person.see_requests;$('canCreate').disabled=!!person.admin;$('permissionMessage').textContent='';openUserSetup(b.dataset.password);};
function closePassword(){$('passwordForm').reset();$('passwordDialog').close();}
$('passwordClose').onclick=closePassword;
$('passwordDialog').addEventListener('close',()=>$('passwordForm').reset());
$('passwordForm').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));if(d.password!==d.confirm){$('passwordError').textContent='The passwords do not match.';return;}$('passwordSave').disabled=true;try{const r=await api('admin/password',d);closePassword();if(r.signed_out){clearInterval(timer);await boot();toast('Password changed. Sign in with your new password.');}else toast('Password changed. The user must sign in again.');}catch(err){$('passwordError').textContent=err.message;}finally{$('passwordSave').disabled=false;}};

async function retryConnection(){if(user)await refresh().catch(()=>toast('Cannot reach the server. Check the store Wi-Fi or VPN.'));else await boot();}
$('refresh').onclick=retryConnection;$('retry').onclick=retryConnection;
window.addEventListener('online',retryConnection);
window.addEventListener('offline',()=>{setServerConnection(false);$('offline').hidden=false;$('connection').textContent='Disconnected';});
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&user)retryConnection();});

function employeeSummary(){const selected=[...$('employeeOptions').querySelectorAll('input:checked')].map(e=>e.value);$('employeeSummary').textContent=selected.length?selected.join(', '):'Select employees (optional)';}
$('employeeOptions').onchange=employeeSummary;

let statusEditing=null;
function openStatus(id){
 statusEditing=[...state.jobs,...(state.requests||[])].find(j=>j.id===id);if(!statusEditing)return;
 $('statusCustomer').textContent=statusEditing.customer+' · Current status: '+statusEditing.status;
 document.querySelector('.statusOptions').innerHTML='<legend>Appointment status</legend>'+(user.can_create?['Scheduled','In Route / In Progress','Completed','Canceled']:['Requested','Canceled']).map(value=>`<label><input type="radio" name="appointmentStatus" value="${value}" required ${value==='Requested'&&(!statusEditing.request||statusEditing.requestedBy!==user.name)?'disabled':''}><span>${value==='Canceled'?'Cancelled':value}</span></label>`).join('');
 for(const option of document.querySelectorAll('[name=appointmentStatus]'))option.checked=option.value===statusEditing.status;
 $('statusError').textContent='';$('statusDialog').showModal();
}
$('statusClose').onclick=()=>$('statusDialog').close();
$('statusForm').onsubmit=async e=>{
 e.preventDefault();if(!statusEditing)return;$('statusSave').disabled=true;
 try{await api('status',{id:statusEditing.id,revision:statusEditing.revision,status:new FormData(e.target).get('appointmentStatus')});$('statusDialog').close();toast('Status updated.');await refresh().catch(()=>toast('Status saved. Reconnect to refresh the schedule.'));}
 catch(err){$('statusError').textContent=err.message;}
 finally{$('statusSave').disabled=false;}
};

$('accountButton').textContent='Return to Home';
$('accountButton').onclick=async()=>{try{const pref=await api('account/landing');if(pref.home_section)storeSection(pref.home_section);else await chooseLanding();}catch(e){toast(e.message);}};
$('accountClose').onclick=()=>$('accountDialog').close();
$('accountForm').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button.primary');button.disabled=true;try{await api('account/password',Object.fromEntries(new FormData(e.target)));$('accountDialog').close();e.target.reset();await boot();toast('Login updated. Sign in with your new password or passcode.');}catch(err){$('accountError').textContent=err.message;}finally{button.disabled=false;}};

function renderRequests(){
 const requests=(state.requests||[]).filter(j=>j.status!=='Canceled');$('requestsButton').hidden=!can('see_requests')||!requests.length;$('requestsButton').textContent=`Requests (${requests.length})`;
 if(!can('see_requests'))$('requestsList').hidden=true;
 $('requestsList').innerHTML=requests.map(j=>`<div class="panel"><strong>${esc(j.type)} request: ${esc(j.customer)}</strong><p>${j.start?esc(j.start):'Requested date/time not specified'} · ${esc(j.address)} · ${esc(j.items)}</p><p>Submitted by ${esc(j.requestedBy)}</p>${photoLinks(j)}${user.can_create?`<button data-review="${esc(j.id)}">Review request</button>`:`<button data-request-status="${esc(j.id)}">Status Update</button>`}</div>`).join('');
 document.querySelectorAll('#jobs .editIcon').forEach(b=>b.hidden=!user.can_create);
}
$('requestsButton').onclick=()=>$('requestsList').hidden=!$('requestsList').hidden;
$('requestsList').onclick=e=>{const status=e.target.closest('[data-request-status]');if(status){openStatus(status.dataset.requestStatus);return;}const b=e.target.closest('[data-review]');if(!b)return;const request=state.requests.find(j=>j.id===b.dataset.review);openJob(request.id);};
$('savePermissions').onclick=async()=>{try{await api('admin/permissions',{name:$('passwordUser').value,can_create:$('canCreate').checked,see_requests:$('seeRequests').checked});$('permissionMessage').textContent='Permissions saved.';await refresh();}catch(e){$('permissionMessage').textContent=e.message;}};

const securityPanel=document.createElement('section');securityPanel.className='card';securityPanel.innerHTML=`<h2>Login security</h2><form id="loginSecurityForm"><label>Failed login attempts before lockout <input id="maxLoginAttempts" type="number" min="1" max="100" step="1" required value="5"></label><button type="submit">Save login limit</button><p>Default: 5. A successful login resets the count. Locked accounts stay locked until an authorized employee unlocks them. Changing the limit does not unlock existing accounts.</p></form><div id="accountUnlockControls"><h3>Locked accounts</h3><button type="button" id="refreshLockouts">Refresh locked accounts</button><div id="lockedAccounts"></div></div><p id="loginSecurityMessage" role="status"></p>`;
$('settings').append(securityPanel);
async function loadLoginSecurity(){
 $('loginSecurityForm').hidden=!user?.admin;$('accountUnlockControls').hidden=!can('unlock_users');$('loginSecurityMessage').textContent='';
 try{if(user?.admin){const data=await api('admin/login-security');$('maxLoginAttempts').value=data.max_attempts;}
 if(can('unlock_users')){const data=await api('admin/lockouts');$('lockedAccounts').innerHTML=data.users.map(u=>`<div class="listRow"><span>${esc(u.name)} · ${u.failures} failed attempts · ${esc(u.locked_at)}</span><button type="button" data-unlock="${esc(u.name)}">Unlock user</button></div>`).join('')||'<p>No locked accounts.</p>';}}
 catch(e){$('loginSecurityMessage').textContent=e.message;}
}
$('loginSecurityForm').onsubmit=async e=>{e.preventDefault();try{await api('admin/login-security',{max_attempts:Number($('maxLoginAttempts').value)});$('loginSecurityMessage').textContent='Login attempt limit saved.';}catch(e){$('loginSecurityMessage').textContent=e.message;}};
$('refreshLockouts').onclick=loadLoginSecurity;
$('lockedAccounts').onclick=async e=>{const b=e.target.closest('[data-unlock]');if(!b)return;b.disabled=true;try{await api('admin/unlock-user',{name:b.dataset.unlock});await loadLoginSecurity();$('loginSecurityMessage').textContent=b.dataset.unlock+' unlocked.';}catch(e){$('loginSecurityMessage').textContent=e.message;}finally{b.disabled=false;}};
const receiptSettings=document.createElement('div');receiptSettings.className='panel';receiptSettings.id='receiptSettings';
receiptSettings.innerHTML='<h2>Receipt categories / codes</h2><form id="receiptCategoryForm"><label>One category or code per line<textarea id="receiptCodes" rows="8" maxlength="20200"></textarea></label><button>Save receipt categories</button></form><p id="receiptSettingsResult" role="status"></p><h3>Submitted receipts</h3><button id="refreshReceipts" type="button">Refresh receipts</button><div id="receiptList"></div>';
$('settings').append(receiptSettings);
const appearancePanel=document.createElement('div');appearancePanel.className='panel';appearancePanel.id='appearanceSettings';
appearancePanel.innerHTML='<h2>Appearance</h2><label for="appearanceMode">Color mode</label><select id="appearanceMode"><option value="light">Light mode</option><option value="dark">Dark mode</option><option value="system">Use system settings</option></select><p>Saved to your user account on the server and restored when you sign in on any device.</p><p id="appearanceStatus" role="status"></p>';
$('settings').append(appearancePanel);
$('appearanceMode').value=window.appAppearance.preference;
$('appearanceMode').onchange=async()=>{const select=$('appearanceMode'),previous=window.appAppearance.preference;select.disabled=true;try{const r=await api('account/appearance',{mode:select.value});window.appAppearance.set(r.mode);$('appearanceStatus').textContent='Appearance saved to your account.';}catch(e){select.value=previous;$('appearanceStatus').textContent=e.message;}finally{select.disabled=false;}};
const mobilePanel=document.createElement('div');mobilePanel.className='panel';mobilePanel.id='mobileViewSettings';mobilePanel.innerHTML='<h2>Mobile view</h2><label for="mobileViewMode">Layout for this browser / device</label><select id="mobileViewMode"><option value="auto">Automatic (detect device and screen)</option><option value="mobile">Mobile view on</option><option value="desktop">Mobile view off (desktop layout)</option></select><p>Automatic adapts to the screen size. You can override it here for this browser.</p><p id="mobileViewStatus" role="status"></p>';$('settings').append(mobilePanel);
let mobileViewMode='auto';try{mobileViewMode=localStorage.getItem('yfc-mobile-view')||'auto';}catch{}
if(!['auto','mobile','desktop'].includes(mobileViewMode))mobileViewMode='auto';
const layoutRules=[];for(const sheet of document.styleSheets){try{for(const rule of sheet.cssRules){if(rule.media&&/\b(?:min|max)-width\s*:/.test(rule.conditionText))layoutRules.push([rule,rule.conditionText]);}}catch{}}
function isMobileView(){return mobileViewMode==='mobile'||(mobileViewMode==='auto'&&(matchMedia('(max-width:740px)').matches||/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)));}
function applyMobileView(){for(const [rule,original]of layoutRules)rule.media.mediaText=mobileViewMode==='auto'?original:((mobileViewMode==='mobile')===/max-width/.test(original)?'all':'not all');document.documentElement.dataset.mobileView=mobileViewMode;$('mobileViewMode').value=mobileViewMode;}
applyMobileView();$('mobileViewMode').onchange=()=>{mobileViewMode=$('mobileViewMode').value;applyMobileView();try{localStorage.setItem('yfc-mobile-view',mobileViewMode);$('mobileViewStatus').textContent='Layout preference saved for this browser.';}catch{$('mobileViewStatus').textContent='Layout applied. This browser could not save the preference.';}};
const sharingPanel=document.createElement('div');sharingPanel.className='panel';sharingPanel.id='sharingSettings';sharingPanel.innerHTML='<h2>Sharing</h2><p>Choose sharing options offered on each device layout.</p><form id="sharingForm"></form><p id="sharingStatus" role="status"></p>';
for(const view of ['mobile','desktop']){const field=document.createElement('fieldset');field.innerHTML='<legend>'+view[0].toUpperCase()+view.slice(1)+' view</legend>'+['text','email','native'].map(type=>'<label><input type="checkbox" name="'+view+'_'+type+'"> '+({text:'Text',email:'Email',native:'Native sharing / AirDrop (where supported)'})[type]+'</label>').join('');sharingPanel.querySelector('form').append(field);}
sharingPanel.querySelector('form').insertAdjacentHTML('beforeend','<button type="submit">Save sharing options</button>');$('settings').append(sharingPanel);
const pageColorPanel=document.createElement('div');pageColorPanel.id='pageColorSettings';pageColorPanel.className='panel';pageColorPanel.innerHTML='<h2>Page Colors</h2><p>Administrator changes apply to everyone. Set each page’s header and backgrounds for light and dark mode. Header text adjusts automatically for contrast.</p><form id="pageColorForm"><div id="pageColorFields"></div><button type="submit">Save page colors</button><button type="button" id="resetPageColors">Restore default colors</button></form><p id="pageColorStatus" role="status"></p>';$('settings').append(pageColorPanel);
const settingsPanels=[...$('settings').children];settingsPanels[0].remove();
const settingsNames=['Phone Access','Backups','Updates','Vehicles','Users','Recent Changes','Login Security','Receipts','Appearance','Mobile View','Sharing','Page Colors'];
const settingsGroups=[{name:'Application Settings',panels:[8,9,10,11,1,2,4,6,5]},{name:'Thrift Mart Dispatch',panels:[3]},{name:'Store Associate Paging',panels:[]},{name:'Receipts & Accounting',panels:[7]},{name:'Print with a Purpose',panels:[]}];
const settingsCategories=document.createElement('nav');settingsCategories.className='settingsTabs';settingsCategories.id='settingsCategories';settingsCategories.setAttribute('aria-label','Settings categories');
const settingsTabs=document.createElement('nav');settingsTabs.className='settingsTabs settingsSubcategories';settingsTabs.id='settingsSubcategories';settingsTabs.setAttribute('aria-label','Settings subcategories');
const settingsEmpty=document.createElement('p');settingsEmpty.id='settingsEmpty';settingsEmpty.setAttribute('role','status');settingsEmpty.hidden=true;
let selectedSettingsCategory=null;
function settingsAllowed(i){if(i===12)return can('manage_staff_schedule');return i!==0&&(i===8||i===9||!!user?.admin||([[],['backup_settings','create_backups'],['check_updates','configure_updates','install_updates'],['manage_vehicles'],['manage_users','reset_passwords','rename_users','manage_roles','manage_staff_schedule'],['view_audit'],['unlock_users'],[],[],[]][i]||[]).some(can));}
function settingsCategory(index){
 index=index===null?0:index;selectedSettingsCategory=index;
 settingsPanels.forEach(panel=>panel.hidden=true);settingsTabs.hidden=false;settingsTabs.replaceChildren();settingsEmpty.hidden=true;
 [...settingsCategories.children].forEach((button,i)=>{button.classList.toggle('selected',i===index);button.setAttribute('aria-pressed',String(i===index));});
 const descriptions={1:['↺','Configure backups and recovery.'],2:['↑','Check releases and connected users.'],3:['▰','Manage dispatch vehicles.'],4:['♙','Manage employee accounts and role assignments.'],5:['≡','Review recent application changes.'],6:['⊙','Manage login protection and locked accounts.'],7:['▤','Configure receipt categories.'],8:['◐','Choose your preferred color mode.'],9:['▣','Set the layout for this device.'],10:['↗','Choose available sharing options.'],11:['◈','Customize application page colors.'],12:['▦','Define jobs used in staff scheduling.']};
 const panels=settingsGroups[index].panels.filter(settingsAllowed);
 for(const i of panels){const button=document.createElement('button');button.type='button';button.dataset.settingsPanel=i;button.setAttribute('aria-label',settingsNames[i]);const [icon,description]=descriptions[i]||['⚙','Manage these settings.'];button.innerHTML=`<span class="settingsTileIcon" aria-hidden="true">${icon}</span><span><strong>${esc(settingsNames[i])}</strong><small>${description}</small></span><span aria-hidden="true">›</span>`;button.onclick=()=>settingsSection(i);settingsTabs.append(button);}
 if(index===0&&can('manage_roles')){const button=document.createElement('button');button.type='button';button.setAttribute('aria-label','Roles');button.innerHTML='<span class="settingsTileIcon" aria-hidden="true">☷</span><span><strong>Roles</strong><small>Manage shared permissions by category.</small></span><span aria-hidden="true">›</span>';button.onclick=()=>{settingsSection(4);selectUserSettings('roles');};settingsTabs.append(button);}
 if(!settingsTabs.children.length){settingsEmpty.textContent='No settings are currently available in this category.';settingsEmpty.hidden=false;}
}
function settingsSection(index){if(!settingsAllowed(index))return;if(index===12)loadWorkJobs();if(index===4)selectUserSettings();if(index===10)loadSharingSettings();if(index===11)loadPageColors(true);const group=settingsGroups.findIndex(g=>g.panels.includes(index));if(group!==selectedSettingsCategory)settingsCategory(group);settingsPanels.forEach((panel,i)=>panel.hidden=i!==index);settingsTabs.hidden=true;}
settingsGroups.forEach((group,i)=>{const button=document.createElement('button');button.type='button';button.textContent=group.name;button.onclick=()=>settingsCategory(i);settingsCategories.append(button);});
$('settings').prepend(settingsCategories,settingsTabs,settingsEmpty);settingsCategory(null);

const globalActions=document.querySelector('.bottomActions');document.querySelector('main').append(globalActions);globalActions.hidden=true;
function updateSignedInUser(){if(!user){commReset();profileReset();workPayrollReset();workCardReset();userIdentityDialog.close();$('userIdentityForm').reset();}else {renderHeaderAvatar();commPoll();if(isMobileView()||commIsIos())commPreparePush();}$('headerShortcuts').hidden=!user;globalActions.hidden=!user; $('loggedOutStatus').hidden=!!user; $('signedInUser').textContent=user?'Signed in as '+user.name:'';$('signedInUser').hidden=!user; }

let permissionCatalog={},savedUserGrants={};
let employeePermissionVersion=0;
async function loadPermissionList(name){
 const version=++employeePermissionVersion,signedIn=user;
 employeeRolesData=null;employeeIndividualGrants={};employeeRole.disabled=true;$('savePermissions').disabled=true;$('permissionChecklist').replaceChildren();$('userRoleSummary').textContent='Loading access…';$('editIndividualAccess').hidden=true;
 if(!can('manage_users')){$('userRoleSummary').textContent='User management permission is required to view or assign roles.';return;}
 try{
  const [data,roleData]=await Promise.all([api('admin/permission-catalog'),api('roles')]);
  if(version!==employeePermissionVersion||user!==signedIn||$('passwordUser').value!==name||!$('passwordDialog').open)return;
  permissionCatalog=data.permissions;savedUserGrants=Object.fromEntries(data.users.map(u=>[u.name,u.grants]));populateEmployeeRole(name,roleData);
  const person=state.users.find(u=>u.name===name),defaults=Object.fromEntries(Object.keys(permissionCatalog).map(key=>[key,false]));
  for(const key of ['view_schedule','submit_requests','cancel_appointments','call_contacts','text_contacts','navigate','change_own_password','submit_receipts'])defaults[key]=true;
  for(const key of ['create_appointments','edit_appointments','delete_appointments','update_status','review_requests','view_reports'])defaults[key]=!!person.can_create;
  defaults.see_requests=!!person.can_create&&!!person.see_requests;
  const grants={...(savedUserGrants[name]||defaults)};
  for(const key of ['submit_receipts','view_schedule','show_vehicle_filter','show_search'])if(!(key in grants))grants[key]=true;
  employeeIndividualGrants=grants;setEmployeeRoleMode();$('savePermissions').disabled=!!person.admin;
 }catch(e){if(version===employeePermissionVersion){$('permissionMessage').textContent=e.message;$('userRoleSummary').textContent='Access could not be loaded. No changes have been made.';}}
}
const permissionChecklist=document.createElement('div');permissionChecklist.id='permissionChecklist';$('permissionFields').prepend(permissionChecklist);
$('canCreate').closest('label').hidden=true;$('seeRequests').closest('label').hidden=true;
$('savePermissions').onclick=async()=>{
 const button=$('savePermissions');button.disabled=true;
 try{if(!employeeRolesData)throw Error('Load the user’s access before saving.');const id=employeeRole.value?Number(employeeRole.value):null;
 if(id!==null||employeeHadRole)await api('admin/user-role',{name:$('passwordUser').value,role_id:id});
 employeeHadRole=id!==null;$('permissionMessage').textContent=id!==null?'Role assigned. Permissions follow the selected role.':'Individual permissions retained.';await loadUserList();
 }catch(e){$('permissionMessage').textContent=e.message;}finally{button.disabled=!employeeRolesData||employeeRole.disabled;}
};

function can(key){return !!(user&&(user.admin||user.grants?.[key]));}
function applyPermissions(){
 $('notifyUpdateSection').hidden=!user.admin;$('openRoles').hidden=!can('manage_roles');if(!can('manage_roles')&&!rolesArea.hidden)selectUserSettings();
 $('filter').hidden=!can('show_vehicle_filter');$('search').hidden=!can('show_search');
 document.querySelectorAll('#jobs .editIcon').forEach(b=>b.hidden=!can('edit_appointments'));
 document.querySelectorAll('#jobs .statusUpdate').forEach(b=>b.hidden=!(can('update_status')||can('cancel_appointments')));
 for(const [selector,key] of [['.textCustomer','text_contacts'],['a[href^="tel:"]','call_contacts'],['a[aria-label^="Navigate"]','navigate']])document.querySelectorAll(selector).forEach(el=>el.hidden=!can(key));
 $('settingsTab').hidden=false;
 $('serverUpdateButton').hidden=!can('check_updates');
 $('reportsTab').hidden=document.body.dataset.section==='receipts'?false:document.body.dataset.section!=='dispatch'||!can('view_reports');
 $('accountButton').hidden=false;$('remove').hidden=!editing||!can('delete_appointments');
 $('addPickup').hidden=$('addDelivery').hidden=!(can('create_appointments')||can('submit_requests'));
}

let requestPhotos=[];
function photoLinks(j){return Array.from({length:j.photoCount||0},(_,i)=>`<a class="photoLink" href="/api/photo/${encodeURIComponent(j.id)}/${i}" target="_blank" rel="noopener">View photo ${i+1}</a>`).join(' ');}
const requestSection=document.createElement('section');requestSection.id='requestPhotoSection';requestSection.innerHTML='<hr><h3>Photos (optional)</h3><button id="addPhotos" type="button">Add photos</button><p>Up to 3 photos. Images are resized before uploading.</p><p id="photoMessage" role="status"></p><div id="photoPreviews"></div><hr>';
const optionalDivider=document.createElement('div');optionalDivider.id='optionalDivider';optionalDivider.innerHTML='<hr><h3>Additional details (optional)</h3>';
const jobGrid=$('jobForm').querySelector('.grid'),originalFields=[...jobGrid.children],originalActions=$('jobForm').querySelector('.actions');
jobGrid.append(requestSection);requestSection.hidden=true;
const bottomRequestSubmit=document.createElement('button');bottomRequestSubmit.type='submit';bottomRequestSubmit.className='primary bottomRequestSubmit';bottomRequestSubmit.textContent='Submit';
function layoutRequestForm(){
 bottomRequestSubmit.remove();
 requestPhotos=[];$('photoMessage').textContent='';renderPhotoPreviews();$('addPhotos').disabled=false;
 const requestOnly=!user.can_create;
 for(const field of originalFields)jobGrid.append(field);
 requestSection.hidden=!requestOnly;jobGrid.append(requestSection);optionalDivider.remove();$('jobForm').append(originalActions);
 for(const field of ['phone','street','city','state','zip','items'])$('jobForm').elements[field].required=!requestOnly;
 if(requestOnly){
 const customer=$('jobForm').elements.customer.closest('label');jobGrid.prepend(customer);customer.after(requestSection);requestSection.after(originalActions);originalActions.after(optionalDivider);
 $('save').textContent='Submit';$('jobForm').append(bottomRequestSubmit);
 }
 if(editing&&editing.photoCount){$('photoPreviews').innerHTML=photoLinks(editing);}
}
function renderPhotoPreviews(){$('photoPreviews').innerHTML=requestPhotos.map((photo,i)=>`<div><img alt="Attached photo ${i+1}" src="data:image/jpeg;base64,${photo}"><button type="button" data-remove-photo="${i}">Remove photo ${i+1}</button></div>`).join('');}
$('addPhotos').onclick=()=>{if(isMobileView())$('photoPicker').showModal();else $('photoFiles').click();};
$('chooseLibrary').onclick=()=>{$('photoPicker').close();$('photoFiles').click();};$('chooseCamera').onclick=()=>{$('photoPicker').close();$('cameraFile').click();};$('closePhotoPicker').onclick=()=>$('photoPicker').close();
$('photoPreviews').onclick=e=>{const b=e.target.closest('[data-remove-photo]');if(b){requestPhotos.splice(Number(b.dataset.removePhoto),1);renderPhotoPreviews();}};
async function readPhoto(file){const url=URL.createObjectURL(file);try{const img=new Image();img.src=url;await img.decode();const scale=Math.min(1,1280/img.width,1280/img.height),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.width*scale));canvas.height=Math.max(1,Math.round(img.height*scale));const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);return canvas.toDataURL('image/jpeg',.75).split(',')[1];}finally{URL.revokeObjectURL(url);}}
for(const id of ['photoFiles','cameraFile'])$(id).onchange=async e=>{const files=[...e.target.files];$('photoMessage').textContent='Preparing photos…';$('addPhotos').disabled=true;$('save').disabled=true;bottomRequestSubmit.disabled=true;try{for(const file of files){if(requestPhotos.length>=3){toast('Up to 3 photos per request.');break;}if(file.size>25000000)throw Error('Choose a photo smaller than 25 MB.');const photo=await readPhoto(file);if(photo.length>1333332)throw Error('Photo is too large. Choose a smaller image.');requestPhotos.push(photo);}renderPhotoPreviews();$('photoMessage').textContent=requestPhotos.length+' photo(s) attached. Tap Submit to upload with this request.';}catch(err){$('photoMessage').textContent='Unable to add photo. '+err.message+' Try selecting a JPEG from your photo library.';toast('Unable to add photo: '+err.message);}finally{e.target.value='';$('addPhotos').disabled=false;$('save').disabled=false;bottomRequestSubmit.disabled=false;}};

let reportJobs=[];
$('reportDate').value=localDate(new Date());
$('reportsTab').onclick=()=>{if(document.body.dataset.section==='receipts')openReceiptHistory(true);else{storeSection('dispatch');tab('reports');}};
async function loadReport(){try{const result=await api('reports');reportJobs=result.jobs;
 for(const [id,values] of [['reportVehicle',[...new Set([...state.vehicles,...reportJobs.map(j=>j.vehicle).filter(Boolean)])]],['reportStaff',[...new Set([...state.users.map(u=>u.name),...reportJobs.flatMap(j=>j.staffNames|| (j.staff?[j.staff]:[]))])]]]){const current=$(id).value;$(id).innerHTML=`<option value="">${id==='reportVehicle'?'All vehicles':'All staff'}</option>`+values.sort().map(v=>`<option>${esc(v)}</option>`).join('');$(id).value=current;}
 $('reportError').textContent='';renderReport();}catch(e){$('reportError').textContent=e.message;$('reportOutput').innerHTML='';}}
function renderReport(){
 const date=$('reportDate').value;if(!date)return;
 const start=$('reportPeriod').value==='week'?weekStart(date):date,end=$('reportPeriod').value==='week'?shiftDate(start,6):start;
 const type=$('reportType').value,vehicle=$('reportVehicle').value,staff=$('reportStaff').value,scope=$('reportScope').value;
 const jobs=reportJobs.filter(j=> (scope==='all'||(scope==='requests'?j.request:!j.request))&&(!type||j.type===type)&&(!vehicle||j.vehicle===vehicle)&&(!staff||(j.staffNames||[j.staff]).includes(staff))&&(!j.start?j.request&&$('reportUndated').checked:j.start.slice(0,10)<=end&&(j.end||j.start).slice(0,10)>=start)).sort((a,b)=>(a.start||'9999').localeCompare(b.start||'9999'));
 $('reportOutput').innerHTML=`<h2>Thrift Mart Dispatch — ${scope==='requests'?'Requests':scope==='all'?'Appointments & requests':'Appointments'}</h2><p>${esc(dateLabel(start))}${end!==start?' – '+esc(dateLabel(end)):''}</p><p>${esc(type||'Pickups & deliveries')} · ${esc(vehicle||'All vehicles')} · ${esc(staff||'All staff')}</p><p><strong>${jobs.length} records · ${jobs.filter(j=>j.type==='Pickup').length} pickups · ${jobs.filter(j=>j.type==='Delivery').length} deliveries</strong></p>`+jobs.map(j=>`<article class="reportRecord"><h3>${esc(j.type)}${j.request?' request':''} — ${esc(j.customer)}</h3><p><strong>${j.start?esc(dateLabel(j.start.slice(0,10)))+' · '+esc(timeLabel(j.start)):'No requested date/time'}${j.end?' to '+esc(timeLabel(j.end)):''}</strong> · ${esc(j.status==='Canceled'?'Cancelled':j.status)}</p><p>${esc(j.address||'Address not provided')}<br>${esc(j.phone||'Phone not provided')}</p><p><strong>Items:</strong> ${esc(j.items||'Not provided')}</p><p><strong>Vehicle:</strong> ${esc(j.vehicle||'Unassigned')} · <strong>Staff:</strong> ${esc(j.staff||'Unassigned')}</p>${j.notes?`<p><strong>Notes:</strong> ${esc(j.notes)}</p>`:''}${j.requestedBy?`<p>Requested by ${esc(j.requestedBy)}</p>`:''}</article>`).join('')+(jobs.length?'':'<p>No records match the selected filters.</p>');
}
$('reportFilters').onsubmit=e=>{e.preventDefault();loadReport();};
for(const id of ['reportPeriod','reportDate','reportScope','reportType','reportVehicle','reportStaff','reportUndated'])$(id).onchange=renderReport;
let emailReportUrl=null;
function reportEmailDraft(text,subject){
 const full='mailto:?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(text);
 const attachment=full.length>1800;
 return {attachment,href:attachment?'mailto:?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent('Please see the attached Thrift Mart Dispatch report.'):full};
}
$('emailReport').onclick=()=>{
 if(!can('view_reports'))return;
 if(!$('reportOutput').textContent.trim()){toast('Refresh the report first.');return;}
 const text=$('reportOutput').innerText,subject='Thrift Mart Dispatch report — '+$('reportDate').value;
 const draft=reportEmailDraft(text,subject);
 $('emailReportPreview').value=text;
 $('emailReportHelp').textContent=draft.attachment?'This report is too long for an email link. First download the report, then open your email app and attach the downloaded file.':'Open your email app to create a message containing the report below. You can also download it as an attachment.';
 $('openReportEmail').href=draft.href;
 if(emailReportUrl)URL.revokeObjectURL(emailReportUrl);
 emailReportUrl=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
 $('downloadEmailReport').href=emailReportUrl;
 $('emailReportDialog').showModal();
};
$('closeEmailReport').onclick=()=>$('emailReportDialog').close();
$('emailReportDialog').addEventListener('close',()=>{if(emailReportUrl)URL.revokeObjectURL(emailReportUrl);emailReportUrl=null;$('emailReportPreview').value='';$('downloadEmailReport').removeAttribute('href');$('openReportEmail').removeAttribute('href');});
$('printReport').onclick=()=>{if(!$('reportOutput').textContent){toast('Refresh the report first.');return;}window.print();};

const reviewPhotos=document.createElement('section');reviewPhotos.id='reviewPhotos';$('jobForm').querySelector('.dialogTop').after(reviewPhotos);
function renderReviewPhotos(){
 reviewPhotos.hidden=!editing;
 reviewPhotos.innerHTML=editing?`<h3>Photos</h3>${editing.photoCount?'<p>Select a photo to open a larger preview.</p><div class="reviewPhotoGrid">'+Array.from({length:editing.photoCount},(_,i)=>`<button type="button" data-preview-photo="${i}" aria-label="Preview photo ${i+1}"><img src="/api/photo/${encodeURIComponent(editing.id)}/${i}" alt="Request photo ${i+1}"><span>View photo ${i+1}</span></button>`).join('')+'</div>':'<p>No photos attached.</p>'}<hr>`:'';
}
reviewPhotos.onclick=e=>{const button=e.target.closest('[data-preview-photo]');if(!button||!editing)return;const index=Number(button.dataset.previewPhoto);$('photoPreviewTitle').textContent=`${editing.customer} — Photo ${index+1}`;$('photoPreviewError').textContent='';$('largePhoto').src=`/api/photo/${encodeURIComponent(editing.id)}/${index}`;$('photoPreviewDialog').showModal();};
$('largePhoto').onerror=()=>$('photoPreviewError').textContent='Unable to load this photo. Check your connection and try again.';
$('closePhotoPreview').onclick=()=>$('photoPreviewDialog').close();
$('photoPreviewDialog').addEventListener('close',()=>{$('largePhoto').removeAttribute('src');});

$('jobs').addEventListener('keydown',e=>{const header=e.target.closest('[data-toggle-appointment]');if(header&&(e.key==='Enter'||e.key===' ')){e.preventDefault();const id=header.dataset.toggleAppointment;header.click();document.querySelector(`[data-toggle-appointment="${id}"]`)?.focus();}});

const printPage=document.createElement('section');printPage.id='printPurpose';printPage.hidden=true;printPage.className='panel';printPage.innerHTML='<h1>Print with a Purpose</h1><p>This page is being designed. Check back soon.</p>';$('app').before(printPage);
const printMenu=document.createElement('button');printMenu.id='printSection';printMenu.type='button';printMenu.textContent='Print with a Purpose';printMenu.onclick=()=>storeSection('print');menuDivider.before(printMenu);
let pagingEnabled=false,pagingTimer=null,lastPageId=0,pagingBusy=false;
const appearanceMenu=document.createElement('button');appearanceMenu.type='button';appearanceMenu.id='appearanceMenu';appearanceMenu.textContent='Settings';appearanceMenu.onclick=()=>{if(requireSignIn()){storeSection('dispatch');tab('settings');}};$('storeMenu').append(appearanceMenu);
function closeStoreMenu(){$('storeMenu').hidden=true;$('storeMenuButton').setAttribute('aria-expanded','false');}
document.addEventListener('pointerdown',e=>{if(!$('storeMenu').contains(e.target)&&!$('storeMenuButton').contains(e.target))closeStoreMenu();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeStoreMenu();});
document.addEventListener('pointermove',e=>{if(e.pointerType!=='mouse'||isMobileView()||$('storeMenu').hidden)return;const a=$('storeMenu').getBoundingClientRect(),b=$('storeMenuButton').getBoundingClientRect();if(e.clientX<Math.min(a.left,b.left)||e.clientX>Math.max(a.right,b.right)||e.clientY<Math.min(a.top,b.top)||e.clientY>Math.max(a.bottom,b.bottom))closeStoreMenu();});
$('storeMenuButton').onclick=()=>{const open=$('storeMenu').hidden;$('storeMenu').hidden=!open;$('storeMenuButton').setAttribute('aria-expanded',String(open));};
function storeSection(section){
 if(!requireSignIn())return;
 section=section===true?'paging':section===false?'dispatch':section;document.body.classList.remove('settingsView');$('settings').hidden=true;
 $('receiptUpload').hidden=true;if($('receiptHistory'))$('receiptHistory').hidden=true;
 $('storeMenu').hidden=true;$('storeMenuButton').setAttribute('aria-expanded','false');
 if(!['dispatch','paging','receipts','print'].includes(section))section='dispatch';
 if(section==='paging'&&!can('send_pages')&&!can('receive_pages')){toast('Ask an administrator for paging permission.');return;}
 printPage.hidden=section!=='print';$('paging').hidden=section!=='paging';$('app').hidden=section!=='dispatch';$('receipts').hidden=section!=='receipts';
 if(section==='dispatch')quickView(null);
 setSectionHeader({dispatch:'Thrift Mart Dispatch',paging:'Store Associate Paging',receipts:'Receipts & Accounting',print:'Print with a Purpose'}[section],section);
 $('reportsTab').hidden=section==='receipts'?false:section!=='dispatch'||!can('view_reports');$('pagingForm').hidden=!can('send_pages');$('enablePaging').disabled=!can('receive_pages')||pagingEnabled;
}
$('receiptsSection').onclick=()=>storeSection('receipts');
$('pagingSection').onclick=()=>storeSection(true);$('dispatchSection').onclick=()=>storeSection(false);$('backDispatch').onclick=()=>storeSection(false);
function sayPage(text){const speech=new SpeechSynthesisUtterance(text);speech.rate=.9;speech.onerror=()=>{$('pageReceiverStatus').textContent='Audio playback failed. Enable the speaker again and test the volume.';};window.speechSynthesis.speak(speech);}
$('pagingForm').onsubmit=async e=>{e.preventDefault();$('sendPage').disabled=true;try{await api('paging/send',{area:$('pageArea').value});$('pageSendStatus').textContent='Page queued for enabled speaker devices. Playback is not confirmed.';}catch(err){$('pageSendStatus').textContent=err.message;}finally{$('sendPage').disabled=false;}};
function stopPaging(){pagingEnabled=false;clearInterval(pagingTimer);if('speechSynthesis' in window)window.speechSynthesis.cancel();$('enablePaging').disabled=false;$('disablePaging').disabled=true;$('pageReceiverStatus').textContent='Speaker disabled.';}
$('disablePaging').onclick=stopPaging;
$('enablePaging').onclick=async()=>{if(!('speechSynthesis' in window)){toast('Speech playback is not supported by this browser.');return;}try{sayPage('M G C Y F C Operations. Speaker test.');const result=await api('paging');lastPageId=result.latest;pagingEnabled=true;$('enablePaging').disabled=true;$('disablePaging').disabled=false;$('pageReceiverStatus').textContent='Speaker enabled. Keep this device awake and browser open.';clearInterval(pagingTimer);pagingTimer=setInterval(pollPages,3000);}catch(e){stopPaging();toast(e.message);}};
async function pollPages(){if(!pagingEnabled||pagingBusy||!user)return;pagingBusy=true;try{if(!can('receive_pages')){stopPaging();return;}const result=await api('paging');for(const page of result.pages){if(page.id>lastPageId){lastPageId=page.id;if(Date.now()/1000-page.at<30)sayPage(`Associate assistance requested at ${page.area}. Associate to ${page.area}, please.`);}}lastPageId=Math.max(lastPageId,result.latest);$('pageReceiverStatus').textContent='Speaker enabled · Connected';}catch(e){$('pageReceiverStatus').textContent='Paging connection interrupted: '+e.message;}finally{pagingBusy=false;}}

function setSectionHeader(title,section){
 section=section===true?'dispatch':section===false?'signin':section;
 if(section!=='workforce'&&$('workforce')&&!workPanel.hidden){
  workPanel.hidden=true;
  $('workCopyDialog').close();
  workVersion++;
 }
 if(section!=='comms'&&!commPanel.hidden){commPanel.hidden=true;commVersion++;$('commPrefsDialog').close();}
 $('currentSection').textContent=title;document.body.dataset.section=section;
 document.querySelector('meta[name="theme-color"]').content=({dispatch:'#b51f2b',paging:'#7a1520',receipts:'#067a06',print:'#073ea6',comms:'#9fcf04',workforce:'#cb04cf'})[section]||'#215baa';applyPageColors();
}
let requestedReceipts=false;
function populateDailySections(preference){
 const choices=$('sectionChoices');choices.replaceChildren();
 for(const id of ['dispatch','paging','receipts','print'])$(id+'Section').hidden=!preference.options.some(o=>o.id===id);
 for(const option of preference.options){const label=document.createElement('label');label.className='sectionChoice';const input=document.createElement('input');input.type='radio';input.name='section';input.value=option.id;input.required=true;input.checked=option.id===(requestedReceipts?'receipts':preference.section||preference.options[0].id);label.append(input,document.createTextNode(option.label));choices.append(label);}
 $('sectionChoiceError').textContent='';$('sectionDay').textContent=preference.date+' (server calendar day)';
}
async function chooseLanding(force=false){const preference=await api('account/landing');populateDailySections(preference);if(preference.section&&!force){const target=requestedReceipts?'receipts':preference.section;requestedReceipts=false;storeSection(target);return;}setSectionHeader('Choose today’s starting page',false);if(!$('sectionChooser').open)$('sectionChooser').showModal();}
$('sectionChooserForm').onsubmit=async e=>{e.preventDefault();const section=new FormData(e.target).get('section');try{await api('account/landing',{section});requestedReceipts=false;$('sectionChooser').close();storeSection(section);}catch(err){$('sectionChoiceError').textContent=err.message;}};
$('sectionChooser').addEventListener('cancel',e=>e.preventDefault());
$('chooseStartSection').onclick=()=>{if(!requireSignIn())return;closeStoreMenu();chooseLanding(true).catch(e=>toast(e.message));};
let updateReminderAfter=0;
function noticeStorageKey(){return 'yfc-update-notice:'+user.name;}
function checkUpdateNotice(){const notice=state.updateNotice;if(!user||!notice||Date.now()<updateReminderAfter||document.querySelector('dialog[open]'))return;let seen=null;try{seen=localStorage.getItem(noticeStorageKey());}catch{}if(seen===String(notice.id))return;$('userUpdateMessage').textContent=`${notice.actor} asks you to refresh to server version ${notice.version}.`;$('userUpdateDialog').showModal();}
$('notifyUsersUpdate').onclick=async()=>{if(!confirm('Notify users to save their work and refresh their web app? Install the server update first.'))return;$('notifyUsersUpdate').disabled=true;try{await api('admin/notify-update',{});$('notifyUpdateStatus').textContent='Notice sent. Connected users will see it on their next refresh; offline users when they reconnect.';}catch(e){$('notifyUpdateStatus').textContent=e.message;}finally{$('notifyUsersUpdate').disabled=false;}};
$('userUpdateNow').onclick=()=>{if(!confirm('Reload now? Any unsaved form entries will be lost.'))return;try{localStorage.setItem(noticeStorageKey(),String(state.updateNotice.id));}catch{}location.reload();};
$('userUpdateLater').onclick=()=>{updateReminderAfter=Date.now()+5*60*1000;$('userUpdateDialog').close();};
$('userUpdateDialog').addEventListener('cancel',()=>{updateReminderAfter=Date.now()+5*60*1000;});

// Start media only on the signed-out screen; never delay access to the form.
(()=>{
 const media=JSON.parse($('splashMedia').textContent),desktop=$('desktopVideo'),phone=$('mobileVideo'),intro=$('mobileIntro');
 const mobile=matchMedia('(max-width:740px)'),reduce=matchMedia('(prefers-reduced-motion:reduce)');
 const format=desktop.canPlayType('video/mp4; codecs="avc1.42E01E"')?'mp4':'webm';let timeout,started=false,introFrame=null,fadeTimer=null,fading=false;const introEnd=5.5,introFadeMs=700;
 desktop.poster=media.desktopposter;phone.poster=media.mobileposter;
 const fallback=document.createElement('img');fallback.id='desktopFallback';fallback.alt='Mississippi Gulf Coast Youth for Christ ministries and stores';fallback.src=media.desktopposter;fallback.hidden=true;desktop.after(fallback);
 desktop.muted=true;desktop.defaultMuted=true;desktop.autoplay=true;desktop.playsInline=true;
 let desktopTimeout,failed=false,playAttempt=0;
 function showFallback(){failed=true;clearTimeout(desktopTimeout);desktop.pause();desktop.hidden=true;fallback.hidden=false;$('pauseVideo').hidden=true;}
 function waitForPlayback(){clearTimeout(desktopTimeout);desktopTimeout=setTimeout(showFallback,10000);}
 desktop.addEventListener('error',showFallback);
 desktop.addEventListener('playing',()=>{if(failed)return;clearTimeout(desktopTimeout);desktop.hidden=false;fallback.hidden=true;$('pauseVideo').hidden=false;});
 desktop.addEventListener('waiting',waitForPlayback);

 const mobilePlayPrompt=document.createElement('button');mobilePlayPrompt.id='mobilePlayPrompt';mobilePlayPrompt.type='button';mobilePlayPrompt.className='primary';mobilePlayPrompt.textContent='Tap to play intro';mobilePlayPrompt.hidden=true;$('login').before(mobilePlayPrompt);mobilePlayPrompt.onclick=()=>playIntro(true);
 function finish(){clearTimeout(timeout);clearTimeout(fadeTimer);cancelAnimationFrame(introFrame);phone.pause();phone.autoplay=false;intro.hidden=true;intro.classList.remove('introFading');fading=false}
 function fadeIntro(){if(intro.hidden||fading)return;fading=true;clearTimeout(timeout);cancelAnimationFrame(introFrame);phone.pause();intro.classList.add('introFading');fadeTimer=setTimeout(finish,introFadeMs);}
 function watchIntro(){if(intro.hidden||fading)return;if(phone.currentTime>=introEnd){fadeIntro();return;}introFrame=requestAnimationFrame(watchIntro);}
 function playIntro(manual=false){if((reduce.matches&&!manual)||$('auth').hidden)return;mobilePlayPrompt.hidden=true;clearTimeout(timeout);clearTimeout(fadeTimer);cancelAnimationFrame(introFrame);fading=false;intro.classList.remove('introFading');intro.hidden=false;phone.muted=true;phone.defaultMuted=true;phone.autoplay=true;phone.playsInline=true;phone.setAttribute('muted','');phone.setAttribute('playsinline','');phone.setAttribute('webkit-playsinline','');const source=new URL('/media/mobile-intro.'+format+'?v=title-2',location.href).href;if(phone.src!==source){phone.src=source;phone.load();}phone.currentTime=0;phone.play().catch(()=>{finish();if(!$('auth').hidden&&isMobileView())mobilePlayPrompt.hidden=false;});introFrame=requestAnimationFrame(watchIntro);timeout=setTimeout(finish,10000)}
 function playDesktop(){const attempt=++playAttempt;failed=false;desktop.hidden=false;fallback.hidden=true;$('pauseVideo').hidden=false;if(!desktop.src)desktop.src=media['desktop'+format];waitForPlayback();desktop.play().then(()=>{if(attempt!==playAttempt)return;clearTimeout(desktopTimeout);if($('auth').hidden){desktop.pause();return;}$('pauseVideo').textContent='Pause video'}).catch(()=>{if(attempt===playAttempt&&!$('auth').hidden)showFallback();})}
 function sync(){if($('auth').hidden){mobilePlayPrompt.hidden=true;++playAttempt;clearTimeout(desktopTimeout);desktop.pause();started=false;if(!intro.hidden)finish();return;}if(!started){started=true;if(isMobileView()){if(document.activeElement!==$('login').elements.name)playIntro();}else if(!reduce.matches)playDesktop();else showFallback();}}
 $('skipVideo').onclick=finish;phone.onended=fadeIntro;phone.onerror=finish;phone.addEventListener('timeupdate',()=>{if(!intro.hidden&&phone.currentTime>=introEnd)fadeIntro();});document.addEventListener('visibilitychange',()=>{if(document.hidden&&!intro.hidden)finish();});
 $('pauseVideo').onclick=()=>{if(desktop.paused)playDesktop();else{clearTimeout(desktopTimeout);desktop.pause();$('pauseVideo').textContent='Play video'}};
 $('replayIntro').onclick=()=>{if(isMobileView())playIntro(true);else{desktop.currentTime=0;playDesktop()}};
 $('receiptShortcut').onclick=()=>openReceiptUpload();
 new MutationObserver(sync).observe($('auth'),{attributes:true,attributeFilter:['hidden']});
 mobile.addEventListener('change',()=>{finish();desktop.pause();if(!mobile.matches&&!reduce.matches&&!$('auth').hidden)playDesktop()});
 reduce.addEventListener('change',()=>{if(reduce.matches){finish();showFallback()}else if(!mobile.matches&&!$('auth').hidden)playDesktop()});sync();
})();

// Receipt collection remains separate from authenticated operations access.
let receiptFile=null,receiptId=null,receiptBusy=false;
function resetReceipt(){receiptFile=null;receiptId=null;$('receiptFilename').textContent='No file selected.';$('receiptResult').textContent='';$('receiptCamera').value='';}
function pickReceipt(input){receiptFile=input.files[0]||null;receiptId=null;$('receiptFilename').textContent=receiptFile?receiptFile.name:'No file selected.';$('receiptResult').textContent='';}
$('receiptFile').onchange=()=>pickReceipt($('receiptFile'));$('receiptCamera').onchange=()=>pickReceipt($('receiptCamera'));
$('receiptCameraButton').onclick=()=>$('receiptCamera').click();$('receiptGalleryButton').onclick=()=>$('receiptFile').click();
const receiptAssigneeLabel=document.createElement('label');receiptAssigneeLabel.id='receiptAssigneeLabel';receiptAssigneeLabel.innerHTML='Assign receipt to user *<select id="receiptAssignee"><option value="">Select a user</option></select><span class="muted">Required when submitting without signing in.</span>';$('receiptCategory').closest('label').before(receiptAssigneeLabel);
const reimbursementLabel=document.createElement('label');reimbursementLabel.className='reimbursementLabel';reimbursementLabel.innerHTML='<input id="receiptReimbursement" type="checkbox"> Reimbursement Required';$('receiptCategory').closest('label').after(reimbursementLabel);
async function openReceiptUpload(){
 printPage.hidden=true;$('receiptForm').reset();$('auth').hidden=true;$('app').hidden=true;$('paging').hidden=true;$('receipts').hidden=true;$('storeMenu').hidden=true;$('receiptUpload').hidden=false;
 setSectionHeader('Receipt Upload','receipts');$('receiptCategory').replaceChildren(new Option('Select a category / code',''));$('receiptCategoryHelp').textContent='Loading categories…';
 receiptAssigneeLabel.hidden=!!user;$('receiptAssignee').required=!user;$('receiptAssignee').disabled=!!user;$('receiptAssignee').replaceChildren(new Option('Select a user',''));
 try{if(!user){const people=await api('receipt-users');for(const person of people.users)$('receiptAssignee').add(new Option(person.name,person.id));if(!people.users.length)$('receiptResult').textContent='No receipt submitters are configured. Ask an administrator for help.';}const r=await api('receipt-categories');for(const code of r.categories)$('receiptCategory').add(new Option(code,code));$('receiptCategoryHelp').textContent=r.categories.length?'':'An administrator needs to add receipt categories in Settings before you can submit.';}
 catch(e){$('receiptCategoryHelp').textContent=e.message;}
}
$('openReceiptUpload').onclick=()=>openReceiptUpload();
const resetDialog=document.createElement('dialog');resetDialog.id='receiptResetDialog';resetDialog.innerHTML='<h2>Reset receipt form?</h2><p>This will clear the information and attachment you entered.</p><button type="button" id="confirmReceiptReset">Yes, reset form</button><button type="button" id="cancelReceiptReset">No, keep my information</button>';document.body.append(resetDialog);
$('receiptForm').onreset=resetReceipt;
$('receiptForm').querySelector('[type=reset]').onclick=e=>{e.preventDefault();resetDialog.showModal();};
$('confirmReceiptReset').onclick=()=>{resetDialog.close();$('receiptForm').reset();};
function cancelReceiptReset(){resetDialog.close();toast('No changes have been made.');}
$('cancelReceiptReset').onclick=cancelReceiptReset;
resetDialog.addEventListener('cancel',e=>{e.preventDefault();cancelReceiptReset();});
$('receiptReturn').onclick=async()=>{if(receiptBusy)return;$('receiptUpload').hidden=true;await boot();};
$('receiptForm').onsubmit=async e=>{
 e.preventDefault();if(receiptBusy)return;
 if(!receiptFile){$('receiptResult').textContent='Choose a receipt photo or file.';return;}
 if(receiptFile.size>3000000){$('receiptResult').textContent='Choose a file 3 MB or smaller.';return;}
 const startNew=e.submitter?.value==='new';receiptBusy=true;
 const buttons=[...$('receiptForm').querySelectorAll('button,input,select')];buttons.forEach(b=>b.disabled=true);
 try{
  if(!receiptId){const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);receiptId=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');}
  const body=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('Unable to read this file.'));reader.readAsDataURL(receiptFile);});
  const r=await api('receipt-submit',{id:receiptId,category:$('receiptCategory').value,filename:receiptFile.name,body,account_upload:!!user,assignee:user?undefined:$('receiptAssignee').value,reimbursement_required:$('receiptReimbursement').checked});
  $('receiptForm').reset();$('receiptResult').textContent='Receipt saved. Email delivery is pending email setup.'+(startNew?' Ready for the next receipt.':' Confirmation: '+r.id);
  if(startNew)$('receiptGalleryButton').focus();
 }catch(err){$('receiptResult').textContent=err.message;}
 finally{receiptBusy=false;buttons.forEach(b=>b.disabled=false);}
};
async function loadReceiptSettings(){
 receiptSettings.hidden=!user?.admin;if(!user?.admin)return;
 try{const r=await api('receipt-categories');$('receiptCodes').value=r.categories.join('\n');await loadReceipts();}catch(e){$('receiptSettingsResult').textContent=e.message;}
}
async function loadReceipts(){try{const r=await api('admin/receipts');$('receiptList').innerHTML=r.receipts.map(x=>`<p>${esc(new Date(x.at*1000).toLocaleString())} · ${x.guest_assigned?'Assigned by guest to ':''}${esc(x.actor)} · ${esc(x.category)} · Reimbursement: ${x.reimbursement_required?'Required':'Not required'} · <a href="/api/admin/receipt-file/${esc(x.id)}" target="_blank" rel="noopener">${esc(x.filename)}</a> · Email pending</p>`).join('')||'<p>No receipts submitted.</p>';}catch(e){$('receiptSettingsResult').textContent=e.message;}}
$('refreshReceipts').onclick=loadReceipts;
$('receiptCategoryForm').onsubmit=async e=>{e.preventDefault();try{await api('admin/receipt-categories',{categories:$('receiptCodes').value.split('\n').map(x=>x.trim()).filter(Boolean)});$('receiptSettingsResult').textContent='Receipt categories saved.';}catch(err){$('receiptSettingsResult').textContent=err.message;}};

boot();

const shareCard=document.createElement('section');shareCard.className='receiptShortcut shareYfc';shareCard.innerHTML='<div><h3>Share YFC with Someone</h3><div class="shareYfcRow"><img id="shareYfcLogo" alt="Youth for Christ"><button type="button" id="shareYfcButton">Share YFC</button></div></div>';
document.querySelector('.loginColumn').append(shareCard);$('shareYfcLogo').src=document.querySelector('#loginBrand img').src;
const shareDialog=document.createElement('dialog');shareDialog.innerHTML='<h2>Share YFC with Someone</h2><p>Choose how to share the YFC website.</p><div class="shareOptions"><a id="shareText">Text message</a><a id="shareEmail">Email</a><button id="shareNative" type="button">AirDrop / More options</button></div><p id="shareResult" role="status"></p><button id="closeShare" type="button">Close</button>';document.body.append(shareDialog);
const shareUrl='https://www.coastyfc.com/',shareText='Learn more about Mississippi Gulf Coast Youth for Christ: '+shareUrl;
$('shareText').href='sms:'+(/iPhone|iPad|iPod/i.test(navigator.userAgent)?'&':'?')+'body='+encodeURIComponent(shareText);$('shareEmail').href='mailto:?subject='+encodeURIComponent('Mississippi Gulf Coast Youth for Christ')+'&body='+encodeURIComponent(shareText);
let sharingOptions={mobile:{text:true,email:true,native:true},desktop:{text:true,email:true,native:false}};
shareCard.after($('replayIntro'));
const textAppDialog=document.createElement('dialog');textAppDialog.id='textAppDialog';textAppDialog.innerHTML='<h2>Choose a messaging application</h2><p>Your computer may ask you to select or install an application that handles text messages.</p><a id="openTextApp">Find / open a messaging app</a><button type="button" id="closeTextApp">Close</button>';document.body.append(textAppDialog);$('openTextApp').href=$('shareText').href;$('closeTextApp').onclick=()=>textAppDialog.close();
const shareEmailDialog=document.createElement('dialog');shareEmailDialog.id='shareEmailDialog';shareEmailDialog.innerHTML='<h2>Share by email</h2><p>Choose where to compose your message.</p><p><a id="shareMailApp">Email app on this computer</a></p><p><a id="shareGmail" target="_blank" rel="noopener">Gmail in a new browser tab</a></p><p><a id="shareOutlook" target="_blank" rel="noopener">Outlook in a new browser tab</a></p><button type="button" id="closeShareEmail">Close</button>';document.body.append(shareEmailDialog);$('shareMailApp').href=$('shareEmail').href;$('shareGmail').href='https://mail.google.com/mail/?view=cm&fs=1&su='+encodeURIComponent('Mississippi Gulf Coast Youth for Christ')+'&body='+encodeURIComponent(shareText);$('shareOutlook').href='https://outlook.live.com/mail/0/deeplink/compose?subject='+encodeURIComponent('Mississippi Gulf Coast Youth for Christ')+'&body='+encodeURIComponent(shareText);$('closeShareEmail').onclick=()=>shareEmailDialog.close();
function currentSharingOptions(){return sharingOptions[isMobileView()?'mobile':'desktop'];}
function updateSharingDisplay(){const options=currentSharingOptions();shareCard.hidden=!Object.values(options).some(Boolean);$('shareText').hidden=!options.text;$('shareEmail').hidden=!options.email;$('shareNative').hidden=!options.native||!navigator.share;}
async function loadSharingSettings(){try{sharingOptions=await api('sharing');for(const view of ['mobile','desktop'])for(const type of ['text','email','native'])$('sharingForm').elements[view+'_'+type].checked=sharingOptions[view][type];updateSharingDisplay();}catch(e){$('sharingStatus').textContent=e.message;}}
$('sharingForm').onsubmit=async e=>{e.preventDefault();const options={};for(const view of ['mobile','desktop'])options[view]=Object.fromEntries(['text','email','native'].map(type=>[type,$('sharingForm').elements[view+'_'+type].checked]));try{sharingOptions=await api('sharing',options);updateSharingDisplay();$('sharingStatus').textContent='Sharing options saved for mobile and desktop views.';}catch(err){$('sharingStatus').textContent=err.message;}};
$('mobileViewMode').addEventListener('change',updateSharingDisplay);window.addEventListener('resize',updateSharingDisplay);
$('shareYfcButton').onclick=()=>{updateSharingDisplay();shareDialog.showModal();$('shareResult').textContent=currentSharingOptions().native&&navigator.share?'Native sharing includes AirDrop on supported Apple devices.':'Choose Text or Email to share the YFC website.';};$('closeShare').onclick=()=>shareDialog.close();
$('shareText').onclick=e=>{if(!currentSharingOptions().text){e.preventDefault();return;}if(!isMobileView()){e.preventDefault();shareDialog.close();textAppDialog.showModal();}};
$('shareEmail').onclick=e=>{if(!currentSharingOptions().email){e.preventDefault();return;}if(!isMobileView()){e.preventDefault();shareDialog.close();shareEmailDialog.showModal();}};
$('shareNative').onclick=async()=>{if(!currentSharingOptions().native)return;try{await navigator.share({title:'Mississippi Gulf Coast Youth for Christ',text:'Share YFC with Someone',url:shareUrl});shareDialog.close();}catch(e){if(e.name!=='AbortError')$('shareResult').textContent='Sharing was unavailable. Please use text or email.';}};
loadSharingSettings();

window.addEventListener("hashchange",()=>{if(["#login","#settings"].includes(location.hash))boot();});

// Only deliberate user interaction extends an active session across midnight.
let lastActivitySent=0;
function reportActivity(event){if(!event.isTrusted||!user||Date.now()-lastActivitySent<30000)return;lastActivitySent=Date.now();api('account/activity',{}).catch(()=>{});}
for(const type of ['pointerdown','pointermove','keydown','input','touchstart','scroll'])document.addEventListener(type,reportActivity,{passive:true,capture:true});
setInterval(()=>{if(user)api('account/landing').catch(()=>{});},30000);

const receiptDivider=document.createElement('hr');$('receipts').querySelector('h1').after(receiptDivider);
const receiptActions=document.createElement('div');receiptActions.className='receiptHomeActions';const receiptArt=document.querySelector('.receipt-icon').cloneNode(true);receiptArt.removeAttribute('id');receiptActions.append(receiptArt,$('openReceiptUpload'));const receiptBar=document.createElement('span');receiptBar.className='receiptActionDivider';receiptBar.textContent='|';receiptBar.setAttribute('aria-hidden','true');const myReceipts=document.createElement('button');myReceipts.id='viewMyReceipts';myReceipts.textContent='View My Receipts';myReceipts.type='button';myReceipts.onclick=()=>openReceiptHistory(false);receiptActions.append(receiptBar,myReceipts);$('receipts').append(receiptActions);
const receiptHistory=document.createElement('section');receiptHistory.id='receiptHistory';receiptHistory.hidden=true;receiptHistory.innerHTML='<h1 id="receiptHistoryTitle">My Receipts</h1><form id="receiptHistoryFilters" class="panel grid"><label>Search filename, category or uploader<input id="receiptHistorySearch" type="search" maxlength="200"></label><label>From date<input id="receiptHistoryFrom" type="date"></label><label>Through date<input id="receiptHistoryTo" type="date"></label><label>Category<select id="receiptHistoryCategory"><option value="">All categories</option></select></label><label id="receiptScopeLabel">Receipts<select id="receiptHistoryScope"><option value="mine">My receipts</option><option value="all">All users’ receipts</option></select></label><button type="submit">Search receipts</button></form><p id="receiptHistorySummary" role="status"></p><div id="receiptHistoryResults"></div><div class="receiptHistoryPaging"><button id="receiptHistoryPrevious" type="button">Previous</button><button id="receiptHistoryNext" type="button">Next</button><button id="receiptHistoryPrint" type="button">Print receipt report</button><button id="receiptHistoryBack" type="button">Return to Receipts &amp; Accounting</button></div>';$('receipts').after(receiptHistory);
let receiptHistoryOffset=0,receiptHistoryRequest=0;
async function openReceiptHistory(report){if(!user)return;storeSection('receipts');$('receipts').hidden=true;receiptHistory.hidden=false;$('receiptUpload').hidden=true;$('receiptHistoryTitle').textContent=report?'Receipt Reports':'My Receipts';setSectionHeader(report?'Receipt Reports':'My Receipts','receipts');$('receiptHistoryScope').value=report&&can('view_all_receipts')?'all':'mine';receiptHistoryOffset=0;try{const r=await api('receipt-categories');const select=$('receiptHistoryCategory'),value=select.value;select.replaceChildren(new Option('All categories',''));for(const code of r.categories)select.add(new Option(code,code));select.value=value;await loadReceiptHistory();}catch(e){$('receiptHistorySummary').textContent=e.message;}}
async function loadReceiptHistory(){const request=++receiptHistoryRequest;const query=new URLSearchParams({scope:$('receiptHistoryScope').value,search:$('receiptHistorySearch').value,from:$('receiptHistoryFrom').value,to:$('receiptHistoryTo').value,category:$('receiptHistoryCategory').value,offset:String(receiptHistoryOffset)});try{const r=await api('receipts?'+query);if(request!==receiptHistoryRequest)return;$('receiptScopeLabel').hidden=!r.can_view_all;$('receiptHistorySummary').textContent=r.total+' receipt(s) found'+(r.total?' · Showing '+(r.offset+1)+'–'+(r.offset+r.receipts.length):'');$('receiptHistoryResults').innerHTML=r.receipts.map(row=>'<article class="panel receiptRecord"><h2>'+esc(row.filename)+'</h2><p>'+esc(new Date(row.at*1000).toLocaleString())+' · '+esc(row.category)+' · '+(row.guest_assigned?'Assigned by guest to ':'Uploaded by ')+esc(row.actor)+' · Reimbursement: '+(row.reimbursement_required?'Required':'Not required')+'</p><a target="_blank" rel="noopener" href="/api/receipt-file/'+encodeURIComponent(row.id)+'">View receipt</a></article>').join('')||'<p>No receipts match your filters.</p>';$('receiptHistoryPrevious').disabled=r.offset===0;$('receiptHistoryNext').disabled=r.offset+r.receipts.length>=r.total;}catch(e){if(request!==receiptHistoryRequest)return;$('receiptHistorySummary').textContent=e.message;$('receiptHistoryResults').replaceChildren();}}
$('receiptHistoryFilters').onsubmit=e=>{e.preventDefault();receiptHistoryOffset=0;loadReceiptHistory();};$('receiptHistoryPrevious').onclick=()=>{receiptHistoryOffset=Math.max(0,receiptHistoryOffset-100);loadReceiptHistory();};$('receiptHistoryNext').onclick=()=>{receiptHistoryOffset+=100;loadReceiptHistory();};$('receiptHistoryBack').onclick=()=>storeSection('receipts');$('receiptHistoryPrint').onclick=()=>window.print();

const pageColorNames={dispatch:'Thrift Mart Dispatch',paging:'Store Associate Paging',receipts:'Receipts & Accounting',print:'Print with a Purpose',settings:'Settings',signin:'Sign-in Page'};
let pageColors=Object.fromEntries(Object.entries({dispatch:'#b51f2b',paging:'#7a1520',receipts:'#067a06',print:'#073ea6',settings:'#000000',signin:'#ffffff'}).map(([name,header])=>[name,{header,light:'#faf6f5',dark:'#101821'}])),defaultPageColors=null;
function colorInk(hex){const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722>.179?'#111111':'#ffffff';}
function applyPageColors(){const section=document.body.dataset.section,colors=pageColors[section],dark=document.documentElement.dataset.theme==='dark';if(!colors)return;const header=document.querySelector('body>header'),ink=colorInk(colors.header);header.style.backgroundColor=colors.header;header.style.color=ink;for(const id of ['connection','signedInUser','loggedOutStatus'])$(id).style.color=ink;operationsTitle.style.color=ink;$('currentSection').style.color=ink;$('storeMenuButton').style.color=ink;document.documentElement.style.setProperty('--page-background',dark?colors.dark:colors.light);document.documentElement.style.setProperty('--page-text',colorInk(dark?colors.dark:colors.light));document.querySelector('meta[name="theme-color"]').content=colors.header;for(const [name,color]of Object.entries(pageColors)){const button=$(name+'Section');if(button){button.style.backgroundColor=color.header;button.style.color=colorInk(color.header);}}if(section==='signin'){$('loginBrand').style.color=ink;}else $('loginBrand').style.removeProperty('color');}
function populatePageColors(pages){const fields=$('pageColorFields');fields.replaceChildren();for(const [name,colors]of Object.entries(pages)){const field=document.createElement('fieldset'),legend=document.createElement('legend');legend.textContent=pageColorNames[name];field.append(legend);for(const [key,label]of Object.entries({header:'Header / page accent',light:'Page background — light mode',dark:'Page background — dark mode'})){const row=document.createElement('label');row.textContent=label;const picker=document.createElement('input');picker.type='color';picker.name=name+'_'+key;picker.value=colors[key];row.append(picker);field.append(row);}fields.append(field);}}
async function loadPageColors(edit=false){try{const result=await api('page-colors');pageColors=result.pages;defaultPageColors=result.defaults;applyPageColors();if(edit){populatePageColors(pageColors);$('pageColorStatus').textContent='';}}catch(e){if(edit)$('pageColorStatus').textContent=e.message;}}
$('pageColorForm').onsubmit=async e=>{e.preventDefault();const pages=Object.fromEntries(Object.keys(pageColorNames).map(name=>[name,Object.fromEntries(['header','light','dark'].map(key=>[key,e.target.elements[name+'_'+key].value]))]));try{const result=await api('page-colors',{pages});pageColors=result.pages;defaultPageColors=result.defaults;applyPageColors();$('pageColorStatus').textContent='Page colors saved for everyone.';}catch(err){$('pageColorStatus').textContent=err.message;}};
$('resetPageColors').onclick=()=>{if(defaultPageColors){populatePageColors(defaultPageColors);$('pageColorStatus').textContent='Default colors loaded. Select Save page colors to apply them.';}};
new MutationObserver(applyPageColors).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
applyPageColors();loadPageColors();setInterval(()=>loadPageColors(),60000);

const employeeRoleLabel=document.createElement('label');employeeRoleLabel.innerHTML='Role<select id="employeeRole"><option value="">Individual permissions (existing)</option></select>';const employeeRole=employeeRoleLabel.querySelector('select');$('permissionFields').prepend(employeeRoleLabel);let employeeHadRole=false,employeeRolesData=null,employeeIndividualGrants={};
function populateEmployeeRole(name,data){employeeRolesData=data;employeeHadRole=!!data.assignments[name];employeeRole.replaceChildren(new Option('Individual permissions (existing)',''));for(const role of data.roles)employeeRole.add(new Option(role.name,String(role.id)));employeeRole.value=employeeHadRole?String(data.assignments[name]):'';employeeRole.disabled=!!state.users.find(person=>person.name===name)?.admin;}
function setEmployeeRoleMode(){
 const role=employeeRolesData?.roles.find(item=>String(item.id)===employeeRole.value),admin=!!state.users.find(p=>p.name===$('passwordUser').value)?.admin;
 $('userRoleSummary').textContent=admin?'Administrator · full access. Roles apply to employee accounts.':role?`${role.name} · ${Object.values(role.grants).filter(Boolean).length} enabled permissions. Changes to this role apply to every assigned user.`:'Individual access · existing permissions are retained. Choose a shared role to simplify management.';
 $('editIndividualAccess').hidden=!!role||admin||!user.admin;
 $('manageUserRole').hidden=!can('manage_roles');renderUserAccessPreview(role?.grants||employeeIndividualGrants,admin);
}
employeeRole.onchange=setEmployeeRoleMode;
const openRoles=document.createElement('button');openRoles.id='openRoles';openRoles.type='button';openRoles.textContent='Roles';settingsPanels[4].append(openRoles);
const rolesArea=document.createElement('section');rolesArea.id='rolesArea';rolesArea.hidden=true;rolesArea.innerHTML='<h2>Permission Roles</h2><p>Assign a role to use one permission set for an employee. Existing individual permissions remain available when a role is removed. Role changes apply to all assigned employees.</p><label>Choose a role<select id="roleSelect"><option value="">Create a new role</option></select></label><form id="roleForm"><label>Role name<input id="roleName" maxlength="80" required></label><nav id="roleCategories" class="settingsTabs" aria-label="Role permission categories"></nav><div id="rolePermissions"></div><button type="submit">Save role</button></form><p id="roleStatus" role="status"></p>';settingsPanels[4].append(rolesArea);
let rolesData=null;
function showRole(){
 const selected=rolesData.roles.find(role=>String(role.id)===$('roleSelect').value);$('roleName').value=selected?selected.name:'';
 const count=selected?Object.values(rolesData.assignments).filter(id=>id===selected.id).length:0;
 $('roleAssignmentCount').textContent=selected?`${count} assigned user${count===1?'':'s'}. Saving changes updates access for all of them.`:'Create a reusable permission set, then assign it in a user’s Role tab.';
 buildPermissionEditor($('rolePermissions'),$('roleCategories'),rolesData.permissions,rolesData.groups,selected?.grants||{},'roleGrant',key=>!user.admin&&!rolesData.grantable.includes(key));
 selectRoleEditorTab('properties');$('roleStatus').textContent='';
}
let rolesLoadVersion=0;
async function loadRoles(selected=''){
 const version=++rolesLoadVersion, signedIn=user;
 const select=$('roleSelect'), fields=[$('roleName'),select,$('roleForm').querySelector('button[type=submit]')];
 for(const field of fields)field.disabled=true;
 $('roleCategories').replaceChildren();$('rolePermissions').replaceChildren();
 $('roleStatus').textContent='Loading roles…';
 try{
  const data=await api('roles');
  if(version!==rolesLoadVersion||signedIn!==user)return;
  rolesData=data;select.replaceChildren(new Option('Create a new role',''));
  for(const role of data.roles)select.add(new Option(role.name,String(role.id)));
  select.value=String(selected);showRole();
  for(const field of fields)field.disabled=false;
 }catch(e){if(version===rolesLoadVersion&&signedIn===user)$('roleStatus').textContent=e.message;}
}
const userSettingsTabs=document.createElement('nav');userSettingsTabs.className='settingsTabs userSettingsTabs';
userSettingsTabs.setAttribute('aria-label','Manage users and roles');
const userSettingsPanel=document.createElement('section');userSettingsPanel.id='userSettingsPanel';
const usersSettingsButton=document.createElement('button');usersSettingsButton.type='button';usersSettingsButton.id='openUsers';usersSettingsButton.textContent='Users';
const userSettingsHeading=document.createElement('h2');userSettingsHeading.textContent='Users';
for(const node of [...settingsPanels[4].childNodes])if(node!==openRoles&&node!==rolesArea)userSettingsPanel.append(node);
const heading=userSettingsPanel.querySelector('h2');if(heading)heading.textContent='Users';else userSettingsPanel.prepend(userSettingsHeading);
userSettingsTabs.append(usersSettingsButton,openRoles);
settingsPanels[4].prepend(userSettingsTabs,userSettingsPanel);
function renderUserList(){
 const edit=can('manage_users')||can('reset_passwords')||can('rename_users')||can('manage_staff_schedule');
 $('users').innerHTML=state.users.map(person=>{
  const name=esc(person.name);
  const pin=can('reset_passwords')&&(!person.admin||user.admin);
  const rename=can('rename_users')&&(!person.admin||user.admin);
  return `<div class="listRow"><span>${name}${person.admin?' · Administrator':''}</span>
   <span>${rename?`<button type="button" data-user-identity="${name}">Employee Profile</button>`:''}
   ${can('manage_staff_schedule')?`<button type="button" data-work-assignment="${name}">Work assignments</button>`:''}
   ${pin?`<button type="button" data-clock-pin="${name}">Time Clock PIN</button>`:''}
   ${edit?`<button type="button" data-password="${name}">Edit user</button>`:''}</span></div>`;
 }).join('');
}
async function loadUserList(){
 const signedIn=user;
 const {users}=await api('admin/users');
 if(user===signedIn){state.users=users;renderUserList();}
}
const addUserStatus=document.createElement('dialog');
addUserStatus.id='addUserStatus';
addUserStatus.setAttribute('aria-labelledby','addUserTitle');
addUserStatus.setAttribute('aria-describedby','addUserMessage');
addUserStatus.innerHTML=`<h2 id="addUserTitle" tabindex="-1" autofocus>Add user</h2>
 <p id="addUserMessage" role="status"></p>
 <progress id="addUserProgress" aria-label="Adding user"></progress>
 <form method="dialog" class="actions"><button id="addUserDone" class="primary">Done</button></form>`;
document.body.append(addUserStatus);
addUserStatus.addEventListener('cancel',e=>{if($('addUserDone').disabled)e.preventDefault();});
addUserStatus.addEventListener('close',()=>{
 if(!serverOnline)setServerConnection(false);
});
$('userForm').onsubmit=async e=>{
 e.preventDefault();
 if(addUserStatus.open)return;
 const form=e.currentTarget,submit=form.querySelector('button');
 const data=Object.fromEntries(new FormData(form));
 const message=$('addUserMessage'),progress=$('addUserProgress'),done=$('addUserDone');
 submit.disabled=true;
 done.disabled=true;
 progress.hidden=false;
 message.textContent='Adding user…';
 addUserStatus.showModal();
 try{
  await api('user',data);
  form.reset();
  message.textContent='User added. Refreshing the Users list…';
  message.textContent=await loadUserList().then(
   ()=>'User added successfully.',
   ()=>'User added successfully. Reopen Users to refresh the list.'
  );
 }catch(err){
  message.textContent=err.status?err.message:
   'The app could not confirm whether the user was added. Check the Users list before trying again.';
 }finally{
  progress.hidden=true;
  done.disabled=false;
  submit.disabled=false;
  done.focus();
 }
};
const renameUserDialog=document.createElement('dialog');
renameUserDialog.innerHTML='<form id="renameUserForm"><h2>Edit display name</h2><label>Display name<input id="renameUserName" maxlength="80" required></label><p id="renameUserError" role="alert"></p><div class="actions"><button type="button" id="renameUserCancel">Cancel</button><button class="primary">Save name</button></div></form>';
document.body.append(renameUserDialog);
let renameUserTarget;
function openRenameUser(name){
 renameUserTarget=name;
 $('renameUserName').value=renameUserTarget;
 $('renameUserError').textContent='';
 renameUserDialog.showModal();
}
$('renameUserCancel').onclick=()=>renameUserDialog.close();
$('renameUserForm').onsubmit=async e=>{
 e.preventDefault();
 const submit=e.submitter,signedIn=user;
 submit.disabled=true;
 $('renameUserError').textContent='';
 try{
  const result=await api('admin/rename-user',{name:renameUserTarget,new_name:$('renameUserName').value});
  if(!user||user!==signedIn)return;
  user.name=result.signed_in_name;
  $('signedInUser').textContent='Signed in as '+user.name;
  renameUserDialog.close();
  toast('User name updated.');
  if(can('view_schedule'))await refresh();else await loadUserList();
 }catch(err){
  if(renameUserDialog.open)$('renameUserError').textContent=err.message;else toast(err.message);
 }finally{submit.disabled=false;}
};

function selectUserSettings(target){
 const usersAllowed=can('manage_users')||can('reset_passwords')||can('rename_users')||can('manage_staff_schedule'),rolesAllowed=can('manage_roles');
 const roles=rolesAllowed&&(target==='roles'||!usersAllowed);
 usersSettingsButton.hidden=!usersAllowed;openRoles.hidden=!rolesAllowed;
 userSettingsPanel.hidden=roles||!usersAllowed;rolesArea.hidden=!roles;
 for(const [button,selected] of [[usersSettingsButton,!roles],[openRoles,roles]]){
  button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));
 }
 if(roles)loadRoles();
 else if(usersAllowed){
  $('userForm').hidden=!can('manage_users');
  loadUserList().catch(e=>toast(e.message));
 }
}
usersSettingsButton.onclick=()=>selectUserSettings('users');openRoles.onclick=()=>selectUserSettings('roles');$('roleSelect').onchange=showRole;
$('roleForm').onsubmit=async e=>{e.preventDefault();const button=$('roleForm').querySelector('[type=submit]');if(button.disabled||!rolesData)return;button.disabled=true;const grants=Object.fromEntries([...$('rolePermissions').querySelectorAll('[data-role-grant]')].map(input=>[input.dataset.roleGrant,input.checked]));try{const payload={name:$('roleName').value,grants};if($('roleSelect').value)payload.id=Number($('roleSelect').value);const result=await api('roles',payload);await loadRoles(result.id);$('roleStatus').textContent='Role saved. Assigned users receive its updated permissions.';}catch(err){$('roleStatus').textContent=err.message;button.disabled=false;}};

// Staff communications. Membership and read state are enforced by the server.
const commMenu = document.createElement('button');
commMenu.type = 'button';
commMenu.id = 'commsSection';
commMenu.textContent = 'Communications Hub';
$('chooseStartSection').before(commMenu);
const commAlert = document.createElement('button');
commAlert.type = 'button';
commAlert.id = 'commAlert';
commAlert.hidden = true;
commAlert.setAttribute('aria-live', 'polite');
const commPanel = document.createElement('section');
commPanel.id = 'comms';
commPanel.hidden = true;
commPanel.innerHTML = `
 <div class="commLayout">
  <aside class="commSidebar" aria-label="Communications">
   <div class="commSidebarHead"><h2>ComHub</h2><button type="button" id="commPreferences" aria-label="Preferences" title="Preferences">⚙</button><button class="primary" type="button" id="commNew" aria-label="New message" title="New message">✎</button></div>
   <div class="commLinks">
    <button type="button" data-comm-view="files">Files</button>
    <button type="button" data-comm-view="saved">Saved messages</button>
    <button type="button" data-comm-view="team">Team</button>
   </div>
   <div class="commLists"><h3>Groups</h3><button type="button" id="commGroup">＋ Create group</button><div id="commGroups"></div><button type="button" id="commHiddenGroups" hidden>Hidden groups</button>
   <h3>Direct messages</h3><div id="commDirect"></div></div>
  </aside>
  <div class="commWorkspace">
   <div class="commHeading"><button type="button" id="commBack">‹ Conversations</button><h2 id="commTitle">Communications Hub</h2><p id="commMembers" class="muted"></p></div>
   <p id="commError" role="status" hidden></p>
   <div id="commContent"></div>
   <form id="commComposer" hidden>
    <label class="commComposeLabel" for="commText">Message</label>
    <textarea id="commText" rows="2" maxlength="5000" placeholder="Write a message…"></textarea>
    <div class="commComposerActions"><label for="commFile">Attach a file (up to 3 MB)</label><input id="commFile" type="file"><button type="submit" class="primary">Send</button></div>
   </form>
  </div>
 </div>
 <dialog id="commPrefsDialog"><form id="commPrefsForm">
  <h2>Preferences</h2>
  <label class="commCheck"><input type="checkbox" name="direct"> Allow people to send me direct messages</label>
  <label>Conversation order<select name="order"><option value="recent">Recent messages first</option><option value="unread">Unread messages first</option></select></label>
  <label>Direct messages<select name="dm"><option value="all">Show all</option><option value="unread">Unread only</option></select></label>
  <label>Group messages<select name="group"><option value="all">Show all</option><option value="unread">Unread only</option></select></label>
  <label class="commCheck"><input type="checkbox" name="alerts"> Show new message alerts</label>
  <label class="commCheck" id="commMobilePushOption" hidden><input type="checkbox" id="commMobilePush" checked> Mobile notifications on this device</label>
  <button type="button" id="commBrowserAlerts" hidden>Enable notifications on this device</button>
  <p id="commDeviceStatus" class="muted" role="status">Check whether this device supports push notifications.</p>
  <div class="actions"><button type="button" id="commPrefsCancel">Cancel</button><button class="primary">Done</button></div>
 </form></dialog>`;
const commPushWelcome = document.createElement('section');
commPushWelcome.id = 'commPushWelcome';
commPushWelcome.hidden = true;
commPushWelcome.className = 'card';
commPushWelcome.setAttribute('aria-label','Set up mobile notifications');
commPushWelcome.innerHTML = '<h2>Mobile notifications</h2><p id="commPushWelcomeStatus" role="status"></p><div class="actions"><button type="button" id="commPushLater">Not now</button><button type="button" class="primary" id="commPushAllow">Allow notifications</button></div>';
document.querySelector('main').prepend(commAlert, commPushWelcome, commPanel);

const commApi = (path, data) => api('comms/' + path, data);
const commEmpty = () => ({threads: [], team: [], preferences: {}, account: ''});
let commInbox = commEmpty(), commUnread = new Map(), commView = '', commThread = 0;
let commRows = [], commOlder = false, commVersion = 0, commPollBusy = false;
let commSession = null, commHighWater = null, commAlertThread = 0, commAlertTimer;

function commError(message = '') {
 $('commError').textContent = message;
 $('commError').hidden = !message;
}
function commReset() {
 commVersion++;
 commView = ''; commThread = 0; commRows = []; commInbox = commEmpty(); commUnread = new Map();
 commHighWater = null; commAlertThread = 0; clearTimeout(commAlertTimer);
 commPushRevision++;
 commPushRegistration = commPushConfig = commPushDevice = null;
 commPushWelcome.hidden = true;
 commAlert.hidden = true; commMenu.textContent = 'Communications Hub';
 $('storeMenuButton').classList.remove('commHasUnread');
 $('commContent').replaceChildren(); $('commComposer').reset(); $('commPrefsDialog').close();
 commPanel.hidden = true;
}
function commBadge() {
 const count = [...commUnread.values()].reduce((sum, row) => sum + row.unread, 0);
 commMenu.textContent = 'Communications Hub' + (count ? ` (${count} unread)` : '');
 $('storeMenuButton').classList.toggle('commHasUnread', count > 0);
 if (!commPanel.hidden) commSidebar();
}
function commSidebar() {
 const {threads, preferences} = commInbox;
 $('commGroup').hidden = !commInbox.manage_groups;
 $('commHiddenGroups').hidden = !threads.some(t=>t.kind==='group'&&t.hidden);
 for (const [kind, list] of [['dm', 'commDirect'], ['group', 'commGroups']]) {
  const items = threads.filter(t => !t.hidden && t.kind === kind && (preferences[kind] !== 'unread' || commUnread.has(t.id) || t.id === commThread));
  if (preferences.order === 'unread') items.sort((a,b) => Number(commUnread.has(b.id)) - Number(commUnread.has(a.id)));
  const focused = document.activeElement?.dataset.commThread;
  $(list).innerHTML = items.map(t => `<button type="button" data-comm-thread="${t.id}" aria-pressed="${t.id===commThread}"><span>${esc(t.title)}</span>${commUnread.has(t.id) ? `<strong class="commBadge" aria-label="Unread messages">${commUnread.get(t.id).unread}</strong>` : ''}</button>`).join('') || '<p class="muted">No conversations to show.</p>';
  if (focused) $(list).querySelector(`[data-comm-thread="${Number(focused)}"]`)?.focus({preventScroll:true});
 }
 for (const b of commPanel.querySelectorAll('[data-comm-view]')) b.setAttribute('aria-pressed', String(b.dataset.commView === commView));
}
function commScreen(view, title, id = 0) {
 commVersion++; commView = view; commThread = id; commRows = []; commOlder = false;
 commPanel.dataset.view = view;
 $('commTitle').textContent = title; $('commMembers').textContent = '';
 $('commContent').replaceChildren(); $('commComposer').reset();
 $('commComposer').hidden = view !== 'thread';
 commError(); commSidebar();
 return commVersion;
}
async function commLoadInbox() {
 const signedIn = user;
 const data = await commApi('inbox');
 if (signedIn !== user || commPanel.hidden) return false;
 commInbox = data; commSidebar(); return true;
}
function commMessage(m, list = false) {
 const thread = commInbox.threads.find(t => t.id === m.thread);
 const title = thread?.hidden ? '' : thread?.title;
 return `<article class="commMessage${m.author === commInbox.account ? ' mine' : ''}">
  <div class="commMessageHead">${commAvatar(m.author,m.sender,m.photo)}<strong>${esc(m.sender)}</strong><time datetime="${new Date(m.sent*1000).toISOString()}">${esc(new Date(m.sent*1000).toLocaleString([], {dateStyle:'medium',timeStyle:'short'}))}</time>
  <button type="button" data-comm-save="${m.id}" aria-pressed="${!!m.saved}">${m.saved ? 'Unsave' : 'Save'}</button>
  ${thread?.kind==='dm' ? `<button type="button" data-comm-delete="${m.id}">Delete for me</button>` : ''}</div>
  ${list && title ? `<button type="button" class="commJump" data-comm-thread="${m.thread}">${esc(title)}</button>` : ''}
  ${m.text ? `<p>${esc(m.text)}</p>` : ''}
  ${m.filename ? `<a href="/api/comms/file/${m.id}" download="${esc(m.filename)}">${esc(m.filename)}</a>` : ''}</article>`;
}
function commRenderThread(scroll = false) {
 const body = $('commContent'), y = body.scrollTop, h = body.scrollHeight;
 const atBottom = h - body.clientHeight - y < 70;
 body.innerHTML = (commOlder ? '<button type="button" id="commOlder">Load earlier messages</button>' : '') +
  (commRows.map(m => commMessage(m)).join('') || '<p class="commEmpty">Start the conversation by sending a message.</p>');
 body.scrollTop = scroll || atBottom ? body.scrollHeight : y;
}
async function commRead(version) {
 const id = commRows.at(-1)?.id, thread = commThread;
 if (version !== commVersion || !id || document.hidden || !commUnread.has(thread)) return;
 await commApi('read', {thread, id});
 if (version === commVersion && commUnread.get(thread)?.latest <= id) {
  commUnread.delete(thread); commBadge();
 }
}
async function commLoadMessages(version, before = 0) {
 const thread = commThread;
 const data = await commApi('messages?thread=' + thread + (before ? '&before=' + before : ''));
 if (version !== commVersion) return;
 const oldHeight = $('commContent').scrollHeight;
 if (before) {
  commRows = [...data.messages, ...commRows];
  commOlder = data.older;
 } else {
  const first = data.messages[0]?.id;
  const earlier = commRows.filter(m => m.id < first);
  commRows = [...earlier, ...data.messages];
  if (!earlier.length) commOlder = data.older;
 }
 commRenderThread(!before && !oldHeight);
 if (before) $('commContent').scrollTop += $('commContent').scrollHeight - oldHeight;
 await commRead(version);
}
async function commOpenThread(id) {
 const thread = commInbox.threads.find(t => t.id === id);
 if (!thread || thread.hidden) return;
 const version = commScreen('thread', thread.title, id);
 $('commMembers').textContent = thread.kind === 'group' ? ['You', ...thread.members].join(', ') : 'Direct message';
 if(thread.kind==='group'){
  const controls=document.createElement('span');
  controls.className='commGroupControls';
  controls.innerHTML=`<button type="button" data-comm-hide-group="${id}">Hide group</button>${commInbox.manage_groups?'<button type="button" id="commManageGroup">Manage group</button>':''}`;
  $('commMembers').append(controls);
 }
 $('commTitle').tabIndex = -1; $('commTitle').focus({preventScroll:true});
 try { await commLoadMessages(version); } catch (e) { if (version === commVersion) commError(e.message); }
}
function commTeam(mode, group = null) {
 const isGroup = mode === 'group', isTeam = mode === 'team';
 if(isGroup&&!commInbox.manage_groups)return;
 commScreen(mode, isGroup ? (group?'Manage group':'Create group') : isTeam ? 'Team directory' : 'New message');
 $('commContent').innerHTML = `<div class="commDirectory">
  ${isGroup ? '<label>Group name<input id="commGroupName" maxlength="80" placeholder="e.g. Volunteer coordinators"></label>' : ''}
  <label>${isGroup ? 'Find members' : 'Search team members'}<input id="commSearch" type="search" placeholder="Search by name"></label>
  <div id="commPeople"></div>
  ${isGroup ? '<button class="primary" type="button" id="commCreateGroup">Create group</button>' : ''}
 </div>`;
 const chosen = new Set(group?.member_ids ?? []), search = $('commSearch');
 const action=group?'Save group':'Create group';
 if(group)$('commGroupName').value=group.title;
 function render() {
  const matches = commInbox.team.filter(p => p.name.toLowerCase().includes(search.value.trim().toLowerCase()));
  $('commPeople').innerHTML = matches.map(p => {
   const label = `${commAvatar(p.id,p.name,p.photo)}<span>${esc(p.name)}</span>`;
   return isGroup ? `<label class="commPerson"><input type="checkbox" value="${esc(p.id)}" ${chosen.has(p.id) ? 'checked' : ''}>${label}</label>`
    : `<button type="button" class="commPerson" data-comm-person="${esc(p.id)}">${label}</button>`;
  }).join('') || '<p class="commEmpty">No team members found.</p>';
  if (isGroup) $('commCreateGroup').textContent = `${action}${chosen.size ? ' (' + chosen.size + ' selected)' : ''}`;
 }
 search.oninput = render; render();
 $('commPeople').onchange = ({target}) => {
  if (target.checked) chosen.add(target.value); else chosen.delete(target.value);
  $('commCreateGroup').textContent = `${action}${chosen.size ? ' (' + chosen.size + ' selected)' : ''}`;
 };
 if (isGroup) $('commCreateGroup').onclick = e => commCreate(e.currentTarget, 'group', [...chosen], $('commGroupName').value, group?.id);
 else $('commPeople').onclick = e => {
  const b = e.target.closest('[data-comm-person]');
  if (b) commCreate(b, 'dm', [b.dataset.commPerson]);
 };
 search.focus();
}
async function commCreate(button, kind, members, title = '', thread) {
 const version = commVersion;
 button.disabled = true; commError();
 try {
  const result = await commApi(thread?'manage-group':'create', {kind, members, title, thread});
  if (version === commVersion && await commLoadInbox() && version === commVersion) await commOpenThread(result.id);
 } catch (e) { if (version === commVersion) commError(e.message); }
 finally { button.disabled = false; }
}
async function commCollection(view) {
 const version = commScreen(view, view === 'files' ? 'Files' : 'Saved messages');
 try {
  const data = await commApi(view);
  if (version === commVersion) $('commContent').innerHTML = data.messages.map(m => commMessage(m, true)).join('') ||
   (view === 'files' ? '<p class="commEmpty">Files shared in your conversations appear here.</p>' : '<p class="commEmpty">Save a message to find it here later.</p>');
 } catch (e) { if (version === commVersion) commError(e.message); }
}
async function commOpen(thread = 0) {
 if (!requireSignIn()) return;
 if (commSession !== user) { commReset(); commSession = user; }
 commAlert.hidden = true;
 storeSection('dispatch'); $('app').hidden = true;
 setSectionHeader('Communications Hub', 'comms');
 commPanel.hidden = false;
 const version = commScreen('home', 'Communications Hub');
 $('commContent').innerHTML = '<p class="commEmpty">Choose a conversation or start a new message.</p>';
 try { if (await commLoadInbox() && thread && version === commVersion) await commOpenThread(thread); }
 catch (e) { if (version === commVersion) commError(e.message); }
}
commMenu.onclick = () => commOpen();
commAlert.onclick = () => commOpen(commAlertThread);
$('commBack').onclick = () => commScreen('home', 'Communications Hub');
$('commNew').onclick = () => commTeam('new');
$('commGroup').onclick = () => commTeam('group');
function commShowHiddenGroups(){
 commScreen('hidden-groups','Hidden groups');
 $('commContent').innerHTML=commInbox.threads.filter(t=>t.kind==='group'&&t.hidden)
  .map(t=>`<article class="commMessage"><strong>${esc(t.title)}</strong> <button type="button" data-comm-restore-group="${t.id}">Restore group</button></article>`)
  .join('')||'<p class="commEmpty">No hidden groups.</p>';
}
$('commHiddenGroups').onclick=commShowHiddenGroups;
commPanel.addEventListener('click', async e => {
 const button = e.target.closest('button');
 if (!button) return;
 const {commView: view, commThread: thread, commSave: save} = button.dataset, version = commVersion;
 if (thread) return commOpenThread(Number(thread));
 if (view) return view === 'team' ? commTeam(view) : commCollection(view);
 try {
  if(button.id==='commManageGroup'){
   const group=commInbox.threads.find(t=>t.id===commThread);
   if(group)commTeam('group',group);
   return;
  }
  const {commDelete,commHideGroup,commRestoreGroup}=button.dataset;
  if(commDelete){
   if(!confirm('Delete this direct message from your view?'))return;
   button.disabled=true;
   const id=Number(commDelete);
   await commApi('delete-message',{id});
   if(version!==commVersion)return;
   if(commView==='thread'){commRows=commRows.filter(m=>m.id!==id);commRenderThread();}
   else await commCollection(commView);
   return;
  }
  if(commHideGroup||commRestoreGroup){
   button.disabled=true;
   const id=Number(commHideGroup||commRestoreGroup);
   await commApi('hide-group',{thread:id,hidden:!!commHideGroup});
   if(version!==commVersion)return;
   if(commHideGroup)commUnread.delete(id);
   if(await commLoadInbox()&&version===commVersion){
    if(commHideGroup)commScreen('home','Communications Hub');
    else await commOpenThread(id);
    commBadge();
   }
   return;
  }
  if (button.id === 'commOlder') { button.disabled = true; await commLoadMessages(version, commRows[0]?.id); }
  if (save) {
   button.disabled = true;
   const saving = button.getAttribute('aria-pressed') !== 'true';
   await commApi('save', {id: Number(save), save: saving});
   if (version !== commVersion) return;
   if (commView === 'saved' || commView === 'files') await commCollection(commView);
   else {
    const row = commRows.find(m => m.id === Number(save));
    if (row) row.saved = saving;
    button.textContent = saving ? 'Unsave' : 'Save';
    button.setAttribute('aria-pressed', String(saving));
   }
  }
 } catch (err) { if (version === commVersion) commError(err.message); }
 finally { button.disabled = false; }
});
$('commComposer').onsubmit = async e => {
 e.preventDefault();
 const version = commVersion, thread = commThread, button = e.submitter;
 const text = $('commText').value, file = $('commFile').files[0];
 if (!text.trim() && !file) return commError('Write a message or choose a file.');
 if (file && (file.size > 3000000 || !file.size)) return commError('Choose a nonempty file of 3 MB or smaller.');
 button.disabled = true; commError();
 try {
  const data = {thread, text};
  if (file) {
   data.filename = file.name;
   data.file = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1]);
    reader.onerror = () => reject(Error('Could not read the attachment.'));
    reader.readAsDataURL(file);
   });
  }
  if (version !== commVersion || !user) return;
  await commApi('send', data);
  if (version === commVersion) {
   $('commComposer').reset();
   await commLoadInbox();
   if (version === commVersion) { await commLoadMessages(version); $('commContent').scrollTop = $('commContent').scrollHeight; }
  }
 } catch (err) { if (version === commVersion) commError(err.message); }
 finally { button.disabled = false; }
};

$('commPreferences').onclick = () => {
 const prefs = commInbox.preferences, form = $('commPrefsForm');
 form.elements.direct.checked = prefs.direct ?? true;
 form.elements.alerts.checked = prefs.alerts ?? true;
 for (const [key, value] of Object.entries({order:'recent',dm:'all',group:'all'})) form.elements[key].value = prefs[key] ?? value;
 $('commDeviceStatus').textContent = 'Check whether this device supports push notifications.';
 $('commPrefsDialog').showModal();
 commPreparePush();
};
$('commPrefsCancel').onclick = () => $('commPrefsDialog').close();
let commPushRegistration, commPushConfig, commPushDevice, commPushRevision = 0;
let commPushBusy = false;
const commIsIos = () => /iPhone|iPad|iPod/.test(navigator.userAgent) ||
 (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const commMobileDevice = () => isMobileView() || commIsIos() || /Android/i.test(navigator.userAgent);
const commPushChoice = key => {try {return localStorage.getItem(key);} catch {return null;}};
function commStorePushChoice(key, value) {
 try {localStorage.setItem(key, value);} catch {return;}
}
const commMobilePushOn = () => commPushChoice('yfc-mobile-push') !== 'off';
const commWelcomeSeen = () => commPushChoice('yfc-mobile-push-seen') === 'yes';
$('commPushLater').onclick = () => {
 commStorePushChoice('yfc-mobile-push-seen', 'yes');
 commPushWelcome.hidden = true;
};

function commPushId(create = false) {
 try {
  let id = localStorage.getItem('yfc-push-device');
  if (!id && create) {
   id = crypto.randomUUID().replaceAll('-', '');
   localStorage.setItem('yfc-push-device', id);
  }
  return id;
 } catch {
  return null;
 }
}

function commPushUi(message, action = '', showInstall = false) {
 const button = $('commBrowserAlerts');
 $('commDeviceStatus').textContent = message;
 button.hidden = !action || (commMobileDevice() && action === 'disable');
 button.disabled = button.hidden;
 button.dataset.action = action;
 button.textContent = action === 'disable' ? 'Turn off on this device' : 'Enable notifications on this device';
 const welcome = commMobileDevice() && commMobilePushOn() && !commWelcomeSeen() &&
  (showInstall || (action === 'enable' && window.Notification?.permission !== 'denied'));
 commPushWelcome.hidden = !welcome;
 $('commPushWelcomeStatus').textContent = showInstall ? message :
  'Allow this device to notify you when you receive a new message.';
 $('commPushAllow').hidden = showInstall;
}

async function commPreparePush() {
 if (commPushBusy || !user) return;
 const revision = ++commPushRevision, signedIn = user;
 const mobile = commMobileDevice(), mobileToggle = $('commMobilePush');
 $('commMobilePushOption').hidden = !mobile;
 mobileToggle.checked = commMobilePushOn();
 commPushUi('Checking notification support…');
 if (mobile && !mobileToggle.checked) {
  commPushUi('Mobile notifications are off on this device.');
  return;
 }
 if (commIsIos() && !navigator.standalone && !matchMedia('(display-mode: standalone)').matches) {
  commPushUi('On iPhone or iPad, add YFC Operations to your Home Screen, then open it from there to enable notifications.', '', true);
  return;
 }
 if (!window.isSecureContext || !('serviceWorker' in navigator) || !('PushManager' in window)) {
  commPushUi('Use the secure HTTPS address in a browser that supports push notifications. In-app alerts still work.');
  return;
 }
 try {
  const device = commPushId(true);
  if (!device) {
   commPushUi('This browser could not save the device setting. In-app alerts still work.');
   return;
  }
  const config = await commApi('push?device=' + device);
  if (revision !== commPushRevision || signedIn !== user) return;
  if (!config.available) {
   commPushUi(config.reason === 'runtime'
    ? 'The server needs the full YFC Operations installer with push support. In-app alerts still work.'
    : 'Use the secure HTTPS address to enable device notifications.');
   return;
  }
  await navigator.serviceWorker.register('/push-worker.js');
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (revision !== commPushRevision || signedIn !== user) return;
  commPushDevice = device;
  commPushConfig = config;
  commPushRegistration = registration;
  if (config.enabled && subscription && Notification.permission === 'granted') {
   commPushUi('Notifications are enabled on this device. Turn on new message alerts above to receive them.', 'disable');
  } else if (Notification.permission === 'denied') {
   commPushUi('Notifications are blocked. Allow them in your browser or device settings.', config.enabled ? 'disable' : '');
  } else {
   commPushUi('Get a system notification for new messages, including while YFC Operations is closed.', 'enable');
  }
 } catch {
  if (revision === commPushRevision && signedIn === user) commPushUi('Device notifications could not be set up. In-app alerts still work.');
 }
}

async function commChangePush(enabled) {
 const signedIn = user, revision = commPushRevision;
 if (commPushBusy || !signedIn || !commPushRegistration || !commPushConfig || !commPushDevice) return;
 commPushBusy = true;
 const button = $('commBrowserAlerts');
 $('commPushAllow').disabled = true;
 $('commPushLater').disabled = true;
 $('commMobilePush').disabled = true;
 const registration = commPushRegistration, device = commPushDevice, config = commPushConfig;
 button.disabled = true;
 try {
  if (!enabled) {
   await commApi('push', {device, enabled:false});
   const subscription = await registration.pushManager.getSubscription();
   if (subscription) await subscription.unsubscribe();
  } else {
   const publicKey = config.publicKey.replaceAll('-', '+').replaceAll('_', '/');
   const key = Uint8Array.from(atob(publicKey), char => char.charCodeAt(0));
   // Call subscribe directly from the user's click so iOS can show its permission prompt.
   const subscription = await registration.pushManager.subscribe({userVisibleOnly:true, applicationServerKey:key});
   if (signedIn !== user) return;
   await commApi('push', {device, enabled:true, subscription:subscription.toJSON()});
   commStorePushChoice('yfc-mobile-push-seen', 'yes');
   if (revision === commPushRevision) $('commPrefsForm').elements.alerts.checked = true;
  }
  commPushBusy = false;
  if (revision === commPushRevision && signedIn === user) await commPreparePush();
 } catch (err) {
  if (revision === commPushRevision && signedIn === user) {
   if (err.name === 'InvalidStateError') {
    await commApi('push', {device, enabled:false}).catch(() => {});
    const old = await registration.pushManager.getSubscription().catch(() => null);
    if (old) await old.unsubscribe().catch(() => {});
    if (revision === commPushRevision && signedIn === user)
     commPushUi('This device had an old subscription. Enable notifications again.', 'enable');
   } else if (Notification.permission === 'denied') {
    commStorePushChoice('yfc-mobile-push-seen', 'yes');
    commPushUi('Notifications are blocked. Allow them in your browser or device settings.');
   } else {
    const message = err.message || 'Could not change device notifications. Try again.';
    $('commDeviceStatus').textContent = message;
    $('commPushWelcomeStatus').textContent = message;
    button.disabled = false;
   }
  }
 }
 finally {
  commPushBusy = false;
  $('commPushAllow').disabled = false;
  $('commPushLater').disabled = false;
  $('commMobilePush').disabled = false;
 }
}

$('commBrowserAlerts').onclick = e => commChangePush(e.currentTarget.dataset.action === 'enable');
$('commPushAllow').onclick = () => commChangePush(true);
$('commMobilePush').onchange = async e => {
 const toggle = e.currentTarget, signedIn = user;
 if (!signedIn) return;
 if (toggle.checked) {
  commStorePushChoice('yfc-mobile-push', 'on');
  commStorePushChoice('yfc-mobile-push-seen', 'no');
  await commPreparePush();
  return;
 }
 toggle.disabled = true;
 $('commBrowserAlerts').disabled = true;
 try {
  const device = commPushId();
  if (device) await commApi('push', {device, enabled:false});
  if (signedIn !== user) return;
  commStorePushChoice('yfc-mobile-push', 'off');
  if (commPushRegistration) {
   const subscription = await commPushRegistration.pushManager.getSubscription().catch(() => null);
   if (subscription) await subscription.unsubscribe().catch(() => {});
  }
  await commPreparePush();
 } catch (err) {
  toggle.checked = true;
  $('commDeviceStatus').textContent = err.message;
  $('commBrowserAlerts').disabled = false;
 } finally {toggle.disabled = false;}

};

$('commPrefsForm').onsubmit = async e => {
 e.preventDefault();
 const f = e.target.elements, version = commVersion;
 try {
  const preferences = await commApi('preferences', {direct:f.direct.checked, alerts:f.alerts.checked, order:f.order.value, dm:f.dm.value, group:f.group.value});
  if (version !== commVersion) return;
  commInbox.preferences = preferences; commSidebar(); $('commPrefsDialog').close();
 } catch (err) { if (version === commVersion) $('commDeviceStatus').textContent = err.message; }
};
if ('serviceWorker' in navigator) navigator.serviceWorker.addEventListener('message', event => {
 if (event.data?.type !== 'open-comms') return;
 if (user) {
  $('sectionChooser').close();
  commOpen();
 } else {
  history.replaceState(null, '', location.pathname + location.search + '#comms');
 }
});

function commNotify(thread) {
 commAlertThread = thread; commAlert.textContent = 'New message · Open ComHub'; commAlert.hidden = false;
 clearTimeout(commAlertTimer);
 commAlertTimer = setTimeout(() => commAlert.hidden = true, 12000);

}
async function commPoll() {
 if (commSession !== user) { commReset(); commSession = user; commBadge(); }
 if (!user || commPollBusy) return;
 const signedIn = user;
 commPollBusy = true;
 try {
  const result = await commApi('status');
  if (signedIn !== user) return;
  profileReviewStatus(result);
  const fresh = result.unread.filter(r => commHighWater !== null && r.latest > commHighWater);
  const alert = fresh.filter(r => document.hidden || commPanel.hidden || r.id !== commThread).sort((a,b) => b.latest-a.latest)[0];
  commHighWater = Math.max(commHighWater ?? 0, ...result.unread.map(r => r.latest));
  commUnread = new Map(result.unread.map(r => [r.id, r]));
  if (result.alerts && alert) commNotify(alert.id);
  if (!commPanel.hidden) {
   if (result.unread.some(r => r.latest > (commInbox.threads.find(t => t.id === r.id)?.latest ?? 0))) await commLoadInbox();
   if (commThread && !document.hidden && commUnread.has(commThread)) {
    if (commUnread.get(commThread).latest > (commRows.at(-1)?.id ?? 0)) await commLoadMessages(commVersion);
    else await commRead(commVersion);
   }
  }
  commBadge();
 } catch (err) { if (!commPanel.hidden) commError(err.message); }
 finally { commPollBusy = false; }
}
setInterval(commPoll, 4500);
document.addEventListener('visibilitychange', () => { if (!document.hidden) commPoll(); });

// Staff scheduling and time clock.
const workMenu = document.createElement('button');
workMenu.type = 'button';
workMenu.id = 'workforceSection';
workMenu.textContent = 'Scheduling & Time Clock';
$('commsSection').after(workMenu);
const workPanel = document.createElement('section');
workPanel.id = 'workforce';
workPanel.hidden = true;
workPanel.innerHTML = `
 <div class="workHead"><p class="workKicker">STAFF OPERATIONS</p><h2>Scheduling &amp; Time Clock</h2></div>
 <nav class="workTabs" aria-label="Scheduling and time clock">
  <button type="button" data-work-view="clock">Time Clock</button>
  <details class="workDropdown"><summary>My Timekeeping <span aria-hidden="true">▾</span></summary><div>
   <button type="button" data-work-view="mine">My Schedule</button>
   <button type="button" data-work-view="requests">My Requests</button>
   <button type="button" data-work-view="availability">My Availability</button>
   <button type="button" data-work-view="my-cards">My Timecards</button>
  </div></details>
  <details class="workDropdown" id="workManagerMenu" hidden><summary>Manager Functions <span aria-hidden="true">▾</span></summary><div>
   <button type="button" data-work-view="review" hidden>Review Requests</button>
   <button type="button" data-work-view="time-cards" hidden>Time Cards</button>
   <button type="button" data-work-view="team" hidden>Scheduling</button>
   <button type="button" data-work-view="time-card-audit" hidden>Time Card Audit</button>
   <button type="button" data-work-view="payroll" hidden>Payroll Export</button>
  </div></details>
  <details class="workDropdown" id="workSetupMenu" hidden><summary>Time Clock Setup <span aria-hidden="true">▾</span></summary><div>
   <button type="button" data-work-view="sites" hidden>Work Sites</button>
  </div></details>
 </nav>
 <p id="workStatus" role="status"></p>
 <button id="workQuickBack" type="button" hidden>Back to sign in</button>
 <div id="workWeekControls" class="workWeek" hidden>
  <button type="button" id="workPrev" aria-label="Previous week">‹</button>
  <label>Week of <input type="date" id="workWeekDate"></label>
  <button type="button" id="workNext" aria-label="Next week">›</button>
  <button type="button" id="workThisWeek">This week</button>
 </div>
 <section data-work-panel="clock">
  <h3 id="workClockState">Loading time clock…</h3>
  <div class="workTotals">
   <div><span>Clocked in today</span><strong id="workGross">—</strong></div>
   <div><span>Worked today, excluding breaks</span><strong id="workNet">—</strong></div>
  </div>
  <p id="workGeoStatus"></p>
  <div class="actions" id="workPunches">
   <button type="button" class="primary" data-work-punch="in" hidden>Clock in</button>
   <button type="button" data-work-punch="start_break" hidden>Start break</button>
   <button type="button" class="primary" data-work-punch="end_break" hidden>End break</button>
   <button type="button" data-work-punch="out" hidden>Clock out</button>
  </div>
 </section>
 <section data-work-panel="mine" hidden>
  <h3>My schedule <span id="workMyRange"></span></h3>
  <div class="workTotals workScheduleTotals"><div><span>Scheduled hours</span><strong id="workScheduledHours">—</strong></div><div><span>Total shifts</span><strong id="workScheduledCount">—</strong></div></div>
  <div class="workTotals">
   <div><span>Clocked in this week</span><strong id="workWeekGross">—</strong></div>
   <div><span>Worked this week, excluding breaks</span><strong id="workWeekNet">—</strong></div>
  </div>
  <div id="workMyShifts" class="workList"></div>
 </section>
 <section data-work-panel="team" hidden>
  <div class="workScheduleHeading"><h3>Scheduling</h3><button type="button" id="workCopyWeek">Copy week…</button></div>
  <p class="workLegend">Dashed shifts belong to another job. Pending requests are marked for review.</p>
  <p>Shift dates and times use the server’s local time.</p>
  <div id="workTeamShifts" class="workList"></div>
  <button type="button" id="workAddShift" class="primary">Add shift</button>
  <dialog id="workShiftDialog"><form id="workShiftForm" class="workForm" hidden>
   <h3 id="workShiftTitle">Add shift</h3>
   <label>Employee<select name="account" required></select></label>
   <label>Start<input type="datetime-local" name="start" required></label>
   <label>End<input type="datetime-local" name="end" required></label>
   <label>Job<input name="job" list="workShiftJobs" maxlength="80"></label><datalist id="workShiftJobs"></datalist>
   <label>Location<input name="location" list="workShiftSites" maxlength="100"></label><datalist id="workShiftSites"></datalist>
   <label>Notes<textarea name="notes" maxlength="500" rows="2"></textarea></label>
   <div class="actions"><button type="button" id="workDeleteShift" hidden>Delete shift</button><button type="button" id="workCancelShift">Cancel</button><button type="submit" class="primary">Save shift</button></div>
   <p id="workShiftError" role="alert"></p>
  </form></dialog>
 </section>
 <section data-work-panel="availability" hidden><h3>My availability</h3><p>Approved recurring unavailable periods and pending changes.</p><button type="button" id="workAvailabilityEdit">Request availability change</button><div id="workOwnAvailability" class="workList"></div></section>
 <section data-work-panel="my-cards" hidden><h3>My timecards</h3><div id="workOwnCards" class="workList"></div></section>
 <dialog id="workCopyDialog"><form id="workCopyForm" class="workForm"><h3>Copy shifts to another week</h3><p>Copies shifts starting in the source week, with the same employees, jobs, sites and local times. Existing shifts are kept. If any shift overlaps, nothing is copied.</p><label>Source Sunday<input type="date" name="source" required></label><label>Destination Sunday<input type="date" name="target" required></label><p id="workCopyError" role="alert"></p><div class="actions"><button type="button" id="workCopyCancel">Cancel</button><button class="primary">Copy shifts</button></div></form></dialog>
 <section data-work-panel="requests" hidden>
  <h3>My requests</h3>
  <div class="actions"><button type="button" id="workAvailability">Request availability change</button><button type="button" id="workTimeOff">Request time off</button></div>
  <div id="workMyRequests" class="workList"></div>
 </section>
 <section data-work-panel="review" hidden>
  <h3>Review staff requests</h3>
  <div id="workReviewRequests" class="workList"></div>
 </section>
 <dialog id="workRequestDialog"><form id="workRequestForm" class="workForm">
  <h3 id="workRequestTitle"></h3>
  <div id="workAvailabilityFields">
   <p>List all recurring periods when you cannot work. Once approved, this replaces your previous weekly availability. Leave the list empty to clear recurring restrictions.</p>
   <div id="workAvailabilityBlocks"></div><button type="button" id="workAddBlock">Add unavailable period</button>
  </div>
  <div id="workTimeOffFields" class="workRequestDates">
   <label>First day off<input type="date" name="start"></label>
   <label>Last day off (inclusive)<input type="date" name="end"></label>
   <label>From (optional, single day)<input type="time" name="from_time"></label><label>Until<input type="time" name="until_time"></label>
  </div>
  <label>Note for your administrator<textarea name="notes" maxlength="500" rows="2"></textarea></label>
  <p id="workRequestError" role="alert"></p>
  <div class="actions"><button type="button" id="workRequestCancel">Cancel</button><button class="primary">Submit request</button></div>
 </form></dialog>
 <section data-work-panel="time-cards" hidden>
  <h3>Time cards</h3><p>Clock and break times use the server’s local time. A reason is required for each correction.</p>
  <div id="workTimeCards" class="workList"></div><button type="button" class="primary" id="workAddCard" hidden>Add time card</button>
 </section>
 <section data-work-panel="time-card-audit" hidden>
  <h3>Time card audit</h3><p>Read-only history of time card corrections.</p>
  <div id="workTimeAudit" class="workList"></div>
  <button type="button" id="workAuditOlder" hidden>Load older entries</button>
 </section>
 <dialog id="workCardDialog"><form id="workCardForm" class="workForm">
  <h3 id="workCardTitle">Edit time card</h3><p id="workCardEmployee"></p>
  <label id="workCardPersonLabel" hidden>Employee<select name="account"></select></label>
  <label>Clock in<input type="datetime-local" step="1" name="start" required></label>
  <label>Clock out<input type="datetime-local" step="1" name="end"></label>
  <div id="workCardBreaks"></div><button type="button" id="workCardAddBreak" hidden>Add break</button>
  <label>Reason for correction<textarea name="reason" rows="2" maxlength="500" required></textarea></label>
  <p id="workCardError" role="alert"></p>
  <div class="actions"><button type="button" id="workCardCancel">Cancel</button><button class="primary" id="workCardSave">Save correction</button></div>
 </form></dialog>
 <section data-work-panel="payroll" hidden>
  <h3>QuickBooks Online Payroll</h3>
  <p>Use the dates shown under Pay period in QuickBooks. Export one completed seven-day period for employees on the same QuickBooks pay schedule.</p>
  <form id="workPayrollForm" class="workForm">
   <label>Pay period<select name="period"><option value="sunday">Sunday–Saturday</option><option value="quickbooks">Match QuickBooks pay period</option></select></label>
   <label>Pay period start<input name="start" type="date" min="2000-01-02" max="2100-12-31" step="7" aria-describedby="workPayrollRange" required></label>
   <p id="workPayrollRange" role="status">Choose the Sunday that starts the pay period.</p>
   <p id="workPayrollOvertimeHelp" hidden>Weekly overtime is calculated across the seven days shown. Use that treatment when these dates match the employee’s overtime workweek.</p>
   <label>Weekly overtime threshold (hours)<input name="threshold" type="number" min="1" max="168" step="0.25" value="40" required></label>
   <label>Flag no recorded break at this many hours<input name="break_after" type="number" min="0" max="48" step="0.25" value="5.5" required></label>
   <p>Use 0 to review all worked shifts with no break recorded. A flag does not mean a break was required.</p>
   <label>Recorded breaks<select name="breaks"><option value="exclude" selected>Exclude recorded breaks</option><option value="include">Include recorded breaks</option></select></label>
   <button type="submit" class="primary">Preview hours</button>
  </form>
  <p id="workPayrollStatus" role="status"></p>
  <div id="workPayrollRows"></div>
  <div id="workPayrollActions" hidden>
   <button type="button" id="workPayrollDownload" class="primary">Download QuickBooks CSV</button>
   <button type="button" id="workPayrollPrint">Print / Save as PDF</button>
  </div>
 </section>
 <section data-work-panel="sites" hidden>
  <h3>Work sites and geofencing</h3>
  <p>Assign sites and location requirements per employee in Settings → Users → Work assignments.</p>
  <div id="workSiteList" class="workList"></div>
  <button type="button" id="workAddSite">Add work site</button>
  <form id="workSiteForm" class="workForm" hidden>
   <h3 id="workSiteTitle">Add work site</h3>
   <label>Site name<input name="name" maxlength="80" required></label>
   <label>Street address<input name="address" maxlength="240" placeholder="Street, city, state ZIP"></label>
   <button type="button" id="workFindAddress">Find address</button>
   <div id="workAddressMatches" class="workAddressMatches"></div>
   <p id="workMapStatus" role="status">Enter a U.S. work address or coordinates. Address lookup sends the address to the U.S. Census Geocoder.</p>
   <label>Latitude<input name="latitude" type="number" min="-90" max="90" step="any" required></label>
   <label>Longitude<input name="longitude" type="number" min="-180" max="180" step="any" required></label>
   <div class="workRadius"><label id="workRadiusLabel">Radius (meters)<input name="radius" type="number" min="30" max="2000" step="any" required value="150"></label>
   <label>Radius unit<select name="radius_unit"><option value="m">Meters</option><option value="ft">Feet</option></select></label></div>
   <div id="workMapPanel" hidden>
    <svg id="workSiteMap" viewBox="0 0 560 300" role="img" aria-label="Work site map with center pin and clock-in radius"></svg>
    <p class="workMapCaption">Tap or click the map to adjust the center. Verify the pin before saving. Map © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>.</p>
   </div>
   <div class="actions"><button type="button" id="workUseLocation">Use my current location</button><button type="button" id="workCancelSite">Cancel</button><button class="primary">Save work site</button></div>
  </form>
 </section>`;
document.querySelector('main').append(workPanel);

const workApi = (path, data) => api('workforce/' + path, data);
let workQuick=false,workQuickTimeout;
let workView = 'clock', workWeek = '', workData, workLoadedAt = 0, workVersion = 0, workFetch = 0, workBusy = false;
let workTeam = {people:[],shifts:[]}, workSites = [], workEditingShift = null, workEditingSite = null;

function workStatus(message = '') { $('workStatus').textContent = message; }
function workDuration(value) {
 const seconds = Math.floor(Math.max(0,value));
 return `${Math.floor(seconds/3600)}h ${String(Math.floor(seconds/60)%60).padStart(2,'0')}m ${String(seconds%60).padStart(2,'0')}s`;
}
function workTick() {
 if (!workData || (!user&&!workQuick) || workPanel.hidden) return;
 const elapsed = Math.floor((performance.now() - workLoadedAt)/1000);
 const clock = workData.clock;
 const dayDelta = Math.max(0,Math.min(elapsed,workData.day_end-workData.now));
 const weekDelta = workData.now >= workData.week_start && workData.now < workData.week_end
  ? Math.max(0,Math.min(elapsed,workData.week_end-workData.now)) : 0;
 $('workGross').textContent = workDuration(clock.gross + (clock.state!=='out' ? dayDelta : 0));
 $('workNet').textContent = workDuration(clock.worked + (clock.state==='working' ? dayDelta : 0));
 $('workWeekGross').textContent = workDuration(clock.week_gross + (clock.state!=='out' ? weekDelta : 0));
 $('workWeekNet').textContent = workDuration(clock.week_worked + (clock.state==='working' ? weekDelta : 0));
}
function workShiftList(shifts, editable) {
 return shifts.map(shift=>`<article class="workRow">
  <div><strong>${editable?esc(shift.name):esc(shift.location || 'Scheduled shift')}</strong>
  <p>${esc(shift.start.replace('T',' '))} – ${esc(shift.end.replace('T',' '))}</p>
  ${shift.job?`<p>${esc(shift.job)}</p>`:''}
  ${editable&&shift.location?`<p>${esc(shift.location)}</p>`:''}
  ${shift.notes?`<p>${esc(shift.notes)}</p>`:''}</div>
  ${editable?`<div class="actions"><button type="button" data-edit-shift="${shift.id}">Edit</button><button type="button" data-remove-shift="${shift.id}">Remove</button></div>`:''}
 </article>`).join('') || '<p>No shifts scheduled for this week.</p>';
}
function workRender(data) {
 workData = data;
 workLoadedAt = performance.now();
 workWeek = data.week;
 $('workWeekDate').value = data.week;
 $('workClockState').textContent = ({out:'Clocked out',working:'Clocked in',break:'On break'})[data.clock.state]
  + (data.clock.since ? ' since ' + data.clock.since.replace('T',' ') : '');
 $('workGeoStatus').textContent = data.require_location
  ? (data.sites_ready ? 'Clock in and out from an approved work site.' : 'A manager needs to assign you a work site before clock-in and clock-out.')
  : 'Location checks are off.';
 const allowed = ({out:['in'],working:['out','start_break'],break:['out','end_break']})[data.clock.state];
 for (const button of workPanel.querySelectorAll('[data-work-punch]')) {
  const punch=button.dataset.workPunch;
  button.hidden=!allowed.includes(punch);
  button.disabled=workBusy || (data.require_location&&!data.sites_ready&&['in','out'].includes(punch));
 }
 workPanel.querySelector('[data-work-view=team]').hidden = !data.manage_schedule || !workIsDesktop();
 workPanel.querySelector('[data-work-view=review]').hidden = !data.manage_review;
 workPanel.querySelector('[data-work-view=time-cards]').hidden = !data.edit_time_cards&&!data.add_time_cards;
 workPanel.querySelector('[data-work-view=time-card-audit]').hidden = !user?.admin;
 workPanel.querySelector('[data-work-view=payroll]').hidden = !data.export_payroll;
 workPanel.querySelector('[data-work-view=sites]').hidden = !data.manage_sites;
 $('workManagerMenu').hidden=![...$('workManagerMenu').querySelectorAll('button')].some(b=>!b.hidden);
 $('workSetupMenu').hidden=!data.manage_sites;
 workRenderMine(data);
 workTick();
}
async function workLoad(version = workVersion) {
 const signedIn=user, request=++workFetch, query='?week='+encodeURIComponent(workWeek);
 try {
  const data=await workApi(workQuick?'quick':'overview'+query);
  if (workPanel.hidden || version!==workVersion || request!==workFetch || user!==signedIn) return;
  if ((workView==='time-card-audit'&&!user?.admin)||(workView==='payroll'&&!data.export_payroll)||(workView==='time-cards'&&!data.edit_time_cards&&!data.add_time_cards)||(workView==='team'&&!data.manage_schedule)||(workView==='review'&&!data.manage_review)||(workView==='sites'&&!data.manage_sites)) {
   workSelect('clock');return;
  }
  workRender(data);
  if (workView==='team') {
   const result=await workApi('team'+query);
   if (workPanel.hidden || version!==workVersion || request!==workFetch || user!==signedIn) return;
   workTeam=result;
   $('workAddShift').disabled=false;
   workRenderGrid(result,data.week);
  }
  if(workView==='time-cards'){
   const result=await workApi('time-cards?week='+encodeURIComponent(data.week));
   if (workPanel.hidden||version!==workVersion||request!==workFetch||user!==signedIn)return;
   workRenderTimeCards(result.cards,result.people);
  }
  if(workView==='my-cards'){
   const result=await workApi('my-time-cards'+query);
   if(version!==workVersion||request!==workFetch||user!==signedIn)return;
   $('workOwnCards').innerHTML=result.cards.map(card=>`<article class="workRow"><div><strong>${esc(card.start.replace('T',' '))} – ${card.end?esc(card.end.replace('T',' ')):'Still clocked in'}</strong><p>${card.breaks.length?card.breaks.map(b=>'Break: '+esc(b.start.replace('T',' '))+' – '+(b.end?esc(b.end.replace('T',' ')):'In progress')).join('<br>'):'No breaks recorded'}</p></div></article>`).join('')||'<p>No timecards this week.</p>';
  }
  if(workView==='time-card-audit')await workLoadAudit();
  if (['requests','availability','review'].includes(workView)) {
   const review=workView==='review';
   const result=await workApi(review?'review-requests':'requests');
   if (workPanel.hidden || version!==workVersion || request!==workFetch || user!==signedIn) return;
   workRenderRequests(result,review);
  }
  if (workView==='sites') {
   const result=await workApi('sites');
   if (workPanel.hidden || version!==workVersion || request!==workFetch || user!==signedIn) return;
   workSites=result.sites;
   $('workAddSite').disabled=false;
   $('workSiteList').innerHTML=result.sites.map(site=>`<article class="workRow">
    <div><strong>${esc(site.name)}</strong><p>${esc(workRadiusText(site.radius))} radius</p>${site.address?`<p>${esc(site.address)}</p>`:''}</div>
    <div class="actions"><button type="button" data-edit-site="${site.id}">Edit</button><button type="button" data-remove-site="${site.id}">Remove</button></div>
   </article>`).join('') || '<p>No work sites configured.</p>';
  }
 } catch (err) {
  if (version===workVersion && request===workFetch && user===signedIn && !workPanel.hidden) {
   if(workQuick&&err.message==='Enter your Time Clock PIN again.')workCloseQuick(err.message);
   else workStatus(err.message);
  }
 }
}
function workSelect(view) {
 if(view==='team'&&!workIsDesktop())view='mine';
 for(const menu of workPanel.querySelectorAll('.workDropdown'))menu.open=false;
 workView=view;
 $('workCopyDialog').close();
 workVersion++;
 workStatus();
 $('workWeekControls').hidden=!['mine','team','time-cards','my-cards'].includes(view);
 $('workShiftDialog').close();$('workRequestDialog').close();$('workCardDialog').close();
 $('workShiftForm').hidden=$('workSiteForm').hidden=true;
 if(view==='time-cards'){$('workTimeCards').textContent='Loading time cards…';$('workAddCard').hidden=true;}
 if(view==='time-card-audit'){$('workTimeAudit').textContent='Loading audit entries…';$('workAuditOlder').hidden=true;}
 if(view==='team'){
  $('workTeamShifts').textContent='Loading shifts…';
  $('workAddShift').disabled=true;
 }
 if(view==='sites'){
  $('workSiteList').textContent='Loading work sites…';
  $('workAddSite').disabled=true;
 }
 for (const tab of workPanel.querySelectorAll('[data-work-view]')) tab.setAttribute('aria-pressed',String(tab.dataset.workView===view));
 for (const panel of workPanel.querySelectorAll('[data-work-panel]')) panel.hidden=panel.dataset.workPanel!==view;
 workLoad();
}
function workOpen(quick=false,view='clock'){
 if (!quick&&!requireSignIn()) return;
 workQuick=quick;
 if(quick)$('auth').hidden=true;
 else storeSection('dispatch');
 $('app').hidden=true;
 workPanel.hidden=false;
 workPanel.querySelector('.workHead h2').textContent=quick?'Time Clock':'Scheduling & Time Clock';
 workPanel.querySelector('.workTabs').hidden=quick;
 $('workQuickBack').hidden=!quick;
 setSectionHeader(quick?'Time Clock':'Scheduling & Time Clock','workforce');
 workWeek='';
 workPayrollReset();
 workData=null;
 workTeam={people:[],shifts:[]};
 workSites=[];
 $('workClockState').textContent='Loading time clock…';
 for(const id of ['workGeoStatus','workMyShifts','workTeamShifts','workSiteList'])$(id).textContent='';
 for(const id of ['workGross','workNet','workWeekGross','workWeekNet'])$(id).textContent='—';
 for(const button of workPanel.querySelectorAll('[data-work-punch],[data-work-view=team],[data-work-view=sites],[data-work-view=payroll],[data-work-view=time-cards],[data-work-view=time-card-audit]'))button.hidden=true;
 workSelect(view);
}
workMenu.onclick=()=>workOpen();
function workMoveWeek(days) {
 if (!workWeek) return;
 const next=new Date(workWeek+'T12:00:00Z');
 next.setUTCDate(next.getUTCDate()+days);
 workWeek=next.toISOString().slice(0,10);
 workSelect(workView);
}
$('workPrev').onclick=()=>workMoveWeek(-7);
$('workNext').onclick=()=>workMoveWeek(7);
$('workThisWeek').onclick=()=>{workWeek='';workSelect(workView);};
$('workWeekDate').onchange=e=>{workWeek=e.target.value;workSelect(workView);};

function workPosition() {
 if (!window.isSecureContext || !navigator.geolocation)
  return Promise.reject(Error('Open the secure HTTPS staff address to share your location.'));
 return new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(position=>{
  const {latitude,longitude,accuracy}=position.coords;
  resolve({latitude,longitude,accuracy});
 },error=>reject(Error(error.code===1 ? 'Allow location access for this site and try again.' :
  'Could not get an accurate location. Move to a spot with better reception and try again.')),
 {enableHighAccuracy:true,maximumAge:0,timeout:15000}));
}
async function workPunch(action) {
 if (!workData || workBusy) return;
 const signedIn=user,version=workVersion;
 workBusy=true;
 for(const button of workPanel.querySelectorAll('[data-work-punch]')) button.disabled=true;
 workStatus();
 try {
  const data={action};
  if (workData.require_location && ['in','out'].includes(action)) {
   workStatus('Checking your location…');
   data.position=await workPosition();
  }
  if (user!==signedIn || version!==workVersion || workPanel.hidden) return;
  await workApi(workQuick?'quick/punch':'punch',data);
  if (user===signedIn && version===workVersion) {
   if(workQuick)workCloseQuick('Punch recorded.');
   else workStatus('Punch recorded.');
  }
 } catch (err) {
  if (user===signedIn && version===workVersion) workStatus(err.message);
 } finally {
  workBusy=false;
  if (!workPanel.hidden && user===signedIn) await workLoad();
 }
}
function workEditShift(shift,cell) {
 const form=$('workShiftForm');
 form.reset();
 workEditingShift=shift;
 $('workShiftTitle').textContent=shift?'Edit shift':'Add shift';
 $('workDeleteShift').hidden=!shift;
 $('workShiftError').textContent='';
 const fields=form.elements;
 fields.account.replaceChildren(new Option('Choose an employee',''),...workTeam.people.map(p=>new Option(p.name,p.id)));
 if (shift) for (const key of ['account','start','end','location','notes','job']) fields[key].value=shift[key];
 if(cell){
  fields.account.value=cell.account;
  fields.start.value=cell.day+'T09:00';
  fields.end.value=cell.day+'T17:00';
 }
 workShiftOptions(!shift);
 if(cell?.job!==undefined)fields.job.value=cell.job;
 form.hidden=false;
 $('workShiftDialog').showModal();
 fields.account.focus();
}
function workEditSite(site) {
 const form=$('workSiteForm');
 form.reset();
 workEditingSite=site;
 $('workSiteTitle').textContent=site?'Edit work site':'Add work site';
 if (site) for (const key of ['name','latitude','longitude','address']) form.elements.namedItem(key).value=site[key]??'';
 $('workAddressMatches').replaceChildren();
 $('workMapStatus').textContent='Find a U.S. work address or enter coordinates. Address lookup uses the U.S. Census Geocoder.';
 workSetRadiusUnit(workRadiusUnit(),site?.radius??150);
 workRenderMap();
 form.hidden=false;
 form.elements.namedItem('name').focus();
}
async function workSave(path,data,button,form) {
 const signedIn=user,version=workVersion;
 if (button) button.disabled=true;
 workStatus();
 try {
  await workApi(path,data);
  if (user!==signedIn || version!==workVersion || workPanel.hidden) return;
  if(form){
   form.hidden=true;
   form.closest('dialog')?.close();
  }
  workStatus('Saved.');
  await workLoad(version);
 } catch(err) { if(user===signedIn&&version===workVersion){
  if($('workShiftDialog').open)$('workShiftError').textContent=err.message;else workStatus(err.message);
 } }
 finally { if(button)button.disabled=false; }
}
function workShiftOptions(defaults){
 const form=$('workShiftForm'), fields=form.elements;
 const person=workTeam.people.find(p=>p.id===fields.account.value);
 $('workShiftJobs').replaceChildren(...(person?.jobs||[]).map(job=>new Option(job)));
 $('workShiftSites').replaceChildren(...(person?.locations||[]).map(site=>new Option(site)));
 if(defaults){fields.job.value=person?.primary_job||'';fields.location.value=person?.primary_location||'';}
}
$('workShiftForm').elements.account.onchange=()=>workShiftOptions(true);
$('workAddShift').onclick=()=>workEditShift(null);
$('workCancelShift').onclick=()=>$('workShiftDialog').close();
$('workDeleteShift').onclick=e=>{
 const shift=workEditingShift;
 if(shift&&confirm('Remove this scheduled shift?'))workSave('shift',{id:shift.id,revision:shift.revision,remove:true},e.currentTarget,$('workShiftForm'));
};
$('workAddSite').onclick=()=>workEditSite(null);
$('workCancelSite').onclick=()=>$('workSiteForm').hidden=true;
$('workUseLocation').onclick=async e=>{
 const button=e.currentTarget,version=workVersion,form=$('workSiteForm');
 button.disabled=true;
 try{
  const position=await workPosition();
  if(version!==workVersion||form.hidden)return;
  for(const field of ['latitude','longitude'])form.elements[field].value=position[field].toFixed(7);
  workRenderMap();
  workStatus('Location filled in. Review the site and radius, then save.');
 }catch(err){if(version===workVersion)workStatus(err.message);}
 finally{button.disabled=false;}
};
$('workShiftForm').onsubmit=e=>{
 e.preventDefault();
 const data=Object.fromEntries(new FormData(e.currentTarget));
 if(workEditingShift)Object.assign(data,{id:workEditingShift.id,revision:workEditingShift.revision});
 workSave('shift',data,e.submitter,e.currentTarget);
};
$('workSiteForm').onsubmit=e=>{
 e.preventDefault();
 const data=Object.fromEntries(new FormData(e.currentTarget));
 for(const field of ['latitude','longitude'])data[field]=Number(data[field]);
 data.radius=workRadiusMeters(e.currentTarget);
 if(Math.abs(data.radius-30)<1e-8)data.radius=30;
 if(Math.abs(data.radius-2000)<1e-8)data.radius=2000;
 delete data.radius_unit;
 if(workEditingSite)data.id=workEditingSite.id;
 workSave('site',data,e.submitter,e.currentTarget);
};
workPanel.addEventListener('click',e=>{
 const button=e.target.closest('button');
 if(!button)return;
 const {workView:view,workPunch:punch,editShift,removeShift,editSite,removeSite}=button.dataset;
 if(view){workSelect(view);return;}
 if(punch){workPunch(punch);return;}
 if(editShift)workEditShift(workTeam.shifts.find(s=>s.id===Number(editShift)));
 if(removeShift&&confirm('Remove this scheduled shift?')){
  const shift=workTeam.shifts.find(s=>s.id===Number(removeShift));
  if(shift)workSave('shift',{id:shift.id,revision:shift.revision,remove:true},button);
 }
 if(editSite)workEditSite(workSites.find(s=>s.id===Number(editSite)));
 if(removeSite&&confirm('Remove this approved work site?'))workSave('site',{id:Number(removeSite),remove:true},button);
});
setInterval(workTick,1000);
setInterval(()=>{
 if((user||workQuick)&&!workPanel.hidden&&!workBusy&&['clock','mine'].includes(workView))workLoad();
},20000);

const headerShortcuts=document.createElement('div');
headerShortcuts.id='headerShortcuts';
headerShortcuts.hidden=true;
headerShortcuts.innerHTML=`
 <button type="button" id="headerHome" title="Return to Home" aria-label="Return to Home">
  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10 9-7 9 7v10h-6v-6H9v6H3z"/></svg>
 </button>
 <button type="button" id="headerClock" title="Time Clock" aria-label="Open Time Clock">
  <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
 </button>`;
$('connection').after(headerShortcuts);
$('headerHome').onclick=()=>$('accountButton').click();
$('headerClock').onclick=()=>workOpen();

const loginClock=document.createElement('a');
loginClock.id='loginTimeClock';
loginClock.href='#time-clock';
loginClock.setAttribute('role','button');
loginClock.textContent='Time Clock';
$('login').querySelector('button.primary').after(loginClock);
loginClock.onkeydown=e=>{if(e.key===' '){e.preventDefault();loginClock.click();}};
const quickClockDialog=document.createElement('dialog');
quickClockDialog.innerHTML='<form id="quickClockForm"><h2>Time Clock</h2><label>Time Clock PIN<input name="pin" type="password" inputmode="numeric" autocomplete="off" pattern="[0-9]{6}" maxlength="6" required></label><p id="quickClockError" role="alert"></p><div class="actions"><button type="button" id="quickClockCancel">Cancel</button><button class="primary">Open Time Clock</button></div></form>';
document.body.append(quickClockDialog);
loginClock.onclick=e=>{
 e.preventDefault();
 $('quickClockForm').reset();
 $('quickClockError').textContent='';
 quickClockDialog.showModal();
};
$('quickClockCancel').onclick=()=>quickClockDialog.close();
$('quickClockForm').onsubmit=async e=>{
 e.preventDefault();
 const form=e.currentTarget,button=e.submitter;
 button.disabled=true;
 $('quickClockError').textContent='';
 try{
  await workApi('quick/login',{pin:form.elements.pin.value});
  form.reset();
  if(!quickClockDialog.open){await workApi('quick/close',{});return;}
  quickClockDialog.close();
  workOpen(true);
  clearTimeout(workQuickTimeout);
  workQuickTimeout=setTimeout(()=>workCloseQuick('Enter your Time Clock PIN again.'),180000);
 }catch(err){$('quickClockError').textContent=err.message;}
 finally{button.disabled=false;}
};
function workCloseQuick(message=''){
 if(!workQuick)return;
 clearTimeout(workQuickTimeout);
 workQuick=false;
 workData=null;
 setSectionHeader('Sign in','signin');
 $('auth').hidden=false;
 loginClock.focus();
 workApi('quick/close',{}).catch(()=>{});
 if(message)toast(message);
}
$('workQuickBack').onclick=()=>workCloseQuick();

const clockPinDialog=document.createElement('dialog');
clockPinDialog.innerHTML='<form id="clockPinForm"><h2>Time Clock PIN</h2><p id="clockPinPerson"></p><label>New six-digit PIN<input name="pin" type="password" inputmode="numeric" autocomplete="off" pattern="[0-9]{6}" maxlength="6" required></label><p id="clockPinError" role="alert"></p><div class="actions"><button type="button" id="clockPinRemove">Remove PIN</button><button type="button" id="clockPinCancel">Cancel</button><button class="primary">Save PIN</button></div></form>';
document.body.append(clockPinDialog);
let clockPinTarget;
$('users').addEventListener('click',e=>{
 const button=e.target.closest('[data-clock-pin]');
 if(!button)return;
 clockPinTarget=button.dataset.clockPin;
 $('clockPinForm').reset();
 $('clockPinPerson').textContent=clockPinTarget;
 $('clockPinError').textContent='';
 clockPinDialog.showModal();
});
$('clockPinCancel').onclick=()=>clockPinDialog.close();
async function setClockPin(pin,button){
 button.disabled=true;
 $('clockPinError').textContent='';
 try{
  await api('admin/clock-pin',{name:clockPinTarget,pin});
  clockPinDialog.close();
  toast(pin?'Time Clock PIN saved.':'Time Clock PIN removed.');
 }catch(err){$('clockPinError').textContent=err.message;}
 finally{button.disabled=false;}
}
$('clockPinForm').onsubmit=e=>{
 e.preventDefault();
 setClockPin(e.currentTarget.elements.pin.value,e.submitter);
};
$('clockPinRemove').onclick=e=>setClockPin('',e.currentTarget);

const profileMenu=document.createElement('button');
profileMenu.type='button';
profileMenu.textContent='My profile';
$('chooseStartSection').before(profileMenu);
const photoNotifications=document.createElement('button');
photoNotifications.type='button';
photoNotifications.id='photoNotifications';
photoNotifications.hidden=true;
photoNotifications.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9a6 6 0 0 1 12 0c0 5 2 7 2 7H4s2-2 2-7m4 10a2 2 0 0 0 4 0"/></svg><span id="photoReviewCount" hidden></span>';
photoNotifications.title='Notifications';
photoNotifications.setAttribute('aria-label','Notifications');
const headerProfile=document.createElement('button');
headerProfile.type='button';
headerProfile.id='headerProfile';
headerProfile.title='My profile';
headerProfile.setAttribute('aria-label','Open my profile');
headerShortcuts.append(photoNotifications,headerProfile);
headerProfile.onclick=()=>profileMenu.click();
let headerAvatarKey='';

function renderHeaderAvatar(account='',revision=null){
 const name=user?.name||'';
 const key=JSON.stringify([account,revision,name]);
 if(key===headerAvatarKey)return;
 headerAvatarKey=key;
 headerProfile.innerHTML=commAvatar(account,name,!!revision,revision);
 const picture=headerProfile.querySelector('img');
 if(picture)picture.addEventListener('error',()=>{
  if(headerAvatarKey===key)headerProfile.innerHTML=commAvatar('',name,false);
 },{once:true});
}

const profileDialog=document.createElement('dialog');
profileDialog.innerHTML=`<form id="profilePhotoForm">
 <h2>My profile</h2><p id="profileIdentity"></p><div id="profilePhotos" class="profilePhotos"></div>
 <p id="profilePhotoStatus" role="status"></p>
 <label>Upload a profile picture<input type="file" id="profilePhotoInput" accept="image/*"></label>
 <div class="actions"><button type="button" id="profileStartCamera">Take a picture</button><button type="button" id="profileCapture" hidden>Capture picture</button></div>
 <video id="profileCamera" autoplay muted playsinline hidden aria-label="Camera preview"></video>
 <img id="profileCapturePreview" hidden alt="Newly captured profile picture">
 <div class="actions"><button type="button" id="closeProfilePhoto">Close</button><button class="primary" id="profilePhotoSubmit">Submit for approval</button></div>
 </form>`;
const photoQueueDialog=document.createElement('dialog');
photoQueueDialog.innerHTML=`<h2>Notifications</h2>
 <section id="scheduleNotice" hidden><h3>Scheduling requests</h3><p id="scheduleNoticeCount"></p><button id="scheduleNoticeOpen" type="button">Review scheduling requests</button></section>
 <section id="profilePhotoNotice" hidden><h3>Profile picture approvals</h3>
 <p id="photoQueueStatus" role="status"></p><div id="photoQueue"></div></section>
 <div class="actions"><button type="button" id="closePhotoQueue">Close</button></div>`;
document.body.append(profileDialog,photoQueueDialog);
const profileWelcome=document.createElement('section');
profileWelcome.id='profileWelcome';
profileWelcome.className='card';
profileWelcome.hidden=true;
profileWelcome.innerHTML='<h2>Add a profile picture</h2><p>Take a picture or upload one so teammates can recognize you.</p><div class="actions"><button type="button" id="profileWelcomeCamera" class="primary">Take a picture</button><button type="button" id="profileWelcomeUpload">Upload a picture</button><button type="button" id="profileWelcomeSkip">Skip for now</button></div>';
document.querySelector('main').prepend(profileWelcome);
let profilePromptSkipped=false,profileCameraStream,profileCaptureData='',profileCameraVersion=0;
$('profileWelcomeSkip').onclick=()=>{profilePromptSkipped=true;profileWelcome.hidden=true;};
$('profileWelcomeUpload').onclick=()=>profileMenu.click();
$('profileWelcomeCamera').onclick=()=>{profileMenu.click();profileStartCamera();};

const profileApi=(path,data)=>api('profile/'+path,data);
let photoPendingCount=0,showPhotoReview=false;
function profileReset(){
 photoNotifications.hidden=true;
 profileWelcome.hidden=true;
 profilePromptSkipped=false;
 profileStopCamera();
 photoPendingCount=0;
 headerAvatarKey='';
 headerProfile.replaceChildren();
 profileDialog.close();
 photoQueueDialog.close();
 $('profileIdentity').textContent='';
 $('profilePhotos').replaceChildren();
 $('photoQueue').replaceChildren();
 $('profilePhotoForm').reset();
}
function profileReviewStatus(result){
 renderHeaderAvatar(result.profile_account,result.profile_photo_revision);
 profileWelcome.hidden=profilePromptSkipped||!!result.profile_photo_revision||!!result.profile_photo_pending;
 const photos=result.pending_photos||0, schedule=result.pending_schedule||0;
 const count=photos+schedule;
 showPhotoReview=result.photo_review;
 photoNotifications.hidden=!result.photo_review&&!result.schedule_review;
 $('profilePhotoNotice').hidden=!result.photo_review;
 $('scheduleNotice').hidden=!result.schedule_review;
 $('scheduleNoticeCount').textContent=schedule?`${schedule} request${schedule===1?'':'s'} awaiting review.`:'No scheduling requests awaiting review.';
 $('photoReviewCount').hidden=!count;
 $('photoReviewCount').textContent=count;
 const counts=[photos?`${photos} profile picture approvals`:'',schedule?`${schedule} scheduling requests`:''].filter(Boolean);
 photoNotifications.setAttribute('aria-label',counts.length?'Notifications, '+counts.join(', '):'Notifications');
 if(!result.photo_review&&!result.schedule_review&&photoQueueDialog.open)photoQueueDialog.close();
 if(result.photo_review&&photos!==photoPendingCount&&photoQueueDialog.open)loadPhotoQueue();
 photoPendingCount=photos;
}
function commAvatar(id,name,photo,revision=null){
 if(photo)return `<img class="commInitial" src="/api/profile/photo/${encodeURIComponent(id)}${revision?'?v='+encodeURIComponent(revision):''}" alt="" loading="lazy">`;
 return `<span class="commInitial" aria-hidden="true">${esc(name.trim().slice(0,2).toUpperCase())}</span>`;
}
async function loadProfilePhoto(){
 const signedIn=user;
 const [photo,identity]=await Promise.all([profileApi('mine'),profileApi('identity')]);
 if(user!==signedIn||!profileDialog.open)return;
 const legal=[identity.first,identity.middle,identity.last].filter(Boolean).join(' ');
 $('profileIdentity').textContent='Login username: '+identity.username+(legal?' · Legal name: '+legal:'');
 const id=encodeURIComponent(photo.account||'');
 $('profilePhotos').innerHTML=(photo.approved?`<figure><img alt="Approved profile picture" src="/api/profile/photo/${id}"><figcaption>Current picture</figcaption></figure>`:'')+
  (photo.pending_revision?`<figure><img alt="Pending profile picture" src="/api/profile/pending/${id}/${encodeURIComponent(photo.pending_revision)}"><figcaption>Awaiting approval</figcaption></figure>`:'');
 $('profilePhotoStatus').textContent=({
  pending:'Your submitted picture is waiting for approval.',
  approved:'Your picture is approved and visible to signed-in staff.',
  rejected:'Your last submission was declined. You can submit another picture.',
  none:user?.admin?'Your picture will appear when saved.':'Your picture will appear after approval.'
 })[photo.status]||'';
}
profileMenu.onclick=async()=>{
 closeStoreMenu();
 $('profilePhotoForm').reset();
 profileClearCapture();
 $('profileIdentity').textContent='';
 $('profilePhotos').replaceChildren();
 $('profilePhotoStatus').textContent='Loading profile…';
 $('profilePhotoSubmit').textContent=user?.admin?'Save profile picture':'Submit for approval';
 profileDialog.showModal();
 try{await loadProfilePhoto();}catch(e){$('profilePhotoStatus').textContent=e.message;}
};
$('closeProfilePhoto').onclick=()=>profileDialog.close();
profileDialog.addEventListener('close',()=>{profileStopCamera();profileClearCapture();});
function profileStopCamera(){
 profileCameraVersion++;
 profileCameraStream?.getTracks().forEach(track=>track.stop());
 profileCameraStream=null;
 const video=$('profileCamera');
 video.srcObject=null;
 video.hidden=true;
 $('profileCapture').hidden=true;
 $('profileCapture').disabled=true;
 $('profileStartCamera').disabled=false;
}
function profileClearCapture(){
 profileCaptureData='';
 $('profileCapturePreview').removeAttribute('src');
 $('profileCapturePreview').hidden=true;
}
async function profileStartCamera(){
 if(!navigator.mediaDevices?.getUserMedia){
  $('profilePhotoStatus').textContent='Camera access requires a supported browser and a secure address. You can upload a picture instead.';
  return;
 }
 profileStopCamera();
 const version=profileCameraVersion;
 $('profileStartCamera').disabled=true;
 try{
  const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
  if(!profileDialog.open||version!==profileCameraVersion){stream.getTracks().forEach(track=>track.stop());return;}
  profileCameraStream=stream;
  const video=$('profileCamera');
  video.srcObject=stream;
  video.hidden=false;
  $('profileCapture').hidden=false;
  await video.play();
  if(version===profileCameraVersion)$('profileCapture').disabled=false;
 }catch{
  if(version===profileCameraVersion){
   profileStopCamera();
   $('profilePhotoStatus').textContent='Camera unavailable. Check your camera permission or upload a picture.';
  }
 }
}
$('profileStartCamera').onclick=profileStartCamera;
$('profilePhotoInput').onchange=()=>{profileStopCamera();profileClearCapture();};
$('profileCapture').onclick=()=>{
 const video=$('profileCamera');
 if(!video.videoWidth)return;
 try{
  profileCaptureData=profileEncodeImage(video,video.videoWidth,video.videoHeight);
  $('profilePhotoInput').value='';
  const preview=$('profileCapturePreview');
  preview.src='data:image/jpeg;base64,'+profileCaptureData;
  preview.hidden=false;
  profileStopCamera();
  $('profilePhotoStatus').textContent='Picture captured. Review it, then submit it or take another.';
 }catch(err){$('profilePhotoStatus').textContent=err.message;}
};
function profileEncodeImage(source,width,height){
 const canvas=document.createElement('canvas');
 canvas.width=canvas.height=256;
 const context=canvas.getContext('2d'),side=Math.min(width,height);
 if(!context||!side)throw Error('This picture could not be opened.');
 context.fillStyle='#fff';
 context.fillRect(0,0,256,256);
 context.drawImage(source,(width-side)/2,(height-side)/2,side,side,0,0,256,256);
 return canvas.toDataURL('image/jpeg',0.88).split(',')[1];
}
async function profilePhotoData(file){
 if(file.size>12000000)throw Error('Choose a picture smaller than 12 MB.');
 const url=URL.createObjectURL(file);
 try{
  const picture=new Image();
  picture.src=url;
  try{await picture.decode();}catch{throw Error('Choose an image your browser can open, such as JPEG or PNG.');}
  return profileEncodeImage(picture,picture.naturalWidth,picture.naturalHeight);
 }finally{URL.revokeObjectURL(url);}
}
$('profilePhotoForm').onsubmit=async e=>{
 e.preventDefault();
 const file=$('profilePhotoInput').files[0], signedIn=user, button=e.submitter;
 if(!file&&!profileCaptureData){$('profilePhotoStatus').textContent='Take a picture or choose one to upload first.';return;}
 button.disabled=true;
 try{
  const image=profileCaptureData||await profilePhotoData(file);
  if(user!==signedIn)return;
  await profileApi('upload',{image});
  if(user!==signedIn)return;
  $('profilePhotoForm').reset();
  profileClearCapture();
  profileStopCamera();
  profilePromptSkipped=true;
  profileWelcome.hidden=true;
  await loadProfilePhoto();
  commPoll();
 }catch(err){if(user===signedIn)$('profilePhotoStatus').textContent=err.message;}
 finally{button.disabled=false;}
};
async function loadPhotoQueue(){
 const signedIn=user;
 try{
  const {requests}=await profileApi('queue');
  if(user!==signedIn||!photoQueueDialog.open)return;
  $('photoQueue').innerHTML=requests.map(request=>{
   const id=encodeURIComponent(request.account),revision=encodeURIComponent(request.pending_revision);
   return `<article class="profileReviewRow"><img alt="" src="/api/profile/pending/${id}/${revision}">
    <div><strong>${esc(request.name)}</strong><p>Profile picture approval</p>
     ${request.own?'<p>Your picture is pending your approval.</p>':''}
     <div class="actions"><button type="button" data-decision="reject" data-account="${id}" data-revision="${revision}">Decline</button><button type="button" class="primary" data-decision="approve" data-account="${id}" data-revision="${revision}">Approve</button></div>
    </div></article>`;
  }).join('')||'<p>No profile pictures are waiting for approval.</p>';
 }catch(err){if(user===signedIn&&photoQueueDialog.open)$('photoQueueStatus').textContent=err.message;}
}
photoNotifications.onclick=()=>{
 $('photoQueue').replaceChildren();
 $('photoQueueStatus').textContent='';
 photoQueueDialog.showModal();
 if(showPhotoReview)loadPhotoQueue();
};
$('closePhotoQueue').onclick=()=>photoQueueDialog.close();
$('scheduleNoticeOpen').onclick=()=>{photoQueueDialog.close();workOpen(false,'review');};
$('photoQueue').onclick=async e=>{
 const button=e.target.closest('[data-decision]');
 if(!button)return;
 const row=button.closest('article'),signedIn=user;
 const {decision,account,revision}=button.dataset;
 for(const control of row.querySelectorAll('button'))control.disabled=true;
 try{
  await profileApi('review',{decision,account,revision});
  if(user!==signedIn)return;
  $('photoQueueStatus').textContent=decision==='approve'?'Picture approved.':'Picture declined.';
  await loadPhotoQueue();
  commPoll();
 }catch(err){
  if(user===signedIn){$('photoQueueStatus').textContent=err.message;await loadPhotoQueue();}
 }
};

const workFeet=0.3048;
const workMapSize={width:560,height:300,tile:256};
const workSiteFields=$('workSiteForm').elements;
let workMapCenter=null,workMapFrame=null,workAddressSearch=0;
function workRadiusUnit(){
 try{return localStorage.getItem('yfc-work-radius-unit')==='ft'?'ft':'m';}catch{return 'm';}
}
function workRadiusText(meters){
 const feet=workRadiusUnit()==='ft';
 return `${new Intl.NumberFormat(undefined,{maximumFractionDigits:1}).format(feet?meters/workFeet:meters)} ${feet?'ft':'m'}`;
}
function workRadiusMeters(form){
 const radius=form.elements.radius.valueAsNumber;
 return form.elements.radius_unit.value==='ft'?radius*workFeet:radius;
}
function workSetRadiusUnit(unit,meters){
 const factor=unit==='ft'?workFeet:1;
 workSiteFields.radius_unit.value=unit;
 $('workRadiusLabel').firstChild.textContent=unit==='ft'?'Radius (feet)':'Radius (meters)';
 workSiteFields.radius.min=30/factor;
 workSiteFields.radius.max=2000/factor;
 if(Number.isFinite(meters))workSiteFields.radius.value=meters/factor;
}
workSiteFields.radius_unit.onchange=()=>{
 const unit=workSiteFields.radius_unit.value;
 const previous=unit==='ft'?'m':'ft';
 const value=workSiteFields.radius.valueAsNumber;
 workSetRadiusUnit(unit,previous==='ft'?value*workFeet:value);
 try{localStorage.setItem('yfc-work-radius-unit',unit);}catch{}
 workRenderMap();
};
function workProject(lat,lon,scale){
 const angle=Math.max(-85.05112878,Math.min(85.05112878,lat))*Math.PI/180;
 return [(lon+180)/360*scale,(1-Math.asinh(Math.tan(angle))/Math.PI)*scale/2];
}
function workBoundaryPoint(lat,lon,meters,bearing){
 const rad=Math.PI/180, distance=meters/6371000;
 const a=lat*rad;
 const b=Math.asin(Math.sin(a)*Math.cos(distance)+Math.cos(a)*Math.sin(distance)*Math.cos(bearing));
 const l=lon*rad+Math.atan2(Math.sin(bearing)*Math.sin(distance)*Math.cos(a),Math.cos(distance)-Math.sin(a)*Math.sin(b));
 return [b/rad,l/rad];
}
function workRenderMap(){
 const svg=$('workSiteMap'), lat=workSiteFields.latitude.valueAsNumber, lon=workSiteFields.longitude.valueAsNumber;
 const radius=workRadiusMeters($('workSiteForm'));
 const valid=Number.isFinite(lat)&&Math.abs(lat)<=85.05112878&&Number.isFinite(lon)&&Math.abs(lon)<=180;
 $('workMapPanel').hidden=!valid;
 workMapCenter=null;
 if(!valid){svg.replaceChildren();workMapFrame=null;return;}
 const {width,height,tile}=workMapSize;
 const meters=Number.isFinite(radius)&&radius>=30-1e-8&&radius<=2000+1e-8?radius:0;
 const zoom=Math.max(3,Math.min(19,Math.floor(Math.log2(height*0.35*2*Math.PI*6371000*Math.cos(lat*Math.PI/180)/(tile*Math.max(meters,30))))));
 const tiles=2**zoom, scale=tile*tiles;
 const [x,y]=workProject(lat,lon,scale);
 const left=x-width/2, top=y-height/2;
 const frame=[zoom,left,top].join(':');
 const parts=[];
 if(frame!==workMapFrame){
  for(let ty=Math.max(0,Math.floor(top/tile));ty<=Math.min(tiles-1,Math.floor((top+height)/tile));ty++){
   for(let tx=Math.floor(left/tile);tx<=Math.floor((left+width)/tile);tx++){
    const wrapped=(tx%tiles+tiles)%tiles;
    parts.push(`<image href="https://tile.openstreetmap.org/${zoom}/${wrapped}/${ty}.png" x="${tx*tile-left}" y="${ty*tile-top}" width="256" height="256"></image>`);
   }
  }
  svg.innerHTML='<g id="workMapTiles">'+parts.join('')+'</g><polygon id="workMapBoundary"/><g class="workMapPin" transform="translate(280 150)"><path d="M0 0C-3-5-10-11-10-19a10 10 0 0 1 20 0C10-11 3-5 0 0Z"/><circle cx="0" cy="-19" r="3"/></g>';
  workMapFrame=frame;
 }
 const points=meters?Array.from({length:64},(_,i)=>{
  const p=workBoundaryPoint(lat,lon,meters,i*Math.PI/32);
  const [px,py]=workProject(p[0],p[1],scale);
  return `${(px-left).toFixed(2)},${(py-top).toFixed(2)}`;
 }).join(' '):'';
 $('workMapBoundary').setAttribute('points',points);
 workMapCenter={left,top,scale};
}
for(const field of ['latitude','longitude','radius'])workSiteFields[field].addEventListener('input',workRenderMap);
$('workSiteMap').onclick=e=>{
 const svg=e.currentTarget, matrix=svg.getScreenCTM();
 if(!workMapCenter||!matrix)return;
 const point=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix.inverse());
 const {left,top,scale}=workMapCenter;
 const lon=(point.x+left)/scale*360;
 const lat=Math.atan(Math.sinh(Math.PI*(1-2*(point.y+top)/scale)))*180/Math.PI;
 workSiteFields.latitude.value=lat.toFixed(7);
 workSiteFields.longitude.value=(((lon+360)%360)-180).toFixed(7);
 workRenderMap();
};
$('workFindAddress').onclick=async e=>{
 const button=e.currentTarget,address=workSiteFields.address.value.trim();
 const version=workVersion,editing=workEditingSite,search=++workAddressSearch;
 const current=()=>version===workVersion&&editing===workEditingSite&&search===workAddressSearch&&!$('workSiteForm').hidden;
 const status=$('workMapStatus'), list=$('workAddressMatches');
 list.replaceChildren();
 if(address.length<5){status.textContent='Enter a street address with a city and state or ZIP code.';return;}
 button.disabled=true;
 status.textContent='Looking up the work address…';
 try{
  const {matches}=await workApi('geocode?address='+encodeURIComponent(address));
  if(!current()||workSiteFields.address.value.trim()!==address)return;
  status.textContent=matches.length?'Choose an address match, then verify the pin on the map.':'No matching address. Check the address or enter coordinates manually.';
  for(const match of matches){
   const choice=document.createElement('button');
   choice.type='button';
   choice.textContent=match.address;
   choice.onclick=()=>{
    workSiteFields.address.value=match.address;
    workSiteFields.latitude.value=match.latitude.toFixed(7);
    workSiteFields.longitude.value=match.longitude.toFixed(7);
    list.replaceChildren();
    status.textContent='Address placed on the map. Adjust the pin if needed before saving.';
    workRenderMap();
   };
   list.append(choice);
  }
 }catch(err){if(current())status.textContent=err.message;}
 finally{button.disabled=false;}
};
workSiteFields.address.addEventListener('input',()=>$('workAddressMatches').replaceChildren());

const workWeekdays=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
function workDateOffset(day,offset){
 const date=new Date(day+'T12:00:00Z');
 date.setUTCDate(date.getUTCDate()+offset);
 return date.toISOString().slice(0,10);
}
function workShiftTime(value){
 const [hour,minute]=value.slice(-5).split(':').map(Number);
 return `${hour%12||12}:${String(minute).padStart(2,'0')} ${hour<12?'AM':'PM'}`;
}
function workRenderMine(data){
 const unique=[...new Map(data.shifts.map(s=>[s.id,s])).values()];
 $('workScheduledHours').textContent=(unique.reduce((n,s)=>n+s.week_seconds,0)/3600).toLocaleString(undefined,{maximumFractionDigits:2});
 $('workScheduledCount').textContent=unique.length;
 $('workMyRange').textContent=`${data.week} – ${workDateOffset(data.week,6)}`;
 $('workMyShifts').innerHTML=Array.from({length:7},(_,i)=>{
  const day=workDateOffset(data.week,i),next=workDateOffset(day,1);
  // Show each shift once, on its starting day (or the first visible day for an overnight carry-in).
  const shifts=unique.filter(s=>s.start.slice(0,10)===day||(i===0&&s.start<day&&s.end>day));
  const label=new Date(day+'T12:00:00').toLocaleDateString(undefined,{weekday:'long',month:'short',day:'numeric'});
  return `<section class="workDay"><h4>${esc(label)}</h4>${shifts.length?shifts.map(s=>`<article class="workPersonalShift"><strong>${workShiftTime(s.start)} – ${workShiftTime(s.end)}${s.start.slice(0,10)!==s.end.slice(0,10)?' (ends '+esc(s.end.slice(0,10))+')':''}</strong><b>${esc(s.job||'Scheduled shift')}</b><span>${esc(s.location||'No location specified')}</span>${s.notes?`<p>${esc(s.notes)}</p>`:''}</article>`).join(''):'<div class="workDayEmpty">You don’t have any shifts on this day.</div>'}</section>`;
 }).join('');
}
function workRenderGrid(team,week){
 const days=[6,0,1,2,3,4,5].map((weekday,i)=>({label:workWeekdays[weekday],day:workDateOffset(week,i),next:workDateOffset(week,i+1)}));
 const jobs=[...new Set([...(team.jobs||[]),...team.people.flatMap(p=>p.jobs),...team.shifts.map(s=>s.job)].filter(Boolean))].sort((a,b)=>a.localeCompare(b));
 if(team.people.some(p=>!p.jobs.length)||team.shifts.some(s=>!s.job))jobs.push('');
 const absences=[...(team.absences||[]),...(team.pending_absences||[]).map(b=>({...b,pending:true}))];
 $('workTeamShifts').innerHTML=`<div class="workGridScroll" tabindex="0" aria-label="Weekly staff schedule"><table class="workScheduleGrid"><thead><tr><th scope="col">Employee</th><th scope="col">Shifts</th>${days.map(d=>`<th scope="col">${d.label} ${d.day.slice(5)}</th>`).join('')}<th scope="col">Hours</th></tr><tr class="workDispatchRow"><th scope="row" colspan="2">Dispatch</th>${days.map(d=>`<td>${(team.dispatch||[]).filter(e=>e.start.slice(0,10)===d.day).map(e=>`<div class="workDispatch type${e.type}">${workShiftTime(e.start)} ${e.type}</div>`).join('')}</td>`).join('')}<td></td></tr></thead>${jobs.map(job=>{
  const people=team.people.filter(p=>p.jobs.includes(job)||(!job&&!p.jobs.length)||team.shifts.some(s=>s.account===p.id&&s.job===job));
  return `<tbody data-job-section="${esc(job)}"><tr class="workJobHeading"><th colspan="10" scope="rowgroup">${esc(job||'Unassigned job')} <small>${people.length} employees</small></th></tr>${people.map(person=>{
   const all=team.shifts.filter(s=>s.account===person.id),own=all.filter(s=>s.job===job);
   return `<tr><th scope="row">${esc(person.name)}</th><td>${own.length}</td>${days.map(({day,next})=>{
    const blocked=absences.filter(b=>b.account===person.id&&b.day===day);
    return `<td>${blocked.map(b=>`<div class="workAbsence ${b.kind==='time-off'?'timeOff':''} ${b.pending?'workPending':''}">${b.pending?'Pending · ':''}${b.kind==='time-off'?'Time off':'Unavailable'}${b.start?' '+workShiftTime(b.start)+' – '+workShiftTime(b.end):' · all day'}</div>`).join('')}${all.filter(s=>s.start<next+'T00:00'&&s.end>day+'T00:00').map(s=>{
     const ghost=s.job!==job;
     const contents=`<strong>${workShiftTime(s.start)} – ${workShiftTime(s.end)}</strong><span>${esc(s.job||'Unassigned job')}${ghost?' · other job':''}</span>${s.location?`<span>${esc(s.location)}</span>`:''}${s.start.slice(0,10)!==s.end.slice(0,10)?'<span>Overnight shift</span>':''}`;
     return ghost?`<div class="workShiftCard workGhost" aria-label="Other job: ${esc(s.job)}">${contents}</div>`:`<button class="workShiftCard" type="button" data-edit-shift="${s.id}">${contents}</button>`;
    }).join('')}<button type="button" class="workGridAdd" data-grid-account="${esc(person.id)}" data-grid-day="${day}" data-grid-job="${esc(job)}" aria-label="Add ${esc(job)} shift for ${esc(person.name)} on ${day}">＋</button></td>`;
   }).join('')}<td>${(own.reduce((n,s)=>n+s.week_seconds,0)/3600).toLocaleString(undefined,{maximumFractionDigits:2})}</td></tr>`;
  }).join('')}</tbody>`;
 }).join('')}</table></div>`;
}
$('workTeamShifts').addEventListener('click',e=>{
 const b=e.target.closest('[data-grid-account]');
 if(b)workEditShift(null,{account:b.dataset.gridAccount,day:b.dataset.gridDay,job:b.dataset.gridJob});
});

let workRequestKind='';
function workAddBlock(){
 const list=$('workAvailabilityBlocks');
 if(list.children.length>=28)return;
 const row=document.createElement('div');
 row.className='workAvailabilityBlock';
 row.innerHTML=`<label>Day<select>${[6,0,1,2,3,4,5].map(i=>`<option value="${i}">${workWeekdays[i]}</option>`).join('')}</select></label>
  <label>From<input type="time"></label><label>Until<input type="time"></label>
  <label class="workCheck"><input type="checkbox" checked>All day</label>
  <button type="button" aria-label="Remove unavailable period">Remove</button>`;
 const allDay=row.querySelector('input[type=checkbox]');
 const times=[...row.querySelectorAll('input[type=time]')];
 const update=()=>times.forEach(input=>{input.disabled=allDay.checked;input.required=!allDay.checked;});
 allDay.onchange=update;update();
 row.querySelector('button').onclick=()=>row.remove();
 list.append(row);
}
function workRequestOpen(kind){
 workRequestKind=kind;
 const form=$('workRequestForm');
 form.reset();
 const availability=kind==='availability';
 $('workRequestTitle').textContent=availability?'Request availability change':'Request time off';
 $('workAvailabilityFields').hidden=!availability;
 $('workTimeOffFields').hidden=availability;
 $('workAvailabilityBlocks').replaceChildren();
 for(const input of [$('workRequestForm').elements.start,$('workRequestForm').elements.end]){
  input.required=!availability;input.disabled=availability;input.min=workData?.today||'';
 }
 if(availability)workAddBlock();
 $('workRequestError').textContent='';
 $('workRequestDialog').showModal();
}
$('workAvailability').onclick=()=>workRequestOpen('availability');
$('workTimeOff').onclick=()=>workRequestOpen('time-off');
$('workAddBlock').onclick=workAddBlock;
$('workRequestCancel').onclick=()=>$('workRequestDialog').close();
$('workRequestForm').onsubmit=async e=>{
 e.preventDefault();
 const form=e.currentTarget,button=e.submitter,version=workVersion;
 const data={kind:workRequestKind,notes:form.elements.notes.value};
 if(workRequestKind==='availability'){
  data.blocks=[...$('workAvailabilityBlocks').children].map(row=>{
   const allDay=row.querySelector('input[type=checkbox]').checked;
   const [start,end]=[...row.querySelectorAll('input[type=time]')].map(i=>allDay?'':i.value);
   return {day:Number(row.querySelector('select').value),start,end};
  });
 }else{data.start=form.elements.start.value;data.end=form.elements.end.value;data.from_time=form.elements.from_time.value;data.until_time=form.elements.until_time.value;}
 button.disabled=true;
 try{
  await workApi('request',data);
  if(version!==workVersion)return;
  $('workRequestDialog').close();
  workStatus(user?.admin?'Request applied.':can('manage_staff_schedule')?'Request pending. Open Review requests to approve it.':'Request sent for approval.');
  await workLoad();
 }catch(err){if(version===workVersion)$('workRequestError').textContent=err.message;}
 finally{button.disabled=false;}
};
function workRenderRequests(result,review){
 const list=$(review?'workReviewRequests':workView==='availability'?'workOwnAvailability':'workMyRequests');
 if(workView==='availability')result={...result,requests:result.requests.filter(r=>r.kind==='availability')};
 list.innerHTML=result.requests.map(request=>{
  const availability=request.kind==='availability';
  const summary=availability?(request.details.blocks.map(b=>`${workWeekdays[b.day]}: ${b.start?b.start+' – '+b.end:'All day'}`).join(', ')||'Clear weekly unavailability'):
   `${request.details.start} to ${request.details.end}${request.details.from_time?" · "+request.details.from_time+" – "+request.details.until_time:""}`;
  const pending=request.status==='pending';
  return `<article class="workRow"><div><strong>${review?esc(request.name)+' · ':''}${availability?'Availability':'Time off'}</strong>
   <p>${esc(summary)}</p>${request.notes?`<p>${esc(request.notes)}</p>`:''}<p class="workRequestState">${esc(request.status)}${request.reviewer?' · '+esc(request.reviewer):''}</p></div>
   ${pending?`<div class="actions">${review?
    `<button type="button" data-work-request="${request.id}" data-work-decision="declined">Decline</button><button class="primary" type="button" data-work-request="${request.id}" data-work-decision="approved">Approve</button>`:
    `<button type="button" data-work-request="${request.id}">Withdraw</button>`}</div>`:''}</article>`;
 }).join('')||'<p>No requests yet.</p>';
}
for(const id of ['workMyRequests','workReviewRequests','workOwnAvailability']){
 $(id).addEventListener('click',async e=>{
  const button=e.target.closest('[data-work-request]');
  if(!button)return;
  const id=Number(button.dataset.workRequest),decision=button.dataset.workDecision;
  await workSave(decision?'review-request':'withdraw-request',{id,decision},button);
  commPoll();
 });
}

const workAssignmentDialog=document.createElement('dialog');
workAssignmentDialog.innerHTML=`<form id="workAssignmentForm">
 <h2>Work assignments</h2><p id="workAssignmentName"></p>
 <label>Assigned jobs (one per line)<textarea name="jobs" rows="4" maxlength="2430"></textarea></label>
 <label>Primary job<select name="primary_job"></select></label>
 <fieldset><legend>Assigned work sites</legend><div id="workAssignmentSites"></div></fieldset>
 <label>Primary work site<select name="primary_site"></select></label>
 <label class="workAssignmentCheck"><input type="checkbox" name="require_location"> Require location checks when clocking in and out</label>
 <p id="workAssignmentError" role="alert"></p>
 <div class="actions"><button type="button" id="workAssignmentClose">Cancel</button><button type="submit" class="primary">Save assignments</button></div>
 </form>`;
document.body.append(workAssignmentDialog);
const workAssignmentForm=$('workAssignmentForm');
let workAssignmentName='',workAssignmentVersion=0;
function workAssignmentJobs(){
 return [...new Set(workAssignmentForm.elements.jobs.value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean))];
}
function workAssignmentUpdateChoices(){
 const fields=workAssignmentForm.elements,jobs=workAssignmentJobs();
 const sites=[...$('workAssignmentSites').querySelectorAll('input:checked')];
 for(const [field,choices,empty] of [[fields.primary_job,jobs.map(job=>[job,job]),'No jobs assigned'],
     [fields.primary_site,sites.map(input=>[input.dataset.name,input.value]),'No sites assigned']]){
  const current=field.value;
  field.replaceChildren(...(choices.length?choices:[[empty,'']]).map(([label,value])=>new Option(label,value)));
  if(choices.some(([,value])=>value===current))field.value=current;
 }
}
workAssignmentForm.elements.jobs.addEventListener('input',workAssignmentUpdateChoices);
$('workAssignmentSites').addEventListener('change',workAssignmentUpdateChoices);
$('workAssignmentClose').onclick=()=>workAssignmentDialog.close();
$('users').addEventListener('click',async e=>{
 const button=e.target.closest('[data-work-assignment]');
 if(!button)return;
 const name=button.dataset.workAssignment,version=++workAssignmentVersion,signedIn=user;
 const fields=workAssignmentForm.elements,submit=workAssignmentForm.querySelector('[type=submit]');
 workAssignmentName=name;
 workAssignmentForm.reset();
 $('workAssignmentSites').replaceChildren();
 workAssignmentUpdateChoices();
 $('workAssignmentName').textContent=name;
 $('workAssignmentError').textContent='Loading assignments…';
 submit.disabled=true;
 workAssignmentDialog.showModal();
 try{
  const {assignment,sites}=await workApi('assignment?name='+encodeURIComponent(name));
  if(user!==signedIn||version!==workAssignmentVersion||!workAssignmentDialog.open)return;
  fields.jobs.value=assignment.jobs.join('\n');
  fields.require_location.checked=assignment.require_location;
  $('workAssignmentSites').replaceChildren(...sites.map(site=>{
   const label=document.createElement('label'),input=document.createElement('input');
   label.className='workAssignmentCheck';
   input.type='checkbox';
   input.value=site.id;
   input.dataset.name=site.name;
   input.checked=assignment.sites.includes(site.id);
   label.append(input,document.createTextNode(site.name));
   return label;
  }));
  if(!sites.length)$('workAssignmentSites').textContent='No work sites have been configured.';
  workAssignmentUpdateChoices();
  fields.primary_job.value=assignment.primary_job;
  fields.primary_site.value=assignment.primary_site??'';
  $('workAssignmentError').textContent='';
  submit.disabled=false;
 }catch(err){if(version===workAssignmentVersion&&user===signedIn)$('workAssignmentError').textContent=err.message;}
});
workAssignmentForm.onsubmit=async e=>{
 e.preventDefault();
 const fields=e.currentTarget.elements,button=e.submitter,version=workAssignmentVersion,signedIn=user;
 const sites=[...$('workAssignmentSites').querySelectorAll('input:checked')].map(input=>Number(input.value));
 button.disabled=true;
 try{
  await workApi('assignment',{name:workAssignmentName,jobs:workAssignmentJobs(),sites,
   primary_job:fields.primary_job.value,primary_site:fields.primary_site.value?Number(fields.primary_site.value):null,
   require_location:fields.require_location.checked});
  if(user===signedIn&&version===workAssignmentVersion){workAssignmentDialog.close();toast('Work assignments saved.');}
 }catch(err){if(user===signedIn&&version===workAssignmentVersion)$('workAssignmentError').textContent=err.message;}
 finally{if(version===workAssignmentVersion)button.disabled=false;}
};

const workPayrollForm=$('workPayrollForm');
const workPayrollActions=$('workPayrollActions');
const workPayrollPrintReport=document.createElement('article');
workPayrollPrintReport.id='workPayrollPrintReport';
workPayrollPrintReport.hidden=true;
document.body.append(workPayrollPrintReport);
window.addEventListener('afterprint',()=>{
 document.body.classList.remove('printingPayroll');
 workPayrollPrintReport.replaceChildren();
});
let workPayrollPreview=null,workPayrollChoices=new Map();
const workPayrollIssueLabels={
 'missing-clock-in':'No clock-in matched this scheduled shift',
 'missing-clock-out':'Missing clock-out',
 'missing-break-end':'Missing break end',
 'no-break-recorded':'No break recorded'
};
function workPayrollHardStop(employee){
 return employee.has_punches===false||employee.open_punch||employee.issues?.some(issue=>issue.kind==='missing-break-end');
}
function workPayrollReviewIssues(employee){
 return employee.issues?.filter(issue=>['missing-clock-in','no-break-recorded'].includes(issue.kind))||[];
}
function workPayrollReset(){
 workPayrollPreview=null;
 workPayrollChoices.clear();
 $('workPayrollRows').replaceChildren();
 $('workPayrollStatus').textContent='';
 workPayrollActions.hidden=true;
}
function workPayrollTotals(employee,treatment){
 const preview=workPayrollPreview;
 const seconds=preview.breaks==='include'?employee.gross:employee.net;
 const overtime=treatment==='overtime'?Math.max(0,seconds-preview.threshold*3600):0;
 const totalCents=Math.round(seconds/36),overtimeCents=Math.round(overtime/36);
 return {regular:((totalCents-overtimeCents)/100).toFixed(2),overtime:(overtimeCents/100).toFixed(2),
  total:(totalCents/100).toFixed(2)};
}
function workPayrollSelection(){
 if(!workPayrollPreview)return;
 let selected=0,blocked=workPayrollPreview.unlinked>0;
 for(const row of $('workPayrollRows').querySelectorAll('[data-payroll-account]')){
  const employee=workPayrollPreview.employees.find(e=>e.account===row.dataset.payrollAccount);
  const include=row.querySelector('[data-payroll-include]'), treatment=row.querySelector('select');
  const review=row.querySelector('[data-payroll-reviewed]');
  if(review)review.disabled=!include.checked;
  treatment.disabled=!include.checked;
  const value=include.checked&&treatment.value?workPayrollTotals(employee,treatment.value):null;
  row.querySelector('[data-regular]').textContent=value?.regular??'—';
  row.querySelector('[data-overtime]').textContent=value?.overtime??'—';
  if(!include.checked)continue;
  selected++;
  if(!value||workPayrollHardStop(employee)||(review&&!review.checked))blocked=true;
 }
 workPayrollActions.hidden=blocked||selected===0;
}
function workPayrollRender(){
 const result=workPayrollPreview;
 $('workPayrollStatus').textContent=result.unlinked
  ? 'This week includes punches for removed accounts. Reconcile those hours before exporting.'
  : `${result.start} through ${result.end}. Review employee matches and hours in QuickBooks before submitting payroll.`;
 $('workPayrollRows').innerHTML=result.employees.length?`<div class="workGridScroll"><table class="workPayrollTable">
  <thead><tr><th>Include</th><th>Employee</th><th>Punch review</th><th>Overtime treatment</th><th>Total hours</th><th>Regular hours</th><th>Overtime hours</th></tr></thead>
  <tbody>${result.employees.map(employee=>{
   const choice=workPayrollChoices.get(employee.account);
   return `<tr data-payroll-account="${esc(employee.account)}">
    <td><input data-payroll-include type="checkbox" aria-label="Include ${esc(employee.name)}" ${choice?.included?'checked':''}></td>
    <th scope="row">${esc(employee.name)}</th>
    <td>${(employee.issues||[]).map(issue=>`<p class="payrollIssue">${esc(workPayrollIssueLabels[issue.kind]||issue.kind)} · ${esc(issue.at.replace('T',' '))}</p>`).join('')||
      (employee.open_punch?'<p class="payrollIssue">Missing clock-out</p>':'No flags')}
      ${workPayrollHardStop(employee)?(employee.has_punches===false?'<small>No recorded work hours to export.</small>':'<small>Correct the open punch or break before including these hours.</small>'):
       workPayrollReviewIssues(employee).length?`<label class="workAssignmentCheck"><input type="checkbox" data-payroll-reviewed aria-label="Reviewed flags for ${esc(employee.name)}" ${choice?.reviewed?'checked':''}> Reviewed flags</label>`:''}</td>
    <td><select aria-label="Overtime treatment for ${esc(employee.name)}">
     <option value="">Choose treatment</option><option value="overtime" ${choice?.treatment==='overtime'?'selected':''}>Apply weekly overtime</option>
     <option value="regular" ${choice?.treatment==='regular'?'selected':''}>All hours regular</option>
    </select></td><td>${((result.breaks==='include'?employee.gross:employee.net)/3600).toFixed(2)}</td><td data-regular>—</td><td data-overtime>—</td></tr>`;
  }).join('')}</tbody></table></div>`:'<p>No punches were recorded for this workweek.</p>';
 workPayrollSelection();
}
$('workPayrollRows').onchange=e=>{
 const row=e.target.closest('[data-payroll-account]');
 if(!row)return;
 workPayrollChoices.set(row.dataset.payrollAccount,{included:row.querySelector('[data-payroll-include]').checked,treatment:row.querySelector('select').value,reviewed:row.querySelector('[data-payroll-reviewed]')?.checked??false});
 workPayrollSelection();
};
workPayrollForm.oninput=e=>{
 if(e.target.name==='start'||e.target.name==='period'){
  workPayrollChoices.clear();
  const {start,period}=workPayrollForm.elements;
  const matchQuickBooks=period.value==='quickbooks';
  start.min=matchQuickBooks?'2000-01-01':'2000-01-02';
  start.step=matchQuickBooks?'1':'7';
  $('workPayrollOvertimeHelp').hidden=!matchQuickBooks;
  $('workPayrollRange').textContent=start.value&&start.validity.valid
   ? `${dateLabel(start.value)} through ${dateLabel(shiftDate(start.value,6))}`
   : matchQuickBooks?'Choose the first date shown under Pay period in QuickBooks.':'Choose the Sunday that starts the pay period.';
 }
 workPayrollPreview=null;
 $('workPayrollRows').replaceChildren();
 workPayrollActions.hidden=true;
 $('workPayrollStatus').textContent='';
};
workPayrollForm.onsubmit=async e=>{
 e.preventDefault();
 const signedIn=user,version=workVersion,button=e.submitter;
 const data=Object.fromEntries(new FormData(e.currentTarget));
 button.disabled=true;
 $('workPayrollStatus').textContent='Loading recorded hours…';
 try{
  const result=await workApi(workPayrollQuery(data));
  if(signedIn!==user||version!==workVersion)return;
  const current=Object.fromEntries(new FormData(workPayrollForm));
  if(Object.keys(data).some(key=>data[key]!==current[key]))return;
  for(const choice of workPayrollChoices.values())choice.reviewed=false;
  workPayrollPreview={...data,...result,threshold:Number(data.threshold)};

  workPayrollRender();
 }catch(err){if(signedIn===user&&version===workVersion)$('workPayrollStatus').textContent=err.message;}
 finally{button.disabled=false;}
};
function workPayrollCsvCell(value){
 let text=String(value);
 if(/^[\s]*[=+@-]|^[\t\r\n]/.test(text))text="'"+text;
 return '"'+text.replaceAll('"','""')+'"';
}
function workPayrollQuery({start,period,break_after}){
 return 'payroll?'+new URLSearchParams({start,period,break_after}).toString();
}
async function workPayrollExport(format){
 const buttons=workPayrollActions.querySelectorAll('button');
 if(!workData?.export_payroll||!workPayrollPreview||workPayrollActions.hidden||buttons[0].disabled)return;
 const signedIn=user,version=workVersion,preview=workPayrollPreview;
 const {start,end,employees}=preview;
 for(const button of buttons)button.disabled=true;
 try{
  const latest=await workApi(workPayrollQuery(preview));
  if(user!==signedIn||version!==workVersion||workPayrollPreview!==preview||workPayrollActions.hidden)return;
  if(latest.unlinked!==preview.unlinked||JSON.stringify(latest.employees)!==JSON.stringify(employees)){
   for(const choice of workPayrollChoices.values())choice.reviewed=false;
   workPayrollPreview={...preview,...latest};
   workPayrollRender();
   $('workPayrollStatus').textContent='Time records changed since the preview. Review the updated hours and flags before exporting.';
   return;
  }
 }catch(err){
  if(user===signedIn&&version===workVersion)$('workPayrollStatus').textContent=err.message;
  return;
 }finally{for(const button of buttons)button.disabled=false;}
 const rows=employees.filter(employee=>workPayrollChoices.get(employee.account)?.included).map(employee=>({
  name:employee.name,...workPayrollTotals(employee,workPayrollChoices.get(employee.account).treatment)
 }));
 if(format==='print')workPayrollPrint(preview,rows);
 else workPayrollCsv(start,end,rows);
}
$('workPayrollDownload').onclick=()=>workPayrollExport('csv');
$('workPayrollPrint').onclick=()=>workPayrollExport('print');
function workPayrollCsv(start,end,rows){
 const lines=[['Employee','Pay Period Start','Pay Period End','Regular Hours','Overtime Hours']];
 for(const row of rows)lines.push([row.name,start,end,row.regular,row.overtime]);
 const file=new Blob([lines.map(line=>line.map(workPayrollCsvCell).join(',')).join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'});
 const url=URL.createObjectURL(file),link=document.createElement('a');
 link.href=url;
 link.download=`quickbooks-payroll-${start}-to-${end}.csv`;
 link.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function workPayrollPrint({start,end,breaks},rows){
 workPayrollPrintReport.innerHTML=`<h1>Payroll Hours Report</h1>
  <p>MGC YFC Operations · ${esc(dateLabel(start))} through ${esc(dateLabel(end))}</p>
  <p>Hours are shown in decimal format. Recorded breaks ${breaks==='include'?'included':'excluded'}.</p>
  <table>
   <thead><tr><th scope="col">Employee</th><th scope="col">Regular Hours</th><th scope="col">Overtime Hours</th><th scope="col">Total Hours</th></tr></thead>
   <tbody>${rows.map(row=>`<tr><th scope="row">${esc(row.name)}</th><td>${row.regular}</td><td>${row.overtime}</td><td>${row.total}</td></tr>`).join('')}</tbody>
  </table>`;
 document.body.classList.add('printingPayroll');
 window.print();
}

let workTimeCards=[],workCardPeople=[],workEditingCard=null,workAuditNext=0;
function workCardReset(){
 workTimeCards=[];
 workCardPeople=[];
 workEditingCard=null;
 workAuditNext=0;
 $('workCardDialog').close();
 $('workCardForm').reset();
 for(const id of ['workTimeCards','workTimeAudit','workCardBreaks','workCardEmployee'])$(id).replaceChildren();
 $('workAuditOlder').hidden=true;
}
function workCardWhen(value){return value?value.replace('T',' '):'Open';}
function workRenderTimeCards(cards,people){
 workTimeCards=cards;workCardPeople=people;
 $('workAddCard').hidden=!workData?.add_time_cards;
 $('workTimeCards').innerHTML=cards.map(card=>`<article class="workRow"><div><strong>${esc(card.name)}</strong>
  <p>${esc(workCardWhen(card.start))} → ${esc(workCardWhen(card.end))}</p><p>${card.breaks.length} break${card.breaks.length===1?'':'s'}</p></div>
  ${workData?.edit_time_cards?`<button type="button" data-edit-card="${card.id}">Edit time card</button>`:''}</article>`).join('')||'<p>No time cards for this week.</p>';
}
$('workTimeCards').onclick=e=>{
 const button=e.target.closest('[data-edit-card]');
 if(!button)return;
 const card=workTimeCards.find(c=>c.id===Number(button.dataset.editCard));
 if(!card)return;
 workEditingCard=card;
 const form=$('workCardForm');
 form.reset();
 $('workCardTitle').textContent='Edit time card';
 $('workCardSave').textContent='Save correction';
 $('workCardPersonLabel').hidden=true;
 $('workCardAddBreak').hidden=true;
 form.elements.account.disabled=true;
 form.elements.account.required=false;
 form.elements.end.required=false;
 $('workCardEmployee').textContent=card.name;
 form.elements.start.value=card.start;
 form.elements.end.value=card.end;
 $('workCardError').textContent='';
 $('workCardBreaks').innerHTML=card.breaks.map((item,i)=>`<fieldset data-break-card="${item.id}"><legend>Break ${i+1}</legend>
  <label>Start<input data-start type="datetime-local" step="1" value="${esc(item.start)}" required></label>
  <label>End<input data-end type="datetime-local" step="1" value="${esc(item.end)}"></label></fieldset>`).join('');
 $('workCardDialog').showModal();
};
$('workCardCancel').onclick=()=>$('workCardDialog').close();
$('workCardForm').onsubmit=async e=>{
 e.preventDefault();
 const form=e.currentTarget,card=workEditingCard,signedIn=user,version=workVersion,button=e.submitter;
 if(!card&&!workData?.add_time_cards)return;
 button.disabled=true;
 $('workCardError').textContent='';
 const breaks=[...form.querySelectorAll('[data-break-card]')].map(row=>({
  id:Number(row.dataset.breakCard),start:row.querySelector('[data-start]').value,end:row.querySelector('[data-end]').value
 }));
 try{
  const data={start:form.elements.start.value,end:form.elements.end.value,reason:form.elements.reason.value,breaks};
  if(card)Object.assign(data,{id:card.id,revision:card.revision});
  else data.account=form.elements.account.value;
  await workApi(card?'edit-time-card':'add-time-card',data);
  if(user!==signedIn||version!==workVersion)return;
  $('workCardDialog').close();
  workPayrollReset();
  workStatus(card?'Correction saved and recorded in the audit log.':'Time card added and recorded in the audit log.');
  await workLoad();
 }catch(err){if(user===signedIn&&version===workVersion)$('workCardError').textContent=err.message;}
 finally{button.disabled=false;}
};
function workAuditSnapshot(label,card){
 if(!card)return `<div><strong>${label}</strong><p>No entry existed.</p></div>`;
 return `<div><strong>${label}</strong><p>Clock: ${esc(workCardWhen(card.start))} → ${esc(workCardWhen(card.end))}</p>
  ${card.breaks.map((b,i)=>`<p>Break ${i+1}: ${esc(workCardWhen(b.start))} → ${esc(workCardWhen(b.end))}</p>`).join('')}</div>`;
}
async function workLoadAudit(before=0){
 const signedIn=user,version=workVersion,button=$('workAuditOlder');
 button.disabled=true;
 try{
  const result=await workApi('time-card-audit'+(before?'?before='+before:''));
  if(user!==signedIn||version!==workVersion||workPanel.hidden)return;
  const content=result.entries.map(entry=>`<article class="workAuditEntry">
   <h4>${esc(entry.employee)} · Time card #${entry.period}</h4>
   <p>${esc(entry.actor)} · ${esc(entry.at.replace('T',' '))}</p>
   <p>${esc(entry.reason)}</p>
   <div class="workAuditComparison">${workAuditSnapshot('Before',entry.before)}${workAuditSnapshot('After',entry.after)}</div>
   </article>`).join('');
  if(before)$('workTimeAudit').insertAdjacentHTML('beforeend',content);
  else $('workTimeAudit').innerHTML=content||'<p>No corrections have been recorded.</p>';
  workAuditNext=result.entries.at(-1)?.id??0;
  button.hidden=!result.more;
 }catch(err){if(user===signedIn&&version===workVersion)workStatus(err.message);}
 finally{button.disabled=false;}
}
$('workAuditOlder').onclick=()=>{if(workAuditNext)workLoadAudit(workAuditNext);};

$('workAddCard').onclick=()=>{
 if(!workData?.add_time_cards)return;
 workEditingCard=null;
 const form=$('workCardForm'),fields=form.elements;
 form.reset();
 $('workCardTitle').textContent='Add time card';
 $('workCardSave').textContent='Save time card';
 $('workCardEmployee').textContent='';
 $('workCardError').textContent='';
 $('workCardBreaks').replaceChildren();
 $('workCardPersonLabel').hidden=false;
 $('workCardAddBreak').hidden=false;
 fields.account.replaceChildren(new Option('Choose an employee',''),...workCardPeople.map(person=>new Option(person.name,person.id)));
 fields.account.disabled=false;
 fields.account.required=true;
 fields.end.required=true;
 $('workCardDialog').showModal();
};
$('workCardAddBreak').onclick=()=>{
 const list=$('workCardBreaks');
 if(list.children.length>=20)return;
 const row=document.createElement('fieldset');
 row.dataset.breakCard='0';
 row.innerHTML='<legend>Break</legend><label>Start<input data-start type="datetime-local" step="1" required></label><label>End<input data-end type="datetime-local" step="1" required></label><button type="button">Remove break</button>';
 row.querySelector('button').onclick=()=>row.remove();
 list.append(row);
};

const userIdentityDialog=document.createElement('dialog');
userIdentityDialog.setAttribute('aria-labelledby','userIdentityTitle');
userIdentityDialog.innerHTML=`<form id="userIdentityForm">
 <h2 id="userIdentityTitle">Employee Profile</h2><p id="userIdentityPerson"></p>
 <button type="button" id="editDisplayName">Edit display name</button>
 <label>Login username<input name="username" maxlength="80" required autocomplete="off"></label>
 <label>Legal first name<input name="first" maxlength="80"></label>
 <label>Legal middle name<input name="middle" maxlength="80"></label>
 <label>Legal last name<input name="last" maxlength="80"></label>
 <p id="userIdentityError" role="alert"></p>
 <div class="actions"><button type="button" id="closeUserIdentity">Cancel</button><button type="submit" class="primary">Save names</button></div>
 </form>`;
document.body.append(userIdentityDialog);
let userIdentityTarget='',userIdentityVersion=0;
$('closeUserIdentity').onclick=()=>userIdentityDialog.close();
$('editDisplayName').onclick=()=>{
 userIdentityDialog.close();
 openRenameUser(userIdentityTarget);
};
$('users').addEventListener('click',async e=>{
 const button=e.target.closest('[data-user-identity]');
 if(!button)return;
 const name=button.dataset.userIdentity,version=++userIdentityVersion,signedIn=user;
 const form=$('userIdentityForm'),submit=form.querySelector('[type=submit]');
 userIdentityTarget=name;
 form.reset();
 submit.disabled=true;
 $('userIdentityPerson').textContent=name;
 $('userIdentityError').textContent='Loading account…';
 userIdentityDialog.showModal();
 try{
  const identity=await api('admin/user-identity?name='+encodeURIComponent(name));
  if(user!==signedIn||version!==userIdentityVersion||!userIdentityDialog.open)return;
  for(const key of ['username','first','middle','last'])form.elements[key].value=identity[key];
  $('userIdentityError').textContent='';
  submit.disabled=false;
 }catch(err){if(user===signedIn&&version===userIdentityVersion)$('userIdentityError').textContent=err.message;}
});
$('userIdentityForm').onsubmit=async e=>{
 e.preventDefault();
 const button=e.submitter,version=userIdentityVersion,signedIn=user;
 const data={...Object.fromEntries(new FormData(e.currentTarget)),name:userIdentityTarget};
 button.disabled=true;
 try{
  await api('admin/user-identity',data);
  if(user===signedIn&&version===userIdentityVersion){userIdentityDialog.close();toast('Employee profile saved.');}
 }catch(err){if(user===signedIn&&version===userIdentityVersion)$('userIdentityError').textContent=err.message;}
 finally{if(version===userIdentityVersion)button.disabled=false;}
};

// Responsive manager scheduling and accessible menus.
const workDesktop=window.matchMedia('(min-width: 1024px)');
function workIsDesktop(){return mobileViewMode==='desktop'||(mobileViewMode!=='mobile'&&workDesktop.matches);}
function workLayoutChanged(){
 if(workData)workRender(workData);
 if(!workIsDesktop()&&workView==='team'&&!workPanel.hidden){$('workCopyDialog').close();workSelect('mine');}
}
workDesktop.addEventListener('change',workLayoutChanged);
$('mobileViewMode').addEventListener('change',workLayoutChanged);
$('workAvailabilityEdit').onclick=()=>workRequestOpen('availability');
$('workCopyWeek').onclick=()=>{
 const form=$('workCopyForm');form.elements.source.value=workWeek;form.elements.target.value=workDateOffset(workWeek,7);
 $('workCopyError').textContent='';$('workCopyDialog').showModal();
};
$('workCopyCancel').onclick=()=>$('workCopyDialog').close();
$('workCopyForm').onsubmit=async e=>{
 e.preventDefault();const button=e.submitter,signedIn=user,version=workVersion;button.disabled=true;$('workCopyError').textContent='';
 try{const values=Object.fromEntries(new FormData(e.currentTarget));const result=await workApi('copy-week',values);
  if(user!==signedIn||version!==workVersion||workPanel.hidden)return;
  $('workCopyDialog').close();workWeek=values.target;workSelect('team');workStatus(`Copied ${result.copied} ${result.copied===1?'shift':'shifts'}.`);
 }catch(error){$('workCopyError').textContent=error.message;}finally{button.disabled=false;}
};
for(const menu of workPanel.querySelectorAll('.workDropdown'))menu.addEventListener('toggle',()=>{
 if(menu.open)for(const other of workPanel.querySelectorAll('.workDropdown'))if(other!==menu)other.open=false;
});
document.addEventListener('pointerdown',e=>{for(const menu of document.querySelectorAll('.workDropdown,.headerMenu'))if(!menu.contains(e.target))menu.open=false;});
document.addEventListener('keydown',e=>{if(e.key==='Escape')for(const menu of document.querySelectorAll('.workDropdown,.headerMenu'))if(menu.open){menu.open=false;menu.querySelector('summary').focus();}});
const headerMenu=document.createElement('details');headerMenu.className='headerMenu';
headerMenu.innerHTML='<summary>Menu <span aria-hidden="true">▾</span></summary><div id="headerMenuItems"></div>';
$('storeMenuButton').parentElement.append(headerMenu);
for(const id of ['chooseStartSection','appearanceMenu'])if($(id))$('headerMenuItems').append($(id));
// Move the utility actions at the bottom of Pages, preserving their existing handlers.
for(const button of [...$('storeMenu').children])if(!/Section$/.test(button.id))$('headerMenuItems').append(button);
headerMenu.addEventListener('click',e=>{if(e.target.closest('button'))headerMenu.open=false;});
$('storeMenuButton').before($('currentSection'));
$('storeMenuButton').innerHTML='View Panel <span aria-hidden="true">▾</span>';

const workJobsPanel=document.createElement('div');workJobsPanel.className='panel';workJobsPanel.hidden=true;
workJobsPanel.innerHTML='<h2>Jobs</h2><p>Each job has a section in manager Scheduling. Assign employees to jobs under Users → Work assignments. Existing employee assignments are included automatically.</p><form id="workJobsForm"><label>Job names (one per line)<textarea name="jobs" rows="8" maxlength="16200"></textarea></label><button class="primary">Save jobs</button></form><p id="workJobsStatus" role="status"></p>';
settingsPanels.push(workJobsPanel);settingsNames.push('Jobs');settingsGroups[0].panels.push(12);$('settings').append(workJobsPanel);
async function loadWorkJobs(){
 const form=$('workJobsForm');form.querySelector('button').disabled=true;$('workJobsStatus').textContent='Loading jobs…';
 try{const data=await workApi('jobs');form.elements.jobs.value=data.jobs.join('\n');$('workJobsStatus').textContent='';form.querySelector('button').disabled=false;}
 catch(error){$('workJobsStatus').textContent=error.message;}
}
$('workJobsForm').onsubmit=async e=>{
 e.preventDefault();e.submitter.disabled=true;
 try{await workApi('jobs',{jobs:e.currentTarget.elements.jobs.value.split(/\r?\n/).map(j=>j.trim()).filter(Boolean)});$('workJobsStatus').textContent='Jobs saved.';}
 catch(error){$('workJobsStatus').textContent=error.message;}finally{e.submitter.disabled=false;}
};

// Connection presence contains status only, never form contents or session tokens.
const updateConnectionsPanel=document.createElement('section');
updateConnectionsPanel.id='updateConnectionsPanel';updateConnectionsPanel.hidden=true;
updateConnectionsPanel.innerHTML=`<div class="connectionPanelHead"><h3>Connections before updating</h3><button type="button" id="refreshUpdateConnections">Refresh connections</button></div>
 <p id="updateConnectionsStatus" role="status">Checking connections…</p>
 <p>Your current connection is excluded. Notify others and wait for them to finish, or install immediately when no other connections remain. Other tabs still count separately.</p>
 <div id="updateConnectionsList"></div><p id="updateConnectionsChecked" class="connectionPanelNote"></p>
 <p class="connectionPanelNote">Activity means interacting with the app, not automatic polling. The local server controller is excluded. Inactive users do not delay updates; unsaved work may be interrupted. Check guest activity separately.</p>`;
$('updateConfig').before(updateConnectionsPanel);
let updateConnectionsState=null,updateConnectionsChecking=false,updateConnectionsAt=0;
function updateInstallButton(){
 $('installUpdate').disabled=updateBusy||!!(user?.admin&&(!updateConnectionsState||Date.now()-updateConnectionsAt>30000||updateConnectionsState.other_connections));
}
function connectionAge(stamp,now){
 if(stamp===null)return 'PIN access in progress';
 const seconds=Math.max(0,Math.floor(now-stamp));
 return seconds<60?'Just now':seconds<3600?Math.floor(seconds/60)+' min ago':Math.floor(seconds/3600)+' hr ago';
}
async function refreshUpdateConnections(){
 updateConnectionsPanel.hidden=!user?.admin;
 if(!user?.admin){updateConnectionsState=null;updateInstallButton();return false;}
 if(updateConnectionsChecking)return false;
 const signedIn=user;updateConnectionsChecking=true;$('refreshUpdateConnections').disabled=true;
 try{
  const result=await api('admin/update-connections');
  if(user!==signedIn)return false;
  updateConnectionsState=result;updateConnectionsAt=Date.now();
  updateConnectionsPanel.dataset.blocked=String(result.other_connections>0);
  $('updateConnectionsStatus').textContent=result.other_connections?`${result.other_connections} other active ${result.other_connections===1?'connection':'connections'} — use the notification option or wait.`:'No other active users. Inactive connections do not hold updates.';
  $('updateConnectionsList').innerHTML=result.connections.filter(row=>!row.current).map(row=>`<article class="updateConnectionRow"><div><strong>${esc(row.name)}${row.current?' · You (this connection)':''}</strong><span>${esc(row.kind)}</span></div><div><b>${({active:'Active',inactive:'Inactive'})[row.status]}</b><span>Last activity: ${connectionAge(row.last_active,result.checked_at)}</span><span>Last seen: ${connectionAge(row.last_seen,result.checked_at)}</span></div></article>`).join('')||'<p>No signed-in connections reported.</p>';
  $('updateConnectionsChecked').textContent='Checked '+new Date(result.checked_at*1000).toLocaleTimeString()+'. Inactive after '+result.inactive_minutes+' minutes without interaction. Refreshes every 15 seconds.';
  return result.other_connections===0;
 }catch(error){
  if(user===signedIn){updateConnectionsState=null;updateConnectionsPanel.dataset.blocked='true';$('updateConnectionsStatus').textContent='Connection status unavailable. Installation is disabled until the status can be checked.';$('updateConnectionsList').replaceChildren();$('updateConnectionsChecked').textContent='';}
  return false;
 }finally{updateConnectionsChecking=false;$('refreshUpdateConnections').disabled=false;updateInstallButton();}
}
$('refreshUpdateConnections').onclick=refreshUpdateConnections;
function sendConnectionPresence(closing=false){
 if(!user)return;
 fetch('/api/account/connection',{method:'POST',headers:{'Content-Type':'application/json','X-Dispatch':'1','X-Dispatch-Connection':connectionId},body:JSON.stringify({closing}),keepalive:closing}).catch(()=>{});
}
setInterval(()=>{sendConnectionPresence();if(user?.admin&&!$('settings').hidden&&!$('updatePanel').hidden)refreshUpdateConnections();else updateInstallButton();},15000);
window.addEventListener('pagehide',event=>{if(!event.persisted)sendConnectionPresence(true);});
window.addEventListener('pageshow',()=>sendConnectionPresence());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)sendConnectionPresence();});
// Settings and account editors use the existing APIs without changing stored access on load.
function buildPermissionEditor(container,toolbar,catalog,groups,grants,attribute,locked){
 toolbar.className='permissionTools';toolbar.replaceChildren();container.replaceChildren();
 const category=document.createElement('select');category.setAttribute('aria-label','Permission category');category.add(new Option('All categories',''));
 for(const name of Object.keys(groups))category.add(new Option(name,name));
 const search=document.createElement('input');search.type='search';search.placeholder='Find a permission';search.setAttribute('aria-label','Find a permission');
 const count=document.createElement('p');count.className='permissionCount';count.setAttribute('role','status');
 const rows=[];
 for(const [group,keys]of Object.entries(groups))for(const key of keys){
  const row=document.createElement('label');row.className='permissionRow';row.dataset.category=group;
  const text=document.createElement('span');text.innerHTML=`<strong>${esc(catalog[key])}</strong><small>${esc(group)}</small>`;
  const control=document.createElement('span');control.className='permissionToggle';
  const input=document.createElement('input');input.type='checkbox';input.dataset[attribute]=key;input.checked=!!grants[key];input.disabled=locked(key);
  const status=document.createElement('span');const update=()=>{status.textContent=input.checked?'Enabled':'Disabled';row.dataset.enabled=String(input.checked);};input.onchange=update;update();
  control.append(input,status);row.append(text,control);container.append(row);rows.push(row);
 }
 const filter=()=>{const query=search.value.trim().toLowerCase();for(const row of rows)row.hidden=!!((category.value&&row.dataset.category!==category.value)||(query&&!row.textContent.toLowerCase().includes(query)));const visible=rows.filter(row=>!row.hidden);count.textContent=`${visible.length} of ${rows.length} permissions shown`;};
 const categoryLabel=document.createElement('label');categoryLabel.append('Category',category);
 const searchLabel=document.createElement('label');searchLabel.append('Filter',search);
 toolbar.append(categoryLabel,searchLabel);
 for(const [label,value]of [['Enable shown',true],['Disable shown',false]]){const button=document.createElement('button');button.type='button';button.textContent=label;button.onclick=()=>{for(const row of rows){const input=row.querySelector('input');if(!row.hidden&&!input.disabled){input.checked=value;input.dispatchEvent(new Event('change',{bubbles:true}));}}};toolbar.append(button);}
 const clear=document.createElement('button');clear.type='button';clear.textContent='Clear filter';clear.onclick=()=>{category.value='';search.value='';filter();};toolbar.append(clear,count);
 category.onchange=search.oninput=filter;filter();
}

const settingsHeading=document.createElement('div');settingsHeading.className='settingsHeading';settingsHeading.innerHTML='<p class="eyebrow">ADMINISTRATION & PREFERENCES</p><h1>Settings</h1><p>Choose an area to manage your application.</p>';$('settings').prepend(settingsHeading);
for(const panel of settingsPanels){const back=document.createElement('button');back.type='button';back.className='settingsBack';back.textContent='‹ Back to settings';back.onclick=()=>settingsCategory(selectedSettingsCategory);panel.prepend(back);}

const roleTabs=document.createElement('nav');roleTabs.className='editorTabs';roleTabs.setAttribute('aria-label','Role editor');
const roleProperties=document.createElement('section');roleProperties.id='roleProperties';
const roleNameLabel=$('roleName').closest('label');roleProperties.append(roleNameLabel);
const roleAssignmentCount=document.createElement('p');roleAssignmentCount.id='roleAssignmentCount';roleProperties.append(roleAssignmentCount);
const rolePermissionPanel=document.createElement('section');rolePermissionPanel.id='rolePermissionPanel';rolePermissionPanel.hidden=true;rolePermissionPanel.append($('roleCategories'),$('rolePermissions'));
$('roleForm').prepend(roleTabs,roleProperties,rolePermissionPanel);
for(const name of ['properties','permissions']){const b=document.createElement('button');b.type='button';b.dataset.roleTab=name;b.textContent=name[0].toUpperCase()+name.slice(1);b.onclick=()=>selectRoleEditorTab(name);roleTabs.append(b);}
function selectRoleEditorTab(name){roleProperties.hidden=name!=='properties';rolePermissionPanel.hidden=name!=='permissions';for(const b of roleTabs.children){const selected=b.dataset.roleTab===name;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));}}
const roleCancel=document.createElement('button');roleCancel.type='button';roleCancel.textContent='Cancel changes';roleCancel.onclick=()=>{if(rolesData)showRole();};$('roleForm').append(roleCancel);
$('roleForm').querySelector('[type=submit]').classList.add('primary');

// Keep password, role assignment and personal details as separate forms/actions.
const userEditor=$('passwordDialog');userEditor.classList.add('userEditor');userEditor.setAttribute('aria-labelledby','userEditorTitle');
const editorHeading=$('passwordForm').querySelector('.dialogTop');
editorHeading.querySelector('h2').id='userEditorTitle';editorHeading.querySelector('h2').textContent='Edit user';
userEditor.prepend(editorHeading);
const userEditorSummary=document.createElement('p');userEditorSummary.id='userEditorSummary';editorHeading.after(userEditorSummary);
const userEditorTabs=document.createElement('nav');userEditorTabs.className='editorTabs';userEditorTabs.setAttribute('aria-label','User setup');userEditorSummary.after(userEditorTabs);
const userEditorPanels={};
for(const [name,label]of [['properties','Properties'],['role','Role'],['personal','Personal'],['view','User view']]){const button=document.createElement('button');button.type='button';button.dataset.userTab=name;button.textContent=label;button.onclick=()=>selectUserEditorTab(name);userEditorTabs.append(button);const panel=document.createElement('section');panel.id='userEditor_'+name;panel.hidden=true;userEditor.append(panel);userEditorPanels[name]=panel;}
userEditorPanels.properties.append($('passwordForm'));
userEditorPanels.role.append($('permissionFields'));$('permissionFields').querySelector('legend').textContent='Role assignment';
$('savePermissions').textContent='Save role assignment';
const roleSummary=document.createElement('p');roleSummary.id='userRoleSummary';employeeRoleLabel.after(roleSummary);
const accessButtons=document.createElement('div');accessButtons.className='actions';accessButtons.innerHTML='<button type="button" id="manageUserRole">Manage roles</button><button type="button" id="editIndividualAccess">Edit individual access</button>';$('permissionFields').append(accessButtons);
const individualDialog=document.createElement('dialog');individualDialog.className='permissionEditorDialog';individualDialog.setAttribute('aria-labelledby','individualTitle');individualDialog.innerHTML='<h2 id="individualTitle">Individual access</h2><p>These permissions apply only to this employee. Shared roles can be managed in Settings → Roles.</p><nav id="individualTools"></nav><p id="individualStatus" role="status"></p><div class="actions"><button type="button" id="individualCancel">Cancel</button><button type="button" class="primary" id="individualSave">Save individual access</button></div>';document.body.append(individualDialog);$('individualTools').after($('permissionChecklist'));
$('editIndividualAccess').onclick=()=>{if(!employeeRolesData||employeeRole.value||!user.admin)return;buildPermissionEditor($('permissionChecklist'),$('individualTools'),permissionCatalog,employeeRolesData.groups,employeeIndividualGrants,'grant',()=>false);$('individualStatus').textContent='';individualDialog.showModal();};
$('individualCancel').onclick=()=>individualDialog.close();
$('individualSave').onclick=async()=>{const button=$('individualSave');button.disabled=true;try{if(employeeHadRole)throw Error('Save the switch to individual access first.');const grants=Object.fromEntries([...$('permissionChecklist').querySelectorAll('[data-grant]')].map(input=>[input.dataset.grant,input.checked]));await api('admin/permissions',{name:$('passwordUser').value,grants,can_create:grants.create_appointments,see_requests:grants.see_requests});employeeIndividualGrants=grants;setEmployeeRoleMode();individualDialog.close();$('permissionMessage').textContent='Individual permissions saved.';}catch(e){$('individualStatus').textContent=e.message;}finally{button.disabled=false;}};
$('manageUserRole').onclick=()=>{const role=employeeRole.value;closePassword();settingsSection(4);selectUserSettings('roles');if(role)loadRoles(role);};
userEditorPanels.personal.innerHTML='<form id="userPersonalForm"><h3>Personal & login details</h3><div class="userFieldGrid"><label>Login username<input name="username" maxlength="80" required autocomplete="off"></label><label>Legal first name<input name="first" maxlength="80"></label><label>Legal middle name<input name="middle" maxlength="80"></label><label>Legal last name<input name="last" maxlength="80"></label></div><p id="userPersonalStatus" role="status"></p><button type="submit" class="primary">Save personal details</button></form>';
userEditorPanels.view.innerHTML='<h3>Access overview</h3><p>Preview based on the selected role or existing individual access. Unsaved role selections are previews only.</p><div id="userAccessPreview" class="accessPreview"></div>';
const propertyActions=document.createElement('div');propertyActions.className='userPropertyActions';propertyActions.innerHTML='<h3>Account actions</h3><div id="userPropertyButtons" class="actions"></div>';
userEditorPanels.properties.prepend(propertyActions);
function selectUserEditorTab(name){for(const [key,panel]of Object.entries(userEditorPanels))panel.hidden=key!==name;for(const button of userEditorTabs.children){const selected=button.dataset.userTab===name;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));}}
function renderUserAccessPreview(grants,admin){const items=[['Dispatch',admin||grants.view_schedule],['Paging',admin||grants.send_pages||grants.receive_pages],['Receipts & Accounting',true],['Print with a Purpose',true],['My Timekeeping',true],['Manager scheduling',admin||grants.manage_staff_schedule],['Payroll export',admin||grants.export_payroll],['Role management',admin||grants.manage_roles]];$('userAccessPreview').innerHTML=items.map(([label,enabled])=>`<div><strong>${label}</strong><span>${enabled?'Available':'Not enabled'}</span></div>`).join('');}
async function openUserSetup(name){
 const person=state.users.find(p=>p.name===name);if(!person)return;
 $('userEditorTitle').textContent='Edit user';$('userEditorSummary').textContent=name+' · '+(person.admin?'Administrator':'Employee');
 $('passwordForm').hidden=!(can('reset_passwords')&&(!person.admin||user.admin));
 const buttons=$('userPropertyButtons');buttons.replaceChildren();
 for(const [attribute,label,allowed]of [['userIdentity','Edit display name / profile',can('rename_users')&&(!person.admin||user.admin)],['clockPin','Time Clock PIN',can('reset_passwords')&&(!person.admin||user.admin)],['workAssignment','Work assignments',can('manage_staff_schedule')]])if(allowed){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=()=>{const original=[...$('users').querySelectorAll('button')].find(item=>item.dataset[attribute]===name);if(original){closePassword();original.click();}};buttons.append(b);}
 const personal=$('userPersonalForm');personal.reset();for(const field of personal.elements)field.disabled=true;$('userPersonalStatus').textContent=can('rename_users')?'Loading personal details…':'Edit user names permission is required to view or change these details.';
 $('userAccessPreview').textContent='Load the user’s access to see an overview.';
 selectUserEditorTab('properties');userEditor.showModal();loadPermissionList(name);
 if(can('rename_users')){const signedIn=user,version=employeePermissionVersion;try{const identity=await api('admin/user-identity?name='+encodeURIComponent(name));if(user!==signedIn||version!==employeePermissionVersion||!userEditor.open)return;for(const key of ['username','first','middle','last'])personal.elements[key].value=identity[key];for(const field of personal.elements)field.disabled=false;$('userPersonalStatus').textContent='';}catch(e){if(userEditor.open&&$('passwordUser').value===name)$('userPersonalStatus').textContent=e.message;}}
}
$('userPersonalForm').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{await api('admin/user-identity',{...Object.fromEntries(new FormData(e.currentTarget)),name:$('passwordUser').value});$('userPersonalStatus').textContent='Personal details saved.';}catch(error){$('userPersonalStatus').textContent=error.message;}finally{button.disabled=false;}};
userEditor.addEventListener('close',()=>{++employeePermissionVersion;individualDialog.close();});

$('roleName').addEventListener('invalid',()=>selectRoleEditorTab('properties'));
// Coordinated updates: finishing work, acknowledgement, then an automatic restart.
let updateFlow=null,updateFlowSeen='',updateFlowMandatory=false,updateFlowPolling=false,flowReceipt=null;
let writesInFlight=0,submittedForm=null;
const changedForms=new Map();
const formSnapshot=form=>JSON.stringify([...new FormData(form)].map(([key,value])=>[key,typeof value==='string'?value:[value.name,value.size,value.lastModified]]));
document.addEventListener('input',event=>{const form=event.target.form;if(form)changedForms.set(form,formSnapshot(form));},true);
document.addEventListener('change',event=>{const form=event.target.form;if(form)changedForms.set(form,formSnapshot(form));},true);
document.addEventListener('reset',event=>changedForms.delete(event.target),true);
document.addEventListener('submit',event=>{submittedForm=event.target;const form=event.target;setTimeout(()=>{if(submittedForm===form)submittedForm=null;},0);},true);
const apiBeforeCoordination=api;
api=async function(path,data){
 const mutation=!!data&&!['account/activity','account/connection','update-check','pos-update/heartbeat'].includes(path)&&!path.includes('update-flow');
 const form=mutation?submittedForm:null,snapshot=form?formSnapshot(form):null;
 if(mutation)writesInFlight++;
 try{const result=await apiBeforeCoordination(path,data);if(form&&formSnapshot(form)===snapshot)changedForms.delete(form);return result;}
 finally{if(mutation)writesInFlight--;}
};
function hasUnfinishedWork(){
 for(const form of [...changedForms.keys()]){if(!form.isConnected){changedForms.delete(form);continue;}const dialog=form.closest('dialog');if((!dialog||dialog.open)&&!form.closest('[hidden]'))return true;}
 return writesInFlight>0||shiftAutoBusy||shiftAutoDirty||!!shiftAutoAttempt||!!receiptBusy||!!workBusy;
}
const updatePendingBadge=document.createElement('button');updatePendingBadge.id='updatePendingBadge';updatePendingBadge.type='button';updatePendingBadge.hidden=true;updatePendingBadge.textContent='Update pending';document.querySelector('body>header').append(updatePendingBadge);
const updateFlowDialog=document.createElement('dialog');updateFlowDialog.id='updateFlowDialog';updateFlowDialog.setAttribute('aria-labelledby','updateFlowTitle');
updateFlowDialog.innerHTML='<h2 id="updateFlowTitle">Update pending</h2><p id="updateFlowMessage"></p><div id="updateFlowPeople"></div><p id="updateFlowError" role="status"></p><div class="actions"><button type="button" id="minimizeUpdateFlow">Finish my current task</button><button type="button" class="primary" id="acknowledgeUpdateFlow">My work is saved — ready to update</button><button type="button" id="cancelUpdateFlow">Cancel update request</button><button type="button" id="finishUpdateFlow" hidden>Return to sign in</button></div>';
document.body.append(updateFlowDialog);
const updateFlowActions=document.createElement('div');updateFlowActions.className='updateFlowActions';updateFlowActions.innerHTML='<button type="button" id="requestCoordinatedUpdate">Notify users & update when ready</button><p>Users may finish their current task. The server updates automatically after everyone is ready.</p>';$('installUpdate').before(updateFlowActions);
function renderUpdateFlow(){
 if(!updateFlow)return;
 const phase=updateFlow.phase,terminal=['complete','failed','canceled'].includes(phase),owner=updateFlow.requester;
 updatePendingBadge.hidden=terminal;updatePendingBadge.textContent=updateFlow.ready?'Ready for update':'Update pending';
 $('minimizeUpdateFlow').hidden=owner||updateFlowMandatory||updateFlow.ready||terminal;
 $('acknowledgeUpdateFlow').hidden=owner||updateFlow.ready||terminal;
 $('cancelUpdateFlow').hidden=!owner||phase!=='waiting';
 $('finishUpdateFlow').hidden=!terminal;
 $('finishUpdateFlow').textContent=phase==='complete'?'Update complete — sign in':phase==='failed'?'Close update notice':'Return to work';
 $('updateFlowTitle').textContent=phase==='complete'?'Update complete':phase==='failed'?'Update could not finish':phase==='canceled'?'Update canceled':owner?'Coordinating update':updateFlow.ready?'Ready — waiting for update':updateFlowMandatory?'The system will now update':'Update pending';
 $('updateFlowMessage').textContent=phase==='complete'?`Version ${updateFlow.version} is installed. Your saved work is retained.`:phase==='failed'?(updateFlow.error||'The update was not completed.'):phase==='canceled'?'You can continue working.':phase==='preparing'?'Downloading and verifying the update. Other users can continue their current tasks.':phase==='applying'?'Everyone is ready. Installing the update and restarting the server…':owner?`Waiting for ${updateFlow.waiting} other active connection(s). Your requesting connection and the local server controller are excluded. Installation starts automatically when everyone is ready.`:updateFlow.ready?'Your connection is paused. The update will begin after everyone has acknowledged.':updateFlowMandatory?'Confirm that your work is saved. Your connection will then pause until the update finishes.':'An update is pending. Finish your current form or task. You can minimize this notice to the header. When you leave this page, acknowledgement will be required.';
 $('updateFlowPeople').innerHTML=owner?(updateFlow.connections||[]).map(p=>`<div class="updateConnectionRow"><strong>${esc(p.name)}</strong><span>${esc(p.kind)} · ${esc(p.status)}</span></div>`).join(''):'';
}
function showUpdateFlow(mandatory=false){updateFlowMandatory ||= mandatory;renderUpdateFlow();if(!updateFlowDialog.open)updateFlowDialog.showModal();}
updateFlowDialog.addEventListener('cancel',event=>{event.preventDefault();if(!updateFlowMandatory&&!updateFlow?.requester&&!updateFlow?.ready)updateFlowDialog.close();});
$('minimizeUpdateFlow').onclick=()=>updateFlowDialog.close();updatePendingBadge.onclick=()=>showUpdateFlow();
function updateFlowPath(action=''){return (workQuick?'workforce/quick/update-flow':'update-flow')+(action?'/'+action:'');}
function rememberFlow(result){if(result.receipt){flowReceipt=result.receipt;try{sessionStorage.setItem('yfc-update-receipt',flowReceipt);}catch{}}}
async function pollUpdateFlow(){
 if(updateFlowPolling)return;updateFlowPolling=true;
 try{
  if(flowReceipt){
   const response=await fetch('/api/update-result?receipt='+encodeURIComponent(flowReceipt),{signal:AbortSignal.timeout(5000)});
   if(response.ok){const result=await response.json();if(['complete','failed','canceled'].includes(result.phase)){updateFlow={...updateFlow,...result};showUpdateFlow(true);return;}if(result.phase==='applying'){updateFlow={...updateFlow,...result};showUpdateFlow(true);return;}}
  }
  if(!user&&!workQuick)return;
  const result=await api(updateFlowPath());
  if(!result.active){if(updateFlow&&['failed','canceled'].includes(result.phase)){updateFlow=result;showUpdateFlow(true);}return;}
  updateFlow=result;rememberFlow(result);renderUpdateFlow();
  if(updateFlowSeen!==result.id){updateFlowSeen=result.id;updateFlowMandatory=false;showUpdateFlow(result.requester||result.ready);}
  else if(result.ready||result.requester)showUpdateFlow(true);
 }catch(error){if(updateFlowDialog.open&&updateFlow)$('updateFlowError').textContent='Waiting for the server. Keep this page open; completion will be confirmed after it reconnects.';}
 finally{updateFlowPolling=false;}
}
$('requestCoordinatedUpdate').onclick=async()=>{
 if(!updateVersion){$('updateStatus').textContent='Check for an available update first.';return;}
 if(hasUnfinishedWork()){toast('Save or finish your current work before requesting the update.');return;}
 if(!confirm('Your current work is saved. Notify other users, wait for their acknowledgement, then install automatically?'))return;
 const button=$('requestCoordinatedUpdate');button.disabled=true;
 try{updateFlow=await api('update-flow/start',{version:updateVersion,ready:true});rememberFlow(updateFlow);updateFlowSeen=updateFlow.id;showUpdateFlow(true);}
 catch(error){$('updateStatus').textContent=error.message;}finally{button.disabled=false;}
};
$('acknowledgeUpdateFlow').onclick=async()=>{
 if(hasUnfinishedWork()){ $('updateFlowError').textContent='There is unfinished work or a save still in progress. Finish and save it before acknowledging.';return;}
 const button=$('acknowledgeUpdateFlow');button.disabled=true;
 try{updateFlow=await api(updateFlowPath('acknowledge'),{id:updateFlow.id,ready:true});rememberFlow(updateFlow);showUpdateFlow(true);$('updateFlowError').textContent='';}
 catch(error){$('updateFlowError').textContent=error.message;}finally{button.disabled=false;}
};
$('cancelUpdateFlow').onclick=async()=>{try{await api('update-flow/cancel',{id:updateFlow.id});await pollUpdateFlow();}catch(error){$('updateFlowError').textContent=error.message;}};
$('finishUpdateFlow').onclick=()=>{const complete=updateFlow?.phase==='complete';updateFlow=null;flowReceipt=null;updateFlowMandatory=false;updatePendingBadge.hidden=true;try{sessionStorage.removeItem('yfc-update-receipt');}catch{}updateFlowDialog.close();if(complete)location.reload();};
function guardUpdateNavigation(){
 if(!updateFlow?.active||updateFlow.requester)return true;
 if(hasUnfinishedWork()){toast('An update is pending. Finish or save your current task before changing pages.');return false;}
 showUpdateFlow(true);return false;
}
for(const [get,set]of [[()=>tab,v=>tab=v],[()=>storeSection,v=>storeSection=v],[()=>workSelect,v=>workSelect=v],[()=>settingsSection,v=>settingsSection=v],[()=>settingsCategory,v=>settingsCategory=v],[()=>openReceiptHistory,v=>openReceiptHistory=v],[()=>workOpen,v=>workOpen=v],[()=>chooseLanding,v=>chooseLanding=v],[()=>commOpen,v=>commOpen=v],[()=>commOpenThread,v=>commOpenThread=v],[()=>openReceiptUpload,v=>openReceiptUpload=v]]){const original=get();set(function(...args){if(!guardUpdateNavigation())return original.constructor.name==='AsyncFunction'?Promise.resolve(false):false;return original.apply(this,args);});}
try{flowReceipt=sessionStorage.getItem('yfc-update-receipt');}catch{}
setInterval(pollUpdateFlow,3000);setTimeout(pollUpdateFlow,1000);
window.addEventListener('beforeunload',event=>{if(hasUnfinishedWork()){event.preventDefault();event.returnValue='';}});

// Every valid shift edit is persisted; retries reuse an immutable operation key.
let shiftAutoDirty=false,shiftAutoBusy=false,shiftAutoAttempt=null,shiftAutoTimer=null,shiftAutoLast='';
const shiftForm=$('workShiftForm');
const shiftSaveStatus=document.createElement('p');shiftSaveStatus.id='shiftSaveStatus';shiftSaveStatus.setAttribute('role','status');shiftForm.prepend(shiftSaveStatus);
const originalEditShift=workEditShift;
workEditShift=function(...args){if(shiftAutoBusy||shiftAutoDirty||shiftAutoAttempt){toast('Finish saving the open shift first.');return;}originalEditShift(...args);shiftAutoLast=formSnapshot(shiftForm);shiftSaveStatus.textContent='Changes save automatically. Invalid or incomplete fields stay here until corrected.';};
function queueShiftSave(){shiftAutoDirty=formSnapshot(shiftForm)!==shiftAutoLast;clearTimeout(shiftAutoTimer);shiftSaveStatus.textContent='Unsaved changes…';shiftAutoTimer=setTimeout(saveShiftAutomatically,650);}
shiftForm.addEventListener('input',queueShiftSave);shiftForm.addEventListener('change',queueShiftSave);
async function saveShiftAutomatically(){
 clearTimeout(shiftAutoTimer);if(shiftAutoBusy)return false;
 if(!shiftAutoDirty&&!shiftAutoAttempt)return true;
 if(!shiftAutoAttempt&&!shiftForm.checkValidity()){shiftSaveStatus.textContent='Not saved yet — complete the required fields.';return false;}
 shiftAutoBusy=true;
 try{
  while(shiftAutoDirty||shiftAutoAttempt){
   if(!shiftAutoAttempt){
    if(!shiftForm.checkValidity())return false;
    const snapshot=formSnapshot(shiftForm),data=Object.fromEntries(new FormData(shiftForm));
    if(workEditingShift)Object.assign(data,{id:workEditingShift.id,revision:workEditingShift.revision});
    data.save_request=Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join('');
    shiftAutoAttempt={data,snapshot};
   }
   shiftSaveStatus.textContent='Saving…';
   const attempt=shiftAutoAttempt,result=await workApi('shift',attempt.data);
   workEditingShift={...attempt.data,...result.shift};$('workDeleteShift').hidden=false;
   shiftAutoLast=attempt.snapshot;shiftAutoAttempt=null;shiftAutoDirty=formSnapshot(shiftForm)!==shiftAutoLast;
   if(!shiftAutoDirty)changedForms.delete(shiftForm);
  }
  $('workShiftError').textContent='';shiftSaveStatus.textContent='All changes saved.';return true;
 }catch(error){if(error.status>=400&&error.status<500)shiftAutoAttempt=null;shiftSaveStatus.textContent='Not saved — your edits are still in this form.';$('workShiftError').textContent=error.message+' Use Save & close to retry.';return false;}
 finally{shiftAutoBusy=false;}
}
async function finishShiftEditing(){if(await saveShiftAutomatically()){changedForms.delete(shiftForm);$('workShiftDialog').close();await workLoad();}}
shiftForm.querySelector('[type=submit]').textContent='Save & close';
shiftForm.onsubmit=event=>{event.preventDefault();if(!workEditingShift&&!shiftAutoDirty)shiftAutoDirty=true;finishShiftEditing();};
$('workCancelShift').textContent='Done';$('workCancelShift').onclick=finishShiftEditing;
$('workShiftDialog').addEventListener('cancel',event=>{event.preventDefault();finishShiftEditing();});
$('workDeleteShift').onclick=async event=>{if(shiftAutoBusy){toast('Wait for the current save to finish.');return;}if(shiftAutoAttempt){toast('Resolve the uncertain save before deleting this shift.');return;}const shift=workEditingShift;if(shift&&confirm('Remove this scheduled shift?')){shiftAutoDirty=false;changedForms.delete(shiftForm);clearTimeout(shiftAutoTimer);await workSave('shift',{id:shift.id,revision:shift.revision,remove:true},event.currentTarget,shiftForm);}};

const discardShiftDraft=document.createElement('button');discardShiftDraft.type='button';discardShiftDraft.textContent='Discard unsaved edits';$('workCancelShift').after(discardShiftDraft);
discardShiftDraft.onclick=async()=>{if(shiftAutoBusy||shiftAutoAttempt){toast('Wait for or retry the uncertain save before discarding edits.');return;}if(shiftAutoDirty&&!confirm('Discard only the unsaved edits? Changes already saved remain on the schedule.'))return;clearTimeout(shiftAutoTimer);shiftAutoDirty=false;changedForms.delete(shiftForm);$('workShiftDialog').close();await workLoad();};

const openProfileBeforeUpdate=profileMenu.onclick;profileMenu.onclick=async function(event){if(guardUpdateNavigation())return openProfileBeforeUpdate.call(this,event);};
const updateInstallButtonBeforeFlow=updateInstallButton;
updateInstallButton=function(){updateInstallButtonBeforeFlow();updateFlowActions.hidden=!can('install_updates');$('requestCoordinatedUpdate').disabled=updateBusy||!updateVersion||!!updateFlow?.active;};
updateInstallButton();

// Administrator-configurable interaction timeout, used by both update entry points.
const activityPanel=document.createElement('div');activityPanel.className='panel';activityPanel.id='activitySettings';activityPanel.hidden=true;
activityPanel.innerHTML='<button type="button" id="activitySettingsBack">‹ Back to settings</button><h2>Connection activity</h2><p>A user is active while interacting with application pages. Background checks and the local server controller do not count as activity.</p><form id="activitySettingsForm"><label>Minutes without interaction before becoming inactive<input name="inactive_minutes" type="number" min="1" max="120" step="1" value="5" required></label><p>Default: 5 minutes. Inactive users do not delay updates, so their unsaved work may be interrupted. Saved timecards and reservations remain intact.</p><button type="submit" class="primary">Save activity settings</button><p id="activitySettingsStatus" role="status"></p></form>';
$('settings').append(activityPanel);const activityPanelIndex=settingsPanels.length;settingsPanels.push(activityPanel);settingsNames.push('Connection Activity');settingsGroups[0].panels.push(activityPanelIndex);
const settingsAllowedBeforeActivity=settingsAllowed;settingsAllowed=function(index){return index===activityPanelIndex?!!user?.admin:settingsAllowedBeforeActivity(index);};
let activityLoadVersion=0;const settingsSectionBeforeActivity=settingsSection;settingsSection=function(index){const result=settingsSectionBeforeActivity(index);if(index===activityPanelIndex&&!activityPanel.hidden){const version=++activityLoadVersion,form=$('activitySettingsForm'),input=form.elements.inactive_minutes,button=form.querySelector('[type=submit]');input.disabled=button.disabled=true;$('activitySettingsStatus').textContent='Loading settings…';api('activity-settings').then(data=>{if(version!==activityLoadVersion)return;input.value=data.inactive_minutes;input.disabled=button.disabled=false;$('activitySettingsStatus').textContent='';}).catch(error=>{if(version===activityLoadVersion)$('activitySettingsStatus').textContent=error.message;});}return result;};
$('activitySettingsBack').onclick=()=>settingsCategory(0);
$('activitySettingsForm').onsubmit=async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{const result=await api('activity-settings',{inactive_minutes:Number(event.target.elements.inactive_minutes.value)});$('activitySettingsStatus').textContent='Saved. Connections become inactive after '+result.inactive_minutes+' minutes without interaction.';}catch(error){$('activitySettingsStatus').textContent=error.message;}finally{button.disabled=false;}};


// Open a permitted Operations tool from the separate POS application.
const chooseLandingBeforePos=chooseLanding;
chooseLanding=async function(force=false){
 const target=location.hash;
 if(!force&&['#retail-users','#retail-roles'].includes(target)){history.replaceState(null,'',location.pathname+location.search);if(!guardUpdateNavigation())return;if(!can(target==='#retail-roles'?'manage_roles':'manage_users')){toast('Your role does not have access to this setting.');return;}tab('settings');settingsSection(4);selectUserSettings(target==='#retail-roles'?'roles':'users');return;}
 if(!force&&['#pos-time-clock','#pos-reservations','#pos-paging'].includes(target)){
  history.replaceState(null,'',location.pathname+location.search);
  if(!guardUpdateNavigation())return;
  if(target==='#pos-time-clock'){workOpen(false,'clock');return;}
  if(target==='#pos-reservations'&&can('view_schedule')){storeSection('dispatch');return;}
  if(target==='#pos-paging'&&can('send_pages')){storeSection('paging');return;}
  toast('Your account does not have access to that Operations function.');
 }
 return chooseLandingBeforePos(force);
};
window.addEventListener('hashchange',()=>{if(user&&(location.hash.startsWith('#pos-')||location.hash.startsWith('#retail-')))chooseLanding();});

// Keep Operations inside the protected POS window when launched by its native shell.
window.posKioskCanLeave=()=>!hasUnfinishedWork()&&guardUpdateNavigation();
function installPosNativeToolbar(){
 if(!window.pywebview?.api||document.querySelector('.posNativeToolbar'))return;
 const bar=document.createElement('div');bar.className='posNativeToolbar';bar.innerHTML='<strong>POS · Operations</strong><button id="returnNativePos">Return to POS</button><button id="exitNativePos">Exit POS</button><span id="nativePosError" role="status"></span>';document.body.append(bar);document.body.classList.add('insideNativePos');
 const dialog=document.createElement('dialog');dialog.innerHTML='<h2>Exit Point of Sale</h2><p>Save your Operations work before exiting.</p><form><label>Admin exit passcode<input type="password" inputmode="numeric" maxlength="12" required></label><p role="alert"></p><button>Exit POS</button><button type="button">Keep working</button></form>';document.body.append(dialog);
 const form=dialog.querySelector('form');form.addEventListener('input',()=>changedForms.delete(form));
 window.showPosKioskExit=()=>{form.reset();dialog.querySelector('[role=alert]').textContent='';if(!dialog.open)dialog.showModal();};
 $('exitNativePos').onclick=window.showPosKioskExit;
 form.querySelector('[type=button]').onclick=()=>dialog.close();
 form.onsubmit=async e=>{e.preventDefault();changedForms.delete(form);const code=form.querySelector('input').value;form.reset();const result=await window.pywebview.api.request_exit(code);if(result?.error)dialog.querySelector('[role=alert]').textContent=result.error;};
 $('returnNativePos').onclick=async()=>{const result=await window.pywebview.api.open_operations('pos');if(result.error)$('nativePosError').textContent=result.error;};
}
window.addEventListener('pywebviewready',installPosNativeToolbar);
installPosNativeToolbar();

// POS update controls shared by the register and Operations screens.
(()=>{
 const inPos=typeof posPanel!=='undefined',node=document.createElement('section');node.id='posApplicationUpdates';node.hidden=true;
 node.innerHTML='<h2>POS application updates</h2><p>Warn checkout staff, let transactions finish, then update their POS applications.</p><button type="button" id="openPosUpdates">Manage POS updates</button>';
 (inPos?document.getElementById('posAdmin'):document.getElementById('settings')).append(node);
 const dialog=document.createElement('dialog');dialog.id='posUpdatesDialog';dialog.innerHTML='<h2>POS application updates</h2><p>Updates do not change timecards or reservations. Each checkout computer receives its full warning period and waits for staff to finish the current sale.</p><form id="posUpdateSettings"><label>Employee warning (seconds)<input name="seconds" type="number" min="30" max="3600" value="120" required></label><button>Save warning time</button></form><div class="actions"><button type="button" id="checkPosRelease">Check for updates</button><button type="button" id="startPosRelease" disabled>Notify staff and update POS</button><button type="button" id="cancelPosRelease">Cancel update request</button></div><label>Checkout computers<select id="posUpdateTarget"><option value="all">All connected POS computers</option></select></label><p id="posReleaseStatus" role="status"></p><div id="posDeviceList"></div><button type="button" id="closePosUpdates">Close</button>';
 document.body.append(dialog);
 const banner=document.createElement('aside');banner.id='posInstallBanner';banner.hidden=true;banner.setAttribute('role','status');banner.innerHTML='<strong>POS update pending</strong><span id="posInstallMessage"></span><button type="button" id="posInstallReady">My work is finished — update</button>';document.body.append(banner);
 const get=id=>document.getElementById(id);let state=null,info=null,busy=false,lastStatus='',deadline=0,campaignId=null,seconds=0,installing=false;
 const setBanner=shown=>{banner.hidden=!shown;document.body.classList.toggle('posInstallWarning',shown);};
 function render(data){
  state=data;if(!user?.admin)return;
  const release=data.release||{},campaign=data.campaign;
  get('posReleaseStatus').textContent=release.checking?'Checking the published POS release…':release.error||('Latest POS: '+(release.version||'Check for updates')+(campaign?' · Update requested by '+campaign.by:''));
  get('startPosRelease').disabled=!release.version||release.checking||!!campaign;
  get('cancelPosRelease').disabled=!campaign;
  const target=get('posUpdateTarget').value;get('posUpdateTarget').replaceChildren(new Option('All connected POS computers','all'));
  get('posDeviceList').replaceChildren();
  for(const device of data.devices||[]){
   const active=Date.now()/1000-device.seen<45;
   const text=device.user+' · '+device.device.slice(0,6)+' · POS '+device.version+' · '+(active?device.status:'Not recently connected')+(device.updater?'':' · One-time installer required');
   const row=document.createElement('p');row.textContent=text;get('posDeviceList').append(row);
   if(active)get('posUpdateTarget').append(new Option(device.user+' · '+device.device.slice(0,6),device.device));
  }
  if([...get('posUpdateTarget').options].some(x=>x.value===target))get('posUpdateTarget').value=target;
 }
 async function action(name,body={}){
  try{render(await api('pos-update/'+name,body));}catch(e){get('posReleaseStatus').textContent=e.message;}
 }
 get('openPosUpdates').onclick=async()=>{dialog.showModal();try{const data=await api('pos-update/state');render(data);get('posUpdateSettings').elements.seconds.value=data.seconds;}catch(e){get('posReleaseStatus').textContent=e.message;}};
 get('closePosUpdates').onclick=()=>dialog.close();get('checkPosRelease').onclick=()=>action('check');get('cancelPosRelease').onclick=()=>action('cancel');
 get('startPosRelease').onclick=()=>action('start',{target:get('posUpdateTarget').value});
 get('posUpdateSettings').onsubmit=async e=>{e.preventDefault();await action('settings',{seconds:Number(e.target.elements.seconds.value)});};
 get('posInstallReady').onclick=async()=>{
  if(!inPos){const result=await window.pywebview.api.open_operations('pos');if(result.error)get('posInstallMessage').textContent=result.error;return;}
  if(!info?.updater){get('posInstallMessage').textContent='This older POS needs the one-time installer. Ask an administrator to finish this installation.';return;}
  const result=await window.pywebview.api.install_update();if(result?.error){get('posInstallMessage').textContent=result.error;lastStatus=result.error;}
 };
 async function poll(){
  if(busy||!user||installing)return;busy=true;
  try{
   node.hidden=!user.admin;
   if(location.hash==='#pos-updates'&&user.admin&&!dialog.open){get('openPosUpdates').click();history.replaceState(null,'',location.pathname);}
   const native=window.pywebview?.api;
   if(native){
    info=await native.kiosk_info();
    if(info.device){
     const result=await api('pos-update/heartbeat',{device:info.device,version:info.version||'1.0.1',updater:!!info.updater,status:lastStatus||'Connected'});render(result);
    }
   }else if(user.admin&&dialog.open)render(await api('pos-update/state'));
   if(!native||!info?.device)return;
   const campaign=state?.campaign;
   if(!campaign||(campaign.target!=='all'&&campaign.target!==info.device)){setBanner(false);campaignId=null;if(info.updater)await native.update_status(null);return;}
   if(info.updater){
    const update=await native.update_status(campaign.id);lastStatus=update.state==='complete'?'Update complete · POS '+info.version:update.error||update.state+(update.seconds?' · '+update.seconds+' seconds':'');
    if(update.state==='complete'||update.state==='idle'){setBanner(false);return;}
    seconds=update.seconds||0;deadline=Date.now()+seconds*1000;campaignId=campaign.id;setBanner(true);
    get('posInstallMessage').textContent=update.error|| (seconds?'Update in '+seconds+' seconds. Finish your current transaction.':'Warning time ended. Finish or cancel the current sale, then confirm you are ready.')+(update.state==='downloading'?' Downloading the verified installer…':'');
    get('posInstallReady').disabled=update.state!=='ready'||seconds>0;
    if(!inPos){get('posInstallReady').disabled=false;get('posInstallReady').textContent='Return to POS to finish update';}
    window.posUpdateCountdownDone=seconds===0;
   }else{
    if(campaignId!==campaign.id){campaignId=campaign.id;deadline=Date.now()+campaign.seconds*1000;}
    setBanner(true);get('posInstallReady').disabled=true;get('posInstallMessage').textContent='An update is pending. Finish your transaction. This older POS requires an administrator to install the new version once.';lastStatus='One-time installer required';
   }
  }catch(e){if(!banner.hidden)get('posInstallMessage').textContent='Update paused: '+e.message;}
  finally{busy=false;}
 }
 setInterval(()=>{if(!banner.hidden&&deadline>Date.now()&&info?.updater)get('posInstallMessage').textContent='Update in '+Math.ceil((deadline-Date.now())/1000)+' seconds. Please finish your current transaction.';},1000);
 setInterval(poll,4000);window.addEventListener('pywebviewready',poll);setTimeout(poll,1000);
 if(inPos){
  window.posUpdateFreeze=()=>{
   if(unfinished()||posCurrent?.lines.length||flow?.active)return false;
   installing=true;window.posUpdateInstalling=true;document.body.classList.add('posInstalling');get('posInstallMessage').textContent='Installing POS update. The application will reopen when finished.';return true;
  };
  window.posUpdateUnfreeze=()=>{installing=false;window.posUpdateInstalling=false;document.body.classList.remove('posInstalling');};
  const original=posDo;posDo=async function(action,...args){if(window.posUpdateInstalling)return;if(action==='new'&&window.posUpdateCountdownDone&&!banner.hidden){posMessage('An update is ready. Finish this transaction and update before starting another.');return;}return original(action,...args);};
 }
})();
