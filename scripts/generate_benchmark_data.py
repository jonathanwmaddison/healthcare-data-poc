#!/usr/bin/env python3
"""
Generate benchmark healthcare data with realistic fragmentation.

Key features for benchmarking agentic search/data pipelines:
1. Each system has its OWN patient ID scheme (no shared IDs)
2. Ground truth MPI maps which IDs are the same patient
3. Realistic data quality issues (duplicates, orphans, mismatches)
4. Benchmark queries with expected results
"""
import json
import random
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)  # Reproducible for benchmarking

# ID schemes per system (realistic vendor patterns)
ID_SCHEMES = {
    "ehr": lambda i: f"MRN-{100000 + i}",
    "lis": lambda i: f"LAB-{200000 + i}",
    "ris": lambda i: f"RAD-{300000 + i}",
    "pharmacy": lambda i: f"RX-{400000 + i}",
    "pas": lambda i: f"ADT-{500000 + i}",
    "billing": lambda i: f"ACCT-{600000 + i}",
}

# Demographics data
FIRST_NAMES_M = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua"]
FIRST_NAMES_F = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
STATES = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA"]

# Clinical data
ICD10_CONDITIONS = [
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential (primary) hypertension"),
    ("E78.5", "Hyperlipidemia, unspecified"),
    ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
    ("J45.909", "Unspecified asthma, uncomplicated"),
    ("K21.0", "Gastro-esophageal reflux disease with esophagitis"),
    ("M54.5", "Low back pain"),
    ("F32.9", "Major depressive disorder, single episode, unspecified"),
    ("F41.9", "Anxiety disorder, unspecified"),
    ("I48.91", "Unspecified atrial fibrillation"),
    ("N18.3", "Chronic kidney disease, stage 3"),
    ("E03.9", "Hypothyroidism, unspecified"),
    ("G47.33", "Obstructive sleep apnea"),
    ("M17.11", "Primary osteoarthritis, right knee"),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery"),
]

MEDICATIONS = [
    ("metformin", "860975", "Metformin 500 MG Oral Tablet"),
    ("lisinopril", "314076", "Lisinopril 10 MG Oral Tablet"),
    ("atorvastatin", "617311", "Atorvastatin 20 MG Oral Tablet"),
    ("amlodipine", "197361", "Amlodipine 5 MG Oral Tablet"),
    ("omeprazole", "198048", "Omeprazole 20 MG Delayed Release Oral Capsule"),
    ("levothyroxine", "966247", "Levothyroxine Sodium 50 MCG Oral Tablet"),
    ("albuterol", "745679", "Albuterol 0.083 MG/ML Inhalation Solution"),
    ("gabapentin", "310430", "Gabapentin 300 MG Oral Capsule"),
    ("sertraline", "312940", "Sertraline 50 MG Oral Tablet"),
    ("hydrochlorothiazide", "310798", "Hydrochlorothiazide 25 MG Oral Tablet"),
]

LAB_PANELS = {
    "BMP": [
        ("2345-7", "Glucose", "mg/dL", 70, 100),
        ("2160-0", "Creatinine", "mg/dL", 0.7, 1.3),
        ("3094-0", "BUN", "mg/dL", 7, 20),
        ("2951-2", "Sodium", "mmol/L", 136, 145),
        ("2823-3", "Potassium", "mmol/L", 3.5, 5.0),
        ("2075-0", "Chloride", "mmol/L", 98, 106),
        ("2028-9", "CO2", "mmol/L", 23, 29),
    ],
    "CBC": [
        ("789-8", "RBC", "M/uL", 4.5, 5.5),
        ("718-7", "Hemoglobin", "g/dL", 12.0, 17.5),
        ("4544-3", "Hematocrit", "%", 36, 50),
        ("787-2", "MCV", "fL", 80, 100),
        ("6690-2", "WBC", "K/uL", 4.5, 11.0),
        ("777-3", "Platelets", "K/uL", 150, 400),
    ],
    "LIPID": [
        ("2093-3", "Total Cholesterol", "mg/dL", 0, 200),
        ("2571-8", "Triglycerides", "mg/dL", 0, 150),
        ("2085-9", "HDL Cholesterol", "mg/dL", 40, 60),
        ("13457-7", "LDL Cholesterol", "mg/dL", 0, 100),
    ],
    "HBA1C": [
        ("4548-4", "Hemoglobin A1c", "%", 4.0, 5.6),
    ],
}

IMAGING_TYPES = [
    ("71046", "Chest X-ray, 2 views"),
    ("70553", "MRI Brain without contrast"),
    ("74177", "CT Abdomen/Pelvis with contrast"),
    ("73721", "MRI Lower Extremity without contrast"),
    ("71250", "CT Chest without contrast"),
]


class BenchmarkDataGenerator:
    def __init__(self, num_patients=1000):
        self.num_patients = num_patients
        self.master_patient_index = []  # Ground truth
        self.patients_by_system = {sys: [] for sys in ID_SCHEMES.keys()}
        self.benchmark_queries = []

    def generate_patient_demographics(self, patient_num):
        """Generate base patient demographics"""
        gender = random.choice(["male", "female"])
        first_names = FIRST_NAMES_M if gender == "male" else FIRST_NAMES_F

        birth_year = random.randint(1940, 2005)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)

        city_idx = random.randint(0, len(CITIES) - 1)

        return {
            "first_name": random.choice(first_names),
            "last_name": random.choice(LAST_NAMES),
            "middle_name": random.choice(first_names) if random.random() < 0.7 else None,
            "gender": gender,
            "birth_date": f"{birth_year}-{birth_month:02d}-{birth_day:02d}",
            "ssn_last4": f"{random.randint(1000, 9999)}",
            "phone": f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
            "city": CITIES[city_idx],
            "state": STATES[city_idx],
            "zip": f"{random.randint(10000, 99999)}",
        }

    def vary_demographics(self, base, system):
        """Create realistic variations per system"""
        varied = base.copy()

        # Name variations (common across systems)
        if random.random() < 0.3:
            # Abbreviate first name
            varied["first_name"] = base["first_name"][0] + "."
        if random.random() < 0.2:
            # ALL CAPS (common in older systems)
            varied["first_name"] = base["first_name"].upper()
            varied["last_name"] = base["last_name"].upper()
        if random.random() < 0.1:
            # Typo in last name
            ln = list(base["last_name"])
            if len(ln) > 3:
                ln[random.randint(1, len(ln)-2)] = random.choice("aeiou")
            varied["last_name"] = "".join(ln)
        if random.random() < 0.15:
            # Missing middle name
            varied["middle_name"] = None

        # Date format variations
        if system == "lis":
            # MM/DD/YYYY format
            parts = base["birth_date"].split("-")
            varied["birth_date"] = f"{parts[1]}/{parts[2]}/{parts[0]}"
        elif system == "billing":
            # MMDDYYYY format
            parts = base["birth_date"].split("-")
            varied["birth_date"] = f"{parts[1]}{parts[2]}{parts[0]}"

        # Phone format variations
        if system in ["lis", "ris"]:
            # No formatting
            varied["phone"] = base["phone"].replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
        elif system == "billing":
            # Different format
            digits = base["phone"].replace("(", "").replace(")", "").replace(" ", "").replace("-", "")
            varied["phone"] = f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"

        return varied

    def create_fhir_patient(self, patient_id, demographics, system):
        """Create FHIR Patient resource with system-specific ID"""
        name = {"family": demographics["last_name"], "given": [demographics["first_name"]]}
        if demographics["middle_name"]:
            name["given"].append(demographics["middle_name"])

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
            "birthDate": demographics["birth_date"] if "-" in demographics["birth_date"] else None,
            "telecom": [{"system": "phone", "value": demographics["phone"]}],
            "address": [{
                "city": demographics["city"],
                "state": demographics["state"],
                "postalCode": demographics["zip"]
            }]
        }

        # Some systems store DOB differently
        if "-" not in demographics["birth_date"]:
            patient["extension"] = [{
                "url": "http://hospital.example.org/fhir/StructureDefinition/birth-date-string",
                "valueString": demographics["birth_date"]
            }]

        return patient

    def generate_all_patients(self):
        """Generate patients across all systems with ground truth mapping"""
        print(f"Generating {self.num_patients} patients across {len(ID_SCHEMES)} systems...")

        for i in range(self.num_patients):
            base_demographics = self.generate_patient_demographics(i)

            # Generate system-specific IDs
            system_ids = {}
            for system, id_func in ID_SCHEMES.items():
                system_ids[system] = id_func(i)

            # Store ground truth
            mpi_entry = {
                "canonical_id": f"patient-{i:05d}",
                "demographics": base_demographics,
                "system_ids": system_ids,
            }
            self.master_patient_index.append(mpi_entry)

            # Create patient in each system with variations
            for system, patient_id in system_ids.items():
                varied_demo = self.vary_demographics(base_demographics, system)
                patient = self.create_fhir_patient(patient_id, varied_demo, system)
                self.patients_by_system[system].append(patient)

        # Add duplicate patients (same person, registered twice)
        self._add_duplicates()

        print(f"  Created {sum(len(p) for p in self.patients_by_system.values())} patient records")

    def _add_duplicates(self):
        """Add duplicate patient registrations (common MPI problem)"""
        num_duplicates = int(self.num_patients * 0.05)  # 5% duplicates

        for _ in range(num_duplicates):
            # Pick a random patient to duplicate
            orig_idx = random.randint(0, self.num_patients - 1)
            orig_entry = self.master_patient_index[orig_idx]

            # Pick a system to have the duplicate
            system = random.choice(list(ID_SCHEMES.keys()))

            # Create new ID
            dup_id = f"DUP-{random.randint(700000, 799999)}"

            # Varied demographics (this is why duplicates happen)
            varied = self.vary_demographics(orig_entry["demographics"], system)
            # More aggressive variations for duplicates
            if random.random() < 0.5:
                varied["first_name"] = orig_entry["demographics"]["first_name"][0] + "."
            if random.random() < 0.3:
                varied["middle_name"] = None

            patient = self.create_fhir_patient(dup_id, varied, system)
            self.patients_by_system[system].append(patient)

            # Record in ground truth
            if "duplicate_ids" not in orig_entry:
                orig_entry["duplicate_ids"] = []
            orig_entry["duplicate_ids"].append({"system": system, "id": dup_id})

    def generate_clinical_data(self):
        """Generate conditions, medications, labs, imaging for patients"""
        print("Generating clinical data...")

        self.conditions = []  # EHR
        self.medications = []  # Pharmacy
        self.lab_orders = []  # LIS
        self.lab_results = []  # LIS
        self.imaging_orders = []  # RIS
        self.encounters = []  # PAS
        self.claims = []  # Billing

        for mpi_entry in self.master_patient_index:
            self._generate_patient_clinical_data(mpi_entry)

        # Add orphaned records (results without orders, etc.)
        self._add_orphaned_records()

        print(f"  Conditions: {len(self.conditions)}")
        print(f"  Medications: {len(self.medications)}")
        print(f"  Lab Orders: {len(self.lab_orders)}, Results: {len(self.lab_results)}")
        print(f"  Imaging Orders: {len(self.imaging_orders)}")
        print(f"  Encounters: {len(self.encounters)}")
        print(f"  Claims: {len(self.claims)}")

    def _generate_patient_clinical_data(self, mpi_entry):
        """Generate clinical data for one patient"""
        ehr_id = mpi_entry["system_ids"]["ehr"]
        lis_id = mpi_entry["system_ids"]["lis"]
        ris_id = mpi_entry["system_ids"]["ris"]
        pharmacy_id = mpi_entry["system_ids"]["pharmacy"]
        pas_id = mpi_entry["system_ids"]["pas"]
        billing_id = mpi_entry["system_ids"]["billing"]

        # Store clinical data mapping in ground truth
        mpi_entry["clinical_data"] = {
            "condition_ids": [],
            "medication_ids": [],
            "lab_order_ids": [],
            "imaging_order_ids": [],
            "encounter_ids": [],
            "claim_ids": [],
        }

        # Conditions (1-5 per patient)
        num_conditions = random.randint(1, 5)
        patient_conditions = random.sample(ICD10_CONDITIONS, num_conditions)

        for icd_code, display in patient_conditions:
            cond_id = f"cond-{uuid.uuid4().hex[:8]}"
            condition = {
                "resourceType": "Condition",
                "id": cond_id,
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": icd_code, "display": display}],
                    "text": display
                },
                "subject": {"reference": f"Patient/{ehr_id}"},
                "onsetDateTime": self._random_date(365*5, 30),
            }
            self.conditions.append(condition)
            mpi_entry["clinical_data"]["condition_ids"].append(cond_id)

        # Medications (0-4 per patient)
        num_meds = random.randint(0, 4)
        patient_meds = random.sample(MEDICATIONS, num_meds)

        for med_name, rxcui, display in patient_meds:
            med_id = f"med-{uuid.uuid4().hex[:8]}"
            medication = {
                "resourceType": "MedicationRequest",
                "id": med_id,
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {
                    "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxcui, "display": display}],
                    "text": display
                },
                "subject": {"reference": f"Patient/{pharmacy_id}"},  # Pharmacy system ID!
                "authoredOn": self._random_date(365, 0),
                "dosageInstruction": [{"text": "Take as directed"}],
            }
            self.medications.append(medication)
            mpi_entry["clinical_data"]["medication_ids"].append(med_id)

        # Lab orders and results (0-3 panels per patient)
        num_labs = random.randint(0, 3)
        for _ in range(num_labs):
            panel_name = random.choice(list(LAB_PANELS.keys()))
            order_id = f"labord-{uuid.uuid4().hex[:8]}"

            order = {
                "resourceType": "ServiceRequest",
                "id": order_id,
                "status": "completed",
                "intent": "order",
                "code": {"coding": [{"system": "http://loinc.org", "code": panel_name, "display": panel_name}]},
                "subject": {"reference": f"Patient/{lis_id}"},  # LIS system ID!
                "authoredOn": self._random_date(180, 0),
            }
            self.lab_orders.append(order)
            mpi_entry["clinical_data"]["lab_order_ids"].append(order_id)

            # Generate results for each test in panel
            for loinc, test_name, unit, low, high in LAB_PANELS[panel_name]:
                result_id = f"labres-{uuid.uuid4().hex[:8]}"

                # Generate value (80% normal, 20% abnormal)
                if random.random() < 0.8:
                    value = round(random.uniform(low, high), 1)
                else:
                    # Abnormal
                    if random.random() < 0.5:
                        value = round(random.uniform(low * 0.5, low * 0.95), 1)
                    else:
                        value = round(random.uniform(high * 1.05, high * 1.5), 1)

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
                    "effectiveDateTime": self._random_date(180, 0),
                    "valueQuantity": {"value": value, "unit": unit},
                    "referenceRange": [{"low": {"value": low}, "high": {"value": high}}],
                    "interpretation": [{"coding": [{"code": interpretation}]}],
                }
                self.lab_results.append(result)

        # Imaging orders (0-2 per patient)
        num_imaging = random.randint(0, 2)
        for _ in range(num_imaging):
            cpt, description = random.choice(IMAGING_TYPES)
            order_id = f"imgord-{uuid.uuid4().hex[:8]}"

            order = {
                "resourceType": "ServiceRequest",
                "id": order_id,
                "status": "completed",
                "intent": "order",
                "code": {"coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": cpt, "display": description}]},
                "subject": {"reference": f"Patient/{ris_id}"},  # RIS system ID!
                "authoredOn": self._random_date(365, 0),
            }
            self.imaging_orders.append(order)
            mpi_entry["clinical_data"]["imaging_order_ids"].append(order_id)

        # Encounters (1-5 per patient)
        num_encounters = random.randint(1, 5)
        for _ in range(num_encounters):
            enc_id = f"enc-{uuid.uuid4().hex[:8]}"
            enc_type = random.choice(["AMB", "EMER", "IMP", "OBSENC"])

            encounter = {
                "resourceType": "Encounter",
                "id": enc_id,
                "status": "finished",
                "class": {"code": enc_type},
                "subject": {"reference": f"Patient/{pas_id}"},  # PAS system ID!
                "period": {
                    "start": self._random_date(365, 30),
                    "end": self._random_date(29, 0),
                }
            }
            self.encounters.append(encounter)
            mpi_entry["clinical_data"]["encounter_ids"].append(enc_id)

        # Claims (1 per encounter, roughly)
        for enc_id in mpi_entry["clinical_data"]["encounter_ids"]:
            if random.random() < 0.9:  # 90% have claims
                claim_id = f"claim-{uuid.uuid4().hex[:8]}"

                claim = {
                    "resourceType": "Claim",
                    "id": claim_id,
                    "status": "active",
                    "type": {"coding": [{"code": "institutional"}]},
                    "patient": {"reference": f"Patient/{billing_id}"},  # Billing system ID!
                    "created": self._random_date(180, 0),
                    "provider": {"reference": "Organization/hospital"},
                    "total": {"value": round(random.uniform(100, 5000), 2), "currency": "USD"},
                }
                self.claims.append(claim)
                mpi_entry["clinical_data"]["claim_ids"].append(claim_id)

    def _add_orphaned_records(self):
        """Add orphaned records for realism"""
        # Lab results without orders
        for _ in range(30):
            result_id = f"orphan-res-{uuid.uuid4().hex[:8]}"
            lis_id = f"LAB-{random.randint(200000, 200999)}"  # May or may not exist

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
            self.lab_results.append(result)

        # Orders that were never resulted
        for _ in range(20):
            order_id = f"abandoned-{uuid.uuid4().hex[:8]}"
            lis_id = f"LAB-{random.randint(200000, 200999)}"

            order = {
                "resourceType": "ServiceRequest",
                "id": order_id,
                "status": "active",  # Still active but old!
                "intent": "order",
                "code": {"coding": [{"system": "http://loinc.org", "code": "CBC", "display": "CBC"}]},
                "subject": {"reference": f"Patient/{lis_id}"},
                "authoredOn": self._random_date(400, 100),  # Very old
                "note": [{"text": "ABANDONED: Specimen never collected"}],
            }
            self.lab_orders.append(order)

    def _random_date(self, days_ago_max, days_ago_min):
        """Generate random date in range"""
        days = random.randint(days_ago_min, days_ago_max)
        dt = datetime.now() - timedelta(days=days)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def generate_benchmark_queries(self):
        """Generate benchmark queries with expected results"""
        print("Generating benchmark queries...")

        # Query 1: Find all data for a specific patient
        sample_patient = self.master_patient_index[42]
        self.benchmark_queries.append({
            "id": "Q001",
            "description": "Find all clinical data for patient with EHR MRN MRN-100042",
            "difficulty": "medium",
            "hint": "Patient may have different IDs in each system",
            "expected_result": {
                "patient_ids": sample_patient["system_ids"],
                "num_conditions": len(sample_patient["clinical_data"]["condition_ids"]),
                "num_medications": len(sample_patient["clinical_data"]["medication_ids"]),
                "num_lab_orders": len(sample_patient["clinical_data"]["lab_order_ids"]),
                "num_encounters": len(sample_patient["clinical_data"]["encounter_ids"]),
            }
        })

        # Query 2: Find all diabetic patients
        diabetic_patients = [
            p for p in self.master_patient_index
            if any(c in str(p.get("clinical_data", {}).get("condition_ids", []))
                   for c in ["E11", "E10"])  # Simplified - actual would check conditions
        ]
        # Count actual diabetics from conditions
        diabetic_ehr_ids = set()
        for cond in self.conditions:
            code = cond.get("code", {}).get("coding", [{}])[0].get("code", "")
            if code.startswith("E11") or code.startswith("E10"):
                patient_ref = cond.get("subject", {}).get("reference", "")
                diabetic_ehr_ids.add(patient_ref.replace("Patient/", ""))

        self.benchmark_queries.append({
            "id": "Q002",
            "description": "Find all patients with Type 2 Diabetes (ICD-10 E11.x)",
            "difficulty": "easy",
            "hint": "Query EHR conditions for ICD-10 codes starting with E11",
            "expected_result": {
                "count": len(diabetic_ehr_ids),
                "sample_ids": list(diabetic_ehr_ids)[:5],
            }
        })

        # Query 3: Find patients with abnormal glucose
        abnormal_glucose_patients = set()
        for result in self.lab_results:
            code = result.get("code", {}).get("coding", [{}])[0].get("code", "")
            if code == "2345-7":  # Glucose LOINC
                interp = result.get("interpretation", [{}])[0].get("coding", [{}])[0].get("code", "")
                if interp in ["H", "L"]:
                    patient_ref = result.get("subject", {}).get("reference", "")
                    abnormal_glucose_patients.add(patient_ref.replace("Patient/", ""))

        self.benchmark_queries.append({
            "id": "Q003",
            "description": "Find all patients with abnormal glucose results",
            "difficulty": "medium",
            "hint": "Query LIS for Observation with LOINC 2345-7 and interpretation H or L",
            "expected_result": {
                "count": len(abnormal_glucose_patients),
                "sample_ids": list(abnormal_glucose_patients)[:5],
            }
        })

        # Query 4: Find duplicate patient records
        duplicates = [p for p in self.master_patient_index if "duplicate_ids" in p]
        self.benchmark_queries.append({
            "id": "Q004",
            "description": "Identify duplicate patient records (same person, multiple MRNs)",
            "difficulty": "hard",
            "hint": "Look for patients with similar demographics but different IDs",
            "expected_result": {
                "num_patients_with_duplicates": len(duplicates),
                "sample": [
                    {
                        "canonical": d["canonical_id"],
                        "primary_ids": d["system_ids"],
                        "duplicate_ids": d["duplicate_ids"]
                    } for d in duplicates[:3]
                ]
            }
        })

        # Query 5: Cross-system cohort - diabetics on metformin with recent A1C
        self.benchmark_queries.append({
            "id": "Q005",
            "description": "Find diabetic patients currently on metformin who have had an HbA1c test in the last 6 months",
            "difficulty": "hard",
            "hint": "Requires joining data from EHR (conditions), Pharmacy (medications), and LIS (lab results). Patient IDs differ across systems.",
            "expected_result": {
                "description": "Requires patient matching across systems - ground truth in MPI",
            }
        })

        # Query 6: Find orphaned records
        orphaned_results = [r for r in self.lab_results if "basedOn" not in r]
        abandoned_orders = [o for o in self.lab_orders if o.get("status") == "active" and "abandoned" in o.get("id", "")]

        self.benchmark_queries.append({
            "id": "Q006",
            "description": "Find data quality issues: orphaned lab results (no order) and abandoned orders (no result)",
            "difficulty": "medium",
            "hint": "Check for Observations without basedOn and ServiceRequests with old authoredOn but status=active",
            "expected_result": {
                "orphaned_results": len(orphaned_results),
                "abandoned_orders": len(abandoned_orders),
            }
        })

        print(f"  Created {len(self.benchmark_queries)} benchmark queries")

    def save_all(self, output_dir="data"):
        """Save all data to files"""
        output_path = Path(output_dir)
        seed_path = output_path / "seed"
        benchmark_path = output_path / "benchmark"

        seed_path.mkdir(parents=True, exist_ok=True)
        benchmark_path.mkdir(parents=True, exist_ok=True)

        # Save system-specific bundles
        print("Saving seed data bundles...")

        # EHR bundle (patients + conditions)
        ehr_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["ehr"]] +
                     [{"resource": c} for c in self.conditions]
        }
        self._save_json(seed_path / "ehr_seed.json", ehr_bundle)

        # LIS bundle (patients + orders + results)
        lis_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["lis"]] +
                     [{"resource": o} for o in self.lab_orders] +
                     [{"resource": r} for r in self.lab_results]
        }
        self._save_json(seed_path / "lis_seed.json", lis_bundle)

        # RIS bundle (patients + imaging orders)
        ris_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["ris"]] +
                     [{"resource": o} for o in self.imaging_orders]
        }
        self._save_json(seed_path / "ris_seed.json", ris_bundle)

        # Pharmacy bundle (patients + medications)
        pharmacy_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["pharmacy"]] +
                     [{"resource": m} for m in self.medications]
        }
        self._save_json(seed_path / "pharmacy_seed.json", pharmacy_bundle)

        # PAS bundle (patients + encounters)
        pas_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["pas"]] +
                     [{"resource": e} for e in self.encounters]
        }
        self._save_json(seed_path / "pas_seed.json", pas_bundle)

        # Billing bundle (patients + claims)
        billing_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": p} for p in self.patients_by_system["billing"]] +
                     [{"resource": c} for c in self.claims]
        }
        self._save_json(seed_path / "billing_seed.json", billing_bundle)

        # Save ground truth (MPI)
        print("Saving benchmark ground truth...")
        self._save_json(benchmark_path / "master_patient_index.json", {
            "description": "Ground truth patient identity mapping across systems",
            "total_patients": len(self.master_patient_index),
            "patients": self.master_patient_index
        })

        # Save benchmark queries
        self._save_json(benchmark_path / "benchmark_queries.json", {
            "description": "Benchmark queries for testing agentic search/data pipelines",
            "queries": self.benchmark_queries
        })

        # Save API documentation for agents
        self._save_json(benchmark_path / "api_catalog.json", {
            "description": "Available APIs for querying healthcare data",
            "systems": {
                "ehr": {
                    "name": "Electronic Health Record",
                    "base_url": "http://localhost:8001",
                    "resources": ["Patient", "Condition"],
                    "patient_id_prefix": "MRN-",
                    "example_query": "GET /Patient?_id=MRN-100001",
                },
                "lis": {
                    "name": "Laboratory Information System",
                    "base_url": "http://localhost:8002",
                    "resources": ["Patient", "ServiceRequest", "Observation"],
                    "patient_id_prefix": "LAB-",
                    "example_query": "GET /Observation?subject=Patient/LAB-200001",
                },
                "ris": {
                    "name": "Radiology Information System",
                    "base_url": "http://localhost:8003",
                    "resources": ["Patient", "ServiceRequest", "ImagingStudy"],
                    "patient_id_prefix": "RAD-",
                },
                "pharmacy": {
                    "name": "Pharmacy System",
                    "base_url": "http://localhost:8005",
                    "resources": ["Patient", "MedicationRequest"],
                    "patient_id_prefix": "RX-",
                },
                "pas": {
                    "name": "Patient Administration System",
                    "base_url": "http://localhost:8006",
                    "resources": ["Patient", "Encounter"],
                    "patient_id_prefix": "ADT-",
                },
                "billing": {
                    "name": "Billing System",
                    "base_url": "http://localhost:8007",
                    "resources": ["Patient", "Claim", "Coverage"],
                    "patient_id_prefix": "ACCT-",
                },
            },
            "note": "Each system has its own patient ID scheme. The same physical patient will have different IDs in each system."
        })

        print(f"\nData saved to {output_path}/")
        print(f"  Seed data: {seed_path}/")
        print(f"  Benchmark: {benchmark_path}/")

    def _save_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  Saved {path}")


def main():
    generator = BenchmarkDataGenerator(num_patients=1000)
    generator.generate_all_patients()
    generator.generate_clinical_data()
    generator.generate_benchmark_queries()
    generator.save_all()

    print("\n" + "="*60)
    print("BENCHMARK DATA GENERATED")
    print("="*60)
    print("""
Key characteristics for benchmarking agentic search:

1. PATIENT ID FRAGMENTATION
   - EHR uses MRN-XXXXXX
   - LIS uses LAB-XXXXXX
   - RIS uses RAD-XXXXXX
   - Pharmacy uses RX-XXXXXX
   - PAS uses ADT-XXXXXX
   - Billing uses ACCT-XXXXXX

   Same patient = different ID in each system!

2. DEMOGRAPHIC VARIATIONS
   - Name spelling variations across systems
   - Date format differences (YYYY-MM-DD vs MM/DD/YYYY)
   - Phone format differences

3. DATA QUALITY ISSUES
   - ~5% duplicate patient registrations
   - Orphaned lab results (no order)
   - Abandoned orders (no result)

4. BENCHMARK QUERIES (data/benchmark/benchmark_queries.json)
   - Q001: Find all data for specific patient
   - Q002: Find all diabetic patients
   - Q003: Find patients with abnormal glucose
   - Q004: Identify duplicate records
   - Q005: Cross-system cohort query
   - Q006: Find data quality issues

5. GROUND TRUTH (data/benchmark/master_patient_index.json)
   - Maps canonical patient ID to all system IDs
   - Use to score agent accuracy

To rebuild services with new data:
   docker-compose build --no-cache && docker-compose up -d
""")


if __name__ == "__main__":
    main()
