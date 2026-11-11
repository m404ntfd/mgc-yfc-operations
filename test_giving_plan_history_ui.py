"""Browser checks for monthly draft history using synthetic, in-memory API data."""
import os
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


class MonthlyHistoryUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        options = {'executable_path': os.environ['TEST_CHROMIUM']} if os.environ.get('TEST_CHROMIUM') else {}
        cls.browser = cls.pw.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1200, 'height': 1000})
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.set_content('<main></main>')
        self.page.add_script_tag(content=r'''
          const officeCards=[], changedForms=new Set();
          let officeAction=()=>{}, allowed=true, historyMode='normal', historyRelease;
          const calls=[];
          const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
          const can=p=>p==='view_giving'||(p==='manage_giving_plans'&&allowed);
          const posMoney=c=>'$'+(c/100).toFixed(2);
          const before={id:'plan1',revision:1,donor:'donor1',amount:2500,start:'2026-12-01',billing_day:1,fund:'Ministry',status:'draft'};
          const after={...before,revision:2,amount:4000,fund:'Youth <script>bad()</script>',status:'cancelled'};
          const overview={donors:[{id:'donor1',name:'Example Donor',email:'',delivery:'print'}],gifts:[],plans:[after]};
          const history=[{before,after,revision:2,actor:'Admin <img src=x onerror=bad()>',at:'2026-11-11T15:00:00Z'},
                         {before:null,after:before,revision:1,actor:'Admin',at:'2026-11-10T15:00:00Z'}];
          const api=async path=>{
            calls.push(path);
            if(path==='giving/overview')return overview;
            if(path==='giving/plan_history?id=plan1'){
              if(historyMode==='delayed')await new Promise(resolve=>historyRelease=resolve);
              if(historyMode==='error')throw Error('History unavailable <script>bad()</script>');
              return {history:historyMode==='empty'?[]:history};
            }
            throw Error('Unexpected API call '+path);
          };
          const thriftModal=(title,body)=>{
            const dialog=document.createElement('section');
            dialog.innerHTML='<button class="flowClose">Close</button><p class="flowError"></p>'+body;
            document.querySelector('main').append(dialog);return dialog;
          };
          const thriftClose=d=>d.remove();
        ''')
        self.page.add_script_tag(path=str(Path(__file__).parent / 'static/giving-office.js'))
        self.page.evaluate('givingOpen()')
        self.page.locator('[data-tab=plans]').click()

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])

    def test_before_after_audit_and_escaped_values(self):
        self.page.locator('[data-plan-history]').click()
        entries = self.page.locator('.givingPlanHistoryEntry')
        expect(entries).to_have_count(2)
        expect(entries.nth(0)).to_contain_text('Cancelled � Revision 2')
        expect(entries.nth(0)).to_contain_text('$25.00')
        expect(entries.nth(0)).to_contain_text('$40.00')
        expect(entries.nth(0)).to_contain_text('2026-11-11T15:00:00Z')
        expect(entries.nth(0)).to_contain_text('Admin <img src=x onerror=bad()>')
        expect(entries.nth(0)).to_contain_text('Youth <script>bad()</script>')
        expect(entries.nth(1)).to_contain_text('Created � Revision 1')
        expect(entries.nth(1).locator('tbody tr').first.locator('td').first).to_have_text('-')
        expect(self.page.locator('#givingContent script, #givingContent img')).to_have_count(0)
        self.assertEqual(self.page.evaluate('calls'), ['giving/overview', 'giving/plan_history?id=plan1'])
        self.page.locator('[data-cancel]').click()
        expect(self.page.locator('[data-edit-plan]')).to_have_count(1)

    def test_legacy_empty_history(self):
        self.page.evaluate("historyMode='empty'")
        self.page.locator('[data-plan-history]').click()
        expect(self.page.locator('#givingContent')).to_contain_text('may predate history tracking')
        expect(self.page.locator('.givingPlanHistoryEntry')).to_have_count(0)

    def test_error_and_retry(self):
        self.page.evaluate("historyMode='error'")
        self.page.locator('[data-plan-history]').click()
        expect(self.page.locator('[role=alert]')).to_have_text('History unavailable <script>bad()</script>')
        self.page.evaluate("historyMode='normal'")
        self.page.get_by_role('button', name='Retry history').click()
        expect(self.page.locator('.givingPlanHistoryEntry')).to_have_count(2)

    def test_late_response_does_not_replace_editor(self):
        self.page.evaluate("historyMode='delayed'")
        self.page.locator('[data-plan-history]').click()
        expect(self.page.locator('[role=status]')).to_have_text('Loading history.')
        self.page.locator('[data-cancel]').click()
        self.page.locator('[data-edit-plan]').click()
        self.page.locator('[name=amount]').fill('99')
        self.page.evaluate('historyRelease()')
        expect(self.page.locator('[name=amount]')).to_have_value('99')
        expect(self.page.locator('.givingPlanHistoryEntry')).to_have_count(0)

    def test_permission_hides_history(self):
        self.page.evaluate('allowed=false')
        self.page.locator('[data-tab=donors]').click()
        self.page.locator('[data-tab=plans]').click()
        expect(self.page.locator('[data-plan-history], [data-edit-plan]')).to_have_count(0)
        self.assertEqual(self.page.evaluate('calls'), ['giving/overview'])

    def test_closed_dialog_ignores_response(self):
        self.page.evaluate("historyMode='delayed'")
        self.page.locator('[data-plan-history]').click()
        self.page.locator('.flowClose').click()
        self.page.evaluate('historyRelease()')
        expect(self.page.locator('#givingDialog')).to_have_count(0)


if __name__ == '__main__':
    unittest.main()
