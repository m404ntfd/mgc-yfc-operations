"""First product starts checkout; canceled prompts and retries preserve existing work."""
import json, os, uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_update_coordination import CoordinatorFixture
from test_ui_helpers import password_login_page
import server

f=CoordinatorFixture()
out=Path('output/preview');out.mkdir(parents=True,exist_ok=True)
def post(action,**data):
 status,result=f.call('pos/'+action,dict(data,request=uuid.uuid4().hex));assert status==200,(action,result);return result
def rows(table):
 with server.connect() as c:return [tuple(r) for r in c.execute('SELECT * FROM '+table+' ORDER BY rowid')]
def carts():return rows('pos_carts')
def cart(ident):
 with server.connect() as c:return dict(c.execute('SELECT * FROM pos_carts WHERE id=?',(ident,)).fetchone())
def body(ident):return json.loads(cart(ident)['body'])
def units(ident):return sum(x['quantity'] for x in body(ident)['lines'])
try:
 post('settings',store='Thrift Mart · SAMPLE',tax_bps=700,confirmed=True)
 fixed=post('product-save',name='Sample fixed-price shirt',category='Clothes',price=599,taxable=True,rules={})['ids'][0]
 opened=post('product-save',name='Sample open-price furniture',category='Furniture',price=100,taxable=True,rules={'open_priced':True})['ids'][0]
 weighed=post('product-save',name='Sample weighed merchandise',category='Goods',price=200,taxable=True,rules={'sold_by_weight':True})['ids'][0]
 choice=post('product-save',name='Sample item with choices',category='Goods',price=500,taxable=True,rules={'modifiers':[{'id':'size','name':'Size','required':True,'options':[{'id':'large','name':'Large','price':100}]}]})['ids'][0]
 old=post('new')['cart'];old=post('add',cart=old['id'],revision=old['revision'],product=fixed,quantity=1)['cart'];post('cash',cart=old['id'],revision=old['revision'],tender=1000)
 with server.connect() as c:
  account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0]
  c.execute("INSERT INTO work_periods VALUES(901,?,1200,NULL,'Office',NULL)",(account,))
  c.execute('INSERT INTO work_breaks VALUES(902,901,1300,NULL)')
  c.execute('INSERT INTO jobs VALUES(?,?,?)',('Delivery',903,json.dumps({'type':'Delivery','customer':'Protected sample reservation','notes':'Keep this unchanged'})))
  c.execute('INSERT INTO photos VALUES(?,?,?)',('Delivery',0,b'protected-sample-photo'))
 protected={name:rows(name) for name in ('work_periods','work_breaks','jobs','photos','pos_products','retail_product_rules','pos_settings','users')}
 original_sales=rows('pos_sales')
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('TEST_CHROMIUM') or None)
  ctx=browser.new_context(viewport={'width':1440,'height':1000},has_touch=True,reduced_motion='reduce')
  errors=[];origin=f'http://127.0.0.1:{f.port}'
  p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)));p.goto(origin+'/pos')
  password_login_page(p).locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
  expect(p.locator('#posCatalog')).to_be_visible()
  def fresh():
   page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(origin+'/pos')
   expect(page.locator('#posCart')).to_contain_text('Tap a product to start a sale')
   return page
  def product(page,ident):return page.locator('[data-pos-product="'+ident+'"]')
  def current(page):return page.locator('#posCarts').input_value()
  def acknowledge(page,reason):
   expect(page.locator('dialog[open]')).to_contain_text('Item not added')
   expect(page.locator('dialog[open]')).to_contain_text(reason)
   page.locator('[data-product-cancel-ok]').tap()
  # Mouse starts one sale; a subsequent touch adds to that same sale.
  before=len(carts());product(p,fixed).click();expect(p.locator('#posCart')).to_contain_text('$6.41')
  first=current(p);assert len(carts())==before+1 and units(first)==1
  product(p,fixed).tap();expect(p.locator('#posCart')).to_contain_text('$12.82');assert current(p)==first and units(first)==2
  p.screenshot(path=str(out/'DESK-First-Product-Receipt.png'))
  # Empty price/weight cancellation writes nothing and explains why the item was not added.
  q=fresh();before=carts();product(q,opened).tap();expect(q.locator('#deskKeypadValue')).to_be_visible();assert carts()==before
  q.screenshot(path=str(out/'DESK-First-Product-Price.png'))
  q.locator('.deskKeypadCancel').tap();acknowledge(q,'because no price was entered');assert carts()==before
  product(q,weighed).tap();q.keyboard.press('Escape');acknowledge(q,'because no weight was entered');assert carts()==before
  product(q,opened).tap();q.locator('#deskKeypadValue').fill('0');q.locator('.deskKeypadApply').tap();assert carts()==before
  q.locator('#deskKeypadValue').fill('12.34');q.locator('.deskKeypadApply').tap();expect(q.locator('#posCart')).to_contain_text('$13.20')
  open_cart=current(q);assert len(carts())==len(before)+1 and body(open_cart)['lines'][0]['price']==1234
  # Cancellation keeps the complete saved cart and revision untouched.
  saved=cart(open_cart);product(q,opened).tap();q.locator('.deskKeypadCancel').tap()
  expect(q.locator('dialog[open]')).to_contain_text('because no price was entered')
  q.screenshot(path=str(out/'DESK-Canceled-Price-Keeps-Receipt.png'))
  acknowledge(q,'because no price was entered');assert cart(open_cart)==saved
  product(q,weighed).tap();q.locator('.flowClose').tap();acknowledge(q,'because no weight was entered');assert cart(open_cart)==saved
  product(q,opened).tap();q.locator('#deskKeypadValue').fill('8.00');q.locator('.deskKeypadCancel').tap();acknowledge(q,'entry was canceled');assert cart(open_cart)==saved
  # Weight and required item choices can each be the first product.
  w=fresh();before=len(carts());product(w,weighed).tap();w.locator('#storeWeight [name=weight]').fill('2.5')
  expect(w.locator('#storeWeight [name=weight]')).to_have_value('2.5');expect(w.locator('#storeWeightTotal')).to_contain_text('$5.00');w.locator('#storeWeight button.primary').tap();expect(w.locator('#posCart')).to_contain_text('$5.35')
  assert len(carts())==before+1 and body(current(w))['lines'][0]['weight_milli']==2500
  m=fresh();before=len(carts());product(m,choice).tap();m.locator('#flowChoices select').select_option('large');m.locator('#flowChoices button.primary').tap();expect(m.locator('#posCart')).to_contain_text('$6.42');assert len(carts())==before+1
  # An already-created empty cart is reused.
  e=fresh();e.evaluate('()=>posDo("new")');empty=current(e);before=len(carts())
  product(e,fixed).tap();expect(e.locator('#posCart')).to_contain_text('$6.41');assert current(e)==empty and len(carts())==before
  # The next product after payment starts a new sale, preserving the completed receipt.
  p.locator('#posPayNow').tap();p.locator('#checkoutTender').fill('20.00');p.locator('#checkoutComplete').tap();expect(p.locator('#posReceipt')).to_contain_text('$12.82')
  paid=rows('pos_sales');product(p,fixed).tap();expect(p.locator('#posCart')).to_be_visible();expect(p.locator('#posCart')).to_contain_text('$6.41');assert current(p)!=first and rows('pos_sales')==paid
  # A second event during automatic cart creation cannot create a second cart.
  r=fresh();held=[];r.route('**/api/pos/new',lambda route:held.append(route));before=len(carts())
  with r.expect_request('**/api/pos/new'):product(r,fixed).tap()
  product(r,fixed).dispatch_event('click');assert len(held)==1
  held[0].continue_();r.unroute('**/api/pos/new');expect(r.locator('#posCart')).to_contain_text('$6.41');assert len(carts())==before+1 and units(current(r))==1
  # Lost responses reuse the existing idempotency keys rather than duplicating products/sales.
  def lose_once(page,path):
   def lose(route):
    route.fetch();route.abort();page.unroute(path,lose)
   page.route(path,lose)
  n=fresh();before=len(carts());lose_once(n,'**/api/pos/new');product(n,fixed).tap();expect(n.locator('#posRetry')).to_be_visible();assert len(carts())==before+1
  product(n,fixed).tap();assert len(carts())==before+1
  n.locator('#posRetry').tap();expect(n.locator('#posRetry')).to_be_hidden();product(n,fixed).tap();expect(n.locator('#posCart')).to_contain_text('$6.41');assert len(carts())==before+1 and units(current(n))==1
  a=fresh();before=len(carts());lose_once(a,'**/api/pos/add');product(a,fixed).tap();expect(a.locator('#posRetry')).to_be_visible();a.locator('#posRetry').tap();expect(a.locator('#posRetry')).to_be_hidden();assert len(carts())==before+1 and units(current(a))==1
  o=fresh();before=len(carts());product(o,opened).tap();o.locator('#deskKeypadValue').fill('8.50');expect(o.locator('#deskKeypadValue')).to_have_value('8.50');lose_once(o,'**/api/pos/add');o.locator('.deskKeypadApply').tap()
  expect(o.locator('.flowError')).not_to_be_empty();o.locator('.flowProductCancel').tap();expect(o.locator('.flowError')).to_contain_text('last save is unconfirmed');expect(o.locator('[data-product-cancel-ok]')).to_have_count(0)
  o.locator('#flowChoices button.primary').tap();expect(o.locator('#posCart')).to_contain_text('$9.10');assert len(carts())==before+1 and units(current(o))==1
  for name,values in protected.items():assert rows(name)==values,name
  assert rows('pos_sales')[:len(original_sales)]==original_sales
  assert not errors,errors
  browser.close()
 print('PASS first-product mouse/touch checkout, price/weight/options, cancel messages, existing/paid sale preservation, interrupted requests, rapid taps and protected operational data')
finally:f.close()
