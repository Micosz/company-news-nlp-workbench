import unittest

from datetime import date

from date_audit import audit, cross_check, read_slash, shape, slash_order


def iso_only(value):
    """Stand-in parser: reads YYYY-MM-DD and nothing else."""
    parts = value.split('-')
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return value, value
    return None


class ShapeTest(unittest.TestCase):
    def test_slash_date(self):
        self.assertEqual(shape('07/02/2013'), '99/99/9999')

    def test_words_collapse(self):
        self.assertEqual(shape('AFTER 4 January 2009'), 'A 9 A 9999')
        self.assertEqual(shape('NA'), shape('UNKNOWN'))

    def test_strips_spaces(self):
        self.assertEqual(shape('  2013 '), '9999')


class AuditTest(unittest.TestCase):
    def test_counts_add_up(self):
        values = ['2013-09-13', '', '  ', '07/02/2013', '11/10/2011', '07/02/2013', 'NA', 2013]
        result = audit(values, iso_only)
        self.assertEqual(result['total'], 8)
        self.assertEqual((result['empty'], result['read'], result['unread']), (2, 1, 5))

    def test_shapes_keep_most_common_example(self):
        values = ['07/02/2013', '11/10/2011', '07/02/2013', 'NA']
        shapes = audit(values, iso_only)['shapes']
        self.assertEqual(shapes[0], ('99/99/9999', 3, '07/02/2013'))
        self.assertEqual(shapes[1], ('A', 1, 'NA'))

    def test_everything_read(self):
        result = audit(['2013-09-13', '2008-12-12'], iso_only)
        self.assertEqual((result['unread'], result['shapes']), (0, []))


class SlashOrderTest(unittest.TestCase):
    def test_each_case(self):
        values = ['12/18/2008', '18/12/2008', '02/01/2008', '31/31/2008', '00/05/2008']
        self.assertEqual(slash_order(values),
                         {'month_first': 1, 'day_first': 1, 'either': 1, 'invalid': 2})

    def test_ignores_other_formats(self):
        values = ['2008-12-18', '13 September 2013', 'XX/XX/1974', '12/13', '']
        self.assertEqual(sum(slash_order(values).values()), 0)

    def test_single_digits(self):
        self.assertEqual(slash_order(['7/22/2008'])['month_first'], 1)


def iso_day(value):
    try:
        d = date.fromisoformat(value.strip())
    except ValueError:
        return None
    return d, d


class CrossCheckTest(unittest.TestCase):
    def test_read_slash_both_ways(self):
        self.assertEqual(read_slash('02/01/2008', True), date(2008, 2, 1))
        self.assertEqual(read_slash('02/01/2008', False), date(2008, 1, 2))
        self.assertIsNone(read_slash('12/18/2008', False))
        self.assertIsNone(read_slash('2008-12-18', True))

    def test_counts_each_outcome(self):
        slash = {'m1': '12/18/2008', 'm2': '02/01/2008', 'm3': '02/01/2008',
                 'm4': '05/05/2008', 'm5': '03/04/2008', 'm6': '03/04/2008', 'm7': 'NA'}
        reference = {'m1': '2008-12-18', 'm2': '2008-02-01', 'm3': '2008-01-02',
                     'm4': '2008-05-05', 'm5': '2009-01-01', 'm6': 'NA'}
        self.assertEqual(cross_check(slash, reference, iso_day), {
            'month_first_only': 2, 'day_first_only': 1, 'same_either_way': 1,
            'neither': 1, 'no_day_reference': 1})


if __name__ == '__main__':
    unittest.main()
