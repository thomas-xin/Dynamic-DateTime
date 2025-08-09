# Dynamic-DateTime

## Installation
`py -m pip install dynamic-datetime` - Windows<br />
`python3 -m pip install dynamic-datetime` - Linux

## Usage
- Usage examples (date used for most examples is 2024/12/08)
```python
from dynamic_dt import DynamicDT, TimeDelta, get_timezone

# Parsing
DynamicDT.parse("now")    # 2024-12-08 06:13:27.7125025 UTC
DynamicDT.parse("now in MDT")    # 2024-12-08 00:14:02.9757217 MDT
DynamicDT.parse("now in London")    # 2024-12-08 06:14:37.6658725 Europe/London
DynamicDT.parse("3 october 2016 in edt")    # 2016-10-03 00:00:00 EDT
DynamicDT.parse("1961/01/29")    # 1961-01-29 00:00:00 UTC
DynamicDT.parse("-123456789/05/11")    # 123456789-05-11 00:00:00 BCE UTC
DynamicDT.parse("next thursday acdt")    # 2024-12-12 00:00:00 ACDT
DynamicDT.parse("2 hours before last december 22nd, utc-12")    # 2023-12-21 22:00:00 UTC-12
DynamicDT.parse("one minute before two hours after sixty two years before three hundred and twelve thousand and seventy one nanoseconds before a million years after tomorrow")    # 1001962-12-09 01:58:59.999687929 UTC
DynamicDT.parse("300-06-09 bce 6pm aqtt")    # 0300-06-09 18:00:00 BCE AQTT

# Arithmetic
DynamicDT.parse("now+1h") - DynamicDT.parse("now")    # 59 minutes 59.9999153 seconds
DynamicDT.parse("now+1h", timestamp=1733639741) - DynamicDT.parse("now", timestamp=1733639741)    # 1 hour
DynamicDT.parse("now+1h utc-1.5") + DynamicDT.parse_delta("9876543210 years, -1 attoseconds")    # 9876545234-12-08 06:17:13.1265439 UTC-1:30

# Advanced
import datetime
import pytz

repr(DynamicDT.parse_delta("1 year"))    # TimeDelta(1, 0, 0, 0, 0, 0, 0, None)
DynamicDT.parse_delta("1 year").total_seconds()    # 31556925
DynamicDT.parse_delta("9876543210 years, -1 attoseconds").to_string(precision=20)    # 43 galactic years 123 megaanna 541 millennia 210 years -1 day 23 hours 59 minutes 59.999999999999999999 seconds
DynamicDT.parse_delta("1234567 seconds").negate().to_short()    # -14d6h56m7s
DynamicDT.parse_delta("-14d6h56m7s +2mo")   # 2 months -15 days 17 hours 3 minutes 53 seconds
repr(DynamicDT.parse("4 years after"))    # DynamicDT(2028, 12, 8, 6, 48, 14, fraction=Fraction(4312121, 10000000), tzinfo=get_timezone('UTC'))
DynamicDT.parse("4 years after").as_iso()    # 2028-12-08T06:48:43.8579817Z
DynamicDT.parse("4 years after").as_full()    # Thursday 8 December 2028 at 06:49
DynamicDT.parse("4 years after").as_discord()    # <t:1859870945:F>
DynamicDT.parse("4 years after").as_rel_discord()    # <t:1859871001:R>
DynamicDT.parse("4 years after").timestamp()    # 1859871105.7713845
DynamicDT.parse("4 years after").timestamp_exact()    # Fraction(18598711279456937, 10000000)
DynamicDT.parse("4 years after").replace(year=300000, minute=3, tzinfo=get_timezone("utc+6"))    # 300000-12-08 06:03:53.9029728 UTC+6
DynamicDT.parse("4 years after").cast(tz=get_timezone("utc+6"))    # 2028-12-08 12:55:54.789339 UTC+6
repr(DynamicDT.now())    # DynamicDT(2024, 12, 8, 17, 56, 31, fraction=Fraction(6281317, 10000000))
repr(DynamicDT.now(tz=datetime.timezone.utc))    # DynamicDT(2024, 12, 8, 6, 56, 55, fraction=Fraction(1347719, 2000000), tzinfo=get_timezone('UTC'))
DynamicDT(1234, 5, 6, 7, tzinfo=pytz.timezone("US/Mountain"))    # DynamicDT(1234, 5, 6, 7, 0, 0, tzinfo=get_timezone('US/Mountain'))
DynamicDT.unix()    # Fraction(17336412228141707, 10000000)
repr(DynamicDT.fromtimestamp(-100000000000, tz=get_timezone("pacific")))   # DynamicDT(-1199, 2, 15, 6, 13, 20, tzinfo=get_timezone('US/Pacific'))
DynamicDT.parse("1 yoctosecond from now").timestamp_string(100)    # 1736318072.652227100000000000000001
DynamicDT.parse("1 quectosecond until now").timestamp_string(100)    # 1736318184.458186399999999999999999999999
```
