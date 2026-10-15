from decimal import Decimal
from support import IntegrityTest

class NumberTests(IntegrityTest):
    def parse(self,value,**kw):return self.module('numbers').parse_quantity(value,**kw)
    def test_very_small_price_not_zero(self):
        r=self.parse('0.000000000000000123');self.assertEqual(Decimal(r['value']),Decimal('0.000000000000000123'));self.assertEqual(r['status'],'observed')
    def test_binary_float_input_not_silently_rounded(self):self.assertEqual(self.parse(0.1)['status'],'invalid')
    def test_large_precise_integer_preserved(self):self.assertEqual(self.parse('99985622230')['value'],'99985622230')
    def test_more_than_default_decimal_precision_preserved(self):self.assertEqual(self.parse('123456789012345678901234567890.12')['value'],'123456789012345678901234567890.12')
    def test_billion_abbreviation_preserves_display_step(self):
        r=self.parse('62.8B');self.assertEqual(Decimal(r['value']),Decimal('62800000000'));self.assertEqual(Decimal(r['quantum']),Decimal('100000000'))
    def test_million_integer_display_not_exact_unit_count(self):self.assertEqual(Decimal(self.parse('20M')['quantum']),Decimal('1000000'))
    def test_zero_is_observed_not_missing(self):self.assertEqual(self.parse('0.00')['status'],'observed');self.assertEqual(self.parse('0.00')['value'],'0.00')
    def test_missing_sentinel_not_zero(self):
        for value in [None,'','--','N/A','null']:self.assertEqual(self.parse(value)['status'],'missing');self.assertIsNone(self.parse(value)['value'])
    def test_nonfinite_not_number(self):
        for value in ['NaN','Infinity','-Infinity',True]:self.assertEqual(self.parse(value)['status'],'invalid')
    def test_english_grouping(self):self.assertEqual(self.parse('1,234.50')['value'],'1234.50')
    def test_bad_grouping_rejected(self):self.assertEqual(self.parse('12,34')['status'],'invalid')
    def test_french_explicit_separators(self):self.assertEqual(self.parse('1\u202f234,50',decimal_mark=',',group_mark='\u202f')['value'],'1234.50')
    def test_german_explicit_separators(self):self.assertEqual(self.parse('1.234,50',decimal_mark=',',group_mark='.')['value'],'1234.50')
    def test_same_separator_configuration_rejected(self):
        with self.assertRaises(ValueError):self.parse('1,23',decimal_mark=',',group_mark=',')
    def test_scientific_notation(self):
        r=self.parse('1.23e-8');self.assertEqual(Decimal(r['value']),Decimal('0.0000000123'));self.assertEqual(Decimal(r['quantum']),Decimal('0.0000000001'))
    def test_exact_api_value_has_no_display_rounding_interval(self):self.assertEqual(self.parse('123.4500',exact=True)['quantum'],'0')
    def test_currency_is_not_implicitly_stripped(self):self.assertEqual(self.parse('$1.20')['status'],'invalid')
    def test_unsupported_compact_zero_notation_not_guessed(self):self.assertEqual(self.parse('0.0₇123')['status'],'invalid')
    def test_huge_exponent_bounded(self):self.assertEqual(self.parse('1e99999999')['status'],'invalid')
    def test_negative_change_retained(self):self.assertEqual(self.parse('-4.52')['value'],'-4.52')
