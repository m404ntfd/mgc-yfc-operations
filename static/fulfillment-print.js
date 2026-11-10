// Shared DESK / STORE OPS printing of the saved sale and saved sold slip.
function fulfillmentEscape(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fulfillmentMoney(v){return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(v/100);}
function fulfillmentLine(l){return fulfillmentEscape(l.name)+(l.weight_milli?` · ${(l.weight_milli/1000).toFixed(3)} lb × ${fulfillmentMoney(l.price_per_lb)}/lb`:'');}
function fulfillmentSlipMarkup(p,sale){
 const e=fulfillmentEscape;
 return ['CUSTOMER PICKUP SLIP','SOLD · HOLD FOR CUSTOMER'].map(title=>`<section class="fulfillmentTicket"><h1>${title}</h1><h2>${e(sale.settings.store)}</h2><h3>Receipt #${p.sale}</h3><p>${e(p.customer)} · ${e(p.contact)}</p><p>Storage: ${e(p.location)} · Due: ${e(p.due)}</p><p>Status: ${e(p.status.replaceAll('_',' '))}</p><ul>${sale.lines.filter(l=>!l.donation&&!l.gift_certificate).map(l=>`<li>${l.quantity} × ${fulfillmentLine(l)}</li>`).join('')}</ul><p>${e(p.notes)}</p><p>Dispatch: ${e(p.dispatch_reference||'Not scheduled')}</p></section>`).join('');
}
function fulfillmentReceiptMarkup(s){
 const e=fulfillmentEscape,m=fulfillmentMoney,r=s.receipt_design||{};
 return `<section>${r.logo?`<img alt="Store logo" style="max-width:160px" src="${e(r.logo)}">`:''}<h1>${e(s.settings.store)}</h1><p>${e(r.address)}<br>${e(r.phone)}</p><h2>Receipt #${s.id}</h2><p>${e(s.at)} · ${e(s.cashier)}</p><table><thead><tr><th>Item</th><th>Qty</th><th>Amount</th></tr></thead><tbody>${s.lines.map(l=>`<tr><td>${fulfillmentLine(l)}</td><td>${l.quantity}</td><td>${m(l.subtotal)}</td></tr>`).join('')}</tbody></table><p>Subtotal: ${m(s.subtotal)}<br>Tax: ${m(s.tax)}<br><strong>Total: ${m(s.total)}</strong><br>${s.store_credit?`Store credit: ${m(s.store_credit)} · ${e(s.credit_account)}<br>`:''}Cash received: ${m(s.tender)}<br>Change: ${m(s.change)}${s.cash_rounding?'<br>Cash rounding: '+m(s.cash_rounding):''}</p><p>${e(r.policy)}</p><p>${e(r.footer)}</p></section>`;
}
function fulfillmentPrint(title,html){
 if(window.pywebview){
  const frame=document.createElement('iframe');frame.title=title;frame.style.cssText='position:fixed;width:1px;height:1px;left:-10000px;border:0';
  frame.onload=async()=>{try{await Promise.all([...frame.contentDocument.images].map(img=>img.decode().catch(()=>{})));frame.contentWindow.focus();frame.contentWindow.print();}catch(e){alert('Unable to print. Please try again.');}finally{setTimeout(()=>frame.remove(),60000);}};
  frame.srcdoc='<!doctype html><html><head><title>'+fulfillmentEscape(title)+'</title><style>body{font:16px Arial;padding:24px;color:#111;background:white}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}.fulfillmentTicket+ .fulfillmentTicket{break-before:page}p{white-space:pre-line}</style></head><body>'+html+'</body></html>';
  document.body.append(frame);return true;
 }
 const w=window.open('','_blank');if(!w)return false;
 w.document.write('<!doctype html><html><head><title>'+fulfillmentEscape(title)+'</title><style>body{font:16px Arial;padding:24px;color:#111;background:white}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}.fulfillmentTicket+ .fulfillmentTicket{break-before:page}p{white-space:pre-line}</style></head><body>'+html+'</body></html>');w.document.close();w.focus();w.print();return true;
}
