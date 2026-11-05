import unittest,base64,http.cookiejar,urllib.request
import test_server
class ReceiptAssignmentTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):test_server.Tests.setUpClass()
 @classmethod
 def tearDownClass(cls):test_server.Tests.tearDownClass()
 def test_guest_assignment_and_reimbursement(self):
  call=test_server.Tests.call;call('setup',{'name':'Admin','password':'testpassword'});call('user',{'name':'Employee','password':'testpassword'});call('user',{'name':'Disabled','password':'testpassword'});call('admin/permissions',{'name':'Disabled','grants':{'submit_receipts':False}});call('admin/receipt-categories',{'categories':['Office']})
  guest=urllib.request.build_opener();people=call('receipt-users',client=guest)[1]['users'];self.assertEqual([p['name'] for p in people],['Admin','Employee']);employee_id=next(p['id'] for p in people if p['name']=='Employee')
  data={'id':'e'*32,'filename':'receipt.pdf','category':'Office','body':base64.b64encode(b'%PDF-1.4 test').decode()}
  self.assertEqual(call('receipt-submit',data,guest)[0],400)
  self.assertEqual(call('receipt-submit',dict(data,assignee='stale'),guest)[0],400)
  self.assertEqual(call('receipt-submit',dict(data,assignee=employee_id,reimbursement_required='yes'),guest)[0],400)
  self.assertEqual(call('receipt-submit',dict(data,assignee=employee_id,reimbursement_required=True),guest)[0],200)
  self.assertIsNone(call('session',client=guest)[1]['user']);self.assertEqual(call('receipt-file/'+'e'*32,client=guest)[0],401)
  employee=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));call('login',{'name':'Employee','password':'testpassword'},employee)
  record=call('receipts',client=employee)[1]['receipts'][0];self.assertEqual(record['actor'],'Employee');self.assertEqual(record['guest_assigned'],1);self.assertEqual(record['reimbursement_required'],1)
  self.assertEqual(call('receipt-submit',dict(data,id='d'*32,assignee=people[0]['id']),employee)[0],200)
  record=call('receipts',client=employee)[1]['receipts'][0];self.assertEqual(record['actor'],'Employee');self.assertEqual(record['guest_assigned'],0);self.assertEqual(record['reimbursement_required'],0)
if __name__=='__main__':unittest.main()
