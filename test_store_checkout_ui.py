"""Native checkout starts on the first product and follows its registered store."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page,office_setting,wait_for_pos_save
import server

f=CoordinatorFixture();out=Path(os.environ.get('STORE_CHECKOUT_PREVIEW','test-artifacts/store-checkout'));out.mkdir(parents=True,exist_ok=True)
def post(path,**data):
 code,result=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert code==200,(path,result);return result
def rows(table):
 with server.connect() as c:return [tuple(r) for r in c.execute('SELECT * FROM '+table+' ORDER BY rowid')]
try:
 post('settings',store='Thrift Mart · SAMPLE',tax_bps=700,confirmed=True)
 s=f.call('pos/stores')[1]['stores'][1]
 receipt=dict(address='Binopoly · SAMPLE LOCATION',phone='SAMPLE CONTACT',logo='',policy='SAMPLE return policy',footer='Thank you for shopping Binopoly · SAMPLE')
 post('store-save',**dict(s,name='Binopoly · SAMPLE',tax_bps=1000,confirmed=True,receipt=receipt))
 thrift=post('product-save',name='SAMPLE Thrift Mart shirt',category='Clothes',price=500,taxable=True,rules={})['ids'][0]
 fixed=post('product-save',name='Sample individually priced item',category='Goods',price=500,taxable=True,rules={'store_id':'binopoly'})['ids'][0]
 opened=post('product-save',name='Sample open-price item',category='Goods',price=100,taxable=True,rules={'store_id':'binopoly','open_priced':True})['ids'][0]
 weighed=post('product-save',name='Sample goods by the pound',category='Goods',price=200,taxable=True,rules={'store_id':'binopoly','sold_by_weight':True})['ids'][0]
 post('terminal-save',name='Thrift Mart · Sample browser',device='c'*32,store_id='thrift-mart',enabled=True)
 infos=[]
 for index,device in enumerate(('a'*32,'b'*32),1):
  post('terminal-save',name='Binopoly · Sample Register '+str(index),device=device,store_id='binopoly',enabled=True)
  info=dict(app='pos',device=device,version='1.18.0',configured=True,nonce='f'*64,computer=dict(id=str(index)*32,hostname='SAMPLE-PC-'+str(index),macs=[],os='Windows fixture'))
  assert f.call('computers/self',info)[0]==200
  assert f.call('computers/register',dict(id=str(index)*32,revision=0,name='Sample Computer '+str(index),role='pos',app='pos',device=device))[0]==200
  infos.append(info)
 with server.connect() as c:
  account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
  c.execute("INSERT INTO work_periods VALUES(901,?,100,NULL,'Office',NULL)",(account,));c.execute('INSERT INTO work_breaks VALUES(902,901,200,NULL)')
  c.execute("INSERT INTO jobs VALUES('sample-reservation',8,?)",('{"type":"Delivery","customer":"SAMPLE","notes":"Keep"}',))
  c.execute("INSERT INTO photos VALUES('sample-reservation',0,?)",(b'SAMPLE attachment',))
 protected={name:rows(name) for name in ('work_periods','work_breaks','jobs','photos','pos_products','retail_product_rules','pos_settings','users')}
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None);errors=[];origin=f'http://127.0.0.1:{f.port}'
  def native(info):
   ctx=browser.new_context(viewport={'width':1920,'height':1080},has_touch=True,reduced_motion='reduce')
   ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+";localStorage.setItem('coastyouth-retail-device','"+'c'*32+"');window.pywebview={api:{kiosk_info:async()=>window.fixtureInfo,terminal_info:async()=>window.fixtureInfo}};")
   assert ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'}).status==200
   page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(origin+'/pos?kiosk=1');return page
  p=native(infos[0]);expect(p.locator('#retailStoreBadge')).to_have_text('Binopoly · SAMPLE')
  expect(p.locator('#nativeTerminalStatus')).to_contain_text('Registered');expect(p.locator('#nativeTerminalSetup')).not_to_be_visible()
  assert p.locator('[data-pos-product="'+thrift+'"]').count()==0
  # A routine device heartbeat must not silently discard a product tap on a remote connection.
  held=[];p.route('**/api/computers/self',lambda route:held.append(route))
  with p.expect_request('**/api/computers/self',timeout=12000):p.wait_for_timeout(5200)
  assert held
  p.locator('[data-pos-product="'+fixed+'"]').tap();expect(p.locator('#posCart')).to_contain_text('$5.50');wait_for_pos_save(p)
  for route in held:route.continue_()
  p.unroute('**/api/computers/self')
  assert p.evaluate("localStorage.getItem('coastyouth-retail-device')")=='c'*32
  first=p.evaluate('posCurrent.id');assert p.evaluate('posCurrent.store_id')=='binopoly'
  p.locator('[data-pos-product="'+opened+'"]').tap();expect(p.locator('#flowOpenPrice')).to_be_visible();p.locator('.flowProductCancel').tap()
  expect(p.locator('dialog[open]')).to_contain_text('because no price was entered');p.locator('[data-product-cancel-ok]').tap();expect(p.locator('#posCart')).to_contain_text('$5.50')
  p.locator('[data-pos-product="'+weighed+'"]').tap();p.locator('#storeWeight [name=weight]').fill('2.25');p.locator('#storeWeight button.primary').tap();expect(p.locator('#posCart')).to_contain_text('$10.45');wait_for_pos_save(p)
  expect(p.locator('#posStatus')).to_contain_text('added to the sale and saved')
  p.screenshot(path=str(out/'DESK-Registered-Store-Receipt.png'))
  p.locator('#posPayNow').tap();p.locator('#posCash [name=tender]').fill('20');p.locator('#posCash button.primary').tap();expect(p.locator('#posReceipt')).to_contain_text(receipt['footer']);wait_for_pos_save(p)
  previous=rows('pos_sales');p.reload();expect(p.locator('#retailStoreBadge')).to_have_text('Binopoly · SAMPLE')
  p.locator('[data-pos-product="'+fixed+'"]').tap();expect(p.locator('#posCart')).to_contain_text('$5.50');assert p.evaluate('posCurrent.id')!=first
  # A second registered PC uses exactly the same store receipt and tax configuration.
  second=native(infos[1]);expect(second.locator('#retailStoreBadge')).to_have_text('Binopoly · SAMPLE');expect(second.locator('#nativeTerminalSetup')).not_to_be_visible()
  second.locator('[data-pos-product="'+fixed+'"]').click();expect(second.locator('#posCart')).to_contain_text('$5.50');wait_for_pos_save(second)
  second.locator('#posPayNow').click();second.locator('#posCash [name=tender]').fill('10');second.locator('#posCash button.primary').click();expect(second.locator('#posReceipt')).to_contain_text(receipt['footer']);wait_for_pos_save(second)
  assert rows('pos_sales')[:len(previous)]==previous
  # OFFICE exposes store assignments beside terminals, not per-terminal tax/receipt settings.
  officeContext=browser.new_context(viewport={'width':1920,'height':1080});assert officeContext.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'}).status==200
  office=officeContext.new_page();office.on('pageerror',lambda e:errors.append(str(e)));office.goto(origin+'/office')
  office_setting(office,'terminals').click();expect(office.locator('#terminalForm [name=store_id]')).to_be_visible();expect(office.locator('#retailEditor')).to_contain_text('Binopoly · SAMPLE')
  office.screenshot(path=str(out/'OFFICE-Terminal-Store-Settings.png'))
  # New native enrollment explicitly selects a store and refreshes products immediately.
  info=dict(infos[0],device='d'*32,computer=dict(id='4'*32,hostname='SAMPLE-NEW-PC',macs=[],os='Windows fixture'))
  new=native(info);expect(new.locator('#nativeTerminalForm [name=store_id]')).to_be_visible();new.locator('#nativeTerminalForm [name=name]').fill('Binopoly · New sample register');new.locator('#nativeTerminalForm [name=store_id]').select_option('binopoly')
  new.screenshot(path=str(out/'DESK-Register-Store.png'))
  new.locator('#nativeTerminalForm button').click();expect(new.locator('#nativeTerminalSetup')).not_to_be_visible();expect(new.locator('#retailStoreBadge')).to_have_text('Binopoly · SAMPLE')
  new.locator('[data-pos-product="'+opened+'"]').tap();new.locator('#flowOpenPrice').fill('12');new.locator('#flowChoices button.primary').tap();expect(new.locator('#posCart')).to_contain_text('$13.20')
  for name,values in protected.items():assert rows(name)==values,name
  assert not errors,errors;browser.close()
 print('PASS native saved-session store resolution, first tap during heartbeat, shared receipts/taxes across PCs, cancellation, weight/open price, registration, historical sales and protected records')
finally:f.close()
