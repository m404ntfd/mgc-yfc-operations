/* Shared availability is server-owned; browser timers never decide acceptance. */
function onlineRequestsMarkup(){
 const value=state.onlineRequests;
 const status=value?`Online Requests are ${value.paused?'paused':'active'}`:'Checking Online Requests…';
 const until=value?.paused?`<span>Automatically resumes ${esc(onlineRequestsDate(value.paused_until))}.</span>`:'';
 return `<div class="onlineRequestsControl"><div role="status"><strong><span aria-hidden="true">${value?.paused?'⏸':'●'}</span> ${status}</strong>${until}</div>${can('review_requests')&&value?`<button type="button" data-online-pause>Pause Online Requests</button>${value.paused?'<button type="button" class="secondary" data-online-resume>Resume now</button>':''}`:''}</div>`;
}
function onlineRequestsDate(stamp){return new Date(stamp*1000).toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});}
const onlineRequestsDialog=document.createElement('dialog');
onlineRequestsDialog.id='onlineRequestsDialog';
onlineRequestsDialog.setAttribute('aria-labelledby','onlineRequestsTitle');
onlineRequestsDialog.innerHTML=`<h2 id="onlineRequestsTitle">Pause Online Requests</h2><p>Pause new online donation pickup requests on coastyfc.com, thriftmart.coastyfc.com, and binopoly.coastyfc.com.</p><p>Existing requests and appointments stay available. Requests reopen automatically when the pause ends.</p><div class="onlinePauseChoices"><button type="button" data-pause-hours="8">8 hours</button><button type="button" data-pause-hours="12">12 hours</button><button type="button" data-pause-hours="24">24 hours</button></div><p id="onlinePauseError" role="alert"></p><button type="button" class="secondary" data-pause-close>Cancel</button>`;
document.body.append(onlineRequestsDialog);
let onlinePauseBusy=false,onlinePauseRevision=0;
$('pendingOverview').addEventListener('click',async event=>{
 const pause=event.target.closest('[data-online-pause]'),resume=event.target.closest('[data-online-resume]');
 if(!pause&&!resume)return;
 if(onlinePauseBusy)return;
 if(resume){await onlineRequestsSave({resume:true,revision:state.onlineRequests.revision},resume);return;}
 onlinePauseRevision=state.onlineRequests.revision;
 $('onlinePauseError').textContent='';onlineRequestsDialog.showModal();
});
async function onlineRequestsSave(data,button){
 onlinePauseBusy=true;button.disabled=true;
 for(const b of onlineRequestsDialog.querySelectorAll('button'))b.disabled=true;
 try{
  state.onlineRequests=await api('online-requests',data);renderTotals();
  onlineRequestsDialog.close();toast(data.resume?'Online Requests are active.':`Online Requests are paused until ${onlineRequestsDate(state.onlineRequests.paused_until)}.`);
 }catch(error){if(onlineRequestsDialog.open)$('onlinePauseError').textContent=error.message;else toast(error.message);await refresh();}
 finally{onlinePauseBusy=false;button.disabled=false;for(const b of onlineRequestsDialog.querySelectorAll('button'))b.disabled=false;}
}
onlineRequestsDialog.addEventListener('cancel',event=>{if(onlinePauseBusy)event.preventDefault();});
onlineRequestsDialog.addEventListener('click',event=>{
 const button=event.target.closest('button');if(!button||onlinePauseBusy)return;
 if(button.hasAttribute('data-pause-close')){onlineRequestsDialog.close();return;}
 if(button.dataset.pauseHours)onlineRequestsSave({hours:Number(button.dataset.pauseHours),revision:onlinePauseRevision},button);
});
