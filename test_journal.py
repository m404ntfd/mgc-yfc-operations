from contextlib import closing
"""Data preservation tests for verified backup, journal, restore and retention."""
import datetime as dt,json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import server
from remote.restore import restore_backup
from verify_dispatch_backup import verify

class JournalTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.data=self.root/'data';self.data.mkdir();self.folder=self.root/'OneDrive';self.folder.mkdir()
  self.patches=[patch.object(server,'DATA',self.data),patch.object(server,'DB',self.data/'schedule.db')]
  for p in self.patches:p.start()
  server.init();(self.data/'backup-settings.json').write_text(json.dumps({'enabled':True,'folder':str(self.folder)}))
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def job(self,id,kind='Pickup',status='Completed',date='2026-09-01',modified=None):
  body=json.dumps({'type':kind,'status':status,'start':date+'T10:00','end':date+'T11:00','customer':'Preservation test','photoCount':1})
  with server.connect() as c:
   c.execute('INSERT INTO jobs VALUES(?,?,?)',(id,3,body));c.execute('INSERT INTO photos VALUES(?,?,?)',(id,0,b'photo-bytes-'+id.encode()));c.execute('INSERT INTO audit VALUES(?,?,?,?)',((modified or date)+'T12:00','Tester','Updated',id))
 def test_verified_archive_reports_and_standalone_restore(self):
  self.job('old-pickup');self.job('old-delivery','Delivery');self.job('recent',date='2026-10-20');self.job('unfinished',status='Scheduled');self.job('future',date='2026-12-01');self.job('recent-edit',modified='2026-11-01');self.job('boundary',date='2026-10-06')
  self.assertEqual(server.archive_dispatch(dt.date(2026,11,5)),2)
  with server.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],5)
   self.assertEqual(len(server.all_report_jobs(c)),7)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM photos').fetchone()[0],5)
  self.assertEqual(server.archive_dispatch(dt.date(2026,11,5)),0)
  backup=server.complete_backup();status=json.loads((self.data/'backup-status.json').read_text());self.assertTrue(status['verified']);self.assertEqual(status['counts']['total'],7);self.assertEqual(status['counts']['Delivery'],1);self.assertEqual(status['counts']['photos'],7)
  restored=self.root/'restored';restore_backup(backup,restored)
  with closing(sqlite3.connect(restored/'schedule.db')) as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],7);self.assertEqual(c.execute('SELECT COUNT(*) FROM photos').fetchone()[0],7);self.assertEqual(c.execute('SELECT COUNT(*) FROM audit').fetchone()[0],7);self.assertEqual(c.execute('SELECT COUNT(*) FROM journal_archives').fetchone()[0],0)
 def test_host_preflight_detects_missing_and_changed_data(self):
  self.job('pickup');self.job('delivery','Delivery');backup=server.complete_backup()
  self.assertEqual(verify(self.data,backup)['live_entries_matched']['total'],2)
  with server.connect() as c:c.execute("UPDATE photos SET body=? WHERE job='pickup'",(b'changed',))
  with self.assertRaises(ValueError):verify(self.data,backup)
 def test_backup_failure_retains_every_record(self):
  self.job('keep')
  with patch.object(server,'verify_backup_archive',side_effect=OSError('disk error')):
   with self.assertRaises(OSError):server.archive_dispatch(dt.date(2026,11,5))
  with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],1);self.assertEqual(c.execute('SELECT COUNT(*) FROM photos').fetchone()[0],1)
 def test_journal_verification_failure_retains_every_record(self):
  self.job('keep')
  with patch.object(server,'open_journal',side_effect=ValueError('readback mismatch')):
   with self.assertRaises(ValueError):server.archive_dispatch(dt.date(2026,11,5))
  with server.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],1);self.assertEqual(c.execute('SELECT COUNT(*) FROM photos').fetchone()[0],1)
 def test_missing_journal_blocks_partial_backup_and_reports(self):
  self.job('old');server.archive_dispatch(dt.date(2026,11,5));next((self.folder/'Dispatch Journal').glob('*.db')).unlink()
  with self.assertRaises(ValueError):server.complete_backup()
  with server.connect() as c:
   with self.assertRaises(ValueError):server.all_report_jobs(c)
 def test_disabled_backups_do_not_remove_records(self):
  self.job('keep');(self.data/'backup-settings.json').write_text(json.dumps({'enabled':False,'folder':str(self.folder)}));self.assertEqual(server.archive_dispatch(dt.date(2026,11,5)),0)
 def test_legacy_preference_migration_keeps_jobs(self):
  self.job('keep')
  with server.connect() as c:c.execute('DROP TABLE landing_preferences');c.execute('CREATE TABLE landing_preferences(name TEXT PRIMARY KEY,section TEXT)');c.execute("INSERT INTO landing_preferences VALUES('Test','dispatch')")
  server.init()
  with server.connect() as c:self.assertIsNone(c.execute('SELECT chosen_on FROM landing_preferences').fetchone()[0]);self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],1)
if __name__=='__main__':unittest.main()
