"""Connection dialogs against isolated sample server; no live accounts or records."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_update_coordination import CoordinatorFixture
from test_theme_contrast import AUDIT
from test_ui_helpers import password_login_page


def run():
    fixture=CoordinatorFixture()
    out=Path('output/preview/connection-dialog');out.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
            origin=f'http://127.0.0.1:{fixture.port}'
            for app,path in [('DESK','/pos'),('OFFICE','/office'),('STORE OPS','/')]:
                print('Connection screen',app,flush=True)
                context=browser.new_context(viewport={'width':1440,'height':960})
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(origin+path);expect(page.locator('#auth')).to_be_visible()
                expect(page.locator('#serverConnectionDialog')).not_to_be_visible()
                assert page.evaluate('ConnectionStatus.timeout')==10
                # Authentication failures keep the normal sign-in error.
                if app!='STORE OPS':password_login_page(page)
                page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('incorrect')
                page.locator('#login button[type=submit],#login button:not([type])').first.click()
                expect(page.locator('#serverConnectionDialog')).not_to_be_visible()
                # An actual login request with no response reaches the common 10s deadline.
                page.clock.install()
                page.route('**/api/login',lambda route:None)
                page.locator('#login [name=password]').fill('testpassword')
                page.locator('#login button[type=submit],#login button:not([type])').first.click()
                dialog=page.locator('#serverConnectionDialog')
                expect(dialog).to_have_attribute('data-state','connecting')
                expect(dialog.locator('button')).to_have_count(0)
                starts=[]
                for _ in range(33):
                    expect(dialog.locator('.lit')).to_have_count(7)
                    starts.append(dialog.locator('.connectionTrack i').evaluate_all('(bars)=>bars.findIndex(b=>b.classList.contains("lit"))'))
                    page.clock.run_for(80)
                assert 0 in starts and 15 in starts and any(a>b for a,b in zip(starts,starts[1:])),starts
                audit=AUDIT.replace('document.querySelectorAll(',"document.querySelector('#serverConnectionDialog').querySelectorAll(")
                for theme in ('classic-gray','harbor-blue','coastal-teal','midnight','coastyouth-red','glass-blue','glass-teal','glass-violet','glass-rose','glass-graphite'):
                    for mode in ('light','dark'):
                        page.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode])
                        assert not page.evaluate(audit),(app,theme,mode,page.evaluate(audit))
                page.evaluate("document.body.dataset.retailTheme='midnight';document.documentElement.dataset.theme='dark'")
                dialog.screenshot(path=str(out/(app+'-Connecting.png')),animations='allow')
                page.clock.fast_forward(10000)
                expect(dialog).to_have_attribute('data-state','failed')
                expect(dialog.locator('h2')).to_have_text('Can Not Connect to Operations Server')
                expect(dialog.locator('.connectionTrack')).to_have_count(0)
                expect(dialog.locator('.connectionRings')).to_be_visible()
                expect(dialog.locator('button')).to_have_count(3)
                for theme in ('classic-gray','midnight','glass-blue','glass-teal','glass-violet','glass-rose','glass-graphite','coastyouth-red'):
                    for mode in ('light','dark'):
                        page.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode])
                        assert not page.evaluate(audit),(app,theme,mode,page.evaluate(audit))
                page.evaluate("document.body.dataset.retailTheme='midnight';document.documentElement.dataset.theme='dark'")
                dialog.screenshot(path=str(out/(app+'-Cannot-Connect.png')))
                # Retry verifies connectivity; it must never replay the submitted password.
                page.unroute('**/api/login')
                page.locator('#serverConnectionRetry').click();expect(dialog).not_to_be_visible()
                assert page.evaluate('user') is None
                page.evaluate("ConnectionStatus.fail('Sample connection timeout')")
                page.locator('#serverConnectionConfigure').click()
                expect(page.locator('#browserServerConnection')).to_be_visible()
                page.locator('#browserServerConnection [name=timeout]').fill('3')
                page.locator('#browserServerConnection button').first.click();expect(dialog).not_to_be_visible()
                assert page.evaluate('ConnectionStatus.timeout')==3
                # A late completion cannot close a newer failed check or expose credentials.
                page.evaluate("{window.pendingCheck=ConnectionStatus.run(()=>new Promise(r=>window.resolveLate=r)).catch(()=>{});}")
                page.clock.fast_forward(3100);expect(dialog).to_have_attribute('data-state','failed')
                page.evaluate('window.resolveLate({ok:true})');expect(dialog).to_have_attribute('data-state','failed')
                page.set_viewport_size({'width':390,'height':844})
                assert dialog.evaluate('(e)=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight}')
                # Offline logout hides the app and is completed before a cached
                # authenticated session can reopen it on a subsequent retry.
                context.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
                page.route('**/api/logout',lambda route:route.abort())
                with page.expect_navigation():page.locator('#serverConnectionLogout').click()
                expect(page.locator('#serverConnectionDialog')).to_have_attribute('data-state','failed')
                assert page.evaluate('user') is None
                page.unroute('**/api/logout');page.locator('#serverConnectionRetry').click()
                expect(page.locator('#serverConnectionDialog')).not_to_be_visible()
                assert context.request.get(origin+'/api/session').json()['user'] is None
                assert not errors,errors
                context.close()
            browser.close()
        print('PASS all three apps: 10s login timeout, seven bouncing segments, theme contrast, recovery controls, mobile layout, no credential replay, late response protection')
    finally:fixture.close()


if __name__=='__main__':run()
