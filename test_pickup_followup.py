import unittest,uuid,datetime as dt,json
import server
from test_retail_workflows import WorkflowTests

class PickupTests(WorkflowTests):
 def paid(self):
  p=self.product('Sample sofa',10000,False,{'pickup_slip':True});cart=self.add(self.cart(),p)
  args=dict(cart=cart['id'],revision=cart['revision'],tender=10000,request=uuid.uuid4().hex)
  first=self.f.call('pos/cash',args);self.assertEqual(first,self.f.call('pos/cash',args));return first[1]['sale']
 def context(self,sale):return self.f.call('pos/pickup-followup?sale='+str(sale['id']))[1]
 def advance(self,sale,action):return self.ok('pickup-followup',sale=sale['id'],revision=self.context(sale)['followup']['revision'],action=action)
 def slip(self,sale):return self.ok('thrift-pickup-save',sale=sale['id'],revision=0,customer='Sample Customer',contact='555-0100',location='Bay A',due=dt.date.today().isoformat(),status='awaiting_pickup',notes='Sample only',dispatch_reference='')
 def test_delivery_atomic_link_retry_and_immutable_sale(self):
  sale=self.paid();self.assertEqual(self.context(sale)['followup']['step'],'pickup');self.advance(sale,'slip')
  self.assertEqual(self.post('pickup-followup',sale=sale['id'],revision=2,action='printed')[0],400)
  self.slip(sale);self.advance(sale,'printed');self.advance(sale,'schedule')
  self.f.call('vehicle',{'name':'Sample truck'})
  day=dt.date.today().isoformat();data=dict(type='Delivery',customer='Sample Customer',phone='555-0100',address='Sample address',items='Sample sofa',vehicle='Sample truck',start=day+'T09:00',end=day+'T10:00',status='Scheduled',retail_sale=sale['id'])
  with server.connect() as c:before=c.execute('SELECT body FROM pos_sales WHERE id=?',(sale['id'],)).fetchone()[0]
  self.assertEqual(self.f.call('save',dict(data,end=day+'T08:00'))[0],400)
  self.assertEqual(self.context(sale)['followup']['step'],'scheduling')
  self.assertEqual(self.f.call('save',data)[0],200);self.assertTrue(self.f.call('save',data)[1]['already_saved'])
  ctx=self.context(sale);self.assertEqual(ctx['followup']['step'],'done');self.assertEqual(ctx['pickup']['dispatch_reference'],ctx['followup']['appointment'])
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT body FROM pos_sales WHERE id=?',(sale['id'],)).fetchone()[0],before)
 def test_unpaid_plain_and_skip(self):
  self.add(self.cart(),self.product(rules={'pickup_slip':True}));self.assertEqual(self.f.call('pos/pickup-pending')[1]['pending'],[])
  sale=self.paid();self.advance(sale,'skip');self.assertEqual(self.context(sale)['followup']['step'],'done')
  self.assertEqual(self.post('pickup-followup',sale=sale['id'],revision=1,action='slip')[0],409)
  self.assertEqual(self.post('product-save',name='Bad',category='Retail',price=100,taxable=True,rules={'pickup_slip':'yes'})[0],400)
 def test_receipt_ownership_and_schedule_permission(self):
  self.f.call('admin/permissions',dict(name='Employee',grants={'use_pos':True},can_create=False,see_requests=False))
  e=self.f.client('pickup-employee');self.f.call('login',dict(name='Employee',password='testpassword'),e)
  sale=self.paid();self.assertEqual(self.f.call('pos/pickup-followup?sale='+str(sale['id']),client=e)[0],404)
  self.assertEqual(self.post('thrift-pickup-save',client=e,sale=sale['id'],revision=0)[0],404)
  p=self.product('Own sofa',10000,False,{'pickup_slip':True});cart=self.post('new',client=e)[1]['cart'];cart=self.post('add',client=e,cart=cart['id'],revision=cart['revision'],product=p['id'],quantity=1)[1]['cart'];own=self.post('cash',client=e,cart=cart['id'],revision=cart['revision'],tender=10000)[1]['sale']
  self.assertEqual(self.post('pickup-followup',client=e,sale=own['id'],revision=1,action='slip')[0],200)
  self.assertEqual(self.post('thrift-pickup-save',client=e,sale=own['id'],revision=0,customer='Sample',contact='555-0100',location='Bay A',due=dt.date.today().isoformat(),status='awaiting_pickup',notes='',dispatch_reference='')[0],200)
  self.assertEqual(self.post('pickup-followup',client=e,sale=own['id'],revision=2,action='printed')[0],200)
  self.assertEqual(self.post('pickup-followup',client=e,sale=own['id'],revision=3,action='schedule')[0],403)

if __name__=='__main__':unittest.main()
