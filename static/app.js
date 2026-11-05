'use strict';
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state={jobs:[],vehicles:[],users:[]},user,setup=false,mode='day',editing=null,timer;
const localDate=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
$('date').value=localDate(new Date());
$('mobileLink').href=location.origin+'/mobile';$('mobileLink').textContent=location.origin+'/mobile';
async function api(path,data){const r=await fetch('/api/'+path,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json','X-Dispatch':'1'}:{},body:data?JSON.stringify(data):undefined});const v=await r.json();if(!r.ok){if(r.status===401&&user){user=null;updateSignedInUser();clearInterval(timer);$('app').hidden=true;$('paging').hidden=true;$('receipts').hidden=true;setSectionHeader('Sign in','signin');$('auth').hidden=false;$('editor').close();$('passwordDialog').close();$('statusDialog').close();}throw Error(v.error||'Request failed');}return v;}
function toast(s){$('toast').textContent=s;$('toast').hidden=false;setTimeout(()=>$('toast').hidden=true,5000);}
async function boot(){try{const s=await api('session');setup=s.setup;user=s.user;if(!user){if(typeof stopPaging==='function')stopPaging();$('paging').hidden=true;$('receipts').hidden=true;setSectionHeader('Sign in','signin');$('sectionChooser').close();expandedAppointments.clear();$('requestsList').hidden=true;}updateSignedInUser();$('authTitle').textContent=setup?'Set up your store':'Welcome back';$('authHelp').textContent=setup?(s.local?'Create the administrator account. Then add your vehicles and employees.':'Open http://localhost:8080 on the server computer to create the first account.'):'Sign in to your operations workspace.';$('auth').hidden=!!user;$('app').hidden=!user;$('connection').textContent=user?'Connected to store':'Store server online';if(user){$('settingsTab').hidden=!user.admin;$('serverUpdateButton').hidden=!user.admin;if(!user.admin)tab('day');if(can('view_schedule'))await refresh();else applyPermissions();clearInterval(timer);timer=setInterval(()=>{if(can('view_schedule'))refresh().catch(()=>{});},10000);await chooseLanding();}}catch(e){$('connection').textContent='Server unavailable';$('offline').hidden=false;toast(e.message);}}
async function refresh(){try{state=await api('state');user.can_create=state.permissions.can_create;user.see_requests=state.permissions.see_requests;user.grants=state.permissions.grants;renderRequests();$('connection').textContent='● Connected · '+new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});$('offline').hidden=true;const value=$('filter').value;$('filter').innerHTML='<option value="">All vehicles</option>'+state.vehicles.map(v=>`<option>${esc(v)}</option>`).join('');$('filter').value=value;render();applyPermissions();checkUpdateNotice();$('vehicles').innerHTML=state.vehicles.map(v=>`<div class="listRow">${esc(v)}</div>`).join('')||'<p>No vehicles yet.</p>';$('users').innerHTML=state.users.map(v=>`<div class="listRow">${esc(v.name)}${v.admin?' · Administrator':''} <button type="button" data-password="${esc(v.name)}">Edit user / permissions</button></div>`).join('');}catch(e){if(e.message.includes('Schedule access required')){$('connection').textContent='Connected · schedule permission required';$('offline').hidden=true;toast('Ask an administrator to enable View schedule, search and filter in your employee permissions.');}else{$('connection').textContent='Disconnected';$('offline').hidden=false;}throw e;}}
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
function tab(t){mode=t;if(t==='settings'){loadUpdates();loadBackups();loadLoginSecurity();}$('schedule').hidden=['settings','reports'].includes(t);$('settings').hidden=t!=='settings';$('reports').hidden=t!=='reports';if(t==='reports')loadReport();render();}
function quickView(offset){const today=localDate(new Date());$('date').value=offset===null?today:shiftDate(weekStart(today),offset);tab(offset===null?'day':'week');}
function openJob(id,type){if(user.can_create&&!state.vehicles.length){toast('Add a vehicle in Settings first.');if(user.admin)tab('settings');return;}editing=id?[...state.jobs,...(state.requests||[])].find(j=>j.id===id):null;$('jobForm').reset();$('jobForm').elements.status.innerHTML=(user.can_create?['Scheduled','In Route / In Progress','Completed','Canceled']:['Requested','Canceled']).map(v=>`<option value="${v}">${v==='Canceled'?'Cancelled':v}</option>`).join('');$('jobVehicle').innerHTML=state.vehicles.map(v=>`<option>${esc(v)}</option>`).join('');const j=editing||{state:'MS',type:type||'Pickup',status:user.can_create?'Scheduled':'Requested',start:$('date').value+'T09:00',end:$('date').value+'T10:00'};for(const [k,v]of Object.entries(j))if($('jobForm').elements[k])$('jobForm').elements[k].value=v;
$('jobForm').elements.street.value=Object.hasOwn(j,'street')?j.street:(j.address||'');$('legacyAddress').hidden=!editing||!!j.street;
const assigned=j.staffNames|| (j.staff?[j.staff]:[]);const names=[...new Set([...state.users.map(u=>u.name),...assigned])];$('employeeOptions').innerHTML=names.map(n=>`<label><input type="checkbox" name="staffNames" value="${esc(n)}" ${assigned.includes(n)?'checked':''}> ${esc(n)}${state.users.some(u=>u.name===n)?'':' (previous assignment)'}</label>`).join('');$('employeeDropdown').open=false;employeeSummary();$('editTitle').textContent=editing?(editing.request?'Review request':'Appointment details'):(user.can_create?'New appointment':'Submit appointment request');$('save').textContent=editing?.request?'Approve & schedule':user.can_create?'Save appointment':'Submit request';$('remove').hidden=!editing;$('formError').textContent='';const form=$('jobForm');$('startLabel').textContent=user.can_create?'Start *':'Requested Date & Time';form.elements.start.required=!!user.can_create;
for(const name of ['end','vehicle']){form.elements[name].closest('label').hidden=!user.can_create;form.elements[name].disabled=!user.can_create;form.elements[name].required=!!user.can_create;}
$('employeeDropdown').closest('.employeeField').hidden=!user.can_create;
if(!user.can_create){form.elements.start.value='';form.elements.end.value='';}
layoutRequestForm();renderReviewPhotos();$('editor').showModal();}
$('login').onsubmit=async e=>{e.preventDefault();try{const wasSetup=setup;await api(setup?'setup':'login',Object.fromEntries(new FormData(e.target)));e.target.reset();await boot();if(wasSetup){tab('settings');settingsSection(3);}}catch(err){$('authError').textContent=err.message;}};
$('logout').onclick=async()=>{try{await api('logout',{});clearInterval(timer);await boot();}catch(e){toast(e.message);}};
$('dayTab').onclick=()=>quickView(null);$('weekTab').onclick=()=>quickView(0);$('nextWeekTab').onclick=()=>quickView(7);$('settingsTab').onclick=()=>tab('settings');$('addPickup').onclick=()=>openJob(null,'Pickup');$('addDelivery').onclick=()=>openJob(null,'Delivery');$('close').onclick=()=>$('editor').close();$('date').onchange=()=>{if(!$('date').value)$('date').value=localDate(new Date());tab('day');};$('filter').onchange=render;$('statusFilter').onchange=render;$('search').oninput=render;
for(const [id,step]of [['prev',-1],['next',1]])$(id).onclick=()=>{$('date').value=shiftDate($('date').value,step*(mode==='week'?7:1));render();};
$('jobs').onclick=e=>{const edit=e.target.closest('[data-edit]');const expand=!edit&&(e.target.closest('[data-expand],[data-toggle-appointment]')||e.target.closest('.job.collapsed'));if(expand){const id=expand.dataset.expand||expand.dataset.toggleAppointment||expand.dataset.appointment;if(expandedAppointments.has(id))expandedAppointments.delete(id);else expandedAppointments.add(id);render();return;}const b=e.target.closest('[data-edit]');if(b&&can('edit_appointments'))openJob(b.dataset.edit);const status=e.target.closest('[data-status]');if(status)openStatus(status.dataset.status);};
$('jobForm').onsubmit=async e=>{e.preventDefault();$('save').disabled=true;bottomRequestSubmit.disabled=true;try{await api('save',{...Object.fromEntries(new FormData(e.target)),staffNames:new FormData(e.target).getAll('staffNames'),photos:requestPhotos,...(editing?{id:editing.id,revision:editing.revision}:{})});$('editor').close();toast('Appointment saved.');await refresh().catch(()=>toast('Saved. Reconnect to refresh the schedule.'));}catch(err){$('formError').textContent=err.message;}finally{$('save').disabled=false;bottomRequestSubmit.disabled=false;}};
$('remove').onclick=async()=>{if(!editing||!confirm('Remove this appointment from the schedule? Use Canceled status instead if you want to keep its details.'))return;try{await api('delete',{id:editing.id,revision:editing.revision});$('editor').close();toast('Appointment removed.');await refresh().catch(()=>toast('Removed. Reconnect to refresh the schedule.'));}catch(e){$('formError').textContent=e.message;}};
for(const [id,path]of [['vehicleForm','vehicle'],['userForm','user']])$(id).onsubmit=async e=>{e.preventDefault();try{await api(path,Object.fromEntries(new FormData(e.target)));e.target.reset();await refresh();toast(path==='user'?'Employee account added.':'Vehicle added.');}catch(err){toast(err.message);}};
$('auditButton').onclick=async()=>{try{const a=await api('audit');$('audit').innerHTML=a.map(r=>`<div class="listRow">${esc(r.action)}<div class="muted">${esc(r.actor)} · ${esc(r.at.replace('T',' '))}</div></div>`).join('')||'<p>No changes yet.</p>';}catch(e){toast(e.message);}};
boot();

let updateVersion=null,updateBusy=false;
async function loadUpdates(){try{const r=await api('updates');$('updateVersion').textContent='Installed version: '+r.current;$('updateRepo').value=r.repository;$('lastUpdate').textContent=r.last?(r.last.error||'Last installed: '+r.last.version+' · '+r.last.at):'';if(!r.launcher)$('updateStatus').textContent='Use Start-Store-Dispatch.bat on the server to enable update installation.';}catch(e){toast(e.message);}}
$('updateConfig').onsubmit=async e=>{e.preventDefault();if(updateBusy)return;try{await api('update-config',{repository:$('updateRepo').value});updateVersion=null;$('installUpdate').hidden=true;$('releaseNotes').textContent='';$('updateStatus').textContent='Repository saved. Ready to check.';}catch(err){$('updateStatus').textContent=err.message;}};
$('checkUpdate').onclick=async()=>{if(updateBusy)return;updateBusy=true;$('checkUpdate').disabled=true;$('installUpdate').hidden=true;$('updateStatus').textContent='Checking GitHub…';try{const r=await api('update-check',{});updateVersion=r.available?r.latest:null;$('updateStatus').textContent=r.available?'Version '+r.latest+' is available.':'You are up to date (version '+r.current+').';$('releaseNotes').textContent=r.notes;$('installUpdate').hidden=!r.available;}catch(e){$('updateStatus').textContent=e.message;}finally{updateBusy=false;$('checkUpdate').disabled=false;}};
$('installUpdate').onclick=async()=>{if(updateBusy||!updateVersion)return;if(!confirm('Install version '+updateVersion+' and restart? Ask everyone to finish saving appointments first. All users will be signed out.'))return;updateBusy=true;$('installUpdate').disabled=true;$('updateStatus').textContent='Downloading and verifying the update…';try{await api('update-install',{version:updateVersion});clearInterval(timer);$('updateStatus').textContent='Restarting. This page will reload when the server is ready.';let tries=0;const poll=setInterval(async()=>{tries++;try{const r=await api('session');if(!r.user){clearInterval(poll);location.reload();}}catch{}if(tries>=45){clearInterval(poll);$('updateStatus').textContent='The server has not returned yet. Check its window on the Windows computer, then reload this page.';}},2000);}catch(e){$('updateStatus').textContent=e.message;}finally{updateBusy=false;$('installUpdate').disabled=false;}};

async function loadBackups(){try{const r=await api('admin/backup-settings');$('backupFolder').value=r.config.folder;$('backupEnabled').checked=r.config.enabled;$('journalEnabled').checked=r.config.journal_enabled!==false;const s=r.status;$('backupStatus').textContent=s?(s.error?'Last backup error: '+s.error:s.verified?`Verified backup: ${s.at} · ${s.counts.Pickup} pickups · ${s.counts.Delivery} deliveries · ${s.counts.photos} photos. ${s.file}. Confirm OneDrive is synced.`:'Previous backup has not been read-back verified. Use Back up now.'):'No complete backup saved yet.';$('journalStatus').textContent=`Dispatch Journal: ${r.journal.records} archived entries in ${r.journal.archives} files. `+(r.journal.status?.error?'Archiving paused: '+r.journal.status.error:'Records are archived only after a complete backup and successful read-back checks.');}catch(e){$('backupStatus').textContent=e.message;}}
$('backupConfig').onsubmit=async e=>{e.preventDefault();try{await api('admin/backup-settings',{folder:$('backupFolder').value,enabled:$('backupEnabled').checked,journal_enabled:$('journalEnabled').checked});$('backupStatus').textContent='Settings saved. Use Back up now to verify the destination.';}catch(err){$('backupStatus').textContent=err.message;}};
$('cloudBackup').onclick=async()=>{$('cloudBackup').disabled=true;$('backupStatus').textContent='Creating a complete backup…';try{const r=await api('admin/backup-now',{});await loadBackups();}catch(e){$('backupStatus').textContent=e.message;}finally{$('cloudBackup').disabled=false;}};

$('serverUpdateButton').onclick=()=>{tab('settings');settingsSection(2);$('updatePanel').scrollIntoView({behavior:'smooth',block:'start'});$('checkUpdate').click();};
$('users').onclick=e=>{const b=e.target.closest('[data-password]');if(!b)return;$('passwordForm').reset();$('passwordUser').value=b.dataset.password;$('passwordError').textContent='';const person=state.users.find(u=>u.name===b.dataset.password);$('canCreate').checked=!!person.can_create;$('seeRequests').checked=!!person.see_requests;$('canCreate').disabled=!!person.admin;$('permissionMessage').textContent='';loadPermissionList(b.dataset.password);$('passwordDialog').showModal();};
function closePassword(){$('passwordForm').reset();$('passwordDialog').close();}
$('passwordClose').onclick=closePassword;
$('passwordDialog').addEventListener('close',()=>$('passwordForm').reset());
$('passwordForm').onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));if(d.password!==d.confirm){$('passwordError').textContent='The passwords do not match.';return;}$('passwordSave').disabled=true;try{const r=await api('admin/password',d);closePassword();if(r.signed_out){clearInterval(timer);await boot();toast('Password changed. Sign in with your new password.');}else toast('Password changed. The user must sign in again.');}catch(err){$('passwordError').textContent=err.message;}finally{$('passwordSave').disabled=false;}};

async function retryConnection(){if(user)await refresh().catch(()=>toast('Cannot reach the server. Check the store Wi-Fi or VPN.'));else await boot();}
$('refresh').onclick=retryConnection;$('retry').onclick=retryConnection;
window.addEventListener('online',retryConnection);
window.addEventListener('offline',()=>{$('offline').hidden=false;$('connection').textContent='Disconnected';});
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

$('accountButton').onclick=()=>{$('accountForm').reset();$('accountError').textContent='';$('accountDialog').showModal();};
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
const settingsPanels=[...$('settings').children];
const settingsTabs=document.createElement('nav');settingsTabs.className='settingsTabs';settingsTabs.setAttribute('aria-label','Settings sections');
const settingsNames=['Phone Access','Backups','Updates','Vehicles','Employees','Recent Changes','Login Security'];
function settingsSection(index){settingsPanels.forEach((panel,i)=>panel.hidden=i!==index);[...settingsTabs.children].forEach((button,i)=>{button.classList.toggle('selected',i===index);button.setAttribute('aria-pressed',String(i===index));});}
settingsPanels.forEach((panel,i)=>{const button=document.createElement('button');button.type='button';button.textContent=settingsNames[i];button.onclick=()=>settingsSection(i);settingsTabs.append(button);});
$('settings').prepend(settingsTabs);settingsSection(0);

function updateSignedInUser(){ $('signedInUser').textContent=user?'Signed in as '+user.name:'';$('signedInUser').hidden=!user; }

let permissionCatalog={},savedUserGrants={};
async function loadPermissionList(name){$('savePermissions').disabled=true;$('permissionChecklist').textContent='Loading permissions…';try{const data=await api('admin/permission-catalog');permissionCatalog=data.permissions;savedUserGrants=Object.fromEntries(data.users.map(u=>[u.name,u.grants]));const person=state.users.find(u=>u.name===name);const defaults={view_schedule:true,submit_requests:true,cancel_appointments:true,call_contacts:true,text_contacts:true,navigate:true,change_own_password:true};for(const key of ['create_appointments','edit_appointments','delete_appointments','update_status','review_requests'])defaults[key]=!!person.can_create;defaults.see_requests=!!person.see_requests;const grants={...defaults,...(savedUserGrants[name]||{})};$('permissionChecklist').innerHTML=Object.entries(permissionCatalog).map(([key,label])=>`<label><input type="checkbox" data-grant="${key}" ${person.admin||grants[key]?'checked':''} ${person.admin?'disabled':''}> ${esc(label)}</label>`).join('');$('savePermissions').disabled=false;}catch(e){$('permissionMessage').textContent=e.message;}}
const permissionChecklist=document.createElement('div');permissionChecklist.id='permissionChecklist';$('permissionFields').prepend(permissionChecklist);
$('canCreate').closest('label').hidden=true;$('seeRequests').closest('label').hidden=true;
$('savePermissions').onclick=async()=>{try{const grants=Object.fromEntries([...document.querySelectorAll('[data-grant]')].map(input=>[input.dataset.grant,input.checked]));await api('admin/permissions',{name:$('passwordUser').value,grants,can_create:grants.create_appointments,see_requests:grants.see_requests});$('permissionMessage').textContent='Permissions saved.';await refresh();}catch(e){$('permissionMessage').textContent=e.message;}};

function can(key){return !!(user&&(user.admin||user.grants?.[key]));}
function applyPermissions(){
 $('notifyUpdateSection').hidden=!user.admin;
 $('filter').hidden=!can('show_vehicle_filter');$('search').hidden=!can('show_search');
 document.querySelectorAll('#jobs .editIcon').forEach(b=>b.hidden=!can('edit_appointments'));
 document.querySelectorAll('#jobs .statusUpdate').forEach(b=>b.hidden=!(can('update_status')||can('cancel_appointments')));
 for(const [selector,key] of [['.textCustomer','text_contacts'],['a[href^="tel:"]','call_contacts'],['a[aria-label^="Navigate"]','navigate']])document.querySelectorAll(selector).forEach(el=>el.hidden=!can(key));
 $('settingsTab').hidden=!user.admin&&!['backup_settings','create_backups','check_updates','configure_updates','install_updates','manage_vehicles','manage_users','reset_passwords','view_audit','unlock_users'].some(can);
 $('serverUpdateButton').hidden=!can('check_updates');
 $('reportsTab').hidden=!can('view_reports');
 $('accountButton').hidden=!can('change_own_password');$('remove').hidden=!editing||!can('delete_appointments');
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
$('addPhotos').onclick=()=>{if(/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)||navigator.maxTouchPoints>1)$('photoPicker').showModal();else $('photoFiles').click();};
$('chooseLibrary').onclick=()=>{$('photoPicker').close();$('photoFiles').click();};$('chooseCamera').onclick=()=>{$('photoPicker').close();$('cameraFile').click();};$('closePhotoPicker').onclick=()=>$('photoPicker').close();
$('photoPreviews').onclick=e=>{const b=e.target.closest('[data-remove-photo]');if(b){requestPhotos.splice(Number(b.dataset.removePhoto),1);renderPhotoPreviews();}};
async function readPhoto(file){const url=URL.createObjectURL(file);try{const img=new Image();img.src=url;await img.decode();const scale=Math.min(1,1280/img.width,1280/img.height),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.width*scale));canvas.height=Math.max(1,Math.round(img.height*scale));const ctx=canvas.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);return canvas.toDataURL('image/jpeg',.75).split(',')[1];}finally{URL.revokeObjectURL(url);}}
for(const id of ['photoFiles','cameraFile'])$(id).onchange=async e=>{const files=[...e.target.files];$('photoMessage').textContent='Preparing photos…';$('addPhotos').disabled=true;$('save').disabled=true;bottomRequestSubmit.disabled=true;try{for(const file of files){if(requestPhotos.length>=3){toast('Up to 3 photos per request.');break;}if(file.size>25000000)throw Error('Choose a photo smaller than 25 MB.');const photo=await readPhoto(file);if(photo.length>1333332)throw Error('Photo is too large. Choose a smaller image.');requestPhotos.push(photo);}renderPhotoPreviews();$('photoMessage').textContent=requestPhotos.length+' photo(s) attached. Tap Submit to upload with this request.';}catch(err){$('photoMessage').textContent='Unable to add photo. '+err.message+' Try selecting a JPEG from your photo library.';toast('Unable to add photo: '+err.message);}finally{e.target.value='';$('addPhotos').disabled=false;$('save').disabled=false;bottomRequestSubmit.disabled=false;}};

let reportJobs=[];
$('reportDate').value=localDate(new Date());
$('reportsTab').onclick=()=>tab('reports');
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

let pagingEnabled=false,pagingTimer=null,lastPageId=0,pagingBusy=false;
$('storeMenuButton').onclick=()=>{const open=$('storeMenu').hidden;$('storeMenu').hidden=!open;$('storeMenuButton').setAttribute('aria-expanded',String(open));};
function storeSection(section){
 section=section===true?'paging':section===false?'dispatch':section;
 $('storeMenu').hidden=true;$('storeMenuButton').setAttribute('aria-expanded','false');
 if(!user){toast('Sign in first.');return;}
 if(!['dispatch','paging','receipts'].includes(section))section='dispatch';
 if(section==='paging'&&!can('send_pages')&&!can('receive_pages')){toast('Ask an administrator for paging permission.');return;}
 $('paging').hidden=section!=='paging';$('app').hidden=section!=='dispatch';$('receipts').hidden=section!=='receipts';
 setSectionHeader({dispatch:'Thrift Mart Dispatch',paging:'Store Associate Paging',receipts:'Receipts & Accounting'}[section],section);
 $('pagingForm').hidden=!can('send_pages');$('enablePaging').disabled=!can('receive_pages')||pagingEnabled;
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
 $('currentSection').textContent=title;document.body.dataset.section=section;
 document.querySelector('meta[name="theme-color"]').content=({dispatch:'#b51f2b',paging:'#7a1520',receipts:'#067a06'})[section]||'#215baa';
}
let requestedReceipts=false;
function populateDailySections(preference){
 const choices=$('sectionChoices');choices.replaceChildren();
 for(const id of ['dispatch','paging','receipts'])$(id+'Section').hidden=!preference.options.some(o=>o.id===id);
 for(const option of preference.options){const label=document.createElement('label');label.className='sectionChoice';const input=document.createElement('input');input.type='radio';input.name='section';input.value=option.id;input.required=true;input.checked=option.id===(requestedReceipts?'receipts':preference.section||preference.options[0].id);label.append(input,document.createTextNode(option.label));choices.append(label);}
 $('sectionChoiceError').textContent='';$('sectionDay').textContent=preference.date+' (server calendar day)';
}
async function chooseLanding(force=false){const preference=await api('account/landing');populateDailySections(preference);if(preference.section&&!force){const target=requestedReceipts?'receipts':preference.section;requestedReceipts=false;storeSection(target);return;}setSectionHeader('Choose today’s starting page',false);if(!$('sectionChooser').open)$('sectionChooser').showModal();}
$('sectionChooserForm').onsubmit=async e=>{e.preventDefault();const section=new FormData(e.target).get('section');try{await api('account/landing',{section});requestedReceipts=false;$('sectionChooser').close();storeSection(section);}catch(err){$('sectionChoiceError').textContent=err.message;}};
$('sectionChooser').addEventListener('cancel',e=>e.preventDefault());
$('chooseStartSection').onclick=()=>{if(!user)return;$('storeMenu').hidden=true;$('storeMenuButton').setAttribute('aria-expanded','false');chooseLanding(true).catch(e=>toast(e.message));};
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
 const format=desktop.canPlayType('video/mp4; codecs="avc1.42E01E"')?'mp4':'webm';let timeout,started=false;
 desktop.poster=media.desktopposter;phone.poster=media.mobileposter;
 function seen(){try{return sessionStorage.getItem('yfc-intro-v3')==='1'}catch{return false}}
 function finish(){clearTimeout(timeout);phone.pause();intro.hidden=true;try{sessionStorage.setItem('yfc-intro-v3','1')}catch{}}
 function playIntro(){if(reduce.matches||$('auth').hidden)return;intro.hidden=false;phone.src=media['mobile'+format];phone.currentTime=0;phone.play().catch(finish);timeout=setTimeout(finish,27000)}
 function playDesktop(){if(!desktop.src)desktop.src=media['desktop'+format];desktop.play().then(()=>{$('pauseVideo').textContent='Pause video'}).catch(()=>{$('pauseVideo').textContent='Play video'})}
 function sync(){if($('auth').hidden){desktop.pause();if(!intro.hidden)finish();return;}if(!started){started=true;if(mobile.matches){if(!seen())playIntro()}else if(!reduce.matches)playDesktop();}}
 $('skipVideo').onclick=finish;phone.onended=finish;phone.onerror=finish;
 $('pauseVideo').onclick=()=>{if(desktop.paused)playDesktop();else{desktop.pause();$('pauseVideo').textContent='Play video'}};
 $('replayIntro').onclick=()=>{if(mobile.matches)playIntro();else{desktop.currentTime=0;playDesktop()}};
 $('receiptShortcut').onclick=()=>{requestedReceipts=true;$('receiptLoginHelp').textContent='Sign in first. Receipts & Accounting will open after sign-in.';$('login').elements.name.focus()};
 new MutationObserver(sync).observe($('auth'),{attributes:true,attributeFilter:['hidden']});
 mobile.addEventListener('change',()=>{finish();desktop.pause();if(!mobile.matches&&!reduce.matches&&!$('auth').hidden)playDesktop()});
 reduce.addEventListener('change',()=>{if(reduce.matches){finish();desktop.pause()}});sync();
})();
