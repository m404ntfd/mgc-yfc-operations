"""Isolated dispatch and website walkthrough; never submits to a live website."""
import functools,json,os,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_theme_contrast import AUDIT

def run():
 f=CoordinatorFixture();servers=[];out=Path('output/preview/online-requests');out.mkdir(parents=True,exist_ok=True)
 try:
  base=f'http://127.0.0.1:{f.port}'
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM'))
   context=browser.new_context(viewport={'width':1440,'height':1050});page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base+'/');page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();page.locator('#sectionChooserForm button').click()
   expect(page.locator('#pendingOverview')).to_contain_text('Online Requests are active')
   page.locator('[data-online-pause]').click();expect(page.locator('#onlineRequestsDialog')).to_be_visible()
   page.screenshot(path=str(out/'pause-options.png'))
   page.locator('[data-pause-hours="8"]').click();expect(page.locator('#pendingOverview')).to_contain_text('Online Requests are paused')
   expect(page.locator('#toast')).not_to_be_visible(timeout=15000)
   for theme in ('light','dark'):
    page.evaluate('(theme)=>{document.documentElement.dataset.theme=theme}',theme)
    issues=[x for x in page.evaluate(AUDIT) if x['cls']=='onlineRequestsControl' or 'Online Requests' in x['text'] or 'Automatically resumes' in x['text'] or 'Resume now' in x['text']]
    assert not issues,issues
    page.locator('#pendingOverview').screenshot(path=str(out/f'dispatch-{theme}.png'))
   page.set_viewport_size({'width':390,'height':844})
   page.locator('#pendingOverview').screenshot(path=str(out/'dispatch-mobile.png'))
   assert page.locator('.onlineRequestsControl strong').bounding_box()['y']<page.locator('[data-online-pause]').bounding_box()['y']
   page.locator('[data-online-resume]').click();expect(page.locator('#pendingOverview')).to_contain_text('Online Requests are active')
   assert not errors,errors
   context.close()
   website_root=os.environ.get('ONLINE_REQUEST_WEBSITE_ROOT')
   if website_root:
    root=Path(website_root);main=root/'site/.sites-checkout/web'
    for name,folder in [('coastyfc',main),('thriftmart',root/'thrift-mart-site/dist'),('binopoly',root/'binopoly-site/dist')]:
     class Quiet(SimpleHTTPRequestHandler):
      def log_message(self,*args):pass
     http=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(folder)));servers.append(http);threading.Thread(target=http.serve_forever,daemon=True).start()
     site=f'http://127.0.0.1:{http.server_port}'
     for mobile in (False,True):
      paused=f.call('online-requests',dict(hours=12,revision=f.call('online-requests')[1]['revision']))[1]
      ctx=browser.new_context(viewport={'width':390 if mobile else 1365,'height':844 if mobile else 1000},is_mobile=mobile,has_touch=mobile)
      mode={'error':False}
      def availability(route):
       if mode['error']:route.fulfill(status=503,json={'message':'Temporarily unavailable'})
       else:route.fulfill(json=f.call('online-requests')[1],headers={'Access-Control-Allow-Origin':'*','Cache-Control':'no-store'})
      ctx.route('https://coastyfc.com/api/online-requests',availability)
      tab=ctx.new_page();web_errors=[];tab.on('pageerror',lambda e:web_errors.append(str(e)));tab.goto(site+'/')
      selector='a[href="pickup-preview"]' if name=='coastyfc' else 'a[href="#donate"]' if name=='thriftmart' else 'a[href*="thriftmart"][href*="donat"]'
      if name=='binopoly':tab.locator('details').filter(has=tab.locator(selector)).locator('summary').click()
      button=tab.locator(selector+':visible').first
      button.click();expect(tab.locator('#online-request-notice')).to_be_visible();expect(tab.locator('#request-notice-title')).to_contain_text('temporarily paused')
      assert tab.url==site+'/'
      assert tab.locator('#online-request-notice').bounding_box()['width']<=(390 if mobile else 1365)
      tab.screenshot(path=str(out/f'{name}-{"mobile" if mobile else "desktop"}.png'))
      current=f.call('online-requests')[1];f.call('online-requests',dict(resume=True,revision=current['revision']))
      tab.locator('[data-notice-check]').click();expect(tab.locator('#online-request-notice')).not_to_be_visible()
      if name=='thriftmart':
       button.click();expect(tab).to_have_url(site+'/#donate')
      mode['error']=True;button.click();expect(tab.locator('#request-notice-title')).to_contain_text('couldn’t check availability')
      assert not web_errors,web_errors
      ctx.close()
    # A direct form visit is guarded, and a later pause preserves entered data.
    ctx=browser.new_context();ctx.route('https://coastyfc.com/api/online-requests',lambda route:route.fulfill(json=f.call('online-requests')[1],headers={'Access-Control-Allow-Origin':'*'}))
    tab=ctx.new_page();http=servers[0];tab.goto(f'http://127.0.0.1:{http.server_port}/pickup-preview.html')
    tab.locator('[name=zip]').fill('39507')
    tab.locator('button[data-next]:visible').first.click()
    f.call('online-requests',dict(hours=24,revision=f.call('online-requests')[1]['revision']))
    tab.reload();expect(tab.locator('#online-request-notice')).to_be_visible();tab.locator('[data-notice-close]').click()
    tab.locator('[name=zip]').fill('39507')
    tab.evaluate("document.querySelector('#pickup-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
    expect(tab.locator('#online-request-notice')).to_be_visible();expect(tab.locator('[name=zip]')).to_have_value('39507');ctx.close()
   browser.close()
 finally:
  for http in servers:http.shutdown();http.server_close()
  f.close()
 print('PASS pause controls, themes, mobile website notices, resume and preserved form values')

if __name__=='__main__':run()
