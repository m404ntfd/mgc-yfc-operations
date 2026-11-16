"""Protected request photos stay inside the signed-in app; synthetic data only."""
import base64
import datetime as dt
import io
import os

from PIL import Image
from test_update_coordination import CoordinatorFixture
import server


def seed_photos(f):
    photos = []
    for color in ('seagreen', 'steelblue'):
        out = io.BytesIO()
        Image.new('RGB', (240, 160), color).save(out, 'JPEG')
        photos.append(base64.b64encode(out.getvalue()).decode())
    assert f.call('vehicle', {'name': 'Test truck'})[0] == 200
    assert f.call('admin/permissions', {'name': 'Employee', 'can_create': False, 'see_requests': True})[0] == 200
    assert f.call('admin/permissions', {'name': 'Second', 'can_create': False, 'see_requests': True})[0] == 200
    employee = f.client('p')
    assert f.call('login', {'name': 'Employee', 'password': 'testpassword'}, employee)[0] == 200
    assert f.call('save', {'customer': 'Sample request', 'type': 'Pickup', 'status': 'Requested', 'photos': photos}, employee)[0] == 200
    day = dt.date.today().isoformat()
    assert f.call('save', {'customer': 'Sample appointment', 'type': 'Delivery', 'status': 'Scheduled',
                          'start': day+'T09:00', 'end': day+'T10:00', 'address': 'Test address',
                          'phone': '228-555-0100', 'items': 'Test item', 'vehicle': 'Test truck', 'photos': photos})[0] == 200
    state = f.call('state')[1]
    return state['requests'][0], state['jobs'][0]


def run():
    from playwright.sync_api import sync_playwright, expect
    f = CoordinatorFixture()
    try:
        request, appointment = seed_photos(f)
        with server.connect() as db:
            before_jobs = [tuple(r) for r in db.execute('SELECT * FROM jobs ORDER BY id')]
            before_photos = [tuple(r) for r in db.execute('SELECT * FROM photos ORDER BY job,position')]
        base = f'http://127.0.0.1:{f.port}'
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'))
            # A separate browser does not inherit the desktop session. Access must stay protected.
            outsider = browser.new_context()
            photo_path = f'/api/photo/{request["id"]}/0'
            assert outsider.request.get(base+photo_path).status == 401
            assert outsider.request.post(base+'/api/login', data={'name': 'Second', 'password': 'testpassword'}, headers={'X-Dispatch': '1'}).status == 200
            assert outsider.request.get(base+photo_path).status == 403
            outsider.close()
            for mobile in (False, True):
                context = browser.new_context(viewport={'width': 390 if mobile else 1440, 'height': 844 if mobile else 1000}, is_mobile=mobile, has_touch=mobile)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base+'/')
                page.locator('#login [name=name]').fill('Admin')
                page.locator('#login [name=password]').fill('testpassword')
                page.locator('#login button').click()
                if not mobile:
                    page.locator('#sectionChooserForm button').click()
                page.locator('#requestsButton').click()

                def view(button, index):
                    button.tap() if mobile else button.click()
                    expect(page.locator('#photoPreviewDialog')).to_be_visible()
                    page.wait_for_function('() => document.querySelector("#largePhoto").naturalWidth === 240')
                    expect(page.locator('#photoPreviewTitle')).to_contain_text(f'Photo {index+1}')
                    assert len(context.pages) == 1 and page.url == base+'/'
                    expect(page.locator('#photoPreviewError')).to_be_empty()
                    page.locator('#closePhotoPreview').click()
                    page.wait_for_function('() => !document.querySelector("#largePhoto").hasAttribute("src")')

                view(page.locator('#requestsList .photoLink').nth(0), 0)
                view(page.locator('#requestsList .photoLink').nth(1), 1)
                page.locator('[data-review]').click()
                page.locator('#jobForm [name=notes]').fill('Unsaved note must survive photo viewing')
                view(page.locator('#reviewPhotos [data-preview-photo]').nth(1), 1)
                expect(page.locator('#editor')).to_be_visible()
                expect(page.locator('#jobForm [name=notes]')).to_have_value('Unsaved note must survive photo viewing')
                # The test deliberately discards only its synthetic draft.
                page.on('dialog', lambda dialog: dialog.accept())
                page.locator('#close').click()
                page.locator(f'[data-expand="{appointment["id"]}"]').click()
                view(page.locator('#jobs .photoLink').nth(0), 0)
                # A missing attachment stays in the app and reports a recoverable error.
                page.route('**'+photo_path, lambda route: route.fulfill(status=404, content_type='application/json', body='{"error":"Not found"}'))
                page.locator('#requestsList .photoLink').nth(0).click()
                expect(page.locator('#photoPreviewError')).to_contain_text('Unable to load this photo')
                page.locator('#closePhotoPreview').click()
                page.unroute('**'+photo_path)
                view(page.locator('#requestsList .photoLink').nth(0), 0)
                assert not errors, errors
                context.close()
            browser.close()
        with server.connect() as db:
            assert before_jobs == [tuple(r) for r in db.execute('SELECT * FROM jobs ORDER BY id')]
            assert before_photos == [tuple(r) for r in db.execute('SELECT * FROM photos ORDER BY job,position')]
        print('PASS request photo desktop/mobile previews, permissions, draft and attachment preservation')
    finally:
        f.close()


if __name__ == '__main__':
    run()
