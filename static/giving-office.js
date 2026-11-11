// Giving is separate from retail sales, inventory intake and store credit.
officeCards.push({section:'giving',action:'giving-workspace',title:'Donors & gifts',description:'Donor records, received gifts, monthly drafts and statement previews.',icon:'♥',permission:'view_giving'});
const beforeGivingAction=officeAction;
officeAction=async function(action){
 if(action!=='giving-workspace')return beforeGivingAction(action);
 if(!navigationAllowed()||unfinished())return posMessage('Finish or discard your current work first.');
 try{await givingOpen();}catch(e){posMessage(e.message);}
};
async function givingOpen(){
 const data=await api('giving/overview');
 const d=thriftModal('Giving','<section id="givingWorkspace"></section>');d.id='givingDialog';
 const root=d.querySelector('#givingWorkspace');let tab='donors',busy=false,pending=null;
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
  root.innerHTML=`<p><strong>Clover: not connected.</strong> Live payments and automatic statement delivery are not enabled.</p><div class="flowToolbar">${tabs.map(([id,label])=>`<button type="button" data-tab="${id}" ${tab===id?'class="primary" aria-current="page"':''}>${label}</button>`).join('')}</div><div id="givingContent"></div>`;
  const area=root.querySelector('#givingContent');
  if(tab==='donors')area.innerHTML=`${can('manage_donors')?'<button data-new="donor" type="button">Add donor</button>':''}`+table(['Donor','Email','Delivery',''],data.donors.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.email)}</td><td>${esc(x.delivery)}</td><td>${can('manage_donors')?`<button data-edit-donor="${x.id}">Edit</button>`:''}</td></tr>`));
  if(tab==='gifts')area.innerHTML=`<p>Record gifts already received. This does not charge a card or update a store cash drawer.</p>${can('record_gifts')?'<button data-new="gift" type="button">Record received gift</button>':''}`+table(['Date','Donor','Fund','Amount','Reference','Status / history'],data.gifts.map(x=>`<tr><td>${esc(x.day)}</td><td>${esc(x.donor_name)}</td><td>${esc(x.fund)}</td><td>${posMoney(x.amount)}</td><td>${esc(x.reference)}</td><td><p>Recorded by ${esc(x.actor)}<br>${esc(x.at)}</p>${x.voided?`<strong>Voided</strong><p>${esc(x.correction.reason)}<br>By ${esc(x.correction.actor)}<br>${esc(x.correction.at)}</p>`:can('adjust_gifts')?`<button data-void="${x.id}">Void incorrect record</button>`:'Recorded'}</td></tr>`));
  if(tab==='plans')area.innerHTML=`<p>Draft monthly commitments only. Saving a draft does not enroll or charge a donor. Secure donor authorization will be required when Clover is connected.</p>${can('manage_giving_plans')?'<button data-new="plan" type="button">Add monthly draft</button>':''}`+table(['Donor','Monthly amount','Billing day','Status',''],data.plans.map(x=>`<tr><td>${esc(donorName(x.donor))}</td><td>${posMoney(x.amount)}</td><td>${x.billing_day}</td><td>${esc(x.status)}</td><td>${can('manage_giving_plans')?`<button data-edit-plan="${x.id}">Edit draft</button>`:''}</td></tr>`));
  if(tab==='statements'){
   area.innerHTML=`<p>Preview current gifts or save a permanent copy for your records. Saved copies keep the donor details, gifts and message as they were when saved. No email will be sent.</p><form id="givingStatement">${select('donor','Donor',donors())}${input('period','Period (YYYY-MM or YYYY)',new Date().getFullYear().toString())}<button type="submit">Preview statement</button></form><div id="givingStatementPreview"></div><h3>Saved statement history</h3><div id="givingStatementHistory"></div>`;
   const form=area.querySelector('form');
   const show=s=>{
    const body=`<h2>${esc(s.settings.organization)}</h2><p>${esc(s.settings.address)}<br>EIN: ${esc(s.settings.ein||'Not configured')}</p><h3>Giving statement — ${esc(s.period)}</h3><p>${esc(s.donor.name)}<br>${esc(s.donor.address)}</p><p style="white-space:pre-wrap">${esc(s.message)}</p>`+table(['Date','Fund','Received','Goods/services value'],s.gifts.map(g=>`<tr><td>${esc(g.day)}</td><td>${esc(g.fund)}</td><td>${posMoney(g.amount)}</td><td>${posMoney(g.benefit_value)}</td></tr>`))+`<p><strong>Period received: ${posMoney(s.total)} · Year to date: ${posMoney(s.ytd)}</strong></p>`+s.gifts.map(g=>`<p>${esc(g.day)}: ${g.benefit?`${esc(g.benefit)} — estimated value ${posMoney(g.benefit_value)}.`:'No goods or services were provided in exchange for this contribution.'}</p>`).join('');
    const preview=area.querySelector('#givingStatementPreview');
    const status=(s.saved?`<p><strong>Saved statement — not sent</strong><br>Saved ${esc(s.created_at)} by ${esc(s.actor)}<br>Reference: ${esc(s.id)}</p>`:'<p><strong>Statement preview — not saved or sent</strong></p>');
    preview.innerHTML=status+body+'<button type="button" id="givingPrint">Print / Save PDF</button>'+(s.saved?'':'<button type="button" id="givingSaveStatement">Save current statement copy</button>');
    preview.querySelector('#givingPrint').onclick=()=>thriftPrint('Giving statement '+s.period,status+body);
    const button=preview.querySelector('#givingSaveStatement');
    if(button)button.onclick=async()=>{try{const result=await save('statement_snapshot',{donor:s.donor.id,period:s.period});const fresh=root.querySelector('#givingStatement');fresh.elements.donor.value=s.donor.id;fresh.elements.period.value=s.period;await fresh.loadHistory();await fresh.showSaved(result.id);}catch(e){error(e);}};
   };
   form.showSaved=async id=>show(await api('giving/statement_snapshot?id='+encodeURIComponent(id)));
   form.loadHistory=async()=>{
    const id=form.elements.donor.value;
    if(!id){area.querySelector('#givingStatementHistory').textContent='Add a donor to create statements.';return;}
    const history=await api('giving/statement_history?donor='+encodeURIComponent(id));
    if(form.elements.donor.value!==id)return;
    const target=area.querySelector('#givingStatementHistory');
    target.innerHTML=table(['Period','Saved','Saved by','Total',''],history.statements.map(x=>`<tr><td>${esc(x.period)}</td><td>${esc(x.created_at)}</td><td>${esc(x.actor)}</td><td>${posMoney(x.total)}</td><td><button type="button" data-snapshot="${esc(x.id)}">View saved copy</button></td></tr>`));
    target.querySelectorAll('[data-snapshot]').forEach(b=>b.onclick=()=>form.showSaved(b.dataset.snapshot).catch(error));
   };
   form.elements.donor.onchange=()=>{area.querySelector('#givingStatementPreview').innerHTML='';form.loadHistory().catch(error);};
   form.onsubmit=async e=>{e.preventDefault();try{const f=form.elements;show(await api('giving/statement?donor='+encodeURIComponent(f.donor.value)+'&period='+encodeURIComponent(f.period.value)));changedForms.delete(form);}catch(e){error(e);}};
   form.loadHistory().catch(error);
  }
  if(tab==='settings')edit('settings',data.settings);
 }
 function edit(kind,item={}){
  const area=root.querySelector('#givingContent');let fields='';
  if(kind==='donor')fields=input('name','Donor name',item.name||'')+input('email','Email',item.email||'','email').replace(' required','')+input('address','Mailing address',item.address||'').replace(' required','')+select('delivery','Statement preference',[['email','Email'],['print','Print']],item.delivery||'print');
  if(kind==='gift')fields=select('donor','Donor',donors())+input('day','Date received',new Date().toLocaleDateString('en-CA'),'date')+input('amount','Amount ($)','','number')+select('method','Already received by',[['cash','Cash'],['check','Check'],['external_card','Card processed elsewhere'],['external_bank','Bank transfer processed elsewhere']])+input('reference','Receipt / deposit reference')+input('fund','Fund / ministry','General Ministry')+input('benefit','Goods/services description (leave blank if none)').replace(' required','')+input('benefit_value','Goods/services value ($)',0,'number');
  if(kind==='plan')fields=select('donor','Donor',donors(),item.donor)+input('amount','Monthly amount ($)',item.amount?item.amount/100:'','number')+input('start','Proposed start',item.start||new Date().toLocaleDateString('en-CA'),'date')+input('billing_day','Billing day (1–28)',item.billing_day||1,'number')+input('fund','Fund / ministry',item.fund||'General Ministry')+select('status','Status',[['draft','Draft — no charges'],['cancelled','Cancelled draft']],item.status||'draft');
  if(kind==='settings')fields=input('organization','Organization',item.organization)+input('ein','EIN',item.ein).replace(' required','')+input('address','Organization mailing address',item.address).replace(' required','')+['monthly_message','annual_message'].map(k=>`<label>${k==='monthly_message'?'Monthly':'Annual'} statement message<textarea name="${k}" rows="4">${esc(item[k])}</textarea></label>`).join('')+'<p>Scheduled email delivery and payment credentials will be configured in a later integration step.</p>';
  area.innerHTML=`<form id="givingEdit"><h3>${kind==='gift'?'Record received gift':kind==='plan'?'Monthly giving draft':kind==='settings'?'Giving settings':'Donor profile'}</h3>${fields}<p>Do not enter card numbers or security codes in these fields.</p><button type="submit" class="primary">Save ${kind==='plan'?'draft':'record'}</button><button type="button" data-cancel>Cancel</button></form>`;
  const form=area.querySelector('form');form.querySelectorAll('input[name=amount],input[name=benefit_value]').forEach(x=>{x.step='0.01';x.min=x.name==='amount'?'0.01':'0';});
  form.onsubmit=async e=>{e.preventDefault();if(busy)return;try{const raw=Object.fromEntries(new FormData(form));if('amount'in raw)raw.amount=posCents(raw.amount);if('benefit_value'in raw)raw.benefit_value=posCents(raw.benefit_value);if('billing_day'in raw)raw.billing_day=Number(raw.billing_day);if(item.id)raw.id=item.id;if(['donor','plan','settings'].includes(kind))raw.revision=item.revision||0;await save(kind,raw,form);}catch(e){error(e);}};
 }
 async function save(kind,body,form){
  const signature=JSON.stringify([kind,body]);if(pending&&pending.signature!==signature)throw Error('Retry the unchanged pending save before making another change.');
  pending=pending||{signature,request:crypto.randomUUID().replaceAll('-','')};busy=true;
  try{const result=await api('giving/'+kind,{...body,request:pending.request});pending=null;if(form)changedForms.delete(form);Object.assign(data,await api('giving/overview'));d.querySelector('.flowError').textContent='';render();return result;}
  catch(e){if(e.status>=400&&e.status<500)pending=null;throw e;}
  finally{busy=false;}
 }
 root.onclick=async e=>{const b=e.target.closest('button');if(!b||busy)return;try{
  if(b.dataset.tab||b.hasAttribute('data-cancel')){if(pending)throw Error('Retry the pending save first.');const f=root.querySelector('form');if(f&&changedForms.has(f)&&!confirm('Discard unsaved changes?'))return;if(f)changedForms.delete(f);tab=b.dataset.tab||tab;render();}
  if(b.dataset.new){if(b.dataset.new!=='donor'&&!data.donors.length)throw Error('Add a donor first.');edit(b.dataset.new);}
  if(b.dataset.editDonor)edit('donor',data.donors.find(x=>x.id===b.dataset.editDonor));
  if(b.dataset.editPlan)edit('plan',data.plans.find(x=>x.id===b.dataset.editPlan));
  if(b.dataset.void){const reason=prompt('Why is this gift record incorrect? This records a void; it does not refund a payment.');if(reason)await save('void',{gift:b.dataset.void,reason});}
 }catch(e){error(e);}};
 render();
}
