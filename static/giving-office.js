// Giving is separate from retail sales, inventory intake and store credit.
officeCards.push({section:'giving',action:'giving-workspace',title:'Donors & gifts',description:'Donor records, received gifts, monthly drafts and statement previews.',icon:'\u2665',permission:'view_giving'});
const beforeGivingAction=officeAction;
officeAction=async function(action){
 if(action!=='giving-workspace')return beforeGivingAction(action);
 if(!navigationAllowed()||unfinished())return posMessage('Finish or discard your current work first.');
 try{await givingOpen();}catch(e){posMessage(e.message);}
};
async function givingOpen(){
 const data=await api('giving/overview');
 const d=thriftModal('Giving','<section id="givingWorkspace"></section>');d.id='givingDialog';
 const root=d.querySelector('#givingWorkspace');let tab='donors',busy=false,pending=null,viewVersion=0;
 const close=()=>{if(busy)return;if(pending){error(Error('Retry the pending save before closing.'));return;}if(root.querySelector('form')&&changedForms.has(root.querySelector('form'))&&!confirm('Discard unsaved giving changes?'))return;root.querySelectorAll('form').forEach(f=>changedForms.delete(f));thriftClose(d);};
 d.querySelector('.flowClose').onclick=close;d.oncancel=e=>{e.preventDefault();close();};
 const error=e=>d.querySelector('.flowError').textContent=e.message;
 const input=(name,label,value='',type='text')=>`<label>${label}<input name="${name}" type="${type}" value="${esc(String(value))}" required></label>`;
 const select=(name,label,options,value)=>`<label>${label}<select name="${name}">${options.map(([v,t])=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(t)}</option>`).join('')}</select></label>`;
 const donors=()=>data.donors.map(x=>[x.id,x.name]);
 const table=(heads,rows)=>`<div style="overflow:auto"><table><thead><tr>${heads.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.join('')||`<tr><td colspan="${heads.length}">No records yet.</td></tr>`}</tbody></table></div>`;
 const donorName=id=>data.donors.find(x=>x.id===id)?.name||'Unknown donor';
 const tabs=[['donors','Donors'],['gifts','Received gifts'],['plans','Monthly giving'],...(can('giving_statements')?[['statements','Statements']]:[]),...(can('giving_settings')?[['settings','Settings']]:[])];
 function render(){
  viewVersion++;
  root.innerHTML=`<p><strong>Clover: not connected.</strong> Live payments and automatic statement delivery are not enabled.</p><div class="flowToolbar">${tabs.map(([id,label])=>`<button type="button" data-tab="${id}" ${tab===id?'class="primary" aria-current="page"':''}>${label}</button>`).join('')}</div><div id="givingContent"></div>`;
  const area=root.querySelector('#givingContent');
  if(tab==='donors')area.innerHTML=`${can('manage_donors')?'<button data-new="donor" type="button">Add donor</button>':''}`+table(['Donor','Email','Delivery',''],data.donors.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.email)}</td><td>${esc(x.delivery)}</td><td>${can('manage_donors')?`<button data-edit-donor="${x.id}">Edit</button> <button type="button" data-donor-history="${esc(x.id)}">Profile history</button>`:''} <button type="button" data-donor-gifts="${esc(x.id)}">Giving history</button></td></tr>`));
  if(tab==='gifts')area.innerHTML=`<p>Record gifts already received. This does not charge a card or update a store cash drawer.</p>${can('record_gifts')?'<button data-new="gift" type="button">Record received gift</button>':''}`+table(['Date','Donor','Fund','Amount','Reference','Status / history'],data.gifts.map(x=>`<tr tabindex="-1" data-gift-row="${esc(x.id)}"><td>${esc(x.day)}</td><td>${esc(x.donor_name)}</td><td>${esc(x.fund)}</td><td>${posMoney(x.amount)}</td><td>${esc(x.reference)}</td><td><p><small>Gift ID: ${esc(x.id)}</small></p>${x.replaces?`<p>Replaces <button type="button" data-gift-link="${esc(x.replaces)}">${esc(x.replaces)}</button></p>`:''}${x.replacement?`<p>Replaced by <button type="button" data-gift-link="${esc(x.replacement)}">${esc(x.replacement)}</button></p>`:''}<p>Recorded by ${esc(x.actor)}<br>${esc(x.at)}</p>${x.voided?`<strong>Voided</strong><p>${esc(x.correction.reason)}<br>By ${esc(x.correction.actor)}<br>${esc(x.correction.at)}</p>`:can('adjust_gifts')?`<button data-void="${x.id}">Void incorrect record</button>${can('record_gifts')?` <button type="button" data-correct-gift="${esc(x.id)}">Correct gift</button>`:''}`:'Recorded'}</td></tr>`));
  if(tab==='plans')area.innerHTML=`<p>Draft monthly commitments only. Saving a draft does not enroll or charge a donor. Secure donor authorization will be required when Clover is connected.</p>${can('manage_giving_plans')?'<button data-new="plan" type="button">Add monthly draft</button>':''}`+table(['Donor','Monthly amount','Billing day','Status',''],data.plans.map(x=>`<tr><td>${esc(donorName(x.donor))}</td><td>${posMoney(x.amount)}</td><td>${x.billing_day}</td><td>${esc(x.status)}</td><td>${can('manage_giving_plans')?`<button data-edit-plan="${x.id}">Edit draft</button> <button type="button" data-plan-history="${esc(x.id)}">View history</button>`:''}</td></tr>`));
  if(tab==='statements'){
   area.innerHTML=`<p>Preview current gifts or save a permanent copy for your records. Saved copies keep the donor details, gifts and message as they were when saved. No email will be sent.</p><form id="givingStatement">${select('donor','Donor',donors())}${input('period','Period (YYYY-MM or YYYY)',new Date().getFullYear().toString())}<button type="submit">Preview statement</button></form><div id="givingStatementPreview"></div><h3>Saved statement history</h3><div id="givingStatementHistory"></div>`;
   const form=area.querySelector('form'),version=viewVersion;
   let statementRequest=0,historyRequest=0;
   const current=()=>version===viewVersion&&d.isConnected&&form.isConnected;
   const show=s=>{
    form.hidden=!!s.saved;
    const missing=['organization','ein','address'].filter(key=>!String(s.settings[key]||'').trim());
    const setupNotice=missing.length?'<p role="note"><strong>Organization setup incomplete.</strong> Complete the organization name, EIN and mailing address in Giving Settings before issuing statements. Saved copies keep their original details; save a new copy after completing setup.</p>':'';
    const body=`<h2>${esc(s.settings.organization)}</h2><p>${esc(s.settings.address)}<br>EIN: ${esc(s.settings.ein||'Not configured')}</p><h3>Giving statement - ${esc(s.period)}</h3><p>${esc(s.donor.name)}<br>${esc(s.donor.address)}</p><p style="white-space:pre-wrap">${esc(s.message)}</p>`+table(['Date','Fund','Received','Goods/services value'],s.gifts.map(g=>`<tr><td>${esc(g.day)}</td><td>${esc(g.fund)}</td><td>${posMoney(g.amount)}</td><td>${posMoney(g.benefit_value)}</td></tr>`))+`<p><strong>Period received: ${posMoney(s.total)} | Year to date: ${posMoney(s.ytd)}</strong></p>`+s.gifts.map(g=>`<p>${esc(g.day)}: ${g.benefit?`${esc(g.benefit)} - estimated value ${posMoney(g.benefit_value)}.`:'No goods or services were provided in exchange for this contribution.'}</p>`).join('');
    const preview=area.querySelector('#givingStatementPreview');
    const status=(s.saved?`<p><strong>Saved statement - not sent</strong><br>Saved ${esc(s.created_at)} by ${esc(s.actor)}<br>Reference: ${esc(s.id)}</p>`:'<p><strong>Statement preview - not saved or sent</strong></p>');
    preview.innerHTML=status+setupNotice+'<div class="flowToolbar" id="givingStatementActions"><button type="button" id="givingPrint">Print / Save PDF</button>'+(s.saved?'<button type="button" id="givingNewStatement">New statement preview</button>':'<button type="button" id="givingSaveStatement">Save current statement copy</button>')+'</div>'+body;
    const newStatement=preview.querySelector('#givingNewStatement');
    if(newStatement)newStatement.onclick=()=>{if(busy||pending)return;statementRequest++;preview.innerHTML='';form.hidden=false;form.elements.period.focus();};
    preview.querySelector('#givingPrint').onclick=()=>thriftPrint('Giving statement '+s.period,status+setupNotice+body);
    if(s.saved&&can('giving_delivery')){
     const delivery=document.createElement('button');delivery.type='button';delivery.id='givingDelivery';delivery.textContent='Review delivery preparation';
     delivery.onclick=()=>{if(busy||pending)return;if(changedForms.has(form)&&!confirm('Discard unsaved changes?'))return;changedForms.delete(form);showDelivery(s);};preview.querySelector('#givingStatementActions').append(delivery);
    }
    const button=preview.querySelector('#givingSaveStatement');
    if(button)button.onclick=async()=>{try{const result=await save('statement_snapshot',{donor:s.donor.id,period:s.period});const fresh=root.querySelector('#givingStatement');fresh.elements.donor.value=s.donor.id;fresh.elements.period.value=s.period;await fresh.loadHistory();await fresh.showSaved(result.id);}catch(e){error(e);}};
   };
   form.showSaved=async id=>{if(busy||pending)return;if(changedForms.has(form)&&!confirm('Discard unsaved statement criteria and view the saved copy?'))return;const request=++statementRequest,donor=form.elements.donor.value;const s=await api('giving/statement_snapshot?id='+encodeURIComponent(id));if(current()&&request===statementRequest&&form.elements.donor.value===donor){changedForms.delete(form);show(s);}};
   form.loadHistory=async()=>{
    const id=form.elements.donor.value,request=++historyRequest;
    if(!id){area.querySelector('#givingStatementHistory').textContent='Add a donor to create statements.';return;}
    const history=await api('giving/statement_history?donor='+encodeURIComponent(id));
    if(!current()||request!==historyRequest||form.elements.donor.value!==id)return;
    const target=area.querySelector('#givingStatementHistory');
    target.innerHTML=table(['Period','Saved','Saved by','Total',''],history.statements.map(x=>`<tr><td>${esc(x.period)}</td><td>${esc(x.created_at)}</td><td>${esc(x.actor)}</td><td>${posMoney(x.total)}</td><td><button type="button" data-snapshot="${esc(x.id)}">View saved copy</button></td></tr>`));
    target.querySelectorAll('[data-snapshot]').forEach(b=>b.onclick=()=>form.showSaved(b.dataset.snapshot).catch(error));
   };
   form.elements.period.oninput=()=>{statementRequest++;area.querySelector('#givingStatementPreview').innerHTML='';};
   form.elements.donor.onchange=()=>{statementRequest++;area.querySelector('#givingStatementPreview').innerHTML='';form.loadHistory().catch(error);};
   form.onsubmit=async e=>{e.preventDefault();const request=++statementRequest;try{const f=form.elements,s=await api('giving/statement?donor='+encodeURIComponent(f.donor.value)+'&period='+encodeURIComponent(f.period.value));if(current()&&request===statementRequest){show(s);changedForms.delete(form);}}catch(e){if(current()&&request===statementRequest)error(e);}};
   form.loadHistory().catch(error);
  }
  if(tab==='settings')edit('settings',data.settings);
 }
 async function showDelivery(s){
  if(!s.saved||!can('giving_statements')||!can('giving_delivery'))return;
  const version=++viewVersion,area=root.querySelector('#givingContent');
  const current=()=>version===viewVersion&&d.isConnected;
  const heading=`<h3>Statement delivery preparation</h3><p><strong>Email sending is disabled. Preparing a delivery does not send it.</strong></p><p>${esc(s.donor.name)} | ${esc(s.period)}<br>Saved statement: ${esc(s.id)}<br>Saved delivery preference: ${esc(s.donor.delivery)}<br>Saved recipient: ${esc(s.donor.email||'No email address')}</p><p>Recipient details come from this saved copy. To use different details, update the donor and save a new statement copy.</p><button type="button" data-cancel>Back to statements</button>`;
  area.innerHTML=heading+'<p role="status">Loading delivery history...</p>';
  const reload=()=>{if(busy)return;if(pending){error(Error('Retry the pending save first.'));return;}const form=area.querySelector('form');if(form&&changedForms.has(form)&&!confirm('Discard unsaved changes?'))return;if(form)changedForms.delete(form);showDelivery(s);};
  try{
   const result=await api('giving/statement_deliveries?statement='+encodeURIComponent(s.id));
   if(!current())return;
   const records=result.deliveries;
   area.innerHTML=heading+'<button type="button" id="givingReloadDelivery">Reload delivery history</button>'+(!records.length?'<p>No delivery has been prepared for this saved statement.</p>':records.map(x=>`<section class="givingDeliveryRecord"><h4>${x.status==='cancelled'?'Cancelled - not sent':'Prepared - not sent'}</h4><p>Recipient: ${esc(x.recipient)}<br>Prepared by ${esc(x.actor)}<br>${esc(x.created_at)}<br>Delivery reference: ${esc(x.id)}</p>${x.cancellation?`<p>Cancelled by ${esc(x.cancellation.actor)}<br>${esc(x.cancellation.at)}<br>Reason: ${esc(x.cancellation.reason)}</p>`:''}</section>`).join(''));
   area.querySelector('#givingReloadDelivery').onclick=reload;
   let kind,body;
   if(!records.length&&s.donor.delivery==='email'&&s.donor.email){
    kind='queue_statement';body={statement:s.id};
    area.insertAdjacentHTML('beforeend','<form id="givingDeliveryForm"><button type="submit">Prepare email delivery</button></form>');
   }else if(!records.length){area.insertAdjacentHTML('beforeend','<p>This copy uses print delivery or has no saved email address. Update the donor and save a new copy to prepare email delivery.</p>');}
   else if(records[0].status==='prepared'){
    kind='cancel_statement_delivery';body={delivery:records[0].id};
    area.insertAdjacentHTML('beforeend','<form id="givingDeliveryForm"><label>Reason for cancellation<input name="reason" required maxlength="500"></label><button type="submit">Cancel preparation</button></form>');
   }else{area.insertAdjacentHTML('beforeend','<p>This preparation is cancelled. Save a new statement copy if another preparation is needed.</p>');}
   const form=area.querySelector('#givingDeliveryForm');
   if(form)form.onsubmit=async e=>{e.preventDefault();if(busy)return;try{const payload={...body};if(kind==='cancel_statement_delivery'){payload.reason=form.elements.reason.value.trim();if(!payload.reason)throw Error('Enter a reason for cancellation.');}await save(kind,payload,form,()=>showDelivery(s));}catch(e){if(current())error(e);}};
  }catch(e){
   if(!current())return;
   area.innerHTML=heading+`<p role="alert">${esc(e.message)}</p><button type="button" id="givingRetryDelivery">Retry delivery history</button>`;
   area.querySelector('#givingRetryDelivery').onclick=reload;
  }
 }

 async function showDonorHistory(id){
  if(!can('manage_donors'))return;
  const version=++viewVersion,area=root.querySelector('#givingContent');
  const heading=`<h3>Donor profile history</h3><p>${esc(donorName(id))}<br><small>Donor ID: ${esc(id)}</small></p><button type="button" data-cancel>Back to donors</button>`;
  area.innerHTML=heading+'<p role="status">Loading profile history...</p>';
  try{
   const result=await api('giving/donor_history?donor='+encodeURIComponent(id));
   if(version!==viewVersion||!d.isConnected)return;
   const fields=[['name','Name'],['email','Email'],['address','Mailing address'],['delivery','Statement preference']];
   area.innerHTML=heading+'<p>Newest changes first. These are the details recorded at each save.</p>'+(!result.history.length?'<p>No recorded changes yet. This profile may predate history tracking; its next saved change will record the prior values.</p>':result.history.map(entry=>
    `<section class="givingDonorHistoryEntry"><h4>${entry.before?'Updated':'Created'} | Revision ${esc(String(entry.revision))}</h4><p>By ${esc(entry.actor)}<br>${esc(entry.at)}</p>`+
    table(['Field','Before','After'],fields.map(([key,label])=>`<tr><th scope="row">${label}</th><td>${entry.before?esc(String(entry.before[key]??'')):'-'}</td><td>${esc(String(entry.after[key]??''))}</td></tr>`))+'</section>'
   ).join(''));
  }catch(e){
   if(version!==viewVersion||!d.isConnected)return;
   area.innerHTML=heading+`<p role="alert">${esc(e.message)}</p><button type="button" data-donor-history="${esc(id)}">Retry profile history</button>`;
  }
 }
 function showDonorGifts(id){
  const version=++viewVersion,area=root.querySelector('#givingContent');
  let request=0,offset=0,filters={year:'',fund:'',include_voided:'false'};
  const current=()=>version===viewVersion&&d.isConnected;
  area.innerHTML=`<h3>Donor giving history</h3><p>${esc(donorName(id))}<br><small>Donor ID: ${esc(id)}</small></p><button type="button" data-cancel>Back to donors</button>
   <form id="givingHistoryFilters"><label>Year (blank for all)<input name="year" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" placeholder="All years"></label>
   <label>Exact fund / ministry (blank for all)<input name="fund" maxlength="100" placeholder="All funds"></label>
   <label><input type="checkbox" name="include_voided"> Include voided entries</label><button type="submit">Apply filters</button></form>
   <div id="givingGiftHistoryResults" aria-live="polite"></div>`;
  const form=area.querySelector('form'),target=area.querySelector('#givingGiftHistoryResults');
  const load=async()=>{
   const ticket=++request;
   target.innerHTML='<p role="status">Loading giving history...</p>';
   try{
    const query=new URLSearchParams({donor:id,...filters,limit:'25',offset:String(offset)});
    const result=await api('giving/gift_history?'+query);
    if(!current()||ticket!==request)return;
    target.innerHTML=`<p><strong>${esc(String(result.total))} matching entries | Received total: ${posMoney(result.amount)}</strong><br>Totals cover all matching pages and exclude voided amounts.</p>`+
     table(['Date','Fund','Amount','Reference','Status / links'],result.gifts.map(g=>`<tr><td>${esc(g.day)}</td><td>${esc(g.fund)}</td><td>${posMoney(g.amount)}</td><td>${esc(g.reference)}</td><td>${g.voided?'Voided - excluded from total':'Recorded'}<br><small>Gift ID: ${esc(g.id)}</small>${g.replaces?`<p>Replaces: ${esc(g.replaces)}</p>`:''}${g.replacement?`<p>Replaced by: ${esc(g.replacement)}</p>`:''}</td></tr>`))+
     `<p>${result.total&&result.gifts.length?`Showing ${offset+1}-${offset+result.gifts.length} of ${result.total}`:'No matching gifts on this page.'}</p><button type="button" id="givingHistoryPrevious" ${offset===0?'disabled':''}>Previous page</button> <button type="button" id="givingHistoryNext" ${result.has_more?'':'disabled'}>Next page</button>`;
    target.querySelector('#givingHistoryPrevious').onclick=()=>{offset=Math.max(0,offset-25);load();};
    target.querySelector('#givingHistoryNext').onclick=()=>{offset+=25;load();};
   }catch(e){
    if(!current()||ticket!==request)return;
    target.innerHTML=`<p role="alert">${esc(e.message)}</p><button type="button" id="givingHistoryRetry">Retry giving history</button>`;
    target.querySelector('#givingHistoryRetry').onclick=load;
   }
  };
  form.onsubmit=e=>{e.preventDefault();filters={year:form.elements.year.value.trim(),fund:form.elements.fund.value.trim(),include_voided:String(form.elements.include_voided.checked)};offset=0;changedForms.delete(form);load();};
  load();
 }

 async function showPlanHistory(id){
  if(!can('manage_giving_plans'))return;
  const version=++viewVersion,area=root.querySelector('#givingContent');
  const heading='<h3>Monthly draft history</h3><p>Draft changes only. These records do not authorize or confirm payments.</p><button type="button" data-cancel>Back to monthly giving</button>';
  area.innerHTML=heading+'<p role="status">Loading history...</p>';
  try{
   const result=await api('giving/plan_history?id='+encodeURIComponent(id));
   if(version!==viewVersion||!d.isConnected)return;
   const fields=[['donor','Donor'],['amount','Monthly amount'],['start','Proposed start'],['billing_day','Billing day'],['fund','Fund / ministry'],['status','Status']];
   const value=(record,key)=>{
    if(!record)return '-';
    if(key==='donor')return `${esc(donorName(record.donor))}<br><small>Donor ID: ${esc(record.donor)}</small>`;
    if(key==='amount')return posMoney(record.amount);
    if(key==='status')return record.status==='draft'?'Draft - no charges':record.status==='cancelled'?'Cancelled draft':esc(String(record.status));
    return esc(String(record[key]??''));
   };
   area.innerHTML=heading+'<p>Newest changes first. Donor names reflect current profiles; donor IDs preserve the recorded association.</p>'+(!result.history.length?'<p>No recorded changes yet. This draft may predate history tracking; its next saved change will record the prior values.</p>':result.history.map(entry=>{
    const action=!entry.before?'Created':entry.after.status==='cancelled'&&entry.before.status!=='cancelled'?'Cancelled':'Updated';
    return `<section class="givingPlanHistoryEntry"><h4>${action} | Revision ${esc(String(entry.revision))}</h4><p>By ${esc(entry.actor)}<br>${esc(entry.at)}</p>`+table(['Field','Before','After'],fields.map(([key,label])=>`<tr><th scope="row">${label}</th><td>${value(entry.before,key)}</td><td>${value(entry.after,key)}</td></tr>`))+'</section>';
   }).join(''));
  }catch(e){
   if(version!==viewVersion||!d.isConnected)return;
   area.innerHTML=heading+`<p role="alert">${esc(e.message)}</p><button type="button" data-plan-history="${esc(id)}">Retry history</button>`;
  }
 }
 function edit(kind,item={}){
  if(kind==='replace_gift'&&(!can('adjust_gifts')||!can('record_gifts')||!item.id||item.voided))throw Error('This gift cannot be corrected.');
  viewVersion++;
  const area=root.querySelector('#givingContent');let fields='';
  if(kind==='donor')fields=input('name','Donor name',item.name||'')+input('email','Email',item.email||'','email').replace(' required','')+input('address','Mailing address',item.address||'').replace(' required','')+select('delivery','Statement preference',[['email','Email'],['print','Print']],item.delivery||'print');
  if(kind==='gift'||kind==='replace_gift')fields=select('donor','Donor',donors(),item.donor)+input('day','Date received',item.day||new Date().toLocaleDateString('en-CA'),'date')+input('amount','Amount ($)',item.amount==null?'':item.amount/100,'number')+select('method','Already received by',[['cash','Cash'],['check','Check'],['external_card','Card processed elsewhere'],['external_bank','Bank transfer processed elsewhere']],item.method)+input('reference','Receipt / deposit reference',item.reference||'')+input('fund','Fund / ministry',item.fund||'General Ministry')+input('benefit','Goods/services description (leave blank if none)',item.benefit||'').replace(' required','')+input('benefit_value','Goods/services value ($)',(item.benefit_value||0)/100,'number');
  if(kind==='replace_gift')fields=`<p>Original gift: <strong>${esc(item.donor_name)} - ${posMoney(item.amount)}</strong><br>${esc(item.day)} | ${esc(item.fund)}<br>Gift ID: ${esc(item.id)}</p><p>Saving preserves the original gift as voided and creates a linked replacement. This does not refund or charge a payment. Saved statement copies remain unchanged.</p>`+fields+input('reason','Reason for correction');
  if(kind==='plan')fields=select('donor','Donor',donors(),item.donor)+input('amount','Monthly amount ($)',item.amount?item.amount/100:'','number')+input('start','Proposed start',item.start||new Date().toLocaleDateString('en-CA'),'date')+input('billing_day','Billing day (1-28)',item.billing_day||1,'number')+input('fund','Fund / ministry',item.fund||'General Ministry')+select('status','Status',[['draft','Draft - no charges'],['cancelled','Cancelled draft']],item.status||'draft');
  if(kind==='settings')fields=input('organization','Organization',item.organization)+input('ein','EIN',item.ein).replace(' required','')+input('address','Organization mailing address',item.address).replace(' required','')+['monthly_message','annual_message'].map(k=>`<label>${k==='monthly_message'?'Monthly':'Annual'} statement message<textarea name="${k}" rows="4">${esc(item[k])}</textarea></label>`).join('')+'<p>Scheduled email delivery and payment credentials will be configured in a later integration step.</p>';
  area.innerHTML=`<form id="givingEdit"><h3>${kind==='replace_gift'?'Correct received gift':kind==='gift'?'Record received gift':kind==='plan'?'Monthly giving draft':kind==='settings'?'Giving settings':'Donor profile'}</h3>${fields}<p>Do not enter card numbers or security codes in these fields.</p><button type="submit" class="primary">${kind==='replace_gift'?'Save correction':'Save '+(kind==='plan'?'draft':'record')}</button><button type="button" data-cancel>Cancel</button></form>`;
  const form=area.querySelector('form');form.querySelectorAll('input[name=amount],input[name=benefit_value]').forEach(x=>{x.step='0.01';x.min=x.name==='amount'?'0.01':'0';});
  form.onsubmit=async e=>{e.preventDefault();if(busy)return;try{const raw=Object.fromEntries(new FormData(form));if('amount'in raw)raw.amount=posCents(raw.amount);if('benefit_value'in raw)raw.benefit_value=posCents(raw.benefit_value);if('billing_day'in raw)raw.billing_day=Number(raw.billing_day);if(kind==='replace_gift')raw.gift=item.id;else if(item.id)raw.id=item.id;if(['donor','plan','settings'].includes(kind))raw.revision=item.revision||0;await save(kind,raw,form);}catch(e){error(e);}};
 }
 async function save(kind,body,form,afterSave){
  const signature=JSON.stringify([kind,body]);if(pending&&pending.signature!==signature)throw Error('Retry the unchanged pending save before making another change.');
  pending=pending||{signature,request:crypto.randomUUID().replaceAll('-','')};busy=true;
  try{if(!pending.result)pending.result=await api('giving/'+kind,{...body,request:pending.request});const result=pending.result;Object.assign(data,await api('giving/overview'));pending=null;if(form)changedForms.delete(form);d.querySelector('.flowError').textContent='';if(afterSave)await afterSave();else render();return result;}
  catch(e){if(!pending?.result&&e.status>=400&&e.status<500)pending=null;throw e;}
  finally{busy=false;}
 }
 root.onclick=async e=>{const b=e.target.closest('button');if(!b||busy)return;try{
  if(b.dataset.tab||b.hasAttribute('data-cancel')){if(pending)throw Error('Retry the pending save first.');const f=root.querySelector('form');if(f&&changedForms.has(f)&&!confirm('Discard unsaved changes?'))return;if(f)changedForms.delete(f);tab=b.dataset.tab||tab;render();}
  if(b.dataset.new){if(b.dataset.new!=='donor'&&!data.donors.length)throw Error('Add a donor first.');edit(b.dataset.new);}
  if(b.dataset.donorHistory)await showDonorHistory(b.dataset.donorHistory);
  if(b.dataset.donorGifts)showDonorGifts(b.dataset.donorGifts);
  if(b.dataset.editDonor)edit('donor',data.donors.find(x=>x.id===b.dataset.editDonor));
  if(b.dataset.correctGift)edit('replace_gift',data.gifts.find(x=>x.id===b.dataset.correctGift));
  if(b.dataset.giftLink){const row=[...root.querySelectorAll('[data-gift-row]')].find(x=>x.dataset.giftRow===b.dataset.giftLink);if(row){row.scrollIntoView({block:'center'});row.focus();}}
  if(b.dataset.editPlan)edit('plan',data.plans.find(x=>x.id===b.dataset.editPlan));
  if(b.dataset.planHistory)await showPlanHistory(b.dataset.planHistory);
  if(b.dataset.void){const reason=prompt('Why is this gift record incorrect? This records a void; it does not refund a payment.');if(reason)await save('void',{gift:b.dataset.void,reason});}
 }catch(e){error(e);}};
 render();
}


