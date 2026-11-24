"""Timed server failures, false responses and recovery with a preserved sample cart."""
import datetime as dt
import json
import os
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from playwright.sync_api import sync_playwright,expect
import server
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import office_setting,wait_for_pos_save

f=CoordinatorFixture();out=Path('output/preview/desk-connection');out.mkdir(parents=True,exist_ok=True)
def post(path,**data):
 code,result=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert code==200,(code,result);return result
try:
 post('settings',store='Thrift Mart SAMPLE',tax_bps=700,confirmed=True)
 product=post('product-save',name='Sample book',category='Books',price=200,taxable=True)['ids'][0]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
  ctx=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,has_touch=True,reduced_motion='reduce')
  origin=f'http://127.0.0.1:{f.port}';ctx.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
  p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  p.add_init_script('''window.healthStarts=[];window.healthActive=0;window.healthMax=0;
   const realFetch=window.fetch;window.fetch=async function(url,...args){
    if(!String(url).startsWith('/api/desk-connection'))return realFetch.call(this,url,...args);
    healthStarts.push(Date.now());healthActive++;healthMax=Math.max(healthMax,healthActive);
    try{return await realFetch.call(this,url,...args);}finally{healthActive--;}
   };''')
  p.clock.install(time=dt.datetime(2026,11,23,12,tzinfo=dt.timezone.utc))
  p.goto(origin+'/pos');light=p.locator('#deskConnectionIndicator');expect(light).to_have_attribute('data-state','connected')
  p.locator('[data-pos-product="'+product+'"]').click();expect(p.locator('#posCart')).to_contain_text('Sample book');wait_for_pos_save(p)
  p.clock.pause_at(p.evaluate('Date.now()')/1000+1)
  p.evaluate('()=>window.deskConnectionMonitor.checkNow()')
  before=p.evaluate('JSON.stringify(posCurrent)')
  p.evaluate('healthStarts=[]')
  p.clock.run_for(9000);assert p.evaluate('healthStarts.length')==0
  p.clock.run_for(1000);expect(light).to_have_attribute('data-state','connected')
  assert p.evaluate('healthStarts.length')==1
  p.evaluate('()=>window.deskConnectionMonitor.checkNow()')
  p.evaluate('document.body.dataset.retailTheme="midnight";document.documentElement.dataset.theme="dark"')
  def preview(name):
   p.screenshot(path=str(out/(name+'.png')),clip={'x':0,'y':0,'width':1000,'height':160})
  preview('connected')
  print('Verified default probe cadence',flush=True)
  mode={'value':'bad-json'}
  def intercept(route):
   nonce=parse_qs(urlsplit(route.request.url).query)['nonce'][0]
   if mode['value']=='timeout':return
   if mode['value']=='gateway':route.fulfill(status=502,content_type='text/html',body='Gateway unavailable');return
   if mode['value']=='bad-json':route.fulfill(status=200,content_type='application/json',body=json.dumps(dict(service='coastyouth-operations',online=True,nonce='stale-response')));return
   route.fulfill(status=200,content_type='application/json',body=json.dumps(dict(service='coastyouth-operations',online=True,nonce=nonce)))
  p.route('**/api/desk-connection?*',intercept)
  p.clock.run_for(19000);expect(light).to_have_attribute('data-state','connected')
  p.clock.run_for(1000);expect(light).to_have_attribute('data-state','delayed');expect(p.locator('#connection')).to_have_text('Connection delayed');preview('delayed')
  p.clock.run_for(10000);expect(light).to_have_attribute('data-state','disconnected');preview('disconnected')
  assert p.evaluate('JSON.stringify(posCurrent)')==before
  print('Verified yellow/red timing and preserved cart',flush=True)
  assert 'Last successful check:' in p.locator('#navCheckout').get_attribute('title')
  # Unrelated successful application requests must not falsely reset the light.
  p.evaluate('()=>api("session")');expect(light).to_have_attribute('data-state','disconnected')
  mode['value']='gateway';p.evaluate('()=>window.deskConnectionMonitor.checkNow()');expect(light).to_have_attribute('data-state','disconnected')
  mode['value']='healthy';p.evaluate('()=>window.deskConnectionMonitor.checkNow()');expect(light).to_have_attribute('data-state','connected')
  print('Verified bad responses and recovery',flush=True)
  # A hung request times out, and repeated calls cannot overlap it.
  mode['value']='timeout';p.evaluate('void window.deskConnectionMonitor.checkNow();void window.deskConnectionMonitor.checkNow()')
  p.clock.run_for(5000);p.clock.run_for(25000);expect(light).to_have_attribute('data-state','disconnected')
  assert p.evaluate('healthMax')==1
  p.clock.run_for(5000)
  for _ in range(40):
   if p.evaluate('healthActive')==0:break
   time.sleep(.05)
  assert p.evaluate('healthActive')==0,'The timed-out probe did not finish'
  print('Verified probe timeout and no overlap',flush=True)
  mode['value']='healthy';p.evaluate('()=>window.deskConnectionMonitor.checkNow()');expect(light).to_have_attribute('data-state','connected')
  ctx.set_offline(True);expect(light).to_have_attribute('data-state','disconnected')
  ctx.set_offline(False);p.evaluate('()=>window.deskConnectionMonitor.checkNow()');expect(light).to_have_attribute('data-state','connected')
  assert p.evaluate('JSON.stringify(posCurrent)')==before
  with server.connect() as c:assert c.execute('SELECT count(*) FROM pos_sales').fetchone()[0]==0
  print('Verified offline event and recovery',flush=True)
  # OFFICE uses its existing status display and offers permission-gated timing controls.
  office=ctx.new_page();office.goto(origin+'/office');office_setting(office,'desk-connection').click()
  form=office.locator('#deskConnectionSettings');expect(form).to_be_visible();office.screenshot(path=str(out/'office-settings.png'))
  form.locator('[name=interval_seconds]').fill('15');form.locator('[name=warning_seconds]').fill('30');form.locator('[name=offline_seconds]').fill('60');form.locator('button').click();expect(form).to_have_count(0)
  assert f.call('pos/checkout-settings')[1]['settings']['connection_monitor']==dict(interval_seconds=15,warning_seconds=30,offline_seconds=60)
  expect(office.locator('#deskConnectionIndicator')).to_have_count(0)
  # New settings apply to this already-open register, without a reload or cart change.
  p.clock.run_for(60000);p.evaluate('()=>window.deskConnectionMonitor.checkNow()')
  expect(p.locator('#navCheckout')).to_have_attribute('title',__import__('re').compile('Checks every 15 seconds'))
  assert p.evaluate('JSON.stringify(posCurrent)')==before
  # Connectivity is independent of cashier authentication and remains available at PIN/sign-in.
  ctx.clear_cookies();p.reload();expect(light).to_have_attribute('data-state','connected');expect(p.locator('#auth')).to_be_visible()
  assert not errors,errors;browser.close()
finally:f.close()
print('PASS 10-second probes, timed yellow/red, nonce/gateway/timeout failures, no overlap, offline/recovery, preserved cart, store settings and signed-out checks')
