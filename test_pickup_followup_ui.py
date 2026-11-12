from test_ui_helpers import office_setting
import os,uuid,datetime as dt
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page

def run():
 f=CoordinatorFixture();out=Path('test-artifacts/pickup-preview');out.mkdir(exist_ok=True);errors=[]
 def post(path,**data):
  status,r=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert status==200,r;return r
 try:
  post('settings',store='Thrift Mart',tax_bps=700,confirmed=True)
  pid=post('product-save',name='Sofa · SAMPLE',category='Furniture',price=12500,taxable=True,rules={'pickup_slip':True})['ids'][0]
  f.call('vehicle',{'name':'Delivery Truck 1'})
  today=dt.date.today().isoformat()
  status,r=f.call('save',dict(type='Delivery',customer='Sample existing booking',phone='555-0101',address='Example address',items='Sample table',vehicle='Delivery Truck 1',start=today+'T13:00',end=today+'T14:00',status='Scheduled'));assert status==200,r
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None,headless=True)
   page=b.new_page(viewport={'width':1440,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
   origin=f'http://127.0.0.1:{f.port}';page.goto(origin+'/office');password_login_page(page).locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();expect(page.locator('#officeHub')).to_be_visible()
   office_setting(page,'catalog').click();page.locator('#flowProductChoice').select_option(pid);expect(page.locator('[name=pickup_slip]')).to_be_checked();page.screenshot(path=str(out/'OFFICE-Pickup-Item.png'))
   page.goto(origin+'/pos');page.locator('[data-pos-product="'+pid+'"]').click();page.locator('#posPayNow').click();page.locator('#checkoutTender').fill('140.00');page.locator('#checkoutComplete').click()
   expect(page.locator('#pickupYes')).to_be_visible();page.screenshot(path=str(out/'DESK-Paid-Pickup-Prompt.png'));page.locator('#pickupYes').click()
   d=page.locator('dialog[open]');d.locator('[name=customer]').fill('Sample Customer');d.locator('[name=contact]').fill('555-0100');d.locator('[name=location]').fill('Furniture bay A');d.locator('[name=due]').fill(today);d.locator('button.primary').click();expect(page.locator('#thriftPrintSlip')).to_be_enabled()
   page.evaluate("window.fulfillmentPrint=(title,html)=>{window.testPrinted=html;return true}");page.locator('#thriftPrintSlip').click();expect(page.locator('#pickupPrinted')).to_be_visible();assert 'SOLD' in page.evaluate('window.testPrinted');page.locator('#pickupPrinted').click();expect(page.locator('#pickupYes')).to_be_visible();page.locator('#pickupYes').click()
   expect(page.locator('#editor.deliveryWorkspace')).to_be_visible(timeout=20000)
   expect(page.locator('#jobForm [name=customer]')).to_have_value('Sample Customer');expect(page.locator('#deliveryCalendar')).to_contain_text('Sample existing booking')
   for name,value in [('street','123 Sample Street'),('city','Gulfport'),('zip','39501')]:page.locator('#jobForm [name='+name+']').fill(value)
   page.locator('#jobForm [name=state]').select_option('MS');page.locator('#jobForm [name=vehicle]').select_option('Delivery Truck 1');page.screenshot(path=str(out/'DESK-Delivery-Workspace.png'))
   page.locator('#save').click();expect(page.get_by_role('heading',name='Delivery scheduled',exact=True)).to_be_visible();page.get_by_role('button',name='Return to POS',exact=True).click();expect(page.locator('#posCatalog')).to_be_visible()
   assert f.call('pos/pickup-followup?sale=1')[1]['followup']['appointment'];assert not errors,errors;b.close()
 finally:f.close()
 print('PASS paid pickup prompt, two-ticket confirmation, split delivery workspace and linked appointment')

if __name__=='__main__':run()


