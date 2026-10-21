"""Insurance claims dataset.

Thameside Insurance, the general insurer of Thameside Financial Group, sells home and motor policies to people in London
and the South East. Its claims team is assessing the claims notified from Tuesday 1 to Wednesday 30 September 2026.
Each row of claims is one claim. Policyholders and suppliers are identified by reference only. The data was extracted
at 18:00 on Friday 16 October 2026, so some claims are settled and others are still open.
"""

import datetime as dt
from collections import defaultdict

from generator.common import firm, uk
from generator.common.dataset import Col, Table
from generator.common import staff_register
from generator.common.people import email_for

D = dt.date
MONTH_START = D(2026, 9, 1)
MONTH_END = D(2026, 9, 30)
EXTRACT = dt.datetime(2026, 10, 16, 18, 0)
EXTRACT_DATE = EXTRACT.date()
STORM_DATE = D(2026, 9, 23)
RESTORATION_PANEL_JOINED = D(2026, 6, 1)
SPECIFIED_LIMIT = "specified"

# ------------------------------------------------------------------ schema


def C(*a, **k):
    return Col(*a, **k)


SCHEMA = [
    Table("staff", "lookup", "People in the claims and customer outcomes teams who appear in the records.", [
        C("staff_id", "TEXT", "Staff identifier."),
        C("first_name", "TEXT", "First name."),
        C("last_name", "TEXT", "Surname."),
        C("job_title", "TEXT", "Job title."),
        C("team", "TEXT", "Team."),
        C("office", "TEXT", "Office: City, Canary Wharf or Croydon."),
        C("settlement_authority_gbp", "REAL", "Largest settlement the person may approve. Empty if they may not approve settlements.", required=False),
        C("email", "TEXT", "Work email address."),
    ]),
    Table("policy_clauses", "lookup", "The policy wordings, clause by clause: cover, limits, excesses, exclusions and claims conditions. Every policy uses the 2025 edition of its product's wording.", [
        C("clause_id", "TEXT", "Clause reference, for example H-5.1. H is the home wording; M is the motor wording."),
        C("product", "TEXT", "Home or Motor."),
        C("section", "TEXT", "Section of the wording, for example Buildings or General conditions."),
        C("clause_type", "TEXT", "Cover, Limit, Excess, Exclusion or Condition."),
        C("heading", "TEXT", "Clause heading."),
        C("wording", "TEXT", "The clause in full, as printed in the policy wording."),
    ]),
    Table("suppliers", "lookup", "Repairers, contractors and other suppliers who carry out work on claims. Names are withheld; suppliers are identified by reference.", [
        C("supplier_id", "TEXT", "Supplier reference, for example SUP-07. Numbers rise with the date the supplier joined the panel."),
        C("supplier_type", "TEXT", "What the supplier does, for example Drying and restoration."),
        C("panel_member", "TEXT", "Yes if the supplier is on Thameside Insurance's approved panel, No if appointed for one claim."),
        C("joined_panel_date", "TEXT", "Date the supplier joined the panel, or was first used."),
        C("area_covered", "TEXT", "Area the supplier works in."),
    ]),
    Table("policies", "lookup", "The policies the claims were made on, as they stood at the extract: cover dates, insured risks, exclusions, excesses and limits. Policyholders are identified by policy only.", [
        C("policy_id", "TEXT", "Policy reference, for example POL-0134. Numbers rise with the date the policy was first taken out."),
        C("product", "TEXT", "Home - Buildings and contents, Home - Buildings only, Home - Contents only, Motor - Comprehensive, or Motor - Third party, fire and theft."),
        C("sales_channel", "TEXT", "How the policy was first sold: Direct online, Price comparison website, Phone or Broker."),
        C("postcode", "TEXT", "Postcode of the insured home, or where the car is kept overnight."),
        C("property_type", "TEXT", "Home policies: type of home. Empty for motor.", required=False),
        C("vehicle", "TEXT", "Motor policies: make, model and year of the insured car. Empty for home.", required=False),
        C("vehicle_value_gbp", "REAL", "Motor policies: market value of the car, the most the policy pays for it (clause M-3.1). Empty for home.", required=False),
        C("first_incepted", "TEXT", "Date the policy was first taken out. Cover has run without a break since then."),
        C("cover_start", "TEXT", "Start of the current period of insurance. Equals first_incepted for a policy in its first year."),
        C("cover_end", "TEXT", "End of the current period of insurance."),
        C("policy_status", "TEXT", "Active, Cancelled or Lapsed, at the extract."),
        C("insured_risks", "TEXT", "Events the policy covers, as shown on the schedule."),
        C("optional_covers", "TEXT", "Optional covers bought, or None.", required=False),
        C("exclusions", "TEXT", "Exclusions and endorsements that apply, as shown on the schedule."),
        C("buildings_sum_insured_gbp", "REAL", "Most the policy pays for one Buildings claim (clause H-4.1). Empty if no Buildings cover.", required=False),
        C("contents_sum_insured_gbp", "REAL", "Most the policy pays for one Contents claim (clause H-4.1). Empty if no Contents cover.", required=False),
        C("single_article_limit_gbp", "REAL", "Most paid for any one valuable that is not specified on the schedule (clause H-3.2). Empty if no Contents cover.", required=False),
        C("specified_items", "TEXT", "Valuables listed on the schedule with their specified value, covered up to that value (clause H-3.2). Empty if none.", required=False),
        C("excess_standard_gbp", "REAL", "Home: excess for each claim (clause H-1.2). Empty for motor.", required=False),
        C("excess_escape_of_water_gbp", "REAL", "Home: excess for an escape of water claim, in place of the standard excess. Empty for motor.", required=False),
        C("excess_compulsory_gbp", "REAL", "Motor: compulsory excess for damage or theft (clause M-1.2). Empty for home.", required=False),
        C("excess_voluntary_gbp", "REAL", "Motor: voluntary excess chosen by the policyholder, added to the compulsory excess. Empty for home.", required=False),
        C("excess_windscreen_gbp", "REAL", "Motor: excess for a windscreen replacement. A repair carries no excess. Empty for home.", required=False),
        C("claims_declared_5y", "INTEGER", "Claims the policyholder declared for the five years before first taking out the policy."),
        C("annual_premium_gbp", "REAL", "Premium for the current period, including Insurance Premium Tax."),
    ]),
    Table("claims", "business", "Primary table: every claim notified by home and motor policyholders in London and the South East from 1 to 30 September 2026, as it stood at the extract.", [
        C("claim_id", "TEXT", "Claim reference, for example CLM-0027. Numbers rise with the time the claim was notified."),
        C("policy_id", "TEXT", "Policy the claim is made on.", "policies.policy_id"),
        C("claim_type", "TEXT", "Cause of the claim, for example Escape of water or Collision - not at fault."),
        C("section", "TEXT", "Section of the policy claimed under: Buildings, Contents, Buildings and contents, or Motor."),
        C("incident_date", "TEXT", "Date the loss or damage happened, as given by the policyholder."),
        C("notified_date", "TEXT", "Date the claim was reported to Thameside Insurance."),
        C("notified_channel", "TEXT", "How it was reported: Phone, Online or Broker."),
        C("description", "TEXT", "The policyholder's account of what happened, as recorded by the handler."),
        C("crime_reference", "TEXT", "Police crime reference number, for theft and malicious damage. Empty if none was given.", required=False),
        C("claimed_amount_gbp", "REAL", "Amount claimed: the policyholder's figure, or the first estimates."),
        C("excess_gbp", "REAL", "Excess the handler recorded as applying to the claim."),
        C("reserve_gbp", "REAL", "Amount set aside for what is still to be paid. Zero once the claim is settled, declined or withdrawn."),
        C("policy_status", "TEXT", "Status of the policy recorded when the claim was notified."),
        C("evidence_status", "TEXT", "Complete, Partial or Insufficient: whether the evidence needed under clause H-6 or M-5 has been received."),
        C("evidence_notes", "TEXT", "What evidence is held or still awaited.", required=False),
        C("proposed_settlement_gbp", "REAL", "Settlement the handler proposes: the agreed cost of the items less the excess. Empty until assessed, and for declined or withdrawn claims.", required=False),
        C("approved_by", "TEXT", "Person who approved the proposed settlement or the decline. Empty until approved.", "staff.staff_id", required=False),
        C("decision_date", "TEXT", "Date the settlement or decline was approved. Empty until then.", required=False),
        C("decline_clause_id", "TEXT", "Clause relied on to decline the claim. Empty unless declined.", "policy_clauses.clause_id", required=False),
        C("decision_notes", "TEXT", "The handler's reason for the decision. Empty until decided.", required=False),
        C("claim_status", "TEXT", "Open - assessing, Open - awaiting evidence, Open - repairs in progress, Open - settlement agreed, Settled, Declined or Withdrawn."),
        C("handler_id", "TEXT", "Claims handler.", "staff.staff_id"),
    ]),
    Table("claim_items", "business", "The parts of each claim: repairs, replacement items, estimates, reports and the documents that support them.", [
        C("item_id", "TEXT", "Item identifier."),
        C("claim_id", "TEXT", "Claim the item belongs to.", "claims.claim_id"),
        C("section", "TEXT", "Buildings, Contents or Motor."),
        C("category", "TEXT", "Kind of item, for example Repair, Replacement, Valuables, Trace and access, Drying, Report or Total loss."),
        C("description", "TEXT", "What the item is, or what the supplier found."),
        C("supplier_id", "TEXT", "Supplier who did the work or wrote the document. Empty for items the policyholder supplied.", "suppliers.supplier_id", required=False),
        C("document_type", "TEXT", "Evidence held for the item: Invoice, Estimate, Receipt, Bank statement, Photograph, Valuation, Report, or None."),
        C("document_ref", "TEXT", "Reference on the document, such as an invoice number. Empty if none.", required=False),
        C("document_date", "TEXT", "Date on the document. Empty if none.", required=False),
        C("service_start", "TEXT", "First day of work or equipment hire, where the document gives one.", required=False),
        C("service_end", "TEXT", "Last day of work or equipment hire, where the document gives one.", required=False),
        C("claimed_amount_gbp", "REAL", "Amount claimed or estimated for the item."),
        C("agreed_amount_gbp", "REAL", "Amount the handler agreed for the item. Empty until agreed, and for declined claims.", required=False),
    ]),
    Table("claim_payments", "business", "Money paid out or received on each claim to the extract: interim payments, final settlements, supplier payments, recoveries, excess refunds and complaint redress.", [
        C("payment_id", "TEXT", "Payment identifier, for example CPY-0042. Numbers rise with the payment date."),
        C("claim_id", "TEXT", "Claim the payment belongs to.", "claims.claim_id"),
        C("payment_date", "TEXT", "Date paid or received."),
        C("payment_type", "TEXT", "Interim payment, Final settlement, Supplier payment, Recovery, Salvage, Excess refund or Complaint redress."),
        C("direction", "TEXT", "Paid (by Thameside Insurance) or Received (a recovery or salvage)."),
        C("payee", "TEXT", "Policyholder, Supplier, Third-party insurer or Salvage agent."),
        C("supplier_id", "TEXT", "Supplier paid, for a supplier payment.", "suppliers.supplier_id", required=False),
        C("section", "TEXT", "Buildings, Contents or Motor."),
        C("gross_amount_gbp", "REAL", "Amount before the excess."),
        C("excess_deducted_gbp", "REAL", "Excess deducted from this payment. For a supplier payment the supplier collects it from the policyholder."),
        C("net_amount_gbp", "REAL", "Amount actually paid or received: gross less excess."),
        C("method", "TEXT", "Faster Payments, BACS or Cheque."),
    ]),
    Table("complaints", "business", "Complaints made about the claims, with how and when each was handled.", [
        C("complaint_id", "TEXT", "Complaint identifier."),
        C("claim_id", "TEXT", "Claim complained about.", "claims.claim_id"),
        C("received_date", "TEXT", "Date the complaint was received."),
        C("channel", "TEXT", "Phone, Email, Letter or Webchat."),
        C("reason", "TEXT", "What the policyholder complained about."),
        C("category", "TEXT", "Complaint category: Claim decision, Settlement amount, Delay, Repair quality or Service."),
        C("handler_id", "TEXT", "Complaints handler.", "staff.staff_id"),
        C("status", "TEXT", "Open, Closed - summary resolution, or Closed - final response."),
        C("resolved_date", "TEXT", "Date of the summary resolution or final response. Empty if open.", required=False),
        C("handling_days", "INTEGER", "Business days from receipt to resolution, or to the extract if still open."),
        C("outcome", "TEXT", "Upheld, Partially upheld or Not upheld. Empty if open.", required=False),
        C("outcome_notes", "TEXT", "The reason given for the outcome.", required=False),
        C("redress_gbp", "REAL", "Compensation offered. Zero if none."),
    ]),
]

# ------------------------------------------------------------------ reference data

# Each staff member's entry in the firm-wide staff register (generator/common/staff_register.py).
STAFF_REGISTER_IDS = {f"STF-{i:02d}": f"TFG-{40 + i:03d}" for i in range(1, 11)}
AUTHORITY = {"Head of Claims": 250_000, "Claims Manager": 100_000, "Claims Team Leader": 25_000, "Claims Handler": 5_000}
TEAMS = {"Claims Validation Investigator": "Claims Validation", "Complaints Handler": "Customer Outcomes",
         "Customer Outcomes Manager": "Customer Outcomes"}

HEAD, MANAGER, LEADER = "STF-01", "STF-02", "STF-03"
HANDLERS = ["STF-04", "STF-05", "STF-06", "STF-07"]
VALIDATION, COMPLAINTS, OUTCOMES = "STF-08", "STF-09", "STF-10"

CLAUSES = [
    # clause, product, section, type, heading, wording
    ("H-1.1", "Home", "General", "Cover", "Period of insurance",
     "We cover loss or damage that happens during the period of insurance shown on your schedule. When you renew, the new "
     "period follows the last one without a break. Loss or damage that happened in an earlier period is covered under the "
     "terms in force at that time. We do not cover anything that happened before you first took out this policy."),
    ("H-1.2", "Home", "General", "Excess", "Excess",
     "For each claim you pay the excess shown on your schedule. A claim for escape of water carries the escape of water "
     "excess instead of the standard excess. A claim for subsidence carries an excess of £1,000. If one incident leads to "
     "a claim under both the Buildings and the Contents sections, the excess applies to each section."),
    ("H-2.1", "Home", "Buildings", "Cover", "Insured events",
     "We cover your buildings against loss or damage caused by fire, lightning, explosion or smoke; storm; flood; escape "
     "of water or oil from a fixed installation; theft or attempted theft; subsidence, heave or landslip; impact; and "
     "malicious damage. Accidental damage is covered only if shown on your schedule."),
    ("H-2.2", "Home", "Buildings", "Cover", "Escape of water",
     "We cover damage caused by water escaping suddenly from a fixed water or heating installation, including the cost of "
     "finding the leak and making good (trace and access) up to £5,000. We do not cover the cost of repairing the part "
     "that failed."),
    ("H-2.3", "Home", "Buildings", "Cover", "Storm",
     "Storm means strong winds with gusts of at least 47 mph, heavy rain of at least 25 mm in an hour, or snow or hail "
     "heavy enough to damage hard surfaces. We do not cover damage to fences, gates or hedges caused by storm."),
    ("H-3.1", "Home", "Contents", "Cover", "Contents",
     "We cover your contents in the home against the events in clause H-2.1. Accidental damage to contents is covered "
     "only if shown on your schedule."),
    ("H-3.2", "Home", "Contents", "Limit", "Valuables",
     "Valuables are jewellery, watches, items of gold, silver or other precious metal, works of art and collections. For "
     "any one valuable we pay up to the single article limit on your schedule, unless the item is listed on your schedule "
     "as a specified item, when we pay up to its specified value. Valuables in total are limited to one third of the "
     "contents sum insured."),
    ("H-4.1", "Home", "General", "Limit", "Most we pay",
     "The most we pay for one claim under a section is the sum insured for that section shown on your schedule, less the "
     "excess."),
    ("H-5.1", "Home", "Exclusions", "Exclusion", "Wear and tear and gradual damage",
     "We do not cover loss or damage caused by wear and tear or gradual deterioration, or by anything that happens "
     "gradually, such as water seeping over time through a shower seal or from a slow leak."),
    ("H-5.2", "Home", "Exclusions", "Exclusion", "Unoccupied home",
     "We do not cover theft, escape of water or malicious damage once the home has been unoccupied for more than 60 days "
     "in a row."),
    ("H-6.1", "Home", "Claims conditions", "Condition", "Reporting theft",
     "You must report theft, attempted theft or malicious damage to the police as soon as possible and give us the crime "
     "reference number."),
    ("H-6.2", "Home", "Claims conditions", "Condition", "Proof of ownership and value",
     "For any item over £500 you must give us proof of ownership and value. This can be a receipt, a bank or card "
     "statement, a photograph showing the item, the original packaging or manual, or a valuation."),
    ("H-6.3", "Home", "Claims conditions", "Condition", "How we settle",
     "We may repair, replace or pay cash. Where we can repair or replace through our suppliers, we may pay the supplier "
     "directly. We may make an interim payment before the claim is settled."),
    ("M-1.1", "Motor", "General", "Cover", "Period of insurance",
     "We cover loss or damage that happens during the period of insurance shown on your schedule. When you renew, the new "
     "period follows the last one without a break. We do not cover anything that happened before you first took out this "
     "policy."),
    ("M-1.2", "Motor", "General", "Excess", "Excess",
     "For each claim for damage to or theft of your car you pay the compulsory excess and any voluntary excess shown on "
     "your schedule. A windscreen repair carries no excess; a windscreen replacement carries the windscreen excess "
     "instead. If the accident was not your fault and we recover our costs in full from the other driver's insurer, we "
     "refund your excess."),
    ("M-2.1", "Motor", "Your car", "Cover", "Damage to your car",
     "Under Comprehensive cover we pay to repair your car after accidental damage, fire, theft or malicious damage. If it "
     "cannot be repaired economically, we pay its market value (a total loss) and take the salvage."),
    ("M-2.2", "Motor", "Your car", "Cover", "Fire and theft",
     "Under Third party, fire and theft cover we pay for loss of or damage to your car caused by fire, theft or attempted "
     "theft only."),
    ("M-2.3", "Motor", "Your car", "Cover", "Windscreen",
     "Under Comprehensive cover we pay to repair or replace broken glass in the windscreen and windows through our "
     "windscreen supplier, including recalibrating driver-assistance cameras."),
    ("M-3.1", "Motor", "General", "Limit", "Most we pay",
     "The most we pay for loss of or damage to your car is its market value at the time of the loss, less the excess."),
    ("M-4.1", "Motor", "Exclusions", "Exclusion", "Keys and security",
     "We do not cover theft of your car, or of anything from it, if the keys were left in or on the car, or it was left "
     "unlocked or with the engine running while unattended."),
    ("M-4.2", "Motor", "Exclusions", "Exclusion", "Drivers",
     "We do not cover the car while it is driven by anyone not named on your certificate of motor insurance."),
    ("M-5.1", "Motor", "Claims conditions", "Condition", "Reporting theft and evidence",
     "You must report theft or malicious damage to the police as soon as possible and give us the crime reference number. "
     "For a total loss you must send us the logbook (V5C) and all keys."),
]

SUPPLIERS = [
    # key, type, panel, joined, area
    ("loss", "Loss adjuster", "Yes", "2014-03-03", "London and the South East"),
    ("plumb_n", "Plumbing and leak detection", "Yes", "2016-05-09", "North and East London, Essex"),
    ("plumb_s", "Plumbing and leak detection", "Yes", "2017-09-18", "South London, Surrey and Kent"),
    ("build_n", "Building repairs", "Yes", "2015-07-06", "North and East London, Hertfordshire, Essex"),
    ("build_s", "Building repairs", "Yes", "2016-02-15", "South London, Surrey, Kent and Sussex"),
    ("roof", "Roofing", "Yes", "2018-10-01", "London and the South East"),
    ("glass_h", "Glazing and locksmith", "Yes", "2019-04-08", "London and the South East"),
    ("repl", "Replacement goods (electricals and furniture)", "Yes", "2015-01-12", "UK-wide"),
    ("jewel", "Jewellery replacement and valuation", "Yes", "2017-03-20", "UK-wide"),
    ("dry_old", "Drying and restoration", "Yes", "2018-06-11", "London and the South East"),
    ("dry_new", "Drying and restoration", "Yes", "2026-06-01", "London, Surrey and Kent"),
    ("motor_e", "Approved motor repairer", "Yes", "2013-11-04", "East London and Essex"),
    ("motor_s", "Approved motor repairer", "Yes", "2014-08-18", "South London and Surrey"),
    ("motor_w", "Approved motor repairer", "Yes", "2016-11-07", "West London, Berkshire and Hertfordshire"),
    ("motor_k", "Approved motor repairer", "Yes", "2019-02-25", "Kent and Sussex"),
    ("screen", "Windscreen repair and replacement", "Yes", "2015-05-11", "UK-wide"),
    ("engineer", "Independent motor engineer (valuations)", "Yes", "2015-09-14", "London and the South East"),
    ("plumb_x", "Plumbing (policyholder's own)", "No", "2026-09-14", "Mitcham"),
]

NORTH = {"N", "E", "EN", "IG", "RM", "CM", "SS", "AL", "WD", "HA", "NW"}
# area: (outward codes, town)
AREAS = [
    ("SE8", "London"), ("SE15", "London"), ("SE23", "London"), ("SE9", "London"), ("SW16", "London"),
    ("SW19", "London"), ("SW11", "London"), ("W5", "London"), ("W13", "London"), ("NW10", "London"),
    ("N17", "London"), ("N8", "London"), ("N16", "London"), ("E17", "London"), ("E11", "London"), ("E14", "London"),
    ("CR0", "Croydon"), ("CR4", "Mitcham"), ("SM1", "Sutton"), ("BR1", "Bromley"), ("KT1", "Kingston upon Thames"),
    ("HA1", "Harrow"), ("IG1", "Ilford"), ("RM1", "Romford"), ("DA1", "Dartford"), ("TN13", "Sevenoaks"),
    ("ME15", "Maidstone"), ("GU1", "Guildford"), ("RH2", "Reigate"), ("RH10", "Crawley"), ("BN1", "Brighton"),
    ("RG1", "Reading"), ("SL1", "Slough"), ("WD17", "Watford"), ("AL1", "St Albans"), ("CM1", "Chelmsford"),
    ("SS1", "Southend-on-Sea"),
]

VEHICLES = [
    ("Ford Fiesta 1.0 EcoBoost", 2019, 9_250), ("Vauxhall Corsa 1.2", 2020, 8_400),
    ("Volkswagen Golf 1.5 TSI", 2021, 17_800), ("Toyota Yaris 1.5 Hybrid", 2022, 15_600),
    ("Nissan Qashqai 1.3 DIG-T", 2020, 14_900), ("Kia Sportage 1.6 T-GDi", 2021, 19_200),
    ("BMW 320d M Sport", 2019, 17_400), ("Mercedes-Benz A180 Sport", 2020, 16_300),
    ("Tesla Model 3 Long Range", 2022, 24_500), ("Hyundai i10 1.0", 2018, 6_200),
    ("Skoda Octavia 2.0 TDI", 2019, 12_100), ("MINI Cooper 1.5", 2021, 15_200),
    ("Toyota Prius 1.8 Hybrid", 2017, 10_400), ("Peugeot 208 1.2 PureTech", 2022, 12_900),
    ("Honda Jazz 1.5 e:HEV", 2021, 16_100), ("Ford Kuga 2.5 PHEV", 2022, 22_700),
    ("Audi A3 Sportback 30 TFSI", 2020, 16_900), ("Renault Clio 1.0 TCe", 2019, 8_100),
]


HOME_RISKS = ("Fire, lightning, explosion and smoke; storm; flood; escape of water or oil; theft; subsidence, heave and "
              "landslip; impact; malicious damage")
MOTOR_RISKS = {"Motor - Comprehensive": "Accidental damage, fire, theft, malicious damage, windscreen, third-party liability",
               "Motor - Third party, fire and theft": "Fire, theft, third-party liability"}

# ------------------------------------------------------------------ helpers


def iso(d):
    return d.isoformat() if d else None


def sep(n):
    return D(2026, 9, n)


def oct_(n):
    return D(2026, 10, n)


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def business_days(a, b):
    """Business days after a, up to and including b."""
    n, d = 0, a
    while d < b:
        d += dt.timedelta(days=1)
        if uk.is_working_day(d):
            n += 1
    return n


def gbp(x):
    return f"£{x:,.2f}"


def r2(x):
    return round(float(x), 2)


class Builder:
    def __init__(self, rng):
        self.rng = rng
        self.rows = defaultdict(list)
        self.cases, self.case_records = [], []
        self.policies, self.claims = [], []
        self.complaints = []
        self.sup = {}
        self.used_postcodes = set()
        self.K = {}  # planted claims by key
        self.handler_cycle = 0

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
                "team": TEAMS.get(p["job_title"], "Claims"), "office": p["office"],
                "settlement_authority_gbp": float(AUTHORITY[p["job_title"]]) if p["job_title"] in AUTHORITY else None,
                "email": email_for(p["first_name"], p["last_name"], firm.EMAIL_DOMAIN)})
        self.rows["policy_clauses"] = [dict(zip(["clause_id", "product", "section", "clause_type", "heading", "wording"], c))
                                       for c in CLAUSES]
        for i, (key, stype, panel, joined, area) in enumerate(sorted(SUPPLIERS, key=lambda s: s[3]), start=1):
            self.sup[key] = {"supplier_id": f"SUP-{i:02d}", "supplier_type": stype, "panel_member": panel,
                             "joined_panel_date": joined, "area_covered": area}
        self.rows["suppliers"] = list(self.sup.values())

    def postcode(self, outward=None):
        rng = self.rng
        while True:
            out = outward or rng.choice(AREAS)[0]
            pc = uk.postcode(rng, out)
            if pc not in self.used_postcodes:
                self.used_postcodes.add(pc)
                return pc

    def policy(self, product, *, first=None, start=None, channel=None, postcode=None, outward=None, contents=None,
               buildings=None, sal=2_000, specified=None, std=None, eow=None, vehicle=None, comp=250, vol=None,
               status="Active", optional=None, exclusions=None, declared=None):
        rng = self.rng
        home = product.startswith("Home")
        if start is None:
            # Renewal day spread over the year before the claim month; most policies have been renewed at least once.
            # Renewal day in the year before the claim month, so the current period covers all of September 2026.
            start = D(2025, 10, 1) + dt.timedelta(days=rng.randint(0, 323))
        if first is None:
            first = add_years(start, -rng.choice([0, 1, 1, 2, 3, 4, 5, 7, 9]))
        p = {"product": product, "sales_channel": channel or rng.choice(
                ["Direct online", "Price comparison website", "Price comparison website", "Phone", "Broker"]),
             "postcode": postcode or self.postcode(outward), "first_incepted": iso(first), "cover_start": iso(start),
             "cover_end": iso(add_years(start, 1) - dt.timedelta(days=1)), "policy_status": status,
             "claims_declared_5y": declared if declared is not None else rng.choice([0, 0, 0, 0, 1, 1, 2])}
        if home:
            has_b = product != "Home - Contents only"
            has_c = product != "Home - Buildings only"
            std = std if std is not None else rng.choice([100, 100, 250])
            p.update({
                "property_type": rng.choice(["Flat", "Flat", "Maisonette", "Terraced house"]) if not has_b
                else rng.choice(["Terraced house", "Semi-detached house", "Detached house", "End-of-terrace house"]),
                "vehicle": None, "vehicle_value_gbp": None, "insured_risks": HOME_RISKS,
                "optional_covers": optional if optional is not None else rng.choice(
                    ["Accidental damage (buildings and contents)", "Home emergency", "Legal expenses", "None",
                     "Accidental damage (buildings and contents); Legal expenses"]),
                "exclusions": exclusions or "Standard exclusions in clauses H-5.1 and H-5.2",
                "buildings_sum_insured_gbp": float(buildings or rng.choice([275_000, 320_000, 380_000, 450_000, 520_000, 640_000])) if has_b else None,
                "contents_sum_insured_gbp": float(contents or rng.choice([30_000, 40_000, 50_000, 60_000, 75_000])) if has_c else None,
                "single_article_limit_gbp": float(sal) if has_c else None, "specified_items": specified,
                "excess_standard_gbp": float(std), "excess_escape_of_water_gbp": float(eow or (350 if std == 100 else 500)),
                "excess_compulsory_gbp": None, "excess_voluntary_gbp": None, "excess_windscreen_gbp": None,
                "annual_premium_gbp": r2(rng.uniform(190, 520) if has_b else rng.uniform(95, 210))})
        else:
            v = vehicle or rng.choice(VEHICLES)
            p.update({"property_type": None, "vehicle": f"{v[0]}, {v[1]}", "vehicle_value_gbp": float(v[2]),
                      "insured_risks": MOTOR_RISKS[product], "optional_covers": optional if optional is not None else rng.choice(
                          ["Protected no-claims discount", "Courtesy car", "None", "Protected no-claims discount; Legal expenses"]),
                      "exclusions": exclusions or "Standard exclusions in clauses M-4.1 and M-4.2",
                      "buildings_sum_insured_gbp": None, "contents_sum_insured_gbp": None, "single_article_limit_gbp": None,
                      "specified_items": None, "excess_standard_gbp": None, "excess_escape_of_water_gbp": None,
                      "excess_compulsory_gbp": float(comp),
                      "excess_voluntary_gbp": float(vol if vol is not None else rng.choice([0, 100, 250, 250, 500])),
                      "excess_windscreen_gbp": 100.0, "annual_premium_gbp": r2(rng.uniform(420, 1_150))})
        self.policies.append(p)
        return p

    def handler(self):
        self.handler_cycle += 1
        return HANDLERS[self.handler_cycle % len(HANDLERS)]

    def claim(self, pol, ctype, section, incident, notified, desc, *, channel=None, crime=None, status="Settled",
              evidence="Complete", notes=None, decline=None, handler=None, excess=None, key=None):
        rng = self.rng
        c = {"pol": pol, "claim_type": ctype, "section": section, "incident_date": iso(incident),
             "notified": dt.datetime.combine(notified, dt.time(rng.randint(8, 19), rng.randint(0, 59), rng.randint(0, 59))),
             "notified_channel": channel or rng.choice(["Phone", "Phone", "Online", "Online", "Broker"] if pol["sales_channel"] == "Broker" else ["Phone", "Phone", "Online"]),
             "description": desc, "crime_reference": crime, "status": status, "evidence": evidence, "notes": notes,
             "decline": decline, "handler": handler or self.handler(), "items": [], "payments": [], "excess": excess,
             "approved_by": None, "decision_date": None, "decision_notes": None, "proposed": None, "reserve": None}
        if c["excess"] is None:
            c["excess"] = self.default_excess(c)
        self.claims.append(c)
        if key:
            self.K[key] = c
        return c

    def default_excess(self, c):
        p, t = c["pol"], c["claim_type"]
        if p["product"].startswith("Home"):
            if t == "Escape of water":
                return p["excess_escape_of_water_gbp"]
            if t == "Subsidence":
                return 1_000.0
            return p["excess_standard_gbp"]
        if t == "Windscreen - repair":
            return 0.0
        if t == "Windscreen - replacement":
            return p["excess_windscreen_gbp"]
        return p["excess_compulsory_gbp"] + p["excess_voluntary_gbp"]

    def item(self, c, section, category, desc, claimed, *, agreed="same", supplier=None, doc="Invoice", ref=None,
             doc_date=None, start=None, end=None):
        it = {"section": section, "category": category, "description": desc,
              "supplier_id": self.sup[supplier]["supplier_id"] if supplier else None, "supplier_key": supplier,
              "document_type": doc, "document_ref": ref, "document_date": iso(doc_date), "service_start": iso(start),
              "service_end": iso(end), "claimed_amount_gbp": r2(claimed),
              "agreed_amount_gbp": r2(claimed) if agreed == "same" else (None if agreed is None else r2(agreed))}
        c["items"].append(it)
        return it

    def pay(self, c, d, ptype, payee, section, gross, excess=0.0, supplier=None, direction="Paid", method=None):
        d = uk.next_working_day(d)
        p = {"date": d, "payment_type": ptype, "direction": direction, "payee": payee,
             "supplier_id": self.sup[supplier]["supplier_id"] if supplier else None, "section": section,
             "gross_amount_gbp": r2(gross), "excess_deducted_gbp": r2(excess), "net_amount_gbp": r2(gross - excess),
             "method": method or ("BACS" if payee in ("Supplier", "Third-party insurer", "Salvage agent") else "Faster Payments")}
        c["payments"].append(p)
        return p

    def decide(self, c, d, approver=None):
        """Records the proposed settlement as the agreed items less the excess, and who approved it."""
        agreed = sum(i["agreed_amount_gbp"] or 0 for i in c["items"])
        c["proposed"] = r2(agreed - c["excess"])
        c["approved_by"] = approver or self.approver(c["proposed"], c["handler"])
        c["decision_date"] = d

    def approver(self, amount, handler):
        if amount <= AUTHORITY["Claims Handler"]:
            return handler
        if amount <= AUTHORITY["Claims Team Leader"]:
            return LEADER
        if amount <= AUTHORITY["Claims Manager"]:
            return MANAGER
        return HEAD

    def excess_left(self, c, section):
        """Excess still to be taken for a section: the claim's excess less what earlier payments deducted.
        A claim under both Buildings and Contents carries the excess for each section (clause H-1.2)."""
        per = c["excess"] / 2 if c["section"] == "Buildings and contents" else c["excess"]
        taken = sum(p["excess_deducted_gbp"] for p in c["payments"] if p["section"] == section and p["payment_type"] != "Excess refund")
        return r2(per - taken)

    def settle_suppliers(self, c, start, *, gap=(3, 9)):
        """Pays each invoiced supplier item, then any policyholder items, taking the excess from the first payments for each section."""
        rng = self.rng
        d = start
        # Suppliers are paid on their invoice (or on supplying a replacement), not on an estimate or report.
        sup_items = [i for i in c["items"] if i["supplier_key"] and (i["agreed_amount_gbp"] or 0) > 0
                     and i["document_type"] not in ("Estimate", "Report", "None")]
        own = [i for i in c["items"] if not i["supplier_key"] and (i["agreed_amount_gbp"] or 0) > 0]
        for it in sup_items:
            ex = min(self.excess_left(c, it["section"]), it["agreed_amount_gbp"])
            self.pay(c, d, "Supplier payment", "Supplier", it["section"], it["agreed_amount_gbp"], ex, supplier=it["supplier_key"])
            d = uk.add_working_days(d, rng.randint(*gap))
        by_sec = defaultdict(float)
        for it in own:
            by_sec[it["section"]] += it["agreed_amount_gbp"]
        for sec, amt in by_sec.items():
            self.pay(c, d, "Final settlement", "Policyholder", sec, amt, min(self.excess_left(c, sec), amt))
        return d

    def crime_ref(self, outward):
        rng = self.rng
        letters = "".join(ch for ch in outward if ch.isalpha())
        if letters in ("ME", "TN", "DA", "CT"):
            return f"Kent Police 46/{rng.randint(100000, 199999)}/26"
        if letters in ("GU", "RH", "KT") and outward not in ("KT1",):
            return f"Surrey Police PR/4526{rng.randint(1000000, 9999999)}"
        if letters == "BN":
            return f"Sussex Police 47260{rng.randint(100000, 199999)}"
        if letters in ("RG", "SL"):
            return f"Thames Valley Police 432600{rng.randint(10000, 99999)}"
        if letters in ("CM", "SS"):
            return f"Essex Police 42/{rng.randint(100000, 199999)}/26"
        if letters in ("AL", "WD"):
            return f"Hertfordshire Constabulary 41/{rng.randint(60000, 99999)}/26"
        return f"Metropolitan Police {rng.randint(5200000, 5299999)}/26"

    # ---- normal claims

    def area_supplier(self, pol, north, south):
        letters = "".join(ch for ch in pol["postcode"].split()[0] if ch.isalpha())
        return north if letters in NORTH else south

    def motor_repairer(self, pol):
        letters = "".join(ch for ch in pol["postcode"].split()[0] if ch.isalpha())
        if letters in ("E", "IG", "RM", "CM", "SS", "N"):
            return "motor_e"
        if letters in ("W", "NW", "HA", "RG", "SL", "WD", "AL"):
            return "motor_w"
        if letters in ("ME", "TN", "DA", "BN", "RH"):
            return "motor_k"
        return "motor_s"

    def notify_day(self, lo=1, hi=30):
        return sep(self.rng.randint(lo, hi))

    def finish(self, c, decided, *, pay_from=None, notes="Supplier invoices and photographs held.", approver=None):
        """Agrees the items, records the decision, and pays the suppliers and policyholder."""
        self.decide(c, decided, approver)
        c["decision_notes"] = notes
        self.settle_suppliers(c, pay_from or uk.add_working_days(decided, self.rng.randint(2, 6)))

    def normal_home(self):
        rng = self.rng
        bc = "Home - Buildings and contents"
        ad = "Accidental damage (buildings and contents)"

        # Escape of water: trace and access, drying, then reinstatement.
        eow = [
            ("Water coming through the kitchen ceiling from the bathroom above; a pipe joint under the bath had failed.", "bath waste"),
            ("Radiator valve in the front bedroom split overnight; water through to the living room ceiling.", "radiator valve"),
            ("Hot water cylinder in the airing cupboard leaked suddenly; landing and bedroom carpets soaked.", "cylinder"),
            ("Washing machine supply hose burst during a wash; kitchen floor and units damaged.", "machine hose"),
            ("Pipe under the bathroom floor burst; water found coming through the hall ceiling.", "floor pipe"),
            ("Toilet cistern feed split; water through to the kitchen below.", "cistern"),
            ("Combi boiler pressure relief pipe failed inside the loft; bedroom ceiling stained and sagging.", "boiler"),
            ("Pipe to the outside tap burst inside the utility room wall.", "utility pipe"),
            ("Ensuite shower mixer connection failed suddenly; water through the dining room ceiling.", "shower mixer"),
            ("Kitchen sink waste pipe joint came apart; water under the units and through to the cellar.", "sink waste"),
            ("Burst pipe in the first-floor bathroom while the family were away for the weekend.", "burst"),
        ]
        for i, (desc, _) in enumerate(eow):
            pol = self.policy(bc if i % 4 else "Home - Buildings only", optional=ad if i % 3 == 0 else None)
            n = self.notify_day(1, 28)
            inc = n - dt.timedelta(days=rng.randint(0, 2))
            c = self.claim(pol, "Escape of water", "Buildings", inc, n, desc)
            plumb = self.area_supplier(pol, "plumb_n", "plumb_s")
            dry = "dry_new" if (plumb == "plumb_s" and i in (1, 6, 9)) else "dry_old"
            t_date = n + dt.timedelta(days=rng.randint(1, 3))
            self.item(c, "Buildings", "Trace and access", "Leak located, access made and making good", rng.randint(28, 95) * 10 + rng.choice([0, 0.5]),
                      supplier=plumb, doc_date=t_date)
            ds = t_date + dt.timedelta(days=1)
            de = ds + dt.timedelta(days=rng.randint(4, 9))
            self.item(c, "Buildings", "Drying", f"{rng.randint(2, 4)} dehumidifiers and {rng.randint(1, 3)} air movers, with moisture readings",
                      round(rng.uniform(780, 2_400), 2), supplier=dry, doc_date=de + dt.timedelta(days=1), start=ds, end=de)
            build = self.area_supplier(pol, "build_n", "build_s")
            reinst = round(rng.uniform(1_600, 6_800), 2)
            if n <= sep(12):
                self.item(c, "Buildings", "Repair", "Reinstatement: replaster, redecorate and replace damaged flooring", reinst,
                          supplier=build, doc_date=de + dt.timedelta(days=rng.randint(10, 16)))
                self.finish(c, de + dt.timedelta(days=rng.randint(9, 15)), pay_from=de + dt.timedelta(days=3))
            elif n <= sep(24):
                self.item(c, "Buildings", "Repair", "Reinstatement estimate: replaster, redecorate and replace damaged flooring", reinst,
                          supplier=build, doc="Estimate", doc_date=de + dt.timedelta(days=2))
                self.finish(c, de + dt.timedelta(days=4), pay_from=de + dt.timedelta(days=3),
                            notes="Trace and access and drying invoiced; reinstatement agreed on estimate.")
                c["status"] = "Open - repairs in progress"
            else:
                self.item(c, "Buildings", "Repair", "Reinstatement estimate awaited", reinst, agreed=None, supplier=build, doc="None")
                for it in c["items"][:2]:
                    it["agreed_amount_gbp"] = None
                c["status"], c["evidence"], c["notes"] = "Open - assessing", "Partial", "Drying in progress; reinstatement estimate awaited."

        # Storm on 23 September: roofs, ceilings and two claims from an earlier windy day.
        roofs = ["Ridge tiles blown off; rain through the loft into the back bedroom.",
                 "Several roof tiles lifted; water stain spreading on the landing ceiling.",
                 "Chimney flashing torn away; water running down the chimney breast.",
                 "Flat roof felt over the kitchen extension torn off by the wind.",
                 "Tree branch broke two rear windows and damaged the gutter.",
                 "Slates slipped on the front roof slope; leak into the front bedroom.",
                 "Lead valley lifted; rain through the ceiling of the stairwell.",
                 "Roof tiles blown onto the drive; daylight visible from the loft.",
                 "Rain driven in under the roof edge; bedroom ceiling sagging.",
                 "Ridge capping dislodged along the whole terrace roof; leak into the loft room."]
        for i, desc in enumerate(roofs):
            pol = self.policy(bc if i % 3 else "Home - Buildings only")
            n = STORM_DATE + dt.timedelta(days=min(6, i // 2))
            c = self.claim(pol, "Storm", "Buildings", STORM_DATE, n, desc,
                           channel=rng.choice(["Phone", "Phone", "Online"]))
            temp = round(rng.uniform(180, 420), 2)
            self.item(c, "Buildings", "Repair", "Emergency temporary repair: tarpaulin and make safe", temp, supplier="roof",
                      doc_date=n + dt.timedelta(days=1))
            perm = round(rng.uniform(450, 3_600), 2)
            if i < 4:
                self.item(c, "Buildings", "Repair", "Permanent roof repair", perm, supplier="roof", doc="Estimate",
                          doc_date=n + dt.timedelta(days=rng.randint(5, 9)))
                self.finish(c, n + dt.timedelta(days=rng.randint(10, 14)), pay_from=n + dt.timedelta(days=6),
                            notes="Weather station records gusts above 47 mph on 23 September; roofer's estimate agreed.")
                c["status"] = "Open - repairs in progress"
            else:
                self.item(c, "Buildings", "Repair", "Permanent roof repair: roofer's report and photographs awaited", perm, agreed=None,
                          supplier="roof", doc="None")
                c["items"][0]["agreed_amount_gbp"] = c["items"][0]["claimed_amount_gbp"]
                self.pay(c, n + dt.timedelta(days=rng.randint(7, 12)), "Supplier payment", "Supplier", "Buildings", temp,
                         min(temp, c["excess"]), supplier="roof")
                c["status"], c["evidence"], c["notes"] = "Open - awaiting evidence", "Partial", "Roofer's report and photographs awaited."
        pol = self.policy(bc)
        c = self.claim(pol, "Storm", "Buildings", sep(7), sep(8), "Six fence panels and two posts blown down in high winds.")
        self.item(c, "Buildings", "Repair", "Replacement fence panels and posts (policyholder's quote)", 640.00, agreed=None, doc="Estimate",
                  doc_date=sep(8))
        c.update(status="Declined", decline="H-2.3", approved_by=LEADER, decision_date=sep(10),
                 decision_notes="Declined under H-2.3: storm damage to fences is not covered.")
        pol = self.policy(bc)
        c = self.claim(pol, "Storm", "Buildings", sep(7), sep(9), "Two ridge tiles came off in high winds; no water inside.")
        self.item(c, "Buildings", "Repair", "Refix two ridge tiles", 185.00, agreed=None, supplier="roof", doc="Estimate", doc_date=sep(10))
        c.update(status="Withdrawn", evidence="Partial", notes="Policyholder withdrew: cost below the excess.")

        # Accidental damage to contents.
        ad_items = [("55-inch television knocked off its stand", 649.00, "repl"), ("Laptop damaged by a spilt drink", 1_199.00, "repl"),
                    ("Red wine spilt on a cream living room carpet", 870.00, None), ("Glass dining table top cracked", 540.00, None),
                    ("Sofa torn by a dog", 1_380.00, None), ("Tablet dropped on a tiled floor", 529.00, "repl"),
                    ("Oven door glass shattered", 320.00, None), ("Hearing aids dropped down a drain", 2_450.00, None),
                    ("Games console and controller knocked into the bath", 489.00, "repl")]
        for i, (desc, amt, sup) in enumerate(ad_items):
            pol = self.policy(bc, optional=ad)
            n = self.notify_day(1, 26)
            c = self.claim(pol, "Accidental damage", "Contents", n - dt.timedelta(days=rng.randint(0, 4)), n, desc + ".")
            doc = "Receipt" if amt > 500 else "Photograph"
            self.item(c, "Contents", "Replacement", ("Replacement through panel supplier: " if sup else "Cash settlement: ") + desc.lower(),
                      amt, supplier=sup, doc=doc, doc_date=n - dt.timedelta(days=rng.randint(200, 1_400)) if doc == "Receipt" else n)
            if i == 6:
                c.update(status="Withdrawn", evidence="Complete", notes="Policyholder withdrew to protect the no-claims record.")
                c["items"][0]["agreed_amount_gbp"] = None
                continue
            self.finish(c, n + dt.timedelta(days=rng.randint(3, 9)), notes="Proof of ownership and photographs held.")

        # Accidental damage to buildings.
        for desc, cat, amt, sup in [("Foot through the bedroom ceiling while in the loft.", "Repair", 620.00, "build"),
                                    ("Heavy bottle dropped into the bathroom basin; basin cracked.", "Repair", 395.00, "plumb"),
                                    ("Football broke the double-glazed patio door.", "Repair", 465.00, "glass_h")]:
            pol = self.policy(bc, optional=ad)
            n = self.notify_day(2, 25)
            c = self.claim(pol, "Accidental damage", "Buildings", n - dt.timedelta(days=1), n, desc)
            s = sup if sup == "glass_h" else self.area_supplier(pol, sup + "_n", sup + "_s")
            self.item(c, "Buildings", cat, desc.split(";")[0].rstrip("."), amt, supplier=s, doc_date=n + dt.timedelta(days=rng.randint(3, 8)))
            self.finish(c, n + dt.timedelta(days=rng.randint(6, 10)))

        # Theft: burglaries with crime references and proof of ownership.
        thefts = [
            ("Burglary through a rear window while the family were at work.", [("Laptop", "Replacement", 1_099.00, "Receipt", "repl"), ("Gold bracelet", "Valuables", 1_350.00, "Valuation", "jewel"), ("Cash", "Replacement", 150.00, "None", None)]),
            ("Front door forced overnight; bicycle and tools taken from the hall.", [("Road bicycle", "Replacement", 1_480.00, "Receipt", None), ("Cordless drill set", "Replacement", 189.00, "Photograph", None)]),
            ("Burglary while on holiday; television and jewellery taken.", [("65-inch television", "Replacement", 899.00, "Receipt", "repl"), ("Diamond earrings", "Valuables", 1_850.00, "Valuation", "jewel")]),
            ("Shed broken into; lawnmower and bicycles taken.", [("Petrol lawnmower", "Replacement", 429.00, "Photograph", None), ("Two children's bicycles", "Replacement", 520.00, "Receipt", None)]),
            ("Burglary through the back door; games console and watch taken.", [("Games console", "Replacement", 479.00, "Receipt", "repl"), ("Wristwatch", "Valuables", 1_200.00, "Receipt", None)]),
            ("Handbag and laptop taken from the hall by a distraction burglar.", [("Laptop", "Replacement", 949.00, "Receipt", None), ("Handbag", "Replacement", 310.00, "Photograph", None)]),
            ("Burglary through a side window; laptop and camera taken.", [("Laptop", "Replacement", 1_299.00, "None", None), ("Camera and lens", "Replacement", 1_150.00, "None", None)]),
        ]
        for i, (desc, its) in enumerate(thefts):
            pol = self.policy(bc if i % 2 else "Home - Contents only")
            n = self.notify_day(2, 27)
            c = self.claim(pol, "Theft", "Contents", n - dt.timedelta(days=rng.randint(0, 1)), n, desc,
                           crime=self.crime_ref(pol["postcode"].split()[0]))
            for name, cat, amt, doc, sup in its:
                self.item(c, "Contents", cat, name if not sup else f"{name}: replacement through panel supplier", amt, supplier=sup, doc=doc,
                          doc_date=None if doc in ("None", "Photograph") else (n + dt.timedelta(days=4) if doc == "Valuation" else n - dt.timedelta(days=rng.randint(150, 1_500))))
            if i == 6:
                for it in c["items"]:
                    it["agreed_amount_gbp"] = None
                c.update(status="Open - awaiting evidence", evidence="Insufficient",
                         notes="Proof of ownership requested for the laptop and camera under H-6.2; not yet received.")
                continue
            self.finish(c, n + dt.timedelta(days=rng.randint(6, 12)), notes="Crime reference and proof of ownership held.")

        # Fire and subsidence.
        for desc, amt in [("Pan fire in the kitchen; units, ceiling and walls damaged by fire and smoke.", 11_840.00),
                          ("Electrical fire in the consumer unit under the stairs; hall and stairs smoke-damaged.", 7_260.00)]:
            pol = self.policy("Home - Buildings only")
            n = self.notify_day(2, 10)
            c = self.claim(pol, "Fire", "Buildings", n - dt.timedelta(days=1), n, desc)
            build = self.area_supplier(pol, "build_n", "build_s")
            self.item(c, "Buildings", "Repair", "Fire and smoke reinstatement (loss adjuster's agreed schedule)", amt, supplier=build,
                      doc="Estimate", doc_date=n + dt.timedelta(days=9))
            self.decide(c, n + dt.timedelta(days=12))
            c["decision_notes"] = "Loss adjuster's schedule agreed; interim payment to the contractor."
            self.pay(c, n + dt.timedelta(days=20), "Interim payment", "Supplier", "Buildings", round(amt * 0.4, -2), c["excess"], supplier=build)
            c["status"] = "Open - repairs in progress"
        pol = self.policy("Home - Buildings only", first=D(2012, 4, 16))
        c = self.claim(pol, "Subsidence", "Buildings", sep(3), sep(4),
                       "Cracks opening above the front bay window and in the hall after the dry summer; front door sticking.")
        self.item(c, "Buildings", "Report", "Loss adjuster's report: movement consistent with clay shrinkage near a street tree; three months' crack monitoring started",
                  650.00, agreed=None, supplier="loss", doc="Report", doc_date=sep(17))
        self.item(c, "Buildings", "Repair", "Underpinning and crack repair, preliminary estimate", 21_400.00, agreed=None, supplier="loss", doc="Estimate",
                  doc_date=sep(17))
        c.update(status="Open - assessing", evidence="Partial", notes="Crack monitoring until December; council tree officer contacted.")

    def normal_motor(self):
        rng = self.rng
        comp = "Motor - Comprehensive"
        at_fault = ["Hit the car in front in slow traffic on the A23.", "Reversed into a bollard in a supermarket car park.",
                    "Clipped a parked van while turning into a side road.", "Slid into a kerb on a wet roundabout; wheel and suspension damaged.",
                    "Drove into the back of a car that braked suddenly on the M25.", "Scraped the side of the car on a gatepost.",
                    "Collided with a cyclist's bike stand while parking; front bumper damaged.", "Hit a pothole-dodging car while changing lanes.",
                    "Reversed into a wall at home.", "Front-end collision at a junction; insured driver pulled out.",
                    "Hit a parked car while pulling out of a space."]
        for i, desc in enumerate(at_fault):
            pol = self.policy(comp)
            n = self.notify_day(1, 29)
            c = self.claim(pol, "Collision - at fault", "Motor", n - dt.timedelta(days=rng.randint(0, 2)), n, desc)
            rep = self.motor_repairer(pol)
            amt = round(rng.uniform(1_150, 6_400), 2)
            if n <= sep(17):
                self.item(c, "Motor", "Repair", "Repair at approved repairer: parts, paint and labour", amt, supplier=rep,
                          doc_date=n + dt.timedelta(days=rng.randint(8, 14)))
                self.finish(c, n + dt.timedelta(days=rng.randint(4, 7)), pay_from=n + dt.timedelta(days=16),
                            notes="Engineer approved the repairer's estimate; repair invoiced.")
            else:
                self.item(c, "Motor", "Repair", "Repair estimate at approved repairer", amt, supplier=rep, doc="Estimate",
                          doc_date=n + dt.timedelta(days=3))
                self.decide(c, n + dt.timedelta(days=rng.randint(4, 7)))
                c["decision_notes"] = "Engineer approved the repairer's estimate."
                c["status"] = "Open - repairs in progress"

        non_fault = ["Third party drove into the back of the insured car at traffic lights.", "Parked car hit by a van making a delivery.",
                     "Third party reversed out of a driveway into the insured car.", "Third party changed lanes into the insured car on the A2.",
                     "Insured car hit by a bus pulling out of a stop.", "Third party jumped a red light and hit the side of the insured car.",
                     "Hit from behind on the M23 slip road.", "Parked car hit overnight; third party left details.",
                     "Third party drove through a give-way line into the insured car.", "Insured car shunted in a queue at a junction."]
        for i, desc in enumerate(non_fault):
            pol = self.policy(comp)
            n = self.notify_day(1, 26)
            c = self.claim(pol, "Collision - not at fault", "Motor", n - dt.timedelta(days=rng.randint(0, 2)), n, desc)
            rep = self.motor_repairer(pol)
            amt = round(rng.uniform(900, 4_800), 2)
            if n > sep(20):
                self.item(c, "Motor", "Repair", "Repair estimate at approved repairer", amt, supplier=rep, doc="Estimate",
                          doc_date=n + dt.timedelta(days=3))
                self.decide(c, n + dt.timedelta(days=rng.randint(4, 7)))
                c["decision_notes"] = "Third party's insurer has accepted liability; repairer's estimate approved."
                c["status"] = "Open - repairs in progress"
                continue
            self.item(c, "Motor", "Repair", "Repair at approved repairer: parts, paint and labour", amt, supplier=rep,
                      doc_date=n + dt.timedelta(days=rng.randint(7, 12)))
            decided = n + dt.timedelta(days=rng.randint(3, 6))
            self.finish(c, decided, pay_from=n + dt.timedelta(days=14), notes="Third party's insurer has accepted liability; repair invoiced.")
            if n <= sep(12) and c["excess"] > 0:
                got = uk.add_working_days(n + dt.timedelta(days=14), rng.randint(12, 16))
                self.pay(c, got, "Recovery", "Third-party insurer", "Motor", amt, direction="Received")
                self.pay(c, uk.add_working_days(got, 2), "Excess refund", "Policyholder", "Motor", c["excess"])

        for i in range(9):
            pol = self.policy(comp)
            n = self.notify_day(1, 30)
            repair = i in (1, 4, 7)
            c = self.claim(pol, "Windscreen - repair" if repair else "Windscreen - replacement", "Motor", n - dt.timedelta(days=rng.randint(0, 3)), n,
                           rng.choice(["Stone chip on the motorway spread into a crack.", "Windscreen cracked by a stone from a lorry.",
                                       "Chip in the driver's line of sight."]) if not repair else "Small stone chip in the windscreen.",
                           channel="Online")
            amt = round(rng.uniform(65, 95), 2) if repair else round(rng.uniform(290, 980), 2)
            self.item(c, "Motor", "Glass", "Windscreen chip repair" if repair else "Windscreen replacement, with camera recalibration where fitted",
                      amt, supplier="screen", doc_date=n + dt.timedelta(days=rng.randint(1, 4)))
            if n <= sep(28):
                self.finish(c, n + dt.timedelta(days=rng.randint(4, 7)), pay_from=n + dt.timedelta(days=8), notes="Glass supplier's invoice.")
            else:
                c["items"][0]["document_type"] = "Estimate"
                c["items"][0]["agreed_amount_gbp"] = None
                c.update(status="Open - assessing", evidence="Partial", notes="Fitting booked; invoice awaited.")

        # Theft of the car: total losses at market value.
        tpft = "Motor - Third party, fire and theft"
        for i, (product, desc) in enumerate([(comp, "Car stolen from outside the policyholder's home overnight; both keys held."),
                                             (tpft, "Car stolen from a station car park; both keys held."),
                                             (comp, "Car stolen from the driveway overnight; keyless entry suspected.")]):
            pol = self.policy(product)
            n = self.notify_day(1, 20)
            c = self.claim(pol, "Theft of vehicle", "Motor", n - dt.timedelta(days=1), n, desc, crime=self.crime_ref(pol["postcode"].split()[0]))
            value = round(pol["vehicle_value_gbp"] * rng.uniform(0.9, 0.98), -1)
            self.item(c, "Motor", "Total loss", "Market value of the car (engineer's valuation from trade guides)", value, supplier="engineer",
                      doc="Valuation", doc_date=n + dt.timedelta(days=rng.randint(10, 14)))
            if i < 2:
                self.decide(c, n + dt.timedelta(days=rng.randint(15, 18)))
                c["decision_notes"] = "Car not recovered after 14 days; settled at market value. Logbook and both keys received."
                self.pay(c, uk.add_working_days(c["decision_date"], 2), "Final settlement", "Policyholder", "Motor", value, c["excess"])
            else:
                c["items"][0]["agreed_amount_gbp"] = None
                c.update(status="Open - awaiting evidence", evidence="Partial",
                         notes="Waiting 14 days for the car to be recovered; logbook (V5C) and second key requested.")
        pol = self.policy(comp)
        n = sep(17)
        c = self.claim(pol, "Theft of vehicle", "Motor", sep(16), n,
                       "Car taken from outside a newsagent while the engine was running and the keys were in the ignition.",
                       crime=self.crime_ref(pol["postcode"].split()[0]))
        self.item(c, "Motor", "Total loss", "Market value of the car (engineer's valuation from trade guides)",
                  round(pol["vehicle_value_gbp"] * 0.95, -1), agreed=None, supplier="engineer", doc="Valuation", doc_date=sep(22))
        c.update(status="Declined", decline="M-4.1", approved_by=LEADER, decision_date=sep(24),
                 decision_notes="Declined under M-4.1: the car was left unattended with the engine running and the keys in it, as the policyholder and the police report state.")

        for i, desc in enumerate(["Paintwork keyed along both sides overnight.", "Wing mirror and windscreen wiper snapped off in the street.",
                                  "Tyres slashed and bonnet dented outside the home.", "Rear window smashed and the car interior damaged."]):
            pol = self.policy(comp)
            n = self.notify_day(1, 26)
            c = self.claim(pol, "Malicious damage", "Motor", n - dt.timedelta(days=1), n, desc, crime=self.crime_ref(pol["postcode"].split()[0]))
            rep = self.motor_repairer(pol)
            self.item(c, "Motor", "Repair", "Repair at approved repairer", round(rng.uniform(420, 1_900), 2), supplier=rep,
                      doc_date=n + dt.timedelta(days=rng.randint(6, 10)))
            self.finish(c, n + dt.timedelta(days=rng.randint(3, 5)), pay_from=n + dt.timedelta(days=12), notes="Crime reference held; repair invoiced.")

        for desc in ["Lost control on a wet bend and hit a tree; airbags deployed.", "Car hit a central reservation barrier; engine and front end destroyed."]:
            pol = self.policy(comp)
            n = self.notify_day(2, 15)
            c = self.claim(pol, "Collision - at fault", "Motor", n - dt.timedelta(days=1), n, desc)
            value = round(pol["vehicle_value_gbp"] * rng.uniform(0.9, 0.97), -1)
            self.item(c, "Motor", "Total loss", "Market value: car uneconomical to repair (engineer's valuation)", value, supplier="engineer",
                      doc="Valuation", doc_date=n + dt.timedelta(days=rng.randint(6, 9)))
            self.decide(c, n + dt.timedelta(days=rng.randint(9, 12)))
            c["decision_notes"] = "Total loss; settled at market value and salvage sold."
            paid = self.pay(c, uk.add_working_days(c["decision_date"], 2), "Final settlement", "Policyholder", "Motor", value, c["excess"])
            self.pay(c, uk.add_working_days(paid["date"], 6), "Salvage", "Salvage agent", "Motor", round(value * rng.uniform(0.12, 0.22), -1), direction="Received")

    # ---- planted cases

    def planted(self):
        bc = "Home - Buildings and contents"
        comp = "Motor - Comprehensive"
        K = self.K

        # CASE: incident two days before a new policy began. The plumber's invoice is dated before the cover start.
        pol = self.policy(bc, first=sep(8), start=sep(8), channel="Price comparison website", outward="CR4", std=100, declared=0,
                          optional="None")
        c = self.claim(pol, "Escape of water", "Buildings", sep(5), sep(9),
                       "Water came through the kitchen ceiling; a pipe under the bath had burst. The policyholder's plumber repaired it.",
                       channel="Online", handler="STF-05", key="before_start")
        self.item(c, "Buildings", "Trace and access", "Emergency call-out: burst pipe under the bath located and repaired; bath panel removed",
                  385.00, supplier="plumb_x", doc_date=sep(6))
        self.item(c, "Buildings", "Drying", "2 dehumidifiers and 1 air mover, with moisture readings", 1_290.00, supplier="dry_old",
                  doc_date=sep(16), start=sep(10), end=sep(15))
        self.item(c, "Buildings", "Repair", "Reinstatement estimate: kitchen ceiling, walls and decoration", 2_795.00, supplier="build_s",
                  doc="Estimate", doc_date=sep(17))
        self.decide(c, sep(18))
        c.update(status="Open - settlement agreed", decision_notes="Cover confirmed as Active; costs agreed on invoices and estimate.")

        # Lookalike: incident three days before the renewal date, covered under the previous period.
        pol = self.policy(comp, first=D(2021, 9, 14), start=sep(14), channel="Direct online", vol=100, declared=0,
                          vehicle=("Volkswagen Polo 1.0 TSI", 2020, 11_300))
        c = self.claim(pol, "Collision - at fault", "Motor", sep(11), sep(15),
                       "Hit a parked car while turning into a narrow side street on the way home.", handler="STF-06", key="renewal")
        self.item(c, "Motor", "Repair", "Repair at approved repairer: front wing, bumper and headlamp", 2_318.46,
                  supplier=self.motor_repairer(pol), doc_date=sep(28))
        self.finish(c, sep(21), pay_from=oct_(2), notes="Incident on 11 September, in the policy period that ended on 13 September; covered under M-1.1.")

        # CASE: fire claim settlement above the contents sum insured.
        pol = self.policy("Home - Contents only", outward="N17", contents=25_000, std=100, channel="Price comparison website",
                          optional="Legal expenses")
        pol["property_type"] = "Flat"
        c = self.claim(pol, "Fire", "Contents", sep(3), sep(3),
                       "Fire started by a tumble dryer in the kitchen of the flat; kitchen destroyed and smoke damage throughout.",
                       channel="Phone", handler="STF-04", key="over_limit")
        for name, claimed, agreed, doc, sup in [
                ("Kitchen appliances", 4_100, 3_860, "Receipt", None), ("Living room furniture", 7_450, 6_940, "Receipt", None),
                ("Clothing and shoes", 5_600, 5_320, "Photograph", None), ("Bedroom furniture and bedding", 4_980, 4_780, "Bank statement", None),
                ("Television, laptop and games console", 4_390, 4_150, "Receipt", None), ("Curtains and blinds", 1_240, 1_240, "Photograph", None),
                ("Kitchenware and food", 1_570, 1_460, "Photograph", None),
                ("Smoke cleaning of soft furnishings and clothing", 2_130, 2_130, "Estimate", "dry_old")]:
            self.item(c, "Contents", "Replacement" if sup is None else "Repair", name, claimed, agreed=agreed, supplier=sup, doc=doc,
                      doc_date=sep(11) if doc == "Estimate" else None)
        self.pay(c, sep(18), "Interim payment", "Policyholder", "Contents", 5_000.00, 100.00)
        self.decide(c, oct_(9), MANAGER)
        c.update(status="Open - settlement agreed", decision_notes="Loss adjuster's schedule of contents agreed. Balance to be paid on approval.")

        # Lookalike: a watch worth more than the single article limit, specified on the schedule.
        pol = self.policy(bc, contents=60_000, sal=2_000, specified="Stainless steel automatic wristwatch, £7,500", std=100, outward="SW19",
                          channel="Broker")
        c = self.claim(pol, "Theft", "Contents", sep(12), sep(13), "Burglary overnight through a rear window; a wristwatch taken from the bedroom.",
                       crime=self.crime_ref("SW19"), channel="Broker", handler="STF-07", key="specified")
        self.item(c, "Contents", "Valuables", "Stainless steel automatic wristwatch: replacement through panel supplier", 7_200.00, supplier="jewel",
                  doc="Valuation", doc_date=sep(18))
        self.finish(c, sep(22), notes="Watch specified on the schedule at £7,500; valuation and crime reference held.")

        # CASE: excess deducted from the interim payment and again from the final settlement.
        pol = self.policy("Home - Buildings only", outward="E17", std=100)
        c = self.claim(pol, "Escape of water", "Buildings", sep(14), sep(15),
                       "Pipe to the kitchen radiator split under the floorboards; water through to the cellar.", handler="STF-04", key="double_excess")
        self.item(c, "Buildings", "Trace and access", "Policyholder's own plumber: leak traced and floorboards lifted", 420.00, doc="Receipt", doc_date=sep(15))
        self.item(c, "Buildings", "Repair", "Policyholder's own builder: replaster cellar ceiling and redecorate", 3_170.00, doc="Estimate", doc_date=sep(19))
        self.item(c, "Buildings", "Repair", "Policyholder's own builder: replace kitchen laminate floor", 1_150.00, doc="Estimate", doc_date=sep(19))
        self.pay(c, sep(22), "Interim payment", "Policyholder", "Buildings", 1_500.00, 350.00)
        self.decide(c, oct_(5))
        c["decision_notes"] = "Cash settlement agreed on the policyholder's own contractors' quotes."
        self.pay(c, oct_(7), "Final settlement", "Policyholder", "Buildings", 3_240.00, 350.00)

        # Lookalike: one storm, a claim under both sections, so the excess is taken for each (clause H-1.2).
        pol = self.policy(bc, outward="RH2", std=100)
        c = self.claim(pol, "Storm", "Buildings and contents", STORM_DATE, STORM_DATE,
                       "Roof tiles blown off; rain through the living room ceiling soaked the sofa and rug.", handler="STF-06", key="two_sections")
        self.item(c, "Buildings", "Repair", "Replace roof tiles and repair living room ceiling", 1_565.00, supplier="roof", doc_date=sep(30))
        self.item(c, "Contents", "Replacement", "Sofa and rug (cash settlement)", 1_120.00, doc="Receipt", doc_date=D(2024, 3, 9))
        self.finish(c, oct_(1), pay_from=oct_(2), notes="Weather station records gusts above 47 mph; buildings and contents both damaged.")

        # CASE: one contractor's drying invoice charged to two claims for the same days.
        pa = self.policy(bc, outward="SE23", std=100)
        ca = self.claim(pa, "Escape of water", "Buildings", sep(9), sep(10), "Burst pipe in the bathroom wall; water through the hall ceiling.",
                        handler="STF-05", key="overlap_a")
        pb = self.policy("Home - Buildings only", outward="BR1", std=250)
        cb = self.claim(pb, "Escape of water", "Buildings", sep(10), sep(11), "Hot water pipe under the kitchen floor burst; floor and units soaked.",
                        handler="STF-07", key="overlap_b")
        for cl, trace, reinst, inv in ((ca, 410.00, 2_960.00, sep(19)), (cb, 655.50, 3_480.00, sep(21))):
            self.item(cl, "Buildings", "Trace and access", "Leak located, access made and making good", trace, supplier="plumb_s",
                      doc_date=cl["notified"].date() + dt.timedelta(days=1))
            it = self.item(cl, "Buildings", "Drying", "3 dehumidifiers and 2 air movers, 7 days, with moisture mapping", 2_184.00, supplier="dry_new",
                           doc_date=inv, start=sep(12), end=sep(18))
            cl["drying"] = it
            self.item(cl, "Buildings", "Repair", "Reinstatement: replaster, redecorate and replace damaged flooring", reinst, supplier="build_s",
                      doc_date=oct_(1))
            self.finish(cl, sep(29), pay_from=sep(30))
        cb["drying"]["ref_copy_of"] = ca["drying"]

        # Lookalike: two neighbours' roofs repaired by the same roofer on the same day after the storm.
        pc = self.postcode("DA1")
        for key, amt, desc in (("neighbour_a", 1_840.00, "Ridge tiles and lead flashing blown off; rain into the loft."),
                               ("neighbour_b", 2_260.00, "Ridge tiles blown off and the chimney pot dislodged; rain into the back bedroom.")):
            pol = self.policy("Home - Buildings only", postcode=pc, std=100)
            pol["property_type"] = "Semi-detached house"
            c = self.claim(pol, "Storm", "Buildings", STORM_DATE, STORM_DATE + dt.timedelta(days=1), desc, key=key)
            self.item(c, "Buildings", "Repair", "Roof repair", amt, supplier="roof", doc_date=oct_(2))
            self.finish(c, oct_(5), pay_from=oct_(8), notes="Weather station records gusts above 47 mph; roofer's invoice and photographs.")

        # CASE: a theft claim paid with no crime reference and no proof of ownership.
        pol = self.policy(bc, outward="SE15", std=100)
        c = self.claim(pol, "Theft", "Contents", sep(15), sep(16),
                       "Laptop, phone and a gold chain taken from the house during the day; the back door was found open.",
                       evidence="Insufficient", handler="STF-06", key="no_evidence",
                       notes="No crime reference given. No receipt, statement or photograph for the laptop, phone or chain.")
        for name, cat, amt in (("Laptop", "Replacement", 1_849.00), ("Mobile phone", "Replacement", 1_099.00), ("Gold chain", "Valuables", 1_200.00)):
            self.item(c, "Contents", cat, name, amt, doc="None")
        self.finish(c, sep(24), pay_from=sep(25), notes="Settled in full to meet the 10-working-day target for simple claims.")

        # Lookalike: no receipts, but card statements and photographs accepted under H-6.2.
        pol = self.policy(bc, outward="KT1", std=100)
        c = self.claim(pol, "Theft", "Contents", sep(18), sep(19), "Burglary through the patio door; e-bike, laptop and television taken.",
                       crime=self.crime_ref("KT1"), handler="STF-07", key="alt_proof",
                       notes="Receipts lost. Card statements and photographs accepted as proof under H-6.2. Crime reference held.")
        for name, amt, doc in (("Electric bicycle", 1_650.00, "Bank statement"), ("Laptop", 1_199.00, "Photograph"), ("43-inch television", 549.00, "Bank statement")):
            self.item(c, "Contents", "Replacement", name, amt, doc=doc, doc_date=sep(20))
        self.finish(c, sep(29), pay_from=oct_(1), notes="Proof of ownership accepted under H-6.2.")

        # CASE: escape of water declined as gradual damage, though the plumber found a sudden burst.
        pol = self.policy(bc, outward="SM1", std=100)
        c = self.claim(pol, "Escape of water", "Buildings", sep(6), sep(7),
                       "Came home to water across the kitchen floor; the hose to the kitchen tap had burst under the sink.",
                       handler="STF-05", key="wrong_decline")
        self.item(c, "Buildings", "Report", "Plumber's report: flexible tap hose under the kitchen sink burst; braiding split at the crimp. Sudden failure. "
                  "Cabinet base and floor were dry and sound before the escape, with no staining or rot.", 180.00, agreed=None, supplier="plumb_s",
                  doc="Report", doc_date=sep(8))
        self.item(c, "Buildings", "Repair", "Estimate: replace kitchen floor and base units", 3_940.00, agreed=None, supplier="build_s",
                  doc="Estimate", doc_date=sep(11))
        c.update(status="Declined", decline="H-5.1", approved_by=LEADER, decision_date=sep(14),
                 decision_notes="Declined under H-5.1: leak under the kitchen sink, wear and tear.")

        # Lookalike: a shower seal that leaked for months, correctly declined under the same clause.
        pol = self.policy(bc, outward="HA1", std=250)
        c = self.claim(pol, "Escape of water", "Buildings", sep(15), sep(16),
                       "Floor under the shower is soft and the kitchen ceiling below is stained.", handler="STF-04", key="right_decline")
        self.item(c, "Buildings", "Report", "Plumber's report: shower tray seal perished; water has seeped into the floor over several months. "
                  "Joists damp and discoloured.", 150.00, agreed=None, supplier="plumb_n", doc="Report", doc_date=sep(17))
        self.item(c, "Buildings", "Repair", "Estimate: replace shower tray, joists and kitchen ceiling", 4_860.00, agreed=None, supplier="build_n",
                  doc="Estimate", doc_date=sep(18))
        c.update(status="Declined", decline="H-5.1", approved_by=LEADER, decision_date=sep(21),
                 decision_notes="Declined under H-5.1: the plumber's report shows water seeping through the shower seal over several months.")

    # ---- complaints

    def complaints_list(self):
        rng = self.rng
        K = self.K
        def pick(pred):
            c = next(c for c in self.claims if pred(c) and not c.get("complained"))
            c["complained"] = True
            return c

        spec = [
            (K["wrong_decline"], sep(16), "Email", "Says the hose burst suddenly, as the plumber's report confirms, and the claim should be paid.",
             "Claim decision", oct_(2), "Not upheld", "Decline reviewed. A leak under a sink is wear and tear; H-5.1 applies. Referral rights to the Financial Ombudsman Service given.", 0),
            (K["right_decline"], sep(23), "Phone", "Disagrees with the decline; says the leak was only noticed last week.",
             "Claim decision", oct_(7), "Not upheld", "The plumber's report shows water seeping through the seal over several months; H-5.1 excludes gradual damage. Referral rights given.", 0),
            (pick(lambda c: c["claim_type"] == "Storm" and c["status"] == "Open - awaiting evidence"), sep(30), "Phone",
             "No roofer has visited a week after the storm; tarpaulin only.", "Delay", None, None, None, 0),
            (pick(lambda c: c["claim_type"] == "Collision - at fault" and c["status"] == "Settled"), sep(28), "Email",
             "Repair took three weeks and no courtesy car was provided, although the policy includes one.", "Repair quality", oct_(6), "Upheld",
             "Courtesy car should have been provided under the policy. Apology and £100 for distress and inconvenience.", 100),
            (pick(lambda c: c["claim_type"].startswith("Windscreen") and c["status"] == "Settled"), sep(21), "Webchat",
             "Fitter arrived on the wrong day.", "Service", sep(22), "Upheld", "Apology; new appointment made the same week.", 0),
            (pick(lambda c: c["claim_type"] == "Escape of water" and c["status"] == "Settled"), sep(24), "Phone",
             "Handler did not return calls for a week.", "Service", oct_(5), "Upheld", "Calls were missed while the team handled storm claims. Apology and £75.", 75),
            (pick(lambda c: c["claim_type"] == "Collision - at fault" and any(i["category"] == "Total loss" for i in c["items"])), sep(29), "Letter",
             "Says the market value offered for the car is too low.", "Settlement amount", oct_(12), "Not upheld",
             "Valuation checked against three trade guides and adverts for similar cars; the offer is fair market value.", 0),
            (pick(lambda c: c["claim_type"] == "Escape of water" and c["status"] != "Declined" and c["excess"] >= 350 and c is not K["double_excess"]
                  and c is not K["before_start"]), oct_(1), "Email",
             "Did not expect a higher excess for escape of water.", "Settlement amount", oct_(8), "Not upheld",
             "The escape of water excess is shown on the schedule and in clause H-1.2.", 0),
            (pick(lambda c: c["claim_type"] == "Collision - not at fault" and not any(p["payment_type"] == "Recovery" for p in c["payments"])
                  and c["excess"] > 0), oct_(2), "Phone",
             "Excess not refunded although the other driver admitted fault.", "Settlement amount", oct_(9), "Partially upheld",
             "Excess is refunded once the other insurer pays (M-1.2); that had not been explained. £50 for poor communication.", 50),
            (pick(lambda c: c["claim_type"] == "Fire" and c["status"] == "Open - repairs in progress"), oct_(8), "Phone",
             "Waited four days for alternative accommodation to be confirmed.", "Delay", None, None, None, 0),
        ]
        for c, received, channel, reason, cat, resolved, outcome, notes, redress in spec:
            c["complained"] = True
            summary = resolved is not None and business_days(received, resolved) <= 3
            self.complaints.append({"claim": c, "received_date": received, "channel": channel, "reason": reason, "category": cat,
                                    "handler_id": COMPLAINTS, "status": "Open" if resolved is None else
                                    "Closed - summary resolution" if summary else "Closed - final response",
                                    "resolved_date": resolved, "outcome": outcome, "outcome_notes": notes, "redress_gbp": float(redress)})
            if redress:
                sec = "Buildings" if c["section"] == "Buildings and contents" else c["section"]
                self.pay(c, uk.add_working_days(resolved, rng.randint(2, 4)), "Complaint redress", "Policyholder", sec, redress)

    # ---- numbering and derived fields

    PREFIX = {"plumb_n": "PN", "plumb_s": "PS", "build_n": "BN", "build_s": "BS", "roof": "RF", "glass_h": "GL", "repl": "RG",
              "jewel": "JW", "dry_old": "DO", "dry_new": "DRN", "motor_e": "ME", "motor_s": "MS", "motor_w": "MW", "motor_k": "MK",
              "screen": "WS", "engineer": "EN", "loss": "LA"}

    def finalise(self):
        rng = self.rng
        for i, p in enumerate(sorted(self.policies, key=lambda p: (p["first_incepted"], p["postcode"])), start=1):
            p["policy_id"] = f"POL-{i:04d}"
        self.claims.sort(key=lambda c: c["notified"])
        for i, c in enumerate(self.claims, start=1):
            c["claim_id"] = f"CLM-{i:04d}"
        # Supplier document references rise with the document date.
        docs = defaultdict(list)
        for c in self.claims:
            for it in c["items"]:
                if it["supplier_key"] and it["document_type"] in ("Invoice", "Estimate", "Report", "Valuation") and "ref_copy_of" not in it:
                    docs[(it["supplier_key"], it["document_type"])].append((it["document_date"], c["claim_id"], it))
        for (sk, dtype), lst in sorted(docs.items()):
            n = rng.randint(1_200, 8_800) if dtype == "Invoice" else rng.randint(100, 900)
            for _, _, it in sorted(lst, key=lambda x: (x[0], x[1])):
                n += rng.randint(1, 40)
                if sk == "plumb_x":
                    it["document_ref"] = f"Invoice {n:04d}"
                else:
                    tag = {"Invoice": "", "Estimate": "Q", "Report": "R", "Valuation": "V"}[dtype]
                    it["document_ref"] = f"{self.PREFIX[sk]}-{tag}{n:05d}" if dtype == "Invoice" else f"{self.PREFIX[sk]}-{tag}{n:04d}"
        for c in self.claims:
            for it in c["items"]:
                if "ref_copy_of" in it:
                    it["document_ref"] = it.pop("ref_copy_of")["document_ref"] + "/2"
        self.complaints_list()

        items, n_item = [], 0
        for c in self.claims:
            c["payments"] = [p for p in c["payments"] if p["date"] <= EXTRACT_DATE]
            for it in c["items"]:
                n_item += 1
                items.append({"item_id": f"CI-{n_item:04d}", "claim_id": c["claim_id"],
                              **{k: it[k] for k in ["section", "category", "description", "supplier_id", "document_type", "document_ref",
                                                    "document_date", "service_start", "service_end", "claimed_amount_gbp", "agreed_amount_gbp"]}})
            self.derive(c)
        self.rows["claim_items"] = items

        pays = sorted(((p["date"], c["claim_id"], p) for c in self.claims for p in c["payments"]), key=lambda x: (x[0], x[1]))
        self.rows["claim_payments"] = [{"payment_id": f"CPY-{i:04d}", "claim_id": cid, "payment_date": iso(d),
                                        **{k: p[k] for k in ["payment_type", "direction", "payee", "supplier_id", "section",
                                                             "gross_amount_gbp", "excess_deducted_gbp", "net_amount_gbp", "method"]}}
                                       for i, (d, cid, p) in enumerate(pays, start=1)]
        for c in self.claims:
            if c["status"] == "Settled" and any(i["category"] == "Total loss" for i in c["items"]):
                c["pol"]["policy_status"] = "Cancelled"
        pcols = [c.name for c in SCHEMA[3].columns]
        self.rows["policies"] = [{k: p[k] for k in pcols} for p in sorted(self.policies, key=lambda p: p["policy_id"])]
        self.rows["claims"] = [{
            "claim_id": c["claim_id"], "policy_id": c["pol"]["policy_id"], "claim_type": c["claim_type"], "section": c["section"],
            "incident_date": c["incident_date"], "notified_date": iso(c["notified"].date()), "notified_channel": c["notified_channel"],
            "description": c["description"], "crime_reference": c["crime_reference"],
            "claimed_amount_gbp": r2(sum(i["claimed_amount_gbp"] for i in c["items"])), "excess_gbp": r2(c["excess"]),
            "reserve_gbp": c["reserve"], "policy_status": "Active", "evidence_status": c["evidence"], "evidence_notes": c["notes"],
            "proposed_settlement_gbp": c["proposed"], "approved_by": c["approved_by"], "decision_date": iso(c["decision_date"]),
            "decline_clause_id": c["decline"], "decision_notes": c["decision_notes"], "claim_status": c["status"],
            "handler_id": c["handler"]} for c in self.claims]
        self.complaints.sort(key=lambda x: (x["received_date"], x["claim"]["claim_id"]))
        self.rows["complaints"] = [{
            "complaint_id": f"CMP-{i:03d}", "claim_id": x["claim"]["claim_id"], "received_date": iso(x["received_date"]),
            "channel": x["channel"], "reason": x["reason"], "category": x["category"], "handler_id": x["handler_id"],
            "status": x["status"], "resolved_date": iso(x["resolved_date"]),
            "handling_days": business_days(x["received_date"], x["resolved_date"] or EXTRACT_DATE),
            "outcome": x["outcome"], "outcome_notes": x["outcome_notes"], "redress_gbp": x["redress_gbp"]}
            for i, x in enumerate(self.complaints, start=1)]

    def derive(self, c):
        """Claim status, reserve and evidence notes from the items and the payments made by the extract."""
        settlement = [p for p in c["payments"] if p["direction"] == "Paid" and p["payment_type"] in
                      ("Interim payment", "Final settlement", "Supplier payment")]
        agreed = sum(i["agreed_amount_gbp"] or 0 for i in c["items"])
        if c["status"] in ("Declined", "Withdrawn"):
            c["reserve"], c["proposed"] = 0.0, None
            for it in c["items"]:
                it["agreed_amount_gbp"] = None
        elif c["proposed"] is not None:
            gross = sum(p["gross_amount_gbp"] for p in settlement)
            if r2(gross) == r2(agreed) and c["status"] == "Settled":
                c["reserve"] = 0.0
            else:
                if c["status"] == "Settled":
                    c["status"] = "Open - settlement agreed"
                c["reserve"] = r2(c["proposed"] - sum(p["net_amount_gbp"] for p in settlement))
        else:
            estimate = sum(i["claimed_amount_gbp"] for i in c["items"]) - c["excess"]
            c["reserve"] = r2(max(0, round(estimate, -1)) - sum(p["net_amount_gbp"] for p in settlement))
        if c["notes"] is None:
            docs = sorted({i["document_type"].lower() + ("s" if i["document_type"] in ("Invoice", "Estimate", "Receipt", "Photograph", "Report", "Valuation") else "")
                           for i in c["items"] if i["document_type"] != "None"})
            c["notes"] = ("Held: " + ", ".join(docs) + "." if docs else None)
            if c["crime_reference"]:
                c["notes"] = (c["notes"] or "") + " Crime reference held."


# ------------------------------------------------------------------ rules (claims procedures)

RULES = [
    ("R-01", "Cover", "Period of cover",
     "Before accepting a claim, the handler checks that the incident date falls within the period of insurance, using "
     "first_incepted and cover_start in policies. An incident in an earlier period of a renewed policy is covered under that "
     "period. An incident before the policy was first taken out is not covered (H-1.1, M-1.1); the claim is referred to Claims "
     "Validation. The policy status recorded on the claim does not show this."),
    ("R-02", "Settlement", "Limits",
     "A proposed settlement may not exceed the sum insured for the section claimed under, or the car's market value, less the "
     "excess (H-4.1, M-3.1). Any one valuable is limited to the single article limit unless it is specified on the schedule, "
     "when its specified value applies (H-3.2)."),
    ("R-03", "Settlement", "Excess",
     "The excess recorded on the claim is taken once, from the first payments made on the claim, whether to the policyholder "
     "or to a supplier. A claim under both Buildings and Contents carries the excess for each section (H-1.2). The excess "
     "deducted across all payments on a claim must never exceed the excess recorded on it. On a non-fault motor claim the "
     "excess is refunded once the other insurer has paid in full (M-1.2)."),
    ("R-04", "Evidence", "Evidence before settlement",
     "A settlement may be proposed only when evidence_status is Complete: proof of ownership and value for any item over "
     "£500 (H-6.2), a police crime reference for theft and malicious damage (H-6.1, M-5.1), and a supplier invoice or "
     "agreed estimate for repairs. A reserve may be set while evidence is awaited."),
    ("R-05", "Suppliers", "Invoice checks",
     "Before paying a supplier invoice, the handler checks that the same work, equipment or invoice has not been charged to "
     "another claim. Invoices from the same supplier with matching amounts or overlapping hire dates are referred to Claims "
     "Validation before payment."),
    ("R-06", "Decisions", "Declining a claim",
     "A claim may be declined only under a clause in the policy wording that applies to the facts, recorded in "
     "decline_clause_id, and supported by the evidence on the claim, such as a supplier's report. Declines are approved by a "
     "Claims Team Leader or above. If the evidence contradicts the clause, the claim is accepted."),
    ("R-07", "Decisions", "Settlement authority",
     "A proposed settlement becomes final only when approved by someone whose settlement authority covers it: Claims Handler "
     "£5,000; Claims Team Leader £25,000; Claims Manager £100,000; Head of Claims £250,000. Until then it is a provisional "
     "assessment."),
    ("R-08", "Complaints", "Complaint handling",
     "Complaints follow the FCA's complaint-handling rules (DISP). A complaint resolved by the close of the third business "
     "day after receipt may be closed with a summary resolution. Otherwise a final response is sent within eight weeks, "
     "with the policyholder's right to refer to the Financial Ombudsman Service. A complaint about a decline is reviewed "
     "against the wording and the evidence, not the original decision alone. Redress is paid within 10 working days of the "
     "outcome."),
]

RULE_TABLES = {
    "R-01": "claims, policies", "R-02": "claims, claim_items, policies, policy_clauses", "R-03": "claims, claim_payments, policy_clauses",
    "R-04": "claims, claim_items, policy_clauses", "R-05": "claim_items, claim_payments, suppliers",
    "R-06": "claims, claim_items, policy_clauses, staff", "R-07": "claims, staff", "R-08": "complaints, claim_payments",
}

# ------------------------------------------------------------------ cases


def record_cases(b):
    K = b.K
    rows = b.rows
    cid = lambda k: K[k]["claim_id"]  # noqa: E731
    items = lambda k: [i for i in rows["claim_items"] if i["claim_id"] == cid(k)]  # noqa: E731
    pays = lambda k: [p for p in rows["claim_payments"] if p["claim_id"] == cid(k)]  # noqa: E731
    claim = lambda k: next(c for c in rows["claims"] if c["claim_id"] == cid(k))  # noqa: E731
    pol = lambda k: next(p for p in rows["policies"] if p["policy_id"] == claim(k)["policy_id"])  # noqa: E731
    complaint = lambda k: next(x for x in rows["complaints"] if x["claim_id"] == cid(k))  # noqa: E731
    long = lambda s: D.fromisoformat(s).strftime("%-d %B %Y")  # noqa: E731

    c, p = claim("before_start"), pol("before_start")
    inv = items("before_start")[0]
    b.case("CASE-01", "Escape of water three days before a new policy began", "incident_before_cover",
           "Genuine exception", "High", "R-01, H-1.1", "A7, A3, A8",
           f"Policy {p['policy_id']} was bought through a price comparison website and started on {long(p['cover_start'])}. Claim {c['claim_id']} "
           f"gives the incident date as {long(c['incident_date'])}, before the policy existed, and was reported the day after cover began. The "
           f"policyholder's plumber's invoice {inv['document_ref']} is dated {long(inv['document_date'])}, also before cover. The claim records the "
           f"policy as Active, and the handler agreed {gbp(c['proposed_settlement_gbp'])} on that basis. H-1.1 excludes anything that happened before "
           f"the policy was first taken out.",
           "Do not pay. Refer to Claims Validation to confirm the date of the escape with the plumber; decline under H-1.1 if confirmed, "
           "and consider whether the policy was bought after the loss.",
           """SELECT c.claim_id FROM claims c JOIN policies p ON p.policy_id = c.policy_id WHERE c.incident_date < p.first_incepted""",
           [("claims", c["claim_id"], "incident before the policy began", 1), ("policies", p["policy_id"], "new policy", 0),
            ("claim_items", inv["item_id"], "plumber's invoice dated before cover", 0)])

    c, p = claim("renewal"), pol("renewal")
    b.case("CASE-02", "Accident three days before the renewal date", "incident_before_cover_lookalike",
           "Benign lookalike", "None", "R-01, M-1.1", "A7, A3",
           f"Claim {c['claim_id']} is for an accident on {long(c['incident_date'])}, before the current period of policy {p['policy_id']} began on "
           f"{long(p['cover_start'])}. The policy was first taken out on {long(p['first_incepted'])} and renewed without a break, so the accident "
           f"is covered under the period that ended the day before the renewal (M-1.1).",
           "No action.",
           """SELECT c.claim_id FROM claims c JOIN policies p ON p.policy_id = c.policy_id
              WHERE c.incident_date < p.cover_start AND c.incident_date >= p.first_incepted""",
           [("claims", c["claim_id"], "incident in the previous period", 1), ("policies", p["policy_id"], "renewed policy", 0)])

    c, p = claim("over_limit"), pol("over_limit")
    cap = p["contents_sum_insured_gbp"] - c["excess_gbp"]
    paid = sum(x["net_amount_gbp"] for x in pays("over_limit"))
    b.case("CASE-03", "Fire settlement approved above the contents sum insured", "settlement_over_limit",
           "Genuine exception", "High", "R-02, H-4.1", "A3, S1, A5",
           f"Claim {c['claim_id']} is a kitchen fire in a flat insured on a contents-only policy, {p['policy_id']}, with a contents sum insured "
           f"of {gbp(p['contents_sum_insured_gbp'])}. The agreed items total {gbp(c['proposed_settlement_gbp'] + c['excess_gbp'])}, and the proposed "
           f"settlement of {gbp(c['proposed_settlement_gbp'])} was approved on {long(c['decision_date'])}. H-4.1 limits one Contents claim to the sum "
           f"insured less the excess, {gbp(cap)}. An interim payment of {gbp(paid)} has been made, so at most {gbp(cap - paid)} is still due, "
           f"not the reserve of {gbp(c['reserve_gbp'])}. Approving the proposal would overpay by {gbp(c['proposed_settlement_gbp'] - cap)}.",
           f"Cap the settlement at {gbp(cap)}, pay the balance of {gbp(cap - paid)}, and reduce the reserve. Explain the limit to the policyholder and "
           "check whether the contents were underinsured at the last renewal.",
           """SELECT c.claim_id FROM claims c JOIN policies p ON p.policy_id = c.policy_id
              WHERE c.proposed_settlement_gbp > CASE c.section WHEN 'Buildings' THEN p.buildings_sum_insured_gbp
                WHEN 'Contents' THEN p.contents_sum_insured_gbp
                WHEN 'Buildings and contents' THEN p.buildings_sum_insured_gbp + p.contents_sum_insured_gbp
                WHEN 'Motor' THEN p.vehicle_value_gbp END - c.excess_gbp""",
           [("claims", c["claim_id"], "settlement above the limit", 1), ("policies", p["policy_id"], "contents sum insured", 0)]
           + [("claim_payments", x["payment_id"], "interim payment", 0) for x in pays("over_limit")])

    c, p = claim("specified"), pol("specified")
    w = items("specified")[0]
    b.case("CASE-04", "£7,200 watch above the single article limit, specified on the schedule", "valuable_over_limit_lookalike",
           "Benign lookalike", "None", "R-02, H-3.2", "A3, A8",
           f"Claim {c['claim_id']} is for a wristwatch stolen in a burglary, valued at {gbp(w['agreed_amount_gbp'])}. The single article limit on policy "
           f"{p['policy_id']} is {gbp(p['single_article_limit_gbp'])}, but the watch is specified on the schedule at £7,500, so H-3.2 covers it in full. "
           f"Valuables in total are well under a third of the {gbp(p['contents_sum_insured_gbp'])} contents sum insured. The settlement was approved by "
           f"the Claims Team Leader, within authority.",
           "No action.",
           """SELECT i.item_id FROM claim_items i JOIN claims c ON c.claim_id = i.claim_id JOIN policies p ON p.policy_id = c.policy_id
              WHERE i.category = 'Valuables' AND i.agreed_amount_gbp > p.single_article_limit_gbp""",
           [("claim_items", w["item_id"], "specified valuable", 1), ("claims", c["claim_id"], "theft claim", 0), ("policies", p["policy_id"], "schedule with the specified item", 0)])

    c = claim("double_excess")
    px = pays("double_excess")
    taken = sum(x["excess_deducted_gbp"] for x in px)
    b.case("CASE-05", "Escape of water excess taken from the interim payment and again from the final settlement", "excess_deducted_twice",
           "Genuine exception", "Medium", "R-03, H-1.2", "S1, A5, A3",
           f"Claim {c['claim_id']} carries an escape of water excess of {gbp(c['excess_gbp'])}. The interim payment {px[0]['payment_id']} on "
           f"{long(px[0]['payment_date'])} deducted it, and the final settlement {px[1]['payment_id']} on {long(px[1]['payment_date'])} deducted it again, "
           f"{gbp(taken)} in all. The agreed items total {gbp(c['proposed_settlement_gbp'] + c['excess_gbp'])}, so the policyholder was due "
           f"{gbp(c['proposed_settlement_gbp'])} and received {gbp(sum(x['net_amount_gbp'] for x in px))}: {gbp(taken - c['excess_gbp'])} short. "
           f"The claim is closed as Settled.",
           f"Pay the policyholder {gbp(taken - c['excess_gbp'])}, with an apology. Check other claims with interim payments for the same error.",
           """SELECT c.claim_id FROM claims c WHERE (SELECT sum(p.excess_deducted_gbp) FROM claim_payments p WHERE p.claim_id = c.claim_id) > c.excess_gbp""",
           [("claims", c["claim_id"], "excess taken twice", 1)] + [("claim_payments", x["payment_id"], "payment deducting the excess", 0) for x in px])

    c = claim("two_sections")
    px = [x for x in pays("two_sections") if x["excess_deducted_gbp"] > 0]
    b.case("CASE-06", "Storm claim with an excess taken for Buildings and again for Contents", "two_excesses_lookalike",
           "Benign lookalike", "None", "R-03, H-1.2", "A3, S1",
           f"Claim {c['claim_id']} is for one storm that damaged the roof and ceiling (Buildings) and soaked a sofa and rug (Contents). Two payments "
           f"each deducted {gbp(px[0]['excess_deducted_gbp'])}. H-1.2 says the excess applies to each section, and the claim records an excess of "
           f"{gbp(c['excess_gbp'])}, which the two deductions equal.",
           "No action.",
           """SELECT claim_id FROM claim_payments WHERE excess_deducted_gbp > 0 GROUP BY claim_id HAVING count(DISTINCT section) > 1""",
           [("claims", c["claim_id"], "claim under two sections", 1)] + [("claim_payments", x["payment_id"], "excess for one section", 0) for x in px])

    da = next(i for i in items("overlap_a") if i["category"] == "Drying")
    db = next(i for i in items("overlap_b") if i["category"] == "Drying")
    sup = da["supplier_id"]
    dpays = [x for k in ("overlap_a", "overlap_b") for x in pays(k) if x["supplier_id"] == sup]
    assert len(dpays) == 2, "both drying invoices must be paid by the extract"
    b.case("CASE-07", "One drying contractor's invoice charged to two claims for the same seven days", "overlapping_invoices",
           "Genuine exception", "High", "R-05", "A2, A6, A7",
           f"Supplier {sup}, a drying and restoration firm that joined the panel in June 2026, invoiced {gbp(da['agreed_amount_gbp'])} on claim "
           f"{cid('overlap_a')} (invoice {da['document_ref']}) and the same amount on claim {cid('overlap_b')} (invoice {db['document_ref']}), each for "
           f"'3 dehumidifiers and 2 air movers, 7 days' from {long(da['service_start'])} to {long(da['service_end'])}. The two homes are in different "
           f"towns, with different policyholders and handlers. The second invoice number is the first with '/2' added. Both invoices have been paid, "
           f"{gbp(sum(x['gross_amount_gbp'] for x in dpays))} in all.",
           "Refer to Claims Validation. Ask the supplier for equipment logs and moisture readings for both homes; recover one payment if the "
           "equipment was at one home; review the supplier's other invoices.",
           """SELECT i.item_id FROM claim_items i JOIN claim_items j ON j.supplier_id = i.supplier_id AND j.claim_id <> i.claim_id
              AND j.agreed_amount_gbp = i.agreed_amount_gbp AND j.service_start <= i.service_end AND i.service_start <= j.service_end""",
           [("claim_items", da["item_id"], "drying invoice", 1), ("claim_items", db["item_id"], "same drying invoice on a second claim", 1),
            ("suppliers", sup, "drying contractor", 0)] + [("claim_payments", x["payment_id"], "payment of a drying invoice", 0) for x in dpays])

    na = next(i for i in items("neighbour_a"))
    nb = next(i for i in items("neighbour_b"))
    b.case("CASE-08", "Same roofer, same day, two claims at one postcode", "shared_supplier_lookalike",
           "Benign lookalike", "None", "R-05", "A2, A6, A8",
           f"Claims {cid('neighbour_a')} and {cid('neighbour_b')} are from neighbouring semi-detached houses sharing the postcode "
           f"{pol('neighbour_a')['postcode']}. Both roofs were damaged in the storm of 23 September. The same roofer, {na['supplier_id']}, repaired both "
           f"on {long(na['document_date'])} and sent two invoices with different numbers and amounts ({gbp(na['agreed_amount_gbp'])} and "
           f"{gbp(nb['agreed_amount_gbp'])}), each describing that house's damage.",
           "No action.",
           """SELECT i.item_id FROM claim_items i JOIN claim_items j ON j.supplier_id = i.supplier_id AND j.claim_id <> i.claim_id
              AND j.document_date = i.document_date
              JOIN claims ci ON ci.claim_id = i.claim_id JOIN claims cj ON cj.claim_id = j.claim_id
              JOIN policies pi ON pi.policy_id = ci.policy_id JOIN policies pj ON pj.policy_id = cj.policy_id
              WHERE pi.postcode = pj.postcode""",
           [("claim_items", na["item_id"], "roof repair invoice", 1), ("claim_items", nb["item_id"], "neighbour's roof repair invoice", 1)])

    c = claim("no_evidence")
    b.case("CASE-09", "Theft claim paid in full with no crime reference and no proof of ownership", "insufficient_evidence",
           "Genuine exception", "Medium", "R-04, H-6.1, H-6.2", "A3, A8",
           f"Claim {c['claim_id']} is for a laptop, a phone and a gold chain, {gbp(c['claimed_amount_gbp'])} in all, taken from a house with an open back "
           f"door. Each item is over £500. The claim has no police crime reference and no receipt, statement or photograph for any item, and its "
           f"evidence status is Insufficient. The handler still proposed {gbp(c['proposed_settlement_gbp'])}, approved it on their own authority on "
           f"{long(c['decision_date'])}, and paid it the next day, noting the 10-working-day target.",
           "Ask the policyholder for the crime reference and proof of ownership. Refer to Claims Validation if they cannot be provided. Remind the "
           "team that the target does not override R-04.",
           """SELECT claim_id FROM claims WHERE evidence_status = 'Insufficient' AND proposed_settlement_gbp IS NOT NULL""",
           [("claims", c["claim_id"], "settled without evidence", 1)] + [("claim_items", i["item_id"], "item with no proof", 0) for i in items("no_evidence")]
           + [("claim_payments", x["payment_id"], "settlement paid", 0) for x in pays("no_evidence")])

    c = claim("alt_proof")
    b.case("CASE-10", "Theft claim with no receipts, proved by card statements and photographs", "alternative_proof_lookalike",
           "Benign lookalike", "None", "R-04, H-6.2", "A3, A8",
           f"Claim {c['claim_id']} is for an e-bike, a laptop and a television, {gbp(c['claimed_amount_gbp'])} in all, after a burglary. There are no "
           f"receipts, but H-6.2 accepts a bank or card statement or a photograph showing the item, and those are held. The crime reference is recorded.",
           "No action.",
           """SELECT DISTINCT i.claim_id FROM claim_items i JOIN claims c ON c.claim_id = i.claim_id
              WHERE c.claim_type = 'Theft' AND i.claimed_amount_gbp > 500 AND i.document_type IN ('Bank statement', 'Photograph')""",
           [("claims", c["claim_id"], "proof accepted under H-6.2", 1)] + [("claim_items", i["item_id"], "item proved by statement or photograph", 0) for i in items("alt_proof")])

    c, x = claim("wrong_decline"), complaint("wrong_decline")
    rep = next(i for i in items("wrong_decline") if i["document_type"] == "Report")
    b.case("CASE-11", "Escape of water declined as wear and tear, against the plumber's report", "wrongful_decline",
           "Genuine exception", "High", "R-06, R-08, H-2.2, H-5.1", "A3, A1, A8",
           f"Claim {c['claim_id']} was declined on {long(c['decision_date'])} under H-5.1 (wear and tear and gradual damage). The plumber's report "
           f"{rep['document_ref']} says the tap hose burst suddenly and the cabinet and floor were dry and sound before the escape. A sudden escape "
           f"from a fixed installation is covered by H-2.2. The policyholder complained ({x['complaint_id']}); the complaint was not upheld on "
           f"{long(x['resolved_date'])} by repeating the decline, without weighing the report, as R-08 requires. Claimed: "
           f"{gbp(c['claimed_amount_gbp'])}.",
           "Overturn the decline, accept the claim under H-2.2, and reopen the complaint with a new final response and redress for the delay.",
           """SELECT c.claim_id FROM claims c WHERE c.decline_clause_id = 'H-5.1' AND EXISTS (SELECT 1 FROM claim_items i
              WHERE i.claim_id = c.claim_id AND i.document_type = 'Report' AND i.description LIKE '%Sudden failure%')""",
           [("claims", c["claim_id"], "wrongly declined", 1), ("claim_items", rep["item_id"], "report showing a sudden escape", 0),
            ("complaints", x["complaint_id"], "complaint wrongly not upheld", 0)])

    c, x = claim("right_decline"), complaint("right_decline")
    rep = next(i for i in items("right_decline") if i["document_type"] == "Report")
    b.case("CASE-12", "Shower leak declined as gradual damage, supported by the plumber's report", "correct_decline_lookalike",
           "Benign lookalike", "None", "R-06, R-08, H-5.1", "A3, A8",
           f"Claim {c['claim_id']} was declined under H-5.1. The plumber's report {rep['document_ref']} says water seeped through a perished shower "
           f"seal over several months. That is the gradual damage H-5.1 names. The complaint {x['complaint_id']} was not upheld with that reason, "
           f"and the policyholder was told of the right to refer to the Financial Ombudsman Service.",
           "No action.",
           """SELECT c.claim_id FROM claims c WHERE c.decline_clause_id = 'H-5.1' AND EXISTS (SELECT 1 FROM claim_items i
              WHERE i.claim_id = c.claim_id AND i.document_type = 'Report' AND i.description LIKE '%over several months%')""",
           [("claims", c["claim_id"], "correctly declined", 1), ("claim_items", rep["item_id"], "report showing gradual damage", 0),
            ("complaints", x["complaint_id"], "complaint correctly not upheld", 0)])


NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
TARGET_DAYS = 10
STORY_APPROVED = True  # approved by the user on 20 October 2026


def settled_within_target(rows):
    """Claims settled by the extract, and how many were fully paid within TARGET_DAYS working days of notification."""
    last = defaultdict(lambda: None)
    for p in rows["claim_payments"]:
        if p["payment_type"] in ("Final settlement", "Supplier payment", "Interim payment"):
            last[p["claim_id"]] = max(last[p["claim_id"]] or "", p["payment_date"])
    settled = [c for c in rows["claims"] if c["claim_status"] == "Settled"]
    fast = [c for c in settled if business_days(D.fromisoformat(c["notified_date"]), D.fromisoformat(last[c["claim_id"]])) <= TARGET_DAYS]
    return settled, fast


def business_story(rows):
    """The firm's current situation. Paragraphs are separated by blank lines; lines starting '- ' are list items.
    Every figure is calculated from the rows, and checks() tests every claim against the data."""
    claims, pols = rows["claims"], rows["policies"]
    by_id = {p["policy_id"]: p for p in pols}
    home = sum(1 for c in claims if by_id[c["policy_id"]]["product"].startswith("Home"))
    storm = [c for c in claims if c["claim_type"] == "Storm" and D.fromisoformat(c["incident_date"]) == STORM_DATE]
    pcw = sum(1 for p in pols if p["sales_channel"] == "Price comparison website")
    settled, fast = settled_within_target(rows)
    status = defaultdict(int)
    for c in claims:
        status["open" if c["claim_status"].startswith("Open") else c["claim_status"].lower()] += 1
    interim = sum(1 for p in rows["claim_payments"] if p["payment_type"] == "Interim payment")
    total = sum(c["claimed_amount_gbp"] for c in claims)
    return "\n".join([
        "Thameside Insurance is the general insurer of Thameside Financial Group plc. It sells home and motor insurance to people "
        "in London and the South East, directly, through price comparison websites and through brokers. Its claims team in "
        "Croydon checks each claim against the policy wording, agrees the cost, and then settles or declines it.",
        "",
        "Several pressures have built up this year:",
        f"- Storm. High winds and heavy rain on {STORM_DATE.day} September brought {len(storm)} storm claims in a week, on top of the "
        "usual flow. The same handlers deal with every kind of claim.",
        f"- Price comparison sales. More policies are now sold through price comparison websites. {pcw} of the {len(pols)} policies "
        "claimed on in September were first bought that way. Cover can start the day after a quote.",
        f"- Settlement target. The board set a target to settle simple claims within {NUMBER_WORDS[TARGET_DAYS]} working days of "
        f"notification. {len(fast)} of the {len(settled)} claims settled by the extract met it.",
        f"- Interim payments. Handlers may make an interim payment before a claim is settled, for example when a policyholder "
        f"cannot wait or a contractor needs paying for work so far. {NUMBER_WORDS[interim].capitalize()} were made on September's claims.",
        f"- New restoration contractor. A second drying and restoration firm joined the supplier panel in "
        f"{RESTORATION_PANEL_JOINED.strftime('%B %Y')} to cope with demand. Its invoices arrive by email.",
        "- Consumer Duty. The FCA expects insurers to show that claims are paid fairly and declined only for good reason. The "
        "board has asked for assurance on declines and complaints.",
        "",
        f"The Head of Claims asked for a review of every claim notified in September 2026. There are {len(claims)}: {home} home and "
        f"{len(claims) - home} motor, with £{total:,.2f} claimed. At the extract on {EXTRACT_DATE.day} October:",
        f"- {status['settled']} are settled.",
        f"- {status['open']} are open.",
        f"- {status['declined']} were declined and {status['withdrawn']} withdrawn.",
        f"- Policyholders have made {len(rows['complaints'])} complaints.",
    ])


def build(rng):
    b = Builder(rng)
    b.lookups()
    b.normal_home()
    b.normal_motor()
    b.planted()
    b.finalise()
    record_cases(b)
    rules = [{"rule_id": r, "category": c, "title": t, "statement": s, "related_tables": RULE_TABLES[r]} for r, c, t, s in RULES]
    facts = [
        ("dataset", "insurance_claims"),
        ("title", "Insurance claims"),
        ("firm", firm.FIRM_NAME),
        ("insurer", "Thameside Insurance, the group's general insurer"),
        ("scenario", "The claims team assesses the home and motor claims notified in September 2026 against the policy terms."),
        ("period", "Claims notified 2026-09-01 to 2026-09-30"),
        ("extract_date", EXTRACT.strftime("%Y-%m-%d %H:%M")),
        ("currency", "GBP"),
        ("seed", firm.SEED),
        ("disclaimer", firm.DISCLAIMER + " Policyholders and suppliers are identified by reference only. The policy wordings, "
                                         "crime references and valuations are invented for the study."),
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

    # The business story's claims must hold in the data.
    claims = [
        (q("SELECT count(*) FROM staff WHERE job_title = 'Claims Handler' AND office = 'Croydon'")[0][0]
         > q("SELECT count(*) FROM staff WHERE job_title = 'Claims Handler' AND office <> 'Croydon'")[0][0],
         "the claims team is mainly in Croydon"),
        (q("SELECT count(*) FROM claims WHERE claim_type = 'Storm' AND incident_date = ? AND notified_date <= date(?, '+6 days')",
           iso(STORM_DATE), iso(STORM_DATE))[0][0] == q("SELECT count(*) FROM claims WHERE claim_type = 'Storm' AND incident_date = ?", iso(STORM_DATE))[0][0],
         "every storm claim for 23 September was notified within a week"),
        (q("SELECT count(*) FROM suppliers WHERE supplier_type = 'Drying and restoration'")[0][0] == 2
         and q("SELECT max(joined_panel_date) FROM suppliers WHERE supplier_type = 'Drying and restoration'")[0][0] == iso(RESTORATION_PANEL_JOINED),
         "a second drying and restoration firm joined the panel in June 2026"),
        (q("SELECT count(*) FROM claim_payments WHERE payment_type = 'Interim payment'")[0][0] > 0, "interim payments were made"),
        (q("SELECT count(*) FROM policies WHERE sales_channel = 'Price comparison website' AND first_incepted >= '2026-01-01'")[0][0] > 0,
         "policies have been sold through price comparison websites this year"),
        (q("SELECT count(*) FROM claims WHERE claim_status = 'Declined'")[0][0] > 0 and q("SELECT count(*) FROM complaints")[0][0] > 0,
         "there are declines and complaints to give assurance on"),
    ]
    errors += [f"story: {text} is not true in the data" for ok, text in claims if not ok]

    ranges = {"claims": (95, 105), "policies": (90, 105), "claim_items": (150, 260), "claim_payments": (80, 200), "complaints": (8, 15)}
    for t, (lo, hi) in ranges.items():
        n = q(f"SELECT count(*) FROM {t}")[0][0]
        if not lo <= n <= hi:
            errors.append(f"{t}: {n} rows, expected {lo}-{hi}")

    for cid_, inc, notified, start, end in q("""SELECT c.claim_id, c.incident_date, c.notified_date, p.cover_start, p.cover_end
                                               FROM claims c JOIN policies p ON p.policy_id = c.policy_id"""):
        if not iso(MONTH_START) <= notified <= iso(MONTH_END):
            errors.append(f"{cid_}: notified outside September")
        if inc > notified:
            errors.append(f"{cid_}: incident after notification")
        if inc > end:
            errors.append(f"{cid_}: incident after the policy ended")
    # Arithmetic: proposed settlement is the agreed items less the excess; payments never exceed what was agreed.
    for cid_, prop, ex, agreed in q("""SELECT c.claim_id, c.proposed_settlement_gbp, c.excess_gbp,
                                       (SELECT sum(agreed_amount_gbp) FROM claim_items i WHERE i.claim_id = c.claim_id)
                                       FROM claims c WHERE c.proposed_settlement_gbp IS NOT NULL"""):
        if round(agreed - ex, 2) != prop:
            errors.append(f"{cid_}: proposed {prop} is not agreed {agreed} less excess {ex}")
    for cid_, status, agreed, gross, reserve, prop in q("""SELECT c.claim_id, c.claim_status,
                                       coalesce((SELECT sum(agreed_amount_gbp) FROM claim_items i WHERE i.claim_id = c.claim_id), 0),
                                       coalesce((SELECT sum(gross_amount_gbp) FROM claim_payments p WHERE p.claim_id = c.claim_id
                                         AND p.payment_type IN ('Interim payment', 'Final settlement', 'Supplier payment')), 0),
                                       c.reserve_gbp, c.proposed_settlement_gbp FROM claims c"""):
        if round(gross, 2) > round(agreed, 2):
            errors.append(f"{cid_}: paid {gross} more than agreed {agreed}")
        if status == "Settled" and (round(gross, 2) != round(agreed, 2) or reserve != 0):
            errors.append(f"{cid_}: settled but not fully paid, or reserve left")
        if status in ("Declined", "Withdrawn") and (reserve != 0 or prop is not None):
            errors.append(f"{cid_}: {status} with a reserve or a proposed settlement")
        if reserve < 0:
            errors.append(f"{cid_}: negative reserve")
    # Authority (R-07) and declines (R-06).
    for cid_, prop, auth in q("""SELECT c.claim_id, c.proposed_settlement_gbp, s.settlement_authority_gbp FROM claims c
                                 JOIN staff s ON s.staff_id = c.approved_by WHERE c.proposed_settlement_gbp IS NOT NULL"""):
        if auth is None or prop > auth:
            errors.append(f"{cid_}: approved beyond authority")
    for (cid_,) in q("""SELECT claim_id FROM claims WHERE (proposed_settlement_gbp IS NOT NULL) <> (approved_by IS NOT NULL AND claim_status <> 'Declined')
                        OR (claim_status = 'Declined') <> (decline_clause_id IS NOT NULL)
                        OR (claim_status = 'Declined' AND approved_by NOT IN (SELECT staff_id FROM staff WHERE settlement_authority_gbp >= 25000))"""):
        errors.append(f"{cid_}: decision fields inconsistent")
    for (cid_,) in q("""SELECT claim_id FROM claims WHERE claim_type IN ('Theft', 'Theft of vehicle', 'Malicious damage')
                        AND evidence_status = 'Complete' AND crime_reference IS NULL"""):
        errors.append(f"{cid_}: complete evidence but no crime reference")
    for (iid,) in q("""SELECT i.item_id FROM claim_items i JOIN claims c ON c.claim_id = i.claim_id
                       WHERE c.evidence_status = 'Complete' AND i.claimed_amount_gbp > 500 AND i.supplier_id IS NULL
                       AND i.document_type NOT IN ('Receipt', 'Bank statement', 'Photograph', 'Valuation', 'Estimate')"""):
        errors.append(f"{iid}: item over £500 without proof on a claim with complete evidence")
    # Payments: working days, by the extract, after notification; final settlement after the decision; excess arithmetic.
    for pid, d, notified, decided, ptype, gross, ex, net in q("""SELECT p.payment_id, p.payment_date, c.notified_date, c.decision_date,
                                       p.payment_type, p.gross_amount_gbp, p.excess_deducted_gbp, p.net_amount_gbp
                                       FROM claim_payments p JOIN claims c ON c.claim_id = p.claim_id"""):
        if not uk.is_working_day(D.fromisoformat(d)) or d > iso(EXTRACT_DATE) or d < notified:
            errors.append(f"{pid}: payment date {d} not a working day, after the extract or before notification")
        if ptype == "Final settlement" and (decided is None or d < decided):
            errors.append(f"{pid}: final settlement before the decision")
        if round(gross - ex, 2) != net or ex < 0:
            errors.append(f"{pid}: gross, excess and net disagree")
    for cid_, section, ex, taken in q("""SELECT c.claim_id, c.section, c.excess_gbp, coalesce(sum(p.excess_deducted_gbp), 0)
                                         FROM claims c LEFT JOIN claim_payments p ON p.claim_id = c.claim_id GROUP BY c.claim_id"""):
        if taken > ex and cid_ not in {r[0] for r in q("SELECT record_id FROM _truth_case_records WHERE case_id = 'CASE-05'")}:
            errors.append(f"{cid_}: excess taken {taken} exceeds {ex}")
    # Complaints (R-08): handling days, summary resolution, redress paid within 10 working days.
    for cmp_, received, resolved, status, days, redress, cid_ in q("""SELECT complaint_id, received_date, resolved_date, status,
                                       handling_days, redress_gbp, claim_id FROM complaints"""):
        end = D.fromisoformat(resolved) if resolved else EXTRACT_DATE
        if days != business_days(D.fromisoformat(received), end):
            errors.append(f"{cmp_}: handling days wrong")
        if status == "Closed - summary resolution" and days > 3:
            errors.append(f"{cmp_}: summary resolution after three business days")
        if days > 40:
            errors.append(f"{cmp_}: beyond eight weeks")
        if redress:
            paid = q("""SELECT payment_date FROM claim_payments WHERE claim_id = ? AND payment_type = 'Complaint redress'
                        AND gross_amount_gbp = ?""", cid_, redress)
            if not paid or business_days(D.fromisoformat(resolved), D.fromisoformat(paid[0][0])) > 10:
                errors.append(f"{cmp_}: redress not paid within 10 working days")
    # Valuables within limits (unless specified), and the documents in time order.
    for (iid,) in q("""SELECT i.item_id FROM claim_items i WHERE i.service_start > i.service_end OR i.document_date > ?""", iso(EXTRACT_DATE)):
        errors.append(f"{iid}: dates out of order")
    for t, col, key in (("claims", "notified_date", "claim_id"), ("policies", "first_incepted", "policy_id"),
                        ("claim_payments", "payment_date", "payment_id"), ("complaints", "received_date", "complaint_id"),
                        ("suppliers", "joined_panel_date", "supplier_id")):
        for a, b_ in q(f"SELECT x.{key}, y.{key} FROM {t} x JOIN {t} y ON x.{col} < y.{col} AND x.{key} > y.{key}"):
            errors.append(f"{t}: {a} is numbered after {b_} but is earlier")
    for (email,) in q("SELECT email FROM staff"):
        if not email.endswith("@" + firm.EMAIL_DOMAIN):
            errors.append(f"{email}: wrong domain")
    return errors
