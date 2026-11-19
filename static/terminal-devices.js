let receiptTerminalOptions=null;
async function terminalDeviceOptions(id){
 if(!can('manage_pos'))return;
 const args=id?{terminal:id}:{device:await retailDevice()};
 try{const options=await api('pos/terminal-options?'+new URLSearchParams(args)),native=window.pywebview?.api;
 let printers=[];if(native?.receipt_printers){const result=await native.receipt_printers();printers=result.printers||[];}
 const d=flowModal('Terminal setup · '+options.terminal.name,`<p><strong>${esc(options.terminal.store_name)} · Registered</strong></p><form id="terminalDevices"><label>Receipt printer<input name="printer" list="receiptPrinterNames" value="${esc(options.printer)}" maxlength="200" placeholder="Choose or enter its Windows printer name"></label><datalist id="receiptPrinterNames">${printers.map(p=>`<option value="${esc(p)}">`).join('')}</datalist><p>Receipts print automatically after payment. When configuring a different computer, enter the printer name exactly as it appears on that register.</p><label>Assigned customer-display link<input readonly value="${esc(options.display_path?new URL(options.display_path,location.origin).href:'Save to create this register’s display link')}"></label><label><input type="checkbox" name="replace_display"> Replace the display link (revokes its previous link)</label><p>Branding and messages come from ${esc(options.terminal.store_name)}. Keep this limited-access link on store devices.</p><button class="primary">Save terminal settings</button></form>${officeMode?'':'<button id="terminalRegistrationEdit" type="button">Computer registration</button>'}`);
 d.querySelector('form').onsubmit=async e=>{e.preventDefault();try{const f=e.target.elements;await retailSave('terminal-options-save',{...args,revision:options.revision,printer:f.printer.value.trim(),replace_display:f.replace_display.checked});changedForms.delete(e.target);thriftClose(d);await loadTerminalDevices();await terminalDeviceOptions(id);}catch(error){thriftError(d,error);}};
 d.querySelector('#terminalRegistrationEdit')?.addEventListener('click',()=>{if(changedForms.has(d.querySelector('form')))return;thriftClose(d);retailEnroll();});
 }catch(e){if(!officeMode&&!retailTerminal)return retailEnroll();posMessage(e.message);}
}
const originalTerminalEditor=retailTerminals;retailTerminals=function(){
 originalTerminalEditor();const root=$('retailEditor');
 for(const edit of root.querySelectorAll('[data-terminal]')){
  const b=document.createElement('button');b.type='button';b.textContent='Printer & customer display';b.onclick=()=>{if(!unfinished())terminalDeviceOptions(edit.dataset.terminal);};edit.after(b);
  if(officeMode){const remove=document.createElement('button');remove.type='button';remove.className='danger';remove.dataset.terminalRemove=edit.dataset.terminal;remove.textContent='Remove';remove.setAttribute('aria-label','Remove '+retailState.terminals.find(t=>t.id===edit.dataset.terminal).name);remove.onclick=()=>terminalRemoval(edit.dataset.terminal);b.after(remove);}
 }
 if(officeMode&&retailState.removed_terminals?.length){
  const history=document.createElement('details');history.id='removedTerminals';history.innerHTML=`<summary>Removed terminals (${retailState.removed_terminals.length})</summary><p>Sales, receipts, drawer history and settings are retained. Restore a terminal here to use its existing registration again.</p><table><thead><tr><th>Terminal</th><th>Store</th><th>Removed by</th><th>Removed</th><th></th></tr></thead><tbody>${retailState.removed_terminals.map(t=>`<tr><td>${esc(t.name)}</td><td>${esc(t.store_name)}</td><td>${esc(t.removed_by)}</td><td>${esc(new Date(t.removed_at).toLocaleString())}</td><td><button type="button" data-terminal-restore="${esc(t.id)}">Restore</button></td></tr>`).join('')}</tbody></table>`;root.append(history);
  for(const b of history.querySelectorAll('[data-terminal-restore]'))b.onclick=()=>terminalRemoval(b.dataset.terminalRestore,true);
 }
};
async function terminalRemoval(id,restore=false){
 if(!officeMode||!can('manage_pos'))return;
 if(unfinished()){posMessage('Save or clear the current form before changing terminal registration.');return;}
 const terminal=(restore?retailState.removed_terminals:retailState.terminals).find(t=>t.id===id);if(!terminal)return;
 const title=restore?'Restore terminal':'Remove terminal';
 const d=flowModal(title,`<p><strong>${esc(terminal.name)}</strong><br>${esc(terminal.store_name)}</p><p>${restore?'Restore this terminal with its previous store, layout, printer and device registration?':'Remove this terminal from the active list? Its checkout and customer display will stop working until an authorized user restores it in OFFICE.'}</p><p>Sales and cash-drawer activity stay in reports under the original terminal name. All audit logs are retained.</p><p>Existing sales, receipts, timecards, reservations and other records will stay intact.</p>${restore?'':'<p>Complete or cancel open and saved sales, and close its cash drawer before removing it.</p>'}<div class="flowToolbar"><button id="terminalRemovalConfirm" type="button" class="${restore?'primary':'danger'}">${title}</button><button id="terminalRemovalCancel" type="button">Cancel</button></div>`);
 let saving=false;d.beforeDismiss=()=>!saving;
 d.querySelector('#terminalRemovalCancel').onclick=()=>d.querySelector('.flowClose').click();
 d.querySelector('#terminalRemovalConfirm').onclick=async()=>{
  if(saving)return;saving=true;
  try{await retailSave(restore?'terminal-restore':'terminal-remove',{id,revision:terminal.revision,confirmed:true});thriftClose(d);retailState=await api('pos/retail-config');retailTerminals();$('terminalStatus').textContent=terminal.name+(restore?' restored.':' removed. Historical records are retained.');}
  catch(error){if(d.isConnected)thriftError(d,error);else posMessage('Terminal updated. Refresh the list to see the change.');}
  finally{saving=false;}
 };
}
customerDisplayEditor=async function(){
 const root=$('flowOffice');try{const s=await api('pos/store-display?store_id='+encodeURIComponent(retailStoreChoice));root.innerHTML=`<h2>Customer display · ${esc(s.store)}</h2><p>Logo and store name follow this location’s receipt branding. Assign the display link to each register in Terminal setup.</p><form id="customerDisplayForm"><label><input name="enabled" type="checkbox" ${s.enabled?'checked':''}> Enable displays for this store</label><label>Welcome message<input name="welcome" value="${esc(s.welcome)}" maxlength="200" required></label><label>Thank-you message<input name="thanks" value="${esc(s.thanks)}" maxlength="200" required></label><button class="primary">Save display settings</button></form><p id="customerSaveStatus" role="status"></p>`;
 root.querySelector('form').onsubmit=async e=>{e.preventDefault();try{const f=e.target.elements;await retailSave('store-display-save',{store_id:s.store_id,revision:s.revision,enabled:f.enabled.checked,welcome:f.welcome.value,thanks:f.thanks.value});changedForms.delete(e.target);await customerDisplayEditor();$('customerSaveStatus').textContent='Saved for this store.';}catch(error){$('customerSaveStatus').textContent=error.message;}};
 }catch(e){root.textContent=e.message;}
};
async function loadTerminalDevices(){
 if(officeMode||!user)return;
 try{receiptTerminalOptions=await api('pos/terminal-options?device='+encodeURIComponent(await retailDevice()));customerPairToken=receiptTerminalOptions.display_path.split('#')[1]||null;}catch{receiptTerminalOptions=null;customerPairToken=null;}
}
let receiptPrintBusy=false,receiptPrintQueue=Promise.resolve();
function deskPrintReceipt(sale,automatic=false){
 if(!sale)return Promise.resolve();
 const work=()=>performReceiptPrint(sale,automatic),result=receiptPrintQueue.then(work,work);
 receiptPrintQueue=result.catch(()=>{});return result;
}
async function performReceiptPrint(sale,automatic=false){
 const key='receipt-auto:'+location.origin+':'+sale.id;
 if(automatic&&localStorage.getItem(key))return;
 const native=window.pywebview?.api,printer=receiptTerminalOptions?.printer;
 if(automatic&&(!native?.receipt_print||!printer)){posMessage('Transaction saved. Select a receipt printer in Terminal setup to enable automatic printing.');return;}
 receiptPrintBusy=true;
 const paper=document.createElement('section');paper.id='automaticReceiptPaper';paper.dataset.sale=String(sale.id);paper.innerHTML=checkoutPaper(sale,true);document.body.append(paper);document.body.classList.add('receiptDirectPrint');
 try{
  if(automatic)localStorage.setItem(key,'requested');
  if(native?.receipt_print&&printer){const result=await native.receipt_print(printer,String(sale.id),automatic);if(result.error)throw Error(result.error);if(automatic)localStorage.setItem(key,'printed');}
  else window.print();
 }catch(e){posMessage(e.message);const message=document.createElement('p');message.setAttribute('role','alert');message.textContent=e.message+' Use Print receipts to try again.';$('posReceipt').append(message);}
 finally{document.body.classList.remove('receiptDirectPrint');paper.remove();receiptPrintBusy=false;}
}
if(!officeMode){
 $('deskTerminalSettings').onclick=()=>{$('deskSettings').open=false;terminalDeviceOptions();};
 customerPairButton.onclick=async()=>{await loadTerminalDevices();if(!customerPairToken){if(can('manage_pos'))return terminalDeviceOptions();return posMessage('Ask a manager to assign this register’s customer display in Terminal setup.');}const url=new URL(receiptTerminalOptions.display_path,location.origin).href;flowModal('Customer display · '+receiptTerminalOptions.terminal.name,`<p>This link stays assigned to this register and uses ${esc(receiptTerminalOptions.terminal.store_name)} branding. Open it on the customer monitor in a browser profile without a staff login.</p><label>Assigned link<input readonly value="${esc(url)}"></label><a href="${esc(url)}" target="_blank" rel="noopener">Open customer display</a>`);await customerDisplaySync();};
 customerDisplaySync=async function(){if(!customerPairToken||customerDisplayBusy||!user)return;customerDisplayBusy=true;try{await api('pos/display-state',{device:await retailDevice(),token:customerPairToken,roundup:checkoutRoundupDisplay(),cart:$('posReceipt').hidden?posCurrent?.id||null:null,sale:!$('posReceipt').hidden?posLastReceipt?.id||null:null});}catch(e){if(e.status===404)customerPairToken=null;}finally{customerDisplayBusy=false;}};
 const load=posLoad;posLoad=async function(...args){await load(...args);await loadTerminalDevices();};
 const receipt=posReceipt;posReceipt=function(sale,automatic=false){receipt(sale);if(automatic)deskPrintReceipt(sale,true);};
 $('posPrintLast').onclick=()=>deskPrintReceipt(posLastReceipt);$('posPrint').onclick=()=>deskPrintReceipt(posLastReceipt);
}
async function customerCreateTouch(){
 const d=thriftModal('Add customer',`<div class="customerColumns"><form id="customerTouchCreate"><label>Full name<input name="name" required maxlength="120" autocomplete="name"></label><label>Phone with area code<input name="phone" type="tel" autocomplete="tel" placeholder="(555) 123-4567"></label><label>Email<input name="email" type="email" maxlength="160" autocomplete="email"></label><label><input name="marketing" type="checkbox"> Customer agrees to marketing messages</label><p>Marketing consent is optional.</p><button class="primary">Save customer</button></form><aside><button id="customerSendForm" type="button">Let customer complete on their touchscreen</button><p id="customerEntryState" role="status"></p></aside></div>`);
 let request=null,timer=null,closing=false;
 const form=d.querySelector('form');
 d.querySelector('#customerSendForm').onclick=async()=>{try{request=await retailSave('customer-entry-start',{});d.querySelector('#customerEntryState').textContent='The form is ready on this register’s customer display. Waiting for the customer…';d.querySelector('#customerSendForm').disabled=true;
 timer=setInterval(async()=>{if(!request||closing)return;try{const result=await api('pos/customer-entry?'+new URLSearchParams({id:request.id,device:await retailDevice()}));if(result.status==='submitted'){clearInterval(timer);for(const [k,v] of Object.entries(result.details)){if(!form.elements[k])continue;if(k==='marketing')form.elements[k].checked=v;else form.elements[k].value=v;}changedForms.set(form,snapshot(form));d.querySelector('#customerEntryState').textContent='Customer finished. Review their details and select Save customer.';}}catch(e){clearInterval(timer);d.querySelector('#customerEntryState').textContent=e.message;}},2000);
 }catch(e){thriftError(d,e);}};
 form.onsubmit=async e=>{e.preventDefault();try{const f=form.elements;let digits=f.phone.value.replace(/\D/g,'');if(digits.length===11&&digits[0]==='1')digits=digits.slice(1);if(digits&&digits.length!==10)throw Error('Enter a phone number including the area code.');const phone=digits?'('+digits.slice(0,3)+') '+digits.slice(3,6)+'-'+digits.slice(6):'',contact=[phone,f.email.value.trim()].filter(Boolean).join(' · ');const r=await retailSave('thrift-customer-save',{name:f.name.value,contact,marketing:f.marketing.checked});changedForms.delete(form);if(posCurrent)await posDo('thrift-customer',{cart:posCurrent.id,revision:posCurrent.revision,customer:r.customer.id});thriftClose(d);posMessage('Customer saved'+(deskTraining.enabled?' in training mode.':'.'));}catch(error){thriftError(d,error);}};
 d.addEventListener('close',()=>{closing=true;clearInterval(timer);if(request)retailSave('customer-entry-close',{id:request.id}).catch(()=>{});},{once:true});
}
