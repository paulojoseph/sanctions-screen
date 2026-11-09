#!/usr/bin/env python3
"""Build the fictional list fixtures and the example customer files.

Everything here is made up. Names are assembled from common given names and family names
of a few naming traditions, so a generated person can look like a real one by accident.
None of them is a real listed person or company.

Output goes to tests/fixtures/lists/ (one file per source, in the official format),
tests/fixtures/lists_old/ (an older UN snapshot for `diff`) and examples/.
The generator is seeded and deterministic: running it twice gives identical bytes.

    python scripts/make_fixtures.py
"""

from __future__ import annotations

import csv
import random
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

SEED = 20250317
ROOT = Path(__file__).resolve().parent.parent
LISTS = ROOT / "tests" / "fixtures" / "lists"
LISTS_OLD = ROOT / "tests" / "fixtures" / "lists_old"
EXAMPLES = ROOT / "examples"

PUBLISH = date(2025, 3, 14)
OLD_PUBLISH = date(2025, 1, 17)

# --------------------------------------------------------------------------------------
# name material: (latin spellings, native script or None)
# --------------------------------------------------------------------------------------

AR_GIVEN = [
    (["Abdul Rahman", "Abd al-Rahman", "Abdurrahman"], "عبد الرحمن"),
    (["Mohammed", "Muhammad", "Mohamed"], "محمد"), (["Ahmed", "Ahmad"], "أحمد"),
    (["Khalid", "Khaled"], "خالد"), (["Hassan", "Hasan"], "حسن"),
    (["Hussein", "Husayn", "Hussain"], "حسين"), (["Omar", "Umar"], "عمر"),
    (["Yusuf", "Youssef", "Yousef"], "يوسف"), (["Ibrahim", "Ebrahim"], "إبراهيم"),
    (["Mahmoud", "Mahmud"], "محمود"), (["Mustafa", "Mostafa"], "مصطفى"),
    (["Tariq", "Tarek"], "طارق"), (["Samir"], "سمير"), (["Nasser", "Nasir"], "ناصر"),
    (["Walid"], "وليد"), (["Karim"], "كريم"), (["Faisal", "Faysal"], "فيصل"),
    (["Salim", "Saleem"], "سالم"), (["Jamal"], "جمال"), (["Rashid", "Rasheed"], "رشيد"),
    (["Bilal"], "بلال"), (["Ali"], "علي"), (["Idris"], "إدريس"), (["Zayd", "Zaid"], "زيد"),
]
AR_FAMILY = [
    (["al-Haddad", "Haddad"], "الحداد"), (["al-Masri", "Elmasri", "Masri"], "المصري"),
    (["al-Tikriti", "Tikriti"], "التكريتي"), (["al-Sayegh", "Sayegh"], "الصايغ"),
    (["Khoury"], "خوري"), (["al-Najjar", "Najjar"], "النجار"),
    (["Mansour", "Mansur"], "منصور"), (["al-Qasim", "Qasim"], "القاسم"),
    (["Darwish"], "درويش"), (["al-Hamdani", "Hamdani"], "الحمداني"),
    (["Shami"], "شامي"), (["al-Farouk", "Farooq"], "الفاروق"),
    (["al-Zahrani", "Zahrani"], "الزهراني"), (["al-Bakri", "Bakri"], "البكري"),
    (["Nassar"], "نصار"), (["al-Halabi", "Halabi"], "الحلبي"),
    (["Suleiman", "Sulayman"], "سليمان"), (["al-Jabouri", "Jabouri"], "الجبوري"),
]
FA_GIVEN = [
    (["Mohammad Reza", "Mohammadreza"], "محمدرضا"), (["Ali Akbar", "Aliakbar"], "علی اکبر"),
    (["Hossein", "Hosein", "Hussein"], "حسین"), (["Mehdi", "Mahdi"], "مهدی"),
    (["Reza"], "رضا"), (["Davood", "Davoud", "Dawood"], "داود"),
    (["Farhad"], "فرهاد"), (["Kaveh"], "کاوه"), (["Parviz"], "پرویز"),
    (["Siavash", "Siyavash"], "سیاوش"), (["Majid"], "مجید"), (["Behrouz", "Behruz"], "بهروز"),
    (["Fatemeh", "Fatima"], "فاطمه"), (["Zahra"], "زهرا"), (["Maryam"], "مریم"),
]
FA_FAMILY = [
    (["Karimi"], "کریمی"), (["Hosseini", "Hoseini", "Husseini"], "حسینی"),
    (["Rahimi"], "رحیمی"), (["Mousavi", "Musavi"], "موسوی"), (["Ahmadi"], "احمدی"),
    (["Tehrani"], "تهرانی"), (["Sadeghi", "Sadeqi"], "صادقی"), (["Jafari"], "جعفری"),
    (["Nazari"], "نظری"), (["Rostami", "Rustami"], "رستمی"), (["Bagheri", "Baqeri"], "باقری"),
    (["Zarei", "Zare'i"], "زارعی"),
]
RU_GIVEN_M = [
    (["Aleksandr", "Alexander", "Alexandr"], "Александр"), (["Sergei", "Sergey", "Serguei"], "Сергей"),
    (["Dmitri", "Dmitry", "Dmitrii"], "Дмитрий"), (["Nikolai", "Nikolay"], "Николай"),
    (["Vladimir"], "Владимир"), (["Pavel"], "Павел"), (["Yuri", "Yury", "Iurii"], "Юрий"),
    (["Andrei", "Andrey"], "Андрей"), (["Igor"], "Игорь"), (["Viktor", "Victor"], "Виктор"),
    (["Oleg"], "Олег"), (["Konstantin"], "Константин"),
]
RU_GIVEN_F = [
    (["Elena", "Yelena"], "Елена"), (["Olga"], "Ольга"), (["Natalia", "Natalya"], "Наталья"),
    (["Tatiana", "Tatyana"], "Татьяна"), (["Irina"], "Ирина"), (["Svetlana"], "Светлана"),
]
# (stem latin, stem cyrillic, male suffix pair, female suffix pair)
RU_SURNAME = [
    (["Petrov"], "Петров"), (["Volkov"], "Волков"), (["Sokolov"], "Соколов"),
    (["Kuznetsov", "Kuznecov"], "Кузнецов"), (["Smirnov"], "Смирнов"), (["Orlov"], "Орлов"),
    (["Kozlov"], "Козлов"), (["Fedorov", "Fyodorov"], "Фёдоров"), (["Morozov"], "Морозов"),
    (["Popov"], "Попов"), (["Lebedev"], "Лебедев"), (["Zaitsev", "Zaytsev"], "Зайцев"),
    (["Novikov"], "Новиков"), (["Shcherbakov", "Scherbakov"], "Щербаков"),
]
RU_PATRONYMIC = [
    (["Ivanovich"], "Иванович"), (["Petrovich"], "Петрович"), (["Sergeyevich", "Sergeevich"], "Сергеевич"),
    (["Aleksandrovich", "Alexandrovich"], "Александрович"), (["Nikolayevich", "Nikolaevich"], "Николаевич"),
    (["Vladimirovich"], "Владимирович"), (["Yuryevich", "Yurievich"], "Юрьевич"),
    (["Andreyevich", "Andreevich"], "Андреевич"),
]
ZH_SURNAME = [
    (["Wang"], "王"), (["Li"], "李"), (["Zhang"], "张"), (["Liu"], "刘"), (["Chen"], "陈"),
    (["Yang"], "杨"), (["Zhao"], "赵"), (["Huang"], "黄"), (["Zhou"], "周"), (["Wu"], "吴"),
    (["Xu"], "徐"), (["Sun"], "孙"), (["Ma"], "马"), (["Zhu"], "朱"), (["Hu"], "胡"),
    (["Guo"], "郭"), (["He"], "何"), (["Gao"], "高"), (["Lin"], "林"), (["Luo"], "罗"),
]
ZH_GIVEN = [
    (["Wei"], "伟"), (["Fang"], "芳"), (["Lei"], "磊"), (["Jun"], "军"), (["Min"], "敏"),
    (["Qiang"], "强"), (["Yan"], "艳"), (["Yong"], "勇"), (["Jing"], "静"), (["Tao"], "涛"),
    (["Ming"], "明"), (["Chao"], "超"), (["Xiuying", "Xiu Ying"], "秀英"), (["Hua"], "华"),
    (["Jianguo", "Jian Guo"], "建国"), (["Zhiqiang", "Zhi Qiang"], "志强"), (["Hai"], "海"),
]
ES_GIVEN = [
    "José", "María", "Juan", "Carlos", "Luis", "Ana", "Carmen", "Javier", "Miguel", "Rafael",
    "Lucía", "Andrés", "Sofía", "Álvaro", "Inés", "Joaquín", "Ramón", "Mónica", "Julián", "Beatriz",
]
ES_SURNAME = [
    "García", "Rodríguez", "López", "Martínez", "González", "Pérez", "Sánchez", "Fernández",
    "Romero", "Torres", "Ramírez", "Flores", "Gutiérrez", "Núñez", "Peña", "Muñoz", "Ortega",
    "Castillo", "Vázquez", "Domínguez",
]
PT_GIVEN = [
    "João", "Maria", "José", "Ana", "Antônio", "Francisca", "Carlos", "Paulo", "Adriana",
    "Luiz", "Marcos", "Juliana", "Fernando", "Patrícia", "Rogério", "Cláudia", "Gonçalo",
]
PT_SURNAME = [
    "Silva", "Souza", "Pereira", "Oliveira", "Ferreira", "Almeida", "Gonçalves", "Carvalho",
    "Ribeiro", "Barbosa", "Araújo", "Cardoso", "Teixeira", "Nascimento", "Moreira", "Mendonça",
]
PT_PARTICLE = ["da", "dos", "de", "do"]
TR_GIVEN = [
    "Mehmet", "Ahmet", "Mustafa", "Ayşe", "Fatma", "Hüseyin", "İbrahim", "Şükrü", "Çağrı",
    "Emre", "Zeynep", "Burak", "Özlem", "Gökhan", "Ümit", "Hakan", "Selin", "Yağmur",
]
TR_SURNAME = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Öztürk", "Aydın", "Doğan", "Arslan", "Güneş",
    "Koç", "Kurt", "Özdemir", "Çetin", "Yıldız", "Aksoy", "Erdoğan", "Taş",
]

ORG_AR_A = ["Al Noor", "Al Rayyan", "Dar al-Salam", "Gulf Star", "Al Fajr", "Bab al-Mandab",
            "Red Sea", "Al Amal", "Najd", "Sahara", "Qamar", "Al Wafa", "Zahra", "Nile Crest"]
ORG_AR_B = ["Trading", "General Trading", "Logistics", "Holdings", "Exchange", "Money Transfer",
            "Shipping", "Construction", "Petroleum", "Electronics", "Commercial Services"]
ORG_RU_A = [("Volga", "Волга"), ("Sibir", "Сибирь"), ("Baltic", "Балтика"), ("Ural", "Урал"),
            ("Neva", "Нева"), ("Don", "Дон"), ("Kama", "Кама"), ("Altai", "Алтай")]
ORG_RU_B = [("Metall", "Металл"), ("Neftegaz", "Нефтегаз"), ("Torg", "Торг"), ("Stroy", "Строй"),
            ("Transit", "Транзит"), ("Invest", "Инвест"), ("Tekhnika", "Техника")]
ORG_ZH_A = ["Shenzhen Haotian", "Dalian Hengxin", "Ningbo Tongda", "Qingdao Ruifeng",
            "Wuhan Jiahe", "Xiamen Lianfa", "Tianjin Yuhang", "Guangzhou Boyuan"]
ORG_ZH_B = ["Electronics", "Shipping", "Trading", "Technology", "Machinery", "Chemical"]
ORG_LATIN_A = ["Comercializadora Andina", "Transportes Rio Verde", "Importadora del Caribe",
               "Distribuidora Cordillera", "Servicios Maritimos del Sur", "Agroexport Pampa",
               "Inversiones Costa Dorada", "Mineracao Serra Azul"]
ORG_LATIN_LEGAL = ["S.A.", "Ltda", "S.A. de C.V.", "S.R.L.", "C.A."]
ORG_TR_A = ["Boğaziçi", "Ege", "Anadolu", "Marmara", "Karadeniz", "Toros", "Akdeniz", "Trakya"]
ORG_TR_B = ["Ticaret", "Denizcilik", "İnşaat", "Enerji", "Lojistik", "Gıda"]

VESSEL_WORDS = ["Sea", "Star", "Wave", "Breeze", "Horizon", "Pearl", "Eagle", "Falcon", "Neptune",
                "Aurora", "Meridian", "Voyager", "Dawn", "Harbor", "Crest", "Anchor"]

CLEAN_GIVEN = [
    "Rafael", "Camila", "Thiago", "Beatriz", "Lucas", "Fernanda", "Gustavo", "Larissa", "Bruno",
    "Aline", "Rodrigo", "Vanessa", "Diego", "Priscila", "Felipe", "Tatiane", "Matheus", "Renata",
    "Daniel", "Eduarda", "Henrique", "Bianca", "Leandro", "Mariana", "Vinicius", "Carolina",
    "Samuel", "Natália", "Ricardo", "Amanda", "Pedro", "Isabela", "Murilo", "Letícia", "Caio",
    "Débora", "William", "Jessica", "Anthony", "Emily", "Oliver", "Sophie", "Lukas", "Hannah",
    "Matteo", "Giulia", "Erik", "Freya", "Noah", "Chloe", "Stefan", "Ingrid", "Lars", "Marta",
    "Tomás", "Valentina", "Nicolás", "Paula", "Sebastián", "Daniela",
]
CLEAN_SURNAME = [
    "Costa", "Lima", "Rocha", "Martins", "Melo", "Freitas", "Campos", "Duarte", "Barros", "Pinto",
    "Moraes", "Nunes", "Vieira", "Correia", "Lopes", "Dias", "Monteiro", "Cavalcanti", "Rezende",
    "Andrade", "Azevedo", "Bastos", "Coelho", "Fonseca", "Guimarães", "Machado", "Miranda",
    "Pacheco", "Siqueira", "Tavares", "Brandão", "Borges", "Cunha", "Xavier", "Medeiros",
    "Smith", "Johnson", "Miller", "Davis", "Clark", "Walker", "Hall", "Young", "King", "Wright",
    "Schmidt", "Weber", "Becker", "Fischer", "Rossi", "Ferrari", "Bianchi", "Romano", "Larsen",
    "Nielsen", "Hansen", "Dubois", "Moreau", "Laurent", "Blanc", "Vega", "Rivera", "Castro",
    "Herrera", "Molina", "Silveira", "Pires", "Valente", "Bezerra", "Lacerda",
]
CLEAN_COMPANY_A = ["Nova", "Prime", "Atlas", "Vertex", "Aurora", "Delta", "Orion", "Pacifico",
                   "Central", "Horizonte", "Alvorada", "Planalto", "Litoral", "Boreal", "Solaris"]
CLEAN_COMPANY_B = ["Software", "Consultoria", "Alimentos", "Engenharia", "Logística", "Design",
                   "Saúde", "Educação", "Comércio", "Têxtil", "Agro", "Energia", "Digital"]
CLEAN_COUNTRIES = ["BR", "BR", "BR", "BR", "US", "PT", "ES", "AR", "MX", "DE", "FR", "IT", "CL", "UY"]

CULTURE_NAT = {
    "arabic": ["SY", "IQ", "LB", "LY", "YE", "SD", "SO"], "persian": ["IR", "AF"],
    "russian": ["RU", "BY"], "chinese": ["CN"], "spanish": ["VE", "CU", "ES"],
    "portuguese": ["BR", "PT"], "turkish": ["TR"],
}
NAT_LONG = {
    "SY": "Syria", "IQ": "Iraq", "LB": "Lebanon", "LY": "Libya", "YE": "Yemen", "SD": "Sudan",
    "SO": "Somalia", "IR": "Iran", "AF": "Afghanistan", "RU": "Russia", "BY": "Belarus",
    "CN": "China", "VE": "Venezuela", "CU": "Cuba", "ES": "Spain", "BR": "Brazil",
    "PT": "Portugal", "TR": "Turkey",
}
NAT_UN = {**NAT_LONG, "SY": "Syrian Arab Republic", "IR": "Iran (Islamic Republic of)",
          "RU": "Russian Federation", "LY": "Libya"}
OFAC_PROGRAMS = {
    "arabic": ["SDGT", "SYRIA"], "persian": ["IRAN", "IRGC"], "russian": ["RUSSIA-EO14024", "UKRAINE-EO13661"],
    "chinese": ["CYBER2", "DPRK3"], "spanish": ["VENEZUELA", "ILLICIT-DRUGS-EO14059"],
    "portuguese": ["ILLICIT-DRUGS-EO14059"], "turkish": ["SDGT", "IRAN"],
}
UN_LISTS = {"arabic": "Al-Qaida", "persian": "Taliban", "russian": "Libya", "chinese": "DPRK",
            "spanish": "Somalia", "portuguese": "Somalia", "turkish": "Al-Qaida"}
UN_PREFIX = {"Al-Qaida": "QD", "Taliban": "TA", "Libya": "LY", "DPRK": "KP", "Somalia": "SO"}
EU_PROGRAMMES = {"arabic": "SYR", "persian": "IRN", "russian": "RUS", "chinese": "PRK",
                 "spanish": "VEN", "portuguese": "VEN", "turkish": "TAL"}
UK_REGIMES = {"arabic": "Syria", "persian": "Iran", "russian": "Russia", "chinese": "Cyber",
              "spanish": "Venezuela", "portuguese": "Global Human Rights", "turkish": "Counter Terrorism"}


# --------------------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------------------

@dataclass
class V:
    """One Latin spelling of a name."""
    given: str
    family: str
    full: str


@dataclass
class Person:
    key: int
    kind: str  # person | organization | vessel | aircraft
    culture: str
    variants: list[V]
    native: str | None = None
    dob: tuple | None = None  # ("full", y, m, d) | ("year", y) | ("circa", y) | ("range", y, y2)
    nat: list[str] = field(default_factory=list)
    passport: str | None = None
    weak_alias: str | None = None
    female: bool = False
    particle: bool = False  # name contains al/bin/ibn style particles
    sources: list[str] = field(default_factory=list)
    imo: str | None = None
    dob_by_source: dict[str, tuple] = field(default_factory=dict)


@dataclass
class Rec:
    """What one source says about one entity."""
    uid: str
    kind: str
    v: V
    native: str | None
    aliases: list[tuple[str, bool]]  # (name, is_weak)
    dob: tuple | None
    nat: list[str]
    passport: str | None
    culture: str
    person: Person
    listed_on: date = PUBLISH


def mk(given: str, family: str) -> V:
    return V(given, family, f"{given} {family}".strip())


def strip_marks(text: str) -> str:
    out = unicodedata.normalize("NFKD", text.replace("ı", "i").replace("İ", "I"))
    return "".join(c for c in out if not unicodedata.combining(c))


# --------------------------------------------------------------------------------------
# person builders
# --------------------------------------------------------------------------------------

def arabic_person(rng: random.Random, key: int) -> Person:
    g, f, fa = rng.choice(AR_GIVEN), rng.choice(AR_FAMILY), rng.choice(AR_GIVEN)
    gl, fl, fal = g[0], f[0], fa[0]
    given = rng.choice(gl)
    fam = rng.choice(fl)
    father = rng.choice(fal)
    sep = rng.choice(["bin", "ibn"])
    variants = [
        mk(given, f"{sep} {father} {fam}"),
        mk(rng.choice(gl), f"{rng.choice(fal)} {rng.choice(fl).replace('al-', '')}"),
        mk(rng.choice(gl), rng.choice(fl)),
    ]
    native = f"{g[1]} بن {fa[1]} {f[1]}"
    p = Person(key, "person", "arabic", variants, native=native, particle=True)
    p.weak_alias = f"Abu {rng.choice(fal)}"
    return p


def persian_person(rng: random.Random, key: int) -> Person:
    g, f = rng.choice(FA_GIVEN), rng.choice(FA_FAMILY)
    variants = [mk(rng.choice(g[0]), rng.choice(f[0])), mk(rng.choice(g[0]), rng.choice(f[0]))]
    p = Person(key, "person", "persian", variants, native=f"{g[1]} {f[1]}")
    p.female = g[0][0] in {"Fatemeh", "Zahra", "Maryam"}
    p.weak_alias = f"{variants[0].given.split()[0][0]}. {variants[0].family}"
    return p


def russian_person(rng: random.Random, key: int) -> Person:
    female = rng.random() < 0.3
    g = rng.choice(RU_GIVEN_F if female else RU_GIVEN_M)
    s = rng.choice(RU_SURNAME)
    pat = rng.choice(RU_PATRONYMIC)
    sl, sc = rng.choice(s[0]), s[1]
    pl, pc = rng.choice(pat[0]), pat[1]
    if female:
        if sl.endswith(("ov", "ev")):
            sl += "a"
        if sc.endswith(("ов", "ев")):
            sc += "а"
        if pl.endswith("ich"):
            pl = pl[:-3] + "na"
        if pc.endswith("ич"):
            pc = pc[:-2] + "на"
    gl = rng.choice(g[0])
    variants = [mk(f"{gl} {pl}", sl), mk(rng.choice(g[0]), sl), mk(f"{gl} {pl}", sl)]
    native = f"{g[1]} {pc} {sc}"
    p = Person(key, "person", "russian", variants, native=native, female=female)
    p.weak_alias = f"{gl[0]}. {sl}"
    return p


def chinese_person(rng: random.Random, key: int) -> Person:
    s, g = rng.choice(ZH_SURNAME), rng.choice(ZH_GIVEN)
    sl, gl = s[0][0], rng.choice(g[0])
    variants = [mk(gl, sl), V(sl, gl, f"{gl} {sl}"), V(gl, sl.upper(), f"{sl.upper()} {gl}")]
    return Person(key, "person", "chinese", variants, native=s[1] + g[1])


def spanish_person(rng: random.Random, key: int) -> Person:
    g1 = rng.choice(ES_GIVEN)
    g2 = rng.choice(ES_GIVEN) if rng.random() < 0.4 else None
    s1, s2 = rng.sample(ES_SURNAME, 2)
    given = f"{g1} {g2}" if g2 else g1
    variants = [mk(given, f"{s1} {s2}"), mk(strip_marks(given), f"{strip_marks(s1)} {strip_marks(s2)}"),
                mk(g1, s1)]
    p = Person(key, "person", "spanish", variants, female=g1 in {"María", "Ana", "Carmen", "Lucía"})
    p.weak_alias = f"{g1[0]}. {s1}"
    return p


def portuguese_person(rng: random.Random, key: int) -> Person:
    g1 = rng.choice(PT_GIVEN)
    s1, s2 = rng.sample(PT_SURNAME, 2)
    part = rng.choice(PT_PARTICLE)
    given = g1 if rng.random() < 0.6 else f"{g1} {rng.choice(PT_GIVEN)}"
    variants = [mk(given, f"{part} {s1} {s2}"), mk(strip_marks(given), f"{strip_marks(s1)} {strip_marks(s2)}"),
                mk(g1, s2)]
    return Person(key, "person", "portuguese", variants)


def turkish_person(rng: random.Random, key: int) -> Person:
    g, s = rng.choice(TR_GIVEN), rng.choice(TR_SURNAME)
    variants = [mk(g, s), mk(strip_marks(g), strip_marks(s))]
    p = Person(key, "person", "turkish", variants)
    p.weak_alias = f"{g[0]}. {s}"
    return p


def org_person(rng: random.Random, key: int, culture: str) -> Person:
    if culture == "arabic":
        a, b = rng.choice(ORG_AR_A), rng.choice(ORG_AR_B)
        legal = rng.choice(["LLC", "FZE", "Co. Ltd.", "FZCO", "Company Limited"])
        full = f"{a} {b} {legal}"
        short = f"{a.replace('Al ', 'Al-')} {b}"
        native = None
    elif culture == "russian":
        a, b = rng.choice(ORG_RU_A), rng.choice(ORG_RU_B)
        full, short = f"{a[0]}{b[0].lower()} OOO", f"{a[0]} {b[0]} JSC"
        native = f"ООО {a[1]}{b[1].lower()}"
    elif culture == "chinese":
        a, b = rng.choice(ORG_ZH_A), rng.choice(ORG_ZH_B)
        full, short = f"{a} {b} Co., Ltd", f"{a} {b} Co Ltd"
        native = None
    elif culture == "turkish":
        a, b = rng.choice(ORG_TR_A), rng.choice(ORG_TR_B)
        full = f"{a} {b} Anonim Şirketi"
        short = f"{strip_marks(a)} {strip_marks(b)} A.S."
        native = None
    else:
        a = rng.choice(ORG_LATIN_A)
        full = f"{a} {rng.choice(ORG_LATIN_LEGAL)}"
        short = strip_marks(full)
        native = None
    variants = [V("", full, full), V("", short, short)]
    p = Person(key, "organization", culture, variants, native=native)
    p.particle = culture == "arabic" and "Al" in full
    return p


def vessel_person(rng: random.Random, key: int) -> Person:
    name = f"{rng.choice(VESSEL_WORDS)} {rng.choice(VESSEL_WORDS)}".upper()
    p = Person(key, "vessel", "arabic", [V("", name, name), V("", name.title(), name.title())])
    p.imo = str(rng.randint(7000000, 9999999))
    return p


def aircraft_person(rng: random.Random, key: int) -> Person:
    tail = f"{rng.choice(['EP', 'RA', 'YK', 'UP', 'EX'])}-{rng.randint(10000, 99999)}"
    p = Person(key, "aircraft", "russian", [V("", tail, tail)])
    return p


def make_dob(rng: random.Random) -> tuple:
    year = rng.randint(1948, 1996)
    roll = rng.random()
    if roll < 0.60:
        return ("full", year, rng.randint(1, 12), rng.randint(1, 28))
    if roll < 0.80:
        return ("year", year)
    if roll < 0.92:
        return ("circa", year)
    return ("range", year, year + rng.randint(1, 3))


# --------------------------------------------------------------------------------------
# universe
# --------------------------------------------------------------------------------------

PERSON_COUNTS = [
    ("arabic", arabic_person, 360), ("persian", persian_person, 150), ("russian", russian_person, 300),
    ("chinese", chinese_person, 200), ("spanish", spanish_person, 170),
    ("portuguese", portuguese_person, 130), ("turkish", turkish_person, 170),
]
ORG_COUNTS = [("arabic", 120), ("russian", 120), ("chinese", 80), ("spanish", 60), ("turkish", 50),
              ("portuguese", 40)]
SOURCE_WEIGHTS = {"ofac": 27, "un": 24, "eu": 25, "uk": 24}
ELIGIBLE = {
    "person": ["ofac", "un", "eu", "uk"], "organization": ["ofac", "un", "eu", "uk"],
    "vessel": ["ofac", "uk"], "aircraft": ["ofac"],
}


def weighted_source(rng: random.Random, options: list[str]) -> str:
    weights = [SOURCE_WEIGHTS[o] for o in options]
    return rng.choices(options, weights=weights, k=1)[0]


def planted_haddad(key: int) -> Person:
    """The name used in the README quick start: listed twice, spelled two ways."""
    p = Person(
        key, "person", "arabic",
        [mk("Abd al Rahman", "HADDAD"), mk("Abdulrahman", "Haddad")],
        native="عبد الرحمن الحداد", dob=("year", 1971), nat=["SY"], passport="TESTN0847193",
        particle=True,
    )
    p.sources = ["ofac", "eu"]
    p.dob_by_source = {"ofac": ("year", 1971), "eu": ("full", 1971, 3, 12)}
    return p


def build_universe(rng: random.Random) -> list[Person]:
    people: list[Person] = []
    key = 1000
    for culture, builder, count in PERSON_COUNTS:
        for _ in range(count):
            key += 1
            people.append(builder(rng, key))
    for culture, count in ORG_COUNTS:
        for _ in range(count):
            key += 1
            people.append(org_person(rng, key, culture))
    for _ in range(30):
        key += 1
        people.append(vessel_person(rng, key))
    for _ in range(20):
        key += 1
        people.append(aircraft_person(rng, key))

    for p in people:
        if p.kind == "person":
            p.dob = make_dob(rng) if rng.random() < 0.72 else None
            p.passport = f"TEST{rng.choice('ABCDEFGHKLMNPRSTUXYZ')}{rng.randint(1000000, 9999999)}" \
                if rng.random() < 0.5 else None
        pool = CULTURE_NAT[p.culture]
        k = 1 if rng.random() < 0.85 else min(2, len(pool))
        p.nat = rng.sample(pool, k=k) if p.kind in ("person", "organization") else []
        if p.kind == "person" and p.weak_alias is None and rng.random() < 0.2:
            p.weak_alias = f"{p.variants[0].given.split()[0][0]}. {p.variants[0].family.split()[-1]}"
        p.sources = [weighted_source(rng, ELIGIBLE[p.kind])]

    shared = [p for p in people if p.kind in ("person", "organization")]
    for p in rng.sample(shared, 80):
        other = [s for s in ELIGIBLE[p.kind] if s not in p.sources]
        p.sources.append(weighted_source(rng, other))

    people.append(planted_haddad(key + 1))
    return people


def render(rng: random.Random, p: Person, source: str, idx: int) -> Rec:
    """Pick the spelling this source uses and the aliases it carries."""
    n = len(p.variants)
    if len(p.sources) > 1:
        v = p.variants[p.sources.index(source) % n]  # the two sources spell it differently
    else:
        v = p.variants[0] if rng.random() < 0.7 else p.variants[rng.randrange(n)]
    aliases: list[tuple[str, bool]] = []
    others = [x for x in p.variants if x.full != v.full]
    if others and rng.random() < 0.6:
        aliases.append((rng.choice(others).full, False))
    if p.weak_alias and rng.random() < 0.7:
        aliases.append((p.weak_alias, True))
    if p.kind == "person" and len(aliases) == 1 and rng.random() < 0.5:
        aliases.append((p.variants[-1].full if p.variants[-1].full != v.full else v.full.upper(), False))
    seen = {v.full}
    aliases = [(a, w) for a, w in aliases if not (a in seen or seen.add(a))]
    return Rec(
        uid=str(idx), kind=p.kind, v=v, native=p.native, aliases=aliases,
        dob=p.dob_by_source.get(source, p.dob), nat=p.nat,
        passport=p.passport, culture=p.culture, person=p,
        listed_on=PUBLISH - timedelta(days=rng.randint(30, 5000)),
    )


# --------------------------------------------------------------------------------------
# writers
# --------------------------------------------------------------------------------------

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def x(text: str | None) -> str:
    return escape(text or "", {'"': "&quot;"})


def ofac_dob(dob: tuple) -> str:
    if dob[0] == "full":
        return f"{dob[3]:02d} {MONTHS[dob[2] - 1]} {dob[1]}"
    if dob[0] == "year":
        return str(dob[1])
    if dob[0] == "circa":
        return f"circa {dob[1]}"
    return f"{dob[1]} to {dob[2]}"


def write_ofac(path: Path, recs: list[Rec]) -> None:
    out = ['<?xml version="1.0" standalone="yes"?>',
           '<sdnList xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://tempuri.org/sdnList.xsd">',
           "  <publshInformation>",
           f"    <Publish_Date>{PUBLISH.strftime('%m/%d/%Y')}</Publish_Date>",
           f"    <Record_Count>{len(recs)}</Record_Count>",
           "  </publshInformation>"]
    sdn_type = {"person": "Individual", "organization": "Entity", "vessel": "Vessel", "aircraft": "Aircraft"}
    for r in recs:
        out.append("  <sdnEntry>")
        out.append(f"    <uid>{r.uid}</uid>")
        if r.kind == "person":
            out.append(f"    <firstName>{x(r.v.given)}</firstName>")
            out.append(f"    <lastName>{x(r.v.family.upper() if r.culture != 'chinese' else r.v.family)}</lastName>")
        else:
            out.append(f"    <lastName>{x(r.v.family)}</lastName>")
        out.append(f"    <sdnType>{sdn_type[r.kind]}</sdnType>")
        progs = OFAC_PROGRAMS[r.culture]
        out.append("    <programList>")
        for pr in progs[: 1 + (int(r.uid) % 2)]:
            out.append(f"      <program>{pr}</program>")
        out.append("    </programList>")
        if r.passport:
            out.append("    <idList>")
            out.append(f"      <id><uid>{int(r.uid) + 500000}</uid><idType>Passport</idType>"
                       f"<idNumber>{r.passport}</idNumber><idCountry>{NAT_LONG.get(r.nat[0], '') if r.nat else ''}"
                       f"</idCountry></id>")
            out.append("    </idList>")
        names = r.aliases + ([(r.native, False)] if r.native else [])
        if names:
            out.append("    <akaList>")
            for i, (nm, weak) in enumerate(names):
                parts = nm.rsplit(" ", 1)
                first, last = (parts[0], parts[1]) if r.kind == "person" and len(parts) == 2 else ("", nm)
                out.append(f"      <aka><uid>{int(r.uid) + 700000 + i}</uid><type>a.k.a.</type>"
                           f"<category>{'weak' if weak else 'strong'}</category>"
                           + (f"<firstName>{x(first)}</firstName>" if first else "")
                           + f"<lastName>{x(last)}</lastName></aka>")
            out.append("    </akaList>")
        if r.nat:
            out.append("    <nationalityList>")
            for n in r.nat:
                out.append(f"      <nationality><uid>{int(r.uid) + 300000}</uid><country>{NAT_LONG[n]}</country>"
                           f"<mainEntry>true</mainEntry></nationality>")
            out.append("    </nationalityList>")
        if r.dob:
            out.append("    <dateOfBirthList>")
            out.append(f"      <dateOfBirthItem><uid>{int(r.uid) + 400000}</uid>"
                       f"<dateOfBirth>{ofac_dob(r.dob)}</dateOfBirth><mainEntry>true</mainEntry></dateOfBirthItem>")
            out.append("    </dateOfBirthList>")
        if r.kind == "vessel":
            out.append(f"    <vesselInfo><callSign>{'C' + str(int(r.uid) % 9000 + 1000)}</callSign>"
                       f"<vesselType>Cargo</vesselType><vesselFlag>Panama</vesselFlag>"
                       f"<tonnage>{int(r.uid) % 9000 + 2000}</tonnage></vesselInfo>")
        out.append("    <remarks>Fictional test record.</remarks>")
        out.append("  </sdnEntry>")
    out.append("</sdnList>")
    path.write_text("\r\n".join(out) + "\r\n", encoding="utf-8", newline="")


def un_name_parts(r: Rec) -> list[str]:
    toks = r.v.full.split()
    if len(toks) <= 4:
        return toks
    return toks[:3] + [" ".join(toks[3:])]


def un_individual(r: Rec, un_list: str, ref: str, extra_alias: list[tuple[str, bool]] | None = None) -> list[str]:
    out = ["    <INDIVIDUAL>", f"      <DATAID>{6900000 + int(r.uid)}</DATAID>", "      <VERSIONNUM>1</VERSIONNUM>"]
    for tag, part in zip(["FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME"], un_name_parts(r), strict=False):
        out.append(f"      <{tag}>{x(part)}</{tag}>")
    out.append(f"      <UN_LIST_TYPE>{un_list}</UN_LIST_TYPE>")
    out.append(f"      <REFERENCE_NUMBER>{ref}</REFERENCE_NUMBER>")
    out.append(f"      <LISTED_ON>{r.listed_on.isoformat()}</LISTED_ON>")
    if r.native:
        out.append(f"      <NAME_ORIGINAL_SCRIPT>{x(r.native)}</NAME_ORIGINAL_SCRIPT>")
    out.append("      <COMMENTS1>Fictional test record.</COMMENTS1>")
    out.append("      <DESIGNATION><VALUE>Logistics coordinator</VALUE></DESIGNATION>")
    for n in r.nat:
        out.append(f"      <NATIONALITY><VALUE>{NAT_UN[n]}</VALUE></NATIONALITY>")
    out.append("      <LIST_TYPE><VALUE>UN List</VALUE></LIST_TYPE>")
    out.append(f"      <LAST_DAY_UPDATED><VALUE>{r.listed_on.isoformat()}</VALUE></LAST_DAY_UPDATED>")
    for nm, weak in (r.aliases + (extra_alias or [])):
        out.append(f"      <INDIVIDUAL_ALIAS><QUALITY>{'Low' if weak else 'Good'}</QUALITY>"
                   f"<ALIAS_NAME>{x(nm)}</ALIAS_NAME></INDIVIDUAL_ALIAS>")
    if r.dob:
        d = r.dob
        if d[0] == "full":
            body = f"<TYPE_OF_DATE>EXACT</TYPE_OF_DATE><DATE>{d[1]:04d}-{d[2]:02d}-{d[3]:02d}</DATE>"
        elif d[0] == "year":
            body = f"<TYPE_OF_DATE>EXACT</TYPE_OF_DATE><YEAR>{d[1]}</YEAR>"
        elif d[0] == "circa":
            body = f"<TYPE_OF_DATE>APPROXIMATE</TYPE_OF_DATE><YEAR>{d[1]}</YEAR>"
        else:
            body = f"<TYPE_OF_DATE>BETWEEN</TYPE_OF_DATE><FROM_YEAR>{d[1]}</FROM_YEAR><TO_YEAR>{d[2]}</TO_YEAR>"
        out.append(f"      <INDIVIDUAL_DATE_OF_BIRTH>{body}</INDIVIDUAL_DATE_OF_BIRTH>")
    if r.passport:
        out.append(f"      <INDIVIDUAL_DOCUMENT><TYPE_OF_DOCUMENT>Passport</TYPE_OF_DOCUMENT>"
                   f"<NUMBER>{r.passport}</NUMBER>"
                   f"<ISSUING_COUNTRY>{NAT_UN[r.nat[0]] if r.nat else ''}</ISSUING_COUNTRY></INDIVIDUAL_DOCUMENT>")
    out.append("      <SORT_KEY/>")
    out.append("    </INDIVIDUAL>")
    return out


def un_entity(r: Rec, un_list: str, ref: str) -> list[str]:
    out = ["    <ENTITY>", f"      <DATAID>{6900000 + int(r.uid)}</DATAID>", "      <VERSIONNUM>1</VERSIONNUM>",
           f"      <FIRST_NAME>{x(r.v.full)}</FIRST_NAME>", f"      <UN_LIST_TYPE>{un_list}</UN_LIST_TYPE>",
           f"      <REFERENCE_NUMBER>{ref}</REFERENCE_NUMBER>", f"      <LISTED_ON>{r.listed_on.isoformat()}</LISTED_ON>"]
    if r.native:
        out.append(f"      <NAME_ORIGINAL_SCRIPT>{x(r.native)}</NAME_ORIGINAL_SCRIPT>")
    out.append("      <COMMENTS1>Fictional test record.</COMMENTS1>")
    out.append("      <LIST_TYPE><VALUE>UN List</VALUE></LIST_TYPE>")
    for nm, weak in r.aliases:
        out.append(f"      <ENTITY_ALIAS><QUALITY>{'Low' if weak else 'Good'}</QUALITY>"
                   f"<ALIAS_NAME>{x(nm)}</ALIAS_NAME></ENTITY_ALIAS>")
    out.append("      <SORT_KEY/>")
    out.append("    </ENTITY>")
    return out


def write_un(path: Path, recs: list[Rec], when: date, overrides: dict[str, Rec] | None = None,
             refs: dict[str, str] | None = None) -> dict[str, str]:
    """Write the UN file. Returns {uid: reference number} so the old snapshot can reuse them."""
    counters: dict[str, int] = {}
    ref_of: dict[str, str] = dict(refs or {})
    inds, ents = [], []
    for r in recs:
        lst = UN_LISTS[r.culture]
        pre = UN_PREFIX[lst] + ("i" if r.kind == "person" else "e")
        if r.uid not in ref_of:
            counters[pre] = counters.get(pre, 0) + 1
            ref_of[r.uid] = f"{pre}.{counters[pre]:03d}"
        use = (overrides or {}).get(r.uid, r)
        (inds if r.kind == "person" else ents).append((use, lst, ref_of[r.uid]))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<CONSOLIDATED_LIST xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="https://scsanctions.un.org/resources/xml/schema/consolidatedLegacyByPRN.xsd" '
           f'dateGenerated="{when.isoformat()}T04:21:09.512Z">', "  <INDIVIDUALS>"]
    for r, lst, ref in inds:
        out.extend(un_individual(r, lst, ref))
    out.append("  </INDIVIDUALS>")
    out.append("  <ENTITIES>")
    for r, lst, ref in ents:
        out.extend(un_entity(r, lst, ref))
    out.append("  </ENTITIES>")
    out.append("</CONSOLIDATED_LIST>")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return ref_of


def write_eu(path: Path, recs: list[Rec], rng: random.Random) -> None:
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           f'<export xmlns="http://eu.europa.ec/fpi/fsd/export" generationDate="{PUBLISH.isoformat()}T12:00:00.000+01:00" '
           'globalFileId="283974">']
    for i, r in enumerate(recs):
        lid = 20000 + int(r.uid)
        out.append(f'  <sanctionEntity designationDetails="" unitedNationId="" euReferenceNumber="EU.{i + 1}.{rng.randint(10, 99)}" '
                   f'logicalId="{lid}">')
        out.append(f'    <regulation type="regulation" regulationType="amendment" organisationType="commission" '
                   f'publicationDate="{r.listed_on.isoformat()}" entryIntoForceDate="{r.listed_on.isoformat()}" '
                   f'numberTitle="{r.listed_on.year}/{rng.randint(100, 999)} (OJ L)" programme="{EU_PROGRAMMES[r.culture]}" '
                   f'logicalId="{lid + 1}"/>')
        is_p = r.kind == "person"
        out.append(f'    <subjectType code="{"P" if is_p else "E"}" classificationCode="{"person" if is_p else "enterprise"}"/>')
        names = [(r.v.full, r.v.given, r.v.family, True)] + [(a, "", "", not w) for a, w in r.aliases]
        if r.native:
            names.append((r.native, "", "", True))
        for j, (whole, first, last, strong) in enumerate(names):
            gender = ' gender="' + ("F" if r.person.female else "M") + '"' if is_p else ""
            out.append(f'    <nameAlias firstName="{x(first)}" middleName="" lastName="{x(last)}" wholeName="{x(whole)}" '
                       f'function=""{gender} title="" nameLanguage="" strong="{"true" if strong else "false"}" '
                       f'regulationLanguage="en" logicalId="{lid + 10 + j}"/>')
        for n in r.nat:
            out.append(f'    <citizenship region="" countryIso2Code="{n}" countryDescription="{NAT_LONG[n].upper()}" '
                       f'regulationLanguage="en" logicalId="{lid + 40}"/>')
        if r.dob:
            d = r.dob
            circa = "true" if d[0] in ("circa", "range") else "false"
            full = ""
            if d[0] == "full":
                full = f' birthdate="{d[1]:04d}-{d[2]:02d}-{d[3]:02d}" dayOfMonth="{d[3]}" monthOfYear="{d[2]}"'
            out.append(f'    <birthdate circa="{circa}" calendarType="GREGORIAN" city=""{full} year="{d[1]}" '
                       f'region="" place="" countryIso2Code="{r.nat[0] if r.nat else ""}" regulationLanguage="en" '
                       f'logicalId="{lid + 50}"/>')
        if r.passport:
            out.append(f'    <identification diplomatic="false" knownExpired="false" knownFalse="false" '
                       f'revokedByIssuer="false" number="{r.passport}" countryIso2Code="{r.nat[0] if r.nat else ""}" '
                       f'identificationTypeCode="passport" regulationLanguage="en" logicalId="{lid + 60}"/>')
        out.append("    <remark>Fictional test record.</remark>")
        out.append("  </sanctionEntity>")
    out.append("</export>")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


UK_HEADER = [
    "Name 6", "Name 1", "Name 2", "Name 3", "Name 4", "Name 5", "Title", "DOB", "Town of Birth",
    "Country of Birth", "Nationality", "Passport Number", "Passport Details", "NI Number", "NI Details",
    "Position", "Address 1", "Address 2", "Address 3", "Address 4", "Address 5", "Address 6",
    "Post/Zip Code", "Country", "Other Information", "Group Type", "Alias Type", "Regime", "Listed On",
    "Last Updated", "Group ID",
]


def write_uk(path: Path, recs: list[Rec]) -> None:
    rows: list[list[str]] = []
    for r in recs:
        gid = str(1000 + int(r.uid))
        gtype = {"person": "Individual", "organization": "Entity", "vessel": "Ship"}[r.kind]
        names = [(r.v.full, r.v.given, r.v.family, "Primary name")]
        names += [(a, "", a, "FKA" if w else "AKA") for a, w in r.aliases]
        for full, given, family, atype in names:
            row = [""] * len(UK_HEADER)
            if gtype == "Individual":
                if given:
                    gtoks = given.split(" ")
                    for i in range(min(len(gtoks), 5)):
                        row[1 + i] = gtoks[i] if i < 4 or len(gtoks) == 5 else " ".join(gtoks[4:])
                    row[0] = family
                else:
                    toks = full.split(" ")
                    row[0] = toks[-1]
                    for i, t in enumerate(toks[:-1][:5]):
                        row[1 + i] = t
            else:
                row[0] = full
            if r.dob:
                d = r.dob
                row[7] = f"{d[3]:02d}/{d[2]:02d}/{d[1]}" if d[0] == "full" else f"00/00/{d[1]}"
            if r.nat:
                row[10] = NAT_LONG[r.nat[0]]
            if r.passport:
                row[11] = r.passport
            row[24] = "Fictional test record."
            row[25], row[26] = gtype, atype
            row[27] = UK_REGIMES[r.culture]
            row[28] = r.listed_on.strftime("%d/%m/%Y")
            row[29] = PUBLISH.strftime("%d/%m/%Y")
            row[30] = gid
            rows.append(row)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        w.writerow(["Last Updated", PUBLISH.strftime("%d/%m/%Y")])
        w.writerow(UK_HEADER)
        w.writerows(rows)


# --------------------------------------------------------------------------------------
# customers
# --------------------------------------------------------------------------------------

def t_nodiac(name: str, rng: random.Random) -> str:
    return strip_marks(name)


def t_swap(name: str, rng: random.Random) -> str:
    toks = name.split()
    return " ".join([toks[-1]] + toks[:-1]) if len(toks) > 1 else name


def t_typo(name: str, rng: random.Random) -> str:
    toks = name.split()
    cand = [i for i, t in enumerate(toks) if len(t) > 4]
    if not cand:
        return name
    i = rng.choice(cand)
    t = toks[i]
    j = rng.randrange(1, len(t) - 2)
    toks[i] = t[:j] + t[j + 1] + t[j] + t[j + 2:]
    return " ".join(toks)


def t_upper(name: str, rng: random.Random) -> str:
    return name.upper()


def t_drop_middle(name: str, rng: random.Random) -> str:
    toks = name.split()
    if len(toks) < 3:
        return name
    del toks[rng.randrange(1, len(toks) - 1)]
    return " ".join(toks)


def t_glue_particle(name: str, rng: random.Random) -> str:
    return name.replace("al-", "al").replace("Abd al ", "Abdal").replace(" al ", " al")


SAFE_TRANSFORMS = [t_nodiac, t_swap, t_typo, t_upper, t_drop_middle]
ALL_TRANSFORMS = SAFE_TRANSFORMS + [t_glue_particle]


def clean_customer(rng: random.Random) -> tuple[str, str]:
    if rng.random() < 0.18:
        name = f"{rng.choice(CLEAN_COMPANY_A)} {rng.choice(CLEAN_COMPANY_B)} {rng.choice(['Ltda', 'S.A.', 'LLC', 'ME'])}"
        return name, rng.choice(CLEAN_COUNTRIES)
    given = rng.choice(CLEAN_GIVEN)
    fam = " ".join(rng.sample(CLEAN_SURNAME, 2 if rng.random() < 0.55 else 1))
    return f"{given} {fam}", rng.choice(CLEAN_COUNTRIES)


def random_date(rng: random.Random) -> str:
    return date(rng.randint(1950, 2001), rng.randint(1, 12), rng.randint(1, 28)).isoformat()


def planted_customer(rng: random.Random, p: Person, transforms: list, dob_mode: str) -> tuple[str, str, str]:
    base = p.variants[rng.randrange(len(p.variants))].full
    name = rng.choice(transforms)(base, rng) if rng.random() < 0.85 else base
    dob = ""
    if p.dob and p.dob[0] == "full":
        if dob_mode == "exact":
            dob = f"{p.dob[1]:04d}-{p.dob[2]:02d}-{p.dob[3]:02d}"
        elif dob_mode == "wrong":
            dob = f"{p.dob[1] + rng.choice([-9, -7, 6, 8]):04d}-{p.dob[2]:02d}-{p.dob[3]:02d}"
    elif p.dob and p.dob[0] in ("year", "circa") and dob_mode == "year":
        dob = str(p.dob[1])
    country = p.nat[0] if p.nat and rng.random() < 0.6 else ""
    return name, dob, country


def write_customers(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["customer_id", "name", "dob", "country"])
        w.writerows(rows)


def make_customers(rng: random.Random, people: list[Person]) -> None:
    solo = [p for p in people if len(p.sources) == 1 and p.kind == "person" and not p.particle]
    full_dob = [p for p in solo if p.dob and p.dob[0] == "full" and p.culture not in ("chinese", "persian")]
    year_dob = [p for p in solo if p.dob and p.dob[0] == "year" and p.culture in ("spanish", "portuguese", "turkish")]

    # --- small file: 50 rows -------------------------------------------------------------
    plants: list[tuple[str, str, str]] = []
    chosen = rng.sample(full_dob, 10)
    for i, p in enumerate(chosen):
        mode = "wrong" if i in (3, 7) else ("exact" if i % 2 == 0 else "none")
        plants.append(planted_customer(rng, p, SAFE_TRANSFORMS, mode))
    # one more person, no DOB given, name only
    plants.append(planted_customer(rng, rng.choice(solo), SAFE_TRANSFORMS, "none"))
    # the "january" customer: list says year only, the customer gives a full date near January
    victim = year_dob[0]
    vname = t_typo(t_drop_middle(victim.variants[0].full, rng), rng)
    plants.append((vname, f"{victim.dob[1]}-01-19", ""))
    # near misses: same family name, different given name
    for p in rng.sample(solo, 2):
        v = p.variants[0]
        plants.append((f"{v.given.split()[0]} {rng.choice(CLEAN_SURNAME)}", "", ""))

    small: list[tuple[str, str, str, str]] = []
    rows = list(plants)
    while len(rows) < 50:
        name, country = clean_customer(rng)
        rows.append((name, "", country))
    rng.shuffle(rows)
    for i, (name, dob, country) in enumerate(rows, 1):
        small.append((f"C-{i:04d}", name, dob, country))
    write_customers(EXAMPLES / "customers_small.csv", small)

    # --- 10k file ------------------------------------------------------------------------
    pool = [p for p in people if p.kind in ("person", "organization")]
    planted_at = set(rng.sample(range(10000), 200))
    big: list[tuple[str, str, str, str]] = []
    for i in range(10000):
        if i in planted_at:
            p = rng.choice(pool)
            mode = rng.choice(["exact", "year", "none", "wrong"])
            name, dob, country = planted_customer(rng, p, ALL_TRANSFORMS, mode)
        else:
            name, country = clean_customer(rng)
            dob = random_date(rng) if rng.random() < 0.6 else ""
        big.append((f"K-{i + 1:05d}", name, dob, country))
    write_customers(EXAMPLES / "customers_10k.csv", big)


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------

def main() -> None:
    rng = random.Random(SEED)
    people = build_universe(rng)
    by_source: dict[str, list[Rec]] = {s: [] for s in SOURCE_WEIGHTS}
    counter = 0
    for p in people:
        for s in p.sources:
            counter += 1
            by_source[s].append(render(rng, p, s, 10000 + counter * 3))

    LISTS.mkdir(parents=True, exist_ok=True)
    LISTS_OLD.mkdir(parents=True, exist_ok=True)
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    write_ofac(LISTS / "ofac_sdn.xml", by_source["ofac"])
    refs = write_un(LISTS / "un_consolidated.xml", by_source["un"], PUBLISH)
    write_eu(LISTS / "eu_fsf.xml", by_source["eu"], rng)
    write_uk(LISTS / "uk_consolidated.csv", by_source["uk"])

    # older UN snapshot: 5 entries not there yet, 4 since removed, 5 changed afterwards
    un = by_source["un"]
    persons = [r for r in un if r.kind == "person"]
    added = {r.uid for r in persons[-5:]}
    changed: dict[str, Rec] = {}
    for r in persons[10:15]:
        old = Rec(**{**r.__dict__})
        if r.dob and r.dob[0] == "full":
            old.dob = ("full", r.dob[1] - 1, r.dob[2], r.dob[3])
        elif r.aliases:
            old.aliases = r.aliases[:-1]
        else:
            old.nat = []
        changed[r.uid] = old
    removed = []
    for k in range(4):
        gone = render(rng, build_universe_one(rng, 9000 + k), "un", 90000 + k)
        removed.append(gone)
    old_recs = [r for r in un if r.uid not in added] + removed
    write_un(LISTS_OLD / "un_consolidated.xml", old_recs, OLD_PUBLISH, overrides=changed,
             refs={**refs, **{r.uid: f"QDi.{900 + ri}" for ri, r in enumerate(removed)}})

    make_customers(rng, people)
    for s, recs in by_source.items():
        print(f"{s}: {len(recs)} entries")


def build_universe_one(rng: random.Random, key: int) -> Person:
    p = arabic_person(rng, key)
    p.dob = make_dob(rng)
    p.nat = ["IQ"]
    p.sources = ["un"]
    return p


if __name__ == "__main__":
    main()
