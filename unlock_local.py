"""Host-only recovery when no authorized employee can sign in.
Run with the bundled Python on the Windows server, using the server's data folder.
No network endpoint is exposed; access to the database file is required.
"""
from contextlib import closing
import argparse,datetime,os,sqlite3
from pathlib import Path

def unlock(data,name):
 db=Path(data)/'schedule.db'
 if not db.is_file():raise ValueError('No schedule.db found in the selected data folder.')
 with closing(sqlite3.connect(db,timeout=15)) as c, c:
  user=c.execute('SELECT name FROM users WHERE name=?',(name,)).fetchone()
  if not user:raise ValueError('User not found.')
  c.execute('DELETE FROM account_lockouts WHERE name=?',(user[0],))
  c.execute('INSERT INTO audit VALUES(?,?,?,?)',(datetime.datetime.now().isoformat(timespec='seconds'),'Local host recovery','Account unlocked: '+user[0],''))
 return user[0]
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('name');p.add_argument('--data',default=os.environ.get('DISPATCH_DATA',str(Path(__file__).resolve().parent/'data')));args=p.parse_args()
 try:print('Unlocked '+unlock(args.data,args.name))
 except (ValueError,sqlite3.Error) as e:p.exit(1,str(e)+'\n')
