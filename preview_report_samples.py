"""Export actual report print views using isolated synthetic records."""
import os,uuid,time,json,datetime as dt,re,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from test_update_coordination import CoordinatorFixture
import server
f=CoordinatorFixture();out=Path('output/pdf');out.mkdir(parents=True,exist_ok=True)
def post(path,**data):
 code,r=f.call('pos/'+path,dict(request=uuid.uuid4().hex,**data));assert code==200,r;return r
try:
 post('settings',store='SAMPLE DATA — CoastYouth Retail',tax_bps=700,confirmed=True)
 for name,category,price,qty in [('Happy Camper shirt','Clothing',1800,3),('Paperback book','Books',399,4),('Desk lamp','Home',1200,2)]:
  post('product',name=name,category=category,price=price,taxable=True)
  cart=post('new')['cart'];cart=post('add',cart=cart['id'],revision=cart['revision'],name=name,category=category,price=price,quantity=qty,taxable=True)['cart'];post('cash',cart=cart['id'],revision=cart['revision'],tender=10000)
 cart=post('new')['cart'];post('add',cart=cart['id'],revision=cart['revision'],name='Sample held shirt',category='Clothing',price=1800,quantity=1,taxable=True)
 with server.connect() as c:
  c.execute("INSERT INTO pos_credit_accounts(name,kind,contact) VALUES('Sample Customer','customer','sample@example.test')")
  c.execute('INSERT INTO retail_sale_events(cart,at,actor,action,body) VALUES(?,?,?,?,?)',(cart['id'],dt.datetime.now().astimezone().isoformat(),'Admin','adjustment-request',json.dumps({'reason':'Sample discount review','amount':200})))
  account=c.execute("SELECT profile_id FROM receipt_profiles WHERE name='Employee'").fetchone()[0];now=int(time.time())
  c.execute('INSERT INTO work_periods VALUES(123,?,?,?,?,?)',(account,now-7200,now-600,'Sample Store','Sample Store'))
  c.execute('INSERT INTO work_breaks VALUES(123,123,?,?)',(now-3600,now-2700))
  c.execute('INSERT INTO work_shifts(account,start,end,location,notes,revision,job) VALUES(?,?,?,?,?,1,?)',(account,now-7200,now+14400,'Sample Store','Sample shift','Sales'))
  c.execute('INSERT INTO jobs VALUES(?,?,?)',('sample-reservation',1,json.dumps(dict(customer='Sample Customer',type='Pickup',start=dt.datetime.now().isoformat(),status='Scheduled'))))
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ['TEST_CHROMIUM']);page=b.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{f.port}/office');page.locator('#login [name=name]').fill('Admin');page.locator('#login [name=password]').fill('testpassword');page.locator('#login button').click();expect(page.locator('#officeTiles')).to_be_visible()
  css=Path('static/pos.css').read_text(encoding='utf8');files=[]
  for mode in ('sales','labor'):
   page.evaluate("mode=>{document.querySelector('#officeWork').hidden=false;retailReportCenter(document.querySelector('#officeForms'),mode);}",mode)
   choices=page.locator('.rrFilters select option').evaluate_all('(els)=>els.map(e=>[e.value,e.textContent])')
   for kind,title in choices:
    page.locator('.rrFilters select').select_option(kind);page.locator('.rrFilters button[type=submit]').count()
    page.locator('.rrFilters').evaluate('(f)=>f.requestSubmit()');expect(page.locator('.rrStatus')).not_to_have_text('Loading…');expect(page.locator('.rrResult')).not_to_be_empty()
    page.evaluate("()=>{window.print=()=>{window.reportPrintHtml=document.getElementById('retailPrintReport').outerHTML;};}");page.locator('[data-rr-print]').click();html=page.evaluate('window.reportPrintHtml')
    printpage=b.new_page();printpage.set_content('<html><head><style>'+css+'@media print{body{background:white!important}table{width:100%}th,td{overflow-wrap:anywhere}}</style></head><body class="retailPrinting">'+html.replace('<h1>','<p>SAMPLE DATA — layout review only</p><h1>',1)+'</body></html>');target=out/(kind+'.pdf');printpage.pdf(path=str(target),format='Letter',print_background=True,margin={'top':'0.4in','bottom':'0.4in','left':'0.4in','right':'0.4in'});printpage.close();files.append(target)
  b.close()
 with zipfile.ZipFile(out/'Report-layout-samples.zip','w',zipfile.ZIP_DEFLATED) as z:
  for path in files:z.write(path,path.name)
 print('Created',len(files),'actual-layout sample PDFs')
finally:f.close()
