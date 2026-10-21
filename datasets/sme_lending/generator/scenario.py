"""SME lending dataset.

Thameside Bank, the retail and commercial bank of Thameside Financial Group, lends to small and medium-sized businesses in
London, the South East and the East of England. Its business banking credit team is reviewing the loan applications received
from Wednesday 1 July to Wednesday 30 September 2026. Each row of loan_applications is one application, with the summary the
relationship manager or the online system prepared. Businesses are identified by reference only. The data was extracted at
18:00 on Friday 16 October 2026, so most applications are decided and some are still open.
"""

import datetime as dt
import math
from collections import defaultdict

from generator.common import firm, uk
from generator.common.dataset import Col, Table
from generator.common import staff_register
from generator.common.people import email_for

D = dt.date
Q_START = D(2026, 7, 1)
Q_END = D(2026, 9, 30)
EXTRACT = dt.datetime(2026, 10, 16, 18, 0)
EXTRACT_DATE = EXTRACT.date()
SCORECARD_LIVE = D(2026, 4, 1)

# Lending policy figures (lending_policy holds the wording).
MIN_DSCR, REFER_DSCR = 1.25, 1.40
MAX_LOAN_TO_TURNOVER = 25.0
MIN_TRADING_MONTHS = 24
TURNOVER_MIN, TURNOVER_MAX = 100_000, 25_000_000
ARREARS_DECLINE_DAYS = 30
MIN_CURRENT_RATIO = 1.00
SECURED_ABOVE = 250_000
SCORECARD_LIMIT = 50_000
ACCOUNTS_MAX_MONTHS = 18
MAX_LTV = {"Commercial property": 70.0, "Equipment": 80.0, "Commercial vehicles": 80.0}
VALUATION_MAX_MONTHS = {"Commercial property": 12, "Equipment": 6, "Commercial vehicles": 6}
FORCED_SALE_DISCOUNT = {"Commercial property": 25.0, "Equipment": 50.0, "Commercial vehicles": 40.0}
VALUED_TYPES = tuple(MAX_LTV)

# ------------------------------------------------------------------ schema


def C(*a, **k):
    return Col(*a, **k)


SCHEMA = [
    Table("staff", "lookup", "People in business banking and business banking credit who appear in the records.", [
        C("staff_id", "TEXT", "Staff identifier."),
        C("first_name", "TEXT", "First name."),
        C("last_name", "TEXT", "Surname."),
        C("job_title", "TEXT", "Job title."),
        C("team", "TEXT", "Team."),
        C("office", "TEXT", "Office: City, Canary Wharf or Croydon."),
        C("lending_authority_gbp", "REAL", "Largest loan the person may approve. Credit Committee decisions are recorded against its chair. Empty if the person may not approve loans.", required=False),
        C("email", "TEXT", "Work email address."),
    ]),
    Table("credit_grades", "lookup", "The credit grades the bank's scorecard gives each application, with what the lending policy does with each.", [
        C("credit_grade", "TEXT", "Grade, A (strongest) to E (weakest)."),
        C("grade_name", "TEXT", "Name of the grade."),
        C("one_year_default_rate", "TEXT", "Range of the chance that a business of this grade defaults within a year, as calibrated by the bank."),
        C("policy_outcome", "TEXT", "What the lending policy does with an application of this grade (policy LP-12)."),
    ]),
    Table("lending_policy", "lookup", "Thameside Bank's lending policy for business term loans and commercial mortgages, version 4.2, in force from 1 April 2026: definitions of every figure in the application summary, the tests each application must pass, referral thresholds, security and evidence rules.", [
        C("policy_id", "TEXT", "Policy reference, for example LP-06."),
        C("category", "TEXT", "Definition, Eligibility, Affordability, Liquidity, Security, Evidence or Decision."),
        C("title", "TEXT", "Short name of the policy."),
        C("statement", "TEXT", "The policy in full."),
        C("threshold", "REAL", "The number the test uses, if it has one.", required=False),
        C("unit", "TEXT", "Unit of the threshold: ratio, percent, months, days or GBP.", required=False),
        C("outcome_if_not_met", "TEXT", "What happens to an application that does not meet the policy: Decline, Refer, Awaiting information or Not applicable (a definition)."),
    ]),
    Table("businesses", "lookup", "The businesses that applied. Names are withheld; each business is identified by reference.", [
        C("business_id", "TEXT", "Business reference, for example SME-0041. Numbers rise with the date the business became a customer of Thameside Bank."),
        C("legal_form", "TEXT", "Private limited company, Limited liability partnership, Partnership or Sole trader."),
        C("sector", "TEXT", "Sector: Hospitality, Professional services, Wholesale, Technology, Construction trades, Healthcare, Manufacturing or Logistics."),
        C("sic_code", "TEXT", "Main activity, as a UK SIC 2007 code."),
        C("sic_description", "TEXT", "Description of the SIC code."),
        C("business_description", "TEXT", "What the business does, as recorded by the bank."),
        C("registered_region", "TEXT", "Region of the registered office or main trading address: London, South East or East of England."),
        C("postcode_district", "TEXT", "Postcode district of the main trading address."),
        C("trading_since", "TEXT", "Date the business started trading."),
        C("incorporated_date", "TEXT", "Date of incorporation at Companies House. Empty for a sole trader or partnership.", required=False),
        C("employees", "INTEGER", "Number of employees, including working owners."),
        C("year_end", "TEXT", "Day and month the business's financial year ends, for example 31 March."),
        C("customer_since", "TEXT", "Date the business opened its first account with Thameside Bank."),
        C("relationship_manager_id", "TEXT", "Relationship manager. Empty for a business served by the online business team.", "staff.staff_id", required=False),
    ]),
    Table("financials", "business", "Each business's annual accounts, and management accounts where the business supplied them: profit and loss, cash flow and balance sheet. Figures are in whole pounds.", [
        C("financial_id", "TEXT", "Accounts identifier, for example FIN-0107."),
        C("business_id", "TEXT", "Business the accounts belong to.", "businesses.business_id"),
        C("accounts_type", "TEXT", "Statutory accounts (unaudited), Accountant-prepared accounts (for a sole trader or partnership), or Management accounts (prepared by the business, not full-year accounts)."),
        C("period_start", "TEXT", "First day of the period."),
        C("period_end", "TEXT", "Last day of the period. The balance sheet figures are as at this date."),
        C("turnover_gbp", "REAL", "Turnover (sales) for the period."),
        C("operating_profit_gbp", "REAL", "Operating profit: profit before interest and tax, after depreciation and amortisation."),
        C("depreciation_amortisation_gbp", "REAL", "Depreciation and amortisation charged in arriving at operating profit."),
        C("interest_paid_gbp", "REAL", "Interest paid on borrowing in the period."),
        C("tax_paid_gbp", "REAL", "Corporation tax paid in the period. Zero for a sole trader or partnership, whose owners pay income tax personally."),
        C("dividends_drawings_gbp", "REAL", "Dividends paid to shareholders, or drawings taken by the owners of a sole trader or partnership."),
        C("net_cash_from_operations_gbp", "REAL", "Net cash from operating activities, from the cash flow statement: operating profit plus depreciation and amortisation, less tax paid, less the increase in working capital."),
        C("fixed_assets_gbp", "REAL", "Fixed assets at the period end: property, equipment, vehicles and intangible assets."),
        C("cash_at_bank_gbp", "REAL", "Cash at bank and in hand."),
        C("trade_debtors_gbp", "REAL", "Money owed by customers."),
        C("stock_gbp", "REAL", "Stock and work in progress."),
        C("other_current_assets_gbp", "REAL", "Prepayments and other current assets."),
        C("current_assets_gbp", "REAL", "Total current assets: cash, trade debtors, stock and other current assets."),
        C("trade_creditors_gbp", "REAL", "Money owed to suppliers."),
        C("bank_overdraft_gbp", "REAL", "Overdraft drawn at the period end."),
        C("other_current_liabilities_gbp", "REAL", "Tax, VAT, accruals and loan repayments due within one year."),
        C("current_liabilities_gbp", "REAL", "Total current liabilities: trade creditors, overdraft and other current liabilities."),
        C("long_term_debt_gbp", "REAL", "Loans repayable after more than one year."),
        C("net_assets_gbp", "REAL", "Net assets: fixed assets plus current assets, less current liabilities and long-term debt."),
    ]),
    Table("loan_applications", "business", "Primary table: every application for a business term loan or commercial mortgage received from 1 July to 30 September 2026, with its application summary and its status at the extract.", [
        C("application_id", "TEXT", "Application reference, for example APP-0082. Numbers rise with the date the application was received."),
        C("business_id", "TEXT", "Business that applied.", "businesses.business_id"),
        C("received_date", "TEXT", "Date the application was received. The tests are applied as at this date."),
        C("channel", "TEXT", "Online (the business applied through online banking and the system prepared the summary) or Relationship manager (the relationship manager prepared the summary)."),
        C("sector", "TEXT", "Sector of the business, copied from businesses."),
        C("product", "TEXT", "Term loan or Commercial mortgage."),
        C("loan_purpose", "TEXT", "What the money is for."),
        C("loan_requested_gbp", "REAL", "Amount requested."),
        C("term_years", "INTEGER", "Term of the loan in years. Repayments are monthly, capital and interest."),
        C("interest_rate_pct", "REAL", "Fixed annual interest rate offered, in percent."),
        C("accounts_used_id", "TEXT", "Accounts the summary's turnover, operating profit and cash flow were taken from.", "financials.financial_id"),
        C("annual_turnover_gbp", "REAL", "Summary: annual turnover."),
        C("operating_profit_gbp", "REAL", "Summary: operating profit."),
        C("cash_flow_available_gbp", "REAL", "Summary: cash flow available for debt service (policy LP-02)."),
        C("existing_debt_service_gbp", "REAL", "Summary: existing annual debt service (policy LP-03)."),
        C("proposed_debt_service_gbp", "REAL", "Summary: proposed annual debt service on the loan requested (policy LP-04)."),
        C("dscr", "REAL", "Summary: debt-service coverage ratio (policy LP-05), to two decimal places."),
        C("loan_to_turnover_pct", "REAL", "Summary: loan requested as a percentage of annual turnover, to one decimal place (policy LP-08)."),
        C("ltv_pct", "REAL", "Summary: loan-to-value, to one decimal place (policy LP-15). Empty if no valued property, equipment or vehicle security.", required=False),
        C("credit_grade", "TEXT", "Grade the bank's scorecard gave the application.", "credit_grades.credit_grade"),
        C("summary_notes", "TEXT", "Commentary in the application summary, by the relationship manager or the online system."),
        C("decision_status", "TEXT", "Status at the extract: Approved, Declined, Refer (waiting for a credit officer's decision), Awaiting information, In assessment or Withdrawn."),
        C("referral_reasons", "TEXT", "Why the application was referred to a credit officer. Empty if it was not referred.", required=False),
        C("decision_route", "TEXT", "Who decided: Automated scorecard, Credit manager, Senior credit manager or Credit committee. Empty if not decided.", required=False),
        C("decided_by", "TEXT", "Person who decided, or the Credit Committee's chair. Empty for a scorecard decision or if not decided.", "staff.staff_id", required=False),
        C("decision_date", "TEXT", "Date of the decision, or of the withdrawal. Empty if not decided.", required=False),
        C("status_reason", "TEXT", "The reason recorded for the status: the tests passed or failed, the judgement made, or the information awaited."),
        C("policy_exception", "TEXT", "For an approval that fails a policy test: the exception the Credit Committee agreed and why (policy LP-21). Empty otherwise.", required=False),
        C("conditions", "TEXT", "Conditions of an approval: security to be taken and covenants. Empty unless approved.", required=False),
    ]),
    Table("existing_loans", "business", "Loans each business had when it applied, from Thameside Bank's records and from a credit reference agency report: balances, repayments, arrears and maturity dates, as at the application date. Includes loans repaid in the last two years.", [
        C("loan_id", "TEXT", "Loan identifier, for example EXL-0031."),
        C("business_id", "TEXT", "Business that borrowed.", "businesses.business_id"),
        C("lender", "TEXT", "Lender: Thameside Bank or another bank."),
        C("facility_type", "TEXT", "Term loan, Bounce Back Loan, Coronavirus Business Interruption Loan (CBILS), Hire purchase or Commercial mortgage."),
        C("original_amount_gbp", "REAL", "Amount first lent."),
        C("start_date", "TEXT", "Date the loan was drawn."),
        C("maturity_date", "TEXT", "Date of the final repayment."),
        C("interest_rate_pct", "REAL", "Annual interest rate, in percent."),
        C("monthly_repayment_gbp", "REAL", "Contractual monthly repayment of capital and interest."),
        C("annual_repayment_gbp", "REAL", "Twelve monthly repayments."),
        C("outstanding_balance_gbp", "REAL", "Balance owed at the application date. Zero once repaid."),
        C("loan_status", "TEXT", "Live or Repaid, at the application date."),
        C("repayment_status", "TEXT", "Up to date, In arrears, Payment holiday (with its end date), or Repaid."),
        C("arrears_days", "INTEGER", "Days the oldest missed repayment was overdue at the application date. Zero if none."),
        C("arrears_gbp", "REAL", "Repayments missed and still unpaid at the application date."),
        C("refinanced_by_application_id", "TEXT", "Application whose loan will repay this loan in full, if any.", "loan_applications.application_id", required=False),
        C("source", "TEXT", "Thameside Bank records, or Credit reference agency report for loans from other lenders."),
    ]),
    Table("collateral", "business", "Security offered for each application: what it is, its valuation and date, and its estimated recoverable value.", [
        C("collateral_id", "TEXT", "Security identifier, for example COL-0012."),
        C("application_id", "TEXT", "Application the security is offered for.", "loan_applications.application_id"),
        C("security_type", "TEXT", "Commercial property (first legal charge), Equipment, Commercial vehicles, Debenture (fixed and floating charge over the business's assets) or Personal guarantee."),
        C("description", "TEXT", "What the security is."),
        C("valuation_status", "TEXT", "Valued, Instructed (valuation ordered, not yet received), or Not valued (debentures and guarantees, which the policy does not value)."),
        C("valuation_basis", "TEXT", "RICS Red Book valuation by a panel valuer, or Supplier quotation for new equipment and vehicles. Empty if not valued.", required=False),
        C("valuation_date", "TEXT", "Date of the valuation or quotation. Empty if not valued.", required=False),
        C("market_value_gbp", "REAL", "Market value, or the quoted price of new equipment or vehicles. Empty if not valued.", required=False),
        C("forced_sale_discount_pct", "REAL", "Discount the bank applies for a forced sale (policy LP-15). Empty if not valued.", required=False),
        C("recoverable_value_gbp", "REAL", "Estimated recoverable value: market value less the forced-sale discount. Empty if not valued.", required=False),
    ]),
]

# ------------------------------------------------------------------ reference data

# Each staff member's entry in the firm-wide staff register (generator/common/staff_register.py).
STAFF_REGISTER_IDS = {"STF-01": "TFG-051", "STF-02": "TFG-052", "STF-03": "TFG-053", "STF-04": "TFG-054",
                      "STF-05": "TFG-039", "STF-06": "TFG-040", "STF-07": "TFG-055", "STF-08": "TFG-056"}
AUTHORITY = {"Head of Business Banking Credit": 1_000_000, "Senior Credit Manager": 250_000, "Credit Manager": 100_000}
HEAD, SENIOR, CM1, CM2 = "STF-01", "STF-02", "STF-03", "STF-04"
RMS = ["STF-05", "STF-06", "STF-07", "STF-08"]
ROUTE_BY = {"Credit committee": HEAD, "Senior credit manager": SENIOR}

GRADES = [
    ("A", "Strong", "Below 0.5%", "Eligible"),
    ("B", "Good", "0.5% to 1.5%", "Eligible"),
    ("C", "Satisfactory", "1.5% to 4%", "Eligible"),
    ("D", "Weak", "4% to 10%", "Refer"),
    ("E", "Poor", "Above 10%", "Decline"),
]

POLICY = [
    # id, category, title, statement, threshold, unit, outcome
    ("LP-01", "Definition", "Accounts used in the tests",
     "Every test uses the business's latest full-year accounts: the row in financials for the business, other than management "
     "accounts, with the latest period end on or before the application's received date. Management accounts are supporting "
     "evidence only and are never used in a test.", None, None, "Not applicable"),
    ("LP-02", "Definition", "Cash flow available for debt service",
     "Cash flow available for debt service = operating profit + depreciation and amortisation - tax paid - dividends and "
     "drawings, all from the accounts in LP-01. Interest paid is not deducted, because debt service includes it. Net cash from "
     "operating activities is not used.", None, "GBP", "Not applicable"),
    ("LP-03", "Definition", "Existing annual debt service",
     "Existing annual debt service = the sum of annual_repayment_gbp for every loan in existing_loans that is Live at the "
     "application date, from any lender, except a loan that this application will repay (refinanced_by_application_id). A loan "
     "counts in full even if it ends within the year. A loan in an agreed payment holiday counts at its contractual repayment.",
     None, "GBP", "Not applicable"),
    ("LP-04", "Definition", "Proposed annual debt service",
     "Proposed annual debt service = 12 x the monthly repayment on the loan requested. Monthly repayment = P x r / (1 - (1 + r) "
     "^ -n), where P is the loan requested, r is interest_rate_pct / 100 / 12 and n is term_years x 12, rounded to the nearest "
     "penny before multiplying by 12.", None, "GBP", "Not applicable"),
    ("LP-05", "Definition", "Debt-service coverage ratio (DSCR)",
     "DSCR = cash flow available for debt service (LP-02) / (existing annual debt service (LP-03) + proposed annual debt "
     "service (LP-04)), rounded to two decimal places, halves rounded up. The tests use the rounded figure.", None, "ratio",
     "Not applicable"),
    ("LP-06", "Affordability", "Minimum DSCR",
     "The DSCR must be at least 1.25. An application with a lower DSCR is declined.", MIN_DSCR, "ratio", "Decline"),
    ("LP-07", "Affordability", "DSCR referral band",
     "An application with a DSCR of at least 1.25 but below 1.40 is referred to a credit officer, a person with lending "
     "authority, who decides it. It may not be approved or declined automatically.", REFER_DSCR, "ratio", "Refer"),
    ("LP-08", "Affordability", "Turnover test for unsecured loans",
     "For a loan with no valued property, equipment or vehicle security, the loan requested may not exceed 25% of turnover in "
     "the accounts in LP-01. Loan to turnover = loan requested / turnover x 100, to one decimal place, halves rounded up.",
     MAX_LOAN_TO_TURNOVER, "percent", "Decline"),
    ("LP-09", "Eligibility", "Time trading",
     "The business must have been trading for at least 24 months at the application date, counted from trading_since.",
     MIN_TRADING_MONTHS, "months", "Decline"),
    ("LP-10", "Eligibility", "Size of business",
     "Turnover in the accounts in LP-01 must be at least £100,000 and no more than £25,000,000.", TURNOVER_MAX, "GBP", "Decline"),
    ("LP-11", "Eligibility", "Arrears on existing borrowing",
     "If any Live loan in existing_loans is more than 30 days in arrears at the application date, the application is declined. "
     "If any is 1 to 30 days in arrears, it is referred.", ARREARS_DECLINE_DAYS, "days", "Decline"),
    ("LP-12", "Eligibility", "Credit grade",
     "An application graded E by the scorecard is declined. An application graded D is referred. See credit_grades.", None,
     None, "Decline"),
    ("LP-13", "Liquidity", "Current ratio",
     "Current ratio = current assets / current liabilities, from the accounts in LP-01. An application with a current ratio "
     "below 1.00 is referred.", MIN_CURRENT_RATIO, "ratio", "Refer"),
    ("LP-14", "Definition", "Other liquidity measures",
     "Quick ratio = (current assets - stock) / current liabilities. Debtor days = trade debtors / turnover x 365. Both are "
     "worked out from the same accounts. They have no thresholds; credit officers use them in their judgement (LP-22).", None,
     None, "Not applicable"),
    ("LP-15", "Security", "Loan to value",
     "Loan to value (LTV) = loan requested / the total market value of the Valued property, equipment and vehicle security "
     "offered for the application x 100, to one decimal place, halves rounded up. Debentures and personal guarantees are not "
     "valued and do not count. Recoverable value = market value less the forced-sale discount: 25% for property, 50% for "
     "equipment and 40% for vehicles.", None, "percent", "Not applicable"),
    ("LP-16", "Security", "Maximum LTV for property",
     "A loan secured on commercial property may not exceed 70% LTV.", MAX_LTV["Commercial property"], "percent", "Decline"),
    ("LP-17", "Security", "Maximum LTV for equipment and vehicles",
     "A loan secured on new equipment or commercial vehicles may not exceed 80% of the supplier's quoted price.",
     MAX_LTV["Equipment"], "percent", "Decline"),
    ("LP-18", "Security", "Security for larger loans",
     "A loan above £250,000 must be secured on valued property, equipment or vehicles.", SECURED_ABOVE, "GBP", "Decline"),
    ("LP-19", "Evidence", "Age of valuations",
     "A property valuation must be a RICS Red Book valuation dated no more than 12 months before the decision date. A supplier "
     "quotation for equipment or vehicles must be dated no more than 6 months before the decision date. No decision may be made "
     "on an older valuation, or before an instructed valuation is received; the application waits for a new one.",
     VALUATION_MAX_MONTHS["Commercial property"], "months", "Awaiting information"),
    ("LP-20", "Evidence", "Age of accounts",
     "The accounts in LP-01 must end no more than 18 months before the application date. If they are older, the application "
     "waits for newer full-year accounts. Management accounts do not replace them.", ACCOUNTS_MAX_MONTHS, "months",
     "Awaiting information"),
    ("LP-21", "Decision", "Policy exceptions",
     "An application that fails a test whose outcome is Decline may be approved only by the Credit Committee, as a policy "
     "exception, with the exception and its reason recorded in policy_exception.", None, None, "Decline"),
    ("LP-22", "Decision", "Judgement",
     "Passing every test does not oblige the bank to lend, and a referral is not a decline. A credit officer weighs the "
     "evidence, including trends in the accounts, and records the reason for the decision.", None, None, "Not applicable"),
]

RULES = [
    ("R-01", "Process", "Order of assessment",
     "Each application is assessed in this order. First the evidence (LP-19, LP-20): if it is out of date or missing, the "
     "status is Awaiting information and no test is applied. Then the tests whose outcome is Decline. Then the referral tests "
     "(LP-07, LP-11, LP-12, LP-13). An application that passes every test is approved by whoever has the authority."),
    ("R-02", "Authority", "Who decides",
     "The automated scorecard decides online applications for unsecured term loans of up to £50,000, and only when no referral "
     "test applies; it approves or declines. Otherwise a credit officer decides: Credit Manager up to £100,000, Senior Credit "
     "Manager up to £250,000, Credit Committee above £250,000 and for every policy exception. The Credit Committee meets on "
     "Tuesdays, and its decisions are recorded against its chair, the Head of Business Banking Credit. Relationship managers "
     "prepare applications but may not decide them."),
    ("R-03", "Process", "Application summary",
     "The relationship manager, or for an online application the system, prepares the summary in loan_applications from the "
     "records in financials, existing_loans and collateral, using the definitions in LP-01 to LP-05, LP-08 and LP-15. "
     "accounts_used_id records which accounts were used. The person deciding checks the summary against the records."),
    ("R-04", "Process", "Referrals",
     "A referred application records its referral_reasons and stays at Refer until a credit officer with enough authority "
     "decides it. The officer records the judgement in status_reason."),
    ("R-05", "Process", "Credit grades",
     "The scorecard grades every application when it is received. The score and the factors behind it are held in the "
     "scorecard system, not in this dataset."),
    ("R-06", "Evidence", "Valuations",
     "Property valuations are instructed by the bank from its panel of valuers, at the customer's cost. A valuation the "
     "customer already holds may be used only if it meets LP-19."),
    ("R-07", "Decision", "What a decision means",
     "Approved means credit has been sanctioned. The loan is drawn only once the conditions are met. Declined applications "
     "may be appealed to the Head of Business Banking Credit."),
]

RULE_TABLES = {
    "R-01": "loan_applications, lending_policy", "R-02": "loan_applications, staff", "R-03": "loan_applications, financials, existing_loans, collateral",
    "R-04": "loan_applications", "R-05": "loan_applications, credit_grades", "R-06": "collateral", "R-07": "loan_applications",
}

# Sector profiles: SIC codes with descriptions, turnover range, operating margin, depreciation, working capital days,
# fixed assets as a share of turnover, legal forms, staff per £100,000 of turnover.
SECTORS = {
    "Hospitality": dict(w=22, T=(180_000, 2_400_000), m=(0.07, 0.13), da=(0.03, 0.05), dd=(2, 6), sd=(4, 9), cd=(18, 30), fa=(0.15, 0.35),
                        forms=[("Private limited company", 8), ("Sole trader", 1), ("Partnership", 1)], epk=1.5, sics=[
        ("56102", "Unlicensed restaurants and cafes", ["Independent café and bakery", "Coffee shop with two sites", "Café and brunch restaurant", "Breakfast café near a station"]),
        ("56101", "Licensed restaurants", ["Neighbourhood restaurant, about 60 covers", "Turkish grill restaurant", "Pizza restaurant with delivery", "Vietnamese restaurant"]),
        ("56302", "Public houses and bars", ["Leasehold pub with food", "Cocktail bar", "Freehold pub with rooms"]),
        ("56103", "Take-away food shops and mobile food stands", ["Caribbean takeaway", "Street-food business with three market stalls"]),
    ], purposes=["Fit-out of a second site", "Kitchen equipment", "Refurbishment of the existing site", "Working capital", "New coffee and bakery equipment"]),
    "Professional services": dict(w=20, T=(300_000, 4_500_000), m=(0.12, 0.22), da=(0.01, 0.02), dd=(45, 70), sd=(0, 3), cd=(15, 28), fa=(0.04, 0.12),
                                  forms=[("Private limited company", 6), ("Limited liability partnership", 3), ("Partnership", 1)], epk=1.0, sics=[
        ("69201", "Accounting and auditing activities", ["Accountancy practice for owner-managed businesses", "Bookkeeping and payroll bureau"]),
        ("69102", "Solicitors", ["High-street solicitors: conveyancing and wills", "Employment law practice"]),
        ("71111", "Architectural activities", ["Architecture practice, residential and schools", "Small architecture studio"]),
        ("70229", "Management consultancy activities other than financial management", ["Operations consultancy for housing associations", "HR consultancy"]),
        ("73110", "Advertising agencies", ["Design and advertising agency"]),
    ], purposes=["Acquisition of a retiring partner's share", "Office fit-out", "Working capital for a new contract", "Acquisition of a smaller practice", "New practice management system"]),
    "Wholesale": dict(w=18, T=(900_000, 11_000_000), m=(0.025, 0.055), da=(0.005, 0.012), dd=(32, 55), sd=(30, 60), cd=(30, 50), fa=(0.03, 0.08),
                      forms=[("Private limited company", 1)], epk=0.18, sics=[
        ("46390", "Non-specialised wholesale of food, beverages and tobacco", ["Food wholesaler supplying restaurants", "Cash-and-carry for convenience stores", "Halal meat and grocery wholesaler"]),
        ("46499", "Wholesale of other household goods", ["Wholesaler of kitchenware and homeware", "Gift and toy wholesaler"]),
        ("46690", "Wholesale of other machinery and equipment", ["Distributor of catering equipment", "Wholesaler of electrical fittings"]),
        ("46460", "Wholesale of pharmaceutical goods", ["Wholesaler of pharmacy and medical supplies"]),
    ], purposes=["Stock for a new supply contract", "Warehouse racking and forklift trucks", "Working capital", "Delivery vans", "New warehouse management system"]),
    "Technology": dict(w=16, T=(400_000, 7_000_000), m=(0.09, 0.19), da=(0.02, 0.05), dd=(38, 62), sd=(0, 1), cd=(18, 35), fa=(0.03, 0.10),
                       forms=[("Private limited company", 1)], epk=0.9, sics=[
        ("62012", "Business and domestic software development", ["Software house building booking systems for gyms", "Developer of payroll software for small firms"]),
        ("62020", "Information technology consultancy activities", ["IT consultancy for schools and charities", "Cloud migration consultancy"]),
        ("62090", "Other information technology service activities", ["Managed IT support for small offices", "Cyber security services for professional firms"]),
        ("63110", "Data processing, hosting and related activities", ["Hosting and data backup services"]),
    ], purposes=["Hiring developers for a new product", "Server and network equipment", "Office fit-out", "Acquisition of a smaller competitor", "Working capital"]),
    "Construction trades": dict(w=8, T=(400_000, 5_000_000), m=(0.05, 0.10), da=(0.015, 0.03), dd=(40, 60), sd=(5, 14), cd=(30, 45), fa=(0.06, 0.15),
                                forms=[("Private limited company", 5), ("Sole trader", 1)], epk=0.8, sics=[
        ("43220", "Plumbing, heat and air-conditioning installation", ["Heating and heat-pump installer", "Commercial plumbing contractor"]),
        ("43210", "Electrical installation", ["Electrical contractor for shops and offices", "Electric vehicle charger installer"]),
        ("43390", "Other building completion and finishing", ["Shopfitting and joinery contractor"]),
    ], purposes=["Vans and tools", "Working capital", "Heat-pump training centre fit-out"]),
    "Healthcare": dict(w=7, T=(500_000, 3_000_000), m=(0.12, 0.22), da=(0.03, 0.06), dd=(5, 14), sd=(3, 7), cd=(15, 28), fa=(0.2, 0.45),
                       forms=[("Private limited company", 3), ("Partnership", 1)], epk=1.2, sics=[
        ("86230", "Dental practice activities", ["Mixed NHS and private dental practice", "Private dental practice, four surgeries"]),
        ("75000", "Veterinary activities", ["Small-animal veterinary practice"]),
        ("86900", "Other human health activities", ["Physiotherapy and sports injury clinic"]),
    ], purposes=["Dental chairs and imaging equipment", "Practice refurbishment", "Acquisition of a second practice"]),
    "Manufacturing": dict(w=5, T=(600_000, 7_000_000), m=(0.05, 0.11), da=(0.03, 0.06), dd=(35, 55), sd=(25, 45), cd=(30, 45), fa=(0.2, 0.4),
                          forms=[("Private limited company", 1)], epk=0.6, sics=[
        ("10710", "Manufacture of bread; manufacture of fresh pastry goods and cakes", ["Wholesale bakery supplying cafés"]),
        ("25620", "Machining", ["Precision engineering workshop"]),
        ("18129", "Printing n.e.c.", ["Commercial printer, packaging and labels"]),
    ], purposes=["New production machinery", "Factory extension", "Working capital"]),
    "Logistics": dict(w=4, T=(500_000, 5_500_000), m=(0.04, 0.08), da=(0.05, 0.08), dd=(35, 52), sd=(0, 2), cd=(25, 40), fa=(0.25, 0.45),
                      forms=[("Private limited company", 1)], epk=0.5, sics=[
        ("49410", "Freight transport by road", ["Same-day courier and pallet delivery", "Temperature-controlled delivery for food producers"]),
        ("53202", "Unlicensed carrier", ["Parcel delivery subcontractor"]),
    ], purposes=["Commercial vehicles", "Working capital", "Depot fit-out"]),
}

REGIONS = {
    "London": (60, ["E1", "E2", "E8", "E14", "E15", "E17", "N1", "N4", "N16", "N17", "NW1", "NW10", "SE1", "SE8", "SE15",
                    "SE18", "SW2", "SW9", "SW11", "SW18", "W3", "W12", "EC1V", "EC2A", "WC1X", "CR0", "HA1", "IG1", "BR1", "UB3"]),
    "South East": (25, ["GU1", "GU14", "RH1", "RH10", "ME14", "ME4", "TN1", "BN1", "BN3", "CT1", "RG1", "SL1", "MK9", "OX4", "KT1", "DA1"]),
    "East of England": (15, ["CM1", "CM20", "SS1", "SS14", "AL1", "CB1", "CO1", "IP1", "LU1", "SG1", "WD17", "HP2", "RM1"]),
}
OTHER_BANKS = ["Barclays", "HSBC UK", "Lloyds Bank", "NatWest", "Santander UK", "Metro Bank"]
PROPERTY = {
    "Hospitality": "Freehold café and restaurant premises with a flat above", "Professional services": "Freehold office building",
    "Wholesale": "Freehold warehouse with yard", "Technology": "Freehold office unit on a business park",
    "Construction trades": "Freehold yard with workshop and office", "Healthcare": "Freehold surgery premises",
    "Manufacturing": "Freehold light industrial unit", "Logistics": "Freehold depot with parking for 20 vehicles",
}
MORTGAGE_PURPOSE = "Purchase of the freehold of the trading premises"
WITHDRAWN = ["found a cheaper offer from another lender", "the project was postponed", "the business chose to fund the purchase from cash",
             "the landlord withdrew the lease of the new site"]

# ------------------------------------------------------------------ helpers


def iso(d):
    return d.isoformat() if d else None


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    last = (D(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
    return D(y, m, min(d.day, last))


def months_between(a, b):
    """Whole months from a to b."""
    n = (b.year - a.year) * 12 + b.month - a.month
    return n - (b.day < a.day)


def half_up(x, places):
    f = 10 ** places
    return math.floor(x * f + 0.5) / f


def gbp(x):
    return f"£{x:,.2f}"


def gbp0(x):
    return f"£{x:,.0f}"


def r2(x):
    return round(float(x), 2)


def monthly_repayment(principal, rate_pct, months):
    r = rate_pct / 100 / 12
    return round(principal * r / (1 - (1 + r) ** -months), 2)


def balance_after(principal, rate_pct, months, k):
    """Balance after k monthly repayments of an amortising loan."""
    if k <= 0:
        return float(principal)
    if k >= months:
        return 0.0
    r = rate_pct / 100 / 12
    pay = principal * r / (1 - (1 + r) ** -months)
    return round(principal * (1 + r) ** k - pay * ((1 + r) ** k - 1) / r, 2)


def next_tuesday(d):
    d = uk.next_working_day(d)
    while d.weekday() != 1 or not uk.is_working_day(d):
        d += dt.timedelta(days=1)
    return d


def year_end_on_or_before(month, day, d):
    """The latest year end (given month and day) on or before d."""
    y = d.year
    while True:
        ye = D(y, month, day)
        if ye <= d:
            return ye
        y -= 1


class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.rows = defaultdict(list)
        self.cases, self.case_records = [], []
        self.apps = []
        self.K = {}
        self.rm_cycle = 0
        self.cm_cycle = 0

    # ---- answer key

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
                "team": "Business Banking Credit" if p["job_title"] in AUTHORITY else "Business Banking", "office": p["office"],
                "lending_authority_gbp": float(AUTHORITY[p["job_title"]]) if p["job_title"] in AUTHORITY else None,
                "email": email_for(p["first_name"], p["last_name"], firm.EMAIL_DOMAIN)})
        self.rows["credit_grades"] = [dict(zip(["credit_grade", "grade_name", "one_year_default_rate", "policy_outcome"], g)) for g in GRADES]
        self.rows["lending_policy"] = [dict(zip(["policy_id", "category", "title", "statement", "threshold", "unit", "outcome_if_not_met"], p))
                                       for p in POLICY]

    # ---- businesses and their accounts

    def business(self, sector, received, *, trading_months=None, form=None, region=None, sic=None, desc=None, rm="auto",
                 year_end=None, customer_months=None):
        rng = self.rng
        prof = SECTORS[sector]
        form = form or rng.choices([f for f, _ in prof["forms"]], [w for _, w in prof["forms"]])[0]
        code, sic_desc, descs = sic or rng.choice(prof["sics"])
        region = region or rng.choices(list(REGIONS), [v[0] for v in REGIONS.values()])[0]
        months = trading_months or rng.choice([30, 40, 52, 64, 75, 90, 110, 130, 160, 200, 260, 330])
        since = add_months(received, -months) - dt.timedelta(days=rng.randint(0, 25))
        since = uk.next_working_day(since)
        inc = None
        if form in ("Private limited company", "Limited liability partnership"):
            inc = since - dt.timedelta(days=rng.randint(7, 60))
        if customer_months is None:
            customer_months = rng.randint(1, max(2, months - 1)) if rng.random() < 0.8 else 0
        cust = min(received - dt.timedelta(days=rng.randint(14, 40)), add_months(since, max(0, months - customer_months)))
        cust = max(cust, since)
        ye = year_end or rng.choice([(3, 31), (3, 31), (12, 31), (12, 31), (6, 30), (9, 30), (4, 30), (8, 31)])
        return {"legal_form": form, "sector": sector, "sic_code": code, "sic_description": sic_desc,
                "business_description": desc or rng.choice(descs), "registered_region": region,
                "postcode_district": rng.choice(REGIONS[region][1]), "trading_since": since, "incorporated_date": inc,
                "employees": None, "year_end": ye, "customer_since": cust, "rm": rm}

    def accounts(self, b, T, *, period_end, months=12, kind=None, m, da, tax, div, interest, cr, dd, sd, cd, fa, ltd,
                 other_cl_extra=0.0, overdraft=0.0, prev=None):
        """One set of accounts. Current ratio cr is met by setting cash (and an overdraft if cash would go negative)."""
        rng = self.rng
        OP = round(T * m)
        DA = round(T * da)
        debt = round(T * dd / 365)
        stock = round(T * sd / 365)
        cred = round(T * cd / 365)
        oca = round(T * rng.uniform(0.005, 0.015))
        ocl = round(T * rng.uniform(0.03, 0.05) + other_cl_extra)
        od = round(overdraft)
        noncash = debt + stock + oca
        cash = round(cr * (cred + od + ocl) - noncash)
        if cash < 1_500:
            # Cash alone cannot reach the ratio: the business is using its overdraft.
            cash = rng.randint(1_500, 6_000)
            od = max(od, round((noncash + cash) / cr - cred - ocl))
        cl = cred + od + ocl
        ca = cash + debt + stock + oca
        fixed = round(T * fa)
        wc = debt + stock + oca - cred - ocl
        if prev is None:
            ncfo = OP + DA - tax - round(T * rng.uniform(-0.01, 0.02))
        else:
            prev_wc = prev["trade_debtors_gbp"] + prev["stock_gbp"] + prev["other_current_assets_gbp"] - prev["trade_creditors_gbp"] - prev["other_current_liabilities_gbp"]
            ncfo = OP + DA - tax - (wc - prev_wc)
        kind = kind or ("Statutory accounts (unaudited)" if b["incorporated_date"] else "Accountant-prepared accounts")
        start = add_months(period_end + dt.timedelta(days=1), -months)
        return {"business": b, "accounts_type": kind, "period_start": start, "period_end": period_end,
                "turnover_gbp": float(round(T)), "operating_profit_gbp": float(OP), "depreciation_amortisation_gbp": float(DA),
                "interest_paid_gbp": float(round(interest)), "tax_paid_gbp": float(round(tax)), "dividends_drawings_gbp": float(round(div)),
                "net_cash_from_operations_gbp": float(round(ncfo)), "fixed_assets_gbp": float(fixed), "cash_at_bank_gbp": float(cash),
                "trade_debtors_gbp": float(debt), "stock_gbp": float(stock), "other_current_assets_gbp": float(oca),
                "current_assets_gbp": float(ca), "trade_creditors_gbp": float(cred), "bank_overdraft_gbp": float(od),
                "other_current_liabilities_gbp": float(ocl), "current_liabilities_gbp": float(cl), "long_term_debt_gbp": float(round(ltd)),
                "net_assets_gbp": float(fixed + ca - cl - round(ltd))}

    @staticmethod
    def corp_tax(profit):
        """Corporation tax on a year's profit: 19% up to £50,000, 25% above £250,000, marginal relief between."""
        if profit <= 0:
            return 0.0
        if profit <= 50_000:
            return profit * 0.19
        if profit >= 250_000:
            return profit * 0.25
        return profit * 0.25 - (250_000 - profit) * 0.015

    @staticmethod
    def cfads(f):
        return f["operating_profit_gbp"] + f["depreciation_amortisation_gbp"] - f["tax_paid_gbp"] - f["dividends_drawings_gbp"]

    # ---- existing loans

    def loan(self, b, received, lender, ftype, amount, start, rate, n, *, first_after=1, status_note=None, arrears_days=0):
        first = add_months(start, first_after)
        maturity = add_months(first, n - 1)
        pay = monthly_repayment(amount, rate, n)
        made = 0 if received < first else months_between(first, received) + 1
        live = maturity >= received
        bal = balance_after(amount, rate, n, made) if live else 0.0
        if live and bal <= 0:
            bal = pay
        rs = "Repaid" if not live else ("In arrears" if arrears_days else (status_note or "Up to date"))
        missed = math.ceil(arrears_days / 30) if arrears_days else 0
        return {"business": b, "lender": lender, "facility_type": ftype, "original_amount_gbp": float(amount), "start_date": start,
                "maturity_date": maturity, "interest_rate_pct": rate, "monthly_repayment_gbp": pay, "annual_repayment_gbp": r2(12 * pay),
                "outstanding_balance_gbp": r2(bal), "loan_status": "Live" if live else "Repaid",
                "repayment_status": rs, "arrears_days": arrears_days if live else 0, "arrears_gbp": r2(missed * pay) if live else 0.0,
                "refinanced_by": None, "source": "Thameside Bank records" if lender == "Thameside Bank" else "Credit reference agency report",
                "first": first, "n": n}

    def existing_loans(self, b, received, T, *, kinds=None, holiday=False):
        """A typical mix of borrowing for a business of this size and age."""
        rng = self.rng
        out = []
        since = b["trading_since"]
        kinds = kinds if kinds is not None else [k for k, p in [("bbl", 0.35), ("cbils", 0.10), ("tsb", 0.28), ("hp", 0.22)]
                                                 if rng.random() < p]
        for k in kinds:
            if k == "bbl" and since < D(2020, 3, 1):
                amt = max(2_000, min(50_000, round(T * rng.uniform(0.6, 0.95) * 0.25, -3)))
                start = uk.next_working_day(D(2020, 5, 4) + dt.timedelta(days=rng.randint(0, 180)))
                n = rng.choice([60, 108, 108])
                note = None
                if holiday and n == 108:
                    note = f"Payment holiday (Pay As You Grow) until {iso(add_months(received, rng.randint(2, 4)).replace(day=1))}"
                out.append(self.loan(b, received, rng.choice(OTHER_BANKS + ["Thameside Bank"]), "Bounce Back Loan", amt, start, 2.5, n,
                                     first_after=12, status_note=note))
            elif k == "cbils" and since < D(2020, 1, 1):
                amt = round(min(250_000, T * rng.uniform(0.06, 0.12)), -3)
                start = uk.next_working_day(D(2020, 7, 1) + dt.timedelta(days=rng.randint(0, 240)))
                out.append(self.loan(b, received, rng.choice(OTHER_BANKS), "Coronavirus Business Interruption Loan (CBILS)", amt, start,
                                     round(rng.uniform(4.2, 6.4), 2), rng.choice([48, 60, 60]), first_after=12))
            elif k == "tsb":
                amt = round(T * rng.uniform(0.03, 0.08), -3)
                start = uk.next_working_day(add_months(received, -rng.randint(6, 44)))
                if start < since:
                    continue
                out.append(self.loan(b, received, "Thameside Bank", "Term loan", max(10_000, amt), start,
                                     round(rng.uniform(6.4, 9.2), 2), rng.choice([36, 48, 60, 60, 84])))
            elif k == "hp":
                amt = round(T * rng.uniform(0.015, 0.045), -2)
                start = uk.next_working_day(add_months(received, -rng.randint(4, 40)))
                if start < since:
                    continue
                out.append(self.loan(b, received, rng.choice(OTHER_BANKS), "Hire purchase", max(6_000, amt), start,
                                     round(rng.uniform(6.9, 9.9), 2), rng.choice([36, 48, 60])))
        return out

    # ---- one application

    def make(self, sector, *, received, expect, product="Term loan", security=None, amount=(25_000, 100_000), dscr=(1.45, 2.6),
             channel=None, cr=(1.15, 2.1), grade=None, trading_months=None, form=None, loans=None, holiday=False, arrears=0,
             refinance=False, turnover_test="pass", ltv=(0.5, 0.68), valuation="valued", stale_accounts=False, mgmt=False,
             fate="decide", key=None, purpose=None, notes=None, sic=None, desc=None, profit_growth=None, cr_prior=None,
             dd_latest=None, dd_prior=None, fa_jump=False, val_age=(15, 120), decide_after=None, T_range=None, step=None,
             term=None, rate=None, margin=None):
        rng = self.rng
        prof = SECTORS[sector]
        for attempt in range(3000):
            b = self.business(sector, received, trading_months=trading_months, form=form, sic=sic, desc=desc)
            lo, hi = T_range or prof["T"]
            T = math.exp(rng.uniform(math.log(lo), math.log(hi)))
            g = rng.uniform(-0.04, 0.16)
            m = rng.uniform(*margin) if margin else rng.uniform(*prof["m"])
            pg = profit_growth if profit_growth is not None else rng.uniform(-0.12, 0.2)
            T_p = T / (1 + g)
            OP_p = T * m / (1 + pg)
            m_p = OP_p / T_p
            da = rng.uniform(*prof["da"])
            company = b["incorporated_date"] is not None
            # Accounts timing: the latest year end at least four months before the application.
            ye_m, ye_d = b["year_end"]
            ye = year_end_on_or_before(ye_m, ye_d, add_months(received, -4))
            if stale_accounts:
                ye = year_end_on_or_before(ye_m, ye_d, add_months(received, -19))
                if months_between(ye, received) > 23:
                    continue
            if months_between(ye, received) > 16 and not stale_accounts:
                continue
            years = 1 if months_between(b["trading_since"], ye) < 24 else 2
            if months_between(b["trading_since"], ye) < 12:
                continue
            ex = loans if loans is not None else None
            ex = self.existing_loans(b, received, T, kinds=ex, holiday=holiday)
            if refinance and not any(x["lender"] == "Thameside Bank" and x["loan_status"] == "Live" and x["facility_type"] == "Term loan" for x in ex):
                continue
            if arrears and not any(x["loan_status"] == "Live" and x["facility_type"] != "Bounce Back Loan" and x["lender"] != "Thameside Bank" for x in ex):
                continue
            interest = sum(x["outstanding_balance_gbp"] * x["interest_rate_pct"] / 100 for x in ex if x["loan_status"] == "Live")
            tax = self.corp_tax(OP_p - interest) if company else 0.0
            post = T * m - tax
            div = post * rng.uniform(0.25, 0.55) if company else T * m * rng.uniform(0.5, 0.7)
            cf = T * m + T * da - tax - div
            if cf <= 0:
                continue
            refi = [x for x in ex if x["lender"] == "Thameside Bank" and x["loan_status"] == "Live" and x["facility_type"] == "Term loan"][:1] if refinance else []
            E = sum(x["annual_repayment_gbp"] for x in ex if x["loan_status"] == "Live" and x not in refi)
            target = rng.uniform(*dscr)
            P_allowed = cf / target - E
            if P_allowed <= 1_000:
                continue
            yrs = term or (rng.choice([15, 18, 20]) if product == "Commercial mortgage" else
                           rng.choice([7, 8, 10]) if security == "property" else rng.choice([3, 4, 5]) if security else rng.choice([2, 3, 4, 5]))
            rt = rate or round(rng.uniform(6.6, 7.9) if product == "Commercial mortgage" else rng.uniform(7.2, 8.9) if security else rng.uniform(8.4, 11.4), 2)
            r = rt / 100 / 12
            n = yrs * 12
            L = P_allowed / 12 * (1 - (1 + r) ** -n) / r
            st = step or (2_500 if L < 60_000 else 5_000 if L < 400_000 else 10_000)
            L = math.floor(L / st) * st
            if refi:
                if L <= refi[0]["outstanding_balance_gbp"] + 20_000 or E == 0:
                    continue
            if not amount[0] <= L <= amount[1]:
                continue
            ltt = half_up(L / T * 100, 1)
            unsecured = security is None
            if unsecured and turnover_test == "pass" and ltt > MAX_LOAN_TO_TURNOVER:
                continue
            if unsecured and turnover_test == "fail" and ltt <= MAX_LOAN_TO_TURNOVER:
                continue
            Pd = r2(12 * monthly_repayment(L, rt, n))
            break
        else:
            raise RuntimeError(f"could not make an application for {sector} {expect} {key}")

        # The accounts, prior year first.
        cr_l = rng.uniform(*cr)
        cr_p = cr_prior or cr_l * rng.uniform(0.9, 1.12)
        dd_p = dd_prior or rng.uniform(*prof["dd"])
        dd_l = dd_latest or dd_p * rng.uniform(0.92, 1.08)
        sd, cd = rng.uniform(*prof["sd"]), rng.uniform(*prof["cd"])
        fa = rng.uniform(*prof["fa"])
        ltd = sum(x["outstanding_balance_gbp"] for x in ex if x["loan_status"] == "Live") * 0.8
        due = sum(min(x["annual_repayment_gbp"], x["outstanding_balance_gbp"]) for x in ex if x["loan_status"] == "Live") * 0.8
        fins = []
        prev = None
        if years == 2:
            tax_pp = self.corp_tax(OP_p * 0.95 - interest) if company else 0.0
            div_p = (OP_p - tax_pp) * rng.uniform(0.25, 0.5) if company else OP_p * rng.uniform(0.5, 0.7)
            prev = self.accounts(b, T_p, period_end=add_months(ye, -12), m=m_p, da=da, tax=tax_pp, div=div_p, interest=interest * 1.1,
                                 cr=cr_p, dd=dd_p, sd=sd, cd=cd, fa=fa, ltd=ltd * 1.15, other_cl_extra=due)
            fins.append(prev)
        fa_l = fa * (2.2 if fa_jump else 1.0)
        latest = self.accounts(b, T, period_end=ye, m=m, da=da, tax=tax, div=div, interest=interest, cr=cr_l, dd=dd_l, sd=sd, cd=cd,
                               fa=fa_l, ltd=ltd, other_cl_extra=due, prev=prev)
        fins.append(latest)
        used = latest
        if mgmt:
            me = (received.replace(day=1) - dt.timedelta(days=1)).replace(day=1) - dt.timedelta(days=1)  # the month end before last
            mg = self.accounts(b, T * rng.uniform(1.12, 1.22), period_end=me, kind="Management accounts", m=m * 1.25, da=da, tax=tax * 1.1,
                               div=div, interest=interest, cr=cr_l * 1.05, dd=dd_l, sd=sd, cd=cd, fa=fa, ltd=ltd, other_cl_extra=due,
                               prev=latest)
            fins.append(mg)
        months_trading = months_between(b["trading_since"], received)
        b["employees"] = max(2, round(T / 100_000 * prof["epk"] * rng.uniform(0.8, 1.2)))

        app = {"business": b, "received": received, "expect": expect, "product": product, "security": security,
               "loan": float(L), "term": yrs, "rate": rt, "proposed": Pd, "fins": fins, "used": used, "latest": latest,
               "loans": ex, "refi": refi, "collateral": [], "fate": fate, "key": key, "months_trading": months_trading,
               "arrears": arrears, "channel": channel, "notes": notes, "decide_after": decide_after,
               "purpose": purpose or (MORTGAGE_PURPOSE if product == "Commercial mortgage" else rng.choice(prof["purposes"]))}
        if arrears:
            x = next(x for x in ex if x["loan_status"] == "Live" and x["facility_type"] != "Bounce Back Loan" and x["lender"] != "Thameside Bank")
            missed = math.ceil(arrears / 30)
            x.update(arrears_days=arrears, arrears_gbp=r2(missed * x["monthly_repayment_gbp"]), repayment_status="In arrears")
        for x in refi:
            x["refinanced_by"] = app
        self.collateral(app, security, ltv, valuation, val_age)
        self.summary(app)
        app["grade"] = grade or self.grade(app)
        self.apps.append(app)
        if key:
            self.K[key] = app
        return app

    def collateral(self, app, security, ltv, valuation, val_age):
        rng = self.rng
        b, L, rec = app["business"], app["loan"], app["received"]
        if security:
            stype = {"property": "Commercial property", "equipment": "Equipment", "vehicles": "Commercial vehicles"}[security]
            target = rng.uniform(*ltv)
            V = math.ceil(L / target / (5_000 if security == "property" else 500)) * (5_000 if security == "property" else 500)
            if security == "property":
                desc = f"{PROPERTY[b['sector']]}, {b['postcode_district']}"
                basis = "RICS Red Book valuation by a panel valuer"
            else:
                desc = {"equipment": f"New equipment: {app['purpose'].lower()}", "vehicles": "Three new 3.5-tonne panel vans"}[security]
                basis = "Supplier quotation"
            vd = valuation if isinstance(valuation, D) else rec - dt.timedelta(days=rng.randint(*val_age))
            if valuation == "instructed":
                app["collateral"].append({"security_type": stype, "description": desc, "valuation_status": "Instructed",
                                          "valuation_basis": None, "valuation_date": None, "market_value_gbp": None,
                                          "forced_sale_discount_pct": None, "recoverable_value_gbp": None,
                                          "instructed": uk.add_working_days(rec, rng.randint(3, 8))})
            else:
                app["collateral"].append({"security_type": stype, "description": desc, "valuation_status": "Valued",
                                          "valuation_basis": basis, "valuation_date": vd, "market_value_gbp": float(V),
                                          "forced_sale_discount_pct": FORCED_SALE_DISCOUNT[stype],
                                          "recoverable_value_gbp": r2(V * (1 - FORCED_SALE_DISCOUNT[stype] / 100))})
        if b["incorporated_date"] and L > 25_000:
            app["collateral"].append({"security_type": "Debenture", "description": "Fixed and floating charge over the company's assets",
                                      "valuation_status": "Not valued", "valuation_basis": None, "valuation_date": None,
                                      "market_value_gbp": None, "forced_sale_discount_pct": None, "recoverable_value_gbp": None})
        if b["incorporated_date"] and not security and L <= 150_000:
            pg = math.ceil(L * 0.5 / 5_000) * 5_000
            app["collateral"].append({"security_type": "Personal guarantee", "description": f"Guarantee from the directors, limited to {gbp0(pg)}",
                                      "valuation_status": "Not valued", "valuation_basis": None, "valuation_date": None,
                                      "market_value_gbp": None, "forced_sale_discount_pct": None, "recoverable_value_gbp": None})

    def summary(self, app):
        """The application summary, worked out with the policy definitions."""
        f = app["used"]
        live = [x for x in app["loans"] if x["loan_status"] == "Live" and x["refinanced_by"] is not app]
        app["turnover"] = f["turnover_gbp"]
        app["op"] = f["operating_profit_gbp"]
        app["cf"] = self.cfads(f)
        app["existing"] = r2(sum(x["annual_repayment_gbp"] for x in live))
        app["dscr"] = half_up(app["cf"] / (app["existing"] + app["proposed"]), 2)
        app["ltt"] = half_up(app["loan"] / app["turnover"] * 100, 1)
        valued = [c for c in app["collateral"] if c["valuation_status"] == "Valued"]
        app["ltv"] = half_up(app["loan"] / sum(c["market_value_gbp"] for c in valued) * 100, 1) if valued else None

    def grade(self, app):
        d, f = app["dscr"], app["latest"]
        cr = f["current_assets_gbp"] / f["current_liabilities_gbp"]
        yrs = app["months_trading"] / 12
        pts = (3 if d >= 2.2 else 2 if d >= 1.7 else 1 if d >= 1.4 else 0) + (2 if cr >= 1.5 else 1 if cr >= 1.15 else 0) \
            + (2 if yrs >= 10 else 1 if yrs >= 5 else 0) - (2 if app["arrears"] else 0) + self.rng.choice([-1, 0, 0, 1])
        g = "A" if pts >= 6 else "B" if pts >= 4 else "C" if pts >= 2 else "D" if pts >= 1 else "E"
        if app["expect"] in ("approve", "refer_band") and g in ("D", "E"):
            g = "C"
        if app["expect"] == "refer_band" and g == "A":
            g = "B"
        return g

    # ---- the policy, applied

    @staticmethod
    def assess(app, decision_date=None):
        """What the policy requires: (information awaited, decline reasons, referral reasons)."""
        info, dec, ref = [], [], []
        f = app["latest"]
        rec = app["received"]
        if f["period_end"] < add_months(rec, -ACCOUNTS_MAX_MONTHS):
            info.append(f"Latest full-year accounts end {iso(f['period_end'])}, more than 18 months before the application (LP-20)")
        when = decision_date or EXTRACT_DATE
        for c in app["collateral"]:
            if c["security_type"] not in VALUED_TYPES:
                continue
            if c["valuation_status"] == "Instructed":
                info.append(f"RICS valuation instructed {iso(c['instructed'])}, not yet received (LP-19)")
            elif c["valuation_date"] < add_months(when, -VALUATION_MAX_MONTHS[c["security_type"]]):
                info.append(f"Valuation dated {iso(c['valuation_date'])} is out of date (LP-19)")
        cf = Builder.cfads(f)
        live = [x for x in app["loans"] if x["loan_status"] == "Live" and x["refinanced_by"] is not app]
        E = sum(x["annual_repayment_gbp"] for x in live)
        d = half_up(cf / (E + app["proposed"]), 2)
        T = f["turnover_gbp"]
        valued = [c for c in app["collateral"] if c["valuation_status"] == "Valued" and c["security_type"] in VALUED_TYPES]
        if app["months_trading"] < MIN_TRADING_MONTHS:
            dec.append(f"Trading for {app['months_trading']} months, less than 24 (LP-09)")
        if not TURNOVER_MIN <= T <= TURNOVER_MAX:
            dec.append(f"Turnover {gbp0(T)} outside £100,000 to £25,000,000 (LP-10)")
        if d < MIN_DSCR:
            dec.append(f"DSCR {d:.2f} is below the minimum of 1.25 (LP-06)")
        if not valued and not any(c["valuation_status"] == "Instructed" for c in app["collateral"]):
            ltt = half_up(app["loan"] / T * 100, 1)
            if ltt > MAX_LOAN_TO_TURNOVER:
                dec.append(f"Loan is {ltt:.1f}% of turnover, above 25% (LP-08)")
            if app["loan"] > SECURED_ABOVE:
                dec.append("Loan above £250,000 without valued security (LP-18)")
        if valued:
            ltv = half_up(app["loan"] / sum(c["market_value_gbp"] for c in valued) * 100, 1)
            limit = min(MAX_LTV[c["security_type"]] for c in valued)
            if ltv > limit:
                dec.append(f"LTV {ltv:.1f}% is above the maximum of {limit:.0f}% ({'LP-16' if limit == 70 else 'LP-17'})")
        worst = max([x["arrears_days"] for x in app["loans"] if x["loan_status"] == "Live"] or [0])
        if worst > ARREARS_DECLINE_DAYS:
            dec.append(f"An existing loan is {worst} days in arrears (LP-11)")
        elif worst > 0:
            ref.append(f"An existing loan is {worst} days in arrears (LP-11)")
        if app["grade"] == "E":
            dec.append("Credit grade E (LP-12)")
        if app["grade"] == "D":
            ref.append("Credit grade D (LP-12)")
        if MIN_DSCR <= d < REFER_DSCR:
            ref.append(f"DSCR {d:.2f} is in the referral band, 1.25 to 1.40 (LP-07)")
        cr = f["current_assets_gbp"] / f["current_liabilities_gbp"]
        if cr < MIN_CURRENT_RATIO:
            ref.append(f"Current ratio {cr:.2f} is below 1.00 (LP-13)")
        return info, dec, ref

    def route(self, app):
        L = app["loan"]
        if L > 250_000:
            return "Credit committee", HEAD
        if L > 100_000:
            return "Senior credit manager", SENIOR
        self.cm_cycle += 1
        return "Credit manager", (CM1, CM2)[self.cm_cycle % 2]

    def decision_day(self, app, route, extra=0):
        rng = self.rng
        rec = app["received"]
        if app["decide_after"]:
            d = uk.add_working_days(rec, app["decide_after"])
            return next_tuesday(d) if route == "Credit committee" else d
        if route == "Automated scorecard":
            return rec
        if route == "Credit committee":
            return next_tuesday(uk.add_working_days(rec, rng.randint(5, 9) + extra))
        return uk.add_working_days(rec, rng.randint(3, 8) + extra)

    def decide(self, app):
        """Sets the status from the policy and the plan's fate."""
        rng = self.rng
        a = app
        a.update(status=None, route=None, by=None, date=None, referral=None, exception=None, conditions=None, reason=None)
        online = a["channel"] == "Online"
        if a["fate"] == "withdrawn":
            a.update(status="Withdrawn", date=uk.add_working_days(a["received"], rng.randint(4, 15)),
                     reason=f"Customer withdrew the application: {rng.choice(WITHDRAWN)}.")
            return
        if a["fate"] == "in_assessment":
            a.update(status="In assessment", reason="Received; the credit analysis is in progress.")
            return
        when = uk.add_working_days(a["received"], a["decide_after"]) if a["decide_after"] else None
        info, dec, ref = self.assess(a, when)
        if info:
            a.update(status="Awaiting information", reason="Awaiting information: " + "; ".join(info) + ".")
            return
        scorecard = online and a["security"] is None and a["loan"] <= SCORECARD_LIMIT
        if dec:
            route, by = ("Automated scorecard", None) if scorecard else self.route(a)
            a.update(status="Declined", route=route, by=by, reason="Declined: " + "; ".join(dec) + ".")
            a["date"] = self.decision_day(a, route)
            return
        if ref:
            route, by = self.route(a)
            a["referral"] = "; ".join(ref) + "."
            if a["fate"] == "refer_pending":
                a.update(status="Refer", reason=f"Referred to the {route.lower()}; waiting for a credit decision.")
                return
            a.update(route=route, by=by, date=self.decision_day(a, route, extra=3))
            if a["fate"] == "refer_approve":
                a.update(status="Approved", reason="Approved after referral: " + a["notes_judgement"])
                a["conditions"] = self.conditions(a)
            else:
                a.update(status="Declined", reason="Declined after referral: " + a["notes_judgement"])
            return
        route, by = ("Automated scorecard", None) if scorecard else self.route(a)
        a.update(status="Approved", route=route, by=by, date=self.decision_day(a, route), conditions=self.conditions(a))
        test = f"LTV {a['ltv']:.1f}%" if a["ltv"] is not None else f"loan {a['ltt']:.1f}% of turnover"
        a["reason"] = f"All policy tests passed: DSCR {a['dscr']:.2f}; {test}; grade {a['grade']}."

    @staticmethod
    def conditions(a):
        parts = []
        for c in a["collateral"]:
            if c["security_type"] == "Commercial property":
                parts.append("first legal charge over the property, with buildings insurance noting the bank's interest")
            elif c["security_type"] in ("Equipment", "Commercial vehicles"):
                parts.append("the bank's charge over the assets bought, on delivery")
            elif c["security_type"] == "Debenture":
                parts.append("debenture")
            elif c["security_type"] == "Personal guarantee":
                parts.append(c["description"][0].lower() + c["description"][1:])
        if a["loan"] > 100_000:
            parts.append("annual accounts within nine months of each year end")
        return ("Conditions: " + "; ".join(parts) + ".") if parts else "Conditions: none beyond the standard loan terms."

    # ---- normal applications

    def received_day(self, lo=Q_START, hi=D(2026, 9, 18)):
        rng = self.rng
        while True:
            d = lo + dt.timedelta(days=rng.randint(0, (hi - lo).days))
            if uk.is_working_day(d):
                return d

    def normal(self):
        rng = self.rng
        sectors = list(SECTORS)
        weights = [SECTORS[s]["w"] for s in sectors]
        pick = lambda: rng.choices(sectors, weights)[0]  # noqa: E731
        plans = []
        plans += [dict(expect="approve", channel="Online", amount=(10_000, 50_000), dscr=(1.5, 3.2), T_range=(150_000, 900_000))] * 17
        plans += [dict(expect="decline", channel="Online", amount=(10_000, 50_000), dscr=(0.75, 1.2), T_range=(150_000, 900_000))] * 4
        plans += [dict(expect="decline", channel="Online", amount=(20_000, 50_000), dscr=(1.45, 3.0), turnover_test="fail",
                       T_range=(110_000, 170_000), loans=[])] * 2
        plans += [dict(expect="approve", amount=(52_500, 100_000), dscr=(1.45, 2.6))] * 12
        plans += [dict(expect="approve", amount=(52_500, 100_000), dscr=(1.45, 2.4), security="equipment", ltv=(0.6, 0.8))] * 4
        plans += [dict(expect="approve", amount=(105_000, 250_000), dscr=(1.45, 2.3))] * 4
        plans += [dict(expect="approve", amount=(105_000, 250_000), dscr=(1.45, 2.3), security="property", ltv=(0.45, 0.66))] * 3
        plans += [dict(expect="approve", amount=(105_000, 250_000), dscr=(1.45, 2.3), security="vehicles", ltv=(0.65, 0.8))] * 2
        plans += [dict(expect="approve", amount=(260_000, 950_000), dscr=(1.45, 2.2), product="Commercial mortgage", security="property",
                       ltv=(0.5, 0.68))] * 7
        plans += [dict(expect="refer_band", fate="refer_approve", amount=(55_000, 240_000), dscr=(1.27, 1.38))] * 4
        plans += [dict(expect="refer_band", fate="refer_decline", amount=(55_000, 240_000), dscr=(1.26, 1.33))] * 2
        plans += [dict(expect="refer", fate="refer_approve", amount=(55_000, 200_000), dscr=(1.5, 2.2), grade="D")] * 1
        plans += [dict(expect="refer", fate="refer_approve", amount=(55_000, 200_000), dscr=(1.6, 2.4), cr=(0.84, 0.96), cr_prior=0.95)] * 1
        plans += [dict(expect="refer", fate="refer_approve", amount=(55_000, 200_000), dscr=(1.6, 2.4), arrears=12)] * 1
        plans += [dict(expect="refer", fate="refer_pending", amount=(55_000, 200_000), dscr=(1.5, 2.2), grade="D", late=True)] * 1
        plans += [dict(expect="refer", fate="refer_pending", amount=(55_000, 200_000), dscr=(1.6, 2.4), cr=(0.84, 0.96), cr_prior=0.97, late=True)] * 1
        plans += [dict(expect="refer", fate="refer_pending", amount=(55_000, 200_000), dscr=(1.6, 2.4), arrears=21, late=True)] * 1
        plans += [dict(expect="decline", amount=(55_000, 240_000), dscr=(0.8, 1.2))] * 2
        plans += [dict(expect="decline", amount=(260_000, 700_000), dscr=(1.5, 2.1), product="Commercial mortgage", security="property",
                       ltv=(0.74, 0.8))] * 1
        plans += [dict(expect="decline", amount=(55_000, 150_000), dscr=(1.5, 2.2), arrears=48)] * 1
        plans += [dict(expect="decline", amount=(30_000, 80_000), dscr=(1.5, 2.4), trading_months=19, loans=[])] * 1
        plans += [dict(expect="awaiting", amount=(260_000, 900_000), dscr=(1.45, 2.2), product="Commercial mortgage", security="property",
                       valuation="instructed", late=True)] * 4
        plans += [dict(expect="awaiting", amount=(55_000, 150_000), dscr=(1.5, 2.3), stale_accounts=True, mgmt=True)] * 2
        plans += [dict(expect="in_assessment", fate="in_assessment", amount=(25_000, 300_000), dscr=(1.2, 2.4), very_late=True)] * 5
        plans += [dict(expect="withdrawn", fate="withdrawn", amount=(25_000, 300_000), dscr=(1.4, 2.4))] * 4
        holiday_left = 2
        judgement_approve = [
            "three years of steady trading and the directors' guarantee outweigh the thin cover.",
            "cover is thin, but the business has a signed two-year contract that adds to profit from next month.",
            "the owners have agreed to halve their drawings for the term of the loan.",
            "the business has repaid two earlier loans with the bank on time.",
            "the fall in the current ratio follows a one-off VAT payment, cleared in the management accounts.",
            "the arrears were a missed direct debit when the business changed banks, cleared within a fortnight.",
        ]
        judgement_decline = ["cover depends on a contract that is not yet signed.", "profit has fallen in each of the last two years.",
                             "the business has no other security and the owners have no capital in it."]
        for p in plans:
            p = dict(p)
            late = p.pop("late", False)
            very_late = p.pop("very_late", False)
            if very_late:
                rec = self.received_day(D(2026, 9, 22), Q_END)
            elif late:
                rec = self.received_day(D(2026, 9, 1), D(2026, 9, 25))
            else:
                rec = self.received_day()
            sector = pick()
            if p.get("product") == "Commercial mortgage" and sector == "Technology":
                sector = "Professional services"
            if p.get("security") == "vehicles":
                sector = rng.choice(["Logistics", "Construction trades", "Wholesale"])
            hol = holiday_left > 0 and p["expect"] == "approve" and p.get("channel") is None
            app = self.make(sector, received=rec, holiday=hol, **p)
            if hol and any(x["repayment_status"].startswith("Payment holiday") for x in app["loans"]):
                holiday_left -= 1
            if app["channel"] is None:
                app["channel"] = "Relationship manager"
            if p.get("fate") == "refer_approve":
                app["notes_judgement"] = judgement_approve[(len(self.apps)) % len(judgement_approve)]
                if p.get("arrears"):
                    app["notes_judgement"] = judgement_approve[5]
                elif p.get("cr"):
                    app["notes_judgement"] = judgement_approve[4]
            elif p.get("fate") == "refer_decline":
                app["notes_judgement"] = judgement_decline[len(self.apps) % len(judgement_decline)]
            self.decide(app)
            want = {"approve": "Approved", "decline": "Declined", "awaiting": "Awaiting information", "in_assessment": "In assessment",
                    "withdrawn": "Withdrawn"}.get(p["expect"])
            if p["expect"] in ("refer", "refer_band"):
                want = {"refer_approve": "Approved", "refer_decline": "Declined", "refer_pending": "Refer"}[p["fate"]]
            if app["status"] != want:
                raise RuntimeError(f"plan {p} gave {app['status']}: {self.assess(app)}")

    # ---- planted cases

    def planted(self):
        K = self.K
        # CASE: passes the turnover test, fails the cash-flow test, approved.
        a = self.make("Wholesale", received=D(2026, 7, 14), expect="decline", amount=(120_000, 200_000), dscr=(1.08, 1.14),
                      T_range=(2_800_000, 4_200_000), margin=(0.022, 0.028), key="cashflow", purpose="Stock for a new supply contract", grade="C",
                      sic=SECTORS["Wholesale"]["sics"][0], desc="Food wholesaler supplying restaurants", loans=["tsb", "hp"])
        a["channel"] = "Relationship manager"
        self.force(a, "Approved", "Senior credit manager", SENIOR, 6,
                   f"Turnover test passed: the loan is {a['ltt']:.1f}% of turnover, well inside 25%. Approved on the strength of sales growth "
                   f"and the new supply contract.")
        a["notes"] = (f"Turnover of {gbp0(a['turnover'])} and growing. The new contract with a restaurant group adds about £600,000 of sales "
                      "a year. Margins are thin, as usual for food wholesale.")

        # Lookalike: DSCR below the minimum, approved by the Credit Committee as a recorded policy exception.
        a = self.make("Healthcare", received=D(2026, 7, 22), expect="decline", product="Commercial mortgage", security="property",
                      amount=(380_000, 480_000), dscr=(1.15, 1.21), ltv=(0.6, 0.66), key="exception", grade="C",
                      sic=SECTORS["Healthcare"]["sics"][0], desc="Private dental practice, four surgeries", form="Private limited company",
                      purpose="Purchase of the freehold of the practice premises from the landlord")
        a["channel"] = "Relationship manager"
        rent = round(a["proposed"] * 0.62, -3)
        after = half_up((a["cf"] + rent) / (a["existing"] + a["proposed"]), 2)
        self.force(a, "Approved", "Credit committee", HEAD, 7,
                   f"Approved as a policy exception (LP-21): DSCR {a['dscr']:.2f} is below 1.25.")
        a["exception"] = (f"DSCR {a['dscr']:.2f} is below the 1.25 minimum (LP-06). The loan buys the premises the practice now rents. Rent "
                          f"of {gbp0(rent)} a year, paid out of operating profit, stops on completion. With the rent added back the DSCR "
                          f"would be {after:.2f}. Agreed by the Credit Committee on that basis.")
        a["notes"] = (f"The practice has rented the building since it opened. The landlord is selling. Rent is {gbp0(rent)} a year and "
                      "stops once the practice owns the premises.")

        # CASE: DSCR in the summary divides by the proposed debt service only.
        a = self.make("Professional services", received=D(2026, 8, 3), expect="decline", amount=(75_000, 100_000), dscr=(1.08, 1.18),
                      key="dscr_wrong", form="Private limited company", sic=SECTORS["Professional services"]["sics"][2],
                      desc="Architecture practice, residential and schools", loans=["tsb", "bbl", "hp"],
                      purpose="Working capital for a new contract")
        a["channel"] = "Relationship manager"
        a["dscr"] = half_up(a["cf"] / a["proposed"], 2)
        a["grade"] = "B"
        self.force(a, "Approved", "Credit manager", CM1, 4,
                   f"All policy tests passed: DSCR {a['dscr']:.2f}; loan {a['ltt']:.1f}% of turnover; grade B.")
        a["notes"] = "Strong cover on the new loan. The practice has won a schools framework contract."

        # Lookalike: existing debt service lower than the loans on file, because this loan repays one of them.
        a = self.make("Hospitality", received=D(2026, 8, 11), expect="approve", amount=(150_000, 240_000), dscr=(1.55, 1.9),
                      refinance=True, key="refinance", loans=["tsb", "hp"], form="Private limited company",
                      sic=SECTORS["Hospitality"]["sics"][0], desc="Coffee shop with two sites",
                      purpose="Fit-out of a third site, and repayment of the existing Thameside term loan")
        a["channel"] = "Relationship manager"
        self.decide_normal(a)
        refi = a["refi"][0]
        a["notes"] = (f"The new loan includes {gbp0(refi['outstanding_balance_gbp'])} to repay the existing Thameside term loan, so that "
                      "loan is left out of existing debt service.")

        # CASE: property valuation 26 months old at the decision.
        a = self.make("Manufacturing", received=D(2026, 7, 20), expect="decline", amount=(300_000, 420_000), dscr=(1.6, 1.9),
                      security="property", ltv=(0.56, 0.62), valuation=D(2024, 6, 12), key="stale_val", grade="B", form="Private limited company",
                      sic=SECTORS["Manufacturing"]["sics"][1], desc="Precision engineering workshop", purpose="New production machinery",
                      decide_after=10, term=8)
        a["channel"] = "Relationship manager"
        self.force(a, "Approved", "Credit committee", HEAD, None,
                   f"All policy tests passed: DSCR {a['dscr']:.2f}; LTV {a['ltv']:.1f}%; grade {a['grade']}.")
        a["notes"] = ("Valuation from the purchase of the unit in June 2024 used, to save the customer a new valuation fee. The unit is "
                      "well kept.")

        # Lookalike: valuation under 12 months old at the decision, over 12 months old at the extract.
        a = self.make("Wholesale", received=D(2026, 9, 1), expect="approve", product="Commercial mortgage", security="property",
                      amount=(400_000, 650_000), dscr=(1.5, 1.9), ltv=(0.55, 0.65), valuation=D(2025, 10, 6), key="near_val",
                      decide_after=17, sic=SECTORS["Wholesale"]["sics"][1], desc="Wholesaler of kitchenware and homeware",
                      purpose="Purchase of the freehold of the warehouse the business rents")
        a["channel"] = "Relationship manager"
        self.decide_normal(a)
        a["notes"] = ("The landlord's RICS valuation of October 2025 was assigned to the bank by the panel valuer who prepared it. It is "
                      "under 12 months old.")

        # CASE: improving profit, worsening liquidity; every test passed, approved without comment.
        a = self.make("Technology", received=D(2026, 8, 18), expect="approve", amount=(80_000, 100_000), dscr=(1.55, 1.75),
                      profit_growth=0.38, cr=(1.02, 1.06), cr_prior=1.74, dd_prior=41, dd_latest=88, key="liquidity",
                      form="Private limited company", sic=SECTORS["Technology"]["sics"][1], desc="IT consultancy for schools and charities",
                      purpose="Hiring developers for a new product", loans=["bbl", "hp"])
        a["channel"] = "Relationship manager"
        a["grade"] = "B"
        self.decide_normal(a)
        a["notes"] = "Operating profit up by more than a third on the new public-sector framework. All tests passed."

        # Lookalike: profit up, current ratio down, because the business bought its freehold with cash.
        a = self.make("Healthcare", received=D(2026, 7, 28), expect="approve", product="Commercial mortgage", security="property",
                      amount=(260_000, 400_000), dscr=(1.7, 2.1), ltv=(0.5, 0.6), profit_growth=0.11, cr=(1.55, 1.65), cr_prior=2.9,
                      fa_jump=True, key="freehold", sic=SECTORS["Healthcare"]["sics"][1], desc="Small-animal veterinary practice",
                      form="Private limited company", purpose="Mortgage on the practice's freehold, bought with cash in 2025, to restore working capital")
        a["channel"] = "Relationship manager"
        self.decide_normal(a)
        a["notes"] = ("The practice bought its freehold for cash last year, so cash fell and fixed assets rose. This mortgage on the freehold "
                      "puts working capital back.")

        # CASE: borderline online application declined by the scorecard instead of being referred.
        a = self.make("Hospitality", received=D(2026, 8, 25), expect="refer_band", channel="Online", amount=(35_000, 50_000),
                      dscr=(1.30, 1.34), T_range=(300_000, 700_000), key="auto_decline", form="Private limited company",
                      sic=SECTORS["Hospitality"]["sics"][0], desc="Independent café and bakery", purpose="New coffee and bakery equipment",
                      grade="C")
        self.force(a, "Declined", "Automated scorecard", None, 0, f"Declined by the scorecard: DSCR {a['dscr']:.2f} is below 1.40.")
        a["notes"] = "Online application. Figures taken from the accounts the customer uploaded."

        # Lookalike: borderline application correctly referred, waiting for a credit officer.
        a = self.make("Professional services", received=D(2026, 9, 21), expect="refer_band", fate="refer_pending",
                      amount=(105_000, 150_000), dscr=(1.33, 1.38), key="referred", form="Limited liability partnership",
                      sic=SECTORS["Professional services"]["sics"][3], desc="Operations consultancy for housing associations",
                      purpose="Acquisition of a retiring partner's share", grade="C")
        a["channel"] = "Relationship manager"
        self.decide(a)
        a["notes"] = ("A five-year contract with a housing association starts in January 2027 and is not in these figures. One of the two "
                      "founding partners retires next year; this loan buys out that partner's share.")

        # CASE: latest full-year accounts out of date; the summary used management accounts; approved.
        a = self.make("Hospitality", received=D(2026, 8, 6), expect="awaiting", amount=(60_000, 95_000), dscr=(1.3, 1.36),
                      stale_accounts=True, mgmt=True, key="mgmt", form="Private limited company",
                      sic=SECTORS["Hospitality"]["sics"][1], desc="Turkish grill restaurant", purpose="Refurbishment of the existing site")
        a["channel"] = "Relationship manager"
        a["used"] = a["fins"][-1]
        self.summary(a)
        a["grade"] = "B"
        self.force(a, "Approved", "Credit manager", CM2, 5,
                   f"All policy tests passed: DSCR {a['dscr']:.2f}; loan {a['ltt']:.1f}% of turnover; grade B.")
        a["notes"] = ("The accountant is still preparing the accounts for last year, so the summary uses the management accounts for the "
                      "last twelve months, which show recent trading.")

        # CASE: an existing loan 47 days in arrears, missed in the summary; approved.
        a = self.make("Logistics", received=D(2026, 7, 9), expect="decline", security="vehicles", amount=(60_000, 100_000),
                      dscr=(1.6, 2.0), ltv=(0.7, 0.8), arrears=47, key="arrears", loans=["hp", "tsb"], form="Private limited company",
                      sic=SECTORS["Logistics"]["sics"][0], desc="Same-day courier and pallet delivery", purpose="Commercial vehicles")
        a["channel"] = "Relationship manager"
        a["grade"] = "C"
        self.force(a, "Approved", "Credit manager", CM2, 4,
                   f"All policy tests passed: DSCR {a['dscr']:.2f}; LTV {a['ltv']:.1f}%; grade C.")
        a["notes"] = "No arrears on existing borrowing. Busy year; three more vans needed for a new contract with a food producer."

    def force(self, a, status, route, by, days, reason):
        """Records a decision that the planted case needs, whatever the policy says."""
        a.update(status=status, route=route, by=by, referral=None, exception=None, reason=reason)
        a["date"] = self.decision_day(a, route) if days is None else (
            next_tuesday(uk.add_working_days(a["received"], days)) if route == "Credit committee" else uk.add_working_days(a["received"], days))
        a["conditions"] = self.conditions(a) if status == "Approved" else None

    def decide_normal(self, a):
        self.decide(a)
        if a["status"] != "Approved":
            raise RuntimeError(f"{a['key']}: expected Approved, got {a['status']}: {self.assess(a)}")

    # ---- numbering and rows

    def finalise(self):
        rng = self.rng
        apps = sorted(self.apps, key=lambda a: (a["received"], a["business"]["customer_since"]))
        for i, a in enumerate(apps, start=1):
            a["application_id"] = f"APP-{i:04d}"
        by_cust = sorted(apps, key=lambda a: (a["business"]["customer_since"], a["received"]))
        for i, a in enumerate(by_cust, start=1):
            a["business"]["business_id"] = f"SME-{i:04d}"
        rm_by_region = {"London": ["STF-05", "STF-07", "STF-08"], "South East": ["STF-06", "STF-07"], "East of England": ["STF-05", "STF-06"]}
        for a in by_cust:
            b = a["business"]
            if a["channel"] == "Online" and a["loan"] <= SCORECARD_LIMIT and b["rm"] == "auto":
                b["rm"] = None
            elif b["rm"] == "auto":
                self.rm_cycle += 1
                opts = rm_by_region[b["registered_region"]]
                b["rm"] = opts[self.rm_cycle % len(opts)]
            ye_m, ye_d = b["year_end"]
            self.rows["businesses"].append({
                "business_id": b["business_id"], "legal_form": b["legal_form"], "sector": b["sector"], "sic_code": b["sic_code"],
                "sic_description": b["sic_description"], "business_description": b["business_description"],
                "registered_region": b["registered_region"], "postcode_district": b["postcode_district"],
                "trading_since": iso(b["trading_since"]), "incorporated_date": iso(b["incorporated_date"]), "employees": b["employees"],
                "year_end": D(2026, ye_m, ye_d).strftime("%-d %B"), "customer_since": iso(b["customer_since"]), "relationship_manager_id": b["rm"]})
        fins = sorted((f for a in apps for f in a["fins"]), key=lambda f: (f["business"]["business_id"], f["period_end"], f["accounts_type"]))
        for i, f in enumerate(fins, start=1):
            f["financial_id"] = f"FIN-{i:04d}"
        fcols = [c.name for c in SCHEMA[4].columns]
        self.rows["financials"] = [{**{k: f[k] for k in fcols if k in f}, "financial_id": f["financial_id"],
                                    "business_id": f["business"]["business_id"], "period_start": iso(f["period_start"]),
                                    "period_end": iso(f["period_end"])} for f in fins]
        for a in apps:
            b = a["business"]
            self.rows["loan_applications"].append({
                "application_id": a["application_id"], "business_id": b["business_id"], "received_date": iso(a["received"]),
                "channel": a["channel"], "sector": b["sector"], "product": a["product"], "loan_purpose": a["purpose"],
                "loan_requested_gbp": a["loan"], "term_years": a["term"], "interest_rate_pct": a["rate"],
                "accounts_used_id": a["used"]["financial_id"], "annual_turnover_gbp": a["turnover"], "operating_profit_gbp": a["op"],
                "cash_flow_available_gbp": r2(a["cf"]), "existing_debt_service_gbp": a["existing"], "proposed_debt_service_gbp": a["proposed"],
                "dscr": a["dscr"], "loan_to_turnover_pct": a["ltt"], "ltv_pct": a["ltv"], "credit_grade": a["grade"],
                "summary_notes": a["notes"] or self.default_notes(a), "decision_status": a["status"], "referral_reasons": a["referral"],
                "decision_route": a["route"], "decided_by": a["by"], "decision_date": iso(a["date"]), "status_reason": a["reason"],
                "policy_exception": a["exception"], "conditions": a["conditions"]})
        loans = sorted((x for a in apps for x in a["loans"]), key=lambda x: (x["business"]["business_id"], x["start_date"], x["lender"]))
        for i, x in enumerate(loans, start=1):
            x["loan_id"] = f"EXL-{i:04d}"
            self.rows["existing_loans"].append({
                "loan_id": x["loan_id"], "business_id": x["business"]["business_id"], "lender": x["lender"], "facility_type": x["facility_type"],
                "original_amount_gbp": x["original_amount_gbp"], "start_date": iso(x["start_date"]), "maturity_date": iso(x["maturity_date"]),
                "interest_rate_pct": x["interest_rate_pct"], "monthly_repayment_gbp": x["monthly_repayment_gbp"],
                "annual_repayment_gbp": x["annual_repayment_gbp"], "outstanding_balance_gbp": x["outstanding_balance_gbp"],
                "loan_status": x["loan_status"], "repayment_status": x["repayment_status"], "arrears_days": x["arrears_days"],
                "arrears_gbp": x["arrears_gbp"], "refinanced_by_application_id": x["refinanced_by"]["application_id"] if x["refinanced_by"] else None,
                "source": x["source"]})
        n = 0
        for a in apps:
            for c in a["collateral"]:
                n += 1
                c["collateral_id"] = f"COL-{n:04d}"
                self.rows["collateral"].append({
                    "collateral_id": c["collateral_id"], "application_id": a["application_id"], "security_type": c["security_type"],
                    "description": c["description"], "valuation_status": c["valuation_status"], "valuation_basis": c["valuation_basis"],
                    "valuation_date": iso(c["valuation_date"]), "market_value_gbp": c["market_value_gbp"],
                    "forced_sale_discount_pct": c["forced_sale_discount_pct"], "recoverable_value_gbp": c["recoverable_value_gbp"]})
        self.sorted_apps = apps

    def default_notes(self, a):
        if a["channel"] == "Online":
            return "Online application. Figures taken from the accounts the customer uploaded."
        b = a["business"]
        yrs = a["months_trading"] // 12
        lines = [f"{b['business_description']}, trading for {yrs} years." if yrs >= 2 else f"{b['business_description']}, trading for {a['months_trading']} months."]
        if any(x["repayment_status"].startswith("Payment holiday") for x in a["loans"]):
            lines.append("The Bounce Back Loan is on a Pay As You Grow payment holiday; it is counted at its full repayment.")
        if any(x["loan_status"] == "Repaid" for x in a["loans"]):
            lines.append("Earlier borrowing repaid on time.")
        if a["product"] == "Commercial mortgage":
            lines.append("The business will own the premises it trades from.")
        return " ".join(lines)


# ------------------------------------------------------------------ cases


def record_cases(b):
    K = b.K
    rows = b.rows
    aid = lambda k: K[k]["application_id"]  # noqa: E731
    app = lambda k: next(r for r in rows["loan_applications"] if r["application_id"] == aid(k))  # noqa: E731
    fin_id = lambda f: f["financial_id"]  # noqa: E731
    long = lambda d: d.strftime("%-d %B %Y")  # noqa: E731

    def true_dscr(a):
        f = a["latest"]
        live = [x for x in a["loans"] if x["loan_status"] == "Live" and x["refinanced_by"] is not a]
        cf = Builder.cfads(f)
        E = r2(sum(x["annual_repayment_gbp"] for x in live))
        return cf, E, half_up(cf / (E + a["proposed"]), 2)

    LATEST = """WITH fy AS (SELECT a.application_id, f.*, row_number() OVER (PARTITION BY a.application_id ORDER BY f.period_end DESC) AS n
                FROM loan_applications a JOIN financials f ON f.business_id = a.business_id
                AND f.accounts_type <> 'Management accounts' AND f.period_end <= a.received_date)"""

    a, r = K["cashflow"], app("cashflow")
    b.case("CASE-01", "Passes the turnover test but fails the cash-flow test, and was approved", "rule_dscr_below_minimum_approved",
           "Genuine exception", "High", "LP-06, LP-08, LP-02 to LP-05", "A3, S1",
           f"Application {r['application_id']} is for an unsecured term loan of {gbp0(a['loan'])} to a food wholesaler with turnover of "
           f"{gbp0(a['turnover'])}. The loan is {a['ltt']:.1f}% of turnover, well inside the 25% turnover test (LP-08). But the wholesaler's "
           f"margin is thin: cash flow available for debt service is {gbp(a['cf'])} against existing debt service of {gbp(a['existing'])} and "
           f"proposed debt service of {gbp(a['proposed'])}, a DSCR of {a['dscr']:.2f}. The summary shows that figure correctly. LP-06 requires "
           f"at least 1.25 and its outcome is Decline. The Senior Credit Manager approved it on {long(a['date'])}, citing the turnover test, "
           "with no policy exception. Only the Credit Committee may approve an exception (LP-21).",
           "Do not draw the loan. Send it to the Credit Committee as a possible exception with the reasons, or decline it. Remind credit "
           "officers that the turnover test does not replace the cash-flow test.",
           """SELECT application_id FROM loan_applications WHERE decision_status = 'Approved' AND dscr < 1.25
              AND policy_exception IS NULL AND loan_to_turnover_pct <= 25""",
           [("loan_applications", r["application_id"], "approved below the minimum DSCR", 1),
            ("financials", fin_id(a["used"]), "accounts showing the thin margin", 0)])

    a, r = K["exception"], app("exception")
    b.case("CASE-02", "DSCR below the minimum, approved by the Credit Committee as a recorded exception", "rule_policy_exception_lookalike",
           "Benign lookalike", "None", "LP-06, LP-21", "A3, A8",
           f"Application {r['application_id']} has a DSCR of {a['dscr']:.2f}, below the 1.25 minimum. It was approved by the Credit Committee "
           f"on {long(a['date'])} as a policy exception, recorded in policy_exception: the loan buys the premises the dental practice rents, so "
           "the rent stops on completion. LP-21 allows exactly this. The LTV is "
           f"{a['ltv']:.1f}%, inside 70%.",
           "No action.",
           """SELECT application_id FROM loan_applications WHERE decision_status = 'Approved' AND dscr < 1.25 AND policy_exception IS NOT NULL""",
           [("loan_applications", r["application_id"], "approved as a recorded exception", 1)])

    a, r = K["dscr_wrong"], app("dscr_wrong")
    cf, E, d = true_dscr(a)
    b.case("CASE-03", "DSCR in the application summary leaves out existing debt service", "calculation_dscr_misstated",
           "Genuine exception", "High", "LP-05, LP-03, LP-06", "S1, A1, A3",
           f"The summary for application {r['application_id']} shows a DSCR of {a['dscr']:.2f}. That is cash flow available of {gbp(cf)} divided "
           f"by the proposed debt service of {gbp(a['proposed'])} alone. LP-05 divides by existing plus proposed debt service. The summary's own "
           f"existing debt service is {gbp(E)}, for the practice's live loans in existing_loans, so the DSCR is {gbp(cf)} / "
           f"({gbp(E)} + {gbp(a['proposed'])}) = {d:.2f}. That is below the 1.25 minimum (LP-06), so the application should have been "
           f"declined. The Credit Manager approved it on {long(a['date'])} on the wrong figure.",
           "Stop the drawdown. Correct the summary, and decline the application or send it to the Credit Committee as an exception. Check "
           "the relationship manager's other summaries.",
           """SELECT application_id FROM loan_applications
              WHERE abs(dscr - round(cash_flow_available_gbp / (existing_debt_service_gbp + proposed_debt_service_gbp), 2)) > 0.005""",
           [("loan_applications", r["application_id"], "DSCR misstated", 1)]
           + [("existing_loans", x["loan_id"], "live loan left out of the DSCR", 0) for x in a["loans"] if x["loan_status"] == "Live"])

    a, r = K["refinance"], app("refinance")
    refi = a["refi"][0]
    all_live = r2(sum(x["annual_repayment_gbp"] for x in a["loans"] if x["loan_status"] == "Live"))
    b.case("CASE-04", "Existing debt service lower than the loans on file, because the new loan repays one of them", "calculation_refinance_lookalike",
           "Benign lookalike", "None", "LP-03", "S1, A3, A1",
           f"The live loans of business {r['business_id']} add up to {gbp(all_live)} a year of repayments, but the summary for application "
           f"{r['application_id']} shows existing debt service of {gbp(a['existing'])}. The difference is loan {refi['loan_id']}, "
           f"{gbp(refi['annual_repayment_gbp'])} a year, which this application repays (refinanced_by_application_id). LP-03 leaves such a "
           f"loan out. The DSCR of {a['dscr']:.2f} is right.",
           "No action.",
           """SELECT a.application_id FROM loan_applications a WHERE a.existing_debt_service_gbp + 0.005 <
              (SELECT coalesce(sum(l.annual_repayment_gbp), 0) FROM existing_loans l WHERE l.business_id = a.business_id AND l.loan_status = 'Live')""",
           [("loan_applications", r["application_id"], "existing debt service correctly excludes the refinanced loan", 1),
            ("existing_loans", refi["loan_id"], "loan being refinanced", 0)])

    a, r = K["stale_val"], app("stale_val")
    c = next(c for c in a["collateral"] if c["security_type"] == "Commercial property")
    age = months_between(c["valuation_date"], a["date"])
    b.case("CASE-05", "Loan approved on a property valuation over two years old", "rule_stale_valuation",
           "Genuine exception", "Medium", "LP-19, LP-15, LP-16", "A3, A7, S2",
           f"Application {r['application_id']} is secured on a light industrial unit. The only valuation, {c['collateral_id']}, is dated "
           f"{long(c['valuation_date'])}: {age} months before the Credit Committee approved the loan on {long(a['date'])}. LP-19 allows 12 "
           f"months and says no decision may be made on an older valuation. The LTV of {a['ltv']:.1f}% uses the 2024 value of "
           f"{gbp0(c['market_value_gbp'])}; the property's value today is not known from the data, so the LTV test cannot be confirmed.",
           "Do not draw the loan. Instruct a new RICS valuation, recalculate the LTV, and confirm the approval only if it is within 70%.",
           """SELECT c.collateral_id FROM collateral c JOIN loan_applications a ON a.application_id = c.application_id
              WHERE c.security_type = 'Commercial property' AND c.valuation_status = 'Valued' AND a.decision_date IS NOT NULL
              AND c.valuation_date < date(a.decision_date, '-12 months')""",
           [("collateral", c["collateral_id"], "valuation out of date at the decision", 1),
            ("loan_applications", r["application_id"], "approved on the old valuation", 0)])

    a, r = K["near_val"], app("near_val")
    c = next(c for c in a["collateral"] if c["security_type"] == "Commercial property")
    b.case("CASE-06", "Valuation over 12 months old at the extract, but under 12 months old when the loan was decided", "rule_valuation_age_lookalike",
           "Benign lookalike", "None", "LP-19", "A7, A3",
           f"Valuation {c['collateral_id']} for application {r['application_id']} is dated {long(c['valuation_date'])}. That is more than 12 "
           f"months before the extract on {long(EXTRACT_DATE)}, but the loan was decided on {long(a['date'])}, less than 12 months after the "
           "valuation. LP-19 measures the age at the decision date, so the valuation was in date.",
           "No action. A new valuation is needed only if the decision is revisited.",
           f"""SELECT c.collateral_id FROM collateral c JOIN loan_applications a ON a.application_id = c.application_id
              WHERE c.valuation_status = 'Valued' AND c.valuation_date < date('{iso(EXTRACT_DATE)}', '-12 months')
              AND c.valuation_date >= date(a.decision_date, '-12 months')""",
           [("collateral", c["collateral_id"], "valuation in date at the decision", 1),
            ("loan_applications", r["application_id"], "decided within 12 months of the valuation", 0)])

    def liq(f):
        return (f["current_assets_gbp"] / f["current_liabilities_gbp"], (f["current_assets_gbp"] - f["stock_gbp"]) / f["current_liabilities_gbp"],
                f["trade_debtors_gbp"] / f["turnover_gbp"] * 365)

    a, r = K["liquidity"], app("liquidity")
    p, l = a["fins"][0], a["fins"][1]
    (cr0, _, dd0), (cr1, q1, dd1) = liq(p), liq(l)
    b.case("CASE-07", "Profit rising, liquidity falling: approved without comment", "judgement_liquidity_deteriorating",
           "Genuine exception", "Medium", "LP-22, LP-13, LP-14", "A8, A12, S1",
           f"Application {r['application_id']} passes every test: DSCR {a['dscr']:.2f}, loan {a['ltt']:.1f}% of turnover, current ratio "
           f"{cr1:.2f}, just above the 1.00 referral level. But between the accounts {fin_id(p)} and {fin_id(l)}, operating profit rose from "
           f"{gbp0(p['operating_profit_gbp'])} to {gbp0(l['operating_profit_gbp'])} while the current ratio fell from {cr0:.2f} to {cr1:.2f}, "
           f"debtor days rose from {dd0:.0f} to {dd1:.0f}, cash fell from {gbp0(p['cash_at_bank_gbp'])} to {gbp0(l['cash_at_bank_gbp'])}, and "
           f"net cash from operations was {gbp0(l['net_cash_from_operations_gbp'])}. Profit is not turning into cash: customers are paying more "
           "slowly. No rule is broken, so this is a matter of judgement (LP-22). The approval records only that all tests passed.",
           "Refer to a credit officer before drawdown. Ask for an aged debtors list and recent management accounts, and consider a "
           "condition on debtor days or a smaller loan.",
           LATEST + """ SELECT l.application_id FROM fy l JOIN fy p ON p.application_id = l.application_id AND l.n = 1 AND p.n = 2
              WHERE l.operating_profit_gbp > p.operating_profit_gbp
              AND l.current_assets_gbp * 1.0 / l.current_liabilities_gbp < 0.7 * p.current_assets_gbp / p.current_liabilities_gbp
              AND l.trade_debtors_gbp * 365.0 / l.turnover_gbp > p.trade_debtors_gbp * 365.0 / p.turnover_gbp + 20""",
           [("loan_applications", r["application_id"], "approved without weighing the liquidity trend", 1),
            ("financials", fin_id(p), "earlier accounts", 0), ("financials", fin_id(l), "latest accounts", 0)])

    a, r = K["freehold"], app("freehold")
    p, l = a["fins"][0], a["fins"][1]
    (cr0, _, dd0), (cr1, q1, dd1) = liq(p), liq(l)
    b.case("CASE-08", "Profit rising, current ratio falling, because the business bought its premises with cash", "judgement_liquidity_lookalike",
           "Benign lookalike", "None", "LP-22, LP-13, LP-14", "A8, A12, S1",
           f"For application {r['application_id']}, operating profit rose from {gbp0(p['operating_profit_gbp'])} to "
           f"{gbp0(l['operating_profit_gbp'])} and the current ratio fell from {cr0:.2f} to {cr1:.2f}. Fixed assets rose from "
           f"{gbp0(p['fixed_assets_gbp'])} to {gbp0(l['fixed_assets_gbp'])}: the practice bought its freehold with cash. Debtor days are "
           f"steady ({dd0:.0f} and {dd1:.0f}), the current ratio is still {cr1:.2f}, and the loan is a mortgage on that freehold that puts "
           "the cash back. Nothing here needs action.",
           "No action.",
           LATEST + """ SELECT l.application_id FROM fy l JOIN fy p ON p.application_id = l.application_id AND l.n = 1 AND p.n = 2
              WHERE l.operating_profit_gbp > p.operating_profit_gbp
              AND l.current_assets_gbp * 1.0 / l.current_liabilities_gbp < 0.7 * p.current_assets_gbp / p.current_liabilities_gbp
              AND l.trade_debtors_gbp * 365.0 / l.turnover_gbp <= p.trade_debtors_gbp * 365.0 / p.turnover_gbp + 20""",
           [("loan_applications", r["application_id"], "liquidity fall explained", 1),
            ("financials", fin_id(p), "earlier accounts", 0), ("financials", fin_id(l), "latest accounts, after the purchase", 0)])

    a, r = K["auto_decline"], app("auto_decline")
    b.case("CASE-09", "Borderline application declined by the scorecard instead of being referred to a person", "judgement_borderline_auto_declined",
           "Genuine exception", "Medium", "LP-07, R-02", "A3, A8, S1",
           f"Online application {r['application_id']} has a DSCR of {a['dscr']:.2f}, inside the referral band of 1.25 to 1.40. LP-07 says such "
           "an application is referred to a credit officer and may not be approved or declined automatically. The scorecard declined it "
           f"the day it was received, {long(a['date'])}, treating 1.40 as a pass mark. Every other test passes. Whether to lend is a "
           "judgement nobody has made.",
           "Reopen the application and refer it to a credit manager, who decides it. Check the scorecard's settings for the referral band, "
           "and look for other online applications it declined in the band.",
           """SELECT application_id FROM loan_applications WHERE decision_route = 'Automated scorecard' AND decision_status = 'Declined'
              AND dscr >= 1.25 AND dscr < 1.40""",
           [("loan_applications", r["application_id"], "declined automatically in the referral band", 1)])

    a, r = K["referred"], app("referred")
    b.case("CASE-10", "Borderline application referred and waiting for a credit officer", "judgement_borderline_referred_lookalike",
           "Benign lookalike", "None", "LP-07, LP-22", "A8, A3",
           f"Application {r['application_id']} has a DSCR of {a['dscr']:.2f}, in the referral band, and every other test passes. It was "
           "referred and is waiting for a decision, as LP-07 requires. The summary notes a contract not yet in the figures and a "
           "partner retiring: points for and against that a credit officer must weigh. No calculation settles it.",
           "No action on the process. The credit officer decides, weighing the new contract against the partner's retirement.",
           """SELECT application_id FROM loan_applications WHERE decision_status = 'Refer' AND dscr >= 1.25 AND dscr < 1.40""",
           [("loan_applications", r["application_id"], "correctly waiting for a person to decide", 1)])

    a, r = K["mgmt"], app("mgmt")
    fy, mg = a["latest"], a["used"]
    cf_fy, E, d_fy = true_dscr(a)
    b.case("CASE-11", "Full-year accounts out of date; the summary used management accounts, and the loan was approved", "rule_accounts_out_of_date",
           "Genuine exception", "Medium", "LP-01, LP-20", "A3, A1, A7, S2",
           f"The latest full-year accounts for application {r['application_id']}, {fin_id(fy)}, end on {long(fy['period_end'])}, more than 18 "
           f"months before the application on {long(a['received'])}. LP-20 says the application waits for newer accounts. Instead the summary "
           f"took its figures from management accounts {fin_id(mg)} (turnover {gbp0(mg['turnover_gbp'])}, against {gbp0(fy['turnover_gbp'])} in "
           f"the full-year accounts), which LP-01 says are never used in a test. On those management figures the DSCR is {a['dscr']:.2f}; on "
           f"the full-year accounts it would be {d_fy:.2f}. Neither figure can be relied on until the accounts arrive.",
           "Withdraw the approval and set the status to Awaiting information. Ask for the accounts for the year since, then redo the summary.",
           LATEST + """ SELECT application_id FROM fy JOIN loan_applications a USING (application_id)
              WHERE fy.n = 1 AND a.decision_status = 'Approved' AND fy.period_end < date(a.received_date, '-18 months')""",
           [("loan_applications", r["application_id"], "approved on out-of-date accounts", 1),
            ("financials", fin_id(fy), "full-year accounts over 18 months old", 0), ("financials", fin_id(mg), "management accounts used", 0)])

    a, r = K["arrears"], app("arrears")
    x = next(x for x in a["loans"] if x["arrears_days"])
    b.case("CASE-12", "Existing loan 47 days in arrears, missed in the summary, and the loan approved", "rule_arrears_missed",
           "Genuine exception", "High", "LP-11", "A1, A3",
           f"The credit reference agency report shows loan {x['loan_id']}, a {x['facility_type'].lower()} with {x['lender']}, "
           f"{x['arrears_days']} days in arrears at the application date, with {gbp(x['arrears_gbp'])} unpaid. LP-11 declines an application "
           f"when any live loan is more than 30 days in arrears. The summary for application {r['application_id']} says there are no arrears, "
           f"and the Credit Manager approved it on {long(a['date'])}.",
           "Do not draw the loan. Ask the business about the arrears, and decline unless the Credit Committee agrees an exception.",
           """SELECT a.application_id FROM loan_applications a WHERE a.decision_status = 'Approved' AND EXISTS
              (SELECT 1 FROM existing_loans l WHERE l.business_id = a.business_id AND l.loan_status = 'Live' AND l.arrears_days > 30)""",
           [("loan_applications", r["application_id"], "approved despite arrears", 1), ("existing_loans", x["loan_id"], "loan in arrears", 0)])


# ------------------------------------------------------------------ business story

NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
                11: "eleven", 12: "twelve"}
STORY_APPROVED = True  # approved by the user on 20 October 2026


def business_story(rows):
    """The firm's current situation. Paragraphs are separated by blank lines; lines starting '- ' are list items.
    Every figure is calculated from the rows, and checks() tests every claim against the data."""
    apps = rows["loan_applications"]
    loans = rows["existing_loans"]
    biz = {b["business_id"]: b for b in rows["businesses"]}
    status = defaultdict(int)
    for a in apps:
        status[a["decision_status"]] += 1
    online = sum(1 for a in apps if a["channel"] == "Online")
    bbl = len({x["business_id"] for x in loans if x["facility_type"] == "Bounce Back Loan" and x["loan_status"] == "Live"})
    hosp_wh = sum(1 for a in apps if a["sector"] in ("Hospitality", "Wholesale"))
    waiting = status["Refer"]
    requested = sum(a["loan_requested_gbp"] for a in apps)
    return "\n".join([
        "Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. Its business banking division lends to "
        "small and medium-sized businesses in London, the South East and the East of England: cafés and restaurants, professional "
        "firms, wholesalers, technology firms and trades. Relationship managers in the City, Canary Wharf and Croydon prepare "
        "applications, and the business banking credit team decides them.",
        "",
        "Several pressures have built up this year:",
        "- Growth target. The board wants business lending to grow, and relationship managers have targets for new lending. The "
        "same relationship managers prepare the application summaries that credit officers decide on.",
        f"- Faster decisions. Since {SCORECARD_LIVE.strftime('%-d %B %Y')} an automated scorecard has decided online applications "
        f"for unsecured loans of up to £50,000. {online} of the quarter's {len(apps)} applications came in online, and the scorecard "
        "decided all of them. Businesses that apply online have no relationship manager.",
        f"- A stretched credit team. Two credit managers, one senior credit manager and the Head of Business Banking Credit decide "
        f"every application the scorecard does not. At the extract, {NUMBER_WORDS.get(waiting, waiting)} referred applications were "
        "still waiting for a decision.",
        f"- Costs. Rises in employer National Insurance in April 2025 and the National Living Wage in April 2026 have squeezed "
        f"margins in hospitality and wholesale, which account for {hosp_wh} of the {len(apps)} applications.",
        f"- Old borrowing. Many businesses are still repaying loans taken during the pandemic. {bbl} of the applicants still have a "
        "Bounce Back Loan, some on Pay As You Grow terms.",
        "- Paperwork. Small companies have nine months after their year end to file accounts, so filed accounts are often a year old. "
        "Valuations are paid for by the customer.",
        "",
        f"The Head of Business Banking Credit asked for a review of every application received from 1 July to 30 September 2026. There "
        f"are {len(apps)}, for {gbp0(requested)} in all. At the extract on {EXTRACT_DATE.day} October:",
        f"- {status['Approved']} are approved and {status['Declined']} declined.",
        f"- {status['Refer']} are referred and waiting for a credit officer, {status['Awaiting information']} are waiting for "
        f"information, and {status['In assessment']} are still being assessed.",
        f"- {status['Withdrawn']} were withdrawn by the customer.",
    ])


def build(rng):
    b = Builder(rng)
    b.lookups()
    b.normal()
    b.planted()
    b.finalise()
    record_cases(b)
    rules = [{"rule_id": r, "category": c, "title": t, "statement": s, "related_tables": RULE_TABLES[r]} for r, c, t, s in RULES]
    facts = [
        ("dataset", "sme_lending"),
        ("title", "SME lending"),
        ("firm", firm.FIRM_NAME),
        ("lender", "Thameside Bank, the group's retail and commercial bank"),
        ("scenario", "The business banking credit team reviews the loan applications from small and medium-sized businesses received in the third quarter of 2026."),
        ("period", "Applications received 2026-07-01 to 2026-09-30"),
        ("extract_date", EXTRACT.strftime("%Y-%m-%d %H:%M")),
        ("currency", "GBP"),
        ("seed", firm.SEED),
        ("disclaimer", firm.DISCLAIMER + " Businesses and valuers are identified by reference only. The lending policy, accounts, "
                                         "credit grades and valuations are invented for the study."),
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
    genuine = {r[0] for r in q("""SELECT r.record_id FROM _truth_case_records r JOIN _truth_cases c USING (case_id)
                                  WHERE c.classification = 'Genuine exception' AND r.table_name = 'loan_applications'""")}
    genuine_apps = genuine | {r[0] for r in q("""SELECT c.application_id FROM _truth_case_records r JOIN _truth_cases t USING (case_id)
                                                 JOIN collateral c ON r.table_name = 'collateral' AND c.collateral_id = r.record_id
                                                 WHERE t.classification = 'Genuine exception'""")}

    # The business story's claims must hold in the data.
    claims = [
        (q("SELECT count(*) FROM loan_applications WHERE decision_route = 'Automated scorecard' AND (channel <> 'Online' OR loan_requested_gbp > 50000)")[0][0] == 0,
         "the scorecard decides only online applications up to £50,000"),
        (q("SELECT count(*) FROM loan_applications a JOIN businesses b USING (business_id) WHERE a.channel = 'Online' AND b.relationship_manager_id IS NOT NULL")[0][0] == 0,
         "businesses that apply online have no relationship manager"),
        (q("SELECT count(*) FROM loan_applications WHERE channel = 'Online' AND decision_route IS NOT 'Automated scorecard'")[0][0] == 0,
         "the scorecard decided every online application"),
        ([r[0] for r in q("SELECT job_title FROM staff WHERE lending_authority_gbp IS NOT NULL ORDER BY job_title")]
         == ["Credit Manager", "Credit Manager", "Head of Business Banking Credit", "Senior Credit Manager"],
         "two credit managers, one senior credit manager and the head of credit decide applications"),
        (q("SELECT count(*) FROM existing_loans WHERE repayment_status LIKE 'Payment holiday (Pay As You Grow)%'")[0][0] > 0,
         "some Bounce Back Loans are on Pay As You Grow terms"),
        (q("SELECT count(*) FROM loan_applications WHERE sector IN ('Hospitality', 'Wholesale')")[0][0] * 3
         > q("SELECT count(*) FROM loan_applications")[0][0], "hospitality and wholesale are a large share of applications"),
        (q("SELECT count(DISTINCT office) FROM staff WHERE job_title LIKE 'Relationship Manager%'")[0][0] == 3,
         "relationship managers work in the City, Canary Wharf and Croydon"),
    ]
    errors += [f"story: {text} is not true in the data" for ok, text in claims if not ok]

    ranges = {"loan_applications": (95, 105), "businesses": (95, 105), "financials": (180, 230), "existing_loans": (70, 200),
              "collateral": (90, 200)}
    for t, (lo, hi) in ranges.items():
        n = q(f"SELECT count(*) FROM {t}")[0][0]
        if not lo <= n <= hi:
            errors.append(f"{t}: {n} rows, expected {lo}-{hi}")

    apps = [dict(zip([c[0] for c in con.execute("SELECT * FROM loan_applications").description], r))
            for r in q("SELECT * FROM loan_applications")]
    fins = defaultdict(list)
    for r in q("SELECT * FROM financials ORDER BY period_end"):
        f = dict(zip([c[0] for c in con.execute("SELECT * FROM financials").description], r))
        fins[f["business_id"]].append(f)
    loans = defaultdict(list)
    lcols = [c[0] for c in con.execute("SELECT * FROM existing_loans").description]
    for r in q("SELECT * FROM existing_loans"):
        loans[r[1]].append(dict(zip(lcols, r)))
    coll = defaultdict(list)
    ccols = [c[0] for c in con.execute("SELECT * FROM collateral").description]
    for r in q("SELECT * FROM collateral"):
        coll[r[1]].append(dict(zip(ccols, r)))
    biz = {r[0]: r for r in q("SELECT business_id, trading_since, legal_form, incorporated_date, customer_since FROM businesses")}
    staff = {r[0]: (r[1], r[2]) for r in q("SELECT staff_id, job_title, lending_authority_gbp FROM staff")}

    for a in apps:
        aid, rec = a["application_id"], D.fromisoformat(a["received_date"])
        if not Q_START <= rec <= Q_END or not uk.is_working_day(rec):
            errors.append(f"{aid}: received outside the quarter or on a non-working day")
        full = [f for f in fins[a["business_id"]] if f["accounts_type"] != "Management accounts" and f["period_end"] <= a["received_date"]]
        if not full:
            errors.append(f"{aid}: no full-year accounts")
            continue
        fy = full[-1]
        used = next(f for f in fins[a["business_id"]] if f["financial_id"] == a["accounts_used_id"])
        live = [x for x in loans[a["business_id"]] if x["loan_status"] == "Live" and x["refinanced_by_application_id"] != aid]
        cf = used["operating_profit_gbp"] + used["depreciation_amortisation_gbp"] - used["tax_paid_gbp"] - used["dividends_drawings_gbp"]
        E = r2(sum(x["annual_repayment_gbp"] for x in live))
        P = r2(12 * monthly_repayment(a["loan_requested_gbp"], a["interest_rate_pct"], a["term_years"] * 12))
        ratio = cf / (E + P)
        if abs(ratio * 100 - math.floor(ratio * 100) - 0.5) < 1e-6:
            errors.append(f"{aid}: DSCR lies on a rounding boundary")
        expect = {"annual_turnover_gbp": used["turnover_gbp"], "operating_profit_gbp": used["operating_profit_gbp"],
                  "cash_flow_available_gbp": r2(cf), "existing_debt_service_gbp": E, "proposed_debt_service_gbp": P,
                  "dscr": half_up(ratio, 2), "loan_to_turnover_pct": half_up(a["loan_requested_gbp"] / used["turnover_gbp"] * 100, 1)}
        valued = [c for c in coll[aid] if c["valuation_status"] == "Valued"]
        expect["ltv_pct"] = half_up(a["loan_requested_gbp"] / sum(c["market_value_gbp"] for c in valued) * 100, 1) if valued else None
        for k, v in expect.items():
            if a[k] != v and not (aid in genuine and k == "dscr"):
                errors.append(f"{aid}: summary {k} is {a[k]}, definitions give {v}")
        if used is not fy and aid not in genuine:
            errors.append(f"{aid}: summary does not use the latest full-year accounts")
        # Decisions: route and authority (R-02), dates, and the fields each status needs.
        st, route, by = a["decision_status"], a["decision_route"], a["decided_by"]
        if st in ("Approved", "Declined"):
            if route is None or a["decision_date"] is None:
                errors.append(f"{aid}: decided without a route or date")
            elif route == "Automated scorecard":
                if by or a["channel"] != "Online" or a["loan_requested_gbp"] > SCORECARD_LIMIT or valued:
                    errors.append(f"{aid}: scorecard decided outside its limits")
            else:
                title, auth = staff[by]
                if auth is None or a["loan_requested_gbp"] > auth:
                    errors.append(f"{aid}: decided beyond authority")
                if (route == "Credit committee") != (by == HEAD) or (route == "Credit committee" and D.fromisoformat(a["decision_date"]).weekday() != 1):
                    errors.append(f"{aid}: Credit Committee decision not by its chair on a Tuesday")
            if st == "Approved" and a["policy_exception"] and route != "Credit committee":
                errors.append(f"{aid}: policy exception not agreed by the Credit Committee")
        elif route or by or (st != "Withdrawn" and a["decision_date"]):
            errors.append(f"{aid}: {st} with decision fields")
        if a["decision_date"] and not a["received_date"] <= a["decision_date"] <= iso(EXTRACT_DATE):
            errors.append(f"{aid}: decision date out of range")
        if a["decision_date"] and not uk.is_working_day(D.fromisoformat(a["decision_date"])):
            errors.append(f"{aid}: decision on a non-working day")
        if (st == "Refer") != (a["referral_reasons"] is not None and a["decision_date"] is None):
            errors.append(f"{aid}: Refer status and referral reasons disagree")
        if (st == "Approved") != (a["conditions"] is not None):
            errors.append(f"{aid}: conditions present only on approvals")
        # Accounts within reach of the application, trading history, numbering.
        b = biz[a["business_id"]]
        if fy["period_end"] < b[1] or b[4] > a["received_date"]:
            errors.append(f"{aid}: accounts before trading started, or customer after the application")
        if (b[2] in ("Private limited company", "Limited liability partnership")) != (b[3] is not None):
            errors.append(f"{a['business_id']}: incorporation date does not match legal form")

    # Accounts arithmetic.
    for bid, fs in fins.items():
        for f in fs:
            if f["current_assets_gbp"] != f["cash_at_bank_gbp"] + f["trade_debtors_gbp"] + f["stock_gbp"] + f["other_current_assets_gbp"]:
                errors.append(f"{f['financial_id']}: current assets do not add up")
            if f["current_liabilities_gbp"] != f["trade_creditors_gbp"] + f["bank_overdraft_gbp"] + f["other_current_liabilities_gbp"]:
                errors.append(f"{f['financial_id']}: current liabilities do not add up")
            if f["net_assets_gbp"] != f["fixed_assets_gbp"] + f["current_assets_gbp"] - f["current_liabilities_gbp"] - f["long_term_debt_gbp"]:
                errors.append(f"{f['financial_id']}: net assets do not add up")
            if f["tax_paid_gbp"] and b_unincorporated(biz[bid]):
                errors.append(f"{f['financial_id']}: corporation tax on an unincorporated business")
            if f["period_end"] > iso(EXTRACT_DATE) or f["period_start"] >= f["period_end"]:
                errors.append(f"{f['financial_id']}: period out of order")
    # Existing loans.
    for bid, ls in loans.items():
        for x in ls:
            if r2(12 * x["monthly_repayment_gbp"]) != x["annual_repayment_gbp"]:
                errors.append(f"{x['loan_id']}: annual repayment is not twelve monthly repayments")
            if (x["loan_status"] == "Repaid") != (x["outstanding_balance_gbp"] == 0) or x["outstanding_balance_gbp"] > x["original_amount_gbp"]:
                errors.append(f"{x['loan_id']}: balance does not match status")
            if x["loan_status"] == "Repaid" and (x["arrears_days"] or x["repayment_status"] != "Repaid"):
                errors.append(f"{x['loan_id']}: repaid loan with arrears")
            if (x["arrears_days"] > 0) != (x["repayment_status"] == "In arrears") or (x["arrears_days"] > 0) != (x["arrears_gbp"] > 0):
                errors.append(f"{x['loan_id']}: arrears fields disagree")
            if x["start_date"] < biz[bid][1]:
                errors.append(f"{x['loan_id']}: loan before the business started trading")
    # Collateral.
    for aid, cs in coll.items():
        for c in cs:
            valued = c["valuation_status"] == "Valued"
            if valued != (c["market_value_gbp"] is not None) or valued != (c["valuation_date"] is not None):
                errors.append(f"{c['collateral_id']}: valuation fields disagree with status")
            if valued and r2(c["market_value_gbp"] * (1 - c["forced_sale_discount_pct"] / 100)) != c["recoverable_value_gbp"]:
                errors.append(f"{c['collateral_id']}: recoverable value wrong")
            if valued and c["forced_sale_discount_pct"] != FORCED_SALE_DISCOUNT[c["security_type"]]:
                errors.append(f"{c['collateral_id']}: wrong forced-sale discount")
    # Numbering rises with dates.
    for t, col, key in (("loan_applications", "received_date", "application_id"), ("businesses", "customer_since", "business_id")):
        for a_, b_ in q(f"SELECT x.{key}, y.{key} FROM {t} x JOIN {t} y ON x.{col} < y.{col} AND x.{key} > y.{key}"):
            errors.append(f"{t}: {a_} is numbered after {b_} but is earlier")
    for (email,) in q("SELECT email FROM staff"):
        if not email.endswith("@" + firm.EMAIL_DOMAIN):
            errors.append(f"{email}: wrong domain")
    errors += policy_checks(con, apps, fins, loans, coll, biz, genuine_apps)
    return errors


def b_unincorporated(b):
    return b[3] is None


def policy_checks(con, apps, fins, loans, coll, biz, genuine):
    """Every application outside the genuine cases has the status the lending policy requires (R-01)."""
    errors = []
    grades = {a["application_id"]: a["credit_grade"] for a in apps}
    for a in apps:
        aid = a["application_id"]
        if aid in genuine:
            continue
        rec = D.fromisoformat(a["received_date"])
        fy = [f for f in fins[a["business_id"]] if f["accounts_type"] != "Management accounts" and f["period_end"] <= a["received_date"]][-1]
        when = D.fromisoformat(a["decision_date"]) if a["decision_date"] else EXTRACT_DATE
        info = D.fromisoformat(fy["period_end"]) < add_months(rec, -ACCOUNTS_MAX_MONTHS)
        valued = []
        for c in coll[aid]:
            if c["security_type"] not in VALUED_TYPES:
                continue
            if c["valuation_status"] != "Valued":
                info = True
            elif D.fromisoformat(c["valuation_date"]) < add_months(when, -VALUATION_MAX_MONTHS[c["security_type"]]):
                info = True
            else:
                valued.append(c)
        d = a["dscr"]
        months = months_between(D.fromisoformat(biz[a["business_id"]][1]), rec)
        worst = max([x["arrears_days"] for x in loans[a["business_id"]] if x["loan_status"] == "Live"] or [0])
        dec = (months < MIN_TRADING_MONTHS or not TURNOVER_MIN <= fy["turnover_gbp"] <= TURNOVER_MAX or d < MIN_DSCR
               or (not valued and not info and (a["loan_to_turnover_pct"] > MAX_LOAN_TO_TURNOVER or a["loan_requested_gbp"] > SECURED_ABOVE))
               or (valued and a["ltv_pct"] > min(MAX_LTV[c["security_type"]] for c in valued))
               or worst > ARREARS_DECLINE_DAYS or grades[aid] == "E")
        ref = (MIN_DSCR <= d < REFER_DSCR or grades[aid] == "D" or 0 < worst <= ARREARS_DECLINE_DAYS
               or fy["current_assets_gbp"] / fy["current_liabilities_gbp"] < MIN_CURRENT_RATIO)
        st = a["decision_status"]
        if st in ("Withdrawn", "In assessment"):
            continue
        if info and st != "Awaiting information":
            errors.append(f"{aid}: evidence out of date or awaited, but status is {st}")
        elif not info and st == "Awaiting information":
            errors.append(f"{aid}: awaiting information with nothing awaited")
        elif not info and dec and not (st == "Declined" or (st == "Approved" and a["policy_exception"])):
            errors.append(f"{aid}: fails a decline test, but status is {st}")
        elif not info and not dec and ref and (st not in ("Refer", "Approved", "Declined") or a["referral_reasons"] is None
                                               or a["decision_route"] == "Automated scorecard"):
            errors.append(f"{aid}: needs referral, but status is {st} via {a['decision_route']}")
        elif not info and not dec and not ref and st != "Approved":
            errors.append(f"{aid}: passes every test, but status is {st}")
    return errors
