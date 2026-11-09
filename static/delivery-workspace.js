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

