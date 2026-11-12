"""Touch checkout acceptance and previews; isolated data, no outgoing email or payment provider."""
import os,json,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
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
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None);ctx=b.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,has_touch=True,reduced_motion='reduce')
  ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.exitCalls=0;window.pywebview={api:{kiosk_info:async()=>window.fixtureInfo,terminal_info:async()=>window.fixtureInfo,request_exit:async()=>{window.exitCalls++;return {error:"Fixture exit verified"}}}};')
  origin=f'http://127.0.0.1:{f.port}';ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
  p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(origin+'/pos?kiosk=1');expect(p.locator('#nativeTerminalStatus')).to_contain_text('Registered')
  def product(i):return p.locator('[data-pos-product="'+products[i]+'"]')
  def settle():p.wait_for_function('()=>!posBusy&&!posPending&&!writeCount')
  product(0).tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');settle()
  product(1).tap();expect(p.locator('.deskAmountPad')).to_be_visible()
  for key in '12.50':p.locator('.deskAmountPad [data-key="'+key+'"]').tap()
  p.screenshot(path=str(out/'DESK-Open-Price-Keypad.png'))
  p.locator('.deskKeypadApply').tap();expect(p.locator('#flowChoices')).to_have_count(0);expect(p.locator('#posCart')).to_contain_text('Clothes & accessories');settle()
  before=p.evaluate('JSON.stringify(posCurrent)');product(1).tap();p.locator('.deskKeypadCancel').tap();expect(p.locator('dialog[open]')).to_contain_text('Item not added');p.locator('[data-product-cancel-ok]').tap();assert p.evaluate('JSON.stringify(posCurrent)')==before
  p.locator('#flowAdjust').tap();expect(p.locator('.checkoutAdjustmentSection')).to_have_count(2);p.screenshot(path=str(out/'DESK-Discounts-Surcharges.png'));p.locator('[data-checkout-preset=discounttransaction]').tap();expect(p.locator('#posCart')).to_contain_text('$13.97');settle()
  p.locator('#checkoutPayLater').tap();p.wait_for_function('()=>!posCurrent');p.locator('#posFindCart').tap();p.locator('[data-saved-sale]').first.tap();p.locator('#checkoutResume').tap();expect(p.locator('#posCart')).to_contain_text('Hardback book');settle()
  p.screenshot(path=str(out/'DESK-Register-1920.png'))
  p.locator('#posPayNow').tap();expect(p.locator('#checkoutTender')).to_be_focused();assert p.locator('#checkoutDue').inner_text()=='$13.95'
  for key in '2000':p.locator('[data-money-key="'+key+'"]').tap()
  expect(p.locator('#checkoutTender')).to_have_value('20.00');expect(p.locator('#checkoutChange')).to_have_text('$6.05');p.screenshot(path=str(out/'DESK-Payment-Cash.png'))
  for theme in ['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+c for c in ['blue','teal','violet','rose','graphite']]:
   for mode in ['light','dark']:
    p.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode])
    issues=p.evaluate(AUDIT.replace('document.querySelectorAll(', 'document.querySelector(".checkoutDialog").querySelectorAll('));assert not issues,(theme,mode,issues)
  p.screenshot(path=str(out/'DESK-Payment-Dark.png'));p.evaluate("document.body.dataset.retailTheme='harbor-blue';document.documentElement.dataset.theme='light'")
  p.locator('[data-method=credit]').tap();p.locator('#checkoutAccount').select_option(str(account['id']));expect(p.locator('#checkoutCreditAmount')).to_have_value('5.00');expect(p.locator('#checkoutDue')).to_have_text('$8.95')
  p.locator('[data-tender=exact]').tap();p.screenshot(path=str(out/'DESK-Payment-Store-Credit.png'))
  # Drop the response after the server commits. Retry must not duplicate a sale or credit debit.
  def lost(route):route.fetch();route.abort();p.unroute('**/api/pos/credit',lost)
  p.route('**/api/pos/credit',lost);p.locator('#checkoutComplete').tap();expect(p.locator('#checkoutComplete')).to_have_text('Retry / check this payment');p.reload();expect(p.locator('#posReceipt')).to_contain_text('Receipt #');expect(p.locator('#checkoutPaymentForm')).to_have_count(0)
  expect(p.locator('#posReceipt')).to_contain_text('Cash rounding');expect(p.locator('#posPrintLast')).to_be_enabled();settle()
  with server.connect() as c:assert c.execute('SELECT count(*) FROM pos_sales').fetchone()[0]==1
  p.locator('#posSalesShortcut').tap();p.locator('[data-checkout-receipt]').first.tap();expect(p.locator('#checkoutReceiptPreview')).to_contain_text('Store credit');p.screenshot(path=str(out/'DESK-Print-Receipts.png'));p.evaluate("document.body.classList.add('checkoutPrinting')");p.emulate_media(media='print');expect(p.locator('#checkoutReceiptPreview')).to_be_visible();expect(p.locator('#checkoutReceiptList')).to_be_hidden();p.pdf(path=str(out/'Sample-Checkout-Receipt.pdf'));p.emulate_media(media='screen');p.evaluate("document.body.classList.remove('checkoutPrinting')");p.locator('#checkoutReceiptClose').tap()
  p.locator('#thriftTools').tap();expect(p.locator('dialog[open]')).to_contain_text('Thrift store checkout');p.locator('dialog[open] .flowClose').tap()
  # Detached form residue must not trap a user. Real unsaved work still blocks exit.
  p.evaluate('()=>{const f=document.createElement("form");changedForms.set(f,"old");}')
  p.locator('#posExitButton').tap();p.locator('#posExitForm [name=code]').fill('123456');p.locator('#posExitForm button.primary').tap();expect(p.locator('#posExitError')).to_have_text('Fixture exit verified');assert p.evaluate('window.exitCalls')==1;p.locator('#posExitCancel').tap()
  # Open-price products with required choices complete in the same keypad dialog.
  custom=post('product-save',name='Sample size choice',category='Clothes',price=100,taxable=True,rules={'open_priced':True,'modifiers':[{'id':'size','name':'Size','required':True,'options':[{'id':'large','name':'Large','price':100}]}]})['ids'][0]
  p.evaluate('posLoad()');p.locator('[data-pos-product="'+custom+'"]').tap();p.locator('#deskKeypadValue').fill('5.00');p.locator('.deskKeypadApply').tap();expect(p.locator('.deskAmountPad')).to_be_visible();p.locator('#deskAmountEntry select').select_option('large');p.locator('.deskKeypadApply').tap();expect(p.locator('#posCart')).to_contain_text('Size: Large');settle()
  p.locator('#posDiscard').tap();expect(p.locator('#checkoutCancelForm select')).to_be_visible();p.locator('#checkoutCancelForm select').select_option('entry-error');p.locator('#checkoutCancelForm button').tap();p.wait_for_function('()=>!posCurrent')
  p.goto(origin+'/office');p.wait_for_function('()=>!!user');p.evaluate('officeAction("checkout-buttons")');expect(p.locator('#checkoutChoiceForm')).to_be_visible();p.screenshot(path=str(out/'OFFICE-Checkout-Choices.png'))
  choice=p.locator('#checkoutChoiceForm');choice.locator('[name=name]').fill('Sample button');choice.locator('[name=value]').fill('3');choice.locator('button.primary').click();assert p.evaluate('unfinished()'), 'Unsaved choices must block updates';p.locator('#checkoutSettingsSave').click();expect(p.locator('#checkoutChoiceForm')).to_have_count(0);assert not p.evaluate('unfinished()')
  assert not errors,errors;b.close()
finally:f.close()
print('PASS automatic product entry, cancel preservation, presets, pay later/find, cash cents keypad, partial credit, payment replay, receipts, exit and OFFICE preview')
