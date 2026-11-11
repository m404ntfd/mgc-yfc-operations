"""First native DESK tap honors product taxes when no default store rate exists."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import wait_for_pos_save
import server

f=CoordinatorFixture();out=Path(os.environ.get('STORE_CHECKOUT_PREVIEW','test-artifacts/store-checkout'));out.mkdir(parents=True,exist_ok=True)
def post(path,**data):
 code,result=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert code==200,(path,result);return result
try:
 post('catalog-options-save',revision=0,categories=['Books'],printing=[],taxes=[dict(id='sample-tax',name='SAMPLE tax',bps=700,store_id='thrift-mart')])
 def product(name,price=1000,**rules):return post('product-save',name=name,category='Books',price=price,taxable=True,rules=dict(tax_ids=['sample-tax'],**rules))['ids'][0]
 fixed=product('SAMPLE Large Hardback',200);opened=product('SAMPLE Custom Book',open_priced=True);weighed=product('SAMPLE Books by weight',200,sold_by_weight=True)
 legacy=post('product-save',name='SAMPLE item needing tax setup',category='Books',price=100,taxable=True,rules={})['ids'][0]
 device='a'*32;post('terminal-save',name='Thrift Mart - SAMPLE register',device=device,store_id='thrift-mart',enabled=True)
 info=dict(app='pos',device=device,version='1.18.0',configured=True,nonce='f'*64,computer=dict(id='b'*32,hostname='SAMPLE-PC',macs=[],os='Windows fixture'))
 assert f.call('computers/self',info)[0]==200
 assert f.call('computers/register',dict(id='b'*32,revision=0,name='Sample Computer',role='pos',app='pos',device=device))[0]==200
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None);errors=[];origin=f'http://127.0.0.1:{f.port}'
  ctx=browser.new_context(viewport={'width':1920,'height':1080},has_touch=True,reduced_motion='reduce')
  ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.pywebview={api:{kiosk_info:async()=>window.fixtureInfo,terminal_info:async()=>window.fixtureInfo}};')
  assert ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'}).status==200
  p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.goto(origin+'/pos?kiosk=1');expect(p.locator('#nativeTerminalStatus')).to_contain_text('Registered')
  expect(p.locator('#posStatus')).not_to_contain_text('Configure receipt and tax settings');assert p.evaluate('posOverview.settings.tax_bps') is None
  p.locator('[data-pos-product="'+fixed+'"]').tap();expect(p.locator('#posCart')).to_contain_text('$2.14');wait_for_pos_save(p);original=p.evaluate('JSON.stringify(posCurrent)')
  p.locator('[data-pos-product="'+opened+'"]').tap();expect(p.locator('#flowOpenPrice')).to_be_visible();p.locator('.flowProductCancel').tap();expect(p.locator('dialog[open]')).to_contain_text('because no price was entered');p.locator('[data-product-cancel-ok]').tap();assert p.evaluate('JSON.stringify(posCurrent)')==original
  p.locator('[data-pos-product="'+legacy+'"]').tap();expect(p.locator('#checkoutSetupRequired')).to_be_visible();expect(p.locator('#checkoutSetupRequired')).to_contain_text('confirm the store’s default tax rate');p.locator('#checkoutSetupClose').tap();assert p.evaluate('JSON.stringify(posCurrent)')==original
  p.locator('[data-pos-product="'+opened+'"]').tap();p.locator('#flowOpenPrice').fill('5');p.locator('#flowChoices button.primary').tap();expect(p.locator('#posCart')).to_contain_text('$7.49');wait_for_pos_save(p)
  p.locator('[data-pos-product="'+weighed+'"]').tap();p.locator('#storeWeight [name=weight]').fill('2.25');p.locator('#storeWeight button.primary').tap();expect(p.locator('#posCart')).to_contain_text('$12.31');wait_for_pos_save(p)
  p.screenshot(path=str(out/'DESK-Product-Taxes-Receipt.png'))
  p.locator('#posPayNow').tap();p.locator('#posCash [name=tender]').fill('20');p.locator('#posCash button.primary').tap();expect(p.locator('#posReceipt')).to_contain_text('$12.31');wait_for_pos_save(p)
  assert p.evaluate('posOverview.settings.tax_bps') is None;assert not errors,errors;browser.close()
 print('PASS native first product tap without a default tax, correct totals, open-price cancellation, missing-tax guidance, weighed items and completed receipt')
finally:f.close()
