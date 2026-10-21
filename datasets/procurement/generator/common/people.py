"""Curated personal names weighted to London's mix of backgrounds.

Each background lists first names as (name, gender) and surnames. A surname given as
(male_form, female_form) changes with gender, as Polish surnames do.
"""

import unicodedata

BACKGROUNDS = {
    # weight, first names, surnames
    "british": (34, [
        ("Oliver", "m"), ("James", "m"), ("Thomas", "m"), ("Daniel", "m"), ("Matthew", "m"),
        ("Paul", "m"), ("Richard", "m"), ("Gareth", "m"), ("Stephen", "m"), ("Graham", "m"),
        ("Rhys", "m"), ("Tom", "m"), ("Sarah", "f"), ("Emma", "f"), ("Rachel", "f"),
        ("Hannah", "f"), ("Lucy", "f"), ("Charlotte", "f"), ("Joanne", "f"), ("Claire", "f"),
        ("Fiona", "f"), ("Helen", "f"), ("Nicola", "f"), ("Philippa", "f"), ("Sophie", "f"),
    ], [
        "Whitmore", "Harding", "Pearce", "Holloway", "Fletcher", "Marsh", "Godfrey", "Bannister",
        "Kendrick", "Ashworth", "Pike", "Dawson", "Ellison", "Hughes", "Turner", "Barker", "Mills",
        "Rowe", "Chambers", "Sutton", "Lambert", "Fairbairn", "Prescott", "Waller", "Hendry",
    ]),
    "irish": (4, [
        ("Aoife", "f"), ("Niamh", "f"), ("Siobhan", "f"), ("Orla", "f"),
        ("Ciarán", "m"), ("Declan", "m"), ("Conor", "m"), ("Eoin", "m"),
    ], ["O'Sullivan", "Byrne", "Doyle", "Kavanagh", "Gallagher", "Moran", "Brennan"]),
    "polish": (4, [
        ("Katarzyna", "f"), ("Agnieszka", "f"), ("Magdalena", "f"),
        ("Piotr", "m"), ("Tomasz", "m"), ("Marek", "m"),
    ], [("Kowalczyk", "Kowalczyk"), ("Zieliński", "Zielińska"), ("Wójcik", "Wójcik"),
        ("Lewandowski", "Lewandowska"), ("Nowak", "Nowak")]),
    "romanian": (2, [("Andrei", "m"), ("Mihai", "m"), ("Ioana", "f"), ("Elena", "f")],
                 ["Popescu", "Ionescu", "Dumitru", "Stan"]),
    "southern_european": (3, [
        ("Marco", "m"), ("João", "m"), ("Giulia", "f"), ("Francesca", "f"), ("Ana", "f"),
    ], ["Rossi", "Esposito", "Bianchi", "Ferreira", "Costa", "Pereira"]),
    "indian": (10, [
        ("Rahul", "m"), ("Vikram", "m"), ("Arjun", "m"), ("Sanjay", "m"), ("Rohan", "m"),
        ("Priya", "f"), ("Anjali", "f"), ("Neha", "f"), ("Kavita", "f"), ("Deepa", "f"),
    ], ["Patel", "Shah", "Mehta", "Sharma", "Gupta", "Iyer", "Desai", "Kapoor", "Chauhan",
        "Rao", "Mistry"]),
    "pakistani": (5, [
        ("Imran", "m"), ("Hamza", "m"), ("Bilal", "m"), ("Usman", "m"),
        ("Ayesha", "f"), ("Sana", "f"), ("Zara", "f"),
    ], ["Khan", "Hussain", "Malik", "Qureshi", "Iqbal", "Chaudhry"]),
    "bangladeshi": (4, [
        ("Shahid", "m"), ("Rahim", "m"), ("Nusrat", "f"), ("Tahmina", "f"), ("Farzana", "f"),
    ], ["Rahman", "Ahmed", "Chowdhury", "Islam", ("Uddin", "Begum"), ("Miah", "Khatun")]),
    "tamil": (2, [("Arun", "m"), ("Dinesh", "m"), ("Meera", "f"), ("Thushara", "f")],
              ["Sivakumar", "Rajendran", "Krishnan", "Selvarajah"]),
    "nigerian": (6, [
        ("Chinedu", "m"), ("Emeka", "m"), ("Tunde", "m"), ("Oluwaseun", "m"),
        ("Ngozi", "f"), ("Funmilayo", "f"), ("Adaeze", "f"), ("Folake", "f"), ("Ifeoma", "f"),
    ], ["Okafor", "Adeyemi", "Okonkwo", "Balogun", "Eze", "Adebayo", "Nwosu", "Ogunleye"]),
    "ghanaian": (3, [("Kwame", "m"), ("Kofi", "m"), ("Yaw", "m"),
                     ("Ama", "f"), ("Akosua", "f"), ("Efua", "f")],
                 ["Mensah", "Boateng", "Asante", "Owusu", "Agyeman"]),
    "somali": (2, [("Abdi", "m"), ("Faisal", "m"), ("Hodan", "f"), ("Amina", "f")],
               ["Farah", "Warsame", "Hassan", "Ali"]),
    "caribbean": (4, [
        ("Leon", "m"), ("Andre", "m"), ("Jermaine", "m"),
        ("Natalie", "f"), ("Simone", "f"), ("Kerry-Ann", "f"),
    ], ["Campbell", "Thompson", "Grant", "Francis", "Bailey", "Clarke"]),
    "chinese": (4, [("Kelvin", "m"), ("Jason", "m"), ("Ming", "m"),
                    ("Michelle", "f"), ("Grace", "f"), ("Yan", "f")],
                ["Chen", "Wong", "Lam", "Cheung", "Zhang", "Liu", "Ng"]),
    "vietnamese": (1, [("Minh", "m"), ("Hieu", "m"), ("Linh", "f"), ("Thao", "f")],
                   ["Nguyen", "Tran", "Pham"]),
    "turkish_arab": (4, [("Emre", "m"), ("Omar", "m"), ("Yusuf", "m"),
                         ("Elif", "f"), ("Zeynep", "f"), ("Layla", "f"), ("Mariam", "f")],
                     ["Yılmaz", "Demir", "Kaya", "Haddad", "Mansour", "Aziz"]),
}


class NamePicker:
    """Draws names with no repeated first name or surname, avoiding reserved surnames."""

    def __init__(self, rng, reserved_surnames=()):
        self.rng = rng
        self.used = set()
        self.reserved = set(reserved_surnames)
        self.keys = list(BACKGROUNDS)
        self.weights = [BACKGROUNDS[k][0] for k in self.keys]

    def pick(self, gender=None):
        for _ in range(500):
            bg = self.rng.choices(self.keys, self.weights)[0]
            _, firsts, surnames = BACKGROUNDS[bg]
            # About one in eight people of a minority background has an anglicised first name.
            if bg != "british" and self.rng.random() < 0.12:
                firsts = BACKGROUNDS["british"][1]
            pool = [f for f in firsts if gender is None or f[1] == gender]
            first, g = self.rng.choice(pool)
            sur = self.rng.choice(surnames)
            if isinstance(sur, tuple):
                sur = sur[0] if g == "m" else sur[1]
            if sur in self.reserved or any(f == first or s == sur for f, s in self.used):
                continue
            self.used.add((first, sur))
            return first, sur
        raise RuntimeError("name pool exhausted")


def ascii_slug(text):
    text = unicodedata.normalize("NFKD", text.replace("ı", "i").replace("ł", "l")).encode("ascii", "ignore").decode()
    return "".join(c for c in text.lower() if c.isalnum() or c == "-")


def email_for(first, last, domain):
    return f"{ascii_slug(first)}.{ascii_slug(last)}@{domain}"
