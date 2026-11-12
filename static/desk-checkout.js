// Touchscreen checkout. All financial saves retain server idempotency and revision checks.
const checkoutStore=()=>decodeURIComponent(stores_id_js());
async function checkoutQuery(path){return api('pos/'+path+'?store_id='+encodeURIComponent(checkoutStore())+'&device='+encodeURIComponent(await retailDevice()));}
function checkoutClose(d){for(const f of d.querySelectorAll('form'))changedForms.delete(f);d.close();d.remove();}
function checkoutError(d,e){d.querySelector('.flowError').textContent=e.message||String(e);}
function checkoutCashDue(amount,settings=posCurrent?.settings){return settings?.cash_rounding==='nearest5'&&settings?.cash_rounding_basis==='total'?Math.round(amount/5)*5:amount;}
function checkoutPaper(s,paid=false){
 const design=s.receipt_design||{};
 return `${receiptDesignMarkup(design)}<h2>${esc(s.settings.store)}</h2><h3>${paid?'Receipt #'+s.id:'Current sale'}</h3>${paid?`<p>${esc(new Date(s.at).toLocaleString())}<br>Cashier: ${esc(s.cashier)}</p>`:''}<table><thead><tr><th>Item</th><th>Qty</th><th>Amount</th></tr></thead><tbody>${s.lines.map(l=>`<tr><td>${esc(l.name)}<small>${esc(flowLineDetails(l))}</small></td><td>${l.quantity}</td><td>${posMoney(l.subtotal)}</td></tr>`).join('')}</tbody></table><dl><dt>Subtotal</dt><dd>${posMoney(s.subtotal)}</dd><dt>Tax</dt><dd>${posMoney(s.tax)}</dd><dt>Total</dt><dd>${posMoney(s.total)}</dd>${paid&&s.method!=='store_credit'?`<dt>Cash rounding</dt><dd>${signedMoney(s.cash_rounding||0)}</dd><dt>Total paid</dt><dd>${posMoney(s.total+(s.cash_rounding||0))}</dd>`:''}${paid&&s.store_credit?`<dt>Store credit</dt><dd>${posMoney(s.store_credit)}</dd>`:''}${paid&&s.method!=='store_credit'?`<dt>Cash tendered</dt><dd>${posMoney(s.tender)}</dd><dt>Change</dt><dd>${posMoney(s.change)}</dd>`:''}</dl>${s.adjustment?`<p>${esc(s.adjustment.mode)}: ${posMoney(s.adjustment.amount)} · ${esc(s.adjustment.reason)}</p>`:''}<p>${esc(design.policy||'')}</p><p>${esc(design.footer||'')}</p>`;
}
function checkoutModal(title,body){const d=flowModal(title,body);d.classList.add('checkoutDialog');return d;}
let checkoutOpening=false;
async function checkoutPayment(){
 if(checkoutOpening||document.querySelector('#checkoutPaymentForm'))return;checkoutOpening=true;
 try{for(let i=0;i<400&&(posBusy||writeCount||flowProductStarting);i++)await new Promise(resolve=>setTimeout(resolve,50));}finally{checkoutOpening=false;}
 if(!navigationAllowed())return;
 if(!posCurrent?.lines.length||posCurrent.held){posMessage('Select a product or find a saved sale first.');return;}
 if(unfinished()){posMessage('Finish or clear the current entry before taking payment.');return;}
 const cart=structuredClone(posCurrent);let method='cash',accounts=[],busy=false,completed=false;
 const d=checkoutModal('Apply payment to transaction',`<div class="checkoutSplit"><section class="checkoutPaper">${checkoutPaper(cart)}</section><section class="checkoutControls"><form id="checkoutPaymentForm"><div class="checkoutAmounts"><label>Amount due<output id="checkoutDue"></output></label><label>Amount tendered<input id="checkoutTender" name="tender" type="text" inputmode="numeric" autocomplete="off" aria-label="Amount tendered"></label><label>Change<output id="checkoutChange"></output></label></div><p id="checkoutRounding"></p><div class="checkoutMethods"><button type="button" data-method="cash" aria-pressed="true">Cash</button><button type="button" data-method="card" disabled title="Credit cards will be added in future updates.">Credit Card<small>Coming in a future update</small></button><button type="button" data-method="credit" ${can('use_store_credit')?'':'disabled'} aria-pressed="false">Store credit</button></div><div id="checkoutCredit" hidden><label>Store-credit account<select id="checkoutAccount" name="account"><option value="">Choose an account</option></select></label><label>Store credit to use ($)<input id="checkoutCreditAmount" name="credit" type="number" step="0.01" min="0.01"></label><p id="checkoutCreditBalance"></p></div><div class="checkoutKeys"><div class="checkoutQuick"><strong>Quick tender</strong><button type="button" data-tender="exact">Exact amount</button>${[500,1000,2000,5000,10000].map(n=>`<button type="button" data-tender="${n}">${posMoney(n)}</button>`).join('')}</div><div class="checkoutNumberPad">${['1','2','3','4','5','6','7','8','9','clear','0','back'].map(k=>`<button type="button" data-money-key="${k}">${k==='clear'?'Clear':k==='back'?'⌫':k}</button>`).join('')}</div></div><p>Enter digits as cents: 1000 = $10.00.</p><div class="checkoutFooter"><button class="primary" id="checkoutComplete" type="submit">Okay · Complete payment</button><button type="button" id="checkoutCancel">Cancel</button></div></form></section></div>`);
 const form=d.querySelector('form'),tender=d.querySelector('#checkoutTender'),credit=d.querySelector('#checkoutCreditAmount'),account=d.querySelector('#checkoutAccount');
 let tenderDigits='';
 const creditCents=()=>method==='credit'&&credit.value?posCents(credit.value):0;
 const due=()=>checkoutCashDue(Math.max(0,cart.total-creditCents()),cart.settings);
 const touch=()=>changedForms.set(form,snapshot(form));
 function render(){
  let amount=0;try{amount=creditCents();}catch{}
  const remaining=Math.max(0,cart.total-amount),cashDue=checkoutCashDue(remaining,cart.settings),received=Number(tenderDigits||0);
  tender.value=(received/100).toFixed(2);d.querySelector('#checkoutDue').textContent=posMoney(cashDue);
  d.querySelector('#checkoutChange').textContent=posMoney(Math.max(0,received-cashDue));
  d.querySelector('#checkoutRounding').textContent=`Calculated total ${posMoney(cart.total)}${amount?' · Store credit '+posMoney(amount):''} · Cash rounding ${signedMoney(cashDue-remaining)}`;
  d.querySelector('#checkoutCredit').hidden=method!=='credit';
  d.querySelectorAll('[data-method]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.method===method));
  const a=accounts.find(x=>String(x.id)===account.value);d.querySelector('#checkoutCreditBalance').textContent=a?'Available: '+posMoney(a.balance):'';
  d.querySelector('#checkoutComplete').textContent=busy?'Recording payment…':'Okay · Complete payment';
  d.querySelector('#checkoutComplete').disabled=busy;
 }
 const editDigit=k=>{if(busy)return;if(k==='clear')tenderDigits='';else if(k==='back')tenderDigits=tenderDigits.slice(0,-1);else if(tenderDigits.length<9)tenderDigits=(tenderDigits+k).replace(/^0+(?=\d)/,'');touch();render();};
 tender.onkeydown=e=>{if(e.ctrlKey||e.metaKey||e.key==='Tab'||e.key==='Enter')return;if(/^\d$/.test(e.key)||['Backspace','Delete','.'].includes(e.key)){e.preventDefault();if(tender.selectionStart===0&&tender.selectionEnd===tender.value.length)tenderDigits='';if(e.key!=='.')editDigit(e.key==='Backspace'?'back':e.key==='Delete'?'clear':e.key);}};
 tender.oninput=()=>{tenderDigits=tender.value.replace(/\D/g,'').slice(0,9);touch();render();};
 tender.onpaste=e=>{e.preventDefault();const v=e.clipboardData.getData('text').trim();if(/^\$?\d+(\.\d{1,2})?$/.test(v)){tenderDigits=String(v.includes('.')?Math.round(Number(v.replace('$',''))*100):Number(v.replace('$','')));touch();render();}};
 d.querySelectorAll('[data-money-key]').forEach(b=>b.onclick=()=>editDigit(b.dataset.moneyKey));
 d.querySelectorAll('[data-tender]').forEach(b=>b.onclick=()=>{tenderDigits=String(b.dataset.tender==='exact'?due():Number(b.dataset.tender));touch();render();});
 account.onchange=()=>{const a=accounts.find(x=>String(x.id)===account.value);credit.value=a?(Math.min(a.balance,cart.total)/100).toFixed(2):'';tenderDigits='';touch();render();};credit.oninput=()=>{touch();render();};
 d.querySelectorAll('[data-method]').forEach(b=>b.onclick=async()=>{if(b.dataset.method==='card'||busy)return;try{if(b.dataset.method==='credit'&&!accounts.length){accounts=(await api('pos/accounts')).accounts.filter(a=>a.active&&a.balance>0);account.innerHTML='<option value="">Choose an account</option>'+accounts.map(a=>`<option value="${a.id}">${esc(a.name)} · ${esc(a.code)} · ${posMoney(a.balance)}</option>`).join('');}method=b.dataset.method;touch();render();if(method==='cash')tender.focus();else account.focus();}catch(e){checkoutError(d,e);}});
 const pending=()=>sessionStorage.getItem('retail-save:'+user.name+':'+(method==='credit'?'credit':'cash'));
 d.beforeDismiss=()=>{if(busy||pending()){checkoutError(d,Error('Payment status is unconfirmed. Retry this same payment to check it before closing.'));return false;}return true;};
 d.querySelector('#checkoutCancel').onclick=()=>d.querySelector('.flowClose').click();
 form.onsubmit=async e=>{e.preventDefault();if(busy||completed)return;try{
  const amount=creditCents(),a=accounts.find(x=>String(x.id)===account.value),received=Number(tenderDigits||0);
  if(method==='credit'&&(!a||amount<=0||amount>Math.min(a.balance,cart.total)))throw Error('Select an account and an amount within its available balance and this sale total.');
  if(received<due())throw Error('Amount tendered is less than the amount due.');
  if(method==='credit'&&amount===cart.total&&received)throw Error('This account covers the full sale. Clear the cash amount.');
  busy=true;render();d.querySelector('.flowError').textContent='';
  const payload={cart:cart.id,revision:cart.revision,tender:received,...(method==='credit'?{account:a.id,account_revision:a.revision,amount}: {})};
  const result=await retailSave(method==='credit'?'credit':'cash',payload);
  completed=true;changedForms.delete(form);checkoutClose(d);posCurrent=null;sessionStorage.removeItem('yfc-pos-selected:'+user.name);$('posCash').reset();changedForms.delete($('posCash'));
  await posLoad();posReceipt(result.sale);posMessage('Payment recorded. Receipt #'+result.sale.id);await pickupAfterPayment(result.sale);
 }catch(error){checkoutError(d,error);}finally{busy=false;if(d.isConnected){render();const locked=!!pending();for(const el of form.querySelectorAll('input,select,button:not(#checkoutComplete)'))el.disabled=locked||el.dataset.method==='card'||(el.dataset.method==='credit'&&!can('use_store_credit'));if(locked)d.querySelector('#checkoutComplete').textContent='Retry / check this payment';}}};
 render();tender.focus();tender.select();
}

async function checkoutFind(){
 if(unfinished()){posMessage('Finish or clear the current entry before finding a sale.');return;}
 const d=checkoutModal('Find a saved transaction','<label>Search saved sales<input id="checkoutFindSearch" placeholder="Item, cashier or sale number"></label><div id="checkoutSaved" class="checkoutList"></div><div class="checkoutFooter"><button type="button" class="primary" id="checkoutResume" disabled>Okay · Open transaction</button><button type="button" id="checkoutFindClose">Close</button></div>');
 let chosen=null,busy=false;
 d.querySelector('#checkoutFindClose').onclick=()=>d.querySelector('.flowClose').click();
 try{const data=await checkoutQuery('held-sales');const render=()=>{const q=d.querySelector('input').value.toLowerCase();d.querySelector('#checkoutSaved').innerHTML=data.carts.filter(c=>(c.id+' '+c.employee+' '+c.lines.map(l=>l.name).join(' ')).toLowerCase().includes(q)).map(c=>`<button type="button" data-saved-sale="${c.id}" aria-pressed="${c.id===chosen?.id}" ${c.employee!==user.name?'disabled':''}><strong>${esc(c.lines[0]?.name||'Empty transaction')} · ${posMoney(c.total)}</strong><small>#${esc(c.id.slice(0,6))} · ${esc(c.employee)} · ${esc(c.terminal||'')} · ${c.held?'Pay later':'Saved'}${c.employee!==user.name?' · Transfer in OFFICE required':''}</small></button>`).join('')||'<p>No matching saved transactions.</p>';};
 d.querySelector('#checkoutFindSearch').oninput=render;d.querySelector('#checkoutSaved').onclick=e=>{const b=e.target.closest('[data-saved-sale]');if(!b||busy)return;chosen=data.carts.find(c=>c.id===b.dataset.savedSale);d.querySelector('#checkoutResume').disabled=false;render();};render();
 d.beforeDismiss=()=>!busy;
 d.querySelector('#checkoutResume').onclick=async()=>{if(!chosen||busy)return;try{busy=true;const result=await retailSave('resume',{cart:chosen.id,revision:chosen.revision});posCurrent=result.cart;checkoutClose(d);$('posReceipt').hidden=true;$('posPrint').hidden=true;await posLoad();posMessage('Saved transaction reopened.');}catch(e){checkoutError(d,e);}finally{busy=false;}};
 }catch(e){checkoutError(d,e);}
}
async function checkoutAdjustments(){
 if(!posCurrent?.lines.length){posMessage('Add items before applying a discount or surcharge.');return;}
 if(unfinished()){posMessage('Finish or clear the current entry first.');return;}
 const cart=structuredClone(posCurrent),d=checkoutModal('Discounts/ Surcharges','<div id="checkoutAdjustments"></div>');
 try{const {settings}=await checkoutQuery('checkout-settings');d.querySelector('#checkoutAdjustments').innerHTML=`<label>Item to adjust<select id="checkoutAdjustItem">${cart.lines.map((l,i)=>`<option value="${i}">${esc(l.name)} · ${posMoney(l.subtotal)}</option>`).join('')}</select></label>${['discount','surcharge'].map(mode=>`<section class="checkoutAdjustmentSection ${mode}"><h3>${mode==='discount'?'Discounts':'Surcharges'}</h3><div class="checkoutAdjustmentColumns">${['item','transaction'].map(scope=>`<div><h4>${scope==='item'?'Individual item':'Whole transaction'}</h4><div class="checkoutPresetTiles">${settings.presets.filter(p=>p.mode===mode&&p.scope===scope).map(p=>`<button type="button" data-checkout-preset="${esc(p.id)}">${esc(p.name)}<small>${p.kind==='percent'?(p.value/100)+'%':posMoney(p.value)}</small></button>`).join('')||'<p>No buttons configured in OFFICE.</p>'}</div></div>`).join('')}</div></section>`).join('')}<p>Applying a choice replaces the previous manual adjustment. Existing approval and discount limits still apply.</p>${cart.adjustment&&can('approve_pos_adjustments')?'<button type="button" id="checkoutRestore">Restore original prices</button>':''}`;
 let busy=false;d.beforeDismiss=()=>!busy;
 const apply=async(preset)=>{if(busy)return;try{busy=true;const data=preset?{preset:preset.id,settings_revision:settings.revision,index:preset.scope==='item'?Number(d.querySelector('select').value):null}:{mode:'discount',amount:0,index:null,reason:'Restore original prices'};const result=await retailSave('adjustment-request',{cart:cart.id,revision:cart.revision,...data});if(result.cart)posCurrent=result.cart;checkoutClose(d);await posLoad();posMessage(result.approval?'Adjustment sent to a manager for approval.':'Adjustment applied.');}catch(e){checkoutError(d,e);}finally{busy=false;}};
 d.querySelectorAll('[data-checkout-preset]').forEach(b=>b.onclick=()=>apply(settings.presets.find(p=>p.id===b.dataset.checkoutPreset)));d.querySelector('#checkoutRestore')?.addEventListener('click',()=>apply(null));
 }catch(e){checkoutError(d,e);}
}
async function checkoutCancelSale(){
 if(!posCurrent||unfinished()){posMessage('Finish or clear the current entry before canceling the sale.');return;}
 const cart=structuredClone(posCurrent),d=checkoutModal('Cancel sale','<div id="checkoutCancelChoices"></div>');
 try{const {settings}=await checkoutQuery('checkout-settings');d.querySelector('#checkoutCancelChoices').innerHTML=`<form id="checkoutCancelForm"><label>Choose a reason<select name="reason" required><option value="">Select a cancellation reason</option>${settings.reasons.map(r=>`<option value="${esc(r.id)}">${esc(r.name)}</option>`).join('')}</select></label><p>The transaction and cancellation history remain on the server.</p><button class="primary" ${settings.reasons.length?'':'disabled'}>Confirm cancellation</button></form>`;let busy=false;d.beforeDismiss=()=>!busy;d.querySelector('form').onsubmit=async e=>{e.preventDefault();if(busy)return;try{busy=true;await retailSave('discard',{cart:cart.id,revision:cart.revision,reason_id:e.target.elements.reason.value,settings_revision:settings.revision});changedForms.delete(e.target);posCurrent=null;sessionStorage.removeItem('yfc-pos-selected:'+user.name);checkoutClose(d);await posLoad();posMessage('Sale canceled.');}catch(error){checkoutError(d,error);}finally{busy=false;}};}catch(e){checkoutError(d,e);}
}
async function checkoutReceipts(){
 if(unfinished()){posMessage('Finish or clear the current entry before opening receipts.');return;}
 const d=checkoutModal('Print receipts · Today','<div class="checkoutSplit"><section id="checkoutReceiptPreview" class="checkoutPaper"><p>Select a completed transaction.</p></section><section class="checkoutControls"><label>Search today’s receipts<input id="checkoutReceiptSearch" placeholder="Receipt number, item or cashier"></label><div id="checkoutReceiptList" class="checkoutList"></div><div class="checkoutFooter"><button type="button" id="checkoutReceiptPrint" disabled>Print receipt</button><button type="button" id="checkoutReceiptEmail" disabled>Email receipt</button><button type="button" id="checkoutReceiptClose">Close</button></div></section></div>');
 let selected=null;d.querySelector('#checkoutReceiptClose').onclick=()=>d.querySelector('.flowClose').click();
 try{const data=await checkoutQuery('today-receipts');const render=()=>{const q=d.querySelector('input').value.toLowerCase();d.querySelector('#checkoutReceiptList').innerHTML=data.sales.filter(s=>(s.id+' '+s.cashier+' '+s.lines.map(l=>l.name).join(' ')).toLowerCase().includes(q)).map(s=>`<button type="button" data-checkout-receipt="${s.id}" aria-pressed="${s.id===selected?.id}"><strong>#${s.id} · ${posMoney(s.total+(s.cash_rounding||0))}</strong><small>${esc(new Date(s.at).toLocaleTimeString())} · ${esc(s.cashier)} · ${esc(s.method.replaceAll('_',' '))}</small></button>`).join('')||'<p>No completed transactions for this store today.</p>';};d.querySelector('input').oninput=render;render();
 d.querySelector('#checkoutReceiptList').onclick=e=>{const b=e.target.closest('[data-checkout-receipt]');if(!b)return;selected=data.sales.find(s=>String(s.id)===b.dataset.checkoutReceipt);d.querySelector('#checkoutReceiptPreview').innerHTML=checkoutPaper(selected,true);d.querySelector('#checkoutReceiptPrint').disabled=false;d.querySelector('#checkoutReceiptEmail').disabled=false;render();};
 d.querySelector('#checkoutReceiptPrint').onclick=()=>{if(!selected)return;document.body.classList.add('checkoutPrinting');window.print();document.body.classList.remove('checkoutPrinting');};
 d.querySelector('#checkoutReceiptEmail').onclick=()=>{if(!selected)return;const mail=checkoutModal('Email receipt #'+selected.id,'<form id="checkoutEmailForm"><label>Customer email<input type="email" name="email" required autocomplete="off"></label><p>A receipt will be sent using the Gmail account configured in OFFICE.</p><button class="primary">Send receipt</button></form>');let busy=false;mail.beforeDismiss=()=>!busy;mail.querySelector('form').onsubmit=async e=>{e.preventDefault();if(busy)return;try{busy=true;await retailSave('email-receipt',{sale:selected.id,email:e.target.elements.email.value,store_id:checkoutStore()});changedForms.delete(e.target);checkoutClose(mail);d.querySelector('.flowError').textContent='Receipt email queued for delivery.';}catch(error){checkoutError(mail,error);}finally{busy=false;}};};
 }catch(e){checkoutError(d,e);}
}

async function checkoutOffice(){
 if(!navigationAllowed()||unfinished()){posMessage('Save or discard the current form first.');return;}
 const {settings}=await checkoutQuery('checkout-settings');
 const d=checkoutModal('Checkout buttons & cancellation reasons',`<p>${esc(posOverview?.settings.store||'Selected store')} · Changes apply to this store’s registers.</p><nav class="checkoutEditorTabs"><button type="button" data-checkout-edit="presets">Discounts/ Surcharges</button><button type="button" data-checkout-edit="reasons">Cancellation reasons</button></nav><div id="checkoutEditor"></div><div class="checkoutFooter"><button type="button" class="primary" id="checkoutSettingsSave">Save checkout settings</button><button type="button" id="checkoutSettingsCancel">Discard & close</button></div>`);
 let section='presets',selected=null,dirty=false,busy=false;const draft=structuredClone(settings);const draftGuard=document.createElement('form');draftGuard.hidden=true;d.append(draftGuard);const markDirty=()=>{dirty=true;changedForms.set(draftGuard,'checkout choices');};
 function render(){const presets=section==='presets';d.querySelector('#checkoutEditor').innerHTML=`<form id="checkoutChoiceForm"><label>Name<input name="name" maxlength="100" required></label>${presets?'<div class="checkoutEditorFields"><label>Type<select name="mode"><option value="discount">Discount</option><option value="surcharge">Surcharge</option></select></label><label>Applies to<select name="scope"><option value="item">Individual item</option><option value="transaction">Whole transaction</option></select></label><label>Value type<select name="kind"><option value="percent">Percent</option><option value="fixed">Fixed amount ($)</option></select></label><label>Value<input name="value" type="number" min="0.01" max="100000" step="0.01" required></label></div>':''}<button class="primary">${selected?'Update choice':'Add'}</button><button type="button" id="checkoutChoiceNew">Clear / new</button></form><div class="checkoutList">${draft[section].map(x=>`<button type="button" data-choice="${esc(x.id)}" aria-pressed="${x.id===selected}"><strong>${esc(x.name)}</strong>${presets?`<small>${esc(x.mode)} · ${esc(x.scope)} · ${x.kind==='percent'?(x.value/100)+'%':posMoney(x.value)}</small>`:''}</button>`).join('')}</div><div class="checkoutFooter"><button type="button" id="checkoutChoiceEdit" ${selected?'':'disabled'}>✎ Edit</button><button type="button" id="checkoutChoiceCopy" ${selected?'':'disabled'}>×2 Copy</button><button type="button" id="checkoutChoiceDelete" ${selected?'':'disabled'}>🗑 Delete</button></div>`;
 const f=d.querySelector('form');const fill=()=>{const x=draft[section].find(x=>x.id===selected);if(!x)return;f.elements.name.value=x.name;if(presets){for(const key of ['mode','scope','kind'])f.elements[key].value=x[key];f.elements.value.value=(x.value/100).toFixed(2);}f.querySelector('button').textContent='Update choice';};
 f.onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(f));const x={id:selected||crypto.randomUUID().replaceAll('-',''),name:data.name.trim(),...(presets?{mode:data.mode,scope:data.scope,kind:data.kind,value:Math.round(Number(data.value)*100)}:{})};if(presets&&data.kind==='percent'&&x.value>10000){checkoutError(d,Error('Percent must be at most 100.'));return;}const i=draft[section].findIndex(x=>x.id===selected);if(i>=0)draft[section][i]=x;else draft[section].push(x);changedForms.delete(f);markDirty();selected=null;render();};
 const discardEntry=()=>!changedForms.has(f)||confirm('Discard the unfinished choice?');
 d.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{if(!discardEntry())return;changedForms.delete(f);selected=b.dataset.choice;render();});
 d.querySelector('#checkoutChoiceEdit').onclick=fill;
 d.querySelector('#checkoutChoiceNew').onclick=()=>{if(!discardEntry())return;changedForms.delete(f);selected=null;render();};
 d.querySelector('#checkoutChoiceCopy').onclick=()=>{if(!discardEntry())return;const x=draft[section].find(x=>x.id===selected);draft[section].push({...x,id:crypto.randomUUID().replaceAll('-',''),name:x.name+' copy'});markDirty();changedForms.delete(f);selected=null;render();};
 d.querySelector('#checkoutChoiceDelete').onclick=()=>{if(!discardEntry()||!confirm('Remove this checkout choice? Past transactions remain unchanged.'))return;draft[section]=draft[section].filter(x=>x.id!==selected);markDirty();changedForms.delete(f);selected=null;render();};
 }
 d.beforeDismiss=()=>!busy&&(!(dirty||changedForms.has(d.querySelector('form')))||confirm('Discard these unsaved checkout settings?'));
 d.querySelectorAll('[data-checkout-edit]').forEach(b=>b.onclick=()=>{const f=d.querySelector('form');if(changedForms.has(f)&&!confirm('Discard the unfinished choice?'))return;changedForms.delete(f);section=b.dataset.checkoutEdit;selected=null;render();});
 d.querySelector('#checkoutSettingsCancel').onclick=()=>d.querySelector('.flowClose').click();
 d.querySelector('#checkoutSettingsSave').onclick=async()=>{if(busy)return;if(changedForms.has(d.querySelector('form'))){checkoutError(d,Error('Add or update the choice before saving settings.'));return;}try{busy=true;const result=await retailSave('checkout-settings-save',draft);Object.assign(draft,result.settings);dirty=false;checkoutClose(d);posMessage('Checkout choices saved for this store.');}catch(e){checkoutError(d,e);}finally{busy=false;}};render();
}
officeCards.push({section:'sales',action:'checkout-buttons',title:'Checkout buttons & cancellation reasons',description:'Configure item and transaction discounts, surcharges and reasons for canceling sales.',icon:'▦',permission:'manage_pos'});
officeNavigationGroups.splice(officeNavigationGroups.findIndex(g=>g.id==='policies')+1,0,{section:'sales',id:'checkout-choices',title:'Checkout buttons',description:'Set item and transaction choices and cancellation reasons for DESK.',actions:['checkout-buttons']});
const checkoutOriginalOfficeAction=officeAction;officeAction=async function(action){if(action==='checkout-buttons'){try{await checkoutOffice();}catch(e){posMessage(e.message);}return;}return checkoutOriginalOfficeAction(action);};

if(!officeMode){
 // Detached, dismissed forms cannot contain an entry the cashier can still finish.
 // Unconfirmed saves are retained separately and must never be cleared here.
 const originalUnfinished=unfinished;
 const checkoutPendingPayment=()=>user&&['cash','credit'].map(action=>({action,key:'retail-save:'+user.name+':'+action})).find(x=>sessionStorage.getItem(x.key));
 unfinished=function(){for(const f of changedForms.keys())if(!f.isConnected||f.closest('dialog:not([open])'))changedForms.delete(f);return originalUnfinished()||!!checkoutPendingPayment();};
 let recovering=false;
 async function recoverCheckoutPayment(){
  const pending=checkoutPendingPayment();if(!pending||recovering||document.querySelector('#checkoutPaymentForm,#checkoutRecovery')||!kioskInfo&&kioskRequested)return;
  recovering=true;const saved=JSON.parse(sessionStorage.getItem(pending.key));
  const d=checkoutModal('Check the last payment','<div id="checkoutRecovery"><p>The last payment response was interrupted. Check its status before starting another payment.</p><button type="button" class="primary" id="checkoutRecover">Retry / check this payment</button></div>');d.beforeDismiss=()=>false;
  let busy=false;
  const complete=async result=>{sessionStorage.removeItem(pending.key);posCurrent=null;sessionStorage.removeItem('yfc-pos-selected:'+user.name);checkoutClose(d);await posLoad();posReceipt(result.sale);posMessage('Payment confirmed. Receipt #'+result.sale.id);};
  d.querySelector('#checkoutRecover').onclick=async()=>{if(busy)return;busy=true;try{const result=await api('pos/'+pending.action,{...JSON.parse(saved.payload),request:saved.request});await complete(result);}catch(e){checkoutError(d,e);if(e.status){sessionStorage.removeItem(pending.key);d.beforeDismiss=()=>true;const close=d.querySelector('#checkoutRecover');close.textContent='Close · Return to sale';close.onclick=async()=>{checkoutClose(d);await posLoad();};}}finally{busy=false;recovering=false;}};
  try{const status=await api('pos/checkout-payment-status?request='+encodeURIComponent(saved.request));if(status.confirmed)await complete(status.result);}catch(e){checkoutError(d,e);}finally{recovering=false;}
 }
 const checkoutLoad=posLoad;posLoad=async function(...args){const result=await checkoutLoad(...args);setTimeout(()=>recoverCheckoutPayment().catch(e=>posMessage(e.message)),0);return result;};
 const oldExit=window.showPosKioskExit;
 function exitReason(){
  unfinished();
  if(writeCount||posBusy||kioskBusy)return 'A save is still running. Wait for it to finish, then select Exit POS again.';
  if(posPending)return 'A transaction has an unconfirmed save. Keep working, then select Retry / check status before exiting.';
  const pending=checkoutPendingPayment()?.key;
  if(pending)return 'The last '+pending.split(':').pop().replaceAll('-',' ')+' is unconfirmed. Reopen that action and retry the unchanged entry before exiting.';
  const f=[...changedForms.keys()][0];if(f)return 'There is an unfinished '+(f.closest('dialog')?.querySelector('h2')?.textContent||f.querySelector('h2,h3')?.textContent||'entry')+'. Keep working to save or cancel it.';
  return 'Finish or cancel the open task before exiting.';
 }
 window.showPosKioskExit=()=>{oldExit();if(unfinished())$('posExitError').textContent=exitReason();};kioskExitButton.onclick=window.showPosKioskExit;
 const originalExitSubmit=$('posExitForm').onsubmit;$('posExitForm').onsubmit=async e=>{if(!window.posKioskCanLeave()){e.preventDefault();$('posExitError').textContent=exitReason();return;}return originalExitSubmit(e);};
 document.body.classList.add('checkoutRedesign');
 const payLater=document.createElement('button');payLater.id='checkoutPayLater';payLater.textContent='Pay later';payLater.onclick=flowHoldCurrent;$('posPayNow').after(payLater);
 $('posPayNow').onclick=checkoutPayment;$('posFindCart').textContent='Find';$('posFindCart').onclick=checkoutFind;
 $('flowAdjust').textContent='Discounts/ Surcharges';$('flowAdjust').onclick=checkoutAdjustments;$('posDiscard').onclick=checkoutCancelSale;
 for(const id of ['posSalesShortcut','navSales']){const b=$(id);if(b){b.textContent='Print receipts';b.onclick=checkoutReceipts;}}
 const thrift=$('thriftTools');if(thrift)thrift.onclick=async()=>{try{await thriftDesk();}catch(e){posMessage('Thrift store tools could not open: '+e.message);}};
 const renderBeforeCheckout=posRender;posRender=function(){renderBeforeCheckout();if(posCurrent?.lines.length){const totals=$('posCart').querySelector(':scope>p:last-child');if(totals&&posCurrent.settings.cash_rounding==='nearest5'){const rounding=checkoutCashDue(posCurrent.total)-posCurrent.total;totals.insertAdjacentHTML('beforeend',`<br><span>Cash rounding: ${signedMoney(rounding)}</span><br><strong>Cash due: ${posMoney(checkoutCashDue(posCurrent.total))}</strong>`);}}payLater.disabled=!posCurrent?.lines.length||!!posPending||posBusy||posCurrent.held;$('posFindCart').disabled=!!posPending||posBusy;};
 const receiptBeforeCheckout=posReceipt;posReceipt=function(sale){receiptBeforeCheckout(sale);$('posPrintLast').disabled=false;if(sale.method!=='store_credit'&&!sale.cash_rounding){const note=document.createElement('p');note.textContent='Cash rounding: '+posMoney(0)+' · Cash collected: '+posMoney(sale.cash_paid??sale.tender-sale.change);$('posReceipt').append(note);}};
}
