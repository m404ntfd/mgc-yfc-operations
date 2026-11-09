async function pickupLoadPending(){
 if(officeMode)return;const {pending}=await api('pos/pickup-pending');let b=$('pickupPending');
 if(!b){b=document.createElement('button');b.id='pickupPending';b.type='button';receiptTools.append(b);}
 b.hidden=!pending.length;b.textContent='Pickup / delivery follow-up'+(pending.length?' ('+pending.length+')':'');b.onclick=()=>pickupResume(pending[0].sale);
}
async function pickupAfterPayment(sale){
 if(officeMode||!sale.lines.some(l=>l.pickup_slip))return;
 try{await pickupResume(sale.id);}catch(e){posMessage('Payment is saved. Resume pickup / delivery follow-up: '+e.message);}
}
async function pickupResume(ident){
 if(posCurrent?.lines.length||unfinished()){posMessage('Finish or hold the current sale and save open forms before continuing the pickup follow-up.');return;}
 try{
 const context=await api('pos/pickup-followup?sale='+ident),f=context.followup;if(!f||f.step==='done'){posMessage(f?.appointment?'Delivery already scheduled: '+f.appointment:'Pickup follow-up completed.');await pickupLoadPending();return;}
 if(f.step==='slip'){await thriftPickupEditor(context.pickup||{sale:ident},context);return;}
 const question=f.step==='pickup'?'Would you like to print a pickup / sold ticket set?':f.step==='delivery'?'Would you like to set up a delivery?':'Continue setting up this delivery?';
 const d=thriftModal(f.step==='pickup'?'Payment collected · pickup slip':'Delivery for receipt #'+ident,`<p>Receipt #${ident} · ${esc(context.sale.settings.store)} · ${posMoney(context.sale.total)} paid</p><h3>${question}</h3><p>The sale is saved. This follow-up can be resumed without taking payment again.</p><div class="flowToolbar"><button class="primary" id="pickupYes">${f.step==='scheduling'?'Open delivery calendar':'Yes'}</button><button id="pickupNo">${f.step==='pickup'?'No pickup slip needed':'No delivery needed'}</button></div><p id="pickupFollowupStatus" role="status"></p>`);
 d.querySelector('#pickupNo').onclick=async()=>{try{await retailSave('pickup-followup',{sale:ident,revision:f.revision,action:'skip'});thriftClose(d);await pickupLoadPending();}catch(e){thriftError(d,e);}};
 d.querySelector('#pickupYes').onclick=async()=>{try{
  if(f.step==='pickup'){await retailSave('pickup-followup',{sale:ident,revision:f.revision,action:'slip'});thriftClose(d);await pickupResume(ident);}
  else {if(f.step==='delivery')await retailSave('pickup-followup',{sale:ident,revision:f.revision,action:'schedule'});thriftClose(d);await pickupOpenDelivery(ident);}
 }catch(e){thriftError(d,e);}};
 }catch(e){posMessage(e.message);}
}
async function pickupOpenDelivery(ident){
 if(window.pywebview?.api?.open_operations){const r=await window.pywebview.api.open_operations('delivery:'+ident);if(r.error)posMessage(r.error);}
 else location.assign('/#pos-delivery-'+ident);
}
function pickupPrintedConfirmation(context){
 const d=thriftModal('Confirm pickup / sold tickets',`<p>The print window has opened. If both tickets printed successfully, continue to delivery setup.</p><p>If printing was canceled or failed, return to the saved slip and print again.</p><div class="flowToolbar"><button id="pickupPrinted" class="primary">Tickets printed — continue</button><button id="pickupPrintAgain">Back to saved slip</button></div>`);
 d.querySelector('#pickupPrintAgain').onclick=()=>{thriftClose(d);pickupResume(context.sale.id);};
 d.querySelector('#pickupPrinted').onclick=async()=>{try{await retailSave('pickup-followup',{sale:context.sale.id,revision:context.followup.revision,action:'printed'});thriftClose(d);await pickupResume(context.sale.id);}catch(e){thriftError(d,e);}};
}
