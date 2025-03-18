import datetime
import fractions
import functools
import math
import os
import re
import time
import dateutil
import pytz

number = int | float
YEAR = 31556952
ERA_YEARS = 400
ERA = YEAR * ERA_YEARS
num_re = re.compile(r"[+-]?([0-9]*\.)?[0-9]+")
ts_re = re.compile(r"<t:[+-]?[0-9]+[^0-9]")


def is_number(s):
	"More powerful version of s.isnumeric() that accepts negatives and floats."
	return num_re.fullmatch(s.removesuffix("."))

def cast_str(s) -> str:
	if isinstance(s, memoryview):
		s = bytes(s)
	if isinstance(s, bytes):
		s = s.decode("utf-8", "replace")
	return str(s)

def to_fraction(x, y):
	"Converts two numbers to a fraction. Required as fractions.Fraction does not accept floats in the divisor."
	if isinstance(x, int) and isinstance(y, int):
		return fractions.Fraction(x, y)
	if not isinstance(x, fractions.Fraction):
		x = fractions.Fraction(x)
	if not isinstance(y, (int, fractions.Fraction)):
		y = fractions.Fraction(y)
	return x / y

def round_min(x) -> number:
	"Casts a number to integer if the conversion would not alter the value."
	if x is None:
		return x
	if math.isfinite(x):
		if x.is_integer():
			return int(x)
		y = int(x)
		if x == y:
			return y
	return x

def round_frac(x) -> number:
	"Casts a number to fraction or integer."
	if x is None:
		return x
	if math.isfinite(x):
		if isinstance(x, float):
			x = fractions.Fraction(round(x * 10 ** 10), 10 ** 10)
		if x.is_integer():
			return int(x)
		y = int(x)
		if x == y:
			return y
	return x

def parse_num(s):
	"Parses a number, may be negative or a non-integer."
	integer = s.split(".", 1)[0]
	if len(integer) > 16:
		return int(integer)
	else:
		return round_min(fractions.Fraction(s))

def parse_num_long(s):
	"Parses natural language as numbers."
	if num_re.fullmatch(s):
		return parse_num(s)
	import number_parser
	s2 = number_parser.parse(s)
	tokens = [w for w in s2.split() if w != "a"]
	return int("".join(tokens))

def strnum(num):
	return str(round_min(round(num, 6)))

def time_disp(s, rounded=True):
	"Returns a representation of a time interval using days:hours:minutes:seconds."
	if not math.isfinite(s):
		return str(s)
	if rounded:
		s = round(s)
	output = strnum(s % 60)
	if len(output) < 2:
		output = "0" + output
	if s >= 60:
		temp = strnum((s // 60) % 60)
		if len(temp) < 2 and s >= 3600:
			temp = "0" + temp
		output = temp + ":" + output
		if s >= 3600:
			temp = strnum((s // 3600) % 24)
			if len(temp) < 2 and s >= 86400:
				temp = "0" + temp
			output = temp + ":" + output
			if s >= 86400:
				output = strnum(s // 86400) + ":" + output
	else:
		output = "0:" + output
	return output

def time_parse(ts, default="s"):
	"Converts a time interval represented using days:hours:minutes:seconds, to a value in seconds."
	if ts == "N/A":
		return math.inf
	data = ts.split(":")
	if len(data) >= 5: 
		raise TypeError("Too many time arguments.")
	if len(data) >= 4:
		mults = (1, 60, 3600, 86400)
	elif len(data) == 3:
		mults = (1, 60, 3600) if default != "d" else (60, 3600, 86400)
	elif len(data) == 2:
		mults = (1, 60) if default == "s" else (60, 3600) if default in "mh" else (3600, 86400)
	elif len(data) == 1:
		mults = (1,) if default == "s" else (60,) if default == "m" else (3600,) if default == "h" else (86400,)
	return round_min(sum(float(count) * mult for count, mult in zip(data, reversed(mults[:len(data)]))))

TIMEZONES = {}
# Update timezone abbreviations list using pytz
for tz in pytz.all_timezones:
	tzinfo = pytz.timezone(tz)
	TIMEZONES[tz.casefold()] = tzinfo
	if "/" in tz and not tz.startswith("Etc/"):
		TIMEZONES[tz.rsplit("/", 1)[-1].casefold()] = tzinfo
	if hasattr(tzinfo, "_tzinfos"):
		temp = {}
		for k, v in tzinfo._tzinfos.items():
			if isinstance(k, tuple):
				assert len(k) == 3, k
				base, offset, name = k
				if name != "LMT" and re.search(r"[A-Za-z]", name):
					tzinfo2 = pytz._FixedOffset(round(base.total_seconds() / 60))
					tzinfo2.canonical_name = name
					temp[name.casefold()] = tzinfo2
		for tz in temp:
			if "st" in tz and tz.replace("st", "dt") in temp:
				TIMEZONES[tz.replace("st", "t")] = tzinfo
		TIMEZONES.update(temp)
# Parse timezone abbreviations list from Wikipedia
# Source: https://en.wikipedia.org/wiki/List_of_time_zone_abbreviations
self_dir = os.path.dirname(os.path.abspath(__file__))
rel_path = "wikipedia_data.txt"
abs_file_path = os.path.join(self_dir, rel_path)
with open(abs_file_path, "r", encoding="utf-8") as f:
	timezone_abbreviations_table = f.read()
for line in timezone_abbreviations_table.splitlines():
	info = line.split("\t")
	name = info[0].split("(", 1)[0].strip()
	abb = name.casefold()
	if len(abb) >= 3 and abb not in TIMEZONES:
		temp = info[-1].replace("\\", "/")
		curr = sorted([round((1 - (i[3] == "−") * 2) * (time_parse(i[4:]) if ":" in i else float(i[4:]) * 60)) for i in temp.split("/") if i.startswith("UTC")])
		if len(curr) == 1:
			curr = curr[0]
		tzinfo = pytz._FixedOffset(curr)
		tzinfo.canonical_name = name
		TIMEZONES[abb] = tzinfo

def get_name(tzinfo):
	"Gets the canonical name of a timezone where possible, returning UTC±X when ambiguous."
	if tzinfo == datetime.timezone.utc:
		return "UTC"
	if isinstance(tzinfo, (pytz._FixedOffset, dateutil.tz.tzoffset)):
		try:
			return tzinfo.canonical_name
		except AttributeError:
			offset = round(tzinfo._offset.total_seconds() / 60)
			negative, offset = offset < 0, abs(offset)
			hours = offset / 60
			if hours.is_integer():
				hourdisp = str(int(hours))
			else:
				hours = math.trunc(hours)
				hourdisp = f"{hours}:{round(offset - hours * 60)}"
			return "UTC" + "+-"[negative] + hourdisp
	return tzinfo.__class__.__name__

def get_offset(tzinfo, dt=None):
	"Gets the total offset of a timezone from UTC, in seconds."
	if tzinfo == datetime.timezone.utc:
		return 0
	if isinstance(tzinfo, pytz._FixedOffset):
		return tzinfo._minutes * 60
	if dt:
		return tzinfo.utcoffset(dt).total_seconds()
	return datetime.datetime.now(tz=tzinfo).utcoffset().total_seconds()

def retrieve_tz(tz):
	"Gets a timezone from a string, retrying with the last part of the string if the first attempt fails."
	tz = tz.casefold()
	try:
		return TIMEZONES[tz]
	except KeyError:
		if "/" in tz:
			try:
				return TIMEZONES[tz.rsplit("/", 1)[-1]]
			except KeyError:
				pass

def get_timezone(tz) -> pytz.BaseTzInfo:
	"Gets a timezone from a string, accepting ± syntax to indicate hours/minutes offsets."
	if isinstance(tz, number):
		tzinfo = pytz._FixedOffset(tz * 60)
		return tzinfo
	otz, tz = tz, retrieve_tz(tz)
	if tz:
		return tz
	a = otz
	m = 0
	for op in ("+-"):
		try:
			i = a.index(op)
			v = time_parse(a[i:], default="h")
			m += v
		except ValueError:
			continue
		else:
			a = a[:i]
			break
	tz = a.casefold()
	tz = retrieve_tz(tz)
	if not tz:
		return
	offset = (get_offset(tz) + m) / 60
	tzinfo = pytz._FixedOffset(round(offset))
	negative, offset = offset < 0, abs(offset)
	hours = offset / 60
	if hours.is_integer():
		hourdisp = str(int(hours))
	else:
		hours = math.trunc(hours)
		hourdisp = f"{hours}:{round(offset - hours * 60)}"
	tzinfo.canonical_name = get_name(tz) + "+-"[negative] + hourdisp
	return tzinfo

def get_time(tz="utc"):
	"Gets the current time at a timezone specified by string."
	return DynamicDT.now(tz=get_timezone(tz))

def month_days(year, month) -> int:
	"Gets the amount of days in a particular Gregorian calendar month."
	if month in (4, 6, 9, 11):
		return 30
	elif month == 2:
		if not year % 400:
			return 29
		elif not year % 100:
			return 28
		elif not year % 4:
			return 29
		return 28
	return 31

def display_to_precision(frac, precision=20):
	"Converts a fraction to a string with a specified precision."
	if not frac:
		return "0"
	if isinstance(frac, int):
		return str(frac)
	if isinstance(frac, float):
		return str(round(frac, precision)).removesuffix(".0")
	if precision <= 0:
		return str(round(frac))
	import decimal
	with decimal.localcontext() as ctx:
		ctx.prec = precision
		d = decimal.Decimal(frac.numerator) / decimal.Decimal(frac.denominator)
		return format(d, f".{precision}f").rstrip("0").removesuffix(".")


UNIT_GALACTIC_YEAR = 226814000
UNIT_YEAR = 31556925
UNIT_MONTH = fractions.Fraction(46751, 1536)

@functools.total_ordering
class TimeDelta:
	"Custom timedelta class that can store both exact representations of years and months, as well as timestamp deltas in seconds. Where ambiguous, a galactic year is treated as exactly 226814000 years, a year is treated as exactly 31556925 seconds, and a month is treated as 46751/1536 (30.436848958[3]) days."

	__slots__ = ("years", "months", "days", "hours", "minutes", "seconds", "fraction", "_total_seconds")

	def __init__(self, years=0, months=0, days=0, hours=0, minutes=0, seconds=0, fraction=0, total_seconds=None, **kwargs):
		self.years = round_frac(years)
		self.months = round_frac(months)
		self.days = round_frac(days)
		self.hours = round_frac(hours)
		self.minutes = round_frac(minutes)
		self.seconds = round_frac(seconds)
		self.fraction = round_frac(fraction)
		self._total_seconds = round_frac(total_seconds) if total_seconds else None

	def __repr__(self):
		return self.__class__.__name__ + repr(tuple(getattr(self, k) for k in self.__slots__))

	def __str__(self):
		return self.to_string()

	def to_string(self, precision=9):
		self.normalise()
		neg_years = self.years < 0
		gy, y = divmod(abs(self.years), UNIT_GALACTIC_YEAR)
		my, y = divmod(y, 1000000)
		ky, y = divmod(y, 1000)
		if neg_years:
			gy, my, ky, y = -gy, -my, -ky, -y
		data = {
			"galactic year": gy,
		}
		data.update(dict(
			megaannum=my,
			millennium=ky,
			year=y,
			month=self.months,
			day=self.days,
			hour=self.hours,
			minute=self.minutes,
			second=round_min(self.seconds + self.fraction),
		))
		plural = dict(
			megaannum="megaanna",
			millennium="millennia",
		)
		out = []
		for k, v in data.items():
			if not v:
				continue
			if v != 1 and v != -1:
				if k in plural:
					k = plural[k]
				else:
					k += "s"
			out.append(f"{display_to_precision(v, precision)} {k}")
		if not out:
			out.append("0 seconds")
		return " ".join(map(str, out))

	def to_dict(self):
		return {k: getattr(self, k) for k in self.__slots__ if not k.startswith("_")}

	def negate(self):
		for k in self.__slots__:
			v = getattr(self, k)
			if v is not None:
				setattr(self, k, -v)
		return self
	__neg__ = negate

	def is_negative(self):
		return self.total_seconds() < 0

	def total_seconds(self):
		x = getattr(self, "_total_seconds", None)
		if x is not None:
			return x
		x = self.years * UNIT_YEAR + (((self.months * UNIT_MONTH + self.days) * 24 + self.hours) * 60 + self.minutes) * 60 + self.seconds
		if abs(x) < 1 << 52:
			x = round_min(x + float(self.fraction))
		self._total_seconds = x
		return x

	def __int__(self):
		return int(self.total_seconds())

	def __float__(self):
		return float(self.total_seconds())

	def __bool__(self):
		return bool(self.total_seconds())

	def __add__(self, other):
		if isinstance(other, self.__class__):
			for k in self.__slots__:
				setattr(self, k, getattr(self, k) + getattr(other, k))
			return self.normalise()
		if isinstance(other, datetime.timedelta):
			self.days += other.days
			self.seconds += other.seconds
			self.fraction += to_fraction(other.microseconds, 1e6)
			self._total_seconds = None
			return self
		return NotImplemented

	def __sub__(self, other):
		if isinstance(other, self.__class__):
			for k in self.__slots__:
				setattr(self, k, getattr(self, k) - getattr(other, k))
			return self.normalise()
		if isinstance(other, datetime.timedelta):
			self.days -= other.days
			self.seconds -= other.seconds
			self.fraction -= to_fraction(other.microseconds, 1e6)
			self._total_seconds = None
			return self
		return NotImplemented

	def normalise(self):
		"""
		Normalize the date and time components of the object.

		This method adjusts the years, months, days, hours, minutes, seconds, and fraction
		attributes of the object to ensure they are within their conventional ranges.
		For example, if the number of months exceeds 12, it will be converted into years
		and months. Similarly, if the number of days exceeds the number of days in a month,
		it will be converted into months and days, and so on.

		If the object represents a negative duration, it will be temporarily negated for
		normalization and then negated again to restore its original sign.

		Returns:
			self: The normalized object.
		"""
		negative = self.is_negative()
		if negative:
			self.negate()
		years, years_partial = divmod(self.years, 1)
		months, months_partial = divmod(self.months + years_partial * 12, 1)
		days, days_partial = divmod(self.days + months_partial * UNIT_MONTH, 1)
		hours, hours_partial = divmod(self.hours + days_partial * 24, 1)
		minutes, minutes_partial = divmod(self.minutes + hours_partial * 60, 1)
		seconds, seconds_partial = divmod(self.seconds + minutes_partial * 60, 1)
		fraction = self.fraction + fractions.Fraction(seconds_partial)
		if not 0 <= fraction < 1:
			ext, fraction = divmod(fraction, 1)
			seconds += ext
		if seconds not in range(0, 60):
			ext, seconds = divmod(seconds, 60)
			minutes += ext
		if minutes not in range(0, 60):
			ext, minutes = divmod(minutes, 60)
			hours += ext
		if hours not in range(0, 24):
			ext, hours = divmod(hours, 24)
			days += ext
		if months not in range(0, 12):
			ext, months = divmod(months, 12)
			years += ext
		modified = years != self.years or months != self.months or days != self.days or hours != self.hours or minutes != self.minutes or seconds != self.seconds or fraction != self.fraction
		if modified:
			self.__init__(years=years, months=months, days=days, hours=hours, minutes=minutes, seconds=seconds, fraction=fraction)
		if negative:
			self.negate()
		return self
	normalize = normalise

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False
		return self.total_seconds() == (other.total_seconds() if hasattr(other, "total_seconds") else other)

	def __lt__(self, other):
		return self.total_seconds() < (other.total_seconds() if hasattr(other, "total_seconds") else other)


class TemporaryDT:
	"""A temporary datetime object that does not perform its own logic, but can be used to set attributes and deltas before creating a DynamicDT object. Used to intercept dateutil's parser output to apply necessary adjustments."""

	def __init__(self):
		self.year = 0
		self.month = 1
		self.day = 1
		self.hour = 0
		self.minute = 0
		self.second = 0
		self.microsecond = 0
		self.set = set()
		self.deltas = []

	def replace(self, **kwargs):
		self.__dict__.update(kwargs)
		self.set.update(kwargs)
		return self

	def negate(self):
		for k in self.set:
			setattr(self, k, -getattr(self, k))

	def __add__(self, other):
		self.deltas.append(other)
		return self


class DynamicDT(datetime.datetime):
	"""
	A flexible datetime class that extends the functionality of Python's built-in datetime.
	The DynamicDT class provides extended datetime functionality including:
	- Support for dates beyond the standard datetime range
	- Fractional seconds with arbitrary precision
	- BCE/CE date handling
	- Natural language parsing
	- Multiple string representation formats
	- Discord timestamp compatibility
	- Enhanced timezone support
	Attributes:
		parsed_as (list): Records the parsing methods used to create the datetime object
		_dt (datetime): Internal datetime object
		_offset (int): Year offset from standard datetime range
		_ts (Fraction): Cached timestamp value
		_fraction (Fraction): Fractional part of second
		tzinfo (datetime.tzinfo): Timezone information
	Class Methods:
		utcfromtimestamp(ts): Create a UTC datetime from a timestamp
		fromtimestamp(ts, tz=None): Create a datetime from a timestamp in given timezone
		to_utc(self): Convert datetime to UTC
		fromdatetime(dt, tz=None): Create from standard datetime object
		utcnow(): Get current UTC datetime
		now(tz=None): Get current datetime in given timezone
		unix(): Get current Unix timestamp
		parse_delta(s, return_remainder=False): Parse a time duration string
		parse(s="", timestamp=None, timezone=None): Parse datetime from string
	Instance Methods:
		timestamp(): Get Unix timestamp as int or float
		timestamp_exact(): Get exact Unix timestamp as Fraction
		copy(): Create a deep copy
		add_years(years=1): Add specified number of years
		add_months(months=1): Add specified number of months
		add(**kwargs): Add specified time units
		replace(**kwargs): Replace datetime components
		cast(tz=UTC): Convert to different timezone
		as_year(): Format year string
		as_date(): Format date string
		as_time(): Format time string
		as_full(): Format full natural language string
		as_iso(): Format ISO-8601 string
		as_discord(): Format Discord absolute timestamp
		as_rel_discord(): Format Discord relative timestamp
	Properties:
		fraction: Get fractional part of second
		offset: Get year offset
		year: Get full year including offset
	Magic Methods:
		__add__, __radd__: Add time delta or number
		__sub__: Subtract time delta, datetime or number
		__eq__, __lt__, __le__, __gt__, __ge__: Compare datetimes
		__str__: Convert to string using as_time()
		__repr__: Detailed string representation
		>>> dt = DynamicDT.parse("2024-01-01 12:00:00")
		>>> dt.as_full()
		'Monday 1 January 2024 at 12:00'
		>>> dt = DynamicDT.parse("1000 BCE")
		>>> dt.as_date()
		'1000-01-01 BCE'
		>>> dt = DynamicDT.parse("next monday at 3pm")
		>>> dt.as_discord()
		'<t:1234567890:F>'
	"""

	__slots__ = ("__weakref__", "_dt", "_offset", "_ts", "_fraction", "parsed_as")

	def __getstate__(self):
		return "0.0.1", ((f := self.timestamp_exact()).numerator, f.denominator), get_name(self.tzinfo)

	def __setstate__(self, s):
		if len(s) == 3:
			v, tsf, tzinfo = s
			assert v == "0.0.1"
			try:
				frac = fractions.Fraction(*tsf)
			except Exception:
				raise TypeError(tsf)
			ts, f = divmod(frac, 1)
			offs, ots = divmod(ts, ERA)
			self._dt = datetime.datetime.fromtimestamp(ots, tz=get_timezone(tzinfo))
			self.set_fraction(f)
			self.set_offset(offs * ERA_YEARS)
			return
		if len(s) == 2:
			frac, tzinfo = s
			ts, f = divmod(frac, 1)
			offs, ots = divmod(ts, ERA)
			if tzinfo and isinstance(tzinfo, str):
				self._dt = datetime.datetime.fromtimestamp(ots, tz=get_timezone(tzinfo))
			elif tzinfo:
				self._dt = datetime.datetime.fromtimestamp(ots, tz=tzinfo)
			else:
				self._dt = None
			self.set_fraction(f)
			self.set_offset(offs * ERA_YEARS)
			return
		raise TypeError("Unpickling failed:", s)

	def copy(self):
		return self.__class__.fromdatetime(self._dt).set_offset(self.offset)

	def __init__(self, *args, **kwargs):
		self.parsed_as = None
		tzinfo = kwargs.pop("tzinfo", None)
		f = kwargs.pop("fraction", None)
		if type(args[0]) is bytes:
			self._dt = datetime.datetime(args[0], tzinfo=tzinfo)
			return
		offs, y = divmod(args[0], ERA_YEARS)
		y += 2000
		offs *= ERA_YEARS
		offs -= 2000
		self._dt = datetime.datetime(y, *args[1:], tzinfo=tzinfo, **kwargs)
		us = self._dt.microsecond
		if us:
			usf = to_fraction(us, 1e6)
			f = (f + usf) if f else usf
		self.set_fraction(f)
		self.set_offset(offs)

	def __new__(cls, *args, **kwargs):
		self = super().__new__(cls, 1, 1, 1)
		self.__init__(*args, **kwargs)
		return self

	def __getattr__(self, k):
		try:
			return self.__getattribute__(k)
		except AttributeError:
			pass
		return getattr(self._dt, k)

	def __str__(self):
		return self.as_time()

	def __repr__(self):
		return self.__class__.__name__ + f"({self.year}, " + ", ".join(str(i) for i in self._dt.timetuple()[1:6]) + (f", fraction={repr(f)}" if (f := self.fraction) else "") + (", tzinfo=get_timezone(" + repr(get_name(self.tzinfo)) + ")" if self.tzinfo else "") + ")"

	def timestamp(self) -> number:
		"Returns the full unix timestamp as an int or float."
		tsf = self.timestamp_exact()
		if tsf.is_integer() or abs(tsf) > 1 << 52:
			return int(tsf)
		else:
			return float(tsf)

	def _timestamp_exact(self):
		offs = self.offset * YEAR
		ts = self._dt.timestamp()
		ts2 = (offs + round_min(ts))
		f = self._fraction
		if ts2.is_integer() and not f:
			return int(ts2)
		return fractions.Fraction(ts2 + (f or 0))

	def timestamp_exact(self) -> fractions.Fraction:
		"Returns the full unix timestamp as an exact fraction."
		try:
			assert self._ts
			return self._ts
		except (AttributeError, AssertionError):
			self._ts = self._timestamp_exact()
		return self._ts

	def timestamp_string(self, precision=9) -> str:
		"Returns the full unix timestamp as a string."
		return display_to_precision(self.timestamp_exact(), precision)

	@property
	def fraction(self) -> fractions.Fraction | int:
		return self._fraction or 0

	def set_fraction(self, frac):
		self._fraction = fractions.Fraction(frac).limit_denominator(1 << 192) if frac else 0

	@property
	def offset(self) -> number:
		try:
			return self._offset
		except AttributeError:
			pass
		self._offset = 0
		return 0

	def set_offset(self, offs):
		self._offset = round(offs)
		self._ts = None
		return self

	def __add__(self, other):
		if not other:
			return self
		if isinstance(other, TimeDelta):
			return self.copy().add(**other.to_dict())
		if isinstance(other, dateutil.relativedelta.relativedelta):
			return self.__class__.fromdatetime(self._dt + other).set_offset(self.offset)
		if not isinstance(other, datetime.timedelta):
			return self.__class__.fromtimestamp(self.timestamp_exact() + fractions.Fraction(other), tz=self.tzinfo)
		ts = self._dt.timestamp() + other.timestamp()
		if abs(self.offset) >= 25600:
			ts = round(ts)
		return self.__class__.fromtimestamp(ts + self.offset * YEAR, tz=self.tzinfo)
	__radd__ = __add__

	def __sub__(self, other):
		if not other:
			return self
		if isinstance(other, TimeDelta):
			return self.copy().add(**other.negate().to_dict())
		if isinstance(other, dateutil.relativedelta.relativedelta):
			return self.__class__.fromdatetime(self._dt + other).set_offset(self.offset)
		if hasattr(other, "total_seconds"):
			other = other.total_seconds()
		if isinstance(other, number):
			return self.fromtimestamp(self.timestamp_exact() - fractions.Fraction(other), tz=self.tzinfo)
		t1, t2 = other, self.cast(tz=other.tzinfo)
		if t2 < t1:
			t1, t2 = t2, t1
			negative = True
		else:
			negative = False
		years = t2.year - t1.year
		months = t2.month - t1.month
		days = t2.day - t1.day
		hours = getattr(t2, "hour", 0) - getattr(t1, "hour", 0)
		minutes = getattr(t2, "minute", 0) - getattr(t1, "minute", 0)
		seconds = getattr(t2, "second", 0) - getattr(t1, "second", 0)
		fraction = getattr(t2, "fraction", 0) - (getattr(t1, "fraction", None) or to_fraction(getattr(t1, "microsecond", 0), 1e6))
		if not 0 <= fraction < 1:
			ext, fraction = divmod(fraction, 1)
			seconds += ext
		if seconds not in range(0, 60):
			seconds, partial = divmod(seconds, 1)
			fraction += fractions.Fraction(partial)
			partial, seconds = divmod(seconds, 60)
			minutes += partial
		if minutes not in range(0, 60):
			minutes, partial = divmod(minutes, 1)
			fraction += fractions.Fraction(partial)
			partial, minutes = divmod(minutes, 60)
			hours += partial
		if hours not in range(0, 24):
			hours, partial = divmod(hours, 1)
			fraction += fractions.Fraction(partial)
			partial, hours = divmod(hours, 24)
			days += partial
		md = month_days(t2.year, t2.month - 1)
		if days not in range(0, md):
			days, partial = divmod(days, 1)
			fraction += fractions.Fraction(partial)
			partial, days = divmod(days, md)
			months += partial
		if months not in range(0, 12):
			months, partial = divmod(months, 1)
			fraction += fractions.Fraction(partial)
			partial, months = divmod(months, 12)
			years += partial
		td = TimeDelta(years=years, months=months, days=days, hours=hours, minutes=minutes, seconds=seconds, fraction=fraction, total_seconds=t2.timestamp() - t1.timestamp())
		if negative:
			td.negate()
		return td

	def __rsub__(self, other):
		return self.fromdatetime(other) - self

	def __eq__(self, other):
		if not isinstance(other, self.__class__):
			return False
		return self.year == other.year and self.timestamp() == other.timestamp()

	def __lt__(self, other):
		return self.year < other.year or self.timestamp() < other.timestamp()
	
	def __le__(self, other):
		return self.year < other.year or self.timestamp() <= other.timestamp()

	def __gt__(self, other):
		return self.year > other.year or self.timestamp() > other.timestamp()
	
	def __ge__(self, other):
		return self.year > other.year or self.timestamp() >= other.timestamp()

	def add_years(self, years=1):
		return self.replace(year=self.year + years)

	def add_months(self, months=1):
		if not months:
			return self
		month = self.month + months
		if month not in range(1, 13):
			years, month = divmod(month - 1, 12)
			return self.replace(year=self.year + years, month=month + 1)
		return self.replace(month=month)

	def add(self, years=0, months=0, days=0, hours=0, minutes=0, seconds=0, fraction=0):
		total_seconds = (((days * 24) + hours) * 60 + minutes) * 60 + seconds
		secs, f = divmod(total_seconds, 1)
		f += self.fraction + fraction
		ext, f = divmod(f, 1)
		self = self.add_months(years * 12 + months)
		self += secs + ext
		self.set_fraction(f)
		return self

	def replace(self, time=None, fraction=None, **kwargs):
		"""
		Replace specified components of the datetime object.

		Parameters:
		time (int, optional): Time in seconds since midnight to replace the time part of the datetime.
		fraction (fractions.Fraction, optional): Fractional part of the second to replace.
		**kwargs: Arbitrary keyword arguments corresponding to datetime components (e.g., year, month, day, hour, minute, second, microsecond, tzinfo).

		Returns:
		self: Updated instance of the datetime object with replaced components.

		Raises:
		ValueError: If any of the provided datetime components are out of their valid range.
		AssertionError: If the provided time is not within the range [0, 86400).
		"""
		offs = None
		if kwargs:
			# Replace everything using standard datetime, except year (which is extended)
			year = kwargs.pop("year", None)
			if year is None:
				year = self.year
			offs, y = divmod(year, ERA_YEARS)
			y += 2000
			offs *= ERA_YEARS
			offs -= 2000
			try:
				dt = self._dt.replace(year=y, **kwargs)
			except ValueError:
				day_partial = hour_partial = minute_partial = 0
				if "microsecond" in kwargs and kwargs["microsecond"] not in range(0, 1e6):
					fraction = (fraction or 0) + to_fraction(kwargs["microsecond"], 1e6)
				if "second" in kwargs and kwargs["second"] not in range(0, 60):
					minute_partial, kwargs["second"] = divmod(kwargs["second"], 60)
				if "minute" in kwargs and kwargs["minute"] not in range(0, 60):
					hour_partial, kwargs["minute"] = divmod(kwargs["minute"], 60)
				if "hour" in kwargs and kwargs["hour"] not in range(0, 24):
					day_partial, kwargs["hour"] = divmod(kwargs["hour"], 24)
				dt = self._dt.replace(year=y, **kwargs) + datetime.timedelta(days=day_partial, hours=hour_partial, minutes=minute_partial)
		else:
			dt = self
		if time is not None:
			# Helper to replace all time values
			assert 0 <= time < 86400
			hour, time = divmod(time, 3600)
			minute, time = divmod(time, 60)
			second, time = divmod(time, 1)
			fraction = fractions.Fraction(time)
			dt = dt.replace(hour=hour, minute=minute, second=second, microsecond=0)
		fraction = fraction if fraction is not None else getattr(self, "fraction", 0) or dt.microsecond / 1e6
		if "tzinfo" in kwargs and isinstance(dt.tzinfo, pytz.BaseTzInfo) and dt.tzinfo._utcoffset.total_seconds() % 1800:
			dt = dt.tzinfo.localize(dt.replace(tzinfo=None))
		self = self.fromdatetime(dt)
		if offs:
			self = self.set_offset(offs)
		self.set_fraction(fraction)
		return self

	def cast(self, tz=datetime.timezone.utc):
		return self.fromtimestamp(self.timestamp_exact(), tz=tz)
	astimezone = cast

	@property
	def year(self) -> int:
		return self._dt.year + self.offset

	@property
	def month(self) -> int:
		return self._dt.month

	@property
	def day(self) -> int:
		return self._dt.day

	@property
	def hour(self) -> int:
		return self._dt.hour

	@property
	def minute(self) -> int:
		return self._dt.minute

	@property
	def second(self) -> int:
		return self._dt.second

	@property
	def microsecond(self) -> int:
		return round(self.fraction * 1e6)

	@property
	def tzinfo(self) -> datetime.tzinfo:
		return self._dt.tzinfo

	def weekday(self) -> int:
		return self._dt.weekday()

	def isoweekday(self) -> int:
		return self._dt.isoweekday()

	def isocalendar(self) -> tuple[int, int, int]:
		return self._dt.isocalendar()

	def date(self) -> datetime.date:
		return self._dt.date()

	def time(self) -> datetime.time:
		return self._dt.time()

	def timetz(self) -> datetime.time:
		return self._dt.timetz()

	def as_year(self) -> str:
		y = abs(self.year)
		year = f"{'%04d' % y}"
		if self.year < 0:
			year += " BCE"
		return year

	def as_date(self) -> str:
		y = abs(self.year)
		date = f"{'%04d' % y}-{'%02d' % self.month}-{'%02d' % self.day}"
		if self.year < 0:
			date += " BCE"
		return date

	def as_time(self, precision=9) -> str:
		"Converts to human-readable timestamp string."
		y = abs(self.year)
		time = f"{'%04d' % y}-{'%02d' % self.month}-{'%02d' % self.day} {'%02d' % self.hour}:{'%02d' % self.minute}:{'%02d' % self.second}"
		if self.fraction:
			time += display_to_precision(self.fraction, precision).lstrip("0")
		if self.year < 0:
			time += " BCE"
		if self.tzinfo:
			time += " " + get_name(self.tzinfo)
		return time

	def as_full(self) -> str:
		"Converts to human-readable natural language string."
		weekday = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[self.weekday() - 1]
		month = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")[self.month - 1]
		year = str(abs(self.year)) + " BCE" * (self.year < 0)
		return f"{weekday} {self.day} {month} {year} at {'%02d' % self.hour}:{'%02d' % self.minute}"

	def as_iso(self, precision=9) -> str:
		"Converts to ISO-compliant timestamp string where possible."
		y = abs(self.year)
		yr = '%04d' % y
		if self.year not in range(0, 10000):
			yr = "+-"[self.year < 0] + yr
		time = f"{yr}-{'%02d' % self.month}-{'%02d' % self.day}T{'%02d' % self.hour}:{'%02d' % self.minute}:{'%02d' % self.second}"
		if self.fraction:
			time += display_to_precision(self.fraction, precision).lstrip("0")
		offset = get_offset(self.tzinfo)
		if offset:
			negative, offset = offset < 0, abs(offset)
			time += "+-"[negative] + time_disp(offset).removesuffix(":00").removesuffix(":00")
		else:
			time += "Z"
		return time
	isoformat = as_iso

	def as_discord(self, strict=True) -> str:
		"Converts to timezone-naive Discord-compliant absolute timestamp where possible."
		ts = round(self.timestamp_exact())
		if not strict or ts in range(0, 8640000000001):
			return f"<t:{round(self.timestamp())}:F>"
		return f"`{self.as_full()}`"

	def as_rel_discord(self, strict=True) -> str:
		"Converts to timezone-naive Discord-compliant relative timestamp where possible."
		ts = round(self.timestamp_exact())
		if not strict or ts in range(0, 8640000000001):
			return f"<t:{round(self.timestamp())}:R>"
		delta = self - self.now(tz=self.tzinfo)
		if delta < 0:
			return f"`{delta.negate()} ago`"
		else:
			return f"`in {delta}`"

	@classmethod
	def utcfromtimestamp(cls, ts):
		return cls.fromtimestamp(ts, tz=datetime.timezone.utc)

	@classmethod
	def fromtimestamp(cls, ts, tz=None):
		offs, ots = divmod(round_min(ts), ERA)
		ext, f = divmod(ots, 1)
		dt = datetime.datetime.fromtimestamp(ext, tz=tz)
		self = cls(*dt.timetuple()[:6], fraction=f, tzinfo=dt.tzinfo)
		self._offset += round(offs * ERA_YEARS)
		self._ts = ts
		return self

	@classmethod
	def to_utc(cls, self):
		return cls.fromtimestamp(self.timestamp())

	@classmethod
	def fromdatetime(cls, dt, tz=None):
		if isinstance(dt, cls):
			return dt.replace(tzinfo=tz) if tz else dt
		return cls(*dt.timetuple()[:6], fraction=to_fraction(dt.microsecond, 10 ** 6), tzinfo=tz or dt.tzinfo)

	@classmethod
	def utcnow(cls):
		return cls.now(tz=datetime.timezone.utc)

	@classmethod
	def now(cls, tz=None):
		return cls.fromtimestamp(cls.unix(), tz=tz)

	@classmethod
	def unix(cls):
		return fractions.Fraction(time.time_ns(), 10 ** 9)

	@classmethod
	def parse_delta(cls, s, return_remainder=False):
		"""
		Parse a time delta from a string representation.
		Args:
			s (str): The string representation of the time delta.
			return_remainder (bool, optional): If True, return the remainder of the string that could not be parsed. Defaults to False.
		Returns:
			TimeDelta: The parsed time delta.
			tuple: If return_remainder is True, returns a tuple containing the parsed time delta and the remainder of the string.
		Raises:
			ValueError: If the input string contains unrecognized tokens.
		Examples:
			>>> parse_delta("1y 2mo 3d")
			TimeDelta(years=1, months=2, days=3)
			>>> parse_delta("1y2mo3d4h30m57s")
			TimeDelta(years=1, months=2, days=3, hours=4, minutes=30, seconds=57)
			>>> parse_delta("1y 2mo 3d", return_remainder=True)
			(TimeDelta(years=1, months=2, days=3), "")
			>>> parse_delta("1y 2mo 3d and 4h", return_remainder=True)
			(TimeDelta(years=1, months=2, days=3, hours=4), "")
			>>> parse_delta("1y 2mo 3d before 4h", return_remainder=True)
			(TimeDelta(years=-1, months=-2, days=-3, hours=4), "")
		"""
		if not isinstance(s, str):
			s = str(s)
		if s.startswith("in "):
			s = s[3:]
		try:
			n = time_parse(s)
		except Exception:
			pass
		else:
			td = TimeDelta(seconds=n)
			if return_remainder:
				return td, ""
			return td
		tokens = s.strip().replace(",", " ").split()
		timechecks = {
			"galactic years": ("gy", "galactic year", "galactic years"),
			"megaanna": ("my", "myr", "megaannum", "megaanna"),
			"millennia": ("ml", "ky", "millennium", "millennia"),
			"centuries": ("c", "century", "centuries"),
			"decades": ("dc", "decade", "decades"),
			"years": ("y", "yr", "year", "years"),
			"months": ("mo", "mth", "mos", "mths", "month", "months"),
			"fortnights": ("fortnight", "fortnights"),
			"weeks": ("w", "wk", "week", "wks", "weeks"),
			"days": ("d", "day", "days"),
			"hours": ("h", "hr", "hour", "hrs", "hours"),
			"minutes": ("m", "min", "minute", "mins", "minutes"),
			"seconds": ("s", "sec", "second", "secs", "seconds"),
			"milliseconds": ("ms", "milli", "millisecond", "millis", "milliseconds"),
			"microseconds": ("μ", "us", "μs", "micro", "microsecond", "micros", "microseconds"),
			"nanoseconds": ("ns", "nano", "nanosecond", "nanos", "nanoseconds"),
			"picoseconds": ("ps", "pico", "picosecond", "picos", "picoseconds"),
			"femtoseconds": ("fs", "femto", "femtosecond", "femtos", "femtoseconds"),
			"attoseconds": ("as", "atto", "attosecond", "attos", "attoseconds"),
			"zeptoseconds": ("zs", "zepto", "zeptosecond", "zeptos", "zeptoseconds"),
			"yoctoseconds": ("ys", "yocto", "yoctosecond", "yoctos", "yoctoseconds"),
			"rontoseconds": ("rs", "ronto", "rontosecond", "rontos", "rontoseconds"),
			"quectoseconds": ("qs", "quecto", "quectosecond", "quectos", "quectoseconds"),
			"plancks": ("planck", "plancks"),
		}
		special_values = {
			"galactic years": ("years", UNIT_GALACTIC_YEAR),
			"megaanna": ("years", 1000000),
			"millennia": ("years", 1000),
			"fortnights": ("days", 14),
			"weeks": ("days", 7),
		}
		subsecond_values = dict(
			milliseconds=1e3,
			microseconds=1e6,
			nanoseconds=1e9,
			picoseconds=1e12,
			femtoseconds=1e15,
			attoseconds=1e18,
			zeptoseconds=1e21,
			yoctoseconds=10 ** 24,
			rontoseconds=10 ** 27,
			quectoseconds=10 ** 30,
			plancks=539 * 10 ** 42,
		)
		timeunits = {u: k for k, v in timechecks.items() for u in v}
		abbreviations = {k: timeunits[k] for k in (
			"gy",
			"my", "myr",
			"ml", "ky",
			"c",
			"dc",
			"y", "yr",
			"mo", "mth", "mos", "mths",
			"w", "wk", "wks",
			"d",
			"h", "hr", "hrs",
			"m", "min", "mins",
			"s", "sec", "secs",
			"ms",
			"μ", "μs", "us",
			"ns",
			"ps",
			"fs",
			"as",
			"zs",
			"ys",
			"rs",
			"qs",
		)}
		abbrevs = re.compile(r"^(?:[+-]?([0-9]*[.])?[0-9]+(?:" + "|".join(abbreviations) + "))+$")

		delta = TimeDelta()
		i = 0
		while i < len(tokens):
			token = tokens[i]
			# Parse full abbreviations first (e.g. "1mo3d4h30m57s")
			if abbrevs.fullmatch(token):
				tokens.pop(i)
				num = 1
				unit = None
				while token:
					match = num_re.match(token)
					if not match:
						search = num_re.search(token)
						if search:
							match, token = token[:search.start()], token[search.end():]
							unit = abbreviations[match]
							if unit in subsecond_values:
								delta.fraction += to_fraction(num, subsecond_values[unit])
							else:
								setattr(delta, unit, num)
							num = parse_num(search.group())
							continue
						match, token = token, ""
						unit = abbreviations[match]
					else:
						token = token[match.end():]
						num = parse_num(match.group())
						continue
					assert unit
					if unit in special_values:
						unit, mult = special_values[unit]
						num *= mult
					if unit in subsecond_values:
						delta.fraction += to_fraction(num, subsecond_values[unit])
					else:
						setattr(delta, unit, num)
				if i < len(tokens) - 1:
					token2 = tokens[i]
					if token2 in ("before", "ago", "to", "until", "till"):
						delta.negate()
						tokens.pop(i)
					elif token2 in ("after", "past", "in", "from"):
						tokens.pop(i)
					elif token2 == "and":
						tokens.pop(i)
				continue
			i += 1
		neg = None
		i = len(tokens) - 1
		while i >= 0:
			token = tokens[i]
			# Parse "before" and "after" keywords at the end of a timeframe
			if token in ("before", "ago", "to", "until", "till"):
				neg = True
				i -= 1
				token = tokens[i]
			elif token in ("after", "past", "in", "from"):
				neg = False
				i -= 1
				token = tokens[i]
			elif token == "and":
				neg = neg or False
				i -= 1
				token = tokens[i]
			# Retry from top if invalid timeunit detected
			if token not in timeunits:
				i -= 1
				continue
			# Greedy scan to include all non-timeunits before current one
			k = i - 1
			for k in range(i - 1, -1, -1):
				if tokens[k] in timeunits:
					k += 1
					break
			# Try each token until a detection succeeds, then add timedelta respecting before/after modes
			for j in range(k, i):
				test = " ".join(tokens[j:i])
				try:
					num = parse_num_long(test)
				except Exception:
					pass
				else:
					if num is not None:
						if neg:
							num = -num
						unit = timeunits[token]
						if unit in special_values:
							unit, mult = special_values[unit]
							num *= mult
						if unit in subsecond_values:
							delta.fraction += to_fraction(num, subsecond_values[unit])
						else:
							setattr(delta, unit, getattr(delta, unit) + num)
						tokens = tokens[:j] + tokens[i + 1 + (neg is not None):]
						i = j
						continue
			i -= 1

		if return_remainder:
			return delta, " ".join(tokens)
		if tokens:
			raise ValueError(tokens)
		return delta

	@classmethod
	def parse(cls, s="", timestamp=None, timezone=None):
		"""
		Parses a given string to create a datetime object with various parsing modes.
		Args:
			s (str): The string to parse. Defaults to an empty string.
			timestamp (float, optional): A Unix timestamp to use as a reference point. Defaults to None.
			timezone (str, optional): A timezone string to use for the datetime object. Defaults to None.
		Returns:
			datetime: A datetime object parsed from the input string.
		Raises:
			ValueError: If the mode is "unix" and the input string is not a valid Unix timestamp.
		Parsing Modes:
			- "now": Current datetime.
			- "now+": Relative to current datetime.
			- "noon": 12 PM.
			- "midnight": 12 AM.
			- "last", "previous", "next", "this", "today", "tomorrow", "yesterday", "unix": Relative datetime.
			- "bce", "bc", "ad", "ce": Common era indicators.
			- "in", "at": Timezone indicators.
			- "natural_language": Natural language parsing.
			- "year": Year parsing.
			- "yyyymmdd": Date parsing in YYYYMMDD format.
			- "unix_timestamp": Unix timestamp parsing.
			- "value": General value parsing.
			- "delta": Time delta parsing.
			- "current": Current datetime.
		Notes:
			- The function handles various datetime formats and natural language inputs.
			- It supports parsing of timezones and relative dates.
			- The function can handle BCE/CE indicators and Unix timestamps.
		"""
		if not isinstance(s, str):
			s = str(s)
		tokens = s.casefold().strip().replace(",", " ").split()
		parsed_as = []

		mode = "next"
		for i, token in enumerate(tuple(tokens)):
			if token == "now":
				tokens.pop(i)
			elif token.startswith("now+") or token.startswith("now-"):
				tokens[i] = token[3:]
			elif token == "noon":
				tokens[i] = "12PM"
			elif token == "midnight":
				tokens[i] = "12AM"
			elif ts_re.match(token):
				tokens[i] = token.split(":", 1)[-1].replace(">", ":").split(":", 1)[0] + ".0"
				parsed_as.append("discord_timestamp")
		for m in ("last", "previous", "next", "this", "today", "tomorrow", "yesterday", "unix"):
			if m in tokens:
				tokens.remove(m)
				mode = m
				parsed_as.append("relative")
				break

		direction = None
		if "bce" in tokens:
			tokens.remove("bce")
			direction = "bce"
		elif "bc" in tokens:
			tokens.remove("bc")
			direction = "bce"
		elif "ad" in tokens:
			tokens.remove("ad")
			direction = "ce"
		elif "ce" in tokens:
			tokens.remove("ce")
			direction = "ce"
		if direction is not None:
			parsed_as.append("common_era")

		tzinfo = None
		if tokens:
			try:
				tzinfo = get_timezone(tokens[-1])
				assert tzinfo, tzinfo
			except (KeyError, AssertionError):
				try:
					tzinfo = get_timezone(tokens[0])
					assert tzinfo, tzinfo
				except (KeyError, AssertionError):
					pass
				else:
					parsed_as.append("timezone")
					tokens.pop(0)
			else:
				parsed_as.append("timezone")
				tokens.pop(-1)
				if tokens and tokens[-1] in ("in", "at"):
					tokens.pop(-1)
		if not tzinfo:
			if timezone:
				tzinfo = get_timezone(timezone)
			else:
				tzinfo = datetime.timezone.utc

		s = " ".join(tokens)
		if s and not is_number(s):
			offset, s = cls.parse_delta(s, return_remainder=True)
		else:
			offset = None

		natural_language = False
		tokens = s.split()
		i = 0
		while i < len(tokens):
			n = None
			for j in range(i + 1, len(tokens) + 1):
				temp = " ".join(tokens[i:j])
				if is_number(temp):
					continue
				try:
					n = parse_num_long(temp)
				except Exception:
					if n is not None:
						natural_language = True
						tokens = tokens[:i] + [str(n) + "."] + tokens[j:]
						i = j
						break
			else:
				if n is not None:
					natural_language = True
					tokens = tokens[:i] + [str(n) + "."] + tokens[j + 1:]
					i = j + 1
					continue
				i += 1
		if natural_language:
			parsed_as.append("natural_language")
		s = " ".join(tokens)
		self = None
		if is_number(s):
			n = parse_num(s)
			if mode != "unix" and (s.endswith(".") or "." not in s and (direction is not None or 1970 <= n <= 2038)):
				parsed_as.append("year")
				self = cls(n, 1, 1, tzinfo=tzinfo)
			elif mode != "unix" and ("." not in s and (direction is not None or 19700101 <= n <= 99991231 and (1 <= n % 10000 // 100 <= 12 and 1 <= n % 100 <= 31))):
				parsed_as.append("yyyymmdd")
				dt = dateutil.parser.parse(str(n), fuzzy=False)
				self = cls.fromdatetime(dt, tz=tzinfo)
			else:
				parsed_as.append("unix_timestamp")
				self = cls.fromtimestamp(n, tz=tzinfo)
		elif mode == "unix":
			raise ValueError(f"Expected a number representing unix timestamp in seconds, got {repr(s)}")

		if s and self is None:
			if timestamp:
				self = cls.fromtimestamp(timestamp, tz=tzinfo)
			else:
				self = cls.now(tz=tzinfo)
			now = self.timestamp_exact()
			self = self.replace(time=0)
			temp = TemporaryDT()
			replacers = {}
			# Parse special indicators such as "last monday", "this month", "next year" etc
			if mode not in ("yesterday", "today", "tomorrow"):
				last_unit = None
				replaced_units = ["year", "month", "week", "day", "hour", "minute", "second"]
			else:
				last_unit = "days"
				replaced_units = ["hour", "minute", "second"]
			# Handle weeks separately since they are not an atomic datetime unit
			unspec = False
			if mode in ("last", "this", "next"):
				tokens = s.split()
				if tokens[0] in replaced_units:
					last_unit = tokens.pop(0)
					if last_unit == "week":
						temp = temp.replace(day=self.day)
					else:
						temp = temp.replace(**{last_unit: getattr(self, last_unit)})
					last_unit += "s"
					unspec = True
				elif tokens[-1] in replaced_units:
					last_unit = tokens.pop(-1)
					if last_unit == "week":
						temp = temp.replace(day=self.day)
					else:
						temp = temp.replace(**{last_unit: getattr(self, last_unit)})
					last_unit += "s"
					unspec = True
				s = " ".join(tokens)
			# Parse remaining strings, storing in our intercepted datetime
			if s:
				parsed_as.append("value")
				tokens = s.split()
				for i, t in enumerate(tuple(tokens)):
					if re.fullmatch(r"[+-]?[0-9]+[\-/\\.][0-9]+[\-/\\.][0-9]+", t):
						coerced = t.replace(".", "-").replace("/", "-").replace("\\", "-").rsplit("-", 2)
						y, m, d = map(int, coerced)
						if 1 <= m <= 12 and 1 <= d <= month_days(y, m):
							temp = temp.replace(year=y, month=m, day=d)
							tokens.pop(i)
					elif re.fullmatch(r"[+-]?[0-9]{3,}", t):
						temp = temp.replace(year=int(t))
						tokens.pop(i)
				if tokens:
					s = " ".join(tokens)
					temp = dateutil.parser.parse(s, default=temp, fuzzy=False)
			# Zero out all units after the recognised ones; i.e. for "March 2020" the day is set to 1, and the hour, minute, second, etc are all set to 0
			for unit in replaced_units:
				if unit == "week":
					continue
				if unit in temp.set:
					replacers[unit] = getattr(temp, unit)
					if unspec:
						last_unit = unit + "s"
						unspec = False
				elif replacers:
					replacers[unit] = 1 if unit in ("month", "day") else 0
				else:
					last_unit = unit + "s"
			# Update necessary units
			self = self.replace(**replacers)
			# dateutil relativedelta automatically adds; correct this behaviour to stay relative when the "this" keyword is used
			if last_unit and mode == "this" and temp.deltas and self.weekday() > temp.deltas[-1].weekday.weekday:
				self += TimeDelta(days=-7)
			# Apply weekday update
			for delta in temp.deltas:
				self += delta
			# Handle all cases of "last" and "next"
			if last_unit == "days" and mode == "tomorrow":
				self += TimeDelta(days=1)
			elif last_unit and mode in ("next", "in") and temp.deltas and self.timestamp_exact() < now:
				self += TimeDelta(days=7)
			elif last_unit == "weeks" and mode in ("next", "in") and self.timestamp_exact() < now:
				self += TimeDelta(days=7)
			elif last_unit and mode in ("next", "in") and self.timestamp_exact() < now:
				self += TimeDelta(**{last_unit: 1})
			elif last_unit and mode in ("last", "from") and temp.deltas and self.timestamp_exact() > now:
				self += TimeDelta(days=-7)
			elif last_unit == "weeks" and mode in ("last", "from") and self.timestamp_exact() > now:
				self += TimeDelta(days=-7)
			elif last_unit and mode in ("last", "from") and self.timestamp_exact() > now:
				self += TimeDelta(**{last_unit: -1})
			elif last_unit == "days" and mode == "yesterday":
				self += TimeDelta(days=-1)
		elif self is None:
			parsed_as.append("current")
			if timestamp:
				self = cls.fromtimestamp(timestamp, tz=tzinfo)
			else:
				self = cls.now(tz=tzinfo)
			# Treat day indicators with no time indicators as midnight
			if mode in ("today", "yesterday", "tomorrow"):
				self = self.replace(time=0)
				if mode == "yesterday":
					self += TimeDelta(days=-1)
				elif mode == "tomorrow":
					self += TimeDelta(days=1)
		else:
			raise ValueError(f"Failed to parse {s}")

		if offset:
			parsed_as.append("delta")
			self += offset
		if direction == "bce":
			self = self.replace(year=-self.year)
		self.parsed_as = parsed_as
		return self