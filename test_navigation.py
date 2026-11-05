"""New page, home selection, settings, and nondestructive reset on both layouts."""
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  F.call('admin/receipt-categories',{'categories':['Supplies']})
  with sync_playwright() as p:
   b=p.chromium.launch()
   for width in (390,1280):
    page=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}')
    page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('#sectionChooser:visible, #print:visible')).to_be_visible()
    if page.locator('#sectionChooser').is_visible():
     page.locator('[name=section][value=print]').check();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#print')).to_be_visible()
    assert page.locator('body>header').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(0, 255, 255)'
    page.locator('#storeMenuButton').click();expect(page.locator('#appearanceMenu')).to_have_text('Settings');page.locator('#appearanceMenu').click()
    expect(page.locator('#print')).to_be_hidden();expect(page.get_by_role('button',name='Phone Access',exact=True)).to_have_count(0)
    expect(page.locator('#accountButton')).to_have_text('Return to Home');page.locator('#accountButton').click();expect(page.locator('#print')).to_be_visible()
    page.locator('#storeMenuButton').click();page.locator('#receiptsSection').click();page.locator('#openReceiptUpload').click()
    page.locator('#receiptCategory').select_option('Supplies')
    page.locator('#receiptFile').set_input_files({'name':'receipt.pdf','mimeType':'application/pdf','buffer':b'%PDF-test'})
    page.once('dialog',lambda d:d.dismiss());page.locator('#receiptReset').click()
    expect(page.locator('#receiptCategory')).to_have_value('Supplies');expect(page.locator('#receiptFilename')).to_have_text('receipt.pdf');expect(page.locator('#toast')).to_have_text('No changes have been made.')
    page.once('dialog',lambda d:d.accept());page.locator('#receiptReset').click();expect(page.locator('#receiptFilename')).to_have_text('No file selected.')
    page.locator('#receiptReturn').click();expect(page.locator('#print')).to_be_visible()
    page.route('**/api/account/lease',lambda route:route.fulfill(status=401,content_type='application/json',body='{"error":"Your session has ended. Please sign in again."}'))
    page.evaluate("async()=>{try{await api('account/lease')}catch{}}")
    expect(page.locator('#auth')).to_be_visible();expect(page.locator('#print')).to_be_hidden()
    assert not errors,errors
    page.close()
   b.close()
 finally:F.tearDownClass()
 print('PASS mobile and desktop print page, settings, home and receipt reset')
if __name__=='__main__':run()
