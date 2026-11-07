'use strict';
const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let user=null,submittedForm=null,writeCount=0,flow=null,flowMandatory=false,flowSeen=null;
const connectionId=Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('');
const changedForms=new Map();
const can=k=>!!(user&&(user.admin||user.grants?.[k]));
const toast=text=>$('posStatus').textContent=text;
function snapshot(f){return JSON.stringify([...new FormData(f)]);}
document.addEventListener('input',e=>{if(e.target.form&&!['login','posExitForm','kioskPasscodeForm'].includes(e.target.form.id))changedForms.set(e.target.form,snapshot(e.target.form));},true);
document.addEventListener('change',e=>{if(e.target.form&&!['login','posExitForm','kioskPasscodeForm'].includes(e.target.form.id))changedForms.set(e.target.form,snapshot(e.target.form));},true);
document.addEventListener('reset',e=>changedForms.delete(e.target),true);
document.addEventListener('submit',e=>{submittedForm=e.target;setTimeout(()=>submittedForm=null,0);},true);
function unfinished(){return writeCount>0||posBusy||!!posPending||changedForms.size>0;}
async function api(path,data){
 const form=submittedForm,stamp=form?snapshot(form):null,mutation=!!data&&!['account/activity','account/connection','pos-update/heartbeat'].includes(path)&&!path.startsWith('update-flow');
 if(mutation)writeCount++;
 try{
  const r=await fetch('/api/'+path,{method:data?'POST':'GET',headers:{'X-Dispatch-Connection':connectionId,...(data?{'Content-Type':'application/json','X-Dispatch':'1'}:{})},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(20000)});
  const value=await r.json();$('connection').textContent='Connected to Operations';
  if(!r.ok){if(r.status===401){user=null;$('posRoot').hidden=true;$('auth').hidden=false;$('cashier').textContent='';}throw Object.assign(Error(value.error||'Request failed'),{status:r.status});}
  if(mutation&&form&&stamp===snapshot(form))changedForms.delete(form);
  return value;
 }catch(e){if(!e.status)$('connection').textContent='Connection interrupted';throw e;}
 finally{if(mutation)writeCount--;}
}
async function boot(){
 try{
  const s=await api('session');user=s.user;
  $('auth').hidden=!!user;$('posRoot').hidden=!user;$('signOut').hidden=!user;$('cashier').textContent=user?.name||'';
  if(s.setup){$('authError').textContent='Set up the Operations server first, then sign in here.';return;}
  if(!user)return;
  if(!can('use_pos')){$('posRoot').hidden=true;$('auth').hidden=false;$('authError').textContent='Ask an administrator to grant Point of Sale access to your role.';return;}
  $('navSetup').hidden=!can('manage_pos');$('posSetupShortcut').hidden=!can('manage_pos');
  for(const [id,allowed]of [['linkClock',true],['linkReservations',can('view_schedule')],['linkPaging',can('send_pages')]]){$(id).setAttribute('aria-disabled',String(!allowed));$(id).tabIndex=allowed?0:-1;}
  await posLoad();
 }catch(e){$('authError').textContent=e.message;}
}
function showFlow(mandatory=false){
 if(!flow)return;
 flowMandatory=flowMandatory||mandatory||flow.ready;
 const done=flow.phase==='complete'||flow.phase==='failed'||flow.phase==='canceled';
 $('updateTitle').textContent=flow.phase==='complete'?'Update complete':flow.phase==='failed'?'Update failed':flow.phase==='canceled'?'Update canceled':'Update pending';
 $('updateText').textContent=done?(flow.error||'You can return to the application.'):flow.ready?'Your work is saved. Waiting for the other users and server update.':'Finish your current work. Before moving to another page, confirm that your work is saved.';
 $('updateMinimize').hidden=flowMandatory||done;$('updateReady').hidden=done||!!flow.ready;$('updateDone').hidden=!done;
 if(!$('updateDialog').open)$('updateDialog').showModal();
}
async function pollFlow(){
 try{
  const receipt=sessionStorage.getItem('yfc-pos-update-receipt');
  if(!user&&receipt){flow=await api('update-result?receipt='+encodeURIComponent(receipt));showFlow(true);return;}
  if(!user)return;
  const current=await api('update-flow');flow=current;
  $('updateBadge').hidden=!flow.active;
  if(flow.receipt)sessionStorage.setItem('yfc-pos-update-receipt',flow.receipt);
  if(flow.active&&flow.id!==flowSeen){flowSeen=flow.id;flowMandatory=false;showFlow();}
  else if($('updateDialog').open)showFlow();
 }catch(e){
  const receipt=sessionStorage.getItem('yfc-pos-update-receipt');
  if(receipt)try{flow=await api('update-result?receipt='+encodeURIComponent(receipt));showFlow(true);}catch{}
 }
}
function navigationAllowed(){
 if(flow?.active){if(unfinished()){toast('Finish or save your current work before changing pages.');return false;}showFlow(true);return false;}
 return true;
}
document.addEventListener('click',e=>{
 const link=e.target.closest('.operationsLinks a');
 if(link&&(link.getAttribute('aria-disabled')==='true'||!user)){e.preventDefault();return;}
 if(e.target.closest('.operationsLinks a,#navCheckout,#navSales,#navSetup,#posNew,#signOut,#posSalesShortcut,#posSetupShortcut')&&!navigationAllowed()){e.preventDefault();e.stopImmediatePropagation();}
},true);
window.addEventListener('beforeunload',e=>{if(unfinished()){e.preventDefault();e.returnValue='';}});

// POS development foundation. No processor credentials or card charges.
const posPanel=document.createElement('section');posPanel.id='posPanel';posPanel.className='panel';posPanel.hidden=false;
posPanel.innerHTML=`<h1>Point of Sale</h1>
<p class="cardNotice">Credit cards will be added in future updates.</p>
<p id="posStatus" role="status"></p><div class="actions"><button id="posNew">New sale</button><button id="posReload">Reload saved carts</button><button id="posRetry" hidden>Retry / check last action</button><button id="posHistory">Sales history</button></div>
<div class="posLayout"><section><h2>Items</h2><label>Search catalog<input id="posSearch" type="search"></label><div id="posCatalog" class="posCatalog"></div>
<details><summary>Manual item</summary><form id="posManual"><label>Description<input name="name" maxlength="120" required></label><label>Category<input name="category" maxlength="60" required></label><label>Unit price ($)<input name="price" type="number" min="0.01" max="100000" step="0.01" required></label><label>Quantity<input name="quantity" type="number" min="1" max="999" value="1" required></label><label><input name="taxable" type="checkbox" checked> Taxable</label><button>Add to sale</button></form></details></section>
<section><h2>Current sale</h2><label>Saved carts<select id="posCarts"><option value="">Choose a cart</option></select></label><div id="posCart"></div><form id="posCash"><label>Cash received ($)<input name="tender" type="number" min="0" step="0.01" required></label><button class="primary">Complete cash sale</button><button type="button" disabled>Credit cards will be added in future updates</button></form><button id="posDiscard">Discard current cart</button></section></div>
<details id="posAdmin"><summary>POS setup and catalog</summary><div class="posLayout"><form id="posSetup"><h2>Receipt and tax settings</h2><label>Store name<input name="store" maxlength="120" required></label><label>Sales tax (%)<input name="tax" type="number" min="0" max="100" step="0.01" required></label><label><input name="confirmed" type="checkbox" required> I confirmed this rate for this store.</label><p>USD; tax rounded per line. Changes apply to new carts. One tax rate is supported.</p><button>Save POS settings</button></form>
<form id="posProduct"><h2>Add catalog item</h2><label>Name<input name="name" maxlength="120" required></label><label>Category<input name="category" maxlength="60" required></label><label>Unit price ($)<input name="price" type="number" min="0.01" max="100000" step="0.01" required></label><label><input name="taxable" type="checkbox" checked> Taxable</label><button>Save catalog item</button></form></div></details>
<section id="posSales" hidden><h2>Recent sales</h2><p>Latest 100 sales visible to your account.</p><div id="posSaleList"></div></section><section id="posReceipt" hidden></section><button id="posPrint" hidden>Print receipt</button>`;
$('posRoot').append(posPanel);
// Touch-friendly register layout. Existing cash/cart operations remain server-backed.
const register=$('posPanel').querySelector('.posLayout');register.classList.add('registerLayout');
const items=register.children[0],receipt=register.children[1];items.classList.add('itemsPane');receipt.classList.add('receiptPane');
items.querySelector('h2').remove();
const searchLabel=$('posSearch').parentElement;searchLabel.classList.add('catalogSearch');searchLabel.firstChild.textContent='Search items';$('posSearch').placeholder='Name or category';
const categoryPane=document.createElement('section');categoryPane.className='categoryPane';categoryPane.innerHTML='<h2>Categories</h2><div id="posCategories"></div>';items.prepend(categoryPane);
const productPane=document.createElement('div');productPane.className='productPane';productPane.innerHTML='<div class="catalogHeading"><h2 id="posCategoryTitle">All items</h2><span id="posItemCount"></span></div>';items.append(productPane);productPane.append(searchLabel,$('posCatalog'),$('posManual').parentElement);
receipt.querySelector('h2').outerHTML='<div class="receiptHeading"><span id="posSaleNumber">CURRENT SALE</span><h2>Receipt</h2><span class="receiptCurrency">USD</span></div>';
const receiptBody=document.createElement('div');receiptBody.className='receiptBody';receipt.insertBefore(receiptBody,$('posCart'));receiptBody.append($('posCart'),$('posReceipt'),$('posPrint'));
const cashDetails=document.createElement('details');cashDetails.id='posCashDetails';cashDetails.innerHTML='<summary>Cash payment</summary>';receipt.insertBefore(cashDetails,$('posCash'));cashDetails.append($('posCash'));
const receiptTools=document.createElement('div');receiptTools.className='receiptTools';receiptTools.append($('posDiscard'));receipt.append(receiptTools);
const rail=document.createElement('aside');rail.className='registerRail';rail.innerHTML='<button id="posPayNow" class="payAction" type="button"><span>Cash</span>Pay now</button><button id="posFindCart" type="button">Find saved sale</button><button id="posPrintLast" type="button">Print last receipt</button><button id="posManualShortcut" type="button">Manual item</button><button id="posSalesShortcut" type="button">Sales history</button><button id="posSetupShortcut" type="button">POS setup</button>';rail.prepend($('posNew'));register.append(rail);
$('posReload').textContent='Refresh sales';$('posDiscard').textContent='Cancel sale';
const closeSales=document.createElement('button');closeSales.type='button';closeSales.textContent='Back to register';closeSales.onclick=()=>{$('posSales').hidden=true;};$('posSales').prepend(closeSales);
$('posPayNow').onclick=()=>{$('posCashDetails').open=true;$('posCash').elements.tender.focus();posMessage('Enter cash received, then complete the cash sale.');};
$('posFindCart').onclick=()=>{$('posCarts').focus();posMessage('Select a saved sale from the list above the receipt.');};
$('posPrintLast').onclick=()=>{if(posLastReceipt){posReceipt(posLastReceipt);$('posPrint').click();}};
$('posManualShortcut').onclick=()=>{$('posManual').parentElement.open=true;$('posManual').scrollIntoView({block:'nearest'});$('posManual').elements.name.focus();};
$('posSalesShortcut').onclick=()=>$('navSales').click();$('posSetupShortcut').onclick=()=>$('navSetup').click();
let posOverview=null,posCurrent=null,posBusy=false,posPending=null,posLastUser=null,posCategory='',posLastReceipt=null;
const posMoney=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(n/100);
function posCents(value){if(!/^\d+(\.\d{1,2})?$/.test(value))throw Error('Use a positive amount with up to two decimal places.');const [a,b='']=value.split('.');return Number(a)*100+Number(b.padEnd(2,'0'));}
function posPendingKey(){return 'yfc-pos-pending:'+user.name;}
function posMessage(text){$('posStatus').textContent=text;}
function posReceipt(sale){
 posLastReceipt=sale;$('posCart').hidden=true;$('posCashDetails').hidden=true;$('posPayNow').disabled=true;$('posSales').hidden=true;
 $('posReceipt').hidden=false;$('posPrint').hidden=false;
 $('posReceipt').innerHTML=`<h2>${esc(sale.settings.store)}</h2><h3>Receipt #${sale.id}</h3><p>${esc(sale.at)}<br>Cashier: ${esc(sale.cashier)}</p><table><thead><tr><th>Item</th><th>Qty</th><th>Amount</th></tr></thead><tbody>${sale.lines.map(x=>`<tr><td>${esc(x.name)}</td><td>${x.quantity}</td><td>${posMoney(x.subtotal)}</td></tr>`).join('')}</tbody></table><p>Subtotal: ${posMoney(sale.subtotal)}<br>Tax: ${posMoney(sale.tax)}<br><strong>Total: ${posMoney(sale.total)}</strong><br>Cash received: ${posMoney(sale.tender)}<br>Change: ${posMoney(sale.change)}</p>`;
 const back=document.createElement('button');back.type='button';back.textContent='Back to current sale';back.className='receiptBack';back.onclick=()=>{$('posReceipt').hidden=true;$('posPrint').hidden=true;posRender();};$('posReceipt').append(back);
}
function posRender(){
 if(!posOverview)return;
 sessionStorage.setItem('yfc-pos-selected:'+user.name,posCurrent?.id||'');
 $('posAdmin').hidden=!can('manage_pos');
 const filter=$('posSearch').value.toLowerCase();
 const categories=[...new Set(posOverview.products.map(x=>x.category))].sort((a,b)=>a.localeCompare(b));
 if(posCategory&&!categories.includes(posCategory))posCategory='';
 const color=category=>'tile-'+(Math.max(0,categories.indexOf(category))%6);
 $('posCategories').innerHTML=[['','All items'],...categories.map(c=>[c,c])].map(([value,label])=>`<button type="button" data-category="${esc(value)}" aria-pressed="${posCategory===value}" class="${value?color(value):'tile-all'}"><span>${esc(label)}</span><small>${value?posOverview.products.filter(x=>x.category===value).length:posOverview.products.length} items</small></button>`).join('');
 $('posCategoryTitle').textContent=posCategory||'All items';
 const products=posOverview.products.filter(x=>(!posCategory||x.category===posCategory)&&(x.name+' '+x.category).toLowerCase().includes(filter));
 $('posItemCount').textContent=products.length+' items';
 $('posCatalog').innerHTML=products.map(x=>`<button type="button" data-pos-product="${x.id}" class="${color(x.category)}"><span>${esc(x.name)}</span><small>${esc(x.category)}</small><strong>${posMoney(x.price)}</strong></button>`).join('')||'<p class="catalogEmpty">No matching items. Choose another category, search again, or add a manual item.</p>';
 $('posCarts').innerHTML='<option value="">Choose a cart</option>'+posOverview.carts.map(c=>`<option value="${c.id}">${esc(c.lines[0]?.name||'Empty cart')} · ${posMoney(c.total)} · ${c.id.slice(0,6)}</option>`).join('');
 $('posCarts').value=posCurrent?.id||'';
 $('posCart').innerHTML=posCurrent?`<p>Cart ${posCurrent.id.slice(0,6)} · Saved on server · Tax ${(posCurrent.settings.tax_bps/100).toFixed(2)}%</p><div class="receiptLines"><table><thead><tr><th>Item</th><th>Qty</th><th>Amount</th><th></th></tr></thead><tbody>${posCurrent.lines.map((x,i)=>`<tr><td>${esc(x.name)}${x.taxable?'':' (non-taxable)'}</td><td>${x.quantity}</td><td>${posMoney(x.subtotal)}</td><td><button type="button" data-pos-remove="${i}">Remove</button></td></tr>`).join('')}</tbody></table></div><p>Subtotal: ${posMoney(posCurrent.subtotal)}<br>Tax: ${posMoney(posCurrent.tax)}<br><strong>Total: ${posMoney(posCurrent.total)}</strong></p>`:'<p>Start a new sale or reopen a saved cart.</p>';
 $('posPayNow').disabled=posBusy||!!posPending||!posCurrent?.lines.length||!$('posReceipt').hidden;
 $('posPrintLast').disabled=!posLastReceipt;
 $('posCart').hidden=!$('posReceipt').hidden;
 $('posSaleNumber').textContent=posCurrent?'OPEN SALE · '+posCurrent.id.slice(0,6).toUpperCase():!$('posReceipt').hidden?'COMPLETED SALE':'CURRENT SALE';
 $('posCashDetails').hidden=!posCurrent?.lines.length||!$('posReceipt').hidden;
 $('posCash').hidden=!posCurrent?.lines.length;$('posDiscard').hidden=!posCurrent;
 $('posRetry').hidden=!posPending;
 $('posNew').disabled=posBusy||!!posPending||posOverview.settings.tax_bps===null;
 if(posOverview.settings.tax_bps===null)posMessage('Configure receipt and tax settings before starting a sale.');
}
async function posLoad(){
 if(posBusy)return;
 try{
  if(posLastUser!==user.name){posLastReceipt=null;posCategory='';posCurrent=null;posOverview=null;posPending=null;posLastUser=user.name;$('posReceipt').hidden=true;$('posPrint').hidden=true;$('posSales').hidden=true;for(const form of posPanel.querySelectorAll('form'))form.reset();}
  posPending=JSON.parse(sessionStorage.getItem(posPendingKey())||'null');
  posOverview=await api('pos/overview');
  const selected=posCurrent?.id||sessionStorage.getItem('yfc-pos-selected:'+user.name);
  posCurrent=posOverview.carts.find(x=>x.id===selected)||null;
  const form=$('posSetup');if(!changedForms.has(form)){form.elements.store.value=posOverview.settings.store;form.elements.tax.value=posOverview.settings.tax_bps===null?'':(posOverview.settings.tax_bps/100).toFixed(2);}
  posRender();if(posPending)posMessage('The last action needs confirmation. Use Retry / check last action before continuing.');
 }catch(error){posMessage(error.message);}
}
async function posDo(action,data={},retry=false){
 if(posBusy)return;
 if(posPending&&!retry){posMessage('Check the pending action before starting another.');return;}
 posBusy=true;
 const forms=[...posPanel.querySelectorAll('form')];const active=document.activeElement?.form;
 try{
  if(!retry){posPending={action,data:{...data,request:Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('')}};sessionStorage.setItem(posPendingKey(),JSON.stringify(posPending));}
  for(const el of posPanel.querySelectorAll('button,input,select'))el.disabled=true;
  posMessage('Saving…');
  const result=await api('pos/'+posPending.action,posPending.data);
  if(result.cart){posCurrent=result.cart;$('posReceipt').hidden=true;$('posPrint').hidden=true;if(posPending.action==='new'){$('posCash').reset();changedForms.delete($('posCash'));}}
  if(result.sale){$('posCashDetails').open=false;posReceipt(result.sale);posCurrent=null;$('posCash').reset();changedForms.delete($('posCash'));}
  if(posPending.action==='discard')posCurrent=null;
  sessionStorage.setItem('yfc-pos-selected:'+user.name,posCurrent?.id||'');
  const finished=posPending.action;sessionStorage.removeItem(posPendingKey());posPending=null;
  if(active&&['add','cash','product'].includes(finished)){active.reset();changedForms.delete(active);}
  posMessage(result.sale?'Cash sale saved. Change: '+posMoney(result.sale.change):'Saved.');
 }catch(error){
  if(error.status>=400&&error.status<500){sessionStorage.removeItem(posPendingKey());posPending=null;}
  posMessage(error.message+(posPending?' Your request is retained. Retry to check it safely.':''));
 }finally{
  posBusy=false;for(const el of posPanel.querySelectorAll('button,input,select'))el.disabled=false;
  $('posCash').querySelector('[type=button]').disabled=true;
  await posLoad();
 }
}
function posCartAction(action,extra){if(!posCurrent){posMessage('Start or select a sale first.');return;}return posDo(action,{cart:posCurrent.id,revision:posCurrent.revision,...extra});}
$('posNew').onclick=()=>{if(changedForms.has($('posCash'))){posMessage('Finish or clear the cash amount before starting another sale.');return;}$('posSales').hidden=true;posDo('new');};$('posReload').onclick=posLoad;$('posRetry').onclick=()=>posDo('',{},true);
$('posSearch').oninput=posRender;
$('posCategories').onclick=e=>{const b=e.target.closest('[data-category]');if(b){posCategory=b.dataset.category;posRender();}};$('posCarts').onchange=()=>{if(posPending)return;if(changedForms.has($('posCash'))){posMessage('Finish or clear the cash amount before switching sales.');$('posCarts').value=posCurrent?.id||'';return;}$('posReceipt').hidden=true;$('posPrint').hidden=true;posCurrent=posOverview.carts.find(x=>x.id===$('posCarts').value)||null;posRender();};
$('posCatalog').onclick=e=>{const b=e.target.closest('[data-pos-product]');if(b)posCartAction('add',{product:b.dataset.posProduct,quantity:1});};
$('posCart').onclick=e=>{const b=e.target.closest('[data-pos-remove]');if(b)posCartAction('remove',{index:Number(b.dataset.posRemove)});};
$('posDiscard').onclick=()=>{if(confirm('Discard this saved cart? Completed sales are not affected.'))posCartAction('discard',{});};
for(const [id,action]of [['posManual','add'],['posProduct','product'],['posSetup','settings'],['posCash','cash']])$(id).onsubmit=e=>{e.preventDefault();try{const f=e.target.elements;const data=action==='settings'?{store:f.store.value,tax_bps:posCents(f.tax.value),confirmed:f.confirmed.checked}:action==='cash'?{tender:posCents(f.tender.value)}:{name:f.name.value,category:f.category.value,price:posCents(f.price.value),taxable:f.taxable.checked,...(action==='add'?{quantity:Number(f.quantity.value)}:{})};if(['add','cash'].includes(action))posCartAction(action,data);else posDo(action,data);}catch(error){posMessage(error.message);}};
$('posHistory').onclick=async()=>{try{const {sales}=await api('pos/sales');$('posSales').hidden=false;$('posSaleList').replaceChildren();for(const sale of sales){const b=document.createElement('button');b.textContent=`#${sale.id} · ${sale.at} · ${posMoney(sale.total)} · ${sale.cashier}`;b.onclick=()=>posReceipt(sale);$('posSaleList').append(b);}if(!sales.length)$('posSaleList').textContent='No completed sales.';}catch(error){posMessage(error.message);}};
$('posPrint').onclick=()=>{document.body.classList.add('printingPos');window.print();};window.addEventListener('afterprint',()=>document.body.classList.remove('printingPos'));

$('login').onsubmit=async e=>{e.preventDefault();try{await api('login',Object.fromEntries(new FormData(e.target)));e.target.reset();$('authError').textContent='';await boot();}catch(error){$('authError').textContent=error.message;}};
$('signOut').onclick=async()=>{if(unfinished()){toast('Save or clear unfinished entries before signing out.');return;}try{await api('logout',{});await boot();}catch(e){toast(e.message);}};
$('navCheckout').onclick=()=>{$('posSales').hidden=true;$('posReceipt').hidden=true;$('posPrint').hidden=true;$('posAdmin').open=false;$('posCart').hidden=false;$('posPanel').scrollIntoView({behavior:'smooth'});};
$('navSales').onclick=()=>$('posHistory').click();
$('navSetup').onclick=()=>{$('posAdmin').open=true;$('posAdmin').scrollIntoView({behavior:'smooth'});};
$('updateBadge').onclick=()=>showFlow(flowMandatory);
$('updateDialog').addEventListener('cancel',e=>{if(flowMandatory)e.preventDefault();});
$('updateMinimize').onclick=()=>$('updateDialog').close();
$('updateReady').onclick=async()=>{if(unfinished()){$('updateError').textContent='Finish or save your current work first.';return;}try{flow=await api('update-flow/acknowledge',{id:flow.id,ready:true});flow.ready=true;showFlow(true);}catch(e){$('updateError').textContent=e.message;}};
$('updateDone').onclick=()=>{sessionStorage.removeItem('yfc-pos-update-receipt');location.reload();};
let lastActivity=0;
for(const name of ['pointerdown','pointermove','keydown','input','scroll','touchstart'])document.addEventListener(name,()=>{if(user&&Date.now()-lastActivity>30000){lastActivity=Date.now();api('account/activity',{}).catch(()=>{});}},{passive:true});
setInterval(()=>{if(user)api('account/connection',{}).catch(()=>{});},15000);
setInterval(pollFlow,3000);
setInterval(async()=>{if(!user)return;try{const s=await api('session');if(s.user?.name!==user?.name){changedForms.clear();posPending=null;await boot();}}catch{}},15000);
window.addEventListener('pagehide',()=>{if(user)fetch('/api/account/connection',{method:'POST',headers:{'Content-Type':'application/json','X-Dispatch':'1','X-Dispatch-Connection':connectionId},body:JSON.stringify({closing:true}),keepalive:true}).catch(()=>{});});

// Installed POS: the native window owns exit protection; browsers do not.
let kioskInfo=null,kioskBusy=false;
const kioskRequested=new URLSearchParams(location.search).get('kiosk')==='1';
if(kioskRequested)document.body.dataset.kiosk='pending';
const kioskExitButton=document.createElement('button');kioskExitButton.id='posExitButton';kioskExitButton.textContent='Exit POS';kioskExitButton.hidden=true;document.querySelector('.headerRight').append(kioskExitButton);
const kioskDialog=document.createElement('dialog');kioskDialog.id='kioskSetupDialog';kioskDialog.innerHTML=`<h2>Set this checkout computer's admin passcode</h2><p id="kioskSetupHelp">An Operations administrator must set an exit passcode before checkout can be used.</p><form id="kioskPasscodeForm"><label>New admin exit passcode<input name="code" type="password" inputmode="numeric" pattern="[0-9]{6,12}" minlength="6" maxlength="12" autocomplete="new-password" required></label><label>Confirm passcode<input name="confirm" type="password" inputmode="numeric" pattern="[0-9]{6,12}" maxlength="12" autocomplete="new-password" required></label><p>Use 6–12 digits. This passcode protects Exit POS on this computer.</p><p id="kioskSetupError" role="alert"></p><div class="actions"><button class="primary">Save admin passcode</button><button type="button" id="kioskSetupCancel">Cancel</button><button type="button" id="kioskSetupExit">Exit POS</button></div></form>`;document.body.append(kioskDialog);
const kioskExitDialog=document.createElement('dialog');kioskExitDialog.id='posExitDialog';kioskExitDialog.innerHTML=`<h2>Exit Point of Sale</h2><p>Saved carts remain on the Operations server.</p><form id="posExitForm"><label id="posExitCodeLabel">Admin exit passcode<input name="code" type="password" inputmode="numeric" maxlength="12" autocomplete="off"></label><p id="posExitError" role="alert"></p><div class="actions"><button class="primary">Exit POS</button><button type="button" id="posExitCancel">Keep working</button></div></form>`;document.body.append(kioskExitDialog);
const kioskSettings=document.createElement('section');kioskSettings.id='posKioskSettings';kioskSettings.hidden=true;kioskSettings.innerHTML='<h2>Checkout computer</h2><p>Full-screen POS with a protected Exit button.</p><button type="button" id="changeKioskPasscode">Change admin exit passcode</button><p id="kioskSettingsStatus" role="status"></p>';$('posAdmin').append(kioskSettings);
window.posKioskCanLeave=()=>!unfinished()&&!kioskBusy;
window.showPosKioskExit=()=>{if(!kioskInfo)return;if(kioskDialog.open)kioskDialog.close();$('posExitForm').reset();$('posExitError').textContent='';$('posExitCodeLabel').hidden=!kioskInfo.configured;if(!kioskExitDialog.open)kioskExitDialog.showModal();};
async function refreshKiosk(){
 if(!window.pywebview?.api)return;
 const info=await window.pywebview.api.kiosk_info();if(info.error){$('authError').textContent=info.error;return;}
 document.querySelector('.operationsLinks p').textContent='Open Operations here, then use Return to POS. Your cart stays saved.';
 kioskInfo=info;document.body.dataset.kiosk=info.configured?'ready':'setup';kioskExitButton.hidden=false;
 kioskSettings.hidden=!user?.admin;$('changeKioskPasscode').hidden=!info.configured;
 if(!info.configured){
  if(user?.admin){$('kioskSetupCancel').hidden=true;$('kioskSetupError').textContent='';if(!kioskDialog.open&&!kioskExitDialog.open)kioskDialog.showModal();}
  else{$('auth').hidden=false;$('authError').textContent='First-time setup: an Operations administrator must sign in and set this computer’s exit passcode.';}
 }
}
const bootBeforeKiosk=boot;boot=async function(){await bootBeforeKiosk();await refreshKiosk();};
const posDoBeforeKiosk=posDo;posDo=async function(...args){if(kioskRequested&&!kioskInfo?.configured){toast('Complete administrator passcode setup before checkout.');return;}return posDoBeforeKiosk(...args);};
kioskExitButton.onclick=window.showPosKioskExit;
$('kioskSetupExit').onclick=window.showPosKioskExit;
$('posExitCancel').onclick=()=>{kioskExitDialog.close();refreshKiosk();};
$('posExitForm').onsubmit=async e=>{e.preventDefault();if(!window.posKioskCanLeave()){$('posExitError').textContent='Finish or save unfinished entries before exiting.';return;}const code=e.target.elements.code.value;e.target.reset();const result=await window.pywebview.api.request_exit(code);if(result?.error)$('posExitError').textContent=result.error;};
$('changeKioskPasscode').onclick=()=>{if(!user?.admin)return;$('kioskSetupCancel').hidden=false;$('kioskPasscodeForm').reset();$('kioskSetupError').textContent='';kioskDialog.showModal();};
$('kioskSetupCancel').onclick=()=>kioskDialog.close();
kioskDialog.addEventListener('cancel',e=>{if(!kioskInfo?.configured)e.preventDefault();});
$('kioskPasscodeForm').onsubmit=async e=>{
 e.preventDefault();if(kioskBusy)return;
 const code=e.target.elements.code.value,confirmation=e.target.elements.confirm.value;
 if(code!==confirmation){$('kioskSetupError').textContent='The passcodes do not match.';return;}
 kioskBusy=true;const button=e.target.querySelector('button');button.disabled=true;
 try{
  const approval=await api('pos/kiosk-approval',{device:kioskInfo.device,nonce:kioskInfo.nonce});
  const result=await window.pywebview.api.configure_passcode(approval.token,code,confirmation);
  if(result.error)throw Error(result.error);
  e.target.reset();kioskDialog.close();$('kioskSettingsStatus').textContent='Admin exit passcode saved for this computer.';
  await refreshKiosk();$('auth').hidden=!!user;$('posRoot').hidden=!user;
 }catch(error){$('kioskSetupError').textContent=error.message;}
 finally{kioskBusy=false;button.disabled=false;}
};
document.addEventListener('click',async e=>{
 const link=e.target.closest('.operationsLinks a');if(!link||!window.pywebview?.api)return;
 e.preventDefault();e.stopImmediatePropagation();
 if(link.getAttribute('aria-disabled')==='true'||!navigationAllowed())return;
 const tool={linkClock:'clock',linkReservations:'reservations',linkPaging:'paging'}[link.id];
 const result=await window.pywebview.api.open_operations(tool);if(result.error)toast(result.error);
},true);
window.addEventListener('pywebviewready',refreshKiosk);

boot();

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
