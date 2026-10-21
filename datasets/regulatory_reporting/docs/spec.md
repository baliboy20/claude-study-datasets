# Regulatory reporting and data lineage — dataset specification

> All people, firms, account numbers and events in this dataset are fictional and were generated for study purposes. Formats follow real UK conventions, so an identifier may coincide with a real one by chance. Planted cases are simulated patterns, not allegations. The MBSR template, its line codes and the source systems are fictional.

This document describes the data and the rules that govern it. It does not reveal which records were planted or why. The answer key is in `planted-cases.md` and in the `_truth_` tables, for reviewers only.

## Business scenario

Thameside Financial Group plc is a mid-sized London financial-services group. Its regulatory reporting team, in the City, prepares a Monthly Balance Sheet Return (MBSR): lending and deposit balances in nine lines, for two group entities consolidated. The template, its line codes and the source systems are fictional; the process follows real UK practice.

The extract holds 100 reporting records for September 2026, from 4 source systems, with balances at 30 September 2026. The draft return was prepared on 2026-10-06 and awaits review. It is due on 2026-10-15. The submitted August return is included for comparison.

Business question: can an analyst, or an AI, trace a reported figure to its source, explain how it was calculated, and detect changes that could make the return wrong? Some records hide genuine errors. Others look wrong but are correct.

## Business context

Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. Each month it reports its balance sheet to the regulator in the Monthly Balance Sheet Return. A small regulatory reporting team in the City and Croydon prepares the return, drawing on 4 source systems run by Technology and Finance Data.

2026 has brought steady change to the systems and rules behind the return:
- System upgrades. Two source systems had major releases this summer: RetailCredit in August and LendingCore in September. Each release changed how some balances are labelled in the monthly extract.
- A changing return. The bank has revised how its products map to return lines several times. A new line for SME overdrafts and revolving credit came in from April. A further revision, moving buy-to-let lending to limited companies, takes effect from October.
- A shorter timetable. The board asked for earlier month-end figures, so the team now prepares the draft return in four working days instead of eight.
- Annual reference data review. At the end of August, the team updated the size classes it uses to decide whether a business borrower counts as an SME.

The Head of Regulatory Reporting asked for the draft September return to be reviewed before the Chief Financial Officer signs it off. The return is due on 15 October 2026. The draft holds 100 source records across 9 return lines. 96 of them are included in the return, reporting £3,091,736,092.22 in total.

## How a figure flows through the records

1. After end-of-day processing on the period end, each source system writes a month-end extract. The balance is read from the field named in `field_dictionary` (`reporting_records.source_field`).
2. Foreign-currency balances are converted to sterling at the period-end rate in `fx_rates` (`amount_gbp`).
3. Each record's product code is mapped to a return line by the rule in `mapping_rules` in force at the period end (`mapping_rule_id`, `mapping_version`, `line_code`).
4. Records are included or excluded under the inclusion rules in `reporting_rules` (`included_in_return`, `exclusion_reason`). The amount used is `reported_amount_gbp`.
5. Each line in `return_figures` is the sum of its included records.
6. Source totals are reconciled to general-ledger figures in `control_totals`.
7. Every change to fields, mappings and the template is recorded in `change_log` with its effective date.

## People and roles

The reporting team's roles and sign-off are described in `docs/roles.html` in this dataset's folder. The data holds them in `staff`.

| Staff | Name and job title | Team | Office |
|---|---|---|---|
| STF-01 | Ioana Dumitru, Chief Financial Officer | Finance leadership | City |
| STF-02 | João Rossi, Head of Regulatory Reporting | Regulatory Reporting | City |
| STF-03 | Emma Waller, Regulatory Reporting Manager | Regulatory Reporting | City |
| STF-04 | Mihai Ionescu, Regulatory Reporting Analyst | Regulatory Reporting | City |
| STF-05 | Ama Mensah, Regulatory Reporting Analyst | Regulatory Reporting | Croydon |
| STF-06 | Sophie Mistry, Data Governance Lead | Finance Data | Canary Wharf |
| STF-07 | Rahim Ahmed, Finance Systems Analyst | Finance Data | Canary Wharf |
| STF-08 | Gareth Lambert, LendingCore Product Owner | Technology | Canary Wharf |
| STF-09 | Claire Fletcher, Retail Systems Product Owner | Technology | Canary Wharf |
| STF-10 | Ming Cheung, Credit Risk Data Manager | Credit Risk | Croydon |
| STF-11 | Ciarán O'Sullivan, Financial Controller | Finance | City |

## Tables

| Table | Kind | Rows | Holds |
|---|---|---|---|
| staff | lookup | 11 | People in the reporting, data and finance teams who appear in the records. |
| entities | lookup | 3 | Legal entities of the group and whether each is in the scope of the return. |
| source_systems | lookup | 4 | Operational systems that supply balances to the return. |
| products | lookup | 16 | Product codes used by the source systems. |
| return_lines | lookup | 9 | Lines of the Monthly Balance Sheet Return (MBSR) template. |
| counterparties | lookup | 56 | Business customers behind commercial facilities and business deposits. Names are withheld; customers are identified by reference. |
| field_dictionary | lookup | 26 | Source fields the return calculation reads, with definitions, types, valid values and validity dates. |
| change_log | business | 12 | Schema changes, mapping amendments, template changes and reference-data changes, with their effective dates. |
| mapping_rules | lookup | 20 | Versioned rules that map each product code to a return line, with effective dates. |
| reporting_rules | lookup | 8 | The return's own instructions: inclusion criteria, calculation and aggregation. |
| fx_rates | lookup | 4 | Bank of England daily spot rates against sterling, quoted as units of currency per £1. |
| reporting_records | business | 100 | Primary table: one row per source balance feeding the September 2026 return, with its lineage from source field to return line. |
| control_totals | business | 18 | Expected totals from the general ledger by source system, product and currency at the period end. |
| return_figures | business | 18 | The return as reported: one row per line for the submitted August return and the draft September return. |
| _meta_dataset | meta | 12 | Facts about the dataset as a whole: name, period, firm, seed and disclaimer. |
| _meta_tables | meta | 20 | One row per table: what it holds and what kind of table it is. |
| _meta_columns | meta | 0 | Data dictionary: one row per column of every table. |
| _meta_rules | meta | 10 | Business rules and policies that apply to the data. |

The `_truth_` tables (answer key) are left out above.

## Reporting rules

The return's own instructions are data, in the `reporting_rules` table, so every role can see them:

| Rule | Type | Rule | Applies to |
|---|---|---|---|
| RR-01 | Inclusion | Include every record of an in-scope entity with a non-zero balance at the period-end date. | All lines |
| RR-02 | Inclusion | Exclude only: closed accounts with a zero balance, and balances with another group entity (intragroup), which are eliminated on consolidation. Record the reason in exclusion_reason. | All lines |
| RR-03 | Calculation | Balances are taken at close of business on the last calendar day of the period, after end-of-day processing has posted that day's transactions. | All lines |
| RR-04 | Calculation | Convert foreign-currency balances to sterling at the Bank of England spot rate for the period-end date, quoted as units of currency per £1: sterling amount = source amount / rate, rounded to the penny. | All lines |
| RR-05 | Classification | Map each record to a line using the mapping rule for its product code that is in force on the period-end date. | All lines |
| RR-06 | Classification | An SME is a business whose turnover in its latest filed accounts is £25 million or less. Lending to a business above that is reported in L60, and its deposits in D30, whatever product it is booked on. Commercial real estate lending stays in L50 whatever the borrower's size. | L30, L40, L60 |
| RR-07 | Aggregation | Each line is the sum of reported_amount_gbp over included records mapped to it, in pounds to the penny. | All lines |
| RR-08 | Aggregation | Total lending is the sum of L10 to L60. Total deposits is the sum of D10 to D30. | All lines |

## Control rules

The controls the reporting team must follow are in `_meta_rules` (analyst role and above):

| Rule | Area | Rule | Applies to |
|---|---|---|---|
| R-01 | Data definitions | **Field dictionary coverage.** Every source field the return reads must be in field_dictionary and valid on the period-end date. A source-system change that renames or removes a field must be matched by a dictionary update, and the return calculation repointed, before the change goes live. | field_dictionary, reporting_records, change_log |
| R-02 | Mapping | **Mapping in force.** A record must be mapped with the rule for its product that is in force on the period-end date: effective_from on or before it, and effective_to empty or on or after it. | mapping_rules, reporting_records |
| R-03 | Change control | **Logged and approved changes.** Every schema change, mapping amendment and template change is logged in change_log with its effective date, and approved before it takes effect. A change takes effect for the first period-end on or after its effective date. | change_log, mapping_rules |
| R-04 | Reconciliation | **Control totals.** For each source system, product and currency, the sum of source_amount over all records, included or not, must agree with the general-ledger control total within its tolerance. A difference above tolerance must be explained and corrected before the return is reviewed. | control_totals, reporting_records |
| R-05 | Completeness | **Justified exclusions.** A record may be excluded only for a reason allowed by reporting rule RR-02, and its status and balance must support the reason given. | reporting_records, reporting_rules |
| R-06 | Classification | **Customer size.** Counterparty size classes are reviewed each year against filed accounts. Lending booked on an SME product to a large corporate is reported as large corporate lending (RR-06). | counterparties, reporting_records, products |
| R-07 | Calculation | **Exchange rates.** Foreign-currency balances use the rate in fx_rates for the period-end date. A rate from any other date is an error. | fx_rates, reporting_records |
| R-08 | Review | **Movement review.** A line that moves by more than 10% from the previous submitted return must be explained in the review pack before approval. | return_figures |
| R-09 | Sign-off | **Four eyes.** The return is prepared by a Regulatory Reporting Analyst, reviewed by the Regulatory Reporting Manager and approved by the Chief Financial Officer. The preparer may not review. | return_figures, staff |
| R-10 | Timetable | **Submission deadline.** The return is due by the 15th calendar day after the period end, or the next working day. The September 2026 return is due on Thursday 15 October 2026. | return_figures |

## Conventions

- Money is in pounds sterling to two decimal places, except `source_amount` and `control_amount`, which are in the currency named beside them.
- Exchange rates are units of currency per £1, as the Bank of England quotes them. Sterling = currency amount / rate.
- Dates are ISO format, YYYY-MM-DD. A mapping rule's dates are inclusive.
- Customers are identified by reference only. Sectors use UK SIC 2007 sections.
- Group entity names were checked against the Companies House register on 20 October 2026. No company is registered as Thameside Bank or Thameside Commercial Finance.

Note on the firm's name: no company is registered as Thameside Financial Group. Real companies with similar names exist, including Thameside Financial Services Limited and Thameside Financial Planning Limited. The name is set in `generator/common/firm.py` and can be changed there.

## Data dictionary

### staff

People in the reporting, data and finance teams who appear in the records.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| staff_id | TEXT | Staff identifier. |  |
| first_name | TEXT | First name. |  |
| last_name | TEXT | Surname. |  |
| job_title | TEXT | Job title. |  |
| team | TEXT | Team. |  |
| office | TEXT | Office: City, Canary Wharf or Croydon. |  |
| email | TEXT | Work email address. |  |

### entities

Legal entities of the group and whether each is in the scope of the return.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| entity_code | TEXT | Entity code, for example ENT-LON-01. |  |
| entity_name | TEXT | Entity name. |  |
| entity_type | TEXT | What the entity does. |  |
| in_return_scope | INTEGER | 1 if the entity's balances are reported in the consolidated return. |  |
| office | TEXT | Office the entity is run from. |  |

### source_systems

Operational systems that supply balances to the return.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| source_system | TEXT | System name. |  |
| description | TEXT | What the system holds. |  |
| data_owner_id | TEXT | Person accountable for the system's data. | staff.staff_id |
| extract_schedule | TEXT | When the month-end extract is due to run. |  |

### products

Product codes used by the source systems.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| product_code | TEXT | Product code. |  |
| description | TEXT | Product. |  |
| source_system | TEXT | System that holds the product. | source_systems.source_system |
| customer_segment | TEXT | Customers the product is sold to: Household, SME, Large corporate, Property company or Commercial real estate. |  |
| balance_type | TEXT | Asset (lending) or Liability (deposits). |  |
| launched_date | TEXT | Date the product was first sold. |  |

### return_lines

Lines of the Monthly Balance Sheet Return (MBSR) template.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| line_code | TEXT | Line code, for example L30. |  |
| line_name | TEXT | Line name. |  |
| section | TEXT | Lending (assets) or Deposits (liabilities). |  |
| description | TEXT | What the line holds. |  |
| effective_from | TEXT | First period-end date the line is reported. |  |
| effective_to | TEXT (optional) | Last period-end date the line is reported. Empty if still in use. |  |

### counterparties

Business customers behind commercial facilities and business deposits. Names are withheld; customers are identified by reference.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| counterparty_id | TEXT | Customer reference. |  |
| sector_code | TEXT | UK SIC 2007 section letter. |  |
| sector | TEXT | UK SIC 2007 section name. |  |
| size_class | TEXT | SME, Large corporate or Intragroup, set from latest filed accounts (reporting rule RR-06). |  |
| annual_turnover_gbp | REAL (optional) | Turnover in the latest filed accounts. Empty for group entities. |  |
| accounts_date | TEXT (optional) | Year-end date of the latest filed accounts. |  |
| country | TEXT | Country of incorporation, ISO code. |  |
| group_entity_code | TEXT (optional) | Entity code if the customer is part of the group. | entities.entity_code |
| onboarded_date | TEXT | Date the customer was onboarded. |  |

### field_dictionary

Source fields the return calculation reads, with definitions, types, valid values and validity dates.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| field_id | TEXT | Field identifier. |  |
| source_system | TEXT | System the field belongs to. | source_systems.source_system |
| field_name | TEXT | Field name as it appears in the extract. |  |
| definition | TEXT | What the field means. |  |
| data_type | TEXT | Data type in the extract. |  |
| valid_values | TEXT (optional) | Allowed values or range. |  |
| feeds_column | TEXT | reporting_records column the field populates. |  |
| valid_from | TEXT | First date the field is valid in the extract. |  |
| valid_to | TEXT (optional) | Last date the field is valid. Empty if still valid. |  |

### change_log

Schema changes, mapping amendments, template changes and reference-data changes, with their effective dates.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| change_id | TEXT | Change identifier. |  |
| logged_date | TEXT | Date the change was logged. |  |
| effective_date | TEXT | Date the change takes effect. |  |
| change_type | TEXT | Schema change, Mapping amendment, Template change, Dictionary update or Reference data. |  |
| source_system | TEXT (optional) | System affected, if any. | source_systems.source_system |
| object_changed | TEXT | Field, rule, line or product changed. |  |
| old_value | TEXT (optional) | Value before the change. |  |
| new_value | TEXT (optional) | Value after the change. |  |
| description | TEXT | What changed and why. |  |
| requested_by | TEXT | Person who asked for the change. | staff.staff_id |
| approved_by | TEXT | Person who approved it. | staff.staff_id |
| status | TEXT | Implemented, or Approved - not yet effective. |  |

### mapping_rules

Versioned rules that map each product code to a return line, with effective dates.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| mapping_rule_id | TEXT | Rule identifier. |  |
| mapping_version | TEXT | Version of the mapping set the rule belongs to, V1 to V4. |  |
| product_code | TEXT | Product the rule maps. | products.product_code |
| line_code | TEXT | Return line the product maps to. | return_lines.line_code |
| effective_from | TEXT | First period-end date the rule applies to. |  |
| effective_to | TEXT (optional) | Last period-end date the rule applies to. Empty if open. |  |
| change_id | TEXT | Change that introduced the rule. | change_log.change_id |
| approved_by | TEXT | Person who approved the rule. | staff.staff_id |

### reporting_rules

The return's own instructions: inclusion criteria, calculation and aggregation.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| reporting_rule_id | TEXT | Rule identifier, for example RR-04. |  |
| rule_type | TEXT | Inclusion, Calculation, Classification or Aggregation. |  |
| statement | TEXT | The rule in full. |  |
| applies_to | TEXT | Lines or records the rule applies to. |  |

### fx_rates

Bank of England daily spot rates against sterling, quoted as units of currency per £1.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| fx_rate_id | TEXT | Rate identifier. |  |
| currency | TEXT | ISO currency code. |  |
| rate_date | TEXT | Date of the rate. |  |
| rate | REAL | Units of currency per £1. |  |
| source | TEXT | Where the rate comes from. |  |

### reporting_records

Primary table: one row per source balance feeding the September 2026 return, with its lineage from source field to return line.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| record_id | TEXT | Record identifier, for example RPT-0084. |  |
| reporting_period | TEXT | Return period, YYYY-MM. |  |
| as_at_date | TEXT | Balance date: the period-end date. |  |
| entity_code | TEXT | Group entity that holds the balance. | entities.entity_code |
| source_system | TEXT | System the balance came from. | source_systems.source_system |
| source_record_ref | TEXT | Facility, account or pool reference in the source system. |  |
| record_type | TEXT | Facility, Account (one customer) or Portfolio (a pool of retail accounts). |  |
| number_of_accounts | INTEGER | Accounts in the record: 1 for a facility or account, more for a portfolio. |  |
| product_code | TEXT | Product code from the source system. | products.product_code |
| counterparty_id | TEXT (optional) | Business customer, if any. Empty for retail portfolios. | counterparties.counterparty_id |
| start_date | TEXT (optional) | Date the facility or account started. Empty for portfolios. |  |
| maturity_date | TEXT (optional) | Contractual maturity or review date. Empty if none. |  |
| account_status | TEXT | Status in the source system: Active or Closed. |  |
| source_field | TEXT | Extract field the balance was read from. |  |
| currency | TEXT | Currency of the balance. |  |
| source_amount | REAL | Balance in the source currency, as extracted. |  |
| fx_rate | REAL | Rate used to convert to sterling, units of currency per £1. 1 for GBP. |  |
| amount_gbp | REAL | source_amount divided by fx_rate, rounded to the penny. |  |
| mapping_rule_id | TEXT | Mapping rule applied. | mapping_rules.mapping_rule_id |
| mapping_version | TEXT | Version of the mapping rule applied. |  |
| line_code | TEXT | Return line the record was mapped to. | return_lines.line_code |
| included_in_return | TEXT | Yes or No. |  |
| exclusion_reason | TEXT (optional) | Why the record was left out. Empty if included. |  |
| reported_amount_gbp | REAL (optional) | Amount the return calculation used for this record. Empty if excluded. |  |
| extracted_at | TEXT | Date and time the source extract ran, ISO format. |  |

### control_totals

Expected totals from the general ledger by source system, product and currency at the period end.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| control_id | TEXT | Control identifier. |  |
| reporting_period | TEXT | Return period. |  |
| source_system | TEXT | Source system the control checks. | source_systems.source_system |
| product_code | TEXT | Product the control checks. | products.product_code |
| currency | TEXT | Currency of the control amount. |  |
| gl_account | TEXT | General-ledger account. |  |
| control_amount | REAL | General-ledger balance after end-of-day processing on the period-end date, in the control currency. |  |
| tolerance | REAL | Largest difference accepted without investigation, in the control currency. |  |
| control_source | TEXT | Where the control figure comes from. |  |
| notes | TEXT (optional) | Notes from the finance team. |  |

### return_figures

The return as reported: one row per line for the submitted August return and the draft September return.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| figure_id | TEXT | Figure identifier. |  |
| reporting_period | TEXT | Return period. |  |
| line_code | TEXT | Return line. | return_lines.line_code |
| reported_amount_gbp | REAL | Figure on the return, in pounds. |  |
| record_count | INTEGER | Number of reporting records behind the figure. |  |
| status | TEXT | Submitted, or Draft - awaiting review. |  |
| prepared_by | TEXT | Preparer. | staff.staff_id |
| prepared_date | TEXT | Date prepared. |  |
| reviewed_by | TEXT (optional) | Reviewer. Empty until reviewed. | staff.staff_id |
| approved_by | TEXT (optional) | Approver. Empty until approved. | staff.staff_id |
| submitted_date | TEXT (optional) | Date submitted. Empty for a draft. |  |

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
| spec.md | 2.2 | 2026-10-20 | Describes the data, its flow and its rules for any reader. Contains no answers | Regulatory reporting and data lineage |
