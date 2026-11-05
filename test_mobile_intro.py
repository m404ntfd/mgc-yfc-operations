"""Mobile title/tagline cutoff, fade-to-login, replay, and desktop isolation."""
from test_server import Tests as F
from playwright.sync_api import sync_playwright,expect
def run():
 F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  with sync_playwright() as p:
   b=p.chromium.launch()
   for webm in (False,True):
    page=b.new_page(viewport={'width':390,'height':850});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    if webm:page.add_init_script("const original=HTMLMediaElement.prototype.canPlayType;HTMLMediaElement.prototype.canPlayType=function(type){return type.includes('mp4')?'':original.call(this,type);};")
    page.goto(f'http://127.0.0.1:{F.port}');expect(page.locator('#mobileIntro')).to_be_visible();page.wait_for_function("()=>document.getElementById('mobileVideo').currentTime>0")
    assert page.locator('#mobileVideo').evaluate('(v)=>v.src.endsWith("#t=0,5.5")')
    expect(page.locator('#mobileIntro')).to_have_class('introFading',timeout=9000)
    assert page.locator('#mobileVideo').evaluate('(v)=>v.paused&&v.currentTime<6')
    expect(page.locator('#mobileIntro')).to_have_css('transition-duration','0.7s');expect(page.locator('#mobileIntro')).to_be_hidden(timeout=2000);expect(page.locator('#login')).to_be_visible()
    page.locator('#replayIntro').click();expect(page.locator('#mobileIntro')).to_be_visible();page.wait_for_function("()=>document.getElementById('mobileVideo').currentTime>0")
    page.locator('#mobileVideo').evaluate('(v)=>{v.currentTime=5.5;v.dispatchEvent(new Event("timeupdate"));}');expect(page.locator('#mobileIntro')).to_be_hidden(timeout=2000)
    page.locator('#replayIntro').click();page.locator('#skipVideo').click();expect(page.locator('#mobileIntro')).to_be_hidden();assert not errors,errors;page.close()
   page=b.new_page(viewport={'width':1280,'height':900});page.goto(f'http://127.0.0.1:{F.port}');page.wait_for_function("()=>document.getElementById('desktopVideo').currentTime>0");page.locator('#desktopVideo').evaluate('(v)=>{v.currentTime=7}');page.wait_for_function("()=>document.getElementById('desktopVideo').currentTime>7");expect(page.locator('#mobileIntro')).to_be_hidden();assert page.locator('#desktopVideo').evaluate('(v)=>!v.paused');b.close()
 finally:F.tearDownClass()
if __name__=='__main__':run()
