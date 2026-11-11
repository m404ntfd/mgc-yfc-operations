"""Filtered giving history uses synthetic records and never exposes a public route."""
import unittest
import uuid
import server
import test_giving_storage as storage


class GiftHistoryTests(unittest.TestCase):
    setUp = storage.GivingStorageTests.setUp
    post = storage.GivingStorageTests.post
    get = storage.GivingStorageTests.get

    def gift(self, **changes):
        data = dict(donor=self.donor, day='2025-12-15', amount=1000,
                    method='check', reference='Synthetic receipt',
                    fund='Ministry', benefit='', benefit_value=0)
        data.update(changes)
        return self.post('gift', **data)['id']

    def history(self, **query):
        return self.get('gift_history', donor=self.donor, **query)

    def test_donor_year_fund_and_totals_span_all_pages(self):
        first = self.gift()
        second = self.gift(amount=2000)
        self.gift(day='2024-12-15', amount=3000)
        self.gift(fund='Youth', amount=4000)
        other = self.post('donor', name='Other', email='', address='', delivery='print')['id']
        self.gift(donor=other, amount=5000)
        page = self.history(year='2025', fund='Ministry', limit='1')
        self.assertEqual((page['total'], page['amount'], page['has_more']), (2, 3000, True))
        next_page = self.history(year='2025', fund='Ministry', limit='1', offset='1')
        self.assertEqual([page['gifts'][0]['id'], next_page['gifts'][0]['id']], sorted([first, second]))
        self.assertFalse(next_page['has_more'])
        self.assertEqual(next_page['amount'], 3000)
        self.assertEqual(self.history()['total'], 4)

    def test_void_and_replacement_count_only_effective_amounts(self):
        original = self.gift()
        saved = self.post('statement_snapshot', donor=self.donor, period='2025')['id']
        replacement = self.post('replace_gift', gift=original, reason='Correct amount',
            donor=self.donor, day='2025-12-15', amount=2500, method='check',
            reference='Corrected receipt', fund='Ministry', benefit='', benefit_value=0)['id']
        active = self.history()
        self.assertEqual((active['total'], active['amount']), (1, 2500))
        self.assertEqual(active['gifts'][0]['replaces'], original)
        all_rows = self.history(include_voided='true')
        self.assertEqual((all_rows['total'], all_rows['amount']), (2, 2500))
        old = next(g for g in all_rows['gifts'] if g['id']==original)
        self.assertTrue(old['voided'])
        self.assertEqual(old['replacement'], replacement)
        self.assertEqual(self.get('statement_snapshot', id=saved)['total'], 1000)

    def test_filters_are_literal_and_empty_pages_keep_totals(self):
        self.gift(fund="Youth's 100%_Fund")
        self.assertEqual(self.history(fund="Youth's 100%_Fund")['total'], 1)
        for value in ('%', '_', "' OR 1=1 --"):
            self.assertEqual(self.history(fund=value)['total'], 0)
        page = self.history(offset='999')
        self.assertEqual((page['gifts'], page['total'], page['amount'], page['has_more']), ([], 1, 1000, False))
        self.assertEqual(self.history(year='2023')['amount'], 0)

    def test_invalid_filters_and_missing_donor(self):
        for query in ({'year':'0000'}, {'year':'25'}, {'year':'202A'},
                      {'limit':'0'}, {'limit':'101'}, {'limit':'1.5'},
                      {'offset':'-1'}, {'include_voided':'yes'}, {'fund':'x'*101}):
            with self.subTest(query=query), self.assertRaises(server.Problem) as error:
                self.history(**query)
            self.assertEqual(error.exception.status, 400)
        with self.assertRaises(server.Problem) as error:
            self.get('gift_history', donor=uuid.uuid4().hex)
        self.assertEqual(error.exception.status, 404)

    def test_staff_permission_and_read_only_behavior(self):
        self.gift()
        before = list(self.c.iterdump())
        self.user = {'name':'Viewer', 'admin':False, 'grants':{'view_giving':True}}
        self.assertEqual(self.history()['total'], 1)
        self.assertEqual(before, list(self.c.iterdump()))
        self.user['grants'] = {}
        for donor in (self.donor, uuid.uuid4().hex):
            with self.assertRaises(server.Problem) as error:
                self.get('gift_history', donor=donor)
            self.assertEqual(error.exception.status, 403)


if __name__ == '__main__':
    unittest.main()
