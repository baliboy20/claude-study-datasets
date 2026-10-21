# Treasury liquidity — dataset specification

> All people, firms, account numbers and events in this dataset are fictional and were generated for study purposes. Formats follow real UK conventions, so an identifier may coincide with a real one by chance. Planted cases are simulated patterns, not allegations. Counterparties outside the group are identified by reference only, and their ratings are invented. The policy, limits and stress scenarios are invented for the study. A synthetic liquidity exercise tests analysis and controls; it does not show compliance with any regulatory liquidity requirement.

This document describes the data and the rules that govern it. It does not reveal which records were planted or why. The answer key is in `planted-cases.md` and in the `_truth_` tables, for reviewers only.

## Business scenario

Thameside Financial Group plc is a mid-sized London financial-services group. Thameside Bank, the group's retail and commercial bank, funds its lending from deposits and wholesale funding. Its treasury team forecasts the bank's cash inflows and outflows every working day, places them in time buckets, and tests the result against the bank's liquid asset buffer, in a base case and under three stress scenarios.

The extract holds the 100 flows in the forecast due from 1 October to 31 December 2026, as at the close of business on 30 September 2026, with the funding instruments behind them, the counterparties, exchange rates, the liquid asset buffer, the stress scenarios, the ladder's buckets and the liquidity policy. It was taken at 2026-09-30 18:00.

Business question: can an analyst, or an AI, calculate the bank's liquidity position over time, apply currency conversions, find concentrations of maturing funding, and explain what happens when funding conditions deteriorate? Can it keep the base case and the stress scenarios apart?

## Business context

Thameside Bank is the retail and commercial bank of Thameside Financial Group plc. It funds its mortgages and business loans mainly from savers' deposits, and tops them up with wholesale funding: deposits from other banks, money market funds, local authorities and companies, certificates of deposit, repos and a senior note. A small treasury team in the City and Canary Wharf manages the bank's cash and its liquid asset buffer, now £1,642,000,000 at market value.

Several pressures have built up this year:
- Savers are leaving. Rivals pay more on fixed-rate bonds, and Retail Banking forecasts £156,800,000 of net withdrawals in the last quarter of the year, more in December than in October.
- Lending is growing. Retail Banking and Business Banking forecast £199,000,000 of new mortgage and business lending to be drawn in the quarter, and the board wants that pace kept up.
- Shorter wholesale funding. To fill the gap, Treasury has borrowed for shorter terms. £864,444,153 of wholesale funding from 23 lenders falls due in the quarter, 21 of the 32 deals for three months or less.
- More currencies. Some funding is raised in US dollars and euros, so 10 of the forecast's flows must be converted to sterling.
- Plans that are not yet deals. Business units have submitted £175,000,000 of inflows that have no signed contract, including the sale of a tranche of mortgages.
- A stretched team. One forecasting analyst loads the daily forecast and the business units' submissions; the Asset and Liability Manager reviews the ladder and the three stress scenarios every day.

ALCO meets on Tuesday 6 October 2026. The Head of Treasury asked for the quarter's liquidity ladder as at 30 September, under the base case and each stress scenario, with an explanation of any limit at risk.

## How the forecast works in the records

1. Each flow is a row in `cashflows`: who pays or receives it, its type, direction, currency, amount, due and expected dates, contract status and the forecasting run that loaded it.
2. A flow that comes from wholesale funding links to its deal in `funding_instruments`, which holds the terms: dates, rate, day count, interest, collateral and status.
3. USD and EUR flows are converted to sterling with a rate from `fx_rates`.
4. The ladder places each base-case flow in a bucket from `liquidity_buckets`, nets inflows against outflows, and adds the cumulative gap to the buffer in `liquid_assets`. Each scenario in `stress_scenarios` changes the base-case flows and haircuts. Every step is defined in `treasury_policy`.

## People and roles

The treasury roles are described in `docs/roles.html` in this dataset's folder. The data holds them in `staff`.

| Staff | Name and job title | Team | Office | Dealing limit |
|---|---|---|---|---|
| STF-01 | Victoria Okwuosa, Head of Treasury | Treasury | City | £250,000,000 |
| STF-02 | Duncan Freer, Asset and Liability Manager | Treasury | City |  |
| STF-03 | Rajesh Venkatesan, Senior Money Markets Dealer | Treasury | City | £100,000,000 |
| STF-04 | Chloe Brannigan, Money Markets Dealer | Treasury | City | £50,000,000 |
| STF-05 | Bartosz Wieczorek, Liquidity Forecasting Analyst | Treasury | Canary Wharf |  |
| STF-06 | Yasmin Qadri, Liquidity Risk Manager | Liquidity Risk | Canary Wharf |  |
| STF-07 | Ioana Dumitru, Chief Financial Officer | Finance (chair of ALCO) | City |  |

## Tables

| Table | Kind | Rows | Holds |
|---|---|---|---|
| cashflows | business | 100 | Primary table: every flow in the liquidity forecast due from 1 October to 31 December 2026, as loaded for the forecast at the close of business on 30 September 2026. |
| funding_instruments | business | 43 | Thameside Bank's wholesale funding that matures, starts or pays interest within reach of the forecast: term deposits, certificates of deposit, repos and senior notes, with their terms. |
| counterparties | lookup | 36 | The other parties to the forecast flows. Firms outside the group are identified by reference and a description only. Ratings are invented for the study. |
| fx_rates | lookup | 26 | Exchange rates captured by the treasury dealing system at 16:00 London time, quoted as units of the currency per £1. |
| liquid_assets | lookup | 5 | The bank's liquid asset buffer at the as-at date: unencumbered assets it can sell or use as collateral to raise cash at once. |
| liquidity_buckets | lookup | 6 | The ladder's reporting intervals, counted in calendar days after the as-at date, and the rule for placing a flow in one. |
| staff | lookup | 7 | People in Thameside Bank's treasury and liquidity risk teams, and the chair of the Asset and Liability Committee (ALCO). |
| stress_scenarios | lookup | 23 | The three stress scenarios, one row per assumption: outflow shocks, reduced inflows, falls in sterling and funding haircuts on the buffer. Applied to the base case as policy TP-11 sets out. |
| treasury_policy | lookup | 16 | Thameside Bank's liquidity policy, version 3.1, in force from 1 July 2026: which flows the forecast includes, how each figure in the liquidity ladder is calculated, and the limits the ladder is tested against. |
| _meta_columns | meta | 0 | Data dictionary: one row per column of every table. |
| _meta_dataset | meta | 13 | Facts about the dataset as a whole: name, period, firm, seed and disclaimer. |
| _meta_rules | meta | 7 | Business rules and policies that apply to the data. |
| _meta_tables | meta | 15 | One row per table: what it holds and what kind of table it is. |

The `_truth_` tables (answer key) are left out above.

## Liquidity policy

The policy is data, in the `treasury_policy` table, so every role can read it. It defines every calculation, so only one reading is possible:

| Policy | Area | Title | Statement |
|---|---|---|---|
| TP-01 | Scope | As-at date and horizon | The forecast is as at the close of business on Wednesday 30 September 2026 (the as-at date, day 0). The ladder covers flows with a bucket date from 1 October to 31 December 2026, in the six buckets in liquidity_buckets. |
| TP-02 | Scope | Flows in the base case | The base case is every flow loaded by a base-case run of the forecasting system (forecast_run beginning BASE-), except inflows whose contract_status is Unconfirmed. Outflows count whatever their status. An inflow from a funding instrument is Confirmed only if the instrument's deal_status is Executed. Flows loaded by a stress run are never part of the base case. |
| TP-03 | Definition | Bucket date | The bucket date of an inflow is its expected_date. The bucket date of an outflow is the earlier of its due_date and its expected_date: an outflow is never assumed to be paid late. |
| TP-04 | Calculation | Bucket allocation | Days = bucket date - as-at date, in calendar days. A flow is in the bucket whose from_day <= days <= to_day. A flow linked to a funding instrument is due on the instrument's payment date (TP-06). |
| TP-05 | Calculation | Conversion to sterling | A USD or EUR flow is converted at the spot rate in fx_rates for the as-at date, whenever the flow was entered: amount_gbp = nominal / rate, rounded to the penny, halves rounded up. A sterling flow is not converted. A sterling amount fixed by a contract, such as the sterling leg of an FX swap, is a sterling flow. |
| TP-06 | Calculation | Maturity amount and payment date | Payment date = the maturity date adjusted under the modified following convention: if it is not a working day in England, the next working day, unless that falls in the next calendar month, in which case the previous working day. Interest = principal x interest_rate_pct / 100 x days / basis, rounded to the penny, halves rounded up, where days run from start_date to the payment date and basis is 365 for ACT/365 and 360 for ACT/360. The maturity flow is principal + interest, on the payment date. A rollover with the same counterparty settles only the interest; the principal stays. |
| TP-07 | Calculation | Net gap | Net gap for a bucket = the sum of amount_gbp of the base-case inflows in the bucket - the sum of amount_gbp of the base-case outflows in the bucket. |
| TP-08 | Calculation | Cumulative gap | Cumulative gap for a bucket = the sum of the net gaps of that bucket and every earlier bucket. |
| TP-09 | Calculation | Liquid asset buffer | Buffer = the sum over liquid_assets of market_value_gbp x (1 - haircut / 100), each rounded to the penny. The base case uses base_haircut_pct. The buffer is available from day 1. |
| TP-10 | Calculation | Liquidity position | Liquidity position for a bucket = buffer (TP-09) + cumulative gap (TP-08) for that bucket. |
| TP-11 | Stress | Applying a stress scenario | A stress scenario starts from the base-case flows (TP-02) and changes them using only its own rows in stress_scenarios. Stressed amount = amount_gbp x m / (1 - f / 100), rounded to the penny, halves rounded up, where m = 1 + shock_pct / 100 for an Outflow increase on the flow's type, m = 1 - shock_pct / 100 for an Inflow reduction on the flow's type, otherwise 1, and f = the FX move for the flow's currency, otherwise 0. A Funding haircut adds shock_pct to the base haircut of every asset of that class. A scenario's figures are never combined with base-case figures or with another scenario's. |
| TP-12 | Limit | Survival over the horizon | The liquidity position must be above zero at the end of every bucket, in the base case and in every stress scenario. A breach is reported to ALCO the same day. |
| TP-13 | Limit | Negative base-case gap | A negative base-case net gap in any bucket is reported to ALCO with its cause, even if the liquidity position stays above zero. |
| TP-14 | Limit | Maturities on one day | Wholesale funding maturities from counterparties outside the group falling due on any one day must not exceed £150,000,000 in the base case, measured on amount_gbp. Intra-group deposits are left out. |
| TP-15 | Limit | Concentration by counterparty group | No concentration group may account for more than 25% of the wholesale funding maturities from counterparties outside the group in the horizon, measured on amount_gbp in the base case. |
| TP-16 | Definition | Wholesale funding | Wholesale funding is borrowing in funding_instruments: term deposits, certificates of deposit, repos and senior notes. Its maturities are cashflows of flow type Wholesale funding maturity. |

## Buckets

| Bucket | Name | Days after the as-at date | Dates |
|---|---|---|---|
| B1 | Next day | 1 to 1 | 2026-10-01 to 2026-10-01 |
| B2 | 2 to 7 days | 2 to 7 | 2026-10-02 to 2026-10-07 |
| B3 | 8 to 14 days | 8 to 14 | 2026-10-08 to 2026-10-14 |
| B4 | 15 days to 1 month | 15 to 31 | 2026-10-15 to 2026-10-31 |
| B5 | 1 to 2 months | 32 to 61 | 2026-11-01 to 2026-11-30 |
| B6 | 2 to 3 months | 62 to 92 | 2026-12-01 to 2026-12-31 |

## Stress scenarios

| Assumption | Scenario | Type | Applies to | Shock | In words |
|---|---|---|---|---|---|
| SP-01 | ST-01 Market-wide stress | Outflow increase | Retail deposit outflow | 40% | Savers withdraw 40% more than forecast as markets fall. |
| SP-02 | ST-01 Market-wide stress | Outflow increase | Business deposit outflow | 40% | Businesses draw down 40% more of their deposits. |
| SP-03 | ST-01 Market-wide stress | Outflow increase | Committed facility drawdown | 100% | Businesses draw twice as much on their committed facilities. |
| SP-04 | ST-01 Market-wide stress | Inflow reduction | Customer loan repayment | 10% | One in ten loan repayments is missed or deferred. |
| SP-05 | ST-01 Market-wide stress | FX move | USD | 10% | Sterling falls 10% against the US dollar. |
| SP-06 | ST-01 Market-wide stress | FX move | EUR | 8% | Sterling falls 8% against the euro. |
| SP-07 | ST-01 Market-wide stress | Funding haircut | UK gilts | 2% | Gilt prices fall; 2 percentage points are added to the gilt haircut. |
| SP-08 | ST-01 Market-wide stress | Funding haircut | Covered bonds | 10% | Covered bonds become harder to sell; 10 points are added. |
| SP-09 | ST-02 Thameside-specific stress | Outflow increase | Retail deposit outflow | 150% | After a two-notch downgrade of Thameside Bank, savers withdraw two and a half times the forecast. |
| SP-10 | ST-02 Thameside-specific stress | Outflow increase | Business deposit outflow | 100% | Businesses withdraw twice the forecast. |
| SP-11 | ST-02 Thameside-specific stress | Outflow increase | Committed facility drawdown | 50% | Businesses draw 50% more on committed facilities. |
| SP-12 | ST-02 Thameside-specific stress | Inflow reduction | New wholesale funding | 100% | Lenders withdraw from forward-starting deals. |
| SP-13 | ST-02 Thameside-specific stress | Funding haircut | Covered bonds | 5% | 5 points are added to the covered bond haircut. |
| SP-14 | ST-03 Combined stress | Outflow increase | Retail deposit outflow | 200% | Savers withdraw three times the forecast. |
| SP-15 | ST-03 Combined stress | Outflow increase | Business deposit outflow | 150% | Businesses withdraw two and a half times the forecast. |
| SP-16 | ST-03 Combined stress | Outflow increase | Committed facility drawdown | 150% | Businesses draw two and a half times the forecast on committed facilities. |
| SP-17 | ST-03 Combined stress | Inflow reduction | Customer loan repayment | 15% | 15% of loan repayments are missed or deferred. |
| SP-18 | ST-03 Combined stress | Inflow reduction | New wholesale funding | 100% | Lenders withdraw from forward-starting deals. |
| SP-19 | ST-03 Combined stress | FX move | USD | 12% | Sterling falls 12% against the US dollar. |
| SP-20 | ST-03 Combined stress | FX move | EUR | 10% | Sterling falls 10% against the euro. |
| SP-21 | ST-03 Combined stress | Funding haircut | UK gilts | 3% | 3 points are added to the gilt haircut. |
| SP-22 | ST-03 Combined stress | Funding haircut | Supranational bonds | 10% | 10 points are added to the supranational bond haircut. |
| SP-23 | ST-03 Combined stress | Funding haircut | Covered bonds | 15% | 15 points are added to the covered bond haircut. |

## Treasury procedures

The procedures the treasury team follows are in `_meta_rules` (analyst role and above):

| Rule | Area | Rule | Applies to |
|---|---|---|---|
| R-01 | Process | **Daily forecast.** The forecasting system takes flows from the treasury dealing system, the lending and deposit platforms, and the business units' forecasts. The base-case run starts at 17:30 each working day, BASE-yyyymmdd. Deals booked after 17:30 and before 17:50 are loaded by an adjustment run at 17:50, BASE-yyyymmdd-ADJ, which is part of the base case. | cashflows, funding_instruments |
| R-02 | Process | **Stress runs.** The Asset and Liability Manager runs each stress scenario in the same forecasting system after the base run, as STnn-yyyymmdd. Stress runs are for the stress ladders only and are kept apart from the base case. | cashflows, stress_scenarios |
| R-03 | Process | **Business unit forecasts.** Retail Banking, Business Banking and Finance submit their forecasts by the 25th of each month. A flow with no signed contract is submitted as Unconfirmed. The Liquidity Forecasting Analyst loads them. | cashflows |
| R-04 | Process | **Exchange rates.** The dealing system captures spot rates at 16:00 London time each working day. The base run converts every USD and EUR flow at the day's rate. | fx_rates, cashflows |
| R-05 | Authority | **Dealing.** Only dealers may agree wholesale deals, each within the dealing limit in staff. Deals above £250,000,000 need ALCO's approval. | funding_instruments, staff |
| R-06 | Authority | **Review and reporting.** The Asset and Liability Manager reviews the ladder each day. The Head of Treasury signs it off for ALCO, which the Chief Financial Officer chairs and which meets on the first Tuesday of each month. The Liquidity Risk Manager sets the stress assumptions and reviews the stress results independently of Treasury. | staff, treasury_policy |
| R-07 | Process | **What the ladder is for.** The ladder is the bank's internal measure of liquidity. It is not a regulatory return: the liquidity coverage ratio and net stable funding ratio are calculated separately, on different definitions. | treasury_policy |

## Conventions

- Amounts in `cashflows` are positive; `direction` says which way the money moves. Money is to the penny.
- Dates are ISO format, YYYY-MM-DD. Working days are those in England and Wales; 25 and 28 December 2026 are bank holidays.
- Exchange rates are units of the currency per £1, as the Bank of England and the London market quote them against sterling.
- Counterparties outside the group are identified by reference and a description only. Their ratings are invented. Nothing in the data says anything about any real firm.
- The ladder is an internal measure for the study. It is not a liquidity coverage ratio or any other regulatory measure.

Note on the firm's name: no company is registered as Thameside Financial Group, Thameside Bank or Thameside Insurance. Real companies with similar names exist, including Thameside Financial Services Limited and Thameside Financial Planning Limited. The name is set in `generator/common/firm.py` and can be changed there.

## Data dictionary

### cashflows

Primary table: every flow in the liquidity forecast due from 1 October to 31 December 2026, as loaded for the forecast at the close of business on 30 September 2026.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| cashflow_id | TEXT | Cash-flow identifier, for example CF-0061. Numbers follow the due date. |  |
| counterparty_id | TEXT | Counterparty paying or receiving the money. | counterparties.counterparty_id |
| instrument_id | TEXT (optional) | Funding instrument the flow belongs to, if any. | funding_instruments.instrument_id |
| flow_type | TEXT | Kind of flow, for example Wholesale funding maturity or Retail deposit outflow. |  |
| business_unit | TEXT | Unit that owns the flow: Treasury, Retail Banking, Business Banking or Finance. |  |
| direction | TEXT | Inflow or Outflow. |  |
| currency | TEXT | GBP, USD or EUR. |  |
| nominal | REAL | Amount of the flow in its own currency, always positive. |  |
| fx_rate_id | TEXT (optional) | Rate used to convert a USD or EUR flow to sterling. Empty for a sterling flow. | fx_rates.fx_rate_id |
| amount_gbp | REAL | Sterling amount of the flow as recorded, always positive (policy TP-05). |  |
| due_date | TEXT | Date the flow is contractually due, or the date the business unit forecasts it for. |  |
| expected_date | TEXT | Date the flow is expected to settle. The same as the due date unless the business unit expects it to be late. |  |
| contract_status | TEXT | Confirmed (a contract fixes it), Behavioural (a forecast from past behaviour) or Unconfirmed (expected, with no contract) (policy TP-02). |  |
| forecast_run | TEXT | Run of the forecasting system that loaded the flow. |  |
| entered_by | TEXT | Person whose run or entry loaded the flow. | staff.staff_id |
| entered_date | TEXT | Date the flow was first recorded. |  |
| notes | TEXT (optional) | Comment recorded with the flow. |  |

### funding_instruments

Thameside Bank's wholesale funding that matures, starts or pays interest within reach of the forecast: term deposits, certificates of deposit, repos and senior notes, with their terms.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| instrument_id | TEXT | Instrument identifier, for example FI-0031. Numbers rise with the time the deal was booked. |  |
| counterparty_id | TEXT | Lender or investor. | counterparties.counterparty_id |
| instrument_type | TEXT | Term deposit, Certificate of deposit, Repo (gilt collateral) or Senior unsecured note. |  |
| deal_status | TEXT | Executed (contract agreed and confirmed), or Agreed in principle, not signed. |  |
| deal_date | TEXT | Date the terms were agreed. |  |
| booked_at | TEXT | Date and time the deal was entered in the treasury dealing system. |  |
| start_date | TEXT | Date the money is received. |  |
| maturity_date | TEXT | Contractual maturity date, before any business-day adjustment. |  |
| currency | TEXT | GBP, USD or EUR. |  |
| principal | REAL | Amount borrowed, in the instrument's currency. |  |
| interest_rate_pct | REAL | Fixed annual interest rate, in percent. |  |
| day_count_basis | TEXT | ACT/365 (sterling) or ACT/360 (dollars and euros), or Semi-annual coupon for a note. |  |
| interest_at_maturity | REAL (optional) | Interest paid with the principal at maturity, in the instrument's currency (policy TP-06). Empty for a note, which pays coupons. |  |
| collateral | TEXT | Unsecured, or the collateral given. |  |
| terms | TEXT | Contractual terms in brief. |  |
| business_day_convention | TEXT | Rule for a payment date that falls on a weekend or bank holiday (policy TP-06). |  |
| rollover_of_id | TEXT (optional) | Instrument this deal replaces at its maturity, if it is a rollover. | funding_instruments.instrument_id |
| dealer_id | TEXT | Dealer who agreed the deal. | staff.staff_id |

### counterparties

The other parties to the forecast flows. Firms outside the group are identified by reference and a description only. Ratings are invented for the study.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| counterparty_id | TEXT | Counterparty reference, for example CP-0012. |  |
| counterparty_type | TEXT | Bank, Building society, Money market fund, Local authority, Corporate, Intra-group, Government, Bondholders, Investor, Customer pool or Other. |  |
| description | TEXT | What the counterparty is. Names are withheld outside the group and government. |  |
| credit_rating | TEXT | Long-term credit rating, or fund rating for a money market fund. Not rated, or Not applicable for customer pools, government and the group's own companies. |  |
| concentration_group | TEXT (optional) | Group of counterparties treated as one for concentration (policy TP-15), for example two entities of one banking group. Empty for customer pools. |  |
| country | TEXT | Country of incorporation, as an ISO 3166 two-letter code. |  |
| intra_group | TEXT | Yes for a company in Thameside Financial Group, otherwise No. |  |

### fx_rates

Exchange rates captured by the treasury dealing system at 16:00 London time, quoted as units of the currency per £1.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| fx_rate_id | TEXT | Rate identifier: FX, currency and valuation date, for example FX-USD-20260930. |  |
| valuation_date | TEXT | Date the rate was captured. |  |
| base_currency | TEXT | Currency the rate is quoted against: always GBP. |  |
| quote_currency | TEXT | Currency quoted: USD or EUR. |  |
| rate | REAL | Units of the quote currency per £1, to four decimal places. |  |
| rate_type | TEXT | Spot. |  |
| source | TEXT | Where the rate came from. |  |

### liquid_assets

The bank's liquid asset buffer at the as-at date: unencumbered assets it can sell or use as collateral to raise cash at once.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| asset_id | TEXT | Asset identifier, for example LA-02. |  |
| asset_class | TEXT | Reserves at the Bank of England, UK gilts, Supranational bonds or Covered bonds. |  |
| description | TEXT | What the holding is. |  |
| currency | TEXT | GBP. |  |
| market_value_gbp | REAL | Market value at the as-at date. |  |
| base_haircut_pct | REAL | Haircut the bank applies in the base case, in percent (policy TP-09). |  |

### liquidity_buckets

The ladder's reporting intervals, counted in calendar days after the as-at date, and the rule for placing a flow in one.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| bucket_id | TEXT | Bucket identifier, B1 (earliest) to B6. |  |
| bucket_name | TEXT | Name of the interval. |  |
| from_day | INTEGER | First day of the bucket, in calendar days after the as-at date. |  |
| to_day | INTEGER | Last day of the bucket, in calendar days after the as-at date. |  |
| start_date | TEXT | First date in the bucket. |  |
| end_date | TEXT | Last date in the bucket. |  |
| allocation_rule | TEXT | How a flow is placed in this bucket (policy TP-04). |  |

### staff

People in Thameside Bank's treasury and liquidity risk teams, and the chair of the Asset and Liability Committee (ALCO).

| Column | Type | Meaning | Points to |
|---|---|---|---|
| staff_id | TEXT | Staff identifier. |  |
| first_name | TEXT | First name. |  |
| last_name | TEXT | Surname. |  |
| job_title | TEXT | Job title. |  |
| team | TEXT | Team. |  |
| office | TEXT | Office: City, Canary Wharf or Croydon. |  |
| dealing_limit_gbp | REAL (optional) | Largest single wholesale deal, in sterling, the person may agree. Empty if the person may not deal. |  |
| email | TEXT | Work email address. |  |

### stress_scenarios

The three stress scenarios, one row per assumption: outflow shocks, reduced inflows, falls in sterling and funding haircuts on the buffer. Applied to the base case as policy TP-11 sets out.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| parameter_id | TEXT | Assumption identifier, for example SP-07. |  |
| scenario_id | TEXT | Scenario: ST-01, ST-02 or ST-03. |  |
| scenario_name | TEXT | Name of the scenario. |  |
| parameter_type | TEXT | Outflow increase, Inflow reduction, FX move or Funding haircut. |  |
| applies_to | TEXT | The flow type, currency or asset class the assumption applies to. |  |
| shock_pct | REAL | Size of the assumption, in percent: the increase or reduction in the flow, the fall in sterling, or the haircut added to the base haircut. |  |
| description | TEXT | The assumption in words. |  |

### treasury_policy

Thameside Bank's liquidity policy, version 3.1, in force from 1 July 2026: which flows the forecast includes, how each figure in the liquidity ladder is calculated, and the limits the ladder is tested against.

| Column | Type | Meaning | Points to |
|---|---|---|---|
| policy_id | TEXT | Policy reference, for example TP-05. |  |
| category | TEXT | Scope, Definition, Calculation, Stress or Limit. |  |
| title | TEXT | Short name of the policy. |  |
| statement | TEXT | The policy in full. |  |
| threshold | REAL (optional) | The number the policy uses, if it has one. |  |
| unit | TEXT (optional) | Unit of the threshold: GBP, percent or days. |  |

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
| spec.md | 1.1 | 2026-10-20 | Describes the data, how the forecast and ladder work, and the liquidity policy for any reader. Contains no answers | Treasury liquidity |
