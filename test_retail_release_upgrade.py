"""Exercise the release updater against synthetic operational data from the previous release."""
from pathlib import Path
import hashlib,json,os,sqlite3,subprocess,sys,urllib.request,tempfile

workspace=Path(__file__).resolve().parent
release_root=workspace
target=Path(tempfile.mkdtemp(prefix='upgrade-integrity-'))
repository=Path(os.environ['RETAIL_BASE_SOURCE'])
baseline_version=(repository/'VERSION').read_text().strip()
target_version=(release_root/'VERSION').read_text().strip()
files=('server.py','updater.py','VERSION','README.txt','static/index.html','static/app.js','static/style.css')
for name in files:
    output=target/name;output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes((repository/name).read_bytes())
environment={**os.environ,'DISPATCH_DATA':str(target/'data'),'OneDrive':'','OneDriveConsumer':'','OneDriveCommercial':''}
subprocess.run([sys.executable,'-c','import server; server.init()'],cwd=target,env=environment,check=True)
database=target/'data/schedule.db'
with sqlite3.connect(database) as c:
    c.execute("INSERT INTO users VALUES('Existing employee','fixture-salt','fixture-hash',0)")
    c.execute("INSERT INTO receipt_profiles VALUES('Existing employee','stable-employee-id')")
    c.execute("INSERT INTO work_periods VALUES(11,'stable-employee-id',100,1000,'Office','Office')")
    c.execute("INSERT INTO work_periods VALUES(12,'stable-employee-id',1200,NULL,'Office',NULL)")
    c.execute('INSERT INTO work_breaks VALUES(21,11,200,300)')
    c.execute('INSERT INTO work_breaks VALUES(22,12,1300,NULL)')
    c.execute("INSERT INTO work_shifts(id,account,start,end,location,notes,revision,job) VALUES(31,'stable-employee-id',100,1000,'Office','Original shift notes',7,'Driver')")
    c.execute("INSERT INTO work_time_card_audit VALUES(41,11,'Existing employee','Manager','2026-11-01T10:30:00-06:00','Keep audit history','{}','{}')")
    c.execute('INSERT INTO work_assignments VALUES(?,?)',('stable-employee-id',json.dumps(dict(jobs=['Driver','Host'],sites=[],primary_job='Driver',primary_site=None,require_location=False))))
    for kind in ('Pickup','Delivery'):
        c.execute('INSERT INTO jobs VALUES(?,?,?)',(kind,8,json.dumps(dict(type=kind,start='2026-11-15T09:00',end='2026-11-15T10:00',customer='Fixture reservation',status='Scheduled',notes='Original reservation'))))
        c.execute('INSERT INTO photos VALUES(?,?,?)',(kind,0,b'original-fixture-attachment'))
    c.execute("INSERT INTO pos_products VALUES(?,?)",('fixture-product',json.dumps(dict(name='Fixture shirt',price=1200,category='Retail',taxable=True,active=True))))
    c.execute("INSERT INTO pos_carts VALUES(?,?,?,?,?,?)",('fixture-cart','stable-employee-id',3,'paid',json.dumps(dict(lines=[dict(product='fixture-product',quantity=1,price=1200)],total=1284)),1700000000))
    c.execute("INSERT INTO pos_sales VALUES(?,?,?,?)",(801,'fixture-cart','stable-employee-id',json.dumps(dict(total=1284,subtotal=1200,tax=84,tender=2000,change=716,lines=[dict(product='fixture-product',quantity=1,price=1200)]))))
    c.execute("INSERT INTO pos_credit_accounts VALUES(?,?,?,?,?,?)",(901,'Fixture customer','customer',None,'fixture contact',1))
    c.execute("INSERT INTO pos_credit_ledger VALUES(?,?,?,?,?,?,?,?)",(902,901,2500,2500,'2026-11-01','Manager','Fixture credit',None))
c.close()
def snapshot(path):
    with sqlite3.connect(path) as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        result={name:c.execute('SELECT * FROM "'+name+'" ORDER BY rowid').fetchall() for name in tables}
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    c.close()
    return result
# Normalize the synthetic fixture with the old version before taking its baseline.
subprocess.run([sys.executable,'-c','import server; server.init()'],cwd=target,env=environment,check=True)
before=snapshot(database)
pending=target/'data/pending-update';pending.mkdir()
raw=(release_root/'dist/Store-Dispatch-Update.zip').read_bytes()
(pending/'release.zip').write_bytes(raw)
(pending/'manifest.json').write_text(json.dumps(dict(version=target_version,sha256=hashlib.sha256(raw).hexdigest())))
subprocess.run([sys.executable,'-c',"import updater; backup=updater.apply(); print(backup)"],cwd=target,env=environment,check=True)
assert snapshot(database)==before,'Updater changed database records before migration'
subprocess.run([sys.executable,'-c','import server; server.init()'],cwd=target,env=environment,check=True)
after=snapshot(database)
assert {name:after[name] for name in before}==before,'Migration changed existing operational data'
backup=Path(json.loads((target/'data/last-update.json').read_text())['backup'])
assert snapshot(backup/'schedule.db')==before,'Backup did not preserve original records'
assert (target/'VERSION').read_text().strip()==target_version
subprocess.run([sys.executable,'-c',"import server; server.init()\nwith server.connect() as c:\n assert server.work_hours(c,'stable-employee-id',(0,2000),1500)==(1200,900)\nprint('Timecard totals and open break retained')"],cwd=target,env=environment,check=True)
assert {name:snapshot(database)[name] for name in before}==before,'Repeated startup changed records'
subprocess.run([sys.executable,'-c',f"import updater,json; from pathlib import Path; updater.rollback_code(Path(json.loads((updater.DATA/'last-update.json').read_text())['backup'])); assert updater.current()=={baseline_version!r}"],cwd=target,env=environment,check=True)
subprocess.run([sys.executable,'-c','import server; server.init()'],cwd=target,env=environment,check=True)
assert {name:snapshot(database)[name] for name in before}==before,'Rollback changed original records'
print(f'PASS populated {baseline_version} to {target_version} preview upgrade, backup, repeated startup and rollback; all existing rows and attachments preserved.')
