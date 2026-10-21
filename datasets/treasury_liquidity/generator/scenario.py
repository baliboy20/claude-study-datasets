"""Treasury liquidity dataset.

Thameside Bank, the retail and commercial bank of Thameside Financial Group, forecasts its cash inflows and outflows every
working day. Its treasury team builds a liquidity ladder from the forecast: flows placed in time buckets, converted to
sterling, netted, and tested against the bank's liquid asset buffer under a base case and three stress scenarios. Each row of
cashflows is one forecast flow due from Thursday 1 October to Thursday 31 December 2026. The forecast is as at the close of
business on Wednesday 30 September 2026, and the data was extracted at 18:00 that day. Counterparties outside the group are
identified by reference only.
"""

import datetime as dt
from collections import defaultdict

from generator import ladder
from generator.common import firm, staff_register, uk
from generator.common.dataset import Col, Table
from generator.common.people import email_for

D = dt.date
AS_AT = ladder.AS_AT
H_START, H_END = D(2026, 10, 1), D(2026, 12, 31)
EXTRACT = dt.datetime(2026, 9, 30, 18, 0)
BASE_RUN, ADJ_RUN, STRESS_RUN = "BASE-20260930", "BASE-20260930-ADJ", "ST02-20260929"
DAILY_LIMIT = ladder.DAILY_LIMIT
GROUP_LIMIT_PCT = ladder.GROUP_LIMIT_PCT
STORY_APPROVED = True  # approved by the user on 20 October 2026

# ------------------------------------------------------------------ schema


def C(*a, **k):
    return Col(*a, **k)


SCHEMA = [
    Table("staff", "lookup", "People in Thameside Bank's treasury and liquidity risk teams, and the chair of the Asset and Liability Committee (ALCO).", [
        C("staff_id", "TEXT", "Staff identifier."),
        C("first_name", "TEXT", "First name."),
        C("last_name", "TEXT", "Surname."),
        C("job_title", "TEXT", "Job title."),
        C("team", "TEXT", "Team."),
        C("office", "TEXT", "Office: City, Canary Wharf or Croydon."),
        C("dealing_limit_gbp", "REAL", "Largest single wholesale deal, in sterling, the person may agree. Empty if the person may not deal.", required=False),
        C("email", "TEXT", "Work email address."),
    ]),
    Table("treasury_policy", "lookup", "Thameside Bank's liquidity policy, version 3.1, in force from 1 July 2026: which flows the forecast includes, how each figure in the liquidity ladder is calculated, and the limits the ladder is tested against.", [
        C("policy_id", "TEXT", "Policy reference, for example TP-05."),
        C("category", "TEXT", "Scope, Definition, Calculation, Stress or Limit."),
        C("title", "TEXT", "Short name of the policy."),
        C("statement", "TEXT", "The policy in full."),
        C("threshold", "REAL", "The number the policy uses, if it has one.", required=False),
        C("unit", "TEXT", "Unit of the threshold: GBP, percent or days.", required=False),
    ]),
    Table("liquidity_buckets", "lookup", "The ladder's reporting intervals, counted in calendar days after the as-at date, and the rule for placing a flow in one.", [
        C("bucket_id", "TEXT", "Bucket identifier, B1 (earliest) to B6."),
        C("bucket_name", "TEXT", "Name of the interval."),
        C("from_day", "INTEGER", "First day of the bucket, in calendar days after the as-at date."),
        C("to_day", "INTEGER", "Last day of the bucket, in calendar days after the as-at date."),
        C("start_date", "TEXT", "First date in the bucket."),
        C("end_date", "TEXT", "Last date in the bucket."),
        C("allocation_rule", "TEXT", "How a flow is placed in this bucket (policy TP-04)."),
    ]),
    Table("counterparties", "lookup", "The other parties to the forecast flows. Firms outside the group are identified by reference and a description only. Ratings are invented for the study.", [
        C("counterparty_id", "TEXT", "Counterparty reference, for example CP-0012."),
        C("counterparty_type", "TEXT", "Bank, Building society, Money market fund, Local authority, Corporate, Intra-group, Government, Bondholders, Investor, Customer pool or Other."),
        C("description", "TEXT", "What the counterparty is. Names are withheld outside the group and government."),
        C("credit_rating", "TEXT", "Long-term credit rating, or fund rating for a money market fund. Not rated, or Not applicable for customer pools, government and the group's own companies."),
        C("concentration_group", "TEXT", "Group of counterparties treated as one for concentration (policy TP-15), for example two entities of one banking group. Empty for customer pools.", required=False),
        C("country", "TEXT", "Country of incorporation, as an ISO 3166 two-letter code."),
        C("intra_group", "TEXT", "Yes for a company in Thameside Financial Group, otherwise No."),
    ]),
    Table("fx_rates", "lookup", "Exchange rates captured by the treasury dealing system at 16:00 London time, quoted as units of the currency per £1.", [
        C("fx_rate_id", "TEXT", "Rate identifier: FX, currency and valuation date, for example FX-USD-20260930."),
        C("valuation_date", "TEXT", "Date the rate was captured."),
        C("base_currency", "TEXT", "Currency the rate is quoted against: always GBP."),
        C("quote_currency", "TEXT", "Currency quoted: USD or EUR."),
        C("rate", "REAL", "Units of the quote currency per £1, to four decimal places."),
        C("rate_type", "TEXT", "Spot."),
        C("source", "TEXT", "Where the rate came from."),
    ]),
    Table("liquid_assets", "lookup", "The bank's liquid asset buffer at the as-at date: unencumbered assets it can sell or use as collateral to raise cash at once.", [
        C("asset_id", "TEXT", "Asset identifier, for example LA-02."),
        C("asset_class", "TEXT", "Reserves at the Bank of England, UK gilts, Supranational bonds or Covered bonds."),
        C("description", "TEXT", "What the holding is."),
        C("currency", "TEXT", "GBP."),
        C("market_value_gbp", "REAL", "Market value at the as-at date."),
        C("base_haircut_pct", "REAL", "Haircut the bank applies in the base case, in percent (policy TP-09)."),
    ]),
    Table("stress_scenarios", "lookup", "The three stress scenarios, one row per assumption: outflow shocks, reduced inflows, falls in sterling and funding haircuts on the buffer. Applied to the base case as policy TP-11 sets out.", [
        C("parameter_id", "TEXT", "Assumption identifier, for example SP-07."),
        C("scenario_id", "TEXT", "Scenario: ST-01, ST-02 or ST-03."),
        C("scenario_name", "TEXT", "Name of the scenario."),
        C("parameter_type", "TEXT", "Outflow increase, Inflow reduction, FX move or Funding haircut."),
        C("applies_to", "TEXT", "The flow type, currency or asset class the assumption applies to."),
        C("shock_pct", "REAL", "Size of the assumption, in percent: the increase or reduction in the flow, the fall in sterling, or the haircut added to the base haircut."),
        C("description", "TEXT", "The assumption in words."),
    ]),
    Table("funding_instruments", "business", "Thameside Bank's wholesale funding that matures, starts or pays interest within reach of the forecast: term deposits, certificates of deposit, repos and senior notes, with their terms.", [
        C("instrument_id", "TEXT", "Instrument identifier, for example FI-0031. Numbers rise with the time the deal was booked."),
        C("counterparty_id", "TEXT", "Lender or investor.", "counterparties.counterparty_id"),
        C("instrument_type", "TEXT", "Term deposit, Certificate of deposit, Repo (gilt collateral) or Senior unsecured note."),
        C("deal_status", "TEXT", "Executed (contract agreed and confirmed), or Agreed in principle, not signed."),
        C("deal_date", "TEXT", "Date the terms were agreed."),
        C("booked_at", "TEXT", "Date and time the deal was entered in the treasury dealing system."),
        C("start_date", "TEXT", "Date the money is received."),
        C("maturity_date", "TEXT", "Contractual maturity date, before any business-day adjustment."),
        C("currency", "TEXT", "GBP, USD or EUR."),
        C("principal", "REAL", "Amount borrowed, in the instrument's currency."),
        C("interest_rate_pct", "REAL", "Fixed annual interest rate, in percent."),
        C("day_count_basis", "TEXT", "ACT/365 (sterling) or ACT/360 (dollars and euros), or Semi-annual coupon for a note."),
        C("interest_at_maturity", "REAL", "Interest paid with the principal at maturity, in the instrument's currency (policy TP-06). Empty for a note, which pays coupons.", required=False),
        C("collateral", "TEXT", "Unsecured, or the collateral given."),
        C("terms", "TEXT", "Contractual terms in brief."),
        C("business_day_convention", "TEXT", "Rule for a payment date that falls on a weekend or bank holiday (policy TP-06)."),
        C("rollover_of_id", "TEXT", "Instrument this deal replaces at its maturity, if it is a rollover.", "funding_instruments.instrument_id", required=False),
        C("dealer_id", "TEXT", "Dealer who agreed the deal.", "staff.staff_id"),
    ]),
    Table("cashflows", "business", "Primary table: every flow in the liquidity forecast due from 1 October to 31 December 2026, as loaded for the forecast at the close of business on 30 September 2026.", [
        C("cashflow_id", "TEXT", "Cash-flow identifier, for example CF-0061. Numbers follow the due date."),
        C("counterparty_id", "TEXT", "Counterparty paying or receiving the money.", "counterparties.counterparty_id"),
        C("instrument_id", "TEXT", "Funding instrument the flow belongs to, if any.", "funding_instruments.instrument_id", required=False),
        C("flow_type", "TEXT", "Kind of flow, for example Wholesale funding maturity or Retail deposit outflow."),
        C("business_unit", "TEXT", "Unit that owns the flow: Treasury, Retail Banking, Business Banking or Finance."),
        C("direction", "TEXT", "Inflow or Outflow."),
        C("currency", "TEXT", "GBP, USD or EUR."),
        C("nominal", "REAL", "Amount of the flow in its own currency, always positive."),
        C("fx_rate_id", "TEXT", "Rate used to convert a USD or EUR flow to sterling. Empty for a sterling flow.", "fx_rates.fx_rate_id", required=False),
        C("amount_gbp", "REAL", "Sterling amount of the flow as recorded, always positive (policy TP-05)."),
        C("due_date", "TEXT", "Date the flow is contractually due, or the date the business unit forecasts it for."),
        C("expected_date", "TEXT", "Date the flow is expected to settle. The same as the due date unless the business unit expects it to be late."),
        C("contract_status", "TEXT", "Confirmed (a contract fixes it), Behavioural (a forecast from past behaviour) or Unconfirmed (expected, with no contract) (policy TP-02)."),
        C("forecast_run", "TEXT", "Run of the forecasting system that loaded the flow."),
        C("entered_by", "TEXT", "Person whose run or entry loaded the flow.", "staff.staff_id"),
        C("entered_date", "TEXT", "Date the flow was first recorded."),
        C("notes", "TEXT", "Comment recorded with the flow.", required=False),
    ]),
]

# ------------------------------------------------------------------ reference data

STAFF_REGISTER_IDS = {"STF-01": "TFG-057", "STF-02": "TFG-058", "STF-03": "TFG-059", "STF-04": "TFG-060",
                      "STF-05": "TFG-061", "STF-06": "TFG-062", "STF-07": "TFG-001"}
HEAD, ALM, SENIOR_DEALER, DEALER, ANALYST, RISK, CFO = (f"STF-0{i}" for i in range(1, 8))
DEALING_LIMIT = {"Head of Treasury": 250_000_000, "Senior Money Markets Dealer": 100_000_000, "Money Markets Dealer": 50_000_000}
TEAM = {"Chief Financial Officer": "Finance (chair of ALCO)", "Liquidity Risk Manager": "Liquidity Risk"}

# id, type, description, rating, concentration group, country
COUNTERPARTIES = [
    ("CP-0001", "Bank", "UK clearing bank", "A+", "CG-01", "GB"),
    ("CP-0002", "Bank", "UK clearing bank", "AA-", "CG-02", "GB"),
    ("CP-0003", "Bank", "UK clearing bank, ring-fenced subsidiary", "A+", "CG-01", "GB"),
    ("CP-0004", "Bank", "German bank, London branch", "A", "CG-03", "DE"),
    ("CP-0005", "Bank", "German bank", "A", "CG-03", "DE"),
    ("CP-0006", "Bank", "French bank, London branch", "A+", "CG-04", "FR"),
    ("CP-0007", "Bank", "Dutch bank", "A+", "CG-05", "NL"),
    ("CP-0008", "Bank", "Japanese bank, London branch", "A", "CG-06", "JP"),
    ("CP-0009", "Bank", "Canadian bank, London branch", "AA-", "CG-07", "CA"),
    ("CP-0010", "Bank", "US bank, London branch", "A+", "CG-08", "US"),
    ("CP-0011", "Bank", "US bank, UK subsidiary", "A+", "CG-08", "GB"),
    ("CP-0012", "Bank", "Nordic bank, London branch", "AA-", "CG-09", "SE"),
    ("CP-0013", "Bank", "Spanish bank, UK subsidiary", "A", "CG-10", "GB"),
    ("CP-0014", "Building society", "UK building society", "A", "CG-11", "GB"),
    ("CP-0015", "Money market fund", "Sterling liquidity fund (low-volatility net asset value)", "AAAmmf", "CG-12", "IE"),
    ("CP-0016", "Money market fund", "Sterling liquidity fund (low-volatility net asset value)", "AAAmmf", "CG-13", "IE"),
    ("CP-0017", "Money market fund", "US dollar liquidity fund (low-volatility net asset value)", "AAAmmf", "CG-14", "LU"),
    ("CP-0018", "Money market fund", "Sterling liquidity fund, same manager as CP-0015", "AAAmmf", "CG-12", "IE"),
    ("CP-0019", "Local authority", "London borough council", "Not rated", "CG-15", "GB"),
    ("CP-0020", "Local authority", "County council, South East England", "Not rated", "CG-16", "GB"),
    ("CP-0021", "Local authority", "Metropolitan borough council, North West England", "Not rated", "CG-17", "GB"),
    ("CP-0022", "Corporate", "UK commercial property group", "BBB+", "CG-18", "GB"),
    ("CP-0023", "Corporate", "UK housing association", "A-", "CG-19", "GB"),
    ("CP-0024", "Corporate", "UK defined-benefit pension scheme", "Not rated", "CG-20", "GB"),
    ("CP-0025", "Intra-group", "Thameside Insurance Limited, a company in the group", "Not applicable", "CG-00", "GB"),
    ("CP-0026", "Intra-group", "Thameside Financial Group plc, the parent company", "Not applicable", "CG-00", "GB"),
    ("CP-0027", "Government", "UK Government: coupons on the bank's gilt holdings", "Not applicable", "CG-21", "GB"),
    ("CP-0028", "Government", "HM Revenue & Customs", "Not applicable", "CG-21", "GB"),
    ("CP-0029", "Bondholders", "Holders of Thameside Bank senior notes, paid through the paying agent", "Not applicable", "CG-22", "GB"),
    ("CP-0030", "Investor", "Prospective buyer of a tranche of the bank's mortgages", "Not rated", "CG-23", "GB"),
    ("CP-0031", "Customer pool", "Retail depositors", "Not applicable", None, "GB"),
    ("CP-0032", "Customer pool", "Business depositors", "Not applicable", None, "GB"),
    ("CP-0033", "Customer pool", "Mortgage customers", "Not applicable", None, "GB"),
    ("CP-0034", "Customer pool", "Business lending customers", "Not applicable", None, "GB"),
    ("CP-0035", "Other", "Employees (payroll)", "Not applicable", None, "GB"),
    ("CP-0036", "Other", "Suppliers", "Not applicable", None, "GB"),
]

BUCKET_RULE = ("A flow is in this bucket if its bucket date (TP-03) is from_day to to_day calendar days after the as-at date "
               "of 30 September 2026, counting the as-at date as day 0.")

LIQUID_ASSETS = [
    ("LA-01", "Reserves at the Bank of England", "Balance on the bank's reserves account at the Bank of England", 682_000_000, 0.0),
    ("LA-02", "UK gilts", "Conventional gilts maturing within five years, held outright and unencumbered", 610_000_000, 1.0),
    ("LA-03", "UK gilts", "Index-linked gilts, held outright and unencumbered", 140_000_000, 3.0),
    ("LA-04", "Supranational bonds", "Sterling bonds of supranational development banks", 110_000_000, 5.0),
    ("LA-05", "Covered bonds", "Sterling covered bonds of other UK issuers, rated AAA", 100_000_000, 10.0),
]

# scenario id, name, [(type, applies to, pct, words)]
SCENARIOS = [
    ("ST-01", "Market-wide stress", [
        ("Outflow increase", "Retail deposit outflow", 40.0, "Savers withdraw 40% more than forecast as markets fall."),
        ("Outflow increase", "Business deposit outflow", 40.0, "Businesses draw down 40% more of their deposits."),
        ("Outflow increase", "Committed facility drawdown", 100.0, "Businesses draw twice as much on their committed facilities."),
        ("Inflow reduction", "Customer loan repayment", 10.0, "One in ten loan repayments is missed or deferred."),
        ("FX move", "USD", 10.0, "Sterling falls 10% against the US dollar."),
        ("FX move", "EUR", 8.0, "Sterling falls 8% against the euro."),
        ("Funding haircut", "UK gilts", 2.0, "Gilt prices fall; 2 percentage points are added to the gilt haircut."),
        ("Funding haircut", "Covered bonds", 10.0, "Covered bonds become harder to sell; 10 points are added."),
    ]),
    ("ST-02", "Thameside-specific stress", [
        ("Outflow increase", "Retail deposit outflow", 150.0, "After a two-notch downgrade of Thameside Bank, savers withdraw two and a half times the forecast."),
        ("Outflow increase", "Business deposit outflow", 100.0, "Businesses withdraw twice the forecast."),
        ("Outflow increase", "Committed facility drawdown", 50.0, "Businesses draw 50% more on committed facilities."),
        ("Inflow reduction", "New wholesale funding", 100.0, "Lenders withdraw from forward-starting deals."),
        ("Funding haircut", "Covered bonds", 5.0, "5 points are added to the covered bond haircut."),
    ]),
    ("ST-03", "Combined stress", [
        ("Outflow increase", "Retail deposit outflow", 200.0, "Savers withdraw three times the forecast."),
        ("Outflow increase", "Business deposit outflow", 150.0, "Businesses withdraw two and a half times the forecast."),
        ("Outflow increase", "Committed facility drawdown", 150.0, "Businesses draw two and a half times the forecast on committed facilities."),
        ("Inflow reduction", "Customer loan repayment", 15.0, "15% of loan repayments are missed or deferred."),
        ("Inflow reduction", "New wholesale funding", 100.0, "Lenders withdraw from forward-starting deals."),
        ("FX move", "USD", 12.0, "Sterling falls 12% against the US dollar."),
        ("FX move", "EUR", 10.0, "Sterling falls 10% against the euro."),
        ("Funding haircut", "UK gilts", 3.0, "3 points are added to the gilt haircut."),
        ("Funding haircut", "Supranational bonds", 10.0, "10 points are added to the supranational bond haircut."),
        ("Funding haircut", "Covered bonds", 15.0, "15 points are added to the covered bond haircut."),
    ]),
]

POLICY = [
    # id, category, title, statement, threshold, unit
    ("TP-01", "Scope", "As-at date and horizon",
     "The forecast is as at the close of business on Wednesday 30 September 2026 (the as-at date, day 0). The ladder covers "
     "flows with a bucket date from 1 October to 31 December 2026, in the six buckets in liquidity_buckets.", 92, "days"),
    ("TP-02", "Scope", "Flows in the base case",
     "The base case is every flow loaded by a base-case run of the forecasting system (forecast_run beginning BASE-), except "
     "inflows whose contract_status is Unconfirmed. Outflows count whatever their status. An inflow from a funding instrument "
     "is Confirmed only if the instrument's deal_status is Executed. Flows loaded by a stress run are never part of the base case.",
     None, None),
    ("TP-03", "Definition", "Bucket date",
     "The bucket date of an inflow is its expected_date. The bucket date of an outflow is the earlier of its due_date and its "
     "expected_date: an outflow is never assumed to be paid late.", None, None),
    ("TP-04", "Calculation", "Bucket allocation",
     "Days = bucket date - as-at date, in calendar days. A flow is in the bucket whose from_day <= days <= to_day. A flow "
     "linked to a funding instrument is due on the instrument's payment date (TP-06).", None, "days"),
    ("TP-05", "Calculation", "Conversion to sterling",
     "A USD or EUR flow is converted at the spot rate in fx_rates for the as-at date, whenever the flow was entered: "
     "amount_gbp = nominal / rate, rounded to the penny, halves rounded up. A sterling flow is not converted. A sterling amount "
     "fixed by a contract, such as the sterling leg of an FX swap, is a sterling flow.", None, None),
    ("TP-06", "Calculation", "Maturity amount and payment date",
     "Payment date = the maturity date adjusted under the modified following convention: if it is not a working day in "
     "England, the next working day, unless that falls in the next calendar month, in which case the previous working day. "
     "Interest = principal x interest_rate_pct / 100 x days / basis, rounded to the penny, halves rounded up, where days run "
     "from start_date to the payment date and basis is 365 for ACT/365 and 360 for ACT/360. The maturity flow is principal + "
     "interest, on the payment date. A rollover with the same counterparty settles only the interest; the principal stays.",
     None, None),
    ("TP-07", "Calculation", "Net gap",
     "Net gap for a bucket = the sum of amount_gbp of the base-case inflows in the bucket - the sum of amount_gbp of the "
     "base-case outflows in the bucket.", None, "GBP"),
    ("TP-08", "Calculation", "Cumulative gap",
     "Cumulative gap for a bucket = the sum of the net gaps of that bucket and every earlier bucket.", None, "GBP"),
    ("TP-09", "Calculation", "Liquid asset buffer",
     "Buffer = the sum over liquid_assets of market_value_gbp x (1 - haircut / 100), each rounded to the penny. The base case "
     "uses base_haircut_pct. The buffer is available from day 1.", None, "GBP"),
    ("TP-10", "Calculation", "Liquidity position",
     "Liquidity position for a bucket = buffer (TP-09) + cumulative gap (TP-08) for that bucket.", None, "GBP"),
    ("TP-11", "Stress", "Applying a stress scenario",
     "A stress scenario starts from the base-case flows (TP-02) and changes them using only its own rows in "
     "stress_scenarios. Stressed amount = amount_gbp x m / (1 - f / 100), rounded to the penny, halves rounded up, where "
     "m = 1 + shock_pct / 100 for an Outflow increase on the flow's type, m = 1 - shock_pct / 100 for an Inflow reduction on "
     "the flow's type, otherwise 1, and f = the FX move for the flow's currency, otherwise 0. A Funding haircut adds shock_pct "
     "to the base haircut of every asset of that class. A scenario's figures are never combined with base-case figures or with "
     "another scenario's.", None, None),
    ("TP-12", "Limit", "Survival over the horizon",
     "The liquidity position must be above zero at the end of every bucket, in the base case and in every stress scenario. A "
     "breach is reported to ALCO the same day.", 0, "GBP"),
    ("TP-13", "Limit", "Negative base-case gap",
     "A negative base-case net gap in any bucket is reported to ALCO with its cause, even if the liquidity position stays above "
     "zero.", 0, "GBP"),
    ("TP-14", "Limit", "Maturities on one day",
     "Wholesale funding maturities from counterparties outside the group falling due on any one day must not exceed "
     "£150,000,000 in the base case, measured on amount_gbp. Intra-group deposits are left out.", DAILY_LIMIT, "GBP"),
    ("TP-15", "Limit", "Concentration by counterparty group",
     "No concentration group may account for more than 25% of the wholesale funding maturities from counterparties outside "
     "the group in the horizon, measured on amount_gbp in the base case.", GROUP_LIMIT_PCT, "percent"),
    ("TP-16", "Definition", "Wholesale funding",
     "Wholesale funding is borrowing in funding_instruments: term deposits, certificates of deposit, repos and senior notes. "
     "Its maturities are cashflows of flow type Wholesale funding maturity.", None, None),
]

RULES = [
    ("R-01", "Process", "Daily forecast",
     "The forecasting system takes flows from the treasury dealing system, the lending and deposit platforms, and the business "
     "units' forecasts. The base-case run starts at 17:30 each working day, BASE-yyyymmdd. Deals booked after 17:30 and before "
     "17:50 are loaded by an adjustment run at 17:50, BASE-yyyymmdd-ADJ, which is part of the base case."),
    ("R-02", "Process", "Stress runs",
     "The Asset and Liability Manager runs each stress scenario in the same forecasting system after the base run, as "
     "STnn-yyyymmdd. Stress runs are for the stress ladders only and are kept apart from the base case."),
    ("R-03", "Process", "Business unit forecasts",
     "Retail Banking, Business Banking and Finance submit their forecasts by the 25th of each month. A flow with no signed "
     "contract is submitted as Unconfirmed. The Liquidity Forecasting Analyst loads them."),
    ("R-04", "Process", "Exchange rates",
     "The dealing system captures spot rates at 16:00 London time each working day. The base run converts every USD and EUR "
     "flow at the day's rate."),
    ("R-05", "Authority", "Dealing",
     "Only dealers may agree wholesale deals, each within the dealing limit in staff. Deals above £250,000,000 need ALCO's "
     "approval."),
    ("R-06", "Authority", "Review and reporting",
     "The Asset and Liability Manager reviews the ladder each day. The Head of Treasury signs it off for ALCO, which the Chief "
     "Financial Officer chairs and which meets on the first Tuesday of each month. The Liquidity Risk Manager sets the stress "
     "assumptions and reviews the stress results independently of Treasury."),
    ("R-07", "Process", "What the ladder is for",
     "The ladder is the bank's internal measure of liquidity. It is not a regulatory return: the liquidity coverage ratio and "
     "net stable funding ratio are calculated separately, on different definitions."),
]
RULE_TABLES = {"R-01": "cashflows, funding_instruments", "R-02": "cashflows, stress_scenarios", "R-03": "cashflows",
               "R-04": "fx_rates, cashflows", "R-05": "funding_instruments, staff", "R-06": "staff, treasury_policy",
               "R-07": "treasury_policy"}

# Spot rates at month ends, and on 30 September (the as-at date); September's other days are filled in by build().
MONTH_END_RATES = {"USD": {D(2026, 6, 30): 1.3685, D(2026, 7, 31): 1.3592, D(2026, 8, 28): 1.3517, D(2026, 9, 30): 1.3406},
                   "EUR": {D(2026, 6, 30): 1.1781, D(2026, 7, 31): 1.1702, D(2026, 8, 28): 1.1611, D(2026, 9, 30): 1.1452}}

# ------------------------------------------------------------------ helpers

money = ladder.money
iso = ladder.iso


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    last = (D(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
    return D(y, m, min(d.day, last))


def prev_working_day(d):
    while not uk.is_working_day(d):
        d -= dt.timedelta(days=1)
    return d


def long(d):
    return d.strftime("%-d %B %Y")


def gbp(x):
    return f"£{x:,.2f}"


def gbp0(x):
    return f"£{x:,.0f}"


class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.rows = defaultdict(list)
        self.cases, self.case_records = [], []
        self.instruments = []  # dicts before numbering
        self.flows = []
        self.K = {}

    def case(self, cid, title, ctype, cls, sev, rules, types, expl, step, sql, records):
        self.cases.append({"case_id": cid, "title": title, "case_type": ctype, "classification": cls,
                           "severity": sev, "rules_involved": rules, "explanation": expl,
                           "expected_next_step": step, "appraisal_types": types, "detection_sql": " ".join(sql.split())})
        for table, rec, role, key in records:
            n = len(self.case_records) + 1
            self.case_records.append({"case_record_id": f"CR-{n:03d}", "case_id": cid, "table_name": table,
                                      "record_id": rec, "role_in_case": role, "is_key_record": int(key)})

    # ---- reference data

    def lookups(self):
        for sid, rid in STAFF_REGISTER_IDS.items():
            p = staff_register.person(rid)
            self.rows["staff"].append({
                "staff_id": sid, "first_name": p["first_name"], "last_name": p["last_name"], "job_title": p["job_title"],
                "team": TEAM.get(p["job_title"], "Treasury"), "office": p["office"],
                "dealing_limit_gbp": float(DEALING_LIMIT[p["job_title"]]) if p["job_title"] in DEALING_LIMIT else None,
                "email": email_for(p["first_name"], p["last_name"], firm.EMAIL_DOMAIN)})
        self.rows["treasury_policy"] = [dict(zip(["policy_id", "category", "title", "statement", "threshold", "unit"],
                                                 (p[0], p[1], p[2], p[3], None if p[4] is None else float(p[4]), p[5])))
                                        for p in POLICY]
        for bid, name, lo, hi in ladder.BUCKETS:
            self.rows["liquidity_buckets"].append({
                "bucket_id": bid, "bucket_name": name, "from_day": lo, "to_day": hi,
                "start_date": iso(AS_AT + dt.timedelta(days=lo)), "end_date": iso(AS_AT + dt.timedelta(days=hi)),
                "allocation_rule": BUCKET_RULE})
        for cid, typ, desc, rating, grp, country in COUNTERPARTIES:
            self.rows["counterparties"].append({
                "counterparty_id": cid, "counterparty_type": typ, "description": desc, "credit_rating": rating,
                "concentration_group": grp, "country": country, "intra_group": "Yes" if typ == "Intra-group" else "No"})
        for aid, cls, desc, mv, h in LIQUID_ASSETS:
            self.rows["liquid_assets"].append({"asset_id": aid, "asset_class": cls, "description": desc, "currency": "GBP",
                                               "market_value_gbp": float(mv), "base_haircut_pct": h})
        n = 0
        for sid, name, params in SCENARIOS:
            for typ, to, pct, words in params:
                n += 1
                self.rows["stress_scenarios"].append({"parameter_id": f"SP-{n:02d}", "scenario_id": sid, "scenario_name": name,
                                                      "parameter_type": typ, "applies_to": to, "shock_pct": pct,
                                                      "description": words})
        self.fx_rates()

    def fx_rates(self):
        """Month-end rates for June to August, and every working day from 17 to 30 September."""
        rng = self.rng
        sept = [d for d in (D(2026, 9, 17) + dt.timedelta(days=i) for i in range(14)) if uk.is_working_day(d)]
        for ccy, ends in MONTH_END_RATES.items():
            series = dict(ends)
            r = ends[D(2026, 9, 30)]
            for d in reversed(sept[:-1]):
                r = round(r * (1 + rng.uniform(-0.0035, 0.0045)), 4)
                series[d] = r
            for d in sorted(series):
                self.rows["fx_rates"].append({
                    "fx_rate_id": f"FX-{ccy}-{d:%Y%m%d}", "valuation_date": iso(d), "base_currency": "GBP",
                    "quote_currency": ccy, "rate": series[d], "rate_type": "Spot",
                    "source": "Treasury dealing system, 16:00 London"})
        self.rates = {(r["quote_currency"], r["valuation_date"]): r for r in self.rows["fx_rates"]}

    # ---- funding instruments

    def instrument(self, cp, itype, ccy, principal, start, maturity, rate=None, *, deal=None, booked=None, status="Executed",
                   dealer=None, terms=None, collateral=None, rollover_of=None, key=None, flow="maturity"):
        rng = self.rng
        if rate is None:
            months = max(1, round((maturity - start).days / 30.4))
            base = {"GBP": 3.72, "USD": 4.05, "EUR": 1.98}[ccy]
            rate = round(base + 0.035 * min(months, 12) + rng.uniform(-0.06, 0.06), 3)
        if deal is None:
            deal = start if ccy == "GBP" else prev_working_day(start - dt.timedelta(days=2))
            while not uk.is_working_day(deal):
                deal -= dt.timedelta(days=1)
        if booked is None:
            booked = dt.datetime.combine(deal, dt.time(rng.randint(8, 15), rng.randint(0, 59)))
        if dealer is None:
            dealer = SENIOR_DEALER if principal / self.spot(ccy) > 50_000_000 or rng.random() < 0.4 else DEALER
        if collateral is None:
            collateral = (f"UK gilts, market value {gbp0(round(principal * 1.02, -5))} (2% haircut)"
                          if itype == "Repo (gilt collateral)" else "Unsecured")
        if terms is None:
            terms = {"Term deposit": "Fixed-term deposit. Principal and interest repaid at maturity. No early withdrawal.",
                     "Certificate of deposit": "Sterling certificate of deposit issued at par. Principal and interest paid at maturity.",
                     "Repo (gilt collateral)": "Sale and repurchase of gilts under the GMRA. Repurchase price = principal plus interest.",
                     }[itype]
        basis = "ACT/365" if ccy == "GBP" else "ACT/360"
        inst = {"counterparty_id": cp, "instrument_type": itype, "deal_status": status, "deal_date": deal, "booked_at": booked,
                "start_date": start, "maturity_date": maturity, "currency": ccy, "principal": float(principal),
                "interest_rate_pct": rate, "day_count_basis": basis, "collateral": collateral, "terms": terms,
                "business_day_convention": "Modified following", "rollover_of": rollover_of, "dealer_id": dealer, "flow": flow}
        inst["payment_date"] = ladder.modified_following(maturity)
        inst["interest_at_maturity"] = ladder.interest(principal, rate, start, inst["payment_date"], basis)
        self.instruments.append(inst)
        if key:
            self.K[key] = inst
        return inst

    def spot(self, ccy, when=AS_AT):
        return 1.0 if ccy == "GBP" else self.rates[(ccy, iso(when))]["rate"]

    # ---- flows

    def flow(self, cp, ftype, unit, direction, ccy, nominal, due, *, expected=None, status="Confirmed", inst=None,
             run=BASE_RUN, by=ANALYST, entered=None, notes=None, rate_date=AS_AT, key=None):
        nominal = money(nominal)
        rate = None if ccy == "GBP" else self.rates[(ccy, iso(rate_date))]
        f = {"counterparty_id": cp, "inst": inst, "flow_type": ftype, "business_unit": unit, "direction": direction,
             "currency": ccy, "nominal": float(nominal), "fx_rate_id": rate["fx_rate_id"] if rate else None,
             "amount_gbp": float(nominal if rate is None else ladder.convert(nominal, rate["rate"])),
             "due_date": due, "expected_date": expected or due, "contract_status": status, "forecast_run": run,
             "entered_by": by, "entered_date": entered or AS_AT, "notes": notes}
        self.flows.append(f)
        if key:
            self.K[key] = f
        return f

    def maturity_flow(self, inst, **kw):
        amount = money(inst["principal"]) + inst["interest_at_maturity"]
        return self.flow(inst["counterparty_id"], "Wholesale funding maturity", "Treasury", "Outflow", inst["currency"], amount,
                         kw.pop("due", inst["payment_date"]), inst=inst, entered=kw.pop("entered", inst["deal_date"]), **kw)

    # ---- normal data

    def wholesale(self):
        """Funding maturing in the horizon. Planted dates (19 November, 2 December, 30 and 31 October, 30 November) are kept
        free of random deals, and no other day comes near the daily limit."""
        rng = self.rng
        reserved = {D(2026, 11, 19), D(2026, 12, 2), D(2026, 10, 30), D(2026, 11, 2), D(2026, 11, 30), D(2026, 10, 15),
                    D(2026, 10, 22), D(2026, 12, 16), D(2026, 11, 11), D(2026, 12, 24)}
        days = [d for d in (H_START + dt.timedelta(days=i) for i in range(92)) if uk.is_working_day(d) and d not in reserved]
        plan = [  # counterparty, type, currency, (min, max) principal in millions, tenor months
            ("CP-0001", "Repo (gilt collateral)", "GBP", (30, 55), 3), ("CP-0002", "Term deposit", "GBP", (25, 45), 6),
            ("CP-0005", "Term deposit", "EUR", (20, 30), 3), ("CP-0006", "Term deposit", "EUR", (15, 25), 6),
            ("CP-0007", "Repo (gilt collateral)", "GBP", (20, 40), 1), ("CP-0008", "Term deposit", "USD", (20, 30), 3),
            ("CP-0010", "Term deposit", "USD", (15, 25), 6), ("CP-0011", "Certificate of deposit", "GBP", (20, 35), 6),
            ("CP-0012", "Term deposit", "GBP", (20, 35), 3), ("CP-0014", "Term deposit", "GBP", (15, 25), 12),
            ("CP-0015", "Certificate of deposit", "GBP", (15, 25), 3), ("CP-0016", "Certificate of deposit", "GBP", (10, 20), 1),
            ("CP-0018", "Certificate of deposit", "GBP", (10, 20), 6), ("CP-0020", "Term deposit", "GBP", (10, 25), 3),
            ("CP-0021", "Term deposit", "GBP", (10, 20), 6), ("CP-0024", "Term deposit", "GBP", (10, 20), 12),
        ]
        for cp, itype, ccy, (lo, hi), tenor in plan:
            for _ in range(200):
                mat = rng.choice(days)
                start = add_months(mat, -tenor)
                if uk.is_working_day(start) and start <= AS_AT - dt.timedelta(days=5):
                    break
            else:
                raise RuntimeError(f"no start date for {cp}")
            days.remove(mat)
            amount = rng.randint(lo, hi) * 1_000_000
            inst = self.instrument(cp, itype, ccy, amount, start, mat)
            self.maturity_flow(inst)
        self.maturity_flow(self.instrument("CP-0018", "Certificate of deposit", "GBP", 15_000_000, D(2026, 9, 1), D(2026, 10, 1)))
        # Funding that matures after the horizon: shown in funding_instruments only.
        for cp, itype, ccy, amt, start, tenor in [
                ("CP-0009", "Term deposit", "GBP", 40_000_000, D(2026, 7, 15), 12), ("CP-0013", "Certificate of deposit", "GBP", 25_000_000, D(2026, 9, 1), 6),
                ("CP-0004", "Term deposit", "EUR", 30_000_000, D(2026, 9, 14), 6), ("CP-0019", "Term deposit", "GBP", 20_000_000, D(2026, 9, 24), 6)]:
            self.instrument(cp, itype, ccy, amt, start, ladder.modified_following(add_months(start, tenor)), flow=None)
        # The bank's senior note pays a coupon in the horizon.
        note = self.instrument("CP-0029", "Senior unsecured note", "GBP", 300_000_000, D(2023, 5, 18), D(2028, 5, 18), 5.375,
                               deal=D(2023, 5, 11), booked=dt.datetime(2023, 5, 11, 14, 5), dealer=HEAD,
                               terms="£300,000,000 5.375% senior unsecured notes due 18 May 2028, listed in London. Fixed coupon paid "
                                     "half-yearly on 18 May and 18 November: principal x 5.375% / 2. Issued with ALCO's approval.", flow=None)
        note["interest_at_maturity"] = None
        note["day_count_basis"] = "Semi-annual coupon"
        self.flow("CP-0029", "Bond coupon", "Treasury", "Outflow", "GBP", 300_000_000 * 0.05375 / 2, D(2026, 11, 18), inst=note,
                  entered=D(2023, 5, 11))
        # A dollar deposit taken in July and swapped into sterling; the swap's far leg repays it in dollars.
        usd = self.instrument("CP-0017", "Term deposit", "USD", 30_000_000, D(2026, 7, 16), D(2026, 12, 16), 4.21,
                              deal=D(2026, 7, 14), dealer=SENIOR_DEALER)
        self.maturity_flow(usd)

    def placements(self):
        """Money the bank has lent: placements and reverse repos maturing in the horizon. Not funding, so no instrument."""
        rng = self.rng
        for cp, ftype, ccy, lo, hi, due in [
                ("CP-0002", "Placement maturity", "GBP", 25, 45, D(2026, 10, 1)), ("CP-0009", "Placement maturity", "GBP", 20, 40, D(2026, 10, 9)),
                ("CP-0006", "Placement maturity", "EUR", 10, 20, D(2026, 10, 20)), ("CP-0012", "Placement maturity", "GBP", 20, 35, D(2026, 10, 28)),
                ("CP-0001", "Placement maturity", "GBP", 25, 40, D(2026, 11, 9)), ("CP-0010", "Placement maturity", "USD", 10, 20, D(2026, 11, 24)),
                ("CP-0013", "Placement maturity", "GBP", 20, 30, D(2026, 12, 8)), ("CP-0007", "Placement maturity", "GBP", 15, 30, D(2026, 12, 21)),
                ("CP-0003", "Reverse repo maturity", "GBP", 30, 50, D(2026, 10, 6)), ("CP-0011", "Reverse repo maturity", "GBP", 20, 40, D(2026, 11, 3)),
                ("CP-0005", "Reverse repo maturity", "GBP", 25, 40, D(2026, 12, 10))]:
            start = add_months(due, -rng.choice([3, 6]))
            principal = rng.randint(lo, hi) * 1_000_000
            rate = {"GBP": 3.85, "USD": 4.15, "EUR": 2.05}[ccy] + rng.uniform(-0.1, 0.1)
            amount = principal + float(ladder.interest(principal, round(rate, 3), start, due, "ACT/365" if ccy == "GBP" else "ACT/360"))
            self.flow(cp, ftype, "Treasury", "Inflow", ccy, amount, due, entered=prev_working_day(start),
                      notes=f"{'Placed' if ftype == 'Placement maturity' else 'Lent against gilts'} on {long(prev_working_day(start))} at {rate:.3f}%")
        for due, amt in [(D(2026, 10, 22), 2_418_750), (D(2026, 12, 7), 3_356_250)]:
            self.flow("CP-0027", "Gilt coupon", "Treasury", "Inflow", "GBP", amt, due, entered=D(2026, 9, 1))

    def business_units(self):
        rng = self.rng
        sub = D(2026, 9, 25)
        fridays = [prev_working_day(D(2026, 10, 2) + dt.timedelta(weeks=i)) for i in range(13)]
        self.retail = {}
        for d in fridays:
            amt = rng.randint(85, 135) * 100_000 + (40 * 100_000 if d.month == 12 else 0)
            self.retail[d] = self.flow("CP-0031", "Retail deposit outflow", "Retail Banking", "Outflow", "GBP", amt, d,
                                       status="Behavioural", entered=sub)
        for d in [D(2026, 10, 7), D(2026, 10, 21), D(2026, 11, 4), D(2026, 11, 18), D(2026, 12, 2), D(2026, 12, 16)]:
            self.flow("CP-0032", "Business deposit outflow", "Business Banking", "Outflow", "GBP", rng.randint(14, 24) * 1_000_000, d,
                      status="Behavioural", entered=sub)
        for d in [D(2026, 10, 15), D(2026, 11, 16), D(2026, 12, 15)]:
            self.flow("CP-0034", "Committed facility drawdown", "Business Banking", "Outflow", "GBP", rng.randint(70, 110) * 100_000, d,
                      status="Behavioural", entered=sub)
        for d in [D(2026, 10, 30), D(2026, 11, 27), D(2026, 12, 18)]:
            self.flow("CP-0033", "New lending drawdown", "Retail Banking", "Outflow", "GBP", rng.randint(42, 58) * 1_000_000, d,
                      status="Behavioural", entered=sub, notes="Mortgage completions forecast for the month")
        for d in [D(2026, 10, 13), D(2026, 11, 12), D(2026, 12, 10)]:
            self.flow("CP-0034", "New lending drawdown", "Business Banking", "Outflow", "GBP", rng.randint(9, 16) * 1_000_000, d,
                      entered=sub, notes="Business loans sanctioned and accepted, drawdown date agreed")
        for d in [D(2026, 10, 26), D(2026, 11, 26), D(2026, 12, 18)]:
            self.flow("CP-0035", "Payroll", "Finance", "Outflow", "GBP", rng.randint(940, 990) * 10_000, d, entered=sub)
        for d in [D(2026, 10, 22), D(2026, 11, 20), D(2026, 12, 22)]:
            self.flow("CP-0028", "PAYE and National Insurance", "Finance", "Outflow", "GBP", rng.randint(400, 440) * 10_000, d, entered=sub)
        for d, exp in [(D(2026, 10, 30), None), (D(2026, 11, 27), D(2026, 12, 1)), (D(2026, 12, 31), None)]:
            self.flow("CP-0036", "Supplier payments", "Finance", "Outflow", "GBP", rng.randint(55, 70) * 100_000, d, expected=exp,
                      entered=sub, notes="Planned for 1 December, after the payment run" if exp else None)
        self.flow("CP-0028", "Corporation tax", "Finance", "Outflow", "GBP", 12_400_000, D(2026, 10, 14), entered=sub,
                  notes="Quarterly instalment payment")
        self.flow("CP-0026", "Dividend to parent", "Finance", "Outflow", "GBP", 35_000_000, D(2026, 11, 25), entered=sub,
                  notes="Interim dividend declared by the board on 15 September 2026")
        # Inflows from customers. Some business borrowers pay late, so their expected date is later.
        for d in [D(2026, 10, 1), D(2026, 11, 2), D(2026, 12, 1)]:
            self.flow("CP-0033", "Customer loan repayment", "Retail Banking", "Inflow", "GBP", rng.randint(46, 54) * 1_000_000, d, entered=sub)
        for d, exp in [(D(2026, 10, 29), D(2026, 11, 3)), (D(2026, 11, 30), None), (D(2026, 12, 30), None)]:
            self.flow("CP-0034", "Customer loan repayment", "Business Banking", "Inflow", "GBP", rng.randint(120, 160) * 100_000, d,
                      expected=exp, entered=sub, notes="Some borrowers pay a few days late" if exp else None)
        self.flow("CP-0030", "Asset sale proceeds", "Treasury", "Inflow", "GBP", 150_000_000, D(2026, 12, 15), status="Unconfirmed",
                  entered=sub, notes="Sale of a tranche of buy-to-let mortgages. Bids due 6 November; no buyer chosen")
        ti = self.instrument("CP-0025", "Term deposit", "GBP", 25_000_000, D(2026, 11, 2), D(2027, 5, 4), 3.95, deal=D(2026, 9, 21),
                             booked=dt.datetime(2026, 9, 21, 11, 20), status="Agreed in principle, not signed", dealer=DEALER, flow=None)
        self.flow("CP-0025", "New wholesale funding", "Treasury", "Inflow", "GBP", 25_000_000, D(2026, 11, 2), status="Unconfirmed",
                  inst=ti, entered=D(2026, 9, 21), notes="Thameside Insurance plans to place cash from a bond maturity")

    # ---- planted cases

    def planted(self):
        rng = self.rng
        # Maturities bunched on Thursday 19 November: three-month deals taken on 19 August.
        self.K["bunched"] = []
        for cp, itype, amt in [("CP-0002", "Term deposit", 50), ("CP-0009", "Term deposit", 45), ("CP-0016", "Certificate of deposit", 35),
                               ("CP-0019", "Term deposit", 25), ("CP-0023", "Term deposit", 20)]:
            inst = self.instrument(cp, itype, "GBP", amt * 1_000_000, D(2026, 8, 19), D(2026, 11, 19))
            self.K["bunched"].append(self.maturity_flow(inst))
        # Wednesday 2 December: large, but a quarter of it is an intra-group deposit.
        self.K["two_dec"] = []
        for cp, itype, amt, start in [("CP-0001", "Term deposit", 60, D(2026, 6, 2)), ("CP-0014", "Certificate of deposit", 35, D(2026, 9, 2)),
                                      ("CP-0020", "Term deposit", 25, D(2026, 9, 2)), ("CP-0025", "Term deposit", 55, D(2026, 6, 2))]:
            inst = self.instrument(cp, itype, "GBP", amt * 1_000_000, start, D(2026, 12, 2))
            self.K["two_dec"].append(self.maturity_flow(inst))
        # Deals booked after the base run: two caught by the adjustment run, one booked after it.
        for cp, itype, ccy, amt, mat, t in [("CP-0015", "Certificate of deposit", "GBP", 20_000_000, D(2026, 11, 11), (17, 38)),
                                             ("CP-0012", "Term deposit", "USD", 25_000_000, D(2026, 11, 30), (17, 44))]:
            inst = self.instrument(cp, itype, ccy, amt, AS_AT, mat, deal=AS_AT if ccy == "GBP" else D(2026, 9, 28),
                                   booked=dt.datetime(2026, 9, 30, *t), dealer=DEALER)
            self.K.setdefault("adj", []).append(self.maturity_flow(inst, run=ADJ_RUN, entered=AS_AT))
        self.instrument("CP-0003", "Repo (gilt collateral)", "GBP", 60_000_000, AS_AT, D(2026, 11, 30), 3.88,
                        booked=dt.datetime(2026, 9, 30, 17, 58), dealer=SENIOR_DEALER, key="missing", flow=None)
        # A maturity on Friday 30 October recorded as due on Monday 2 November.
        inst = self.instrument("CP-0013", "Term deposit", "GBP", 40_000_000, D(2026, 7, 30), D(2026, 10, 30), key="wrong_date")
        self.K["wrong_date_flow"] = self.maturity_flow(inst, due=D(2026, 11, 2))
        # A maturity on Saturday 31 October paid on Friday 30 October under modified following.
        inst = self.instrument("CP-0021", "Term deposit", "GBP", 15_000_000, D(2026, 7, 31), D(2026, 10, 31), key="mod_following")
        self.K["mod_following_flow"] = self.maturity_flow(inst)
        # A rollover: the principal stays, only the interest is paid.
        old = self.instrument("CP-0024", "Term deposit", "GBP", 30_000_000, D(2026, 7, 15), D(2026, 10, 15), key="rolled")
        new = self.instrument("CP-0024", "Term deposit", "GBP", 30_000_000, D(2026, 10, 15), D(2027, 1, 15), 3.86,
                              deal=D(2026, 9, 25), booked=dt.datetime(2026, 9, 25, 10, 12), rollover_of=old, dealer=DEALER,
                              terms="Fixed-term deposit, rolling over the maturing deposit. Only the interest on the maturing deposit "
                                    "is paid on 15 October; the principal stays. No early withdrawal.", flow=None, key="rollover")
        self.K["rolled_flow"] = self.flow("CP-0024", "Wholesale funding interest", "Treasury", "Outflow", "GBP", old["interest_at_maturity"],
                                          D(2026, 10, 15), inst=old, entered=D(2026, 9, 25),
                                          notes="Interest only: the principal rolls into the new deposit")
        # A euro deposit maturing on 22 October, converted at the 30 June rate.
        inst = self.instrument("CP-0004", "Term deposit", "EUR", 40_000_000, D(2026, 7, 22), D(2026, 10, 22), 2.02,
                               deal=D(2026, 7, 20), dealer=SENIOR_DEALER, key="stale")
        self.K["stale_flow"] = self.maturity_flow(inst, rate_date=D(2026, 6, 30))
        # The FX swap's far leg: receive dollars, pay sterling fixed at the forward rate agreed in July.
        fwd = 1.3418
        self.K["swap_usd"] = self.flow("CP-0010", "FX swap far leg", "Treasury", "Inflow", "USD", 30_000_000, D(2026, 12, 16),
                                       entered=D(2026, 7, 14), notes="Far leg of FX swap FXS-2026-014, dealt 14 July 2026: receive USD")
        self.K["swap_gbp"] = self.flow("CP-0010", "FX swap far leg", "Treasury", "Outflow", "GBP", float(money(30_000_000 / fwd)), D(2026, 12, 16),
                                       entered=D(2026, 7, 14),
                                       notes=f"Far leg of FX swap FXS-2026-014, dealt 14 July 2026: pay GBP at the forward rate {fwd:.4f}")
        # New funding counted as confirmed although nothing is signed; and a signed forward-starting deposit.
        inst = self.instrument("CP-0022", "Term deposit", "GBP", 40_000_000, D(2026, 10, 14), D(2027, 4, 14), 4.02, deal=D(2026, 9, 24),
                               booked=dt.datetime(2026, 9, 24, 15, 40), status="Agreed in principle, not signed", dealer=DEALER,
                               flow=None, key="unsigned")
        self.K["unsigned_flow"] = self.flow("CP-0022", "New wholesale funding", "Treasury", "Inflow", "GBP", 40_000_000, D(2026, 10, 14),
                                            inst=inst, entered=D(2026, 9, 24))
        inst = self.instrument("CP-0008", "Term deposit", "GBP", 35_000_000, D(2026, 10, 8), D(2027, 4, 8), 3.98, deal=D(2026, 9, 29),
                               booked=dt.datetime(2026, 9, 29, 10, 25), dealer=SENIOR_DEALER, flow=None, key="forward")
        self.K["forward_flow"] = self.flow("CP-0008", "New wholesale funding", "Treasury", "Inflow", "GBP", 35_000_000, D(2026, 10, 8),
                                           inst=inst, entered=D(2026, 9, 29), notes="Forward-starting deposit, signed 29 September")
        # The Thameside-specific stress run's extra retail outflows, loaded into the base forecast.
        shock = next(p[2] for p in SCENARIOS[1][2] if p[1] == "Retail deposit outflow")
        self.K["stress"] = []
        for d in (D(2026, 10, 9), D(2026, 10, 16)):
            base = self.retail[d]
            self.K["stress"].append(self.flow("CP-0031", "Retail deposit outflow", "Retail Banking", "Outflow", "GBP",
                                              float(money(base["nominal"] * shock / 100)), d, status="Behavioural", run=STRESS_RUN,
                                              by=ALM, entered=D(2026, 9, 29)))

    # ---- numbering

    def finalise(self):
        for n, inst in enumerate(sorted(self.instruments, key=lambda i: i["booked_at"]), start=1):
            inst["instrument_id"] = f"FI-{n:04d}"
        for inst in sorted(self.instruments, key=lambda i: i["booked_at"]):
            self.rows["funding_instruments"].append({
                "instrument_id": inst["instrument_id"], "counterparty_id": inst["counterparty_id"],
                "instrument_type": inst["instrument_type"], "deal_status": inst["deal_status"], "deal_date": iso(inst["deal_date"]),
                "booked_at": inst["booked_at"].strftime("%Y-%m-%d %H:%M"), "start_date": iso(inst["start_date"]),
                "maturity_date": iso(inst["maturity_date"]), "currency": inst["currency"], "principal": inst["principal"],
                "interest_rate_pct": inst["interest_rate_pct"], "day_count_basis": inst["day_count_basis"],
                "interest_at_maturity": None if inst["interest_at_maturity"] is None else float(inst["interest_at_maturity"]),
                "collateral": inst["collateral"], "terms": inst["terms"], "business_day_convention": inst["business_day_convention"],
                "rollover_of_id": inst["rollover_of"]["instrument_id"] if inst["rollover_of"] else None, "dealer_id": inst["dealer_id"]})
        order = sorted(self.flows, key=lambda f: (f["due_date"], f["direction"] == "Inflow", f["flow_type"], -float(f["nominal"]), f["counterparty_id"]))
        for n, f in enumerate(order, start=1):
            f["cashflow_id"] = f"CF-{n:04d}"
            self.rows["cashflows"].append({
                "cashflow_id": f["cashflow_id"], "counterparty_id": f["counterparty_id"],
                "instrument_id": f["inst"]["instrument_id"] if f["inst"] else None, "flow_type": f["flow_type"],
                "business_unit": f["business_unit"], "direction": f["direction"], "currency": f["currency"],
                "nominal": float(f["nominal"]), "fx_rate_id": f["fx_rate_id"], "amount_gbp": float(f["amount_gbp"]),
                "due_date": iso(f["due_date"]), "expected_date": iso(f["expected_date"]), "contract_status": f["contract_status"],
                "forecast_run": f["forecast_run"], "entered_by": f["entered_by"], "entered_date": iso(f["entered_date"]),
                "notes": f["notes"]})


# ------------------------------------------------------------------ answer key


def record_cases(b):
    K = b.K
    rows = b.rows
    cid = lambda f: f["cashflow_id"]  # noqa: E731
    fid = lambda i: i["instrument_id"]  # noqa: E731
    THIRD_PARTY = """FROM cashflows c JOIN counterparties p ON p.counterparty_id = c.counterparty_id
                     WHERE c.flow_type = 'Wholesale funding maturity' AND c.forecast_run LIKE 'BASE-%'"""

    day = K["bunched"][0]["due_date"]
    total = sum(f["amount_gbp"] for f in K["bunched"])
    b.case("CASE-01", "Wholesale funding maturities bunched on one day, above the daily limit", "concentration_daily_limit_breached",
           "Genuine exception", "High", "TP-14, TP-13", "A5, A3, S1",
           f"{len(K['bunched'])} wholesale deals from {len(K['bunched'])} different counterparties all mature on {long(day)}: "
           + ", ".join(f"{cid(f)} {gbp(f['amount_gbp'])}" for f in K["bunched"])
           + f", {gbp(total)} in all. TP-14 allows £150,000,000 a day from counterparties outside the group. Each deal is within "
           f"limits on its own; together they breach. All were three-month deals taken on {long(K['bunched'][0]['inst']['start_date'])}. "
           "They all fall in bucket B5, which has the largest negative base-case net gap (TP-13).",
           "Report the breach to ALCO. Ask Treasury to spread the refinancing over several days, for example by extending some deals "
           "early, and set a check on maturity dates when deals are agreed.",
           f"""SELECT c.cashflow_id {THIRD_PARTY} AND p.intra_group = 'No' AND c.due_date IN
               (SELECT c2.due_date FROM cashflows c2 JOIN counterparties p2 ON p2.counterparty_id = c2.counterparty_id
                WHERE c2.flow_type = 'Wholesale funding maturity' AND c2.forecast_run LIKE 'BASE-%' AND p2.intra_group = 'No'
                GROUP BY c2.due_date HAVING sum(c2.amount_gbp) > {DAILY_LIMIT})""",
           [("cashflows", cid(f), "maturity on the bunched day", 1) for f in K["bunched"]]
           + [("funding_instruments", fid(f["inst"]), "deal taken on the same day", 0) for f in K["bunched"]])

    third = [f for f in K["two_dec"] if f["counterparty_id"] != "CP-0025"]
    intra = next(f for f in K["two_dec"] if f["counterparty_id"] == "CP-0025")
    t_all, t_third = sum(f["amount_gbp"] for f in K["two_dec"]), sum(f["amount_gbp"] for f in third)
    b.case("CASE-02", "Maturities above £150 million on one day, but within the limit once the intra-group deposit is left out",
           "concentration_intra_group_lookalike", "Benign lookalike", "None", "TP-14", "A5, A3",
           f"Wholesale maturities on {long(K['two_dec'][0]['due_date'])} total {gbp(t_all)}, above £150,000,000. But "
           f"{cid(intra)}, {gbp(intra['amount_gbp'])}, repays a deposit from Thameside Insurance, a company in the group, and TP-14 "
           f"leaves intra-group deposits out. The maturities from counterparties outside the group total {gbp(t_third)}, within the limit.",
           "No action.",
           f"""SELECT c.cashflow_id {THIRD_PARTY} AND c.due_date IN
               (SELECT c2.due_date FROM cashflows c2 JOIN counterparties p2 ON p2.counterparty_id = c2.counterparty_id
                WHERE c2.flow_type = 'Wholesale funding maturity' AND c2.forecast_run LIKE 'BASE-%' GROUP BY c2.due_date
                HAVING sum(c2.amount_gbp) > {DAILY_LIMIT} AND sum(CASE WHEN p2.intra_group = 'No' THEN c2.amount_gbp ELSE 0 END) <= {DAILY_LIMIT})""",
           [("cashflows", cid(f), "maturity on the day; intra-group" if f is intra else "maturity on the day", 1) for f in K["two_dec"]])

    m = K["missing"]
    adj = K["adj"]
    amount = m["principal"] + float(m["interest_at_maturity"])
    b.case("CASE-03", "A £60 million repo maturity missing from the forecast", "missing_outflow",
           "Genuine exception", "High", "TP-02, TP-06, R-01", "A1, A7, S1",
           f"Repo {fid(m)} with {m['counterparty_id']}, {gbp0(m['principal'])} at {m['interest_rate_pct']}%, was booked at "
           f"{m['booked_at']:%H:%M} on {long(AS_AT)} and matures on {long(m['payment_date'])}. No flow in cashflows refers to it. The "
           f"adjustment run at 17:50 loaded the deals booked at {adj[0]['inst']['booked_at']:%H:%M} and {adj[1]['inst']['booked_at']:%H:%M} "
           f"({cid(adj[0])}, {cid(adj[1])}); this one was booked after it. The repurchase payment of {gbp(amount)} (principal plus "
           f"interest of {gbp(float(m['interest_at_maturity']))}, TP-06) is missing from bucket B5, so the base-case outflows there "
           "are understated by that amount.",
           "Add the repurchase to the forecast and restate the ladder. Ask why deals booked after the adjustment run are not picked "
           "up the next day.",
           f"""SELECT f.instrument_id FROM funding_instruments f WHERE f.deal_status = 'Executed' AND f.start_date <= '{iso(AS_AT)}'
               AND f.maturity_date BETWEEN '{iso(H_START)}' AND '{iso(H_END)}'
               AND NOT EXISTS (SELECT 1 FROM cashflows c WHERE c.instrument_id = f.instrument_id)""",
           [("funding_instruments", fid(m), "maturity with no flow in the forecast", 1)])

    old, new, fl = K["rolled"], K["rollover"], K["rolled_flow"]
    b.case("CASE-04", "Deposit maturing in the horizon with only its interest in the forecast, because it rolls over",
           "rollover_lookalike", "Benign lookalike", "None", "TP-06", "A1, A7",
           f"Deposit {fid(old)} for {gbp0(old['principal'])} matures on {long(old['payment_date'])}, but the forecast has only "
           f"{cid(fl)}, an interest payment of {gbp(fl['amount_gbp'])}. That is right: {fid(new)}, signed on {long(new['deal_date'])}, "
           f"rolls the same {gbp0(new['principal'])} over with the same counterparty from the same day (rollover_of_id). TP-06 says a "
           "rollover settles only the interest.",
           "No action.",
           f"""SELECT f.instrument_id FROM funding_instruments f WHERE f.maturity_date BETWEEN '{iso(H_START)}' AND '{iso(H_END)}'
               AND EXISTS (SELECT 1 FROM cashflows c WHERE c.instrument_id = f.instrument_id)
               AND NOT EXISTS (SELECT 1 FROM cashflows c WHERE c.instrument_id = f.instrument_id AND c.flow_type = 'Wholesale funding maturity')
               AND f.instrument_type <> 'Senior unsecured note'""",
           [("funding_instruments", fid(old), "maturity rolled over", 1), ("funding_instruments", fid(new), "the rollover deal", 0),
            ("cashflows", cid(fl), "interest only", 0)])

    s = K["stale_flow"]
    spot = b.spot("EUR")
    right = float(ladder.convert(s["nominal"], spot))
    b.case("CASE-05", "Euro maturity converted at the 30 June rate instead of the 30 September rate", "stale_fx_rate",
           "Genuine exception", "Medium", "TP-05, R-04", "S1, A3, A7",
           f"{cid(s)} repays euro deposit {fid(s['inst'])}: €{s['nominal']:,.2f} on {long(s['due_date'])}. It is converted with "
           f"{s['fx_rate_id']}, the rate of {MONTH_END_RATES['EUR'][D(2026, 6, 30)]:.4f} captured on 30 June 2026, three months before "
           f"the as-at date and before the deal was agreed. TP-05 requires the 30 September rate, {spot:.4f}: "
           f"€{s['nominal']:,.2f} / {spot:.4f} = {gbp(right)}, not {gbp(s['amount_gbp'])}. Sterling has fallen since June, so the "
           f"outflow is understated by {gbp(right - s['amount_gbp'])} in bucket B4.",
           "Convert the flow at the 30 September rate and restate the ladder. Find out why the run kept the old rate for this flow.",
           f"""SELECT c.cashflow_id FROM cashflows c JOIN fx_rates r ON r.fx_rate_id = c.fx_rate_id WHERE r.valuation_date <> '{iso(AS_AT)}'""",
           [("cashflows", cid(s), "converted at a stale rate", 1), ("fx_rates", s["fx_rate_id"], "the 30 June rate used", 0),
            ("fx_rates", f"FX-EUR-{AS_AT:%Y%m%d}", "the rate TP-05 requires", 0)])

    g, u = K["swap_gbp"], K["swap_usd"]
    b.case("CASE-06", "Sterling leg of an FX swap fixed at a July forward rate", "fx_contract_rate_lookalike",
           "Benign lookalike", "None", "TP-05", "S1, A3",
           f"{cid(g)} pays {gbp(g['amount_gbp'])} on {long(g['due_date'])}; its notes give a rate of 1.3418 agreed on 14 July, far "
           f"from the 30 September spot rate of {b.spot('USD'):.4f}. It is not a conversion. The amount is the sterling leg of an FX "
           f"swap, fixed by contract, so TP-05 treats it as a sterling flow. The dollar leg, {cid(u)}, is converted at the 30 "
           "September rate, as it should be.",
           "No action.",
           """SELECT cashflow_id FROM cashflows WHERE flow_type = 'FX swap far leg' AND currency = 'GBP'""",
           [("cashflows", cid(g), "sterling amount fixed by the swap", 1), ("cashflows", cid(u), "dollar leg, converted at spot", 0)])

    f = K["unsigned_flow"]
    b.case("CASE-07", "£40 million of new funding counted as confirmed, though nothing is signed", "unconfirmed_inflow_counted",
           "Genuine exception", "High", "TP-02", "A1, A3",
           f"{cid(f)} is a £40,000,000 inflow on {long(f['due_date'])} from a new deposit, {fid(f['inst'])}, from "
           f"{f['counterparty_id']}, a property group. Its contract_status is Confirmed, so it counts in the base case. But the "
           f"instrument's deal_status is '{f['inst']['deal_status']}'. TP-02 says an inflow from an instrument is Confirmed only when "
           "the deal is Executed, and Unconfirmed inflows are left out. The base-case inflows in bucket "
           f"{ladder.bucket_of(f['expected_date'])} are overstated by £40,000,000.",
           "Set the flow to Unconfirmed and restate the ladder. Count it again only when the deposit agreement is signed.",
           """SELECT c.cashflow_id FROM cashflows c JOIN funding_instruments f ON f.instrument_id = c.instrument_id
              WHERE c.direction = 'Inflow' AND c.contract_status = 'Confirmed' AND f.deal_status <> 'Executed'""",
           [("cashflows", cid(f), "counted as confirmed", 1), ("funding_instruments", fid(f["inst"]), "not signed", 0)])

    f = K["forward_flow"]
    b.case("CASE-08", "New funding not yet received, counted as confirmed because the deal is signed", "forward_start_lookalike",
           "Benign lookalike", "None", "TP-02", "A1, A3, A7",
           f"{cid(f)} is a £35,000,000 inflow on {long(f['due_date'])} from deposit {fid(f['inst'])}, which starts after the as-at "
           f"date. It looks like hoped-for funding, but the deal was signed on {long(f['inst']['deal_date'])} and its deal_status is "
           "Executed. It is a forward-starting deposit, so Confirmed is right and the inflow belongs in the base case. Stress scenarios "
           "ST-02 and ST-03 remove it (Inflow reduction on New wholesale funding).",
           "No action.",
           """SELECT c.cashflow_id FROM cashflows c JOIN funding_instruments f ON f.instrument_id = c.instrument_id
              WHERE c.flow_type = 'New wholesale funding' AND c.contract_status = 'Confirmed' AND f.deal_status = 'Executed'""",
           [("cashflows", cid(f), "signed forward-starting deposit", 1), ("funding_instruments", fid(f["inst"]), "executed deal", 0)])

    f, i = K["wrong_date_flow"], K["wrong_date"]
    b.case("CASE-09", "Maturity due on 30 October recorded as 2 November, moving it out of the one-month bucket",
           "wrong_date_bucket", "Genuine exception", "Medium", "TP-04, TP-06", "A1, A7, S1",
           f"Deposit {fid(i)} matures on {i['maturity_date']:%A} {long(i['maturity_date'])}, a working day, so its payment date is the "
           f"same day (TP-06). {cid(f)} records the repayment of {gbp(f['amount_gbp'])} as due on {long(f['due_date'])}. 30 October "
           "is day 30, in bucket B4 (15 days to 1 month); 2 November is day 33, in B5. The amount is right: interest runs to 30 "
           "October. The one-month outflows are understated, and B5's overstated, by the same amount.",
           "Correct the due date to 30 October and restate both buckets.",
           """SELECT c.cashflow_id FROM cashflows c JOIN funding_instruments f ON f.instrument_id = c.instrument_id
              WHERE c.flow_type = 'Wholesale funding maturity' AND c.due_date <> f.maturity_date
              AND strftime('%w', f.maturity_date) NOT IN ('0', '6')""",
           [("cashflows", cid(f), "due date wrong", 1), ("funding_instruments", fid(i), "maturity date", 0)])

    f, i = K["mod_following_flow"], K["mod_following"]
    b.case("CASE-10", "Maturity recorded a day before its maturity date, correctly, under modified following",
           "business_day_lookalike", "Benign lookalike", "None", "TP-06, TP-04", "A7, A3, S1",
           f"Deposit {fid(i)} matures on Saturday {long(i['maturity_date'])}, but {cid(f)} is due on Friday {long(f['due_date'])}. "
           "Under modified following, a Saturday maturity moves to the next working day, Monday 2 November, unless that is in the next "
           "month; it is, so the payment moves back to Friday 30 October. The date is right, the flow stays in bucket B4, and "
           f"interest runs to 30 October: {gbp(float(i['interest_at_maturity']))}.",
           "No action.",
           """SELECT c.cashflow_id FROM cashflows c JOIN funding_instruments f ON f.instrument_id = c.instrument_id
              WHERE c.flow_type = 'Wholesale funding maturity' AND c.due_date <> f.maturity_date
              AND strftime('%w', f.maturity_date) IN ('0', '6')""",
           [("cashflows", cid(f), "date moved under the convention", 1), ("funding_instruments", fid(i), "maturity on a Saturday", 0)])

    st = K["stress"]
    b.case("CASE-11", "Stress-run outflows loaded into the base-case forecast", "stress_mixed_into_base",
           "Genuine exception", "High", "TP-02, TP-11, R-02", "A10, S1",
           f"{cid(st[0])} and {cid(st[1])} are retail deposit outflows of {gbp(st[0]['amount_gbp'])} and {gbp(st[1]['amount_gbp'])}, "
           f"loaded by run {STRESS_RUN}, the Thameside-specific stress run of 29 September, not by a base run. Each is exactly 150% of "
           f"the base forecast for the same week ({cid(b.retail[st[0]['due_date']])} and {cid(b.retail[st[1]['due_date']])}): "
           "the extra run-off ST-02 assumes. TP-02 keeps stress-run flows out of the base case. Left in, they overstate base-case "
           f"outflows in bucket B3 and B4 by {gbp(st[0]['amount_gbp'] + st[1]['amount_gbp'])}; and when ST-02 is applied to the "
           "forecast, those weeks are stressed twice.",
           "Remove the two flows from the base case and restate the base and stress ladders. Keep stress runs from writing to the base forecast.",
           """SELECT cashflow_id FROM cashflows WHERE forecast_run NOT LIKE 'BASE-%'""",
           [("cashflows", cid(f), "stress-run flow in the base case", 1) for f in st]
           + [("cashflows", cid(b.retail[f["due_date"]]), "base forecast for the same week", 0) for f in st])

    b.case("CASE-12", "Flows from a different forecast run that are part of the base case", "adjustment_run_lookalike",
           "Benign lookalike", "None", "TP-02, R-01", "A10, A8",
           f"{cid(adj[0])} and {cid(adj[1])} were loaded by run {ADJ_RUN}, not by the main run. They are deals booked between 17:30 and "
           "17:50 on 30 September, which R-01 sends to the adjustment run. The run's name begins BASE-, so TP-02 counts them in the "
           "base case. They are not stress figures.",
           "No action.",
           f"""SELECT cashflow_id FROM cashflows WHERE forecast_run LIKE 'BASE-%' AND forecast_run <> '{BASE_RUN}'""",
           [("cashflows", cid(f), "adjustment-run flow", 1) for f in adj])


# ------------------------------------------------------------------ business story

NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
                11: "eleven", 12: "twelve"}


def business_story(rows):
    """The firm's current situation. Paragraphs are separated by blank lines; lines starting '- ' are list items.
    Every figure is calculated from the rows, and checks() tests every claim against the data."""
    flows = [f for f in rows["cashflows"] if f["forecast_run"].startswith("BASE-")]
    retail = sum(f["amount_gbp"] for f in flows if f["flow_type"] == "Retail deposit outflow")
    lending = sum(f["amount_gbp"] for f in flows if f["flow_type"] == "New lending drawdown")
    maturing = [f for f in flows if f["flow_type"] == "Wholesale funding maturity"]
    wholesale = sum(f["amount_gbp"] for f in maturing)
    inst = {i["instrument_id"]: i for i in rows["funding_instruments"]}
    short = sum(1 for f in maturing if (D.fromisoformat(inst[f["instrument_id"]]["maturity_date"])
                                        - D.fromisoformat(inst[f["instrument_id"]]["start_date"])).days <= 95)
    lenders = len({f["counterparty_id"] for f in maturing})
    fx = sum(1 for f in flows if f["currency"] != "GBP")
    buffer = sum(a["market_value_gbp"] for a in rows["liquid_assets"])
    unconfirmed = sum(f["amount_gbp"] for f in flows if f["contract_status"] == "Unconfirmed")
    return "\n".join([
        "Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. It funds its mortgages and business "
        "loans mainly from savers' deposits, and tops them up with wholesale funding: deposits from other banks, money market "
        "funds, local authorities and companies, certificates of deposit, repos and a senior note. A small treasury team in the "
        "City and Canary Wharf manages the bank's cash and its liquid asset buffer, now "
        f"{gbp0(buffer)} at market value.",
        "",
        "Several pressures have built up this year:",
        f"- Savers are leaving. Rivals pay more on fixed-rate bonds, and Retail Banking forecasts {gbp0(retail)} of net "
        "withdrawals in the last quarter of the year, more in December than in October.",
        f"- Lending is growing. Retail Banking and Business Banking forecast {gbp0(lending)} of new mortgage and business lending "
        "to be drawn in the quarter, and the board wants that pace kept up.",
        f"- Shorter wholesale funding. To fill the gap, Treasury has borrowed for shorter terms. {gbp0(wholesale)} of wholesale "
        f"funding from {lenders} lenders falls due in the quarter, {short} of the {len(maturing)} deals for three months or less.",
        f"- More currencies. Some funding is raised in US dollars and euros, so {fx} of the forecast's flows must be converted "
        "to sterling.",
        f"- Plans that are not yet deals. Business units have submitted {gbp0(unconfirmed)} of inflows that have no signed "
        "contract, including the sale of a tranche of mortgages.",
        "- A stretched team. One forecasting analyst loads the daily forecast and the business units' submissions; the Asset and "
        "Liability Manager reviews the ladder and the three stress scenarios every day.",
        "",
        "ALCO meets on Tuesday 6 October 2026. The Head of Treasury asked for the quarter's liquidity ladder as at 30 September, "
        "under the base case and each stress scenario, with an explanation of any limit at risk.",
    ])


def build(rng):
    b = Builder(rng)
    b.lookups()
    b.wholesale()
    b.placements()
    b.business_units()
    b.planted()
    b.finalise()
    record_cases(b)
    rules = [{"rule_id": r, "category": c, "title": t, "statement": s, "related_tables": RULE_TABLES[r]} for r, c, t, s in RULES]
    facts = [
        ("dataset", "treasury_liquidity"),
        ("title", "Treasury liquidity"),
        ("firm", firm.FIRM_NAME),
        ("bank", "Thameside Bank, the group's retail and commercial bank"),
        ("scenario", "Thameside Bank's treasury team forecasts its cash flows for the next three months and tests its liquidity under a base case and three stress scenarios."),
        ("period", "Flows due 2026-10-01 to 2026-12-31"),
        ("as_at_date", iso(AS_AT)),
        ("extract_date", EXTRACT.strftime("%Y-%m-%d %H:%M")),
        ("currency", "GBP"),
        ("seed", firm.SEED),
        ("disclaimer", firm.DISCLAIMER + " Counterparties outside the group are identified by reference only, and their ratings are "
                                         "invented. The policy, limits and stress scenarios are invented for the study. A synthetic "
                                         "liquidity exercise tests analysis and controls; it does not show compliance with any "
                                         "regulatory liquidity requirement."),
    ]
    if STORY_APPROVED:
        facts.append(("business_context", business_story(b.rows)))
    b.story_draft = business_story(b.rows)
    return SCHEMA, dict(b.rows), facts, rules, b.cases, b.case_records


# ------------------------------------------------------------------ checks


def checks(con):
    errors = []
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731

    cur = con.execute("SELECT staff_id, first_name, last_name, job_title, office FROM staff")
    cols = [c[0] for c in cur.description]
    errors += staff_register.check([dict(zip(cols, r)) for r in cur.fetchall()], "staff_id", STAFF_REGISTER_IDS)
    planted = {r[0] for r in q("SELECT record_id FROM _truth_case_records r JOIN _truth_cases c USING (case_id) WHERE c.classification = 'Genuine exception'")}

    n = q("SELECT count(*) FROM cashflows")[0][0]
    if not 95 <= n <= 110:
        errors.append(f"cashflows: {n} rows, expected about 100")

    rates = {r[0]: (r[1], r[2], r[3]) for r in q("SELECT fx_rate_id, valuation_date, quote_currency, rate FROM fx_rates")}
    insts = {r["instrument_id"]: r for r in ladder.rows(con, "SELECT * FROM funding_instruments")}
    staff = {r[0]: (r[1], r[2]) for r in q("SELECT staff_id, job_title, dealing_limit_gbp FROM staff")}
    flows = ladder.rows(con, "SELECT * FROM cashflows")
    by_inst = defaultdict(list)
    for f in flows:
        if f["instrument_id"]:
            by_inst[f["instrument_id"]].append(f)

    for f in flows:
        i = f["cashflow_id"]
        due, exp = D.fromisoformat(f["due_date"]), D.fromisoformat(f["expected_date"])
        if not H_START <= due <= H_END or not uk.is_working_day(due) or not uk.is_working_day(exp) or exp > H_END:
            errors.append(f"{i}: due or expected date outside the horizon or not a working day")
        if exp < due or (exp != due and f["notes"] is None):
            errors.append(f"{i}: expected date before the due date, or a late date with no explanation")
        if f["nominal"] <= 0 or f["amount_gbp"] <= 0:
            errors.append(f"{i}: amounts must be positive")
        if f["currency"] == "GBP":
            if f["fx_rate_id"] or f["amount_gbp"] != f["nominal"]:
                errors.append(f"{i}: sterling flow converted")
        else:
            vd, ccy, rate = rates[f["fx_rate_id"]]
            if ccy != f["currency"] or f["amount_gbp"] != float(ladder.convert(f["nominal"], rate)):
                errors.append(f"{i}: conversion does not match its rate")
            if vd != iso(AS_AT) and i not in planted:
                errors.append(f"{i}: converted at a rate not of the as-at date")
        if not f["forecast_run"].startswith("BASE-") and i not in planted:
            errors.append(f"{i}: loaded by a stress run")
        if f["entered_date"] > iso(AS_AT):
            errors.append(f"{i}: entered after the as-at date")
        inst = insts.get(f["instrument_id"])
        if inst:
            if inst["counterparty_id"] != f["counterparty_id"] or inst["currency"] != f["currency"]:
                errors.append(f"{i}: counterparty or currency differs from its instrument")
            if f["direction"] == "Inflow" and (f["contract_status"] == "Confirmed") != (inst["deal_status"] == "Executed") and i not in planted:
                errors.append(f"{i}: contract status disagrees with the deal status")
            if f["flow_type"] == "Wholesale funding maturity":
                pay = ladder.modified_following(D.fromisoformat(inst["maturity_date"]))
                if f["due_date"] != iso(pay) and i not in planted:
                    errors.append(f"{i}: due date is not the instrument's payment date")
                if money(f["nominal"]) != money(inst["principal"]) + money(inst["interest_at_maturity"]):
                    errors.append(f"{i}: maturity amount is not principal plus interest")
            if f["direction"] == "Inflow" and money(f["nominal"]) != money(inst["principal"]):
                errors.append(f"{i}: new funding inflow differs from the principal")

    for iid, inst in insts.items():
        start, mat = D.fromisoformat(inst["start_date"]), D.fromisoformat(inst["maturity_date"])
        pay = ladder.modified_following(mat)
        if inst["interest_at_maturity"] is not None and money(inst["interest_at_maturity"]) != ladder.interest(
                inst["principal"], inst["interest_rate_pct"], start, pay, inst["day_count_basis"]):
            errors.append(f"{iid}: interest does not follow TP-06")
        if not uk.is_working_day(start) or not uk.is_working_day(D.fromisoformat(inst["deal_date"])) or inst["deal_date"] > inst["start_date"]:
            errors.append(f"{iid}: deal or start date not a working day, or deal after start")
        title, limit = staff[inst["dealer_id"]]
        gbp_equiv = inst["principal"] / (1 if inst["currency"] == "GBP" else rates[f"FX-{inst['currency']}-{AS_AT:%Y%m%d}"][2])
        if inst["instrument_type"] != "Senior unsecured note" and (limit is None or gbp_equiv > limit):
            errors.append(f"{iid}: dealt beyond the dealer's limit")
        in_horizon = H_START <= pay <= H_END and start <= AS_AT and inst["deal_status"] == "Executed"
        kinds = {f["flow_type"] for f in by_inst[iid]}
        rolled = any(x["rollover_of_id"] == iid for x in insts.values())
        if in_horizon and iid not in planted:
            want = {"Wholesale funding interest"} if rolled else {"Wholesale funding maturity"}
            if inst["instrument_type"] == "Senior unsecured note":
                want = kinds
            if kinds != want:
                errors.append(f"{iid}: matures in the horizon but its flows are {sorted(kinds)}")
        if inst["rollover_of_id"]:
            prev = insts[inst["rollover_of_id"]]
            if prev["principal"] != inst["principal"] or prev["counterparty_id"] != inst["counterparty_id"] or prev["maturity_date"] != inst["start_date"]:
                errors.append(f"{iid}: rollover terms do not match the maturing deal")
    if q("SELECT count(*) FROM cashflows WHERE flow_type = 'Wholesale funding maturity' AND due_date IN ('2026-12-25', '2026-12-28')")[0][0]:
        errors.append("a maturity falls on a bank holiday")

    # Limits on normal data: the daily limit holds except on the planted day; no group above 25%; numbering.
    days = ladder.daily_third_party(con)
    over = [d for d, v in days.items() if v > DAILY_LIMIT]
    if len(over) != 1:
        errors.append(f"daily limit: expected one day over the limit, found {over}")
    for grp, pct in ladder.group_shares(con).items():
        if pct > GROUP_LIMIT_PCT:
            errors.append(f"concentration group {grp} is {pct:.1f}% of maturities")
    for a_, b_ in q("SELECT x.cashflow_id, y.cashflow_id FROM cashflows x JOIN cashflows y ON x.due_date < y.due_date AND x.cashflow_id > y.cashflow_id"):
        errors.append(f"cashflows: {a_} is numbered after {b_} but is due earlier")
    for a_, b_ in q("SELECT x.instrument_id, y.instrument_id FROM funding_instruments x JOIN funding_instruments y ON x.booked_at < y.booked_at AND x.instrument_id > y.instrument_id"):
        errors.append(f"funding_instruments: {a_} is numbered after {b_} but was booked earlier")
    for (email,) in q("SELECT email FROM staff"):
        if not email.endswith("@" + firm.EMAIL_DOMAIN):
            errors.append(f"{email}: wrong domain")

    # The ladder results the documents describe.
    rec = {s: ladder.ladder(con, s) for s in (None, "ST-01", "ST-02", "ST-03")}
    cor = {s: ladder.ladder(con, s, corrected=True) for s in (None, "ST-03")}
    if any(r["position"] <= 0 for s in (None, "ST-01", "ST-02") for r in rec[s]):
        errors.append("ladder: base case or ST-01/ST-02 position not positive in every bucket")
    if any(r["position"] <= 0 for r in rec["ST-03"]):
        errors.append("ladder: recorded ST-03 position not positive in every bucket")
    if cor["ST-03"][-1]["position"] >= 0 or any(r["position"] <= 0 for r in cor["ST-03"][:-1]):
        errors.append("ladder: corrected ST-03 should breach in B6 only")
    if any(r["position"] <= 0 for r in cor[None]):
        errors.append("ladder: corrected base case not positive")
    negative = [r["bucket_id"] for r in cor[None] if r["net_gap"] < 0]
    if "B5" not in negative or cor[None][3]["cumulative_gap"] + ladder.buffer(con) <= 0:
        errors.append(f"ladder: expected a negative base-case net gap in B5, found {negative}")

    # The business story's claims.
    claims = [
        (q("SELECT count(DISTINCT office) FROM staff WHERE team = 'Treasury'")[0][0] == 2, "the treasury team works in the City and Canary Wharf"),
        (q("SELECT count(*) FROM staff WHERE job_title = 'Liquidity Forecasting Analyst'")[0][0] == 1, "one forecasting analyst"),
        (q("SELECT sum(amount_gbp) FROM cashflows WHERE flow_type = 'Retail deposit outflow' AND forecast_run LIKE 'BASE-%' AND due_date >= '2026-12-01'")[0][0]
         > q("SELECT sum(amount_gbp) FROM cashflows WHERE flow_type = 'Retail deposit outflow' AND forecast_run LIKE 'BASE-%' AND due_date < '2026-11-01'")[0][0],
         "retail withdrawals are higher in December than in October"),
        (q("SELECT count(*) FROM cashflows WHERE contract_status = 'Unconfirmed' AND flow_type = 'Asset sale proceeds'")[0][0] == 1,
         "the unconfirmed inflows include a sale of mortgages"),
        (q("SELECT count(DISTINCT counterparty_type) FROM funding_instruments f JOIN counterparties USING (counterparty_id) WHERE counterparty_type IN ('Bank', 'Money market fund', 'Local authority', 'Corporate')")[0][0] == 4,
         "wholesale funding comes from banks, money market funds, local authorities and companies"),
        (q("SELECT count(DISTINCT instrument_type) FROM funding_instruments")[0][0] == 4, "the four kinds of wholesale funding"),
        (q("SELECT count(*) FROM funding_instruments WHERE currency IN ('USD', 'EUR')")[0][0] > 0, "funding in dollars and euros"),
    ]
    errors += [f"story: {text} is not true in the data" for ok, text in claims if not ok]
    return errors
