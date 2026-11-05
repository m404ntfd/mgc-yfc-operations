"""Mobile/desktop receipt form and authenticated return routing."""
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect
from pathlib import Path
import tempfile

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  F.call('admin/receipt-categories',{'categories':['Ministry','Supplies']})
  with sync_playwright() as p:
   browser=p.chromium.launch();errors=[]
   for width in (390,1280):
    context=browser.new_context(viewport={'width':width,'height':844},reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}')
    page.locator('#receiptShortcut').click();expect(page.locator('#receiptUpload')).to_be_visible();expect(page.locator('#auth')).to_be_hidden()
    page.screenshot(path=str(Path(tempfile.gettempdir())/f'receipt-{width}.png'))
    page.locator('#receiptCategory').select_option('Ministry');page.locator('#receiptAssignee').select_option(label='Admin')
    page.locator('#receiptFile').set_input_files({'name':'receipt.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.4\nreceipt'})
    page.locator('#receiptSubmitNew').click();expect(page.locator('#receiptResult')).to_contain_text('Ready for the next receipt')
    expect(page.locator('#receiptFilename')).to_have_text('No file selected.');expect(page.locator('#receiptCategory')).to_have_value('')
    page.locator('#receiptFile').set_input_files({'name':'receipt.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.4\nreceipt'})
    page.locator('#receiptCategory').select_option('Supplies');page.get_by_role('button',name='Reset',exact=True).click();page.locator('#confirmReceiptReset').click()
    expect(page.locator('#receiptFilename')).to_have_text('No file selected.');expect(page.locator('#receiptCategory')).to_have_value('')
    page.locator('#receiptReturn').click();expect(page.locator('#auth')).to_be_visible();expect(page.locator('#app')).to_be_hidden()
    page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    expect(page.locator('#sectionChooser[open],#receipts:not([hidden])')).to_be_visible()
    if page.locator('#sectionChooser').is_visible():
     page.locator('[name=section][value=receipts]').check();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#receipts')).to_be_visible();page.locator('#openReceiptUpload').click();page.locator('#receiptReturn').click();expect(page.locator('#receipts')).to_be_visible()
    context.clear_cookies();page.locator('#openReceiptUpload').click();page.locator('#receiptReturn').click();expect(page.locator('#auth')).to_be_visible();expect(page.locator('#app')).to_be_hidden()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    context.close()
   assert not errors,errors;browser.close()
 finally:F.tearDownClass()
 print('PASS receipt upload, reset, next receipt, guest isolation and daily-page return on mobile/desktop')
if __name__=='__main__':run()
