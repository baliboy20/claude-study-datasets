"""Procurement fraud and accounts payable dataset.

Thameside Financial Group's finance team pays suppliers for IT, consultancy, facilities,
recruitment and professional services. The extract covers invoices received from
1 August to 30 September 2026, taken at close of business on Wednesday 30 September 2026.
"""

import datetime as dt
import re
from collections import defaultdict

from generator.common import firm, uk
from generator.common.dataset import Col, Table
from generator.common import staff_register
from generator.common.people import NamePicker, email_for

D = dt.date
EXTRACT_DATE = D(2026, 9, 30)
PERIOD_START = D(2026, 8, 1)
NEXT_RUN = D(2026, 10, 1)  # proposed, not yet released, at extract

VAT_RATES = {"S": 0.20, "Z": 0.0, "E": 0.0, "N": 0.0}

# ------------------------------------------------------------------ schema

def C(*a, **k):
    return Col(*a, **k)

SCHEMA = [
    Table("vat_codes", "lookup", "VAT treatment codes used on invoices.", [
        C("vat_code", "TEXT", "Code: S standard, Z zero-rated, E exempt, N supplier not VAT-registered."),
        C("description", "TEXT", "What the code means."),
        C("rate", "REAL", "VAT rate as a fraction, for example 0.20."),
    ]),
    Table("nominal_codes", "lookup", "Chart of accounts: general-ledger expense codes.", [
        C("nominal_code", "TEXT", "Four-digit ledger code."),
        C("description", "TEXT", "Expense type."),
        C("po_required", "INTEGER", "1 if a purchase order is required before an invoice can be paid (rule R-04)."),
    ]),
    Table("approval_policy", "lookup", "Delegated authority: what each business role may approve.", [
        C("business_role", "TEXT", "Business role name, matching employees.business_role."),
        C("approval_limit_gbp", "REAL", "Largest single invoice, including VAT, the role may approve alone. 0 means the role cannot approve."),
        C("scope", "TEXT", "Where the authority applies: none, own cost centre, own department or any."),
        C("notes", "TEXT", "Further conditions."),
    ]),
    Table("employees", "lookup", "Staff involved in buying, approving and paying.", [
        C("employee_id", "TEXT", "Staff number."),
        C("first_name", "TEXT", "First name."),
        C("last_name", "TEXT", "Surname."),
        C("job_title", "TEXT", "Job title."),
        C("business_role", "TEXT", "Role for approval purposes.", "approval_policy.business_role"),
        C("department", "TEXT", "Department."),
        C("office", "TEXT", "Office: City, Canary Wharf or Croydon."),
        C("email", "TEXT", "Work email address."),
        C("start_date", "TEXT", "Date the person joined."),
    ]),
    Table("cost_centres", "lookup", "Cost centres that budgets and invoices are charged to.", [
        C("cost_centre_id", "TEXT", "Cost centre code."),
        C("name", "TEXT", "Cost centre name."),
        C("department", "TEXT", "Department that owns the cost centre."),
        C("budget_holder_id", "TEXT", "Employee accountable for the budget.", "employees.employee_id"),
        C("office", "TEXT", "Office the cost centre mainly serves."),
    ]),
    Table("suppliers", "business", "Supplier master file.", [
        C("supplier_id", "TEXT", "Supplier number."),
        C("supplier_name", "TEXT", "Registered name."),
        C("legal_form", "TEXT", "Ltd, LLP or plc."),
        C("company_number", "TEXT", "Companies House number: 8 digits, or OC for an LLP, SC for a Scottish company."),
        C("incorporated_date", "TEXT", "Date the company was incorporated."),
        C("vat_number", "TEXT", "UK VAT registration number, or empty if not VAT-registered.", required=False),
        C("category", "TEXT", "What the supplier provides."),
        C("default_nominal_code", "TEXT", "Usual ledger code for this supplier.", "nominal_codes.nominal_code"),
        C("address_line_1", "TEXT", "Registered address."),
        C("town", "TEXT", "Town."),
        C("postcode", "TEXT", "Postcode."),
        C("contact_name", "TEXT", "Accounts contact at the supplier."),
        C("contact_phone", "TEXT", "Phone number held on file, used for call-back checks."),
        C("payment_terms", "TEXT", "14 days, 30 days, 30 days EOM (30 days after the end of the invoice month) or 60 days."),
        C("onboarded_date", "TEXT", "Date the supplier was approved for use."),
        C("onboarded_by", "TEXT", "Employee who set the supplier up.", "employees.employee_id"),
        C("status", "TEXT", "Approved or Inactive."),
    ]),
    Table("supplier_bank_details", "business", "Supplier bank accounts, one row per version. A change creates a new version.", [
        C("bank_detail_id", "TEXT", "Bank-detail record number."),
        C("supplier_id", "TEXT", "Supplier.", "suppliers.supplier_id"),
        C("version", "TEXT", "V1 for the first account, V2 for the first change and so on."),
        C("bank_name", "TEXT", "Bank."),
        C("account_name", "TEXT", "Name on the account."),
        C("sort_code", "TEXT", "Sort code, NN-NN-NN."),
        C("account_number", "TEXT", "Eight-digit account number."),
        C("iban", "TEXT", "International account number."),
        C("effective_from", "TEXT", "First date payments go to this account."),
        C("effective_to", "TEXT", "Last date, or empty if current.", required=False),
        C("change_channel", "TEXT", "How the details were received: Onboarding form, Letter, Email or Supplier portal."),
        C("change_logged_by", "TEXT", "Employee who entered the details.", "employees.employee_id"),
        C("verified_by", "TEXT", "Employee who verified the details.", "employees.employee_id", required=False),
        C("verified_date", "TEXT", "Date verified.", required=False),
        C("verification_method", "TEXT", "How the details were verified.", required=False),
        C("cop_result", "TEXT", "Confirmation of Payee result: Match, Close match, No match or Not checked."),
    ]),
    Table("purchase_orders", "business", "Purchase orders. Each order has a single line.", [
        C("po_id", "TEXT", "Purchase order number."),
        C("supplier_id", "TEXT", "Supplier.", "suppliers.supplier_id"),
        C("raised_date", "TEXT", "Date raised."),
        C("raised_by", "TEXT", "Employee who raised it.", "employees.employee_id"),
        C("approved_by", "TEXT", "Employee who approved it.", "employees.employee_id"),
        C("cost_centre_id", "TEXT", "Cost centre charged.", "cost_centres.cost_centre_id"),
        C("nominal_code", "TEXT", "Ledger code.", "nominal_codes.nominal_code"),
        C("description", "TEXT", "What was ordered."),
        C("unit", "TEXT", "Unit of measure, for example day, month or licence."),
        C("quantity", "REAL", "Quantity ordered."),
        C("unit_price", "REAL", "Price per unit, excluding VAT."),
        C("po_value_net", "REAL", "Order value excluding VAT."),
        C("status", "TEXT", "Open, Received or Closed."),
    ]),
    Table("goods_received", "business", "Goods receipts and service confirmations against purchase orders.", [
        C("grn_id", "TEXT", "Goods received note number."),
        C("po_id", "TEXT", "Purchase order.", "purchase_orders.po_id"),
        C("received_date", "TEXT", "Date goods arrived or the service was confirmed."),
        C("received_by", "TEXT", "Employee who confirmed receipt.", "employees.employee_id"),
        C("quantity_received", "REAL", "Quantity delivered."),
        C("quantity_accepted", "REAL", "Quantity accepted."),
        C("status", "TEXT", "Accepted, Partially accepted or Rejected."),
        C("notes", "TEXT", "Receipt notes.", required=False),
    ]),
    Table("invoices", "business", "Supplier invoices registered by accounts payable. This is the primary table.", [
        C("invoice_id", "TEXT", "Internal invoice number, given on registration."),
        C("supplier_id", "TEXT", "Supplier.", "suppliers.supplier_id"),
        C("supplier_invoice_ref", "TEXT", "The supplier's own invoice number."),
        C("invoice_date", "TEXT", "Date on the invoice."),
        C("received_date", "TEXT", "Date the invoice reached accounts payable."),
        C("due_date", "TEXT", "Date payment is due under the supplier's terms."),
        C("service_period", "TEXT", "Month the goods or services relate to, YYYY-MM."),
        C("po_id", "TEXT", "Purchase order, if any.", "purchase_orders.po_id", required=False),
        C("cost_centre_id", "TEXT", "Cost centre charged.", "cost_centres.cost_centre_id"),
        C("nominal_code", "TEXT", "Ledger code.", "nominal_codes.nominal_code"),
        C("description", "TEXT", "Invoice description."),
        C("quantity", "REAL", "Quantity invoiced."),
        C("unit_price", "REAL", "Price per unit, excluding VAT."),
        C("net_amount", "REAL", "Amount excluding VAT."),
        C("vat_code", "TEXT", "VAT treatment.", "vat_codes.vat_code"),
        C("vat_amount", "REAL", "VAT charged."),
        C("gross_amount", "REAL", "Amount including VAT."),
        C("approver_id", "TEXT", "Employee the invoice was routed to for approval.", "employees.employee_id"),
        C("approved_date", "TEXT", "Date approved, if approved.", required=False),
        C("approval_status", "TEXT", "Approved, Awaiting approval or Queried."),
        C("payment_status", "TEXT", "Paid, Scheduled (in the 1 October run), Approved - not yet due, Awaiting approval or On hold."),
        C("bank_detail_version", "TEXT", "Supplier bank-detail version on file when the invoice was registered."),
    ]),
    Table("payments", "business", "Payments made or scheduled, one per invoice.", [
        C("payment_id", "TEXT", "Payment number."),
        C("invoice_id", "TEXT", "Invoice paid.", "invoices.invoice_id"),
        C("supplier_id", "TEXT", "Supplier paid.", "suppliers.supplier_id"),
        C("payment_run_id", "TEXT", "Payment run, or an ad hoc payment reference."),
        C("method", "TEXT", "BACS, Faster Payments or CHAPS."),
        C("run_date", "TEXT", "Date the payment was released to the bank."),
        C("value_date", "TEXT", "Date the funds reach the supplier."),
        C("amount", "REAL", "Amount paid."),
        C("bank_detail_id", "TEXT", "Bank account the payment was sent to.", "supplier_bank_details.bank_detail_id"),
        C("sort_code", "TEXT", "Sort code paid to."),
        C("account_number", "TEXT", "Account number paid to."),
        C("released_by_1", "TEXT", "First releaser.", "employees.employee_id"),
        C("released_by_2", "TEXT", "Second releaser.", "employees.employee_id"),
        C("status", "TEXT", "Settled or Scheduled."),
        C("payment_reference", "TEXT", "Reference shown on the supplier's statement."),
    ]),
    Table("accruals", "business", "Month-end accruals for goods received but not yet invoiced at 30 September 2026.", [
        C("accrual_id", "TEXT", "Accrual number."),
        C("period", "TEXT", "Accounting period, YYYY-MM."),
        C("po_id", "TEXT", "Purchase order.", "purchase_orders.po_id"),
        C("grn_id", "TEXT", "Goods receipt.", "goods_received.grn_id"),
        C("cost_centre_id", "TEXT", "Cost centre.", "cost_centres.cost_centre_id"),
        C("nominal_code", "TEXT", "Ledger code.", "nominal_codes.nominal_code"),
        C("amount_net", "REAL", "Accrued amount excluding VAT."),
        C("posted_by", "TEXT", "Employee who posted the accrual.", "employees.employee_id"),
        C("reversal_date", "TEXT", "Date the accrual reverses."),
    ]),
]

# ------------------------------------------------------------------ reference data

VAT_CODES = [
    {"vat_code": "S", "description": "Standard rate", "rate": 0.20},
    {"vat_code": "Z", "description": "Zero rate (for example printed leaflets and brochures)", "rate": 0.0},
    {"vat_code": "E", "description": "Exempt", "rate": 0.0},
    {"vat_code": "N", "description": "No VAT: supplier not VAT-registered", "rate": 0.0},
]

NOMINALS = [
    ("6100", "IT services and support", 1), ("6110", "Software licences and subscriptions", 1),
    ("6120", "Telecoms and connectivity", 1), ("6200", "Consultancy fees", 1),
    ("6210", "Legal fees", 0), ("6220", "Audit and accountancy fees", 1),
    ("6230", "Tax advisory fees", 0), ("6300", "Recruitment fees", 1),
    ("6310", "Interim and contract staff", 1), ("6320", "Training and development", 1),
    ("6400", "Premises cleaning", 1), ("6410", "Security services", 1),
    ("6420", "Repairs and maintenance", 1), ("6430", "Waste management", 1),
    ("6440", "Catering and hospitality", 1), ("6450", "Water and refreshments", 1),
    ("6500", "Printing, postage and courier", 1), ("6510", "Office supplies", 1),
    ("6520", "Document storage", 1), ("6530", "Translation services", 1),
    ("6600", "Events", 1), ("6700", "Office fit-out (below capitalisation threshold)", 1),
]

POLICY = [
    ("Requester", 0, "none", "Raises purchase requisitions."),
    ("Accounts Payable Assistant", 0, "none", "Registers and matches invoices. Proposes payment runs."),
    ("Procurement Officer", 0, "none", "Raises purchase orders, onboards suppliers, logs bank-detail changes."),
    ("Budget Holder", 5000, "own cost centre", "Approves invoices charged to cost centres they hold."),
    ("Department Head", 25000, "own department", "Approves invoices for any cost centre in their department."),
    ("Head of Finance Operations", 25000, "own department", "Verifies bank-detail changes by call-back. Second releaser of payment runs."),
    ("Finance Director", 100000, "any", "First releaser of payment runs."),
    ("Chief Financial Officer", 250000, "any", "Above £250,000 a second signature from the Chief Executive Officer is required."),
    ("Chief Executive Officer", 250000, "any", "Co-signs invoices above £250,000 with the Chief Financial Officer."),
]
LIMIT = {r: l for r, l, _, _ in POLICY}

# id, title, role, department, office, cost centre held (or None), gender
EMPLOYEES = [
    ("EMP-001", "Chief Financial Officer", "Chief Financial Officer", "Finance", "City", "f"),
    ("EMP-002", "Finance Director", "Finance Director", "Finance", "City", "m"),
    ("EMP-003", "Head of Finance Operations", "Head of Finance Operations", "Finance", "Croydon", "f"),
    ("EMP-004", "Accounts Payable Assistant", "Accounts Payable Assistant", "Finance", "Croydon", "m"),
    ("EMP-005", "Senior Accounts Payable Assistant", "Accounts Payable Assistant", "Finance", "Croydon", "f"),
    ("EMP-006", "Procurement Officer", "Procurement Officer", "Finance", "Canary Wharf", "m"),
    ("EMP-007", "Senior Procurement Officer", "Procurement Officer", "Finance", "City", "f"),
    ("EMP-008", "Head of Technology", "Department Head", "Technology", "Canary Wharf", "m"),
    ("EMP-009", "IT Service Delivery Manager", "Budget Holder", "Technology", "Canary Wharf", "f"),
    ("EMP-010", "Infrastructure Manager", "Budget Holder", "Technology", "Canary Wharf", "m"),
    ("EMP-011", "Head of Facilities and Property", "Department Head", "Facilities", "City", "f"),
    ("EMP-012", "Facilities Manager, Canary Wharf", "Budget Holder", "Facilities", "Canary Wharf", "m"),
    ("EMP-013", "Office Services Manager, Croydon", "Budget Holder", "Facilities", "Croydon", "f"),
    ("EMP-014", "Head of People", "Department Head", "People", "City", "f"),
    ("EMP-015", "Talent Acquisition Manager", "Budget Holder", "People", "City", "m"),
    ("EMP-016", "General Counsel", "Department Head", "Legal and Compliance", "City", "m"),
    ("EMP-017", "Compliance Manager", "Budget Holder", "Legal and Compliance", "City", "f"),
    ("EMP-018", "Information Security Manager", "Budget Holder", "Technology", "Canary Wharf", "f"),
    ("EMP-019", "Chief Executive Officer", "Chief Executive Officer", "Executive", "City", "m"),
    ("EMP-020", "Financial Controller", "Budget Holder", "Finance", "City", "m"),
]

COST_CENTRES = [
    ("CC-110", "Finance Operations", "Finance", "EMP-020", "Croydon"),
    ("CC-120", "Executive Office", "Finance", "EMP-001", "City"),
    ("CC-210", "Technology Service Desk", "Technology", "EMP-009", "Canary Wharf"),
    ("CC-220", "Technology Infrastructure", "Technology", "EMP-010", "Canary Wharf"),
    ("CC-230", "Information Security", "Technology", "EMP-018", "Canary Wharf"),
    ("CC-310", "Facilities - Canary Wharf", "Facilities", "EMP-012", "Canary Wharf"),
    ("CC-320", "Facilities - Croydon", "Facilities", "EMP-013", "Croydon"),
    ("CC-330", "Facilities - City", "Facilities", "EMP-011", "City"),
    ("CC-410", "Talent Acquisition", "People", "EMP-015", "City"),
    ("CC-420", "Learning and Development", "People", "EMP-014", "City"),
    ("CC-510", "Compliance", "Legal and Compliance", "EMP-017", "City"),
    ("CC-520", "Legal", "Legal and Compliance", "EMP-016", "City"),
]

DEPT_HEAD = {"Finance": "EMP-002", "Technology": "EMP-008", "Facilities": "EMP-011",
             "People": "EMP-014", "Legal and Compliance": "EMP-016"}

# Item templates: (description, unit, price low, price high, price step, qty low, qty high, vat code)
T = {
    "it_support": [("Desktop support - additional engineer days", "day", 450, 650, 25, 2, 6, "S"),
                   ("Laptop imaging and deployment", "device", 45, 70, 5, 20, 60, "S"),
                   ("Network switch replacement - labour", "day", 550, 750, 25, 1, 4, "S")],
    "legal": [("Professional fees - commercial contract review", "hour", 285, 395, 5, 6, 28, "S"),
              ("Professional fees - employment advice", "hour", 265, 345, 5, 4, 16, "S")],
    "cleaning": [("Additional deep clean - kitchen and washrooms", "visit", 380, 520, 10, 1, 3, "S")],
    "consult": [("Operating model review - consultant days", "day", 850, 1150, 25, 3, 9, "S")],
    "recruit": [("Placement fee - permanent hire", "placement", 6200, 11800, 50, 1, 1, "S"),
                ("Advertising and shortlisting package", "package", 950, 1650, 50, 1, 2, "S")],
    "audit": [("Accounts preparation support", "day", 950, 1250, 25, 2, 6, "S")],
    "licences": [("Analytics platform subscription - monthly", "licence", 38, 62, 1, 60, 140, "S")],
    "security": [("Manned guarding - monthly service", "month", 9800, 14600, 50, 1, 1, "S"),
                 ("Event security cover", "hour", 24, 32, 1, 16, 48, "S")],
    "print": [("Printed client brochures", "copy", 1, 3, 1, 500, 1800, "Z"),
              ("Business cards", "box", 28, 42, 1, 6, 20, "S")],
    "catering": [("Staff restaurant management fee - monthly", "month", 6400, 8900, 50, 1, 1, "S"),
                 ("Hospitality catering - client event", "head", 38, 65, 1, 30, 120, "S")],
    "tax": [("Tax advisory - VAT partial exemption review", "hour", 240, 320, 5, 8, 30, "S")],
    "office": [("Stationery and consumables", "order", 180, 940, 10, 1, 1, "S"),
               ("Printer toner cartridges", "cartridge", 85, 140, 5, 6, 24, "S")],
    "telecoms": [("Leased line and SIP trunk - monthly", "month", 3800, 5200, 25, 1, 1, "S"),
                 ("Mobile fleet airtime - monthly", "month", 1900, 2800, 25, 1, 1, "S")],
    "hr_consult": [("HR policy review - consultant days", "day", 650, 850, 25, 2, 8, "S")],
    "training": [("Regulatory training workshop", "delegate", 280, 420, 10, 6, 14, "S")],
    "courier": [("Same-day courier services - monthly statement", "month", 240, 690, 10, 1, 1, "S")],
    "cloud": [("Cloud hosting - monthly consumption", "month", 6800, 9600, 10, 1, 1, "S"),
              ("Cloud migration engineering", "day", 700, 900, 25, 3, 10, "S")],
    "electrical": [("Electrical testing - fixed wire inspection", "day", 520, 680, 20, 1, 4, "S"),
                   ("Lighting repairs - reactive call-out", "job", 180, 460, 10, 1, 3, "S")],
    "interim": [("Interim management accountant", "day", 520, 650, 10, 5, 20, "S")],
    "consult2": [("Data governance advisory - consultant days", "day", 900, 1200, 25, 3, 8, "S")],
    "waste": [("Confidential waste and recycling collections - monthly", "month", 640, 980, 10, 1, 1, "S")],
    "storage": [("Archive box storage - monthly", "box-month", 0.45, 0.55, 0.01, 2400, 3600, "S"),
                ("Archive retrieval requests", "retrieval", 6, 9, 1, 20, 80, "S")],
    "search": [("Executive search - retained fee instalment", "instalment", 8500, 14500, 250, 1, 1, "S")],
    "cyber": [("Penetration test - external perimeter", "day", 950, 1250, 25, 3, 8, "S")],
    "events": [("Event production - client seminar", "event", 3800, 9200, 100, 1, 1, "S")],
    "water": [("Water cooler rental and servicing - monthly", "month", 210, 340, 10, 1, 1, "S")],
    "translation": [("Translation - regulatory correspondence", "1,000 words", 95, 140, 5, 3, 18, "N")],
    "fitout": [("Meeting room refurbishment - furniture and installation", "room", 3200, 6800, 100, 1, 2, "S")],
    "pentest_ignore": [],
}

# key, name, form, category, nominal, area, terms, onboarded, templates, cost centres, ad hoc weight,
# monthly template index or None, bank, country
SUPPLIERS = [
    ("kestrelgate", "Kestrelgate IT Services Ltd", "Ltd", "IT services", "6100", "City of London", "30 days", D(2021, 3, 15), "it_support", ["CC-210", "CC-220"], 4, None),
    ("okafor", "Okafor & Lindqvist LLP", "LLP", "Legal services", "6210", "City of London", "30 days", D(2019, 6, 3), "legal", ["CC-520", "CC-510"], 4, None),
    ("wapping", "Wapping Facilities Ltd", "Ltd", "Cleaning", "6400", "Wapping", "30 days EOM", D(2020, 1, 20), "cleaning", ["CC-310"], 1, None),
    ("brindlemoor", "Brindlemoor Consulting Ltd", "Ltd", "Management consultancy", "6200", "City of London", "30 days", D(2022, 9, 5), "consult", ["CC-120", "CC-110"], 2, None),
    ("hollowfield", "Hollowfield Recruitment Ltd", "Ltd", "Recruitment", "6300", "Fitzrovia", "14 days", D(2021, 11, 8), "recruit", ["CC-410"], 3, None),
    ("pemberton", "Pemberton Ashdown LLP", "LLP", "Audit and accountancy", "6220", "City of London", "30 days", D(2018, 4, 9), "audit", ["CC-110"], 1, None),
    ("northcote", "Northcote Data Systems Ltd", "Ltd", "Software licences", "6110", "Southwark", "30 days EOM", D(2020, 7, 1), "licences", ["CC-220"], 0, 0),
    ("quayguard", "Quayguard Security Services Ltd", "Ltd", "Security services", "6410", "Canary Wharf", "30 days", D(2019, 2, 11), "security", ["CC-310"], 1, 0),
    ("sixpenny", "Sixpenny Print & Design Ltd", "Ltd", "Printing", "6500", "Islington", "30 days", D(2022, 2, 14), "print", ["CC-320", "CC-330"], 3, None),
    ("marlowe", "Marlowe Catering Partners Ltd", "Ltd", "Catering", "6440", "Canary Wharf", "30 days", D(2020, 10, 12), "catering", ["CC-310", "CC-330"], 2, 0),
    ("adeyemi", "Adeyemi Tax Advisory Ltd", "Ltd", "Tax advisory", "6230", "City of London", "30 days", D(2023, 1, 16), "tax", ["CC-110"], 2, None),
    ("fairlop", "Fairlop Office Supplies Ltd", "Ltd", "Office supplies", "6510", "Hainault", "30 days", D(2019, 9, 23), "office", ["CC-320", "CC-330", "CC-310"], 5, None),
    ("cobaltline", "Cobaltline Networks Ltd", "Ltd", "Telecoms", "6120", "Canary Wharf", "30 days", D(2021, 5, 4), "telecoms", ["CC-220"], 0, 0),
    ("hartwell", "Hartwell Kaur Associates Ltd", "Ltd", "HR consultancy", "6200", "Croydon", "30 days", D(2023, 6, 19), "hr_consult", ["CC-420"], 2, None),
    ("tallis", "Tallis Lane Training Ltd", "Ltd", "Training", "6320", "Bloomsbury", "30 days", D(2022, 11, 7), "training", ["CC-420", "CC-510"], 2, None),
    ("greyfriars", "Greyfriars Couriers Ltd", "Ltd", "Courier", "6500", "City of London", "14 days", D(2020, 3, 2), "courier", ["CC-330"], 0, 0),
    ("linnet", "Linnet Cloud Solutions Ltd", "Ltd", "Cloud services", "6100", "Shoreditch", "30 days", D(2022, 4, 25), "cloud", ["CC-220"], 2, 0),
    ("brookmill", "Brookmill Electrical Contractors Ltd", "Ltd", "Electrical maintenance", "6420", "Deptford", "30 days", D(2021, 8, 16), "electrical", ["CC-310", "CC-330", "CC-320"], 4, None),
    ("ashgrove", "Ashgrove Interim Finance Ltd", "Ltd", "Interim staff", "6310", "City of London", "14 days", D(2023, 3, 6), "interim", ["CC-110"], 3, None),
    ("mehtaquinn", "Mehta Quinn Consulting LLP", "LLP", "Data and governance consultancy", "6200", "City of London", "30 days", D(2023, 10, 2), "consult2", ["CC-510", "CC-230"], 2, None),
    ("stonecroft", "Stonecroft Waste Solutions Ltd", "Ltd", "Waste management", "6430", "Mitcham", "30 days EOM", D(2019, 12, 2), "waste", ["CC-310"], 0, 0),
    ("kowalski", "Kowalski Building Maintenance Ltd", "Ltd", "Building maintenance", "6420", "Bow", "30 days", D(2022, 6, 13), "electrical", ["CC-330", "CC-320"], 3, None),
    ("silverdale", "Silverdale Archive Storage Ltd", "Ltd", "Document storage", "6520", "Thamesmead", "30 days EOM", D(2018, 11, 26), "storage", ["CC-110"], 1, 0),
    ("fleetwood", "Fleetwood Hart Search Ltd", "Ltd", "Executive search", "6300", "Fitzrovia", "30 days", D(2023, 2, 20), "search", ["CC-410"], 2, None),
    ("corvid", "Corvid Cyber Assurance Ltd", "Ltd", "Cyber security testing", "6100", "Shoreditch", "30 days", D(2024, 1, 15), "cyber", ["CC-230"], 2, None),
    ("lantern", "Lantern Row Events Ltd", "Ltd", "Events", "6600", "Southwark", "14 days", D(2024, 5, 7), "events", ["CC-120"], 2, None),
    ("clearbrook", "Clearbrook Water Services Ltd", "Ltd", "Water and refreshments", "6450", "Tottenham", "30 days EOM", D(2019, 5, 20), "water", ["CC-320"], 0, 0),
    ("osei", "Osei Translation Services Ltd", "Ltd", "Translation", "6530", "Islington", "14 days", D(2024, 9, 9), "translation", ["CC-510"], 2, None),
    ("gableend", "Gable End Interiors Ltd", "Ltd", "Office fit-out", "6700", "Edinburgh", "30 days", D(2025, 2, 3), "fitout", ["CC-330", "CC-310"], 2, None),
    ("quillmark", "Quillmark Digital Ltd", "Ltd", "Data platform consultancy", "6200", "Shoreditch", "30 days", D(2025, 11, 10), "consult2", ["CC-220"], 0, None),
    ("velloway", "Velloway Technology Ltd", "Ltd", "IT services", "6100", "Bow", "14 days", D(2026, 8, 17), "it_support", ["CC-210"], 0, None),
]

# Surnames that appear in supplier names. No person carries them, so no conflict of interest is implied by accident.
RESERVED_SURNAMES = {"Okafor", "Lindqvist", "Adeyemi", "Osei", "Mehta", "Quinn", "Kowalski", "Kaur", "Hartwell",
                     "Hart", "Fleetwood", "Pemberton", "Ashdown", "Tallis", "Marlowe"}

# Supplier invoice numbering: (format, anchor number, anchor date, numbers issued per day).
# Planted references sit on these sequences so they look like every other invoice from the supplier.
REF_FORMATS = {
    "kestrelgate": ("KIT-{n}", 24817, D(2026, 9, 3), 4.0),
    "wapping": ("WF-{n}", 10388, D(2026, 8, 31), 2.1),
    "tallis": ("TLT-{n}", 5521, D(2026, 9, 7), 0.4),
    "velloway": ("VT-{n}", 107, D(2026, 8, 26), 0.07),
    "brindlemoor": ("BC-2026-{n:04d}", 318, D(2026, 9, 14), 1.2),
    "cobaltline": ("CN-{n}", 30914, D(2026, 9, 1), 9.0),
    "quayguard": ("QSS/26/{n}", 4471, D(2026, 9, 21), 3.0),
    "brookmill": ("BEC-{n:05d}", 8812, D(2026, 9, 11), 2.0),
    "pemberton": ("PA-INV-{n}", 60271, D(2026, 8, 24), 14.0),
    "quillmark": ("QD-2026{n:03d}", 41, D(2026, 9, 11), 0.15),
    "sixpenny": ("SPD/26/{n}", 1187, D(2026, 9, 3), 1.5),
}

# Bands just under an approval limit that normal invoices avoid, so only planted cases sit there.
NEAR_LIMIT_BANDS = [(4500, 5000), (22500, 25000), (90000, 100000), (225000, 250000)]

# Each employee's entry in the firm-wide staff register (generator/common/staff_register.py).
STAFF_REGISTER_IDS = {f"EMP-{n:03d}": f"TFG-{n:03d}" for n in range(1, 21)}

# Business story facts the data must agree with (checked in checks()).
NEW_AP_ASSISTANT, NEW_AP_START = "EMP-004", D(2026, 7, 6)
PORTAL_OPENED = D(2026, 8, 1)

# Appraisal types each planted case needs (IDs from docs/appraisal-types.html).
APPRAISAL = {
    "CASE-01": "A2", "CASE-02": "A5, A3", "CASE-03": "A6", "CASE-04": "A1", "CASE-05": "A7, A4",
    "CASE-06": "A1", "CASE-07": "A3", "CASE-08": "A2, A8", "CASE-09": "A8", "CASE-10": "A7, A8",
    "CASE-11": "A5, A3", "CASE-12": "A4",
}

# ------------------------------------------------------------------ helpers


def pence(x):
    return int(round(x * 100))


def money(p):
    return round(p / 100, 2)


def iso(d):
    return d.isoformat() if d else None


def due_date(invoice_date, terms):
    if terms == "30 days EOM":
        eom = D(invoice_date.year + (invoice_date.month == 12), invoice_date.month % 12 + 1, 1) - dt.timedelta(days=1)
        return eom + dt.timedelta(days=30)
    days = int(terms.split()[0])
    return invoice_date + dt.timedelta(days=days)


def payment_runs():
    d, runs = D(2026, 8, 4), []
    while d <= NEXT_RUN:
        if d.weekday() in (1, 3) and uk.is_working_day(d):
            runs.append(d)
        d += dt.timedelta(days=1)
    return runs


RUNS = payment_runs()


def choose_run(approved, due):
    """Latest BACS run whose value date is on or before the due date; else the first run after approval."""
    eligible = [r for r in RUNS if r > approved]
    if not eligible:
        return None
    on_time = [r for r in eligible if uk.bacs_value_date(r) <= due]
    return on_time[-1] if on_time else eligible[0]


# ------------------------------------------------------------------ builder


class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.names = NamePicker(rng, RESERVED_SURNAMES | staff_register.surnames())
        # Register first names are taken too, so no contact shares a first name with a member of staff.
        self.names.used |= {(p[0], p[1]) for p in staff_register.PEOPLE.values()}
        self.roots = set()
        self.phones = set()
        self.rows = defaultdict(list)
        self.cases, self.case_records = [], []
        self.inv_specs = []  # invoice drafts before numbering
        self.po_seq, self.grn_seq, self.bd_seq = 412, 31877, 1
        self.used_gross = defaultdict(set)  # supplier -> gross pence, keeps normal amounts unique per supplier
        self.emp = {}
        self.cc = {}
        self.sup = {}

    # ---- lookups and master data

    def lookups(self):
        self.rows["vat_codes"] = VAT_CODES
        self.rows["nominal_codes"] = [{"nominal_code": c, "description": d, "po_required": r} for c, d, r in NOMINALS]
        self.rows["approval_policy"] = [{"business_role": r, "approval_limit_gbp": float(l), "scope": s, "notes": n}
                                        for r, l, s, n in POLICY]
        for eid, title, role, dept, office, g in EMPLOYEES:
            person = staff_register.person(STAFF_REGISTER_IDS[eid])
            first, last = person["first_name"], person["last_name"]
            n = int(eid[-3:])
            start = uk.next_working_day(D(2008 + (n * 7) % 17, 1 + (n * 5) % 12, 1 + (n * 11) % 27))
            if eid == NEW_AP_ASSISTANT:
                start = NEW_AP_START  # the replacement assistant in the business story
            row = {"employee_id": eid, "first_name": first, "last_name": last, "job_title": title,
                   "business_role": role, "department": dept, "office": office,
                   "email": email_for(first, last, firm.EMAIL_DOMAIN), "start_date": iso(start)}
            self.rows["employees"].append(row)
            self.emp[eid] = row
        for cid, name, dept, holder, office in COST_CENTRES:
            row = {"cost_centre_id": cid, "name": name, "department": dept, "budget_holder_id": holder, "office": office}
            self.rows["cost_centres"].append(row)
            self.cc[cid] = row

    def suppliers(self):
        for i, s in enumerate(SUPPLIERS, start=1):
            key, name, form, cat, nominal, area, terms, onboarded, tmpl, ccs, weight, monthly = s
            town, outwards = uk.DISTRICTS[area]
            country = "Scotland" if area == "Edinburgh" else "England"
            first, last = self.names.pick()
            vat = None if tmpl == "translation" else uk.vat_number(self.rng)
            sid = f"SUP-{i:04d}"
            if key == "velloway":
                incorporated = D(2026, 7, 9)  # set up five weeks before onboarding
            else:
                incorporated = onboarded - dt.timedelta(days=self.rng.randint(400, 5000))
                incorporated = max(incorporated, D(2004, 3, 1))
            row = {"supplier_id": sid, "supplier_name": name, "legal_form": form,
                   "company_number": uk.company_number(self.rng, form, incorporated, country),
                   "incorporated_date": iso(incorporated), "vat_number": vat,
                   "category": cat, "default_nominal_code": nominal,
                   "address_line_1": uk.street_address(self.rng, self.roots), "town": town,
                   "postcode": uk.postcode(self.rng, self.rng.choice(outwards)),
                   "contact_name": f"{first} {last}",
                   "contact_phone": uk.landline(self.rng, self.phones, "Edinburgh" if town == "Edinburgh" else "London"),
                   "payment_terms": terms, "onboarded_date": iso(onboarded),
                   "onboarded_by": "EMP-007" if i % 2 else "EMP-006", "status": "Approved"}
            self.rows["suppliers"].append(row)
            self.sup[key] = dict(row, key=key, tmpl=tmpl, ccs=ccs, weight=weight, monthly=monthly, nominal=nominal)
        # One historic supplier no longer used.
        self.inactive_supplier()

    def inactive_supplier(self):
        first, last = self.names.pick()
        sid = f"SUP-{len(SUPPLIERS) + 1:04d}"
        self.rows["suppliers"].append({
            "supplier_id": sid, "supplier_name": "Harbourline Removals Ltd", "legal_form": "Ltd",
            "company_number": uk.company_number(self.rng, "Ltd", D(2011, 2, 14)), "incorporated_date": "2011-02-14",
            "vat_number": uk.vat_number(self.rng),
            "category": "Office removals", "default_nominal_code": "6420",
            "address_line_1": uk.street_address(self.rng, self.roots), "town": "London",
            "postcode": uk.postcode(self.rng, "SE8"), "contact_name": f"{first} {last}",
            "contact_phone": uk.landline(self.rng, self.phones), "payment_terms": "30 days",
            "onboarded_date": "2017-07-10", "onboarded_by": "EMP-006", "status": "Inactive"})
        self.add_bank(sid, "Harbourline Removals Ltd", "V1", D(2017, 7, 10), D(2025, 3, 31), "Onboarding form",
                      "EMP-006", "EMP-003", D(2017, 7, 11), "Call-back to number on file", "Not checked",
                      bank="Lloyds Bank")

    def add_bank(self, sid, name, version, start, end, channel, logged, verifier, vdate, method, cop,
                 bank=None, sc=None, acct=None):
        bank = bank or self.rng.choice(list(uk.BANKS))
        sc = sc or uk.sort_code(self.rng, bank)
        acct = acct or uk.account_number(self.rng)
        bid = f"BD-{self.bd_seq:04d}"
        self.bd_seq += 1
        row = {"bank_detail_id": bid, "supplier_id": sid, "version": version, "bank_name": bank,
               "account_name": name.upper().replace(" LIMITED", " LTD"), "sort_code": sc, "account_number": acct,
               "iban": uk.iban(bank, sc, acct), "effective_from": iso(start), "effective_to": iso(end),
               "change_channel": channel, "change_logged_by": logged, "verified_by": verifier,
               "verified_date": iso(vdate), "verification_method": method, "cop_result": cop}
        self.rows["supplier_bank_details"].append(row)
        return row

    def bank_details(self):
        """V1 for every supplier; a few historic, properly verified changes; planted changes come later."""
        historic_changes = {"marlowe": D(2025, 4, 14), "fairlop": D(2025, 10, 6), "kowalski": D(2025, 6, 23)}
        planted = {"velloway", "cobaltline", "northcote"}
        for key, s in self.sup.items():
            if key in planted:
                continue
            on = D.fromisoformat(s["onboarded_date"])
            if key in historic_changes:
                ch = historic_changes[key]
                self.add_bank(s["supplier_id"], s["supplier_name"], "V1", on, ch - dt.timedelta(days=1),
                              "Onboarding form", s["onboarded_by"], "EMP-003", on + dt.timedelta(days=1),
                              "Call-back to number on file", "Match" if on.year >= 2020 else "Not checked")
                self.add_bank(s["supplier_id"], s["supplier_name"], "V2", ch, None, "Letter", "EMP-006",
                              "EMP-003", ch - dt.timedelta(days=2), "Call-back to number on file", "Match")
            else:
                self.add_bank(s["supplier_id"], s["supplier_name"], "V1", on, None, "Onboarding form",
                              s["onboarded_by"], "EMP-003", uk.add_working_days(on, 1),
                              "Call-back to number on file", "Match" if on.year >= 2020 else "Not checked")

    def bank_on(self, sid, day):
        for b in self.rows["supplier_bank_details"]:
            if b["supplier_id"] != sid:
                continue
            start = D.fromisoformat(b["effective_from"])
            end = D.fromisoformat(b["effective_to"]) if b["effective_to"] else D(2099, 1, 1)
            if start <= day <= end:
                return b
        raise KeyError((sid, day))

    # ---- purchase orders, receipts, invoices

    def approver_for(self, gross, cc_id, exclude=()):
        """Lowest-authority approver allowed to approve this amount for this cost centre."""
        cc = self.cc[cc_id]
        chain = [cc["budget_holder_id"], DEPT_HEAD[cc["department"]], "EMP-002", "EMP-001"]
        for e in chain:
            role = self.emp[e]["business_role"]
            if gross <= LIMIT[role] and e not in exclude:
                return e
        raise ValueError(gross)

    def new_po(self, sup, raised, raised_by, cc_id, nominal, desc, unit, qty, price, vat_code, status="Received",
               approved_by=None):
        net = pence(qty * price)
        gross = net + pence(money(net) * VAT_RATES[vat_code])
        po_id = f"PO-{self.po_seq:05d}"
        self.po_seq += 1
        row = {"po_id": po_id, "supplier_id": sup["supplier_id"], "raised_date": iso(raised), "raised_by": raised_by,
               "approved_by": approved_by or self.approver_for(money(gross), cc_id, exclude=(raised_by,)),
               "cost_centre_id": cc_id, "nominal_code": nominal, "description": desc, "unit": unit,
               "quantity": float(qty), "unit_price": float(price), "po_value_net": money(net), "status": status}
        self.rows["purchase_orders"].append(row)
        return row

    def new_grn(self, po, received, qty_recv, qty_acc, notes=None):
        receiver = self.cc[po["cost_centre_id"]]["budget_holder_id"]
        status = "Accepted" if qty_acc == qty_recv else "Partially accepted"
        row = {"grn_id": f"GRN-{self.grn_seq:06d}", "po_id": po["po_id"], "received_date": iso(received),
               "received_by": receiver, "quantity_received": float(qty_recv), "quantity_accepted": float(qty_acc),
               "status": status, "notes": notes}
        self.grn_seq += 1
        self.rows["goods_received"].append(row)
        return row

    def draw_line(self, sup, normal=True):
        """Random line from the supplier's templates, avoiding near-limit bands and repeated amounts."""
        for _ in range(400):
            desc, unit, lo, hi, step, qlo, qhi, vat = self.rng.choice(T[sup["tmpl"]])
            steps = int(round((hi - lo) / step))
            price = round(lo + step * self.rng.randint(0, steps), 2)
            qty = self.rng.randint(qlo, qhi)
            if sup["key"] == "osei":
                vat = "N"
            net = pence(qty * price)
            gross = net + pence(money(net) * VAT_RATES[vat])
            g = money(gross)
            if normal and (any(lo_ <= g < hi_ for lo_, hi_ in NEAR_LIMIT_BANDS) or g >= 90000
                           or gross in self.used_gross[sup["supplier_id"]]):
                continue
            self.used_gross[sup["supplier_id"]].add(gross)
            return desc, unit, qty, price, vat
        raise RuntimeError(sup["key"])

    def invoice(self, sup, inv_date, ref, cc_id, desc, unit, qty, price, vat, po=None, received=None,
                approver=None, approved=None, status=None, service_period=None, nominal=None):
        net = pence(qty * price)
        vat_p = pence(money(net) * VAT_RATES[vat])
        received = received or inv_date + dt.timedelta(days=self.rng.choice([0, 1, 1, 2, 3, 4, 6]))
        received = uk.next_working_day(max(received, PERIOD_START))
        received = min(received, EXTRACT_DATE)
        gross = money(net + vat_p)
        self.used_gross[sup["supplier_id"]].add(net + vat_p)
        if approver is None:
            exclude = (po["raised_by"],) if po else ()
            approver = self.approver_for(gross, cc_id, exclude)
        if status is None:
            approved = approved or uk.add_working_days(received, self.rng.choice([1, 1, 2, 2, 3, 4]))
            status = "Approved" if approved <= EXTRACT_DATE else "Awaiting approval"
        if status != "Approved":
            approved = None
        spec = {"supplier_id": sup["supplier_id"], "supplier_invoice_ref": ref, "invoice_date": inv_date,
                "received_date": received, "due_date": due_date(inv_date, sup["payment_terms"]),
                "service_period": service_period or inv_date.strftime("%Y-%m"),
                "po_id": po["po_id"] if po else None, "cost_centre_id": cc_id,
                "nominal_code": nominal or (po["nominal_code"] if po else sup["nominal"]),
                "description": desc, "quantity": float(qty), "unit_price": float(price),
                "net_amount": money(net), "vat_code": vat, "vat_amount": money(vat_p), "gross_amount": gross,
                "approver_id": approver, "approved_date": approved, "approval_status": status,
                "bank_detail_version": self.bank_on(sup["supplier_id"], received)["version"],
                "_sup": sup}
        self.inv_specs.append(spec)
        return spec

    def ref_format(self, key):
        if key in REF_FORMATS:
            return REF_FORMATS[key]
        sup = self.sup[key]
        prefix = "".join(w[0] for w in sup["supplier_name"].replace("&", "").split()[:2]).upper()
        style = sum(map(ord, key)) % 4
        fmt = [f"{prefix}-{{n}}", f"{prefix}/26/{{n}}", "INV-{n:06d}", "{n}"][style]
        rng = __import__("random").Random(key)  # fixed per supplier, independent of draw order
        return fmt, rng.randint(1200, 88000), D(2026, 9, 1), rng.choice([0.6, 1.5, 3.0, 7.0])

    def assign_refs(self):
        """Give normal invoices supplier references that rise with invoice date, around any planted ones."""
        by_sup = defaultdict(list)
        for spec in self.inv_specs:
            by_sup[spec["_sup"]["key"]].append(spec)
        for key, specs in by_sup.items():
            fmt, anchor_n, anchor_d, rate = self.ref_format(key)
            head, tail = re.split(r"\{n[^}]*\}", fmt)
            rx = re.compile(re.escape(head) + r"(\d+)" + re.escape(tail))
            for spec in specs:
                m = rx.fullmatch(spec["supplier_invoice_ref"] or "")
                spec["_ref_n"] = int(m.group(1)) if m else None
            seq = sorted(specs, key=lambda x: (x["invoice_date"], x["_ref_n"] or 0))
            prev = None
            for i, spec in enumerate(seq):
                if spec["supplier_invoice_ref"]:
                    prev = spec["_ref_n"] if spec["_ref_n"] is not None else prev
                    continue
                est = anchor_n + round((spec["invoice_date"] - anchor_d).days * rate)
                nxt = next((t["_ref_n"] for t in seq[i + 1:] if t["_ref_n"] is not None), None)
                n = est if prev is None else max(prev + 1 + self.rng.randint(0, int(rate)), est)
                if nxt is not None and n >= nxt:
                    n = nxt - 1 if prev is None else prev + 1
                spec["supplier_invoice_ref"] = fmt.format(n=n)
                spec["_ref_n"] = prev = n

    def normal_invoice(self, sup, inv_date, line=None, service_period=None, cc_id=None, partial=False):
        desc, unit, qty, price, vat = line or self.draw_line(sup)
        cc_id = cc_id or self.rng.choice(sup["ccs"])
        nominal_po_required = dict((c, r) for c, _, r in NOMINALS)[sup["nominal"]]
        po = None
        if nominal_po_required:
            raised = inv_date - dt.timedelta(days=self.rng.randint(12, 45))
            raised = uk.next_working_day(raised)
            raiser = self.rng.choice(["EMP-006", "EMP-007", "EMP-006", "EMP-007", self.cc[cc_id]["budget_holder_id"]])
            po = self.new_po(sup, raised, raiser, cc_id, sup["nominal"], desc, unit, qty, price, vat)
            recv = min(inv_date, raised + dt.timedelta(days=self.rng.randint(5, 30)))
            recv = uk.next_working_day(recv) if uk.next_working_day(recv) <= inv_date else recv
            if partial and qty > 2:
                accepted = qty - 1
                self.new_grn(po, recv, qty, accepted, "One unit returned as faulty; credit not required, invoice for accepted quantity.")
                qty = accepted
            else:
                self.new_grn(po, recv, qty, qty)
        return self.invoice(sup, inv_date, None, cc_id, desc, unit, qty, price, vat, po=po,
                            service_period=service_period)

    def random_weekday(self, start, end):
        while True:
            d = start + dt.timedelta(days=self.rng.randint(0, (end - start).days))
            if uk.is_working_day(d):
                return d

    # ---- planted cases

    def case(self, cid, title, ctype, cls, sev, rules, expl, step, sql, records):
        self.cases.append({"case_id": cid, "title": title, "case_type": ctype, "classification": cls,
                           "severity": sev, "rules_involved": rules, "explanation": expl,
                           "expected_next_step": step, "detection_sql": " ".join(sql.split())})
        for table, rec, role, key in records:
            self.case_records.append({"case_id": cid, "table_name": table, "record_id": rec,
                                      "role_in_case": role, "is_key_record": int(key)})

    def plant(self):
        s, rng = self.sup, self.rng
        P = {}  # planted invoice specs by label; ids are resolved after numbering

        # CASE-01 duplicate invoice with a reformatted reference.
        k = s["kestrelgate"]
        po = self.new_po(k, D(2026, 8, 10), "EMP-007", "CC-220", "6100",
                         "Network switch replacement - labour", "day", 16, 650, "S")
        self.new_grn(po, D(2026, 8, 28), 16, 16)
        P["dup_orig"] = self.invoice(k, D(2026, 9, 3), "KIT-24817", "CC-220", po["description"], "day", 16, 650, "S",
                                     po=po, received=D(2026, 9, 4), approver="EMP-008", approved=D(2026, 9, 8))
        P["dup_copy"] = self.invoice(k, D(2026, 9, 3), "KIT24817", "CC-220", po["description"], "day", 16, 650, "S",
                                     po=po, received=D(2026, 9, 25), approver="EMP-008", approved=D(2026, 9, 29))

        # CASE-02 invoice splitting under the £5,000 budget-holder limit.
        t = s["tallis"]
        P["split5"] = []
        for d_, (qty, price) in zip([D(2026, 9, 7), D(2026, 9, 8), D(2026, 9, 10)], [(13, 300), (11, 350), (12, 335)]):
            po = self.new_po(t, D(2026, 8, 24), "EMP-006", "CC-410", "6320",
                             f"Interview skills workshop - cohort {'ABC'[len(P['split5'])]}", "delegate", qty, price, "S",
                             approved_by="EMP-015")
            self.new_grn(po, d_, qty, qty)
            P["split5"].append(self.invoice(t, d_, f"TLT-{5521 + len(P['split5'])}", "CC-410", po["description"],
                                            "delegate", qty, price, "S", po=po, received=d_ + dt.timedelta(days=1),
                                            approver="EMP-015", approved=uk.add_working_days(d_, 2), nominal="6320"))

        # CASE-03 a new supplier paid into another supplier's bank account.
        fw, vw = s["fleetwood"], s["velloway"]
        fw_bank = self.bank_on(fw["supplier_id"], D(2026, 9, 1))
        self.add_bank(vw["supplier_id"], vw["supplier_name"], "V1", D(2026, 8, 17), None, "Supplier portal",
                      "EMP-006", "EMP-006", D(2026, 8, 17), "Supplier portal self-certification", "Not checked",
                      bank=fw_bank["bank_name"], sc=fw_bank["sort_code"], acct=fw_bank["account_number"])
        P["shared"] = []
        for d_, qty, price in [(D(2026, 8, 26), 5, 640), (D(2026, 9, 9), 6, 600)]:
            po = self.new_po(vw, d_ - dt.timedelta(days=9), "EMP-006", "CC-210", "6100",
                             "Desktop support - additional engineer days", "day", qty, price, "S", approved_by="EMP-009")
            self.new_grn(po, d_ - dt.timedelta(days=1), qty, qty)
            P["shared"].append(self.invoice(vw, d_, f"VT-{100 + len(P['shared']) + 7}", "CC-210", po["description"],
                                            "day", qty, price, "S", po=po, received=d_, approver="EMP-009",
                                            approved=uk.add_working_days(d_, 1)))

        # CASE-04 invoice exceeds its purchase order (24 days billed against 20 ordered and received).
        b = s["brindlemoor"]
        po = self.new_po(b, D(2026, 7, 27), "EMP-007", "CC-120", "6200",
                         "Operating model review - consultant days", "day", 20, 900, "S")
        self.new_grn(po, D(2026, 9, 11), 20, 20, "Service confirmation: 20 consultant days delivered.")
        P["over_po"] = self.invoice(b, D(2026, 9, 14), "BC-2026-0318", "CC-120", po["description"], "day", 24, 900,
                                    "S", po=po, received=D(2026, 9, 15), approver="EMP-002", approved=D(2026, 9, 18))

        # CASE-05 payment to newly changed, poorly verified bank details, sent by Faster Payments.
        c = s["cobaltline"]
        on = D.fromisoformat(c["onboarded_date"])
        self.add_bank(c["supplier_id"], c["supplier_name"], "V1", on, D(2026, 9, 13), "Onboarding form", "EMP-007",
                      "EMP-003", on + dt.timedelta(days=1), "Call-back to number on file", "Match")
        self.add_bank(c["supplier_id"], "Cobaltline Networks Ltd", "V2", D(2026, 9, 14), None, "Email", "EMP-005",
                      "EMP-005", D(2026, 9, 14), "Email reply from requester", "No match", bank="Starling Bank")
        po = self.new_po(c, D(2026, 8, 3), "EMP-007", "CC-220", "6120",
                         "Core network maintenance - annual renewal", "year", 1, 32000, "S")
        self.new_grn(po, D(2026, 9, 1), 1, 1, "Annual maintenance renewal confirmed by Infrastructure.")
        P["new_bank"] = self.invoice(c, D(2026, 9, 1), "CN-30914", "CC-220", po["description"], "year", 1, 32000,
                                     "S", po=po, received=D(2026, 9, 2), approver="EMP-002", approved=D(2026, 9, 7))

        # CASE-06 invoice paid with no goods receipt.
        q = s["quayguard"]
        po = self.new_po(q, D(2026, 9, 1), "EMP-006", "CC-310", "6410", "Event security cover", "hour", 105, 32, "S")
        P["no_grn"] = self.invoice(q, D(2026, 9, 21), "QSS/26/4471", "CC-310", po["description"], "hour", 105, 32, "S",
                                   po=po, received=D(2026, 9, 21), approver="EMP-012", approved=D(2026, 9, 22))

        # CASE-07 approval above the approver's limit.
        bm = s["brookmill"]
        po = self.new_po(bm, D(2026, 9, 2), "EMP-006", "CC-310", "6420",
                         "Emergency replacement of distribution board - Level 3", "job", 1, 6540, "S",
                         approved_by="EMP-011")
        self.new_grn(po, D(2026, 9, 9), 1, 1, "Works completed and signed off by Facilities.")
        P["over_limit"] = self.invoice(bm, D(2026, 9, 11), "BEC-08812", "CC-310", po["description"], "job", 1, 6540,
                                       "S", po=po, received=D(2026, 9, 14), approver="EMP-012", approved=D(2026, 9, 15))

        # CASE-08 benign: identical monthly cleaning invoices for different months.
        w = s["wapping"]
        P["recurring"] = []
        for d_, ref in [(D(2026, 8, 31), "WF-10388"), (D(2026, 9, 30), "WF-10452")]:
            po = self.new_po(w, D(d_.year, d_.month, 1), "EMP-006", "CC-310", "6400",
                             f"Office cleaning - Canary Wharf - {d_.strftime('%B %Y')}", "month", 1, 3300, "S",
                             approved_by="EMP-012")
            self.new_grn(po, d_, 1, 1)
            P["recurring"].append(self.invoice(w, d_, ref, "CC-310", po["description"], "month", 1, 3300, "S", po=po,
                                               received=uk.next_working_day(d_), approver="EMP-012",
                                               approved=uk.add_working_days(d_, 2) if d_.month == 8 else None,
                                               status=None if d_.month == 8 else "Awaiting approval",
                                               service_period=d_.strftime("%Y-%m")))

        # CASE-09 benign: large audit fee, properly approved by the CFO and paid by CHAPS.
        pa = s["pemberton"]
        po = self.new_po(pa, D(2026, 7, 6), "EMP-020", "CC-110", "6220", "Interim audit fieldwork - FY2026",
                         "engagement", 1, 155000, "S", approved_by="EMP-001")
        self.new_grn(po, D(2026, 8, 21), 1, 1, "Interim fieldwork complete; engagement partner sign-off received.")
        P["large"] = self.invoice(pa, D(2026, 8, 24), "PA-INV-60271", "CC-110", po["description"], "engagement", 1,
                                  155000, "S", po=po, received=D(2026, 8, 25), approver="EMP-001", approved=D(2026, 8, 27))

        # CASE-10 benign: bank-detail change verified properly by call-back.
        n = s["northcote"]
        on = D.fromisoformat(n["onboarded_date"])
        self.add_bank(n["supplier_id"], n["supplier_name"], "V1", on, D(2026, 9, 2), "Onboarding form", "EMP-006",
                      "EMP-003", on + dt.timedelta(days=1), "Call-back to number on file", "Match")
        self.add_bank(n["supplier_id"], n["supplier_name"], "V2", D(2026, 9, 3), None, "Letter", "EMP-006", "EMP-003",
                      D(2026, 9, 2), "Call-back to number on file", "Match", bank="HSBC UK")

        # CASE-11 invoice splitting under the £25,000 department-head limit.
        qm = s["quillmark"]
        P["split25"] = []
        for d_, qty, price, ph in [(D(2026, 9, 11), 17, 1200, 1), (D(2026, 9, 18), 18, 1100, 2)]:
            po = self.new_po(qm, D(2026, 9, 1), "EMP-007", "CC-220", "6200",
                             f"Data platform discovery - phase {ph}", "day", qty, price, "S", approved_by="EMP-008")
            self.new_grn(po, d_ - dt.timedelta(days=1), qty, qty)
            P["split25"].append(self.invoice(qm, d_, f"QD-{2026}{40 + ph:03d}", "CC-220", po["description"], "day",
                                             qty, price, "S", po=po, received=d_, approver="EMP-008",
                                             approved=uk.add_working_days(d_, 2)))

        # CASE-12 the person who raised the PO also approved the invoice.
        sp = s["sixpenny"]
        po = self.new_po(sp, D(2026, 8, 19), "EMP-013", "CC-320", "6500", "Printed client brochures", "copy",
                         1400, 2.10, "Z", approved_by="EMP-011")
        self.new_grn(po, D(2026, 9, 2), 1400, 1400)
        P["sod"] = self.invoice(sp, D(2026, 9, 3), "SPD/26/1187", "CC-320", po["description"], "copy", 1400, 2.10,
                                "Z", po=po, received=D(2026, 9, 4), approver="EMP-013", approved=D(2026, 9, 7))
        return P

    # ---- normal volume

    def normal_volume(self, target):
        # Monthly recurring invoices for August and September.
        for key, s in self.sup.items():
            if s["monthly"] is None:
                continue
            for month in (8, 9):
                d_ = uk.last_working_day_of_month(2026, month)
                desc, unit, lo, hi, step, qlo, qhi, vat = T[s["tmpl"]][s["monthly"]]
                for _ in range(200):
                    price = round(lo + step * self.rng.randint(0, int(round((hi - lo) / step))), 2)
                    qty = self.rng.randint(qlo, qhi)
                    net = pence(qty * price)
                    gross = net + pence(money(net) * VAT_RATES[vat])
                    if not any(a <= money(gross) < b_ for a, b_ in NEAR_LIMIT_BANDS) and gross not in self.used_gross[s["supplier_id"]]:
                        break
                self.normal_invoice(s, d_, line=(f"{desc} ({d_.strftime('%B %Y')})", unit, qty, price, vat),
                                    service_period=d_.strftime("%Y-%m"))
        keys = [k for k, s in self.sup.items() if s["weight"]]
        weights = [self.sup[k]["weight"] for k in keys]
        partial_left = 2
        while len(self.inv_specs) < target:
            sup = self.sup[self.rng.choices(keys, weights)[0]]
            d_ = self.random_weekday(PERIOD_START - dt.timedelta(days=5), EXTRACT_DATE - dt.timedelta(days=1))
            partial = partial_left > 0 and sup["tmpl"] in ("office", "it_support") and self.rng.random() < 0.5
            partial_left -= partial
            self.normal_invoice(sup, d_, partial=partial)
        # Two invoices queried with the supplier, so held.
        held = [x for x in self.inv_specs if x.get("_normal", True)
                                     and x["approval_status"] == "Approved" and x["received_date"] > D(2026, 9, 14)
                                     and x["_sup"]["key"] in ("fairlop", "brookmill", "kowalski", "hartwell")]
        for spec in self.rng.sample(held, min(2, len(held))):
            spec["approval_status"] = "Queried"
            spec["approved_date"] = None
            spec["_hold"] = True

    def uninvoiced_orders(self):
        """Orders received but not invoiced (accrued) and orders still open."""
        rows = []
        picks = [("brookmill", "CC-330"), ("kowalski", "CC-320"), ("corvid", "CC-230"), ("hartwell", "CC-420"),
                 ("mehtaquinn", "CC-510"), ("fairlop", "CC-310"), ("lantern", "CC-120"), ("ashgrove", "CC-110")]
        for i, (key, cc_id) in enumerate(picks):
            sup = self.sup[key]
            desc, unit, qty, price, vat = self.draw_line(sup)
            po = self.new_po(sup, D(2026, 9, 1) + dt.timedelta(days=i), "EMP-007" if i % 2 else "EMP-006", cc_id,
                             sup["nominal"], desc, unit, qty, price, vat)
            grn = self.new_grn(po, uk.next_working_day(D(2026, 9, 15) + dt.timedelta(days=i)), qty, qty)
            rows.append({"accrual_id": f"ACR-{2609}{i + 1:02d}", "period": "2026-09", "po_id": po["po_id"],
                         "grn_id": grn["grn_id"], "cost_centre_id": cc_id, "nominal_code": po["nominal_code"],
                         "amount_net": po["po_value_net"], "posted_by": "EMP-020", "reversal_date": "2026-10-01"})
        for i, (key, cc_id) in enumerate([("tallis", "CC-510"), ("sixpenny", "CC-330"), ("osei", "CC-510"),
                                          ("gableend", "CC-310"), ("fleetwood", "CC-410")]):
            sup = self.sup[key]
            desc, unit, qty, price, vat = self.draw_line(sup)
            self.new_po(sup, D(2026, 9, 21) + dt.timedelta(days=i), "EMP-006", cc_id, sup["nominal"], desc, unit,
                        qty, price, vat, status="Open")
        self.rows["accruals"] = rows

    # ---- numbering and payments

    def finalise(self):
        self.assign_refs()
        specs = sorted(self.inv_specs, key=lambda x: (x["received_date"], x["supplier_id"], x["supplier_invoice_ref"]))
        pay_seq = 50311
        for n, spec in enumerate(specs):
            spec["invoice_id"] = f"INV-{260101 + n}"
        for spec in specs:
            sup = spec["_sup"]
            status = spec["approval_status"]
            pay = None
            if spec.get("_hold"):
                pay_status = "On hold"
            elif status == "Awaiting approval":
                pay_status = "Awaiting approval"
            else:
                pay = self.payment_plan(spec)
                if pay is None:
                    pay_status = "Approved - not yet due"
                else:
                    pay_status = "Scheduled" if pay["run_date"] >= NEXT_RUN else "Paid"
            if pay:
                bank = self.bank_on(spec["supplier_id"], pay["run_date"])
                run_id = pay["run_id"]
                self.rows["payments"].append({
                    "payment_id": f"PAY-{pay_seq}", "invoice_id": spec["invoice_id"], "supplier_id": spec["supplier_id"],
                    "payment_run_id": run_id, "method": pay["method"], "run_date": iso(pay["run_date"]),
                    "value_date": iso(pay["value_date"]), "amount": spec["gross_amount"],
                    "bank_detail_id": bank["bank_detail_id"], "sort_code": bank["sort_code"],
                    "account_number": bank["account_number"], "released_by_1": "EMP-002", "released_by_2": "EMP-003",
                    "status": "Scheduled" if pay["run_date"] >= NEXT_RUN else "Settled",
                    "payment_reference": f"THAMESIDE {spec['supplier_invoice_ref']}"[:18]})
                pay_seq += 1
            row = {k: (iso(v) if isinstance(v, D) else v) for k, v in spec.items() if not k.startswith("_")}
            row["payment_status"] = pay_status
            self.rows["invoices"].append(row)
        self.rows["invoices"].sort(key=lambda r: r["invoice_id"])
        self.rows["payments"].sort(key=lambda r: r["payment_id"])
        self.rows["purchase_orders"].sort(key=lambda r: r["po_id"])
        self.rows["goods_received"].sort(key=lambda r: r["grn_id"])
        for po in self.rows["purchase_orders"]:
            if po["status"] == "Open":
                continue
            invoiced = [i for i in self.rows["invoices"] if i["po_id"] == po["po_id"]]
            po["status"] = "Closed" if invoiced and all(i["payment_status"] == "Paid" for i in invoiced) else "Received"
        for i, r in enumerate(self.case_records, start=1):
            r["case_record_id"] = f"CR-{i:03d}"

    def payment_plan(self, spec):
        override = spec.get("_pay")
        if override:
            return override
        run = choose_run(spec["approved_date"], spec["due_date"])
        if run is None or run > NEXT_RUN:
            return None
        if spec["gross_amount"] >= 100000:
            eligible = [r for r in RUNS if r > spec["approved_date"]]
            on_time = [r for r in eligible if r <= spec["due_date"]]
            run = on_time[-1] if on_time else eligible[0]
            return {"run_id": f"CHAPS-{run.strftime('%Y%m%d')}-01", "method": "CHAPS", "run_date": run, "value_date": run}
        return {"run_id": f"BACS-{run.isoformat()}", "method": "BACS", "run_date": run,
                "value_date": uk.bacs_value_date(run)}


# ------------------------------------------------------------------ rules

RULES = [
    ("R-01", "Approval", "Approval limits", "An invoice may be approved only by someone whose approval_policy limit is at least the invoice's gross amount (including VAT)."),
    ("R-02", "Approval", "Approval scope", "A Budget Holder approves only invoices charged to a cost centre they hold. A Department Head approves only invoices for cost centres in their department. The Finance Director and Chief Financial Officer may approve for any cost centre."),
    ("R-03", "Approval", "Very large invoices", "An invoice above £250,000 needs the Chief Financial Officer and the Chief Executive Officer to approve it."),
    ("R-04", "Purchasing", "No purchase order, no payment", "Every invoice needs a purchase order raised before the goods or services are ordered, except invoices coded to a nominal code with po_required = 0 (legal fees 6210 and tax advisory 6230)."),
    ("R-05", "Purchasing", "Three-way match", "Before payment, an invoice must match its purchase order and a goods receipt: invoiced quantity may not exceed the quantity accepted, and invoiced net amount may not exceed the order's net value. Differences must be resolved with the supplier or covered by an approved order variation."),
    ("R-06", "Segregation of duties", "Orderer cannot approve", "The person who raised a purchase order may not approve an invoice against it."),
    ("R-07", "Supplier bank details", "Bank-detail changes", "A new or changed bank account must be verified, before the first payment, by calling the supplier back on the number already on file. The verifier must be a different person from the one who logged the change. A Confirmation of Payee result other than Match must be resolved before payment."),
    ("R-08", "Approval", "No splitting", "A purchase may not be split into several orders or invoices to keep each below an approval limit. Related invoices from one supplier for one cost centre within 14 days are treated as one purchase for approval purposes."),
    ("R-09", "Payments", "Payment methods", "Suppliers are paid by BACS in runs on Tuesdays and Thursdays. BACS money arrives two working days after the run. Faster Payments are used only for urgent payments approved by the Finance Director. Payments of £100,000 or more go by CHAPS, which arrives the same day."),
    ("R-10", "Payments", "Payment timing", "An approved invoice is paid in the latest BACS run whose arrival date is on or before the due date. If that run has passed, it is paid in the next run."),
    ("R-11", "Payments", "Payment terms", "14 days, 30 days and 60 days run from the invoice date. 30 days EOM runs 30 days from the last day of the invoice month."),
    ("R-12", "Payments", "Dual release", "Each payment needs two releasers in the banking portal: the Finance Director and the Head of Finance Operations."),
    ("R-13", "VAT", "VAT treatment", "Standard-rated supplies carry VAT at 20%. Printed brochures are zero-rated. A supplier that is not VAT-registered charges no VAT. Because most of the group's income is VAT-exempt financial services, it can recover only part of its input VAT: the provisional recovery rate for 2026/27 is 18%."),
    ("R-14", "Invoices", "Duplicate check", "An invoice with the same supplier, amount and invoice date as an earlier one, or a supplier reference that differs only in punctuation or spacing, must be checked as a possible duplicate before approval."),
    ("R-15", "Month-end", "Accruals", "At month-end, goods and services received but not yet invoiced are accrued at the purchase order's net value. The accrual reverses on the first day of the next month."),
    ("R-16", "Suppliers", "Approved suppliers only", "Payments may be made only to suppliers with status Approved."),
]

RULE_TABLES = {
    "R-01": "invoices, employees, approval_policy", "R-02": "invoices, employees, cost_centres",
    "R-03": "invoices, employees", "R-04": "invoices, purchase_orders, nominal_codes",
    "R-05": "invoices, purchase_orders, goods_received", "R-06": "invoices, purchase_orders",
    "R-07": "supplier_bank_details, payments", "R-08": "invoices, purchase_orders",
    "R-09": "payments", "R-10": "invoices, payments", "R-11": "suppliers, invoices",
    "R-12": "payments, employees", "R-13": "invoices, vat_codes", "R-14": "invoices",
    "R-15": "accruals, purchase_orders, goods_received", "R-16": "suppliers, payments",
}

# ------------------------------------------------------------------ cases (descriptions; ids filled in build)


def record_cases(b, P, inv):
    """inv maps a planted spec to its invoice row."""
    rows = b.rows
    pay_by_inv = {p["invoice_id"]: p for p in rows["payments"]}
    bank = {(x["supplier_id"], x["version"]): x for x in rows["supplier_bank_details"]}
    sid = {k: v["supplier_id"] for k, v in b.sup.items()}

    def I(spec):
        return inv[id(spec)]["invoice_id"]

    def pay(spec):
        return pay_by_inv[I(spec)]["payment_id"]

    a, c = P["dup_orig"], P["dup_copy"]
    b.case("CASE-01", "Duplicate invoice with reformatted reference", "duplicate_invoice", "Genuine exception", "High",
           "R-14, R-05",
           f"Kestrelgate IT Services invoice KIT-24817 (£{a['gross_amount']:,.2f}) was registered on {iso(a['received_date'])} and paid. The same invoice arrived again on {iso(c['received_date'])} as KIT24817, without the hyphen, and was registered, approved and scheduled for payment. Same supplier, date, amount and purchase order.",
           "Remove the second invoice from the 1 October payment run, cancel it, and ask Kestrelgate to confirm in writing that it was a resend.",
           """SELECT a.invoice_id FROM invoices a JOIN invoices b ON a.supplier_id = b.supplier_id AND a.invoice_id <> b.invoice_id
              AND a.gross_amount = b.gross_amount
              AND upper(replace(replace(replace(a.supplier_invoice_ref,'-',''),'/',''),' ','')) = upper(replace(replace(replace(b.supplier_invoice_ref,'-',''),'/',''),' ',''))""",
           [("invoices", I(a), "original", 1), ("invoices", I(c), "duplicate", 1),
            ("payments", pay(a), "payment of original", 0), ("payments", pay(c), "scheduled duplicate payment", 0)])

    sp = P["split5"]
    total = sum(x["gross_amount"] for x in sp)
    b.case("CASE-02", "Invoice splitting under the £5,000 limit", "split_invoices", "Genuine exception", "Medium",
           "R-08, R-01",
           f"Three Tallis Lane Training invoices for interview-skills workshops, dated within four days, each just under £5,000 and each approved by the Talent Acquisition Manager (limit £5,000). Together they total £{total:,.2f}, which needed Department Head approval. The three orders were raised on the same day.",
           "Refer to the Head of People for retrospective approval and remind the budget holder of the splitting rule.",
           """SELECT i.invoice_id FROM invoices i JOIN employees e ON e.employee_id = i.approver_id
              JOIN approval_policy p ON p.business_role = e.business_role
              WHERE p.approval_limit_gbp = 5000 AND i.gross_amount >= 0.9 * p.approval_limit_gbp AND i.gross_amount <= p.approval_limit_gbp
              AND EXISTS (SELECT 1 FROM invoices j WHERE j.invoice_id <> i.invoice_id AND j.supplier_id = i.supplier_id
                AND j.approver_id = i.approver_id AND abs(julianday(j.invoice_date) - julianday(i.invoice_date)) <= 14
                AND j.gross_amount >= 0.9 * p.approval_limit_gbp AND j.gross_amount <= p.approval_limit_gbp)""",
           [("invoices", I(x), f"split part {n + 1}", 1) for n, x in enumerate(sp)])

    vb, fb = bank[(sid["velloway"], "V1")], bank[(sid["fleetwood"], "V1")]
    b.case("CASE-03", "New supplier shares another supplier's bank account", "shared_bank_account", "Genuine exception",
           "High", "R-07",
           f"Velloway Technology Ltd was set up through the supplier portal on 17 August 2026. Its bank details (sort code {vb['sort_code']}, account {vb['account_number']}) are the same as Fleetwood Hart Search Ltd's, a long-standing supplier. The details were self-certified, not verified by call-back, and Confirmation of Payee was not run. Two Velloway invoices have been paid into that account.",
           "Stop further payments to Velloway, contact Fleetwood Hart on the number on file, and refer to the financial crime team. A shared account is a risk indicator, not proof of fraud.",
           """SELECT b.bank_detail_id FROM supplier_bank_details b WHERE EXISTS (SELECT 1 FROM supplier_bank_details c
              WHERE c.sort_code = b.sort_code AND c.account_number = b.account_number AND c.supplier_id <> b.supplier_id)""",
           [("supplier_bank_details", vb["bank_detail_id"], "new supplier's account", 1),
            ("supplier_bank_details", fb["bank_detail_id"], "existing supplier's account", 1),
            ("suppliers", sid["velloway"], "new supplier", 0)]
           + [("invoices", I(x), "invoice from new supplier", 0) for x in P["shared"]]
           + [("payments", pay(x), "payment into shared account", 0) for x in P["shared"] if I(x) in pay_by_inv])

    o = P["over_po"]
    b.case("CASE-04", "Invoice exceeds purchase order and goods receipt", "invoice_exceeds_po", "Genuine exception",
           "Medium", "R-05",
           f"Brindlemoor Consulting billed 24 consultant days (net £{o['net_amount']:,.2f}) against a purchase order for 20 days (net £18,000.00). The service confirmation records 20 days delivered. The invoice was approved without an order variation.",
           "Hold payment of the excess 4 days, ask Brindlemoor for a credit note or evidence of agreed extra days, and raise an order variation if the days were genuinely agreed.",
           "SELECT i.invoice_id FROM invoices i JOIN purchase_orders p ON p.po_id = i.po_id WHERE i.net_amount > p.po_value_net",
           [("invoices", I(o), "over-billed invoice", 1), ("purchase_orders", o["po_id"], "original order", 0)])

    nb = P["new_bank"]
    cv2 = bank[(sid["cobaltline"], "V2")]
    to_new = [p for p in rows["payments"] if p["bank_detail_id"] == cv2["bank_detail_id"]]
    others = [p for p in to_new if p["invoice_id"] != I(nb)]
    more = ""
    if others:
        if len(others) == 1:
            o1 = others[0]
            more = (f" A further payment of £{o1['amount']:,.2f} went to the same account in the "
                    f"{D.fromisoformat(o1['run_date']).strftime('%-d %B')} BACS run.")
        else:
            more = (f" A further {len(others)} payments totalling £{sum(p['amount'] for p in others):,.2f} went to the "
                    f"same account in later BACS runs.")
    b.case("CASE-05", "Payment to bank details changed days earlier without call-back", "bank_detail_change",
           "Genuine exception", "High", "R-07, R-09",
           f"An email on 14 September 2026 asked to move Cobaltline Networks' payments to a new Starling Bank account. The same assistant logged the change and 'verified' it by replying to the email, and Confirmation of Payee returned No match. Two days later £{nb['gross_amount']:,.2f} was sent to the new account by Faster Payments rather than in a BACS run. The invoice itself was registered while the old account was on file.{more}",
           "Call Cobaltline on the number on file to confirm whether it asked for the change. If not, ask the bank to recall the payments, report them as authorised push payment fraud, and restore the previous details.",
           """SELECT pm.payment_id FROM payments pm JOIN supplier_bank_details b ON b.bank_detail_id = pm.bank_detail_id
              WHERE b.version <> 'V1' AND julianday(pm.run_date) - julianday(b.effective_from) BETWEEN 0 AND 30
              AND (b.verification_method NOT LIKE 'Call-back%' OR b.verified_by = b.change_logged_by OR b.cop_result <> 'Match')""",
           [("payments", p["payment_id"], "payment to new account", 1) for p in to_new]
           + [("supplier_bank_details", cv2["bank_detail_id"], "changed bank details", 0),
              ("invoices", I(nb), "invoice paid by Faster Payments", 0)])

    ng = P["no_grn"]
    b.case("CASE-06", "Invoice approved for payment with no goods receipt", "missing_goods_receipt", "Genuine exception", "Low",
           "R-05",
           "Quayguard Security billed 105 hours of event security against a purchase order, but no goods receipt or service confirmation exists for the order. The invoice was approved by the budget holder without one.",
           "Ask the Facilities Manager to confirm the hours were worked, using sign-in sheets, and record a service confirmation.",
           "SELECT i.invoice_id FROM invoices i WHERE i.po_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM goods_received g WHERE g.po_id = i.po_id)",
           [("invoices", I(ng), "invoice without receipt", 1), ("purchase_orders", ng["po_id"], "order never receipted", 0)])

    ol = P["over_limit"]
    b.case("CASE-07", "Invoice approved above the approver's limit", "approval_over_limit", "Genuine exception",
           "Medium", "R-01",
           f"A Brookmill Electrical invoice for £{ol['gross_amount']:,.2f} was approved by the Facilities Manager, Canary Wharf, a Budget Holder with a £5,000 limit. The purchase order was correctly approved by the Head of Facilities and Property, but the invoice was not routed to her.",
           "Obtain retrospective approval from the Head of Facilities and Property and check the workflow routing rule.",
           """SELECT i.invoice_id FROM invoices i JOIN employees e ON e.employee_id = i.approver_id
              JOIN approval_policy p ON p.business_role = e.business_role
              WHERE i.approval_status = 'Approved' AND i.gross_amount > p.approval_limit_gbp""",
           [("invoices", I(ol), "invoice approved over limit", 1)])

    r1, r2 = P["recurring"]
    b.case("CASE-08", "Monthly cleaning invoices with identical amounts", "recurring_lookalike", "Benign lookalike",
           "None", "R-14",
           "Wapping Facilities sends one cleaning invoice a month for a fixed fee, so the August and September invoices have the same amount and cost centre. They have different references, dates, service periods and purchase orders. They are not duplicates.",
           "No action. A duplicate check should clear them by comparing service period and reference.",
           """SELECT a.invoice_id FROM invoices a JOIN invoices b ON a.supplier_id = b.supplier_id AND a.invoice_id <> b.invoice_id
              AND a.gross_amount = b.gross_amount AND a.service_period <> b.service_period""",
           [("invoices", I(r1), "August invoice", 1), ("invoices", I(r2), "September invoice", 1)])

    lg = P["large"]
    b.case("CASE-09", "Large audit fee paid by CHAPS", "large_payment_lookalike", "Benign lookalike", "None",
           "R-01, R-09",
           f"Pemberton Ashdown LLP's interim audit fee of £{lg['gross_amount']:,.2f} is by far the largest invoice. It has a purchase order raised by the Financial Controller, a service confirmation, approval by the Chief Financial Officer within her £250,000 limit, and payment by CHAPS as required for amounts of £100,000 or more.",
           "No action. The size is unusual but every control was followed.",
           "SELECT invoice_id FROM invoices WHERE gross_amount >= 100000",
           [("invoices", I(lg), "large invoice", 1), ("payments", pay(lg), "CHAPS payment", 0)])

    nv2 = bank[(sid["northcote"], "V2")]
    nb_pay = [p for p in rows["payments"] if p["bank_detail_id"] == nv2["bank_detail_id"]]
    b.case("CASE-10", "Bank-detail change verified by call-back", "verified_bank_change", "Benign lookalike", "None",
           "R-07",
           "Northcote Data Systems moved its account to HSBC UK by letter. The Procurement Officer logged the change and the Head of Finance Operations verified it by calling the number on file before it took effect. Confirmation of Payee returned Match. The next payment went to the new account.",
           "No action. This is how a bank-detail change should be handled.",
           """SELECT pm.payment_id FROM payments pm JOIN supplier_bank_details b ON b.bank_detail_id = pm.bank_detail_id
              WHERE b.version <> 'V1' AND julianday(pm.run_date) - julianday(b.effective_from) BETWEEN 0 AND 30
              AND b.verification_method LIKE 'Call-back%' AND b.verified_by <> b.change_logged_by AND b.cop_result = 'Match'""",
           [("payments", p["payment_id"], "payment to new account", 1) for p in nb_pay]
           + [("supplier_bank_details", nv2["bank_detail_id"], "changed bank details", 0)])

    s2 = P["split25"]
    total = sum(x["gross_amount"] for x in s2)
    b.case("CASE-11", "Invoice splitting under the £25,000 limit", "split_invoices", "Genuine exception", "Medium",
           "R-08, R-01",
           f"Quillmark Digital billed a data platform discovery project as two phases, a week apart, each just under £25,000 and each approved by the Head of Technology (limit £25,000). Together they total £{total:,.2f}, which needed Finance Director approval. Both orders were raised on 1 September.",
           "Refer to the Finance Director for retrospective approval and review whether the project was scoped as one purchase.",
           """SELECT i.invoice_id FROM invoices i JOIN employees e ON e.employee_id = i.approver_id
              JOIN approval_policy p ON p.business_role = e.business_role
              WHERE p.approval_limit_gbp = 25000 AND i.gross_amount >= 0.9 * p.approval_limit_gbp AND i.gross_amount <= p.approval_limit_gbp
              AND EXISTS (SELECT 1 FROM invoices j WHERE j.invoice_id <> i.invoice_id AND j.supplier_id = i.supplier_id
                AND j.approver_id = i.approver_id AND abs(julianday(j.invoice_date) - julianday(i.invoice_date)) <= 14
                AND j.gross_amount >= 0.9 * p.approval_limit_gbp AND j.gross_amount <= p.approval_limit_gbp)""",
           [("invoices", I(x), f"phase {n + 1}", 1) for n, x in enumerate(s2)])

    sd = P["sod"]
    b.case("CASE-12", "Orderer approved the invoice for their own order", "segregation_of_duties", "Genuine exception",
           "Low", "R-06",
           "The Office Services Manager, Croydon raised the purchase order for printed brochures and then approved the supplier's invoice against it. The amount is within her limit, so only the segregation rule is broken.",
           "Have the Head of Facilities and Property review the invoice, and block self-approval in the workflow.",
           "SELECT i.invoice_id FROM invoices i JOIN purchase_orders p ON p.po_id = i.po_id WHERE i.approver_id = p.raised_by",
           [("invoices", I(sd), "self-approved invoice", 1), ("purchase_orders", sd["po_id"], "order raised by approver", 0)])


def _long_date(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def business_story(rows):
    """The firm's current situation. Paragraphs are separated by blank lines; lines starting '- ' are list items.
    Every figure is calculated from the rows, so the story always matches the data."""
    inv = rows["invoices"]
    pays = rows["payments"]
    settled = [p for p in pays if p["status"] == "Settled"]
    scheduled = [p for p in pays if p["status"] == "Scheduled"]
    unapproved = [i for i in inv if i["approval_status"] != "Approved"]
    received = sorted(i["received_date"] for i in inv)
    approved_suppliers = sum(1 for s_ in rows["suppliers"] if s_["status"] == "Approved")
    gbp = lambda x: f"£{x:,.2f}"  # noqa: E731
    total = lambda xs, k: sum(x[k] for x in xs)  # noqa: E731
    return "\n".join([
        f"{firm.FIRM_NAME} is a mid-sized London financial-services group of about 650 staff. Its head office is in the "
        f"City, operations are at Canary Wharf, and finance and service teams are in Croydon. The group buys IT, consultancy, "
        f"facilities, recruitment and professional services from {approved_suppliers} approved suppliers.",
        "",
        "2026 has been a year of change for the finance function:",
        "- Cost pressure. In January the board set a target to cut third-party spend by 8% this year. Budget holders are "
        "reviewing every order, and new spending gets more scrutiny than before.",
        "- Accounts payable moved to Croydon. In March, invoice processing moved from the City to the Croydon service centre "
        "under the Head of Finance Operations. An experienced assistant left in June. Their replacement joined in July and "
        "is still being trained. Until then, the Senior Accounts Payable Assistant covered both roles.",
        "- New systems. A new invoice-approval workflow went live in July and routes each invoice to an approver "
        "automatically. In August the group opened a supplier portal, where new suppliers can register and enter their own details.",
        "- A major project. Technology is running a data platform programme approved last autumn, delivered with outside "
        "consultancy support.",
        "- Year-end audit. The external auditors did their interim fieldwork in August and September, ahead of the "
        "31 December year end.",
        "",
        f"The Finance Director asked for a review of all supplier invoices received in August and September before the "
        f"audit's final phase. This extract is that review's starting point. It covers {len(inv)} invoices worth "
        f"{gbp(total(inv, 'gross_amount'))}, received between {_long_date(D.fromisoformat(received[0]))} and "
        f"{_long_date(D.fromisoformat(received[-1]))}:",
        f"- {len(settled)} payments totalling {gbp(total(settled, 'amount'))} have been made.",
        f"- {len(scheduled)} payments totalling {gbp(total(scheduled, 'amount'))} are scheduled for Thursday 1 October.",
        f"- {len(unapproved)} invoices worth {gbp(total(unapproved, 'gross_amount'))} are not yet approved.",
    ])


def build(rng):
    b = Builder(rng)
    b.lookups()
    b.suppliers()
    b.bank_details()
    P = b.plant()
    planted = list(b.inv_specs)
    for spec in planted:
        spec["_normal"] = False
    # Case 05: urgent Faster Payment to the new account, outside the run.
    P["new_bank"]["_pay"] = {"run_id": "FPS-20260916-03", "method": "Faster Payments", "run_date": D(2026, 9, 16),
                             "value_date": D(2026, 9, 16)}
    b.normal_volume(100)
    b.uninvoiced_orders()
    b.finalise()
    inv = {id(spec): row for spec, row in zip(
        sorted(b.inv_specs, key=lambda x: x["invoice_id"]), b.rows["invoices"])}
    record_cases(b, P, inv)
    for c in b.cases:
        c["appraisal_types"] = APPRAISAL[c["case_id"]]
    rules = [{"rule_id": r, "category": c, "title": t, "statement": s,
              "related_tables": RULE_TABLES[r]} for r, c, t, s in RULES]
    facts = [
        ("dataset", "procurement"),
        ("title", "Procurement fraud and accounts payable"),
        ("firm", firm.FIRM_NAME),
        ("scenario", "The finance team pays suppliers for IT, consultancy, facilities, recruitment and professional services."),
        ("period", "Invoices received 2026-08-01 to 2026-09-30"),
        ("extract_date", EXTRACT_DATE.isoformat()),
        ("currency", "GBP"),
        ("seed", firm.SEED),
        ("disclaimer", firm.DISCLAIMER),
        ("business_context", business_story(b.rows)),
    ]
    return SCHEMA, dict(b.rows), facts, rules, b.cases, b.case_records


# ------------------------------------------------------------------ checks


def checks(con):
    errors = []
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731

    ranges = {"invoices": (100, 100), "suppliers": (28, 36), "supplier_bank_details": (30, 42),
              "purchase_orders": (70, 125), "goods_received": (70, 120), "employees": (18, 24),
              "cost_centres": (10, 14), "approval_policy": (6, 10), "payments": (40, 100), "accruals": (5, 12)}
    for t, (lo, hi) in ranges.items():
        n = q(f"SELECT count(*) FROM {t}")[0][0]
        if not lo <= n <= hi:
            errors.append(f"{t}: {n} rows, expected {lo}-{hi}")

    for inv, net, code, vat, gross, rate in q(
            "SELECT invoice_id, net_amount, i.vat_code, vat_amount, gross_amount, rate FROM invoices i JOIN vat_codes v USING (vat_code)"):
        if abs(round(net * rate, 2) - vat) > 0.005 or abs(net + vat - gross) > 0.005:
            errors.append(f"{inv}: VAT or gross wrong for code {code}")
    for inv, qty, price, net in q("SELECT invoice_id, quantity, unit_price, net_amount FROM invoices"):
        if abs(round(qty * price, 2) - net) > 0.005:
            errors.append(f"{inv}: quantity x price != net")

    for sid, vat, cn, pc, phone in q("SELECT supplier_id, vat_number, company_number, postcode, contact_phone FROM suppliers"):
        if vat and not uk.vat_valid(vat):
            errors.append(f"{sid}: VAT number {vat} fails check digits")
        if not uk.COMPANY_NO_RE.match(cn):
            errors.append(f"{sid}: company number {cn}")
        if not uk.POSTCODE_RE.match(pc):
            errors.append(f"{sid}: postcode {pc}")
        if not phone.startswith(("020 7946 0", "0131 496 0")):
            errors.append(f"{sid}: phone {phone} outside the Ofcom drama range")
    for bid, sc, acct, iban_ in q("SELECT bank_detail_id, sort_code, account_number, iban FROM supplier_bank_details"):
        if not uk.SORT_CODE_RE.match(sc) or len(acct) != 8 or not acct.isdigit():
            errors.append(f"{bid}: sort code or account number format")
        if not uk.iban_valid(iban_) or iban_[8:] != sc.replace("-", "") + acct:
            errors.append(f"{bid}: IBAN {iban_} invalid or does not match account")

    for pid, method, run, value in q("SELECT payment_id, method, run_date, value_date FROM payments"):
        r, v = D.fromisoformat(run), D.fromisoformat(value)
        if not (uk.is_working_day(r) and uk.is_working_day(v)):
            errors.append(f"{pid}: payment on a non-working day")
        if method == "BACS" and (r.weekday() not in (1, 3) or v != uk.bacs_value_date(r)):
            errors.append(f"{pid}: BACS run not Tue/Thu or value date wrong")
    for pid, amount, gross in q("SELECT payment_id, amount, gross_amount FROM payments JOIN invoices USING (invoice_id)"):
        if abs(amount - gross) > 0.005:
            errors.append(f"{pid}: payment amount differs from invoice")
    for sid, ref, n in q("SELECT supplier_id, supplier_invoice_ref, count(*) FROM invoices GROUP BY 1, 2 HAVING count(*) > 1"):
        errors.append(f"{sid}: supplier reference {ref} used {n} times")
    for sid, ref1, ref2 in q("""SELECT a.supplier_id, a.supplier_invoice_ref, b.supplier_invoice_ref FROM invoices a JOIN invoices b
                               ON a.supplier_id = b.supplier_id AND a.invoice_date < b.invoice_date
                               AND length(a.supplier_invoice_ref) = length(b.supplier_invoice_ref)
                               AND a.supplier_invoice_ref > b.supplier_invoice_ref"""):
        errors.append(f"{sid}: reference {ref1} is later than {ref2} but dated earlier")
    for inv, rd in q("SELECT invoice_id, received_date FROM invoices"):
        if not PERIOD_START.isoformat() <= rd <= EXTRACT_DATE.isoformat():
            errors.append(f"{inv}: received {rd} outside the period")

    # Staff must match the firm-wide register.
    cur = con.execute("SELECT employee_id, first_name, last_name, job_title, office FROM employees")
    cols = [d[0] for d in cur.description]
    errors += staff_register.check([dict(zip(cols, r)) for r in cur.fetchall()], "employee_id", STAFF_REGISTER_IDS)

    # The business story's claims must hold in the data.
    start = q("SELECT start_date, job_title FROM employees WHERE employee_id = ?", NEW_AP_ASSISTANT)[0]
    if start[0] != NEW_AP_START.isoformat() or "Accounts Payable" not in start[1]:
        errors.append("story: the replacement accounts payable assistant must have joined in July 2026")
    for (d,) in q("SELECT start_date FROM employees"):
        if not uk.is_working_day(D.fromisoformat(d)):
            errors.append(f"staff start date {d} is not a working day")
    for bid, d in q("SELECT bank_detail_id, effective_from FROM supplier_bank_details WHERE change_channel = 'Supplier portal'"):
        if d < PORTAL_OPENED.isoformat():
            errors.append(f"story: {bid} came through the supplier portal before it opened in August 2026")
    if q("SELECT office FROM employees WHERE business_role = 'Head of Finance Operations'")[0][0] != "Croydon":
        errors.append("story: the Head of Finance Operations must be based in Croydon")
    if q("SELECT count(*) FROM suppliers WHERE category LIKE '%consultancy%' AND onboarded_date BETWEEN '2025-09-01' AND '2025-12-31'")[0][0] == 0:
        errors.append("story: the data platform programme's consultancy supplier must have been onboarded last autumn")
    if q("SELECT count(*) FROM _truth_cases WHERE appraisal_types IS NULL OR appraisal_types = ''")[0][0]:
        errors.append("every planted case needs its appraisal types")

    # Approval scope (R-02) for every approved invoice not planted as an approval case.
    planted = {r[0] for r in q("SELECT record_id FROM _truth_case_records r JOIN _truth_cases c USING (case_id) "
                               "WHERE c.case_type IN ('approval_over_limit', 'split_invoices')")}
    for inv, cc_id, dept, holder, appr_dept, role in q(
            """SELECT i.invoice_id, i.cost_centre_id, c.department, c.budget_holder_id, e.department, e.business_role
               FROM invoices i JOIN cost_centres c USING (cost_centre_id) JOIN employees e ON e.employee_id = i.approver_id"""):
        if inv in planted:
            continue
        ok = (role in ("Finance Director", "Chief Financial Officer")
              or (role == "Department Head" and appr_dept == dept)
              or (role == "Budget Holder" and q("SELECT 1 FROM invoices WHERE invoice_id = ? AND approver_id = ?", inv, holder)))
        if not ok:
            errors.append(f"{inv}: approver outside scope for {cc_id}")
    return errors
