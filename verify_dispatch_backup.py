"""Read-only host preflight: compare live dispatch entries with a full backup ZIP."""
import argparse,contextlib,json,sqlite3,tempfile,zipfile
from pathlib import Path

def verify(data,backup):
 data=Path(data);backup=Path(backup)
 if not (data/'schedule.db').is_file():raise ValueError('No schedule.db found in the selected server data folder.')
 with tempfile.TemporaryDirectory() as temp:
  live=Path(temp)/'live.db';saved=Path(temp)/'saved.db'
  with contextlib.closing(sqlite3.connect((data/'schedule.db').resolve().as_uri()+'?mode=ro',uri=True)) as src,contextlib.closing(sqlite3.connect(live)) as dst:src.backup(dst)
  with zipfile.ZipFile(backup) as z:
   if z.testzip() is not None:raise ValueError('Backup ZIP is damaged.')
   manifest=json.loads(z.read('manifest.json'))
   if manifest.get('application')!='thrift-mart-dispatch':raise ValueError('Not a supported dispatch backup.')
   saved.write_bytes(z.read('schedule.db'))
  with contextlib.closing(sqlite3.connect(live)) as a,contextlib.closing(sqlite3.connect(saved)) as b:
   if b.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup database integrity check failed.')
   counts={'Pickup':0,'Delivery':0,'total':0,'photos':0}
   for row in a.execute('SELECT id,revision,body FROM jobs'):
    if b.execute('SELECT id,revision,body FROM jobs WHERE id=?',(row[0],)).fetchone()!=row:raise ValueError('A current appointment is missing or different in the backup. Create a fresh backup while users are not editing.')
    kind=json.loads(row[2]).get('type');counts['total']+=1
    if kind in counts:counts[kind]+=1
   for row in a.execute('SELECT job,position,body FROM photos'):
    if b.execute('SELECT job,position,body FROM photos WHERE job=? AND position=?',row[:2]).fetchone()!=row:raise ValueError('A current photo is missing or different in the backup.')
    counts['photos']+=1
   for row in a.execute('SELECT at,actor,action,job FROM audit'):
    if not b.execute('SELECT 1 FROM audit WHERE at=? AND actor=? AND action=? AND job=?',row).fetchone():raise ValueError('Current audit history is missing from the backup.')
   if a.execute("SELECT 1 FROM sqlite_master WHERE name='journal_archives'").fetchone() and a.execute('SELECT 1 FROM journal_archives').fetchone():
    if not manifest.get('includes_dispatch_journal'):raise ValueError('This backup does not confirm inclusion of Dispatch Journal history.')
   return {'verified':True,'live_entries_matched':counts,'backup_entries':b.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],'backup':str(backup),'note':'Read-back verification succeeded. Separately confirm this file is synced in OneDrive. No live data was changed.'}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,default=Path(__file__).resolve().parent/'data');parser.add_argument('--backup',type=Path,required=True);args=parser.parse_args()
 try:print(json.dumps(verify(args.data,args.backup),indent=2))
 except Exception as e:parser.exit(1,'VERIFICATION FAILED: '+str(e)+'\n')
if __name__=='__main__':main()
