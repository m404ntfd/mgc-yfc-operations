"""Exercise role filters, user tabs, access preservation, and responsive settings."""
import os,json,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_server import Tests as F

def run():
 F.setUpClass()
 try:
  F.call('setup',dict(name='Admin',password='testpassword'))
  for name in ['Employee','Limited']:F.call('user',dict(name=name,password='testpassword'))
  original={'view_schedule':True,'submit_receipts':False,'show_search':True,'export_payroll':False}
  F.call('admin/permissions',dict(name='Employee',grants=original))
  original=next(u for u in F.call('admin/permission-catalog')[1]['users'] if u['name']=='Employee')['grants']
  F.call('admin/permissions',dict(name='Limited',grants={'manage_roles':True,'submit_receipts':True}))
  ident=F.call('roles',dict(name='Office team',grants={'view_schedule':True,'submit_receipts':True,'export_payroll':True}))[1]['id']
  db=Path(F.tmp.name)/'schedule.db'
  with sqlite3.connect(db) as c:
   c.execute("INSERT INTO jobs VALUES('keep-reservation',3,?)",(json.dumps(dict(type='Pickup',customer='Sample reservation',start='2026-12-01T09:00',end='2026-12-01T10:00',notes='Keep unchanged')),))
   c.execute("INSERT INTO photos VALUES('keep-reservation',0,?)",(b'preserved-attachment',))
   account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
   c.execute("INSERT INTO work_periods VALUES(901,?,100,NULL,'Office',NULL)",(account,))
   c.execute('INSERT INTO work_breaks VALUES(902,901,200,NULL)')
  c.close()
  def records():
   with sqlite3.connect(db) as c:result={t:c.execute('SELECT * FROM '+t).fetchall() for t in ['jobs','photos','work_periods','work_breaks','work_time_card_audit']}
   c.close()
   return result
  before=records()
  with sync_playwright() as pw:
   browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
   errors=[]
   def login(name):
    page=browser.new_page(viewport={'width':1360,'height':1100},reduced_motion='reduce');page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}');page.locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
    if page.locator('#profileWelcomeSkip').is_visible():page.locator('#profileWelcomeSkip').click()
    page.locator('#settingsTab').click();return page
   page=login('Admin');out=Path(os.environ.get('TEST_ARTIFACTS',F.tmp.name));out.mkdir(exist_ok=True,parents=True)
   expect(page.locator('#settingsSubcategories')).to_be_visible();page.screenshot(path=str(out/'settings-menu.png'))
   page.locator('#settingsSubcategories').get_by_role('button',name='Roles',exact=True).click()
   page.locator('#roleSelect').select_option(str(ident));expect(page.locator('#roleName')).to_have_value('Office team')
   page.locator('[data-role-tab=permissions]').click()
   page.locator('#roleCategories select').select_option('Receipts & Accounting')
   page.locator('#roleCategories input').fill('Submit receipts')
   page.locator('#roleCategories').get_by_role('button',name='Disable shown',exact=True).click()
   expect(page.locator('[data-role-grant=submit_receipts]')).not_to_be_checked()
   page.locator('#roleForm [type=submit]').click();expect(page.locator('#roleStatus')).to_contain_text('Role saved')
   saved=next(r for r in F.call('roles')[1]['roles'] if r['id']==ident)['grants']
   assert saved['view_schedule'] and saved['export_payroll'] and not saved['submit_receipts'],saved
   page.locator('[data-role-tab=permissions]').click();page.set_viewport_size({'width':1360,'height':1800});page.locator('#rolesArea').evaluate("element => element.scrollIntoView({block:'center'})");page.locator('#rolesArea').screenshot(path=str(out/'role-permissions.png'));page.set_viewport_size({'width':1360,'height':1100})
   page.locator('[data-role-grant=export_payroll]').uncheck();page.locator('#roleForm').get_by_role('button',name='Cancel changes').click()
   assert next(r for r in F.call('roles')[1]['roles'] if r['id']==ident)['grants']['export_payroll']
   page.locator('#openUsers').click();page.locator('[data-password=Employee]').click()
   expect(page.locator('#userEditor_properties')).to_be_visible();page.screenshot(path=str(out/'user-setup.png'))
   page.locator('[data-user-tab=role]').click();expect(page.locator('#userRoleSummary')).to_contain_text('Individual access')
   assert page.locator('#passwordDialog [data-grant]').count()==0
   page.locator('#savePermissions').click();expect(page.locator('#permissionMessage')).to_contain_text('retained')
   assert next(u for u in F.call('admin/permission-catalog')[1]['users'] if u['name']=='Employee')['grants']==original
   page.locator('#employeeRole').select_option(str(ident));page.locator('#savePermissions').click();expect(page.locator('#permissionMessage')).to_contain_text('Role assigned')
   page.locator('[data-user-tab=view]').click();expect(page.locator('#userAccessPreview')).to_contain_text('Payroll export')
   page.locator('[data-user-tab=personal]').click();expect(page.locator('#userPersonalForm [type=submit]')).to_be_enabled();page.locator('#userPersonalForm [name=first]').fill('Sample');page.locator('#userPersonalForm [type=submit]').click();expect(page.locator('#userPersonalStatus')).to_contain_text('saved')
   page.locator('[data-user-tab=role]').click();page.locator('#employeeRole').select_option('');page.locator('#savePermissions').click();expect(page.locator('#permissionMessage')).to_contain_text('retained')
   assert next(u for u in F.call('admin/permission-catalog')[1]['users'] if u['name']=='Employee')['grants']==original
   page.locator('#editIndividualAccess').click();page.locator('#individualTools input').fill('Submit receipts');page.locator('[data-grant=submit_receipts]').check();page.locator('#individualCancel').click()
   assert next(u for u in F.call('admin/permission-catalog')[1]['users'] if u['name']=='Employee')['grants']==original
   page.locator('#editIndividualAccess').click();page.locator('#individualTools input').fill('Submit receipts');page.locator('[data-grant=submit_receipts]').check();page.locator('#individualSave').click();expect(page.locator('#permissionMessage')).to_contain_text('Individual permissions saved')
   stored=next(u for u in F.call('admin/permission-catalog')[1]['users'] if u['name']=='Employee')['grants'];assert stored==dict(original,submit_receipts=True)
   page.set_viewport_size({'width':390,'height':900});page.locator('[data-user-tab=properties]').click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(out/'user-setup-mobile.png'))
   page.locator('#passwordClose').click();page.locator('#settingsCategories').get_by_role('button',name='Application Settings',exact=True).click()
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.locator('#settingsSubcategories').get_by_role('button',name='Appearance',exact=True).click();page.locator('#appearanceMode').select_option('dark');expect(page.locator('html')).to_have_attribute('data-theme','dark');page.locator('#appearanceSettings .settingsBack').click() if page.locator('#appearanceSettings').count() else page.locator('.settingsBack:visible').click()
   page.screenshot(path=str(out/'settings-menu-dark-mobile.png'))
   limited=login('Limited');limited.locator('#settingsSubcategories').get_by_role('button',name='Roles',exact=True).click();limited.locator('#roleSelect').select_option(str(ident));limited.locator('[data-role-tab=permissions]').click();expect(limited.locator('[data-role-grant=export_payroll]')).to_be_disabled()
   limited.locator('#roleCategories').get_by_role('button',name='Disable shown').click();expect(limited.locator('[data-role-grant=export_payroll]')).to_be_checked()
   assert records()==before,'Account UI changed operational records'
   assert not errors,errors
   browser.close()
 finally:F.tearDownClass()
 print('PASS role filtering, hidden-grant preservation, assignment restoration, cancel, personal details, limited permissions, responsive layout, and unchanged operational records')
if __name__=='__main__':run()
