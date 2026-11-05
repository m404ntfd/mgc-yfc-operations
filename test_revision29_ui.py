from pathlib import Path
import tempfile,base64
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'});F.call('admin/receipt-categories',{'categories':['Office']})
  F.call('receipt-submit',{'id':'a'*32,'filename':'office.pdf','category':'Office','body':base64.b64encode(b'%PDF-1.4 example').decode()})
  with sync_playwright() as p:
   b=p.chromium.launch()
   for width in (1280,390):
    page=b.new_page(viewport={'width':width,'height':1000},color_scheme='dark',reduced_motion='reduce');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}');expect(page.locator('.shareYfc')).to_be_visible()
    assert page.locator('#replayIntro').evaluate('(e)=>e.previousElementSibling.classList.contains("shareYfc")')
    page.locator('#shareYfcButton').click();expect(page.locator('#shareEmail')).to_be_visible()
    if width==1280:
     page.locator('#shareEmail').click();expect(page.locator('#shareEmailDialog')).to_be_visible();expect(page.locator('#shareGmail')).to_have_attribute('target','_blank');page.locator('#closeShareEmail').click()
     page.locator('#shareYfcButton').click();page.locator('#shareText').click();expect(page.locator('#textAppDialog')).to_be_visible();page.locator('#closeTextApp').click()
    else:page.locator('#closeShare').click()
    page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    if width==1280:expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#sectionChooser')).to_be_hidden()
    page.locator('#storeMenuButton').click();expect(page.locator('#storeMenu')).to_be_visible()
    if width==1280:
     page.mouse.move(1200,950);expect(page.locator('#storeMenu')).to_be_hidden();page.locator('#storeMenuButton').click()
    page.locator('#signedInUser').click();expect(page.locator('#storeMenu')).to_be_hidden()
    page.locator('#reportsTab').click();expect(page.locator('#reports')).to_be_visible();expect(page.locator('#reportOutput')).to_contain_text('Thrift Mart Dispatch')
    page.locator('#storeMenuButton').click();page.locator('#receiptsSection').click();expect(page.locator('#viewMyReceipts')).to_be_visible();expect(page.locator('#receipts .receipt-icon')).to_be_visible()
    page.locator('#reportsTab').click();expect(page.locator('#receiptHistory')).to_be_visible();expect(page.locator('#reports')).to_be_hidden();expect(page.locator('#currentSection')).to_have_text('Receipt Reports');expect(page.locator('#receiptHistoryResults')).to_contain_text('office.pdf');assert page.locator('body>header').evaluate('(e)=>getComputedStyle(e).backgroundColor')=='rgb(6, 122, 6)'
    page.locator('#receiptHistorySearch').fill('absent');page.locator('#receiptHistoryFilters button').click();expect(page.locator('#receiptHistorySummary')).to_contain_text('0 receipt(s)')
    page.locator('#receiptHistoryBack').click();page.locator('#viewMyReceipts').click();expect(page.locator('#receiptHistoryTitle')).to_have_text('My Receipts')
    page.locator('#settingsTab').click();page.get_by_role('button',name='Application Settings',exact=True).click();page.get_by_role('button',name='Sharing',exact=True).click();expect(page.locator('#sharingSettings')).to_be_visible()
    page.locator('#sharingForm [name=desktop_text]').uncheck();page.locator('#sharingForm button').click();expect(page.locator('#sharingStatus')).to_contain_text('saved')
    page.screenshot(path=str(Path(tempfile.gettempdir())/f'settings29-{width}.png'))
    page.locator('#storeMenuButton').click();page.locator('#dispatchSection').click();page.locator('#weekTab').click();expect(page.locator('.dayEmpty').first).to_be_visible();assert page.locator('.dayEmpty').first.evaluate('(e)=>getComputedStyle(e).backgroundColor')!='rgb(255, 255, 255)'
    assert not errors,errors;page.close()
   b.close()
 finally:F.tearDownClass()

if __name__=='__main__':run()
