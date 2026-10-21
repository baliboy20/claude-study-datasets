"""AML transaction monitoring dataset.

Thameside Bank, the retail and commercial bank of Thameside Financial Group, monitors its customers' payments.
Its financial-crime team is reviewing the alerts raised in the week Monday 14 to Sunday 20 September 2026.
Each row of payments is one payment into or out of a customer's account. Customers and counterparties are
identified by reference only. Countries outside the UK are fictional jurisdictions with user-assigned ISO codes.
The data was extracted at 18:00 on Tuesday 22 September 2026, with the alert queue part-worked.
"""

import datetime as dt
import math
from collections import defaultdict

from generator.common import firm, uk
from generator.common.dataset import Col, Table
from generator.common import staff_register
from generator.common.people import email_for

D = dt.date
WEEK_START = D(2026, 9, 14)
WEEK_END = D(2026, 9, 20)
EXTRACT = dt.datetime(2026, 9, 22, 18, 0)
HISTORY_MONTHS = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
REVIEW_MONTHS = {"High": 12, "Medium": 24, "Low": 36}

# ------------------------------------------------------------------ schema


def C(*a, **k):
    return Col(*a, **k)


SCHEMA = [
    Table("staff", "lookup", "People in the financial-crime team and business banking who appear in the records.", [
        C("staff_id", "TEXT", "Staff identifier."),
        C("first_name", "TEXT", "First name."),
        C("last_name", "TEXT", "Surname."),
        C("job_title", "TEXT", "Job title."),
        C("team", "TEXT", "Team."),
        C("office", "TEXT", "Office: City, Canary Wharf or Croydon."),
        C("email", "TEXT", "Work email address."),
    ]),
    Table("jurisdictions", "lookup", "Countries that payments come from or go to, with the bank's country risk rating. Every country other than the UK is fictional.", [
        C("country_code", "TEXT", "Two-letter code. GB is the United Kingdom; XA to XD are user-assigned ISO codes standing for fictional jurisdictions."),
        C("country_name", "TEXT", "Name."),
        C("risk_rating", "TEXT", "Country risk in the bank's model: Low, Medium or High."),
        C("notes", "TEXT", "Why the rating was given."),
    ]),
    Table("alert_rules", "lookup", "Transaction-monitoring rules, with their thresholds, windows and the severity of the alerts they raise.", [
        C("rule_id", "TEXT", "Rule identifier, for example TM-03."),
        C("rule_name", "TEXT", "Short name."),
        C("description", "TEXT", "What the rule looks for, in full."),
        C("applies_to", "TEXT", "Customers and payments the rule tests."),
        C("threshold_gbp", "REAL", "Amount at or above which the rule fires. Empty if the rule has no amount threshold.", required=False),
        C("window", "TEXT", "Time window the rule looks across. Empty if it tests single payments.", required=False),
        C("run_frequency", "TEXT", "Real time (as each payment is made) or the batch schedule."),
        C("severity", "TEXT", "Severity of the alerts it raises: High, Medium or Low."),
        C("effective_from", "TEXT", "Date the rule, at this threshold, went live."),
    ]),
    Table("customers", "lookup", "The bank's customers who appear in the payments. Names are withheld; customers are identified by reference.", [
        C("customer_id", "TEXT", "Customer reference, for example CUS-0017. Numbers rise with account opening date."),
        C("segment", "TEXT", "Personal or Business."),
        C("customer_type", "TEXT", "Individual, Sole trader, Partnership, Limited liability partnership or Limited company."),
        C("occupation_or_activity", "TEXT", "Occupation of an individual, or business activity, as declared at onboarding or last review."),
        C("expected_monthly_turnover_gbp", "REAL", "Expected value of money paid into the account each month, declared at onboarding or last review."),
        C("expected_activity", "TEXT", "Payments the customer said to expect, recorded at onboarding or last review."),
        C("risk_rating", "TEXT", "Customer risk rating: Low, Medium or High."),
        C("risk_reason", "TEXT", "Main reason for a Medium or High rating. Empty for Low.", required=False),
        C("account_opened_date", "TEXT", "Date the account was opened."),
        C("last_review_date", "TEXT", "Date of the last customer due-diligence review, or of onboarding if none since."),
        C("next_review_due", "TEXT", "Date the next periodic review is due."),
        C("postcode_district", "TEXT", "Outward part of the customer's UK postcode, for example E14."),
        C("relationship_manager_id", "TEXT", "Relationship manager, for business customers who have one.", "staff.staff_id", required=False),
    ]),
    Table("counterparties", "lookup", "The other side of each payment: payees and payers. Names are withheld; counterparties are identified by reference.", [
        C("counterparty_id", "TEXT", "Counterparty reference, for example CP-008. Numbers rise with the date first seen."),
        C("counterparty_type", "TEXT", "Individual, Business, Charity, Public body or Financial institution."),
        C("entity_type", "TEXT", "What the counterparty is, for example Solicitors (SRA-regulated) or Card acquirer."),
        C("country_code", "TEXT", "Country where the counterparty's account is held.", "jurisdictions.country_code"),
        C("relationship", "TEXT", "How the bank's customers deal with it, for example Employer, Supplier or Family or friend."),
        C("linked_customer_id", "TEXT", "The Thameside customer this counterparty is, if it is one.", "customers.customer_id", required=False),
        C("first_seen_date", "TEXT", "Date any Thameside customer first paid or was paid by it."),
        C("screening_status", "TEXT", "Sanctions and watch-list screening result: Clear, Potential match - discounted, Incomplete or Pending."),
        C("screening_date", "TEXT", "Date of the latest screening. Empty if not yet screened.", required=False),
        C("screening_notes", "TEXT", "Notes from the sanctions team.", required=False),
    ]),
    Table("monthly_activity", "business", "Each customer's normal pattern: payments in and out of the account per month, March to August 2026.", [
        C("activity_id", "TEXT", "Row identifier."),
        C("customer_id", "TEXT", "Customer.", "customers.customer_id"),
        C("month", "TEXT", "Calendar month, YYYY-MM."),
        C("credits_count", "INTEGER", "Number of payments into the account."),
        C("credits_value_gbp", "REAL", "Value of payments into the account."),
        C("debits_count", "INTEGER", "Number of payments out of the account."),
        C("debits_value_gbp", "REAL", "Value of payments out of the account."),
    ]),
    Table("payments", "business", "Primary table: every payment into or out of the customers' accounts from Monday 14 to Sunday 20 September 2026. Card purchases and cash are not included.", [
        C("payment_id", "TEXT", "Payment identifier, for example PAY-0042. Numbers rise with time."),
        C("customer_id", "TEXT", "Thameside customer whose account the payment went into or out of.", "customers.customer_id"),
        C("payment_datetime", "TEXT", "Date and time the payment was made or received, YYYY-MM-DD HH:MM:SS, UK time."),
        C("direction", "TEXT", "Outbound (paid by the customer) or Inbound (received by the customer). A transfer between two Thameside customers is recorded once, as the payer's outbound payment."),
        C("amount_gbp", "REAL", "Amount in pounds."),
        C("payment_type", "TEXT", "Faster Payments, BACS, CHAPS, SWIFT or Internal transfer (between two Thameside accounts)."),
        C("counterparty_id", "TEXT", "The payee of an outbound payment or the payer of an inbound one.", "counterparties.counterparty_id"),
        C("channel", "TEXT", "How the payment was made: Mobile app, Online banking, Business online banking, Bulk payment file, Direct Debit, Branch, Relationship manager, or Inbound payment."),
        C("origin_country", "TEXT", "Country the money came from.", "jurisdictions.country_code"),
        C("destination_country", "TEXT", "Country the money went to.", "jurisdictions.country_code"),
        C("payment_reference", "TEXT", "Reference entered by the payer."),
        C("risk_score", "INTEGER", "Score from 1 to 99 given by the bank's monitoring model; higher means riskier. Alerts are raised by the rules in alert_rules, not by the score."),
        C("alert_status", "TEXT", "No alert; Open (at least one alert on the payment is not closed); or Closed (every alert on it is closed)."),
        C("payment_status", "TEXT", "Completed, or Held - awaiting screening."),
    ]),
    Table("alerts", "business", "Alerts raised by the monitoring rules on the week's payments, and the state of each at the extract.", [
        C("alert_id", "TEXT", "Alert identifier. Numbers rise with time."),
        C("payment_id", "TEXT", "Payment that triggered the alert.", "payments.payment_id"),
        C("customer_id", "TEXT", "Customer the alert is about.", "customers.customer_id"),
        C("rule_id", "TEXT", "Rule that fired.", "alert_rules.rule_id"),
        C("raised_datetime", "TEXT", "When the alert was raised."),
        C("severity", "TEXT", "High, Medium or Low, from the rule."),
        C("investigation_status", "TEXT", "Open - unassigned, Open - assigned, Under investigation, or Closed - no further action."),
        C("assigned_to", "TEXT", "Analyst working the alert. Empty if unassigned.", "staff.staff_id", required=False),
        C("analyst_decision", "TEXT", "The analyst's decision and reason. Empty until decided.", required=False),
        C("decision_date", "TEXT", "Date of the decision. Empty until decided.", required=False),
        C("evidence_reference", "TEXT", "Document the analyst relied on, if any.", required=False),
    ]),
]

# ------------------------------------------------------------------ reference data

# Each staff member's entry in the firm-wide staff register (generator/common/staff_register.py).
STAFF_REGISTER_IDS = {'STF-01': 'TFG-030', 'STF-02': 'TFG-031', 'STF-03': 'TFG-032', 'STF-04': 'TFG-033', 'STF-05': 'TFG-034', 'STF-06': 'TFG-035', 'STF-07': 'TFG-036', 'STF-08': 'TFG-037', 'STF-09': 'TFG-038', 'STF-10': 'TFG-039', 'STF-11': 'TFG-040'}

STAFF = [
    # id, title, team, office, gender
    ("STF-01", "Money Laundering Reporting Officer", "Financial Crime", "City", "f"),
    ("STF-02", "Head of Financial Crime Operations", "Financial Crime", "Canary Wharf", "m"),
    ("STF-03", "Transaction Monitoring Manager", "Financial Crime", "Canary Wharf", "f"),
    ("STF-04", "Financial Crime Analyst", "Transaction Monitoring", "Canary Wharf", "m"),
    ("STF-05", "Financial Crime Analyst", "Transaction Monitoring", "Croydon", "f"),
    ("STF-06", "Financial Crime Analyst", "Transaction Monitoring", "Croydon", "m"),
    ("STF-07", "Senior Investigator", "Financial Crime Investigations", "Canary Wharf", "f"),
    ("STF-08", "Sanctions Screening Lead", "Sanctions", "Canary Wharf", "m"),
    ("STF-09", "Customer Due Diligence Team Leader", "Customer Due Diligence", "Croydon", "f"),
    ("STF-10", "Relationship Manager, Business Banking", "Business Banking", "City", "m"),
    ("STF-11", "Relationship Manager, Business Banking", "Business Banking", "Croydon", "f"),
]

JURISDICTIONS = [
    ("GB", "United Kingdom", "Low", "Home country."),
    ("XA", "Jurisdiction XA (fictional)", "High", "Fictional. Rated High in the bank's model for weak anti-money-laundering controls."),
    ("XB", "Jurisdiction XB (fictional)", "High", "Fictional. Rated High in the bank's model for company secrecy and weak supervision."),
    ("XC", "Jurisdiction XC (fictional)", "Medium", "Fictional. Rated Medium: adequate laws, limited public company records."),
    ("XD", "Jurisdiction XD (fictional)", "Low", "Fictional. Rated Low: strong controls and open company records."),
]
COUNTRY_RISK = {j[0]: j[2] for j in JURISDICTIONS}

ALERT_RULES = [
    ("TM-01", "Large payment, personal customer", "A single payment of £10,000 or more into or out of a personal customer's account.",
     "Personal customers; inbound and outbound; all payment types", 10_000, None, "Real time", "Medium", "2024-02-05"),
    ("TM-02", "New payee, high value", "An outbound payment of £5,000 or more to a counterparty first seen in the last 30 days.",
     "All customers; outbound", 5_000, "Counterparty first seen within 30 days before the payment", "Real time", "Low", "2024-02-05"),
    ("TM-03", "Rapid movement of funds", "An outbound payment of at least 80% of a single credit of £5,000 or more that reached the same account in the previous 24 hours. Credits include internal transfers from other Thameside customers.",
     "All customers; outbound", 5_000, "24 hours", "Real time", "High", "2025-06-02"),
    ("TM-04", "Activity above profile", "Money paid into the account in a calendar month is more than twice the customer's expected monthly turnover.",
     "All customers; inbound", None, "Calendar month", "Monthly batch, run on the first working day of the next month", "Medium", "2024-02-05"),
    ("TM-05", "High-risk jurisdiction", "Any payment of £1,000 or more to or from a jurisdiction rated High.",
     "All customers; inbound and outbound", 1_000, None, "Real time", "High", "2024-02-05"),
    ("TM-06", "Large international business payment", "An outbound SWIFT payment of £50,000 or more by a business customer.",
     "Business customers; outbound SWIFT", 50_000, None, "Real time", "Low", "2024-02-05"),
]

# key, segment, type, activity, expected £/month, expected activity, risk, reason, opened, last review, rm
CUSTOMERS = [
    ("P", "Personal", "Individual", "Retired", 3_200, "Pension and interest in; household bills out", "Low", None, "2004-05-17", "2024-03-11", None),
    ("H", "Personal", "Individual", "Retired teacher", 2_400, "Pension in; household bills out", "Low", None, "2007-10-02", "2024-06-20", None),
    ("N2", "Personal", "Individual", "Bus driver", 2_600, "Weekly wages in; rent and bills out", "Low", None, "2009-02-23", "2024-02-05", None),
    ("N4", "Personal", "Individual", "Chartered accountant", 4_800, "Salary in; mortgage, school fees and bills out", "Low", None, "2011-06-14", "2024-08-12", None),
    ("G", "Business", "Partnership", "Dental practice", 62_000, "NHS contract and patient card payments in; payroll and suppliers out", "Low", None, "2013-09-16", "2024-01-22", "STF-11"),
    ("N3", "Personal", "Individual", "Pharmacist", 4_300, "Salary in; mortgage and bills out", "Low", None, "2014-05-06", "2024-04-15", None),
    ("M", "Business", "Limited company", "Builders' merchant", 85_000, "Card settlements and trade account receipts in; suppliers and payroll out", "Low", None, "2015-03-09", "2024-05-20", "STF-10"),
    ("Q", "Business", "Limited company", "Freight forwarding", 150_000, "Receipts from UK and overseas clients; hauliers, payroll and duties out", "Medium", "International trade", "2015-11-02", "2025-01-13", "STF-10"),
    ("K", "Personal", "Individual", "Nurse", 3_100, "Salary in; rent and bills out", "Low", None, "2016-03-01", "2024-10-07", None),
    ("D", "Business", "Limited liability partnership", "Architectural practice", 45_000, "Client fees in; payroll and rent out", "Low", None, "2016-04-25", "2024-09-30", "STF-11"),
    ("N1", "Personal", "Individual", "Software developer", 5_200, "Salary in on the 15th; rent and bills out", "Low", None, "2017-01-16", "2025-01-27", None),
    ("W", "Business", "Limited company", "Wholesale of electronic components", 120_000, "UK customer receipts in; overseas suppliers by SWIFT and payroll out", "Medium", "International trade", "2018-07-09", "2025-03-17", "STF-10"),
    ("N7", "Personal", "Individual", "Marketing manager", 4_600, "Salary in on the 15th; mortgage and bills out", "Low", None, "2018-10-08", "2024-10-21", None),
    ("N5", "Personal", "Individual", "Civil servant", 3_100, "Salary in; rent and bills out", "Low", None, "2019-03-04", "2025-02-10", None),
    ("J", "Business", "Sole trader", "Plumbing and heating engineer", 8_500, "Payments from household customers in; merchants out", "Low", None, "2019-05-13", "2024-11-04", None),
    ("S", "Personal", "Individual", "Warehouse supervisor", 2_900, "Salary in; rent and bills out", "Low", None, "2019-08-05", "2024-08-27", None),
    ("E", "Business", "Limited company", "Import and wholesale of textiles", 95_000, "Receipts from UK and overseas buyers; suppliers and payroll out", "High", "Regular trade with a High-risk jurisdiction", "2020-01-20", "2025-06-12", "STF-11"),
    ("N10", "Personal", "Individual", "Chef", 2_300, "Weekly wages in; rent and bills out", "Low", None, "2020-06-01", "2023-11-27", None),
    ("F", "Business", "Limited company", "Café and takeaway", 18_000, "Card settlements in; food suppliers and payroll out", "Low", None, "2021-02-15", "2024-03-04", None),
    ("N6", "Personal", "Individual", "Electrician (employed)", 3_000, "Weekly wages in; rent and bills out", "Low", None, "2021-09-20", "2024-09-30", None),
    ("N8", "Personal", "Individual", "Care worker", 1_900, "Weekly wages in; rent, bills and small transfers to family abroad", "Low", None, "2022-04-11", "2025-04-14", None),
    ("L", "Business", "Limited company", "Hand car wash and valeting", 26_000, "Card settlements in; suppliers and payroll out", "High", "Cash-intensive business", "2022-08-08", "2025-10-05", "STF-11"),
    ("N9", "Personal", "Individual", "Retail assistant", 1_700, "Weekly wages in; rent share and bills out", "Low", None, "2023-01-09", "2026-01-12", None),
    ("A", "Personal", "Individual", "Student", 900, "Student loan and part-time wages in; living costs out", "Low", None, "2026-06-08", "2026-06-08", None),
    ("B", "Business", "Sole trader", "Mobile phone accessories (market stall)", 6_000, "Card settlements in; stock purchases out", "Medium", "New business with no trading history", "2026-07-20", "2026-07-20", None),
    ("C", "Business", "Limited company", "General trading (import and export)", 15_000, "UK customer receipts in; overseas suppliers out", "Medium", "New company; international trade", "2026-08-03", "2026-08-03", None),
]

# ------------------------------------------------------------------ helpers


def iso(d):
    return d.isoformat() if d else None


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return D(d.year + y, m + 1, min(d.day, 28 if m + 1 == 2 else 30 if m + 1 in (4, 6, 9, 11) else 31))


def day(n):
    """Day of the September 2026 week: 14 (Monday) to 20 (Sunday)."""
    return D(2026, 9, n)


class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.rows = defaultdict(list)
        self.cases, self.case_records = [], []
        self.cust = {}
        self.cps = []
        self.pays = []
        self.handling = {}  # (payment draft id, rule) -> alert handling
        self.P = {}

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
        rng = self.rng
        for sid, title, team, office, g in STAFF:
            person = staff_register.person(STAFF_REGISTER_IDS[sid])
            first, last = person["first_name"], person["last_name"]
            self.rows["staff"].append({"staff_id": sid, "first_name": first, "last_name": last, "job_title": title,
                                       "team": team, "office": office, "email": email_for(first, last, firm.EMAIL_DOMAIN)})
        self.rows["jurisdictions"] = [dict(zip(["country_code", "country_name", "risk_rating", "notes"], j)) for j in JURISDICTIONS]
        self.rows["alert_rules"] = [dict(zip(["rule_id", "rule_name", "description", "applies_to", "threshold_gbp", "window",
                                              "run_frequency", "severity", "effective_from"], r)) for r in ALERT_RULES]
        for r in self.rows["alert_rules"]:
            if r["threshold_gbp"] is not None:
                r["threshold_gbp"] = float(r["threshold_gbp"])
        # Postcode districts: the two newest business customers share one; nobody else uses it.
        pool = [o for area, (_, outs) in uk.DISTRICTS.items() for o in outs if area != "Edinburgh" and o != "N17"]
        for i, (key, seg, ctype, act, exp, expect, risk, reason, opened, review, rm) in enumerate(
                sorted(CUSTOMERS, key=lambda c: c[8]), start=1):
            last = D.fromisoformat(review)
            district = "N17" if key in ("B", "C") else "E3" if key == "A" else rng.choice(pool)
            self.cust[key] = {
                "customer_id": f"CUS-{i:04d}", "segment": seg, "customer_type": ctype, "occupation_or_activity": act,
                "expected_monthly_turnover_gbp": float(exp), "expected_activity": expect, "risk_rating": risk,
                "risk_reason": reason, "account_opened_date": opened, "last_review_date": review,
                "next_review_due": iso(add_months(last, REVIEW_MONTHS[risk])), "postcode_district": district,
                "relationship_manager_id": rm}
        self.rows["customers"] = sorted(self.cust.values(), key=lambda c: c["customer_id"])

    def cp(self, ctype, entity, relationship, first_seen, country="GB", linked=None, screening="Clear",
           screened=None, notes=None):
        c = {"counterparty_type": ctype, "entity_type": entity, "country_code": country, "relationship": relationship,
             "linked_customer_id": self.cust[linked]["customer_id"] if linked else None,
             "first_seen_date": first_seen, "screening_status": screening,
             "screening_date": screened if screened is not None or screening == "Pending" else first_seen,
             "screening_notes": notes}
        self.cps.append(c)
        return c

    def pay(self, key, d, direction, amount, ptype, cp, ref, *, at=None, channel=None, status="Completed", alerts=None):
        rng = self.rng
        if at is None:
            business_hours = self.cust[key]["segment"] == "Business" or cp["counterparty_type"] != "Individual"
            lo, hi = {"BACS": (5 * 60 + 30, 6 * 60 + 30), "CHAPS": (8 * 60 + 30, 16 * 60 + 45),
                      "SWIFT": (9 * 60 + 30, 15 * 60 + 30)}.get(ptype, (8 * 60, 18 * 60) if business_hours else (7 * 60 + 10, 22 * 60 + 40))
            m = rng.randint(lo, hi)
            at = f"{m // 60:02d}:{m % 60:02d}"
        when = dt.datetime.combine(d, dt.time.fromisoformat(at)) + dt.timedelta(seconds=rng.randint(0, 59))
        cust = self.cust[key]
        if channel is None:
            if direction == "Inbound":
                channel = "Inbound payment"
            elif ptype == "BACS":
                channel = "Bulk payment file" if cust["segment"] == "Business" else "Direct Debit"
            elif ptype in ("CHAPS", "SWIFT"):
                channel = "Business online banking" if cust["segment"] == "Business" else "Branch"
            else:
                channel = "Business online banking" if cust["segment"] == "Business" else rng.choice(["Mobile app", "Mobile app", "Online banking"])
        p = {"key": key, "cust": cust, "when": when, "direction": direction, "amount": round(float(amount), 2),
             "ptype": ptype, "cp": cp, "ref": ref, "channel": channel, "status": status}
        if direction == "Outbound":
            p["origin"], p["dest"] = "GB", cp["country_code"]
        else:
            p["origin"], p["dest"] = cp["country_code"], "GB"
        for rule, h in (alerts or {}).items():
            self.handling[(id(p), rule)] = h
        self.pays.append(p)
        return p

    # ---- the week's payments

    def week(self):
        rng = self.rng
        P = self.P
        cp, pay = self.cp, self.pay

        # Shared counterparties
        acquirer = cp("Business", "Card acquirer", "Merchant services", "2013-09-16")
        energy = cp("Business", "Energy supplier", "Utility", "2009-02-23")
        water = cp("Business", "Water company", "Utility", "2009-02-23")
        council = cp("Public body", "London borough council (council tax)", "Public body", "2004-05-17")
        lender = cp("Financial institution", "Mortgage lender", "Lender", "2014-05-06")
        payroll = cp("Business", "Employees (bulk payroll file)", "Employees", "2013-09-16")

        # ---- normal personal customers
        emp_n1 = cp("Business", "Software company", "Employer", "2017-01-31")
        emp_n7 = cp("Business", "Retail group head office", "Employer", "2018-10-15")
        emp_bus = cp("Business", "Bus operator", "Employer", "2009-03-06")
        emp_elec = cp("Business", "Electrical contractor", "Employer", "2021-09-24")
        emp_care = cp("Business", "Home care agency", "Employer", "2022-04-15")
        emp_shop = cp("Business", "Supermarket chain", "Employer", "2023-01-13")
        emp_rest = cp("Business", "Restaurant group", "Employer", "2020-06-05")
        landlord = cp("Individual", "Private landlord", "Landlord", "2017-02-01")
        agent = cp("Business", "Letting agent", "Landlord", "2020-06-26")
        friend5 = cp("Individual", "Individual", "Family or friend", "2019-07-12")
        n10_cp = cp("Individual", "Individual", "Family or friend", "2023-02-03", linked="N10")

        pay("N1", day(15), "Inbound", 3_486.27, "BACS", emp_n1, "SALARY SEP")
        pay("N1", day(15), "Outbound", 1_950.00, "Faster Payments", landlord, "RENT FLAT 2", channel="Standing order")
        pay("N1", day(17), "Outbound", 112.40, "BACS", energy, "ENERGY DD 4471902")
        pay("N7", day(15), "Inbound", 3_092.55, "BACS", emp_n7, "PAY 15SEP26")
        pay("N7", day(16), "Outbound", 1_384.19, "BACS", lender, "MORTGAGE 30091827")
        pay("N2", day(18), "Inbound", 618.42, "BACS", emp_bus, "WAGES WK24")
        pay("N2", day(14), "Outbound", 168.00, "BACS", council, "CTAX 61044281")
        pay("N3", day(15), "Outbound", 1_412.66, "BACS", lender, "MORTGAGE 30155420")
        pay("N4", day(16), "Outbound", 54.20, "BACS", water, "WATER 8830214")
        pay("N5", day(19), "Outbound", 60.00, "Faster Payments", friend5, "Pizza and taxi")
        pay("N6", day(18), "Inbound", 774.10, "BACS", emp_elec, "WAGES W/E 13/09")
        pay("N8", day(18), "Inbound", 466.85, "BACS", emp_care, "PAY WK 37")
        pay("N9", day(18), "Inbound", 402.37, "BACS", emp_shop, "WEEKLY PAY")
        pay("N9", day(18), "Outbound", 450.00, "Internal transfer", n10_cp, "Rent share Sept")
        pay("N10", day(18), "Inbound", 541.90, "BACS", emp_rest, "WAGES")
        pay("N10", day(19), "Outbound", 1_150.00, "Faster Payments", agent, "RENT 14 SAILMAKER CT", channel="Standing order")
        pay("K", day(14), "Outbound", 96.30, "BACS", energy, "ENERGY DD 5513208")
        pay("H", day(16), "Outbound", 147.00, "BACS", council, "CTAX 61092264")
        pay("P", day(17), "Outbound", 61.75, "BACS", water, "WATER 8812006")
        pay("S", day(14), "Outbound", 158.00, "BACS", council, "CTAX 61177019")
        pay("N1", day(16), "Outbound", 35.00, "Faster Payments", cp("Individual", "Individual", "Family or friend", "2021-04-09"), "Five-a-side")
        pay("N2", day(19), "Outbound", 40.00, "Faster Payments", cp("Individual", "Individual", "Family or friend", "2012-07-30"), "Birthday")
        pay("N3", day(16), "Outbound", 182.00, "BACS", council, "CTAX 61210437")
        pay("N4", day(15), "Outbound", 1_876.34, "BACS", lender, "MORTGAGE 30022918")
        pay("N5", day(15), "Outbound", 1_325.00, "Faster Payments", cp("Individual", "Private landlord", "Landlord", "2019-03-29"), "RENT 3B", channel="Standing order")
        pay("N6", day(15), "Outbound", 895.00, "Faster Payments", cp("Business", "Letting agent", "Landlord", "2021-10-01"), "RENT FLAT 6", channel="Standing order")
        pay("N7", day(17), "Outbound", 138.75, "BACS", energy, "ENERGY DD 4920113")
        pay("K", day(14), "Outbound", 1_240.00, "Faster Payments", cp("Individual", "Private landlord", "Landlord", "2016-04-01"), "RENT SEPT", channel="Standing order")
        pay("H", day(17), "Outbound", 200.00, "Faster Payments", cp("Individual", "Individual", "Family or friend", "2015-12-18"), "Happy birthday")
        pay("P", day(15), "Outbound", 121.60, "BACS", energy, "ENERGY DD 3308451")

        # ---- normal business customers
        food = cp("Business", "Food and drink wholesaler", "Supplier", "2021-03-01")
        timber = cp("Business", "Timber merchant", "Supplier", "2015-04-13")
        aggregates = cp("Business", "Cement and aggregates supplier", "Supplier", "2017-02-20")
        dental = cp("Business", "Dental supplies distributor", "Supplier", "2013-10-07")
        nhs = cp("Public body", "NHS dental contract payments", "Public body", "2013-10-31")
        client_d = cp("Business", "Property developer", "Customer", "2021-05-10")
        client_q = cp("Business", "Freight client (importer)", "Customer", "2016-08-22", country="XD")
        haulier = cp("Business", "Haulage company", "Supplier", "2016-01-18")
        supplier_xd = cp("Business", "Electronic components distributor", "Supplier", "2019-02-11", country="XD",
                         screened="2026-02-09")
        uk_buyer_w = cp("Business", "Electronics retailer", "Customer", "2018-09-03")
        merchant_j = cp("Business", "Plumbing merchant", "Supplier", "2019-05-20")
        car_care = cp("Business", "Car care products supplier", "Supplier", "2022-08-22")
        uk_supplier_e = cp("Business", "Textile finishing company", "Supplier", "2020-02-17")

        for d0 in (14, 15, 16, 17, 18):
            pay("F", day(d0), "Inbound", round(rng.uniform(480, 1_150), 2), "BACS", acquirer, f"CARD SETTLEMENT {d0 - 1:02d}0926")
        pay("F", day(16), "Outbound", 2_318.40, "BACS", food, "INV 88214")
        pay("F", day(18), "Outbound", 4_126.73, "BACS", payroll, "PAYROLL WK37")
        for d0 in (14, 16, 18):
            pay("M", day(d0), "Inbound", round(rng.uniform(3_100, 4_700), 2), "BACS", acquirer, f"CARD SETTLEMENT {d0 - 1:02d}0926")
        pay("M", day(18), "Outbound", 14_872.10, "BACS", payroll, "PAYROLL WK37")
        for d0 in (15, 18):
            pay("L", day(d0), "Inbound", round(rng.uniform(1_900, 3_200), 2), "BACS", acquirer, f"CARD SETTLEMENT {d0 - 1:02d}0926")
        pay("L", day(16), "Outbound", 1_286.52, "BACS", car_care, "INV CC-30418")
        pay("L", day(18), "Outbound", 5_312.88, "BACS", payroll, "PAYROLL WK37")
        pay("G", day(15), "Inbound", 41_206.00, "BACS", nhs, "UDA CONTRACT SEP26")
        pay("G", day(16), "Inbound", 3_877.25, "BACS", acquirer, "CARD SETTLEMENT 150926")
        pay("G", day(17), "Outbound", 3_164.90, "BACS", dental, "INV 230981")
        pay("D", day(14), "Inbound", 14_400.00, "Faster Payments", client_d, "FEE STAGE 3 PROJ 2207")
        pay("D", day(18), "Outbound", 21_830.65, "BACS", payroll, "PAYROLL SEP")
        pay("Q", day(15), "Inbound", 22_040.00, "SWIFT", client_q, "INV FQ-6612 FREIGHT AUG")
        pay("Q", day(17), "Outbound", 7_840.00, "BACS", haulier, "SUBCON AUG INV 4471")
        pay("Q", day(18), "Outbound", 31_205.12, "BACS", payroll, "PAYROLL SEP")
        pay("W", day(14), "Inbound", 28_615.80, "BACS", uk_buyer_w, "REMIT 77120 77134")
        pay("W", day(16), "Outbound", 64_250.00, "SWIFT", supplier_xd, "PO 5531 COMPONENTS",
            alerts={"TM-06": ("Closed - no further action", "STF-05", "Long-standing supplier in a Low-risk jurisdiction; amount in line with past orders.", "2026-09-17", "PO 5531 and supplier invoice")})
        pay("W", day(18), "Outbound", 38_904.33, "BACS", payroll, "PAYROLL SEP")
        pay("J", day(15), "Outbound", 1_642.18, "Faster Payments", merchant_j, "ACC 30981 AUG STMT")
        for d0, amt in ((14, 1_380.00), (17, 640.00), (19, 1_865.00)):
            c = cp("Individual", "Individual", "Customer", iso(day(d0)))
            pay("J", day(d0), "Inbound", amt, "Faster Payments", c, rng.choice(["Boiler service", "Invoice 2209", "Bathroom works"]) if d0 != 17 else "Leak repair")
        pay("E", day(16), "Outbound", 6_215.00, "BACS", uk_supplier_e, "INV TF-11842")
        pay("E", day(18), "Outbound", 22_870.41, "BACS", payroll, "PAYROLL SEP")
        pay("G", day(18), "Outbound", 36_410.08, "BACS", payroll, "PAYROLL SEP")
        pay("D", day(15), "Outbound", 4_500.00, "Faster Payments", cp("Business", "Commercial landlord", "Landlord", "2016-05-03"), "RENT Q3 STUDIO 4")
        pay("F", day(17), "Outbound", 640.20, "Faster Payments", cp("Business", "Bakery", "Supplier", "2022-01-14"), "INV 5521")

        # ---- CASE: structuring just below the TM-01 threshold (no rule looks at several payments)
        rel1 = cp("Individual", "Individual", "Family or friend", "2024-11-23")
        rel2 = cp("Individual", "Individual", "Family or friend", "2025-06-30")
        P["struct"] = [
            pay("S", day(14), "Outbound", 9_480.00, "Faster Payments", rel1, "Loan", at="18:12"),
            pay("S", day(15), "Outbound", 9_750.00, "Faster Payments", rel2, "Money as agreed", at="07:55"),
            pay("S", day(15), "Outbound", 9_620.00, "Faster Payments", rel1, "Loan 2", at="21:40"),
            pay("S", day(16), "Outbound", 9_860.00, "Faster Payments", rel2, "Thanks", at="12:03"),
        ]

        # ---- lookalike: a business paying established suppliers just under £10,000
        P["below_ok"] = [
            pay("M", day(15), "Outbound", 9_640.00, "BACS", timber, "INV T-55210"),
            pay("M", day(17), "Outbound", 9_815.40, "BACS", aggregates, "INV 0091733"),
        ]

        # ---- CASE: funds passing through a chain of Thameside accounts to a High-risk jurisdiction
        origin = cp("Individual", "Individual", "Unknown", "2026-09-15")
        to_b = cp("Business", "Sole trader", "Thameside customer", "2026-09-15", linked="B")
        to_c = cp("Business", "Limited company", "Thameside customer", "2026-09-16", linked="C")
        overseas = cp("Business", "Trading company", "Overseas supplier", "2026-09-17", country="XB", screened="2026-09-17")
        under_inv = ("Under investigation", "STF-04", None, None, None)
        b_closed = ("Closed - no further action", "STF-05", "Payee is an existing Thameside business customer; customer says the payments are for stock.", "2026-09-17", None)
        unassigned = ("Open - unassigned", None, None, None, None)
        P["chain_in"] = pay("A", day(15), "Inbound", 24_500.00, "Faster Payments", origin, "For the car", at="10:12",
                            alerts={"TM-01": under_inv})
        P["chain"] = [
            pay("A", day(15), "Outbound", 24_300.00, "Internal transfer", to_b, "Car", at="10:41",
                alerts={"TM-01": under_inv, "TM-02": under_inv, "TM-03": under_inv}),
            pay("B", day(16), "Outbound", 12_000.00, "Internal transfer", to_c, "Stock 1", at="09:20", alerts={"TM-02": b_closed}),
            pay("B", day(16), "Outbound", 12_100.00, "Internal transfer", to_c, "Stock 2", at="09:24", alerts={"TM-02": b_closed}),
            pay("C", day(17), "Outbound", 23_900.00, "SWIFT", overseas, "INVOICE 0917 GOODS", at="11:05",
                alerts={"TM-02": unassigned, "TM-05": unassigned}),
        ]

        # ---- lookalike: a gifted house deposit passing from parent to child to the child's solicitor
        to_k = cp("Individual", "Individual", "Family or friend", "2024-12-20", linked="K")
        sol_k = cp("Business", "Solicitors (SRA-regulated)", "Professional adviser", "2026-08-14")
        P["gift"] = [
            pay("P", day(17), "Outbound", 45_000.00, "Internal transfer", to_k, "Gift towards house deposit", at="10:02",
                alerts={"TM-01": ("Closed - no further action", "STF-05", "Gift from parent to child towards a house purchase; signed gift letter and solicitor's letter seen.", "2026-09-18", "Gifted deposit letter and solicitor's letter dated 16/09/2026")}),
            pay("K", day(18), "Outbound", 61_750.00, "CHAPS", sol_k, "PURCHASE 9 LANTHORN MEWS", at="09:15", channel="Online banking",
                alerts={"TM-01": ("Open - assigned", "STF-06", None, None, None), "TM-03": ("Open - assigned", "STF-06", None, None, None)}),
        ]

        # ---- CASE: sudden change for the café: many new individual payers, then one payment to a cryptoasset exchange
        P["cafe"] = []
        for d0, at, amt in ((14, "19:42", 3_200.00), (15, "08:17", 4_850.00), (15, "22:06", 2_950.00), (16, "13:31", 4_400.00),
                            (16, "20:58", 3_780.00), (17, "07:44", 4_120.00), (17, "23:12", 3_500.00)):
            c = cp("Individual", "Individual", "Unknown", iso(day(d0)))
            P["cafe"].append(pay("F", day(d0), "Inbound", amt, "Faster Payments", c,
                                 rng.choice(["Payment", "Invoice", "For goods", "F", "Payment 2", "Order"]), at=at))
        crypto = cp("Business", "Cryptoasset exchange (FCA-registered)", "Exchange", "2026-09-18")
        P["cafe"].append(pay("F", day(18), "Outbound", 27_500.00, "Faster Payments", crypto, "Account top up", at="10:26",
                             alerts={"TM-02": unassigned}))

        # ---- lookalike: a house sale completing for a retired customer
        sol_h = cp("Business", "Solicitors (SRA-regulated)", "Professional adviser", "2026-07-02")
        P["sale"] = pay("H", day(14), "Inbound", 318_450.00, "CHAPS", sol_h, "SALE 41 TIDEMILL ROAD COMPLETION", at="13:48",
                        alerts={"TM-01": ("Closed - no further action", "STF-04", "Completion of the customer's house sale; matches the solicitor's completion statement.", "2026-09-15", "Completion statement, 41 Tidemill Road")})

        # ---- CASE: payments released to a counterparty whose screening is incomplete
        supplier_xc = cp("Business", "Electronics manufacturer", "Supplier", "2026-08-03", country="XC", screening="Incomplete",
                         screened="2026-08-03",
                         notes="Entity name screened: no match. Beneficial owners and registered address not provided; requested from the customer 2026-08-04, not yet received.")
        P["incomplete"] = [
            pay("W", day(15), "Outbound", 36_800.00, "SWIFT", supplier_xc, "PO 5528 DEPOSIT", at="11:22"),
            pay("W", day(17), "Outbound", 41_200.00, "SWIFT", supplier_xc, "PO 5528 BALANCE", at="14:09"),
        ]

        # ---- lookalike: a payment correctly held while screening is pending
        family_xd = cp("Individual", "Individual", "Family or friend", "2026-09-18", country="XD", screening="Pending",
                       notes="Name and address received 2026-09-18; screening queued.")
        P["held"] = pay("N8", day(18), "Outbound", 2_750.00, "SWIFT", family_xd, "Family support", at="11:37", channel="Branch",
                        status="Held - awaiting screening")

        # ---- lookalike: a payee that once matched a sanctions name, discounted with reasons
        haulier_pm = cp("Business", "Haulage subcontractor (sole trader)", "Supplier", "2023-05-15", screening="Potential match - discounted",
                        screened="2026-08-03",
                        notes="Name similar to an entry on the UK sanctions list. Date of birth and nationality differ. Discounted 2023-05-19; re-screened 2026-08-03 with the same result.")
        P["discounted"] = pay("Q", day(16), "Outbound", 4_200.00, "BACS", haulier_pm, "SUBCON INV 0613")

        # ---- lookalike: innocent payments to new payees that all raise TM-02
        P["innocent"] = [
            pay("N3", day(14), "Outbound", 7_840.00, "Faster Payments",
                cp("Business", "Kitchen design and fitting company", "Supplier", "2026-09-02"), "KITCHEN DEPOSIT INV 1043", at="20:15",
                alerts={"TM-02": ("Open - assigned", "STF-06", None, None, None)}),
            pay("N4", day(15), "Outbound", 8_450.00, "Faster Payments",
                cp("Charity", "Independent school", "Education provider", "2026-09-01"), "AUTUMN TERM FEES REF 2291", at="09:03",
                alerts={"TM-02": ("Open - assigned", "STF-06", None, None, None)}),
            pay("N5", day(16), "Outbound", 6_180.00, "Faster Payments",
                cp("Charity", "University", "Education provider", "2026-08-28"), "HALLS 2026/27 STUDENT 88120417", at="18:47",
                alerts={"TM-02": unassigned}),
            pay("N6", day(17), "Outbound", 6_500.00, "Faster Payments",
                cp("Business", "Franchised motor dealer", "Retailer", "2026-09-12"), "DEPOSIT ORDER 55120", at="12:20",
                alerts={"TM-02": unassigned}),
            pay("N7", day(19), "Outbound", 5_500.00, "Faster Payments",
                cp("Business", "Wedding venue", "Retailer", "2026-09-05"), "WEDDING BALANCE 12/06/27", at="10:55",
                alerts={"TM-02": unassigned}),
        ]

        # ---- the High-risk customer whose review is overdue
        buyer_xa = cp("Business", "Clothing retailer", "Customer", "2020-03-02", country="XA", screened="2026-03-02")
        P["edd_pay"] = pay("E", day(15), "Inbound", 18_400.00, "SWIFT", buyer_xa, "INV TX-2291 AUG SHIPMENT", at="10:48",
                           alerts={"TM-05": ("Closed - no further action", "STF-06", "Regular receipt from an established overseas buyer; consistent with the customer's profile. Enhanced due diligence on file.", "2026-09-16", "Invoice TX-2291")})

        # ---- normal activity for the newest accounts
        pay("A", day(14), "Outbound", 42.50, "Faster Payments", cp("Individual", "Individual", "Family or friend", "2026-06-20"), "Food shop")
        stall = cp("Business", "Market operator", "Supplier", "2026-07-24")
        pay("B", day(14), "Outbound", 85.00, "Faster Payments", stall, "PITCH FEE WK38")
        pay("B", day(18), "Inbound", 612.45, "BACS", acquirer, "CARD SETTLEMENT 170926")
        pay("A", day(18), "Inbound", 186.20, "BACS", cp("Business", "Coffee shop chain", "Employer", "2026-07-03"), "WAGES WK37")
        pay("C", day(14), "Inbound", 1_850.00, "Faster Payments", cp("Business", "Mobile phone repair shop", "Customer", "2026-08-21"), "INV 003")

    # ---- numbering, alerts and history

    def finalise(self):
        rng = self.rng
        # Counterparty references rise with the date first seen.
        for i, c in enumerate(sorted(self.cps, key=lambda c: (c["first_seen_date"], c["entity_type"])), start=1):
            c["counterparty_id"] = f"CP-{i:03d}"
        self.rows["counterparties"] = sorted(
            [{k: c[k] for k in ["counterparty_id", "counterparty_type", "entity_type", "country_code", "relationship",
                                "linked_customer_id", "first_seen_date", "screening_status", "screening_date", "screening_notes"]}
             for c in self.cps if any(p["cp"] is c for p in self.pays)],
            key=lambda c: c["counterparty_id"])

        self.pays.sort(key=lambda p: p["when"])
        for i, p in enumerate(self.pays, start=1):
            p["payment_id"] = f"PAY-{i:04d}"
        alerts = self.alerts()
        status = {}
        for a in alerts:
            s = "Closed" if a["investigation_status"].startswith("Closed") else "Open"
            status[a["payment_id"]] = "Open" if "Open" in (s, status.get(a["payment_id"])) else "Closed"
        for p in self.pays:
            self.rows["payments"].append({
                "payment_id": p["payment_id"], "customer_id": p["cust"]["customer_id"],
                "payment_datetime": p["when"].strftime("%Y-%m-%d %H:%M:%S"), "direction": p["direction"],
                "amount_gbp": p["amount"], "payment_type": p["ptype"], "counterparty_id": p["cp"]["counterparty_id"],
                "channel": p["channel"], "origin_country": p["origin"], "destination_country": p["dest"],
                "payment_reference": p["ref"], "risk_score": self.score(p), "alert_status": status.get(p["payment_id"], "No alert"),
                "payment_status": p["status"]})
        self.rows["alerts"] = alerts
        self.history()

    def new_payee(self, p):
        first = D.fromisoformat(p["cp"]["first_seen_date"])
        return p["direction"] == "Outbound" and (p["when"].date() - first).days <= 30

    def credits(self, p):
        """Credits of £5,000 or more that reached p's account in the 24 hours before p."""
        cid = p["cust"]["customer_id"]
        out = []
        for q in self.pays:
            into = (q["direction"] == "Inbound" and q["cust"]["customer_id"] == cid) or \
                   (q["ptype"] == "Internal transfer" and q["cp"]["linked_customer_id"] == cid)
            if into and q["amount"] >= 5_000 and p["when"] - dt.timedelta(hours=24) <= q["when"] < p["when"]:
                out.append(q)
        return out

    def fired(self, p):
        """Rules from alert_rules that this payment meets. TM-04 runs monthly and has not run for September."""
        r = []
        personal = p["cust"]["segment"] == "Personal"
        if personal and p["amount"] >= 10_000:
            r.append("TM-01")
        if self.new_payee(p) and p["amount"] >= 5_000:
            r.append("TM-02")
        if p["direction"] == "Outbound" and any(p["amount"] >= 0.8 * q["amount"] for q in self.credits(p)):
            r.append("TM-03")
        if p["amount"] >= 1_000 and "High" in (COUNTRY_RISK[p["origin"]], COUNTRY_RISK[p["dest"]]):
            r.append("TM-05")
        if not personal and p["direction"] == "Outbound" and p["ptype"] == "SWIFT" and p["amount"] >= 50_000:
            r.append("TM-06")
        return r

    def alerts(self):
        rng = self.rng
        sev = {r[0]: r[7] for r in ALERT_RULES}
        out = []
        for p in self.pays:
            for rule in self.fired(p):
                key = (id(p), rule)
                if key not in self.handling:
                    raise RuntimeError(f"unplanned alert {rule} on {p['payment_id']} ({p['key']} {p['amount']} {p['ref']})")
                st, who, decision, ddate, evidence = self.handling.pop(key)
                out.append({"payment_id": p["payment_id"], "customer_id": p["cust"]["customer_id"],
                            "rule_id": rule, "raised_datetime": (p["when"] + dt.timedelta(seconds=rng.randint(20, 150))).strftime("%Y-%m-%d %H:%M:%S"),
                            "severity": sev[rule], "investigation_status": st, "assigned_to": who, "analyst_decision": decision,
                            "decision_date": ddate, "evidence_reference": evidence})
        if self.handling:
            raise RuntimeError(f"planned alerts that no rule raised: {[k[1] for k in self.handling]}")
        out.sort(key=lambda a: a["raised_datetime"])
        n = 48_170
        for a in out:
            n += rng.randint(3, 40)
            a["alert_id"] = f"ALR-{n:06d}"
        return [{"alert_id": a.pop("alert_id"), **a} for a in out]

    def score(self, p):
        base = {"Faster Payments": 10, "BACS": 4, "CHAPS": 14, "SWIFT": 20, "Internal transfer": 8}[p["ptype"]]
        s = base + min(26, 6 * math.log10(max(p["amount"], 100) / 100))
        s += {"High": 30, "Medium": 12, "Low": 0}[max((COUNTRY_RISK[p["origin"]], COUNTRY_RISK[p["dest"]]),
                                                     key=lambda r: ("Low", "Medium", "High").index(r))]
        s += {"High": 14, "Medium": 7, "Low": 0}[p["cust"]["risk_rating"]]
        s += 10 if self.new_payee(p) else 0
        s += 8 if (p["when"].date() - D.fromisoformat(p["cust"]["account_opened_date"])).days < 183 else 0
        s += self.rng.randint(-4, 4)
        return int(max(1, min(99, round(s))))

    def history(self):
        rng = self.rng
        n = 0
        for c in self.rows["customers"]:
            opened = D.fromisoformat(c["account_opened_date"])
            exp = c["expected_monthly_turnover_gbp"]
            business = c["segment"] == "Business"
            for month in HISTORY_MONTHS:
                y, m = map(int, month.split("-"))
                end = add_months(D(y, m, 1), 1) - dt.timedelta(days=1)
                if opened > end:
                    continue
                share = min(1.0, ((end - opened).days + 1) / 30) if opened.year == y and opened.month == m else 1.0
                cv = round(exp * rng.uniform(0.82, 1.12) * share, 2)
                dv = round(cv * rng.uniform(0.86, 1.03), 2)
                cn = max(1, round((rng.randint(28, 60) if business else rng.randint(2, 6)) * share))
                dn = max(1, round((rng.randint(20, 45) if business else rng.randint(9, 24)) * share))
                n += 1
                self.rows["monthly_activity"].append({"activity_id": f"MA-{n:04d}", "customer_id": c["customer_id"], "month": month,
                                                      "credits_count": cn, "credits_value_gbp": cv, "debits_count": dn,
                                                      "debits_value_gbp": dv})


# ------------------------------------------------------------------ rules (controls)

RULES = [
    ("R-01", "Alert handling", "Working alerts", "Every alert is assigned to an analyst and decided within 10 working days of being raised. High-severity alerts are worked first."),
    ("R-02", "Alert handling", "Closing an alert", "An analyst may close an alert with no further action only with a recorded reason and the evidence relied on, such as an invoice, contract or completion statement. A customer's explanation alone is not evidence."),
    ("R-03", "Alert handling", "Connected activity", "Before deciding an alert, the analyst reviews the customer's other payments and alerts for the last 30 days, and those of any counterparty that is also a Thameside customer. Connected alerts are decided together."),
    ("R-04", "Suspicious activity", "Patterns without an alert", "Rules do not catch every pattern. Several payments kept just below a threshold, funds passed quickly between accounts, or activity far outside the customer's normal pattern are reported to the Money Laundering Reporting Officer even if no alert was raised."),
    ("R-05", "Suspicious activity", "Internal reporting", "An analyst who knows or suspects money laundering escalates to the Money Laundering Reporting Officer, who decides whether to make a suspicious activity report to the National Crime Agency. Nobody tells the customer."),
    ("R-06", "Sanctions", "Screening before payment", "A payment may be released only to a counterparty whose screening status is Clear or Potential match - discounted. A payment to a counterparty that is Pending or Incomplete is held until screening is complete."),
    ("R-07", "Customer due diligence", "Periodic review", "Customers are reviewed every 12 months if rated High, 24 months if Medium and 36 months if Low. A High-risk customer whose review is overdue is referred to the Customer Due Diligence team, and new alerts on that customer are escalated to a Senior Investigator."),
    ("R-08", "Customer due diligence", "Profile", "A customer's expected turnover and expected activity are confirmed at onboarding and each review. Activity well outside them is a reason to ask the customer and to review the risk rating."),
]

RULE_TABLES = {
    "R-01": "alerts, alert_rules", "R-02": "alerts", "R-03": "alerts, payments, counterparties",
    "R-04": "payments, monthly_activity, customers", "R-05": "alerts, staff",
    "R-06": "payments, counterparties", "R-07": "customers, alerts", "R-08": "customers, monthly_activity, payments",
}

# ------------------------------------------------------------------ cases


def gbp(x):
    return f"£{x:,.2f}"


def record_cases(b):
    P = b.P
    rows = b.rows
    R = lambda p: p["payment_id"]  # noqa: E731
    cid = lambda k: b.cust[k]["customer_id"]  # noqa: E731
    alerts_on = lambda ps: [a for a in rows["alerts"] if a["payment_id"] in {R(p) for p in ps}]  # noqa: E731
    hist = defaultdict(list)
    for m in rows["monthly_activity"]:
        hist[m["customer_id"]].append(m)
    avg = lambda k, f: sum(m[f] for m in hist[cid(k)]) / len(hist[cid(k)])  # noqa: E731

    st = P["struct"]
    total = sum(p["amount"] for p in st)
    b.case("CASE-01", "Four payments just below the £10,000 alert threshold", "structuring_below_threshold",
           "Genuine exception", "Medium", "TM-01, R-04, R-08", "A5, A7, A12, A8",
           f"Customer {cid('S')}, a warehouse supervisor with expected turnover of £2,900 a month, sent four Faster Payments of "
           f"between £9,480 and £9,860 in three days, {gbp(total)} in all, to two personal payees. Each is just under the £10,000 "
           f"threshold of TM-01, so no alert was raised, and no rule looks at several payments together. The customer's debits "
           f"averaged {gbp(avg('S', 'debits_value_gbp'))} a month from March to August.",
           "Report to the Money Laundering Reporting Officer under R-04. Ask the customer where the money came from and what the payments were for; check the payees' other banking relationships if known.",
           """SELECT p.payment_id FROM payments p JOIN customers c ON c.customer_id = p.customer_id
              WHERE c.segment = 'Personal' AND p.direction = 'Outbound' AND p.amount_gbp >= 9000 AND p.amount_gbp < 10000
              AND (SELECT count(*) FROM payments q WHERE q.customer_id = p.customer_id AND q.direction = 'Outbound'
                   AND q.amount_gbp >= 9000 AND q.amount_gbp < 10000) >= 3""",
           [("payments", R(p), "payment just below the threshold", 1) for p in st]
           + [("customers", cid("S"), "customer far outside normal pattern", 0), ("alert_rules", "TM-01", "threshold avoided", 0)])

    bo = P["below_ok"]
    b.case("CASE-02", "Builders' merchant paying regular suppliers just under £10,000", "below_threshold_lookalike",
           "Benign lookalike", "None", "TM-01", "A5, A8",
           f"Customer {cid('M')}, a builders' merchant, paid two long-standing suppliers (a timber merchant and an aggregates supplier, "
           f"both paid since 2017 or earlier) £9,640.00 and £9,815.40 against invoice numbers. TM-01 applies only to personal customers, "
           f"the amounts are not round, and they fit the customer's turnover of about £85,000 a month.",
           "No action.",
           """SELECT p.payment_id FROM payments p JOIN customers c ON c.customer_id = p.customer_id
              WHERE c.segment = 'Business' AND p.amount_gbp >= 9000 AND p.amount_gbp < 10000""",
           [("payments", R(p), "supplier payment just under £10,000", 1) for p in bo])

    ch = P["chain"]
    ch_alerts = alerts_on(ch + [P["chain_in"]])
    b.case("CASE-03", "£24,500 passed through three new accounts to a High-risk jurisdiction in two days", "pass_through_chain",
           "Genuine exception", "High", "TM-03, TM-05, R-02, R-03, R-04", "A11, A6, A7, A8",
           f"On 15 September student {cid('A')} (account opened June 2026, expected turnover £900 a month) received £24,500 from an "
           f"individual first seen that day, and 29 minutes later moved £24,300 to sole trader {cid('B')} (opened July 2026). The next "
           f"morning {cid('B')} split it into two transfers of £12,000 and £12,100 to {cid('C')} (opened August 2026, same postcode "
           f"district as {cid('B')}). On 17 September {cid('C')} sent £23,900 by SWIFT to a trading company in Jurisdiction XB, rated High. "
           f"The split kept each transfer under 80% of the credit, so TM-03 did not fire at {cid('B')}, and {cid('C')}'s payment was made almost 26 hours "
           f"after the money arrived, outside TM-03's 24 hours. The {len(ch_alerts)} alerts on these payments are split between two analysts "
           f"and the unassigned queue. {cid('B')}'s two were closed on the customer's word, against R-02, and nobody linked them as R-03 requires.",
           "Escalate all three customers together to a Senior Investigator and the Money Laundering Reporting Officer; consider a suspicious activity report. Reopen the two closed alerts. Do not alert the customers.",
           """WITH RECURSIVE back(payment_id, payer, at, depth, end_id) AS (
                SELECT p.payment_id, p.customer_id, p.payment_datetime, 0, p.payment_id FROM payments p
                WHERE p.direction = 'Outbound' AND p.destination_country <> 'GB'
                UNION ALL
                SELECT q.payment_id, q.customer_id, q.payment_datetime, b.depth + 1, b.end_id FROM back b
                JOIN counterparties c ON c.linked_customer_id = b.payer
                JOIN payments q ON q.counterparty_id = c.counterparty_id AND q.direction = 'Outbound'
                 AND q.payment_datetime < b.at AND q.payment_datetime >= datetime(b.at, '-48 hours'))
              SELECT DISTINCT payment_id FROM back WHERE end_id IN (SELECT end_id FROM back GROUP BY end_id HAVING max(depth) >= 2)""",
           [("payments", R(p), "hop in the chain", 1) for p in ch]
           + [("payments", R(P["chain_in"]), "credit that started the chain", 0)]
           + [("alerts", a["alert_id"], f"{a['rule_id']} alert, {a['investigation_status']}", 0) for a in ch_alerts]
           + [("customers", cid(k), "account in the chain", 0) for k in ("A", "B", "C")])

    g = P["gift"]
    b.case("CASE-04", "Gifted house deposit passed from parent to child to solicitor", "pass_through_lookalike",
           "Benign lookalike", "None", "TM-01, TM-03, R-03", "A11, A7, A8",
           f"Retired customer {cid('P')} transferred £45,000 to {cid('K')}, a Thameside customer and family member paid before, "
           f"with the reference 'Gift towards house deposit'. The next morning {cid('K')} paid £61,750 by CHAPS to the solicitors "
           f"paid in August for the purchase. The funds moved fast and raised a High TM-03 alert, but they went to a regulated "
           f"solicitor for a named property, and the analyst on {cid('P')}'s alert saw a signed gift letter.",
           "Close the open alerts on the customer's account, citing the gift letter and the solicitor's letter.",
           """SELECT p.payment_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
              WHERE c.linked_customer_id IS NOT NULL AND EXISTS (SELECT 1 FROM payments q JOIN counterparties d ON d.counterparty_id = q.counterparty_id
                WHERE q.customer_id = c.linked_customer_id AND d.entity_type LIKE 'Solicitors%'
                AND q.payment_datetime > p.payment_datetime AND q.payment_datetime <= datetime(p.payment_datetime, '+48 hours'))
              UNION
              SELECT q.payment_id FROM payments q JOIN counterparties d ON d.counterparty_id = q.counterparty_id
              WHERE d.entity_type LIKE 'Solicitors%' AND q.direction = 'Outbound' AND EXISTS (SELECT 1 FROM payments p
                JOIN counterparties c ON c.counterparty_id = p.counterparty_id WHERE c.linked_customer_id = q.customer_id
                AND q.payment_datetime > p.payment_datetime AND q.payment_datetime <= datetime(p.payment_datetime, '+48 hours'))""",
           [("payments", R(p), "step in the gifted deposit", 1) for p in g]
           + [("alerts", a["alert_id"], f"{a['rule_id']} alert", 0) for a in alerts_on(g)])

    cf = P["cafe"]
    ins = [p for p in cf if p["direction"] == "Inbound"]
    b.case("CASE-05", "Café receives money from seven strangers and sends it to a cryptoasset exchange", "sudden_change_in_activity",
           "Genuine exception", "High", "TM-02, R-03, R-04, R-08", "A12, A5, A8",
           f"Customer {cid('F')}, a café whose account normally receives card settlements, received {len(ins)} Faster Payments from "
           f"{len(ins)} different individuals in four days, {gbp(sum(p['amount'] for p in ins))} in all, several of them late in the evening, with "
           f"references such as 'Payment' and 'Invoice'. None of the payers had paid any Thameside customer before. On 18 September it "
           f"sent £27,500 to a cryptoasset exchange first seen that day. Its credits averaged {gbp(avg('F', 'credits_value_gbp'))} a "
           f"month from March to August. The only alert is a Low-severity TM-02 on the last payment, unassigned in a queue with five "
           f"innocent TM-02 alerts. TM-04 runs monthly and will not see September until 1 October.",
           "Raise the alert's priority, review the account with R-03 in mind, and escalate to the Money Laundering Reporting Officer; the pattern fits an account used to collect and convert third-party funds.",
           """WITH sus AS (SELECT p.customer_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
                WHERE p.direction = 'Inbound' AND c.counterparty_type = 'Individual'
                AND c.first_seen_date >= date(p.payment_datetime, '-30 days')
                GROUP BY p.customer_id HAVING count(DISTINCT p.counterparty_id) >= 5)
              SELECT p.payment_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
              WHERE p.customer_id IN (SELECT customer_id FROM sus) AND c.first_seen_date >= date(p.payment_datetime, '-30 days')""",
           [("payments", R(p), "payment from a new individual payer" if p["direction"] == "Inbound" else "payment to a new cryptoasset exchange", 1) for p in cf]
           + [("alerts", a["alert_id"], "Low-severity alert, unassigned", 0) for a in alerts_on(cf)]
           + [("customers", cid("F"), "customer with a sudden change", 0)])

    s = P["sale"]
    b.case("CASE-06", "Retired customer receives £318,450 from a house sale", "sudden_change_lookalike",
           "Benign lookalike", "None", "TM-01, R-08", "A12, A8",
           f"Customer {cid('H')} normally receives about {gbp(avg('H', 'credits_value_gbp'))} a month. On 14 September £318,450 arrived by "
           f"CHAPS from a firm of solicitors with the reference 'SALE 41 TIDEMILL ROAD COMPLETION'. The TM-01 alert was closed with the "
           f"completion statement as evidence.",
           "No action.",
           """SELECT p.payment_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
              WHERE p.direction = 'Inbound' AND c.entity_type LIKE 'Solicitors%'
              AND p.amount_gbp > 3 * (SELECT max(m.credits_value_gbp) FROM monthly_activity m WHERE m.customer_id = p.customer_id)""",
           [("payments", R(s), "house sale proceeds", 1)] + [("alerts", a["alert_id"], "TM-01 alert, closed with evidence", 0) for a in alerts_on([s])])

    inc = P["incomplete"]
    cp_inc = inc[0]["cp"]["counterparty_id"]
    b.case("CASE-07", "£78,000 released to a supplier whose screening is incomplete", "incomplete_screening",
           "Genuine exception", "High", "R-06", "A3, A7, A8",
           f"Customer {cid('W')} paid £36,800 and £41,200 by SWIFT to {cp_inc}, an electronics manufacturer in Jurisdiction XC, first "
           f"seen on 3 August 2026. Its screening is Incomplete: the name was screened but its beneficial owners and address were never "
           f"provided. R-06 says the payments should have been held. Neither raised an alert: the payee was first seen more than 30 days "
           f"earlier, XC is rated Medium, and each payment is under TM-06's £50,000.",
           "Refer to the Sanctions Screening Lead; obtain the beneficial owners and screen them; hold further payments to the supplier; find out why the payment system released them.",
           """SELECT p.payment_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
              WHERE c.screening_status IN ('Incomplete', 'Pending') AND p.payment_status = 'Completed'""",
           [("payments", R(p), "payment released despite incomplete screening", 1) for p in inc]
           + [("counterparties", cp_inc, "counterparty with incomplete screening", 0)])

    h = P["held"]
    b.case("CASE-08", "Payment to a new overseas payee correctly held for screening", "screening_hold_lookalike",
           "Benign lookalike", "None", "R-06", "A3, A8",
           f"Customer {cid('N8')}, a care worker who expects to send small sums to family abroad, asked in branch to send £2,750 to a "
           f"family member in Jurisdiction XD, rated Low. The payee is Pending screening, so the payment is held, as R-06 requires.",
           "No action beyond completing the screening.",
           """SELECT p.payment_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
              WHERE c.screening_status IN ('Incomplete', 'Pending') AND p.payment_status LIKE 'Held%'""",
           [("payments", R(h), "payment held pending screening", 1), ("counterparties", h["cp"]["counterparty_id"], "payee pending screening", 0)])

    dc = P["discounted"]
    b.case("CASE-09", "Payee whose name resembles a sanctioned person, already discounted", "screening_match_lookalike",
           "Benign lookalike", "None", "R-06", "A3, A8",
           f"Customer {cid('Q')} paid a haulage subcontractor £4,200. The subcontractor's name resembles an entry on the UK sanctions list, "
           f"but its date of birth and nationality differ. The sanctions team discounted the match in 2023 and again on 3 August 2026, so "
           f"R-06 allows the payment.",
           "No action.",
           """SELECT p.payment_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
              WHERE c.screening_status = 'Potential match - discounted'""",
           [("payments", R(dc), "payment to a discounted match", 1), ("counterparties", dc["cp"]["counterparty_id"], "discounted match", 0)])

    inn = P["innocent"]
    inn_alerts = alerts_on(inn)
    b.case("CASE-10", "Five new-payee alerts for school fees, halls, a car, a kitchen and a wedding", "same_alert_lookalike",
           "Benign lookalike", "None", "TM-02", "A8",
           "Five personal customers each paid £5,500 to £8,450 to a payee they had not paid before: an independent school's autumn "
           "term fees, university halls of residence, a car dealer's deposit, a kitchen fitter's deposit and a wedding venue's balance. "
           "Each raised a Low TM-02 alert. The references, the payee types and the customers' incomes all fit, and September is when "
           "school and university fees fall due.",
           "Close each alert with the payment reference and payee type as the reason; consider excluding education providers from TM-02.",
           """SELECT a.alert_id FROM alerts a JOIN payments p ON p.payment_id = a.payment_id
              JOIN customers cu ON cu.customer_id = p.customer_id JOIN counterparties c ON c.counterparty_id = p.counterparty_id
              WHERE a.rule_id = 'TM-02' AND cu.segment = 'Personal' AND c.counterparty_type <> 'Individual'
              AND c.linked_customer_id IS NULL AND p.destination_country = 'GB'""",
           [("alerts", a["alert_id"], "innocent TM-02 alert", 1) for a in inn_alerts]
           + [("payments", R(p), "payment that raised it", 0) for p in inn])

    e = b.cust["E"]
    b.case("CASE-11", "High-risk customer three months overdue for review, alert closed on stale due diligence", "overdue_review",
           "Genuine exception", "Medium", "R-07, R-02", "A3, A7, A8",
           f"Customer {e['customer_id']}, a textile importer rated High because it trades with Jurisdiction XA, was last reviewed on "
           f"{e['last_review_date']}; its review was due on {e['next_review_due']}. On 15 September it received £18,400 from a buyer in XA. "
           f"The TM-05 alert was closed the next day by an analyst who cited 'enhanced due diligence on file', but that due diligence "
           f"is out of date, and R-07 says the alert should have gone to a Senior Investigator.",
           "Refer the customer to the Customer Due Diligence team for an immediate review, reopen the alert for a Senior Investigator, and check other closed alerts on overdue High-risk customers.",
           "SELECT c.customer_id FROM customers c WHERE c.risk_rating = 'High' AND c.next_review_due < '2026-09-22'",
           [("customers", e["customer_id"], "High-risk customer overdue for review", 1), ("payments", R(P["edd_pay"]), "payment from XA", 0)]
           + [("alerts", a["alert_id"], "alert closed on out-of-date due diligence", 0) for a in alerts_on([P["edd_pay"]])])

    l = b.cust["L"]
    b.case("CASE-12", "High-risk customer whose review is due soon, not overdue", "review_due_lookalike",
           "Benign lookalike", "None", "R-07", "A3, A7",
           f"Customer {l['customer_id']}, a hand car wash rated High as a cash-intensive business, was last reviewed on {l['last_review_date']}. "
           f"Its next review is due on {l['next_review_due']}, after the extract date, so it is not overdue.",
           "No action now; the review is scheduled.",
           "SELECT c.customer_id FROM customers c WHERE c.risk_rating = 'High' AND c.next_review_due BETWEEN '2026-09-22' AND date('2026-09-22', '+30 days')",
           [("customers", l["customer_id"], "High-risk customer with a review due soon", 1)])


NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
APP_OPENING_LAUNCH = D(2026, 7, 1)
SCREENING_SYSTEM_LIVE = D(2026, 8, 1)


def business_story(rows):
    """The firm's current situation. Paragraphs are separated by blank lines; lines starting '- ' are list items.
    Every figure is calculated from the rows, and checks() tests every claim against the data."""
    pays, alerts, rules = rows["payments"], rows["alerts"], rows["alert_rules"]
    analysts = sum(1 for s_ in rows["staff"] if s_["job_title"] == "Financial Crime Analyst")
    newest = max(rules, key=lambda r: r["effective_from"])
    newest_date = D.fromisoformat(newest["effective_from"])
    closed = sum(1 for a in alerts if a["investigation_status"].startswith("Closed"))
    investigating = sum(1 for a in alerts if a["investigation_status"] == "Under investigation")
    open_ = [a for a in alerts if a["investigation_status"].startswith("Open")]
    unassigned = sum(1 for a in open_ if a["investigation_status"] == "Open - unassigned")
    total = sum(p["amount_gbp"] for p in pays)
    return "\n".join([
        "Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. It serves personal customers and "
        f"small businesses across London and the South East. Its financial crime team checks payments against "
        f"{NUMBER_WORDS[len(rules)]} monitoring rules. Every alert must be reviewed, and either closed with a reason or escalated.",
        "",
        "Several pressures have built up this year:",
        f"- More alerts than people. Alert numbers rose after the newest rule, {newest['rule_name'].lower()}, was added in "
        f"{newest_date.strftime('%B %Y')}. The team has grown to {NUMBER_WORDS[analysts]} analysts, and some are still "
        "building experience.",
        "- Faster account opening. In July the bank launched app-based account opening, so personal accounts can now open "
        "within minutes.",
        "- Due diligence backlog. Periodic reviews of higher-risk customers fell behind when the due diligence team moved to Croydon.",
        "- New screening system. In August, sanctions screening moved to a new system. The team is still working through "
        "records carried over from the old one.",
        "- Board attention. After another bank was fined for weak monitoring, the board asked for assurance that alerts "
        "are being handled properly.",
        "",
        "The Money Laundering Reporting Officer asked for a review of one week's alerts, raised from "
        f"{WEEK_START.day} to {WEEK_END.day} {WEEK_END.strftime('%B %Y')}. The week holds {len(pays)} payments worth "
        f"£{total:,.2f}. They raised {len(alerts)} alerts:",
        f"- {closed} are closed.",
        f"- {investigating} are under investigation.",
        f"- {len(open_)} are still open, {unassigned} of them not yet assigned to anyone.",
    ])


def build(rng):
    b = Builder(rng)
    b.lookups()
    b.week()
    b.finalise()
    record_cases(b)
    rules = [{"rule_id": r, "category": c, "title": t, "statement": s, "related_tables": RULE_TABLES[r]}
             for r, c, t, s in RULES]
    facts = [
        ("dataset", "aml"),
        ("title", "AML transaction monitoring"),
        ("firm", firm.FIRM_NAME),
        ("bank", "Thameside Bank, the group's retail and commercial bank"),
        ("scenario", "The financial-crime team reviews the payment-monitoring alerts raised in one week of customer payments."),
        ("period", "Payments 2026-09-14 to 2026-09-20; customer history 2026-03 to 2026-08"),
        ("extract_date", EXTRACT.strftime("%Y-%m-%d %H:%M")),
        ("currency", "GBP"),
        ("seed", firm.SEED),
        ("disclaimer", firm.DISCLAIMER + " Jurisdictions XA to XD are fictional. Customers and counterparties are identified by "
                                         "reference only. The monitoring rules and risk scores are invented for the study and are "
                                         "not a validated detection model."),
        ("business_context", business_story(b.rows)),
    ]
    return SCHEMA, dict(b.rows), facts, rules, b.cases, b.case_records


# ------------------------------------------------------------------ checks


def checks(con):
    errors = []
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731

    # Staff must match the firm-wide register.
    cur = con.execute("SELECT staff_id, first_name, last_name, job_title, office FROM staff")
    cols = [c[0] for c in cur.description]
    errors += staff_register.check([dict(zip(cols, r)) for r in cur.fetchall()], "staff_id", STAFF_REGISTER_IDS)

    # The business story's claims must hold in the data.
    claims = [
        (q("SELECT count(*) FROM staff WHERE job_title = 'Financial Crime Analyst'")[0][0] in NUMBER_WORDS,
         "the number of analysts can be written as a word"),
        (q("SELECT office FROM staff WHERE job_title = 'Customer Due Diligence Team Leader'")[0][0] == "Croydon",
         "the due diligence team is in Croydon"),
        (q("SELECT count(*) FROM customers WHERE account_opened_date >= ?", APP_OPENING_LAUNCH.isoformat())[0][0] > 0,
         "accounts have opened since app-based opening launched in July 2026"),
        (q("SELECT count(*) FROM counterparties WHERE screening_date >= ?", SCREENING_SYSTEM_LIVE.isoformat())[0][0] > 0,
         "counterparties have been screened on the new system since August 2026"),
        (q("SELECT count(*) FROM alert_rules WHERE effective_from >= '2026-01-01'")[0][0] == 0,
         "no rule was added this year (the story dates the newest rule)"),
    ]
    errors += [f"story: {text} is not true in the data" for ok, text in claims if not ok]

    ranges = {"payments": (95, 105), "customers": (20, 35), "counterparties": (40, 75), "alerts": (15, 35),
              "monthly_activity": (100, 200)}
    for t, (lo, hi) in ranges.items():
        n = q(f"SELECT count(*) FROM {t}")[0][0]
        if not lo <= n <= hi:
            errors.append(f"{t}: {n} rows, expected {lo}-{hi}")

    # Payment timing follows the schemes' operating days and hours.
    for pid, ts, ptype in q("SELECT payment_id, payment_datetime, payment_type FROM payments"):
        when = dt.datetime.fromisoformat(ts)
        if not WEEK_START <= when.date() <= WEEK_END:
            errors.append(f"{pid}: outside the week")
        if ptype in ("BACS", "CHAPS", "SWIFT") and not uk.is_working_day(when.date()):
            errors.append(f"{pid}: {ptype} on a non-working day")
        if ptype == "CHAPS" and not dt.time(6) <= when.time() <= dt.time(18):
            errors.append(f"{pid}: CHAPS outside 06:00-18:00")
    for (pid,) in q("""SELECT payment_id FROM payments WHERE (direction = 'Outbound' AND origin_country <> 'GB')
                      OR (direction = 'Inbound' AND destination_country <> 'GB')"""):
        errors.append(f"{pid}: origin or destination does not match direction")
    for (pid,) in q("""SELECT p.payment_id FROM payments p JOIN counterparties c ON c.counterparty_id = p.counterparty_id
                      WHERE (p.payment_type = 'Internal transfer') <> (c.linked_customer_id IS NOT NULL)
                      OR c.linked_customer_id = p.customer_id OR c.first_seen_date > date(p.payment_datetime)"""):
        errors.append(f"{pid}: counterparty link, type or first-seen date is inconsistent")
    for (pid,) in q("""SELECT p.payment_id FROM payments p JOIN customers c ON c.customer_id = p.customer_id
                      WHERE c.account_opened_date > date(p.payment_datetime)"""):
        errors.append(f"{pid}: before the account was opened")
    # alert_status on each payment agrees with its alerts.
    for pid, st, derived in q("""SELECT p.payment_id, p.alert_status, CASE WHEN count(a.alert_id) = 0 THEN 'No alert'
                                 WHEN sum(a.investigation_status NOT LIKE 'Closed%') > 0 THEN 'Open' ELSE 'Closed' END
                                 FROM payments p LEFT JOIN alerts a ON a.payment_id = p.payment_id GROUP BY p.payment_id"""):
        if st != derived:
            errors.append(f"{pid}: alert_status {st}, alerts say {derived}")
    for (aid,) in q("""SELECT alert_id FROM alerts WHERE (investigation_status LIKE 'Closed%') <> (analyst_decision IS NOT NULL)
                      OR (investigation_status = 'Open - unassigned') <> (assigned_to IS NULL)"""):
        errors.append(f"{aid}: status, analyst and decision disagree")
    for (aid,) in q("""SELECT a.alert_id FROM alerts a JOIN payments p ON p.payment_id = a.payment_id
                      JOIN alert_rules r ON r.rule_id = a.rule_id WHERE a.severity <> r.severity
                      OR a.customer_id <> p.customer_id OR a.raised_datetime < p.payment_datetime
                      OR a.raised_datetime > '2026-09-22 18:00:00'"""):
        errors.append(f"{aid}: alert inconsistent with its payment or rule")
    # Review dates follow R-07, and no history month would have raised TM-04.
    for c_id, risk, last, nxt in q("SELECT customer_id, risk_rating, last_review_date, next_review_due FROM customers"):
        if nxt != iso(add_months(D.fromisoformat(last), REVIEW_MONTHS[risk])):
            errors.append(f"{c_id}: next review does not follow the review cycle")
    for c_id, month in q("""SELECT m.customer_id, m.month FROM monthly_activity m JOIN customers c ON c.customer_id = m.customer_id
                           WHERE m.credits_value_gbp > 2 * c.expected_monthly_turnover_gbp"""):
        errors.append(f"{c_id}: {month} credits would have raised TM-04")
    for t, col, prefix in (("payments", "payment_datetime", "payment_id"), ("alerts", "raised_datetime", "alert_id"),
                           ("customers", "account_opened_date", "customer_id"), ("counterparties", "first_seen_date", "counterparty_id")):
        for a, b_ in q(f"""SELECT x.{prefix}, y.{prefix} FROM {t} x JOIN {t} y ON x.{col} < y.{col} AND x.{prefix} > y.{prefix}"""):
            errors.append(f"{t}: {a} is numbered after {b_} but is earlier")
    for (email,) in q("SELECT email FROM staff"):
        if not email.endswith("@" + firm.EMAIL_DOMAIN):
            errors.append(f"{email}: wrong domain")
    return errors
