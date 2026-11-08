from test_ui_helpers import password_login_page
import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
import server

def run():
 f=CoordinatorFixture();n=0
 def post(path,**data):
  nonlocal n
  n+=1;status,result=f.call('pos/'+path,dict(data,request=f'{n:032x}'));assert status==200,(status,result);return result
 try:
  post('settings',store='Thrift Mart',tax_bps=700,confirmed=True)
  for category,items in [('Clothing',[('Adult shirt',599),('Jeans',899),('Jacket',1499),('Children’s shirt',399)]),('Home',[('Table lamp',1299),('Picture frame',499),('Dinnerware set',1099)]),('Books & media',[('Paperback book',199),('Hardcover book',399),('DVD',299)]),('Furniture',[('Side table',2499),('Dining chair',1999)]),('Accessories',[('Handbag',799),('Belt',299),('Scarf',399)])]:
   for name,price in items:post('product',name=name,category=category,price=price,taxable=True)
  f.call('roles',dict(name='Retail staff',grants={'use_pos':True,'use_store_credit':True}))
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));context=b.new_context(viewport={'width':1366,'height':900});p=context.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));origin=f'http://127.0.0.1:{f.port}'
   p.goto(origin+'/office');password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();expect(p.locator('#officeTiles .officeTile')).to_have_count(32)
   out=Path(os.environ.get('TEST_ARTIFACTS','test-artifacts'));out.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(out/'CoastYouth-Retail-OFFICE-Preview.png'))
   p.locator('[data-office-action=users]').click();form=p.locator('#officeAddUser');form.locator('[name=name]').fill('Office sample staff');form.locator('[name=password]').fill('testpassword');form.locator('[name=confirm]').fill('testpassword');assert p.evaluate('unfinished()')
   form.locator('button').first.click();expect(p.locator('#officeUserRows')).to_contain_text('Office sample staff');assert not p.evaluate('changedForms.has(document.querySelector("#officeAddUser"))')
   p.locator('#officeRoleUser').select_option(label='Office sample staff');p.locator('#officeRoleChoice').select_option(label='Retail staff');p.locator('#officeUserRole button').first.click();expect(p.locator('#officeUserRows')).to_contain_text('Retail staff')
   p.screenshot(path=str(out/'CoastYouth-Retail-OFFICE-Users-Preview.png'))
   q=context.new_page();q.goto(origin+'/#retail-users');expect(q.locator('#userSettingsPanel')).to_be_visible();expect(q.locator('#userSettingsPanel')).to_contain_text('Office sample staff')
   q.locator('#userForm [name=name]').fill('Operations sample staff');q.locator('#userForm [name=password]').fill('testpassword');q.locator('#userForm button').click();expect(q.locator('#addUserMessage')).to_contain_text('successfully');p.locator('#officeUsersRefresh').click();expect(p.locator('#officeUserRows')).to_contain_text('Operations sample staff')
   form.locator('[name=name]').fill('office SAMPLE staff');form.locator('[name=password]').fill('testpassword');form.locator('[name=confirm]').fill('testpassword');form.locator('button').first.click();expect(p.locator('#posStatus')).not_to_have_text('User added to the shared directory. Assign a role to set their access.');form.locator('[type=reset]').click()
   with server.connect() as c:
    assert c.execute("SELECT COUNT(*) FROM users WHERE name='office sample staff'").fetchone()[0]==1
    assert c.execute("SELECT COUNT(*) FROM receipt_profiles WHERE name='office sample staff'").fetchone()[0]==1
   p.locator('#officeBack').click();p.locator('[data-office-action=catalog]').click();p.locator('#flowProductForm [name=name]').fill('OFFICE sample item');p.locator('#flowProductForm [name=category]').fill('Home');p.locator('#flowProductForm [name=price]').fill('6.50');p.locator('#flowProductForm button.primary').first.click();expect(p.locator('#flowProductStatus')).to_contain_text('Product saved')
   desk=context.new_page();desk.goto(origin+'/pos');expect(desk.locator('#posCatalog')).to_contain_text('OFFICE sample item');expect(desk.locator('#posSetup')).to_be_hidden();expect(desk.locator('#posAdmin')).to_be_hidden();expect(desk.locator('#posSetupShortcut')).to_be_hidden();expect(desk.locator('#navSetup')).to_be_hidden();desk.locator('#posNew').click();expect(desk.locator('#posCart')).to_contain_text('Saved on server');desk.locator('#posCatalog button').filter(has_text='Adult shirt').click();desk.locator('#posCatalog button').filter(has_text='Table lamp').click();expect(desk.locator('#posCart')).to_contain_text('$20.31');desk.screenshot(path=str(out/'CoastYouth-Retail-DESK-Preview.png'))
   desk.locator('#posPayNow').click();desk.locator('#posCash [name=tender]').fill('25');desk.locator('#posCash button.primary').click();expect(desk.locator('#posReceipt')).to_contain_text('Change: $4.69')
   p.locator('#officeBack').click();p.locator('[data-office-action=history]').click();p.locator('#posSaleList button').first.click();expect(p.locator('#officeReceipt')).to_be_visible();expect(p.locator('#posReceipt')).to_contain_text('Change: $4.69');p.emulate_media(media='print');expect(p.locator('#posReceipt')).to_be_visible();p.emulate_media(media='screen');p.locator('.receiptBack').click();p.locator('[data-office-action=roles]').click()
   # A user-management role can open OFFICE without checkout permission.
   f.call('admin/permissions',dict(name='Employee',grants={'manage_users':True},can_create=False,see_requests=False))
   restricted=b.new_page();restricted.goto(origin+'/office');password_login_page(restricted).locator('#login [name=name]').fill('Employee');restricted.locator('#login [name=password]').fill('testpassword');restricted.locator('#login button').click();expect(restricted.locator('[data-office-action=users]')).to_be_visible();expect(restricted.locator('[data-office-action=catalog]')).to_have_count(0)
   restricted.locator('[data-office-action=users]').click();expect(restricted.locator('#officeUserRows')).to_contain_text('Office sample staff')
   noaccess=b.new_page();noaccess.goto(origin+'/office');password_login_page(noaccess).locator('#login [name=name]').fill('Office sample staff');noaccess.locator('#login [name=password]').fill('testpassword');noaccess.locator('#login button').click();expect(noaccess.locator('#authError')).to_contain_text('OFFICE requires');expect(noaccess.locator('#posRoot')).to_be_hidden()
   for width,height in [(1366,768),(1024,768)]:
    p.set_viewport_size({'width':width,'height':height});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   assert not errors,errors;b.close()
 finally:f.close()
 print('PASS shared users in both directions, duplicate prevention, roles, OFFICE access, catalog sync, DESK and compact layouts')
if __name__=='__main__':run()
