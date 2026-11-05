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
            alex.locator('#storeMenuButton').click()
            alex.get_by_role('button',name='My profile').click()
            png=alex.evaluate("""()=>{const canvas=document.createElement('canvas');canvas.width=canvas.height=24;
              const context=canvas.getContext('2d');context.fillStyle='green';context.fillRect(0,0,24,24);
              return Array.from(atob(canvas.toDataURL('image/png').split(',')[1]),c=>c.charCodeAt(0));}""")
            alex.locator('#profilePhotoInput').set_input_files({'name':'photo.png','mimeType':'image/png','buffer':bytes(png)})
            alex.get_by_role('button',name='Submit for approval').click()
            expect(alex.locator('#profilePhotoStatus')).to_contain_text('waiting for approval')
            pending=alex.locator('#profilePhotos img').get_attribute('src')
            photo_id=pending.split('/')[-2]
            assert alex.request.get(base+pending).ok
            assert admin.request.get(base+pending).ok
            assert admin.request.get(base+'/api/profile/photo/'+photo_id).status==404
            assert alex.request.get(base+'/api/profile/queue').status==403
            expect(alex.locator('#photoNotifications')).to_be_hidden()
            expect(admin.locator('#photoReviewCount')).to_have_text('1',timeout=10000)
            admin.locator('#photoNotifications').click()
            expect(admin.locator('#photoQueue')).to_contain_text('Alex')
            admin.locator('#photoQueue').get_by_role('button',name='Approve',exact=True).click()
            expect(admin.locator('#photoQueueStatus')).to_have_text('Picture approved.')
            assert admin.request.get(base+'/api/profile/photo/'+photo_id).ok
            assert admin.request.get(base+pending).status==404
            admin.locator('#closePhotoQueue').click()
            alex.locator('#closeProfilePhoto').click()
            admin.locator('#storeMenuButton').click()
            admin.locator('#commsSection').click()
            admin.locator('#commNew').click()
            admin.locator('#commSearch').fill('alex')
            expect(admin.locator('#commPeople img')).to_have_attribute('src','/api/profile/photo/'+photo_id)
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
            alex.once('dialog',lambda dialog:dialog.accept())
            alex.locator('#commContent').get_by_role('button', name='Delete for me').click()
            expect(alex.locator('#commContent')).not_to_contain_text('Volunteer team meets at 3.')
            expect(admin.locator('#commContent')).to_contain_text('Volunteer team meets at 3.')
            admin.locator('#commGroup').click()
            admin.locator('#commGroupName').fill('Volunteers')
            admin.locator('#commPeople').get_by_role('checkbox', name='Alex').check()
            admin.locator('#commCreateGroup').click()
            expect(admin.locator('#commTitle')).to_have_text('Volunteers')
            admin.locator('#commText').fill('Keep this group message.')
            admin.locator('#commComposer').get_by_role('button',name='Send').click()
            expect(admin.locator('#commContent')).to_contain_text('Keep this group message.')
            admin.locator('#commManageGroup').click()
            admin.locator('#commGroupName').fill('Volunteer Team')
            admin.locator('#commCreateGroup').click()
            expect(admin.locator('#commTitle')).to_have_text('Volunteer Team')
            admin.get_by_role('button',name='Hide group',exact=True).click()
            expect(admin.locator('#commGroups')).not_to_contain_text('Volunteer Team')
            admin.locator('#commHiddenGroups').click()
            admin.get_by_role('button',name='Restore group').click()
            expect(admin.locator('#commTitle')).to_have_text('Volunteer Team')
            expect(admin.locator('#commContent')).to_contain_text('Keep this group message.')
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
