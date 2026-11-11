from test_ui_helpers import password_login_page
import os,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
import server

def run():
 f=CoordinatorFixture();server.POS_UPDATE_RELEASE={'checking':False,'version':'9.0.0','checked':time.time()};server.POS_UPDATE_DEVICES.clear()
 try:
  f.call('pos/settings',{'request':'f'*32,'store':'Preview store','tax_bps':0,'confirmed':True})
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));context=b.new_context(viewport={'width':1366,'height':900});p=context.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.add_init_script("""window.testSeconds=30;window.testState='ready';window.retryCalls=0;window.installCalls=0;window.pywebview={api:{kiosk_info:async()=>({device:'a'.repeat(32),nonce:'b'.repeat(64),configured:true,version:'1.1.0',updater:true}),update_status:async id=>id?({state:window.testState,error:window.testState==='error'?'Download interrupted':null,seconds:window.testSeconds,version:'1.1.0',target:'9.0.0'}):({state:'idle'}),retry_update:async()=>{window.retryCalls++;window.testState='downloading';return {state:'downloading',seconds:window.testSeconds};},install_update:async()=>{window.installCalls++;return window.posUpdateFreeze()?{ok:true}:{error:'Finish or cancel your current sale.'}}}};""")
   origin=f'http://127.0.0.1:{f.port}';p.goto(origin+'/pos?kiosk=1');password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
   p.locator('#posNew').click();expect(p.locator('#posCart')).to_contain_text('Saved on server');p.locator('#posManualShortcut').click()
   form=p.locator('#posManual');form.locator('[name=name]').fill('Test sale');form.locator('[name=category]').fill('General');form.locator('[name=price]').fill('5');form.get_by_role('button',name='Add to sale',exact=True).click();expect(p.locator('#posCart')).to_contain_text('$5.00')
   office=p.context.new_page();office.goto(origin+'/office#pos-updates');expect(office.locator('#posReleaseStatus')).to_contain_text('9.0.0')
   office.locator('#posUpdateSettings [name=seconds]').fill('30');office.locator('#posUpdateSettings button').click();office.locator('#startPosRelease').click();expect(office.locator('#posReleaseStatus')).to_contain_text('requested');office.locator('#closePosUpdates').click()
   expect(p.locator('#posInstallBanner')).to_be_visible(timeout=10000);expect(p.locator('#posInstallReady')).to_be_enabled();expect(p.locator('#posCart')).to_contain_text('$5.00')
   out=Path(os.environ.get('TEST_ARTIFACTS','test-artifacts'));out.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(out/'POS-Update-Warning-Preview.png'))
   p.evaluate('window.testSeconds=0');expect(p.locator('#posInstallMessage')).not_to_contain_text('Warning time remaining',timeout=10000);expect(p.locator('#posInstallReady')).to_be_enabled(timeout=10000);p.locator('#posInstallReady').click();expect(p.locator('#posInstallMessage')).to_contain_text('Finish or cancel');assert not p.evaluate('!!window.posUpdateInstalling')
   p.locator('#posNew').click();expect(p.locator('#posStatus')).to_contain_text('update before starting another')
   p.locator('#posDiscard').click();p.locator('dialog[open] [name=reason]').fill('Customer left before update');p.locator('dialog[open] form button').click();expect(p.locator('#posDiscard')).to_be_hidden();
   # A failed download remains visible; a one-second countdown paint must not hide it.
   p.evaluate("window.testState='error';window.testSeconds=2")
   expect(p.locator('#posInstallReady')).to_have_text('Retry update download',timeout=10000)
   expect(p.locator('#posInstallReady')).to_be_enabled();expect(p.locator('#posInstallMessage')).to_contain_text('Download interrupted')
   p.wait_for_timeout(1100);expect(p.locator('#posInstallMessage')).to_contain_text('Download interrupted')
   p.locator('#posInstallReady').click();assert p.evaluate('window.retryCalls')==1
   expect(p.locator('#posInstallMessage')).to_contain_text('Downloading and verifying')
   p.locator('#posInstallReady').click();expect(p.locator('#posInstallReady')).to_have_text('Keep working')
   assert p.evaluate('window.installCalls')==0
   # Canceling readiness is possible while the download continues.
   p.locator('#posInstallReady').click();expect(p.locator('#posInstallReady')).to_have_text('My work is finished — update')
   p.evaluate('window.testSeconds=0')
   p.locator('#posInstallReady').click();expect(p.locator('#posInstallMessage')).to_contain_text('marked finished')
   p.wait_for_timeout(4300);assert p.evaluate('window.installCalls')==0
   p.screenshot(path=str(out/'POS-Update-Ready-Waiting-Preview.png'))
   p.evaluate("window.testState='ready'")
   expect(p.locator('body.posInstalling')).to_be_visible(timeout=10000);assert p.evaluate('window.installCalls')==1
   # Operations entry point also opens the administrator controls after login.
   q=b.new_page();q.goto(origin+'/#pos-updates');password_login_page(q).locator('#login [name=name]').fill('Admin');q.locator('#login [name=password]').fill('testpassword');q.locator('#login button').click();expect(q.locator('#posUpdatesDialog')).to_be_visible(timeout=10000)
   assert not errors,errors;b.close()
 finally:f.close()
 print('PASS POS/Operations update controls, warning seconds, unfinished-sale block and safe acknowledgement')
if __name__=='__main__':run()
