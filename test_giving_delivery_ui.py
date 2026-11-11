"""Delivery preparation browser checks use synthetic responses and never send mail."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


class DeliveryUI(unittest.TestCase):
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
          let officeAction=()=>{},grants=['view_giving','giving_statements','giving_delivery'];
          let mode='normal',readFailed=false,refreshFailed=false,releaseRead,releaseSnapshot;
          const can=p=>grants.includes(p);
          const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
          const posMoney=c=>'$'+(c/100).toFixed(2);
          let sequence=0;
          Object.defineProperty(globalThis,'crypto',{value:{randomUUID:()=> (++sequence).toString(16).padStart(32,'0')}});
          const data={donors:[{id:'donor1',name:'Current donor',email:'current@example.test',delivery:'email'},
            {id:'donor2',name:'Second donor',email:'second@example.test',delivery:'email'}],gifts:[],plans:[]};
          const snapshot={id:'snapshot1',saved:true,donor:{id:'donor1',name:'Saved donor',address:'Test address',email:'saved@example.test',delivery:'email'},
            settings:{organization:'Test ministry',address:'Test address',ein:''},period:'2025',message:'Thank you',
            gifts:[],total:0,ytd:0,created_at:'2026-01-01',actor:'Admin'};
          const records=[];
          const api=async(path,body)=>{
            if(path==='giving/overview'){
              if(mode==='refresh'&&posts.length&&!refreshFailed){refreshFailed=true;throw Object.assign(Error('Refresh failed'),{status:403});}
              return structuredClone(data);
            }
            if(path.startsWith('giving/statement_history'))return {statements:[{id:'snapshot1',period:'2025',created_at:'2026-01-01',actor:'Admin',total:0}]};
            if(path.startsWith('giving/statement_snapshot?')){
              if(mode==='lateSnapshot')await new Promise(r=>releaseSnapshot=r);
              return structuredClone(snapshot);
            }
            if(path.startsWith('giving/statement?'))return {...structuredClone(snapshot),saved:false};
            if(path.startsWith('giving/statement_deliveries?')){
              if(mode==='readError'&&!readFailed){readFailed=true;throw Error('History unavailable');}
              if(mode==='late')await new Promise(r=>releaseRead=r);
              if(mode==='afterWriteRead'&&posts.length&&!readFailed){readFailed=true;throw Error('History unavailable');}
              return {sending_enabled:false,deliveries:structuredClone(records)};
            }
            posts.push({path,body});
            if(mode==='ambiguous'&&posts.length===1)throw Error('Connection lost');
            if(path==='giving/queue_statement'){
              records.push({id:'delivery1',statement:body.statement,recipient:snapshot.donor.email,
                actor:'Staff <script>bad()</script>',created_at:'2026-01-01',status:'prepared',cancellation:null});
            }else if(path==='giving/cancel_statement_delivery'){
              records[0].status='cancelled';records[0].cancellation={reason:body.reason,actor:'Admin',at:'2026-01-02'};
            }else throw Error('Unexpected write '+path);
            return {ok:true,id:'delivery1'};
          };
          const thriftModal=(title,body)=>{const d=document.createElement('section');d.innerHTML='<button class="flowClose">Close</button><p class="flowError"></p>'+body;document.querySelector('main').append(d);return d;};
          const thriftClose=d=>d.remove();
          document.addEventListener('input',e=>{if(e.target.form)changedForms.add(e.target.form)});
        ''')
        self.p.add_script_tag(path=str(Path(__file__).parent/'static/giving-office.js'))
        self.p.evaluate('givingOpen()')
        self.p.locator('[data-tab=statements]').click()

    def tearDown(self):
        self.p.close()
        self.assertEqual(self.errors, [])

    def open_delivery(self):
        self.p.locator('[data-snapshot]').click()
        self.p.locator('#givingDelivery').click()

    def prepare(self):
        self.p.get_by_role('button', name='Prepare email delivery', exact=True).click()

    def test_prepare_saved_recipient_and_cancel_with_audit(self):
        self.open_delivery()
        expect(self.p.locator('#givingContent')).to_contain_text('saved@example.test')
        expect(self.p.locator('#givingContent')).not_to_contain_text('current@example.test')
        self.prepare()
        expect(self.p.locator('.givingDeliveryRecord')).to_contain_text('Prepared - not sent')
        expect(self.p.locator('.givingDeliveryRecord')).to_contain_text('Staff <script>bad()</script>')
        expect(self.p.locator('#givingContent script')).to_have_count(0)
        self.assertEqual(self.p.evaluate('posts[0].body.statement'), 'snapshot1')
        self.assertNotIn('recipient', self.p.evaluate('posts[0].body'))
        self.p.get_by_role('button', name='Cancel preparation', exact=True).click()
        self.assertEqual(self.p.evaluate('posts.length'), 1)
        self.p.locator('[name=reason]').fill('   ')
        self.p.get_by_role('button', name='Cancel preparation', exact=True).click()
        expect(self.p.locator('.flowError')).to_have_text('Enter a reason for cancellation.')
        self.p.locator('[name=reason]').fill('Wrong copy <script>bad()</script>')
        self.p.get_by_role('button', name='Cancel preparation', exact=True).click()
        expect(self.p.locator('.givingDeliveryRecord')).to_contain_text('Cancelled - not sent')
        expect(self.p.locator('.givingDeliveryRecord')).to_contain_text('Wrong copy <script>bad()</script>')
        expect(self.p.locator('#givingDeliveryForm')).to_have_count(0)
        self.assertEqual(self.p.evaluate('posts[1].body.delivery'), 'delivery1')

    def test_print_preference_preview_and_permission(self):
        self.p.locator('#givingStatement [type=submit]').click()
        expect(self.p.locator('#givingStatementPreview')).to_contain_text('Statement preview')
        expect(self.p.locator('#givingDelivery')).to_have_count(0)
        self.p.evaluate("snapshot.donor.delivery='print'")
        self.open_delivery()
        expect(self.p.locator('#givingContent')).to_contain_text('uses print delivery')
        expect(self.p.locator('#givingDeliveryForm')).to_have_count(0)
        self.p.locator('[data-cancel]').click()
        self.p.evaluate("grants=grants.filter(x=>x!=='giving_delivery')")
        self.p.locator('[data-snapshot]').click()
        expect(self.p.locator('#givingStatementPreview')).to_contain_text('Saved statement')
        expect(self.p.locator('#givingDelivery')).to_have_count(0)
        self.assertEqual(self.p.evaluate('posts'), [])

    def test_read_error_retry_and_late_response(self):
        self.p.evaluate("mode='readError'")
        self.open_delivery()
        expect(self.p.locator('[role=alert]')).to_have_text('History unavailable')
        self.p.locator('#givingRetryDelivery').click()
        expect(self.p.locator('#givingDeliveryForm')).to_be_visible()
        self.p.evaluate("mode='late'")
        self.p.locator('#givingReloadDelivery').click()
        self.p.locator('[data-tab=donors]').click()
        self.p.evaluate('releaseRead()')
        expect(self.p.locator('#givingContent')).to_contain_text('Current donor')
        expect(self.p.locator('.givingDeliveryRecord')).to_have_count(0)
        self.assertEqual(self.p.evaluate('posts'), [])

    def test_ambiguous_retry_keeps_request_and_blocks_navigation(self):
        self.p.evaluate("mode='ambiguous'")
        self.open_delivery(); self.prepare()
        expect(self.p.locator('.flowError')).to_have_text('Connection lost')
        self.p.locator('[data-cancel]').click()
        expect(self.p.locator('.flowError')).to_have_text('Retry the pending save first.')
        self.p.locator('.flowClose').click()
        expect(self.p.locator('#givingDialog')).to_be_visible()
        self.prepare()
        expect(self.p.locator('.givingDeliveryRecord')).to_contain_text('Prepared - not sent')
        self.assertEqual(self.p.evaluate('posts[0]'), self.p.evaluate('posts[1]'))

    def test_overview_failure_retry_does_not_repeat_write(self):
        self.p.evaluate("mode='refresh'")
        self.open_delivery(); self.prepare()
        expect(self.p.locator('.flowError')).to_have_text('Refresh failed')
        self.prepare()
        expect(self.p.locator('.givingDeliveryRecord')).to_contain_text('Prepared - not sent')
        self.assertEqual(self.p.evaluate('posts.length'), 1)

    def test_post_write_history_failure_retries_read_only(self):
        self.p.evaluate("mode='afterWriteRead'")
        self.open_delivery(); self.prepare()
        expect(self.p.locator('[role=alert]')).to_have_text('History unavailable')
        self.p.locator('#givingRetryDelivery').click()
        expect(self.p.locator('.givingDeliveryRecord')).to_contain_text('Prepared - not sent')
        self.assertEqual(self.p.evaluate('posts.length'), 1)

    def test_saved_copy_separates_period_and_shows_setup_notice(self):
        self.p.locator('[data-snapshot]').click()
        expect(self.p.locator('#givingStatement')).to_be_hidden()
        expect(self.p.locator('#givingStatementPreview')).to_contain_text('Giving statement - 2025')
        expect(self.p.locator('#givingStatementPreview')).to_contain_text('Organization setup incomplete.')
        expect(self.p.locator('#givingStatementActions #givingPrint')).to_be_visible()
        self.p.locator('#givingNewStatement').click()
        expect(self.p.locator('#givingStatement')).to_be_visible()
        expect(self.p.locator('#givingStatementPreview')).to_be_empty()

    def test_period_edit_invalidates_pending_preview(self):
        self.p.locator('#givingStatement [type=submit]').click()
        expect(self.p.locator('#givingStatementPreview')).to_contain_text('Statement preview')
        self.p.locator('#givingStatement [name=period]').fill('2024')
        expect(self.p.locator('#givingStatementPreview')).to_be_empty()

    def test_late_saved_copy_does_not_replace_new_donor(self):
        self.p.evaluate("mode='lateSnapshot'")
        self.p.locator('[data-snapshot]').click()
        self.p.locator('#givingStatement [name=donor]').select_option('donor2')
        self.p.evaluate('releaseSnapshot()')
        expect(self.p.locator('#givingStatementPreview')).to_be_empty()
        expect(self.p.locator('#givingDelivery')).to_have_count(0)


if __name__ == '__main__':
    unittest.main()

