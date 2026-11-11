// OFFICE navigation changes only; existing editors, permissions and saves are reused.
const officeNavigationSections=[
 ['home','Home','⌂','Choose an area or search for a setting.'],
 ['products','Products','▦','Items, pricing, donation intake and product organization.'],
 ['sales','Sales','＄','Payment rules, transactions, refunds and cash drawers.'],
 ['accounts','Customers','◎','Customer accounts, rewards and customer communications.'],
 ['staff','Staff','♙','Users, permissions, onboarding and timekeeping.'],
 ['reports','Reports','▥','Sales, store activity and labor reports.'],
 ['system','System','⚙','Stores, checkout screens, printers, computers and updates.']
];
const officeNavigationGroups=[
 {section:'products',id:'items',title:'Items & pricing',description:'Create products, manage prices and receive donated stock.',actions:['catalog','bundles','availability','bulk-catalog','thrift-intake']},
 {section:'products',id:'organization',title:'Product organization',description:'Revenue Centers → Departments → Sub Departments.',actions:['revenue-centers','departments','sub-departments']},
 {section:'sales',id:'policies',title:'Taxes & payment rules',description:'Keep taxes, discounts, surcharges and cash settings separate.',actions:['taxes','cash-rules','discount-rules','surcharge-settings','card-future-settings']},
 {section:'sales',id:'transactions',title:'Transactions & cash',description:'Review sales, approve adjustments and manage cash drawers.',actions:['history','held','refunds','approvals','stores-drawers']},
 {section:'sales',id:'fulfillment',title:'Pickup & delivery',description:'Manage sold items awaiting collection or delivery.',actions:['thrift-pickups']},
 {section:'accounts',id:'accounts',title:'Customers & balances',description:'Customer profiles, store credit, vouchers and gift certificates.',actions:['thrift-customers','accounts','thrift-vouchers','stores-gifts','stores-members']},
 {section:'accounts',id:'programs',title:'Rewards & programs',description:'Color tags, donation prompts, loyalty and optional programs.',actions:['thrift-settings','stores-programs']},
 {section:'accounts',id:'messages',title:'Receipts & messages',description:'Receipt design, reservation confirmations and reminders.',actions:['receipt-design','reservation-messages']},
 {section:'staff',id:'access',title:'Users & permissions',description:'One shared user directory with role-based access.',actions:['users','user-setup','roles','login-security']},
 {section:'staff',id:'hr',title:'Human resources',description:'Invite employees and review onboarding progress.',actions:['hr-onboarding']},
 {section:'staff',id:'timekeeping',title:'Timekeeping',description:'Manage time entries, schedules, requests and payroll.',actions:['timekeeping-manage']},
 {section:'staff',id:'communications',title:'Communications oversight',description:'Review retained staff messages and attachments with permission.',actions:['review-communications']},
 {section:'reports',id:'sales',title:'Sales analysis',description:'Sales, tax, cash, products and transaction summaries.',actions:['report-center','reports']},
 {section:'reports',id:'store',title:'Store activity',description:'Donations, color tags, pickups, vouchers and employee cash advances.',actions:['thrift-reports','cash-advance-report']},
 {section:'reports',id:'labor',title:'Labor & schedules',description:'Time-entry reports and printable employee schedules.',actions:['labor-reports','schedule-report']},
 {section:'system',id:'stores',title:'Stores & appearance',description:'Store profiles, branding and your color theme.',actions:['stores-profiles','office-appearance']},
 {section:'system',id:'checkout',title:'Checkout & printing',description:'Terminals, DESK layouts, customer displays and ticket printing.',actions:['terminals','layouts','customer-display','printing-categories','printing']},
 {section:'system',id:'computers',title:'Computers & updates',description:'Computer registration, application updates and the shared server.',actions:['computer-register','computer-updates','server']}
];
const officeNavigationAliases={'product-tools':'catalog',receipt:'stores-profiles',cards:'card-future-settings'};
function officeSettingsPath(entry){
 const action=officeNavigationAliases[entry.action]||entry.action;
 const group=officeNavigationGroups.find(g=>g.actions.includes(action));
 const section=officeNavigationSections.find(s=>s[0]===(group?.section||entry.section));
 return [section?.[1]||'Settings',group?.title].filter(Boolean).join(' › ');
}
function officeMenuCards(){
 if(!user)return [];
 return [...officeAvailableCards().filter(c=>!officeNavigationAliases[c.action]),{action:'office-appearance',title:'Appearance & themes',description:'Choose your color theme or the store default.',section:'system',icon:'◐',keywords:'color colour liquid glass aero dark light gray grey'}];
}
if(officeMode){
 officeSections.splice(0,officeSections.length,...officeNavigationSections);
 const labels={
  catalog:['Products & item choices','Create items, set prices, and configure open prices, weights and add-ons.'],
  printing:['Printer routing','Assign printing categories to ticket destinations.'],
  'discount-rules':['Discount & return rules','Discount limits, eligible products and the return window.'],
  'card-future-settings':['Credit cards · future update','Credit cards and card surcharges will be added in future updates.'],
  users:['Add users & assign roles','Create shared accounts and assign their roles.'],
  'user-setup':['Employee profiles & access','Personal details, work assignments, PINs and individual access.'],
  reports:['Sales totals','Compare sales, tax, cash and store-credit totals.']
 };
 for(const card of officeCards){
  const group=officeNavigationGroups.find(g=>g.actions.includes(officeNavigationAliases[card.action]||card.action));
  if(group)card.section=group.section;
  if(labels[card.action])[card.title,card.description]=labels[card.action];
 }
 let officeGroup='',officeOpenedAction='';
 officeNav.innerHTML=officeSections.map(([id,label,icon])=>`<button type="button" data-office-section="${id}"><span aria-hidden="true">${icon}</span>${label}</button>`).join('');
 const navigation=document.createElement('div');navigation.id='officeNavigation';
 navigation.innerHTML='<nav id="officeBreadcrumb" aria-label="Settings location"></nav><nav id="officeGroups" aria-label="Settings groups"></nav><div id="officeGroupHeading"><h2></h2><p></p></div>';
 $('officeTiles').before(navigation);
 const availableGroups=cards=>officeNavigationGroups.filter(g=>cards.some(c=>g.actions.includes(c.action)));
 const tile=(card,attribute,extra='')=>`<button type="button" class="officeTile" ${attribute}><span class="officeIcon" aria-hidden="true">${esc(card.icon)}</span><span><strong>${esc(card.title)}</strong><small>${esc(card.description)}</small>${extra}</span><span aria-hidden="true">›</span></button>`;
 officeRender=function(){
  const cards=officeMenuCards(),groups=availableGroups(cards),sections=new Set(groups.map(g=>g.section));
  if(officeSection!=='home'&&!sections.has(officeSection)){officeSection='home';officeGroup='';}
  const section=officeSections.find(s=>s[0]===officeSection)||officeSections[0];
  const sectionGroups=groups.filter(g=>g.section===officeSection);
  if(!sectionGroups.some(g=>g.id===officeGroup))officeGroup=sectionGroups[0]?.id||'';
  const group=sectionGroups.find(g=>g.id===officeGroup);
  $('officeHeading').textContent=officeSection==='home'?'OFFICE settings':section[1];
  document.querySelector('.officeIntro p').textContent=section[3];
  for(const b of officeNav.querySelectorAll('button')){b.hidden=b.dataset.officeSection!=='home'&&!sections.has(b.dataset.officeSection);b.setAttribute('aria-current',b.dataset.officeSection===officeSection?'page':'false');}
  $('officeBreadcrumb').hidden=officeSection==='home';
  $('officeBreadcrumb').innerHTML='<button type="button" data-office-category="home">Home</button><span aria-hidden="true">›</span>'+`<button type="button" data-office-category="${section[0]}">${esc(section[1])}</button>`+(group?`<span aria-hidden="true">›</span><button type="button" data-office-group="${group.id}">${esc(group.title)}</button>`:'');
  const opened=cards.find(c=>c.action===officeOpenedAction);
  if(opened&&!$('officeWork').hidden)$('officeBreadcrumb').innerHTML+=`<span aria-hidden="true">›</span><strong aria-current="page">${esc(opened.title)}</strong>`;
  $('officeGroups').hidden=officeSection==='home'||!$('officeWork').hidden;
  $('officeGroups').innerHTML=sectionGroups.map(g=>`<button type="button" data-office-group="${g.id}" aria-pressed="${g.id===officeGroup}">${esc(g.title)}<span class="officeGroupCount">${cards.filter(c=>g.actions.includes(c.action)).length}</span></button>`).join('');
  $('officeGroupHeading').hidden=!group||!$('officeWork').hidden;
  $('officeGroupHeading').querySelector('h2').textContent=group?.title||'';
  $('officeGroupHeading').querySelector('p').textContent=group?.description||'';
  if(officeSection==='home'){
   $('officeTiles').innerHTML=officeSections.filter(s=>sections.has(s[0])).map(([id,title,icon,description])=>tile({title,icon,description},`data-office-category="${id}"`,`<span class="officeTileMeta">${groups.filter(g=>g.section===id).length} focused groups</span>`)).join('');
  }else{
   $('officeTiles').innerHTML=(group?.actions||[]).map(a=>cards.find(c=>c.action===a)).filter(Boolean).map(c=>tile(c,`data-office-action="${c.action}"`)).join('');
  }
  if(!$('officeTiles').innerHTML)$('officeTiles').innerHTML='<p>No settings are available for your role.</p>';
  $('officeBack').textContent='‹ Back to '+(group?.title||'settings');
 };
 officeHome=function(section='home',group=''){
  if(!navigationAllowed())return;
  if(unfinished()){posMessage('Save or discard your current work before changing settings.');return;}
  const legacy={hr:['staff','hr'],security:['staff','access'],timekeeping:['staff','timekeeping'],communications:['staff','communications']};
  [section,group]=legacy[section]||[section,group];
  officeSection=section;officeGroup=group;officeOpenedAction='';
  $('officeWork').hidden=true;$('officeTiles').hidden=false;officeRender();
 };
 const openExisting=officeAction;
 officeAction=async function(action){
  action=officeNavigationAliases[action]||action;
  const card=officeMenuCards().find(c=>c.action===action);
  if(!card){posMessage('Your role does not have access to this setting.');return;}
  if(!navigationAllowed())return;
  if(unfinished()){posMessage('Save or discard your current work before opening another setting.');return;}
  const group=officeNavigationGroups.find(g=>g.actions.includes(action));
  if(group){officeSection=group.section;officeGroup=group.id;}
  officeOpenedAction=action;officeRender();
  if(action==='office-appearance')retailAppearanceButton.click();
  else await openExisting(action);
  officeRender();
 };
 $('officeTiles').onclick=e=>{const b=e.target.closest('button');if(b?.dataset.officeCategory)officeHome(b.dataset.officeCategory);else if(b?.dataset.officeAction)officeAction(b.dataset.officeAction);};
 navigation.onclick=e=>{const b=e.target.closest('button');if(b?.dataset.officeCategory)officeHome(b.dataset.officeCategory);else if(b?.dataset.officeGroup)officeHome(officeSection,b.dataset.officeGroup);};
 $('officeBack').onclick=()=>officeHome(officeSection,officeGroup);
 new MutationObserver(()=>{if($('auth').hidden)return;officeSection='home';officeGroup='';officeOpenedAction='';$('officeWork').hidden=true;$('officeTiles').hidden=false;officeRender();}).observe($('auth'),{attributes:true,attributeFilter:['hidden']});
}
