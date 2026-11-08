import os,uuid,unittest,json,sqlite3
from pathlib import Path
from test_update_coordination import CoordinatorFixture
import server
class RetailTests(unittest.TestCase):
 def setUp(self):self.f=CoordinatorFixture()
 def tearDown(self):self.f.close()
 def post(self,path,**data):return self.f.call('pos/'+path,dict(data,request=uuid.uuid4().hex))
 def test_config(self):
  f=self.f
  p=self.post('product',name='Shirt',category='Clothing',price=599,taxable=True)[1]['product']['id']
  data=dict(name='Main',columns=4,groups=[dict(name='Clothing',color='#336699',products=[p])])
  code,l=self.post('layout-save',**data);self.assertEqual(code,200,l)
  self.assertEqual(self.post('layout-save',**dict(data,id=l['id'],revision=0))[0],409)
  self.assertEqual(self.post('layout-save',**dict(data,groups=[dict(name='Bad',color='red',products=[p])]))[0],400)
  t=dict(name='Front 1',layout=l['id'],enabled=True,device='a'*32)
  code,terminal=self.post('terminal-save',**t);self.assertEqual(code,200,terminal)
  self.assertEqual(self.post('terminal-save',**dict(t,name='Front 2'))[0],409)
  self.assertEqual(self.post('terminal-save',**dict(t,name='front 1',device='b'*32))[0],409)
  code,result=f.call('pos/terminal?device='+'a'*32);self.assertEqual(result['layout']['name'],'Main')
  e=f.client('e');f.call('login',dict(name='Employee',password='testpassword'),e)
  self.assertEqual(f.call('pos/retail-config',client=e)[0],403)
  self.assertEqual(f.call('pos/layout-save',dict(data,request=uuid.uuid4().hex),e)[0],403)
  # Exact operational rows survive both additive migration and repeat startup.
  with server.connect() as c:
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
   before={t:[tuple(r) for r in c.execute('SELECT * FROM "'+t+'"')] for t in tables}
   server.init_pos(c);server.init_pos(c)
   for t in tables:self.assertEqual(before[t],[tuple(r) for r in c.execute('SELECT * FROM "'+t+'"')],t)
if __name__=='__main__':unittest.main()
