"""Browser playback failure, hover controls, and server health transitions."""
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect

def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  assert F.call('connection-status')[0]==200
  with sync_playwright() as p:
   browser=p.chromium.launch()
   for blocked in (False,True):
    page=browser.new_page(viewport={'width':1280,'height':1000})
    if blocked:page.add_init_script("HTMLMediaElement.prototype.play=function(){return Promise.reject(new DOMException('Blocked','NotAllowedError'));}")
    page.goto(f'http://127.0.0.1:{F.port}')
    expect(page.locator('#auth')).to_be_visible()
    expect(page.locator('#loggedOutStatus')).to_have_text('No User Currently Logged In')
    expect(page.locator('#connectionDot')).to_have_attribute('data-connection-state','online')
    if blocked:
     expect(page.locator('#desktopFallback')).to_be_visible();expect(page.locator('#desktopVideo')).to_be_hidden();expect(page.locator('#pauseVideo')).to_be_hidden()
    else:
     page.wait_for_function("document.getElementById('desktopVideo').currentTime>0")
     assert page.locator('#desktopVideo').evaluate('(v)=>v.muted')
     expect(page.locator('#pauseVideo')).to_have_css('opacity','0')
     page.locator('.loginShowcase').hover();expect(page.locator('#pauseVideo')).to_have_css('opacity','1')
     page.locator('#pauseVideo').click();assert page.locator('#desktopVideo').evaluate('(v)=>v.paused')
    page.route('**/api/connection-status',lambda r:r.fulfill(json={'online':True,'update_available':True}))
    page.evaluate('pollServerConnection()');expect(page.locator('#connectionDot')).to_have_attribute('data-connection-state','update')
    page.route('**/api/state',lambda r:r.abort())
    page.evaluate("api('state').catch(()=>{})");expect(page.locator('#connectionDot')).to_have_attribute('data-connection-state','offline')
    page.unroute('**/api/state');page.evaluate('pollServerConnection()');expect(page.locator('#connectionDot')).to_have_attribute('data-connection-state','update')
    page.close()
   browser.close()
 finally:F.tearDownClass()
 print('PASS autoplay, blocked-play fallback, hover pause, guest identity, update/offline/recovery indicators')
if __name__=='__main__':run()
