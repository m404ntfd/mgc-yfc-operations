from test_ui_helpers import wait_for_pos_save
from test_ui_helpers import office_setting
from test_ui_helpers import password_login_page
import os,json,uuid,datetime as dt,struct
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
import server

f=CoordinatorFixture()
def post(path,**data):
 code,result=f.call('pos/'+path,dict(data,request=uuid.uuid4().hex));assert code==200,(path,result);return result
try:
 post('settings',store='CoastYouth Retail',tax_bps=700,confirmed=True)
 for name,price,taxable in [('Adult shirt',599,True),('Paperback book',399,False)]:post('product-save',name=name,category='Retail',price=price,taxable=taxable,rules={})
 with server.connect() as c:
  c.execute('INSERT INTO jobs VALUES(?,?,?)',('preview-reservation',6,json.dumps({'customer':'Sample customer','type':'Delivery','start':(dt.datetime.now()+dt.timedelta(days=2)).isoformat(timespec='minutes'),'end':(dt.datetime.now()+dt.timedelta(days=2,hours=1)).isoformat(timespec='minutes'),'address':'123 Sample Street','status':'Scheduled','notes':'Not for customer display'})))
 with sync_playwright() as pw:
  browser=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));ctx=browser.new_context(viewport={'width':1440,'height':1050});p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));origin=f'http://127.0.0.1:{f.port}';out=Path(os.environ.get('TEST_ARTIFACTS','test-artifacts'));out.mkdir(parents=True,exist_ok=True)
  icon=Path('assets/desk.ico').read_bytes();size,offset=struct.unpack_from('<II',icon,6+16*(struct.unpack_from('<H',icon,4)[0]-1)+8);logo=icon[offset:offset+size]
  p.goto(origin+'/office');password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click();expect(office_setting(p,'receipt-design')).to_be_visible()
  office_setting(p,'receipt-design').click();form=p.locator('#customerReceiptForm');form.locator('[name=address]').fill('123 Sample Street\nMobile, AL');form.locator('[name=phone]').fill('Customer service · sample contact');form.locator('[name=policy]').fill('Returns accepted within 30 days with your receipt.');form.locator('[name=footer]').fill('Thank you for supporting our community!');p.locator('#customerLogo').set_input_files({'name':'receipt-logo.png','mimeType':'image/png','buffer':logo});expect(p.locator('#customerReceiptPreview img')).to_be_visible();form.locator('button.primary').click();expect(p.locator('#customerSaveStatus')).to_contain_text('saved');p.locator('#officeHub').evaluate('(e)=>e.scrollTop=0');p.screenshot(path=str(out/'Customer-Receipt-Design.png'))
  p.locator('#officeBack').click();office_setting(p,'reservation-messages').click();expect(p.locator('.customerConnection')).to_contain_text('Not connected');p.locator('#customerEmailForm [name=sender]').fill('reservations@example.test');p.locator('#customerEmailForm button.primary').click();expect(p.locator('#customerSaveStatus')).to_contain_text('saved');p.locator('#officeHub').evaluate('(e)=>e.scrollTop=0');p.screenshot(path=str(out/'Customer-Gmail-Templates.png'))
  p.locator('#customerReservationsTab').click();p.locator('#customerContactForm [name=job]').select_option('preview-reservation');p.locator('#customerContactForm [name=email]').fill('sample.customer@example.test');p.locator('#customerContactForm [name=confirmations]').check();p.locator('#customerContactForm [name=reminders]').check();p.locator('#customerPreviewReservation').click();expect(p.locator('#customerReservationBody')).to_contain_text('Sample customer');p.locator('#officeHub').evaluate('(e)=>e.scrollTop=0');p.screenshot(path=str(out/'Customer-Reservation-Preview.png'));p.locator('#customerContactForm button.primary').click();expect(p.locator('#customerContactStatus')).to_contain_text('unchanged');expect(p.locator('#customerReservationPanel .flowTable')).to_contain_text('pending');p.locator('#officeHub').evaluate('(e)=>e.scrollTop=0');p.screenshot(path=str(out/'Customer-Delivery-History.png'))
  p.locator('#officeBack').click();office_setting(p,'customer-display').click();p.locator('#customerDisplayForm [name=enabled]').check();p.locator('#customerDisplayForm button.primary').click();expect(p.locator('#customerSaveStatus')).to_contain_text('saved');p.locator('#officeHub').evaluate('(e)=>e.scrollTop=0');p.screenshot(path=str(out/'Customer-Display-Settings.png'))
  desk=ctx.new_page();desk.on('pageerror',lambda e:errors.append(str(e)));desk.goto(origin+'/pos');desk.locator('#posNew').click();expect(desk.locator('#posCart')).to_contain_text('Saved on server');desk.locator('#posCatalog button').filter(has_text='Adult shirt').click();expect(desk.locator('#posCart')).to_contain_text('Adult shirt');wait_for_pos_save(desk);desk.locator('#posCatalog button').filter(has_text='Paperback book').click();expect(desk.locator('#posCart')).to_contain_text('$10.40');desk.locator('#customerPair').click();expect(desk.locator('#customerPairLink')).to_be_visible();link=desk.locator('#customerPairLink').input_value();desk.locator('.flowClose').click()
  # Separate unauthenticated browser context: the display must not need staff cookies.
  display=browser.new_page(viewport={'width':1440,'height':900});display.on('pageerror',lambda e:errors.append(str(e)));display.goto(link);expect(display.locator('#total')).to_have_text('$10.40');expect(display.locator('#lines')).to_contain_text('Paperback book');assert display.locator('body').inner_text().find('Admin')<0;display.screenshot(path=str(out/'Customer-Checkout-Display.png'));display.reload();expect(display.locator('#total')).to_have_text('$10.40')
  desk.locator('#posPayNow').click();desk.locator('#posCash [name=tender]').fill('20');desk.locator('#posCash button.primary').click();expect(desk.locator('#posReceipt')).to_contain_text('Thank you for supporting our community!');expect(desk.locator('#posReceipt .receiptLogo')).to_be_visible();expect(display.locator('#welcomeText')).to_contain_text('Thank you');expect(display.locator('#welcomeNote')).to_contain_text('$9.60');display.screenshot(path=str(out/'Customer-Thank-You-Display.png'))
  display.route('**/api/customer-display',lambda route:route.abort());expect(display.locator('#status')).to_contain_text('Disconnected',timeout=10000);expect(display.locator('#sale')).to_be_hidden();expect(display.locator('#lines')).to_be_empty()
  p.set_viewport_size({'width':1024,'height':900});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.locator('#officeBack').click();office_setting(p,'receipt-design').click();assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  with server.connect() as c:
   row=c.execute("SELECT * FROM jobs WHERE id='preview-reservation'").fetchone();assert row['revision']==6;assert json.loads(row['body'])['notes']=='Not for customer display'
  assert not errors,errors;browser.close()
finally:f.close()
print('PASS receipt design, email previews and opt-in queue, isolated display pairing, payment, disconnection, and unchanged reservations')
