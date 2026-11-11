from test_ui_helpers import password_login_page
from test_computer_updates import ComputerTests
from playwright.sync_api import sync_playwright,expect
import os,re
f=ComputerTests();f.setUp()
try:
 f.heartbeat();f.register();f.f.call('pos/settings',{'request':'f'*32,'store':'Test shop','tax_bps':0,'confirmed':True})
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'));p=b.new_page(viewport={'width':1366,'height':900})
  p.add_init_script("""window.testSeconds=30;window.installAttempts=0;window.pywebview={api:{kiosk_info:async()=>({device:'a'.repeat(32),nonce:'b'.repeat(64),configured:true,version:'1.0.0',updater:true,computer:{id:'1'.repeat(32),hostname:'TEST-POS',macs:[]}}),update_status:async id=>id?({state:'ready',seconds:window.testSeconds,version:'1.0.0',target:'9.0.0'}):({state:'idle'}),install_update:async()=>{window.installAttempts++;return window.posUpdateFreeze(false)?{ok:true}:{error:'Finish your current sale first.'}}}};""")
  p.goto(f'http://127.0.0.1:{f.f.port}/pos?kiosk=1');password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
  p.locator('#posNew').click();p.locator('#posManualShortcut').click();p.locator('#posManual [name=name]').fill('Test item');p.locator('#posManual [name=category]').fill('General');p.locator('#posManual [name=price]').fill('5');p.locator('#posManual').get_by_role('button',name='Add to sale',exact=True).click();expect(p.locator('#posCart')).to_contain_text('$5.00')
  code,result=f.f.call('computers/start',{'computers':['1'*32],'seconds':30});assert code==200,result
  expect(p.locator('#posInstallBanner')).to_be_visible(timeout=10000);assert p.evaluate('window.installAttempts')==0
  p.evaluate('window.testSeconds=0');expect(p.locator('#posInstallMessage')).to_contain_text('Finish your current sale',timeout=10000);assert not p.evaluate('!!window.posUpdateInstalling');expect(p.locator('#posCart')).to_contain_text('$5.00')
  p.locator('#posDiscard').click();p.locator('dialog[open] [name=reason]').fill('Synthetic test cancellation');p.locator('dialog[open] form button').click()
  expect(p.locator('body')).to_have_class(re.compile(r'.*posInstalling.*'),timeout=10000);b.close()
 print('PASS coordinated automatic update waits for warning and unfinished sale, then installs without a second staff click.')
finally:f.tearDown()
