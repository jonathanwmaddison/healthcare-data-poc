#!/usr/bin/env python3
"""
HDH-Bench Data Generator

Generates a 6-system healthcare environment with:
1. Randomized cross-system ID mappings (no trivial pattern to exploit)
2. Exact ground truth computed during generation for all 12 tasks
3. FHIR R4 seed bundles ready for Docker services

Usage:
    python scripts/generate.py
    python scripts/generate.py --patients 1000 --output data
"""

import json
import random
import uuid
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple

SEED = 42
random.seed(SEED)

# ── Demographics pools ──────────────────────────────────────────────────────

NAME_TYPOS = {
    "Smith": ["Smyth", "Smithe", "Smth", "Simth"],
    "Johnson": ["Johnsen", "Jonson", "Jhonson", "Johnsson"],
    "Williams": ["Wiliams", "Willams", "Willaims", "Wlliams"],
    "Brown": ["Browne", "Brwon", "Bown", "Bronw"],
    "Jones": ["Jons", "Joness", "Jhones", "Jonse"],
    "Garcia": ["Gracia", "Garsia", "Garciaa", "Garca"],
    "Miller": ["Miler", "Millr", "Muller", "Millar"],
    "Davis": ["Davies", "Daviss", "Dvis", "Davs"],
    "Rodriguez": ["Rodrigez", "Rodriquez", "Rodrigues", "Rodrguez"],
    "Martinez": ["Martines", "Martinz", "Martnez", "Martimez"],
}

FIRST_NAME_ABBREVS = {
    "Michael": ["Mike", "M.", "Mich"], "William": ["Will", "Bill", "W."],
    "Robert": ["Rob", "Bob", "R."], "James": ["Jim", "Jamie", "J."],
    "John": ["Jon", "Johnny", "J."], "Jennifer": ["Jen", "Jenny", "J."],
    "Elizabeth": ["Liz", "Beth", "E."], "Margaret": ["Marge", "Peggy", "M."],
    "Patricia": ["Pat", "Patty", "P."], "Barbara": ["Barb", "Barbie", "B."],
}

MALE_NAMES = ["Michael", "William", "Robert", "James", "John",
              "David", "Richard", "Joseph", "Thomas", "Charles"]
FEMALE_NAMES = ["Jennifer", "Elizabeth", "Margaret", "Patricia", "Barbara",
                "Mary", "Linda", "Susan", "Jessica", "Sarah"]
LAST_NAMES = list(NAME_TYPOS.keys())
STREETS = ["Oak", "Maple", "Main", "First", "Second", "Park", "Cedar", "Elm", "Pine", "Lake"]
STREET_TYPES = ["St", "Ave", "Rd", "Dr", "Ln", "Blvd"]
CITIES = ["Boston", "Cambridge", "Newton", "Brookline", "Somerville",
          "Springfield", "Worcester", "Lowell", "Quincy", "Lynn"]
ZIPS = ["02101", "02139", "02458", "02445", "02143", "01103", "01602", "01852", "02169", "01902"]

# ── Clinical codes ───────────────────────────────────────────────────────────

ICD10_CONDITIONS = [
    ("E11.9", "Type 2 diabetes mellitus without complications", 0.12),
    ("I10", "Essential (primary) hypertension", 0.15),
    ("E78.5", "Hyperlipidemia, unspecified", 0.10),
    ("J44.9", "COPD, unspecified", 0.04),
    ("J45.909", "Unspecified asthma, uncomplicated", 0.05),
    ("K21.0", "GERD with esophagitis", 0.06),
    ("M54.5", "Low back pain", 0.08),
    ("F32.9", "Major depressive disorder, single episode", 0.07),
    ("F41.9", "Anxiety disorder, unspecified", 0.06),
    ("I48.91", "Unspecified atrial fibrillation", 0.03),
    ("N18.3", "Chronic kidney disease, stage 3", 0.02),
    ("E03.9", "Hypothyroidism, unspecified", 0.04),
    ("G47.33", "Obstructive sleep apnea", 0.03),
    ("M17.11", "Primary osteoarthritis, right knee", 0.03),
    ("I25.10", "Atherosclerotic heart disease", 0.02),
    ("C50.911", "Malignant neoplasm of breast, unspecified", 0.02),
    ("C34.90", "Malignant neoplasm of lung, unspecified", 0.015),
    ("C18.9", "Malignant neoplasm of colon, unspecified", 0.01),
]

ICD9_TO_ICD10 = {
    "250.00": ("E11.9", "Diabetes mellitus"), "401.9": ("I10", "Hypertension"),
    "272.4": ("E78.5", "Hyperlipidemia"), "496": ("J44.9", "COPD"),
    "493.90": ("J45.909", "Asthma"), "530.81": ("K21.0", "GERD"),
    "724.2": ("M54.5", "Low back pain"), "311": ("F32.9", "Depression"),
    "300.00": ("F41.9", "Anxiety"), "427.31": ("I48.91", "AFib"),
}

MEDICATIONS = [
    ("860975", "Metformin 500 MG Oral Tablet", ["E11.9"], 0.10),
    ("314076", "Lisinopril 10 MG Oral Tablet", ["I10"], 0.12),
    ("617311", "Atorvastatin 20 MG Oral Tablet", ["E78.5"], 0.11),
    ("197361", "Amlodipine 5 MG Oral Tablet", ["I10"], 0.08),
    ("198048", "Omeprazole 20 MG Capsule", ["K21.0"], 0.09),
    ("966247", "Levothyroxine 50 MCG Tablet", ["E03.9"], 0.06),
    ("745679", "Albuterol Inhalation Solution", ["J45.909"], 0.05),
    ("310430", "Gabapentin 300 MG Capsule", ["M54.5"], 0.04),
    ("312940", "Sertraline 50 MG Tablet", ["F32.9", "F41.9"], 0.06),
    ("310798", "Hydrochlorothiazide 25 MG Tablet", ["I10"], 0.05),
]

DOSAGE_INSTRUCTIONS = [
    "Take 1 tablet by mouth once daily",
    "Take 1 tablet by mouth twice daily with food",
    "Take 2 tablets by mouth at bedtime",
    "Take 1 tablet by mouth every morning",
    "Take 1 tablet by mouth every 12 hours",
    "Apply to affected area twice daily",
    "Inhale 2 puffs every 4-6 hours as needed",
    "Take 1 capsule by mouth three times daily with meals",
    "Take 1 tablet by mouth once daily in the morning",
    "Take 1-2 tablets by mouth every 4-6 hours as needed for pain",
    "Inject 10 units subcutaneously before breakfast",
    "Take 1 tablet under the tongue as needed for chest pain",
]

BIOMARKER_TESTS = {
    "HER2_IHC": {
        "loinc": "18474-7", "name": "HER2 Immunohistochemistry",
        "results": [("0", 0.3), ("1+", 0.25), ("2+", 0.25), ("3+", 0.2)],
        "cancer_codes": ["C50.911"],
    },
    "HER2_FISH": {
        "loinc": "32996-3", "name": "HER2 Gene Amplification FISH",
        "results": [("negative", 0.6), ("positive", 0.25), ("equivocal", 0.15)],
        "cancer_codes": ["C50.911"],
    },
    "EGFR_MUTATION": {
        "loinc": "21659-7", "name": "EGFR Gene Mutation Analysis",
        "results": [("negative", 0.7), ("exon 19 deletion", 0.12), ("L858R", 0.1), ("T790M", 0.05), ("other mutation", 0.03)],
        "cancer_codes": ["C34.90"],
    },
    "PD_L1": {
        "loinc": "85147-9", "name": "PD-L1 Expression by IHC",
        "results": [("TPS <1%", 0.4), ("TPS 1-49%", 0.35), ("TPS >=50%", 0.25)],
        "cancer_codes": ["C34.90", "C50.911"],
    },
    "ALK_FISH": {
        "loinc": "69935-2", "name": "ALK Gene Rearrangement FISH",
        "results": [("negative", 0.95), ("positive", 0.05)],
        "cancer_codes": ["C34.90"],
    },
    "KRAS_MUTATION": {
        "loinc": "55206-9", "name": "KRAS Gene Mutation Analysis",
        "results": [("wild type", 0.6), ("G12C", 0.15), ("G12D", 0.1), ("G12V", 0.1), ("other mutation", 0.05)],
        "cancer_codes": ["C34.90", "C18.9"],
    },
}

LAB_PANELS = {
    "24323-8": {
        "name": "Comprehensive Metabolic Panel",
        "tests": [
            ("2345-7", "Glucose", "mg/dL", 70, 100, 15),
            ("2160-0", "Creatinine", "mg/dL", 0.7, 1.3, 0.3),
            ("3094-0", "BUN", "mg/dL", 7, 20, 5),
            ("2951-2", "Sodium", "mmol/L", 136, 145, 3),
            ("2823-3", "Potassium", "mmol/L", 3.5, 5.0, 0.5),
        ]
    },
    "58410-2": {
        "name": "Complete Blood Count",
        "tests": [
            ("6690-2", "WBC", "K/uL", 4.5, 11.0, 2.0),
            ("789-8", "RBC", "M/uL", 4.5, 5.5, 0.5),
            ("718-7", "Hemoglobin", "g/dL", 12.0, 17.5, 1.5),
            ("777-3", "Platelets", "K/uL", 150, 400, 50),
        ]
    },
    "4548-4": {
        "name": "Hemoglobin A1c",
        "tests": [("4548-4", "HbA1c", "%", 4.0, 5.6, 1.5)]
    },
    "2093-3": {
        "name": "Lipid Panel",
        "tests": [
            ("2093-3", "Total Cholesterol", "mg/dL", 0, 200, 40),
            ("2571-8", "Triglycerides", "mg/dL", 0, 150, 50),
            ("2085-9", "HDL", "mg/dL", 40, 60, 15),
        ]
    },
}

LAB_COMMENTS = [
    "CRITICAL VALUE - Physician notified",
    "Hemolyzed specimen - results may be affected",
    "Lipemic specimen - triglycerides affected",
    "Results consistent with diabetes",
    "Recommend repeat testing in 3 months",
    "Values trending up from previous",
]

SYSTEM_CONFIGS = {
    "ehr":      {"prefix": "MRN-",  "offset": 100000},
    "lis":      {"prefix": "LAB-",  "offset": 200000},
    "ris":      {"prefix": "RAD-",  "offset": 300000},
    "pharmacy": {"prefix": "RX-",   "offset": 400000},
    "pas":      {"prefix": "ADT-",  "offset": 500000},
    "billing":  {"prefix": "ACCT-", "offset": 600000},
}


def _random_date(days_ago_max: int, days_ago_min: int) -> str:
    days = random.randint(days_ago_min, days_ago_max)
    dt = datetime(2026, 2, 1) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _weighted_choice(options: List[Tuple[str, float]]) -> str:
    r = random.random()
    cum = 0.0
    for value, prob in options:
        cum += prob
        if r < cum:
            return value
    return options[-1][0]


class BenchmarkGenerator:
    def __init__(self, num_patients: int = 1000):
        self.num_patients = num_patients

        # Per-system patient lists (FHIR Patient resources)
        self.patients_by_system: Dict[str, list] = {s: [] for s in SYSTEM_CONFIGS}

        # Clinical resources
        self.conditions: list = []
        self.medications: list = []
        self.lab_orders: list = []
        self.lab_results: list = []
        self.encounters: list = []

        # MPI entries (ground truth)
        self.mpi: list = []

        # ── Ground truth tracking ───────────────────────────────────────
        # T04: patients with E11.9 conditions
        self.gt_diabetic_patients: Set[str] = set()
        # T05: patients with LOINC 4548-4 observations
        self.gt_hba1c_patients: Set[str] = set()
        # T06: patients with active RxNorm 860975 medications
        self.gt_metformin_patients: Set[str] = set()
        # T10: observation IDs without basedOn
        self.gt_orphaned_observations: list = []
        # T11: stale active ServiceRequest IDs
        self.gt_abandoned_orders: list = []
        # T12: condition IDs with ICD-9 codes
        self.gt_legacy_conditions: list = []

        # Per-patient clinical tracking (for T01, T02, T03, T09)
        self.gt_patient_records: Dict[str, dict] = {}

        # ID mapping: canonical index -> system-specific patient ID
        self.id_maps: Dict[str, Dict[int, str]] = {}

    def _build_id_maps(self):
        """Create randomized per-system ID mappings.

        Instead of patient index i always mapping to prefix+offset+i,
        we shuffle a list of suffixes per system so the mapping is random
        but deterministic (using our global seed).
        """
        indices = list(range(self.num_patients))
        for system, cfg in SYSTEM_CONFIGS.items():
            shuffled = indices.copy()
            random.shuffle(shuffled)
            self.id_maps[system] = {}
            for canonical_idx, shuffled_idx in enumerate(shuffled):
                self.id_maps[system][canonical_idx] = f"{cfg['prefix']}{cfg['offset'] + shuffled_idx}"

    def _generate_demographics(self) -> Dict:
        gender = random.choice(["male", "female"])
        first_name = random.choice(MALE_NAMES if gender == "male" else FEMALE_NAMES)
        last_name = random.choice(LAST_NAMES)
        middle_name = random.choice(MALE_NAMES if gender == "male" else FEMALE_NAMES) if random.random() < 0.7 else None

        city_idx = random.randint(0, len(CITIES) - 1)
        area = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)

        return {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "gender": gender,
            "birth_date": f"{random.randint(1940, 2005)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "ssn_last4": f"{random.randint(1000, 9999)}",
            "phone": f"({area}) {exchange}-{number}",
            "street": f"{random.randint(1, 999)} {random.choice(STREETS)} {random.choice(STREET_TYPES)}",
            "city": CITIES[city_idx],
            "state": "MA",
            "zip": ZIPS[city_idx],
        }

    def _vary_demographics(self, base: Dict, system: str, is_dup: bool = False) -> Dict:
        varied = base.copy()
        chance = 0.5 if is_dup else 0.3

        if random.random() < chance and base["first_name"] in FIRST_NAME_ABBREVS:
            varied["first_name"] = random.choice(FIRST_NAME_ABBREVS[base["first_name"]])
        if random.random() < chance and base["last_name"] in NAME_TYPOS and random.random() < 0.3:
            varied["last_name"] = random.choice(NAME_TYPOS[base["last_name"]])
        if random.random() < 0.4:
            varied["first_name"] = varied["first_name"].upper()
            varied["last_name"] = varied["last_name"].upper()
        if random.random() < 0.3:
            varied["middle_name"] = None

        # Phone format variations
        digits = base["phone"].replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        if system == "lis":
            varied["phone"] = digits
        elif system == "billing":
            varied["phone"] = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
        elif system == "pharmacy":
            varied["phone"] = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

        if random.random() < 0.1:
            varied["birth_date"] = None
        if random.random() < 0.05:
            varied["phone"] = None

        return varied

    def _make_fhir_patient(self, patient_id: str, demo: Dict, system: str) -> Dict:
        name = {"family": demo["last_name"]}
        given = [demo["first_name"]]
        if demo.get("middle_name"):
            given.append(demo["middle_name"])
        name["given"] = given

        patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [{
                "use": "usual",
                "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
                "system": f"http://{system}.hospital.example.org/patients",
                "value": patient_id
            }],
            "active": True,
            "name": [name],
            "gender": demo["gender"],
        }
        if demo.get("birth_date"):
            patient["birthDate"] = demo["birth_date"]
        if demo.get("phone"):
            patient["telecom"] = [{"system": "phone", "value": demo["phone"]}]
        if demo.get("street"):
            patient["address"] = [{
                "line": [demo["street"]],
                "city": demo["city"],
                "state": demo["state"],
                "postalCode": demo["zip"]
            }]
        return patient

    # ── Generation ───────────────────────────────────────────────────────

    def generate_all(self):
        self._build_id_maps()
        self._generate_patients()
        self._generate_clinical_data()
        self._add_data_quality_issues()
        self._compute_cross_system_ground_truth()

    def _generate_patients(self):
        print(f"Generating {self.num_patients} patients across 6 systems...")
        for i in range(self.num_patients):
            base_demo = self._generate_demographics()
            system_ids = {sys: self.id_maps[sys][i] for sys in SYSTEM_CONFIGS}
            canonical_id = f"patient-{i:05d}"

            mpi_entry = {
                "canonical_id": canonical_id,
                "demographics": base_demo,
                "system_ids": system_ids,
                "clinical_data": {
                    "condition_ids": [],
                    "medication_ids": [],
                    "lab_order_ids": [],
                    "lab_result_ids": [],
                    "encounter_ids": [],
                }
            }
            self.mpi.append(mpi_entry)

            # Initialize per-patient record tracking
            self.gt_patient_records[canonical_id] = {
                "system_ids": system_ids,
                "demographics": base_demo,
                "conditions": [],
                "medications": [],
                "lab_results": [],
                "encounters": [],
            }

            for system, pid in system_ids.items():
                varied = self._vary_demographics(base_demo, system)
                patient = self._make_fhir_patient(pid, varied, system)
                self.patients_by_system[system].append(patient)

        # Add duplicates (~5%)
        self._add_duplicates()
        total = sum(len(p) for p in self.patients_by_system.values())
        print(f"  Created {total} patient records ({self.num_patients} unique + duplicates)")

    def _add_duplicates(self):
        num_dups = int(self.num_patients * 0.05)
        for _ in range(num_dups):
            orig_idx = random.randint(0, self.num_patients - 1)
            orig = self.mpi[orig_idx]
            systems_to_dup = random.sample(list(SYSTEM_CONFIGS.keys()), random.randint(1, 3))

            for system in systems_to_dup:
                dup_id = f"DUP-{random.randint(700000, 799999)}"
                varied = self._vary_demographics(orig["demographics"], system, is_dup=True)
                patient = self._make_fhir_patient(dup_id, varied, system)
                self.patients_by_system[system].append(patient)

                if "duplicate_ids" not in orig:
                    orig["duplicate_ids"] = []
                orig["duplicate_ids"].append({"system": system, "id": dup_id})

    def _generate_clinical_data(self):
        print("Generating clinical data...")
        for i, mpi_entry in enumerate(self.mpi):
            canonical_id = mpi_entry["canonical_id"]
            ehr_id = mpi_entry["system_ids"]["ehr"]
            lis_id = mpi_entry["system_ids"]["lis"]
            pharmacy_id = mpi_entry["system_ids"]["pharmacy"]
            pas_id = mpi_entry["system_ids"]["pas"]

            # ── Conditions ──
            patient_condition_codes = []
            for icd10, display, prevalence in ICD10_CONDITIONS:
                if random.random() < prevalence:
                    cond_id = f"cond-{uuid.uuid4().hex[:8]}"
                    condition = {
                        "resourceType": "Condition",
                        "id": cond_id,
                        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                        "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                        "code": {
                            "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": icd10, "display": display}],
                            "text": display
                        },
                        "subject": {"reference": f"Patient/{ehr_id}"},
                        "onsetDateTime": _random_date(365 * 5, 30),
                        "recordedDate": _random_date(365 * 5, 30),
                    }
                    self.conditions.append(condition)
                    mpi_entry["clinical_data"]["condition_ids"].append(cond_id)
                    patient_condition_codes.append(icd10)
                    self.gt_patient_records[canonical_id]["conditions"].append(cond_id)

                    # T04: track diabetic patients
                    if icd10 == "E11.9":
                        self.gt_diabetic_patients.add(canonical_id)

            # ── Medications ──
            for rxnorm, display, indications, base_prob in MEDICATIONS:
                prob = base_prob
                if any(ind in patient_condition_codes for ind in indications):
                    prob = min(0.8, prob * 3)
                if random.random() < prob:
                    med_id = f"med-{uuid.uuid4().hex[:8]}"
                    medication = {
                        "resourceType": "MedicationRequest",
                        "id": med_id,
                        "status": "active",
                        "intent": "order",
                        "medicationCodeableConcept": {
                            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxnorm, "display": display}],
                            "text": display
                        },
                        "subject": {"reference": f"Patient/{pharmacy_id}"},
                        "authoredOn": _random_date(365, 0),
                        "dosageInstruction": [{"text": random.choice(DOSAGE_INSTRUCTIONS)}],
                    }
                    self.medications.append(medication)
                    mpi_entry["clinical_data"]["medication_ids"].append(med_id)
                    self.gt_patient_records[canonical_id]["medications"].append(med_id)

                    # T06: track metformin patients
                    if rxnorm == "860975":
                        self.gt_metformin_patients.add(canonical_id)

            # ── Biomarker tests ──
            for test_name, test_info in BIOMARKER_TESTS.items():
                relevant = [c for c in patient_condition_codes if c in test_info["cancer_codes"]]
                if not relevant or random.random() > 0.8:
                    continue
                result_value = _weighted_choice(test_info["results"])
                result_id = f"biomarker-{uuid.uuid4().hex[:8]}"
                obs = {
                    "resourceType": "Observation",
                    "id": result_id,
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
                    "code": {"coding": [{"system": "http://loinc.org", "code": test_info["loinc"], "display": test_info["name"]}]},
                    "subject": {"reference": f"Patient/{lis_id}"},
                    "effectiveDateTime": _random_date(365, 30),
                    "valueString": result_value,
                }
                if any(kw in result_value.lower() for kw in ["positive", "3+", "deletion", "mutation"]):
                    obs["note"] = [{"text": f"POSITIVE RESULT: {test_info['name']} shows {result_value}. Recommend oncology consultation."}]
                self.lab_results.append(obs)

            # ── Lab orders & results ──
            num_panels = random.randint(0, 3)
            panel_codes = random.sample(list(LAB_PANELS.keys()), min(num_panels, len(LAB_PANELS)))
            for panel_code in panel_codes:
                panel = LAB_PANELS[panel_code]
                order_id = f"labord-{uuid.uuid4().hex[:8]}"
                order_date = _random_date(180, 0)

                order = {
                    "resourceType": "ServiceRequest",
                    "id": order_id,
                    "status": "completed",
                    "intent": "order",
                    "code": {"coding": [{"system": "http://loinc.org", "code": panel_code, "display": panel["name"]}]},
                    "subject": {"reference": f"Patient/{lis_id}"},
                    "authoredOn": order_date,
                }
                self.lab_orders.append(order)
                mpi_entry["clinical_data"]["lab_order_ids"].append(order_id)

                for loinc, test_name, unit, low, high, std_dev in panel["tests"]:
                    result_id = f"labres-{uuid.uuid4().hex[:8]}"
                    if random.random() < 0.8:
                        value = round(random.uniform(low, high), 1)
                    else:
                        if random.random() < 0.5:
                            value = round(low - random.uniform(0.1, 1) * std_dev, 1)
                        else:
                            value = round(high + random.uniform(0.1, 1) * std_dev, 1)

                    interpretation = "N"
                    if value < low:
                        interpretation = "L"
                    elif value > high:
                        interpretation = "H"

                    result = {
                        "resourceType": "Observation",
                        "id": result_id,
                        "status": "final",
                        "code": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": test_name}]},
                        "subject": {"reference": f"Patient/{lis_id}"},
                        "basedOn": [{"reference": f"ServiceRequest/{order_id}"}],
                        "effectiveDateTime": order_date,
                        "valueQuantity": {"value": value, "unit": unit},
                        "referenceRange": [{"low": {"value": low}, "high": {"value": high}}],
                        "interpretation": [{"coding": [{"code": interpretation}]}],
                    }

                    if random.random() < 0.1 or (interpretation != "N" and random.random() < 0.3):
                        result["note"] = [{"text": random.choice(LAB_COMMENTS)}]

                    self.lab_results.append(result)
                    mpi_entry["clinical_data"]["lab_result_ids"].append(result_id)
                    self.gt_patient_records[canonical_id]["lab_results"].append(result_id)

                    # T05: track HbA1c patients
                    if loinc == "4548-4":
                        self.gt_hba1c_patients.add(canonical_id)

            # ── Encounters ──
            num_encounters = random.randint(1, 5)
            enc_types = [("AMB", 0.6), ("EMER", 0.15), ("IMP", 0.1), ("OBSENC", 0.15)]
            for _ in range(num_encounters):
                enc_id = f"enc-{uuid.uuid4().hex[:8]}"
                enc_type = _weighted_choice(enc_types)
                encounter = {
                    "resourceType": "Encounter",
                    "id": enc_id,
                    "status": "finished",
                    "class": {"code": enc_type},
                    "subject": {"reference": f"Patient/{pas_id}"},
                    "period": {
                        "start": _random_date(365, 30),
                        "end": _random_date(29, 0),
                    }
                }
                self.encounters.append(encounter)
                mpi_entry["clinical_data"]["encounter_ids"].append(enc_id)
                self.gt_patient_records[canonical_id]["encounters"].append(enc_id)

        print(f"  Conditions: {len(self.conditions)}")
        print(f"  Medications: {len(self.medications)}")
        print(f"  Lab Orders: {len(self.lab_orders)}")
        print(f"  Lab Results: {len(self.lab_results)}")
        print(f"  Encounters: {len(self.encounters)}")

    def _add_data_quality_issues(self):
        """Add orphaned results, abandoned orders, and legacy ICD-9 conditions."""
        print("Adding data quality issues...")

        # T10: Orphaned lab results (no basedOn)
        for _ in range(30):
            lis_id = f"LAB-{random.randint(200000, 200999)}"
            result_id = f"orphan-res-{uuid.uuid4().hex[:8]}"
            obs = {
                "resourceType": "Observation",
                "id": result_id,
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "2345-7", "display": "Glucose"}]},
                "subject": {"reference": f"Patient/{lis_id}"},
                "effectiveDateTime": _random_date(365, 30),
                "valueQuantity": {"value": random.randint(70, 200), "unit": "mg/dL"},
                "note": [{"text": "ORPHANED: Order not found in system"}],
            }
            self.lab_results.append(obs)
            self.gt_orphaned_observations.append(result_id)

        # T11: Abandoned orders (stale active)
        for _ in range(20):
            lis_id = f"LAB-{random.randint(200000, 200999)}"
            order_id = f"abandoned-{uuid.uuid4().hex[:8]}"
            order = {
                "resourceType": "ServiceRequest",
                "id": order_id,
                "status": "active",
                "intent": "order",
                "code": {"coding": [{"system": "http://loinc.org", "code": "58410-2", "display": "CBC"}]},
                "subject": {"reference": f"Patient/{lis_id}"},
                "authoredOn": _random_date(400, 150),
                "note": [{"text": "ABANDONED: Specimen never collected"}],
            }
            self.lab_orders.append(order)
            self.gt_abandoned_orders.append(order_id)

        # T12: Legacy ICD-9 conditions
        for _ in range(100):
            ehr_id = f"MRN-{random.randint(100000, 100999)}"
            cond_id = f"legacy-{uuid.uuid4().hex[:8]}"
            icd9_code = random.choice(list(ICD9_TO_ICD10.keys()))
            icd10_code, display = ICD9_TO_ICD10[icd9_code]
            condition = {
                "resourceType": "Condition",
                "id": cond_id,
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-9-cm", "code": icd9_code}],
                },
                "subject": {"reference": f"Patient/{ehr_id}"},
                "onsetDateTime": _random_date(365 * 10, 365 * 3),
                "recordedDate": _random_date(365 * 10, 365 * 3),
                "note": [{"text": "Migrated from legacy system"}],
            }
            self.conditions.append(condition)
            self.gt_legacy_conditions.append(cond_id)

        print(f"  Orphaned observations: {len(self.gt_orphaned_observations)}")
        print(f"  Abandoned orders: {len(self.gt_abandoned_orders)}")
        print(f"  Legacy ICD-9 conditions: {len(self.gt_legacy_conditions)}")

    def _compute_cross_system_ground_truth(self):
        """Compute cross-system task answers from the per-patient tracking sets."""
        # T07 and T08 are computed after all data is generated
        # (they rely on set intersections via canonical IDs)
        pass  # Computed at save time in _build_ground_truth()

    # ── Selecting specific patients for T01, T02, T03, T09 ───────────

    def _pick_task_patients(self) -> Dict:
        """Pick specific patients for patient-matching tasks.

        We want patients that actually have data across the required systems.
        """
        # T01: single-system lookup - pick a patient with conditions in EHR
        t01_patient = None
        for entry in self.mpi:
            if entry["clinical_data"]["condition_ids"]:
                t01_patient = entry["canonical_id"]
                break

        # T02: cross-system match (EHR + Pharmacy) - pick patient with conditions AND medications
        t02_patient = None
        for entry in self.mpi:
            if entry["clinical_data"]["condition_ids"] and entry["clinical_data"]["medication_ids"]:
                t02_patient = entry["canonical_id"]
                break

        # T03: full 360 match (all 6 systems) - pick patient with data in many systems
        t03_patient = None
        for entry in self.mpi:
            has_conditions = bool(entry["clinical_data"]["condition_ids"])
            has_meds = bool(entry["clinical_data"]["medication_ids"])
            has_labs = bool(entry["clinical_data"]["lab_order_ids"])
            has_encounters = bool(entry["clinical_data"]["encounter_ids"])
            if has_conditions and has_meds and has_labs and has_encounters:
                t03_patient = entry["canonical_id"]
                break

        # T09: complete record for one patient - pick patient with rich data
        t09_patient = None
        for entry in self.mpi:
            conds = len(entry["clinical_data"]["condition_ids"])
            meds = len(entry["clinical_data"]["medication_ids"])
            labs = len(entry["clinical_data"]["lab_result_ids"])
            if conds >= 2 and meds >= 1 and labs >= 2:
                t09_patient = entry["canonical_id"]
                if t09_patient not in (t01_patient, t02_patient, t03_patient):
                    break

        return {
            "T01": t01_patient,
            "T02": t02_patient,
            "T03": t03_patient,
            "T09": t09_patient,
        }

    def _build_ground_truth(self) -> Dict:
        """Build the complete ground truth for all 12 tasks."""
        task_patients = self._pick_task_patients()

        # T07: diabetics on metformin (intersection)
        t07_patients = self.gt_diabetic_patients & self.gt_metformin_patients
        t07_pairs = []
        for canonical_id in sorted(t07_patients):
            entry = next(e for e in self.mpi if e["canonical_id"] == canonical_id)
            t07_pairs.append({
                "canonical_id": canonical_id,
                "ehr_id": entry["system_ids"]["ehr"],
                "pharmacy_id": entry["system_ids"]["pharmacy"],
            })

        # T08: diabetics + metformin + HbA1c (triple intersection)
        t08_patients = self.gt_diabetic_patients & self.gt_metformin_patients & self.gt_hba1c_patients
        t08_triples = []
        for canonical_id in sorted(t08_patients):
            entry = next(e for e in self.mpi if e["canonical_id"] == canonical_id)
            t08_triples.append({
                "canonical_id": canonical_id,
                "ehr_id": entry["system_ids"]["ehr"],
                "pharmacy_id": entry["system_ids"]["pharmacy"],
                "lis_id": entry["system_ids"]["lis"],
            })

        gt = {
            "description": "Exact ground truth for HDH-Bench - DO NOT give to agents",
            "generated_at": datetime.now().isoformat(),
            "seed": SEED,
            "num_patients": self.num_patients,
            "tasks": {}
        }

        # T01: Single-system patient lookup
        t01_cid = task_patients["T01"]
        t01_entry = next(e for e in self.mpi if e["canonical_id"] == t01_cid)
        gt["tasks"]["T01"] = {
            "type": "exact_record",
            "description": "Single-system patient lookup in EHR",
            "patient_ehr_id": t01_entry["system_ids"]["ehr"],
            "expected": {
                "patient_id": t01_entry["system_ids"]["ehr"],
                "demographics": t01_entry["demographics"],
                "condition_ids": t01_entry["clinical_data"]["condition_ids"],
            }
        }

        # T02: Cross-system match (EHR + Pharmacy)
        t02_cid = task_patients["T02"]
        t02_entry = next(e for e in self.mpi if e["canonical_id"] == t02_cid)
        gt["tasks"]["T02"] = {
            "type": "exact_record",
            "description": "Cross-system match EHR + Pharmacy",
            "patient_ehr_id": t02_entry["system_ids"]["ehr"],
            "expected": {
                "ehr_id": t02_entry["system_ids"]["ehr"],
                "pharmacy_id": t02_entry["system_ids"]["pharmacy"],
                "demographics": t02_entry["demographics"],
                "condition_ids": t02_entry["clinical_data"]["condition_ids"],
                "medication_ids": t02_entry["clinical_data"]["medication_ids"],
            }
        }

        # T03: Full 360 match (all 6 systems)
        t03_cid = task_patients["T03"]
        t03_entry = next(e for e in self.mpi if e["canonical_id"] == t03_cid)
        gt["tasks"]["T03"] = {
            "type": "exact_record",
            "description": "Full 360 match across all 6 systems",
            "patient_ehr_id": t03_entry["system_ids"]["ehr"],
            "expected": {
                "system_ids": t03_entry["system_ids"],
                "demographics": t03_entry["demographics"],
            }
        }

        # T04: Diabetic patients (E11.9)
        gt["tasks"]["T04"] = {
            "type": "id_set",
            "description": "Patients with E11.9 in EHR",
            "expected_ids": sorted(list(self.gt_diabetic_patients)),
            "expected_ehr_ids": sorted([
                next(e for e in self.mpi if e["canonical_id"] == cid)["system_ids"]["ehr"]
                for cid in self.gt_diabetic_patients
            ]),
            "count": len(self.gt_diabetic_patients),
        }

        # T05: HbA1c lab results (LOINC 4548-4)
        gt["tasks"]["T05"] = {
            "type": "id_set",
            "description": "Patients with HbA1c (LOINC 4548-4) observations in LIS",
            "expected_ids": sorted(list(self.gt_hba1c_patients)),
            "expected_lis_ids": sorted([
                next(e for e in self.mpi if e["canonical_id"] == cid)["system_ids"]["lis"]
                for cid in self.gt_hba1c_patients
            ]),
            "count": len(self.gt_hba1c_patients),
        }

        # T06: Active metformin (RxNorm 860975)
        gt["tasks"]["T06"] = {
            "type": "id_set",
            "description": "Patients with active metformin (RxNorm 860975) in Pharmacy",
            "expected_ids": sorted(list(self.gt_metformin_patients)),
            "expected_pharmacy_ids": sorted([
                next(e for e in self.mpi if e["canonical_id"] == cid)["system_ids"]["pharmacy"]
                for cid in self.gt_metformin_patients
            ]),
            "count": len(self.gt_metformin_patients),
        }

        # T07: Diabetics on metformin
        gt["tasks"]["T07"] = {
            "type": "id_pair_set",
            "description": "Patients with E11.9 in EHR AND metformin in Pharmacy",
            "expected_pairs": t07_pairs,
            "count": len(t07_pairs),
        }

        # T08: Diabetics + metformin + HbA1c
        gt["tasks"]["T08"] = {
            "type": "id_triple_set",
            "description": "Patients with E11.9 AND metformin AND HbA1c",
            "expected_triples": t08_triples,
            "count": len(t08_triples),
        }

        # T09: Complete record for one patient
        t09_cid = task_patients["T09"]
        t09_entry = next(e for e in self.mpi if e["canonical_id"] == t09_cid)
        gt["tasks"]["T09"] = {
            "type": "exact_record",
            "description": "Complete clinical record for one patient across all systems",
            "patient_ehr_id": t09_entry["system_ids"]["ehr"],
            "expected": {
                "system_ids": t09_entry["system_ids"],
                "demographics": t09_entry["demographics"],
                "condition_ids": t09_entry["clinical_data"]["condition_ids"],
                "medication_ids": t09_entry["clinical_data"]["medication_ids"],
                "lab_result_ids": t09_entry["clinical_data"]["lab_result_ids"],
                "encounter_ids": t09_entry["clinical_data"]["encounter_ids"],
            }
        }

        # T10: Orphaned lab results — computed from ALL observations, not just the
        # explicitly created orphans. Biomarker observations also lack basedOn.
        all_orphaned = sorted([
            obs["id"] for obs in self.lab_results
            if "basedOn" not in obs
        ])
        gt["tasks"]["T10"] = {
            "type": "id_set",
            "description": "Observations without basedOn reference in LIS",
            "expected_ids": all_orphaned,
            "count": len(all_orphaned),
        }

        # T11: Abandoned orders
        gt["tasks"]["T11"] = {
            "type": "id_set",
            "description": "ServiceRequests with status=active older than 90 days in LIS",
            "expected_ids": sorted(self.gt_abandoned_orders),
            "count": len(self.gt_abandoned_orders),
        }

        # T12: Legacy ICD-9 conditions
        gt["tasks"]["T12"] = {
            "type": "id_set",
            "description": "Conditions with ICD-9 coding system in EHR",
            "expected_ids": sorted(self.gt_legacy_conditions),
            "count": len(self.gt_legacy_conditions),
        }

        return gt

    # ── Save ─────────────────────────────────────────────────────────────

    def save(self, output_dir: Path):
        seed_dir = output_dir / "seed"
        gt_dir = output_dir / "benchmark" / "ground_truth"
        seed_dir.mkdir(parents=True, exist_ok=True)
        gt_dir.mkdir(parents=True, exist_ok=True)

        print("Saving data...")

        # EHR: patients + conditions
        self._save_bundle(seed_dir / "ehr_seed.json",
                          self.patients_by_system["ehr"] + self.conditions)

        # LIS: patients + orders + results
        self._save_bundle(seed_dir / "lis_seed.json",
                          self.patients_by_system["lis"] + self.lab_orders + self.lab_results)

        # RIS: patients only
        self._save_bundle(seed_dir / "ris_seed.json",
                          self.patients_by_system["ris"])

        # Pharmacy: patients + medications
        self._save_bundle(seed_dir / "pharmacy_seed.json",
                          self.patients_by_system["pharmacy"] + self.medications)

        # PAS: patients + encounters
        self._save_bundle(seed_dir / "pas_seed.json",
                          self.patients_by_system["pas"] + self.encounters)

        # Billing: patients only
        self._save_bundle(seed_dir / "billing_seed.json",
                          self.patients_by_system["billing"])

        # MPI
        mpi_data = {
            "description": "Ground truth patient identity mapping - DO NOT give to agents",
            "generated_at": datetime.now().isoformat(),
            "total_patients": len(self.mpi),
            "duplicate_patients": sum(1 for p in self.mpi if "duplicate_ids" in p),
            "patients": self.mpi,
        }
        self._save_json(gt_dir / "master_patient_index.json", mpi_data)

        # Ground truth
        ground_truth = self._build_ground_truth()
        self._save_json(gt_dir / "ground_truth.json", ground_truth)

        print(f"\nData saved to {output_dir}")

    def _save_bundle(self, path: Path, resources: list):
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": r} for r in resources]
        }
        self._save_json(path, bundle)

    def _save_json(self, path: Path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate HDH-Bench data with exact ground truth")
    parser.add_argument("--patients", "-p", type=int, default=1000, help="Number of patients")
    parser.add_argument("--output", "-o", default="data", help="Output directory")
    args = parser.parse_args()

    gen = BenchmarkGenerator(num_patients=args.patients)
    gen.generate_all()
    gen.save(Path(args.output))

    gt = gen._build_ground_truth()
    print(f"\n{'='*60}")
    print("HDH-BENCH DATA GENERATED")
    print(f"{'='*60}")
    print(f"Patients: {args.patients}")
    print(f"Ground truth tasks: {len(gt['tasks'])}")
    for tid, task in gt["tasks"].items():
        count = task.get("count", "N/A")
        print(f"  {tid}: {task['description']} (count={count})")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
