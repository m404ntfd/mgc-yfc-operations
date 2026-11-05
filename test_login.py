"""Exercise live login media and the receipts shortcut."""
import test_server
from playwright.sync_api import sync_playwright, expect

def run():
 F=test_server.Tests; F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  with sync_playwright() as p:
   b=p.chromium.launch()
   for width in (390,1280):
    page=b.new_page(viewport={'width':width,'height':850});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{F.port}');expect(page.locator('#auth')).to_be_visible()
    if width==390:
     expect(page.locator('#mobileIntro')).to_be_visible();page.locator('#skipVideo').click();expect(page.locator('#mobileIntro')).to_be_hidden()
     page.locator('#replayIntro').click();expect(page.locator('#mobileIntro')).to_be_visible();page.locator('#skipVideo').click()
    else:
     expect(page.locator('#desktopVideo')).to_be_visible();assert page.locator('#desktopVideo').evaluate('(v)=>v.src.startsWith("data:video/")')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=f'/tmp/login-{width}.png')
    page.locator('#receiptShortcut').click();page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    if width==390:
     expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#receipts')).to_be_visible();expect(page.locator('#sectionChooser')).to_be_hidden();expect(page.locator('#mobileIntro')).to_be_hidden()
    assert page.locator('#desktopVideo').evaluate('(v)=>v.paused');assert not errors,errors;page.close()
   b.close()
 finally:F.tearDownClass()
 print('PASS desktop/mobile media, skip/replay, receipts sign-in, no overflow and media stops after login')
if __name__=='__main__':run()
