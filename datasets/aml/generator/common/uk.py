"""UK formats and calendars: postcodes, phones, bank details, VAT and company numbers, working days."""

import datetime as dt
import re

def _easter(year):
    """Gregorian Easter Sunday (anonymous algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    return dt.date(year, month, (h + l_ - 7 * m + 114) % 31 + 1)


def _monday(year, month, last=False):
    if last:
        d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
        return d - dt.timedelta(days=d.weekday())
    d = dt.date(year, month, 1)
    return d + dt.timedelta(days=(7 - d.weekday()) % 7)


# One-off changes announced by the government.
_MOVED = {2020: {"early_may": dt.date(2020, 5, 8)}, 2012: {"spring": dt.date(2012, 6, 4)},
          2022: {"spring": dt.date(2022, 6, 2)}}
_EXTRA = {2011: [dt.date(2011, 4, 29)], 2012: [dt.date(2012, 6, 5)], 2022: [dt.date(2022, 6, 3), dt.date(2022, 9, 19)],
          2023: [dt.date(2023, 5, 8)]}


def bank_holidays(year):
    """England and Wales bank holidays for a year, with weekend substitutes and one-off changes."""
    days = set()
    ny = dt.date(year, 1, 1)
    days.add(ny + dt.timedelta(days={5: 2, 6: 1}.get(ny.weekday(), 0)))
    easter = _easter(year)
    days |= {easter - dt.timedelta(days=2), easter + dt.timedelta(days=1)}
    moved = _MOVED.get(year, {})
    days.add(moved.get("early_may", _monday(year, 5)))
    days.add(moved.get("spring", _monday(year, 5, last=True)))
    days.add(_monday(year, 8, last=True))
    xmas, boxing = dt.date(year, 12, 25), dt.date(year, 12, 26)
    if xmas.weekday() == 5:      # Saturday: both move to Monday and Tuesday
        days |= {xmas + dt.timedelta(days=2), xmas + dt.timedelta(days=3)}
    elif xmas.weekday() == 6:    # Sunday: Christmas moves to Tuesday, Boxing Day stays Monday
        days |= {xmas + dt.timedelta(days=2), boxing}
    elif xmas.weekday() == 4:    # Friday: Boxing Day moves to Monday
        days |= {xmas, xmas + dt.timedelta(days=3)}
    else:
        days |= {xmas, boxing}
    days |= set(_EXTRA.get(year, []))
    return days


_HOLIDAY_CACHE = {}


def is_bank_holiday(d):
    if d.year not in _HOLIDAY_CACHE:
        _HOLIDAY_CACHE[d.year] = bank_holidays(d.year)
    return d in _HOLIDAY_CACHE[d.year]


def is_working_day(d):
    return d.weekday() < 5 and not is_bank_holiday(d)


def add_working_days(d, n):
    while n > 0:
        d += dt.timedelta(days=1)
        if is_working_day(d):
            n -= 1
    return d


def next_working_day(d):
    while not is_working_day(d):
        d += dt.timedelta(days=1)
    return d


def last_working_day_of_month(year, month):
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    while not is_working_day(d):
        d -= dt.timedelta(days=1)
    return d


def bacs_value_date(submission):
    """BACS three-day cycle: input on day 1, funds arrive on day 3."""
    return add_working_days(submission, 2)


# ---------------------------------------------------------------- places and phones

DISTRICTS = {
    # area label: (town on the address, outward codes)
    "City of London": ("London", ["EC1A", "EC1V", "EC2A", "EC2M", "EC2V", "EC3M", "EC3V", "EC4A"]),
    "Shoreditch": ("London", ["EC2A", "E2"]),
    "Canary Wharf": ("London", ["E14"]),
    "Wapping": ("London", ["E1W"]),
    "Bow": ("London", ["E3"]),
    "Southwark": ("London", ["SE1"]),
    "Deptford": ("London", ["SE8"]),
    "Thamesmead": ("London", ["SE28"]),
    "Islington": ("London", ["N1"]),
    "Tottenham": ("London", ["N17"]),
    "Bloomsbury": ("London", ["WC1A", "WC1B"]),
    "Fitzrovia": ("London", ["W1T", "W1W"]),
    "Croydon": ("Croydon", ["CR0"]),
    "Mitcham": ("Mitcham", ["CR4"]),
    "Hainault": ("Ilford", ["IG6"]),
    "Edinburgh": ("Edinburgh", ["EH3"]),
}

INWARD_LETTERS = "ABDEFGHJLNPQRSTUWXYZ"

STREET_ROOTS = [
    "Halberd", "Tallowmere", "Bellfounder", "Wharfinger", "Saltmarsh", "Lockkeeper", "Cordwainer",
    "Haberdine", "Quillon", "Barrowgate", "Tenterground", "Sailmaker", "Lanthorn", "Mallowfield",
    "Gantry", "Chandler's", "Pewterer", "Hopkiln", "Wainscot", "Tidemill", "Lighterman's",
    "Fellmonger", "Stavewood", "Brickfield", "Coalwharf", "Tackle", "Hatchway", "Malthouse",
    "Glovers", "Netloft", "Furrier's", "Sluicegate", "Bargehouse", "Corbel", "Lamplighter's",
]
STREET_SUFFIXES = ["Street", "Lane", "Yard", "Row", "Court", "Place", "Mews", "Wharf", "Road"]
BUILDING_PREFIXES = ["", "", "", "Unit {n}, ", "Suite {n}, ", "{ord} Floor, "]


def postcode(rng, outward):
    return f"{outward} {rng.randint(1, 9)}{rng.choice(INWARD_LETTERS)}{rng.choice(INWARD_LETTERS)}"


def street_address(rng, used_roots):
    """Invented street; each street root is used once per dataset."""
    prefix = rng.choice(BUILDING_PREFIXES)
    ordinal = rng.choice(["1st", "2nd", "3rd", "4th", "5th"])
    prefix = prefix.format(n=rng.randint(1, 14), ord=ordinal)
    root = rng.choice([r for r in STREET_ROOTS if r not in used_roots])
    used_roots.add(root)
    return f"{prefix}{rng.randint(2, 148)} {root} {rng.choice(STREET_SUFFIXES)}"


DRAMA_LANDLINE = {"London": "020 7946 0", "Edinburgh": "0131 496 0"}


def landline(rng, used, city="London"):
    """Ofcom reserves these ranges for fiction (020 7946 0xxx, 0131 496 0xxx), so they never ring a real line."""
    while True:
        n = f"{DRAMA_LANDLINE[city]}{rng.randint(0, 999):03d}"
        if n not in used:
            used.add(n)
            return n


def mobile(rng, used):
    """Ofcom reserves 07700 900000-900999 for fiction."""
    while True:
        n = f"07700 900{rng.randint(0, 999):03d}"
        if n not in used:
            used.add(n)
            return n


# ---------------------------------------------------------------- banks

BANKS = {
    # display name: (IBAN bank code, sort-code prefixes, or a fixed sort code)
    "Barclays": ("BARC", ["20"]),
    "HSBC UK": ("HBUK", ["40"]),
    "Lloyds Bank": ("LOYD", ["30", "77"]),
    "NatWest": ("NWBK", ["60", "50"]),
    "Santander UK": ("ABBY", ["09"]),
    "Metro Bank": ("MYMB", "23-05-80"),
    "Starling Bank": ("SRLG", "60-83-71"),
}


def sort_code(rng, bank):
    spec = BANKS[bank][1]
    if isinstance(spec, str):
        return spec
    return f"{rng.choice(spec)}-{rng.randint(0, 99):02d}-{rng.randint(0, 99):02d}"


def account_number(rng):
    return f"{rng.randint(10_000_000, 99_999_999)}"


def _iban_check(country, bban):
    digits = "".join(str(int(c, 36)) for c in bban + country + "00")
    return 98 - int(digits) % 97


def iban(bank, sc, acct):
    bban = BANKS[bank][0] + sc.replace("-", "") + acct
    return f"GB{_iban_check('GB', bban):02d}{bban}"


def iban_valid(value):
    value = value.replace(" ", "")
    rearranged = value[4:] + value[:4]
    return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1


# ---------------------------------------------------------------- VAT and company numbers

VAT_WEIGHTS = [8, 7, 6, 5, 4, 3, 2]


def vat_number(rng):
    """GB VAT number whose last two digits satisfy HMRC's modulus-97 check."""
    while True:
        body = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(6)]
        check = (-sum(w * d for w, d in zip(VAT_WEIGHTS, body))) % 97
        if check < 97:
            return "GB" + "".join(map(str, body)) + f"{check:02d}"


def vat_valid(value):
    m = re.fullmatch(r"GB(\d{9})", value)
    if not m:
        return False
    d = [int(c) for c in m.group(1)]
    total = sum(w * x for w, x in zip(VAT_WEIGHTS, d[:7])) + int(m.group(1)[7:])
    return total % 97 in (0, 42)  # 42 covers the newer "+55" scheme


# Approximate Companies House numbering by year of incorporation, so a number matches a firm's age.
_NUMBERING = {
    "England": [(2004, 5_000_000), (2008, 6_450_000), (2010, 7_100_000), (2012, 7_900_000), (2014, 8_800_000),
                (2016, 9_950_000), (2018, 11_150_000), (2020, 12_380_000), (2021, 13_100_000),
                (2022, 13_850_000), (2023, 14_600_000), (2024, 15_400_000), (2025, 16_150_000), (2027, 17_650_000)],
    "LLP": [(2004, 305_000), (2010, 352_000), (2015, 400_000), (2020, 430_000), (2024, 450_000), (2027, 462_000)],
    "Scotland": [(2004, 260_000), (2010, 370_000), (2015, 500_000), (2020, 650_000), (2024, 800_000), (2027, 860_000)],
}


def company_number(rng, legal_form, incorporated, country="England"):
    series = "LLP" if legal_form == "LLP" else country
    pts = _NUMBERING[series]
    y = incorporated.year + (incorporated.timetuple().tm_yday - 1) / 365
    for (y0, n0), (y1, n1) in zip(pts, pts[1:]):
        if y0 <= y < y1:
            n = int(n0 + (n1 - n0) * (y - y0) / (y1 - y0)) + rng.randint(-1500, 1500)
            break
    if series == "LLP":
        return f"OC{n:06d}"
    if series == "Scotland":
        return f"SC{n:06d}"
    return f"{n:08d}"


POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]? \d[ABD-HJLNP-UW-Z]{2}$")
SORT_CODE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}$")
COMPANY_NO_RE = re.compile(r"^(\d{8}|OC\d{6}|SC\d{6})$")
