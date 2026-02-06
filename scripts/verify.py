#!/usr/bin/env python3
"""
Verify ground truth by replaying task queries against seed data.

Loads the generated seed JSON files (same data the FHIR services load) and
replays each task's query logic against them. Asserts results match
ground_truth.json exactly.

Usage:
    python scripts/verify.py
    python scripts/verify.py --data-dir data
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set


def load_bundle(path: Path) -> List[Dict]:
    """Load a FHIR bundle and return list of resources."""
    with open(path) as f:
        bundle = json.load(f)
    return [entry["resource"] for entry in bundle.get("entry", [])]


def resources_by_type(resources: List[Dict]) -> Dict[str, List[Dict]]:
    """Group resources by resourceType."""
    by_type: Dict[str, List[Dict]] = {}
    for r in resources:
        rt = r.get("resourceType", "Unknown")
        by_type.setdefault(rt, []).append(r)
    return by_type


class GroundTruthVerifier:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.seed_dir = data_dir / "seed"
        self.gt_dir = data_dir / "benchmark" / "ground_truth"

        # Load ground truth
        with open(self.gt_dir / "ground_truth.json") as f:
            self.gt = json.load(f)

        with open(self.gt_dir / "master_patient_index.json") as f:
            self.mpi = json.load(f)

        # Load seed data
        self.ehr = resources_by_type(load_bundle(self.seed_dir / "ehr_seed.json"))
        self.lis = resources_by_type(load_bundle(self.seed_dir / "lis_seed.json"))
        self.pharmacy = resources_by_type(load_bundle(self.seed_dir / "pharmacy_seed.json"))
        self.pas = resources_by_type(load_bundle(self.seed_dir / "pas_seed.json"))

        # Build MPI lookup
        self.mpi_by_canonical = {p["canonical_id"]: p for p in self.mpi["patients"]}
        self.mpi_by_ehr = {p["system_ids"]["ehr"]: p for p in self.mpi["patients"]}
        self.mpi_by_lis = {p["system_ids"]["lis"]: p for p in self.mpi["patients"]}
        self.mpi_by_pharmacy = {p["system_ids"]["pharmacy"]: p for p in self.mpi["patients"]}

        self.passed = 0
        self.failed = 0

    def _assert_eq(self, task_id: str, label: str, actual, expected):
        if actual == expected:
            return True
        print(f"  FAIL [{task_id}] {label}: expected {expected}, got {actual}")
        return False

    def verify_all(self):
        tasks = self.gt["tasks"]
        for task_id in sorted(tasks.keys()):
            method = getattr(self, f"verify_{task_id.lower()}", None)
            if method:
                ok = method(tasks[task_id])
                if ok:
                    self.passed += 1
                    print(f"  PASS {task_id}")
                else:
                    self.failed += 1
            else:
                print(f"  SKIP {task_id} (no verifier)")

    def verify_t01(self, gt_task: Dict) -> bool:
        """T01: Single-system patient lookup."""
        ehr_id = gt_task["patient_ehr_id"]
        expected = gt_task["expected"]

        # Find patient in EHR seed
        patients = [p for p in self.ehr.get("Patient", []) if p["id"] == ehr_id]
        if not patients:
            print(f"  FAIL [T01] patient {ehr_id} not found in EHR seed")
            return False

        # Find conditions for this patient
        cond_ids = sorted([
            c["id"] for c in self.ehr.get("Condition", [])
            if c["subject"]["reference"] == f"Patient/{ehr_id}"
            and c["code"]["coding"][0].get("system") == "http://hl7.org/fhir/sid/icd-10-cm"
        ])
        expected_cond_ids = sorted(expected["condition_ids"])
        return self._assert_eq("T01", "condition_ids", cond_ids, expected_cond_ids)

    def verify_t02(self, gt_task: Dict) -> bool:
        """T02: Cross-system match (EHR + Pharmacy)."""
        ehr_id = gt_task["patient_ehr_id"]
        expected = gt_task["expected"]

        # Verify EHR ID
        ok = self._assert_eq("T02", "ehr_id", ehr_id, expected["ehr_id"])

        # Find via MPI
        mpi_entry = self.mpi_by_ehr.get(ehr_id)
        if not mpi_entry:
            print(f"  FAIL [T02] patient {ehr_id} not in MPI")
            return False

        ok = ok and self._assert_eq("T02", "pharmacy_id",
                                     mpi_entry["system_ids"]["pharmacy"], expected["pharmacy_id"])

        # Verify conditions
        cond_ids = sorted([
            c["id"] for c in self.ehr.get("Condition", [])
            if c["subject"]["reference"] == f"Patient/{ehr_id}"
            and c["code"]["coding"][0].get("system") == "http://hl7.org/fhir/sid/icd-10-cm"
        ])
        ok = ok and self._assert_eq("T02", "condition_ids", cond_ids, sorted(expected["condition_ids"]))

        # Verify medications
        pharm_id = mpi_entry["system_ids"]["pharmacy"]
        med_ids = sorted([
            m["id"] for m in self.pharmacy.get("MedicationRequest", [])
            if m["subject"]["reference"] == f"Patient/{pharm_id}"
        ])
        ok = ok and self._assert_eq("T02", "medication_ids", med_ids, sorted(expected["medication_ids"]))
        return ok

    def verify_t03(self, gt_task: Dict) -> bool:
        """T03: Full 360 match (all 6 systems)."""
        ehr_id = gt_task["patient_ehr_id"]
        mpi_entry = self.mpi_by_ehr.get(ehr_id)
        if not mpi_entry:
            print(f"  FAIL [T03] patient {ehr_id} not in MPI")
            return False
        return self._assert_eq("T03", "system_ids",
                                mpi_entry["system_ids"], gt_task["expected"]["system_ids"])

    def verify_t04(self, gt_task: Dict) -> bool:
        """T04: Diabetic patients (E11.9)."""
        # Find all patients with E11.9 conditions in EHR
        diabetic_ehr_ids = set()
        for c in self.ehr.get("Condition", []):
            code = c["code"]["coding"][0].get("code", "")
            system = c["code"]["coding"][0].get("system", "")
            if code == "E11.9" and system == "http://hl7.org/fhir/sid/icd-10-cm":
                patient_ref = c["subject"]["reference"]
                ehr_id = patient_ref.split("/")[-1]
                diabetic_ehr_ids.add(ehr_id)

        # Map to canonical IDs via MPI
        canonical_ids = set()
        for ehr_id in diabetic_ehr_ids:
            entry = self.mpi_by_ehr.get(ehr_id)
            if entry:
                canonical_ids.add(entry["canonical_id"])

        expected_canonical = set(gt_task["expected_ids"])
        ok = self._assert_eq("T04", "canonical_count", len(canonical_ids), len(expected_canonical))
        ok = ok and self._assert_eq("T04", "canonical_ids", sorted(canonical_ids), sorted(expected_canonical))

        expected_ehr = set(gt_task["expected_ehr_ids"])
        ok = ok and self._assert_eq("T04", "ehr_ids", sorted(diabetic_ehr_ids), sorted(expected_ehr))
        return ok

    def verify_t05(self, gt_task: Dict) -> bool:
        """T05: HbA1c lab results (LOINC 4548-4)."""
        hba1c_lis_ids = set()
        for obs in self.lis.get("Observation", []):
            code = obs["code"]["coding"][0].get("code", "")
            if code == "4548-4":
                patient_ref = obs["subject"]["reference"]
                lis_id = patient_ref.split("/")[-1]
                hba1c_lis_ids.add(lis_id)

        canonical_ids = set()
        for lis_id in hba1c_lis_ids:
            entry = self.mpi_by_lis.get(lis_id)
            if entry:
                canonical_ids.add(entry["canonical_id"])

        expected_canonical = set(gt_task["expected_ids"])
        ok = self._assert_eq("T05", "canonical_count", len(canonical_ids), len(expected_canonical))
        ok = ok and self._assert_eq("T05", "canonical_ids", sorted(canonical_ids), sorted(expected_canonical))
        return ok

    def verify_t06(self, gt_task: Dict) -> bool:
        """T06: Active metformin (RxNorm 860975)."""
        metformin_pharm_ids = set()
        for med in self.pharmacy.get("MedicationRequest", []):
            code = med["medicationCodeableConcept"]["coding"][0].get("code", "")
            status = med.get("status", "")
            if code == "860975" and status == "active":
                patient_ref = med["subject"]["reference"]
                pharm_id = patient_ref.split("/")[-1]
                metformin_pharm_ids.add(pharm_id)

        canonical_ids = set()
        for pharm_id in metformin_pharm_ids:
            entry = self.mpi_by_pharmacy.get(pharm_id)
            if entry:
                canonical_ids.add(entry["canonical_id"])

        expected_canonical = set(gt_task["expected_ids"])
        ok = self._assert_eq("T06", "canonical_count", len(canonical_ids), len(expected_canonical))
        ok = ok and self._assert_eq("T06", "canonical_ids", sorted(canonical_ids), sorted(expected_canonical))
        return ok

    def verify_t07(self, gt_task: Dict) -> bool:
        """T07: Diabetics on metformin (intersection)."""
        # Recompute T04 canonical IDs
        diabetic_canonical = set()
        for c in self.ehr.get("Condition", []):
            code = c["code"]["coding"][0].get("code", "")
            system = c["code"]["coding"][0].get("system", "")
            if code == "E11.9" and system == "http://hl7.org/fhir/sid/icd-10-cm":
                ehr_id = c["subject"]["reference"].split("/")[-1]
                entry = self.mpi_by_ehr.get(ehr_id)
                if entry:
                    diabetic_canonical.add(entry["canonical_id"])

        # Recompute T06 canonical IDs
        metformin_canonical = set()
        for med in self.pharmacy.get("MedicationRequest", []):
            code = med["medicationCodeableConcept"]["coding"][0].get("code", "")
            if code == "860975" and med.get("status") == "active":
                pharm_id = med["subject"]["reference"].split("/")[-1]
                entry = self.mpi_by_pharmacy.get(pharm_id)
                if entry:
                    metformin_canonical.add(entry["canonical_id"])

        intersection = diabetic_canonical & metformin_canonical

        expected_pairs = gt_task["expected_pairs"]
        expected_canonical = {p["canonical_id"] for p in expected_pairs}

        ok = self._assert_eq("T07", "count", len(intersection), len(expected_canonical))
        ok = ok and self._assert_eq("T07", "canonical_ids", sorted(intersection), sorted(expected_canonical))
        return ok

    def verify_t08(self, gt_task: Dict) -> bool:
        """T08: Diabetics + metformin + HbA1c (triple intersection)."""
        diabetic_canonical = set()
        for c in self.ehr.get("Condition", []):
            code = c["code"]["coding"][0].get("code", "")
            system = c["code"]["coding"][0].get("system", "")
            if code == "E11.9" and system == "http://hl7.org/fhir/sid/icd-10-cm":
                ehr_id = c["subject"]["reference"].split("/")[-1]
                entry = self.mpi_by_ehr.get(ehr_id)
                if entry:
                    diabetic_canonical.add(entry["canonical_id"])

        metformin_canonical = set()
        for med in self.pharmacy.get("MedicationRequest", []):
            code = med["medicationCodeableConcept"]["coding"][0].get("code", "")
            if code == "860975" and med.get("status") == "active":
                pharm_id = med["subject"]["reference"].split("/")[-1]
                entry = self.mpi_by_pharmacy.get(pharm_id)
                if entry:
                    metformin_canonical.add(entry["canonical_id"])

        hba1c_canonical = set()
        for obs in self.lis.get("Observation", []):
            code = obs["code"]["coding"][0].get("code", "")
            if code == "4548-4":
                lis_id = obs["subject"]["reference"].split("/")[-1]
                entry = self.mpi_by_lis.get(lis_id)
                if entry:
                    hba1c_canonical.add(entry["canonical_id"])

        intersection = diabetic_canonical & metformin_canonical & hba1c_canonical

        expected_triples = gt_task["expected_triples"]
        expected_canonical = {t["canonical_id"] for t in expected_triples}

        ok = self._assert_eq("T08", "count", len(intersection), len(expected_canonical))
        ok = ok and self._assert_eq("T08", "canonical_ids", sorted(intersection), sorted(expected_canonical))
        return ok

    def verify_t09(self, gt_task: Dict) -> bool:
        """T09: Complete record for one patient."""
        ehr_id = gt_task["patient_ehr_id"]
        expected = gt_task["expected"]
        mpi_entry = self.mpi_by_ehr.get(ehr_id)
        if not mpi_entry:
            print(f"  FAIL [T09] patient {ehr_id} not in MPI")
            return False

        ok = self._assert_eq("T09", "system_ids", mpi_entry["system_ids"], expected["system_ids"])

        # Verify condition IDs
        cond_ids = sorted([
            c["id"] for c in self.ehr.get("Condition", [])
            if c["subject"]["reference"] == f"Patient/{ehr_id}"
            and c["code"]["coding"][0].get("system") == "http://hl7.org/fhir/sid/icd-10-cm"
        ])
        ok = ok and self._assert_eq("T09", "condition_ids", cond_ids, sorted(expected["condition_ids"]))

        # Verify medication IDs
        pharm_id = mpi_entry["system_ids"]["pharmacy"]
        med_ids = sorted([
            m["id"] for m in self.pharmacy.get("MedicationRequest", [])
            if m["subject"]["reference"] == f"Patient/{pharm_id}"
        ])
        ok = ok and self._assert_eq("T09", "medication_ids", med_ids, sorted(expected["medication_ids"]))

        # Verify lab result IDs
        lis_id = mpi_entry["system_ids"]["lis"]
        lab_ids = sorted([
            o["id"] for o in self.lis.get("Observation", [])
            if o["subject"]["reference"] == f"Patient/{lis_id}"
            and "basedOn" in o  # exclude orphans
        ])
        ok = ok and self._assert_eq("T09", "lab_result_ids", lab_ids, sorted(expected["lab_result_ids"]))

        # Verify encounter IDs
        pas_id = mpi_entry["system_ids"]["pas"]
        enc_ids = sorted([
            e["id"] for e in self.pas.get("Encounter", [])
            if e["subject"]["reference"] == f"Patient/{pas_id}"
        ])
        ok = ok and self._assert_eq("T09", "encounter_ids", enc_ids, sorted(expected["encounter_ids"]))
        return ok

    def verify_t10(self, gt_task: Dict) -> bool:
        """T10: Orphaned lab results (no basedOn)."""
        orphaned_ids = sorted([
            o["id"] for o in self.lis.get("Observation", [])
            if "basedOn" not in o
        ])
        expected_ids = sorted(gt_task["expected_ids"])
        return self._assert_eq("T10", "orphaned_ids", orphaned_ids, expected_ids)

    def verify_t11(self, gt_task: Dict) -> bool:
        """T11: Abandoned orders (active + old)."""
        cutoff = datetime(2026, 2, 1) - timedelta(days=90)
        abandoned_ids = []
        for sr in self.lis.get("ServiceRequest", []):
            if sr.get("status") != "active":
                continue
            authored = sr.get("authoredOn", "")
            try:
                dt = datetime.strptime(authored, "%Y-%m-%dT%H:%M:%SZ")
                if dt < cutoff:
                    abandoned_ids.append(sr["id"])
            except ValueError:
                continue

        abandoned_ids = sorted(abandoned_ids)
        expected_ids = sorted(gt_task["expected_ids"])
        return self._assert_eq("T11", "abandoned_ids", abandoned_ids, expected_ids)

    def verify_t12(self, gt_task: Dict) -> bool:
        """T12: Legacy ICD-9 conditions."""
        legacy_ids = sorted([
            c["id"] for c in self.ehr.get("Condition", [])
            if c["code"]["coding"][0].get("system") == "http://hl7.org/fhir/sid/icd-9-cm"
        ])
        expected_ids = sorted(gt_task["expected_ids"])
        return self._assert_eq("T12", "legacy_ids", legacy_ids, expected_ids)


def main():
    parser = argparse.ArgumentParser(description="Verify ground truth against seed data")
    parser.add_argument("--data-dir", "-d", default="data", help="Data directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    print(f"Verifying ground truth in {data_dir}...")
    print()

    verifier = GroundTruthVerifier(data_dir)
    verifier.verify_all()

    print()
    print(f"{'='*40}")
    print(f"PASSED: {verifier.passed}/{verifier.passed + verifier.failed}")
    if verifier.failed:
        print(f"FAILED: {verifier.failed}")
        sys.exit(1)
    else:
        print("All ground truth verified!")
        sys.exit(0)


if __name__ == "__main__":
    main()
