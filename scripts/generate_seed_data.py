#!/usr/bin/env python3
"""
Generate realistic, messy healthcare data for 1000+ patients.
Simulates real-world data quality issues found in healthcare systems.
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional
import string

# Configuration
NUM_PATIENTS = 1000
NUM_PRACTITIONERS = 50
NUM_ENCOUNTERS_PER_PATIENT = (0, 8)  # Range
CONDITION_PROBABILITY = 0.7
ALLERGY_PROBABILITY = 0.3
LAB_ORDER_PROBABILITY = 0.6
IMAGING_PROBABILITY = 0.3
MEDICATION_PROBABILITY = 0.5

# Realistic first names (with some duplicates, misspellings)
FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark",
    "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
    "George", "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan",
    "Jacob", "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin",
    "Scott", "Brandon", "Benjamin", "Samuel", "Raymond", "Gregory", "Frank",
    "Jose", "Juan", "Carlos", "Miguel", "Luis", "Mohammed", "Ahmed", "Wei", "Raj",
    # Misspellings that happen in real data
    "Micheal", "Jonh", "Willaim", "Jeffery", "Mathew", "Jonathon", "Steven", "Stephen",
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol",
    "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura",
    "Cynthia", "Kathleen", "Amy", "Angela", "Shirley", "Anna", "Brenda", "Pamela",
    "Emma", "Nicole", "Helen", "Samantha", "Katherine", "Christine", "Debra",
    "Maria", "Rosa", "Carmen", "Fatima", "Priya", "Wei", "Yuki", "Aisha",
    # Misspellings
    "Jenifer", "Elizebeth", "Barbra", "Michell", "Rebbecca", "Cathrine", "Sara",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson", "Watson",
    "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster",
    "Chen", "Wang", "Li", "Zhang", "Liu", "Singh", "Kumar", "Das", "Khan", "Ali",
    # With suffixes sometimes
    "Smith Jr", "Williams III", "Johnson Sr",
    # Hyphenated
    "Garcia-Lopez", "Smith-Jones", "Lee-Wong", "Martinez-Rodriguez",
]

STREETS = [
    "Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine St", "Elm St", "Washington Ave",
    "Park Rd", "Lake Dr", "Hill St", "Forest Ave", "River Rd", "Church St", "School St",
    "North St", "South Ave", "East Blvd", "West Dr", "Center St", "Union Ave",
    "Spring St", "High St", "Mill Rd", "Prospect Ave", "Academy St", "Court St",
    "Highland Ave", "Grove St", "Pearl St", "Pleasant St", "Bridge St", "Water St",
    # Apartments, units
    "Main St Apt 4", "Oak Ave #201", "Maple Dr Unit B", "Pine St Apt. 12",
    "Elm Street, Apartment 3B", "123 Washington Ave, Suite 100",
]

CITIES = [
    ("Boston", "MA", ["02101", "02102", "02108", "02109", "02110", "02111", "02113", "02114", "02115", "02116"]),
    ("Cambridge", "MA", ["02138", "02139", "02140", "02141", "02142"]),
    ("Somerville", "MA", ["02143", "02144", "02145"]),
    ("Brookline", "MA", ["02445", "02446", "02447"]),
    ("Newton", "MA", ["02458", "02459", "02460", "02461", "02462", "02464", "02465", "02466", "02467", "02468"]),
    ("Worcester", "MA", ["01601", "01602", "01603", "01604", "01605", "01606", "01607", "01608", "01609", "01610"]),
    ("Springfield", "MA", ["01101", "01102", "01103", "01104", "01105", "01107", "01108", "01109"]),
    ("Lowell", "MA", ["01850", "01851", "01852", "01853", "01854"]),
    ("Quincy", "MA", ["02169", "02170", "02171"]),
    ("Lynn", "MA", ["01901", "01902", "01903", "01904", "01905"]),
    # Some out of state
    ("Providence", "RI", ["02901", "02902", "02903", "02904", "02905", "02906", "02907", "02908", "02909"]),
    ("Hartford", "CT", ["06101", "06102", "06103", "06104", "06105", "06106"]),
    ("Manchester", "NH", ["03101", "03102", "03103", "03104", "03105"]),
]

# ICD-10 conditions with realistic prevalence
CONDITIONS = [
    # Common chronic conditions
    ("E11.9", "Type 2 diabetes mellitus without complications", 0.12),
    ("E11.65", "Type 2 diabetes mellitus with hyperglycemia", 0.05),
    ("E11.21", "Type 2 diabetes mellitus with diabetic nephropathy", 0.02),
    ("I10", "Essential (primary) hypertension", 0.25),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery without angina pectoris", 0.08),
    ("I25.5", "Ischemic cardiomyopathy", 0.03),
    ("I48.91", "Unspecified atrial fibrillation", 0.04),
    ("I50.9", "Heart failure, unspecified", 0.05),
    ("E78.5", "Hyperlipidemia, unspecified", 0.18),
    ("E78.00", "Pure hypercholesterolemia, unspecified", 0.08),
    ("J44.9", "Chronic obstructive pulmonary disease, unspecified", 0.06),
    ("J44.1", "Chronic obstructive pulmonary disease with acute exacerbation", 0.02),
    ("J45.909", "Unspecified asthma, uncomplicated", 0.08),
    ("K21.0", "Gastro-esophageal reflux disease with esophagitis", 0.10),
    ("K21.9", "Gastro-esophageal reflux disease without esophagitis", 0.05),
    ("M54.5", "Low back pain", 0.15),
    ("M17.11", "Primary osteoarthritis, right knee", 0.06),
    ("M17.12", "Primary osteoarthritis, left knee", 0.05),
    ("G47.33", "Obstructive sleep apnea", 0.07),
    ("F32.9", "Major depressive disorder, single episode, unspecified", 0.08),
    ("F41.1", "Generalized anxiety disorder", 0.07),
    ("F41.9", "Anxiety disorder, unspecified", 0.04),
    ("N18.3", "Chronic kidney disease, stage 3 (moderate)", 0.04),
    ("N18.4", "Chronic kidney disease, stage 4 (severe)", 0.01),
    ("E03.9", "Hypothyroidism, unspecified", 0.06),
    ("E05.90", "Thyrotoxicosis, unspecified without thyrotoxic crisis", 0.02),
    ("G43.909", "Migraine, unspecified, not intractable, without status migrainosus", 0.05),
    ("R51.9", "Headache, unspecified", 0.03),  # Sometimes coded as symptom
    ("B18.2", "Chronic viral hepatitis C", 0.02),
    ("K70.30", "Alcoholic cirrhosis of liver without ascites", 0.01),
    # Acute conditions
    ("J06.9", "Acute upper respiratory infection, unspecified", 0.15),
    ("J18.9", "Pneumonia, unspecified organism", 0.03),
    ("N39.0", "Urinary tract infection, site not specified", 0.08),
    ("A09", "Infectious gastroenteritis and colitis, unspecified", 0.04),
    ("S72.001A", "Fracture of unspecified part of neck of right femur, initial encounter", 0.005),
    ("I21.9", "Acute myocardial infarction, unspecified", 0.01),
    ("I63.9", "Cerebral infarction, unspecified", 0.008),
    # Sometimes free text is used instead of codes
    (None, "High blood pressure", 0.05),  # Missing ICD code
    (None, "Sugar diabetes", 0.02),
    (None, "Bad cholesterol", 0.02),
    (None, "Chest pain - cardiac workup negative", 0.01),
]

# Allergies with RxNorm codes
ALLERGIES = [
    ("7980", "Penicillin", ["allergy"], "high", 0.08),
    ("82122", "Sulfonamides", ["allergy"], "high", 0.04),
    ("723", "Amoxicillin", ["allergy"], "high", 0.05),
    ("2670", "Codeine", ["intolerance"], "low", 0.03),
    ("7052", "Morphine", ["intolerance"], "moderate", 0.02),
    ("161", "Acetaminophen", ["allergy"], "low", 0.01),
    ("5640", "Ibuprofen", ["intolerance"], "low", 0.04),
    ("203150", "Aspirin", ["allergy", "intolerance"], "moderate", 0.06),
    ("4337", "Erythromycin", ["allergy"], "moderate", 0.02),
    ("25033", "Fluoroquinolones", ["allergy"], "high", 0.02),
    ("10689", "Tramadol", ["intolerance"], "low", 0.02),
    ("36567", "Simvastatin", ["intolerance"], "low", 0.01),
    ("321988", "Lisinopril", ["intolerance"], "low", 0.02),
    # NKDA often recorded
    (None, "No Known Drug Allergies", None, None, 0.40),
    # Environmental/food (sometimes in drug allergy list erroneously)
    (None, "Latex", ["allergy"], "high", 0.02),
    (None, "Shellfish", ["allergy"], "high", 0.03),
    (None, "Peanuts", ["allergy"], "high", 0.02),
    (None, "Bee stings", ["allergy"], "high", 0.01),
    (None, "Contrast dye", ["allergy"], "high", 0.02),
]

# Medications with RxNorm
MEDICATIONS = [
    ("197361", "Lisinopril 10 MG Oral Tablet", "I10", 0.15),
    ("314076", "Lisinopril 20 MG Oral Tablet", "I10", 0.10),
    ("197381", "Atorvastatin 20 MG Oral Tablet", "E78.5", 0.12),
    ("617314", "Atorvastatin 40 MG Oral Tablet", "E78.5", 0.08),
    ("860975", "Metformin 500 MG Oral Tablet", "E11.9", 0.10),
    ("861007", "Metformin 1000 MG Oral Tablet", "E11.9", 0.06),
    ("310965", "Amlodipine 5 MG Oral Tablet", "I10", 0.10),
    ("308136", "Amlodipine 10 MG Oral Tablet", "I10", 0.06),
    ("312961", "Omeprazole 20 MG Delayed Release Oral Capsule", "K21.0", 0.12),
    ("198211", "Omeprazole 40 MG Delayed Release Oral Capsule", "K21.0", 0.05),
    ("197591", "Furosemide 40 MG Oral Tablet", "I50.9", 0.04),
    ("197732", "Hydrochlorothiazide 25 MG Oral Tablet", "I10", 0.08),
    ("313850", "Gabapentin 300 MG Oral Capsule", "M54.5", 0.05),
    ("197319", "Levothyroxine 50 MCG Oral Tablet", "E03.9", 0.06),
    ("311989", "Clopidogrel 75 MG Oral Tablet", "I25.10", 0.04),
    ("849727", "Aspirin 81 MG Delayed Release Oral Tablet", "I25.10", 0.10),
    ("904420", "Sertraline 50 MG Oral Tablet", "F32.9", 0.06),
    ("312938", "Alprazolam 0.5 MG Oral Tablet", "F41.1", 0.03),
    ("859751", "Acetaminophen 325 MG / Hydrocodone Bitartrate 5 MG Oral Tablet", "M54.5", 0.02),
    ("197696", "Prednisone 10 MG Oral Tablet", None, 0.03),
    ("309362", "Albuterol 0.083 MG/ACTUAT Inhalation Solution", "J45.909", 0.05),
    ("245314", "Amoxicillin 500 MG Oral Capsule", None, 0.04),
    ("309114", "Azithromycin 250 MG Oral Tablet", None, 0.03),
    ("562251", "Rosuvastatin 10 MG Oral Tablet", "E78.5", 0.05),
    ("484824", "Pantoprazole 40 MG Delayed Release Oral Tablet", "K21.0", 0.06),
]

# Lab tests with LOINC codes
LAB_TESTS = [
    ("24323-8", "Comprehensive metabolic panel", 0.30),
    ("24362-6", "Basic metabolic panel", 0.25),
    ("58410-2", "Complete blood count (CBC) with differential", 0.35),
    ("57021-8", "CBC without differential", 0.15),
    ("24331-1", "Lipid panel", 0.20),
    ("4548-4", "Hemoglobin A1c", 0.15),
    ("2160-0", "Creatinine", 0.10),
    ("33914-3", "Glomerular filtration rate (GFR)", 0.08),
    ("2951-2", "Sodium", 0.05),
    ("2823-3", "Potassium", 0.05),
    ("1742-6", "ALT", 0.08),
    ("1920-8", "AST", 0.08),
    ("2885-2", "Total protein", 0.05),
    ("1751-7", "Albumin", 0.05),
    ("3016-3", "TSH", 0.12),
    ("14749-6", "Free T4", 0.06),
    ("5902-2", "Prothrombin time (PT)", 0.05),
    ("6301-6", "INR", 0.05),
    ("5811-5", "Urinalysis", 0.15),
    ("49765-1", "Urine drug screen", 0.03),
    ("20570-8", "Troponin I", 0.02),
    ("33762-6", "BNP", 0.03),
    ("30341-2", "ESR", 0.04),
    ("1988-5", "CRP", 0.05),
    ("5778-6", "Blood culture", 0.02),
    ("5799-2", "Urine culture", 0.04),
]

# Imaging procedures
IMAGING_PROCEDURES = [
    ("36643-5", "XR Chest 2 Views", "CR", 0.25),
    ("24627-2", "XR Chest PA", "CR", 0.10),
    ("36554-4", "XR Abdomen", "CR", 0.05),
    ("37016-3", "XR Spine Lumbar", "CR", 0.08),
    ("24558-9", "CT Head without contrast", "CT", 0.10),
    ("24566-2", "CT Head with contrast", "CT", 0.05),
    ("30746-2", "CT Abdomen and Pelvis with contrast", "CT", 0.08),
    ("24531-6", "CT Chest with contrast", "CT", 0.06),
    ("36813-4", "MRI Brain without contrast", "MR", 0.05),
    ("24590-0", "MRI Brain with and without contrast", "MR", 0.04),
    ("26287-7", "US Abdomen complete", "US", 0.08),
    ("46342-2", "US Renal", "US", 0.04),
    ("30711-5", "US Pelvis", "US", 0.05),
    ("24725-4", "Mammogram screening", "MG", 0.06),
    ("69259-3", "DEXA bone density", "DX", 0.03),
]

# Insurance payers
PAYERS = [
    ("payer-bcbs", "Blue Cross Blue Shield", "commercial", 0.25),
    ("payer-aetna", "Aetna", "commercial", 0.12),
    ("payer-cigna", "Cigna", "commercial", 0.10),
    ("payer-uhc", "UnitedHealthcare", "commercial", 0.15),
    ("payer-harvard", "Harvard Pilgrim", "commercial", 0.08),
    ("payer-tufts", "Tufts Health Plan", "commercial", 0.05),
    ("payer-medicare", "Medicare", "government", 0.15),
    ("payer-medicaid", "Medicaid", "government", 0.08),
    ("payer-tricare", "TRICARE", "government", 0.02),
    (None, None, "self-pay", 0.05),  # Uninsured
]


def random_date(start_year: int, end_year: int) -> str:
    """Generate random date string."""
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def random_datetime(start_days_ago: int = 365, end_days_ago: int = 0) -> str:
    """Generate random datetime string."""
    days_ago = random.randint(end_days_ago, start_days_ago)
    dt = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def random_phone() -> str:
    """Generate random phone number with various formats (realistic messiness)."""
    formats = [
        "({area}) {prefix}-{line}",
        "{area}-{prefix}-{line}",
        "{area}.{prefix}.{line}",
        "{area}{prefix}{line}",
        "1-{area}-{prefix}-{line}",
        "+1{area}{prefix}{line}",
        "{area} {prefix} {line}",
        "({area}){prefix}-{line}",  # Missing space
    ]
    area = random.randint(200, 999)
    prefix = random.randint(200, 999)
    line = random.randint(1000, 9999)
    fmt = random.choice(formats)
    return fmt.format(area=area, prefix=prefix, line=line)


def random_ssn() -> Optional[str]:
    """Generate random SSN (sometimes missing or partial)."""
    if random.random() < 0.1:  # 10% missing
        return None
    if random.random() < 0.05:  # 5% partial/redacted
        return f"XXX-XX-{random.randint(1000, 9999)}"
    return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"


def generate_patient(patient_num: int) -> dict:
    """Generate a realistic patient with messy data."""
    patient_id = f"pat-{patient_num:05d}"

    # Gender and name
    gender = random.choice(["male", "female"])
    if gender == "male":
        first_name = random.choice(FIRST_NAMES_MALE)
    else:
        first_name = random.choice(FIRST_NAMES_FEMALE)

    last_name = random.choice(LAST_NAMES)

    # Sometimes middle name, sometimes initial, sometimes none
    middle = None
    if random.random() < 0.6:
        if random.random() < 0.5:
            middle = random.choice(FIRST_NAMES_MALE if random.random() < 0.5 else FIRST_NAMES_FEMALE)
        else:
            middle = random.choice(string.ascii_uppercase)

    # Name variations (realistic messiness)
    given = [first_name]
    if middle:
        if random.random() < 0.8:
            given.append(middle)

    # Sometimes nicknames recorded
    if random.random() < 0.1:
        nicknames = {"William": "Bill", "Robert": "Bob", "James": "Jim", "Michael": "Mike",
                     "Richard": "Dick", "Elizabeth": "Liz", "Jennifer": "Jen", "Patricia": "Pat"}
        if first_name in nicknames:
            given[0] = nicknames[first_name] if random.random() < 0.5 else first_name

    # Build name object
    name_obj = {
        "use": "official",
        "family": last_name,
        "given": given,
    }

    # Sometimes prefix
    if random.random() < 0.3:
        if gender == "male":
            name_obj["prefix"] = [random.choice(["Mr.", "Mr", "MR"])]
        else:
            name_obj["prefix"] = [random.choice(["Ms.", "Mrs.", "Miss", "Ms", "MRS"])]

    # Birth date - realistic age distribution
    age_weights = [0.05, 0.08, 0.12, 0.15, 0.18, 0.15, 0.12, 0.08, 0.05, 0.02]  # 0-9, 10-19, ... 90-99
    age_decade = random.choices(range(10), weights=age_weights)[0]
    age = age_decade * 10 + random.randint(0, 9)
    birth_year = datetime.now().year - age
    birth_date = random_date(birth_year, birth_year)

    # Address - sometimes incomplete
    city_info = random.choice(CITIES)
    address = {
        "use": random.choice(["home", "home", "home", "temp", "old"]),
        "city": city_info[0],
        "state": city_info[1],
        "postalCode": random.choice(city_info[2]),
    }

    # Street address - sometimes missing
    if random.random() < 0.9:
        street_num = random.randint(1, 9999)
        street = random.choice(STREETS)
        address["line"] = [f"{street_num} {street}"]

        # Sometimes apartment/unit on separate line
        if "Apt" not in street and random.random() < 0.2:
            apt_formats = ["Apt {}", "Apt. {}", "Unit {}", "#{}", "Apartment {}"]
            address["line"].append(random.choice(apt_formats).format(random.randint(1, 500)))

    # Phone - sometimes multiple, sometimes missing
    telecom = []
    if random.random() < 0.95:
        telecom.append({
            "system": "phone",
            "value": random_phone(),
            "use": random.choice(["home", "mobile", "work"]),
        })
    if random.random() < 0.4:
        telecom.append({
            "system": "phone",
            "value": random_phone(),
            "use": random.choice(["mobile", "work"]),
        })

    # Email - sometimes present
    if random.random() < 0.6:
        email_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "comcast.net", "verizon.net"]
        email_name = f"{first_name.lower()}.{last_name.lower().replace(' ', '').replace('-', '')}"
        if random.random() < 0.3:
            email_name += str(random.randint(1, 99))
        telecom.append({
            "system": "email",
            "value": f"{email_name}@{random.choice(email_domains)}",
        })

    # Build patient resource
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [
            {
                "use": "usual",
                "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
                "system": "http://hospital.example.org/mrn",
                "value": f"MRN-{100000 + patient_num}",
            }
        ],
        "active": True,
        "name": [name_obj],
        "gender": gender,
        "birthDate": birth_date,
        "address": [address],
    }

    if telecom:
        patient["telecom"] = telecom

    # SSN - sometimes
    ssn = random_ssn()
    if ssn:
        patient["identifier"].append({
            "use": "official",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "SS"}]},
            "system": "http://hl7.org/fhir/sid/us-ssn",
            "value": ssn,
        })

    # Marital status - sometimes
    if random.random() < 0.7:
        marital_codes = [("M", "Married"), ("S", "Never Married"), ("D", "Divorced"), ("W", "Widowed")]
        m = random.choice(marital_codes)
        patient["maritalStatus"] = {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus", "code": m[0], "display": m[1]}]
        }

    # Language - sometimes
    if random.random() < 0.3:
        languages = [("en", "English"), ("es", "Spanish"), ("pt", "Portuguese"), ("zh", "Chinese"),
                     ("vi", "Vietnamese"), ("fr", "French"), ("ht", "Haitian Creole")]
        lang = random.choices(languages, weights=[0.70, 0.15, 0.03, 0.04, 0.03, 0.02, 0.03])[0]
        patient["communication"] = [{
            "language": {"coding": [{"system": "urn:ietf:bcp:47", "code": lang[0], "display": lang[1]}]},
            "preferred": True
        }]

    # Deceased - small percentage
    if random.random() < 0.02:
        patient["deceasedBoolean"] = True
        if random.random() < 0.7:
            patient["deceasedDateTime"] = random_datetime(365 * 2, 30)

    return patient


def generate_practitioner(pract_num: int) -> dict:
    """Generate a practitioner."""
    pract_id = f"pract-{pract_num:03d}"

    gender = random.choice(["male", "female"])
    if gender == "male":
        first_name = random.choice(FIRST_NAMES_MALE[:30])  # Common names only
    else:
        first_name = random.choice(FIRST_NAMES_FEMALE[:30])

    last_name = random.choice(LAST_NAMES[:60])

    specialties = [
        ("207Q00000X", "Family Medicine"),
        ("207R00000X", "Internal Medicine"),
        ("208D00000X", "General Practice"),
        ("207RC0000X", "Cardiovascular Disease"),
        ("207RE0101X", "Endocrinology"),
        ("207RG0100X", "Gastroenterology"),
        ("207RN0300X", "Nephrology"),
        ("207RP1001X", "Pulmonary Disease"),
        ("2084N0400X", "Neurology"),
        ("207X00000X", "Orthopaedic Surgery"),
        ("208600000X", "Surgery"),
        ("207V00000X", "Obstetrics & Gynecology"),
        ("208000000X", "Pediatrics"),
        ("2084P0800X", "Psychiatry"),
        ("207L00000X", "Anesthesiology"),
        ("2086S0120X", "Radiology"),
        ("246Q00000X", "Pathology"),
        ("207P00000X", "Emergency Medicine"),
    ]

    spec = random.choice(specialties)

    return {
        "resourceType": "Practitioner",
        "id": pract_id,
        "identifier": [
            {"system": "http://hl7.org/fhir/sid/us-npi", "value": f"{random.randint(1000000000, 1999999999)}"}
        ],
        "active": True,
        "name": [{"family": last_name, "given": [first_name], "prefix": ["Dr."]}],
        "gender": gender,
        "qualification": [{
            "code": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0360", "code": "MD"}]},
            "identifier": [{"system": "http://example.org/specialty", "value": spec[0]}],
        }]
    }


def generate_condition(patient_id: str, condition_num: int) -> Optional[dict]:
    """Generate a condition for a patient."""
    # Weighted random selection
    weights = [c[2] for c in CONDITIONS]
    condition = random.choices(CONDITIONS, weights=weights)[0]

    code_obj = {}
    if condition[0]:  # Has ICD code
        code_obj = {
            "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": condition[0], "display": condition[1]}],
            "text": condition[1]
        }
    else:  # Free text only (messy data)
        code_obj = {"text": condition[1]}

    onset_date = random_datetime(365 * 5, 30)

    cond = {
        "resourceType": "Condition",
        "id": f"cond-{patient_id}-{condition_num}",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                       "code": random.choice(["active", "active", "active", "resolved", "inactive"])}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                       "code": random.choice(["confirmed", "confirmed", "confirmed", "provisional", "unconfirmed"])}]
        },
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]}],
        "code": code_obj,
        "subject": {"reference": f"Patient/{patient_id}"},
        "onsetDateTime": onset_date,
        "recordedDate": onset_date,
    }

    return cond


def generate_allergy(patient_id: str, allergy_num: int) -> Optional[dict]:
    """Generate an allergy for a patient."""
    weights = [a[4] for a in ALLERGIES]
    allergy = random.choices(ALLERGIES, weights=weights)[0]

    # NKDA is special
    if allergy[1] == "No Known Drug Allergies":
        return None  # Don't create a resource for NKDA

    code_obj = {}
    if allergy[0]:  # Has RxNorm code
        code_obj = {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": allergy[0], "display": allergy[1]}]
        }
    else:  # Free text
        code_obj = {"text": allergy[1]}

    allergyResource = {
        "resourceType": "AllergyIntolerance",
        "id": f"allergy-{patient_id}-{allergy_num}",
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                       "code": random.choice(["confirmed", "confirmed", "unconfirmed"])}]
        },
        "code": code_obj,
        "patient": {"reference": f"Patient/{patient_id}"},
        "recordedDate": random_datetime(365 * 10, 365),
    }

    if allergy[2]:
        allergyResource["type"] = random.choice(allergy[2])
        allergyResource["category"] = ["medication"] if allergy[0] else ["environment"]

    if allergy[3]:
        allergyResource["criticality"] = allergy[3]

    # Sometimes add reaction details
    if random.random() < 0.5 and allergy[0]:
        reactions = [
            ("271807003", "Eruption of skin"),
            ("267036007", "Dyspnea"),
            ("422587007", "Nausea"),
            ("422400008", "Vomiting"),
            ("418290006", "Itching"),
            ("39579001", "Anaphylaxis"),
        ]
        rxn = random.choice(reactions)
        allergyResource["reaction"] = [{
            "manifestation": [{"coding": [{"system": "http://snomed.info/sct", "code": rxn[0], "display": rxn[1]}]}],
            "severity": random.choice(["mild", "moderate", "severe"])
        }]

    return allergyResource


def generate_medication_request(patient_id: str, practitioner_id: str, encounter_id: Optional[str], med_num: int) -> dict:
    """Generate a medication request."""
    weights = [m[3] for m in MEDICATIONS]
    med = random.choices(MEDICATIONS, weights=weights)[0]

    med_request = {
        "resourceType": "MedicationRequest",
        "id": f"medrx-{patient_id}-{med_num}",
        "identifier": [{"system": "http://hospital.example.org/prescriptions", "value": f"RX-{random.randint(100000, 999999)}"}],
        "status": random.choice(["active", "active", "active", "completed", "stopped"]),
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": med[0], "display": med[1]}]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "authoredOn": random_datetime(365, 0),
        "requester": {"reference": f"Practitioner/{practitioner_id}"},
    }

    if encounter_id:
        med_request["encounter"] = {"reference": f"Encounter/{encounter_id}"}

    # Dosage instruction
    frequencies = [
        (1, 1, "d", "once daily"),
        (2, 1, "d", "twice daily"),
        (3, 1, "d", "three times daily"),
        (4, 1, "d", "four times daily"),
        (1, 1, "wk", "once weekly"),
    ]
    freq = random.choice(frequencies)

    med_request["dosageInstruction"] = [{
        "text": f"Take as directed {freq[3]}",
        "timing": {"repeat": {"frequency": freq[0], "period": freq[1], "periodUnit": freq[2]}},
        "route": {"coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]},
        "doseAndRate": [{"doseQuantity": {"value": 1, "unit": "tablet"}}]
    }]

    med_request["dispenseRequest"] = {
        "numberOfRepeatsAllowed": random.randint(0, 11),
        "quantity": {"value": random.choice([30, 60, 90]), "unit": "tablet"},
        "expectedSupplyDuration": {"value": 30, "unit": "days"}
    }

    return med_request


def generate_service_request_lab(patient_id: str, practitioner_id: str, encounter_id: str, order_num: int) -> dict:
    """Generate a lab order."""
    weights = [t[2] for t in LAB_TESTS]
    test = random.choices(LAB_TESTS, weights=weights)[0]

    return {
        "resourceType": "ServiceRequest",
        "id": f"laborder-{patient_id}-{order_num}",
        "identifier": [{"system": "http://hospital.example.org/orders", "value": f"ORD-{random.randint(100000, 999999)}"}],
        "status": random.choice(["active", "completed", "completed", "completed"]),
        "intent": "order",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
        "priority": random.choice(["routine", "routine", "routine", "urgent", "stat"]),
        "code": {"coding": [{"system": "http://loinc.org", "code": test[0], "display": test[1]}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "authoredOn": random_datetime(180, 0),
        "requester": {"reference": f"Practitioner/{practitioner_id}"},
    }


def generate_service_request_imaging(patient_id: str, practitioner_id: str, encounter_id: str, order_num: int) -> dict:
    """Generate an imaging order."""
    weights = [p[3] for p in IMAGING_PROCEDURES]
    proc = random.choices(IMAGING_PROCEDURES, weights=weights)[0]

    return {
        "resourceType": "ServiceRequest",
        "id": f"radorder-{patient_id}-{order_num}",
        "identifier": [{"system": "http://hospital.example.org/orders", "value": f"RAD-{random.randint(100000, 999999)}"}],
        "status": random.choice(["active", "completed", "completed", "completed"]),
        "intent": "order",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "imaging"}]}],
        "priority": random.choice(["routine", "routine", "urgent", "stat"]),
        "code": {"coding": [{"system": "http://loinc.org", "code": proc[0], "display": proc[1]}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "authoredOn": random_datetime(180, 0),
        "requester": {"reference": f"Practitioner/{practitioner_id}"},
    }


def generate_encounter(patient_id: str, practitioner_id: str, encounter_num: int) -> dict:
    """Generate an encounter."""
    encounter_classes = [
        ("AMB", "ambulatory", 0.60),
        ("IMP", "inpatient encounter", 0.15),
        ("EMER", "emergency", 0.10),
        ("OBSENC", "observation encounter", 0.05),
        ("HH", "home health", 0.05),
        ("VR", "virtual", 0.05),
    ]

    weights = [e[2] for e in encounter_classes]
    enc_class = random.choices(encounter_classes, weights=weights)[0]

    start_dt = random_datetime(365 * 2, 1)

    encounter = {
        "resourceType": "Encounter",
        "id": f"enc-{patient_id}-{encounter_num}",
        "identifier": [{"system": "http://hospital.example.org/encounters", "value": f"ENC-{random.randint(100000, 999999)}"}],
        "status": random.choice(["finished", "finished", "finished", "in-progress"]),
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": enc_class[0], "display": enc_class[1]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "participant": [{"individual": {"reference": f"Practitioner/{practitioner_id}"}}],
        "period": {"start": start_dt},
    }

    if encounter["status"] == "finished":
        # Calculate end time
        if enc_class[0] == "AMB":
            hours = random.uniform(0.25, 2)
        elif enc_class[0] == "IMP":
            hours = random.uniform(24, 168)  # 1-7 days
        elif enc_class[0] == "EMER":
            hours = random.uniform(2, 12)
        else:
            hours = random.uniform(0.5, 4)

        end_dt = (datetime.fromisoformat(start_dt.replace("Z", "")) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        encounter["period"]["end"] = end_dt

    return encounter


def generate_coverage(patient_id: str, coverage_num: int) -> dict:
    """Generate insurance coverage."""
    weights = [p[3] for p in PAYERS]
    payer = random.choices(PAYERS, weights=weights)[0]

    if payer[0] is None:  # Self-pay
        return None

    coverage = {
        "resourceType": "Coverage",
        "id": f"cov-{patient_id}-{coverage_num}",
        "status": "active",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "HIP" if payer[2] == "commercial" else "PUBLICPOL",
            }]
        },
        "subscriber": {"reference": f"Patient/{patient_id}"},
        "subscriberId": f"SUB-{random.randint(100000, 999999)}",
        "beneficiary": {"reference": f"Patient/{patient_id}"},
        "payor": [{"reference": f"Organization/{payer[0]}", "display": payer[1]}],
        "period": {
            "start": f"{datetime.now().year}-01-01",
            "end": f"{datetime.now().year}-12-31"
        }
    }

    if payer[2] == "commercial":
        coverage["class"] = [
            {"type": {"coding": [{"code": "group"}]}, "value": f"GRP-{random.randint(1000, 9999)}"},
            {"type": {"coding": [{"code": "plan"}]}, "value": random.choice(["PPO", "HMO", "EPO", "POS"])},
        ]

    return coverage


def main():
    """Generate all seed data."""
    print("Generating healthcare seed data...")

    # Generate practitioners
    practitioners = []
    for i in range(1, NUM_PRACTITIONERS + 1):
        practitioners.append(generate_practitioner(i))
    print(f"Generated {len(practitioners)} practitioners")

    # Generate patients and their data
    ehr_resources = []
    lis_resources = []
    ris_resources = []
    pharmacy_resources = []
    pas_resources = []
    billing_resources = []

    for i in range(1, NUM_PATIENTS + 1):
        if i % 100 == 0:
            print(f"Processing patient {i}/{NUM_PATIENTS}...")

        patient = generate_patient(i)
        patient_id = patient["id"]
        ehr_resources.append(patient)

        # Assign primary practitioner
        primary_pract = random.choice(practitioners)["id"]

        # Generate conditions
        if random.random() < CONDITION_PROBABILITY:
            num_conditions = random.randint(1, 5)
            for j in range(num_conditions):
                cond = generate_condition(patient_id, j + 1)
                if cond:
                    ehr_resources.append(cond)

        # Generate allergies
        if random.random() < ALLERGY_PROBABILITY:
            num_allergies = random.randint(1, 3)
            for j in range(num_allergies):
                allergy = generate_allergy(patient_id, j + 1)
                if allergy:
                    ehr_resources.append(allergy)

        # Generate encounters
        num_encounters = random.randint(*NUM_ENCOUNTERS_PER_PATIENT)
        encounter_ids = []
        for j in range(num_encounters):
            enc_pract = random.choice(practitioners)["id"]
            enc = generate_encounter(patient_id, enc_pract, j + 1)
            pas_resources.append(enc)
            encounter_ids.append(enc["id"])

        # Generate lab orders (attached to encounters)
        if encounter_ids and random.random() < LAB_ORDER_PROBABILITY:
            num_labs = random.randint(1, 4)
            for j in range(num_labs):
                enc_id = random.choice(encounter_ids)
                lab_order = generate_service_request_lab(patient_id, primary_pract, enc_id, j + 1)
                lis_resources.append(lab_order)

        # Generate imaging orders
        if encounter_ids and random.random() < IMAGING_PROBABILITY:
            num_imaging = random.randint(1, 2)
            for j in range(num_imaging):
                enc_id = random.choice(encounter_ids)
                img_order = generate_service_request_imaging(patient_id, primary_pract, enc_id, j + 1)
                ris_resources.append(img_order)

        # Generate medications
        if random.random() < MEDICATION_PROBABILITY:
            num_meds = random.randint(1, 6)
            enc_id = encounter_ids[0] if encounter_ids else None
            for j in range(num_meds):
                med = generate_medication_request(patient_id, primary_pract, enc_id, j + 1)
                pharmacy_resources.append(med)

        # Generate coverage
        coverage = generate_coverage(patient_id, 1)
        if coverage:
            billing_resources.append(coverage)

    # Add practitioners to EHR
    ehr_resources.extend(practitioners)

    # Create bundle files
    def make_bundle(resources):
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": r} for r in resources]
        }

    # Write files
    with open("data/seed/ehr_seed.json", "w") as f:
        json.dump(make_bundle(ehr_resources), f, indent=2)
    print(f"EHR: {len(ehr_resources)} resources")

    with open("data/seed/lis_seed.json", "w") as f:
        json.dump(make_bundle(lis_resources), f, indent=2)
    print(f"LIS: {len(lis_resources)} resources")

    with open("data/seed/ris_seed.json", "w") as f:
        json.dump(make_bundle(ris_resources), f, indent=2)
    print(f"RIS: {len(ris_resources)} resources")

    with open("data/seed/pharmacy_seed.json", "w") as f:
        json.dump(make_bundle(pharmacy_resources), f, indent=2)
    print(f"Pharmacy: {len(pharmacy_resources)} resources")

    with open("data/seed/pas_seed.json", "w") as f:
        json.dump(make_bundle(pas_resources), f, indent=2)
    print(f"PAS: {len(pas_resources)} resources")

    with open("data/seed/billing_seed.json", "w") as f:
        json.dump(make_bundle(billing_resources), f, indent=2)
    print(f"Billing: {len(billing_resources)} resources")

    total = len(ehr_resources) + len(lis_resources) + len(ris_resources) + len(pharmacy_resources) + len(pas_resources) + len(billing_resources)
    print(f"\nTotal: {total} resources generated")


if __name__ == "__main__":
    main()
