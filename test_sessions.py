"""Lease boundaries, activity grace, and expired-token removal."""
import datetime as dt
import unittest
from unittest.mock import patch
import server

class SessionTests(unittest.TestCase):
 def setUp(self):
  self.start=dt.datetime(2026,11,5,23,58).timestamp()
  self.session=server.new_session('Employee',False,self.start)
 def test_idle_midnight_and_no_revival(self):
  s=server.new_session('Employee',False,self.start-600)
  self.assertTrue(server.session_valid(s,s['midnight']-1))
  self.assertFalse(server.session_valid(s,s['midnight']))
  handler=object.__new__(server.Handler);handler.headers={'Cookie':'session=expired-test'}
  server.SESSIONS['expired-test']=s
  with patch('server.time.time',return_value=s['midnight']):
   with self.assertRaises(server.Problem):handler.user()
  self.assertNotIn('expired-test',server.SESSIONS)
 def test_active_midnight_then_idle(self):
  s=self.session
  self.assertTrue(server.session_valid(s,s['midnight']))
  self.assertFalse(server.session_valid(s,self.start+300))
  s['last_activity']=self.start+240
  self.assertTrue(server.session_valid(s,self.start+400))
  self.assertFalse(server.session_valid(s,self.start+540))
 def test_hard_24_hour_cap(self):
  s=self.session;s['last_activity']=s['expires']-1
  self.assertTrue(server.session_valid(s,s['expires']-1))
  self.assertFalse(server.session_valid(s,s['expires']))
 def test_midnight_uses_server_calendar(self):
  self.assertEqual(dt.datetime.fromtimestamp(self.session['midnight']),dt.datetime(2026,11,6))

if __name__=='__main__':unittest.main()
