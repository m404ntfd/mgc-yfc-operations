"""Local sample UI with a mocked native Clover check; no real cards/device calls."""
import json
import os
from pathlib import Path
import time
import uuid

from playwright.sync_api import sync_playwright, expect
import server
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import office_setting, wait_for_pos_save
from test_theme_contrast import AUDIT


def run():
    f = CoordinatorFixture()
    out = Path('output/preview/clover-pilot'); out.mkdir(parents=True, exist_ok=True)
    server.POS_UPDATE_RELEASE = server.OFFICE_UPDATE_RELEASE = {'version':'0.0.0','checked':time.time(),'attempted':time.time(),'checking':False}
    def post(path, **data):
        code, result = f.call('pos/'+path, dict(request=uuid.uuid4().hex, **data))
        assert code == 200, (code, result)
        return result
    try:
        post('settings', store='Thrift Mart SAMPLE', tax_bps=700, confirmed=True)
        terminal = post('terminal-save', name='pos1 · SAMPLE', device='1'*32, enabled=True)['id']
        post('terminal-save', name='Other checkout · SAMPLE', device='2'*32, enabled=True)
        product = post('product-save', name='Preserved sample book', category='Books', price=200, taxable=True)['ids'][0]
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
            context = browser.new_context(viewport={'width':1920,'height':1080}, device_scale_factor=1, has_touch=True)
            origin = f'http://127.0.0.1:{f.port}'
            context.request.post(origin+'/api/login', data={'name':'Admin','password':'testpassword'}, headers={'X-Dispatch':'1'})
            page = context.new_page(); errors=[]; page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(origin+'/office')
            office_setting(page, 'clover-pilot').click()
            dialog = page.locator('.cloverPilotDialog')
            expect(dialog).to_be_visible()
            page.locator('#cloverTerminal').select_option(terminal)
            form = page.locator('#cloverSettingsForm')
            expect(form).to_contain_text('pos1')
            form.locator('[name=address]').fill('192.168.2.50')
            form.locator('[name=serial]').fill('TESTSERIAL0564')
            page.locator('#cloverSave').click()
            expect(page.locator('#cloverTestResult')).to_contain_text('details saved')
            expect(page.locator('#cloverTest')).to_be_disabled()
            expect(dialog).to_contain_text('Open DESK on pos1')
            # Test the new fields/controls in every available theme and both modes.
            audit = AUDIT.replace("document.querySelectorAll(", "document.querySelector('.cloverPilotDialog').querySelectorAll(")
            for theme in server.RETAIL_THEMES:
                for mode in ('light','dark'):
                    page.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode;}', [theme,mode])
                    issues=page.evaluate(audit)
                    assert not issues, (theme,mode,issues)
            page.evaluate("document.body.dataset.retailTheme='classic-gray';document.documentElement.dataset.theme='light'")
            dialog.screenshot(path=str(out/'office-setup.png'))
            dialog.locator('.flowClose').click()
            page.add_init_script("""window.fixtureChecks=0;
              window.pywebview={api:{kiosk_info:async()=>({configured:true,device:'1'.repeat(32),nonce:'b'.repeat(64)}),
              clover_connection_check:async(token)=>{
                const r=await fetch('/api/pos/clover-test-redeem',{method:'POST',headers:{'Content-Type':'application/json','X-Dispatch':'1'},body:JSON.stringify({token,device:'1'.repeat(32),nonce:'b'.repeat(64)})});
                const approval=await r.json();if(!r.ok)return {error:approval.error};
                window.fixtureChecks++;
                return {status:'authorization_required',reachable:true,authorized:false,source_computer:'pos1 (SAMPLE)',payments_attempted:0,message:'Clover is reachable securely. Merchant authorization is still required.'};
              }}};""")
            page.goto(origin+'/pos?kiosk=1')
            page.locator('[data-pos-product="'+product+'"]').click();wait_for_pos_save(page)
            before=page.evaluate('JSON.stringify(posCurrent)')
            page.locator('#deskSettings summary').click();page.locator('#deskCloverSetup').click()
            expect(dialog).to_be_visible()
            expect(page.locator('#cloverTerminal option')).to_have_count(1)
            expect(page.locator('#cloverTest')).to_be_enabled()
            page.locator('#cloverTest').click()
            expect(page.locator('#cloverTestResult')).to_contain_text('Checked from pos1 (SAMPLE)')
            assert page.evaluate('window.fixtureChecks') == 1
            assert page.evaluate('JSON.stringify(posCurrent)') == before
            page.evaluate("document.body.dataset.retailTheme='midnight';document.documentElement.dataset.theme='dark'")
            dialog.screenshot(path=str(out/'desk-connection.png'))
            # Unsaved edits cannot silently test the older saved address.
            page.locator('#cloverSettingsForm [name=address]').fill('192.168.2.51')
            page.locator('#cloverTest').click()
            expect(page.locator('#cloverTestResult')).to_contain_text('Save the edited')
            assert page.evaluate('window.fixtureChecks') == 1
            dialog.locator('.flowClose').click()
            assert page.evaluate('JSON.stringify(posCurrent)') == before
            # Ordinary users do not receive the setup entry or permissions.
            context.clear_cookies()
            context.request.post(origin+'/api/login', data={'name':'Employee','password':'testpassword'}, headers={'X-Dispatch':'1'})
            page.goto(origin+'/office')
            expect(page.locator('#officeSettingsSearch')).to_be_visible()
            assert page.evaluate("!officeMenuCards().some(c=>c.action==='clover-pilot')")
            assert not errors, errors
            browser.close()
        print('PASS Clover OFFICE/DESK setup, save, native check, terminal isolation, permissions, all themes, and preserved sample sale')
    finally:
        f.close()


if __name__ == '__main__':
    run()
