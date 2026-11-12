// DESK touch controls; OFFICE and printed receipts retain their own layouts.
function deskQuantityControl(line,index){
 if(officeMode)return String(line.quantity);
 const special=line.weight_milli?'By weight':line.intake?'Single item':line.gift_certificate||line.donation?'Fixed amount':'';
 if(special)return `<span class="deskFixedQuantity">${line.quantity}<small>${special}</small></span>`;
 const locked=posBusy||!!posPending||posCurrent?.held||posCurrent?.reward||posCurrent?.adjustment;
 return `<div class="deskQuantity" aria-label="Quantity for ${esc(line.name)}"><button type="button" data-desk-quantity="${index}" data-step="-1" aria-label="Decrease quantity of ${esc(line.name)}" ${locked||line.quantity<=1?'disabled':''}>−</button><output aria-live="polite">${line.quantity}</output><button type="button" data-desk-quantity="${index}" data-step="1" aria-label="Increase quantity of ${esc(line.name)}" ${locked||line.quantity>=999?'disabled':''}>+</button></div>`;
}
(function(){
 if(officeMode)return;
 document.body.classList.add('deskTouch');
 const status=document.getElementById('posStatus'),actions=document.querySelector('#posPanel>.actions');
 const statusRow=document.createElement('div');statusRow.className='deskStatusRow';status.before(statusRow);statusRow.append(status,actions);document.getElementById('posHistory').hidden=true;
 let scheduled=false;
 const scrollTargets={groups:()=>document.getElementById('posCategories'),products:()=>document.getElementById('posCatalog'),receipt:()=>document.querySelector('#posCart .receiptLines')};
 const labels={groups:'Groups',products:'Products',receipt:'Receipt'};
 function scrollBar(kind,target){
  if(!target)return;
  let bar=document.querySelector(`[data-desk-scrollbar="${kind}"]`);
  if(!bar){
   bar=document.createElement('div');bar.className='deskScroll';bar.dataset.deskScrollbar=kind;
   bar.innerHTML=`<button type="button" data-scroll-direction="-1" aria-label="Scroll ${labels[kind].toLowerCase()} up"><span aria-hidden="true">▲</span> Up</button><button type="button" data-scroll-direction="1" aria-label="Scroll ${labels[kind].toLowerCase()} down"><span aria-hidden="true">▼</span> Down</button>`;
   target.after(bar);
   bar.onclick=e=>{const button=e.target.closest('[data-scroll-direction]'),area=scrollTargets[kind]();if(!button||!area)return;area.scrollBy({top:Number(button.dataset.scrollDirection)*Math.max(100,area.clientHeight*.7),behavior:'auto'});refreshScroll();};
  }
  bar.hidden=target.scrollHeight<=target.clientHeight+2;
  bar.querySelector('[data-scroll-direction="-1"]').disabled=target.scrollTop<=1;
  bar.querySelector('[data-scroll-direction="1"]').disabled=target.scrollTop+target.clientHeight>=target.scrollHeight-2;
 }
 function refreshScroll(){for(const [kind,get]of Object.entries(scrollTargets))scrollBar(kind,get());}
 function fieldName(input){
  return input.getAttribute('aria-label')||[...(input.labels||[])].map(label=>[...label.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ')).filter(Boolean).join(' ')||'Enter value';
 }
 function addKeypads(){
  for(const input of document.querySelectorAll('#posManual input[type=number],#posCash input[type=number],#flowChoices input[type=number],#storeWeight input[type=number],#creditPay input[type=number],#checkoutPaymentForm input[type=number],#cashAdvanceForm input[type=number]')){
   if(input.classList.contains('deskKeypadInput')||input.closest('#posAdmin')||input.closest('#posSetup')||input.hidden||!input.parentElement.matches('label'))continue;
   // Keep the input mounted: moving a focused number field can interrupt typed input.
   input.classList.add('deskKeypadInput');input.parentElement.classList.add('deskNumberLabel');
   input.inputMode=input.step&&input.step!=='1'?'decimal':'numeric';
   const button=document.createElement('button');button.type='button';button.className='deskKeypadOpen';button.textContent='Keypad';button.setAttribute('aria-label','Open keypad for '+fieldName(input));input.after(button);
   button.onclick=e=>{e.preventDefault();if(!input.disabled&&!input.readOnly)openKeypad(input);};
   if(input.id==='flowOpenPrice')openKeypad(input);
  }
 }
 function openKeypad(input){
  const name=fieldName(input),decimal=input.step==='any'||(input.step&&Number(input.step)%1!==0);
  const dialog=flowModal(name,`<form id="deskAmountEntry"><label class="deskKeypadLabel">${esc(name)}<input id="deskKeypadValue" name="value" type="text" inputmode="${decimal?'decimal':'numeric'}" autocomplete="off"></label></form><p class="deskKeypadError" role="alert"></p><div class="deskKeypadGrid">${['7','8','9','4','5','6','1','2','3','clear','0',decimal?'.':'back'].map(key=>`<button type="button" data-key="${key}" aria-label="${key==='clear'?'Clear entry':key==='back'?'Backspace':key==='.'?'Decimal point':key}">${key==='clear'?'Clear':key==='back'?'⌫':key}</button>`).join('')}</div><div class="deskKeypadActions">${decimal?'<button type="button" data-key="back" aria-label="Backspace">⌫ Backspace</button>':''}<button type="button" class="deskKeypadCancel">Cancel</button><button type="button" class="primary deskKeypadApply">Use value</button></div>`);
  dialog.classList.add('deskAmountPad');const value=dialog.querySelector('#deskKeypadValue'),error=dialog.querySelector('.deskKeypadError');value.value=input.value;const entry=dialog.querySelector("#deskAmountEntry");entry.onsubmit=e=>{e.preventDefault();apply();};changedForms.set(entry,snapshot(entry));value.focus();value.select();
  const openPrice=input.id==='flowOpenPrice',choiceForm=input.form,parentDialog=input.closest('dialog'),moved=[];
  if(openPrice){
   dialog.querySelector('.deskKeypadApply').textContent='Okay · Add to sale';
   for(const select of choiceForm.querySelectorAll('select')){const label=select.closest('label'),marker=document.createComment('choice');label.before(marker);moved.push([label,marker]);entry.append(label);}
   dialog.onDismiss=()=>{if(value.value.trim())input.value=value.value;for(const [label,marker]of moved)marker.replaceWith(label);parentDialog.querySelector('.flowClose').click();};
  }
  const cancel=()=>dialog.querySelector('.flowClose').click();dialog.querySelector('.deskKeypadCancel').onclick=cancel;
  dialog.querySelectorAll('[data-key]').forEach(button=>button.onclick=()=>{
   const key=button.dataset.key,start=value.selectionStart??value.value.length,end=value.selectionEnd??start;
   if(key==='clear'){value.value='';value.dispatchEvent(new Event('input',{bubbles:true}));value.focus();return;}
   let text=value.value,position=start;
   if(key==='back'){text=text.slice(0,start===end?Math.max(0,start-1):start)+text.slice(end);position=start===end?Math.max(0,start-1):start;}
   else{text=text.slice(0,start)+key+text.slice(end);position=start+key.length;}
   if(text.length<=16&&new RegExp(decimal?'^\\d*(\\.\\d*)?$':'^\\d*$').test(text)){value.value=text;value.dispatchEvent(new Event('input',{bubbles:true}));value.focus();value.setSelectionRange(position,position);error.textContent='';}
  });
  function apply(){
   if(!input.isConnected||input.disabled||input.readOnly){error.textContent='This field is no longer available. Close the keypad and reopen the item.';return;}
   const text=value.value.trim(),check=input.cloneNode();check.required=true;check.value=text;
   if(!text||!new RegExp(decimal?'^\\d+(\\.\\d+)?$':'^\\d+$').test(text)||!check.checkValidity()){error.textContent=check.validationMessage||'Enter a valid value for this field.';return;}
   if(openPrice&&!entry.reportValidity())return;
   for(const [label,marker]of moved)marker.replaceWith(label);
   input.value=text;input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));changedForms.delete(entry);dialog.close();dialog.remove();if(openPrice)choiceForm.requestSubmit();else input.focus();
  }
  dialog.querySelector('.deskKeypadApply').onclick=apply;value.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();apply();}};
 }
 document.getElementById('posCart').addEventListener('click',async e=>{
  const b=e.target.closest('[data-desk-quantity]');if(!b)return;
  if(!posCurrent||posBusy||posPending||writeCount){posMessage('Please finish the current save before changing quantity.');return;}
  if(changedForms.has(document.getElementById('posCash'))){posMessage('Finish or clear the cash entry before changing quantities.');return;}
  const index=Number(b.dataset.deskQuantity),line=posCurrent.lines[index];if(!line)return;
  await posCartAction('quantity',{index,quantity:line.quantity+Number(b.dataset.step)});
 });
 function scan(){scheduled=false;addKeypads();refreshScroll();}
 function schedule(){if(!scheduled){scheduled=true;requestAnimationFrame(scan);}}
 new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
 window.addEventListener('resize',schedule);document.addEventListener('scroll',schedule,true);
 scan();
})();
