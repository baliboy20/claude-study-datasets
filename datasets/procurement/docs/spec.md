# Procurement fraud and accounts payable — dataset specification

> All people, firms, account numbers and events in this dataset are fictional and were generated for study purposes. Formats follow real UK conventions, so an identifier may coincide with a real one by chance. Planted cases are simulated patterns, not allegations.

This document describes the data and the rules that govern it. It does not reveal which records were planted or why. The answer key is in `planted-cases.md` and in the `_truth_` tables, for reviewers only.

## Business question

Can an analyst, or an AI, find suspicious payment patterns by joining invoices, purchase orders, goods receipts, approvals, bank details and payments? Some patterns are genuine control failures. Others look suspicious but are legitimate.

## Business context

Thameside Financial Group plc is a mid-sized London financial-services group of about 650 staff. Its head office is in the City, operations are at Canary Wharf, and finance and service teams are in Croydon. The group buys IT, consultancy, facilities, recruitment and professional services from 31 approved suppliers.

2026 has been a year of change for the finance function:
- Cost pressure. In January the board set a target to cut third-party spend by 8% this year. Budget holders are reviewing every order, and new spending gets more scrutiny than before.
- Accounts payable moved to Croydon. In March, invoice processing moved from the City to the Croydon service centre under the Head of Finance Operations. An experienced assistant left in June. Their replacement joined in July and is still being trained. Until then, the Senior Accounts Payable Assistant covered both roles.
- New systems. A new invoice-approval workflow went live in July and routes each invoice to an approver automatically. In August the group opened a supplier portal, where new suppliers can register and enter their own details.
- A major project. Technology is running a data platform programme approved last autumn, delivered with outside consultancy support.
- Year-end audit. The external auditors did their interim fieldwork in August and September, ahead of the 31 December year end.

The Finance Director asked for a review of all supplier invoices received in August and September before the audit's final phase. This extract is that review's starting point. It covers 100 invoices worth £760,921.45, received between 3 August 2026 and 30 September 2026:
- 60 payments totalling £500,748.06 have been made.
- 23 payments totalling £185,592.00 are scheduled for Thursday 1 October.
- 17 invoices worth £74,581.39 are not yet approved.

## How a purchase flows through the records

1. A Procurement Officer or budget holder raises a purchase order (`purchase_orders`). Someone else approves it.
2. The goods arrive or the service is delivered. The budget holder records a goods receipt (`goods_received`).
3. The supplier's invoice arrives. Accounts payable registers it (`invoices`) and matches it to the order and the receipt.
4. The invoice is routed to an approver according to the delegated authority (`approval_policy`).
5. Approved invoices are paid in the BACS run that gets the money to the supplier by the due date (`payments`). Each run is released by two people.
6. Supplier bank accounts are kept in versions (`supplier_bank_details`). A change creates a new version, which must be verified by calling the supplier back.
7. At month-end, goods received but not yet invoiced are accrued (`accruals`).

## People and roles

The business roles, approval limits and separation-of-duties rules are agreed in `docs/roles.html` in this dataset's folder. The data holds them in `employees`, `cost_centres` and `approval_policy`.

| Employee | Job title | Business role | Department | Office |
|---|---|---|---|---|
| EMP-001 | Ioana Dumitru, Chief Financial Officer | Chief Financial Officer | Finance | City |
| EMP-002 | Usman Khan, Finance Director | Finance Director | Finance | City |
| EMP-003 | Philippa Hendry, Head of Finance Operations | Head of Finance Operations | Finance | Croydon |
| EMP-004 | Yusuf Haddad, Accounts Payable Assistant | Accounts Payable Assistant | Finance | Croydon |
| EMP-005 | Sarah Barker, Senior Accounts Payable Assistant | Accounts Payable Assistant | Finance | Croydon |
| EMP-006 | Jermaine Grant, Procurement Officer | Procurement Officer | Finance | Canary Wharf |
| EMP-007 | Joanne Fairbairn, Senior Procurement Officer | Procurement Officer | Finance | City |
| EMP-008 | James Ellison, Head of Technology | Department Head | Technology | Canary Wharf |
| EMP-009 | Natalie Bailey, IT Service Delivery Manager | Budget Holder | Technology | Canary Wharf |
| EMP-010 | Stephen Rowe, Infrastructure Manager | Budget Holder | Technology | Canary Wharf |
| EMP-011 | Neha Iyer, Head of Facilities and Property | Department Head | Facilities | City |
| EMP-012 | Tunde Okonkwo, Facilities Manager, Canary Wharf | Budget Holder | Facilities | Canary Wharf |
| EMP-013 | Ana Bianchi, Office Services Manager, Croydon | Budget Holder | Facilities | Croydon |
| EMP-014 | Lucy Pike, Head of People | Department Head | People | City |
| EMP-015 | Paul Pham, Talent Acquisition Manager | Budget Holder | People | City |
| EMP-016 | Omar Kaya, General Counsel | Department Head | Legal and Compliance | City |
| EMP-017 | Nicola Harding, Compliance Manager | Budget Holder | Legal and Compliance | City |
| EMP-018 | Grace Lam, Information Security Manager | Budget Holder | Technology | Canary Wharf |
| EMP-019 | Shahid Rahman, Chief Executive Officer | Chief Executive Officer | Executive | City |
| EMP-020 | Ciarán O'Sullivan, Financial Controller | Budget Holder | Finance | City |

## Tables

| Table | Kind | Rows | Holds |
|---|---|---|---|
| vat_codes | lookup | 4 | VAT treatment codes used on invoices. |
| nominal_codes | lookup | 22 | Chart of accounts: general-ledger expense codes. |
| approval_policy | lookup | 9 | Delegated authority: what each business role may approve. |
| employees | lookup | 20 | Staff involved in buying, approving and paying. |
| cost_centres | lookup | 12 | Cost centres that budgets and invoices are charged to. |
| suppliers | business | 32 | Supplier master file. |
| supplier_bank_details | business | 37 | Supplier bank accounts, one row per version. A change creates a new version. |
| purchase_orders | business | 104 | Purchase orders. Each order has a single line. |
| goods_received | business | 98 | Goods receipts and service confirmations against purchase orders. |
| invoices | business | 100 | Supplier invoices registered by accounts payable. This is the primary table. |
| payments | business | 83 | Payments made or scheduled, one per invoice. |
| accruals | business | 8 | Month-end accruals for goods received but not yet invoiced at 30 September 2026. |
| _meta_dataset | meta | 11 | Facts about the dataset as a whole: name, period, firm, seed and disclaimer. |
| _meta_tables | meta | 18 | One row per table: what it holds and what kind of table it is. |
| _meta_columns | meta | 0 | Data dictionary: one row per column of every table. |
| _meta_rules | meta | 16 | Business rules and policies that apply to the data. |

The `_truth_` tables (answer key) are left out above.

## Business rules

| Rule | Area | Rule | Applies to |
|---|---|---|---|
| R-01 | Approval | **Approval limits.** An invoice may be approved only by someone whose approval_policy limit is at least the invoice's gross amount (including VAT). | invoices, employees, approval_policy |
| R-02 | Approval | **Approval scope.** A Budget Holder approves only invoices charged to a cost centre they hold. A Department Head approves only invoices for cost centres in their department. The Finance Director and Chief Financial Officer may approve for any cost centre. | invoices, employees, cost_centres |
| R-03 | Approval | **Very large invoices.** An invoice above £250,000 needs the Chief Financial Officer and the Chief Executive Officer to approve it. | invoices, employees |
| R-04 | Purchasing | **No purchase order, no payment.** Every invoice needs a purchase order raised before the goods or services are ordered, except invoices coded to a nominal code with po_required = 0 (legal fees 6210 and tax advisory 6230). | invoices, purchase_orders, nominal_codes |
| R-05 | Purchasing | **Three-way match.** Before payment, an invoice must match its purchase order and a goods receipt: invoiced quantity may not exceed the quantity accepted, and invoiced net amount may not exceed the order's net value. Differences must be resolved with the supplier or covered by an approved order variation. | invoices, purchase_orders, goods_received |
| R-06 | Segregation of duties | **Orderer cannot approve.** The person who raised a purchase order may not approve an invoice against it. | invoices, purchase_orders |
| R-07 | Supplier bank details | **Bank-detail changes.** A new or changed bank account must be verified, before the first payment, by calling the supplier back on the number already on file. The verifier must be a different person from the one who logged the change. A Confirmation of Payee result other than Match must be resolved before payment. | supplier_bank_details, payments |
| R-08 | Approval | **No splitting.** A purchase may not be split into several orders or invoices to keep each below an approval limit. Related invoices from one supplier for one cost centre within 14 days are treated as one purchase for approval purposes. | invoices, purchase_orders |
| R-09 | Payments | **Payment methods.** Suppliers are paid by BACS in runs on Tuesdays and Thursdays. BACS money arrives two working days after the run. Faster Payments are used only for urgent payments approved by the Finance Director. Payments of £100,000 or more go by CHAPS, which arrives the same day. | payments |
| R-10 | Payments | **Payment timing.** An approved invoice is paid in the latest BACS run whose arrival date is on or before the due date. If that run has passed, it is paid in the next run. | invoices, payments |
| R-11 | Payments | **Payment terms.** 14 days, 30 days and 60 days run from the invoice date. 30 days EOM runs 30 days from the last day of the invoice month. | suppliers, invoices |
| R-12 | Payments | **Dual release.** Each payment needs two releasers in the banking portal: the Finance Director and the Head of Finance Operations. | payments, employees |
| R-13 | VAT | **VAT treatment.** Standard-rated supplies carry VAT at 20%. Printed brochures are zero-rated. A supplier that is not VAT-registered charges no VAT. Because most of the group's income is VAT-exempt financial services, it can recover only part of its input VAT: the provisional recovery rate for 2026/27 is 18%. | invoices, vat_codes |
| R-14 | Invoices | **Duplicate check.** An invoice with the same supplier, amount and invoice date as an earlier one, or a supplier reference that differs only in punctuation or spacing, must be checked as a possible duplicate before approval. | invoices |
| R-15 | Month-end | **Accruals.** At month-end, goods and services received but not yet invoiced are accrued at the purchase order's net value. The accrual reverses on the first day of the next month. | accruals, purchase_orders, goods_received |
| R-16 | Suppliers | **Approved suppliers only.** Payments may be made only to suppliers with status Approved. | suppliers, payments |

## Conventions

- Money is in pounds sterling to two decimal places. Amounts on invoices include VAT unless the column says net.
- Dates are ISO format, YYYY-MM-DD. Bank holidays follow England and Wales.
- Sort codes are NN-NN-NN. Account numbers have eight digits. IBANs and VAT numbers carry valid check digits.
- Phone numbers are in Ofcom's ranges reserved for fiction (020 7946 0xxx, 0131 496 0xxx).
- Companies House numbers follow the real numbering for the incorporation year. They may coincide with real companies.
- Every supplier name and the firm's email domain were checked against the Companies House register and DNS on 20 October 2026. No exact match was found. See the note on the firm's name below.

Note on the firm's name: no company is registered as Thameside Financial Group. Real companies with similar names exist, including Thameside Financial Services Limited and Thameside Financial Planning Limited. The name is set in `generator/common/firm.py` and can be changed there.

## Data dictionary

### vat_codes

VAT treatment codes used on invoices.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| vat_code | TEXT | Code: S standard, Z zero-rated, E exempt, N supplier not VAT-registered. |  |
| description | TEXT | What the code means. |  |
| rate | REAL | VAT rate as a fraction, for example 0.20. |  |

### nominal_codes

Chart of accounts: general-ledger expense codes.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| nominal_code | TEXT | Four-digit ledger code. |  |
| description | TEXT | Expense type. |  |
| po_required | INTEGER | 1 if a purchase order is required before an invoice can be paid (rule R-04). |  |

### approval_policy

Delegated authority: what each business role may approve.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| business_role | TEXT | Business role name, matching employees.business_role. |  |
| approval_limit_gbp | REAL | Largest single invoice, including VAT, the role may approve alone. 0 means the role cannot approve. |  |
| scope | TEXT | Where the authority applies: none, own cost centre, own department or any. |  |
| notes | TEXT | Further conditions. |  |

### employees

Staff involved in buying, approving and paying.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| employee_id | TEXT | Staff number. |  |
| first_name | TEXT | First name. |  |
| last_name | TEXT | Surname. |  |
| job_title | TEXT | Job title. |  |
| business_role | TEXT | Role for approval purposes. | approval_policy.business_role |
| department | TEXT | Department. |  |
| office | TEXT | Office: City, Canary Wharf or Croydon. |  |
| email | TEXT | Work email address. |  |
| start_date | TEXT | Date the person joined. |  |

### cost_centres

Cost centres that budgets and invoices are charged to.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| cost_centre_id | TEXT | Cost centre code. |  |
| name | TEXT | Cost centre name. |  |
| department | TEXT | Department that owns the cost centre. |  |
| budget_holder_id | TEXT | Employee accountable for the budget. | employees.employee_id |
| office | TEXT | Office the cost centre mainly serves. |  |

### suppliers

Supplier master file.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| supplier_id | TEXT | Supplier number. |  |
| supplier_name | TEXT | Registered name. |  |
| legal_form | TEXT | Ltd, LLP or plc. |  |
| company_number | TEXT | Companies House number: 8 digits, or OC for an LLP, SC for a Scottish company. |  |
| incorporated_date | TEXT | Date the company was incorporated. |  |
| vat_number | TEXT (optional) | UK VAT registration number, or empty if not VAT-registered. |  |
| category | TEXT | What the supplier provides. |  |
| default_nominal_code | TEXT | Usual ledger code for this supplier. | nominal_codes.nominal_code |
| address_line_1 | TEXT | Registered address. |  |
| town | TEXT | Town. |  |
| postcode | TEXT | Postcode. |  |
| contact_name | TEXT | Accounts contact at the supplier. |  |
| contact_phone | TEXT | Phone number held on file, used for call-back checks. |  |
| payment_terms | TEXT | 14 days, 30 days, 30 days EOM (30 days after the end of the invoice month) or 60 days. |  |
| onboarded_date | TEXT | Date the supplier was approved for use. |  |
| onboarded_by | TEXT | Employee who set the supplier up. | employees.employee_id |
| status | TEXT | Approved or Inactive. |  |

### supplier_bank_details

Supplier bank accounts, one row per version. A change creates a new version.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| bank_detail_id | TEXT | Bank-detail record number. |  |
| supplier_id | TEXT | Supplier. | suppliers.supplier_id |
| version | TEXT | V1 for the first account, V2 for the first change and so on. |  |
| bank_name | TEXT | Bank. |  |
| account_name | TEXT | Name on the account. |  |
| sort_code | TEXT | Sort code, NN-NN-NN. |  |
| account_number | TEXT | Eight-digit account number. |  |
| iban | TEXT | International account number. |  |
| effective_from | TEXT | First date payments go to this account. |  |
| effective_to | TEXT (optional) | Last date, or empty if current. |  |
| change_channel | TEXT | How the details were received: Onboarding form, Letter, Email or Supplier portal. |  |
| change_logged_by | TEXT | Employee who entered the details. | employees.employee_id |
| verified_by | TEXT (optional) | Employee who verified the details. | employees.employee_id |
| verified_date | TEXT (optional) | Date verified. |  |
| verification_method | TEXT (optional) | How the details were verified. |  |
| cop_result | TEXT | Confirmation of Payee result: Match, Close match, No match or Not checked. |  |

### purchase_orders

Purchase orders. Each order has a single line.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| po_id | TEXT | Purchase order number. |  |
| supplier_id | TEXT | Supplier. | suppliers.supplier_id |
| raised_date | TEXT | Date raised. |  |
| raised_by | TEXT | Employee who raised it. | employees.employee_id |
| approved_by | TEXT | Employee who approved it. | employees.employee_id |
| cost_centre_id | TEXT | Cost centre charged. | cost_centres.cost_centre_id |
| nominal_code | TEXT | Ledger code. | nominal_codes.nominal_code |
| description | TEXT | What was ordered. |  |
| unit | TEXT | Unit of measure, for example day, month or licence. |  |
| quantity | REAL | Quantity ordered. |  |
| unit_price | REAL | Price per unit, excluding VAT. |  |
| po_value_net | REAL | Order value excluding VAT. |  |
| status | TEXT | Open, Received or Closed. |  |

### goods_received

Goods receipts and service confirmations against purchase orders.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| grn_id | TEXT | Goods received note number. |  |
| po_id | TEXT | Purchase order. | purchase_orders.po_id |
| received_date | TEXT | Date goods arrived or the service was confirmed. |  |
| received_by | TEXT | Employee who confirmed receipt. | employees.employee_id |
| quantity_received | REAL | Quantity delivered. |  |
| quantity_accepted | REAL | Quantity accepted. |  |
| status | TEXT | Accepted, Partially accepted or Rejected. |  |
| notes | TEXT (optional) | Receipt notes. |  |

### invoices

Supplier invoices registered by accounts payable. This is the primary table.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| invoice_id | TEXT | Internal invoice number, given on registration. |  |
| supplier_id | TEXT | Supplier. | suppliers.supplier_id |
| supplier_invoice_ref | TEXT | The supplier's own invoice number. |  |
| invoice_date | TEXT | Date on the invoice. |  |
| received_date | TEXT | Date the invoice reached accounts payable. |  |
| due_date | TEXT | Date payment is due under the supplier's terms. |  |
| service_period | TEXT | Month the goods or services relate to, YYYY-MM. |  |
| po_id | TEXT (optional) | Purchase order, if any. | purchase_orders.po_id |
| cost_centre_id | TEXT | Cost centre charged. | cost_centres.cost_centre_id |
| nominal_code | TEXT | Ledger code. | nominal_codes.nominal_code |
| description | TEXT | Invoice description. |  |
| quantity | REAL | Quantity invoiced. |  |
| unit_price | REAL | Price per unit, excluding VAT. |  |
| net_amount | REAL | Amount excluding VAT. |  |
| vat_code | TEXT | VAT treatment. | vat_codes.vat_code |
| vat_amount | REAL | VAT charged. |  |
| gross_amount | REAL | Amount including VAT. |  |
| approver_id | TEXT | Employee the invoice was routed to for approval. | employees.employee_id |
| approved_date | TEXT (optional) | Date approved, if approved. |  |
| approval_status | TEXT | Approved, Awaiting approval or Queried. |  |
| payment_status | TEXT | Paid, Scheduled (in the 1 October run), Approved - not yet due, Awaiting approval or On hold. |  |
| bank_detail_version | TEXT | Supplier bank-detail version on file when the invoice was registered. |  |

### payments

Payments made or scheduled, one per invoice.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| payment_id | TEXT | Payment number. |  |
| invoice_id | TEXT | Invoice paid. | invoices.invoice_id |
| supplier_id | TEXT | Supplier paid. | suppliers.supplier_id |
| payment_run_id | TEXT | Payment run, or an ad hoc payment reference. |  |
| method | TEXT | BACS, Faster Payments or CHAPS. |  |
| run_date | TEXT | Date the payment was released to the bank. |  |
| value_date | TEXT | Date the funds reach the supplier. |  |
| amount | REAL | Amount paid. |  |
| bank_detail_id | TEXT | Bank account the payment was sent to. | supplier_bank_details.bank_detail_id |
| sort_code | TEXT | Sort code paid to. |  |
| account_number | TEXT | Account number paid to. |  |
| released_by_1 | TEXT | First releaser. | employees.employee_id |
| released_by_2 | TEXT | Second releaser. | employees.employee_id |
| status | TEXT | Settled or Scheduled. |  |
| payment_reference | TEXT | Reference shown on the supplier's statement. |  |

### accruals

Month-end accruals for goods received but not yet invoiced at 30 September 2026.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| accrual_id | TEXT | Accrual number. |  |
| period | TEXT | Accounting period, YYYY-MM. |  |
| po_id | TEXT | Purchase order. | purchase_orders.po_id |
| grn_id | TEXT | Goods receipt. | goods_received.grn_id |
| cost_centre_id | TEXT | Cost centre. | cost_centres.cost_centre_id |
| nominal_code | TEXT | Ledger code. | nominal_codes.nominal_code |
| amount_net | REAL | Accrued amount excluding VAT. |  |
| posted_by | TEXT | Employee who posted the accrual. | employees.employee_id |
| reversal_date | TEXT | Date the accrual reverses. |  |

### _meta_dataset

Facts about the dataset as a whole: name, period, firm, seed and disclaimer.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| key | TEXT | Name of the fact. |  |
| value | TEXT | Value of the fact. |  |

### _meta_tables

One row per table: what it holds and what kind of table it is.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| table_name | TEXT | Table name. |  |
| kind | TEXT | business (operational records), lookup (reference data), meta (documentation) or truth (answer key). |  |
| description | TEXT | What the table holds. |  |
| primary_key | TEXT | Column that identifies a row. |  |
| row_count | INTEGER | Number of rows. |  |

### _meta_columns

Data dictionary: one row per column of every table.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| column_key | TEXT | table.column, unique. |  |
| table_name | TEXT | Table the column belongs to. | _meta_tables.table_name |
| column_name | TEXT | Column name. |  |
| position | INTEGER | Order of the column in the table, from 1. |  |
| data_type | TEXT | TEXT, INTEGER or REAL. Money is REAL in pounds with two decimal places. Dates are TEXT in ISO format (YYYY-MM-DD). |  |
| description | TEXT | Meaning of the column. |  |
| references_column | TEXT (optional) | table.column this column points to, if any. |  |
| nullable | INTEGER | 1 if the column may be empty. |  |

### _meta_rules

Business rules and policies that apply to the data.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| rule_id | TEXT | Rule identifier, for example R-04. |  |
| category | TEXT | Area the rule belongs to. |  |
| title | TEXT | Short name of the rule. |  |
| statement | TEXT | The rule in full. |  |
| related_tables | TEXT | Tables the rule applies to. |  |

## Rebuilding and serving

Run from this dataset's folder:

```bash
python3 generator/build.py
```

The build is deterministic: the same code and seed produce byte-identical files. See `api/README.md` for serving the data through the local API.



---

| Document | Version | Date | Purpose | Dataset |
|---|---|---|---|---|
| spec.md | 3.2 | 2026-10-20 | Describes the data, its flow and its rules for any reader. Contains no answers | Procurement fraud and accounts payable |
