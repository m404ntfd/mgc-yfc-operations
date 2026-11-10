let catalogOptions=null;
const catalogSetupSections={
 revenue_centers:{title:'Revenue Centers',description:'Create the revenue centers used for sales reporting.',action:'revenue-centers',parent:null},
 departments:{title:'Departments',description:'Assign each Department to its reporting Revenue Center.',action:'departments',parent:'revenue_centers',parentKey:'revenue_center_id',parentLabel:'Revenue Center'},
 sub_departments:{title:'Sub Departments',description:'Organize products and assign each Sub Department to a Department.',action:'sub-departments',parent:'departments',parentKey:'department_id',parentLabel:'Department'},
 printing:{title:'Printing categories',description:'Configure the printing choices available in product setup.',action:'printing-categories'},
 taxes:{title:'Taxes',description:'Configure named taxes and rates separately for each store.',action:'taxes'}
};
for(const info of Object.values(catalogSetupSections))officeCards.push({section:'sales',action:info.action,title:info.title,description:info.description,permission:'manage_pos',icon:'▤'});
const catalogOfficeAction=officeAction;
officeAction=async function(action){const entry=Object.entries(catalogSetupSections).find(([key,value])=>value.action===action);if(entry||action==='catalog-options')return catalogOptionsEditor(entry?.[0]||'sub_departments');return catalogOfficeAction(action);};
const catalogProductEditor=flowProductEditor;
flowProductEditor=function(){catalogProductEditor();const f=$('flowProductForm');if(!f||!catalogOptions)return;
 for(const [key,values,empty] of [['category',catalogOptions.sub_departments.map(x=>({value:x.key,label:x.name})),false],['print_category',catalogOptions.printing.map(x=>({value:x,label:x})),true]]){const old=f.elements[key],select=document.createElement('select');select.name=key;select.required=!empty;select.innerHTML=(empty?'<option value="">No printing category</option>':'<option value="">Choose a Sub Department</option>')+values.map(x=>`<option value="${esc(x.value)}">${esc(x.label)}</option>`).join('');select.value=old.value;old.replaceWith(select);}
 const assignment=document.createElement('p');assignment.className='catalogAssignment';f.elements.category.closest('label').after(assignment);
 const showAssignment=()=>{const sub=catalogOptions.sub_departments.find(x=>x.key===f.elements.category.value),dept=catalogOptions.departments.find(x=>x.id===sub?.department_id),center=catalogOptions.revenue_centers.find(x=>x.id===dept?.revenue_center_id);assignment.textContent='Reports to: '+(dept?.name||'Unassigned Department')+' → '+(center?.name||'Unassigned Revenue Center');};showAssignment();f.elements.category.addEventListener('change',showAssignment);
 const old=f.elements.taxable;old.closest('label').hidden=true;let box=document.createElement('details');box.className='taxDropdown';box.innerHTML='<summary>Taxes — select one or more</summary><div></div>';old.closest('label').after(box);
 const render=()=>{const ids=flowProduct.rules.tax_ids??(flowProduct.taxable?['legacy']:[]);box.querySelector('div').innerHTML=[{id:'legacy',name:'Store default tax',bps:null},...catalogOptions.taxes.filter(t=>t.store_id===f.elements.store_id.value)].map(t=>`<label><input type="checkbox" data-item-tax value="${esc(t.id)}" ${ids.includes(t.id)?'checked':''}> ${esc(t.name)}${t.bps===null?'':' ('+(t.bps/100)+'%)'}</label>`).join('')+'<small>No selection = non-taxable. Store default cannot combine with named taxes.</small>';};render();
 box.onchange=e=>{if(e.target.checked){for(const x of box.querySelectorAll('[data-item-tax]'))if(x!==e.target&&(e.target.value==='legacy'||x.value==='legacy'))x.checked=false;}old.checked=!!box.querySelector(':checked');};f.elements.store_id.addEventListener('change',()=>{flowProduct.rules.tax_ids=[];render();old.checked=false;});
};
// Shared form/list interaction for configuration records. Copy always creates a new identity.
const setupActionIcons={
 delete:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 10v7m4-7v7"/></svg>',
 copy:'<span aria-hidden="true">x2</span>',
 edit:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 16 11-11 4 4L8 20H4v-4Zm9-9 4 4m-2-6 2-2 4 4-2 2"/></svg>'
};
function setupCopyName(name,rows,limit=60){let n=1,value;do{const suffix=n===1?' (copy)':' (copy '+n+')';value=name.slice(0,limit-suffix.length)+suffix;n++;}while(rows.some(x=>x.name?.toLocaleLowerCase()===value.toLocaleLowerCase()));return value;}
function setupListEditor(root,config){
 let rows=structuredClone(config.rows),selected=-1,editing=-1,busy=false,draft=null;
 root.classList.add('setupListEditor');root.innerHTML=`<form id="${config.formId||'setupEntryForm'}" class="setupEntryForm"><fieldset class="setupEntryFields"><legend class="setupEntryHeading"></legend><div class="setupFields"></div><div class="flowToolbar"><button type="submit" class="primary setupSubmit">Add</button><button type="button" class="setupCancel">Clear</button></div></fieldset></form><section class="setupSavedList" aria-label="${esc(config.plural)}"><div class="setupListHeading"><h3>${esc(config.plural)}</h3><div class="setupActions" role="group" aria-label="Selected item actions">${['delete','copy','edit'].map(action=>`<button type="button" data-setup-action="${action}" aria-label="${action==='copy'?'Copy':action==='edit'?'Edit':'Delete'} selected ${esc(config.singular)}" title="${action==='copy'?'Copy (x2)':action==='edit'?'Edit':'Delete'}" disabled>${setupActionIcons[action]}</button>`).join('')}</div></div><p class="setupSelectionHint">Select a row, then choose delete, copy, or edit.</p><div class="setupTableScroll"><table class="setupTable"><thead><tr><th scope="col"><span class="setupSrOnly">Selected</span></th>${config.columns.map(x=>`<th scope="col">${esc(x.title)}</th>`).join('')}</tr></thead><tbody></tbody></table></div></section><p id="${config.statusId||'setupListStatus'}" class="setupStatus" role="status" aria-live="polite"></p>`;
 const form=root.querySelector('form'),fields=root.querySelector('.setupFields'),status=root.querySelector('.setupStatus');
 const message=(text,error=false)=>{status.textContent=text;status.classList.toggle('setupError',error);};
 const discard=()=>!changedForms.has(form)||confirm('Discard the unsaved '+config.singular+' details?');
 const renderList=()=>{
  root.querySelector('tbody').innerHTML=rows.length?rows.map((row,i)=>`<tr data-setup-row="${i}" tabindex="0" aria-selected="${i===selected}"><td class="setupSelectedMark" aria-label="${i===selected?'Selected':'Not selected'}">${i===selected?'✓':''}</td>${config.columns.map(column=>`<td>${esc(column.value(row))}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${config.columns.length+1}">No entries yet. Complete the form above and click Add.</td></tr>`;
  for(const button of root.querySelectorAll('[data-setup-action]'))button.disabled=busy||selected<0;
  root.querySelector('.setupSelectionHint').textContent=selected<0?'Select a row, then choose delete, copy, or edit.':'Selected: '+config.label(rows[selected]);
 };
 const formValue=(row,mode='add')=>{editing=mode==='edit'?selected:-1;draft=structuredClone(row);fields.innerHTML=config.fields(row,mode);form.querySelector('legend').textContent=(mode==='edit'?'Edit ':mode==='copy'?'Copy ':'Add ')+config.singular;form.querySelector('.setupSubmit').textContent=mode==='edit'?'Save changes':'Add';form.querySelector('.setupCancel').textContent=mode==='add'?'Clear':'Cancel';changedForms.delete(form);if(mode==='copy')changedForms.set(form,'copy awaiting Add');config.afterRender?.(fields,row);};
 const setBusy=value=>{busy=value;form.querySelector('fieldset').disabled=value;renderList();root.setAttribute('aria-busy',String(value));};
 const select=i=>{selected=i;renderList();config.onSelect?.(rows[i]);};
 root.querySelector('tbody').onclick=e=>{const row=e.target.closest('[data-setup-row]');if(row&&!busy)select(Number(row.dataset.setupRow));};
 root.querySelector('tbody').onkeydown=e=>{const row=e.target.closest('[data-setup-row]');if(!row||busy)return;let i=Number(row.dataset.setupRow);if(['Enter',' ','ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();if(e.key==='ArrowDown')i=Math.min(rows.length-1,i+1);if(e.key==='ArrowUp')i=Math.max(0,i-1);if(e.key==='Home')i=0;if(e.key==='End')i=rows.length-1;select(i);root.querySelector(`[data-setup-row="${i}"]`).focus();}};
 for(const button of root.querySelectorAll('[data-setup-action]'))button.onclick=async()=>{
  if(busy||selected<0)return;const action=button.dataset.setupAction,item=rows[selected];if(!discard())return;
  if(action==='edit'){formValue(structuredClone(item),'edit');message('Editing '+config.label(item)+'.');fields.querySelector('input,select,textarea')?.focus();return;}
  if(action==='copy'){formValue(config.copy(structuredClone(item),rows),'copy');message('Review the copy, then click Add.');fields.querySelector('input,select,textarea')?.focus();return;}
  if(!confirm('Delete '+config.label(item)+'? Existing sales and history will remain unchanged.'))return;
  try{setBusy(true);const next=await config.remove(item,rows);rows=structuredClone(next);selected=-1;formValue(config.blank());message(config.label(item)+' deleted.');}catch(error){message(error.message,true);}finally{setBusy(false);}
 };
 form.querySelector('.setupCancel').onclick=()=>{if(busy||!discard())return;formValue(config.blank());message('Ready to add '+config.singular+'.');};
 form.onsubmit=async e=>{e.preventDefault();if(busy||!form.reportValidity())return;try{const item=config.read(form,editing<0?draft:rows[editing]);const operation=editing<0?'added':'updated';setBusy(true);const result=await config.save(item,editing,rows);rows=structuredClone(result.rows);selected=result.selected??(editing<0?rows.length-1:editing);formValue(config.blank());message(config.singular+' '+operation+'.');}catch(error){message(error.message,true);}finally{setBusy(false);}};
 formValue(config.blank());renderList();return {form,hasChanges:()=>changedForms.has(form),canClose:()=>!busy&&discard(),message,get rows(){return structuredClone(rows);}};
}
async function catalogOptionsEditor(section='sub_departments'){
 if(unfinished())return posMessage('Save or discard current work first.');
 let v;try{v=await api('pos/catalog-options');}catch(error){return posMessage(error.message);}
 catalogOptions=v;const info=catalogSetupSections[section],hierarchy=['revenue_centers','departments','sub_departments'].includes(section);
 const singular={revenue_centers:'Revenue Center',departments:'Department',sub_departments:'Sub Department',taxes:'tax',printing:'printing category'}[section];
 const d=flowModal(info.title,`<p>${esc(info.description)}</p><nav class="catalogSetupNav" aria-label="Catalog setup sections">${Object.entries(catalogSetupSections).map(([key,value])=>`<button type="button" data-catalog-section="${key}" aria-pressed="${section===key}">${esc(value.title)}</button>`).join('')}</nav>${hierarchy?'<p class="catalogHierarchyPath">Revenue Center <span>→</span> Department <span>→</span> Sub Department <span>→</span> Product</p>':''}<div id="catalogSetupEditor"></div>`);d.classList.add('catalogSetup');
 const readRows=()=>v[section].map(x=>typeof x==='string'?{name:x}:x);
 const saveRows=async rows=>{v=await retailSave('catalog-options-save',{revision:v.revision,section,[section]:section==='printing'?rows.map(x=>x.name):rows});catalogOptions=v;return readRows();};
 const columns=[{title:'Name',value:row=>row.name}];
 if(info.parent)columns.push({title:info.parentLabel,value:row=>v[info.parent].find(x=>x.id===row[info.parentKey])?.name||'Unassigned'});
 if(section==='sub_departments')columns.push({title:'Revenue Center',value:row=>v.revenue_centers.find(x=>x.id===v.departments.find(p=>p.id===row.department_id)?.revenue_center_id)?.name||'Unassigned'});
 if(section==='taxes')columns.push({title:'Rate',value:row=>(row.bps/100).toFixed(2)+'%'},{title:'Store',value:row=>retailStores.find(x=>x.id===row.store_id)?.name||row.store_id});
 const list=setupListEditor(d.querySelector('#catalogSetupEditor'),{singular,plural:info.title,formId:'catalogOptionsForm',statusId:'catalogSaved',rows:readRows(),columns,label:row=>row.name,
  blank:()=>({id:flowId(),name:'',bps:0,store_id:retailStoreChoice}),
  fields:(row,mode)=>`<label>Name<input name="entry_name" value="${esc(row.name)}" required maxlength="60"></label>${info.parent?`<label>${info.parentLabel}<select name="entry_parent" ${section==='sub_departments'&&mode==='edit'&&!row.department_id?'':'required'}><option value="">${section==='sub_departments'&&mode==='edit'&&!row.department_id?'Unassigned — choose a Department':'Choose a '+info.parentLabel}</option>${v[info.parent].map(parent=>`<option value="${esc(parent.id)}" ${parent.id===row[info.parentKey]?'selected':''}>${esc(parent.name)}</option>`).join('')}</select></label>`:''}${section==='taxes'?`<label>Rate (%)<input name="entry_rate" type="number" min="0" max="100" step="0.01" value="${row.bps/100}" required></label><label>Store<select name="entry_store">${retailStores.map(store=>`<option value="${esc(store.id)}" ${store.id===row.store_id?'selected':''}>${esc(store.name)}</option>`).join('')}</select></label>`:''}`,
  read:(form,old)=>{const f=form.elements;return {...old,id:old?.id||flowId(),name:f.entry_name.value.trim(),...(info.parent?{[info.parentKey]:f.entry_parent.value}:{}),...(section==='taxes'?{bps:posCents(f.entry_rate.value),store_id:f.entry_store.value}:{})};},
  copy:(row,rows)=>({...row,id:flowId(),key:undefined,name:setupCopyName(row.name,rows)}),
  save:async(item,index,rows)=>{if(rows.some((x,i)=>i!==index&&x.name.toLocaleLowerCase()===item.name.toLocaleLowerCase()&&(section!=='taxes'||x.store_id===item.store_id)))throw Error('An entry with this name already exists. Choose a different name.');const next=rows.slice();if(index<0)next.push(item);else next[index]=item;return {rows:await saveRows(next),selected:index<0?next.length-1:index};},
  remove:async(item,rows)=>saveRows(rows.filter(x=>x!==item))
 });
 const close=()=>{if(!list.canClose())return;changedForms.delete(list.form);d.close();d.remove();};d.querySelector('.flowClose').onclick=close;d.oncancel=e=>{e.preventDefault();close();};
 for(const button of d.querySelectorAll('[data-catalog-section]'))button.onclick=()=>{if(!list.canClose())return;changedForms.delete(list.form);d.close();d.remove();catalogOptionsEditor(button.dataset.catalogSection);};
 if(info.parent&&!v[info.parent].length)list.message('Create '+catalogSetupSections[info.parent].title+' first using the setup menu above.');
}
let catalogLeavePending=false;
document.addEventListener('click',e=>{const target=e.target.closest('[data-office-section],[data-office-action],#officeBack,.operationsLinks a,#signOut');const form=$('flowProductForm');if(!target||!form||!changedForms.has(form)||catalogLeavePending)return;e.preventDefault();e.stopImmediatePropagation();const d=flowModal('Finish this item?',`<p>Complete the item and save it, or discard your changes before moving to the next page.</p><div class="flowToolbar"><button id="itemKeepEditing">Keep editing</button><button id="itemSaveLeave">Save & continue</button><button id="itemDiscardLeave">Discard & continue</button></div>`);const close=()=>{d.close();d.remove();};$('itemKeepEditing').onclick=close;const go=()=>{close();catalogLeavePending=true;target.click();catalogLeavePending=false;};$('itemDiscardLeave').onclick=()=>{changedForms.delete(form);go();};$('itemSaveLeave').onclick=async()=>{if(!form.reportValidity()){close();return;}await form.onsubmit({preventDefault(){},target:form});if(!changedForms.has(form))go();else d.querySelector('.flowError').textContent=$('flowProductStatus').textContent;};},true);

const catalogFlowOffice=flowOffice;flowOffice=async function(action){if(['product-tools','bundles','availability'].includes(action))catalogOptions=await api('pos/catalog-options');return catalogFlowOffice(action);};
