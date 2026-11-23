"""Touch checkout acceptance and previews; isolated data, no outgoing email or payment provider."""
import os,json,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_ui_helpers import open_checkout
from test_update_coordination import CoordinatorFixture
import server
from test_theme_contrast import AUDIT
f=CoordinatorFixture();out=Path(os.environ.get('TEST_ARTIFACTS','output/preview/checkout'));out.mkdir(parents=True,exist_ok=True)
def post(action,**data):
 code,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert code==200,(action,result);return result
try:
 post('settings',store='Thrift Mart · SAMPLE',tax_bps=700,confirmed=True)
 policy=f.call('pos/policies')[1]['policy'];post('policies-save',**dict(policy,cash_rounding='nearest5'))
 settings=f.call('pos/checkout-settings')[1]['settings']
 settings['presets']=[dict(id=mode+scope,name=name,mode=mode,scope=scope,kind='percent',value=amount) for mode,scope,name,amount in [('discount','item','Item markdown',1000),('discount','transaction','Member savings',1000),('surcharge','item','Item service',500),('surcharge','transaction','Service charge',500)]]
 post('checkout-settings-save',**settings)
 products=[]
 for name,price,group,rules in [('Hardback book',200,'Books',{}),('Clothes & accessories',0,'Clothes',{'open_priced':True}),('Table lamp',899,'Household',{}),('Magazine',75,'Books',{}),('Furniture',0,'Furniture',{'open_priced':True}),('Custom shirt',800,'Clothes',{}),('Records',149,'Media',{}),('Toys',0,'Toys',{'open_priced':True})]:
  products.append(post('product-save',name=name,category=group,price=max(1,price),taxable=True,rules=rules)['ids'][0])
 account=post('account-create',kind='customer',name='Sample customer',contact='')['account'];post('account-adjust',account=account['id'],account_revision=account['revision'],amount=500,direction='add',reason='Sample balance')
 info=dict(app='pos',device='a'*32,version='1.18.0',configured=True,nonce='b'*64,computer=dict(id='c'*32,hostname='SAMPLE-TOUCH-PC',macs=[],os='Windows fixture'))
 post('terminal-save',name='Thrift Mart Register 1',device='a'*32,enabled=True)
 assert f.call('computers/self',info)[0]==200
 assert f.call('computers/register',dict(id='c'*32,revision=0,name='Sample Touch Register',role='pos',app='pos',device='a'*32))[0]==200
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' if os.name=='nt' else None));ctx=b.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,has_touch=True,reduced_motion='reduce')
  ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.printCalls=[];window.pywebview={api:{kiosk_info:async()=>window.fixtureInfo,terminal_info:async()=>window.fixtureInfo,desktop_update_status:async()=>({available:true,message:"An update is available. Restart CoastYouth Retail "+(location.pathname==="/office"?"OFFICE":"DESK")+" to install it."}),receipt_printers:async()=>({printers:["Sample Receipt Printer"]}),receipt_print:async(p,s,a)=>{window.printCalls.push({printer:p,sale:s,automatic:a});return {ok:true}},request_exit:async()=>({error:"Fixture exit verified"})}};')
  origin=f'http://127.0.0.1:{f.port}';ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
  p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(origin+'/pos?kiosk=1');expect(p.locator('#nativeTerminalStatus')).to_contain_text('Registered');expect(p.locator('#navSales')).to_contain_text('OFF');assert not errors,errors
  def product(i):return p.locator('[data-pos-product="'+products[i]+'"]')
  def settle():p.wait_for_function('()=>!posBusy&&!posPending&&!writeCount')
  p.locator('#deskSettings summary').tap();p.locator('#deskTerminalSettings').tap();expect(p.locator('#terminalDevices')).to_be_visible();p.locator('#terminalDevices [name=printer]').fill('Sample Receipt Printer');p.locator('#terminalDevices button').tap();expect(p.locator('#terminalDevices [readonly]')).not_to_have_value('Save to create this register’s display link');p.screenshot(path=str(out/'DESK-Terminal-Printer.png'));p.locator('dialog[open] .flowClose').tap()
  product(0).tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');settle();product(1).tap();expect(p.locator('.deskAmountPad')).to_be_visible()
  for key in '1000':p.locator('.deskAmountPad [data-key="'+key+'"]').tap()
  expect(p.locator('#deskKeypadValue')).to_have_value('10.00');p.screenshot(path=str(out/'DESK-Cents-Entry.png'));p.locator('.deskKeypadApply').tap();expect(p.locator('#posCart')).to_contain_text('Clothes & accessories');settle()
  p.locator('#posDiscard').tap();expect(p.locator('[data-cancel-reason]')).to_have_count(len(settings['reasons']));p.screenshot(path=str(out/'DESK-Cancel-Reasons.png'));p.locator('[data-cancel-reason]').first.tap();p.wait_for_function('()=>!posCurrent')
  p.locator('#navSales').tap();p.locator('#trainingConfirm').tap();expect(p.locator('#deskTrainingBanner')).to_be_visible();product(0).tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');settle();assert p.locator('#posPayNow').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(173, 23, 53)';p.screenshot(path=str(out/'DESK-Training-1920.png'))
  # The scheduled warning also fits the register while a practice sale remains saved.
  warning=ctx.new_page();warning.add_init_script("sessionStorage.setItem('yfc-pos-selected:Admin',"+json.dumps(p.evaluate('posCurrent.id'))+");");warning.route('**/api/maintenance',lambda route:route.fulfill(json={'time':'2026-11-15T03:55:00-06:00'}));warning.goto(origin+'/pos?kiosk=1');expect(warning.locator('#serverMaintenanceBanner')).to_be_visible();expect(warning.locator('#posCart')).to_contain_text('Hardback book');warning.screenshot(path=str(out/'DESK-Overnight-Warning.png'));box=warning.locator('#posPayNow').bounding_box();assert box and box['y']+box['height']<=1080,box;warning.close()
  # Bottom-right payment button must remain reachable at 1080p with update notices.
  box=p.locator('#posPayNow').bounding_box();assert box and box['y']+box['height']<=1080,box
  open_checkout(p,touch=True);p.locator('[data-tender=exact]').tap();p.locator('#checkoutComplete').tap();p.wait_for_function('()=>!receiptPrintBusy&&printCalls.length===1');assert p.evaluate('printCalls[0].automatic')
  with server.connect() as c:assert c.execute('SELECT count(*) FROM pos_sales').fetchone()[0]==0;assert c.execute('SELECT count(*) FROM retail_training_transactions').fetchone()[0]==1
  p.evaluate('posReceipt(posLastReceipt)');p.wait_for_timeout(200);assert p.evaluate('printCalls.length')==1
  p.locator('#deskCreditToggle').tap();expect(p.locator('#deskCreditChoices')).to_be_visible();p.locator('#posStatus').tap();expect(p.locator('#deskCreditChoices')).to_be_hidden()
  display=f.call('pos/store-display?store_id=thrift-mart')[1];post('store-display-save',store_id='thrift-mart',revision=display['revision'],enabled=True,welcome='Welcome to Thrift Mart',thanks='Thank you for supporting our community')
  p.locator('#thriftTools').tap();p.locator('#deskThriftAddCustomer').tap();expect(p.locator('#customerTouchCreate')).to_be_visible();p.locator('#customerSendForm').tap();expect(p.locator('#customerEntryState')).to_contain_text('Waiting for the customer')
  link=f.call('pos/terminal-options?device='+'a'*32)[1]['display_path'];guest=b.new_context(viewport={'width':1920,'height':1080},has_touch=True);customer=guest.new_page();customer.goto(origin+link);expect(customer.locator('#customerEntry')).to_be_visible();expect(customer.locator('#storeTitle')).to_contain_text('Thrift Mart')
  customer.locator('[name=name]').fill('Sample Customer');customer.locator('[name=phone]').fill('2285550100');customer.locator('[name=email]').fill('sample@example.com');customer.screenshot(path=str(out/'Customer-Touchscreen-Form.png'));customer.locator('#customerEntryForm button').tap();expect(customer.locator('#customerEntryDone')).to_be_visible();expect(p.locator('#customerTouchCreate [name=name]')).to_have_value('Sample Customer',timeout=10000);p.screenshot(path=str(out/'DESK-Customer-Review.png'));p.locator('#customerTouchCreate button.primary').tap();expect(p.locator('#customerTouchCreate')).to_have_count(0)
  with server.connect() as c:assert c.execute('SELECT count(*) FROM thrift_customers').fetchone()[0]==0
  guest.close()
  # A failed printer must retain the paid transaction and allow deliberate reprint.
  p.evaluate('()=>{window.pywebview.api.receipt_print=async()=>({error:"Sample printer unavailable. Transaction saved."})}');product(0).tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');settle();open_checkout(p,touch=True);p.locator('[data-tender=exact]').tap();p.locator('#checkoutComplete').tap();expect(p.locator('#posReceipt [role=alert]')).to_contain_text('Sample printer unavailable');p.wait_for_function('()=>!receiptPrintBusy')
  with server.connect() as c:assert c.execute('SELECT count(*) FROM pos_sales').fetchone()[0]==0;assert c.execute('SELECT count(*) FROM retail_training_transactions').fetchone()[0]==2
  p.evaluate('()=>{window.pywebview.api.receipt_print=async(p,s,a)=>{printCalls.push({printer:p,sale:s,automatic:a});return {ok:true}}}');p.locator('#posPrintLast').tap();p.wait_for_function('()=>!receiptPrintBusy&&printCalls.length===2');assert p.evaluate('printCalls[1].automatic') is False

  p.goto(origin+'/office');p.wait_for_function('()=>!!user');p.evaluate('officeAction("computer-updates")');expect(p.locator('#computerRows')).to_contain_text('1.18.0');expect(p.locator('#computerRollout')).to_have_count(0);p.screenshot(path=str(out/'OFFICE-Installed-Versions.png'));p.locator('dialog[open] .flowClose').tap();p.evaluate('officeAction("training-report")');expect(p.locator('#trainingReportRows')).to_contain_text('2 practice transactions');p.screenshot(path=str(out/'OFFICE-Training-Report.png'));assert not errors,errors
  assert f.call('admin/clock-pin',{'name':'Admin','pin':'654321'})[0]==200
  ctx.clear_cookies();p.goto(origin+'/pos?kiosk=1');expect(p.locator('#deskPinForm [name=pin]')).to_be_focused();p.locator('#deskPinForm [name=pin]').fill('654321');p.locator('#deskPinForm [name=pin]').press('Enter');expect(p.locator('#auth')).to_be_hidden();b.close()
finally:f.close()
print('PASS: touch cents, cancellation list, training isolation, printer routing, popup menus and inventory previews')
