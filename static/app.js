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
const operationsTitle=document.createElement('div');operationsTitle.className='operationsTitle';operationsTitle.innerHTML='<img src="/app-icon-192.png" alt="" width="40" height="40"> <span>CoastYouth Retail <strong class="storeOpsWordmark">STORE OPS</strong></span>';$('storeMenuButton').before(operationsTitle);const pageLabel=$('currentSection');$('storeMenuButton').replaceChildren(pageLabel,document.createTextNode(' ▾'));
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
$('jobForm').onsubmit=async e=>{e.preventDefault();$('save').disabled=true;bottomRequestSubmit.disabled=true;try{await api('save',{...Object.fromEntries(new FormData(e.target)),staffNames:new FormData(e.target).getAll('staffNames'),photos:requestPhotos,...(window.retailDeliveryContext?{retail_sale:window.retailDeliveryContext.sale.id,type:'Delivery'}:{}),...(editing?{id:editing.id,revision:editing.revision}:{})});$('editor').close();toast('Appointment saved.');await refresh().catch(()=>toast('Saved. Reconnect to refresh the schedule.'));}catch(err){$('formError').textContent=err.message;}finally{$('save').disabled=false;bottomRequestSubmit.disabled=false;}};
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
const settingsGroups=[{name:'Application Settings',panels:[8,9,10,11,1,2,4,6,5]},{name:'Thrift Mart Dispatch',panels:[3]},{name:'Store Associate Paging',panels:[]},{name:'Receipts & Accounting',panels:[7]},{name:'Dashboard',panels:[]}];
const settingsCategories=document.createElement('nav');settingsCategories.className='settingsTabs';settingsCategories.id='settingsCategories';settingsCategories.setAttribute('aria-label','Settings categories');
const settingsTabs=document.createElement('nav');settingsTabs.className='settingsTabs settingsSubcategories';settingsTabs.id='settingsSubcategories';settingsTabs.setAttribute('aria-label','Settings subcategories');
const settingsEmpty=document.createElement('p');settingsEmpty.id='settingsEmpty';settingsEmpty.setAttribute('role','status');settingsEmpty.hidden=true;
let selectedSettingsCategory=null;
const officeSecurityPage=location.pathname==='/office-security';
function settingsAllowed(i){if(!officeSecurityPage&&[4,6].includes(i))return false;if(i===12)return can('manage_staff_schedule');return i!==0&&(i===8||i===9||!!user?.admin||([[],['backup_settings','create_backups'],['check_updates','configure_updates','install_updates'],['manage_vehicles'],['manage_users','reset_passwords','rename_users','manage_roles','manage_staff_schedule'],['view_audit'],['unlock_users'],[],[],[]][i]||[]).some(can));}
function settingsCategory(index){
 index=index===null?0:index;selectedSettingsCategory=index;
 settingsPanels.forEach(panel=>panel.hidden=true);settingsTabs.hidden=false;settingsTabs.replaceChildren();settingsEmpty.hidden=true;
 [...settingsCategories.children].forEach((button,i)=>{button.classList.toggle('selected',i===index);button.setAttribute('aria-pressed',String(i===index));});
 const descriptions={1:['↺','Configure backups and recovery.'],2:['↑','Check releases and connected users.'],3:['▰','Manage dispatch vehicles.'],4:['♙','Manage employee accounts and role assignments.'],5:['≡','Review recent application changes.'],6:['⊙','Manage login protection and locked accounts.'],7:['▤','Configure receipt categories.'],8:['◐','Choose your preferred color mode.'],9:['▣','Set the layout for this device.'],10:['↗','Choose available sharing options.'],11:['◈','Customize application page colors.'],12:['▦','Define jobs used in staff scheduling.']};
 const panels=settingsGroups[index].panels.filter(settingsAllowed);
 for(const i of panels){const button=document.createElement('button');button.type='button';button.dataset.settingsPanel=i;button.setAttribute('aria-label',settingsNames[i]);const [icon,description]=descriptions[i]||['⚙','Manage these settings.'];button.innerHTML=`<span class="settingsTileIcon" aria-hidden="true">${icon}</span><span><strong>${esc(settingsNames[i])}</strong><small>${description}</small></span><span aria-hidden="true">›</span>`;button.onclick=()=>settingsSection(i);settingsTabs.append(button);}
 if(officeSecurityPage&&index===0&&can('manage_roles')){const button=document.createElement('button');button.type='button';button.setAttribute('aria-label','Roles');button.innerHTML='<span class="settingsTileIcon" aria-hidden="true">☷</span><span><strong>Roles</strong><small>Manage shared permissions by category.</small></span><span aria-hidden="true">›</span>';button.onclick=()=>{settingsSection(4);selectUserSettings('roles');};settingsTabs.append(button);}
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

const printPage=document.createElement('section');printPage.id='printPurpose';printPage.hidden=true;printPage.className='panel';printPage.innerHTML='<h1>Dashboard</h1><p>This page is being designed. Check back soon.</p>';$('app').before(printPage);
const printMenu=document.createElement('button');printMenu.id='printSection';printMenu.type='button';printMenu.textContent='Dashboard';printMenu.onclick=()=>storeSection('print');menuDivider.before(printMenu);
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
 setSectionHeader({dispatch:'Thrift Mart Dispatch',paging:'Store Associate Paging',receipts:'Receipts & Accounting',print:'Dashboard'}[section],section);
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
document.querySelector('.loginColumn').append(shareCard);$('shareYfcLogo').src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABUYAAAJYCAMAAACZ5Mw2AAAAvVBMVEX///8AAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAYAAAblSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyHlSyERHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMRHCMAAAblSyERHCMqtOxXAAAAPHRSTlMAEEBggJDA0DDw4LAgcFCgIEAQgJDAcGDQsFDg8KAwQGCAILDgkKDA8HBQEDDQd6pmuyJE7szdVYgzEZke9AA9AABSB0lEQVR42u2dCXczt5GuuUsUKYqi9oWyM3EcO04yuXNn5m7U9/9/1uWihaJ6eatQBYDd73POzHHiqIlGsx8CqEKh0yGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghpHl0e/3BcDQ6WX3hZDQaDvq9burWEUJIzpz2h6PxqpLxaNg/Td1OQgjJkN5gtIIZDXqp20sIaQxnqHrOAj4ENdxEd/lufzIGP+FzWDrpT007sv4jVequ77pR0Z/1pP0RTvHtDer/MK8OJ0QO/r4N3D9jrFm6XDtU++KfnBua1OmtpkYjdzghCoboa6KS3BZ0xDuTX3qmduiOSd+qH53eamo0cocToqALT+svlJ9wDl5fPKXvDuC2lzMe2AxJnd5qajRyhxOiAX/jdCHuLrhuKR3tTi+sBHBhEbt3equp0cgdTogKWEcj1eXRVQPZlN5Oots7C3/jnN5qajRyhxOiAh0uqhYvO1Pw2qIpva1Etx8fOrV3equp0cgdToiOGfqmnCmiTGCyk2RK3x2I85sALsK2ODm91dRo5A4nRAkc7pYnPaHvs2CgOzMILBUxPg/pQ6e3mhqN3OGEKIGn9WPx1BdUHj6l7wamOFVxEhBrcnqrqdHIHU6Ilj76rkiTnoC3aAM+pZ95zOc/0e8xcHqrqdHIHU6IGnhDuuyriQ5z0Sm951B0x0gbanJ6q6nRyB1OiJopOsiTJT2BAXV0Sn/qtCq6z1iTjtChRqlRQtCtRivJ7slT7JLolB5eeghjqOpAp7eaGo3c4SQJ88sd89QNCQSd1kuSnsBrguM/ePd/KBNN6pPTW02NRu5wEonF5eXV1fXNzc3rd9b/7fXV7eVl6jbKmaKvCx6FAfNRsSm9/7LoJycKjzq91dRo5A4n3iwu765u7l8xbh6u7o7KpmBQXZD0hK1kYlP67gl0MSPG8swnp7eaGo3c4cSR+ePVzRMo0H3uH64uF6kbD4KKCk16Ar0MTenjWlTjUae3mhqN3OHEicurh2eFQT95Wt69pL4JADAghH49wWQnaEof26IKjzq91dRo5A4nDlxe3QQZ9IPnh7t56pupA53Wn0BXw5KdoCl9fIvKPer0VlOjkTucGDO/CxyFfhuVXj+mvqdq0LRMJOkJHNsil0phUbFHnd5qajRyhxNLXq7QWJKMh7uMl0otD03Ckp2gbH7BmZ+WyOL1Tm81NRq5w4kZL9eacFIDTIqmZtYnPWGp8lDU37y2KAq2ePGG01tNjUbucGLD/NZnHPrFpJnO7uGDmer0B14IKU0H76+yR1KIxemtpkYjdzix4O7B3aFbnq+zDN6jr19dfB2LViFT+gRC+ERQgdTpraZGI3c4CWZ+bRtTqub+LvX9FoDOoKu/olilE2RKj59w4gIeZnJ6q6nRyB1OAnk0ym2SDEnnqW/6EFRb1euGmIyRsV6i8NI7eAUBp7eaGo3c4SSExZ1nVKmcZW4bRtGDmaoylbCXGJnSJ1wY3QEvjzq91dRo5A4nehZXMWfzX7nJTKRgCZCqpCdoCIlM6eEyqN8YDQez3huzwVA/qEXLjzq91dRo5A4nWlJKdMNTVouk6LS+POkJS3Zym9KPJ+cFS5qn/YnKyei03umtVmoUxqnZH1CjLWFxndSh+YkUrY5cNprEkp2Qt19Tp3lSMXycaVJQwSrOTm81NZqq5URA6pHoh0gzmtqDY8Cy9xdKdvKJ0o8HNZftDuTnkGDReqe3mhpN1XKCk4lEN+SzRoquSPYC/hqZ0kvL3Y8HyAS8L5Uz5imnt5oaTdVygpIoOl/Gcp66Q94A4+NnhX8MhaiQd3+KteKDIbiK2UUrWb0DRZmc3mpqNFXLCcZl9DzRWq4y2W0PTuuLhpRQjNhhL/2JoCDTVBa6OkOu6fRWU6OpWk4QFsvUziziKY/N9lPML0VJT1BRO2RKL8vZwU+I2iLLR0Wq+Tm91dRoqpYTgLt8FkW/cjNP3TUbwHnv9yg2FFyH3nzJEXZj8RsjOvIeGY46vdXUaKqWk1rm+c3nP7lK3TsbwErJh5NzKLgOTemnWAO2nMCn7O21VFILGhiOOr3V1GiqlpM6rlKbspr7DIo/gcXrD99haBQL1U0SrIxqzkNee1TyCfWXc3qrqdFULSfVvPjXEw0lgwEpOK3/+lWdIn8Cvfdd7OM36CzaEZm6/o10equp0VQtJ5VkPhTdkcGAFFs8/LpsiKxnYufc40lJaotK9prWVyhxequp0VQtJxVkvSq6T/IBKRgpP5f+CVYKGY4ABVhUsj5a636nt5oaTdVyUs5jrgH679ykziHFNhHtJz0hVsLeerRcHzi2LQPfblorf6e3mhpN1XJSRp65omU8J84hBc9T+pzvIslOoPbgZcvAVwVOTq3NeXJqKjWaquWkhCOILX3lOm1/gY553z4EDe2wKT0cYALLL5UDr8HWbZJyequp0VQtJ8Uc0YT+nfu0E3tsTPj+HiOLAOA7j1bIg7ZpVoMuj9YJ2+mtpkZTtZwUkkFZUTnPSSP24NLhrnTHFPhfoiuZ6A4mgxcFndbXGdupsdRoqpaTAhbHEqE/JGlBZyzSszMMkj2EHlgMRn4k58iXgi7D1vwCOL3V1GiqlpPvHN2y6CfLlP2GDQs3dUGQUR36xqMjxKAo/TtoddWanwCnt5oaTdVy8o2X41sW/SRl5hM2rd8kPQFhfTg5CazXbDIYhaNMk+qrOL3V1GiqlpND7lKbMIz7ebquw4I9F1DlOXRKr62LogRMCxhXX8XpraZGU7WcHHAU2z+rSBlowjZM9oBRK/6+Qx9pNRiFV0erU56c3mpqNFXLyVeWqS1o4NF05zRhS4fA/wjfbyTMVw2/RezzqgfTTm81NZqq5eQLDbDoa8qAvaxQvNZC+2CLlUDxOhRsxF09+nV6q6nRVC0nexxtolM+HpUdXGTwtmPpAbiWa8EWgKu97fRWt0CjblCjViz8Ep1ubh6urq5uL9+5Xf+nmxu/z0vm0anFV1pSQgSLMBkFmDaAQabKazi91dSoHmrUCBeL3iyvHivWKheXd1cPHp+bzKMWr4Jk7Ahd0HBOj45/K19Lp7eaGtVDjdpgbtGb60c0aH55u7T+9GSVSiTHFoW/69j5JcKjQKvBZvWV59U7vdXUqB5q1ARbi95cicPli8dr0ybcJupI8GCmckRVQbFAvek7MoU+stLcTi2mRvVQoxYYWvTpWl37c373YLeFKtW8PvRlEIWDsA+zvUGotGplqN7praZG9VCjBphZ9P4qNPv9cWll0lQelZzqHvqmQ29emDy+AS2OVn6m01tNjeqhRg1Ymnjr6dpmB9Hjw1F7FK4SX4TwoA8owSq4XvNXoLe9Mqrl9FZTo3qo0XBMLLo0PMdjcWsyPE7kUbBaSCHCDE9Io4ZZoxuwn4mqKzi91dSoHmo0GIMizU9X1qWVLg3cnmh/PXgwk8V7DuUFGL8iU+hOqq7g1GRqVA81Gkp4Tacbl2Hf/Cp4lTSRR9XTevHZndBVDZPv8Q/tBl2AGo0MNRrIY7BE3WqBLG6fAtv2lKb+KHxY5wHi6Td0Veu7Cx4CO73V1KgeajSM0CrNfhLdchco0jQH3eFnuge+5dBlre8OWpClRsVQo0fLIsyizhLdEDi1T3OuCHYw0yHy2TdyVeN8J2rUS0bU6NESFBF/MgzOl7MIE+lVkn5Fz+vcR7FnE7msuUahTARqVAw1eqwsA/z0HG2/5TwokTSK6w9RTOsVBUSgWJa5RqHXnRr16VcnqNEAQoL0y5irjpcBS6RpwvXyab2iQj01ug81qoca1fOid9NT7KM6Amb2acJM0grOmjJM1Kisx6lRn5a3moV+iJdgwXGur82fJMyEnun+hqomKFROiho16gpvGVGjR4naS/dpstpv1QPSJFXzZAcz6Q6dQ65MjRp1hbeMqNFj5FYrpes0Oe3rAak6ryCJ9yXTemVlZeTSTHgy6gpvGVGjR4h2YfQ5SeT7jStlo5Msjwqm9dpjPpBrj63vixr1kRE1enxoF0ZvUg1Fd1wqJ/ZJDhXB3wvtOfLQxa1vixr1kRE1enwoyzolO+PoHW2F6SRjaPRgJvVhSdDVu9qrlwANssNaTY1GhhpVoStI8pzuBPhPlrqmpxhFgwcz6U/uDB4YaoDuKewC1GhkqFENuq30T2ki9IfoNg08pGgq9mZop/SgRvu298SyzU4yokaPDdXuyjRp7AXoqlJlO60POP8Y2rpver4yeMIyz2KSQ40eGaopfdTdn9W8aBZIk0zrgaGbfkqf5ki78M90equpUT3UqBxVlD5NxbmyO9B4NMm0vv4bHDJYhFL8jTOewo/Rc3qrqVE91KgcTZQ+Tb25UlQejV0HYEP9NzhEo9g6pe0pItBHDsKuQI0Wk2nLW8mlwkA5hOi/spTfRIojRQKNU8MUcpppjAkzd+Vr6fRWU6OpWt5KFAO5/Cyq8miCIXX9NzgoAgQ5bWJ5Q9jUs3IA7PRWU6OpWt5GFHvpc7SoyqPz6I2s/wYHaRRaqDRdHMW2FAT2CTWq6NZ0LW8hipTRPC2q8ehN9DbWf4ODNIqdQTqzu58p9IHVvnJ6q6nRVC1vIfL4Uq4W1Xg0epSp/hscpFGsGt+F3f1gc/rKQL1Xn1CjqVrePuZi82SV6XSAeJn3KXYLnZTxDrjd1G5b/Rn0edVBLac+qW8aNerT8vYhrtWcs0UVeU+xKzg7KeMDrBjfudXtgEdMVadY1f/9EGyO8LLUqE/LW4c42Sn+aqII8U6C2HuZ6r/BYRrFTnI+s7odrBR1zcf5DBu79e2iRn1a3jqkg9Fs9tGXId5fHznpqf4bHKZR8KgSo9TRKfZpNWux9S7WaB9IaA3ram8ZUaPHgrQ40vM8dYtrkY6vIw9Hvd9tcHHUaDiKJQbUSRsY0ioWc4EfFGrUp+VtQzoFzqMyXjXSn4a4lae9320w5mMzHMV2MNVKENCo4rUGFE+N+rS8ZUiNk+RETTFL4V3NYzbO+91GB4hnFsF68JC+uppVQ5dOAfYFhP2WeMuIGj0ShIPRrIP0n0jD9VFvy8UY+4Cxc4uqo1Cl0VV9XgDgC3n1QCDCFCgL7+tTo8eBcDCafXjpnbkwzBTzvvz9hp4/qq+x/0YX/aS6ilJIWEw8eEYcH9YF3jKiRo8D2WD0+RgWRncIy1DHDNbXf4NDNQpMkbeElIfeguVWAWlFyBKreP6NtC7s/r1lRI0eBULZHMfC6A7ZDteYwfr6b3CoRsFYvTKn/RMwtQow4BS4iFT6yJw+MF3BW0bU6FEgyxlNUitei3B5NOJwtP4bHLxoiR7jHFahBLb1uH4+jlxG+GIje/0DT1PxlhE1egzIEiyTnFyk50V2c/EaVv8NDtYoGvlZjQPWBqfowihSBwWJ+MvKqUDrtoE97S0javQYWIpMk+QczQCuRHcXr2iV+8stCP0gA8Wyz4CHvMiRJdByrujNhgpPBdYL9JYRNXoEyEo7HdWUfotoWn8frVn13+DwTCQ0yLRanSg9KrAoMnMOP6P5sH3QL0ngmVTeMqJGjwDRcO3IpvQbZNP6aHVH67/B4Rqdwo5bnahUIrAo9EJiDRaUpYKSCEI3xHrLiBo9AkS5lccUpX9HFK2PloJf/w02yIsHdzJt0KyPnsKrBugYEtrBOoaVj60Ohxav9pYRNZo/otT7zKvjFSOrmRdruF3/DTbQ6BTX3GoszsicCSwKvo+Y99ElCFDzoUepeMuIGs0fUbbT8STe7yPKi4013q7/BhtoVDIcXa2GogXSLr7yuoIXNMEdrNj4ER0sh1YV8JYRNZo9ogDTkeyl/4bkpyLWaSL132ALjU4lqludCF6anmBZFH8dkWT5DYhHUYsGHzPtLSNqNHskC4dHGF/aIYoyRQoy1X+DLTQKnjT3ATog7YqGuYLoOrqxtH5eDy85BJcK9JYRNZo9knXDyPXhDVnmN+Su/wabaBTPHd0xHgAi7Q6EV8VTivAtA9UvuGDJIbhSoLeMqNHckSwbPh3rYFS2dBFpJ1P9N9hEo7iXPvw0qHHeVCxRya59/NoXFe2cgUWrVxaHTHvLiBrNHckwLd9j6euRJMfGuc/6b7CNRtGSyvtMKmLXM3TavYekNLQkcFUm0pnknsNF4f0Z1GjmLARJo9FPck91o3E2atV/g400im9632M8OS/IIz09n2guJsoomoquPOp/M2lviI9EVwZlAqnR1iNJGj3mwahsOBpl8aL+G2ykUbyQ3TdHDQez3prT9f/NBkPFsHaHLBQuHe2eTQb93huKRhqcRVX/IdRoo3loyWBUNhyN8oNR/w220qhmWm+J8LQn9Hg8o8ZFeZTUaJNZtGYwKsrsijKrr/8Gm2lUNa23Q/omRrW+xcGo9l3wFWo0bwRx+oiVOH2QBOtjzOrrv8FmGoVPt3NBfBsxh6MWg1FqtOUscbMcb86o4mZj1FR18E85on2btij2CClyAbSYWML7Y6jRvBGsFx5vzug7gq1MMTLw67/BhhpNtzyqKWQ6jda64H2g4KOkRhuM4PSQY91Nvw++sz7GCkb9N9hSo5LCoJbojicR7mDVty6wXjP8KKnRBiOIuhxnaaevCLK7Itxu/TfYUqOpwkzKQ55EmZ96BPWfwx4lNdpg8OM14p2t4Qm+hhFhJbj+G2yqUVGJZTO0cfA4UabAA0EFj5IabS6CdKdjz3bagY++I5Snrv8G22o0hUf12UQxpvX6c/zEj5IabS6CSe7xB5g2CIJM/jdc/w021mh8j4bkZEaIiZkZwvujqNGcWcJSaUKAaQO+iuGf8lT/DbbWaGyPBmW2Swv8yTFaGIUeJTXaXPBSo8d2Nn0Zt/AdX7u3pf4bbK7RuB4N3B/k3dbw+niCR0mNNhZ8W8/R72CS37J/TK3+G2yv0c5ptLwnXabTPr5brwwtSo22GXwnaFPm9JJZvXtT6r/BDhqNlj96FmxRRcFpAZpdAQGPkhptLHjcuilzesms3v1EpvpvsIdGhWeFahmZWMrPo6YWpUbbDLyppzFzesms3j1ztP4b7KPRTt9/gdSq5V4evTC1KDXaZmCjxKkGHwd4Vu9+0/FkdIj3AunY7tXzUb7luij2KKnRpoJvqG9G7v0OeCXDvUp1/TfYS6OSUzMVTCyHeh7xertMJ/hRUqNNBV8mbEbu/Q78x8P7ruu/wW4a7XR6bpvWx5JzlwDMY2KGY2X8UVKjTWWJ+qQZ++nfgffVe8eY6r/BjhrtdJ12WxqvOm6wHTrbBL+kj5IabSpwhMk/Ez0m8OlT3jGm+m+wp0Y7nanDdsuRy0tnOHQem0/osUdJjTYVeHbbnHSnDfBahneMqf4b7KvRtZ6MRXpmca5REWZruSOb+qKHeMuIGs0WPPWnSUujgsVR77WM+m+wt0Y7nb7hEqmbRDf0LFZIz4yXbT/wlhE1mi3Z6CQ28M+Hczvqv8H+Gu10ZkYjUleJbgg2/tivO71lRI1myxVqk+bsBN0Brwk7V8Cv/wbH0Oh6oGewrWkS42ULEul44BBaeocabS1L1CZNyhrdAGeOOofqc9FopzM9DxrpnQ18Vhy/09dO7Z3HytRoa8llUBYduFi1c6g+H42uOb1QprmPL6K+Z6p2ujeRGm0tcP5k6oZaA5fAj3AeU070huIx6dnQK2hTTrcvO8V+0neczZO2g8qkaREm/M4jnMeUGdP+BazSs4t+rLn8Id0Z2MyzixkdShyBx2RNizDhyxnt0+iG6WwwqpHU2WgwS6XQj2b2h9U5BqNhMs2T1gDnOzVvagvvY0rd0IT0ZoPBaHQQ0TkZjQaDWUaLZdPe+WBy0MptI3s0KIkBHGhp1h6mDXCqV+qGEkKyBnZJ0wL1gsNTmnfrhBBDWjwkg9cz3M8RIYQcM2icpUEHiLyzQDXavPUMQoghbQ5XoxptXnSNEGJImzX6RI0SQsJBNzE1q2bzDvQnhBolhFTQ5oktqtEmnYhKCDGnzRpFazw1cUGDEGIGqtHb1A11AE32okYJIRWgGm1i7iQ1SggJB86dpEYJIaSIVu/kQQ8HpUYJIeW0WqPozTev1CohxA5qFCF1QwkhGUONUqOEkCCoUWqUEBIENUqNEkKCoEapUUJIEPCJdm3WKCP1hJAK2qxR5o0SQgxANXqXuqEOcBcTIcQAVKNNrPBEjRJCDKBGqVFCSBBt1uiSGiWEhBNyHtHlkR/gjla/X6ZuKCEkY+b3ARq9eX1+uD1ilfIsJkJIGIvHJToWLVbJw/bfPD/czVPfig70OD9qlBBSwPzuAVbohqKTQT9DNPfXxzgoDfkJIYS0m8UtOpf/oCjMcrf/P3g6OpPO0Xtv4tYDQkgAC+E49G28WXClw82UT9fz1DcnodX1BAghal6W6IrgAUUXK7Dt3SL1HcKge0Ffj22YTQjxY3Ennsx/MC+4XlGE6nl5LNZBs+9Z4IkQ8sb8WjkQ3VI0sy1ZHbg/jg34aL4TNUoI2XK5DHDoa3G4unQ893R1BHN7NNuLm5gIIWsu4aFXGQ9FVy3/nz/nL1L0zqlRQoiBREtqF1f+xXKe+r6rOwW9c6aNEtJ6LCS6pmh0WROxynpECgfqb1O3lBCSFiOJFseYrmv+Juep/TLkxgkhrWEOy6KWwhpPtX/1nG3UHq4nME/dUkJIOhZwaiRAYaQF+Lv7PEdzC/jGU7eUEJKOO7yAk1Yn0L7Sh3nqnijgMejngxDSBuZWi6LvFI0q76C/fM4wSlO3rPtBq4s2d3v9wXA0Oll94WQ0Gg76vW7q1hHijOV8fkfR4ig6Nb7PbocovC02w5+AKJz2h6PxqpLxaNg/Td1OQrx40W+eL1dh0QfB1aIyy76Eq+S1MlDfG4xWMKNBL3V7CXHAfii6oSh5CZvVby2c1YAUb7fhhw5wNykwamS3PxlLP3o86U+NH1BQX41Ho4vBec+6TaRNeAxFNxTlLuEB77wGpPAo+j78sz7IX6Nrh2o//uTc1Fo2fTW6OOdQmWiAt+dIKdpWj2exb5Q0T903H8DFriwjTLlrdKZ26I5JP8u+OhnOGA0jIhbWAfpPnos+D96avr3CY+rueQNOd3q13D6QtUa7g7PwNowHVkNS476a9GlSAnMZUlO0jkIJypJTr6U35MMSbrDlim7GGp1eWDXjwiZ2b99Xk5nhoyRNxm1Cv+XB4CPzmNjDPzbP4Z/1SbYatZPohpHFcqRHX51xSErqWWgOq5NQFKtfCMe/zxlkEOFz+ofwD/skU43aSnTDJHxq79NX4wFFSqrxitB/UrhQCO8Heid9QvsyTVuz1Gh3IM5vArgI1ZVXX50ZhsFIA3FdFt1RuL8cz2R/J/X+SsEA2jTZNUeNzgwCS0WMz3PtqxNuvCKl4AnlAcyLPnkpvsx92jKkeFeZLo1mqNFuYIqTn648+2pg+lRJgxBPrVUUBtrlw9HEgSY8J8x0aTQ/jc485vM2unLtqxPubyJFLKNYtGR0pvjw54RbQwXaty06nZlGPYeiO0Z6Xfn21Zh7m8g3Fu7BpUqvKIajKT0qsP7c9IPz0uip06roF12pczV9+2q1YqSJHBDPoiVbzFWlUFIdLyIIMFluqO9kptG+s6feGGbZVyt6lBwQ0aIldeOkuaNJPSrYL2BcTCUnjQ69NfXORJf65K5RepTsM49p0ZIzNXRpAmk8Kti9arzwkI9G/ZdFPzlRedRfo/Qo+eTFP130C/PCVugKoqTwqMD4T8YfnY1GuyfhH4cz1mQ+RdDoinEm8kZsi5bkzr/oLpbAo4LBqHUdlVw0GteiOo/G0OiYeU9kS9R10R3zwoYoC+5H96hk+cE6mSATjca2qMqjMTS6OnH+spHjIIFFS4ajC+VpzrE9Kmim9Zw+E43Gt6jGo1E0yv1MpJPGomXDUVH95k8i549KBqPmtVGz0GgKiyo8GkejK+6vJ1YWfV7eSfaSllQWUU7r43pUMmY2b1gWGhWc+WmJNF4fSaOjCN85kjdLG4duitqLNiKVVAxVSv15Hq/HJINR49z7Th4aNa8tiiJch4yk0RVL4rcdA4vuHLpBUvG5OHe0M1cmDcSr9yTaJmBfFjUDjZ5HslMBFxn11SdnUb54JFvCDwy5ufsUmCiBvuRkOryoPKRle0TrDvZyT6/RXiQ5FSKqQBpLo0zCbzdaZ32w/Lr2JxmolcWwlcujseo4i1YuHNqUXKNd38J4dUjiOdE0yqSnNhOYdv98dTjYEhUsLdtsrj0MKk7ak6h1DkdGJddoovDSO2eCMFM0jTJY32K0aZplEhUO1crCQurcgRjhetH43TxptJNeowkXRncIlkfjaVRbg4ocP7o97OUSlV6ybDlTG2Z69g8zyX55PM7dS6zRqXpKPxoOZr03ZoOhflCLx8Xr++r7jvht+waDiSwzlkGm1qJdhNxwXWIsWZWmkiiTerHBPr3oENGqhYvW69XguqtGZb/x5Lxg1nvan6icjE/rNRr9pDcU1KTmrL6lBISXbualVxWN1ko9oyxSYr9n6ADZLiuXoFdajWrqNE8qho8zTQoqPIMO0+iaHty8wDNMyZGinTmv5fdYcVnZELf0tDftEaVVTQtHuJg892hDUo3Ko/TjQU0FpO5Afg4JOvQL1uh6yAwOvyd+nU4yRr0H9LpyqiqsYV+qPaVHfZdHZSen2p4I+k5SjUrL3Y8HyAS8L5UzuvvSQKPoYvTYr9NJvmgXRp/qcniWMu3Ny66j9KhnFr5wGcQh26mTVqNToe6G4CpmVxo3A6NMJhoFFzJYdrSFKEspvS5rR3vCEz7Ltaf0qEd0fIdwoO0k9JQalS1kngjCLlNZ6AoMjNtoFPMoq+C3D2XG6DOy9LiUXbP8xDddvN6v2JMwP8xnMJpSo7JdoMJmyPJRsd2XRhqFfj5YdbR9yBb53rmfI9eWHjhfrhudR72ynoTLIF7NSKhRyRF2Y/HoTHTkPTYctdIoElmjRluHbkqP5u8sZZetiArpzis1PtH4DWl+mNfW1HQanQo0d6JYKhTVgoaGo1YaRcJMLDraNnRTetgL0uFoxbhtodlo5VJ7VDoydgt1pdOoYGVUdx5yV/IJNn0FarRLjZJDNFP6Z8FS31J47aXhtZwUJt7n77QymlCjgErCLNoRmRoRoJlGgc1b1GjL0Ezp7yWBG+lwtDK6rqmIaj+hlo6K/fKukmkUT0pSW1Sy1xSpUGKn0forsVZey1AsOApryy+l16/KAFAkPpkn4YtvyG0wmk6jcAQowKKS9VFg9dVOo7P69vj0OskUReL9jVBLwgzLmiylS3nA3nhvvbjLfDYwbUmlUUAkO8ZBiej4dlNgF7udRoFcL5deJ5kiVpymxIbYO5UeVSQ+mSaPysfDc7/nl0qj8LJlYB46nJwK5DxRo8SJZQSLKnIBnqoGvHKPWq5Nyi3qWWgqkUbhAFNwAWN4DbZ+kxQ1SnyQx5dU5d7k6rm39ahdqSf5rbjWR0mkUbRCnkH9YnR5tF7YMTXKws1tQpyIqSyaKU/4tPWo2fkditKnftv6O8k0iu5gMthajk7r68UVU6NMeGoR4lrN2j2NCvvYetTIZYr4lm8N/kQaBSM/snPkS0CXYWtjWXYarR+MU6MtQrpmKcx02kOR41/5YdIfAJuZtabMlF+y04Y0GkVHiCbl4tDznmpj9XYarS+0yrrN7UFqhSe9ixQZAdUelbbdYmu9xqLOB5mk0ShYr9lkMApHmWrNZafR+vValiZpD8LBaFDROc1ZT09VHyjMojIYjmos6n08aRqNgmEfo9rFYFpAbcV5M41O6xvDw5hag1QLYdPTB42Eqjy6lF0reDiqKifoexpUKo1iXjMajMKro3UpTzErPLFsc2sQDkYDozSqQ/OeK/bDC+uDhI4Lhdbe4bh/aUcSjYJLo2anDE+xz6sbAcasN2rf6SRPhIPR4POBNVVFKuUtFHPQcFRc08lE3fUk0Si2WGlYnQMrUVI3+rXSKJDtxcokrUE2GNUH6T/QVAut1Lds88BzQNNfdMeseE/pE2kUyxo1XB7Esv3r3BXxLCaz9QySObLBqMWZRppo/WtlJRRZmElfMO9O13L3KX0ijWIRJsPDMcEgU3BfIRqFVjTAs0rJ0SObpZrU7NRE618ra0SLBrjqrUy6s6pC8sNgkmgUcprpvBYb/9ZY0ESjfSiLNaA4IDkmZBNio3HVUuej8mVN2fKobo6tOwLq1TvxfkcKjZ5CTjP9XGxWXzMGtNAoljHL5Pu2IMo/sgqVKE9yrjiFVLQ0oSr0pJzQe52ldwBehF5IhVGwQL1pys8U+sgac4drtA8Wq8YOfCZHj+xkD7NQiWJv/ZvIyyL2op+DubjBC026q97ZYlJoFPtM2/uE/FUT2AnUaPccrfhfuxGANATRcp9hqESX9bTVUnGQSxS3Eu/MfNQORSPkOm3JVqPGtTmgxdGazwzR6Ok5WtRqxZ2g7UGiB1MjqEd361lyYTskYhbmPOmHonEWRjtpNAplcQbXa1bc50noNQ5v+rS3ZjCY4EdCbRgzwNQSREuKpidr6vLYdzwVLi5IovWiW7lVD0UjLYx2Mtao8aZybD02UV8dwMFoW5AMs4wX+RRHKe21pWCQJ1lvFdzLpW63wI4IGaM7UmgUGpsZbyqfQo1O1Fdf4WC0LYgCTNbTU2X26BvL+bcLLgV/PgcbOZdc9BsGW75AUmgU+nvD5Hv8Q6sFFkmjDNO3Bcl6YvBe+m8oznSuFKkkyoQFmRZXIUNmky1fINlq1PpGDYbAcTTKuvetQZK+Obf/+GWYR7+JVOBlZCdToESjhZc2tEaj0IJsBhodWw/DSa5IVhM9YiUhYaYikUqGo7WKC5aobUiuhlw1aj4mOxaNcjd9axAkjfqkP4Z79GuwSXBDNWsU8+tQiXofG/KV1mgU2oWZXqOM0rcHwZzeKXEnKFz/xtPdh+IFIbPK1NHLZXiz7NeSq0igUSj3yFyj0I0m1ygL5LUHwZzebS+OhUdfn6/nb5cTJHCVbmxd3Gp3/O8TZw/oB9RoThqlRVuEYArsl0Uelvb0aa076dVKRouPATuW9oiX6rSDGs1Io7RomxAsTM79WqE5Z7OI5+tNehE+kCyM1ZsMjhNYNIVGoTp5bdQoLdomBAuJrut8Vh5dm/H6RZDzVJTUuThSi7YnxJS/RhldahWC3HvfNHI7j4ooXKgITx14jVbVaZ/WaDT3hKcxM53aBb4I6B0uSePR+6KmKM8J+WrReJuXPshVo+YlNzPX6IhZ9y0DXwZ0zyNP49GiMaNBxCuFRbPVaLt2MY2N61mR7MEPYQo5kRgkiUeLNjKFL46WnnPiSrYatS5zBJ0kl6ivLljTqXXgwZgYieQpPOqyOBo/urQl23qjxoXyLIbATn11wfl8C8HLaEaZpCbwaOGS7/IoLZqvRo3LxWVbtpkSbSewGdTHustQn7ypp7AZR2nRJBqFTiUyTv+BTlgOPotJytk5p/PtBF8ajVViwyr1HadocVR9ZumGuPvo92nLkXYWn2ncV+PhabLHThKDZ41GCzy/WOxll1C4OHqUFk2i0XNIMrb3aXGMnrVGORJtL3DWaKQ5/QaDunkiChdH9W2IWV/0kBQaxdYpbdcMoY+sWUiw7qtJwudO0gKP/GKWzVws43q0qA3aJjw/Su/WkhQanUIXMI0xYeauyQ4w7yvrbARyLOD5kXHtEHg+k5BLuxY8pUi6/ySFRrGhoelYDbvNqcVFBJwlffQkHXiEKXLDogbsb4N6Zp+bVCH6N5JoFFqoNF0chQ60q9s5Vd9Xezc9RT6Q1UhaChxhilx+uNN5ibhAWnSMvGofU9QDQ4qoV4PDq34BSc2wVgfktNrkAJFGsVNLmDTaTpaoIPwKNpexsCmcjFC4zVVxmaTLoluSaBQK1VuW38TG3MPgq+xrtItsP+Vpyu0E3sMU8ZDgDwQl/AKZh3TNO2l20X8liUahws2W2+rPoM+rC2rJNIq5m+XxWgnsiCSti5ZBWjSMlA6G44/XC0iiUaxOyMqs7NEM03bdDFuo0S4ibyaPthF4ATD60uhb+yJN7IsUKAvVP6UYrn8njUah7aB2gWwopFX/cUKNYhtQ61YSSAOBw9HJYiePUSL2RTEm0a76h8QR+nfSaBRbHLVKHZ1in1a7FivVKJYfwB2h7QNWRbqdOXPxGqWCoi1agoynDGJLb6TRKLg4ajQcxRID6qUt1iiU9H/i0L8kb+CJa8qk8tsIA9KCj8WP+stlKNpJpVEw5mMzHMV2MAERLbFGsdUEVr5vHcsAzcRj7r9CWvQzAf5pJquiOxJpFBwgnlkEYLCVUWBUKNcoNOpmlKl1oBPm+/CPCuLRO2RfpELsL6/yGYp2kmkUjJ1bfDgU6Fkhg0K5RrGfC5YoaRvoTqGH8I8KY+G8yb5o7Rf5jblJu4X+G4k0CqY8GQRgoCz4DfUbihQanUIfzRIlLQO1TAY5kb6hpqIbrP/A55Q18QpJpVFoq+TKIACD5VZB+4kUGsVy8FmipGWglrkN/6hwLh132as0mtd8fksqjYKx+uC8SjC1CopmaTSKDYZZoqRVwNn3mURR7tyWSIs0uqz+k+U8dXcUkEqjYM2lVeB2SdjWSJxHo1FsODpmiZI2AadGZqJRv+Snol1alcuxN9l0yReSaRSN/KzGAcujU3RhFKqDotIoltvFEiVtAtZo6oZ+srhyEalQo5lKNKFG4dBPQEJQFx7yQhXrdBrFfi9YoqRFHKFGnUQq0mi2Ek2oUTjItFqdKD0qsCg0GtRpFFu+MMmQJccBvBc0dUO/srBfIxVoNGOJptToFHbc6kS1dCiwKJZypNQotouKJUraA5qMmai+UwXWIi26w8Jyp8vMEkUPSKdRdCfTBs366Cm8aoAuTSo1Cm6jYomS1nC8Gu10Lk3zSIvu8PuSx/P1PPVt15BQo1Ncc6uxeHf9TGBRMP9dq1EsXYBRptZwzBrtdOZLu0VSRKP3d/nliR6SUKOS4eh60itaPOziK6+4wbQaBW+UJUrawnFrdLNIapWRX6vR58xn82+k1OhUorrViWDLZE+wLLqCN2OqNYrdKEuUtIVj1+ial2uTIWmNRm+OYCC6JaVGpac7owPSrmiYi0+n1RoFb9TwDD+SMw3Q6JpHgzp6VRq9v53DbVlcp91mn1SjeO7ojvEAEGl3ILwqfMqxXqPgjbJESTtohkY3k/tQk5ZqVOLQ9Z88pTwooJNYo/hWpk+R1jhvKpYonmqk1yg4HGWJknbQFI1ueAwKOBWdNXX5+nA3lzRhcb29VkqPptUoWlJ5n0nFhp8ZWs9p313wkmSARsFy/yxR0gqapNE1L1fqJKii0iTS5dCP0/cSejSxRvFN73uMJ+cFSZan5xPNxQTbMEM0io27WaKkFTRMoxsudSoNL6i6Xw81nUcTaxQvZHfIaDiY9dacrv9vNhgqhrU7BKXnQzQKVrRi8mgbaKBGN7zcLaUuDdXoQXX+ZB5NrVHNtN4SyV72II2CB+uxREkLaKhGt7w8Xj3gWaWBGv22NzWVR5NrVDWtt0MSHA/SKPh7wRIlLeAWlMxz6oaqWcbQaNG+1EQeTa5R+HQ7F0Q3F6ZRsII0o0zN5ygL5YlAJ/cBGi05/jlNHaj0GhVUzDNHdiZnmEbRva8sUdJ4jkWjiwft4A7VqHrwOC8b7z4n2TyagUbTLY8KC5kGahRcvmCUqfHAGk27n3xx//p6rxvdoTeoHDuWSnTj0RT7R3PQqKQwqCXS8nuBGkX3voqLWZEjY+5sGSN2rrp5VPyp6w1WSXTNfQKP5qDRVGEm6fQ5VKPgllCWKGk8qGWSbnD8yCd4EjfDc7hdI9E1y/h9lYVGRSWWzRCP+kI1iibJskRJ00EtE56drudxrx1Pt7IR3iN6g+JWXdZKNEm35aHRFB6Vz52DNQpuCWWJkqaDHsXxkK6J869b5WUF6NHEWKlG78DQlWYdIohMNBrfo4oVyHCNgqVYTqJ0OUkGGshOl3+/+J5C/4AvZCJDRvH9La7gg6Ce55G7KxeNxvaoJo4TrlE0KYHJo80Gri+XrIWFIoTn9g4/E9Bs/oPYYaZsNBrXo6pouIFGwS2hLFHSbOBJ7zxRA0sXNx+g+TJ6e+gi5vxWeiLpNXhlI/LRaOc0Wt6T5qBRqK/qFzXB4ahsXwA5MtDdoPEX+XbMK2qIPl/XhtfhhK5bpDG64tBxey4jjUbLHz1TbhSy0OgUbCNLlDQZOCEoUai+ZlL+VGNS+PaA1VZtWei4y6M5aVR4VqiWkTYv00Kj6C2yREmTeUFlkCbGBKw5VJrUcs3iSltcP2rX5aXRTt9/gVR/PyYaRbcaMMrUZOAxVYrGgZJ/Wj6WBHJMI2hzbWl9aMXAiMw06r5AOg7IyTTRKHwcKqNMDQauyDnPuXHrId/tS8AFwAHjbf7T+tw02um6FnyahMyVbTSKHofKEiUNBh6vJdgOCk/J32y1PDyAboH+Kbprcy4Qu9zSFmSn0U6nB+71kTMOC9zYaBQ+N4UlSpoLrKr4+8PnirHf08P+oBSOMOHT7muVR+NN6zPUaKeLznuFXASGbYw0im4JZYmS5gJvOn+K3rTwo+ng3whBfadHzcQ+3rQ+R412OlOHEqSj4J3qVhoFt4Suhgl6nkQBzqyMXnIUFvy+rr4macJTcEm7XjQT+2g1CfLU6HpmbyzSM4MpspVG4TrVLFHSWGATxIw3r1lItwutefqqenhpVDbSXmiS8GMVbM1Vo+sxm+ESqYVEDTUKbglliZLmAk+d7+O2Sxhf2rbwIO3pDv1D6VhxKW9brDWRfDXa6cyMRqQ2EjXUKDwcPU/W98QXXFdRi2zgiw0f3Bw2EB41igfa8B7aTyJtA8tZo+thm8G2ponZ1NhOo1Ow7SxR0lTwJcioKU9Lsae+pRLAc3rFjBse6H4Q6WSmvDW6Fs550Nz+bGAoIjuNwrteWaKkoeDDvpilm+FUpXKLClSnaKDco3FKPeWu0TWnF8odouML2xiNoUbh06cYZWooeChnHq9R4mSngrRWeE6vyo6XezRi9+VObygek54NWSSJ5MsS9kC8WL14MFpgUXyYrVu2FHs0wQF3GTPtX8AqPbvoc1GRZA2ug3ixeulgtGg8icfOlMlIYo/Oo/XfkTCdDUY1Lj0bDWZUKMkeQUw8Vga+dDBaeFIHvlihbaY0Xs/haCG92WAwGh1UgjoZjQaDGVcSybGA+yaWB4SD0acii+JjRX3hkKXQo/NI/UcIiQxebSNS0o5wMPpcOEjGVRyw5Cv0PYejhDQUweb1OEEmoZwKDzsSqDhgqWIh3F8/j9J/hJDo4BqIsqVRuIGpOM6+jHNPL7J6T5GPCSWExEJQaiPGTibcgBuKVzYFKg5TmyxcH2lVhBASG4EKIgxH8T2cFWISqDjwAGSZ9COXySKEREIiLv9T12VpRMU5n4LBaOhZfbLl0fjFrwkhURDM6v1T8EV1Rktm5IIbCo6ew2dUb/H/GSKEpECywOe9Oioqev9UPKWXZEyFe01UGTVmfRdCSDwks3rvaelSIqWSbZyCjKnQOf0G0bR+7tx/hJA0SI7F8B2OigJMJVN6yYDWIiNeNK1nkImQZiKZ1fsm7Ri0RHSKk0mZAMmpywwyEdJQJFnkrjnkkglyybhYslZpI7WFpPtin7BKCInDUuABTxFIdjDdh1/CaootGUNzJxMhzUS0vKcviVSLJGk0PL5kF/ARrCNwVk9IQxFFm/3CJIJmlMhclL1vln4kiWpxVk9IMxHtDX+eO7VCMiEv2b8kqhVilwwvGANzVk9IMxFFSdym9YKhZEkTRFN6w/m1IOOfs3pCGookacdtWi/IXw3eTG98F4LlCM7qCWkmMgE9u6hAkHtvMRg1zYAVrIowA5+QhrIUefTeIwlfEKgpXtWUVYeyXaTEg/WOmQ6EkJQIT0DyOFcIX1goXl+UxZeMt7cLFO7QdYSQHBAegeSwtx5fXyyeFy9T/hAIViRYLY+QhmJyIGcIAhEVLikIb2Bu3Hxc4kx5IqSpWBwPHwK+NFo8kJS133xVAre4f+1rQkgahKM58zATvjQaeqbyhrl5/+FBJo+nRwjJAeFw1HpABy+NFtdaTjwYlfwMXIZ/GCEkS6TDUWMXhX1s8sGooL7LlcfTI4TkgHQ4appJjnuwcE6ffDAqmNXzRCZCGovslMsNhmlPcOJl4ZxetgvL50gkeFbPbfWENJdlQo/Cn104lpPVBPCZVePjadeDWAghKRHuAzL1KDwrL/xEUcO9zpOCG8EYEyHNRXTouq1H4Q+cF/yxqF6q2+mmcIUqVichpLmIjtU0dQK8uFm4sCg5Itov/R1e3uU+JkIajOQ4jHdMwt7wwmLRp4mOt/ebUsMhOhZ5IqTJiMZ172YzWGuElxOKZuSiOb1LstMOtAnP4R9FCMkWRZTJZF8orNGikihLQVu94ksb4DCZXxMIIemR1T5+d1NwvacgA0nU71mmDk674kEihDQa8V6mrUdDo9/opxYtK0q2DbguS8KLC8x4IqTRqKb1wQuk8McU/K1gAO12OPQWOE7GjCdCmo1qWv/6eh80U0U/pWgD0hJvpFfKqMFdEEIahGpavx7pBYyx4JSloukwfvqId1EQdCDPxFFCGo5yWv/6ejPXfiQ8HS7SKC56783sISu8hJAmoUnC33lKOyCFNVrwt3iEyT2yszwyjXZ7s8FwNDpZ7XM2Gg0Gs9PUbSMu7J74+OB5n/e6qRtmxE8//2nNT/+Wuh0bUB0UCEK3QhqiUVj6/lNpNPs1A41O+4MvL9N3TiaDxrxcZE1vMDkrf9zj0aCXuoWh/PznH+/88pf0Jl3gy43fuNLMnFGNFu2HR90V4Sg5eBOBf1OqOD2fVBt0z6XDGVXaAGbDE+RxjwZHPAv5+ZcfX/g1uUhftMujr7ocUjTjsmgYB7rLN9dpR8igOhazizPkhdp/t86n4k8Z1F9W2f76CyODKqB9VQO30cV6Hizvldh9taPbnwhu7uxiBlyzF9J/Omoe67/99cchv/1u9ITUyErPHfAk3ioUMhsG4zqe25feyV6jswt0GHrwbg2Ezmi0Rj8YXZwbTIR9NdqTP/LxsHZMmp1Gf/ptK85f//bH5j/9/fd/7Aak4U8nDFk9+W+6E0ZzUI0WZd9jGo2Sqpm3RqdDnUN3nPQls/t2aHTXMaHrHp4a7UunHuDTzk2jP28l+qc/Pv+bn7aj038EPRkDlNmjHyIVTe1RjV5pGxrnGLmcNdofBX+RL/CFsxZpdMNE9BsTq6+6g4DfzfGg6pYy0+jfN2PRvx6shf6ew3g0JMy05ekODzaFaBRpp0ENKgS4+HSkZ/hB91w5KjlghM5hW6bRNRNkSTFqX/VDJh8bLspFmpdG//itUJhbuaZeHw0JM+14vp6DnxWiUaQhsUoq5anRoFHJAaBI26fR1epMOST16aseFJqvpnxEmpdGfy0Zdv59M9NPHa+XH7j8nXtsSOqs0WiF6bLUaPCo5CsjZGrfRo3WTYRj9lV3aHRH/eLrZ6XRnzaLoNtl0X++xej//V+7f/N7BtP6sHD9Bw+ASX016lyQRNSW6Brt2Uzn9xnWy6KdGt2MSOV35NBXhg+9+FczK41uBqM/bf/pnx/JTv9j9682cabUw1FtsacCk86rPwiNzag0GrEsXXYanUpSBmHGteuAbdXoanUiTmC37yvbuxsUfEJOGv3jc8j5qdEf/9z+F5uB6l+U3zQ7lkYeXc/urx8rBqUhGq2L1DsevqS9jWgaPbedz38yqRmQtlejxdqJ2Vdd65/Ok+9Jwzlp9OePwehWo//R6fzP//zx4792/80/fvz4RflNM8TOoxuVLu9K8kkdNRrRorlpdBqe41TKWfWgq80aLdJOxL7qGsSWDvg++8hJo79+mvJNo51///Hjv3f/ze85zOqNPbp16cPV3eX84FP8NBrToplp1Di0dMh51We3WqOrsWhvk21fTe0tumZ48Ck5afQfn2GkN43+r8/R6N8/h6pJMffoGzc3N8urNx7QHNUijVaeCR0n7f6dnDTavfD+Xl9UfHq7NbpaSSJNpn3VdfrtPFjFyUmja1H+6e0f99ZG//X93ybFy6Mq9xa0ryrKHynt/h04tcG/KT6Dkq+MyhdI265RiUct+8phRv/GyZeHnZlG//b2j58a/d/v//aXTDSak0eLNFqRThDZonDe1pN7S059J/SFr9Y+rdeowKOGfeVn0dXqbH/FNzONvk/bPzT6fz7+7V9z0WhGHi2qGVo+k466Lrohm7LN/Uhf7VKPUqO4Rw37ynMh58uzzkyjP7/943Zt9J97U/p8JvWdnDxa0LjSjezRLZrNWUyxLFruUWoUa4dtX5073k3Wk/r9tdH/6Pz3jx//+X/3/m3qbfUfZOPReUHjSvb+x7corFHnwJfRRkDs7SpuAjW6Wo3BvCezvjp1vJmzfENM62n7X9/+cafRf63///97+29+yiRSv8NqP1MoRXmnxfJKcYgxehe+xU/dQ/T7lExdqdFV6U+MW185LoyOD9KEc9LoX9amfCs0+pbw9N+fq6Obf6n8pnlgs78+mKKNnYUrkvH20X8C18lz1WgOFqVGt2D7maz6yvGeDi2alUb/9rk4+qbRf31uqv/tx48/K79pLlwG182zoGiMWRBj0pwHZdBF6F14HmgSb110VRFGoUa3QPvrjfpq6pec8c2iWWl0k9P0to3pfRfTf71vqv99L/6UBy+hdZwtKAzOfLdotMp4X4APBhUesSIhD4tSoztGyB0Z9ZXjLOR7j2al0T+VRuM39Zx/+6OTFYvAc0VMKGrY4T6m2OmiZe0oZe7WBM8owzcqUnqo0R1ISXybvpr63UTBc85Ko9vi938v+jd/zSlO/0HYOXcmFA3kDuJfy0QW7TyF/BaY4Dixg96uD6jRHWc2bQGu4jcYLXrOWWl0uzr6W4FHf83hULsC7pIvkBbFmOa1/4soLNB7uA//rGI8N7FAb9cH1CjSS4Z9NY17B3lpdOvL7x79tcSu6Um+QFqYcrnXqETLohse0Xtwy76PGaSv9gM1+gaQ9GTSV243NCz8uMw0+sf2WPqv66N/3/53Pyu/Zs4slmk1+lzUqM9Z/U2qCX1HsOThle8UM7xUM8qiRt+pD9ab9JXk1JCz0WDQ2zEbTKr/sqSMV2YaffPoLz9/hJP+/uuPjC3aST6xL1oc/ZhOJ5vQb4AH6k7ZWDEXRuvmqtToO0OLttReAw8tnp0fbq6a9svL5ZcVQ8xNo50/dtr88ec//e2nn37/9Zftf/gtn/1L35knndgX7k5abv/VU7oJfUeQfO91UKm61v14NBzM3oYnvf5gUr/CWrvid/waLUjy2TBAumef+iCTRV+hPwsl52N3z4vHpKUlZbPTaKfz828/DvhzZqlOh8AJkg4UFpnbJr5fJ5zQdyT7vHw+X1eXYjzpF0w7e4NKV9THTZqo0b3uGQrm0LWzeou+wn5CxxUnFswKLnGiOS/a43FB/PGnLyL9c85D0R0pI02FY7mn1yfHnHYIOGvUJ8KkmtJflOc1Ts9LTRor+lyIzXsZptE1PTicdx7elvq+gloyrjZ67/CBG1g0pkbX/O0vf90q9Jc//57BAUwAV8lWSAtn9XeJh6KCdCen0lPy4yDHg5rX5LRYFUghzcZrdN074CLKJEJfQXPsca0Vvx4ka2HRyBo9Puap9jT5l45Xgc/pXSJM4sWqMWLDbsErDpUjboFG0QXJcYS+QhZ0xsAG//2zZM8sLEqN1vKYaECaNJBUCjyn92m/JOFlQ91I9J3p4SgXK+reCo2CGWZ1ZUcN+gqpMIvsS927EmLdaI+r0SzShJoS1GMG+gJu/nP4h31HmDI6EpykPvsy0wOPxmiHRrFur7uSQV8B6wtQlZTPWzKyKDWKMMfHYHY8p14GLQKva+1S+l42GK2Nenxh/5BR9IChlmgU2jdWV3XUoK+AHCxsMNp586iVRalRjMsES6RJionWAJclcdkiIBqMil+R7sfEPsUxbQfYvJdWGkWOhY+gUeCp4z28+TJZWZQaRbnDDWJEhkEmuGKzz9KoZDCqCcC+DbqSHBp8gM17aaVR5EbrptNRNIrO6Tf0BQ86zuNqBdFFmjpF9DtLuO0eS6OSwehIFYDdelTwcrVGo91wg0XR6EXdJfYxG4tSoyIii9T9nHcp+EZQlwCZYDAqep0+2ZTgkwxRWqNRILrjr1HA5dixUPbYPK7W8Bh1jXSe+nYPENSzdljYFeSMSuZ2X+hCeaYftEej9Veqq5UX3lfAF4AaPRIul/E0mlnO00KQQeuQZoBvYDLZmILQHo3Ogu80ikbrC035YPO4WsX8Ktrcfp76Xr8gyJ91qHwPTOneqN8OaEV7NAoozL2vgDJ56mlIIDaPq23cRUokzWo4KhmMOqQ74aWd4n1jqVH8TqOEmGq3pDqR05fymJjfRhmSzlPf5x6SzVwO7YbrX0ZcH6NG8TuNkzcKp9/bYvO4WsnLtb9JMxqOCsL0HnP6KfAObQGOBTKDGv2krnBzHI0mmtXbPK624m/SfHJHl4JWp5zTG2YD1kKN4gIz6Cuk1qxdSn38x9Vi5reuOVDZ5I4KNjAlndNHTXlpj0brtz5E0ChS+tRsm3yCx9VyHq/9yuQ/pr65NyR36OD+KfAGbd+iaFH6De3RaH2Nurq6zQZ9BZXiH6cQls3jIovLqxuXwqRPeRR6wks7vbrk3qMbQePmX7dHo/WTgQilScAT7RLk4Ns8LrJl/nh1Y75Y6nXcu+zOJD8RHiX+wDOBIie8tEaj0/r21JUljHWIyJqT6M6yeVxkj8vHq6WlTXMogy9a/024nz7yQKQ1GgVuNELZZnwHxkRQsNsCm8dFCrhc+3TNw82Gd61u/vn6SlRP3yF7SIpoSu/h/Sn29sRdGW2PRpF6ozH6Cs4dXq1GUTNIbR4XESIarCaf1r+IVn09kguALd0blIWd1LRFo0A5g9p0XYu+Qg5j+uBsEG9IavO4iBDZ8U6Jk0cXsjwEj6r94PsTO9kFjHm4kNlZTLW/YBYaBXbVf+GkH2l6YvO4iBD8aLgNiaP1S1ljPZqAHZZet5HGnHZoFIrs1M6hTUbu0pNhV6tJFJPaPC4iRaYml/PhUPCj6be4LEEg+1cSlElrhUb7UOfXyspEo6oOn5y7z+5tHheRItmh7uUmjBdZS10ONAVDtNG/qm3QKLaeUpd8b6RRJNZVxMh5TGrzuIgYYam9ZMeESsrjuQkfSxiMXyWt+Rrtg9Po+q3sNuE4MH+4ANfZvc3jImJEe9TXg7xE2aPC8JJTaT9sD1P9iMiahmu0e46uRQK/YDYa1Q5Ht0zckqBsHheRI6xoksij0rorPpX9MF3F3wTYZI2enuOntiBdb5QcFtbl4wufZA6bx0XkCIejacL1S2EjnepMY1O5+N/U5mn0tLdmMJgIEt1X2LYHI4125cH6r7ikk9o8LqJAOtC7j+9RsUWvfdqB5TtF3sLUaYJGbUDmAVZbFQQHxJYxMi9KavO4iALpcDS+R8UWdQnTd0CNJjiHhxrd9TzyA2a240u0lamEs4Htb67N4yIaxOfiRfao2KJueVlQXCHB+RHU6BZocGe3cVa24FDC2FSkNo+LaBDmjm48GjPOJLeo12AUOYQnRaCeGt2C/X7ZaXQaEq3/ZFxX2k+AzeMiKq7loorm0YXiDGm35FbotUhQrZcaXTPGQjaGZVxObTy6OjNzm83jIiqkqe0bj0YqUyLOF331rOgHvRTUaJr2gcmYltWwDMJMOyZGM3ubx0V0yOp4Og/59nnRlJ32Mzz0SlCjSdqHdrtpUcGe0XjU6uQmm8dFlGiOwotwdv2d5lgpx3ZBb0SCLyo1ipd4ta3NajWvN6pnY/O4iBJx0tN28jx3bpV8zfbVMb6EViahRhO0Dy+UbVziemoSr99wYjCxt3lcRIvOWK6nLs91p0Xf+rWIGlXernv7BMcNWJ8U0NVXKTngLHyDqM3jIloWurPvrv2Gfo+6c6I9jg75AHobqNHo7ZMc2mJ/4ApWCBVgHOxRm8dF1Kim9a+vT07xHE2e04bnuWcnQS8DNRq7faKgnsO5VVNsk3A9wR61eVxEj2pa7zUgVQ5FXaf0HUbqte+la/vGsrJzLsf/zUILlbzfS6BHbR4X0aOc1q8HpOYrpHNptZQPXKf01Kj2vfRs30hYKMnpFFW0rnQNZ2FxJpvHRQJQTus38jLd07SQHVe6j++UnhrVvpd+7ZPvpHQ7jNpGpLUHRFdi87hICHp9vS7nZq241c7n17hmDnRAjcY+pL7TYo1eyAdvbhpdT+0t1kiD8kdtHhcJQj2XthPpnXZpYdsG7w6CcgRZ4SlW+y40hY8dNdrpnF6ER+1DThixeVwkCMXeelORLm5DJBqhfh802oh+Sn1LNaqSqLNGO51uPzQfH6qaWoLN4yJh6JdHtzwEZT/Nr4MsHqPqFDZpi/a4PmifRs/OtbJx1uia6SBslTRgVcjmcZFAApZHtzzdakeEj8pE0U8i1ErBdMCzmJzbNx4G5AX5a3TN6TDEpPovkOe1CU6wzF4f7uQmfVmGDUQ3OB2/9AVMB4ZleE3b5UMKjYZkBUXR6JrpuXp2r19dt3lcJBRNfc8Ck84FH/m4DFoRfcM5Y3QHVl8yfqjeTw0276W15kMOGIil0U6ASdWuc7w0kTAPHxduuL9+RAall1ch2QH7nxfleKhT6CWIH2Nqm0ZDZBBRo2um/Yni9tTDUdeeIwJebDy6Udvy9rLcbpd310YKfY13qAn2FoRX6hHSOo0G/FLF1eiarmJMqj3C3uZxEQPuzOS2FdzNw9XV5eXlm+de1v94dbW8sZjHx7coeBhk9MXR49fo3lWmSBfrt4pF12hHEbvXfoNsHhexwNajMYhyoMkGrLZk2IY+BY3SKHYAvHa8lkSjHekOJ+03yOZxEROWqbWYq0U759hboH7HlTRLo11kJ5B6+TCRRjudnkSkylwEm8dFbDguj8azKHoUZOzqJM3SKLaUqt0zmUyj628PvkiqvDubx0WMOCaPRjha7xPsJYgdq2+YRrvISqI2eTShRtezGXTLvfKH2OZxESuOx6NRLQpuB1314z6thmm000f6WFkKKalGO6fggFS5ZmHzuIgZx+LRuBZFU3ciV3lqmkaxjAhdXllajXa6mEeV8xmbx0XsOA6PRrYomIAf+9vaOI1Ca9C6cHZijaIeTfm4iCHH4NEYG+m/Ai5uxR2ONk6j2OKJKrsytUaxlV9lsofN4yKW5O/RiDH6d9BTyUOK74ppnkahUb8qypRco9hQW6c7r+uSAG5TazI/i3ZmyDuwCj6bTEbzNIr9XGlKlKTXKHRv1GhzyHo/07P3yUvFOKesqGigRqdQJyukkIFGkeEoNdogLs3qlNhbNNY++gPQWX3MAiUN1CiWE6EIaGegUeSnmBptEi+2NUTsiFMZrwBwI1PUaX0TNQptCVWM+XPQKBBAo0YbxcKump0ly1QW7XTgYj0hxYU7ogT+JmoUG46OxRHtHDQKFF+hRhvGdWplFnCbsD/A8iSroOXRgaiGfiM1iv1eiTPLctAo0AZqtGnc5bZA+hx0Amko2Gxzi3pP6GY3pMCjzdQotCVUnFlm3ld9lxExNdo4XiwOaLLjJt2EfgscZFJ79HRr6hG8uNpMjWJbQqVL0NZ9tZb9iXQVHDhYhBptHotlanXucZW6N6bI2/2GyqOnb+Nd+PVsqEaxaJ6wRIlxX/VFD+oNIMSU8nERLx5zmdg/JZ3Q7xAMRzUbFk8/Vg3Q17OhGgXrackyy2z76lT2oOBepUabyTyPiP1D4gn9lin0dr9xIZ3x7S8Jgq9nUzWKFYKRRZlM++rjF+9M4nLgtljhqancph+QJtq49A3JcHR1IhstfU2GGUN/3FSNgh0tGvFb9tXnvGE1FoS6gLtivdHGknxAmjBZ9CtT6O3+eMMEr/m3sr6QRxurUayjRSVKDPvq9EvOBpzehqR6KGtS2zwu4kvSFdIcVkXfgQ6v/OQE/PJ2C95xxKON1ShYJjtNju3pgQ7RaQfy5VGmeNg8LuLMIlku/nPyAP0+gtzRHRMkt7BfmHA+rv/mN1ejYEcL5GDWV6ffmzZAhsVQ/oGyIINpTxE/XtLM7Jfz1Df+FXwr0zuTui9wv3TXTu3QpLkaBYejgoiMVV+dFgn+rH4UeYr8MIyTPi4Sgcf41UpuMprPvyE5dPz9HTsvH5JOh1VbH+tezgZrFCxhgO+7NeqrMhuOerq/+4q2HIPN4yJRuIsr0pwWRT9AD2X6ysmw4GvcnQ3rXFHj0SZrFNsSim/ItOmrChue9MM+fYPqeBSzx0XisLiKF2t6SlHjHgB8IQpes8ngvPfO+WACDbcGoW1R3qXNexmiUWxLKJ4hZNJX1Uu2Z8MSqffR6mC6k5io0WMjlkhzlWgHfb2tqAxGN1qjYIFXNG/Toq/qT/csmHb0auccn3+tfFrU6PERYWp/k0m6fSFTabQ+jCqPNlqj4DI0WqLEoK/AM5JHF4PNhON0/X+DoWgtXTunp0aPkUffqP0y0TEhKNiqnRkVHm22RsFlaDDKFN5XoEUDUJ+bYPO4SGRell5z+6erXLYslSPaExpO+Qb7ZmsU7Wcs1zK4r/wtKtlN4PG4SHQWdx7FSJc5z+Y/ibs8Wu7RhmsUXD7BokyhfeVvUXWAiRo9ZubXtqukN3f5D0R3dOGggQ1lHm24RtGsCGgHZWBfRbCofjBKjR43L2Ymvbmdp74ZAVgytR0nxQOVpmsU3BIKlSgJ66sIFg0YjFKjR8/LbfDs/nl5NOPQd2J7tDjNvOkaRffeIuO4oL6KYdGAgxCp0SaweFzqB6U3V5kH5ouZ+b9X+xRP6xuvUfRUa6AxQX0VwaLSs6UcHhdJzvzxWpwG9fRwm+N+T4yoaU8li6PN1yjYy0DeekhfxUjNkJ506vC4SB683F3fYJlQN8ury2ObyB8Q0aNltUebr1G0FEz9jDikryIMRgPiS2aPi+TE5ePV9U2JTm/W/ry7nKduogm9WOujpRWcW6BRcEtofYmSkL7yXxoNmtJTo43m5fILR7kGWkWkOFNr0++3gMPR2hJzWYeYsKO3vB8XISk4jZGHX3FKaBs0OgW7qW5tMbCvfJdHlWeHGD8uQpLQVVRxFjKpmO61QaOowOqmxaF95enRUItSo+S4UZcfBRkEfrjytmzeSxONohW1BqFtqekrv5BiWHjJ7nERkgrXQFPNKeit0Cj8SzUNvUpNO06dtgCHW5QaJcdOd+Lzdq1K94B+0A6NosexjgLbUl9v1OVJq4uMmj8uQhJy7jQgrU2GbIdG4eNY+2FtAfrK/kmPg9dF7R4XISlxGaac1CfBtESj6JbQyhIlNn01NY4pngVmOpk+LkLS0rNeNxsjlSraolE0ujOM0Fczyyc9Ccu6N35chKSmbzrfm0BV09qiUTQHv+pyZn3VHVg96XHQPnr7x0VIcuxer9UI/NK3RqPgltCqEiWGfdW1yXK7MBqKmj0uQjLASKSoRFukUXg4eh7QFkFfGTxp/ClHe1yE5EE/eHuo5PVqj0anYO+Vlygx7qvuedAa6ZlJgN74cRGSC72QXYPjC1Hktj0ahfdiTvRtkfbVTJ2fMTJbFDV9XITkQ7evfL9O+sLVshZpFN0SWnpFj77qaiYfwp/KiI+LkKxQmPTkPOBIM5KK6bnoSY8n1gNRQppMbwCnap9dSMehJCNmQ2xQejKkQwkR0zu/qHnDzkaDGYehR0+3N5hUxZzG68fMX0pC1Ex754PJ6GBoejIaDQczrlg1it5sMByNzr4+58ngvEeDEkIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEJaz/8HAyTxhK56rlUAAAAASUVORK5CYII=";
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

const pageColorNames={dispatch:'Thrift Mart Dispatch',paging:'Store Associate Paging',receipts:'Receipts & Accounting',print:'Dashboard',settings:'Settings',signin:'Sign-in Page'};
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
 if(!officeSecurityPage)return;
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
  controls.innerHTML=`<button type="button" data-comm-hide-group="${id}">Hide group</button><button type="button" data-comm-leave-group="${id}">Leave group</button>${commInbox.manage_groups?'<button type="button" id="commManageGroup">Manage group</button>':''}`;
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
  if(button.dataset.commLeaveGroup){if(!confirm('Leave this group? Its conversation and files remain on the server for authorized reviewers.'))return;await commApi('leave-group',{thread:Number(button.dataset.commLeaveGroup)});commScreen('home','Communications Hub');await commLoadInbox();return;}
  const {commDelete,commHideGroup,commRestoreGroup}=button.dataset;
  if(commDelete){
   if(!confirm('Delete this private message from your account and devices? This does not delete it for the other person. A retained copy remains available to authorized staff reviewers.'))return;
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
workMenu.textContent = 'Time Functions';
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
 workPanel.querySelector('.workHead h2').textContent=quick?'Time Clock':'Time Functions';
 workPanel.querySelector('.workTabs').hidden=quick;
 $('workQuickBack').hidden=!quick;
 setSectionHeader(quick?'Time Clock':'Time Functions','workforce');
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
  <p>CoastYouth Retail STORE OPS · ${esc(dateLabel(start))} through ${esc(dateLabel(end))}</p>
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
const roleCancel=document.createElement('button');roleCancel.type='button';roleCancel.textContent='Cancel changes';roleCancel.onclick=()=>{if(rolesData)showRole();changedForms.delete(roleForm);};$('roleForm').append(roleCancel);
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
function renderUserAccessPreview(grants,admin){const items=[['Dispatch',admin||grants.view_schedule],['Paging',admin||grants.send_pages||grants.receive_pages],['Receipts & Accounting',true],['Dashboard',true],['My Timekeeping',true],['Manager scheduling',admin||grants.manage_staff_schedule],['Payroll export',admin||grants.export_payroll],['Role management',admin||grants.manage_roles]];$('userAccessPreview').innerHTML=items.map(([label,enabled])=>`<div><strong>${label}</strong><span>${enabled?'Available':'Not enabled'}</span></div>`).join('');}
async function openUserSetup(name){
 if(!officeSecurityPage){toast('Manage users in CoastYouth Retail OFFICE.');return;}
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
 if(!force&&['#retail-users','#retail-roles'].includes(target)){if(!officeSecurityPage){location.replace('/office'+target);return;}history.replaceState(null,'',location.pathname+location.search);if(!guardUpdateNavigation())return;if(!can(target==='#retail-roles'?'manage_roles':'manage_users')){toast('Your role does not have access to this setting.');return;}tab('settings');settingsSection(4);selectUserSettings(target==='#retail-roles'?'roles':'users');return;}
 if(!force&&location.hash==='#office-timekeeping'){history.replaceState(null,'',location.pathname);workOpen(false,'time-cards');return;}
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
 if(typeof window.pywebview?.api?.request_exit!=='function'||document.querySelector('.posNativeToolbar'))return;
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
 const get=id=>document.getElementById(id);let state=null,info=null,busy=false,lastStatus='',deadline=0,campaignId=null,seconds=0,installing=false,acting=false,staffReady=false,lastUpdate=null,noticeError='',pollError='';
 const setBanner=shown=>{banner.hidden=!shown;document.body.classList.toggle('posInstallWarning',shown);if(!shown){staffReady=false;lastUpdate=null;noticeError='';window.posUpdateCountdownDone=false;}};
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
 function drawNotice(){
  if(banner.hidden||!info?.updater||!lastUpdate)return;
  seconds=Math.max(0,Math.ceil((deadline-Date.now())/1000));
  const button=get('posInstallReady');
  button.disabled=acting||installing;
  if(!inPos){button.textContent='Return to POS to finish update';}
  else button.textContent=lastUpdate.state==='error'?'Retry update download':staffReady?'Keep working':'My work is finished — update';
  window.posUpdateCountdownDone=seconds===0;
  const wait=seconds?'Warning time remaining: '+seconds+' seconds. ':'';
  let message=pollError||lastUpdate.error||noticeError;
  if(!message){
   if(lastUpdate.state==='downloading')message=wait+'Downloading and verifying the installer. '+(staffReady?'Your work is marked finished. The update will start when the download and warning time are complete.':'Finish your work, then select My work is finished — update when ready.');
   else if(lastUpdate.state==='ready')message=wait+(staffReady?'Your work is marked finished. Waiting for the warning time to end.':'Finish or hold the current sale and save your work, then select My work is finished — update.');
   else if(lastUpdate.state==='installing')message='Installing the update. DESK will reopen when finished.';
   else message=wait+'Checking update readiness. Your work has not been closed.';
  }
  if(lastUpdate.state==='error')message='Update paused: '+(message||'The installer could not be prepared.')+' Select Retry update download. Your sale is unchanged.';
  get('posInstallMessage').textContent=message;
 }
 async function attemptInstall(native){
  if(acting||installing||lastUpdate?.state!=='ready'||seconds>0)return;
  acting=true;drawNotice();
  try{
   const outcome=await native.install_update();
   if(outcome?.error){staffReady=false;noticeError=outcome.error;lastStatus=outcome.error;}
  }catch(error){staffReady=false;noticeError='Update paused: '+error.message;}
  finally{acting=false;if(!installing)drawNotice();}
 }
 for(const event of ['pointerdown','keydown','input'])document.addEventListener(event,e=>{
  if(staffReady&&!banner.contains(e.target)){staffReady=false;noticeError='';drawNotice();}
 },true);
 get('posInstallReady').onclick=async()=>{
  if(acting||installing)return;
  const native=window.pywebview?.api;
  if(!inPos){const result=await native.open_operations('pos');if(result.error)get('posInstallMessage').textContent=result.error;return;}
  if(!info?.updater){get('posInstallMessage').textContent='This older POS needs the one-time installer. Ask an administrator to finish this installation.';return;}
  noticeError='';
  if(lastUpdate?.state==='error'){
   staffReady=false;acting=true;drawNotice();
   try{
    // Older installed clients can retry safely too; they repeat their warning period.
    if(native.retry_update){lastUpdate=await native.retry_update(campaignId);deadline=Date.now()+Math.max(0,lastUpdate.seconds||0)*1000;}
    else{await native.update_status(null);lastUpdate=null;}
   }catch(error){noticeError='Unable to retry the download: '+error.message;}
   finally{acting=false;drawNotice();}
   await poll();return;
  }
  if(staffReady){staffReady=false;drawNotice();return;}
  if(unfinished()||posCurrent?.lines.length||flow?.active){noticeError='Finish or cancel your current sale, or hold it, and save all unfinished entries before updating.';drawNotice();return;}
  staffReady=true;drawNotice();await attemptInstall(native);
 };
 async function poll(){
  if(busy||acting||!user||installing)return;busy=true;
  try{
   node.hidden=!user.admin;
   if(location.hash==='#pos-updates'&&user.admin&&!dialog.open){get('openPosUpdates').click();history.replaceState(null,'',location.pathname);}
   const native=window.pywebview?.api?.kiosk_info?window.pywebview.api:null;
   if(native){
    info=await native.kiosk_info();
    if(info.device){
     const result=await api('pos-update/heartbeat',{device:info.device,version:info.version||'1.0.1',updater:!!info.updater,status:lastStatus||'Connected'});render(result);
    }
   }else if(user.admin&&dialog.open)render(await api('pos-update/state'));
   if(!native||!info?.device)return;
   const campaign=state?.campaign;
   if(!campaign||(campaign.target!=='all'&&campaign.target!==info.device&&!campaign.targets?.includes(info.device))){setBanner(false);campaignId=null;if(info.updater)await native.update_status(null);return;}
   if(info.updater){
    const update=await native.update_status(campaign.id);lastStatus=update.state==='complete'?'Update complete · POS '+info.version:update.error||update.state+(update.seconds?' · '+update.seconds+' seconds':'');
    if(update.state==='complete'||update.state==='idle'){setBanner(false);return;}
    if(campaignId!==campaign.id){staffReady=false;noticeError='';}
    pollError='';lastUpdate=update;seconds=Math.max(0,Number(update.seconds)||0);deadline=Date.now()+seconds*1000;campaignId=campaign.id;setBanner(true);drawNotice();
    if(inPos&&update.state==='ready'&&seconds===0&&(staffReady||campaign.mode==='force'||campaign.automatic)&&!unfinished())await attemptInstall(native);
   }else{
    if(campaignId!==campaign.id){campaignId=campaign.id;deadline=Date.now()+campaign.seconds*1000;}
    setBanner(true);get('posInstallReady').disabled=true;get('posInstallMessage').textContent='An update is pending. Finish your transaction. This older POS requires an administrator to install the new version once.';lastStatus='One-time installer required';
   }
  }catch(e){if(!banner.hidden){pollError='Update paused: '+e.message;get('posInstallMessage').textContent=pollError;}}
  finally{busy=false;}
 }
 setInterval(drawNotice,1000);
 setInterval(poll,4000);window.addEventListener('pywebviewready',poll);setTimeout(poll,1000);
 if(inPos){
  window.posUpdateFreeze=()=>{
   if(unfinished()||posCurrent?.lines.length||flow?.active)return false;
   installing=true;window.posUpdateInstalling=true;document.body.classList.add('posInstalling');get('posInstallMessage').textContent='Installing POS update. The application will reopen when finished.';return true;
  };
  window.posUpdateUnfreeze=()=>{installing=false;window.posUpdateInstalling=false;document.body.classList.remove('posInstalling');};
  const original=posDo;posDo=async function(action,...args){if(window.posUpdateInstalling)return;if(action==='new'&&window.posUpdateCountdownDone&&!banner.hidden){posMessage('An update is pending. Finish this transaction and update before starting another.');return;}return original(action,...args);};
 }
})();

// BEGIN REPORT CENTER
// Shared read-only reporting interface embedded into Operations and OFFICE.
function retailReportCenter(root,mode='sales'){
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const dollar=n=>n===null?'Not available':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
 const sales=[['dashboard','Dashboard'],['donations','Donation performance'],['donations-employee','Donations by employee'],['sales','Sales report'],['transactions','Transaction log'],['cash','Cash summary'],['drawer','Drawer summary'],['cash-reconciliation','Cash-drawer reconciliation'],['employee-time','Employee sales by time'],['products','Products sold'],['sub-departments','Sales by Sub Department'],['departments','Sales by Department'],['revenue-centers','Sales by Revenue Center'],['modifiers','Products & modifiers'],['products-hour','Products sold by hour'],['seven-day','Revenue by day and hour'],['pricing','Pricing'],['hierarchy','Reporting hierarchy'],['tax-assignment','Tax assignment'],['tax-audit','Tax audit'],['accounts','Account information'],['adjustments','Adjustments log'],['journal','Sales journal'],['tabs','Open and held sales'],['reservations','Reservation schedule']];
 const labor=[['labor','Labor hours'],['time-entries','Time entries'],['schedule','Print employee schedule']];
 const choices=mode==='cash-advances'?[['cash-advances','Employee cash advances']]:mode==='labor'?labor:mode==='schedule'?[labor[2]]:sales;
 const today=new Date(),date=d=>new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10);
 root.innerHTML=`<section class="retailReport"><h1>${mode==='cash-advances'?'Employee cash advances':mode==='dashboard'?'Dashboard':mode==='labor'?'Labor & time reports':mode==='schedule'?'Print schedule':'Sales analysis'}</h1><form class="rrFilters"><label>Store<select name="store_id"><option value="thrift-mart">Thrift Mart</option><option value="binopoly">Binopoly</option><option value="">All stores</option></select></label><label>Report<select name="kind">${choices.map(([k,t])=>`<option value="${k}">${t}</option>`).join('')}</select></label><label>From<input type="date" name="start" value="${date(today)}" required></label><label>Through<input type="date" name="end" value="${date(today)}" required></label>${mode==='cash-advances'?'<label>Employee name<input name="employee" type="search" placeholder="All employees"></label>':''}<button>Run report</button><button type="button" data-rr-print>Print</button><button type="button" data-rr-export>Export CSV</button></form><p class="rrStatus" role="status"></p><div class="rrResult"></div></section>`;
 let result=null;const form=root.querySelector('form'),status=root.querySelector('.rrStatus'),output=root.querySelector('.rrResult');
 root.querySelector('[data-rr-print]').onclick=async()=>{if(!result)return;let print=document.getElementById('retailPrintReport');if(print)print.remove();print=document.createElement('section');print.id='retailPrintReport';print.classList.toggle('rrWide',(result.columns?.length||0)>6);print.innerHTML=output.innerHTML;document.body.append(print);await Promise.all([...print.querySelectorAll('img')].map(img=>img.decode().catch(()=>{})));document.body.classList.add('retailPrinting');try{window.print();}finally{document.body.classList.remove('retailPrinting');print.remove();}};
 root.querySelector('[data-rr-export]').onclick=()=>{if(!result?.rows){status.textContent='Choose a detailed report to export rows.';return;}const cell=v=>'"'+String(v??'').replace(/^[=+@\-]/,"'$&").replace(/"/g,'""')+'"';const csv=[result.columns,...result.rows].map(r=>r.map(cell).join(',')).join('\r\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));a.download='CoastYouth-'+result.document.kind+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
 const chart=(title,values)=>{const entries=Object.entries(values),max=Math.max(1,...entries.map(x=>Math.abs(x[1])));return `<article class="rrCard"><h2>${title}</h2>${entries.length?entries.map(([name,n])=>`<div class="rrBar"><div><span>${escape(name)}</span><strong>${dollar(n)}</strong></div><div class="rrTrack"><i style="width:${Math.abs(n)/max*100}%;background:${n<0?'#b54a45':'#0969ed'}"></i></div></div>`).join(''):'<p>No activity in this period.</p>'}</article>`;};
 form.onsubmit=async e=>{e.preventDefault();status.textContent='Loading…';result=null;output.replaceChildren();try{const end=new Date(form.elements.end.value+'T00:00:00');end.setDate(end.getDate()+1);const endLocal=date(end)+'T00:00:00';const q=new URLSearchParams({store_id:form.elements.store_id.value,kind:form.elements.kind.value,...(form.elements.employee?{employee:form.elements.employee.value}:{}),start:form.elements.start.value+'T00:00:00',end:endLocal});result=await api('retail-reports?'+q);if(result.rows){output.innerHTML=`<h2>${escape(result.title)}</h2><div class="rrTable"><table><thead><tr>${result.columns.map(c=>`<th>${escape(c)}</th>`).join('')}</tr></thead><tbody>${result.rows.map(r=>`<tr>${r.map(v=>`<td>${escape(v)}</td>`).join('')}</tr>`).join('')||`<tr><td colspan="${result.columns.length}">No records in this period.</td></tr>`}</tbody></table></div>`;}else{const delta=result.prior_net?((result.net-result.prior_net)/Math.abs(result.prior_net)*100).toFixed(1)+'%':'N/A';output.innerHTML=`<h2>${escape(result.store||'CoastYouth Retail')}</h2><div class="rrMetrics">${[['Gross sales',dollar(result.gross)],['Net sales',dollar(result.net)],['Transactions',result.transactions],['Average net sale',dollar(result.average)],['Prior-period change',delta],['Labor % of net sales','Not available']].map(([a,b])=>`<article class="rrCard"><span>${a}</span><strong>${b}</strong></article>`).join('')}</div><article class="rrCard"><h2>Donation performance</h2><div class="rrMetrics">${[['Donations',dollar(result.donations.total)],['Donating transactions',result.donations.donors],['Participation',result.donations.participation===null?'N/A':result.donations.participation+'%'],['Average donation',dollar(result.donations.average)],['Donations per 1,000 transactions',dollar(result.donations.per_thousand)]].map(([a,b])=>`<div><span>${a}</span><strong>${b}</strong></div>`).join('')}</div><p>Voluntary donations are separate from merchandise revenue.</p></article><div class="rrCharts">${chart('Net sales over time',result.buckets)}${chart('Net sales by item',result.items)}${chart('Net sales by Sub Department',result.categories)}${chart('Net sales by employee',result.employees)}</div><article class="rrCard"><h2>Who’s working · shared employee directory</h2>${result.working===null?'<p>Time card or payroll permission required.</p>':`<strong>${result.working.length} employees clocked in</strong><p>${result.working.map(escape).join(', ')}</p>`}</article>`;}const doc=result.document,heading=result.title||choices.find(x=>x[0]===doc.kind)?.[1]||'Report';const existingTitle=output.querySelector(':scope>h2');if(existingTitle)existingTitle.remove();output.insertAdjacentHTML('afterbegin',`<header class="rrDocumentHeader">${doc.logo?`<img src="${escape(doc.logo)}" alt="${escape(doc.store)} logo">`:`<span class="rrBrandMark" aria-hidden="true">${escape(doc.store.split(/\s+/).slice(0,2).map(w=>w[0]).join(''))}</span>`}<div><p>COASTYOUTH RETAIL · REPORTS</p><strong>${escape(doc.store)}</strong><h2>${escape(heading)}</h2></div></header><div class="rrDocumentMeta"><span><b>Period:</b> ${escape(doc.start)} through ${escape(doc.end)}</span><span><b>Scope:</b> ${escape(doc.scope)}</span><span><b>Generated:</b> ${escape(new Date(doc.generated).toLocaleString())}</span></div>${result.rows?'<h3 class="rrSectionBar">Report details · '+result.rows.length+' records</h3>':''}`);if(result.summary)output.querySelector('.rrDocumentMeta').insertAdjacentHTML('afterend',`<div class="rrMetrics">${result.summary.map(([name,value])=>`<article class="rrCard"><span>${escape(name)}</span><strong>${escape(value)}</strong></article>`).join('')}</div>`);output.insertAdjacentHTML('beforeend',`<footer class="rrDocumentFooter">${escape(result.note||'Report dates use the server’s local time.')}<br>${escape(doc.store)} · ${escape(heading)}</footer>`);status.textContent=result.note||'Report ready. Dates use the server’s local time.';}catch(err){status.textContent=err.message;}};
 if(['labor','schedule'].includes(mode)){form.elements.store_id.value='';form.elements.store_id.closest('label').hidden=true;}
 if(!['labor','schedule'].includes(mode)&&typeof retailStoreChoice!=='undefined')form.elements.store_id.value=retailStoreChoice;
 form.requestSubmit();
}

// END REPORT CENTER

const storeSectionBeforeDashboard=storeSection;storeSection=function(section){storeSectionBeforeDashboard(section);if(section==='print'&&!printPage.hidden)retailReportCenter(printPage,'dashboard');};
const printStaffSchedule=document.createElement('button');printStaffSchedule.type='button';printStaffSchedule.textContent='Print employee schedule';printStaffSchedule.onclick=()=>{const d=document.createElement('dialog');d.className='schedulePrintDialog';d.innerHTML='<button type="button">Close</button><div></div>';d.querySelector('button').onclick=()=>{d.close();d.remove();};document.body.append(d);d.showModal();retailReportCenter(d.querySelector('div'),'schedule');};
setInterval(()=>{const nav=document.querySelector('#workManagerMenu>div');if(nav&&!printStaffSchedule.isConnected)nav.append(printStaffSchedule);printStaffSchedule.hidden=!can('manage_staff_schedule');},2000);

// Keep business panels together, followed by communication and time tools.
const viewPanelDivider=document.createElement('hr');
viewPanelDivider.setAttribute('role','separator');
const panelMenu=$('storeMenu');
panelMenu.prepend($('printSection'),$('dispatchSection'),$('pagingSection'),$('receiptsSection'),viewPanelDivider,$('commsSection'),$('workforceSection'));

const commTestNotification=document.createElement('button');commTestNotification.type='button';commTestNotification.textContent='Send test notification';$('commDeviceStatus').before(commTestNotification);
commTestNotification.onclick=async()=>{try{
 if(!('Notification' in window))throw Error('This browser does not support notifications.');
 const permission=Notification.permission==='default'?await Notification.requestPermission():Notification.permission;
 if(permission!=='granted')throw Error('Allow notifications for this site in your browser or device settings first.');
 const registration=await navigator.serviceWorker?.getRegistration();
 if(registration)await registration.showNotification('CoastYouth Retail STORE OPS',{body:'Test notification: notifications are working on this device.',icon:'/app-icon-192.png',tag:'store-ops-test'});
 else new Notification('CoastYouth Retail STORE OPS',{body:'Test notification: notifications are working on this device.',icon:'/app-icon-192.png'});
 $('commDeviceStatus').textContent='Test sent to this device. This checks local notification display, not background server delivery.';
 }catch(e){$('commDeviceStatus').textContent=e.message;}};

if(location.pathname==='/office-timekeeping')document.body.classList.add('officeTimeEmbed');

// BEGIN FULFILLMENT PRINT
// Shared DESK / STORE OPS printing of the saved sale and saved sold slip.
function fulfillmentEscape(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fulfillmentMoney(v){return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(v/100);}
function fulfillmentLine(l){return fulfillmentEscape(l.name)+(l.weight_milli?` · ${(l.weight_milli/1000).toFixed(3)} lb × ${fulfillmentMoney(l.price_per_lb)}/lb`:'');}
function fulfillmentSlipMarkup(p,sale){
 const e=fulfillmentEscape;
 return ['CUSTOMER PICKUP SLIP','SOLD · HOLD FOR CUSTOMER'].map(title=>`<section class="fulfillmentTicket"><h1>${title}</h1><h2>${e(sale.settings.store)}</h2><h3>Receipt #${p.sale}</h3><p>${e(p.customer)} · ${e(p.contact)}</p><p>Storage: ${e(p.location)} · Due: ${e(p.due)}</p><p>Status: ${e(p.status.replaceAll('_',' '))}</p><ul>${sale.lines.filter(l=>!l.donation&&!l.gift_certificate).map(l=>`<li>${l.quantity} × ${fulfillmentLine(l)}</li>`).join('')}</ul><p>${e(p.notes)}</p><p>Dispatch: ${e(p.dispatch_reference||'Not scheduled')}</p></section>`).join('');
}
function fulfillmentReceiptMarkup(s){
 const e=fulfillmentEscape,m=fulfillmentMoney,r=s.receipt_design||{};
 return `<section>${r.logo?`<img alt="Store logo" style="max-width:160px" src="${e(r.logo)}">`:''}<h1>${e(s.settings.store)}</h1><p>${e(r.address)}<br>${e(r.phone)}</p><h2>Receipt #${s.id}</h2><p>${e(s.at)} · ${e(s.cashier)}</p><table><thead><tr><th>Item</th><th>Qty</th><th>Amount</th></tr></thead><tbody>${s.lines.map(l=>`<tr><td>${fulfillmentLine(l)}</td><td>${l.quantity}</td><td>${m(l.subtotal)}</td></tr>`).join('')}</tbody></table><p>Subtotal: ${m(s.subtotal)}<br>Tax: ${m(s.tax)}<br><strong>Total: ${m(s.total)}</strong><br>${s.store_credit?`Store credit: ${m(s.store_credit)} · ${e(s.credit_account)}<br>`:''}Cash received: ${m(s.tender)}<br>Change: ${m(s.change)}${s.cash_rounding?'<br>Cash rounding: '+m(s.cash_rounding):''}</p><p>${e(r.policy)}</p><p>${e(r.footer)}</p></section>`;
}
function fulfillmentPrint(title,html){
 if(window.pywebview){
  const frame=document.createElement('iframe');frame.title=title;frame.style.cssText='position:fixed;width:1px;height:1px;left:-10000px;border:0';
  frame.onload=async()=>{try{await Promise.all([...frame.contentDocument.images].map(img=>img.decode().catch(()=>{})));frame.contentWindow.focus();frame.contentWindow.print();}catch(e){alert('Unable to print. Please try again.');}finally{setTimeout(()=>frame.remove(),60000);}};
  frame.srcdoc='<!doctype html><html><head><title>'+fulfillmentEscape(title)+'</title><style>body{font:16px Arial;padding:24px;color:#111;background:white}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}.fulfillmentTicket+ .fulfillmentTicket{break-before:page}p{white-space:pre-line}</style></head><body>'+html+'</body></html>';
  document.body.append(frame);return true;
 }
 const w=window.open('','_blank');if(!w)return false;
 w.document.write('<!doctype html><html><head><title>'+fulfillmentEscape(title)+'</title><style>body{font:16px Arial;padding:24px;color:#111;background:white}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}.fulfillmentTicket+ .fulfillmentTicket{break-before:page}p{white-space:pre-line}</style></head><body>'+html+'</body></html>');w.document.close();w.focus();w.print();return true;
}

// END FULFILLMENT PRINT
// BEGIN DELIVERY WORKSPACE
// Reuse the actual Operations editor and calendar; no second reservation store.
window.retailDeliveryContext=null;
const deliveryLandingBefore=chooseLanding;
chooseLanding=async function(force=false){
 const match=location.hash.match(/^#pos-delivery-([1-9][0-9]{0,12})$/);
 if(!force&&match){try{await deliveryWorkspace(Number(match[1]));}catch(e){toast(e.message);}return;}
 return deliveryLandingBefore(force);
};
function deliveryRequest(){return Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('');}
async function deliveryReturnToDesk(){
 if(window.pywebview?.api?.open_operations){const r=await window.pywebview.api.open_operations('pos');if(r.error)toast(r.error);}
 else location.assign('/pos');
}
async function deliveryWorkspace(ident){
 if(window.retailDeliveryContext)return;
 if(!guardUpdateNavigation())return;
 const context=await api('pos/pickup-followup?sale='+ident);
 if(!context.can_schedule)throw Error('Your account needs View schedule and Create appointments permissions. The sold slip remains saved for an authorized scheduler.');
 if(context.followup?.appointment){toast('Delivery is already scheduled: '+context.followup.appointment);storeSection('dispatch');return;}
 if(context.followup?.step!=='scheduling'||!context.pickup)throw Error('Choose delivery from the saved pickup-slip follow-up in DESK first.');
 await refresh();if(!state.vehicles.length)throw Error('Add a delivery vehicle in STORE OPS settings before scheduling. The paid sale and sold slip remain saved.');
 expandedAppointments.clear();storeSection('dispatch');quickView(0);openJob(null,'Delivery');
 const editor=$('editor'),form=$('jobForm'),schedule=$('schedule'),nav=document.querySelector('.scheduleNav');
 const anchors=[schedule,nav].map(node=>{const marker=document.createComment('delivery-workspace-return');node.before(marker);return {node,marker};});
 const calendar=document.createElement('section');calendar.id='deliveryCalendar';calendar.setAttribute('aria-label','Delivery calendar');calendar.innerHTML='<h2>Appointments · this week</h2><p>Review existing bookings before choosing the delivery time.</p>';calendar.append(nav,schedule);editor.append(calendar);
 const footer=document.createElement('footer');footer.id='deliveryFooter';footer.innerHTML='<button type="button" id="deliveryPrintReceipt">Reprint customer receipt</button><button type="button" id="deliveryPrintSlip">Reprint pickup / sold slips</button><button type="button" id="deliveryPageLoading">Page associate for loading</button><button type="button" id="deliveryNotNeeded">No delivery needed — return to POS</button>';editor.append(footer);
 const message=document.createElement('p');message.id='deliveryReceiptContext';message.textContent='Paid receipt #'+ident+' · '+context.sale.settings.store+' · Stored at '+context.pickup.location;form.querySelector('.dialogTop').after(message);
 editor.classList.add('deliveryWorkspace');window.retailDeliveryContext=context;
 $('editTitle').textContent='New delivery appointment';form.elements.type.value='Delivery';form.elements.type.disabled=true;
 form.elements.customer.value=context.pickup.customer;form.elements.phone.value=context.pickup.contact;
 form.elements.items.value=context.sale.lines.filter(l=>!l.donation&&!l.gift_certificate).map(l=>l.quantity+' × '+l.name+(l.weight_milli?' ('+(l.weight_milli/1000).toFixed(3)+' lb)':'')).join('\n');
 form.elements.notes.value='Receipt #'+ident+' · '+context.sale.settings.store+'\nStorage: '+context.pickup.location+(context.pickup.notes?'\n'+context.pickup.notes:'');
 form.elements.start.value=context.pickup.due+'T09:00';form.elements.end.value=context.pickup.due+'T10:00';
 changedForms.set(form,formSnapshot(form));
 const previousClose=$('close').onclick;let leaving=false;
 const closeDraft=()=>{if(writesInFlight){toast('Wait for the save to finish.');return;}if(changedForms.has(form)&&!confirm('Close these unsaved delivery details? The paid sale and pickup slip will remain saved.'))return;changedForms.delete(form);editor.close();};
 $('close').onclick=closeDraft;const cancel=e=>{e.preventDefault();closeDraft();};editor.addEventListener('cancel',cancel);
 const protectCalendar=e=>{if(e.target.closest('[data-edit],[data-status]')){e.preventDefault();e.stopImmediatePropagation();toast('Finish this new delivery before editing an existing appointment.');}};schedule.addEventListener('click',protectCalendar,true);
 $('deliveryPrintReceipt').onclick=()=>{if(!fulfillmentPrint('Customer receipt #'+ident,fulfillmentReceiptMarkup(context.sale)))toast('Allow the print window to open.');};
 $('deliveryPrintSlip').onclick=()=>{if(!fulfillmentPrint('Pickup / sold ticket set',fulfillmentSlipMarkup(context.pickup,context.sale)))toast('Allow the print window to open.');};
 $('deliveryPageLoading').disabled=!can('send_pages');$('deliveryPageLoading').onclick=deliveryLoadingPage;
 $('deliveryNotNeeded').onclick=async()=>{
  if(writesInFlight){toast('Wait for the save to finish.');return;}
  if(changedForms.has(form)&&!confirm('Discard the unsaved delivery details and return to POS?'))return;
  try{await api('pos/pickup-followup',{sale:ident,revision:context.followup.revision,action:'skip',request:deliveryRequest()});leaving=true;changedForms.delete(form);editor.close();await deliveryReturnToDesk();}catch(e){$('formError').textContent=e.message;}
 };
 editor.addEventListener('close',async()=>{
  editor.classList.remove('deliveryWorkspace');for(const {node,marker}of anchors){marker.replaceWith(node);}calendar.remove();footer.remove();message.remove();editor.removeEventListener('cancel',cancel);schedule.removeEventListener('click',protectCalendar,true);$('close').onclick=previousClose;form.elements.type.disabled=false;window.retailDeliveryContext=null;changedForms.delete(form);history.replaceState(null,'',location.pathname+location.search);
  if(leaving)return;
  try{const current=await api('pos/pickup-followup?sale='+ident);if(current.followup?.appointment){const d=document.createElement('dialog');d.innerHTML='<h2>Delivery scheduled</h2><p>The delivery is linked to receipt #'+ident+'. The paid sale remains unchanged.</p><button type="button">Return to POS</button>';document.body.append(d);d.showModal();d.querySelector('button').onclick=()=>{d.close();d.remove();deliveryReturnToDesk();};}}catch(e){toast('Check the saved delivery before trying again: '+e.message);}
 },{once:true});
}
function deliveryLoadingPage(){
 const d=document.createElement('dialog');d.innerHTML='<h2>Page associate for loading</h2><p>Choose an existing paging area. Sending uses the current STORE OPS paging system.</p><label>Paging area<select></select></label><p role="status"></p><button type="button" data-send>Send page</button><button type="button" data-close>Close</button>';document.body.append(d);
 const select=d.querySelector('select');select.innerHTML=$('pageArea').innerHTML;const loading=[...select.options].find(o=>/load/i.test(o.textContent));if(loading)select.value=loading.value;
 d.querySelector('[data-close]').onclick=()=>{d.close();d.remove();};d.querySelector('[data-send]').onclick=async()=>{const b=d.querySelector('[data-send]');b.disabled=true;try{await api('paging/send',{area:select.value});d.querySelector('[role=status]').textContent='Page queued for enabled speaker devices. Playback is not confirmed.';}catch(e){d.querySelector('[role=status]').textContent=e.message;}finally{b.disabled=false;}};d.showModal();
}


// END DELIVERY WORKSPACE

// BEGIN OFFICE SECURITY
// OFFICE owns shared account administration; STORE OPS keeps staff self-service.
if(officeSecurityPage){
 document.body.classList.add('officeSecurityEmbed');document.title='CoastYouth Retail OFFICE · Users & roles';
 const securityLandingBefore=chooseLanding;
 chooseLanding=async function(){
  if(!user)return;
  tab('settings');settingsSection(4);
  selectUserSettings(location.hash==='#retail-roles'?'roles':'users');
 };
}

// END OFFICE SECURITY

// Theme preference is shared with DESK and OFFICE.
async function opsRetailTheme(){if(!user)return;const pref=await api('account/retail-theme');document.body.dataset.retailTheme=pref.theme==='default'?pref.default:pref.theme;}
const glassBoot=boot;boot=async function(){await glassBoot();await opsRetailTheme();};
const glassSelect=document.createElement('select');glassSelect.setAttribute('aria-label','Liquid glass color');glassSelect.innerHTML='<option value="">Choose liquid glass color</option>'+['blue','teal','violet','rose','graphite'].map(x=>`<option value="glass-${x}">${x[0].toUpperCase()+x.slice(1)}</option>`).join('');$('appearanceMode').after(glassSelect);glassSelect.onchange=async()=>{try{const old=await api('account/retail-theme');await api('account/retail-theme',{scope:'user',theme:glassSelect.value,revision:old.revision});await opsRetailTheme();}catch(e){toast(e.message);}};if(user)opsRetailTheme();

const hrOpsButton=document.createElement('button');hrOpsButton.textContent='HR · Onboarding';hrOpsButton.hidden=true;hrOpsButton.onclick=()=>window.open('/hr','_blank','noopener');$('settingsTab').after(hrOpsButton);const hrOpsBoot=boot;boot=async function(){await hrOpsBoot();hrOpsButton.hidden=!user||!can('manage_hr');};if(user)hrOpsButton.hidden=!can('manage_hr');

api('account/retail-theme').then(pref=>{document.body.dataset.retailTheme=pref.theme==='default'?pref.default:pref.theme;}).catch(()=>{});
api('session').then(s=>{hrOpsButton.hidden=!s.user||!(s.user.admin||s.user.grants?.manage_hr);}).catch(()=>{});
// BEGIN TERMINAL REGISTRATION
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

// END TERMINAL REGISTRATION
