"""Exercise actual pages with isolated fixtures and capture preview screens."""
import os,uuid,datetime as dt
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page

def run():
 f=CoordinatorFixture();out=Path('test-artifacts/store-preview');out.mkdir(exist_ok=True);errors=[]
 def post(path,**data):
  status,r=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert status==200,r;return r
 try:
  post('settings',store='Thrift Mart',tax_bps=700,confirmed=True)
  profile=f.call('pos/stores')[1]['stores'][1]
  post('store-save',**dict(profile,tax_bps=700,confirmed=True,receipt=dict(address='Binopoly · SAMPLE PREVIEW',phone='Sample location',logo='',policy='Store return policy appears here.',footer='Thank you for shopping Binopoly!')))
  pid=post('product-save',name='Bin merchandise by the pound',category='Weighed goods',price=200,taxable=True,rules=dict(store_id='binopoly',sold_by_weight=True))['ids'][0]
  post('product-save',name='Individually priced item',category='Individual items',price=500,taxable=True,rules=dict(store_id='binopoly'))
  tid=post('terminal-save',name='Binopoly · Register 1',device='2'*32,enabled=True)['id'];post('store-terminal',terminal=tid,store_id='binopoly',previous='thrift-mart')
  post('thrift-settings',revision=0,tags=[],donations=True,loyalty=True,stack_tags=False,earn_cents=100,reward_points=100,reward_cents=500)
  customer=post('thrift-customer-save',name='Sample Customer',contact='PREVIEW ONLY',marketing=False)['customer']
  for i in range(4):
   c=post('new')['cart'];c=post('add',cart=c['id'],revision=c['revision'],name='Sample thrift item',category='Clothing',quantity=1,price=1500,taxable=False)['cart']
   if i<3:c=post('thrift-donation',cart=c['id'],revision=c['revision'],amount=100+i*50)['cart']
   post('cash',cart=c['id'],revision=c['revision'],tender=2000)
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None,headless=True)
   page=b.new_page(viewport={'width':1440,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)))
   origin=f'http://127.0.0.1:{f.port}';page.goto(origin+'/office');password_login_page(page).locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();expect(page.locator('#officeHub')).to_be_visible()
   expect(page.locator('#retailStoreBadge')).to_have_text('Thrift Mart')
   page.locator('[data-office-action=stores-programs]').click();expect(page.locator('#storePrograms [name=drawers]')).not_to_be_checked();expect(page.locator('#storePrograms [name=gifts]')).not_to_be_checked();page.screenshot(path=str(out/'OFFICE-Optional-Programs.png'));page.locator('dialog[open] .flowClose').click()
   page.locator('[data-office-action=thrift-settings]').click();page.locator('[data-thrift-tab=loyalty]').click();expect(page.locator('#thriftSettings [name=loyalty_scope]')).to_be_visible();page.screenshot(path=str(out/'OFFICE-Loyalty-Scope.png'));page.locator('dialog[open] .flowClose').click()
   page.locator('[data-office-action=stores-profiles]').click();page.locator('[data-store=binopoly]').click();expect(page.locator('#storeReceiptPreview')).to_contain_text('Binopoly');page.screenshot(path=str(out/'OFFICE-Binopoly-Store.png'));page.locator('dialog[open] .flowClose').click()
   page.locator('[data-office-action=catalog]').click();page.locator('#flowProductChoice').select_option(pid);expect(page.locator('#flowProductForm [name=sold_by_weight]')).to_be_checked();page.screenshot(path=str(out/'OFFICE-Weighted-Product.png'));page.locator('#officeBack').click()
   page.evaluate("localStorage.setItem('coastyouth-retail-device','"+'2'*32+"')")
   page.goto(origin+'/pos');expect(page.locator('#retailStoreBadge')).to_have_text('Binopoly');page.locator('#posNew').click();expect(page.locator('#posCart')).to_contain_text('Binopoly');page.locator('[data-pos-product="'+pid+'"]').click();page.locator('#storeWeight [name=weight]').fill('3.25');expect(page.locator('#storeWeightTotal')).to_have_text('$6.50 before tax');page.screenshot(path=str(out/'DESK-Enter-Weight.png'));page.locator('#storeWeight button.primary').click();expect(page.locator('#posCart')).to_contain_text('3.250 lb');page.screenshot(path=str(out/'DESK-Binopoly-Sale.png'));page.locator('#posPayNow').click();page.locator('#posCash [name=tender]').fill('10');page.locator('#posCash button.primary').click();expect(page.locator('#posReceipt')).to_contain_text('Thank you for shopping Binopoly!');expect(page.locator('#posNew')).to_be_enabled();page.screenshot(path=str(out/'DESK-Binopoly-Receipt.png'))
   page.goto(origin+'/');page.get_by_role('radio',name='Dashboard',exact=True).check();page.get_by_role('button',name='Continue',exact=True).click();page.get_by_role('button',name='Skip for now',exact=True).click();expect(page.locator('.rrResult')).to_contain_text('Donation performance');page.locator('.rrCard').filter(has=page.get_by_role('heading',name='Donation performance',exact=True)).screenshot(path=str(out/'STORE-OPS-Donation-Dashboard.png'))
   page.goto(origin+'/office');page.evaluate("retailReportCenter(document.querySelector('#officeHub'),'dashboard')");expect(page.locator('.rrResult')).to_contain_text('Donation performance');expect(page.locator('.rrResult')).to_contain_text('$4.50');page.screenshot(path=str(out/'OFFICE-Donation-Dashboard.png'));page.locator('.rrFilters [name=kind]').select_option('donations-employee');page.locator('.rrFilters button').first.click();expect(page.locator('.rrResult')).to_contain_text('75.0%');page.screenshot(path=str(out/'OFFICE-Donation-Report.png'))
   # Optional features enabled only in this disposable preview fixture.
   p=f.call('pos/programs')[1]['programs'];post('programs-save',**dict(p,gifts=True,membership=True,birthdays=True,drawers=True))
   drawer=post('drawer-open',terminal=tid,opening=10000)['drawer'];post('drawer-move',id=drawer['id'],amount=2500,direction='out',reason='Sample safe drop')
   page.goto(origin+'/office');page.locator('[data-office-action=stores-drawers]').click();expect(page.locator('#drawerRows')).to_contain_text('$75.00');page.screenshot(path=str(out/'OFFICE-Cash-Drawer.png'));page.locator('dialog[open] .flowClose').click()
   page.locator('[data-office-action=stores-members]').click();page.locator('#memberSearch [name=search]').fill('Sample');page.locator('#memberSearch button').click();page.locator('[data-member]').click();page.locator('#memberForm [name=card]').fill('123456789012');page.locator('#memberForm [name=birthday]').fill(dt.date.today().strftime('%m-%d'));page.locator('#memberForm button').click();expect(page.locator('#memberEdit svg')).to_be_visible();page.screenshot(path=str(out/'OFFICE-Membership.png'));page.locator('dialog[open] .flowClose').click()
   page.goto(origin+'/pos');page.locator('#posNew').click();page.locator('#retailProgramsDesk').click();page.locator('#giftSell [name=amount]').fill('25');page.locator('#giftSell button').click();expect(page.locator('#posCart')).to_contain_text('Gift certificate GC');page.locator('#posPayNow').click();page.locator('#posCash [name=tender]').fill('25');page.locator('#posCash button.primary').click();expect(page.locator('#posReceipt')).to_contain_text('Gift certificate GC')
   page.goto(origin+'/office');page.locator('[data-office-action=stores-gifts]').click();expect(page.locator('dialog[open]')).to_contain_text('$25.00');page.screenshot(path=str(out/'OFFICE-Gift-Certificates.png'))
   page.locator('dialog[open] .flowClose').click()
   second=post('terminal-save',name='Binopoly · Register 2',device='3'*32,enabled=True)['id'];post('store-terminal',terminal=second,store_id='binopoly',previous='thrift-mart');post('drawer-open',terminal=second,opening=0)
   page.evaluate('financeRefund(5)');page.locator('#financeRefundForm [name=qty_0]').fill('1');page.locator('#financeRefundForm [name=reason]').fill('TEST full weighed return');page.locator('#financeRefundForm [name=drawer_id]').select_option(str(drawer['id']));page.locator('#financeRefundForm button').click();expect(page.locator('#financeRefundPreview')).to_contain_text('$6.96');page.locator('#financeRefundConfirm').click();expect(page.locator('dialog[open]')).to_contain_text('Cash to give: $6.96')
   assert not errors,errors;b.close()
 finally:f.close()
 print('PASS store profiles, weighted checkout/receipt, donations, optional-program defaults, drawers, memberships and gifts')

if __name__=='__main__':run()
