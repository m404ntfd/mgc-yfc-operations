import os,uuid,datetime as dt,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
import server
f=CoordinatorFixture();out=Path('test-artifacts');out.mkdir(exist_ok=True)
def post(path,**data):
 code,r=f.call('pos/'+path,dict(request=uuid.uuid4().hex,**data));assert code==200,r;return r
try:
 post('settings',store='CoastYouth Retail',tax_bps=700,confirmed=True)
 for name,category,price,qty in [('Happy Camper shirt','T-Shirts',1800,3),('Paperback book','Books',399,4),('Desk lamp','Home',1200,2)]:
  post('product',name=name,category=category,price=price,taxable=True)
  cart=post('new')['cart'];cart=post('add',cart=cart['id'],revision=cart['revision'],name=name,category=category,price=price,quantity=qty,taxable=True)['cart'];post('cash',cart=cart['id'],revision=cart['revision'],tender=10000)
 f.call('admin/clock-pin',dict(name='Employee',pin='654321'))
 f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
 with server.connect() as c:
  account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
  c.execute('INSERT INTO work_periods VALUES(?,?,?,?,?,?)',(123,account,time.time()-7200,None,'Store',None))
 with sync_playwright() as pw:
  b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));ctx=b.new_context(viewport={'width':1440,'height':1000});p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));url=f'http://127.0.0.1:{f.port}'
  p.goto(url+'/office');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();expect(p.locator('[data-office-action=reports]')).to_be_visible()
  p.locator('[data-office-action=report-center]').click();expect(p.locator('.rrStatus')).to_contain_text('Net sales exclude');p.screenshot(path=str(out/'Next-OFFICE-Analysis.png'))
  p.locator('.rrFilters [name=kind]').select_option('cash');p.locator('.rrFilters button').first.click();expect(p.locator('.rrTable')).to_contain_text('100.54')
  p.locator('#officeBack').click();p.locator('[data-office-action=users]').click();p.locator('#officeUserRows tr').filter(has_text='Employee').get_by_role('button',name='Edit user').click();expect(p.locator('.officeUserWizard')).to_be_visible();p.screenshot(path=str(out/'Next-OFFICE-User.png'))
  p.locator('[data-user-pane="2"]').click();expect(p.locator('#officeContactDetails')).to_be_visible();p.locator('#officeContactDetails [name=city]').fill('Mobile');p.locator('#officeContactDetails button').click();expect(p.locator('#officeUserSaveStatus')).to_contain_text('saved');p.screenshot(path=str(out/'Next-OFFICE-Personal.png'))
  p.evaluate("document.querySelector('.officeUserWizard').close()");p.locator('#officeBack').click();p.locator('[data-office-action=labor-reports]').click();expect(p.locator('.rrTable')).to_contain_text('Employee');p.screenshot(path=str(out/'Next-OFFICE-Labor.png'))
  p.goto(url);p.wait_for_timeout(300);
  if p.locator('#sectionChooserForm').is_visible():p.locator('#sectionChooserForm [name=section][value=print]').check();p.locator('#sectionChooserForm button').click()

  if p.get_by_role('button',name='Skip for now',exact=True).is_visible():p.get_by_role('button',name='Skip for now',exact=True).click()
  p.evaluate("storeSection('print')");expect(p.locator('#printPurpose > .retailReport .rrResult > .rrMetrics')).to_be_visible();p.screenshot(path=str(out/'Next-Dashboard-Desktop.png'))
  p.set_viewport_size({'width':390,'height':844});p.locator('#printPurpose').scroll_into_view_if_needed();p.screenshot(path=str(out/'Next-Dashboard-Mobile.png'));assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  desk=b.new_context(viewport={'width':1280,'height':900}).new_page();desk.goto(url+'/pos');expect(desk.locator('#deskPinForm')).to_be_visible();desk.screenshot(path=str(out/'Next-DESK-PIN.png'));desk.locator('#deskPinForm [name=pin]').fill('654321');desk.locator('#deskPinForm button.primary').click();expect(desk.locator('#cashier')).to_have_text('Employee');desk.locator('#signOut').click();expect(desk.locator('#deskPinForm')).to_be_visible();expect(desk.locator('#posRoot')).to_be_hidden();expect(desk.locator('#deskPinForm [name=pin]')).to_have_value('');assert not errors,errors
  b.close()
 print('PASS dashboard, OFFICE reports and shared user editor, responsive layout, PIN sign-in and logout; screenshots saved.')
finally:f.close()
