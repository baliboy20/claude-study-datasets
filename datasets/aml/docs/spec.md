# AML transaction monitoring — dataset specification

> All people, firms, account numbers and events in this dataset are fictional and were generated for study purposes. Formats follow real UK conventions, so an identifier may coincide with a real one by chance. Planted cases are simulated patterns, not allegations. Jurisdictions XA to XD are fictional. Customers and counterparties are identified by reference only. The monitoring rules and risk scores are invented for the study and are not a validated detection model.

This document describes the data and the rules that govern it. It does not reveal which records were planted or why. The answer key is in `planted-cases.md` and in the `_truth_` tables, for reviewers only.

## Business scenario

Thameside Financial Group plc is a mid-sized London financial-services group. Thameside Bank, the group's retail and commercial bank, monitors its customers' payments for signs of money laundering. Monitoring rules raise alerts, which analysts in the financial-crime team review and either close or escalate to the Money Laundering Reporting Officer.

The extract holds 102 payments, worth £1,199,222.97 in all, made into or out of the accounts of 26 customers from Monday 14 to Sunday 20 September 2026, and the 20 alerts they raised. It was taken at 2026-09-22 18:00, so some alerts are closed and others are still open. Each customer's payments for March to August 2026 are summarised by month, to show what is normal for them.

Business question: can an analyst, or an AI, find suspicious patterns across several payments and connected accounts, rather than treating each payment on its own? Can it put the alerts in order of risk, clear innocent ones with reasons, and find patterns that raised no alert at all?

## Business context

Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. It serves personal customers and small businesses across London and the South East. Its financial crime team checks payments against six monitoring rules. Every alert must be reviewed, and either closed with a reason or escalated.

Several pressures have built up this year:
- More alerts than people. Alert numbers rose after the newest rule, rapid movement of funds, was added in June 2025. The team has grown to three analysts, and some are still building experience.
- Faster account opening. In July the bank launched app-based account opening, so personal accounts can now open within minutes.
- Due diligence backlog. Periodic reviews of higher-risk customers fell behind when the due diligence team moved to Croydon.
- New screening system. In August, sanctions screening moved to a new system. The team is still working through records carried over from the old one.
- Board attention. After another bank was fined for weak monitoring, the board asked for assurance that alerts are being handled properly.

The Money Laundering Reporting Officer asked for a review of one week's alerts, raised from 14 to 20 September 2026. The week holds 102 payments worth £1,199,222.97. They raised 20 alerts:
- 6 are closed.
- 4 are under investigation.
- 10 are still open, 6 of them not yet assigned to anyone.

## How monitoring works in the records

1. Each payment into or out of a customer's account is a row in `payments`. A transfer between two Thameside customers is recorded once, as the payer's outbound payment; the payee is the counterparty whose `linked_customer_id` is the receiving customer.
2. The monitoring model gives each payment a `risk_score`. The score does not raise alerts.
3. The rules in `alert_rules` test each payment as it is made. A payment that meets a rule raises one alert per rule in `alerts`. Rule TM-04 runs monthly and had not yet run for September.
4. Analysts work the alerts: `investigation_status`, `assigned_to`, `analyst_decision` and `evidence_reference`. `payments.alert_status` summarises the alerts on each payment.
5. Counterparties are screened against sanctions and watch lists. The result is in `counterparties.screening_status`.
6. Customers have a risk rating, an expected monthly turnover and a periodic review date in `customers`. Their normal activity is in `monthly_activity`.

## People and roles

The financial-crime team's roles are described in `docs/roles.html` in this dataset's folder. The data holds them in `staff`.

| Staff | Name and job title | Team | Office |
|---|---|---|---|
| STF-01 | Hodan Warsame, Money Laundering Reporting Officer | Financial Crime | City |
| STF-02 | Arun Sivakumar, Head of Financial Crime Operations | Financial Crime | Canary Wharf |
| STF-03 | Priya Shah, Transaction Monitoring Manager | Financial Crime | Canary Wharf |
| STF-04 | Hamza Malik, Financial Crime Analyst | Transaction Monitoring | Canary Wharf |
| STF-05 | Elif Mansour, Financial Crime Analyst | Transaction Monitoring | Croydon |
| STF-06 | Yaw Asante, Financial Crime Analyst | Transaction Monitoring | Croydon |
| STF-07 | Layla Demir, Senior Investigator | Financial Crime Investigations | Canary Wharf |
| STF-08 | Kelvin Ng, Sanctions Screening Lead | Sanctions | Canary Wharf |
| STF-09 | Anjali Rao, Customer Due Diligence Team Leader | Customer Due Diligence | Croydon |
| STF-10 | Marek Kowalczyk, Relationship Manager, Business Banking | Business Banking | City |
| STF-11 | Farzana Begum, Relationship Manager, Business Banking | Business Banking | Croydon |

## Tables

| Table | Kind | Rows | Holds |
|---|---|---|---|
| staff | lookup | 11 | People in the financial-crime team and business banking who appear in the records. |
| jurisdictions | lookup | 5 | Countries that payments come from or go to, with the bank's country risk rating. Every country other than the UK is fictional. |
| alert_rules | lookup | 6 | Transaction-monitoring rules, with their thresholds, windows and the severity of the alerts they raise. |
| customers | lookup | 26 | The bank's customers who appear in the payments. Names are withheld; customers are identified by reference. |
| counterparties | lookup | 71 | The other side of each payment: payees and payers. Names are withheld; counterparties are identified by reference. |
| monthly_activity | business | 144 | Each customer's normal pattern: payments in and out of the account per month, March to August 2026. |
| payments | business | 102 | Primary table: every payment into or out of the customers' accounts from Monday 14 to Sunday 20 September 2026. Card purchases and cash are not included. |
| alerts | business | 20 | Alerts raised by the monitoring rules on the week's payments, and the state of each at the extract. |
| _meta_dataset | meta | 12 | Facts about the dataset as a whole: name, period, firm, seed and disclaimer. |
| _meta_tables | meta | 14 | One row per table: what it holds and what kind of table it is. |
| _meta_columns | meta | 0 | Data dictionary: one row per column of every table. |
| _meta_rules | meta | 8 | Business rules and policies that apply to the data. |

The `_truth_` tables (answer key) are left out above.

## Monitoring rules

The monitoring rules and their thresholds are data, in the `alert_rules` table, so every role can see them:

| Rule | Name | Looks for | Threshold | Runs | Severity |
|---|---|---|---|---|---|
| TM-01 | Large payment, personal customer | A single payment of £10,000 or more into or out of a personal customer's account. | £10,000.00 | Real time | Medium |
| TM-02 | New payee, high value | An outbound payment of £5,000 or more to a counterparty first seen in the last 30 days. | £5,000.00 | Real time | Low |
| TM-03 | Rapid movement of funds | An outbound payment of at least 80% of a single credit of £5,000 or more that reached the same account in the previous 24 hours. Credits include internal transfers from other Thameside customers. | £5,000.00 | Real time | High |
| TM-04 | Activity above profile | Money paid into the account in a calendar month is more than twice the customer's expected monthly turnover. |  | Monthly batch, run on the first working day of the next month | Medium |
| TM-05 | High-risk jurisdiction | Any payment of £1,000 or more to or from a jurisdiction rated High. | £1,000.00 | Real time | High |
| TM-06 | Large international business payment | An outbound SWIFT payment of £50,000 or more by a business customer. | £50,000.00 | Real time | Low |

## Control rules

The procedures the financial-crime team must follow are in `_meta_rules` (analyst role and above):

| Rule | Area | Rule | Applies to |
|---|---|---|---|
| R-01 | Alert handling | **Working alerts.** Every alert is assigned to an analyst and decided within 10 working days of being raised. High-severity alerts are worked first. | alerts, alert_rules |
| R-02 | Alert handling | **Closing an alert.** An analyst may close an alert with no further action only with a recorded reason and the evidence relied on, such as an invoice, contract or completion statement. A customer's explanation alone is not evidence. | alerts |
| R-03 | Alert handling | **Connected activity.** Before deciding an alert, the analyst reviews the customer's other payments and alerts for the last 30 days, and those of any counterparty that is also a Thameside customer. Connected alerts are decided together. | alerts, payments, counterparties |
| R-04 | Suspicious activity | **Patterns without an alert.** Rules do not catch every pattern. Several payments kept just below a threshold, funds passed quickly between accounts, or activity far outside the customer's normal pattern are reported to the Money Laundering Reporting Officer even if no alert was raised. | payments, monthly_activity, customers |
| R-05 | Suspicious activity | **Internal reporting.** An analyst who knows or suspects money laundering escalates to the Money Laundering Reporting Officer, who decides whether to make a suspicious activity report to the National Crime Agency. Nobody tells the customer. | alerts, staff |
| R-06 | Sanctions | **Screening before payment.** A payment may be released only to a counterparty whose screening status is Clear or Potential match - discounted. A payment to a counterparty that is Pending or Incomplete is held until screening is complete. | payments, counterparties |
| R-07 | Customer due diligence | **Periodic review.** Customers are reviewed every 12 months if rated High, 24 months if Medium and 36 months if Low. A High-risk customer whose review is overdue is referred to the Customer Due Diligence team, and new alerts on that customer are escalated to a Senior Investigator. | customers, alerts |
| R-08 | Customer due diligence | **Profile.** A customer's expected turnover and expected activity are confirmed at onboarding and each review. Activity well outside them is a reason to ask the customer and to review the risk rating. | customers, monthly_activity, payments |

## Conventions

- Money is in pounds sterling to two decimal places.
- Dates are ISO format, YYYY-MM-DD. Times are UK time, YYYY-MM-DD HH:MM:SS.
- Faster Payments run every day at any hour. BACS, CHAPS and SWIFT run on working days only; BACS credits and debits are posted early in the morning.
- Customers and counterparties are identified by reference only, as monitoring data usually is. No customer or counterparty is a real person or firm.
- The only real country is the United Kingdom (GB). XA, XB, XC and XD are codes the ISO standard leaves free for private use; here they stand for fictional jurisdictions. Nothing in the data describes a real country other than the UK.
- Sanctions screening results are invented. The note that a name resembles an entry on the UK sanctions list refers to no real entry.

Note on the firm's name: no company is registered as Thameside Financial Group or Thameside Bank. Real companies with similar names exist, including Thameside Financial Services Limited and Thameside Financial Planning Limited. The name is set in `generator/common/firm.py` and can be changed there.

## Data dictionary

### staff

People in the financial-crime team and business banking who appear in the records.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| staff_id | TEXT | Staff identifier. |  |
| first_name | TEXT | First name. |  |
| last_name | TEXT | Surname. |  |
| job_title | TEXT | Job title. |  |
| team | TEXT | Team. |  |
| office | TEXT | Office: City, Canary Wharf or Croydon. |  |
| email | TEXT | Work email address. |  |

### jurisdictions

Countries that payments come from or go to, with the bank's country risk rating. Every country other than the UK is fictional.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| country_code | TEXT | Two-letter code. GB is the United Kingdom; XA to XD are user-assigned ISO codes standing for fictional jurisdictions. |  |
| country_name | TEXT | Name. |  |
| risk_rating | TEXT | Country risk in the bank's model: Low, Medium or High. |  |
| notes | TEXT | Why the rating was given. |  |

### alert_rules

Transaction-monitoring rules, with their thresholds, windows and the severity of the alerts they raise.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| rule_id | TEXT | Rule identifier, for example TM-03. |  |
| rule_name | TEXT | Short name. |  |
| description | TEXT | What the rule looks for, in full. |  |
| applies_to | TEXT | Customers and payments the rule tests. |  |
| threshold_gbp | REAL (optional) | Amount at or above which the rule fires. Empty if the rule has no amount threshold. |  |
| window | TEXT (optional) | Time window the rule looks across. Empty if it tests single payments. |  |
| run_frequency | TEXT | Real time (as each payment is made) or the batch schedule. |  |
| severity | TEXT | Severity of the alerts it raises: High, Medium or Low. |  |
| effective_from | TEXT | Date the rule, at this threshold, went live. |  |

### customers

The bank's customers who appear in the payments. Names are withheld; customers are identified by reference.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| customer_id | TEXT | Customer reference, for example CUS-0017. Numbers rise with account opening date. |  |
| segment | TEXT | Personal or Business. |  |
| customer_type | TEXT | Individual, Sole trader, Partnership, Limited liability partnership or Limited company. |  |
| occupation_or_activity | TEXT | Occupation of an individual, or business activity, as declared at onboarding or last review. |  |
| expected_monthly_turnover_gbp | REAL | Expected value of money paid into the account each month, declared at onboarding or last review. |  |
| expected_activity | TEXT | Payments the customer said to expect, recorded at onboarding or last review. |  |
| risk_rating | TEXT | Customer risk rating: Low, Medium or High. |  |
| risk_reason | TEXT (optional) | Main reason for a Medium or High rating. Empty for Low. |  |
| account_opened_date | TEXT | Date the account was opened. |  |
| last_review_date | TEXT | Date of the last customer due-diligence review, or of onboarding if none since. |  |
| next_review_due | TEXT | Date the next periodic review is due. |  |
| postcode_district | TEXT | Outward part of the customer's UK postcode, for example E14. |  |
| relationship_manager_id | TEXT (optional) | Relationship manager, for business customers who have one. | staff.staff_id |

### counterparties

The other side of each payment: payees and payers. Names are withheld; counterparties are identified by reference.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| counterparty_id | TEXT | Counterparty reference, for example CP-008. Numbers rise with the date first seen. |  |
| counterparty_type | TEXT | Individual, Business, Charity, Public body or Financial institution. |  |
| entity_type | TEXT | What the counterparty is, for example Solicitors (SRA-regulated) or Card acquirer. |  |
| country_code | TEXT | Country where the counterparty's account is held. | jurisdictions.country_code |
| relationship | TEXT | How the bank's customers deal with it, for example Employer, Supplier or Family or friend. |  |
| linked_customer_id | TEXT (optional) | The Thameside customer this counterparty is, if it is one. | customers.customer_id |
| first_seen_date | TEXT | Date any Thameside customer first paid or was paid by it. |  |
| screening_status | TEXT | Sanctions and watch-list screening result: Clear, Potential match - discounted, Incomplete or Pending. |  |
| screening_date | TEXT (optional) | Date of the latest screening. Empty if not yet screened. |  |
| screening_notes | TEXT (optional) | Notes from the sanctions team. |  |

### monthly_activity

Each customer's normal pattern: payments in and out of the account per month, March to August 2026.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| activity_id | TEXT | Row identifier. |  |
| customer_id | TEXT | Customer. | customers.customer_id |
| month | TEXT | Calendar month, YYYY-MM. |  |
| credits_count | INTEGER | Number of payments into the account. |  |
| credits_value_gbp | REAL | Value of payments into the account. |  |
| debits_count | INTEGER | Number of payments out of the account. |  |
| debits_value_gbp | REAL | Value of payments out of the account. |  |

### payments

Primary table: every payment into or out of the customers' accounts from Monday 14 to Sunday 20 September 2026. Card purchases and cash are not included.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| payment_id | TEXT | Payment identifier, for example PAY-0042. Numbers rise with time. |  |
| customer_id | TEXT | Thameside customer whose account the payment went into or out of. | customers.customer_id |
| payment_datetime | TEXT | Date and time the payment was made or received, YYYY-MM-DD HH:MM:SS, UK time. |  |
| direction | TEXT | Outbound (paid by the customer) or Inbound (received by the customer). A transfer between two Thameside customers is recorded once, as the payer's outbound payment. |  |
| amount_gbp | REAL | Amount in pounds. |  |
| payment_type | TEXT | Faster Payments, BACS, CHAPS, SWIFT or Internal transfer (between two Thameside accounts). |  |
| counterparty_id | TEXT | The payee of an outbound payment or the payer of an inbound one. | counterparties.counterparty_id |
| channel | TEXT | How the payment was made: Mobile app, Online banking, Business online banking, Bulk payment file, Direct Debit, Branch, Relationship manager, or Inbound payment. |  |
| origin_country | TEXT | Country the money came from. | jurisdictions.country_code |
| destination_country | TEXT | Country the money went to. | jurisdictions.country_code |
| payment_reference | TEXT | Reference entered by the payer. |  |
| risk_score | INTEGER | Score from 1 to 99 given by the bank's monitoring model; higher means riskier. Alerts are raised by the rules in alert_rules, not by the score. |  |
| alert_status | TEXT | No alert; Open (at least one alert on the payment is not closed); or Closed (every alert on it is closed). |  |
| payment_status | TEXT | Completed, or Held - awaiting screening. |  |

### alerts

Alerts raised by the monitoring rules on the week's payments, and the state of each at the extract.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| alert_id | TEXT | Alert identifier. Numbers rise with time. |  |
| payment_id | TEXT | Payment that triggered the alert. | payments.payment_id |
| customer_id | TEXT | Customer the alert is about. | customers.customer_id |
| rule_id | TEXT | Rule that fired. | alert_rules.rule_id |
| raised_datetime | TEXT | When the alert was raised. |  |
| severity | TEXT | High, Medium or Low, from the rule. |  |
| investigation_status | TEXT | Open - unassigned, Open - assigned, Under investigation, or Closed - no further action. |  |
| assigned_to | TEXT (optional) | Analyst working the alert. Empty if unassigned. | staff.staff_id |
| analyst_decision | TEXT (optional) | The analyst's decision and reason. Empty until decided. |  |
| decision_date | TEXT (optional) | Date of the decision. Empty until decided. |  |
| evidence_reference | TEXT (optional) | Document the analyst relied on, if any. |  |

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
| spec.md | 2.2 | 2026-10-20 | Describes the data, how monitoring works and its rules for any reader. Contains no answers | AML transaction monitoring |
