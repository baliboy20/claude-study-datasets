# SME lending — dataset specification

> All people, firms, account numbers and events in this dataset are fictional and were generated for study purposes. Formats follow real UK conventions, so an identifier may coincide with a real one by chance. Planted cases are simulated patterns, not allegations. Businesses and valuers are identified by reference only. The lending policy, accounts, credit grades and valuations are invented for the study.

This document describes the data and the rules that govern it. It does not reveal which records were planted or why. The answer key is in `planted-cases.md` and in the `_truth_` tables, for reviewers only.

## Business scenario

Thameside Financial Group plc is a mid-sized London financial-services group. Thameside Bank, the group's retail and commercial bank, lends to small and medium-sized businesses in London, the South East and the East of England: cafés and restaurants, professional firms, wholesalers, technology firms and trades. Each application has a summary, prepared by a relationship manager or by the online system, that a credit officer or an automated scorecard decides on.

The extract holds the 99 applications received from 1 July to 30 September 2026, for £15,275,000 in all, with the businesses that made them, their accounts, their existing borrowing, the security offered, the credit grades and the lending policy. It was taken at 2026-10-16 18:00, so most applications are decided and some are still open.

Business question: can an analyst, or an AI, work out the affordability ratios, apply the lending rules, and find where the evidence is incomplete or contradictory? Can it tell a calculation, a policy rule and a credit judgement apart, and leave a judgement to a person?

## Business context

Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. Its business banking division lends to small and medium-sized businesses in London, the South East and the East of England: cafés and restaurants, professional firms, wholesalers, technology firms and trades. Relationship managers in the City, Canary Wharf and Croydon prepare applications, and the business banking credit team decides them.

Several pressures have built up this year:
- Growth target. The board wants business lending to grow, and relationship managers have targets for new lending. The same relationship managers prepare the application summaries that credit officers decide on.
- Faster decisions. Since 1 April 2026 an automated scorecard has decided online applications for unsecured loans of up to £50,000. 24 of the quarter's 99 applications came in online, and the scorecard decided all of them. Businesses that apply online have no relationship manager.
- A stretched credit team. Two credit managers, one senior credit manager and the Head of Business Banking Credit decide every application the scorecard does not. At the extract, four referred applications were still waiting for a decision.
- Costs. Rises in employer National Insurance in April 2025 and the National Living Wage in April 2026 have squeezed margins in hospitality and wholesale, which account for 44 of the 99 applications.
- Old borrowing. Many businesses are still repaying loans taken during the pandemic. 11 of the applicants still have a Bounce Back Loan, some on Pay As You Grow terms.
- Paperwork. Small companies have nine months after their year end to file accounts, so filed accounts are often a year old. Valuations are paid for by the customer.

The Head of Business Banking Credit asked for a review of every application received from 1 July to 30 September 2026. There are 99, for £15,275,000 in all. At the extract on 16 October:
- 66 are approved and 14 declined.
- 4 are referred and waiting for a credit officer, 6 are waiting for information, and 5 are still being assessed.
- 4 were withdrawn by the customer.

## How an application works in the records

1. A business applies, online or through its relationship manager. The application is a row in `loan_applications`; the business is in `businesses`.
2. The business's accounts are in `financials`, its existing borrowing in `existing_loans`, and the security it offers in `collateral`.
3. The summary in `loan_applications` sets out turnover, operating profit, cash flow available for debt service, existing and proposed debt service, the DSCR, loan to turnover and LTV. `accounts_used_id` shows which accounts it used. Every figure is defined in `lending_policy`.
4. The scorecard grades the application (`credit_grades`). The application is then approved, declined, referred to a credit officer, or held for information, and the status, route, decider and reason are recorded.

## People and roles

The business banking roles are described in `docs/roles.html` in this dataset's folder. The data holds them in `staff`.

| Staff | Name and job title | Team | Office | Lending authority |
|---|---|---|---|---|
| STF-01 | Helena Marchetti, Head of Business Banking Credit | Business Banking Credit | City | £1,000,000 |
| STF-02 | Kunle Adesanya, Senior Credit Manager | Business Banking Credit | City | £250,000 |
| STF-03 | Rebecca Thornton, Credit Manager | Business Banking Credit | Croydon | £100,000 |
| STF-04 | Sunil Varma, Credit Manager | Business Banking Credit | Croydon | £100,000 |
| STF-05 | Marek Kowalczyk, Relationship Manager, Business Banking | Business Banking | City |  |
| STF-06 | Farzana Begum, Relationship Manager, Business Banking | Business Banking | Croydon |  |
| STF-07 | Tariq Siddiqui, Relationship Manager, Business Banking | Business Banking | City |  |
| STF-08 | Jade Ofori, Relationship Manager, Business Banking | Business Banking | Canary Wharf |  |

## Tables

| Table | Kind | Rows | Holds |
|---|---|---|---|
| collateral | business | 167 | Security offered for each application: what it is, its valuation and date, and its estimated recoverable value. |
| existing_loans | business | 72 | Loans each business had when it applied, from Thameside Bank's records and from a credit reference agency report: balances, repayments, arrears and maturity dates, as at the application date. Includes loans repaid in the last two years. |
| financials | business | 193 | Each business's annual accounts, and management accounts where the business supplied them: profit and loss, cash flow and balance sheet. Figures are in whole pounds. |
| loan_applications | business | 99 | Primary table: every application for a business term loan or commercial mortgage received from 1 July to 30 September 2026, with its application summary and its status at the extract. |
| businesses | lookup | 99 | The businesses that applied. Names are withheld; each business is identified by reference. |
| credit_grades | lookup | 5 | The credit grades the bank's scorecard gives each application, with what the lending policy does with each. |
| lending_policy | lookup | 22 | Thameside Bank's lending policy for business term loans and commercial mortgages, version 4.2, in force from 1 April 2026: definitions of every figure in the application summary, the tests each application must pass, referral thresholds, security and evidence rules. |
| staff | lookup | 8 | People in business banking and business banking credit who appear in the records. |
| _meta_columns | meta | 0 | Data dictionary: one row per column of every table. |
| _meta_dataset | meta | 12 | Facts about the dataset as a whole: name, period, firm, seed and disclaimer. |
| _meta_rules | meta | 7 | Business rules and policies that apply to the data. |
| _meta_tables | meta | 14 | One row per table: what it holds and what kind of table it is. |

The `_truth_` tables (answer key) are left out above.

## Lending policy

The policy is data, in the `lending_policy` table, so every role can read it. It defines every figure in the summary, so only one reading is possible:

| Policy | Area | Title | Statement | If not met |
|---|---|---|---|---|
| LP-01 | Definition | Accounts used in the tests | Every test uses the business's latest full-year accounts: the row in financials for the business, other than management accounts, with the latest period end on or before the application's received date. Management accounts are supporting evidence only and are never used in a test. | Not applicable |
| LP-02 | Definition | Cash flow available for debt service | Cash flow available for debt service = operating profit + depreciation and amortisation - tax paid - dividends and drawings, all from the accounts in LP-01. Interest paid is not deducted, because debt service includes it. Net cash from operating activities is not used. | Not applicable |
| LP-03 | Definition | Existing annual debt service | Existing annual debt service = the sum of annual_repayment_gbp for every loan in existing_loans that is Live at the application date, from any lender, except a loan that this application will repay (refinanced_by_application_id). A loan counts in full even if it ends within the year. A loan in an agreed payment holiday counts at its contractual repayment. | Not applicable |
| LP-04 | Definition | Proposed annual debt service | Proposed annual debt service = 12 x the monthly repayment on the loan requested. Monthly repayment = P x r / (1 - (1 + r) ^ -n), where P is the loan requested, r is interest_rate_pct / 100 / 12 and n is term_years x 12, rounded to the nearest penny before multiplying by 12. | Not applicable |
| LP-05 | Definition | Debt-service coverage ratio (DSCR) | DSCR = cash flow available for debt service (LP-02) / (existing annual debt service (LP-03) + proposed annual debt service (LP-04)), rounded to two decimal places, halves rounded up. The tests use the rounded figure. | Not applicable |
| LP-06 | Affordability | Minimum DSCR | The DSCR must be at least 1.25. An application with a lower DSCR is declined. | Decline |
| LP-07 | Affordability | DSCR referral band | An application with a DSCR of at least 1.25 but below 1.40 is referred to a credit officer, a person with lending authority, who decides it. It may not be approved or declined automatically. | Refer |
| LP-08 | Affordability | Turnover test for unsecured loans | For a loan with no valued property, equipment or vehicle security, the loan requested may not exceed 25% of turnover in the accounts in LP-01. Loan to turnover = loan requested / turnover x 100, to one decimal place, halves rounded up. | Decline |
| LP-09 | Eligibility | Time trading | The business must have been trading for at least 24 months at the application date, counted from trading_since. | Decline |
| LP-10 | Eligibility | Size of business | Turnover in the accounts in LP-01 must be at least £100,000 and no more than £25,000,000. | Decline |
| LP-11 | Eligibility | Arrears on existing borrowing | If any Live loan in existing_loans is more than 30 days in arrears at the application date, the application is declined. If any is 1 to 30 days in arrears, it is referred. | Decline |
| LP-12 | Eligibility | Credit grade | An application graded E by the scorecard is declined. An application graded D is referred. See credit_grades. | Decline |
| LP-13 | Liquidity | Current ratio | Current ratio = current assets / current liabilities, from the accounts in LP-01. An application with a current ratio below 1.00 is referred. | Refer |
| LP-14 | Definition | Other liquidity measures | Quick ratio = (current assets - stock) / current liabilities. Debtor days = trade debtors / turnover x 365. Both are worked out from the same accounts. They have no thresholds; credit officers use them in their judgement (LP-22). | Not applicable |
| LP-15 | Security | Loan to value | Loan to value (LTV) = loan requested / the total market value of the Valued property, equipment and vehicle security offered for the application x 100, to one decimal place, halves rounded up. Debentures and personal guarantees are not valued and do not count. Recoverable value = market value less the forced-sale discount: 25% for property, 50% for equipment and 40% for vehicles. | Not applicable |
| LP-16 | Security | Maximum LTV for property | A loan secured on commercial property may not exceed 70% LTV. | Decline |
| LP-17 | Security | Maximum LTV for equipment and vehicles | A loan secured on new equipment or commercial vehicles may not exceed 80% of the supplier's quoted price. | Decline |
| LP-18 | Security | Security for larger loans | A loan above £250,000 must be secured on valued property, equipment or vehicles. | Decline |
| LP-19 | Evidence | Age of valuations | A property valuation must be a RICS Red Book valuation dated no more than 12 months before the decision date. A supplier quotation for equipment or vehicles must be dated no more than 6 months before the decision date. No decision may be made on an older valuation, or before an instructed valuation is received; the application waits for a new one. | Awaiting information |
| LP-20 | Evidence | Age of accounts | The accounts in LP-01 must end no more than 18 months before the application date. If they are older, the application waits for newer full-year accounts. Management accounts do not replace them. | Awaiting information |
| LP-21 | Decision | Policy exceptions | An application that fails a test whose outcome is Decline may be approved only by the Credit Committee, as a policy exception, with the exception and its reason recorded in policy_exception. | Decline |
| LP-22 | Decision | Judgement | Passing every test does not oblige the bank to lend, and a referral is not a decline. A credit officer weighs the evidence, including trends in the accounts, and records the reason for the decision. | Not applicable |

## Credit grades

| Grade | Name | One-year default rate | Policy outcome |
|---|---|---|---|
| A | Strong | Below 0.5% | Eligible |
| B | Good | 0.5% to 1.5% | Eligible |
| C | Satisfactory | 1.5% to 4% | Eligible |
| D | Weak | 4% to 10% | Refer |
| E | Poor | Above 10% | Decline |

## Credit procedures

The procedures the credit team follows are in `_meta_rules` (analyst role and above):

| Rule | Area | Rule | Applies to |
|---|---|---|---|
| R-01 | Process | **Order of assessment.** Each application is assessed in this order. First the evidence (LP-19, LP-20): if it is out of date or missing, the status is Awaiting information and no test is applied. Then the tests whose outcome is Decline. Then the referral tests (LP-07, LP-11, LP-12, LP-13). An application that passes every test is approved by whoever has the authority. | loan_applications, lending_policy |
| R-02 | Authority | **Who decides.** The automated scorecard decides online applications for unsecured term loans of up to £50,000, and only when no referral test applies; it approves or declines. Otherwise a credit officer decides: Credit Manager up to £100,000, Senior Credit Manager up to £250,000, Credit Committee above £250,000 and for every policy exception. The Credit Committee meets on Tuesdays, and its decisions are recorded against its chair, the Head of Business Banking Credit. Relationship managers prepare applications but may not decide them. | loan_applications, staff |
| R-03 | Process | **Application summary.** The relationship manager, or for an online application the system, prepares the summary in loan_applications from the records in financials, existing_loans and collateral, using the definitions in LP-01 to LP-05, LP-08 and LP-15. accounts_used_id records which accounts were used. The person deciding checks the summary against the records. | loan_applications, financials, existing_loans, collateral |
| R-04 | Process | **Referrals.** A referred application records its referral_reasons and stays at Refer until a credit officer with enough authority decides it. The officer records the judgement in status_reason. | loan_applications |
| R-05 | Process | **Credit grades.** The scorecard grades every application when it is received. The score and the factors behind it are held in the scorecard system, not in this dataset. | loan_applications, credit_grades |
| R-06 | Evidence | **Valuations.** Property valuations are instructed by the bank from its panel of valuers, at the customer's cost. A valuation the customer already holds may be used only if it meets LP-19. | collateral |
| R-07 | Decision | **What a decision means.** Approved means credit has been sanctioned. The loan is drawn only once the conditions are met. Declined applications may be appealed to the Head of Business Banking Credit. | loan_applications |

## Conventions

- Money is in pounds sterling. Accounts are in whole pounds; repayments and summary figures are to the penny.
- Dates are ISO format, YYYY-MM-DD. Applications are received and decided on working days in England and Wales.
- Existing loans, balances and arrears are as at the application date, from the bank's records and a credit reference agency report.
- Businesses and valuers are identified by reference only. Postcode districts and SIC codes are real; the businesses are not.
- Other lenders are named because a credit reference report names them. Nothing in the data says anything about those lenders.

Note on the firm's name: no company is registered as Thameside Financial Group, Thameside Bank or Thameside Insurance. Real companies with similar names exist, including Thameside Financial Services Limited and Thameside Financial Planning Limited. The name is set in `generator/common/firm.py` and can be changed there.

## Data dictionary

### collateral

Security offered for each application: what it is, its valuation and date, and its estimated recoverable value.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| collateral_id | TEXT | Security identifier, for example COL-0012. |  |
| application_id | TEXT | Application the security is offered for. | loan_applications.application_id |
| security_type | TEXT | Commercial property (first legal charge), Equipment, Commercial vehicles, Debenture (fixed and floating charge over the business's assets) or Personal guarantee. |  |
| description | TEXT | What the security is. |  |
| valuation_status | TEXT | Valued, Instructed (valuation ordered, not yet received), or Not valued (debentures and guarantees, which the policy does not value). |  |
| valuation_basis | TEXT (optional) | RICS Red Book valuation by a panel valuer, or Supplier quotation for new equipment and vehicles. Empty if not valued. |  |
| valuation_date | TEXT (optional) | Date of the valuation or quotation. Empty if not valued. |  |
| market_value_gbp | REAL (optional) | Market value, or the quoted price of new equipment or vehicles. Empty if not valued. |  |
| forced_sale_discount_pct | REAL (optional) | Discount the bank applies for a forced sale (policy LP-15). Empty if not valued. |  |
| recoverable_value_gbp | REAL (optional) | Estimated recoverable value: market value less the forced-sale discount. Empty if not valued. |  |

### existing_loans

Loans each business had when it applied, from Thameside Bank's records and from a credit reference agency report: balances, repayments, arrears and maturity dates, as at the application date. Includes loans repaid in the last two years.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| loan_id | TEXT | Loan identifier, for example EXL-0031. |  |
| business_id | TEXT | Business that borrowed. | businesses.business_id |
| lender | TEXT | Lender: Thameside Bank or another bank. |  |
| facility_type | TEXT | Term loan, Bounce Back Loan, Coronavirus Business Interruption Loan (CBILS), Hire purchase or Commercial mortgage. |  |
| original_amount_gbp | REAL | Amount first lent. |  |
| start_date | TEXT | Date the loan was drawn. |  |
| maturity_date | TEXT | Date of the final repayment. |  |
| interest_rate_pct | REAL | Annual interest rate, in percent. |  |
| monthly_repayment_gbp | REAL | Contractual monthly repayment of capital and interest. |  |
| annual_repayment_gbp | REAL | Twelve monthly repayments. |  |
| outstanding_balance_gbp | REAL | Balance owed at the application date. Zero once repaid. |  |
| loan_status | TEXT | Live or Repaid, at the application date. |  |
| repayment_status | TEXT | Up to date, In arrears, Payment holiday (with its end date), or Repaid. |  |
| arrears_days | INTEGER | Days the oldest missed repayment was overdue at the application date. Zero if none. |  |
| arrears_gbp | REAL | Repayments missed and still unpaid at the application date. |  |
| refinanced_by_application_id | TEXT (optional) | Application whose loan will repay this loan in full, if any. | loan_applications.application_id |
| source | TEXT | Thameside Bank records, or Credit reference agency report for loans from other lenders. |  |

### financials

Each business's annual accounts, and management accounts where the business supplied them: profit and loss, cash flow and balance sheet. Figures are in whole pounds.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| financial_id | TEXT | Accounts identifier, for example FIN-0107. |  |
| business_id | TEXT | Business the accounts belong to. | businesses.business_id |
| accounts_type | TEXT | Statutory accounts (unaudited), Accountant-prepared accounts (for a sole trader or partnership), or Management accounts (prepared by the business, not full-year accounts). |  |
| period_start | TEXT | First day of the period. |  |
| period_end | TEXT | Last day of the period. The balance sheet figures are as at this date. |  |
| turnover_gbp | REAL | Turnover (sales) for the period. |  |
| operating_profit_gbp | REAL | Operating profit: profit before interest and tax, after depreciation and amortisation. |  |
| depreciation_amortisation_gbp | REAL | Depreciation and amortisation charged in arriving at operating profit. |  |
| interest_paid_gbp | REAL | Interest paid on borrowing in the period. |  |
| tax_paid_gbp | REAL | Corporation tax paid in the period. Zero for a sole trader or partnership, whose owners pay income tax personally. |  |
| dividends_drawings_gbp | REAL | Dividends paid to shareholders, or drawings taken by the owners of a sole trader or partnership. |  |
| net_cash_from_operations_gbp | REAL | Net cash from operating activities, from the cash flow statement: operating profit plus depreciation and amortisation, less tax paid, less the increase in working capital. |  |
| fixed_assets_gbp | REAL | Fixed assets at the period end: property, equipment, vehicles and intangible assets. |  |
| cash_at_bank_gbp | REAL | Cash at bank and in hand. |  |
| trade_debtors_gbp | REAL | Money owed by customers. |  |
| stock_gbp | REAL | Stock and work in progress. |  |
| other_current_assets_gbp | REAL | Prepayments and other current assets. |  |
| current_assets_gbp | REAL | Total current assets: cash, trade debtors, stock and other current assets. |  |
| trade_creditors_gbp | REAL | Money owed to suppliers. |  |
| bank_overdraft_gbp | REAL | Overdraft drawn at the period end. |  |
| other_current_liabilities_gbp | REAL | Tax, VAT, accruals and loan repayments due within one year. |  |
| current_liabilities_gbp | REAL | Total current liabilities: trade creditors, overdraft and other current liabilities. |  |
| long_term_debt_gbp | REAL | Loans repayable after more than one year. |  |
| net_assets_gbp | REAL | Net assets: fixed assets plus current assets, less current liabilities and long-term debt. |  |

### loan_applications

Primary table: every application for a business term loan or commercial mortgage received from 1 July to 30 September 2026, with its application summary and its status at the extract.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| application_id | TEXT | Application reference, for example APP-0082. Numbers rise with the date the application was received. |  |
| business_id | TEXT | Business that applied. | businesses.business_id |
| received_date | TEXT | Date the application was received. The tests are applied as at this date. |  |
| channel | TEXT | Online (the business applied through online banking and the system prepared the summary) or Relationship manager (the relationship manager prepared the summary). |  |
| sector | TEXT | Sector of the business, copied from businesses. |  |
| product | TEXT | Term loan or Commercial mortgage. |  |
| loan_purpose | TEXT | What the money is for. |  |
| loan_requested_gbp | REAL | Amount requested. |  |
| term_years | INTEGER | Term of the loan in years. Repayments are monthly, capital and interest. |  |
| interest_rate_pct | REAL | Fixed annual interest rate offered, in percent. |  |
| accounts_used_id | TEXT | Accounts the summary's turnover, operating profit and cash flow were taken from. | financials.financial_id |
| annual_turnover_gbp | REAL | Summary: annual turnover. |  |
| operating_profit_gbp | REAL | Summary: operating profit. |  |
| cash_flow_available_gbp | REAL | Summary: cash flow available for debt service (policy LP-02). |  |
| existing_debt_service_gbp | REAL | Summary: existing annual debt service (policy LP-03). |  |
| proposed_debt_service_gbp | REAL | Summary: proposed annual debt service on the loan requested (policy LP-04). |  |
| dscr | REAL | Summary: debt-service coverage ratio (policy LP-05), to two decimal places. |  |
| loan_to_turnover_pct | REAL | Summary: loan requested as a percentage of annual turnover, to one decimal place (policy LP-08). |  |
| ltv_pct | REAL (optional) | Summary: loan-to-value, to one decimal place (policy LP-15). Empty if no valued property, equipment or vehicle security. |  |
| credit_grade | TEXT | Grade the bank's scorecard gave the application. | credit_grades.credit_grade |
| summary_notes | TEXT | Commentary in the application summary, by the relationship manager or the online system. |  |
| decision_status | TEXT | Status at the extract: Approved, Declined, Refer (waiting for a credit officer's decision), Awaiting information, In assessment or Withdrawn. |  |
| referral_reasons | TEXT (optional) | Why the application was referred to a credit officer. Empty if it was not referred. |  |
| decision_route | TEXT (optional) | Who decided: Automated scorecard, Credit manager, Senior credit manager or Credit committee. Empty if not decided. |  |
| decided_by | TEXT (optional) | Person who decided, or the Credit Committee's chair. Empty for a scorecard decision or if not decided. | staff.staff_id |
| decision_date | TEXT (optional) | Date of the decision, or of the withdrawal. Empty if not decided. |  |
| status_reason | TEXT | The reason recorded for the status: the tests passed or failed, the judgement made, or the information awaited. |  |
| policy_exception | TEXT (optional) | For an approval that fails a policy test: the exception the Credit Committee agreed and why (policy LP-21). Empty otherwise. |  |
| conditions | TEXT (optional) | Conditions of an approval: security to be taken and covenants. Empty unless approved. |  |

### businesses

The businesses that applied. Names are withheld; each business is identified by reference.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| business_id | TEXT | Business reference, for example SME-0041. Numbers rise with the date the business became a customer of Thameside Bank. |  |
| legal_form | TEXT | Private limited company, Limited liability partnership, Partnership or Sole trader. |  |
| sector | TEXT | Sector: Hospitality, Professional services, Wholesale, Technology, Construction trades, Healthcare, Manufacturing or Logistics. |  |
| sic_code | TEXT | Main activity, as a UK SIC 2007 code. |  |
| sic_description | TEXT | Description of the SIC code. |  |
| business_description | TEXT | What the business does, as recorded by the bank. |  |
| registered_region | TEXT | Region of the registered office or main trading address: London, South East or East of England. |  |
| postcode_district | TEXT | Postcode district of the main trading address. |  |
| trading_since | TEXT | Date the business started trading. |  |
| incorporated_date | TEXT (optional) | Date of incorporation at Companies House. Empty for a sole trader or partnership. |  |
| employees | INTEGER | Number of employees, including working owners. |  |
| year_end | TEXT | Day and month the business's financial year ends, for example 31 March. |  |
| customer_since | TEXT | Date the business opened its first account with Thameside Bank. |  |
| relationship_manager_id | TEXT (optional) | Relationship manager. Empty for a business served by the online business team. | staff.staff_id |

### credit_grades

The credit grades the bank's scorecard gives each application, with what the lending policy does with each.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| credit_grade | TEXT | Grade, A (strongest) to E (weakest). |  |
| grade_name | TEXT | Name of the grade. |  |
| one_year_default_rate | TEXT | Range of the chance that a business of this grade defaults within a year, as calibrated by the bank. |  |
| policy_outcome | TEXT | What the lending policy does with an application of this grade (policy LP-12). |  |

### lending_policy

Thameside Bank's lending policy for business term loans and commercial mortgages, version 4.2, in force from 1 April 2026: definitions of every figure in the application summary, the tests each application must pass, referral thresholds, security and evidence rules.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| policy_id | TEXT | Policy reference, for example LP-06. |  |
| category | TEXT | Definition, Eligibility, Affordability, Liquidity, Security, Evidence or Decision. |  |
| title | TEXT | Short name of the policy. |  |
| statement | TEXT | The policy in full. |  |
| threshold | REAL (optional) | The number the test uses, if it has one. |  |
| unit | TEXT (optional) | Unit of the threshold: ratio, percent, months, days or GBP. |  |
| outcome_if_not_met | TEXT | What happens to an application that does not meet the policy: Decline, Refer, Awaiting information or Not applicable (a definition). |  |

### staff

People in business banking and business banking credit who appear in the records.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| staff_id | TEXT | Staff identifier. |  |
| first_name | TEXT | First name. |  |
| last_name | TEXT | Surname. |  |
| job_title | TEXT | Job title. |  |
| team | TEXT | Team. |  |
| office | TEXT | Office: City, Canary Wharf or Croydon. |  |
| lending_authority_gbp | REAL (optional) | Largest loan the person may approve. Credit Committee decisions are recorded against its chair. Empty if the person may not approve loans. |  |
| email | TEXT | Work email address. |  |

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

### _meta_dataset

Facts about the dataset as a whole: name, period, firm, seed and disclaimer.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| key | TEXT | Name of the fact. |  |
| value | TEXT | Value of the fact. |  |

### _meta_rules

Business rules and policies that apply to the data.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| rule_id | TEXT | Rule identifier, for example R-04. |  |
| category | TEXT | Area the rule belongs to. |  |
| title | TEXT | Short name of the rule. |  |
| statement | TEXT | The rule in full. |  |
| related_tables | TEXT | Tables the rule applies to. |  |

### _meta_tables

One row per table: what it holds and what kind of table it is.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| table_name | TEXT | Table name. |  |
| kind | TEXT | business (operational records), lookup (reference data), meta (documentation) or truth (answer key). |  |
| description | TEXT | What the table holds. |  |
| primary_key | TEXT | Column that identifies a row. |  |
| row_count | INTEGER | Number of rows. |  |

## Rebuilding and serving

Run from this dataset's folder:

```bash
python3 generator/build.py
```

The build is deterministic: the same code and seed produce byte-identical files. See `api/README.md` for serving the data through the local API.



---

| Document | Version | Date | Purpose | Dataset |
|---|---|---|---|---|
| spec.md | 1.2 | 2026-10-20 | Describes the data, how applications are handled and the lending policy for any reader. Contains no answers | SME lending |
