"""Touch tools, permitted account management and receipt completion on isolated data."""
import json, os, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import open_checkout, office_setting
import server

f=CoordinatorFixture();out=Path('output/preview/desk-tools-completion');out.mkdir(parents=True,exist_ok=True)
def post(action,**data):
 code,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert code==200,(action,result);return result
try:
 post('settings',store='Thrift Mart · SAMPLE',tax_bps=700,confirmed=True)
 product=post('product-save',name='Hardback book',category='Books',price=200,taxable=True)['ids'][0]
 customer=post('thrift-customer-save',name='Sample Loyalty Customer',contact='228-555-0100',marketing=False)['customer']
 info=dict(app='pos',device='a'*32,version='1.22.0',configured=True,nonce='b'*64,computer=dict(id='c'*32,hostname='SAMPLE-DESK',macs=[],os='Windows fixture'))
 terminal=post('terminal-save',name='Thrift Mart Register 1',device='a'*32,enabled=True)
 assert f.call('computers/self',info)[0]==200
 assert f.call('computers/register',dict(id='c'*32,revision=0,name='Sample Touch Register',role='pos',app='pos',device='a'*32))[0]==200
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
  ctx=b.new_context(viewport={'width':1920,'height':1080},has_touch=True,reduced_motion='reduce')
  ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.operationCalls=[];window.printCalls=[];window.pywebview={api:{kiosk_info:async()=>fixtureInfo,terminal_info:async()=>fixtureInfo,open_operations:async t=>{operationCalls.push(t);return {ok:true}},request_exit:async()=>({error:"Fixture exit only"}),receipt_print:async(p,s,a)=>{printCalls.push({p,s,a});return {ok:true}}}};')
  origin=f'http://127.0.0.1:{f.port}';ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
  p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(origin+'/pos?kiosk=1')
  expect(p.locator('#nativeTerminalStatus')).to_contain_text('Registered')
  expect(p.locator('#deskLoyaltyCustomer')).to_be_hidden()
  p.locator('#thriftTools').tap();expect(p.locator('#deskThriftTags')).to_be_disabled();p.keyboard.press('Escape')
  p.locator('[data-pos-product="'+product+'"]').tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');p.wait_for_function('()=>!posBusy&&!writeCount')
  expect(p.locator('#deskLoyaltyCustomer')).to_be_visible();before=p.evaluate('JSON.stringify(posCurrent)')
  cancel=p.locator('#posDiscard').bounding_box();loyalty=p.locator('#deskLoyaltyCustomer').bounding_box();assert loyalty['y']>=cancel['y']+cancel['height']
  for width,height in [(1920,1080),(1366,768),(1024,768)]:
   p.set_viewport_size({'width':width,'height':height})
   for theme in ['classic-gray','midnight','glass-blue']:
    p.evaluate('(t)=>document.body.dataset.retailTheme=t',theme);p.locator('#thriftTools').tap();expect(p.locator('#deskThriftChoices')).to_be_visible()
    issues=p.evaluate('''()=>[...document.querySelectorAll('#deskThriftChoices button:not([hidden])')].flatMap(el=>{const r=el.getBoundingClientRect();return r.left<0||r.top<0||r.right>innerWidth||r.bottom>innerHeight||!el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))?[el.id]:[]})''');assert not issues,(width,theme,issues)
    if width==1920 and theme=='classic-gray':p.screenshot(path=str(out/'DESK-Thrift-Tools.png'))
    p.keyboard.press('Escape');expect(p.locator('#thriftTools')).to_be_focused()
   p.locator('#deskCreditToggle').tap();p.locator('#thriftTools').tap();expect(p.locator('#deskCreditChoices')).to_be_hidden();p.keyboard.press('Escape')
  p.set_viewport_size({'width':1920,'height':1080});p.evaluate("document.body.dataset.retailTheme='classic-gray'")
  p.locator('#thriftTools').tap();p.locator('#deskThriftDispatch').tap();p.wait_for_function('()=>operationCalls.length===1');assert p.evaluate('operationCalls[0]')=='reservations';assert p.evaluate('JSON.stringify(posCurrent)')==before
  p.locator('#deskLoyaltyCustomer').tap();expect(p.locator('#thriftCustomerSearch')).to_be_visible();p.locator('#thriftCustomerSearch [name=search]').fill('Sample Loyalty');p.locator('#thriftCustomerSearch button').tap();p.locator('[data-select-customer]').tap();p.wait_for_function('(id)=>posCurrent.customer===id',arg=customer['id']);p.wait_for_function('()=>!posBusy&&!writeCount')
  p.screenshot(path=str(out/'DESK-Loyalty-Shortcut.png'))
  p.locator('#deskCreditToggle').tap();p.locator('#creditOpen').tap();p.locator('#creditCreateDetails summary').tap();p.locator('#creditCreate [name=name]').fill('Sample Credit Account');p.locator('#creditCreate button').first.tap();expect(p.locator('#creditSummary')).to_contain_text('Sample Credit Account')
  p.locator('#creditAdjust [name=amount]').fill('12.50');p.locator('#creditAdjust [name=reason]').fill('Sample approved adjustment');p.locator('#creditAdjust button').first.tap();expect(p.locator('.creditBalance')).to_contain_text('$12.50');expect(p.locator('#creditHistory')).to_contain_text('Sample approved adjustment');p.wait_for_function('()=>!posBusy&&!writeCount');p.screenshot(path=str(out/'DESK-Credit-Management.png'));p.locator('#creditClose').tap()
  # A missing printer requires acknowledgement; it never undoes the payment.
  open_checkout(p,touch=True,acknowledge_missing_printer=False);p.locator('[data-tender=exact]').tap();p.locator('#checkoutComplete').tap();expect(p.locator('#receiptNoPrinterOkay')).to_be_visible();p.screenshot(path=str(out/'DESK-No-Printer.png'));p.wait_for_timeout(5300);expect(p.locator('#posReceipt')).to_be_visible()
  p.locator('#receiptNoPrinterOkay').tap();expect(p.locator('#receiptResetNotice')).to_contain_text('5 seconds');expect(p.locator('#posReceipt')).to_be_hidden(timeout=8000);expect(p.locator('#deskLoyaltyCustomer')).to_be_hidden();expect(p.locator('#posPrintLast')).to_be_enabled()
  with server.connect() as c:assert c.execute('SELECT count(*) FROM pos_sales').fetchone()[0]==1
  # Timing is configured per store in OFFICE and read by every register.
  office=ctx.new_page();office.goto(origin+'/office');office_setting(office,'receipt-completion').click();expect(office.locator('#receiptCompletionSettings [name=seconds]')).to_have_value('5');office.locator('#receiptCompletionSettings [name=seconds]').fill('2');office.screenshot(path=str(out/'OFFICE-Receipt-Timing.png'));office.locator('#receiptCompletionSettings button').click();expect(office.locator('#receiptCompletionSettings')).to_have_count(0);office.close();p.bring_to_front()
  options=f.call('pos/terminal-options?device='+'a'*32)[1];post('terminal-options-save',device='a'*32,revision=options['revision'],printer='Sample Receipt Printer');p.evaluate('loadTerminalDevices()')
  p.locator('[data-pos-product="'+product+'"]').tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');p.wait_for_function('()=>!posBusy&&!writeCount&&!flowProductStarting');open_checkout(p,touch=True);p.locator('[data-tender=exact]').tap();p.locator('#checkoutComplete').tap();expect(p.locator('#receiptResetNotice')).to_be_visible();p.wait_for_function('()=>printCalls.length===1');assert p.evaluate('printCalls[0].a')
  # A new transaction must not be cleared by the old receipt's timer.
  p.locator('[data-pos-product="'+product+'"]').tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');p.wait_for_function('()=>!posBusy&&!writeCount');next_cart=p.evaluate('JSON.stringify(posCurrent)');p.wait_for_timeout(2800);assert p.evaluate('JSON.stringify(posCurrent)')==next_cart
  open_checkout(p,touch=True);p.locator('[data-tender=exact]').tap();p.locator('#checkoutComplete').tap();expect(p.locator('#receiptResetNotice')).to_be_visible();p.locator('#posFindCart').tap();p.wait_for_timeout(2800);expect(p.locator('#posReceipt')).to_be_visible();p.locator('dialog[open] .flowClose').tap();expect(p.locator('#posReceipt')).to_be_hidden(timeout=6000)
  with server.connect() as c:assert c.execute('SELECT count(*) FROM pos_sales').fetchone()[0]==3
  ops=ctx.new_page();ops.goto(origin+'/#pos-reservations');expect(ops.locator('#returnNativePos')).to_have_text('Return to DESK');assert ops.locator('.posNativeToolbar').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(173, 23, 53)';ops.screenshot(path=str(out/'STORE-OPS-DESK-Return-Bar.png'));ops.locator('#returnNativePos').click();ops.wait_for_function('()=>operationCalls.includes("pos")')
  # Ordinary browser / STORE OPS contexts never get DESK's return or exit bar.
  ordinary=b.new_context();q=ordinary.new_page();q.goto(origin+'/');expect(q.locator('.posNativeToolbar')).to_have_count(0)
  assert f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True,'use_store_credit':True,'view_schedule':False,'view_pos_sales':False,'manage_store_credit':False},can_create=False,see_requests=False))[0]==200
  ordinary.request.post(origin+'/api/login',data={'name':'Employee','password':'testpassword'},headers={'X-Dispatch':'1'});q.goto(origin+'/pos');q.locator('#thriftTools').click();expect(q.locator('#deskThriftDispatch')).to_be_hidden();expect(q.locator('#deskThriftSold')).to_be_hidden();q.keyboard.press('Escape');q.locator('#deskCreditToggle').click();q.locator('#creditOpen').click();expect(q.locator('#creditCreateDetails')).to_be_hidden();q.locator('[data-credit]').first.click();expect(q.locator('#creditAdjust')).to_be_hidden()
  assert not errors,errors;b.close()
finally:
 if 'errors' in globals() and errors:print('Browser errors:',errors,flush=True)
 f.close()
print('PASS thrift menus, loyalty, preserved carts, permitted credit edits, receipt acknowledgement/printing/reset, store timing and DESK-only red return bar')
