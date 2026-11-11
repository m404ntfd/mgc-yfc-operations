// Search navigation only: no customer records, form values, or settings are indexed.
(()=>{
 if(!officeMode)return;
 const aliases={
  'catalog':'items products open price priced weight pounds pickup slip barcode sku',
  'product-tools':'items modifiers add ons options open price priced weight pounds pickup slip',
  'sub-departments':'categories category groups subdepartment subdepartments',
  'departments':'department hierarchy reporting',
  'revenue-centers':'revenue centre centers centres accounting reporting',
  'taxes':'tax taxable rates sales tax',
  'printing-categories':'print category tickets',
  'printing':'printer routes routing destinations preparation tickets',
  'cash-rules':'pennies cash rounding change return window',
  'discount-rules':'discount coupon markdown limits approvals returns',
  'surcharge-settings':'surcharge fees limits',
  'user-setup':'employee staff password reset pin passcode job work assignments profile',
  'users':'employee staff add account',
  'roles':'security access permissions roles',
  'terminals':'register pc computer checkout device layout',
  'computer-register':'register pc computer mac network device',
  'computer-updates':'software install version notify staff update website web app ops server',
  'receipt-design':'receipt logo address phone footer return policy branding',
  'stores-profiles':'store binopoly thrift mart branding receipts price tax',
  'stores-programs':'loyalty points rewards birthday gift certificates cash drawer',
  'thrift-settings':'donation color tags markdown loyalty points rewards',
  'reservation-messages':'gmail email confirmations reminders smtp',
  'hr-onboarding':'human resources hire onboarding paperwork email help',
  'timekeeping-manage':'time clock timecards punches payroll schedules availability requests work sites',
  'login-security':'unlock lockouts login attempts',
  'customer-display':'customer facing second screen monitor welcome',
  'layouts':'pos buttons colors layout editor'
 };
 const host=document.createElement('div');host.id='officeSettingsSearch';host.hidden=true;host.setAttribute('role','search');
 host.innerHTML='<div class="officeSearchField"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><input id="officeSearchInput" type="search" placeholder="Search settings…" aria-label="Search OFFICE settings" role="combobox" aria-autocomplete="list" aria-haspopup="listbox" aria-controls="officeSearchResults" aria-expanded="false" autocomplete="off" spellcheck="false" maxlength="120"><button type="button" id="officeSearchClear" aria-label="Clear settings search" hidden>×</button></div><div id="officeSearchPopup" hidden><p id="officeSearchSummary" role="status" aria-live="polite"></p><div id="officeSearchResults" role="listbox" aria-label="Matching OFFICE settings"></div><p class="officeSearchHint">↑ ↓ to choose · Enter to open · Esc to close</p></div>';
 officeNav.after(host);
 const input=$('officeSearchInput'),clear=$('officeSearchClear'),popup=$('officeSearchPopup'),results=$('officeSearchResults'),summary=$('officeSearchSummary');
 let matches=[],active=-1,opening=false,sessionName=null,renderedMarkup='';
 const normalize=value=>String(value).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
 const entries=()=>officeMenuCards();
 function close(){popup.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');}
 function sync(){
  host.hidden=!user||!$('auth').hidden||$('posRoot').hidden;
  if(host.hidden||sessionName!==user?.name){input.value='';results.replaceChildren();renderedMarkup='';matches=[];clear.hidden=true;close();}
  sessionName=user?.name;
 }
 function select(index){
  active=index;
  [...results.children].forEach((b,i)=>b.setAttribute('aria-selected',String(i===index)));
  if(index<0)input.removeAttribute('aria-activedescendant');
  else{input.setAttribute('aria-activedescendant','officeSearchResult'+index);results.children[index]?.scrollIntoView({block:'nearest'});}
 }
 function render(){
  sync();if(host.hidden)return;
  const query=normalize(input.value),words=query.split(' ').filter(Boolean);clear.hidden=!input.value;
  matches=words.length?entries().map(entry=>{
   const title=normalize(entry.title),section=officeSettingsPath(entry);
   const haystack=normalize([entry.title,entry.description,section,aliases[entry.action]||'',entry.keywords||''].join(' '));
   return {...entry,sectionLabel:section,score:title===query?0:title.startsWith(query)?1:title.includes(query)?2:3,match:words.every(word=>haystack.includes(word))};
  }).filter(entry=>entry.match).sort((a,b)=>a.score-b.score||a.title.localeCompare(b.title)):[];
  const markup=matches.map((entry,i)=>'<button type="button" role="option" tabindex="-1" id="officeSearchResult'+i+'" data-office-action="'+esc(entry.action)+'" aria-selected="false"><span class="officeSearchPath">'+esc(entry.sectionLabel)+'</span><strong>'+esc(entry.title)+'</strong><small>'+esc(entry.description)+'</small></button>').join('');
  // Preserve result nodes when a Save / Discard dialog returns focus here.
  if(markup!==renderedMarkup){results.innerHTML=markup;renderedMarkup=markup;}
  summary.textContent=!query?'Find a setting by name or keyword.':matches.length?matches.length+' matching '+(matches.length===1?'setting':'settings'):'No matching settings available for your role. Try another word.';
  popup.hidden=false;input.setAttribute('aria-expanded','true');select(matches.length?0:-1);
 }
 input.addEventListener('input',render);input.addEventListener('focus',render);
 input.addEventListener('keydown',e=>{
  if(e.isComposing)return;
  if(e.key==='Escape'){e.preventDefault();close();return;}
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){
   e.preventDefault();if(popup.hidden)render();
   if(matches.length)select((active+(e.key==='ArrowDown'?1:-1)+matches.length)%matches.length);
  }else if(e.key==='Enter'){e.preventDefault();if(popup.hidden)render();else if(active>=0)results.children[active]?.click();}
 });
 clear.onclick=()=>{input.value='';input.focus();render();};
 // Keep combobox focus while selecting with a mouse or touch pointer.
 results.addEventListener('pointerdown',e=>{if(e.target.closest('[data-office-action]'))e.preventDefault();});
 results.addEventListener('click',async e=>{
  const button=e.target.closest('[data-office-action]');if(!button||opening)return;
  const action=button.dataset.officeAction;
  // Re-check access at activation; do not trust a previously rendered result.
  if(!user||!entries().some(entry=>entry.action===action)){render();return;}
  close();
  if(!navigationAllowed())return;
  if(unfinished()){posMessage('Save or discard the current form before opening another setting.');return;}
  opening=true;
  try{
   await officeAction(action);
   input.value='';clear.hidden=true;
   if(!document.querySelector('dialog[open]')){
    const title=$('officeWork').hidden?$('officeHeading'):$('officeWorkTitle');
    title.setAttribute('tabindex','-1');title.focus({preventScroll:true});
   }
  }catch(error){posMessage(error.message);}
  finally{opening=false;}
 });
 document.addEventListener('pointerdown',e=>{if(!host.contains(e.target))close();});
 host.addEventListener('focusout',()=>queueMicrotask(()=>{if(!host.contains(document.activeElement))close();}));
 document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'&&!host.hidden&&!document.querySelector('dialog[open]')){e.preventDefault();input.focus();input.select();}
 });
 const oldRender=officeRender;officeRender=function(...args){const result=oldRender(...args);sync();return result;};
 new MutationObserver(sync).observe($('auth'),{attributes:true,attributeFilter:['hidden']});
 new MutationObserver(sync).observe($('posRoot'),{attributes:true,attributeFilter:['hidden']});
 const bar=document.querySelector('.sidebar');
 new ResizeObserver(()=>document.body.style.setProperty('--office-topbar-height',bar.offsetHeight+'px')).observe(bar);
 sync();
})();
