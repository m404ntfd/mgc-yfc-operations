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
    for t in f.call('hr/dashboard')[1]['templates']:
        if t['id'].startswith('source-'):post('browser-source-activate',template=t['id'],reviewed=True)
    invite=post('invite',request=uuid.uuid4().hex,first='Jamie',middle='',last='Sample',phone='228-555-0100',email='jamie@example.test',username='Jamie Sample',employer=server.HR_EMPLOYERS[1])
    with sync_playwright() as pw:
        browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));ctx=browser.new_context(viewport={'width':1440,'height':1100});page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f'http://127.0.0.1:{f.port}/onboarding#'+invite['link'].split('#')[1]);page.locator('#inviteLogin [name=username]').fill(invite['username']);page.locator('#inviteLogin [name=password]').fill(invite['temporary_password']);page.locator('#inviteLogin button').click()
        page.locator('#newPassword [name=password]').fill('browser-test-password');page.locator('#newPassword [name=repeat]').fill('browser-test-password');page.locator('#newPassword button').click();page.locator('#consentForm [name=access]').check();page.locator('#consentForm [name=agree]').check();page.locator('#consentForm button').click()
        page.locator('[data-step=profile]').click()
        for name,value in {'phone':'2285550100','address':'100 Test Street','city':'Gulfport','zip':'39501'}.items():page.locator('#employeeProfile [name='+name+']').fill(value)
        page.get_by_role('button',name='SAVE & CONTINUE',exact=True).click()
        expect(page.locator('#employeeSection h2')).to_contain_text('Background')
        page.locator('#completeBrowserForm').click();expect(page.locator('[data-form-field=bg_company]')).to_be_disabled()
        page.screenshot(path=str(out/'Employee-Original-Background.png'))
        for kind in ['w4','i9','ms']:
            page.locator('[data-step='+kind+']').click();page.locator('#completeBrowserForm').click()
            expect(page.locator('.browserPage img').first).to_be_visible()
            if kind=='w4':
                ssn=page.get_by_role('textbox',name='Social security number',exact=True);ssn.fill('123456789');page.locator('.browserDocument h2').click();expect(ssn).to_have_value('***-**-6789');ssn.focus();expect(ssn).to_have_value('123-45-6789');page.locator('.browserDocument h2').click();expect(page.locator('#browserSaveStatus')).to_have_text('All changes saved securely');assert ssn.evaluate('(el)=>browserWork.values[el.dataset.formField]')=='123-45-6789'
                saved=page.request.get(f'http://127.0.0.1:{f.port}/api/hr/browser-form?form='+page.evaluate('browserWork.key.form')).json();assert saved['values'][ssn.get_attribute('data-form-field')]=='123-45-6789'
            if kind=='i9':
                phone=page.get_by_role('textbox',name='Telephone Number',exact=True);phone.fill('2285550123');page.locator('.browserDocument h2').click();expect(phone).to_have_value('(228) 555-0123')
                date=page.get_by_role('textbox',name='Date of Birth mmddyyyy',exact=True);date.fill('03041990');page.locator('.browserDocument h2').click();expect(date).to_have_value('03/04/1990');expect(page.get_by_role('button',name='Open calendar for Date of Birth mmddyyyy',exact=True)).to_be_visible()
            expect(page.locator('[data-reviewed]')).to_have_count(0);expect(page.locator('[name=reviewedDocument]')).to_have_count(1)
            page.screenshot(path=str(out/('Employee-Original-'+kind+'.png')))
            assert page.locator('#employeeSection a[href*="/api/hr/template"]').count()==0
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'Employee-Original-Mobile.png'));assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors,errors;browser.close()
    print('PASS save-and-continue, source form overlays, no blank download links and mobile layout')
finally:f.close()
