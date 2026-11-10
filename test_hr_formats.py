import unittest
import server
class FormatTests(unittest.TestCase):
 def test_formats(self):
  def f(label,value):return server.hr_format_value(dict(type='text',label=label),value,True)
  self.assertEqual(f('Phone number','12285550123'),'(228) 555-0123')
  self.assertEqual(f('Social Security number','123456789'),'123-45-6789')
  self.assertEqual(f('Date of Birth','1990-03-04'),'03/04/1990')
  self.assertEqual(f('Expiration Date','N/A'),'N/A')
  for label,value in [('Social Security number','***-**-6789'),('Phone number','5550123'),('Date of Birth','02/30/1990')]:
   with self.assertRaises(server.Problem):f(label,value)
if __name__=='__main__':unittest.main()
