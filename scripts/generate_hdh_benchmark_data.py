#!/usr/bin/env python3
"""
HDH-Bench Data Generator

Generates realistic healthcare benchmark data by combining:
1. Synthea - for realistic clinical data (conditions, labs, medications)
2. FEBRL - for realistic patient demographics with known duplicates
3. Custom fragmentation - to simulate multi-system ID chaos

Usage:
    python scripts/generate_hdh_benchmark_data.py
    python scripts/generate_hdh_benchmark_data.py --patients 1000 --use-febrl
    python scripts/generate_hdh_benchmark_data.py --download-synthea
"""

import json
import random
import uuid
import hashlib
import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import urllib.request
import zipfile
import os

# Set seed for reproducibility
random.seed(42)

# FEBRL-style name variations for realistic duplicates
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

FIRST_NAME_ABBREVIATIONS = {
    "Michael": ["Mike", "M.", "Mich", "Michl"],
    "William": ["Will", "Bill", "W.", "Wm"],
    "Robert": ["Rob", "Bob", "R.", "Robt"],
    "James": ["Jim", "Jamie", "J.", "Jas"],
    "John": ["Jon", "Johnny", "J.", "Jn"],
    "Jennifer": ["Jen", "Jenny", "J.", "Jenn"],
    "Elizabeth": ["Liz", "Beth", "E.", "Eliz"],
    "Margaret": ["Marge", "Peggy", "M.", "Marg"],
    "Patricia": ["Pat", "Patty", "P.", "Patrc"],
    "Barbara": ["Barb", "Barbie", "B.", "Barba"],
}

# Clinical code systems
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
    # Oncology conditions for biomarker tasks
    ("C50.911", "Malignant neoplasm of breast, unspecified", 0.02),
    ("C34.90", "Malignant neoplasm of lung, unspecified", 0.015),
    ("C18.9", "Malignant neoplasm of colon, unspecified", 0.01),
]

# Oncology biomarker tests
BIOMARKER_TESTS = {
    "HER2_IHC": {
        "loinc": "18474-7",
        "name": "HER2 Immunohistochemistry",
        "results": [("0", 0.3), ("1+", 0.25), ("2+", 0.25), ("3+", 0.2)],
        "cancer_codes": ["C50.911"],
    },
    "HER2_FISH": {
        "loinc": "32996-3",
        "name": "HER2 Gene Amplification FISH",
        "results": [("negative", 0.6), ("positive", 0.25), ("equivocal", 0.15)],
        "cancer_codes": ["C50.911"],
    },
    "EGFR_MUTATION": {
        "loinc": "21659-7",
        "name": "EGFR Gene Mutation Analysis",
        "results": [("negative", 0.7), ("exon 19 deletion", 0.12), ("L858R", 0.1), ("T790M", 0.05), ("other mutation", 0.03)],
        "cancer_codes": ["C34.90"],
    },
    "PD_L1": {
        "loinc": "85147-9",
        "name": "PD-L1 Expression by IHC",
        "results": [("TPS <1%", 0.4), ("TPS 1-49%", 0.35), ("TPS >=50%", 0.25)],
        "cancer_codes": ["C34.90", "C50.911"],
    },
    "ALK_FISH": {
        "loinc": "69935-2",
        "name": "ALK Gene Rearrangement FISH",
        "results": [("negative", 0.95), ("positive", 0.05)],
        "cancer_codes": ["C34.90"],
    },
    "KRAS_MUTATION": {
        "loinc": "55206-9",
        "name": "KRAS Gene Mutation Analysis",
        "results": [("wild type", 0.6), ("G12C", 0.15), ("G12D", 0.1), ("G12V", 0.1), ("other mutation", 0.05)],
        "cancer_codes": ["C34.90", "C18.9"],
    },
}

# Pathology report templates
PATHOLOGY_TEMPLATES = [
    "Diagnosis: {cancer_type}. Grade: {grade}. Tumor size: {size} cm. Margins: {margins}. {nodes_text}. {biomarker_text}",
    "FINAL DIAGNOSIS: Invasive {cancer_type}, {grade} differentiated. Greatest dimension {size} cm. {nodes_text}. Resection margins {margins}. {biomarker_text}",
    "Pathologic staging: {stage}. {cancer_type}, {grade}. {nodes_text}. Margins: {margins}. Additional findings: {biomarker_text}",
]

# Legacy ICD-9 codes (for terminology mapping tasks)
ICD9_TO_ICD10 = {
    "250.00": "E11.9",   # Diabetes
    "401.9": "I10",      # Hypertension
    "272.4": "E78.5",    # Hyperlipidemia
    "496": "J44.9",      # COPD
    "493.90": "J45.909", # Asthma
    "530.81": "K21.0",   # GERD
    "724.2": "M54.5",    # Low back pain
    "311": "F32.9",      # Depression
    "300.00": "F41.9",   # Anxiety
    "427.31": "I48.91",  # AFib
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

# Free-text dosage instructions (for unstructured data tasks)
DOSAGE_INSTRUCTIONS = [
    "Take 1 tablet by mouth once daily",
    "Take 1 tablet by mouth twice daily with food",
    "Take 2 tablets by mouth at bedtime",
    "Take 1 tablet by mouth every morning",
    "Take 1 tablet by mouth every 12 hours",
    "Apply to affected area twice daily",
    "Inhale 2 puffs every 4-6 hours as needed for shortness of breath",
    "Take 1 capsule by mouth three times daily with meals",
    "Take 1 tablet by mouth once daily in the morning with or without food",
    "Take 1-2 tablets by mouth every 4-6 hours as needed for pain",
    "Inject 10 units subcutaneously before breakfast",
    "Take 1 tablet under the tongue as needed for chest pain",
]

# Clinical note templates (for unstructured data tasks)
CLINICAL_NOTE_TEMPLATES = [
    "Patient presents with {complaint}. Physical exam reveals {finding}. Assessment: {diagnosis}. Plan: {plan}.",
    "Follow-up visit for {diagnosis}. Patient reports {symptom}. Vitals stable. Continue current medications.",
    "Chief complaint: {complaint}. History: Patient has known {diagnosis}. Today complains of {symptom}. Will order {test}.",
    "Routine visit. Patient with {diagnosis} well-controlled on current regimen. No new complaints.",
    "Emergency visit for {complaint}. Labs show {finding}. Diagnosis: {diagnosis}. Patient admitted for observation.",
]

COMPLAINTS = ["chest pain", "shortness of breath", "fatigue", "headache", "abdominal pain", "dizziness", "cough"]
FINDINGS = ["elevated blood pressure", "irregular heartbeat", "decreased breath sounds", "tenderness", "normal exam"]
SYMPTOMS = ["improved symptoms", "worsening fatigue", "no change", "occasional dizziness", "mild discomfort"]
PLANS = ["continue current therapy", "increase medication dose", "order labs", "referral to specialist", "lifestyle modifications"]
TESTS = ["CBC", "CMP", "lipid panel", "chest X-ray", "EKG", "urinalysis"]

# Allergy data (with mix of coded and free-text)
ALLERGIES_CODED = [
    ("7980", "Penicillin", "rash"),
    ("2670", "Aspirin", "hives"),
    ("3498", "Sulfa drugs", "anaphylaxis"),
    ("1191", "Codeine", "nausea"),
    ("70618", "Amoxicillin", "rash"),
]

ALLERGIES_FREETEXT = [
    "Patient reports allergy to shellfish - develops hives",
    "Latex allergy - skin irritation reported",
    "Iodine contrast - history of reaction",
    "Bee sting allergy - carries EpiPen",
    "Seasonal allergies - pollen, grass",
    "Patient states 'bad reaction' to morphine",
    "Reports intolerance to metformin (GI upset)",
]

# Lab comments (for unstructured data tasks)
LAB_COMMENTS = [
    ("critical", "CRITICAL VALUE - Physician notified at {time}"),
    ("critical", "PANIC VALUE - Results called to floor"),
    ("quality", "Hemolyzed specimen - results may be affected"),
    ("quality", "Lipemic specimen - triglycerides affected"),
    ("quality", "Insufficient sample - partial results only"),
    ("interpretation", "Results consistent with {condition}"),
    ("interpretation", "Recommend repeat testing in {timeframe}"),
    ("interpretation", "Values trending {direction} from previous"),
]

LAB_PANELS = {
    "24323-8": {  # CMP
        "name": "Comprehensive Metabolic Panel",
        "tests": [
            ("2345-7", "Glucose", "mg/dL", 70, 100, 15),
            ("2160-0", "Creatinine", "mg/dL", 0.7, 1.3, 0.3),
            ("3094-0", "BUN", "mg/dL", 7, 20, 5),
            ("2951-2", "Sodium", "mmol/L", 136, 145, 3),
            ("2823-3", "Potassium", "mmol/L", 3.5, 5.0, 0.5),
        ]
    },
    "58410-2": {  # CBC
        "name": "Complete Blood Count",
        "tests": [
            ("6690-2", "WBC", "K/uL", 4.5, 11.0, 2.0),
            ("789-8", "RBC", "M/uL", 4.5, 5.5, 0.5),
            ("718-7", "Hemoglobin", "g/dL", 12.0, 17.5, 1.5),
            ("777-3", "Platelets", "K/uL", 150, 400, 50),
        ]
    },
    "4548-4": {  # HbA1c
        "name": "Hemoglobin A1c",
        "tests": [
            ("4548-4", "HbA1c", "%", 4.0, 5.6, 1.5),
        ]
    },
    "2093-3": {  # Lipid Panel
        "name": "Lipid Panel",
        "tests": [
            ("2093-3", "Total Cholesterol", "mg/dL", 0, 200, 40),
            ("2571-8", "Triglycerides", "mg/dL", 0, 150, 50),
            ("2085-9", "HDL", "mg/dL", 40, 60, 15),
        ]
    },
}

# System ID schemes
SYSTEM_ID_SCHEMES = {
    "ehr": ("MRN-", 100000),
    "lis": ("LAB-", 200000),
    "ris": ("RAD-", 300000),
    "pharmacy": ("RX-", 400000),
    "pas": ("ADT-", 500000),
    "billing": ("ACCT-", 600000),
}


class HDHDataGenerator:
    def __init__(self, num_patients: int = 1000, use_febrl: bool = True):
        self.num_patients = num_patients
        self.use_febrl = use_febrl
        self.master_patient_index = []
        self.patients_by_system = {sys: [] for sys in SYSTEM_ID_SCHEMES.keys()}
        self.clinical_data = {
            "conditions": [],
            "medications": [],
            "lab_orders": [],
            "lab_results": [],
            "encounters": [],
            "claims": [],
        }

    def generate_demographics(self, patient_idx: int) -> Dict:
        """Generate base patient demographics"""
        gender = random.choice(["male", "female"])

        if gender == "male":
            first_names = ["Michael", "William", "Robert", "James", "John",
                          "David", "Richard", "Joseph", "Thomas", "Charles"]
        else:
            first_names = ["Jennifer", "Elizabeth", "Margaret", "Patricia", "Barbara",
                          "Mary", "Linda", "Susan", "Jessica", "Sarah"]

        last_names = list(NAME_TYPOS.keys())

        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        middle_name = random.choice(first_names) if random.random() < 0.7 else None

        birth_year = random.randint(1940, 2005)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)

        # Generate SSN (last 4 only for realism)
        ssn_last4 = f"{random.randint(1000, 9999)}"

        # Generate phone with various formats
        area = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        phone = f"({area}) {exchange}-{number}"

        # Generate address
        streets = ["Oak", "Maple", "Main", "First", "Second", "Park", "Cedar", "Elm", "Pine", "Lake"]
        street_types = ["St", "Ave", "Rd", "Dr", "Ln", "Blvd"]
        cities = ["Boston", "Cambridge", "Newton", "Brookline", "Somerville",
                 "Springfield", "Worcester", "Lowell", "Quincy", "Lynn"]
        states = ["MA"] * 10  # Keep in one state for simplicity
        zips = ["02101", "02139", "02458", "02445", "02143", "01103", "01602", "01852", "02169", "01902"]

        city_idx = random.randint(0, len(cities) - 1)

        return {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "gender": gender,
            "birth_date": f"{birth_year}-{birth_month:02d}-{birth_day:02d}",
            "ssn_last4": ssn_last4,
            "phone": phone,
            "street": f"{random.randint(1, 999)} {random.choice(streets)} {random.choice(street_types)}",
            "city": cities[city_idx],
            "state": states[city_idx],
            "zip": zips[city_idx],
        }

    def create_demographic_variation(self, base: Dict, system: str, is_duplicate: bool = False) -> Dict:
        """Create realistic variations of demographics per system"""
        varied = base.copy()

        # More aggressive variations for duplicates
        variation_chance = 0.5 if is_duplicate else 0.3

        # Name variations
        if random.random() < variation_chance:
            first_name = base["first_name"]
            if first_name in FIRST_NAME_ABBREVIATIONS:
                varied["first_name"] = random.choice(FIRST_NAME_ABBREVIATIONS[first_name])

        if random.random() < variation_chance:
            last_name = base["last_name"]
            if last_name in NAME_TYPOS and random.random() < 0.3:
                varied["last_name"] = random.choice(NAME_TYPOS[last_name])

        if random.random() < 0.4:
            # Case variations
            varied["first_name"] = varied["first_name"].upper()
            varied["last_name"] = varied["last_name"].upper()

        if random.random() < 0.3:
            varied["middle_name"] = None  # Missing middle name

        # Date format variations by system
        if system == "lis":
            # MM/DD/YYYY format
            parts = base["birth_date"].split("-")
            varied["birth_date_display"] = f"{parts[1]}/{parts[2]}/{parts[0]}"
        elif system == "billing":
            # MMDDYYYY format
            parts = base["birth_date"].split("-")
            varied["birth_date_display"] = f"{parts[1]}{parts[2]}{parts[0]}"
        else:
            varied["birth_date_display"] = base["birth_date"]

        # Phone format variations
        digits = base["phone"].replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        if system == "lis":
            varied["phone"] = digits  # No formatting
        elif system == "billing":
            varied["phone"] = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"  # Dot format
        elif system == "pharmacy":
            varied["phone"] = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"  # Dash format

        # Randomly null out some fields
        if random.random() < 0.1:
            varied["birth_date"] = None
        if random.random() < 0.05:
            varied["phone"] = None

        return varied

    def create_fhir_patient(self, patient_id: str, demographics: Dict, system: str) -> Dict:
        """Create FHIR Patient resource"""
        name = {"family": demographics["last_name"]}
        given = [demographics["first_name"]]
        if demographics.get("middle_name"):
            given.append(demographics["middle_name"])
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
            "gender": demographics["gender"],
        }

        if demographics.get("birth_date"):
            patient["birthDate"] = demographics["birth_date"]

        if demographics.get("phone"):
            patient["telecom"] = [{"system": "phone", "value": demographics["phone"]}]

        if demographics.get("street"):
            patient["address"] = [{
                "line": [demographics["street"]],
                "city": demographics["city"],
                "state": demographics["state"],
                "postalCode": demographics["zip"]
            }]

        return patient

    def generate_patients(self):
        """Generate all patients across systems"""
        print(f"Generating {self.num_patients} patients across {len(SYSTEM_ID_SCHEMES)} systems...")

        for i in range(self.num_patients):
            base_demographics = self.generate_demographics(i)

            # Create system-specific IDs
            system_ids = {}
            for system, (prefix, offset) in SYSTEM_ID_SCHEMES.items():
                system_ids[system] = f"{prefix}{offset + i}"

            # Store in MPI (ground truth)
            mpi_entry = {
                "canonical_id": f"patient-{i:05d}",
                "demographics": base_demographics,
                "system_ids": system_ids,
                "clinical_data": {
                    "condition_ids": [],
                    "medication_ids": [],
                    "lab_order_ids": [],
                    "encounter_ids": [],
                    "claim_ids": [],
                }
            }
            self.master_patient_index.append(mpi_entry)

            # Create patient in each system with variations
            for system, patient_id in system_ids.items():
                varied = self.create_demographic_variation(base_demographics, system)
                patient = self.create_fhir_patient(patient_id, varied, system)
                self.patients_by_system[system].append(patient)

        # Add duplicates (~5% of patients)
        self._add_duplicate_patients()

        total_patients = sum(len(p) for p in self.patients_by_system.values())
        print(f"  Created {total_patients} patient records ({self.num_patients} unique + duplicates)")

    def _add_duplicate_patients(self):
        """Add realistic duplicate patient registrations"""
        num_duplicates = int(self.num_patients * 0.05)

        for _ in range(num_duplicates):
            # Pick a random patient to duplicate
            orig_idx = random.randint(0, self.num_patients - 1)
            orig_entry = self.master_patient_index[orig_idx]

            # Pick systems to have duplicates
            systems_to_dup = random.sample(list(SYSTEM_ID_SCHEMES.keys()), random.randint(1, 3))

            for system in systems_to_dup:
                prefix, offset = SYSTEM_ID_SCHEMES[system]
                dup_id = f"DUP-{random.randint(700000, 799999)}"

                # Create varied demographics (more aggressive for duplicates)
                varied = self.create_demographic_variation(orig_entry["demographics"], system, is_duplicate=True)
                patient = self.create_fhir_patient(dup_id, varied, system)
                self.patients_by_system[system].append(patient)

                # Record duplicate in MPI
                if "duplicate_ids" not in orig_entry:
                    orig_entry["duplicate_ids"] = []
                orig_entry["duplicate_ids"].append({"system": system, "id": dup_id})

    def generate_clinical_data(self):
        """Generate clinical data for all patients"""
        print("Generating clinical data...")

        for mpi_entry in self.master_patient_index:
            self._generate_patient_conditions(mpi_entry)
            self._generate_patient_medications(mpi_entry)
            self._generate_biomarker_tests(mpi_entry)
            self._generate_patient_labs(mpi_entry)
            self._generate_patient_encounters(mpi_entry)

        # Add orphaned records for data quality tasks
        self._add_orphaned_records()
        # Add legacy ICD-9 codes for terminology tasks
        self._add_legacy_codes()

        print(f"  Conditions: {len(self.clinical_data['conditions'])}")
        print(f"  Medications: {len(self.clinical_data['medications'])}")
        print(f"  Lab Orders: {len(self.clinical_data['lab_orders'])}")
        print(f"  Lab Results: {len(self.clinical_data['lab_results'])}")
        print(f"  Encounters: {len(self.clinical_data['encounters'])}")

    def _generate_patient_conditions(self, mpi_entry: Dict):
        """Generate conditions for a patient"""
        ehr_id = mpi_entry["system_ids"]["ehr"]

        # Determine conditions based on prevalence
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
                    "onsetDateTime": self._random_date(365 * 5, 30),
                    "recordedDate": self._random_date(365 * 5, 30),
                }
                self.clinical_data["conditions"].append(condition)
                mpi_entry["clinical_data"]["condition_ids"].append(cond_id)

    def _generate_patient_medications(self, mpi_entry: Dict):
        """Generate medications for a patient"""
        pharmacy_id = mpi_entry["system_ids"]["pharmacy"]
        patient_conditions = [c["code"]["coding"][0]["code"]
                            for c in self.clinical_data["conditions"]
                            if c["subject"]["reference"].endswith(mpi_entry["system_ids"]["ehr"])]

        for rxnorm, display, indications, base_prob in MEDICATIONS:
            # Higher probability if patient has indication
            prob = base_prob
            if any(ind in patient_conditions for ind in indications):
                prob = min(0.8, prob * 3)

            if random.random() < prob:
                med_id = f"med-{uuid.uuid4().hex[:8]}"
                # Generate realistic dosage instruction
                dosage_text = random.choice(DOSAGE_INSTRUCTIONS)

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
                    "authoredOn": self._random_date(365, 0),
                    "dosageInstruction": [{"text": dosage_text}],
                }
                self.clinical_data["medications"].append(medication)
                mpi_entry["clinical_data"]["medication_ids"].append(med_id)

    def _generate_biomarker_tests(self, mpi_entry: Dict):
        """Generate biomarker tests for oncology patients"""
        lis_id = mpi_entry["system_ids"]["lis"]
        ehr_id = mpi_entry["system_ids"]["ehr"]

        # Check if patient has cancer diagnosis
        patient_conditions = [c["code"]["coding"][0]["code"]
                            for c in self.clinical_data["conditions"]
                            if c["subject"]["reference"].endswith(ehr_id)]

        for test_name, test_info in BIOMARKER_TESTS.items():
            # Only generate if patient has relevant cancer
            relevant_cancers = [c for c in patient_conditions if c in test_info["cancer_codes"]]
            if not relevant_cancers:
                continue

            # 80% chance to have biomarker testing if diagnosed with cancer
            if random.random() > 0.8:
                continue

            # Generate test result
            r = random.random()
            cumulative = 0
            result_value = test_info["results"][0][0]
            for result, prob in test_info["results"]:
                cumulative += prob
                if r < cumulative:
                    result_value = result
                    break

            result_id = f"biomarker-{uuid.uuid4().hex[:8]}"
            test_date = self._random_date(365, 30)

            observation = {
                "resourceType": "Observation",
                "id": result_id,
                "status": "final",
                "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
                "code": {"coding": [{"system": "http://loinc.org", "code": test_info["loinc"], "display": test_info["name"]}]},
                "subject": {"reference": f"Patient/{lis_id}"},
                "effectiveDateTime": test_date,
                "valueString": result_value,
            }

            # Add interpretive comment for positive results
            if "positive" in result_value.lower() or "3+" in result_value or "deletion" in result_value or "mutation" in result_value:
                observation["note"] = [{
                    "text": f"POSITIVE RESULT: {test_info['name']} shows {result_value}. Patient may be eligible for targeted therapy. Recommend oncology consultation."
                }]

            self.clinical_data["lab_results"].append(observation)

    def _generate_patient_labs(self, mpi_entry: Dict):
        """Generate lab orders and results for a patient"""
        lis_id = mpi_entry["system_ids"]["lis"]

        # 0-3 lab panels per patient
        num_panels = random.randint(0, 3)
        panel_codes = random.sample(list(LAB_PANELS.keys()), min(num_panels, len(LAB_PANELS)))

        for panel_code in panel_codes:
            panel = LAB_PANELS[panel_code]
            order_id = f"labord-{uuid.uuid4().hex[:8]}"
            order_date = self._random_date(180, 0)

            # Create order
            order = {
                "resourceType": "ServiceRequest",
                "id": order_id,
                "status": "completed",
                "intent": "order",
                "code": {"coding": [{"system": "http://loinc.org", "code": panel_code, "display": panel["name"]}]},
                "subject": {"reference": f"Patient/{lis_id}"},
                "authoredOn": order_date,
            }
            self.clinical_data["lab_orders"].append(order)
            mpi_entry["clinical_data"]["lab_order_ids"].append(order_id)

            # Create results for each test in panel
            for loinc, test_name, unit, low, high, std_dev in panel["tests"]:
                result_id = f"labres-{uuid.uuid4().hex[:8]}"

                # Generate value (80% normal, 20% abnormal)
                if random.random() < 0.8:
                    value = round(random.uniform(low, high), 1)
                else:
                    # Abnormal - use std_dev to determine how far off
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

                # Add lab comments (10% chance, higher for critical values)
                add_comment = random.random() < 0.1 or (interpretation != "N" and random.random() < 0.3)
                if add_comment:
                    comment_type, comment_template = random.choice(LAB_COMMENTS)
                    comment_text = comment_template.format(
                        time=f"{random.randint(8,17):02d}:{random.randint(0,59):02d}",
                        condition=random.choice(["diabetes", "renal disease", "infection", "anemia"]),
                        timeframe=random.choice(["2 weeks", "1 month", "3 months"]),
                        direction=random.choice(["up", "down", "stable"])
                    )
                    result["note"] = [{"text": comment_text}]

                self.clinical_data["lab_results"].append(result)

    def _generate_patient_encounters(self, mpi_entry: Dict):
        """Generate encounters for a patient"""
        pas_id = mpi_entry["system_ids"]["pas"]

        # 1-5 encounters per patient
        num_encounters = random.randint(1, 5)
        encounter_types = [
            ("AMB", 0.6),   # Outpatient
            ("EMER", 0.15), # Emergency
            ("IMP", 0.1),   # Inpatient
            ("OBSENC", 0.15), # Observation
        ]

        for _ in range(num_encounters):
            enc_id = f"enc-{uuid.uuid4().hex[:8]}"

            # Weighted random encounter type
            r = random.random()
            cumulative = 0
            enc_type = "AMB"
            for etype, prob in encounter_types:
                cumulative += prob
                if r < cumulative:
                    enc_type = etype
                    break

            encounter = {
                "resourceType": "Encounter",
                "id": enc_id,
                "status": "finished",
                "class": {"code": enc_type},
                "subject": {"reference": f"Patient/{pas_id}"},
                "period": {
                    "start": self._random_date(365, 30),
                    "end": self._random_date(29, 0),
                }
            }
            self.clinical_data["encounters"].append(encounter)
            mpi_entry["clinical_data"]["encounter_ids"].append(enc_id)

    def _add_orphaned_records(self):
        """Add orphaned records for data quality tasks"""
        # Orphaned lab results (no order)
        for _ in range(30):
            lis_id = f"LAB-{random.randint(200000, 200999)}"
            result_id = f"orphan-res-{uuid.uuid4().hex[:8]}"

            result = {
                "resourceType": "Observation",
                "id": result_id,
                "status": "final",
                "code": {"coding": [{"system": "http://loinc.org", "code": "2345-7", "display": "Glucose"}]},
                "subject": {"reference": f"Patient/{lis_id}"},
                # NO basedOn - orphaned!
                "effectiveDateTime": self._random_date(365, 30),
                "valueQuantity": {"value": random.randint(70, 200), "unit": "mg/dL"},
                "note": [{"text": "ORPHANED: Order not found in system"}],
            }
            self.clinical_data["lab_results"].append(result)

        # Abandoned orders (never resulted)
        for _ in range(20):
            lis_id = f"LAB-{random.randint(200000, 200999)}"
            order_id = f"abandoned-{uuid.uuid4().hex[:8]}"

            order = {
                "resourceType": "ServiceRequest",
                "id": order_id,
                "status": "active",  # Still active but old
                "intent": "order",
                "code": {"coding": [{"system": "http://loinc.org", "code": "58410-2", "display": "CBC"}]},
                "subject": {"reference": f"Patient/{lis_id}"},
                "authoredOn": self._random_date(400, 150),  # Old order
                "note": [{"text": "ABANDONED: Specimen never collected"}],
            }
            self.clinical_data["lab_orders"].append(order)

    def _add_legacy_codes(self):
        """Add legacy ICD-9 coded conditions for terminology tasks"""
        for _ in range(100):
            ehr_id = f"MRN-{random.randint(100000, 100999)}"
            cond_id = f"legacy-{uuid.uuid4().hex[:8]}"

            icd9_code = random.choice(list(ICD9_TO_ICD10.keys()))

            condition = {
                "resourceType": "Condition",
                "id": cond_id,
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-9-cm", "code": icd9_code}],
                },
                "subject": {"reference": f"Patient/{ehr_id}"},
                "onsetDateTime": self._random_date(365 * 10, 365 * 3),
                "recordedDate": self._random_date(365 * 10, 365 * 3),
                "note": [{"text": "Migrated from legacy system"}],
            }
            self.clinical_data["conditions"].append(condition)

    def _random_date(self, days_ago_max: int, days_ago_min: int) -> str:
        """Generate random date in range"""
        days = random.randint(days_ago_min, days_ago_max)
        dt = datetime.now() - timedelta(days=days)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def save_all(self, output_dir: Path):
        """Save all generated data"""
        seed_dir = output_dir / "seed"
        benchmark_dir = output_dir / "benchmark" / "ground_truth"

        seed_dir.mkdir(parents=True, exist_ok=True)
        benchmark_dir.mkdir(parents=True, exist_ok=True)

        print("Saving data...")

        # EHR bundle
        ehr_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": ([{"resource": p} for p in self.patients_by_system["ehr"]] +
                     [{"resource": c} for c in self.clinical_data["conditions"]])
        }
        self._save_json(seed_dir / "ehr_seed.json", ehr_bundle)

        # LIS bundle
        lis_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": ([{"resource": p} for p in self.patients_by_system["lis"]] +
                     [{"resource": o} for o in self.clinical_data["lab_orders"]] +
                     [{"resource": r} for r in self.clinical_data["lab_results"]])
        }
        self._save_json(seed_dir / "lis_seed.json", lis_bundle)

        # RIS bundle
        ris_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["ris"]]
        }
        self._save_json(seed_dir / "ris_seed.json", ris_bundle)

        # Pharmacy bundle
        pharmacy_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": ([{"resource": p} for p in self.patients_by_system["pharmacy"]] +
                     [{"resource": m} for m in self.clinical_data["medications"]])
        }
        self._save_json(seed_dir / "pharmacy_seed.json", pharmacy_bundle)

        # PAS bundle
        pas_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": ([{"resource": p} for p in self.patients_by_system["pas"]] +
                     [{"resource": e} for e in self.clinical_data["encounters"]])
        }
        self._save_json(seed_dir / "pas_seed.json", pas_bundle)

        # Billing bundle
        billing_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["billing"]]
        }
        self._save_json(seed_dir / "billing_seed.json", billing_bundle)

        # Save ground truth MPI
        mpi_data = {
            "description": "Ground truth patient identity mapping - DO NOT give to agents",
            "generated_at": datetime.now().isoformat(),
            "total_patients": len(self.master_patient_index),
            "duplicate_patients": sum(1 for p in self.master_patient_index if "duplicate_ids" in p),
            "patients": self.master_patient_index
        }
        self._save_json(benchmark_dir / "master_patient_index.json", mpi_data)

        # Save expected results
        self._generate_expected_results(benchmark_dir)

        print(f"Data saved to {output_dir}")

    def _generate_expected_results(self, benchmark_dir: Path):
        """Generate expected results for benchmark tasks"""
        # Count diabetics
        diabetic_count = sum(1 for c in self.clinical_data["conditions"]
                           if c["code"]["coding"][0].get("code", "").startswith("E11"))

        # Count abnormal glucose
        abnormal_glucose = sum(1 for r in self.clinical_data["lab_results"]
                              if r["code"]["coding"][0].get("code") == "2345-7"
                              and r.get("interpretation", [{}])[0].get("coding", [{}])[0].get("code") in ["H", "L"])

        # Count duplicates
        duplicate_count = sum(1 for p in self.master_patient_index if "duplicate_ids" in p)

        # Count orphaned/abandoned
        orphaned_results = sum(1 for r in self.clinical_data["lab_results"] if "basedOn" not in r)
        abandoned_orders = sum(1 for o in self.clinical_data["lab_orders"]
                              if o.get("status") == "active" and "abandoned" in o.get("id", ""))

        # Count legacy ICD-9
        legacy_icd9 = sum(1 for c in self.clinical_data["conditions"]
                        if "icd-9-cm" in c["code"]["coding"][0].get("system", ""))

        expected = {
            "description": "Expected results for benchmark scoring - DO NOT give to agents",
            "generated_at": datetime.now().isoformat(),
            "task_expectations": {
                "HDH-COH-001": {"diabetic_count": diabetic_count, "count_range": [diabetic_count - 20, diabetic_count + 20]},
                "HDH-COH-002": {"abnormal_glucose_count": abnormal_glucose},
                "HDH-MPI-003": {"duplicate_count": duplicate_count, "count_range": [duplicate_count - 10, duplicate_count + 10]},
                "HDH-DQ-001": {"orphaned_count": orphaned_results, "count_range": [orphaned_results - 5, orphaned_results + 5]},
                "HDH-DQ-002": {"abandoned_count": abandoned_orders, "count_range": [abandoned_orders - 5, abandoned_orders + 5]},
                "HDH-TRM-002": {"legacy_icd9_count": legacy_icd9, "count_range": [legacy_icd9 - 10, legacy_icd9 + 10]},
            }
        }
        self._save_json(benchmark_dir / "expected_results.json", expected)

    def _save_json(self, path: Path, data: Dict):
        """Save JSON file"""
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  Saved {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate HDH-Bench data")
    parser.add_argument("--patients", "-p", type=int, default=1000, help="Number of patients")
    parser.add_argument("--output", "-o", default="data", help="Output directory")
    parser.add_argument("--use-febrl", action="store_true", help="Use FEBRL-style demographics")
    args = parser.parse_args()

    generator = HDHDataGenerator(num_patients=args.patients, use_febrl=args.use_febrl)
    generator.generate_patients()
    generator.generate_clinical_data()
    generator.save_all(Path(args.output))

    print("\n" + "=" * 60)
    print("HDH-BENCH DATA GENERATED")
    print("=" * 60)
    print(f"""
Key characteristics:

1. PATIENT ID FRAGMENTATION
   - EHR uses MRN-XXXXXX
   - LIS uses LAB-XXXXXX
   - RIS uses RAD-XXXXXX
   - Pharmacy uses RX-XXXXXX
   - PAS uses ADT-XXXXXX
   - Billing uses ACCT-XXXXXX

2. REALISTIC VARIATIONS
   - Name abbreviations (Michael -> Mike, M.)
   - Name typos (Smith -> Smyth)
   - Date format differences
   - Phone format differences
   - ~5% duplicate patient registrations

3. CLINICAL DATA
   - ICD-10 coded conditions (with some ICD-9 legacy)
   - RxNorm coded medications
   - LOINC coded lab results
   - Orphaned records for data quality tasks

4. GROUND TRUTH
   - data/benchmark/ground_truth/master_patient_index.json
   - data/benchmark/ground_truth/expected_results.json

To rebuild services:
   docker-compose build --no-cache && docker-compose up -d
""")


if __name__ == "__main__":
    main()
