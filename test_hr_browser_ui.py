import os,base64,uuid,io
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_hr_browser import sample_pdf,sample_fields
from test_update_coordination import CoordinatorFixture
import server

f=CoordinatorFixture();out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
def post(path,**data):
    code,r=f.call('hr/'+path,data);assert code==200,r;return r
try:
    post('template',kind='deposit',title='SAMPLE ONLY — Browser form',edition='Preview',file=base64.b64encode(sample_pdf()).decode(),reviewed=True)
    template=next(t['id'] for t in f.call('hr/dashboard')[1]['templates'] if t['active'])
    post('browser-publish',template=template,fields=sample_fields(),attestations={'employee':'I confirm that the information I entered is accurate.','employer':'I confirm my review is accurate.'},reviewed=True)
    invite=post('invite',request=uuid.uuid4().hex,first='Jamie',middle='',last='Sample',phone='228-555-0100',email='jamie@example.test',username='Jamie Sample',employer=server.HR_EMPLOYERS[1])
    with sync_playwright() as pw:
        browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));ctx=browser.new_context(viewport={'width':1440,'height':1100});page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{f.port}/onboarding#'+invite['link'].split('#')[1]);page.locator('#inviteLogin [name=username]').fill(invite['username']);page.locator('#inviteLogin [name=password]').fill(invite['temporary_password']);page.locator('#inviteLogin button').click()
        page.locator('#newPassword [name=password]').fill('browser-test-password');page.locator('#newPassword [name=repeat]').fill('browser-test-password');page.locator('#newPassword button').click();page.locator('#consentForm [name=access]').check();page.locator('#consentForm [name=agree]').check();page.locator('#consentForm button').click()
        page.locator('[data-step=deposit]').click();page.locator('#completeBrowserForm').click();expect(page.locator('[data-form-field=name]')).to_be_visible();page.locator('[data-form-field=name]').fill('Jamie Sample');expect(page.locator('#browserSaveStatus')).to_have_text('All changes saved securely')
        page.screenshot(path=str(out/'Employee-Browser-Form.png'),full_page=False)
        # Navigation awaits the encrypted draft, then restores its value.
        pending_saves=[]
        page.route('**/api/hr/browser-save',lambda route:pending_saves.append(route))
        with page.expect_request('**/api/hr/browser-save'):
            page.locator('[data-form-field=name]').fill('Jamie Sample Updated')
        page.wait_for_function('browserWork && !!browserWork.saving')
        page.locator('[data-step=profile]').click();expect(page.locator('[data-form-field=name]')).to_be_visible()
        # A second click during the same save cannot overtake the first navigation.
        page.locator('[data-step=deposit]').click();expect(page.locator('[data-form-field=name]')).to_have_value('Jamie Sample Updated')
        assert len(pending_saves)==1
        pending_saves[0].continue_();page.unroute('**/api/hr/browser-save')
        expect(page.locator('#employeeProfile')).to_be_visible()
        page.locator('[data-step=deposit]').click();page.locator('#completeBrowserForm').click();expect(page.locator('[data-form-field=name]')).to_have_value('Jamie Sample Updated')
        # A failed save keeps the form open, and navigation succeeds after retry.
        page.route('**/api/hr/browser-save',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Temporary save failure"}'))
        page.locator('[data-form-field=name]').fill('Jamie Sample Retry');page.locator('[data-step=profile]').click()
        expect(page.locator('#status')).to_contain_text('Your changes are not saved yet')
        expect(page.locator('[data-form-field=name]')).to_have_value('Jamie Sample Retry')
        page.unroute('**/api/hr/browser-save');page.locator('[data-step=profile]').click();expect(page.locator('#employeeProfile')).to_be_visible()
        page.locator('[data-step=deposit]').click();page.locator('#completeBrowserForm').click();expect(page.locator('[data-form-field=name]')).to_have_value('Jamie Sample Retry')
        page.locator('#browserSign [name=reviewedDocument]').check();expect(page.locator('[data-reviewed]')).to_have_count(0)
        page.locator('#browserSign [name=acknowledged]').check();page.locator('#browserSign [name=name]').fill('Jamie Sample');page.locator('#browserSign [name=password]').fill('browser-test-password');page.locator('#browserSign').scroll_into_view_if_needed();page.screenshot(path=str(out/'Employee-Browser-Signing.png'))
        page.locator('#browserSign button').click();expect(page.locator('#status')).to_contain_text('Form signed and saved')
        expect(page.locator('#status a')).to_have_count(0)
        page.locator('[data-step=deposit]').click();page.locator('#completeBrowserForm').click();expect(page.locator('.browserDocument .badge')).to_contain_text('Signed and submitted');expect(page.locator('#browserSign')).to_have_count(0)
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'Employee-Browser-Form-Mobile.png'));assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Page overflows mobile viewport'
        assert not errors,errors;browser.close()
    print('PASS browser draft persistence, navigation, per-form signing, final-step navigation and mobile layout')
finally:f.close()
