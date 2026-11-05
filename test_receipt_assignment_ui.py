from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect
def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'});F.call('admin/receipt-categories',{'categories':['Office']})
  with sync_playwright() as p:
   b=p.chromium.launch()
   for width in (390,1280):
    page=b.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}');page.locator('#receiptShortcut').click();expect(page.locator('#receiptAssigneeLabel')).to_be_visible();expect(page.locator('#receiptAssignee')).to_have_attribute('required','')
    page.locator('#receiptFile').set_input_files({'name':f'receipt-{width}.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.4 test'});page.locator('#receiptCategory').select_option('Office');page.locator('#receiptReimbursement').check();page.locator('#receiptSubmit').click();expect(page.locator('#receiptResult')).not_to_contain_text('Receipt saved')
    page.locator('#receiptAssignee').select_option(label='Admin');page.locator('#receiptSubmit').click();expect(page.locator('#receiptResult')).to_contain_text('Receipt saved');expect(page.locator('#receiptReimbursement')).not_to_be_checked()
    page.locator('#receiptReturn').click();page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    if width==390:expect(page.locator('#sectionChooser')).to_be_visible();page.locator('[name=section][value=receipts]').check();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#receipts')).to_be_visible();page.locator('#viewMyReceipts').click();expect(page.locator('#receiptHistoryResults')).to_contain_text('Assigned by guest to Admin');expect(page.locator('#receiptHistoryResults')).to_contain_text('Reimbursement: Required')
    page.locator('#receiptHistoryBack').click();page.locator('#openReceiptUpload').click();expect(page.locator('#receiptAssigneeLabel')).to_be_hidden();expect(page.locator('#receiptReimbursement')).to_be_visible();assert not errors,errors;page.close()
   b.close()
 finally:F.tearDownClass()
if __name__=='__main__':run()
