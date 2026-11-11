"""Synthetic browser tests for corrections and ambiguous save responses."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


class GiftCorrectionUI(unittest.TestCase):
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
        self.p = self.browser.new_page()
        self.errors = []
        self.p.on('pageerror', lambda e: self.errors.append(str(e)))
        self.p.set_content('<main></main>')
        self.p.add_script_tag(content=r'''
          const officeCards=[],changedForms=new Set(),posts=[];
          let officeAction=()=>{},grants=['view_giving','record_gifts','adjust_gifts'];
          let mode='normal',refreshFailed=false;
          const can=p=>grants.includes(p);
          const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
          const posMoney=c=>'$'+(c/100).toFixed(2),posCents=v=>Math.round(Number(v)*100);
          // set_content has an opaque origin; provide only the UUID helper used by saves.
          Object.defineProperty(globalThis,'crypto',{value:{randomUUID:()=> '11111111-1111-4111-8111-111111111111'}});
          const gift={id:'original',donor:'donor1',donor_name:'Example Donor',day:'2025-12-15',
            amount:10000,method:'check',reference:'Check 123',fund:'Ministry',benefit:'Dinner',
            benefit_value:1500,actor:'Admin',at:'2026-01-01T12:00:00Z',voided:false};
          const data={donors:[{id:'donor1',name:'Example Donor',email:'',delivery:'print'}],gifts:[gift],plans:[]};
          const api=async(path,body)=>{
            if(path==='giving/overview'){
              if(mode==='refresh'&&posts.length&&!refreshFailed){refreshFailed=true;throw Object.assign(Error('Refresh failed'),{status:403});}
              return structuredClone(data);
            }
            posts.push({path,body});
            if(mode==='conflict')throw Object.assign(Error('Gift already voided.'),{status:409});
            if(mode==='ambiguous'&&posts.length===1)throw Error('Connection lost');
            if(path!=='giving/replace_gift')throw Error('Unexpected write '+path);
            gift.voided=true;gift.replacement='replacement';
            gift.correction={reason:body.reason,actor:'Admin',at:'2026-11-11T12:00:00Z'};
            data.gifts.push({...body,id:'replacement',donor_name:'Example Donor',actor:'Admin',
              at:'2026-11-11T12:00:00Z',voided:false,replaces:'original'});
            return {ok:true,id:'replacement'};
          };
          const thriftModal=(title,body)=>{
            const d=document.createElement('section');
            d.innerHTML='<button class="flowClose">Close</button><p class="flowError"></p>'+body;
            document.querySelector('main').append(d);return d;
          };
          const thriftClose=d=>d.remove();
          document.addEventListener('input',e=>{if(e.target.form)changedForms.add(e.target.form)});
        ''')
        self.p.add_script_tag(path=str(Path(__file__).parent / 'static/giving-office.js'))
        self.p.evaluate('givingOpen()')
        self.p.locator('[data-tab=gifts]').click()

    def tearDown(self):
        self.p.close()
        self.assertEqual(self.errors, [])

    def edit(self):
        self.p.locator('[data-correct-gift=original]').click()
        self.p.locator('[name=amount]').fill('125.50')
        self.p.locator('[name=reason]').fill('Correct amount <script>bad()</script>')

    def save(self):
        self.p.get_by_role('button', name='Save correction', exact=True).click()

    def test_prefill_required_reason_payload_and_links(self):
        self.p.locator('[data-correct-gift=original]').click()
        for key, value in {'donor':'donor1','day':'2025-12-15','amount':'100','method':'check',
                           'reference':'Check 123','fund':'Ministry','benefit':'Dinner','benefit_value':'15'}.items():
            expect(self.p.locator(f'[name={key}]')).to_have_value(value)
        self.save()
        self.assertEqual(self.p.evaluate('posts'), [])
        self.p.locator('[name=amount]').fill('125.50')
        self.p.locator('[name=reason]').fill('Correct amount <script>bad()</script>')
        self.save()
        expect(self.p.locator('[data-gift-row]')).to_have_count(2)
        post = self.p.evaluate('posts[0]')
        self.assertEqual(post['path'], 'giving/replace_gift')
        self.assertEqual(post['body']['gift'], 'original')
        self.assertEqual(post['body']['amount'], 12550)
        self.assertEqual(post['body']['benefit_value'], 1500)
        self.assertNotIn('id', post['body'])
        expect(self.p.locator('[data-gift-row=original]')).to_contain_text('Voided')
        expect(self.p.locator('[data-gift-row=original]')).to_contain_text('Correct amount <script>bad()</script>')
        expect(self.p.locator('#givingContent script')).to_have_count(0)
        expect(self.p.locator('[data-correct-gift=original]')).to_have_count(0)
        self.p.locator('[data-gift-link=original]').click()
        expect(self.p.locator('[data-gift-row=original]')).to_be_focused()

    def test_ambiguous_retry_reuses_request(self):
        self.p.evaluate("mode='ambiguous'")
        self.edit(); self.save()
        expect(self.p.locator('.flowError')).to_have_text('Connection lost')
        self.p.locator('[data-cancel]').click()
        expect(self.p.locator('.flowError')).to_have_text('Retry the pending save first.')
        self.p.locator('[name=amount]').fill('200')
        self.save()
        self.assertEqual(self.p.evaluate('posts.length'), 1)
        self.p.locator('[name=amount]').fill('125.50')
        self.save()
        expect(self.p.locator('[data-gift-row]')).to_have_count(2)
        self.assertEqual(self.p.evaluate('posts[0]'), self.p.evaluate('posts[1]'))

    def test_refresh_failure_does_not_repeat_write(self):
        self.p.evaluate("mode='refresh'")
        self.edit(); self.save()
        expect(self.p.locator('.flowError')).to_have_text('Refresh failed')
        self.save()
        expect(self.p.locator('[data-gift-row]')).to_have_count(2)
        self.assertEqual(self.p.evaluate('posts.length'), 1)

    def test_conflict_keeps_values_and_allows_cancel(self):
        self.p.evaluate("mode='conflict'")
        self.edit(); self.save()
        expect(self.p.locator('.flowError')).to_have_text('Gift already voided.')
        expect(self.p.locator('[name=amount]')).to_have_value('125.50')
        self.p.once('dialog', lambda dialog: dialog.accept())
        self.p.locator('[data-cancel]').click()
        expect(self.p.locator('[data-gift-row]')).to_have_count(1)

    def test_requires_both_permissions(self):
        for grants in [['view_giving','adjust_gifts'],['view_giving','record_gifts']]:
            self.p.evaluate('(v)=>grants=v', grants)
            self.p.locator('[data-tab=donors]').click()
            self.p.locator('[data-tab=gifts]').click()
            expect(self.p.locator('[data-correct-gift]')).to_have_count(0)
        self.assertEqual(self.p.evaluate('posts'), [])


if __name__ == '__main__':
    unittest.main()
