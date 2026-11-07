import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture

def run():
 f=CoordinatorFixture()
 try:
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}))
   p=b.new_page(viewport={'width':1440,'height':1100},reduced_motion='reduce');errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   origin=f'http://127.0.0.1:{f.port}';p.goto(origin+'/pos')
   p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
   expect(p.locator('#posPanel')).to_be_visible();expect(p.locator('#posNew')).to_be_disabled()
   p.locator('#posAdmin summary').click();form=p.locator('#posSetup')
   form.locator('[name=store]').fill('MGC Test Store');form.locator('[name=tax]').fill('7.25');form.locator('[name=confirmed]').check();form.locator('button').click()
   expect(p.locator('#posNew')).to_be_enabled()
   product=p.locator('#posProduct');product.locator('[name=name]').fill('Catalog shirt');product.locator('[name=category]').fill('Clothing');product.locator('[name=price]').fill('3.99');product.locator('button').click()
   expect(p.locator('#posCatalog')).to_contain_text('Catalog shirt');p.locator('#posNew').click();expect(p.locator('#posCart')).to_contain_text('Saved on server')
   p.locator('[data-pos-product]').click();expect(p.locator('#posCart')).to_contain_text('$4.28')
   p.locator('summary').filter(has_text='Manual item').click();form=p.locator('#posManual')
   form.locator('[name=name]').fill('Manual item');form.locator('[name=category]').fill('Housewares');form.locator('[name=price]').fill('2.00');form.locator('[name=taxable]').uncheck();form.locator('button').click()
   expect(p.locator('#posCart')).to_contain_text('$6.28');cart=p.locator('#posCarts').input_value()
   p.reload();expect(p.locator('#posPanel')).to_be_visible();p.locator('#posCarts').select_option(cart);expect(p.locator('#posCart')).to_contain_text('$6.28')
   # Lose the response after the server commits cash. Retry must return the same receipt.
   def lose(route):
    route.fetch();route.abort();p.unroute('**/api/pos/cash',lose)
   p.route('**/api/pos/cash',lose)
   p.locator('#posCash [name=tender]').fill('10.00');p.locator('#posCash button.primary').click()
   expect(p.locator('#posRetry')).to_be_visible();p.locator('#posRetry').click()
   expect(p.locator('#posReceipt')).to_contain_text('Change: $3.72')
   with __import__('server').connect() as c:assert c.execute('SELECT COUNT(*) FROM pos_sales').fetchone()[0]==1
   p.locator('#navSales').click();expect(p.locator('#posSaleList')).to_contain_text('$6.28')
   # Opening Operations never replaces the POS or its saved cart.
   p.locator('#posNew').click();expect(p.locator('#posCart')).to_contain_text('Saved on server')
   p.locator('[data-pos-product]').click();expect(p.locator('#posCart')).to_contain_text('$4.28')
   saved=p.locator('#posCarts').input_value()
   for link,selector in [('linkClock','#workforce'),('linkReservations','#schedule'),('linkPaging','#paging')]:
    with p.expect_popup() as opened:p.locator('#'+link).click()
    operation=opened.value;expect(operation.locator(selector)).to_be_visible()
    assert operation.url.startswith(origin+'/') and '/pos' not in operation.url
    operation.close();expect(p.locator('#posCarts')).to_have_value(saved)
   p.locator('#navCheckout').click()
   p.screenshot(path=str(Path(os.environ.get('TEST_ARTIFACTS','..'))/'POS-1.0.0-Preview.png'),full_page=True)
   # POS participates in the existing safe-update acknowledgement workflow.
   f.call('update-flow/start',dict(version='99.0.0',ready=True));p.evaluate('pollFlow()')
   expect(p.locator('#updateDialog')).to_be_visible();p.locator('#updateMinimize').click()
   p.locator('#linkPaging').click();expect(p.locator('#updateDialog')).to_be_visible();expect(p.locator('#updateMinimize')).to_be_hidden()
   p.locator('#updateReady').click();expect(p.locator('#updateText')).to_contain_text('Waiting')

   assert not errors,errors;b.close()
 finally:f.close()
 print('PASS separate POS, cash checkout/retry, saved cart, Operations links and update acknowledgement')

if __name__=='__main__':run()
