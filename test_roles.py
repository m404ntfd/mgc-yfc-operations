import unittest,http.cookiejar,urllib.request
import test_server
class RoleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):test_server.Tests.setUpClass()
 @classmethod
 def tearDownClass(cls):test_server.Tests.tearDownClass()
 def test_role_updates_delegation_and_individual_preservation(self):
  call=test_server.Tests.call;call('setup',{'name':'Admin','password':'testpassword'})
  for name in ('Employee','RoleEditor'):call('user',{'name':name,'password':'testpassword'})
  clients={name:urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())) for name in ('Employee','RoleEditor')}
  for name,client in clients.items():call('login',{'name':name,'password':'testpassword'},client)
  self.assertEqual(call('roles',client=clients['Employee'])[0],403)
  catalog=call('roles')[1];self.assertIn('manage_roles',catalog['groups']['Application Settings']);self.assertIn('submit_receipts',catalog['groups']['Receipts & Accounting'])
  role=call('roles',{'name':'Receipt Staff','grants':{'submit_receipts':True}})[1]['id']
  self.assertEqual(call('admin/user-role',{'name':'Employee','role_id':role})[0],200)
  grants=call('session',client=clients['Employee'])[1]['user']['grants'];self.assertTrue(grants['submit_receipts']);self.assertFalse(grants['view_schedule'])
  self.assertEqual(call('roles',{'id':role,'name':'Receipt Staff','grants':{'view_schedule':True,'submit_receipts':False}})[0],200)
  grants=call('session',client=clients['Employee'])[1]['user']['grants'];self.assertTrue(grants['view_schedule']);self.assertFalse(grants['submit_receipts'])
  self.assertNotIn('Employee',[p['name'] for p in call('receipt-users')[1]['users']])
  self.assertEqual(call('admin/permissions',{'name':'Employee','grants':{}})[0],409)
  self.assertEqual(call('admin/user-role',{'name':'Employee','role_id':None})[0],200)
  self.assertTrue(call('session',client=clients['Employee'])[1]['user']['grants']['submit_receipts'])
  call('admin/permissions',{'name':'RoleEditor','grants':{'manage_roles':True,'submit_receipts':True}})
  self.assertEqual(call('roles',{'name':'Limited','grants':{'submit_receipts':True}},clients['RoleEditor'])[0],200)
  self.assertEqual(call('roles',{'name':'Escalation','grants':{'install_updates':True}},clients['RoleEditor'])[0],403)
  self.assertEqual(call('admin/user-role',{'name':'Admin','role_id':role})[0],403)
  call('account/landing',{'section':'print'});call('account/landing',{'section':'receipts'});self.assertEqual(call('account/landing')[1]['home_section'],'receipts')
if __name__=='__main__':unittest.main()
