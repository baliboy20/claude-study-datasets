"""The liquidity ladder, calculated from the database exactly as treasury_policy defines it.

Used by scenario.checks(), and by write_docs for the documents and the expected answers, so every figure has one source.
Two bases:
  recorded   the base-case flows as the data holds them (TP-02), with their recorded sterling amounts and dates.
  corrected  the same flows with the policy applied to every record: each USD and EUR flow converted at the as-at rate,
             each maturity on its instrument's payment date, inflows from unsigned deals left out, and any executed
             maturity in the horizon that has no flow added. Worked out from the rules, never from the answer key.
"""

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal

from generator.common import uk

AS_AT = dt.date(2026, 9, 30)
BUCKETS = [("B1", "Next day", 1, 1), ("B2", "2 to 7 days", 2, 7), ("B3", "8 to 14 days", 8, 14),
           ("B4", "15 days to 1 month", 15, 31), ("B5", "1 to 2 months", 32, 61), ("B6", "2 to 3 months", 62, 92)]
DAILY_LIMIT = 150_000_000
GROUP_LIMIT_PCT = 25.0
CENT = Decimal("0.01")


def money(x):
    """A sterling or currency amount rounded to the penny, halves up."""
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def iso(d):
    return d.isoformat() if d else None


def rows(con, sql, *args):
    cur = con.execute(sql, args)
    names = [c[0] for c in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def modified_following(d):
    if uk.is_working_day(d):
        return d
    n = uk.next_working_day(d)
    if n.month == d.month:
        return n
    while not uk.is_working_day(d):
        d -= dt.timedelta(days=1)
    return d


def interest(principal, rate_pct, start, payment, basis):
    """TP-06: principal x rate / 100 x days / basis, rounded to the penny."""
    days = (payment - start).days
    b = 365 if basis == "ACT/365" else 360
    return money(Decimal(str(principal)) * Decimal(str(rate_pct)) / 100 * days / b)


def convert(nominal, rate):
    """TP-05: nominal / rate, rounded to the penny."""
    return money(Decimal(str(nominal)) / Decimal(str(rate)))


def bucket_of(d):
    days = (d - AS_AT).days
    return next((b for b, _, lo, hi in BUCKETS if lo <= days <= hi), None)


def bucket_date(f):
    """TP-03: an inflow's expected date; the earlier of due and expected for an outflow."""
    due, exp = dt.date.fromisoformat(f["due_date"]), dt.date.fromisoformat(f["expected_date"])
    return exp if f["direction"] == "Inflow" else min(due, exp)


def base_flows(con, corrected=False):
    """The flows TP-02 puts in the base case, as dicts with amount (Decimal) and bucket."""
    insts = {i["instrument_id"]: i for i in rows(con, "SELECT * FROM funding_instruments")}
    spot = {r["quote_currency"]: r["rate"] for r in rows(con, "SELECT * FROM fx_rates WHERE valuation_date = ?", iso(AS_AT))}
    out = []
    linked = set()
    for f in rows(con, "SELECT * FROM cashflows ORDER BY cashflow_id"):
        if f["instrument_id"]:
            linked.add(f["instrument_id"])
        if not f["forecast_run"].startswith("BASE-"):
            continue
        f = dict(f)
        inst = insts.get(f["instrument_id"])
        status = f["contract_status"]
        if corrected and inst and f["direction"] == "Inflow" and inst["deal_status"] != "Executed":
            status = "Unconfirmed"
        if f["direction"] == "Inflow" and status == "Unconfirmed":
            continue
        f["amount"] = money(f["amount_gbp"])
        if corrected and f["currency"] != "GBP":
            f["amount"] = convert(f["nominal"], spot[f["currency"]])
        if corrected and inst and f["flow_type"] == "Wholesale funding maturity":
            pay = iso(modified_following(dt.date.fromisoformat(inst["maturity_date"])))
            f["due_date"] = f["expected_date"] = pay
        f["bucket"] = bucket_of(bucket_date(f))
        out.append(f)
    if corrected:
        for i in insts.values():
            pay = modified_following(dt.date.fromisoformat(i["maturity_date"]))
            if (i["deal_status"] == "Executed" and i["start_date"] <= iso(AS_AT) and bucket_of(pay) and i["instrument_id"] not in linked
                    and i["interest_at_maturity"] is not None):
                amount = money(i["principal"]) + money(i["interest_at_maturity"])
                gbp = amount if i["currency"] == "GBP" else convert(amount, spot[i["currency"]])
                out.append({"cashflow_id": None, "instrument_id": i["instrument_id"], "counterparty_id": i["counterparty_id"],
                            "flow_type": "Wholesale funding maturity", "direction": "Outflow", "currency": i["currency"],
                            "nominal": float(amount), "amount": gbp, "due_date": iso(pay), "expected_date": iso(pay),
                            "contract_status": "Confirmed", "forecast_run": "(added)", "bucket": bucket_of(pay)})
    return out


def params(con, scenario):
    return rows(con, "SELECT * FROM stress_scenarios WHERE scenario_id = ?", scenario) if scenario else []


def stressed(f, ps):
    """TP-11: amount x m / (1 - f / 100)."""
    m, fx = Decimal(1), Decimal(0)
    for p in ps:
        if p["parameter_type"] == "Outflow increase" and f["direction"] == "Outflow" and p["applies_to"] == f["flow_type"]:
            m = 1 + Decimal(str(p["shock_pct"])) / 100
        elif p["parameter_type"] == "Inflow reduction" and f["direction"] == "Inflow" and p["applies_to"] == f["flow_type"]:
            m = 1 - Decimal(str(p["shock_pct"])) / 100
        elif p["parameter_type"] == "FX move" and p["applies_to"] == f["currency"]:
            fx = Decimal(str(p["shock_pct"]))
    if m == 1 and fx == 0:
        return f["amount"]
    return money(f["amount"] * m / (1 - fx / 100))


def buffer(con, scenario=None):
    """TP-09, with a scenario's funding haircuts added."""
    add = {p["applies_to"]: p["shock_pct"] for p in params(con, scenario) if p["parameter_type"] == "Funding haircut"}
    return sum(money(Decimal(str(a["market_value_gbp"])) * (1 - (Decimal(str(a["base_haircut_pct"])) + Decimal(str(add.get(a["asset_class"], 0)))) / 100))
               for a in rows(con, "SELECT * FROM liquid_assets"))


def ladder(con, scenario=None, corrected=False):
    """One row per bucket: inflows, outflows, net gap (TP-07), cumulative gap (TP-08), position (TP-10)."""
    ps = params(con, scenario)
    flows = base_flows(con, corrected)
    buf = buffer(con, scenario)
    out, cum = [], Decimal(0)
    for bid, name, lo, hi in BUCKETS:
        ins = sum((stressed(f, ps) for f in flows if f["bucket"] == bid and f["direction"] == "Inflow"), Decimal(0))
        outs = sum((stressed(f, ps) for f in flows if f["bucket"] == bid and f["direction"] == "Outflow"), Decimal(0))
        cum += ins - outs
        out.append({"bucket_id": bid, "bucket_name": name, "inflows": ins, "outflows": outs, "net_gap": ins - outs,
                    "cumulative_gap": cum, "position": buf + cum})
    return out


def daily_third_party(con, corrected=False):
    """TP-14: wholesale funding maturities from counterparties outside the group, by day."""
    outside = {r["counterparty_id"] for r in rows(con, "SELECT counterparty_id FROM counterparties WHERE intra_group = 'No'")}
    days = {}
    for f in base_flows(con, corrected):
        if f["flow_type"] == "Wholesale funding maturity" and f["counterparty_id"] in outside:
            days[f["due_date"]] = days.get(f["due_date"], Decimal(0)) + f["amount"]
    return days


def group_shares(con, corrected=False):
    """TP-15: each concentration group's share of wholesale maturities from counterparties outside the group, in percent."""
    grp = {r["counterparty_id"]: r["concentration_group"]
           for r in rows(con, "SELECT counterparty_id, concentration_group FROM counterparties WHERE intra_group = 'No'")}
    totals = {}
    for f in base_flows(con, corrected):
        if f["flow_type"] == "Wholesale funding maturity" and f["counterparty_id"] in grp:
            g = grp[f["counterparty_id"]]
            totals[g] = totals.get(g, Decimal(0)) + f["amount"]
    whole = sum(totals.values())
    return {g: float(v / whole * 100) for g, v in sorted(totals.items(), key=lambda x: -x[1])}
