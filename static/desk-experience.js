let deskTraining={enabled:false,revision:0,verified:false};
async function deskTrainingRefresh(){
 if(officeMode||!user)return;
 try{deskTraining={...await api('pos/training-state?device='+encodeURIComponent(await retailDevice())),verified:true};}catch(e){deskTraining.verified=false;posMessage('Could not verify training status: '+e.message);}
 deskTrainingRender();
}
function deskTrainingRender(){
 if(officeMode)return;
 const active=deskTraining.enabled,button=$('navSales');
 button.innerHTML='TRAINING – <span class="trainingStatus">'+(deskTraining.verified?(active?'TRAINING ACTIVE':'OFF'):'Checking…')+'</span>';
 button.classList.toggle('trainingActive',active);button.setAttribute('aria-pressed',active);button.disabled=!user||!deskTraining.verified;
 $('deskTrainingBanner').hidden=!active;document.body.classList.toggle('trainingMode',active);
 $('deskSettings').hidden=!user;$('deskTerminalSettings').hidden=!can('manage_pos');
 $('deskCreditToggle').hidden=!can('use_store_credit')&&!can('manage_store_credit')&&!can('issue_cash_advances');
 const saleTools=$('deskSaleTools');
 if(saleTools){
  const sale=!!posCurrent&&$('posReceipt').hidden,blocked=posBusy||!!posPending||writeCount>0;
  saleTools.hidden=!sale||!can('use_pos');$('deskLoyaltyCustomer').disabled=blocked;
  $('thriftTools').hidden=!can('use_pos');
  $('deskThriftSold').hidden=!can('view_pos_sales');$('deskThriftDispatch').hidden=!can('view_schedule');
  for(const button of $('deskThriftChoices').querySelectorAll('[data-requires-sale]'))button.disabled=!sale||blocked;
 }
}
async function deskTrainingToggle(){
 if(!deskTraining.verified||!navigationAllowed()||unfinished()||posPending||writeCount||posBusy)return;
 const next=!deskTraining.enabled,d=checkoutModal(next?'Start training':'End training',`<p>${next?'Practice transactions will appear only in the training report. No money, store credit, stock or loyalty points will be changed. Credit cards are unavailable.':'The register will return to live sales.'}</p><p>Finish, save with Pay later, or cancel your current transaction before switching.</p><button id="trainingConfirm" class="primary">${next?'Start training':'Return to live sales'}</button>`);
 d.querySelector('#trainingConfirm').onclick=async()=>{try{deskTraining={...await retailSave('training-mode',{enabled:next,revision:deskTraining.revision}),verified:true};posCurrent=null;sessionStorage.removeItem('yfc-pos-selected:'+user.name);checkoutClose(d);await posLoad();deskTrainingRender();}catch(e){checkoutError(d,e);}};
}
async function deskTrainingReport(){
 const d=flowModal('Training transactions','<p>Practice only. These entries are excluded from sales, cash drawers, stock and customer balances.</p><form id="trainingReportFilter"><label>From<input type="date" name="from"></label><label>Through<input type="date" name="to"></label><button>Run report</button></form><div id="trainingReportRows"></div><button id="trainingReportPrint" type="button">Print report</button>');
 async function run(){try{const f=d.querySelector('form');const data=await api('pos/training-report?'+new URLSearchParams({from:f.elements.from.value,to:f.elements.to.value}));changedForms.delete(f);d.querySelector('#trainingReportRows').innerHTML=`<h3>${data.count} practice transactions · ${posMoney(data.total)}</h3><table><thead><tr><th>Date / cashier</th><th>Store</th><th>Practice transaction</th><th>Amount</th></tr></thead><tbody>${data.transactions.map(t=>`<tr><td>${esc(new Date(t.at).toLocaleString())}<br>${esc(t.cashier)}</td><td>${esc(t.store_name||t.settings?.store||t.store_id)}</td><td>${esc(t.id)} · ${esc(t.kind)}<br>${esc(t.lines?.map(l=>l.quantity+' × '+l.name).join(', ')||t.employee_name||'')}${t.reason?'<br>'+esc(t.reason):''}</td><td>${posMoney(t.total??t.amount)}</td></tr>`).join('')}</tbody></table>`;}catch(e){d.querySelector('.flowError').textContent=e.message;}}
 d.querySelector('form').onsubmit=e=>{e.preventDefault();run();};d.querySelector('#trainingReportPrint').onclick=()=>thriftPrint('Training transactions · NOT SALES',d.querySelector('#trainingReportRows').innerHTML);await run();
}
officeCards.push({section:'sales',title:'Training transactions',description:'Practice checkouts and advances, excluded from all sales totals.',icon:'▤',action:'training-report',permission:'view_pos_sales'});
const beforeTrainingOffice=officeAction;officeAction=async function(action){if(action==='training-report')return deskTrainingReport();return beforeTrainingOffice(action);};
if(!officeMode){
 const banner=document.createElement('aside');banner.id='deskTrainingBanner';banner.hidden=true;banner.setAttribute('role','status');banner.innerHTML='<span class="trainingDot" aria-hidden="true"></span><strong>TRAINING MODE ACTIVE</strong><span>Practice only · No money collected</span>';$('posPanel').prepend(banner);
 $('navSales').onclick=deskTrainingToggle;
 const settings=document.createElement('details');settings.id='deskSettings';settings.innerHTML='<summary>Settings ▾</summary><div class="deskSettingsMenu"><button id="deskTerminalSettings" type="button">Terminal setup</button></div>';retailAppearanceButton.before(settings);settings.querySelector('div').append(retailAppearanceButton);
 $('deskTerminalSettings').onclick=()=>{settings.open=false;if(can('manage_pos'))retailEnroll();};retailAppearanceButton.addEventListener('click',()=>settings.open=false);
 const rail=$('posPayNow').parentElement,credit=document.createElement('div');credit.className='deskCreditMenu';credit.innerHTML='<button id="deskCreditToggle" type="button" aria-expanded="false">Credit/ Advances</button><div id="deskCreditChoices" hidden></div>';rail.append(credit);credit.querySelector('div').append($('creditOpen'),$('cashAdvanceOpen'));
 const popups=[];
 function buttonPopup(toggle,choices,beforeOpen=()=>true){
  // Keep both menus outside scrolling panes so every touch target stays reachable.
  document.body.append(choices);choices.classList.add('deskActionChoices');
  if(typeof choices.showPopover==='function')choices.setAttribute('popover','manual');
  toggle.setAttribute('aria-controls',choices.id);toggle.setAttribute('aria-expanded','false');
  function close(){if(choices.hidePopover&&choices.matches(':popover-open'))choices.hidePopover();choices.hidden=true;toggle.setAttribute('aria-expanded','false');}
  function place(){
   if(choices.hidden)return;const anchor=toggle.getBoundingClientRect(),box=choices.getBoundingClientRect(),gap=8;
   choices.style.left=Math.max(gap,Math.min(innerWidth-box.width-gap,anchor.right-box.width))+'px';
   choices.style.top=Math.max(gap,Math.min(innerHeight-box.height-gap,anchor.top))+'px';
  }
  toggle.onclick=e=>{if(!choices.hidden){close();return;}if(!beforeOpen())return;for(const popup of popups)popup();choices.hidden=false;if(choices.showPopover)choices.showPopover();place();toggle.setAttribute('aria-expanded','true');if(e.detail===0)choices.querySelector('button:not([hidden]):not(:disabled)')?.focus();};
  choices.addEventListener('click',e=>{if(e.target.closest('button:not(:disabled)'))close();});
  document.addEventListener('pointerdown',e=>{if(!toggle.contains(e.target)&&!choices.contains(e.target))close();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!choices.hidden){close();toggle.focus();}});
  window.addEventListener('resize',place);document.addEventListener('scroll',e=>{if(!choices.contains(e.target))close();},true);
  new MutationObserver(()=>{if($('posRoot').hidden||toggle.hidden)close();}).observe($('posRoot'),{attributes:true,subtree:true,attributeFilter:['hidden']});
  popups.push(close);
 }
 buttonPopup($('deskCreditToggle'),$('deskCreditChoices'));
 document.addEventListener('pointerdown',e=>{if(!settings.contains(e.target))settings.open=false;});document.addEventListener('keydown',e=>{if(e.key==='Escape')settings.open=false;});
 const tools=document.createElement('div');tools.id='deskThriftChoices';tools.hidden=true;
 tools.innerHTML='<button type="button" id="deskThriftCustomer">Find customer &amp; rewards</button><button type="button" id="deskThriftAddCustomer">Add new customer</button><button type="button" id="deskThriftScan">Scan donated item</button><button type="button" id="deskThriftTags" data-requires-sale>Color tags</button><button type="button" id="deskThriftDonation" data-requires-sale>Donation / round-up</button><button type="button" id="deskThriftRewards" data-requires-sale>Redeem rewards</button><button type="button" id="deskThriftSold">Sold-item pickup slip</button><button type="button" id="deskThriftDispatch">Pickup &amp; delivery · STORE OPS</button>';
 function toolsAllowed(){if(!navigationAllowed())return false;if(unfinished()){posMessage('Save or clear current entries first.');return false;}return can('use_pos');}
 buttonPopup($('thriftTools'),tools,()=>{deskTrainingRender();return toolsAllowed();});
 const toolAction=action=>async()=>{if(!toolsAllowed())return;try{await action();}catch(e){posMessage('Thrift store tools could not open: '+e.message);}};
 $('deskThriftCustomer').onclick=toolAction(()=>thriftCustomers(true));$('deskThriftAddCustomer').onclick=toolAction(()=>customerCreateTouch());
 for(const [id,section] of [['deskThriftScan','scan'],['deskThriftTags','tags'],['deskThriftDonation','donations'],['deskThriftRewards','rewards']])$(id).onclick=toolAction(()=>thriftDesk(section));
 $('deskThriftSold').onclick=toolAction(()=>{if(can('view_pos_sales'))return thriftPickupEditor();});
 // Reuse the permitted Operations route, including native Return to POS handling.
 $('deskThriftDispatch').onclick=()=>{if(toolsAllowed()&&can('view_schedule'))$('linkReservations').click();};
 const saleTools=document.createElement('div');saleTools.id='deskSaleTools';saleTools.hidden=true;
 const loyalty=document.createElement('button');loyalty.type='button';loyalty.id='deskLoyaltyCustomer';loyalty.textContent='Loyalty customer';loyalty.onclick=toolAction(()=>{if(posCurrent&&$('posReceipt').hidden)return thriftCustomers(true);});
 $('posDiscard').before(saleTools);saleTools.append($('posDiscard'),loyalty);
 rail.append($('posFindCart'),$('posSalesShortcut'),$('posPrintLast'),$('checkoutPayLater'),$('posPayNow'));
 const load=posLoad;posLoad=async function(...args){await load(...args);await deskTrainingRefresh();};
 const render=posRender;posRender=function(...args){const result=render(...args);deskTrainingRender();return result;};
 const receipt=posReceipt;posReceipt=function(sale){receipt(sale);if(sale.training){$('posReceipt').insertAdjacentHTML('afterbegin','<h2>TRAINING · NOT A VALID SALES RECEIPT</h2><p>No payment was collected.</p>');posMessage('Practice transaction saved to the training report. No money collected.');}};
 const paper=checkoutPaper;checkoutPaper=function(sale,...args){return (sale.training?'<h3>TRAINING · NOT A VALID SALES RECEIPT</h3>':'')+paper(sale,...args);};
 const followup=pickupAfterPayment;pickupAfterPayment=async function(sale){if(sale.training)return;return followup(sale);};
 const query=checkoutQuery;checkoutQuery=async function(path){if(path==='today-receipts'&&deskTraining.enabled){const data=await api('pos/training-receipts?from='+[new Date().getFullYear(),String(new Date().getMonth()+1).padStart(2,'0'),String(new Date().getDate()).padStart(2,'0')].join('-')+'&device='+await retailDevice());return {sales:data.transactions.filter(t=>t.kind==='sale'&&(!retailTerminal||t.terminal_id===retailTerminal.id))};}return query(path);};
 const bootBeforeTraining=boot;boot=async function(...args){await bootBeforeTraining(...args);await deskTrainingRefresh();};deskTrainingRender();
}
