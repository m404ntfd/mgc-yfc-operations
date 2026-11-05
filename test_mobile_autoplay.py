"""Autoplay repeats on reload/logout, with a usable blocked-play fallback."""
import os
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect
def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  with sync_playwright() as p:
   engines=[p.chromium]+([p.webkit] if os.environ.get('TEST_WEBKIT')=='1' else [])
   for engine in engines:
    browser=engine.launch();page=browser.new_page(viewport={'width':390,'height':850},is_mobile=True,has_touch=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("sessionStorage.setItem('yfc-intro-v4','1')")
    page.goto(f'http://127.0.0.1:{F.port}');expect(page.locator('#mobileIntro')).to_be_visible();page.wait_for_function("()=>document.getElementById('mobileVideo').currentTime>0")
    if engine.name=='webkit':
     expect(page.locator('#mobileIntro')).to_have_class('introFading',timeout=9000);assert page.locator('#mobileVideo').evaluate('(v)=>v.paused&&v.currentTime<6');expect(page.locator('#mobileIntro')).to_be_hidden(timeout=2000)
    else:page.locator('#skipVideo').click()
    page.reload();expect(page.locator('#mobileIntro')).to_be_visible();page.wait_for_function("()=>document.getElementById('mobileVideo').currentTime>0");page.locator('#skipVideo').click()
    page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
    if engine.name=='chromium':expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click()
    expect(page.locator('#sectionChooser')).to_be_hidden();page.locator('#logout').click();expect(page.locator('#mobileIntro')).to_be_visible();page.wait_for_function("()=>document.getElementById('mobileVideo').currentTime>0");page.locator('#skipVideo').click();assert not errors,errors;page.close()
    blocked=browser.new_page(viewport={'width':390,'height':850},is_mobile=True,has_touch=True)
    blocked.add_init_script("const play=HTMLMediaElement.prototype.play;let refused=false;HTMLMediaElement.prototype.play=function(){if(this.id==='mobileVideo'&&!refused){refused=true;return Promise.reject(new DOMException('Autoplay blocked','NotAllowedError'));}return play.call(this);};")
    blocked.goto(f'http://127.0.0.1:{F.port}');expect(blocked.locator('#mobilePlayPrompt')).to_be_visible();expect(blocked.locator('#login')).to_be_visible();expect(blocked.locator('#mobileIntro')).to_be_hidden();blocked.locator('#mobilePlayPrompt').click();expect(blocked.locator('#mobileIntro')).to_be_visible();blocked.wait_for_function("()=>document.getElementById('mobileVideo').currentTime>0");blocked.locator('#skipVideo').click();browser.close()
 finally:F.tearDownClass()
if __name__=='__main__':run()
