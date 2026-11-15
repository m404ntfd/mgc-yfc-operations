import json,unittest,uuid,urllib.request
from test_cash_advances import CashAdvanceTests
import server

class TerminalDeviceTests(unittest.TestCase):
 setUp=CashAdvanceTests.setUp
 tearDown=CashAdvanceTests.tearDown
 post=CashAdvanceTests.post
 ok=CashAdvanceTests.ok
 def options(self):return self.f.call('pos/terminal-options?device='+self.device)[1]
 def public(self,path,token,data=None):
  req=urllib.request.Request(f'http://127.0.0.1:{self.f.port}/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-Display-Token':token,'X-Dispatch':'1','Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:
   with e:return e.code,json.load(e)
 def test_display_ownership_branding_rotation_and_customer_entry(self):
  self.ok('terminal-options-save',terminal=self.terminal,revision=0,printer='Fixture printer',replace_display=False)
  opts=self.options();token=opts['display_path'].split('#')[1];self.assertEqual(opts['terminal']['store_name'],'Thrift Mart')
  self.ok('store-display-save',store_id='thrift-mart',revision=0,enabled=True,welcome='Thrift hello',thanks='Thrift thanks')
  self.assertEqual(self.public('customer-display',token)[1]['welcome'],'Thrift hello')
  other=self.ok('terminal-save',name='Binopoly checkout',device='2'*32,enabled=True,store_id='binopoly')['id']
  self.assertEqual(self.post('display-state',token=token,device='2'*32,cart=None,sale=None)[0],403)
  request=self.ok('customer-entry-start',device=self.device)
  code,result=self.public('customer-entry',token,dict(id=request['id'],name='Sample person',phone='2285550101',email='sample@example.com',marketing=False));self.assertEqual(code,200,result)
  public=self.public('customer-display',token)[1];self.assertNotIn('sample@example.com',json.dumps(public));self.assertEqual(public['entry']['status'],'submitted')
  private=self.f.call('pos/customer-entry?id='+request['id']+'&device='+self.device)[1];self.assertEqual(private['details']['phone'],'(228) 555-0101')
  self.ok('customer-entry-close',device=self.device,id=request['id']);self.assertNotIn('entry',self.public('customer-display',token)[1])
  self.ok('terminal-options-save',terminal=self.terminal,revision=1,printer='Fixture printer',replace_display=True)
  self.assertEqual(self.public('customer-display',token)[0],404)
 def test_printer_configuration_requires_permission_and_revision(self):
  self.ok('terminal-options-save',terminal=self.terminal,revision=0,printer='Fixture printer')
  self.assertEqual(self.post('terminal-options-save',terminal=self.terminal,revision=0,printer='Wrong')[0],409)
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  employee=self.f.client('e');self.f.call('login',dict(name='Employee',password='testpassword'),employee)
  self.assertEqual(self.post('terminal-options-save',client=employee,device=self.device,revision=1,printer='Wrong')[0],403)
  self.assertEqual(self.options()['printer'],'Fixture printer')
if __name__=='__main__':unittest.main()
