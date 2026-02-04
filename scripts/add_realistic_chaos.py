#!/usr/bin/env python3
"""
Add realistic healthcare data chaos:
- Duplicate patients (same person, different MRNs)
- Orphaned records (results without orders)
- ID mismatches between systems
- Legacy/inconsistent data
- Missing links
"""
import json
import random
import uuid
from datetime import datetime, timedelta

def load_bundle(path):
    with open(path) as f:
        return json.load(f)

def save_bundle(path, bundle):
    with open(path, 'w') as f:
        json.dump(bundle, f, indent=2)

def random_datetime(days_ago_start=365, days_ago_end=0):
    days = random.randint(days_ago_end, days_ago_start)
    dt = datetime.now() - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def add_duplicate_patients(ehr_bundle):
    """Create duplicate patient records (same person, different MRN)"""
    print("Adding duplicate patients...")

    new_entries = []
    patients = [e for e in ehr_bundle['entry'] if e['resource']['resourceType'] == 'Patient']

    # 5% of patients get duplicated
    for patient in random.sample(patients, min(50, len(patients))):
        orig = patient['resource']
        dup_id = f"pat-DUP-{random.randint(10000, 99999)}"

        # Create duplicate with variations
        dup = {
            "resourceType": "Patient",
            "id": dup_id,
            "identifier": [{
                "use": "usual",
                "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
                "system": "http://hospital.example.org/mrn",
                "value": f"MRN-DUP-{random.randint(100000, 999999)}"
            }],
            "active": True,
            "gender": orig.get('gender'),
            "birthDate": orig.get('birthDate'),
        }

        # Name variations (common in duplicates)
        orig_name = orig.get('name', [{}])[0]
        variations = [
            # First name abbreviated
            lambda n: {"family": n.get('family', '').upper(), "given": [n.get('given', [''])[0][0] + '.']},
            # Last name with typo
            lambda n: {"family": n.get('family', '')[:-1] + random.choice('aeiou'), "given": n.get('given', [])},
            # Middle name missing
            lambda n: {"family": n.get('family', ''), "given": [n.get('given', [''])[0]]},
            # Name swapped
            lambda n: {"family": n.get('given', [''])[0], "given": [n.get('family', '')]},
            # ALL CAPS
            lambda n: {"family": n.get('family', '').upper(), "given": [g.upper() for g in n.get('given', [])]},
        ]
        dup['name'] = [random.choice(variations)(orig_name)]

        # Different phone number (common)
        if random.random() < 0.7:
            area = random.randint(200, 999)
            dup['telecom'] = [{"system": "phone", "value": f"({area}) {random.randint(200,999)}-{random.randint(1000,9999)}"}]

        # Different address (moved)
        if random.random() < 0.5:
            dup['address'] = [{"use": "old", "city": orig.get('address', [{}])[0].get('city', 'Unknown')}]

        new_entries.append({"resource": dup})

    ehr_bundle['entry'].extend(new_entries)
    print(f"  Added {len(new_entries)} duplicate patients")
    return ehr_bundle


def add_orphaned_lab_results(lis_bundle):
    """Add lab results that have no corresponding order (orphaned)"""
    print("Adding orphaned lab results...")

    orphaned_results = []

    for _ in range(30):
        # Create a DiagnosticReport with no basedOn reference
        report_id = f"orphan-report-{uuid.uuid4()}"

        # Random patient (may or may not exist)
        patient_id = f"pat-{random.randint(1, 1200):05d}"

        report = {
            "resourceType": "DiagnosticReport",
            "id": report_id,
            "identifier": [{
                "system": "http://hospital.example.org/reports",
                "value": f"ORPHAN-{random.randint(100000, 999999)}"
            }],
            # Note: NO basedOn reference (orphaned)
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "LAB"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "24323-8", "display": "CMP"}]},
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": random_datetime(365, 30),
            "issued": random_datetime(365, 30),
            "conclusion": "Results filed - order not found in system"
        }
        orphaned_results.append({"resource": report})

    # Also add orders that were never resulted
    for _ in range(20):
        order_id = f"abandoned-order-{uuid.uuid4()}"
        patient_id = f"pat-{random.randint(1, 1200):05d}"

        order = {
            "resourceType": "ServiceRequest",
            "id": order_id,
            "identifier": [{
                "system": "http://hospital.example.org/orders",
                "value": f"ABANDONED-{random.randint(100000, 999999)}"
            }],
            "status": "active",  # Still active but old
            "intent": "order",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "58410-2", "display": "CBC"}]},
            "subject": {"reference": f"Patient/{patient_id}"},
            "authoredOn": random_datetime(400, 100),  # Old order
            "note": [{"text": "Specimen never collected - patient left AMA"}]
        }
        orphaned_results.append({"resource": order})

    lis_bundle['entry'].extend(orphaned_results)
    print(f"  Added {len(orphaned_results)} orphaned records")
    return lis_bundle


def add_id_mismatches(pas_bundle, billing_bundle):
    """Add encounters/coverage where IDs don't match cleanly"""
    print("Adding ID mismatches between PAS and Billing...")

    # Some encounters reference patients that don't exist in billing
    encounters = [e for e in pas_bundle['entry'] if e['resource']['resourceType'] == 'Encounter']

    for enc in random.sample(encounters, min(50, len(encounters))):
        # Change patient reference to a non-standard format
        if random.random() < 0.3:
            orig_ref = enc['resource'].get('subject', {}).get('reference', '')
            if orig_ref:
                # Various ID format issues found in real systems
                variations = [
                    orig_ref.replace('Patient/', 'patient/'),  # Wrong case
                    orig_ref.replace('Patient/', 'PAT-'),  # Different prefix
                    orig_ref.replace('pat-', 'PT'),  # Abbreviated
                    orig_ref + '-MERGED',  # Merged patient indicator
                ]
                enc['resource']['subject']['reference'] = random.choice(variations)

    # Some coverage records have different patient ID formats
    coverages = [e for e in billing_bundle['entry'] if e['resource']['resourceType'] == 'Coverage']

    for cov in random.sample(coverages, min(30, len(coverages))):
        if random.random() < 0.4:
            orig_ref = cov['resource'].get('beneficiary', {}).get('reference', '')
            if orig_ref:
                # Billing system uses account numbers not patient IDs
                cov['resource']['beneficiary']['reference'] = f"Account/ACCT-{random.randint(10000, 99999)}"
                cov['resource']['beneficiary']['display'] = orig_ref  # Original in display field

    print("  Modified patient references for realism")
    return pas_bundle, billing_bundle


def add_legacy_conditions(ehr_bundle):
    """Add conditions with ICD-9 codes (legacy data)"""
    print("Adding legacy ICD-9 conditions...")

    # ICD-9 codes that would be in old records
    icd9_conditions = [
        ("250.00", "Diabetes mellitus type II"),
        ("401.9", "Hypertension NOS"),
        ("272.4", "Hyperlipidemia NEC/NOS"),
        ("496", "COPD NOS"),
        ("493.90", "Asthma NOS"),
        ("530.81", "Esophageal reflux"),
        ("724.2", "Low back pain"),
        ("311", "Depressive disorder NEC"),
        ("300.00", "Anxiety state NOS"),
        ("427.31", "Atrial fibrillation"),
    ]

    legacy_conditions = []

    for _ in range(100):
        patient_id = f"pat-{random.randint(1, 1000):05d}"
        icd9 = random.choice(icd9_conditions)

        cond = {
            "resourceType": "Condition",
            "id": f"legacy-cond-{uuid.uuid4()}",
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-9-cm",  # ICD-9!
                    "code": icd9[0],
                    "display": icd9[1]
                }],
                "text": icd9[1]
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "onsetDateTime": random_datetime(365 * 10, 365 * 3),  # 3-10 years ago
            "recordedDate": random_datetime(365 * 10, 365 * 3),
            "note": [{"text": "Migrated from legacy system - verify coding"}]
        }
        legacy_conditions.append({"resource": cond})

    ehr_bundle['entry'].extend(legacy_conditions)
    print(f"  Added {len(legacy_conditions)} legacy ICD-9 conditions")
    return ehr_bundle


def add_discontinued_meds_with_active_refills(pharmacy_bundle):
    """Add medications that are discontinued but still have refill requests"""
    print("Adding discontinued meds with orphan refills...")

    meds = [e for e in pharmacy_bundle['entry'] if e['resource']['resourceType'] == 'MedicationRequest']

    chaos_records = []

    for med in random.sample(meds, min(40, len(meds))):
        orig = med['resource']

        # Create a refill request for a discontinued med
        if orig.get('status') == 'active':
            # Discontinue the original
            orig['status'] = 'stopped'
            orig['statusReason'] = {"coding": [{"code": "DISCONT", "display": "Therapy discontinued"}]}

            # Create orphaned refill request
            refill = {
                "resourceType": "MedicationRequest",
                "id": f"orphan-refill-{uuid.uuid4()}",
                "identifier": [{
                    "system": "http://pharmacy.example.org/refills",
                    "value": f"REFILL-{random.randint(100000, 999999)}"
                }],
                "status": "active",  # Still active!
                "intent": "reflex-order",
                "medicationCodeableConcept": orig.get('medicationCodeableConcept'),
                "subject": orig.get('subject'),
                "authoredOn": random_datetime(30, 0),
                "priorPrescription": {"reference": f"MedicationRequest/{orig['id']}"},
                "note": [{"text": "AUTO-REFILL REQUEST - Original Rx discontinued, needs pharmacist review"}]
            }
            chaos_records.append({"resource": refill})

    pharmacy_bundle['entry'].extend(chaos_records)
    print(f"  Added {len(chaos_records)} orphaned refill requests")
    return pharmacy_bundle


def add_provider_attribution_issues(ehr_bundle, lis_bundle, ris_bundle):
    """Add orders with providers who no longer exist"""
    print("Adding provider attribution issues...")

    # Create some "departed" practitioners
    departed_practitioners = []
    for i in range(5):
        pract = {
            "resourceType": "Practitioner",
            "id": f"pract-DEPARTED-{i}",
            "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": f"EXPIRED-{random.randint(1000000, 9999999)}"}],
            "active": False,
            "name": [{"family": random.choice(["Smith", "Jones", "Wilson"]), "given": ["Dr."], "suffix": ["(INACTIVE)"]}],
        }
        departed_practitioners.append({"resource": pract})

    ehr_bundle['entry'].extend(departed_practitioners)

    # Update some orders to reference departed providers
    for bundle in [lis_bundle, ris_bundle]:
        orders = [e for e in bundle['entry'] if e['resource']['resourceType'] == 'ServiceRequest']
        for order in random.sample(orders, min(30, len(orders))):
            order['resource']['requester'] = {
                "reference": f"Practitioner/pract-DEPARTED-{random.randint(0, 4)}",
                "display": "Provider no longer with organization"
            }

    print("  Added departed provider references")
    return ehr_bundle, lis_bundle, ris_bundle


def add_future_dated_records(bundles):
    """Add records with future dates (data entry errors)"""
    print("Adding future-dated records (data entry errors)...")

    future_dates = [
        (datetime.now() + timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%dT%H:%M:%SZ")
        for _ in range(20)
    ]

    count = 0
    for bundle in bundles:
        for entry in random.sample(bundle['entry'], min(10, len(bundle['entry']))):
            res = entry['resource']

            # Add future dates to random date fields
            if 'authoredOn' in res and random.random() < 0.1:
                res['authoredOn'] = random.choice(future_dates)
                count += 1
            if 'effectiveDateTime' in res and random.random() < 0.1:
                res['effectiveDateTime'] = random.choice(future_dates)
                count += 1
            if 'recordedDate' in res and random.random() < 0.1:
                res['recordedDate'] = random.choice(future_dates)
                count += 1

    print(f"  Added {count} future-dated fields")


def main():
    print("Loading existing seed data...")

    ehr = load_bundle("data/seed/ehr_seed.json")
    lis = load_bundle("data/seed/lis_seed.json")
    ris = load_bundle("data/seed/ris_seed.json")
    pharmacy = load_bundle("data/seed/pharmacy_seed.json")
    pas = load_bundle("data/seed/pas_seed.json")
    billing = load_bundle("data/seed/billing_seed.json")

    print("\nAdding realistic chaos...\n")

    # Add various types of data quality issues
    ehr = add_duplicate_patients(ehr)
    ehr = add_legacy_conditions(ehr)
    lis = add_orphaned_lab_results(lis)
    pas, billing = add_id_mismatches(pas, billing)
    pharmacy = add_discontinued_meds_with_active_refills(pharmacy)
    ehr, lis, ris = add_provider_attribution_issues(ehr, lis, ris)
    add_future_dated_records([ehr, lis, ris, pharmacy, pas])

    print("\nSaving updated seed data...")

    save_bundle("data/seed/ehr_seed.json", ehr)
    save_bundle("data/seed/lis_seed.json", lis)
    save_bundle("data/seed/ris_seed.json", ris)
    save_bundle("data/seed/pharmacy_seed.json", pharmacy)
    save_bundle("data/seed/pas_seed.json", pas)
    save_bundle("data/seed/billing_seed.json", billing)

    print("\nChaos added! Rebuild containers to load new data.")
    print("  docker-compose build && docker-compose up -d")


if __name__ == "__main__":
    main()
