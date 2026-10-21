"""Thameside Financial Group staff register, version 1.3, 2026-10-20.

Everyone who appears in any dataset, with one name, job and office each. A person who appears in several
datasets is the same person in all of them. Each dataset keeps an identical copy of this file in
generator/common/; when you add a person, add them to every copy and raise the version.

Choose names for new people from outside the name pools in people.py. The procurement generator reserves every
register name when it invents supplier contacts, so a pool name added here changes procurement's data.

Fields: first name, last name, gender (for pronouns in generated text), job title, department, office.
"""

PEOPLE = {
    # Finance, Technology, Facilities, People, Legal and Compliance, Executive (first used in procurement)
    "TFG-001": ("Ioana", "Dumitru", "f", "Chief Financial Officer", "Finance", "City"),
    "TFG-002": ("Usman", "Khan", "m", "Finance Director", "Finance", "City"),
    "TFG-003": ("Philippa", "Hendry", "f", "Head of Finance Operations", "Finance", "Croydon"),
    "TFG-004": ("Yusuf", "Haddad", "m", "Accounts Payable Assistant", "Finance", "Croydon"),
    "TFG-005": ("Sarah", "Barker", "f", "Senior Accounts Payable Assistant", "Finance", "Croydon"),
    "TFG-006": ("Jermaine", "Grant", "m", "Procurement Officer", "Finance", "Canary Wharf"),
    "TFG-007": ("Joanne", "Fairbairn", "f", "Senior Procurement Officer", "Finance", "City"),
    "TFG-008": ("James", "Ellison", "m", "Head of Technology", "Technology", "Canary Wharf"),
    "TFG-009": ("Natalie", "Bailey", "f", "IT Service Delivery Manager", "Technology", "Canary Wharf"),
    "TFG-010": ("Stephen", "Rowe", "m", "Infrastructure Manager", "Technology", "Canary Wharf"),
    "TFG-011": ("Neha", "Iyer", "f", "Head of Facilities and Property", "Facilities", "City"),
    "TFG-012": ("Tunde", "Okonkwo", "m", "Facilities Manager, Canary Wharf", "Facilities", "Canary Wharf"),
    "TFG-013": ("Ana", "Bianchi", "f", "Office Services Manager, Croydon", "Facilities", "Croydon"),
    "TFG-014": ("Lucy", "Pike", "f", "Head of People", "People", "City"),
    "TFG-015": ("Paul", "Pham", "m", "Talent Acquisition Manager", "People", "City"),
    "TFG-016": ("Omar", "Kaya", "m", "General Counsel", "Legal and Compliance", "City"),
    "TFG-017": ("Nicola", "Harding", "f", "Compliance Manager", "Legal and Compliance", "City"),
    "TFG-018": ("Grace", "Lam", "f", "Information Security Manager", "Technology", "Canary Wharf"),
    "TFG-019": ("Shahid", "Rahman", "m", "Chief Executive Officer", "Executive", "City"),
    "TFG-020": ("Ciarán", "O'Sullivan", "m", "Financial Controller", "Finance", "City"),
    # Regulatory reporting, finance data and credit risk (first used in regulatory reporting)
    "TFG-021": ("João", "Rossi", "m", "Head of Regulatory Reporting", "Regulatory Reporting", "City"),
    "TFG-022": ("Emma", "Waller", "f", "Regulatory Reporting Manager", "Regulatory Reporting", "City"),
    "TFG-023": ("Mihai", "Ionescu", "m", "Regulatory Reporting Analyst", "Regulatory Reporting", "City"),
    "TFG-024": ("Ama", "Mensah", "f", "Regulatory Reporting Analyst", "Regulatory Reporting", "Croydon"),
    "TFG-025": ("Sophie", "Mistry", "f", "Data Governance Lead", "Finance Data", "Canary Wharf"),
    "TFG-026": ("Rahim", "Ahmed", "m", "Finance Systems Analyst", "Finance Data", "Canary Wharf"),
    "TFG-027": ("Gareth", "Lambert", "m", "LendingCore Product Owner", "Technology", "Canary Wharf"),
    "TFG-028": ("Claire", "Fletcher", "f", "Retail Systems Product Owner", "Technology", "Canary Wharf"),
    "TFG-029": ("Ming", "Cheung", "m", "Credit Risk Data Manager", "Credit Risk", "Croydon"),
    # Financial crime and business banking (first used in AML)
    "TFG-030": ("Hodan", "Warsame", "f", "Money Laundering Reporting Officer", "Financial Crime", "City"),
    "TFG-031": ("Arun", "Sivakumar", "m", "Head of Financial Crime Operations", "Financial Crime", "Canary Wharf"),
    "TFG-032": ("Priya", "Shah", "f", "Transaction Monitoring Manager", "Financial Crime", "Canary Wharf"),
    "TFG-033": ("Hamza", "Malik", "m", "Financial Crime Analyst", "Transaction Monitoring", "Canary Wharf"),
    "TFG-034": ("Elif", "Mansour", "f", "Financial Crime Analyst", "Transaction Monitoring", "Croydon"),
    "TFG-035": ("Yaw", "Asante", "m", "Financial Crime Analyst", "Transaction Monitoring", "Croydon"),
    "TFG-036": ("Layla", "Demir", "f", "Senior Investigator", "Financial Crime Investigations", "Canary Wharf"),
    "TFG-037": ("Kelvin", "Ng", "m", "Sanctions Screening Lead", "Sanctions", "Canary Wharf"),
    "TFG-038": ("Anjali", "Rao", "f", "Customer Due Diligence Team Leader", "Customer Due Diligence", "Croydon"),
    "TFG-039": ("Marek", "Kowalczyk", "m", "Relationship Manager, Business Banking", "Business Banking", "City"),
    "TFG-040": ("Farzana", "Begum", "f", "Relationship Manager, Business Banking", "Business Banking", "Croydon"),
    # Insurance claims and complaints at Thameside Insurance (first used in insurance claims)
    "TFG-041": ("Caroline", "Ashby", "f", "Head of Claims", "Claims", "City"),
    "TFG-042": ("Femi", "Oyelaran", "m", "Claims Manager", "Claims", "Croydon"),
    "TFG-043": ("Joanna", "Szymańska", "f", "Claims Team Leader", "Claims", "Croydon"),
    "TFG-044": ("Ronan", "Kehoe", "m", "Claims Handler", "Claims", "Croydon"),
    "TFG-045": ("Ruksana", "Akhtar", "f", "Claims Handler", "Claims", "Croydon"),
    "TFG-046": ("Dwayne", "Roberts", "m", "Claims Handler", "Claims", "Croydon"),
    "TFG-047": ("Mei", "Tan", "f", "Claims Handler", "Claims", "Canary Wharf"),
    "TFG-048": ("Nikhil", "Bhatt", "m", "Claims Validation Investigator", "Claims", "Canary Wharf"),
    "TFG-049": ("Bethany", "Price", "f", "Complaints Handler", "Customer Outcomes", "Croydon"),
    "TFG-050": ("Adwoa", "Darko", "f", "Customer Outcomes Manager", "Customer Outcomes", "City"),
    # Business banking credit at Thameside Bank (first used in SME lending)
    "TFG-051": ("Helena", "Marchetti", "f", "Head of Business Banking Credit", "Business Banking Credit", "City"),
    "TFG-052": ("Kunle", "Adesanya", "m", "Senior Credit Manager", "Business Banking Credit", "City"),
    "TFG-053": ("Rebecca", "Thornton", "f", "Credit Manager", "Business Banking Credit", "Croydon"),
    "TFG-054": ("Sunil", "Varma", "m", "Credit Manager", "Business Banking Credit", "Croydon"),
    "TFG-055": ("Tariq", "Siddiqui", "m", "Relationship Manager, Business Banking", "Business Banking", "City"),
    "TFG-056": ("Jade", "Ofori", "f", "Relationship Manager, Business Banking", "Business Banking", "Canary Wharf"),
    # Treasury and liquidity risk at Thameside Bank (first used in treasury liquidity)
    "TFG-057": ("Victoria", "Okwuosa", "f", "Head of Treasury", "Treasury", "City"),
    "TFG-058": ("Duncan", "Freer", "m", "Asset and Liability Manager", "Treasury", "City"),
    "TFG-059": ("Rajesh", "Venkatesan", "m", "Senior Money Markets Dealer", "Treasury", "City"),
    "TFG-060": ("Chloe", "Brannigan", "f", "Money Markets Dealer", "Treasury", "City"),
    "TFG-061": ("Bartosz", "Wieczorek", "m", "Liquidity Forecasting Analyst", "Treasury", "Canary Wharf"),
    "TFG-062": ("Yasmin", "Qadri", "f", "Liquidity Risk Manager", "Risk", "Canary Wharf"),
}


def person(register_id):
    first, last, gender, title, department, office = PEOPLE[register_id]
    return {"first_name": first, "last_name": last, "gender": gender, "job_title": title,
            "department": department, "office": office}


def surnames():
    """Surnames in the register, so other generated people (contacts, customers) never share them."""
    return {p[1] for p in PEOPLE.values()}


def check(staff_rows, id_column, mapping):
    """Each dataset staff row must match its register entry by name, job title and office."""
    errors = []
    for row in staff_rows:
        rid = mapping.get(row[id_column])
        if rid is None:
            errors.append(f"staff register: {row[id_column]} has no register ID")
            continue
        p = person(rid)
        for k in ("first_name", "last_name", "job_title", "office"):
            if row.get(k) != p[k]:
                errors.append(f"staff register: {row[id_column]} {k} is {row.get(k)!r}, register {rid} says {p[k]!r}")
    return errors
