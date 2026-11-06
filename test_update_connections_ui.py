import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_server import Tests as Fixture


def run():
    Fixture.setUpClass()
    try:
        Fixture.call('setup',dict(name='Admin',password='testpassword'))
        Fixture.call('user',dict(name='Staff',password='testpassword'))
        Fixture.call('logout',{})
        origin=f'http://127.0.0.1:{Fixture.port}'
        with sync_playwright() as pw:
            browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
            errors=[]
            def login(name):
                context=browser.new_context(viewport={'width':1280,'height':1000},reduced_motion='reduce')
                page=context.new_page()
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(origin)
                page.locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
                expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
                if page.locator('#profileWelcomeSkip').is_visible():page.locator('#profileWelcomeSkip').click()
                return page
            admin=login('Admin');staff=login('Staff')
            admin.route('**/api/update-check',lambda route:route.fulfill(json=dict(available=True,latest='0.39.1',current='0.39.0',notes='Test release')))
            admin.locator('#serverUpdateButton').click()
            expect(admin.locator('#updateConnectionsStatus')).to_contain_text('1 other signed-in connection')
            expect(admin.locator('#updateConnectionsList')).to_contain_text('Staff')
            expect(admin.locator('#installUpdate')).to_be_disabled()
            expect(staff.locator('#updateConnectionsPanel')).to_be_hidden()
            # A second tab under the administrator's same session is also a blocker.
            second=admin.context.new_page();second.goto(origin)
            expect(second.locator('#app')).to_be_visible()
            admin.locator('#refreshUpdateConnections').click()
            expect(admin.locator('#updateConnectionsStatus')).to_contain_text('2 other signed-in connections')
            second.evaluate('sendConnectionPresence(true)');second.close()
            staff.locator('#logout').click();expect(staff.locator('#auth')).to_be_visible()
            admin.locator('#refreshUpdateConnections').click()
            expect(admin.locator('#updateConnectionsStatus')).to_have_text('No other signed-in connections reported.')
            expect(admin.locator('#installUpdate')).to_be_enabled()
            # A new login after the UI check cannot bypass the server guard.
            def race(route):
                Fixture.call('login',dict(name='Staff',password='testpassword'))
                route.continue_()
            admin.route('**/api/update-install',race)
            admin.on('dialog',lambda dialog:dialog.accept())
            admin.locator('#installUpdate').click()
            expect(admin.locator('#updateStatus')).to_contain_text('Update blocked')
            expect(admin.locator('#installUpdate')).to_be_disabled()
            artifacts=Path(os.environ.get('TEST_ARTIFACTS',Fixture.tmp.name));artifacts.mkdir(parents=True,exist_ok=True)
            admin.set_viewport_size({'width':1280,'height':1400})
            admin.locator('#updateConnectionsPanel').evaluate("element => element.scrollIntoView({block:'center'})")
            admin.locator('#updateConnectionsPanel').screenshot(path=str(artifacts/'update-connections.png'))
            admin.route('**/api/admin/update-connections',lambda route:route.fulfill(status=503,json={'error':'Unavailable'}))
            admin.locator('#refreshUpdateConnections').click()
            expect(admin.locator('#updateConnectionsStatus')).to_contain_text('Connection status unavailable')
            expect(admin.locator('#installUpdate')).to_be_disabled()
            assert not errors,errors
            browser.close()
    finally:Fixture.tearDownClass()


if __name__=='__main__':run()
