// Register shifts are shared by every cashier on a terminal, not employee punches.
const shiftDate=n=>n==null?'—':new Date(n*1000).toLocaleString('en-US',{timeZone:'America/Chicago'});
const shiftTotal=(label,value)=>`<div class="shiftMetric"><small>${esc(label)}</small><strong>${posMoney(value)}</strong></div>`;
officeCards.push(
 {section:'sales',action:'shift-settings',title:'Register shifts & business day',description:'Daily closing time and Letter or receipt report paper.',icon:'◷',permission:'manage_pos',keywords:'end shift terminal cutoff business day closing printer'},
 {section:'reports',action:'shift-history',title:'Register shift reports',description:'Terminal sales, payments, cash advances and unpaid voids by business day.',icon:'▤',permission:'view_pos_sales',keywords:'end shift summary detail close day void'}
);
officeNavigationGroups.find(g=>g.id==='transactions').actions.push('shift-settings');
officeNavigationGroups.find(g=>g.id==='sales'&&g.section==='reports').actions.push('shift-history');

function shiftReportHTML(r,detail=false){
 const totals=`<section class="shiftTotals">${shiftTotal('Completed sales (including tax)',r.sales_total)}${shiftTotal('Tax included',r.tax)}${shiftTotal('Cash rounding',r.cash_rounding)}${shiftTotal('Cash collected after change',r.cash)}${shiftTotal('Store credit collected',r.store_credit)}${shiftTotal('Cash refunds',r.cash_refunds)}${shiftTotal('Store credit refunds',r.credit_refunds)}${shiftTotal('Employee cash advances',r.advances)}${shiftTotal('Net cash movement',r.net_cash)}</section>`;
 const entries=r.events.map(e=>{
  const amount=e.kind==='sale'?e.sale.total:e.kind==='advance'?-e.advance.amount:e.kind==='refund'?-(e.refund.cash+e.refund.store_credit):0;
  const title={sale:'Receipt',void:'Unpaid void',advance:'Cash advance',refund:'Refund'}[e.kind];
  const note=e.kind==='void'?e.reason+' · Original amount '+posMoney(e.original.total)+' · $0.00 collected':e.kind==='advance'?e.advance.employee_name+' · '+e.advance.reason:e.kind==='refund'?'Original receipt #'+e.refund.sale:e.sale.method.replaceAll('_',' ');
  const lines=detail?(e.sale?.lines||e.original?.lines||[]):[];
  return `<article class="shiftEntry"><div><strong>${esc(title)} #${esc(e.reference)}</strong><strong>${posMoney(amount)}</strong></div><p>${esc(e.cashier)} · ${esc(shiftDate(e.at))}</p><p>${esc(note)}</p>${lines.length?'<ul>'+lines.map(l=>`<li>${esc(l.quantity)} × ${esc(l.name)} — ${posMoney(l.subtotal)}${e.kind==='void'?' (voided)':''}</li>`).join('')+'</ul>':''}</article>`;
 }).join('');
 return `<header class="shiftReportHeader">${r.logo?`<img src="${esc(r.logo)}" alt="Store logo">`:''}<div><small>COASTYOUTH RETAIL · ${r.closed?'CLOSED SHIFT':'SHIFT IN PROGRESS'}</small><h2>${esc(r.store_name)}</h2><h3>Register shift ${detail?'detail':'summary'} #${r.id}</h3><p>${esc(r.terminal_name)} · Business date ${esc(r.business_date)}</p></div></header><section class="shiftReportMeta"><p>Opened: ${esc(shiftDate(r.opened))}<br>Closed: ${esc(shiftDate(r.closed))} · Central time<br>${r.closed?'Closed by '+esc(r.actor)+' · '+esc(r.reason):'Scheduled close: '+esc(shiftDate(r.deadline))}</p><p>Cashiers: ${esc(r.users.join(', ')||'No completed activity')}<br>${r.completed} completed transactions · ${r.voided} unpaid voids</p></section>${totals}<p class="shiftReportNote">Net cash movement is cash collected less cash refunds and employee advances. Opening floats, paid-in/out movements and drawer counts remain in Cash drawer reconciliation. Unpaid voids collect $0.00 and do not increase sales or tax.</p><h3 class="shiftSectionBar">${detail?'Transaction detail':'Transactions & audit references'}</h3>${entries||'<p>No completed transactions.</p>'}`;
}

async function shiftPrint(r,format,detail){
 const paper=document.createElement('section');paper.id='registerShiftPaper';paper.dataset.shift=String(r.id);paper.dataset.format=format;paper.innerHTML=shiftReportHTML(r,detail);
 const native=window.pywebview?.api;
 if(format==='receipt'){
  if(officeMode){const d=checkoutModal('Print from this register','<p>Open this shift on its DESK terminal to use the configured receipt printer. From OFFICE, choose Letter paper and select a printer in the print dialog.</p>');return;}
  await loadTerminalDevices();
  if(!receiptTerminalOptions?.printer){checkoutModal('No receipt printer configured','<p>Assign a receipt printer in Terminal setup, or choose Letter paper. The shift report is saved and can be printed later.</p>');return;}
  if(!native?.shift_print){checkoutModal('Update DESK to print this report','<p>Install the latest DESK update to print directly to the configured receipt printer. Letter printing is available now.</p>');return;}
 }
 document.body.append(paper);document.body.classList.add('registerShiftPrinting');
 try{
  if(format==='receipt'){
   const result=await native.shift_print(receiptTerminalOptions.printer,String(r.id));
   if(result.error)throw Error(result.error);
  }else window.print();
 }finally{document.body.classList.remove('registerShiftPrinting');paper.remove();}
}

function shiftShowReport(r,format='letter'){
 const d=checkoutModal('Register shift report',`<div class="shiftPrintControls"><label>Paper<select id="shiftReportFormat"><option value="letter">Letter · 8.5 × 11 inches</option><option value="receipt">Configured receipt printer</option></select></label><button id="shiftPrintSummary" type="button">Print summary</button><button id="shiftPrintDetail" type="button">Print detail</button></div><div class="shiftReportPreview">${shiftReportHTML(r,true)}</div>`);d.classList.add('registerShiftDialog');
 d.querySelector('#shiftReportFormat').value=format;
 for(const [id,detail] of [['shiftPrintSummary',false],['shiftPrintDetail',true]])d.querySelector('#'+id).onclick=async()=>{try{await shiftPrint(r,d.querySelector('#shiftReportFormat').value,detail);}catch(e){checkoutError(d,e);}};
}

async function shiftEndDialog(){
 $('deskSettings').open=false;
 if(posBusy||posPending||writeCount||unfinished()){posMessage('Finish or cancel the current entry before ending the register shift.');return;}
 if(deskTraining.enabled){checkoutModal('Training mode is active','<p>End training before closing a live register shift. Practice transactions remain separate from sales.</p>');return;}
 try{
  const s=await checkoutQuery('shift-status'),r=s.current;
  const rows=s.open.map(c=>`<tr><td>${esc(c.id.slice(0,8))}</td><td>${esc(c.cashier)}</td><td>${c.held?'Saved in Find':'Open sale'}</td><td>${posMoney(c.total)}</td></tr>`).join('');
  const d=checkoutModal('End Shift · '+s.terminal.name,`<p>This closes the register shift for <strong>all cashiers on this terminal</strong>. Employee timecards are unchanged.</p>${r?`<div class="shiftStatusRow"><span>Business date <strong>${esc(r.business_date)}</strong></span><span>Scheduled close <strong>${esc(shiftDate(r.deadline))}</strong></span></div><div class="shiftTotals">${shiftTotal('Completed transactions · '+r.completed,r.sales_total)}${shiftTotal('Open transactions · '+s.open.length,s.open.reduce((n,c)=>n+c.total,0))}</div>`:'<p>No register shift is currently open. Selecting a product or issuing an advance starts the next shift.</p>'}${s.open.length?`<div class="shiftBlocked" role="alert"><strong>Cannot end shift: ${s.open.length} open transaction${s.open.length===1?'':'s'}.</strong><p>Use Find to finish or cancel saved sales. Another cashier or a manager may need to resolve their transactions.</p></div><table><thead><tr><th>Transaction</th><th>Cashier</th><th>Status</th><th>Amount due</th></tr></thead><tbody>${rows}</tbody></table>`:'<p>There are no open transactions on this terminal.</p>'}<div class="shiftActions"><button id="shiftEndConfirm" class="primary" type="button" ${!r||s.open.length?'disabled':''}>End Shift for all cashiers</button>${r?'<button id="shiftPreview" type="button">View / print current summary</button>':''}${s.last?'<button id="shiftLastReport" type="button">Last closed shift report</button>':''}<button id="shiftEndBack" type="button">Keep working</button></div>`);d.classList.add('registerShiftDialog');
  let saving=false;d.beforeDismiss=()=>!saving;
  d.querySelector('#shiftEndBack').onclick=()=>checkoutClose(d);
  d.querySelector('#shiftPreview')?.addEventListener('click',()=>shiftShowReport(r,s.settings.print_format));
  d.querySelector('#shiftLastReport')?.addEventListener('click',()=>shiftShowReport(s.last,s.settings.print_format));
  d.querySelector('#shiftEndConfirm').onclick=async()=>{
   if(saving||!r)return;saving=true;
   try{
    const {report}=await retailSave('shift-end',{shift:r.id,confirmed:true});
    shiftSeenClosed=report.id;checkoutClose(d);posMessage('Register shift ended for all cashiers on '+s.terminal.name+'.');shiftShowReport(report,s.settings.print_format);
   }catch(e){checkoutError(d,e);}finally{saving=false;}
  };
 }catch(e){posMessage(e.message);}
}

async function shiftSettingsDialog(){
 const s=await checkoutQuery('shift-settings');
 const d=checkoutModal('Register shifts & business day',`<p>Applies to all registers assigned to this store. Closing is automatic even when DESK is closed.</p><form id="registerShiftSettings"><label>End of business day · Central time<input name="cutoff" type="time" step="1" required value="${s.cutoff}"></label><label>Default report paper<select name="print_format"><option value="letter">Letter · 8.5 × 11 inches</option><option value="receipt">Receipt printer configured on the register</option></select></label><p>Default closing time: 11:59:59 PM (23:59:59). The business date is the date of the scheduled closing time. Existing open shifts keep their scheduled closing time; changes apply to the next shift.</p><p>At closing, unpaid open and saved sales are voided for $0.00 with no payment collected. Their original items and amounts remain in that business day's shift report. Paid receipts and employee timecards remain intact.</p><button class="primary">Save shift settings</button></form>`);d.classList.add('registerShiftDialog');
 const f=d.querySelector('form');f.elements.print_format.value=s.print_format;
 f.onsubmit=async e=>{e.preventDefault();try{let cutoff=f.elements.cutoff.value;if(cutoff.length===5)cutoff+=':00';await retailSave('shift-settings-save',{...s,cutoff,print_format:f.elements.print_format.value});changedForms.delete(f);checkoutClose(d);posMessage('Shift settings saved. Existing open shifts retain their scheduled closing time.');}catch(error){checkoutError(d,error);}};
}
async function shiftHistoryDialog(){
 const d=checkoutModal('Register shift reports','<form id="shiftHistoryFilter"><label>From<input type="date" name="from" required></label><label>Through<input type="date" name="to" required></label><button>Run report</button></form><p>Dates are business closing dates in Central time. Includes all cashiers, unpaid voids and retained terminal history.</p><div id="shiftHistoryRows"></div>');d.classList.add('registerShiftDialog');
 const f=d.querySelector('form'),today=new Date().toLocaleDateString('en-CA',{timeZone:'America/Chicago'});f.elements.from.value=today;f.elements.to.value=today;
 const run=async()=>{try{const q=new URLSearchParams({store_id:checkoutStore(),from:f.elements.from.value,to:f.elements.to.value});const data=await api('pos/shift-history?'+q);changedForms.delete(f);d.querySelector('#shiftHistoryRows').innerHTML=`${data.more?'<p>Showing 500 shifts. Narrow the date range for more.</p>':''}<table><thead><tr><th>Business date / shift</th><th>Terminal</th><th>Status</th><th></th></tr></thead><tbody>${data.shifts.map(r=>`<tr><td>${esc(r.business_date)} · #${r.id}</td><td>${esc(r.terminal_name)}</td><td>${r.closed?esc(r.reason):'Open'}</td><td><button type="button" data-shift-report="${r.id}">View / print</button></td></tr>`).join('')||'<tr><td colspan="4">No register shifts in this period.</td></tr>'}</tbody></table>`;for(const b of d.querySelectorAll('[data-shift-report]'))b.onclick=async()=>{try{shiftShowReport(await api('pos/shift-report?id='+b.dataset.shiftReport));}catch(e){checkoutError(d,e);}};}catch(e){checkoutError(d,e);}};
 f.onsubmit=e=>{e.preventDefault();run();};await run();
}
const beforeShiftOffice=officeAction;officeAction=async function(action){
 if(!['shift-settings','shift-history'].includes(action))return beforeShiftOffice(action);
 if(!officeMode||!can(action==='shift-settings'?'manage_pos':'view_pos_sales')||!navigationAllowed()||unfinished())return;
 try{if(action==='shift-settings')await shiftSettingsDialog();else await shiftHistoryDialog();}catch(e){posMessage(e.message);}
};
let shiftSeenClosed=null,shiftWatchBusy=false,shiftWatchDevice=null;
async function shiftWatch(){
 if(officeMode||!user||shiftWatchBusy||posBusy||posPending||writeCount)return;
 shiftWatchBusy=true;
 try{
  const device=await retailDevice(),data=await api('pos/shift-watch?'+new URLSearchParams({device,cart:posCurrent?.id||''}));
  if(shiftWatchDevice!==device){shiftWatchDevice=device;shiftSeenClosed=null;}
  const last=data.last;
  if(last&&shiftSeenClosed!==last.id){
   const initial=shiftSeenClosed===null;shiftSeenClosed=last.id;
   if(!initial)posMessage(`Register shift #${last.id} closed ${last.reason==='manual'?'by a cashier':'automatically'} for business date ${last.business_date}. Reports are available under MORE → End Shift.`);
  }
  if(posCurrent&&data.cart_status==='discarded'&&!posBusy&&!posPending&&!writeCount){
   posCurrent=null;sessionStorage.removeItem('yfc-pos-selected:'+user.name);await posLoad();
   checkoutModal('Transaction closed',`<p>This unpaid transaction has been closed. No payment was collected. ${last?.reason==='end-of-business-day'?'The business day ended; the transaction is retained as a $0.00 void in the shift report for '+esc(last.business_date)+'.':'Its history remains on the server.'}</p><p>You can start a new sale by selecting a product.</p>`);
  }
 }catch{}finally{shiftWatchBusy=false;}
}
if(!officeMode){
 const b=document.createElement('button');b.id='deskEndShift';b.type='button';b.textContent='End Shift';b.onclick=shiftEndDialog;$('deskSettings').querySelector('.deskSettingsMenu').append(b);
 setInterval(shiftWatch,10000);
}
