import datetime as dt
import unittest
import server

class SessionExpiryTests(unittest.TestCase):
 def test_midnight_and_activity(self):
  now=dt.datetime(2026,11,6,0,1).timestamp()
  session={'expires':now+3600,'login_day':'2026-11-05','last_active':now-301}
  self.assertTrue(server.session_expired(session,now))
  session['last_active']=now-60
  self.assertFalse(server.session_expired(session,now))
  self.assertTrue(server.session_expired(session,now+240))
 def test_hard_limit_and_same_day(self):
  now=dt.datetime(2026,11,5,12).timestamp()
  session={'expires':now+1,'login_day':'2026-11-05','last_active':now-3600}
  self.assertFalse(server.session_expired(session,now))
  session['last_active']=now+1
  self.assertTrue(server.session_expired(session,now+1))

if __name__=='__main__':unittest.main()
