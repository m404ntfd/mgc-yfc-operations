"""Touch checkout preview and regression checks using an isolated sample store."""
import os,json,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page
import server
from test_theme_contrast import AUDIT
f=CoordinatorFixture();out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
def post(action,**data):
 status,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert status==200,(action,result);return result
def saved(page):
 ident=page.locator('#posCarts').input_value()
 with server.connect() as db:return dict(db.execute('SELECT * FROM pos_carts WHERE id=?',(ident,)).fetchone()) if ident else None
def assert_viewport(page):
 # A scrollable panel may contain more items, but its frame and fixed controls
 # must stay on-screen without Playwright scrolling an ancestor to reach them.
 page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
 issues=page.evaluate("""()=>{
  const failures=[];
  if(document.documentElement.scrollWidth>innerWidth+1||document.documentElement.scrollHeight>innerHeight+1)failures.push('Page exceeds viewport');
  for(const e of document.querySelectorAll('.workspace,.registerLayout,.receiptPane,.receiptTools,.registerRail,.registerRail>button,.deskScroll,.deskScroll>button,#posCart>p:last-child,#posSearch')){
   if(!e.getClientRects().length)continue;
   const b=e.getBoundingClientRect(),name=e.id||e.className||e.textContent;
   if(b.left<0||b.top<0||b.right>innerWidth+1||b.bottom>innerHeight+1)failures.push(name+' outside viewport');
   for(let parent=e.parentElement;parent;parent=parent.parentElement){
    const style=getComputedStyle(parent),r=parent.getBoundingClientRect();
    if(/auto|scroll|hidden|clip/.test(style.overflowY)&&(b.top<r.top-1||b.bottom>r.bottom+1))failures.push(name+' clipped by '+(parent.id||parent.className));
   }
  }
  return failures;
 }""")
 assert not issues,issues
try:
 post('settings',store='Thrift Mart · SAMPLE',tax_bps=700,confirmed=True)
 post('terminal-save',name='Thrift Mart Register 1',device='a'*32,enabled=True,hostname='THRIFTMART-POS-01')
 info=dict(app='pos',device='a'*32,version='1.18.0',configured=True,nonce='b'*64,computer=dict(id='c'*32,hostname='SAMPLE-TOUCH-PC',macs=[],os='Windows fixture'))
 assert f.call('computers/self',info)[0]==200
 assert f.call('computers/register',dict(id='c'*32,revision=0,name='Sample Touch Register',role='pos',app='pos',device='a'*32))[0]==200
 products=[]
 for i in range(48):
  names=['Large Hardback','Small Hardback','Large Paperback','Magazines','Clothes & Accessories','Electronics','Small Paperback','Comic Books','Table Lamp','VHS Tapes','CD & DVDs','Records','Dining Chair','Furniture','Household','Delivery Fee']
  groups=['Books','Clothes','Electronics','Furniture','Household','Media','Delivery','Toys','Sports & Outdoors','Sodas','Linens','Shoes']
  name=names[i] if i<16 else 'Sample item '+str(i+1)
  rules={'open_priced':True} if i in (4,5,13,14,15) else {}
  products.append(post('product-save',name=name,category=(['Books','Books','Books','Books','Clothes','Electronics','Books','Books','Household','Media','Media','Media','Furniture','Furniture','Household','Delivery'][i] if i<16 else groups[i%12]),price=[200,100,100,75,500,1200,50,200,899,75,200,149,1500,100,500,100][i%16],taxable=True,rules=rules)['ids'][0])
 weight=post('product-save',name='Bulk textiles (by weight)',category='Weight',price=200,taxable=True,rules={'sold_by_weight':True})['ids'][0]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
  ctx=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,has_touch=True,reduced_motion='reduce');p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  ctx.add_init_script('window.fixtureInfo='+json.dumps(info)+';window.pywebview={api:{kiosk_info:async()=>window.fixtureInfo,terminal_info:async()=>window.fixtureInfo}};')
  p.goto(f'http://127.0.0.1:{f.port}/pos');password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').tap();expect(p.locator('#posCatalog')).to_be_visible()
  expect(p.locator('#nativeTerminalStatus')).to_contain_text('Registered');assert_viewport(p)
  def item(ident):return p.locator('[data-pos-product="'+ident+'"]')
  item(products[0]).tap();expect(p.locator('.deskQuantity output')).to_have_text('1')
  p.locator('[data-desk-quantity="0"][data-step="1"]').tap();expect(p.locator('.deskQuantity output')).to_have_text('2');expect(p.locator('#posCart')).to_contain_text('$4.28')
  p.reload();expect(p.locator('.deskQuantity output')).to_have_text('2')
  p.locator('[data-desk-quantity="0"][data-step="-1"]').tap();expect(p.locator('.deskQuantity output')).to_have_text('1');expect(p.locator('[data-desk-quantity="0"][data-step="-1"]')).to_be_disabled()
  # A lost response can be retried without increasing the quantity twice.
  def lose(route):route.fetch();route.abort();p.unroute('**/api/pos/quantity',lose)
  p.route('**/api/pos/quantity',lose);p.locator('[data-desk-quantity="0"][data-step="1"]').tap();expect(p.locator('#posRetry')).to_be_visible();p.locator('#posRetry').tap();expect(p.locator('#posRetry')).to_be_hidden();expect(p.locator('.deskQuantity output')).to_have_text('2')
  # Large scroll arrows move each independently scrollable panel.
  for kind,selector in [('products','#posCatalog'),('groups','#posCategories')]:
   down=p.locator(f'[data-desk-scrollbar={kind}] [data-scroll-direction="1"]');expect(down).to_be_visible();down.tap();assert p.locator(selector).evaluate('(e)=>e.scrollTop')>0
   p.locator(f'[data-desk-scrollbar={kind}] [data-scroll-direction="-1"]').tap()
  # Keypad stages input, validates it, and Cancel preserves the sale and field.
  item(products[4]).tap();expect(p.locator('.deskAmountPad')).to_be_visible();assert p.locator('#flowOpenPrice').evaluate('(e)=>e.parentElement.tagName')=='LABEL', 'Touch controls must not reparent the number field'
  assert p.evaluate('unfinished()'), 'Keypad entry must block an automatic restart'
  p.locator('.deskAmountPad [data-key="0"]').tap();p.locator('.deskKeypadApply').tap();expect(p.locator('.deskKeypadError')).not_to_be_empty();p.locator('.deskAmountPad [data-key="clear"]').tap()
  for key in '12.50':p.locator('.deskAmountPad [data-key="'+key+'"]').tap()
  for theme in ['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+v for v in ('blue','teal','violet','rose','graphite')]:
   for mode in ('light','dark'):
    p.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode])
    assert not p.evaluate(AUDIT.replace('document.querySelectorAll(', 'document.querySelector(".deskAmountPad").querySelectorAll(')),theme
  p.evaluate("document.body.dataset.retailTheme='harbor-blue';document.documentElement.dataset.theme='light'")
  p.screenshot(path=str(out/'DESK-Touch-Price-Keypad.png'))
  p.locator('.deskKeypadApply').tap();expect(p.locator('#flowChoices')).to_have_count(0);expect(p.locator('#posCart')).to_contain_text('Clothes & Accessories')
  original=saved(p);item(products[4]).tap();p.locator('.deskAmountPad [data-key="9"]').tap();p.locator('.deskKeypadCancel').tap();expect(p.locator('dialog[open]')).to_contain_text('entry was canceled');p.locator('[data-product-cancel-ok]').tap();assert saved(p)==original
  item(weight).tap();p.locator('#storeWeight .deskKeypadOpen').tap()
  for key in '2.125':p.locator('.deskAmountPad [data-key="'+key+'"]').tap()
  p.locator('.deskKeypadApply').tap();expect(p.locator('#storeWeightTotal')).to_contain_text('$4.25');p.locator('#storeWeight button.primary').tap();expect(p.locator('.deskFixedQuantity')).to_contain_text('By weight')
  for ident in [products[i] for i in (1,2,3,6,7,8,9,10,11,12)]:
   item(ident).tap();expect(p.locator('#posStatus')).not_to_have_text('Saving…')
  expect(p.locator('[data-desk-scrollbar=receipt]')).to_be_visible();p.locator('[data-desk-scrollbar=receipt] [data-scroll-direction="1"]').tap();assert p.locator('.receiptLines').evaluate('(e)=>e.scrollTop')>0;p.locator('[data-desk-scrollbar=receipt] [data-scroll-direction="-1"]').tap()
  # Fit the target screen and keep payment/receipt totals in view.
  assert_viewport(p)
  # Window chrome/taskbar and update notice must reduce the workspace, not clip it.
  p.set_viewport_size({'width':1920,'height':1040});assert_viewport(p)
  p.set_viewport_size({'width':1920,'height':1080})
  p.evaluate("document.body.classList.add('posInstallWarning')");assert_viewport(p)
  p.evaluate("document.body.classList.remove('posInstallWarning')");assert_viewport(p)
  for selector in ['#posPayNow','.receiptTools','#posCart>p:last-child','#posSearch']:
   box=p.locator(selector).bounding_box();assert box and box['x']>=0 and box['y']>=0 and box['x']+box['width']<=1921 and box['y']+box['height']<=1081,(selector,box)
  for selector in ['#posSearch','#posFindCart','[data-desk-quantity="0"][data-step="1"]','#posPayNow','#retailNext']:
   box=p.locator(selector).bounding_box();assert box['height']>=48,(selector,box)
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal page overflow'
  p.locator('#posSearch').fill('');p.locator('#posCatalog').evaluate('(e)=>e.scrollTop=0');p.screenshot(path=str(out/'DESK-Touch-Register-1920.png'))
  # Readable touch controls in all current palettes, including glass light/dark.
  theme_results=[]
  for theme in ['harbor-blue','classic-gray','coastal-teal','midnight','coastyouth-red']+['glass-'+v for v in ('blue','teal','violet','rose','graphite')]:
   for mode in ('light','dark'):
    p.evaluate('([theme,mode])=>{document.body.dataset.retailTheme=theme;document.documentElement.dataset.theme=mode}',[theme,mode])
    issues=p.evaluate(AUDIT);theme_results.append(dict(theme=theme,mode=mode,issues=issues))
    if theme=='midnight' and mode=='dark':p.screenshot(path=str(out/'DESK-Touch-Midnight-1920.png'))
  (out/'DESK-Touch-Contrast.json').write_text(json.dumps(theme_results,indent=2))
  assert not [r for r in theme_results if r['issues']],theme_results
  p.evaluate("document.body.dataset.retailTheme='harbor-blue';document.documentElement.dataset.theme='light'")
  # Cash keypad updates the existing change preview, with explicit payment confirmation.
  p.locator('#posPayNow').tap()
  for key in '10000':p.locator('[data-money-key="'+key+'"]').tap()
  expect(p.locator('#checkoutChange')).not_to_be_empty();p.locator('#checkoutComplete').tap();expect(p.locator('#posReceipt')).to_contain_text('Receipt #')
  assert p.locator('#posReceipt .deskQuantity').count()==0
  p.emulate_media(media='print');expect(p.locator('.deskScroll').first).to_be_hidden();p.emulate_media(media='screen')
  assert not errors,errors;browser.close()
 print('PASS 1920x1080 touch layout, scroll controls, saved quantity/retry, price/weight/cash keypad, cancel preservation and receipt')
finally:
 if 'errors' in locals() and errors:print('BROWSER ERRORS:',errors)
 f.close()
