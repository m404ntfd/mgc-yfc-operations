"""Touch consent and customer-display previews using isolated sample records."""
import json,os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_theme_contrast import AUDIT

def run():
 f=CoordinatorFixture();out=Path('output/preview/roundup');out.mkdir(parents=True,exist_ok=True)
 def post(action,**data):
  code,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert code==200,(action,result);return result
 try:
  post('settings',store='Thrift Mart · SAMPLE',tax_bps=0,confirmed=True)
  settings=f.call('pos/thrift-config')[1]['settings'];assert settings['donations'] and settings['revision']==0,settings
  products=[post('product-save',name=name,category='Household',price=price,taxable=False)['ids'][0] for name,price in [('Sample housewares',1237),('Sample book',200)]]
  device='a'*32;terminal=post('terminal-save',name='Thrift Mart Register 1',device=device,enabled=True)['id']
  post('terminal-options-save',terminal=terminal,revision=0,printer='')
  post('store-display-save',store_id='thrift-mart',revision=0,enabled=True,welcome='Welcome to Thrift Mart',thanks='Thank you!')
  display_path=f.call('pos/terminal-options?device='+device)[1]['display_path']
  info=dict(app='pos',device=device,version='1.19.0',configured=True,nonce='b'*64,computer=dict(id='c'*32,hostname='SAMPLE-TOUCH-PC',macs=[],os='Windows fixture'))
  assert f.call('computers/self',info)[0]==200
  assert f.call('computers/register',dict(id='c'*32,revision=0,name='Sample Touch Register',role='pos',app='pos',device=device))[0]==200
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
   ctx=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,has_touch=True,reduced_motion='reduce')
   ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.pywebview={api:{kiosk_info:async()=>window.fixtureInfo,terminal_info:async()=>window.fixtureInfo}};')
   origin=f'http://127.0.0.1:{f.port}';ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
   p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   customer_ctx=browser.new_context(viewport={'width':1920,'height':1080},reduced_motion='reduce')
   customer=customer_ctx.new_page();customer.on('pageerror',lambda e:errors.append(str(e)))
   customer.goto(origin+display_path)
   p.goto(origin+'/pos?kiosk=1');expect(p.locator('#nativeTerminalStatus')).to_contain_text('Registered')
   def settle():p.wait_for_function('()=>!posBusy&&!posPending&&!writeCount&&!flowProductStarting')
   def product(i):p.locator('[data-pos-product="'+products[i]+'"]').tap();settle()
   def cancel_payment():p.locator('#checkoutCancel').tap();expect(p.locator('#checkoutPaymentForm')).to_have_count(0)
   def discard():
    p.locator('#posDiscard').tap();p.locator('[data-cancel-reason=entry-error]').tap();p.wait_for_function('()=>!posCurrent');settle()
   product(0);expect(p.locator('#posCart')).to_contain_text('Sample housewares');settle()
   before=p.evaluate('JSON.stringify(posCurrent)')
   p.locator('#posPayNow').tap();expect(p.locator('.roundupDialog')).to_be_visible();expect(customer.locator('#customerRoundup')).to_be_visible(timeout=12000)
   expect(customer.locator('#customerRoundupAmount')).to_have_text('+$0.63')
   assert customer.evaluate('()=>{const e=document.querySelector("#displayTraining");e.hidden=false;const r=e.getBoundingClientRect(),visible=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===e;e.hidden=true;return visible}'), 'Training notice must remain above the overlay'
   assert p.evaluate('JSON.stringify(posCurrent)')==before
   geometry=p.locator('.roundupDialog').evaluate('(d)=>{const yes=d.querySelector("#checkoutRoundupYes").getBoundingClientRect(),no=d.querySelector("#checkoutRoundupNo").getBoundingClientRect(),r=d.getBoundingClientRect();return {left:yes.x<no.x,bigger:yes.width>no.width,touch:yes.height>=60&&no.height>=60,fits:r.top>=0&&r.bottom<=innerHeight&&d.scrollWidth<=d.clientWidth}}')
   assert all(geometry.values()),geometry
   results=[]
   themes=['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+c for c in ['blue','teal','violet','rose','graphite']]
   for theme in themes:
    for mode in ['light','dark']:
     p.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode])
     p.wait_for_function('()=>!customerDisplayBusy');p.evaluate('customerDisplaySync()')
     palette=p.evaluate('checkoutRoundupDisplay().theme')
     customer.wait_for_function('(palette)=>Object.entries(palette).every(([key,value])=>document.querySelector(".roundupOverlay").style.getPropertyValue("--roundup-"+key)===value)',arg=palette)
     issues=p.evaluate(AUDIT.replace('document.querySelectorAll(', 'document.querySelector(".roundupDialog").querySelectorAll('))
     customer_issues=customer.evaluate(AUDIT.replace('document.querySelectorAll(', 'document.querySelector(".roundupOverlay").querySelectorAll('))
     results.append(dict(theme=theme,mode=mode,cashier=issues,customer=customer_issues))
     if (theme,mode) in [('harbor-blue','light'),('midnight','dark'),('glass-teal','light')]:
      p.screenshot(path=str(out/f'DESK-Round-Up-{theme}.png'));customer.screenshot(path=str(out/f'Customer-Round-Up-{theme}.png'))
   (out/'theme-results.json').write_text(json.dumps(results,indent=2))
   assert not [x for x in results if x['cashier'] or x['customer']],[x for x in results if x['cashier'] or x['customer']]
   p.locator('#checkoutRoundupNo').tap();expect(p.locator('#checkoutPaymentForm')).to_be_visible();expect(customer.locator('#customerRoundup')).to_be_hidden(timeout=12000)
   assert p.evaluate('JSON.stringify(posCurrent)')==before
   cancel_payment();p.locator('#posPayNow').tap();expect(p.locator('#checkoutPaymentForm')).to_be_visible();expect(p.locator('.roundupDialog')).to_have_count(0);cancel_payment()
   product(1);p.locator('#posPayNow').tap();expect(p.locator('.roundupDialog')).to_be_visible();p.keyboard.press('Escape');expect(p.locator('.roundupDialog')).to_have_count(0);expect(p.locator('#checkoutPaymentForm')).to_have_count(0)
   p.locator('#posPayNow').tap();expect(p.locator('.roundupDialog')).to_be_visible()
   # Lost response after commit: do not permit No or a second donation; retry reuses the same request.
   def lost(route):route.fetch();route.abort();p.unroute('**/api/pos/thrift-donation',lost)
   p.route('**/api/pos/thrift-donation',lost);p.locator('#checkoutRoundupYes').tap()
   expect(p.locator('.roundupDialog .flowError')).not_to_be_empty();expect(p.locator('#checkoutRoundupNo')).to_be_disabled()
   p.locator('#checkoutRoundupYes').tap();expect(p.locator('#checkoutPaymentForm')).to_be_visible();expect(p.locator('#checkoutDue')).to_have_text('$15.00')
   assert p.evaluate('posCurrent.lines.filter(l=>l.donation).length')==1
   assert p.evaluate('posCurrent.lines.find(l=>l.donation).subtotal')==63
   expect(customer.locator('#customerRoundup')).to_be_hidden(timeout=12000)
   cancel_payment();p.locator('#posPayNow').tap();expect(p.locator('#checkoutPaymentForm')).to_be_visible();expect(p.locator('.roundupDialog')).to_have_count(0)
   p.locator('[data-tender=exact]').tap();p.locator('#checkoutComplete').tap();expect(p.locator('#posReceipt')).to_contain_text('Voluntary donation');expect(p.locator('#posReceipt')).to_contain_text('$0.63');settle()
   expect(p.locator('#receiptNoPrinterOkay')).to_be_visible();p.locator('#receiptNoPrinterOkay').tap()
   product(1);p.locator('#posPayNow').tap();expect(p.locator('#checkoutPaymentForm')).to_be_visible();expect(p.locator('.roundupDialog')).to_have_count(0);cancel_payment();discard()
   settings=f.call('pos/thrift-config')[1]['settings'];post('thrift-settings',**dict(settings,donations=False))
   product(0);p.locator('#posPayNow').tap();expect(p.locator('#checkoutPaymentForm')).to_be_visible();expect(p.locator('.roundupDialog')).to_have_count(0)
   assert not errors,errors;browser.close()
 finally:f.close()
 print('PASS touch round-up consent, customer theme sync, 20 theme variants, decline/cancel preservation, lost-response retry, donation receipt and feature setting')

if __name__=='__main__':run()
