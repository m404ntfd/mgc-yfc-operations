"""Type cash immediately after either round-up choice, without focusing the field in the test."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture

def run():
 f=CoordinatorFixture();out=Path('output/preview/checkout-focus');out.mkdir(parents=True,exist_ok=True)
 def post(action,**data):
  code,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert code==200,(action,result);return result
 try:
  post('settings',store='Thrift Mart · SAMPLE',tax_bps=0,confirmed=True)
  product=post('product-save',name='Sample housewares',category='Household',price=1237,taxable=False)['ids'][0]
  info=dict(app='pos',device='a'*32,version='1.21.0',configured=True,nonce='b'*64,computer=dict(id='c'*32,hostname='SAMPLE-CHECKOUT',macs=[],os='Windows fixture'))
  post('terminal-save',name='Sample checkout',device=info['device'],enabled=True)
  assert f.call('computers/self',info)[0]==200
  assert f.call('computers/register',dict(id=info['computer']['id'],revision=0,name='Sample checkout',role='pos',app='pos',device=info['device']))[0]==200
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None);errors=[]
   for touch in (False,True):
    ctx=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,has_touch=touch,reduced_motion='reduce')
    ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.pywebview={api:{kiosk_info:async()=>fixtureInfo,terminal_info:async()=>fixtureInfo}};')
    origin=f'http://127.0.0.1:{f.port}';assert ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'}).status==200
    page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(origin+'/pos?kiosk=1')
    expect(page.locator('#nativeTerminalStatus')).to_contain_text('Registered')
    def choose(selector):
     control=page.locator(selector);control.tap() if touch else control.click()
    for answer in ('No','Yes'):
     choose('[data-pos-product="'+product+'"]');page.wait_for_function('()=>!posBusy&&!posPending&&!writeCount&&!flowProductStarting')
     choose('#posPayNow');choose('#checkoutRoundup'+answer)
     tender=page.locator('#checkoutTender');expect(tender).to_be_visible()
     expect(page.locator('[data-method=cash]')).to_have_attribute('aria-pressed','true')
     expect(page.locator('[data-method=card]')).to_be_disabled()
     # keyboard.type never selects/focuses an element; digits must reach the ready field.
     page.keyboard.type('2000');expect(tender).to_have_value('20.00');expect(tender).to_be_focused()
     expect(page.locator('#checkoutDue')).to_have_text('$13.00' if answer=='Yes' else '$12.37')
     expect(page.locator('#checkoutChange')).to_have_text('$7.00' if answer=='Yes' else '$7.63')
     # Tab remains ordinary keyboard navigation; delayed opening focus must not steal it.
     page.keyboard.press('Tab');expect(tender).not_to_be_focused()
     active=page.evaluate('document.activeElement.outerHTML');page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
     assert page.evaluate('document.activeElement.outerHTML')==active
     choose('[data-method=credit]');expect(page.locator('#checkoutAccount')).to_be_focused()
     choose('[data-method=cash]');expect(tender).to_be_focused()
     page.keyboard.type('2500');expect(tender).to_have_value('25.00')
     # Mix the onscreen keypad with a physical keyboard without clicking the cash field.
     choose('[data-money-key=clear]');choose('[data-money-key="2"]');choose('[data-money-key="0"]')
     page.keyboard.type('00');expect(tender).to_have_value('20.00');expect(tender).to_be_focused()
     choose('[data-tender="2000"]');page.keyboard.type('3000');expect(tender).to_have_value('30.00')
     if not touch and answer=='Yes':page.screenshot(path=str(out/'DESK-Cash-Ready-After-Round-Up.png'))
     # Enter completes exactly this cash sale; the donation choice is preserved.
     page.keyboard.press('Enter');expect(page.locator('#checkoutPaymentForm')).to_have_count(0)
     expect(page.locator('#posReceipt')).to_contain_text('Receipt #');page.wait_for_function('()=>!posBusy&&!posPending&&!writeCount')
     sale=f.call('pos/sales')[1]['sales'][0]
     assert sale['tender']==3000 and sale['total']==(1300 if answer=='Yes' else 1237),sale
     assert bool([line for line in sale['lines'] if line.get('donation')])==(answer=='Yes')
    ctx.close()
   assert not errors,errors;browser.close()
  print('PASS immediate keyboard cash entry after Yes/No on mouse and touch displays, mixed keypad/keyboard entry, method changes, Tab navigation, and correct payment/receipt totals')
 finally:f.close()

if __name__=='__main__':run()
