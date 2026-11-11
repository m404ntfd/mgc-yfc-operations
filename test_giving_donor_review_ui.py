"""Donor review browser checks use synthetic records and read-only API responses."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


class DonorReviewUI(unittest.TestCase):
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
        self.p = self.browser.new_page(viewport={'width': 1280, 'height': 960})
        self.errors = []
        self.p.on('pageerror', lambda e: self.errors.append(str(e)))
        self.p.set_content('<main></main>')
        self.p.add_script_tag(content=r"""
          const officeCards=[],changedForms=new Set(),calls=[];
          let officeAction=()=>{},allowed=true,mode='normal',releaseRead;
          const can=p=>p==='view_giving'||(p==='manage_donors'&&allowed);
          const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
          const posMoney=c=>'$'+(c/100).toFixed(2);
          const before={name:'Original donor',email:'old@example.test',address:'Old address',delivery:'print'};
          const after={name:'Updated donor',email:'new@example.test',address:'New <script>bad()</script>',delivery:'email'};
          const data={donors:[{id:'donor1',...after}],gifts:[],plans:[]};
          const history=[{before,after,revision:2,actor:'Staff <img src=x>',at:'2026-11-11'},
            {before:null,after:before,revision:1,actor:'Admin',at:'2026-11-10'}];
          const api=async(path,body)=>{
            if(body)throw Error('Unexpected write');
            calls.push(path);
            if(path==='giving/overview')return structuredClone(data);
            const url=new URL(path,'https://example.test/');
            if(mode==='late'){mode='normal';await new Promise(r=>releaseRead=r);}
            if(mode==='error')throw Error('History unavailable <script>bad()</script>');
            if(url.pathname==='/giving/donor_history')return {history:mode==='empty'?[]:structuredClone(history)};
            if(url.pathname==='/giving/gift_history'){
              const offset=Number(url.searchParams.get('offset'));
              return {total:26,amount:26000,offset,limit:25,has_more:offset===0,
                gifts:Array.from({length:offset===0?25:1},(_,i)=>({id:'gift'+(offset+i),day:'2025-12-01',
                  fund:'Youth <script>bad()</script>',amount:1000,reference:'Check '+(offset+i),
                  voided:url.searchParams.get('include_voided')==='true'&&i===0,
                  replaces:i===1?'original1':null,replacement:i===0?'replacement1':null}))};
            }
            throw Error('Unexpected request '+path);
          };
          const thriftModal=(title,body)=>{const d=document.createElement('section');d.innerHTML='<button class="flowClose">Close</button><p class="flowError"></p>'+body;document.querySelector('main').append(d);return d;};
          const thriftClose=d=>d.remove();
          document.addEventListener('input',e=>{if(e.target.form)changedForms.add(e.target.form)});
        """)
        self.p.add_script_tag(path=str(Path(__file__).parent/'static/giving-office.js'))
        self.p.evaluate('givingOpen()')

    def tearDown(self):
        self.p.close()
        self.assertEqual(self.errors, [])

    def test_profile_before_after_and_escaping(self):
        self.p.locator('[data-donor-history]').click()
        entries=self.p.locator('.givingDonorHistoryEntry')
        expect(entries).to_have_count(2)
        expect(entries.first).to_contain_text('Updated | Revision 2')
        expect(entries.first).to_contain_text('old@example.test')
        expect(entries.first).to_contain_text('new@example.test')
        expect(entries.first).to_contain_text('New <script>bad()</script>')
        expect(entries.first).to_contain_text('Staff <img src=x>')
        expect(entries.nth(1)).to_contain_text('Created | Revision 1')
        expect(self.p.locator('#givingContent script, #givingContent img')).to_have_count(0)
        self.assertEqual(self.p.evaluate('calls'), ['giving/overview','giving/donor_history?donor=donor1'])

    def test_profile_empty_retry_and_permission(self):
        self.p.evaluate("mode='error'")
        self.p.locator('[data-donor-history]').click()
        expect(self.p.locator('[role=alert]')).to_contain_text('History unavailable')
        self.p.evaluate("mode='empty'")
        self.p.get_by_role('button',name='Retry profile history').click()
        expect(self.p.locator('#givingContent')).to_contain_text('may predate history tracking')
        self.p.evaluate('allowed=false')
        self.p.locator('[data-cancel]').click()
        expect(self.p.locator('[data-donor-history]')).to_have_count(0)
        expect(self.p.locator('[data-donor-gifts]')).to_have_count(1)

    def test_gift_filters_paging_and_full_totals(self):
        self.p.locator('[data-donor-gifts]').click()
        result=self.p.locator('#givingGiftHistoryResults')
        expect(result).to_contain_text('26 matching entries | Received total: $260.00')
        expect(result.locator('tbody tr')).to_have_count(25)
        expect(self.p.locator('#givingHistoryPrevious')).to_be_disabled()
        self.p.locator('#givingHistoryNext').click()
        expect(result).to_contain_text('Showing 26-26 of 26')
        expect(result).to_contain_text('$260.00')
        expect(self.p.locator('#givingHistoryNext')).to_be_disabled()
        self.p.locator('#givingHistoryPrevious').click()
        expect(result).to_contain_text('Showing 1-25 of 26')
        self.p.locator('[name=year]').fill('2025')
        self.p.locator('[name=fund]').fill("Youth's 100%_Fund")
        self.p.locator('[name=include_voided]').check()
        self.p.get_by_role('button',name='Apply filters').click()
        expect(result).to_contain_text('Voided - excluded from total')
        expect(result).to_contain_text('Replaces: original1')
        expect(result).to_contain_text('Replaced by: replacement1')
        query=self.p.evaluate("Object.fromEntries(new URL(calls.at(-1),'https://example.test').searchParams)")
        self.assertEqual(query,dict(donor='donor1',year='2025',fund="Youth's 100%_Fund",include_voided='true',limit='25',offset='0'))
        expect(result.locator('script')).to_have_count(0)

    def test_gift_error_retry_and_latest_filter_wins(self):
        self.p.evaluate("mode='error'")
        self.p.locator('[data-donor-gifts]').click()
        expect(self.p.locator('[role=alert]')).to_contain_text('History unavailable')
        self.p.evaluate("mode='normal'")
        self.p.locator('#givingHistoryRetry').click()
        expect(self.p.locator('#givingHistoryNext')).to_be_visible()
        self.p.evaluate("mode='late'")
        self.p.locator('#givingHistoryNext').click()
        self.p.locator('[name=year]').fill('2024')
        self.p.get_by_role('button',name='Apply filters').click()
        expect(self.p.locator('#givingGiftHistoryResults')).to_contain_text('Showing 1-25 of 26')
        self.p.evaluate('releaseRead()')
        expect(self.p.locator('#givingGiftHistoryResults')).to_contain_text('Showing 1-25 of 26')

    def test_late_profile_and_gift_responses_after_navigation(self):
        for action in ('[data-donor-history]','[data-donor-gifts]'):
            self.p.evaluate("mode='late'")
            self.p.locator(action).click()
            expect(self.p.locator('[role=status]')).to_be_visible()
            self.p.locator('[data-tab=plans]').click()
            self.p.evaluate('releaseRead()')
            expect(self.p.locator('#givingContent')).to_contain_text('Draft monthly commitments only')
            self.p.locator('[data-tab=donors]').click()

    def test_closed_dialog_ignores_gift_response(self):
        self.p.evaluate("mode='late'")
        self.p.locator('[data-donor-gifts]').click()
        self.p.locator('.flowClose').click()
        self.p.evaluate('releaseRead()')
        expect(self.p.locator('#givingDialog')).to_have_count(0)


if __name__=='__main__':
    unittest.main()
