"""OFFICE timeout editing and real isolated local cache files for all three apps."""
import os
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
import connection_preferences
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page, office_setting
from test_theme_contrast import AUDIT


def run():
    fixture=CoordinatorFixture();origin=f'http://127.0.0.1:{fixture.port}'
    out=Path('output/preview/connection-dialog');out.mkdir(parents=True,exist_ok=True)
    def set_timeout(value):
        revision=fixture.call('connection-settings')[1]['revision']
        code,result=fixture.call('connection-settings',{'timeout_seconds':value,'revision':revision})
        assert code==200,result
    def native(page,app,late=False):
        page.expose_function('fixturePreferences',lambda value:connection_preferences.load(app) if value is None else connection_preferences.save(app,value))
        page.add_init_script("window.pywebview={api:{connection_preferences:async(value)=>"+("(value===undefined&&!sessionStorage.getItem('fixture-read-started')?(sessionStorage.setItem('fixture-read-started','1'),new Promise(r=>window.finishNativeRead=r)):window.fixturePreferences(value??null))" if late else "window.fixturePreferences(value??null)")+"}};")
    def cached(page,app,seconds):
        page.wait_for_function('(value)=>ConnectionStatus.timeout===value',arg=seconds)
        page.wait_for_function('(value)=>JSON.parse(localStorage.getItem("coastyouth-connection-"+value[0])).timeout_seconds===value[1]',arg=[app,seconds])
        for _ in range(100):
            value=connection_preferences.load(app)
            if value['timeout_seconds']==seconds and value.get('managed'):return
            page.wait_for_timeout(20)
        raise AssertionError(('Native cache not updated',app,seconds,value))
    try:
        with patch.dict(os.environ,{'APPDATA':str(Path(fixture.tmp.name)/'clients')}),sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
            for app,path in [('pos','/pos'),('office','/office'),('ops','/')]:
                print('Checking OFFICE policy on',app,flush=True);set_timeout(25)
                context=browser.new_context(viewport={'width':1440,'height':960},bypass_csp=True);page=context.new_page();errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)));native(page,app,late=app=='office')
                page.goto(origin+path);expect(page.locator('#auth')).to_be_visible()
                assert page.evaluate('ConnectionStatus.timeout')==10
                assert not connection_preferences.load(app).get('managed')
                password_login_page(page);page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword')
                page.locator('#login button[type=submit],#login button:not([type])').first.click()
                page.wait_for_function('ConnectionStatus.timeout===25')
                if app=='office':page.evaluate('window.finishNativeRead({timeout_seconds:7,managed:true})')
                cached(page,app,25)
                # The next load uses the saved timeout even while the server is
                # unreachable, then receives the latest OFFICE value on retry.
                set_timeout(15);page.route('**/api/session',lambda route:route.abort())
                page.reload();expect(page.locator('#serverConnectionDialog')).to_have_attribute('data-state','failed')
                assert page.evaluate('ConnectionStatus.timeout')==25
                page.unroute('**/api/session');page.locator('#serverConnectionRetry').click();cached(page,app,15)
                # Native startup cache works even if the web-view cache is absent.
                page.evaluate('(app)=>localStorage.removeItem("coastyouth-connection-"+app)',app)
                page.route('**/api/session',lambda route:route.abort());page.reload()
                expect(page.locator('#serverConnectionDialog')).to_have_attribute('data-state','failed');cached(page,app,15)
                page.locator('#serverConnectionConfigure').click()
                expect(page.locator('#browserServerConnection')).to_contain_text('Managed in OFFICE')
                expect(page.locator('#browserServerConnection [name=timeout]')).to_have_count(0)
                assert not errors,errors
                context.close()
            # Administrators edit the shared value through the actual OFFICE UI.
            context=browser.new_context(viewport={'width':1440,'height':960},bypass_csp=True);page=context.new_page();native(page,'office')
            context.request.post(origin+'/api/login',data={'name':'Admin','password':'testpassword'},headers={'X-Dispatch':'1'})
            page.goto(origin+'/office');office_setting(page,'connection-settings').click()
            form=page.locator('#officeConnectionSettings');expect(form).to_be_visible();form.locator('[name=timeout_seconds]').fill('18')
            form.locator('button').click();expect(form).not_to_be_visible();cached(page,'office',18)
            assert fixture.call('connection-settings')[1]['timeout_seconds']==18
            page.route('**/api/connection-settings',lambda route:route.fulfill(json={'timeout_seconds':12,'revision':0}))
            page.evaluate("api('connection-settings')");cached(page,'office',18)
            page.unroute('**/api/connection-settings')
            office_setting(page,'connection-settings').click()
            expect(page.locator('.connectionSettingsDialog')).to_be_visible()
            audit=AUDIT.replace('document.querySelectorAll(',"document.querySelector('.connectionSettingsDialog').querySelectorAll(")
            for theme in ('classic-gray','harbor-blue','coastal-teal','midnight','coastyouth-red','glass-blue','glass-teal','glass-violet','glass-rose','glass-graphite'):
                for mode in ('light','dark'):
                    page.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode])
                    assert not page.evaluate(audit),(theme,mode,page.evaluate(audit))
            page.evaluate("document.body.dataset.retailTheme='classic-gray';document.documentElement.dataset.theme='light'")
            assert page.locator('.connectionSettingsDialog').evaluate('(e)=>e.getBoundingClientRect().width<=640')
            page.locator('#officeConnectionSettings [name=timeout_seconds]').fill('10')
            page.locator('.connectionSettingsDialog').screenshot(path=str(out/'OFFICE-Connection-Setting.png'))
            context.close();browser.close()
        print('PASS OFFICE editing, all app caches, first login, reload refresh, offline fallback, late native read, local cache recovery, and theme contrast')
    finally:fixture.close()


if __name__=='__main__':run()
