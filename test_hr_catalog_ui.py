from test_ui_helpers import office_setting
import os,uuid,base64
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page
import server
f=CoordinatorFixture();out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
def post(path,**body):
 code,r=f.call(path,body);assert code==200,r;return r
try:
 post('pos/settings',request=uuid.uuid4().hex,store='Thrift Mart',tax_bps=700,confirmed=True)
 post('pos/catalog-options-save',request=uuid.uuid4().hex,revision=0,categories=['Clothing','Housewares','Furniture'],printing=['Front counter','Warehouse'],taxes=[dict(id='state',name='Mississippi sales tax',bps=700,store_id='thrift-mart'),dict(id='sample',name='SAMPLE local tax',bps=100,store_id='thrift-mart')])
 post('account/retail-theme',scope='user',theme='glass-blue',revision=0)
 post('hr/template',kind='w4',title='SAMPLE FORM — PREVIEW ONLY',edition='Sample',file=base64.b64encode(b'%PDF-1.4 SAMPLE ONLY').decode(),reviewed=True)
 invitation=post('hr/invite',request=uuid.uuid4().hex,first='Jamie',middle='',last='Sample',phone='228-555-0100',email='jamie@example.test',username='Jamie Sample',employer=server.HR_EMPLOYERS[1])
 with sync_playwright() as pw:
  browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));ctx=browser.new_context(viewport={'width':1440,'height':1050});p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));origin=f'http://127.0.0.1:{f.port}'
  p.goto(origin+'/office');expect(p.locator('#auth h2')).to_have_text('Sign In to CoastYouth Office');p.screenshot(path=str(out/'OFFICE-Glass-Sign-In.png'))
  password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();expect(p.locator('#officeTiles')).to_be_visible();office_setting(p,'catalog').click();form=p.locator('#flowProductForm');expect(form.locator('select[name=category]')).to_be_visible();form.locator('[name=name]').fill('SAMPLE Open-priced furniture');form.locator('[name=category]').select_option('Furniture');form.locator('[name=print_category]').select_option('Warehouse');form.locator('[name=open_priced]').check();expect(form.locator('[name=price]')).to_be_disabled();expect(form.locator('[name=price]')).to_have_value('OPEN PRICE SELECTED');form.locator('.taxDropdown summary').click();form.locator('[data-item-tax][value=state]').check();form.locator('[data-item-tax][value=sample]').check();p.screenshot(path=str(out/'OFFICE-Item-Setup.png'))
  p.locator('#officeBack').click();expect(p.locator('#itemDiscardLeave')).to_be_visible();p.screenshot(path=str(out/'OFFICE-Unsaved-Item.png'));p.locator('#itemKeepEditing').click();expect(form).to_be_visible();p.locator('#officeBack').click();p.locator('#itemSaveLeave').click();expect(p.locator('#officeTiles')).to_be_visible();office_setting(p,'catalog').click();p.locator('#flowProductChoice').select_option(index=1);expect(p.locator('[data-item-tax][value=sample]')).to_be_checked();p.locator('#officeBack').click()
  office_setting(p,'discount-rules').click();p.locator('[data-finance-tab=surcharges]').click();expect(p.locator('[name=max_surcharge]')).to_be_visible();expect(p.locator('[name=max_discount]')).to_be_hidden();p.locator('[data-finance-tab=cards]').click();expect(p.locator('[data-finance-panel=cards]')).to_contain_text('future updates');p.locator('#officeBack').click()
  office_setting(p,'hr-onboarding').click();frame=p.frame_locator('#hrOfficeFrame');expect(frame.locator('#adminSection')).to_contain_text('Jamie Sample');p.screenshot(path=str(out/'OFFICE-Onboarding-Dashboard.png'));frame.locator('[data-admin=invite]').click();p.screenshot(path=str(out/'OFFICE-New-Employee.png'))
  employee=browser.new_context(viewport={'width':1280,'height':1000});e=employee.new_page();e.on('pageerror',lambda x:errors.append(str(x)));e.goto(origin+'/onboarding#'+invitation['link'].split('#')[1]);e.locator('[name=username]').fill(invitation['username']);e.locator('[name=password]').fill(invitation['temporary_password']);e.locator('#inviteLogin button').click();expect(e.locator('#newPassword')).to_be_visible();e.locator('#newPassword [name=password]').fill('sample-secure-password');e.locator('#newPassword [name=repeat]').fill('sample-secure-password');e.locator('#newPassword button').click();expect(e.locator('#consentForm')).to_be_visible();e.screenshot(path=str(out/'Employee-Onboarding-Welcome.png'));e.locator('#helpBubble').click();e.locator('#helpForm textarea').fill('SAMPLE: Could you help me complete my paperwork?');e.locator('#helpForm button').click();expect(e.locator('#status')).to_contain_text('sent to HR');frame.locator('[data-admin=dashboard]').click();frame.locator('#refresh').click();expect(frame.locator('#adminSection')).to_contain_text('1');e.set_viewport_size({'width':390,'height':844});e.screenshot(path=str(out/'Employee-Onboarding-Mobile.png'));assert e.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors;browser.close()
finally:f.close()
print('PASS configured catalog editor, save/discard navigation, taxes, glass theme, HR dashboard, invitation and employee help')
