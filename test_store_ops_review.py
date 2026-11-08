import unittest,base64
from test_update_coordination import CoordinatorFixture
class ReviewTests(unittest.TestCase):
 def test_hidden_messages_retained_and_review_restricted(self):
  f=CoordinatorFixture()
  try:
   other=f.client('review-employee');f.call('login',dict(name='Employee',password='testpassword'),other)
   people=f.call('comms/inbox')[1]['team'];employee=next(p['id'] for p in people if p['name']=='Employee')
   thread=f.call('comms/create',dict(kind='dm',members=[employee]))[1]['id']
   ident=f.call('comms/send',dict(thread=thread,text='Retained sample',filename='sample.txt',file=base64.b64encode(b'sample-only').decode()))[1]['id']
   self.assertEqual(f.call('comms/save',dict(id=ident,save=True),other)[0],200)
   self.assertEqual(f.call('comms/delete-message',dict(id=ident),other)[0],200)
   self.assertEqual(f.call('comms/messages?thread='+str(thread),client=other)[1]['messages'],[])
   self.assertEqual(f.call('comms/review',client=other)[0],403)
   self.assertEqual(f.call('comms/review-file/'+str(ident),client=other)[0],403)
   rows=f.call('comms/review-messages?thread='+str(thread))[1]['messages'];self.assertEqual(rows[0]['text'],'Retained sample');self.assertIn('Employee',rows[0]['saved_by']);self.assertIn('Employee',rows[0]['hidden_by'])
   self.assertEqual(len(f.call('comms/messages?thread='+str(thread))[1]['messages']),1)
  finally:f.close()
if __name__=='__main__':unittest.main()
