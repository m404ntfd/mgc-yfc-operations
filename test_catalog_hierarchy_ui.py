from test_ui_helpers import office_setting
"""Real browser coverage for setup add/select/copy/edit/delete and readable themes."""
import os,time,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_theme_contrast import AUDIT
import server
f=CoordinatorFixture();out=Path('output/preview');out.mkdir(exist_ok=True,parents=True)
server.POS_UPDATE_RELEASE=server.OFFICE_UPDATE_RELEASE={'version':'0.0.0','checked':time.time(),'attempted':time.time(),'checking':False}
def post(path,**body):
 code,result=f.call('pos/'+path,dict(request=uuid.uuid4().hex,**body));assert code==200,result;return result
try:
 post('settings',store='Thrift Mart',tax_bps=700,confirmed=True)
 product=post('product',name='SAMPLE chair',category='Furniture',price=2500,taxable=True)['product']
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'));p=b.new_page(viewport={'width':1440,'height':1050});errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept())
  p.goto(f'http://127.0.0.1:{f.port}/office');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();expect(p.locator('#officeTiles')).to_be_visible()
  for action in ['revenue-centers','departments','sub-departments','printing-categories','taxes']:expect(office_setting(p,action)).to_be_visible()
  assert office_setting(p,'catalog-options').count()==0
  office_setting(p,'revenue-centers').click();form=p.locator('#catalogOptionsForm')
  for action in ['copy','delete','edit']:expect(p.locator('[data-setup-action='+action+']')).to_be_disabled()
  form.locator('[name=entry_name]').fill('Retail sales');form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_text('Revenue Center added.');expect(p.locator('[aria-selected=true]')).to_contain_text('Retail sales')
  p.screenshot(path=str(out/'OFFICE-Revenue-Centers.png'))
  p.locator('[data-catalog-section=departments]').click();form.locator('[name=entry_name]').fill('Home goods');form.locator('[name=entry_parent]').select_option(label='Retail sales');form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_text('Department added.')
  p.locator('[data-setup-action=copy]').click();expect(form.locator('[name=entry_name]')).to_have_value('Home goods (copy)');expect(p.locator('[data-setup-row]')).to_have_count(1);form.locator('[name=entry_name]').fill('Apparel');form.locator('[type=submit]').click();expect(p.locator('[data-setup-row]')).to_have_count(2)
  p.locator('[data-setup-row="0"]').click();expect(p.locator('[data-setup-row="0"]')).to_have_attribute('aria-selected','true');p.locator('[data-setup-action=edit]').click();form.locator('[name=entry_name]').fill('Home & furniture');form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_text('Department updated.');p.screenshot(path=str(out/'OFFICE-Departments.png'))
  p.locator('[data-catalog-section=sub_departments]').click();expect(form.locator('[name=entry_name]')).to_have_value('');p.locator('[data-setup-row="0"]').click();p.locator('[data-setup-action=edit]').click();expect(form.locator('[name=entry_name]')).to_have_value('Furniture');form.locator('[name=entry_parent]').select_option(label='Home & furniture');form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_text('Sub Department updated.');expect(p.locator('[data-setup-row="0"]')).to_contain_text('Retail sales')
  p.locator('[data-setup-action=delete]').click();expect(p.locator('#catalogSaved')).to_contain_text('assigned to a product');expect(p.locator('[data-setup-row]')).to_have_count(1)
  form.locator('[name=entry_name]').fill('Home decor');form.locator('[name=entry_parent]').select_option(label='Home & furniture');form.locator('[type=submit]').click();expect(p.locator('[data-setup-row]')).to_have_count(2);p.locator('[data-setup-row="0"]').click();p.screenshot(path=str(out/'OFFICE-Sub-Departments.png'))
  p.locator('[data-catalog-section=taxes]').click();expect(form.locator('[name=entry_parent]')).to_have_count(0);form.locator('[name=entry_name]').fill('SAMPLE sales tax');form.locator('[name=entry_rate]').fill('7.00');form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_text('tax added.')
  p.locator('[data-setup-action=copy]').click();expect(form.locator('[name=entry_rate]')).to_have_value('7');expect(p.locator('[data-setup-row]')).to_have_count(1);form.locator('[type=submit]').click();expect(p.locator('[data-setup-row]')).to_have_count(2);p.locator('[data-setup-action=delete]').click();expect(p.locator('#catalogSaved')).to_contain_text('deleted.');expect(p.locator('[data-setup-row]')).to_have_count(1)
  p.locator('[data-setup-row="0"]').focus();p.keyboard.press('Enter');expect(p.locator('[data-setup-action=edit]')).to_be_enabled();p.screenshot(path=str(out/'OFFICE-Tax-Setup.png'))
  p.locator('[data-catalog-section=printing]').click();form.locator('[name=entry_name]').fill('Warehouse');form.locator('[type=submit]').click();expect(p.locator('#catalogSaved')).to_have_text('printing category added.')
  themes=['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+x for x in ['blue','teal','violet','rose','graphite']]
  for section in ['revenue_centers','departments','sub_departments','taxes','printing']:
   p.locator('[data-catalog-section='+section+']').click();p.locator('[data-setup-row="0"]').click()
   for theme in themes:
    for mode in ['light','dark']:
     p.evaluate('([t,m])=>{document.body.dataset.retailTheme=t;document.documentElement.dataset.theme=m}',[theme,mode]);p.wait_for_timeout(80)
     issues=p.evaluate(AUDIT);assert not issues,(section,theme,mode,issues)
   if section=='departments':
    p.evaluate("document.body.dataset.retailTheme='midnight';document.documentElement.dataset.theme='dark'");p.screenshot(path=str(out/'OFFICE-Departments-Dark.png'))
  p.evaluate("document.body.dataset.retailTheme='classic-gray';document.documentElement.dataset.theme='light'")
  p.locator('dialog[open] .flowClose').click();office_setting(p,'catalog').click();p.locator('#flowProductChoice').select_option(product['id']);expect(p.locator('#flowProductForm [name=category]')).to_have_value('Furniture');expect(p.locator('.catalogAssignment')).to_contain_text('Home & furniture');p.screenshot(path=str(out/'OFFICE-Item-Department-Assignment.png'))
  assert not errors,errors;b.close()
 print('PASS setup add, selection, editing, copy, safe deletion, keyboard selection, hierarchy assignments and 100 theme/mode checks. Screens use sample data.')
finally:f.close()
