from datetime import datetime,timezone
from support import CrawlTest

class TimeCompatibilityTests(CrawlTest):
    def test_comma_fraction_and_compact_positive_negative_offsets(self):
        moment=self.module('common').moment
        self.assertEqual(moment('2026-09-16T12:00:00,123456+0300'),datetime(2026,9,16,9,0,0,123456,tzinfo=timezone.utc))
        self.assertEqual(moment('2026-09-16T12:00:00,5-0430'),datetime(2026,9,16,16,30,0,500000,tzinfo=timezone.utc))
        self.assertEqual(moment('2026-09-16T12:00:00,000Z'),moment('2026-09-16T12:00:00.000+00:00'))

    def test_missing_timezone_and_malformed_timestamps_still_fail(self):
        moment=self.module('common').moment
        for value in ['2026-09-16T12:00:00,000','2026-09-16','2026-09-16T12:00:00,,000+0300','2026-09-16T12:00:00+9999']:
            with self.subTest(value=value),self.assertRaises(ValueError):moment(value)
