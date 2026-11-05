"""Staff messaging and incoming alerts across separate browser sessions."""
from playwright.sync_api import expect, sync_playwright
from test_server import Tests as Fixture


def run():
    Fixture.setUpClass()
    try:
        Fixture.call('setup', {'name':'Admin', 'password':'testpassword'})
        Fixture.call('user', {'name':'Alex', 'password':'testpassword'})
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            base = f'http://127.0.0.1:{Fixture.port}'
            errors = []

            def session(name, width):
                page = browser.new_page(viewport={'width':width, 'height':900}, reduced_motion='reduce')
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(base)
                page.locator('#login [name=name]').fill(name)
                page.locator('#login [name=password]').fill('testpassword')
                with page.expect_response(lambda r: r.url.endswith('/api/comms/status')) as status:
                    page.locator('#login button').click()
                assert status.value.ok
                expect(page.locator('#sectionChooser')).to_be_visible()
                page.locator('#sectionChooserForm button').click()
                expect(page.locator('#sectionChooser')).to_be_hidden()
                return page

            alex = session('Alex', 390)
            admin = session('Admin', 1280)
            admin.locator('#storeMenuButton').click()
            admin.locator('#commsSection').click()
            admin.locator('#commNew').click()
            admin.locator('#commSearch').fill('alex')
            admin.locator('#commPeople').get_by_role('button', name='Alex').click()
            expect(admin.locator('#commTitle')).to_have_text('Alex')
            admin.locator('#commText').fill('Volunteer team meets at 3.')
            admin.locator('#commFile').set_input_files({
                'name':'agenda.txt', 'mimeType':'text/plain', 'buffer':b'Setup at 2:30'
            })
            admin.locator('#commComposer').get_by_role('button', name='Send').click()
            expect(admin.locator('#commContent')).to_contain_text('Volunteer team meets at 3.')
            expect(alex.locator('#commAlert')).to_be_visible(timeout=12000)
            expect(alex.locator('#storeMenuButton')).to_have_class('commHasUnread')
            alex.locator('#commAlert').click()
            expect(alex.locator('#commContent')).to_contain_text('Volunteer team meets at 3.')
            expect(alex.locator('#storeMenuButton')).not_to_have_class('commHasUnread')
            with alex.expect_download() as download:
                alex.get_by_role('link', name='agenda.txt').click()
            assert download.value.suggested_filename == 'agenda.txt'
            alex.locator('#commContent').get_by_role('button', name='Save', exact=True).click()
            expect(alex.locator('#commContent').get_by_role('button', name='Unsave')).to_be_visible()
            alex.locator('#commBack').click()
            alex.get_by_role('button', name='Saved messages', exact=True).click()
            expect(alex.locator('#commContent')).to_contain_text('Volunteer team meets at 3.')
            assert alex.evaluate('document.documentElement.scrollWidth<=innerWidth')
            alex.locator('#storeMenuButton').click()
            alex.locator('#dispatchSection').click()
            expect(alex.locator('#comms')).to_be_hidden()
            assert not errors, errors
            browser.close()
    finally:
        Fixture.tearDownClass()


if __name__ == '__main__':
    run()
