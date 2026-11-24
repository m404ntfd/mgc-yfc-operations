// Administrator-only setup. This pilot has no payment or card-collection action.
officeCards.push({section:'system',action:'clover-pilot',title:'Clover connection setup',description:'Assign a Clover to a register and check its network connection. Card payments remain off.',icon:'▣',permission:'admin',keywords:'clover mini card reader terminal payment connection pilot'});
officeNavigationGroups.push({section:'system',id:'payment-devices',title:'Payment devices',description:'Assign Clover hardware and check register connections.',actions:['clover-pilot']});
const beforeCloverOfficeAction=officeAction;
officeAction=async function(action){
 if(action!=='clover-pilot')return beforeCloverOfficeAction(action);
 if(!officeMode||!user?.admin||!navigationAllowed()||unfinished())return;
 return cloverPilotSetup();
};

async function cloverPilotSetup(selected){
 if(!user?.admin)return;
 try{
  const native=window.pywebview?.api;
  const info=!officeMode&&native?.kiosk_info?await native.kiosk_info():null;
  const list=await api('pos/clover-settings');
  const terminals=officeMode?list.terminals:list.terminals.filter(t=>t.device===(info?.device||null));
  if(!terminals.length){checkoutModal('Clover connection setup',`<p>${officeMode?'Register a checkout computer before assigning a Clover.':'Open this screen in the registered DESK desktop application. Sign in as an administrator to set up this register’s Clover.'}</p><p>No card payments are enabled.</p>`);return;}
  selected=terminals.some(t=>t.id===selected)?selected:terminals[0].id;
  const d=checkoutModal('Clover connection setup',`<p class="cloverPilotBadge">CONNECTION TEST ONLY · CARD PAYMENTS OFF</p><label>Registered terminal<select id="cloverTerminal">${terminals.map(t=>`<option value="${esc(t.id)}" ${t.id===selected?'selected':''}>${esc(t.name)} · ${esc(t.store_name)}</option>`).join('')}</select></label><div id="cloverSetupBody"><p>Loading saved connection details…</p></div>`);
  d.classList.add('cloverPilotDialog');let busy=false,details=null;
  d.beforeDismiss=()=>!busy;
  function status(message,error=false){const target=d.querySelector('#cloverTestResult');if(target){target.textContent=message;target.dataset.error=String(error);}}
  function setBusy(value){busy=value;for(const control of d.querySelectorAll('input,select,#cloverSave,#cloverTest'))control.disabled=value;d.querySelector('.flowClose').disabled=value;if(!value)updateTest();}
  function updateTest(){const button=d.querySelector('#cloverTest');if(!button||!details)return;button.disabled=busy||!details.settings.revision||details.store_changed||officeMode||!native?.clover_connection_check||info?.device!==details.terminal.device;}
  async function render(){
   details=await api('pos/clover-settings?terminal='+encodeURIComponent(selected));
   if(!d.isConnected)return;
   const s=details.settings,t=details.terminal;
   d.querySelector('#cloverSetupBody').innerHTML=`<div class="cloverPilotColumns"><form id="cloverSettingsForm"><h3>${esc(t.name)} · ${esc(t.store_name)}</h3><p>The saved assignment follows this registered terminal. It does not change store receipts, taxes, or existing transactions.</p>${details.store_changed?'<p class="cloverPilotNotice">This terminal moved to another store. Confirm and save the correct Clover details before testing again.</p>':''}<label>Clover local IP address<input name="address" inputmode="decimal" maxlength="15" required value="${esc(s.address)}" placeholder="For example, 192.168.2.50" autocomplete="off"></label><label>Clover serial number<input name="serial" maxlength="64" pattern="[A-Za-z0-9]{6,64}" required value="${esc(s.serial)}" placeholder="Printed underneath the Clover" autocomplete="off"></label><label>Clover merchant ID (optional for network check)<input name="merchant_id" maxlength="64" pattern="[A-Za-z0-9]{6,64}" value="${esc(s.merchant_id)}" placeholder="Leave blank until confirmed" autocomplete="off"></label><p>The merchant ID identifies the Clover account. Do not enter a password, API key, or card number.</p><button id="cloverSave" class="primary" type="submit">Save connection details</button></form><section class="cloverPilotSteps"><h3>Connection progress</h3><ol><li><strong>Register selected</strong><span>${esc(t.name)} · ${esc(t.store_name)}</span></li><li><strong>${s.revision&&!details.store_changed?'Connection details saved':'Save the Clover details'}</strong><span>Use the local address and serial shown on your device.</span></li><li><strong>Check from this register</strong><span>${officeMode?'Open DESK on '+esc(t.name)+' → MORE → Clover connection setup to run the check from that computer.':native?.clover_connection_check?'REST Pay Display must be running. The check only verifies network access.':'This DESK installation needs the connection-test update before it can run the check.'}</span></li><li><strong>Merchant authorization pending</strong><span>Clover approval and merchant authorization are still required. A successful network check does not enable card payments.</span></li></ol><button type="button" id="cloverTest">Check connection · no charge</button><p id="cloverTestResult" role="status" aria-live="polite">No authorized connection has been confirmed.</p><p>Connection uses the local network. The USB cable can remain connected.</p></section></div>`;
   updateTest();
   const form=d.querySelector('#cloverSettingsForm');
   form.onsubmit=async e=>{
    e.preventDefault();if(busy)return;
    const f=form.elements;
    const payload={terminal:selected,store_id:t.store_id,revision:s.revision,address:f.address.value.trim(),serial:f.serial.value.trim(),merchant_id:f.merchant_id.value.trim()};
    setBusy(true);
    try{await retailSave('clover-settings-save',payload);changedForms.delete(form);await render();status('Connection details saved. Card payments remain off.');}
    catch(error){status(error.message,true);}finally{setBusy(false);}
   };
   d.querySelector('#cloverTest').onclick=async()=>{
    if(busy)return;
    if(changedForms.has(form)){status('Save the edited connection details before testing.',true);return;}
    setBusy(true);status('Checking from this computer… No card will be charged.');
    try{
     const current=await native.kiosk_info();
     if(current.error||current.device!==t.device)throw Error('The registered computer changed. Reopen Clover setup.');
     const approval=await retailSave('clover-test-approval',{terminal:selected,revision:s.revision,device:current.device,nonce:current.nonce});
     const result=await native.clover_connection_check(approval.token);
     if(result.error)throw Error(result.error);
     status(result.message+' Checked from '+result.source_computer+'. No card was charged.');
    }catch(error){status(error.message,true);}finally{setBusy(false);}
   };
  }
  d.querySelector('#cloverTerminal').onchange=async e=>{
   const previous=selected;
   if(busy||changedForms.has(d.querySelector('form'))){e.target.value=previous;status('Save or discard your changes before selecting another terminal.',true);return;}
   selected=e.target.value;setBusy(true);
   try{await render();}catch(error){selected=previous;e.target.value=previous;status(error.message,true);}finally{setBusy(false);}
  };
  await render();
 }catch(error){posMessage(error.message);}
}

const beforeCloverTerminalOptions=terminalDeviceOptions;
terminalDeviceOptions=async function(id){
 await beforeCloverTerminalOptions(id);
 const form=document.querySelector('#terminalDevices');
 if(!form||!user?.admin)return;
 const button=document.createElement('button');button.type='button';button.textContent='Clover connection setup';
 button.onclick=()=>{if(changedForms.has(form))return;thriftClose(form.closest('dialog'));cloverPilotSetup(id);};form.after(button);
};

if(!officeMode){
 const menu=document.querySelector('#deskSettings .deskSettingsMenu');
 if(menu){
  const button=document.createElement('button');button.id='deskCloverSetup';button.type='button';button.textContent='Clover connection setup';button.hidden=!user?.admin;
  button.onclick=()=>{if(!user?.admin||!navigationAllowed()||unfinished())return;$('deskSettings').open=false;cloverPilotSetup();};menu.append(button);
  const beforeCloverRender=posRender;posRender=function(...args){const result=beforeCloverRender(...args);button.hidden=!user?.admin;return result;};
 }
}
