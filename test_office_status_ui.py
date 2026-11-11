"""OFFICE status bar: signed-in state, connection changes, clock and layout."""
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright, expect

class OfficeStatusTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pw=sync_playwright().start()
  cls.browser=cls.pw.chromium.launch()
 @classmethod
 def tearDownClass(cls):
  cls.browser.close();cls.pw.stop()
 def test_identity_connection_clock_and_small_screen(self):
  page=self.browser.new_page(viewport={'width':1280,'height':720})
  try:
   page.set_content('<body class="retailOffice"><div class="workspace"></div><span id="connection">Connecting…</span></body>')
   page.add_script_tag(content="const officeMode=true;let user=null;")
   page.add_script_tag(content=Path('static/office-status.js').read_text(encoding='utf-8').replace('__OFFICE_WEB_VERSION__','0.58.0'))
   bar=page.locator('#officeStatusBar')
   expect(bar).to_contain_text('OFFICE web 0.58.0')
   expect(bar).to_contain_text('Not signed in')
   expect(bar).to_have_attribute('data-state','connecting')
   page.evaluate("user={name:'Admin <script>bad()</script>'};document.getElementById('connection').textContent='Connected to Operations'")
   expect(bar).to_contain_text('Signed in: Admin <script>bad()</script>')
   expect(bar).to_have_attribute('data-state','connected')
   expect(bar.locator('script')).to_have_count(0)
   first=bar.locator('time').get_attribute('datetime')
   page.wait_for_function("(first)=>document.querySelector('#officeStatusBar time').dateTime!==first",arg=first)
   page.evaluate("document.getElementById('connection').textContent='Connection interrupted'")
   expect(bar).to_have_attribute('data-state','disconnected')
   page.evaluate("user=null;document.getElementById('connection').textContent='Connected to Operations'")
   expect(bar).to_contain_text('Not signed in')
   expect(bar).to_have_attribute('data-state','connected')
   self.assertEqual(round(bar.bounding_box()['height']),26)
   page.evaluate("window.pywebview={api:{office_update_info:async()=>({version:'1.15.0'})}};window.dispatchEvent(new Event('pywebviewready'))")
   expect(bar).to_contain_text('OFFICE 1.15.0 | Web 0.58.0')
   page.set_viewport_size({'width':390,'height':700})
   self.assertEqual(round(bar.bounding_box()['height']),48)
   self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),390)
   expect(bar).to_be_in_viewport()
   page.emulate_media(media='print')
   expect(bar).to_be_hidden()
  finally:page.close()

if __name__=='__main__':unittest.main()
