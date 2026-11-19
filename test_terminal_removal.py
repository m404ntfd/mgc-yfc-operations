"""Removing a register never removes its financial history or reporting."""
import json,unittest,uuid
from test_cash_advances import CashAdvanceTests
from test_retail_workflows import WorkflowTests
import server

class TerminalRemovalTests(unittest.TestCase):
 setUp=CashAdvanceTests.setUp
 tearDown=CashAdvanceTests.tearDown
 post=CashAdvanceTests.post
 ok=CashAdvanceTests.ok
 setup=CashAdvanceTests.setup
 payload=CashAdvanceTests.payload
 query=CashAdvanceTests.query
 drawers=CashAdvanceTests.drawers
 product=WorkflowTests.product
 cart=WorkflowTests.cart
 add=WorkflowTests.add

 def terminal_row(self):
  with server.connect() as c:return dict(c.execute('SELECT * FROM retail_terminals WHERE id=?',(self.terminal,)).fetchone())
 def remove(self,**extra):return self.post('terminal-remove',id=self.terminal,revision=self.terminal_row()['revision'],confirmed=True,**extra)
 def report(self,kind):
  code,data=self.f.call(self.query(kind,store_id='thrift-mart'));self.assertEqual(code,200,data)
  data.pop('document',None);return data

 def test_removal_preserves_every_sale_report_drawer_and_original_audit_entry(self):
  drawer=self.drawers()
  code,advance=self.f.call('pos/cash-advance',self.payload());self.assertEqual(code,200,advance)
  cart=self.add(self.cart(device=self.device),self.product(price=1237,taxable=False),device=self.device)
  cart=self.ok('thrift-donation',cart=cart['id'],revision=cart['revision'],amount=0,roundup=True,device=self.device)['cart']
  sale=self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=1300,device=self.device)['sale']
  current=self.f.call('pos/drawers')[1]['drawers'][0]
  self.ok('drawer-close',id=drawer['id'],counted=current['expected'],expected=current['expected'],reason='Fixture end of day')
  with server.connect() as c:
   c.execute("INSERT INTO work_periods VALUES(911,?,100,NULL,'Store',NULL)",(self.people['Employee'],))
   c.execute('INSERT INTO work_breaks VALUES(912,911,200,NULL)')
   c.execute("INSERT INTO jobs VALUES('fixture-reservation',4,?)",(json.dumps({'customer':'Fixture','notes':'Keep original reservation'}),))
   c.execute("INSERT INTO photos VALUES('fixture-reservation',0,?)",(b'original attachment',))
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('retail_terminals','retail_removed_terminals','audit','pos_operations')")]
   before={name:[tuple(r) for r in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in tables}
   audit=[tuple(r) for r in c.execute('SELECT * FROM audit ORDER BY rowid')]
  kinds=['dashboard','sales','transactions','products','cash','drawer','shift','cash-advances','journal','tax-audit']
  reports={kind:self.report(kind) for kind in kinds}
  self.assertIn('SAMPLE Front checkout',str(reports['cash']))
  self.assertTrue(reports['transactions']['rows']);self.assertTrue(reports['cash-advances']['rows'])
  receipt_before=self.f.call('pos/sales')[1];drawers_before=self.f.call('pos/drawers')[1]
  args=dict(id=self.terminal,revision=self.terminal_row()['revision'],confirmed=True,request=uuid.uuid4().hex)
  result=self.f.call('pos/terminal-remove',args);self.assertEqual(result[0],200,result)
  self.assertEqual(self.f.call('pos/terminal-remove',args),result) # Safe replay after a lost response.
  config=self.f.call('pos/retail-config')[1];self.assertEqual(config['terminals'],[])
  self.assertEqual(config['removed_terminals'][0]['name'],'SAMPLE Front checkout')
  for kind in kinds:self.assertEqual(self.report(kind),reports[kind],kind)
  self.assertEqual(self.f.call('pos/sales')[1],receipt_before)
  self.assertEqual(self.f.call('pos/drawers')[1],drawers_before)
  with server.connect() as c:
   server.devices_init(c);server.devices_init(c)
   for name,rows in before.items():self.assertEqual(rows,[tuple(r) for r in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')],name)
   after=[tuple(r) for r in c.execute('SELECT * FROM audit ORDER BY rowid')]
   self.assertEqual(after[:len(audit)],audit);self.assertEqual(len(after),len(audit)+1)
   self.assertIn('Removed terminal SAMPLE Front checkout',after[-1][2])
   self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')

 def test_open_held_sales_and_drawers_block_removal_without_modifying_any_records(self):
  cart=self.add(self.cart(device=self.device),self.product(),device=self.device)
  before=self.terminal_row();code,error=self.remove();self.assertEqual(code,409,error);self.assertIn('sales',error['error'])
  cart=self.ok('hold',cart=cart['id'],revision=cart['revision'],device=self.device)['cart']
  self.assertEqual(self.remove()[0],409)
  self.assertEqual(self.terminal_row(),before)
  self.assertEqual(self.f.call('pos/overview?device='+self.device)[1]['carts'][0],cart)
  cart=self.ok('resume',cart=cart['id'],revision=cart['revision'],device=self.device)['cart']
  self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=cart['total'],device=self.device)
  drawer=self.drawers();self.assertEqual(self.remove()[0],409)
  self.ok('drawer-close',id=drawer['id'],counted=10000,expected=10000,reason='Fixture count')
  self.assertEqual(self.remove()[0],200)

 def test_permission_confirmation_stale_revision_and_explicit_restore(self):
  staff=self.f.client('b');self.f.call('login',dict(name='Employee',password='testpassword'),staff)
  args=dict(id=self.terminal,revision=1,confirmed=True)
  self.assertEqual(self.post('terminal-remove',client=staff,**args)[0],403)
  self.assertEqual(self.post('terminal-remove',**dict(args,confirmed=False))[0],400)
  self.assertEqual(self.post('terminal-remove',**dict(args,revision=0))[0],409)
  self.assertEqual(self.post('terminal-remove',**dict(args,id={}))[0],400)
  old=self.terminal_row();self.ok('terminal-remove',**args)
  self.assertEqual(self.post('terminal-save',**old)[0],409)
  self.assertEqual(self.post('store-terminal',terminal=self.terminal,store_id='binopoly',previous='thrift-mart')[0],409)
  self.assertEqual(self.post('new',device=self.device)[0],403)
  self.assertEqual(self.f.call('pos/terminal?device='+self.device)[1],dict(terminal=None,layout=None,removed=True))
  info=dict(app='pos',device=self.device,version='1.20.0',computer=dict(id='2'*32,hostname='FIXTURE',macs=[],os='Windows test'))
  self.assertIsNone(self.f.call('computers/self',info)[1]['terminal'])
  registration=dict(id='2'*32,revision=0,name='SAMPLE Front checkout',role='pos',app='pos',device=self.device)
  self.assertEqual(self.f.call('computers/register',registration)[0],409)
  self.assertEqual(self.post('terminal-restore',client=staff,id=self.terminal,revision=2,confirmed=True)[0],403)
  self.assertEqual(self.post('terminal-restore',id=self.terminal,revision=1,confirmed=True)[0],409)
  self.ok('terminal-restore',id=self.terminal,revision=2,confirmed=True)
  restored=self.terminal_row();self.assertEqual(restored,dict(old,revision=3))
  self.assertEqual(self.f.call('computers/self',info)[1]['terminal']['name'],old['name'])
  self.assertEqual(self.f.call('pos/retail-config')[1]['removed_terminals'],[])
  self.assertEqual(self.post('new',device=self.device)[0],200)

 def test_admin_can_re_register_original_terminal_without_changing_history(self):
  cart=self.add(self.cart(device=self.device),self.product(price=1237,taxable=False),device=self.device)
  self.ok('cash',cart=cart['id'],revision=cart['revision'],tender=cart['total'],device=self.device)
  before=self.terminal_row();self.assertEqual(self.remove()[0],200)
  info=dict(app='pos',device=self.device,version='1.20.1',computer=dict(id='2'*32,hostname='RECOVERY-PC',macs=[],os='Windows test'))
  state=self.f.call('computers/self',info)[1];removed=state['removed_terminal']
  self.assertIsNone(state['terminal']);self.assertEqual(removed['id'],self.terminal);self.assertEqual(removed['store_id'],'thrift-mart')
  with server.connect() as c:
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'retail_computer%' AND name NOT IN ('audit','retail_terminals','retail_removed_terminals')")]
   rows={name:[tuple(r) for r in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')] for name in tables}
  reports={kind:self.report(kind) for kind in ['sales','transactions','products','cash','journal','tax-audit']}
  args=dict(id='2'*32,revision=state['computer']['revision'],name='SAMPLE Front checkout',role='pos',app='pos',device=self.device,restore_terminal=removed['id'],terminal_revision=removed['revision'],confirm_restore=True)
  staff=self.f.client('r');self.f.call('login',dict(name='Employee',password='testpassword'),staff)
  self.assertEqual(self.f.call('computers/register',args,staff)[0],403)
  for delta in [dict(confirm_restore=False),dict(terminal_revision=0),dict(restore_terminal='wrong'),dict(revision=99)]:
   self.assertEqual(self.f.call('computers/register',dict(args,**delta))[0],409)
  self.assertIsNone(self.f.call('computers/self',info)[1]['terminal']) # Heartbeats never reactivate it.
  self.assertEqual(self.f.call('computers/register',args)[0],200)
  self.assertEqual(self.terminal_row(),dict(before,revision=before['revision']+2,enabled=1))
  restored=self.f.call('computers/self',info)[1];self.assertEqual(restored['terminal']['id'],self.terminal);self.assertIsNone(restored['removed_terminal'])
  with server.connect() as c:
   for name,expected in rows.items():self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid')],expected,name)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM retail_terminals').fetchone()[0],1)
   self.assertTrue(c.execute("SELECT 1 FROM audit WHERE action LIKE 'Re-registered removed terminal%' AND actor='Admin'").fetchone())
  for kind,report in reports.items():self.assertEqual(self.report(kind),report,kind)

 def test_default_roundup_and_saved_off_setting_survive_repeated_startup(self):
  settings=self.f.call('pos/thrift-config')[1]['settings'];self.assertTrue(settings['donations']);self.assertEqual(settings['revision'],0)
  self.ok('thrift-settings',**dict(settings,donations=False))
  with server.connect() as c:
   before=tuple(c.execute('SELECT * FROM thrift_settings').fetchone());server.thrift_init(c);server.thrift_init(c)
   self.assertEqual(tuple(c.execute('SELECT * FROM thrift_settings').fetchone()),before)
  self.assertFalse(self.f.call('pos/thrift-config')[1]['settings']['donations'])

if __name__=='__main__':unittest.main()
