"""Regulatory reporting and data lineage dataset.

Thameside Financial Group's regulatory reporting team prepares the September 2026 Monthly Balance Sheet
Return (MBSR). Each row of reporting_records is one source balance: a commercial facility, a business
deposit account, or a pool of retail accounts, taken from one of four source systems, mapped to a return
line by a versioned mapping rule. The draft return was prepared on Tuesday 6 October 2026 and awaits review.
"""

import datetime as dt
from collections import defaultdict

from generator.common import firm, uk
from generator.common.dataset import Col, Table
from generator.common import staff_register
from generator.common.people import email_for

D = dt.date
PERIOD = "2026-09"
AS_AT = D(2026, 9, 30)
PRIOR = "2026-08"
EXTRACT_DATE = D(2026, 10, 6)  # draft return prepared; dataset taken at close of business
SME_TURNOVER_LIMIT = 25_000_000

# ------------------------------------------------------------------ schema


def C(*a, **k):
    return Col(*a, **k)


SCHEMA = [
    Table("staff", "lookup", "People in the reporting, data and finance teams who appear in the records.", [
        C("staff_id", "TEXT", "Staff identifier."),
        C("first_name", "TEXT", "First name."),
        C("last_name", "TEXT", "Surname."),
        C("job_title", "TEXT", "Job title."),
        C("team", "TEXT", "Team."),
        C("office", "TEXT", "Office: City, Canary Wharf or Croydon."),
        C("email", "TEXT", "Work email address."),
    ]),
    Table("entities", "lookup", "Legal entities of the group and whether each is in the scope of the return.", [
        C("entity_code", "TEXT", "Entity code, for example ENT-LON-01."),
        C("entity_name", "TEXT", "Entity name."),
        C("entity_type", "TEXT", "What the entity does."),
        C("in_return_scope", "INTEGER", "1 if the entity's balances are reported in the consolidated return."),
        C("office", "TEXT", "Office the entity is run from."),
    ]),
    Table("source_systems", "lookup", "Operational systems that supply balances to the return.", [
        C("source_system", "TEXT", "System name."),
        C("description", "TEXT", "What the system holds."),
        C("data_owner_id", "TEXT", "Person accountable for the system's data.", "staff.staff_id"),
        C("extract_schedule", "TEXT", "When the month-end extract is due to run."),
    ]),
    Table("products", "lookup", "Product codes used by the source systems.", [
        C("product_code", "TEXT", "Product code."),
        C("description", "TEXT", "Product."),
        C("source_system", "TEXT", "System that holds the product.", "source_systems.source_system"),
        C("customer_segment", "TEXT", "Customers the product is sold to: Household, SME, Large corporate, Property company or Commercial real estate."),
        C("balance_type", "TEXT", "Asset (lending) or Liability (deposits)."),
        C("launched_date", "TEXT", "Date the product was first sold."),
    ]),
    Table("return_lines", "lookup", "Lines of the Monthly Balance Sheet Return (MBSR) template.", [
        C("line_code", "TEXT", "Line code, for example L30."),
        C("line_name", "TEXT", "Line name."),
        C("section", "TEXT", "Lending (assets) or Deposits (liabilities)."),
        C("description", "TEXT", "What the line holds."),
        C("effective_from", "TEXT", "First period-end date the line is reported."),
        C("effective_to", "TEXT", "Last period-end date the line is reported. Empty if still in use.", required=False),
    ]),
    Table("counterparties", "lookup", "Business customers behind commercial facilities and business deposits. Names are withheld; customers are identified by reference.", [
        C("counterparty_id", "TEXT", "Customer reference."),
        C("sector_code", "TEXT", "UK SIC 2007 section letter."),
        C("sector", "TEXT", "UK SIC 2007 section name."),
        C("size_class", "TEXT", "SME, Large corporate or Intragroup, set from latest filed accounts (reporting rule RR-06)."),
        C("annual_turnover_gbp", "REAL", "Turnover in the latest filed accounts. Empty for group entities.", required=False),
        C("accounts_date", "TEXT", "Year-end date of the latest filed accounts.", required=False),
        C("country", "TEXT", "Country of incorporation, ISO code."),
        C("group_entity_code", "TEXT", "Entity code if the customer is part of the group.", "entities.entity_code", required=False),
        C("onboarded_date", "TEXT", "Date the customer was onboarded."),
    ]),
    Table("field_dictionary", "lookup", "Source fields the return calculation reads, with definitions, types, valid values and validity dates.", [
        C("field_id", "TEXT", "Field identifier."),
        C("source_system", "TEXT", "System the field belongs to.", "source_systems.source_system"),
        C("field_name", "TEXT", "Field name as it appears in the extract."),
        C("definition", "TEXT", "What the field means."),
        C("data_type", "TEXT", "Data type in the extract."),
        C("valid_values", "TEXT", "Allowed values or range.", required=False),
        C("feeds_column", "TEXT", "reporting_records column the field populates."),
        C("valid_from", "TEXT", "First date the field is valid in the extract."),
        C("valid_to", "TEXT", "Last date the field is valid. Empty if still valid.", required=False),
    ]),
    Table("change_log", "business", "Schema changes, mapping amendments, template changes and reference-data changes, with their effective dates.", [
        C("change_id", "TEXT", "Change identifier."),
        C("logged_date", "TEXT", "Date the change was logged."),
        C("effective_date", "TEXT", "Date the change takes effect."),
        C("change_type", "TEXT", "Schema change, Mapping amendment, Template change, Dictionary update or Reference data."),
        C("source_system", "TEXT", "System affected, if any.", "source_systems.source_system", required=False),
        C("object_changed", "TEXT", "Field, rule, line or product changed."),
        C("old_value", "TEXT", "Value before the change.", required=False),
        C("new_value", "TEXT", "Value after the change.", required=False),
        C("description", "TEXT", "What changed and why."),
        C("requested_by", "TEXT", "Person who asked for the change.", "staff.staff_id"),
        C("approved_by", "TEXT", "Person who approved it.", "staff.staff_id"),
        C("status", "TEXT", "Implemented, or Approved - not yet effective."),
    ]),
    Table("mapping_rules", "lookup", "Versioned rules that map each product code to a return line, with effective dates.", [
        C("mapping_rule_id", "TEXT", "Rule identifier."),
        C("mapping_version", "TEXT", "Version of the mapping set the rule belongs to, V1 to V4."),
        C("product_code", "TEXT", "Product the rule maps.", "products.product_code"),
        C("line_code", "TEXT", "Return line the product maps to.", "return_lines.line_code"),
        C("effective_from", "TEXT", "First period-end date the rule applies to."),
        C("effective_to", "TEXT", "Last period-end date the rule applies to. Empty if open.", required=False),
        C("change_id", "TEXT", "Change that introduced the rule.", "change_log.change_id"),
        C("approved_by", "TEXT", "Person who approved the rule.", "staff.staff_id"),
    ]),
    Table("reporting_rules", "lookup", "The return's own instructions: inclusion criteria, calculation and aggregation.", [
        C("reporting_rule_id", "TEXT", "Rule identifier, for example RR-04."),
        C("rule_type", "TEXT", "Inclusion, Calculation, Classification or Aggregation."),
        C("statement", "TEXT", "The rule in full."),
        C("applies_to", "TEXT", "Lines or records the rule applies to."),
    ]),
    Table("fx_rates", "lookup", "Bank of England daily spot rates against sterling, quoted as units of currency per £1.", [
        C("fx_rate_id", "TEXT", "Rate identifier."),
        C("currency", "TEXT", "ISO currency code."),
        C("rate_date", "TEXT", "Date of the rate."),
        C("rate", "REAL", "Units of currency per £1."),
        C("source", "TEXT", "Where the rate comes from."),
    ]),
    Table("reporting_records", "business", "Primary table: one row per source balance feeding the September 2026 return, with its lineage from source field to return line.", [
        C("record_id", "TEXT", "Record identifier, for example RPT-0084."),
        C("reporting_period", "TEXT", "Return period, YYYY-MM."),
        C("as_at_date", "TEXT", "Balance date: the period-end date."),
        C("entity_code", "TEXT", "Group entity that holds the balance.", "entities.entity_code"),
        C("source_system", "TEXT", "System the balance came from.", "source_systems.source_system"),
        C("source_record_ref", "TEXT", "Facility, account or pool reference in the source system."),
        C("record_type", "TEXT", "Facility, Account (one customer) or Portfolio (a pool of retail accounts)."),
        C("number_of_accounts", "INTEGER", "Accounts in the record: 1 for a facility or account, more for a portfolio."),
        C("product_code", "TEXT", "Product code from the source system.", "products.product_code"),
        C("counterparty_id", "TEXT", "Business customer, if any. Empty for retail portfolios.", "counterparties.counterparty_id", required=False),
        C("start_date", "TEXT", "Date the facility or account started. Empty for portfolios.", required=False),
        C("maturity_date", "TEXT", "Contractual maturity or review date. Empty if none.", required=False),
        C("account_status", "TEXT", "Status in the source system: Active or Closed."),
        C("source_field", "TEXT", "Extract field the balance was read from."),
        C("currency", "TEXT", "Currency of the balance."),
        C("source_amount", "REAL", "Balance in the source currency, as extracted."),
        C("fx_rate", "REAL", "Rate used to convert to sterling, units of currency per £1. 1 for GBP."),
        C("amount_gbp", "REAL", "source_amount divided by fx_rate, rounded to the penny."),
        C("mapping_rule_id", "TEXT", "Mapping rule applied.", "mapping_rules.mapping_rule_id"),
        C("mapping_version", "TEXT", "Version of the mapping rule applied."),
        C("line_code", "TEXT", "Return line the record was mapped to.", "return_lines.line_code"),
        C("included_in_return", "TEXT", "Yes or No."),
        C("exclusion_reason", "TEXT", "Why the record was left out. Empty if included.", required=False),
        C("reported_amount_gbp", "REAL", "Amount the return calculation used for this record. Empty if excluded.", required=False),
        C("extracted_at", "TEXT", "Date and time the source extract ran, ISO format."),
    ]),
    Table("control_totals", "business", "Expected totals from the general ledger by source system, product and currency at the period end.", [
        C("control_id", "TEXT", "Control identifier."),
        C("reporting_period", "TEXT", "Return period."),
        C("source_system", "TEXT", "Source system the control checks.", "source_systems.source_system"),
        C("product_code", "TEXT", "Product the control checks.", "products.product_code"),
        C("currency", "TEXT", "Currency of the control amount."),
        C("gl_account", "TEXT", "General-ledger account."),
        C("control_amount", "REAL", "General-ledger balance after end-of-day processing on the period-end date, in the control currency."),
        C("tolerance", "REAL", "Largest difference accepted without investigation, in the control currency."),
        C("control_source", "TEXT", "Where the control figure comes from."),
        C("notes", "TEXT", "Notes from the finance team.", required=False),
    ]),
    Table("return_figures", "business", "The return as reported: one row per line for the submitted August return and the draft September return.", [
        C("figure_id", "TEXT", "Figure identifier."),
        C("reporting_period", "TEXT", "Return period."),
        C("line_code", "TEXT", "Return line.", "return_lines.line_code"),
        C("reported_amount_gbp", "REAL", "Figure on the return, in pounds."),
        C("record_count", "INTEGER", "Number of reporting records behind the figure."),
        C("status", "TEXT", "Submitted, or Draft - awaiting review."),
        C("prepared_by", "TEXT", "Preparer.", "staff.staff_id"),
        C("prepared_date", "TEXT", "Date prepared."),
        C("reviewed_by", "TEXT", "Reviewer. Empty until reviewed.", "staff.staff_id", required=False),
        C("approved_by", "TEXT", "Approver. Empty until approved.", "staff.staff_id", required=False),
        C("submitted_date", "TEXT", "Date submitted. Empty for a draft.", required=False),
    ]),
]

# ------------------------------------------------------------------ reference data

# Appraisal types each planted case needs (IDs from docs/appraisal-types.html).
APPRAISAL = {
    "CASE-01": "A9, A7", "CASE-02": "A9, A3", "CASE-03": "A9, A8", "CASE-04": "A7, A9", "CASE-05": "A7, A8",
    "CASE-06": "A1, A3", "CASE-07": "A3, A8", "CASE-08": "A1, A5", "CASE-09": "A1, A8", "CASE-10": "A3",
    "CASE-11": "A3, A8", "CASE-12": "A9, A7",
}

# Each staff member's entry in the firm-wide staff register (generator/common/staff_register.py).
STAFF_REGISTER_IDS = {'STF-01': 'TFG-001', 'STF-02': 'TFG-021', 'STF-03': 'TFG-022', 'STF-04': 'TFG-023', 'STF-05': 'TFG-024', 'STF-06': 'TFG-025', 'STF-07': 'TFG-026', 'STF-08': 'TFG-027', 'STF-09': 'TFG-028', 'STF-10': 'TFG-029', 'STF-11': 'TFG-020'}

STAFF = [
    # id, title, team, office, gender
    ("STF-01", "Chief Financial Officer", "Finance leadership", "City", "f"),
    ("STF-02", "Head of Regulatory Reporting", "Regulatory Reporting", "City", "m"),
    ("STF-03", "Regulatory Reporting Manager", "Regulatory Reporting", "City", "f"),
    ("STF-04", "Regulatory Reporting Analyst", "Regulatory Reporting", "City", "m"),
    ("STF-05", "Regulatory Reporting Analyst", "Regulatory Reporting", "Croydon", "f"),
    ("STF-06", "Data Governance Lead", "Finance Data", "Canary Wharf", "f"),
    ("STF-07", "Finance Systems Analyst", "Finance Data", "Canary Wharf", "m"),
    ("STF-08", "LendingCore Product Owner", "Technology", "Canary Wharf", "m"),
    ("STF-09", "Retail Systems Product Owner", "Technology", "Canary Wharf", "f"),
    ("STF-10", "Credit Risk Data Manager", "Credit Risk", "Croydon", "m"),
    ("STF-11", "Financial Controller", "Finance", "City", "m"),
]

ENTITIES = [
    ("ENT-GRP-00", "Thameside Financial Group plc", "Holding company. Holds no customer balances.", 0, "City"),
    ("ENT-LON-01", "Thameside Bank", "Deposit-taking bank: mortgages, retail credit, SME lending and all deposits.", 1, "City"),
    ("ENT-CRO-01", "Thameside Commercial Finance", "Commercial real estate and large corporate lending.", 1, "Croydon"),
]

SOURCE_SYSTEMS = [
    ("LendingCore", "Commercial lending: SME, commercial real estate and corporate facilities.", "STF-08", "After end-of-day, 01:00-03:00 on the first day of the next month"),
    ("MortgageHub", "Residential and buy-to-let mortgage book, held as portfolios.", "STF-09", "After end-of-day, 01:00-03:00 on the first day of the next month"),
    ("RetailCredit", "Credit cards and personal loans, held as portfolios.", "STF-09", "After end-of-day, 01:00-04:00 on the first day of the next month"),
    ("DepositBook", "Retail savings portfolios and business deposit accounts.", "STF-07", "After end-of-day, 01:00-03:00 on the first day of the next month"),
]

EXTRACTED_AT = {
    "LendingCore": "2026-10-01T02:14:37",
    "MortgageHub": "2026-09-30T18:02:11",  # CASE: run before end-of-day posting
    "RetailCredit": "2026-10-01T03:41:05",
    "DepositBook": "2026-10-01T01:56:48",
}

PRODUCTS = [
    # code, description, system, segment, balance type, launched
    ("RES-MTG", "Residential mortgage, owner-occupier", "MortgageHub", "Household", "Asset", "2009-04-01"),
    ("BTL-IND", "Buy-to-let mortgage, individual landlord", "MortgageHub", "Household", "Asset", "2012-09-01"),
    ("BTL-LTD", "Buy-to-let mortgage, limited-company landlord", "MortgageHub", "Property company", "Asset", "2017-06-01"),
    ("CARD", "Credit card", "RetailCredit", "Household", "Asset", "2011-03-01"),
    ("PL", "Unsecured personal loan", "RetailCredit", "Household", "Asset", "2010-01-04"),
    ("SME-TERM", "SME term loan", "LendingCore", "SME", "Asset", "2008-06-02"),
    ("SME-OD", "SME overdraft", "LendingCore", "SME", "Asset", "2008-06-02"),
    ("SME-RCF", "SME revolving credit facility", "LendingCore", "SME", "Asset", "2026-07-01"),
    ("CRE-INV", "Commercial real estate investment loan", "LendingCore", "Commercial real estate", "Asset", "2013-05-01"),
    ("CRE-DEV", "Commercial real estate development loan", "LendingCore", "Commercial real estate", "Asset", "2015-02-02"),
    ("CORP-TERM", "Corporate term loan", "LendingCore", "Large corporate", "Asset", "2014-10-01"),
    ("DEP-EASY", "Instant-access savings", "DepositBook", "Household", "Liability", "2008-06-02"),
    ("DEP-ISA", "Cash ISA", "DepositBook", "Household", "Liability", "2008-06-02"),
    ("DEP-FIX", "Fixed-rate savings bond", "DepositBook", "Household", "Liability", "2010-01-04"),
    ("DEP-BUS", "Business deposit account", "DepositBook", "SME", "Liability", "2008-06-02"),
    ("DEP-CORP", "Corporate deposit", "DepositBook", "Large corporate", "Liability", "2014-10-01"),
]
PRODUCT = {p[0]: p for p in PRODUCTS}

RETURN_LINES = [
    ("L10", "Residential mortgages", "Lending", "Mortgages secured on residential property, lent to individuals, including buy-to-let to individual landlords.", "2024-01-31", None),
    ("L20", "Consumer credit", "Lending", "Credit cards and unsecured personal loans to individuals.", "2024-01-31", None),
    ("L30", "SME term lending", "Lending", "Term loans to SMEs. Until March 2026 this line also held SME overdrafts.", "2024-01-31", None),
    ("L40", "SME overdrafts and revolving credit", "Lending", "Overdrafts and revolving credit facilities to SMEs.", "2026-04-30", None),
    ("L50", "Commercial real estate lending", "Lending", "Lending to finance commercial property investment or development.", "2025-04-30", None),
    ("L60", "Lending to large corporates", "Lending", "Lending to businesses that are not SMEs, other than commercial real estate.", "2024-01-31", None),
    ("D10", "Household deposits, instant access", "Deposits", "Instant-access savings and cash ISAs held by individuals.", "2024-01-31", None),
    ("D20", "Household deposits, fixed term", "Deposits", "Fixed-rate savings bonds held by individuals.", "2024-01-31", None),
    ("D30", "Business deposits", "Deposits", "Deposits from SMEs and large corporates.", "2024-01-31", None),
]

# (id, logged, effective, type, system, object, old, new, description, requested, approved, status)
CHANGES = [
    ("CHG-0412", "2023-12-04", "2024-01-01", "Mapping amendment", None, "Mapping set V1", None, "V1",
     "Baseline mapping of every product code to an MBSR line for the first return under the new template.", "STF-03", "STF-02", "Implemented"),
    ("CHG-0466", "2025-03-10", "2025-04-01", "Template change", None, "Return line L50", None, "L50 Commercial real estate lending",
     "New line L50 so commercial real estate is reported apart from other large corporate lending.", "STF-02", "STF-01", "Implemented"),
    ("CHG-0467", "2025-03-10", "2025-04-01", "Mapping amendment", None, "CRE-INV, CRE-DEV", "L60", "L50",
     "Mapping set V2: commercial real estate products move from L60 to the new line L50.", "STF-03", "STF-02", "Implemented"),
    ("CHG-0503", "2025-09-15", "2025-10-01", "Schema change", "DepositBook", "NOTICE_PERIOD_DAYS", None, "NOTICE_PERIOD_DAYS",
     "New field for notice accounts. Not used by the return. Dictionary updated the same day.", "STF-07", "STF-06", "Implemented"),
    ("CHG-0538", "2026-03-09", "2026-04-01", "Template change", None, "Return line L40", None, "L40 SME overdrafts and revolving credit",
     "New line L40 for SME overdrafts and revolving credit. L30 becomes SME term lending only.", "STF-02", "STF-01", "Implemented"),
    ("CHG-0539", "2026-03-09", "2026-04-01", "Mapping amendment", None, "SME-OD", "L30", "L40",
     "Mapping set V3: SME overdrafts move from L30 to the new line L40. The V1 rule ends on 31 March 2026.", "STF-03", "STF-02", "Implemented"),
    ("CHG-0561", "2026-06-15", "2026-07-01", "Reference data", "LendingCore", "SME-RCF", None, "SME-RCF -> L40",
     "New product: SME revolving credit facility, held in LendingCore's new revolving credit module. Mapped to L40 in set V3.", "STF-08", "STF-02", "Implemented"),
    ("CHG-0577", "2026-07-27", "2026-08-10", "Schema change", "RetailCredit", "BAL_OUTSTANDING", "BAL_OUTSTANDING", "CLOSING_BALANCE",
     "RetailCredit release 12.2 renames the balance field in the month-end extract.", "STF-09", "STF-06", "Implemented"),
    ("CHG-0578", "2026-07-28", "2026-08-10", "Dictionary update", "RetailCredit", "CLOSING_BALANCE", "BAL_OUTSTANDING", "CLOSING_BALANCE",
     "Field dictionary: CLOSING_BALANCE added from 10 August 2026; BAL_OUTSTANDING end-dated 9 August 2026. Return calculation repointed.", "STF-06", "STF-02", "Implemented"),
    ("CHG-0583", "2026-08-12", "2026-08-31", "Reference data", None, "Counterparty size classes",
     None, None, "Annual review of counterparty size classes against filed accounts, completed for customers onboarded before 2024.", "STF-10", "STF-02", "Implemented"),
    ("CHG-0596", "2026-09-14", "2026-09-21", "Schema change", "LendingCore", "OUTSTANDING_BALANCE (revolving credit module)", "OUTSTANDING_BALANCE", "OUTSTANDING_BAL",
     "LendingCore release 7.4 renames the balance field in the revolving credit module's extract, to match the module's other abbreviated field names.", "STF-08", "STF-07", "Implemented"),
    ("CHG-0601", "2026-09-24", "2026-10-01", "Mapping amendment", None, "BTL-LTD", "L10", "L50",
     "Mapping set V4: buy-to-let lending to limited companies is lending to property businesses, not to individuals. It moves from L10 to L50 from the October 2026 return.", "STF-03", "STF-02", "Approved - not yet effective"),
]

# (id, version, product, line, from, to, change, approver)
MAPPING = [
    ("MAP-001", "V1", "RES-MTG", "L10", "2024-01-01", None, "CHG-0412"),
    ("MAP-002", "V1", "BTL-IND", "L10", "2024-01-01", None, "CHG-0412"),
    ("MAP-003", "V1", "BTL-LTD", "L10", "2024-01-01", "2026-09-30", "CHG-0412"),
    ("MAP-004", "V1", "CARD", "L20", "2024-01-01", None, "CHG-0412"),
    ("MAP-005", "V1", "PL", "L20", "2024-01-01", None, "CHG-0412"),
    ("MAP-006", "V1", "SME-TERM", "L30", "2024-01-01", None, "CHG-0412"),
    ("MAP-007", "V1", "SME-OD", "L30", "2024-01-01", "2026-03-31", "CHG-0412"),
    ("MAP-008", "V1", "CRE-INV", "L60", "2024-01-01", "2025-03-31", "CHG-0412"),
    ("MAP-009", "V1", "CRE-DEV", "L60", "2024-01-01", "2025-03-31", "CHG-0412"),
    ("MAP-010", "V1", "CORP-TERM", "L60", "2024-01-01", None, "CHG-0412"),
    ("MAP-011", "V1", "DEP-EASY", "D10", "2024-01-01", None, "CHG-0412"),
    ("MAP-012", "V1", "DEP-ISA", "D10", "2024-01-01", None, "CHG-0412"),
    ("MAP-013", "V1", "DEP-FIX", "D20", "2024-01-01", None, "CHG-0412"),
    ("MAP-014", "V1", "DEP-BUS", "D30", "2024-01-01", None, "CHG-0412"),
    ("MAP-015", "V1", "DEP-CORP", "D30", "2024-01-01", None, "CHG-0412"),
    ("MAP-016", "V2", "CRE-INV", "L50", "2025-04-01", None, "CHG-0467"),
    ("MAP-017", "V2", "CRE-DEV", "L50", "2025-04-01", None, "CHG-0467"),
    ("MAP-018", "V3", "SME-OD", "L40", "2026-04-01", None, "CHG-0539"),
    ("MAP-019", "V3", "SME-RCF", "L40", "2026-07-01", None, "CHG-0561"),
    ("MAP-020", "V4", "BTL-LTD", "L50", "2026-10-01", None, "CHG-0601"),
]
CURRENT_RULE = {}  # product -> rule in force at 30 September 2026
for _m in MAPPING:
    if _m[4] <= AS_AT.isoformat() and (_m[5] is None or _m[5] >= AS_AT.isoformat()):
        CURRENT_RULE[_m[2]] = _m

REPORTING_RULES = [
    ("RR-01", "Inclusion", "Include every record of an in-scope entity with a non-zero balance at the period-end date.", "All lines"),
    ("RR-02", "Inclusion", "Exclude only: closed accounts with a zero balance, and balances with another group entity (intragroup), which are eliminated on consolidation. Record the reason in exclusion_reason.", "All lines"),
    ("RR-03", "Calculation", "Balances are taken at close of business on the last calendar day of the period, after end-of-day processing has posted that day's transactions.", "All lines"),
    ("RR-04", "Calculation", "Convert foreign-currency balances to sterling at the Bank of England spot rate for the period-end date, quoted as units of currency per £1: sterling amount = source amount / rate, rounded to the penny.", "All lines"),
    ("RR-05", "Classification", "Map each record to a line using the mapping rule for its product code that is in force on the period-end date.", "All lines"),
    ("RR-06", "Classification", "An SME is a business whose turnover in its latest filed accounts is £25 million or less. Lending to a business above that is reported in L60, and its deposits in D30, whatever product it is booked on. Commercial real estate lending stays in L50 whatever the borrower's size.", "L30, L40, L60"),
    ("RR-07", "Aggregation", "Each line is the sum of reported_amount_gbp over included records mapped to it, in pounds to the penny.", "All lines"),
    ("RR-08", "Aggregation", "Total lending is the sum of L10 to L60. Total deposits is the sum of D10 to D30.", "All lines"),
]

FX = [
    ("FX-0831-EUR", "EUR", "2026-08-31", 1.1572),
    ("FX-0831-USD", "USD", "2026-08-31", 1.3418),
    ("FX-0930-EUR", "EUR", "2026-09-30", 1.1491),
    ("FX-0930-USD", "USD", "2026-09-30", 1.3365),
]
RATE = {(c, d): r for _, c, d, r in FX}

GL = {
    "RES-MTG": "11010", "BTL-IND": "11020", "BTL-LTD": "11030", "CARD": "11210", "PL": "11220",
    "SME-TERM": "11410", "SME-OD": "11420", "SME-RCF": "11430", "CRE-INV": "11610", "CRE-DEV": "11620",
    "CORP-TERM": "11810", "DEP-EASY": "21010", "DEP-ISA": "21020", "DEP-FIX": "21110",
    "DEP-BUS": "21310", "DEP-CORP": "21410",
}

SECTORS = {
    "C": "Manufacturing", "F": "Construction", "G": "Wholesale and retail trade; repair of motor vehicles",
    "H": "Transportation and storage", "I": "Accommodation and food service activities",
    "J": "Information and communication", "L": "Real estate activities",
    "M": "Professional, scientific and technical activities", "N": "Administrative and support service activities",
    "Q": "Human health and social work activities",
}
SME_SECTORS = ["C", "F", "G", "G", "H", "I", "I", "J", "M", "M", "N", "Q"]
LARGE_SECTORS = ["C", "G", "H", "J", "M", "N"]
ACCOUNT_YEAR_ENDS = [D(2025, 12, 31), D(2025, 12, 31), D(2026, 3, 31), D(2025, 6, 30), D(2025, 9, 30)]

# ------------------------------------------------------------------ helpers


def iso(d):
    return d.isoformat() if d else None


def money(rng, lo, hi):
    return round(rng.uniform(lo, hi), 2)


def rand_date(rng, a, b):
    return a + dt.timedelta(days=rng.randint(0, (b - a).days))


# ------------------------------------------------------------------ builder


class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.rows = defaultdict(list)
        self.cases, self.case_records = [], []
        self.recs = []  # record drafts before numbering
        self.cpty = []
        self.planted = {}

    def case(self, cid, title, ctype, cls, sev, rules, expl, step, sql, records):
        self.cases.append({"case_id": cid, "title": title, "case_type": ctype, "classification": cls,
                           "severity": sev, "rules_involved": rules, "explanation": expl,
                           "expected_next_step": step, "detection_sql": " ".join(sql.split())})
        for table, rec, role, key in records:
            n = len(self.case_records) + 1
            self.case_records.append({"case_record_id": f"CR-{n:03d}", "case_id": cid, "table_name": table,
                                      "record_id": rec, "role_in_case": role, "is_key_record": int(key)})

    # ---- reference data

    def lookups(self):
        for sid, title, team, office, g in STAFF:
            person = staff_register.person(STAFF_REGISTER_IDS[sid])
            first, last = person["first_name"], person["last_name"]
            self.rows["staff"].append({"staff_id": sid, "first_name": first, "last_name": last, "job_title": title,
                                       "team": team, "office": office, "email": email_for(first, last, firm.EMAIL_DOMAIN)})
        self.rows["entities"] = [dict(zip(["entity_code", "entity_name", "entity_type", "in_return_scope", "office"], e))
                                 for e in ENTITIES]
        self.rows["source_systems"] = [dict(zip(["source_system", "description", "data_owner_id", "extract_schedule"], s))
                                       for s in SOURCE_SYSTEMS]
        self.rows["products"] = [dict(zip(["product_code", "description", "source_system", "customer_segment",
                                           "balance_type", "launched_date"], p)) for p in PRODUCTS]
        self.rows["return_lines"] = [dict(zip(["line_code", "line_name", "section", "description", "effective_from",
                                               "effective_to"], r)) for r in RETURN_LINES]
        self.rows["mapping_rules"] = [{"mapping_rule_id": m[0], "mapping_version": m[1], "product_code": m[2],
                                       "line_code": m[3], "effective_from": m[4], "effective_to": m[5],
                                       "change_id": m[6], "approved_by": "STF-02"} for m in MAPPING]
        self.rows["reporting_rules"] = [dict(zip(["reporting_rule_id", "rule_type", "statement", "applies_to"], r))
                                        for r in REPORTING_RULES]
        self.rows["fx_rates"] = [{"fx_rate_id": i, "currency": c, "rate_date": d, "rate": r,
                                  "source": "Bank of England daily spot rate against sterling, 4pm London"} for i, c, d, r in FX]
        self.rows["change_log"] = [dict(zip(["change_id", "logged_date", "effective_date", "change_type", "source_system",
                                             "object_changed", "old_value", "new_value", "description", "requested_by",
                                             "approved_by", "status"], c)) for c in CHANGES]
        self.field_dictionary()

    def field_dictionary(self):
        F = [
            ("LendingCore", "FACILITY_ID", "Facility reference, LC followed by seven digits.", "TEXT", "LC0000000-LC9999999", "source_record_ref", "2019-03-01", None),
            ("LendingCore", "PRODUCT_CODE", "Product code of the facility.", "TEXT", "SME-TERM, SME-OD, SME-RCF, CRE-INV, CRE-DEV, CORP-TERM", "product_code", "2019-03-01", None),
            ("LendingCore", "CPTY_ID", "Customer reference.", "TEXT", "CPTY-000000-CPTY-999999", "counterparty_id", "2019-03-01", None),
            ("LendingCore", "FACILITY_STATUS", "Status of the facility.", "TEXT", "Active, Closed", "account_status", "2019-03-01", None),
            ("LendingCore", "CCY", "Currency of the facility.", "TEXT", "GBP", "currency", "2019-03-01", None),
            ("LendingCore", "OUTSTANDING_BALANCE", "Amount owed by the customer at close of business: drawn principal plus accrued interest and fees, less repayments.", "DECIMAL(18,2)", ">= 0", "source_amount", "2019-03-01", None),
            ("LendingCore", "START_DATE", "Date the facility was first drawn.", "DATE", None, "start_date", "2019-03-01", None),
            ("LendingCore", "MATURITY_DATE", "Final repayment date, or next review date for an overdraft or revolving facility.", "DATE", None, "maturity_date", "2019-03-01", None),
            ("MortgageHub", "POOL_ID", "Mortgage portfolio reference.", "TEXT", None, "source_record_ref", "2018-11-05", None),
            ("MortgageHub", "PRODUCT_CODE", "Product code of the portfolio.", "TEXT", "RES-MTG, BTL-IND, BTL-LTD", "product_code", "2018-11-05", None),
            ("MortgageHub", "ACCOUNT_COUNT", "Number of live mortgage accounts in the portfolio.", "INTEGER", "> 0", "number_of_accounts", "2018-11-05", None),
            ("MortgageHub", "CURRENT_BALANCE", "Total balance owed on the portfolio's accounts at close of business, including accrued interest.", "DECIMAL(18,2)", ">= 0", "source_amount", "2018-11-05", None),
            ("MortgageHub", "CCY", "Currency of the portfolio.", "TEXT", "GBP", "currency", "2018-11-05", None),
            ("RetailCredit", "PORTFOLIO_ID", "Portfolio reference.", "TEXT", None, "source_record_ref", "2020-02-03", None),
            ("RetailCredit", "PRODUCT", "Product code of the portfolio.", "TEXT", "CARD, PL", "product_code", "2020-02-03", None),
            ("RetailCredit", "ACCOUNTS", "Number of open accounts in the portfolio.", "INTEGER", "> 0", "number_of_accounts", "2020-02-03", None),
            ("RetailCredit", "BAL_OUTSTANDING", "Total balance owed at close of business.", "DECIMAL(18,2)", ">= 0", "source_amount", "2020-02-03", "2026-08-09"),
            ("RetailCredit", "CLOSING_BALANCE", "Total balance owed at close of business. Replaces BAL_OUTSTANDING.", "DECIMAL(18,2)", ">= 0", "source_amount", "2026-08-10", None),
            ("RetailCredit", "CCY", "Currency of the portfolio.", "TEXT", "GBP", "currency", "2020-02-03", None),
            ("DepositBook", "ACCOUNT_REF", "Account or savings-portfolio reference.", "TEXT", None, "source_record_ref", "2017-07-03", None),
            ("DepositBook", "PRODUCT_CODE", "Product code of the account or portfolio.", "TEXT", "DEP-EASY, DEP-ISA, DEP-FIX, DEP-BUS, DEP-CORP", "product_code", "2017-07-03", None),
            ("DepositBook", "CUSTOMER_ID", "Business customer reference. Empty for retail portfolios.", "TEXT", "CPTY-000000-CPTY-999999", "counterparty_id", "2017-07-03", None),
            ("DepositBook", "ACCT_STATUS", "Status of the account.", "TEXT", "Active, Closed", "account_status", "2017-07-03", None),
            ("DepositBook", "CCY", "Currency of the account.", "TEXT", "GBP, EUR, USD", "currency", "2017-07-03", None),
            ("DepositBook", "LEDGER_BALANCE", "Balance owed to the customer at close of business, including interest credited.", "DECIMAL(18,2)", ">= 0", "source_amount", "2017-07-03", None),
            ("DepositBook", "NOTICE_PERIOD_DAYS", "Notice period for a notice account. Not used by the return.", "INTEGER", ">= 0", "(not used)", "2025-10-01", None),
        ]
        self.rows["field_dictionary"] = [
            {"field_id": f"FD-{i:03d}", "source_system": s, "field_name": n, "definition": d, "data_type": t,
             "valid_values": v, "feeds_column": c, "valid_from": a, "valid_to": b}
            for i, (s, n, d, t, v, c, a, b) in enumerate(F, start=1)]

    # ---- counterparties

    def new_cpty(self, size, earliest, turnover=None, sector=None, group=None):
        rng = self.rng
        if size == "SME" and turnover is None:
            turnover = rng.choice([money(rng, 350_000, 3_000_000), money(rng, 1_000_000, 9_000_000), money(rng, 4_000_000, 19_500_000)])
        elif size == "Large corporate" and turnover is None:
            turnover = money(rng, 40_000_000, 620_000_000)
        if turnover is not None:
            turnover = float(round(turnover / 1000) * 1000)  # filed accounts round to £1,000
        if sector is None:
            sector = rng.choice(SME_SECTORS if size == "SME" else LARGE_SECTORS)
        c = {"size_class": size, "annual_turnover_gbp": turnover if group is None else None,
             "accounts_date": iso(rng.choice(ACCOUNT_YEAR_ENDS)) if group is None else None,
             "sector_code": sector if group is None else "K", "country": "GB", "group_entity_code": group,
             "onboarded_date": earliest - dt.timedelta(days=rng.randint(20, 400))}
        c["sector"] = SECTORS.get(c["sector_code"], "Financial and insurance activities")
        self.cpty.append(c)
        return c

    # ---- records

    def rec(self, system, product, entity, amount, *, cpty=None, start=None, maturity=None, status="Active",
            accounts=1, rtype=None, currency="GBP", pool=None, **over):
        r = {"source_system": system, "product_code": product, "entity_code": entity, "source_amount": amount,
             "cpty": cpty, "start": start, "maturity": maturity, "status": status, "accounts": accounts,
             "record_type": rtype or ("Portfolio" if accounts > 1 or pool else "Facility"), "currency": currency,
             "pool": pool}
        r.update(over)
        self.recs.append(r)
        return r

    def lending(self):
        rng = self.rng
        P = self.planted
        # SME term loans: 18, including two repaid in September, one wrongly excluded, one large corporate
        # booked as SME, and one SME just under the turnover limit.
        sme_term = []
        for i in range(13):
            start = rand_date(rng, D(2019, 6, 1), D(2026, 6, 30))
            sme_term.append(self.rec("LendingCore", "SME-TERM", "ENT-LON-01", money(rng, 28_000, 1_450_000),
                                     cpty=self.new_cpty("SME", start), start=start,
                                     maturity=start + dt.timedelta(days=365 * rng.choice([3, 5, 7]))))
        for i in range(2):  # repaid in September: closed with a zero balance, correctly excluded
            start = rand_date(rng, D(2021, 9, 1), D(2023, 9, 30))
            self.rec("LendingCore", "SME-TERM", "ENT-LON-01", 0.0, cpty=self.new_cpty("SME", start), start=start,
                     maturity=rand_date(rng, D(2026, 9, 1), D(2026, 9, 25)), status="Closed",
                     included="No", reason="Closed, zero balance")
        start = D(2024, 2, 19)
        P["omitted"] = self.rec("LendingCore", "SME-TERM", "ENT-LON-01", 186_412.57, cpty=self.new_cpty("SME", start),
                                start=start, maturity=D(2029, 2, 19), included="No", reason="Closed, zero balance")
        start = D(2021, 5, 10)
        P["misclass"] = self.rec("LendingCore", "SME-TERM", "ENT-LON-01", 1_268_940.33,
                                 cpty=self.new_cpty("Large corporate", start, turnover=61_840_000, sector="C"),
                                 start=start, maturity=D(2028, 5, 10))
        P["misclass"]["cpty"]["accounts_date"] = "2025-12-31"
        start = D(2023, 11, 6)
        P["borderline"] = self.rec("LendingCore", "SME-TERM", "ENT-LON-01", 742_118.06,
                                   cpty=self.new_cpty("SME", start, turnover=24_310_000, sector="G"),
                                   start=start, maturity=D(2028, 11, 6))
        P["borderline"]["cpty"]["accounts_date"] = "2026-03-31"
        self.sme_term = sme_term

        # SME overdrafts: 8. Three were never moved to the V3 rule.
        od = []
        for i in range(8):
            start = rand_date(rng, D(2018, 1, 1), D(2025, 12, 31))
            review = D(2026 + (start.month < 10), start.month, min(start.day, 28))
            od.append(self.rec("LendingCore", "SME-OD", "ENT-LON-01", money(rng, 6_500, 245_000),
                               cpty=self.new_cpty("SME", start), start=start, maturity=review))
        P["obsolete"] = [od[1], od[4], od[6]]
        for r in P["obsolete"]:
            r["rule"] = "MAP-007"

        # SME revolving credit facilities: 3, all in the renamed module.
        P["renamed"] = []
        for d0 in [D(2026, 7, 8), D(2026, 7, 29), D(2026, 8, 18)]:
            amt = money(rng, 420_000, 880_000)
            P["renamed"].append(self.rec("LendingCore", "SME-RCF", "ENT-LON-01", amt, cpty=self.new_cpty("SME", d0),
                                         start=d0, maturity=D(d0.year + 3, d0.month, d0.day), field="OUTSTANDING_BAL",
                                         reported=0.0))

        for i in range(8):
            start = rand_date(rng, D(2017, 1, 1), D(2025, 12, 31))
            self.rec("LendingCore", "CRE-INV", "ENT-CRO-01", money(rng, 1_600_000, 8_900_000),
                     cpty=self.new_cpty(rng.choice(["SME", "SME", "Large corporate"]), start, sector="L"), start=start,
                     maturity=start + dt.timedelta(days=365 * rng.choice([5, 7, 10])))
        for i in range(4):
            start = rand_date(rng, D(2024, 3, 1), D(2026, 4, 30))
            self.rec("LendingCore", "CRE-DEV", "ENT-CRO-01", money(rng, 2_100_000, 6_800_000),
                     cpty=self.new_cpty("SME", start, sector="F"), start=start,
                     maturity=start + dt.timedelta(days=365 * rng.choice([2, 3])))
        self.corp = []
        for i in range(6):
            start = rand_date(rng, D(2019, 1, 1), D(2026, 3, 31))
            self.corp.append(self.rec("LendingCore", "CORP-TERM", "ENT-CRO-01", money(rng, 8_200_000, 34_500_000),
                                      cpty=self.new_cpty("Large corporate", start), start=start,
                                      maturity=start + dt.timedelta(days=365 * rng.choice([5, 7]))))

    def mortgages(self):
        rng = self.rng
        P = self.planted
        for rate in ["FX2", "FX5", "TRK", "SVR"]:
            for region in ["LDN", "SE"]:
                amt = money(rng, 62_000_000, 238_000_000) if rate != "SVR" else money(rng, 21_000_000, 46_000_000)
                self.rec("MortgageHub", "RES-MTG", "ENT-LON-01", amt, accounts=int(amt / rng.uniform(185_000, 245_000)),
                         pool=f"MH-RES-{rate}-{region}")
        for rate in ["FX2", "FX5"]:
            for region in ["LDN", "SE"]:
                amt = money(rng, 19_500_000, 58_000_000)
                self.rec("MortgageHub", "BTL-IND", "ENT-LON-01", amt, accounts=int(amt / rng.uniform(170_000, 225_000)),
                         pool=f"MH-BTI-{rate}-{region}")
        btl = []
        for rate in ["FX2", "FX5"]:
            for region in ["LDN", "SE"]:
                amt = money(rng, 7_400_000, 13_800_000)
                btl.append(self.rec("MortgageHub", "BTL-LTD", "ENT-LON-01", amt,
                                    accounts=int(amt / rng.uniform(260_000, 340_000)), pool=f"MH-BTC-{rate}-{region}"))
        # Two pools were mapped with the October rule; the other two correctly with the September rule.
        P["october"] = [btl[1], btl[2]]
        P["btl_ok"] = [btl[0], btl[3]]
        for r in P["october"]:
            r["rule"] = "MAP-020"

    def retail_credit(self):
        rng = self.rng
        self.planted["rc"] = []
        for product, pool, lo, hi, avg in [("CARD", "RC-CARD-STD", 31e6, 48e6, 2_150), ("CARD", "RC-CARD-BT", 12e6, 21e6, 3_400),
                                            ("PL", "RC-PL-STD", 16e6, 29e6, 8_700), ("PL", "RC-PL-HOME", 6e6, 11e6, 14_200)]:
            amt = money(rng, lo, hi)
            self.planted["rc"].append(self.rec("RetailCredit", product, "ENT-LON-01", amt,
                                               accounts=int(amt / avg * rng.uniform(0.92, 1.08)), pool=pool,
                                               field="CLOSING_BALANCE"))

    def deposits(self):
        rng = self.rng
        P = self.planted
        for i in range(5):
            amt = money(rng, 78_000_000, 205_000_000)
            self.rec("DepositBook", "DEP-EASY", "ENT-LON-01", amt, accounts=int(amt / rng.uniform(11_500, 16_500)),
                     pool=f"DB-EASY-{i + 1:02d}")
        for i in range(3):
            amt = money(rng, 48_000_000, 118_000_000)
            self.rec("DepositBook", "DEP-ISA", "ENT-LON-01", amt, accounts=int(amt / rng.uniform(9_500, 13_000)),
                     pool=f"DB-ISA-{2024 + i}")
        for term in ["1Y", "2Y", "3Y"]:
            for issue in ["A", "B"]:
                amt = money(rng, 38_000_000, 112_000_000)
                self.rec("DepositBook", "DEP-FIX", "ENT-LON-01", amt, accounts=int(amt / rng.uniform(23_000, 31_000)),
                         pool=f"DB-FIX-{term}-{issue}")
        # Business deposits: six from existing SME borrowers, four from deposit-only customers.
        owners = [r["cpty"] for r in self.sme_term[:6]]
        for i in range(10):
            c = owners[i] if i < 6 else None
            start = rand_date(rng, D(2016, 1, 1), D(2026, 5, 31))
            if c is None:
                c = self.new_cpty("SME", start)
            else:
                start = max(start, c["onboarded_date"])
            self.rec("DepositBook", "DEP-BUS", "ENT-LON-01", money(rng, 18_000, 1_950_000), cpty=c, start=start,
                     rtype="Account")
        corp_owners = [r["cpty"] for r in self.corp[:4]]
        P["fx_wrong"] = None
        P["fx_ok"] = []
        specs = [("GBP", 2.2e6, 24e6)] * 5 + [("EUR", 3.1e6, 8.2e6)] * 2 + [("USD", 2.0e6, 5.1e6)]
        for i, (ccy, lo, hi) in enumerate(specs):
            c = corp_owners[i] if i < 4 else None
            start = rand_date(rng, D(2018, 1, 1), D(2026, 6, 30))
            if c is None:
                c = self.new_cpty("Large corporate", start)
            else:
                start = max(start, c["onboarded_date"])
            r = self.rec("DepositBook", "DEP-CORP", "ENT-LON-01", money(rng, lo, hi), cpty=c, start=start,
                         rtype="Account", currency=ccy)
            if ccy == "EUR" and P["fx_wrong"] is None:
                P["fx_wrong"] = r
                r["rate"] = RATE[("EUR", "2026-08-31")]
            elif ccy != "GBP":
                P["fx_ok"].append(r)
        start = D(2022, 4, 1)
        P["intragroup"] = self.rec("DepositBook", "DEP-CORP", "ENT-LON-01", 12_500_000.00,
                                   cpty=self.new_cpty("Intragroup", start, group="ENT-CRO-01"), start=start,
                                   rtype="Account", included="No", reason="Intragroup: eliminated on consolidation")

    # ---- numbering and derived fields

    def finalise(self):
        rng = self.rng
        # Counterparty references rise with onboarding date.
        n = 104_250
        for c in sorted(self.cpty, key=lambda c: (c["onboarded_date"], c["size_class"], c["annual_turnover_gbp"] or 0)):
            n += rng.randint(40, 900)
            c["counterparty_id"] = f"CPTY-{n:06d}"
        self.rows["counterparties"] = [
            {k: (iso(c[k]) if k == "onboarded_date" else c[k]) for k in
             ["counterparty_id", "sector_code", "sector", "size_class", "annual_turnover_gbp", "accounts_date",
              "country", "group_entity_code", "onboarded_date"]}
            for c in sorted(self.cpty, key=lambda c: c["counterparty_id"])]

        # Facility and account references rise with start date.
        lc = sorted([r for r in self.recs if r["source_system"] == "LendingCore"], key=lambda r: r["start"])
        n = 31_870
        for r in lc:
            n += rng.randint(60, 700)
            r["pool"] = f"LC{n:07d}"
        db = sorted([r for r in self.recs if r["source_system"] == "DepositBook" and not r["pool"]], key=lambda r: r["start"])
        n = 40_118_000
        for r in db:
            n += rng.randint(900, 60_000)
            r["pool"] = f"{n:08d}"

        order = {s[0]: i for i, s in enumerate(SOURCE_SYSTEMS)}
        porder = {p[0]: i for i, p in enumerate(PRODUCTS)}
        self.recs.sort(key=lambda r: (order[r["source_system"]], porder[r["product_code"]], r["pool"]))
        fields = {"LendingCore": "OUTSTANDING_BALANCE", "MortgageHub": "CURRENT_BALANCE",
                  "RetailCredit": "CLOSING_BALANCE", "DepositBook": "LEDGER_BALANCE"}
        rules = {m[0]: m for m in MAPPING}
        for i, r in enumerate(self.recs, start=1):
            r["record_id"] = f"RPT-{i:04d}"
            rule = rules[r.get("rule") or CURRENT_RULE[r["product_code"]][0]]
            rate = r.get("rate") or (1.0 if r["currency"] == "GBP" else RATE[(r["currency"], AS_AT.isoformat())])
            amount_gbp = round(r["source_amount"] / rate, 2)
            included = r.get("included", "Yes")
            reported = None if included == "No" else r.get("reported", amount_gbp)
            self.rows["reporting_records"].append({
                "record_id": r["record_id"], "reporting_period": PERIOD, "as_at_date": AS_AT.isoformat(),
                "entity_code": r["entity_code"], "source_system": r["source_system"], "source_record_ref": r["pool"],
                "record_type": r["record_type"], "number_of_accounts": r["accounts"], "product_code": r["product_code"],
                "counterparty_id": r["cpty"]["counterparty_id"] if r["cpty"] else None,
                "start_date": iso(r["start"]), "maturity_date": iso(r["maturity"]), "account_status": r["status"],
                "source_field": r.get("field", fields[r["source_system"]]), "currency": r["currency"],
                "source_amount": r["source_amount"], "fx_rate": rate, "amount_gbp": amount_gbp,
                "mapping_rule_id": rule[0], "mapping_version": rule[1], "line_code": rule[3],
                "included_in_return": included, "exclusion_reason": r.get("reason"),
                "reported_amount_gbp": reported, "extracted_at": EXTRACTED_AT[r["source_system"]]})
        self.controls()
        self.return_figures()

    def controls(self):
        rng = self.rng
        totals = defaultdict(float)
        for r in self.rows["reporting_records"]:
            totals[(r["source_system"], r["product_code"], r["currency"])] += r["source_amount"]
        # Mortgages completed on 30 September, posted by end-of-day after the MortgageHub extract ran.
        self.completions = [money(rng, 165_000, 520_000) for _ in range(6)]
        n = 0
        for (system, product, ccy), total in sorted(totals.items(), key=lambda x: (GL[x[0][1]], x[0][2])):
            n += 1
            amount = round(total, 2)
            notes = None
            if product == "RES-MTG":
                amount = round(amount + sum(self.completions), 2)
            if product == "DEP-EASY":
                amount = round(amount + 0.63, 2)
                notes = "Daily interest accrual is rounded per account in DepositBook and per product in the ledger, so small differences are expected."
            if product == "DEP-CORP" and ccy != "GBP":
                notes = f"Held in {ccy}; control in {ccy}."
            self.rows["control_totals"].append({
                "control_id": f"CTL-{n:02d}", "reporting_period": PERIOD, "source_system": system,
                "product_code": product, "currency": ccy, "gl_account": GL[product] + ("" if ccy == "GBP" else f"-{ccy}"),
                "control_amount": amount, "tolerance": 1.0,
                "control_source": "General-ledger trial balance at 30 September 2026, after end-of-day processing",
                "notes": notes})

    def return_figures(self):
        rng = self.rng
        recs = self.rows["reporting_records"]
        sept = defaultdict(float)
        sept_n = defaultdict(int)
        for r in recs:
            if r["included_in_return"] == "Yes":
                sept[r["line_code"]] += r["reported_amount_gbp"]
                sept_n[r["line_code"]] += 1
        # August basis: September's balances with the errors that existed in August (obsolete overdraft mapping,
        # large corporate booked as SME) but without those that began in September.
        P = self.planted
        sept_only = {id(x) for x in P["renamed"] + P["october"] + [P["omitted"], P["fx_wrong"]]}
        aug = defaultdict(float)
        aug_n = defaultdict(int)
        for draft, r in zip(self.recs, recs):
            if id(draft) in sept_only:
                line = CURRENT_RULE[r["product_code"]][3]
                amt = round(r["source_amount"] / (r["fx_rate"] if draft is not P["fx_wrong"] else RATE[("EUR", "2026-09-30")]), 2)
            elif r["included_in_return"] == "Yes":
                line, amt = r["line_code"], r["reported_amount_gbp"]
            else:
                continue
            aug[line] += amt
            aug_n[line] += 1
        aug["L10"] -= sum(self.completions) * 0.4  # new lending in September
        for line, *_ in RETURN_LINES:
            prior = round(aug[line] * rng.uniform(0.975, 1.008), 2)
            self.rows["return_figures"].append({
                "figure_id": f"RF-{PRIOR}-{line}", "reporting_period": PRIOR, "line_code": line,
                "reported_amount_gbp": prior, "record_count": aug_n[line] + (rng.choice([0, 0, 1]) if aug_n[line] > 6 else 0),
                "status": "Submitted", "prepared_by": "STF-05", "prepared_date": "2026-09-07",
                "reviewed_by": "STF-03", "approved_by": "STF-01", "submitted_date": "2026-09-14"})
        for line, *_ in RETURN_LINES:
            self.rows["return_figures"].append({
                "figure_id": f"RF-{PERIOD}-{line}", "reporting_period": PERIOD, "line_code": line,
                "reported_amount_gbp": round(sept[line], 2), "record_count": sept_n[line],
                "status": "Draft - awaiting review", "prepared_by": "STF-04", "prepared_date": EXTRACT_DATE.isoformat(),
                "reviewed_by": None, "approved_by": None, "submitted_date": None})


# ------------------------------------------------------------------ rules (controls)

RULES = [
    ("R-01", "Data definitions", "Field dictionary coverage", "Every source field the return reads must be in field_dictionary and valid on the period-end date. A source-system change that renames or removes a field must be matched by a dictionary update, and the return calculation repointed, before the change goes live."),
    ("R-02", "Mapping", "Mapping in force", "A record must be mapped with the rule for its product that is in force on the period-end date: effective_from on or before it, and effective_to empty or on or after it."),
    ("R-03", "Change control", "Logged and approved changes", "Every schema change, mapping amendment and template change is logged in change_log with its effective date, and approved before it takes effect. A change takes effect for the first period-end on or after its effective date."),
    ("R-04", "Reconciliation", "Control totals", "For each source system, product and currency, the sum of source_amount over all records, included or not, must agree with the general-ledger control total within its tolerance. A difference above tolerance must be explained and corrected before the return is reviewed."),
    ("R-05", "Completeness", "Justified exclusions", "A record may be excluded only for a reason allowed by reporting rule RR-02, and its status and balance must support the reason given."),
    ("R-06", "Classification", "Customer size", "Counterparty size classes are reviewed each year against filed accounts. Lending booked on an SME product to a large corporate is reported as large corporate lending (RR-06)."),
    ("R-07", "Calculation", "Exchange rates", "Foreign-currency balances use the rate in fx_rates for the period-end date. A rate from any other date is an error."),
    ("R-08", "Review", "Movement review", "A line that moves by more than 10% from the previous submitted return must be explained in the review pack before approval."),
    ("R-09", "Sign-off", "Four eyes", "The return is prepared by a Regulatory Reporting Analyst, reviewed by the Regulatory Reporting Manager and approved by the Chief Financial Officer. The preparer may not review."),
    ("R-10", "Timetable", "Submission deadline", "The return is due by the 15th calendar day after the period end, or the next working day. The September 2026 return is due on Thursday 15 October 2026."),
]

RULE_TABLES = {
    "R-01": "field_dictionary, reporting_records, change_log", "R-02": "mapping_rules, reporting_records",
    "R-03": "change_log, mapping_rules", "R-04": "control_totals, reporting_records",
    "R-05": "reporting_records, reporting_rules", "R-06": "counterparties, reporting_records, products",
    "R-07": "fx_rates, reporting_records", "R-08": "return_figures", "R-09": "return_figures, staff",
    "R-10": "return_figures",
}

# ------------------------------------------------------------------ cases


def gbp(x):
    return f"£{x:,.2f}"


def record_cases(b):
    P = b.planted
    rows = b.rows
    R = lambda d: d["record_id"]  # noqa: E731
    by_id = {r["record_id"]: r for r in rows["reporting_records"]}
    ctl = {(c["product_code"], c["currency"]): c for c in rows["control_totals"]}
    figs = {(f["reporting_period"], f["line_code"]): f["reported_amount_gbp"] for f in rows["return_figures"]}

    rcf = P["renamed"]
    rcf_total = sum(r["source_amount"] for r in rcf)
    b.case("CASE-01", "Renamed source field: revolving credit reported at zero", "renamed_source_field",
           "Genuine exception", "High", "R-01, R-03, R-08",
           f"LendingCore release 7.4 (change CHG-0596, live 21 September 2026) renamed OUTSTANDING_BALANCE to OUTSTANDING_BAL "
           f"in the revolving credit module. The field dictionary was not updated, so the return calculation found no "
           f"balance for the three SME revolving credit facilities and reported each at £0.00. The extract holds "
           f"{gbp(rcf_total)} for them. Line L40 is understated by that amount and falls from {gbp(figs[(PRIOR, 'L40')])} "
           f"in August to {gbp(figs[(PERIOD, 'L40')])}.",
           "Add OUTSTANDING_BAL to the field dictionary from 21 September 2026, repoint the calculation, rerun L40, and add a check that fails when a source field is missing from the dictionary.",
           """SELECT r.record_id FROM reporting_records r WHERE NOT EXISTS (SELECT 1 FROM field_dictionary f
              WHERE f.source_system = r.source_system AND f.field_name = r.source_field AND f.valid_from <= r.as_at_date
              AND (f.valid_to IS NULL OR f.valid_to >= r.as_at_date))""",
           [("reporting_records", R(x), "balance read from unrecognised field", 1) for x in rcf]
           + [("change_log", "CHG-0596", "schema change with no dictionary update", 0),
              ("return_figures", f"RF-{PERIOD}-L40", "understated line", 0)])

    od = P["obsolete"]
    od_total = sum(by_id[R(x)]["reported_amount_gbp"] for x in od)
    b.case("CASE-02", "Obsolete mapping still used for three overdrafts", "obsolete_mapping",
           "Genuine exception", "Medium", "R-02, RR-05",
           f"Mapping set V3 moved SME overdrafts (SME-OD) from L30 to L40 from 1 April 2026 (CHG-0539). Three overdraft "
           f"facilities still carry the V1 rule MAP-007, which ended on 31 March 2026, so {gbp(od_total)} is reported in "
           f"L30 instead of L40. The other five overdrafts use the V3 rule. The return still balances in total.",
           "Remap the three facilities with MAP-018, move the amount from L30 to L40, find why the pipeline kept a cached rule for them, and check whether the April to August returns had the same error.",
           """SELECT r.record_id FROM reporting_records r JOIN mapping_rules m ON m.mapping_rule_id = r.mapping_rule_id
              WHERE m.effective_to IS NOT NULL AND m.effective_to < r.as_at_date""",
           [("reporting_records", R(x), "overdraft mapped with an expired rule", 1) for x in od]
           + [("mapping_rules", "MAP-007", "expired rule", 0), ("mapping_rules", "MAP-018", "rule that should apply", 0)])

    rc = P["rc"]
    b.case("CASE-03", "Renamed field handled correctly in RetailCredit", "renamed_field_lookalike",
           "Benign lookalike", "None", "R-01",
           "RetailCredit renamed BAL_OUTSTANDING to CLOSING_BALANCE from 10 August 2026 (CHG-0577). The field dictionary was "
           "updated the day before it went live (CHG-0578) and the calculation repointed, so the four card and personal-loan "
           "portfolios are read correctly from the new field.",
           "No action. This is how a field rename should be handled.",
           """SELECT r.record_id FROM reporting_records r JOIN field_dictionary f ON f.source_system = r.source_system
              AND f.field_name = r.source_field WHERE f.valid_from > date(r.as_at_date, '-90 days')""",
           [("reporting_records", R(x), "portfolio read from the renamed field", 1) for x in rc]
           + [("change_log", "CHG-0578", "dictionary update", 0)])

    oc = P["october"]
    oc_total = sum(by_id[R(x)]["reported_amount_gbp"] for x in oc)
    b.case("CASE-04", "October mapping applied to September", "future_mapping_applied",
           "Genuine exception", "Medium", "R-02, R-03, RR-05",
           f"Mapping set V4 (CHG-0601, approved 24 September 2026) moves limited-company buy-to-let (BTL-LTD) from L10 to L50 "
           f"from 1 October 2026. Two of the four BTL-LTD portfolios were mapped with the V4 rule MAP-020 in the September "
           f"return, so {gbp(oc_total)} sits in L50 instead of L10. L50 rises and L10 falls by that amount; the total is unchanged.",
           "Remap the two portfolios with MAP-003 for September, and confirm the pipeline selects rules by the period-end date, not the run date.",
           "SELECT r.record_id FROM reporting_records r JOIN mapping_rules m ON m.mapping_rule_id = r.mapping_rule_id WHERE m.effective_from > r.as_at_date",
           [("reporting_records", R(x), "portfolio mapped with a rule not yet in force", 1) for x in oc]
           + [("mapping_rules", "MAP-020", "October rule", 0), ("change_log", "CHG-0601", "approved future change", 0)])

    ok = P["btl_ok"]
    b.case("CASE-05", "Buy-to-let portfolios correctly left on the September rule", "pending_change_lookalike",
           "Benign lookalike", "None", "R-02",
           "Two limited-company buy-to-let portfolios are reported in L10 under MAP-003, although the change log shows BTL-LTD "
           "moving to L50. That change takes effect from the October return, so L10 is correct for September.",
           "No action for September. Check that the October return uses MAP-020.",
           """SELECT r.record_id FROM reporting_records r JOIN mapping_rules m ON m.mapping_rule_id = r.mapping_rule_id
              WHERE m.effective_from <= r.as_at_date AND (m.effective_to IS NULL OR m.effective_to >= r.as_at_date)
              AND EXISTS (SELECT 1 FROM mapping_rules n WHERE n.product_code = m.product_code AND n.effective_from > r.as_at_date)""",
           [("reporting_records", R(x), "portfolio correctly mapped for September", 1) for x in ok])

    om = by_id[R(P["omitted"])]
    b.case("CASE-06", "Active loan omitted from SME term lending", "record_omitted",
           "Genuine exception", "High", "R-05, RR-01, RR-02",
           f"Facility {om['source_record_ref']} is excluded with the reason 'Closed, zero balance', but LendingCore shows it Active "
           f"with {gbp(om['source_amount'])} outstanding and a maturity date of {om['maturity_date']}. It should be in L30, which is "
           f"understated by that amount. The two other exclusions with this reason are genuinely closed with zero balances.",
           "Include the facility in L30, find out why the exclusion reason was set, and require the reason to be checked against status and balance.",
           """SELECT r.record_id FROM reporting_records r LEFT JOIN counterparties c ON c.counterparty_id = r.counterparty_id
              WHERE r.included_in_return = 'No' AND r.account_status = 'Active' AND r.source_amount <> 0
              AND coalesce(c.size_class, '') <> 'Intragroup'""",
           [("reporting_records", om["record_id"], "active facility excluded", 1)])

    ig = by_id[R(P["intragroup"])]
    b.case("CASE-07", "Intragroup deposit correctly excluded", "intragroup_lookalike",
           "Benign lookalike", "None", "R-05, RR-02",
           f"A corporate deposit of {gbp(ig['source_amount'])} is active but excluded. The depositor is Thameside Commercial "
           f"Finance (ENT-CRO-01), another group entity, so the balance is eliminated on consolidation as RR-02 requires. "
           f"It is still in the ledger, so it counts towards the DEP-CORP control total.",
           "No action.",
           """SELECT r.record_id FROM reporting_records r JOIN counterparties c ON c.counterparty_id = r.counterparty_id
              WHERE r.included_in_return = 'No' AND c.size_class = 'Intragroup'""",
           [("reporting_records", ig["record_id"], "intragroup deposit", 1),
            ("counterparties", ig["counterparty_id"], "group entity as customer", 0)])

    c = ctl[("RES-MTG", "GBP")]
    diff = round(sum(b.completions), 2)
    res = [r for r in rows["reporting_records"] if r["product_code"] == "RES-MTG"]
    b.case("CASE-08", "Mortgage total disagrees with the ledger control", "control_total_break",
           "Genuine exception", "High", "R-04, RR-03",
           f"The eight RES-MTG portfolios total {gbp(c['control_amount'] - diff)}; the general-ledger control {c['control_id']} is "
           f"{gbp(c['control_amount'])}, a difference of {gbp(diff)} against a tolerance of £1.00. The MortgageHub extract ran at "
           f"18:02 on 30 September, before end-of-day processing posted that day's {len(b.completions)} mortgage completions. "
           f"Every other system was extracted after end-of-day, as RR-03 requires. L10 is understated.",
           "Rerun the MortgageHub extract after end-of-day, reload L10, and schedule the extract after end-of-day in future.",
           """SELECT c.control_id FROM control_totals c WHERE abs(c.control_amount - (SELECT coalesce(sum(r.source_amount), 0)
              FROM reporting_records r WHERE r.source_system = c.source_system AND r.product_code = c.product_code
              AND r.currency = c.currency)) > c.tolerance""",
           [("control_totals", c["control_id"], "control that does not agree", 1)]
           + [("reporting_records", r["record_id"], "portfolio from the early extract", 0) for r in res])

    c2 = ctl[("DEP-EASY", "GBP")]
    b.case("CASE-09", "Savings total differs from control within tolerance", "tolerance_lookalike",
           "Benign lookalike", "None", "R-04",
           f"The DEP-EASY portfolios differ from control {c2['control_id']} by £0.63, inside the £1.00 tolerance. The difference "
           f"comes from rounding daily interest per account in DepositBook and per product in the ledger.",
           "No action. Record the difference in the reconciliation.",
           """SELECT c.control_id FROM control_totals c WHERE abs(c.control_amount - (SELECT coalesce(sum(r.source_amount), 0)
              FROM reporting_records r WHERE r.source_system = c.source_system AND r.product_code = c.product_code
              AND r.currency = c.currency)) BETWEEN 0.005 AND c.tolerance""",
           [("control_totals", c2["control_id"], "control within tolerance", 1)])

    mc = by_id[R(P["misclass"])]
    b.case("CASE-10", "Large corporate loan reported as SME lending", "misclassified_exposure",
           "Genuine exception", "Medium", "R-06, RR-06",
           f"Facility {mc['source_record_ref']} ({gbp(mc['reported_amount_gbp'])}) was booked as an SME term loan in 2021. The "
           f"customer {mc['counterparty_id']} is now classed as a large corporate: turnover £61,840,000 in accounts to 31 December 2025. "
           f"Under RR-06 the loan belongs in L60, not L30. The return balances, because the amount is right, but the classification is wrong.",
           "Move the facility to L60, ask the relationship team to rebook it on a corporate product, and check other SME-product customers whose turnover has passed £25 million.",
           """SELECT r.record_id FROM reporting_records r JOIN counterparties c ON c.counterparty_id = r.counterparty_id
              JOIN products p ON p.product_code = r.product_code
              WHERE p.customer_segment = 'SME' AND c.size_class = 'Large corporate' AND r.included_in_return = 'Yes'""",
           [("reporting_records", mc["record_id"], "large corporate loan in L30", 1),
            ("counterparties", mc["counterparty_id"], "customer above the SME limit", 0)])

    bl = by_id[R(P["borderline"])]
    b.case("CASE-11", "SME just under the turnover limit", "size_threshold_lookalike",
           "Benign lookalike", "None", "RR-06",
           f"Customer {bl['counterparty_id']} had turnover of £24,310,000 in accounts to 31 March 2026, just under the £25 million "
           f"SME limit, so its term loan is correctly reported in L30.",
           "No action. Review the classification when the next accounts are filed.",
           """SELECT r.record_id FROM reporting_records r JOIN counterparties c ON c.counterparty_id = r.counterparty_id
              JOIN products p ON p.product_code = r.product_code
              WHERE p.customer_segment = 'SME' AND c.annual_turnover_gbp BETWEEN 22500000 AND 25000000""",
           [("reporting_records", bl["record_id"], "SME near the limit", 1)])

    fx = by_id[R(P["fx_wrong"])]
    right = round(fx["source_amount"] / RATE[("EUR", "2026-09-30")], 2)
    b.case("CASE-12", "Euro deposit converted at the August rate", "wrong_fx_rate",
           "Genuine exception", "Low", "R-07, RR-04",
           f"Deposit {fx['source_record_ref']} of €{fx['source_amount']:,.2f} was converted at 1.1572, the 31 August rate, "
           f"giving {gbp(fx['amount_gbp'])}. At the 30 September rate of 1.1491 it is {gbp(right)}, so D30 is understated by "
           f"{gbp(right - fx['amount_gbp'])}. The other euro and dollar deposits use 30 September rates.",
           "Reconvert at the 30 September rate and correct D30; check why one account kept the previous month's rate.",
           """SELECT r.record_id FROM reporting_records r WHERE r.currency <> 'GBP' AND NOT EXISTS (SELECT 1 FROM fx_rates f
              WHERE f.currency = r.currency AND f.rate_date = r.as_at_date AND abs(f.rate - r.fx_rate) < 0.000001)""",
           [("reporting_records", fx["record_id"], "deposit at the wrong rate", 1),
            ("fx_rates", "FX-0930-EUR", "rate that should apply", 0)])


RETURN_DUE = D(2026, 10, 15)


def _long_date(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def business_story(rows):
    """The firm's current situation. Paragraphs are separated by blank lines; lines starting '- ' are list items.
    Every figure is calculated from the rows, and checks() tests every claim against the data."""
    recs = rows["reporting_records"]
    included = [r for r in recs if r["included_in_return"] == "Yes"]
    lines = {r["line_code"] for r in included}
    systems = len(rows["source_systems"])
    total = sum(r["reported_amount_gbp"] for r in included)
    return "\n".join([
        "Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. Each month it reports its "
        "balance sheet to the regulator in the Monthly Balance Sheet Return. A small regulatory reporting team in the City "
        f"and Croydon prepares the return, drawing on {systems} source systems run by Technology and Finance Data.",
        "",
        "2026 has brought steady change to the systems and rules behind the return:",
        "- System upgrades. Two source systems had major releases this summer: RetailCredit in August and LendingCore in "
        "September. Each release changed how some balances are labelled in the monthly extract.",
        "- A changing return. The bank has revised how its products map to return lines several times. A new line for SME "
        "overdrafts and revolving credit came in from April. A further revision, moving buy-to-let lending to limited "
        "companies, takes effect from October.",
        "- A shorter timetable. The board asked for earlier month-end figures, so the team now prepares the draft return in "
        "four working days instead of eight.",
        "- Annual reference data review. At the end of August, the team updated the size classes it uses to decide whether "
        "a business borrower counts as an SME.",
        "",
        "The Head of Regulatory Reporting asked for the draft September return to be reviewed before the Chief Financial "
        f"Officer signs it off. The return is due on {_long_date(RETURN_DUE)}. The draft holds {len(recs)} source records "
        f"across {len(lines)} return lines. {len(included)} of them are included in the return, reporting "
        f"£{total:,.2f} in total.",
    ])


def build(rng):
    b = Builder(rng)
    b.lookups()
    b.lending()
    b.mortgages()
    b.retail_credit()
    b.deposits()
    b.finalise()
    record_cases(b)
    rules = [{"rule_id": r, "category": c, "title": t, "statement": s, "related_tables": RULE_TABLES[r]}
             for r, c, t, s in RULES]
    for c in b.cases:
        c["appraisal_types"] = APPRAISAL[c["case_id"]]
    facts = [
        ("dataset", "regulatory_reporting"),
        ("title", "Regulatory reporting and data lineage"),
        ("firm", firm.FIRM_NAME),
        ("scenario", "The regulatory reporting team prepares the September 2026 Monthly Balance Sheet Return (MBSR) from four source systems."),
        ("period", "Return period 2026-09, balances at 2026-09-30; prior submitted return 2026-08"),
        ("extract_date", EXTRACT_DATE.isoformat()),
        ("return_due", RETURN_DUE.isoformat()),
        ("currency", "GBP"),
        ("seed", firm.SEED),
        ("disclaimer", firm.DISCLAIMER + " The MBSR template, its line codes and the source systems are fictional."),
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

    if q("SELECT count(*) FROM _truth_cases WHERE appraisal_types IS NULL OR appraisal_types = ''")[0][0]:
        errors.append("every planted case needs its appraisal types")

    # The business story's claims must hold in the data.
    def changed(change_type, system, month, obj=None):
        sql = "SELECT count(*) FROM change_log WHERE change_type = ? AND effective_date LIKE ?"
        args = [change_type, month + "%"]
        if system:
            sql += " AND source_system = ?"; args.append(system)
        if obj:
            sql += " AND object_changed LIKE ?"; args.append(obj)
        return q(sql, *args)[0][0] > 0
    claims = [
        (changed("Schema change", "RetailCredit", "2026-08"), "RetailCredit had a release in August 2026"),
        (changed("Schema change", "LendingCore", "2026-09"), "LendingCore had a release in September 2026"),
        (changed("Template change", None, "2026-04", "%L40%"), "the SME overdraft line L40 started in April 2026"),
        (changed("Mapping amendment", None, "2026-10", "BTL-LTD"), "the buy-to-let mapping change takes effect in October 2026"),
        (changed("Reference data", None, "2026-08", "%size class%"), "size classes were reviewed at the end of August 2026"),
        ({o for (o,) in q("SELECT office FROM staff WHERE team = 'Regulatory Reporting'")} == {"City", "Croydon"},
         "the regulatory reporting team works in the City and Croydon"),
        ({t for (t,) in q("SELECT team FROM staff WHERE staff_id IN (SELECT data_owner_id FROM source_systems)")}
         <= {"Technology", "Finance Data"}, "the source systems are run by Technology and Finance Data"),
    ]
    d, n = D(2026, 10, 1), 0
    while d <= EXTRACT_DATE:
        n += uk.is_working_day(d)
        d += dt.timedelta(days=1)
    claims.append((n == 4, "the draft was prepared in four working days"))
    errors += [f"story: {text} is not true in the data" for ok, text in claims if not ok]

    ranges = {"reporting_records": (95, 105), "counterparties": (40, 70), "field_dictionary": (20, 35),
              "mapping_rules": (15, 25), "control_totals": (15, 22), "change_log": (8, 20), "return_figures": (18, 18)}
    for t, (lo, hi) in ranges.items():
        n = q(f"SELECT count(*) FROM {t}")[0][0]
        if not lo <= n <= hi:
            errors.append(f"{t}: {n} rows, expected {lo}-{hi}")

    for rid, src, rate, gbp_ in q("SELECT record_id, source_amount, fx_rate, amount_gbp FROM reporting_records"):
        if abs(round(src / rate, 2) - gbp_) > 0.005:
            errors.append(f"{rid}: amount_gbp is not source_amount / fx_rate")
    for (rid,) in q("""SELECT r.record_id FROM reporting_records r JOIN mapping_rules m USING (mapping_rule_id)
                              WHERE r.mapping_version <> m.mapping_version OR r.line_code <> m.line_code"""):
        errors.append(f"{rid}: mapping version or line differs from its rule")
    for (rid,) in q("""SELECT r.record_id FROM reporting_records r JOIN products p USING (product_code)
                      WHERE p.source_system <> r.source_system"""):
        errors.append(f"{rid}: product does not belong to the source system")
    for (rid,) in q("""SELECT record_id FROM reporting_records WHERE (included_in_return = 'No') <> (exclusion_reason IS NOT NULL)
                      OR (included_in_return = 'No') <> (reported_amount_gbp IS NULL)"""):
        errors.append(f"{rid}: inclusion flag, reason and reported amount disagree")
    for (rid,) in q("""SELECT record_id FROM reporting_records WHERE included_in_return = 'Yes'
                      AND abs(reported_amount_gbp - amount_gbp) > 0.005 AND source_field <> 'OUTSTANDING_BAL'"""):
        errors.append(f"{rid}: reported amount differs from amount_gbp")
    for line, fig, total in q("""SELECT f.line_code, f.reported_amount_gbp, (SELECT coalesce(sum(r.reported_amount_gbp), 0)
                                 FROM reporting_records r WHERE r.line_code = f.line_code AND r.included_in_return = 'Yes')
                                 FROM return_figures f WHERE f.reporting_period = '2026-09'"""):
        if abs(fig - total) > 0.005:
            errors.append(f"{line}: draft figure {fig} differs from its records {total}")
    for (rid,) in q("""SELECT record_id FROM reporting_records WHERE record_type <> 'Portfolio'
                      AND (counterparty_id IS NULL OR start_date IS NULL OR number_of_accounts <> 1)"""):
        errors.append(f"{rid}: facility or account without customer or start date")
    for (rid,) in q("SELECT record_id FROM reporting_records r JOIN products p USING (product_code) WHERE r.start_date < p.launched_date"):
        errors.append(f"{rid}: starts before its product was launched")
    for (rid,) in q("""SELECT r.record_id FROM reporting_records r JOIN counterparties c USING (counterparty_id)
                      WHERE r.start_date < c.onboarded_date"""):
        errors.append(f"{rid}: starts before the customer was onboarded")
    for system, a, b_ in q("""SELECT a.source_system, a.source_record_ref, b.source_record_ref FROM reporting_records a
                             JOIN reporting_records b ON a.source_system = b.source_system AND a.record_type <> 'Portfolio'
                             AND b.record_type <> 'Portfolio' AND a.start_date < b.start_date AND a.source_record_ref > b.source_record_ref"""):
        errors.append(f"{system}: reference {a} is later than {b_} but started earlier")
    for cid, size, t in q("SELECT counterparty_id, size_class, annual_turnover_gbp FROM counterparties"):
        if size == "SME" and not t <= SME_TURNOVER_LIMIT or size == "Large corporate" and not t > SME_TURNOVER_LIMIT:
            errors.append(f"{cid}: size class {size} disagrees with turnover {t}")
    for (rid,) in q("""SELECT DISTINCT record_id FROM reporting_records GROUP BY source_system, source_record_ref HAVING count(*) > 1"""):
        errors.append(f"{rid}: source reference repeated")
    for (email,) in q("SELECT email FROM staff"):
        if not email.endswith("@" + firm.EMAIL_DOMAIN):
            errors.append(f"{email}: wrong domain")
    return errors
