// Employee cash payments use their own immutable ledger, separate from checkout.
function cashAdvancePending(){try{return user?JSON.parse(sessionStorage.getItem('retail-save:'+user.name+':cash-advance')||'null'):null;}catch{return null;}}
const cashAdvanceButton=document.createElement('button');cashAdvanceButton.id='cashAdvanceOpen';cashAdvanceButton.type='button';cashAdvanceButton.textContent='Cash Advance';cashAdvanceButton.hidden=true;$('creditOpen').after(cashAdvanceButton);
function cashAdvanceVisibility(){cashAdvanceButton.hidden=officeMode||!can('use_pos')||(!can('issue_cash_advances')&&!cashAdvancePending());cashAdvanceButton.textContent=cashAdvancePending()?'Cash Advance · Check pending':'Cash Advance';}
const beforeCashAdvanceRender=posRender;posRender=function(...args){beforeCashAdvanceRender(...args);cashAdvanceVisibility();};
const beforeCashAdvanceBoot=boot;boot=async function(){await beforeCashAdvanceBoot();cashAdvanceVisibility();if(!user)$('cashAdvanceDialog')?.close();};
const beforeCashAdvanceUnfinished=unfinished;unfinished=function(){return beforeCashAdvanceUnfinished()||!!cashAdvancePending();};
cashAdvanceButton.onclick=async()=>{if(!navigationAllowed())return;if(writeCount||posBusy||posPending){posMessage('Finish or confirm the current payment before issuing an advance.');return;}try{await cashAdvanceOpen();}catch(e){posMessage(e.message);}};

async function cashAdvanceOpen(){
 if($('cashAdvanceDialog')?.open)return;
 const d=thriftModal('Employee cash advance','<p role="status">Loading employee and drawer information…</p>');d.id='cashAdvanceDialog';
 let busy=false,form=null;
 const close=()=>{if(busy||writeCount)return;if(form&&changedForms.has(form)&&!cashAdvancePending()&&!confirm('Discard this unrecorded cash advance?'))return;thriftClose(d);cashAdvanceVisibility();};
 d.querySelector('.flowClose').onclick=close;d.oncancel=e=>{e.preventDefault();close();};
 const content=document.createElement('section');d.querySelector('p[role=status]').replaceWith(content);
 const error=e=>{d.querySelector('.flowError').textContent=e.message;};
 function receipt(advance,recovered=false){
  if(form)changedForms.delete(form);
  content.innerHTML=`<div class="advanceReceipt"><span class="eyebrow">EMPLOYEE CASH ADVANCE</span><h3>Advance #${advance.id} recorded</h3><strong class="advanceAmount">${posMoney(advance.amount)}</strong><dl><dt>Employee receiving cash</dt><dd>${esc(advance.employee_name)}</dd><dt>Issued by</dt><dd>${esc(advance.actor_name)}</dd><dt>Store / terminal</dt><dd>${esc(advance.store_name)} · ${esc(advance.terminal_name)}</dd><dt>Recorded</dt><dd>${esc(new Date(advance.at).toLocaleString())}</dd><dt>Drawer session</dt><dd>${advance.drawer?'#'+advance.drawer:'Reconciliation not enabled'}</dd><dt>Reason / reference</dt><dd>${esc(advance.reason)}</dd></dl><p>${recovered?'This advance was already recorded. Check whether the cash was handed over before paying; do not pay it twice.':'Give the recorded amount to this employee once. This payment is included in the cash drawer report.'}</p><p class="muted">Payroll recovery is handled separately.</p><div class="flowToolbar"><button id="advancePrint" type="button">Print record</button><button id="advanceDone" class="primary" type="button">Done</button></div></div>`;
  content.querySelector('#advanceDone').onclick=close;
  content.querySelector('#advancePrint').onclick=()=>{const copy=content.querySelector('.advanceReceipt').cloneNode(true);copy.querySelector('.flowToolbar').remove();thriftPrint('Employee cash advance #'+advance.id,copy.innerHTML);};
  cashAdvanceVisibility();
 }
 try{
  const pending=cashAdvancePending();
  if(pending){
   const result=await api('pos/cash-advance-status?request='+encodeURIComponent(pending.request));
   if(result.advance){sessionStorage.removeItem('retail-save:'+user.name+':cash-advance');receipt(result.advance,true);return;}
  }
  const device=await retailDevice(),data=await api('pos/cash-advance-setup?device='+encodeURIComponent(device)),ctx=data.context;
  const saved=pending?JSON.parse(pending.payload):null;
  content.innerHTML=`<div class="advanceContext"><strong>${esc(ctx.store_name)}</strong><span>${esc(ctx.terminal_name)}${ctx.drawer_id?' · Drawer #'+ctx.drawer_id:''}</span></div><p>${ctx.drawers_enabled?(ctx.drawer_id?'Expected drawer cash: '+posMoney(ctx.expected):'Open this terminal’s cash drawer in OFFICE before issuing an advance.'):'Drawer reconciliation is off. This payment will still appear in cash and employee-advance reports.'}</p><form id="cashAdvanceForm"><label>Employee receiving cash<select name="employee" required><option value="">Select another employee</option>${data.employees.map(e=>`<option value="${esc(e.id)}">${esc(e.name)}</option>`).join('')}</select></label><label>Amount ($)<input name="amount" type="number" inputmode="decimal" min="0.01" max="100000" step="0.01" required></label><label>Reason / reference<textarea name="reason" maxlength="300" rows="3" required></textarea></label><p>Confirm the employee and amount before handing over cash. This is a cash payment record; payroll recovery is handled separately.</p><button id="advanceSubmit" class="primary" type="submit">Record cash advance</button></form>`;
  form=content.querySelector('form');const fields=form.elements;
  if(saved){fields.employee.value=saved.employee;fields.amount.value=(saved.amount/100).toFixed(2);fields.reason.value=saved.reason;}
  function frozen(){if(cashAdvancePending()){for(const field of [fields.employee,fields.amount,fields.reason])field.disabled=true;fields.namedItem('advanceSubmit').textContent='Retry / check this advance';}else {fields.namedItem('advanceSubmit').textContent='Record cash advance';fields.namedItem('advanceSubmit').disabled=ctx.drawers_enabled&&!ctx.drawer_id;}}
  frozen();
  form.onsubmit=async e=>{
   e.preventDefault();if(busy)return;
   try{
    const retry=cashAdvancePending();const payload=retry?JSON.parse(retry.payload):{employee:fields.employee.value,amount:posCents(fields.amount.value),reason:fields.reason.value,terminal:ctx.terminal,store_id:ctx.store_id,drawer_id:ctx.drawer_id,confirmed:true};
    if(!retry&&!confirm(`Record ${posMoney(payload.amount)} cash paid to ${fields.employee.selectedOptions[0]?.textContent} from ${ctx.store_name} / ${ctx.terminal_name}?`))return;
    busy=true;d.querySelector('.flowError').textContent='';
    const result=await retailSave('cash-advance',payload);receipt(result.advance,!!retry);
   }catch(e){error(e);if(!cashAdvancePending())for(const field of [fields.employee,fields.amount,fields.reason])field.disabled=false;frozen();if(cashAdvancePending())d.querySelector('.flowError').textContent='Payment status is unconfirmed. Retry / check this same advance before handing over cash. '+e.message;}
   finally{busy=false;cashAdvanceVisibility();}
  };
 }catch(e){content.textContent='Cash advances are unavailable. '+e.message;}
}
