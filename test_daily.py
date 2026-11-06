"""Daily chooser uses host date and the exact permitted menu sections."""
import datetime as dt,sqlite3
from pathlib import Path
import test_server
from playwright.sync_api import sync_playwright,expect

def run():
 F=test_server.Tests;F.setUpClass()
 try:
  F.call('setup',{'name':'Admin','password':'testpassword'})
  with sync_playwright() as p:
   b=p.chromium.launch();page=b.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
   page.goto(f'http://127.0.0.1:{F.port}');page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click()
   expect(page.locator('#sectionChooser')).to_be_visible();assert page.locator('#sectionChoices label').all_text_contents()==['Thrift Mart Dispatch','Store Associate Paging','Receipts & Accounting','Print with a Purpose']
   page.locator('[name=section][value=receipts]').check();page.locator('#sectionChooserForm button').click();expect(page.locator('#sectionChooser')).to_be_hidden();page.reload();expect(page.locator('#receipts')).to_be_visible();expect(page.locator('#sectionChooser')).to_be_hidden()
   with sqlite3.connect(Path(F.tmp.name)/'schedule.db') as c:c.execute("UPDATE landing_preferences SET chosen_on=?",((dt.date.today()-dt.timedelta(days=1)).isoformat(),))
   c.close()
   page.reload();expect(page.locator('#sectionChooser')).to_be_visible();page.locator('[name=section][value=dispatch]').check();page.locator('#sectionChooserForm button').click();expect(page.locator('#sectionChooser')).to_be_hidden();expect(page.locator('#app')).to_be_visible()
   page.locator('.headerMenu summary').click();page.locator('#chooseStartSection').click();expect(page.locator('#sectionChooser')).to_be_visible();page.locator('#sectionChooserForm button').click();expect(page.locator('#sectionChooser')).to_be_hidden()
   b.close()
  F.call('user',{'name':'Employee','password':'testpassword'})
  F.call('logout',{});F.call('login',{'name':'Employee','password':'testpassword'})
  choices=F.call('account/landing')[1]['options'];assert [x['id'] for x in choices]==['dispatch','receipts','print'];assert F.call('account/landing',{'section':'paging'})[0]==403
 finally:F.tearDownClass()
 print('PASS day rollover, same-day reuse, manual chooser, permissions and menu parity')
if __name__=='__main__':run()
