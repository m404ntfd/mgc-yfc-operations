"""DESK payment entry/recovery and OFFICE advance report with sample employees."""
import os,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_cash_advances import CashAdvanceTests
from test_ui_helpers import password_login_page
from test_theme_contrast import AUDIT
import server

def run():
 fixture=CashAdvanceTests();fixture.setUp();f=fixture.f;out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
 server.POS_UPDATE_RELEASE=server.OFFICE_UPDATE_RELEASE={'version':'0.0.0','checked':time.time(),'attempted':time.time(),'checking':False}
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'));p=browser.new_page(viewport={'width':1440,'height':1000});errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept())
   origin=f'http://127.0.0.1:{f.port}'
   p.add_init_script("localStorage.setItem('coastyouth-retail-device','"+fixture.device+"')")
   def login(page,name,app='pos'):
    page.goto(origin+'/'+app);password_login_page(page).locator('#login [name=name]').fill(name);page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();expect(page.locator('#posRoot')).to_be_visible()
   login(p,'Admin');expect(p.locator('#cashAdvanceOpen')).to_be_visible()
   p.screenshot(path=str(out/'DESK-Cash-Advance-Button.png'))
   for width,height in [(1440,1000),(1366,768),(1024,768)]:
    p.set_viewport_size({'width':width,'height':height});p.locator('#cashAdvanceOpen').scroll_into_view_if_needed();rect=p.locator('#cashAdvanceOpen').bounding_box();assert rect and rect['x']+rect['width']<=width+1 and rect['y']+rect['height']<=height+1
   p.set_viewport_size({'width':1440,'height':1000});p.locator('#cashAdvanceOpen').click();form=p.locator('#cashAdvanceForm');expect(form).to_be_visible()
   assert fixture.people['Admin'] not in form.locator('[name=employee] option').evaluate_all('(opts)=>opts.map(x=>x.value)')
   form.locator('[name=employee]').select_option(fixture.people['Employee']);form.locator('[name=amount]').fill('25.00');form.locator('[name=reason]').fill('SAMPLE approved employee advance')
   for theme in ['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+x for x in ['blue','teal','violet','rose','graphite']]:
    for mode in ['light','dark']:
     p.evaluate('([t,m])=>{document.body.dataset.retailTheme=t;document.documentElement.dataset.theme=m}',[theme,mode]);p.wait_for_timeout(40);issues=p.evaluate(AUDIT.replace('document.querySelectorAll(',"document.querySelector('#cashAdvanceDialog').querySelectorAll("));assert not issues,(theme,mode,issues)
   p.evaluate("document.body.dataset.retailTheme='harbor-blue';document.documentElement.dataset.theme='light'");p.screenshot(path=str(out/'DESK-Employee-Cash-Advance.png'))
   form.locator('[type=submit]').click();expect(p.locator('.advanceReceipt')).to_contain_text('Advance #1 recorded');expect(p.locator('.advanceAmount')).to_have_text('$25.00');p.locator('#advanceDone').click()
   # Drop the successful reply, then reload the page. The saved request is resolved,
   # not sent again as a second payment or a second cash movement.
   p.route('**/api/pos/cash-advance',lambda route:(route.fetch(),route.abort()))
   p.locator('#cashAdvanceOpen').click();form=p.locator('#cashAdvanceForm');form.locator('[name=employee]').select_option(fixture.people['Second']);form.locator('[name=amount]').fill('10.00');form.locator('[name=reason]').fill('SAMPLE connection recovery')
   form.locator('[type=submit]').click();expect(p.locator('#cashAdvanceDialog .flowError')).to_contain_text('unconfirmed');expect(form.locator('[name=amount]')).to_be_disabled();assert p.evaluate('unfinished()')
   p.reload();expect(p.locator('#cashAdvanceOpen')).to_contain_text('Check pending');p.locator('#cashAdvanceOpen').click();expect(p.locator('.advanceReceipt')).to_contain_text('already recorded');expect(p.locator('.advanceAmount')).to_have_text('$10.00');p.locator('#advanceDone').click();assert not p.evaluate('cashAdvancePending()')
   with server.connect() as c:assert c.execute('SELECT COUNT(*) FROM retail_cash_advances').fetchone()[0]==2
   p.unroute('**/api/pos/cash-advance')
   # A tracked cash advance reduces the drawer and remains visible in its report.
   fixture.drawers();p.locator('#cashAdvanceOpen').click();form=p.locator('#cashAdvanceForm');form.locator('[name=employee]').select_option(fixture.people['Employee']);form.locator('[name=amount]').fill('15.00');form.locator('[name=reason]').fill('SAMPLE tracked drawer advance');form.locator('[type=submit]').click();expect(p.locator('.advanceReceipt')).to_contain_text('Advance #3 recorded');p.locator('#advanceDone').click()
   assert f.call('pos/drawers')[1]['drawers'][0]['expected']==8500
   p.goto(origin+'/office');expect(p.locator('[data-office-action=cash-advance-report]')).to_be_visible();p.locator('[data-office-action=cash-advance-report]').click();expect(p.locator('.rrResult')).to_contain_text('$50.00');expect(p.locator('.rrResult tbody tr')).to_have_count(3)
   p.set_viewport_size({'width':1440,'height':1400});p.screenshot(path=str(out/'OFFICE-Employee-Cash-Advances.png'));p.set_viewport_size({'width':1440,'height':1000})
   p.locator('.rrFilters [name=employee]').fill('Employee');p.locator('.rrFilters button[type=submit],.rrFilters button:not([type])').first.click();expect(p.locator('.rrResult tbody tr')).to_have_count(2);expect(p.locator('.rrResult')).to_contain_text('$40.00')
   p.evaluate("()=>{window.print=()=>{window.advancePrint=document.querySelector('#retailPrintReport').innerText}}");p.locator('[data-rr-print]').click();assert 'Employee cash advances' in p.evaluate('window.advancePrint') and 'Thrift Mart' in p.evaluate('window.advancePrint')
   with p.expect_download() as download:p.locator('[data-rr-export]').click()
   assert download.value.suggested_filename=='CoastYouth-cash-advances.csv'
   p.locator('#officeBack').click();p.locator('[data-office-action=report-center]').click();p.locator('.rrFilters [name=kind]').select_option('drawer');p.locator('.rrFilters button:not([type])').click();expect(p.locator('.rrResult')).to_contain_text('Employee advances');expect(p.locator('.rrResult tbody')).to_contain_text('50.00');p.screenshot(path=str(out/'OFFICE-Drawer-Advances.png'))
   # Report-only permission works without checkout or all-sales access.
   f.call('admin/permissions',dict(name='Second',grants={'view_cash_advances':True},can_create=False,see_requests=False))
   viewer=browser.new_page();login(viewer,'Second','office');expect(viewer.locator('[data-office-action=cash-advance-report]')).to_be_visible();expect(viewer.locator('[data-office-action=report-center]')).to_have_count(0);viewer.locator('[data-office-action=cash-advance-report]').click();expect(viewer.locator('.rrResult')).to_contain_text('$50.00')
   f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False));staff=browser.new_page();login(staff,'Employee');expect(staff.locator('#cashAdvanceOpen')).to_be_hidden()
   assert not errors,errors;browser.close()
 finally:fixture.tearDown()
 print('PASS DESK advance button/form, 20 themes, cash confirmation, lost-response/reload recovery, drawer totals, OFFICE filters/print/export, and permission separation.')

if __name__=='__main__':run()
