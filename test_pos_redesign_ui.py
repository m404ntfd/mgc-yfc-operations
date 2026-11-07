import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture

def run():
 f=CoordinatorFixture();number=0
 def post(path,**data):
  nonlocal number
  number+=1;status,result=f.call('pos/'+path,dict(data,request=f'{number:032x}'));assert status==200,(status,result);return result
 try:
  post('settings',store='MGC YFC Preview',tax_bps=700,confirmed=True)
  products=[]
  for category,items in [('Clothing',[('Adult shirt',599),('Jeans',899),('Jacket',1499),('Children’s shirt',399)]),('Home',[('Table lamp',1299),('Picture frame',499),('Dinnerware set',1099)]),('Books & media',[('Paperback book',199),('Hardcover book',399),('DVD',299)]),('Furniture',[('Side table',2499),('Dining chair',1999)]),('Accessories',[('Handbag',799),('Belt',299),('Scarf',399)]),('Seasonal',[('Holiday decor',499),('Gift wrap',199)])]:
   for name,price in items:products.append(post('product',name=name,category=category,price=price,taxable=True)['product'])
  cart=post('new')['cart']
  for product in [products[0],products[1],products[4]]:cart=post('add',cart=cart['id'],revision=cart['revision'],product=product['id'],quantity=1)['cart']
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));p=b.new_page(viewport={'width':1366,'height':900});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.add_init_script("window.pywebview={api:{kiosk_info:async()=>({configured:true,device:'a'.repeat(32),nonce:'b'.repeat(64)}),request_exit:async()=>({error:'Preview only'})}}")
   p.goto(f'http://127.0.0.1:{f.port}/pos?kiosk=1');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
   expect(p.locator('#posCategories button')).to_have_count(7);p.locator('#posCarts').select_option(cart['id']);expect(p.locator('#posCart')).to_contain_text('$29.93')
   p.locator('[data-category=Clothing]').click();expect(p.locator('#posCatalog button')).to_have_count(4)
   p.locator('#posSearch').fill('jeans');expect(p.locator('#posCatalog button')).to_have_count(1);p.locator('#posSearch').fill('');p.locator('[data-category=""]').click()
   p.locator('#posPayNow').click();expect(p.locator('#posCash [name=tender]')).to_be_focused()
   p.locator('#posCash [name=tender]').fill('40');p.locator('#posNew').click();expect(p.locator('#posStatus')).to_contain_text('clear the cash amount');expect(p.locator('#posCarts')).to_have_value(cart['id']);p.evaluate("document.querySelector('#posCash').reset();document.querySelector('#posCashDetails').open=false")
   p.locator('#posManualShortcut').click();expect(p.locator('#posManual [name=name]')).to_be_focused();p.locator('summary').filter(has_text='Manual item').click()
   p.evaluate("document.querySelector('.eyebrow').textContent='DESIGN PREVIEW · SAMPLE ITEMS';document.querySelector('#posStatus').textContent='Sale saved · Select an item to add it to the receipt.'")
   out=Path(os.environ.get('TEST_ARTIFACTS','test-artifacts'));out.mkdir(parents=True,exist_ok=True)
   p.screenshot(path=str(out/'POS-Redesign-Preview.png'))
   for width,height in [(1366,768),(1280,800),(1024,768)]:
    p.set_viewport_size({'width':width,'height':height})
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
    for selector in ['#posPayNow','#posNew','#posExitButton']:
     rect=p.locator(selector).bounding_box();assert rect and rect['y']+rect['height']<=height+1,(selector,rect,height)
   p.set_viewport_size({'width':1366,'height':768});p.screenshot(path=str(out/'POS-Redesign-Compact-Preview.png'))
   # Receipt printing must include the receipt and exclude register/catalog chrome.
   p.locator('#posPayNow').click();p.locator('#posCash [name=tender]').fill('40');p.locator('#posCash button.primary').click();expect(p.locator('#posReceipt')).to_contain_text('Change: $10.07')
   p.emulate_media(media='print');expect(p.locator('#posReceipt')).to_be_visible();expect(p.locator('#posCatalog')).to_be_hidden();p.emulate_media(media='screen')
   p.locator('#posNew').click();expect(p.locator('#posCart')).to_contain_text('Saved on server');expect(p.locator('#posReceipt')).to_be_hidden()
   p.locator('#posSalesShortcut').click();p.locator('#posSaleList button').first.click();expect(p.locator('#posCashDetails')).to_be_hidden();expect(p.locator('#posPayNow')).to_be_disabled();p.locator('.receiptBack').click();expect(p.locator('#posReceipt')).to_be_hidden();expect(p.locator('#posCart')).to_be_visible()
   assert not errors,errors;b.close()
 finally:f.close()
 print('PASS category/search tiles, saved receipt, cash guard, shortcuts, compact screens, cash checkout and print layout')

if __name__=='__main__':run()
