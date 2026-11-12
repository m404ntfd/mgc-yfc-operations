from test_ui_helpers import password_login_page
"""Browser layout and first-run gating checks; native integration tested separately."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture

def run():
 f=CoordinatorFixture()
 try:
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));p=b.new_page(viewport={'width':1440,'height':1050});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.add_init_script("""let configured=false;window.pywebview={api:{kiosk_info:async()=>({device:'a'.repeat(32),nonce:'b'.repeat(64),configured}),configure_passcode:async()=>{configured=true;return {ok:true}},request_exit:async()=>({error:'Incorrect admin passcode.'})}};""")
   p.goto(f'http://127.0.0.1:{f.port}/pos?kiosk=1')
   expect(p.locator('#posExitButton')).to_be_visible();expect(p.locator('#posRoot')).to_be_hidden()
   password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
   expect(p.locator('#kioskSetupDialog')).to_be_visible();expect(p.locator('#posRoot')).to_be_hidden()
   out=Path(os.environ.get('TEST_ARTIFACTS','test-artifacts'));out.mkdir(parents=True,exist_ok=True)
   p.screenshot(path=str(out/'POS-Admin-Passcode-Setup.png'))
   p.locator('#kioskSetupExit').click();expect(p.locator('#posExitDialog')).to_be_visible();p.locator('#posExitCancel').click()
   expect(p.locator('#kioskSetupDialog')).to_be_visible()
   form=p.locator('#kioskPasscodeForm');form.locator('[name=code]').fill('123456');form.locator('[name=confirm]').fill('123456');form.locator('button.primary').click()
   expect(p.locator('#kioskSetupDialog')).to_be_hidden();expect(p.locator('#posRoot')).to_be_visible()
   f.call('pos/settings',dict(request='d'*32,store='MGC YFC',tax_bps=0,confirmed=True));p.evaluate('posLoad()')
   expect(p.locator('#posCatalog')).to_be_visible();p.locator('#navCheckout').click()
   p.screenshot(path=str(out/'POS-Full-Screen-Preview.png'))
   p.locator('#posExitButton').click();p.locator('#posExitForm [name=code]').fill('000000');p.locator('#posExitForm button.primary').click();expect(p.locator('#posExitError')).to_contain_text('Incorrect')
   p.locator('#posExitCancel').click();expect(p.locator('#posAdmin')).to_be_hidden();p.goto(f'http://127.0.0.1:{f.port}/office');expect(p.locator('#posKioskSettings')).to_be_visible()
   assert not errors,errors;b.close()
 finally:f.close()
 print('PASS first-run UI gating, setup exit/cancel, admin settings and passcode error display')

if __name__=='__main__':run()
