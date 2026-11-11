"""New section, first daily home, removed phone settings, and safe receipt reset."""
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  F.call('admin/receipt-categories',{'categories':['Office']})
  with sync_playwright() as p:
   b=p.chromium.launch()
   for width in (390,1280):
    page=b.new_page(viewport={'width':width,'height':900},reduced_motion='reduce');errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}')
    page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    if width==1280:
     page.locator('#accountButton').click();page.locator('#storeMenuButton').click();page.locator('#printSection').click()
    if width==390:
     page.locator('[name=section][value=print]').check();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#printPurpose')).to_be_visible()
    assert page.locator('body>header').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(7, 62, 166)'
    page.locator('.headerMenu summary').click();page.locator('#appearanceMenu').click()
    expect(page.locator('#printPurpose')).to_be_hidden();expect(page.locator('#currentSection')).to_have_text('Settings')
    expect(page.get_by_role('button',name='Phone Access',exact=True)).to_be_hidden()
    page.locator('#accountButton').click();expect(page.locator('#printPurpose' if width==390 else '#receipts')).to_be_visible()
    page.locator('.headerMenu summary').click();page.locator('#chooseStartSection').click()
    page.locator('[name=section][value=receipts]').check();page.locator('#sectionChooserForm button').click()
    # Verify the new home from a different section, so the visibility assertion
    # waits for Home's asynchronous response before opening the upload form.
    expect(page.locator('#sectionChooser')).to_be_hidden()
    page.locator('#storeMenuButton').click();page.locator('#printSection').click()
    expect(page.locator('#printPurpose')).to_be_visible()
    page.locator('#accountButton').click();expect(page.locator('#receipts')).to_be_visible()
    page.locator('#storeMenuButton').click();page.locator('#receiptsSection').click();page.locator('#openReceiptUpload').click()
    page.locator('#receiptCategory').select_option('Office')
    page.locator('#receiptFile').set_input_files({'name':'receipt.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.4 receipt'})
    page.locator('#receiptForm [type=reset]').click();expect(page.locator('#receiptResetDialog')).to_be_visible()
    page.locator('#cancelReceiptReset').click();expect(page.locator('#receiptCategory')).to_have_value('Office');expect(page.locator('#receiptFilename')).to_contain_text('receipt.pdf');expect(page.locator('#toast')).to_have_text('No changes have been made.')
    page.locator('#receiptForm [type=reset]').click();page.locator('#confirmReceiptReset').click();expect(page.locator('#receiptCategory')).to_have_value('');expect(page.locator('#receiptFilename')).to_have_text('No file selected.')
    assert not errors,errors
    page.close()
   b.close()
 finally:F.tearDownClass()

if __name__=='__main__':run()
