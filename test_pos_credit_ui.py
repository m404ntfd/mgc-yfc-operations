import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture

def run():
 f=CoordinatorFixture();n=0
 def post(path,**data):
  nonlocal n
  n+=1;status,result=f.call('pos/'+path,dict(data,request=f'{n:032x}'));assert status==200,(status,result);return result
 try:
  post('settings',store='MGC YFC Preview',tax_bps=0,confirmed=True)
  a=post('account-create',kind='customer',name='Jordan Taylor',contact='Sample customer · Credit reference 1042')['account']
  a=post('account-adjust',account=a['id'],account_revision=0,amount=5000,direction='add',reason='Opening store credit — sample account')['account']
  post('account-create',kind='customer',name='Morgan Reed',contact='Sample customer')
  employee=f.call('pos/accounts')[1]['employees'][1]
  post('account-create',kind='employee',name=employee['name'],employee=employee['id'],contact='Sample employee account')
  cart=post('new')['cart'];cart=post('add',cart=cart['id'],revision=1,name='Table lamp',category='Home',price=2993,quantity=1,taxable=False)['cart']
  with sync_playwright() as pw:
   b=pw.chromium.launch(**({'executable_path':os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}));p=b.new_page(viewport={'width':1366,'height':900});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.goto(f'http://127.0.0.1:{f.port}/pos');p.locator('#login [name=name]').fill('Admin');p.locator('#login [name=password]').fill('testpassword');p.locator('#login button').click()
   expect(p.locator('#creditOpen')).to_be_visible();p.locator('#posCarts').select_option(cart['id']);p.locator('#creditOpen').click();p.locator('[data-credit="1"]').click();expect(p.locator('.creditBalance')).to_contain_text('$50.00')
   p.locator('#creditAdjust [name=amount]').fill('5');p.locator('#creditAdjust [name=reason]').fill('Customer service adjustment — example')
   assert p.evaluate('unfinished()')
   p.locator('#creditAdjust button').first.click();expect(p.locator('.creditBalance')).to_contain_text('$55.00');expect(p.locator('#creditHistory tr')).to_have_count(2)
   assert not p.evaluate('changedForms.has(document.querySelector("#creditAdjust"))')
   out=Path(os.environ.get('TEST_ARTIFACTS','test-artifacts'));out.mkdir(parents=True,exist_ok=True);p.screenshot(path=str(out/'POS-Store-Credit-Accounts-Preview.png'))
   p.locator('#creditPay [name=amount]').fill('20');p.locator('#creditPay [name=tender]').fill('10');expect(p.locator('#creditRemainder')).to_contain_text('$9.93')
   # Server commits, response is lost: retry must retrieve the original sale.
   def lose(route):
    route.fetch();route.abort();p.unroute('**/api/pos/credit',lose)
   p.route('**/api/pos/credit',lose);p.locator('#creditPay button').first.click();expect(p.locator('#creditRetry')).to_be_visible(timeout=25000)
   # Pending requests can be safely retried from the account dialog.
   p.locator('#creditRetry').click();expect(p.locator('#creditDialog')).not_to_be_visible();expect(p.locator('#posReceipt')).to_contain_text('Store credit: $20.00');expect(p.locator('#posReceipt')).to_contain_text('Change: $0.07')
   assert len(f.call('pos/sales')[1]['sales'])==1
   p.locator('#creditOpen').click();expect(p.locator('.creditBalance')).to_contain_text('$35.00');expect(p.locator('#creditHistory tr')).to_have_count(3)
   p.locator('#creditCreateDetails summary').click();p.locator('#creditCreate [name=name]').fill('New sample account');p.locator('#creditCreate button').first.click();expect(p.locator('#creditSummary')).to_contain_text('New sample account')
   for width,height in [(1366,768),(1024,768)]:
    p.set_viewport_size({'width':width,'height':height});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   assert not errors,errors;b.close()
 finally:f.close()
 print('PASS account UI, adjustments, draft tracking, credit/cash receipt, lost-response retry, account creation and compact layouts')
if __name__=='__main__':run()
