import unittest
from fractions import Fraction

# src/dynamic_dt/test___init__.py
from dynamic_dt import (
	is_number, cast_str, to_fraction, round_min, round_frac, parse_num, parse_num_long,
	strnum, time_disp, time_parse, get_name, get_offset, retrieve_tz, get_timezone,
	get_time, month_days, TimeDelta, DynamicDT
)

class TestDynamicDT(unittest.TestCase):

	def test_is_number(self):
		self.assertTrue(is_number("123"))
		self.assertTrue(is_number("-123.45"))
		self.assertFalse(is_number("abc"))

	def test_cast_str(self):
		self.assertEqual(cast_str(b"hello"), "hello")
		self.assertEqual(cast_str(memoryview(b"world")), "world")
		self.assertEqual(cast_str("test"), "test")

	def test_to_fraction(self):
		self.assertEqual(to_fraction(1, 2), Fraction(1, 2))
		self.assertEqual(to_fraction(1.5, 2), Fraction(3, 4))

	def test_round_min(self):
		self.assertEqual(round_min(1.0), 1)
		self.assertEqual(round_min(1.5), 1.5)
		self.assertEqual(round_min(None), None)

	def test_round_frac(self):
		self.assertEqual(round_frac(1.0), 1)
		self.assertEqual(round_frac(1.5), Fraction(3, 2))
		self.assertEqual(round_frac(None), None)

	def test_parse_num(self):
		self.assertEqual(parse_num("123"), 123)
		self.assertEqual(parse_num("123.45"), Fraction(12345, 100))

	def test_parse_num_long(self):
		self.assertEqual(parse_num_long("one hundred twenty three"), 123)

	def test_strnum(self):
		self.assertEqual(strnum(123.456789), "123.456789")
		self.assertEqual(strnum(123.0), "123")

	def test_time_disp(self):
		self.assertEqual(time_disp(3661), "1:01:01")
		self.assertEqual(time_disp(59), "0:59")

	def test_time_parse(self):
		self.assertEqual(time_parse("1:01:01"), 3661)
		self.assertEqual(time_parse("0:59"), 59)

	def test_get_name(self):
		tzinfo = get_timezone("UTC")
		self.assertEqual(get_name(tzinfo), "UTC")

	def test_get_offset(self):
		tzinfo = get_timezone("UTC")
		self.assertEqual(get_offset(tzinfo), 0)

	def test_retrieve_tz(self):
		tzinfo = retrieve_tz("UTC")
		self.assertEqual(get_name(tzinfo), "UTC")

	def test_get_timezone(self):
		tzinfo = get_timezone("UTC")
		self.assertEqual(get_name(tzinfo), "UTC")

	def test_get_time(self):
		dt = get_time("UTC")
		self.assertIsInstance(dt, DynamicDT)

	def test_month_days(self):
		self.assertEqual(month_days(2020, 2), 29)
		self.assertEqual(month_days(2021, 2), 28)

	def test_TimeDelta(self):
		td = TimeDelta(years=1, months=2, days=3)
		self.assertEqual(td.years, 1)
		self.assertEqual(td.months, 2)
		self.assertEqual(td.days, 3)

	def test_DynamicDT(self):
		dt = DynamicDT(2023, 1, 1)
		self.assertEqual(dt.year, 2023)
		self.assertEqual(dt.month, 1)
		self.assertEqual(dt.day, 1)

	def test_DynamicDT_add(self):
		dt = DynamicDT(2023, 1, 1)
		dt += TimeDelta(days=1)
		self.assertEqual(dt.day, 2)

	def test_DynamicDT_sub(self):
		dt1 = DynamicDT(2023, 1, 2)
		dt2 = DynamicDT(2023, 1, 1)
		td = dt1 - dt2
		self.assertEqual(td.days, 1)

	def test_DynamicDT_replace(self):
		dt = DynamicDT(2023, 1, 1)
		dt = dt.replace(year=2024)
		self.assertEqual(dt.year, 2024)

	def test_DynamicDT_parse(self):
		dt = DynamicDT.parse("2023-01-01")
		self.assertEqual(dt.year, 2023)
		self.assertEqual(dt.month, 1)
		self.assertEqual(dt.day, 1)

if __name__ == "__main__":
	unittest.main()