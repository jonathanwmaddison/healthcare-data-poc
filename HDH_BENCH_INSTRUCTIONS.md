# HDH-Bench: Healthcare Data Harmony Benchmark

## Instructions for AI Agent

You are an AI agent tasked with querying and integrating data from a hospital's healthcare information systems. You have access to FHIR R4 REST APIs exposed by 6 independent systems. You interact with them by making HTTP GET requests.

---

## 1. Available Systems & API Reference

### System Endpoints

| System | Base URL | Patient ID Format | Resources Available |
|--------|----------|-------------------|---------------------|
| **EHR** (Electronic Health Record) | `http://localhost:8001/fhir/r4` | `MRN-XXXXXX` | Patient, Condition |
| **LIS** (Laboratory Information System) | `http://localhost:8002/fhir/r4` | `LAB-XXXXXX` | Patient, ServiceRequest, Observation |
| **RIS** (Radiology Information System) | `http://localhost:8003/fhir/r4` | `RAD-XXXXXX` | Patient, ServiceRequest, ImagingStudy |
| **Pharmacy** | `http://localhost:8005/fhir/r4` | `RX-XXXXXX` | Patient, MedicationRequest |
| **PAS** (Patient Administration System) | `http://localhost:8006/fhir/r4` | `ADT-XXXXXX` | Patient, Encounter |
| **Billing** | `http://localhost:8007/fhir/r4` | `ACCT-XXXXXX` | Patient, Claim, Coverage |

### Standard FHIR Endpoints

```
GET /fhir/r4/{ResourceType}              # List/search resources
GET /fhir/r4/{ResourceType}/{id}         # Get by ID
GET /fhir/r4/{ResourceType}?param=value  # Search with parameters
GET /fhir/r4/metadata                    # Capability statement
```

### Search Parameters by Resource

**Patient** (all systems):
- `_id` - Patient ID
- `name` - Search by name
- `birthdate` - Search by DOB (YYYY-MM-DD)
- `gender` - male/female
- `identifier` - External identifier

**Condition** (EHR only):
- `subject` - Patient reference (e.g., `subject=Patient/MRN-100001`)
- `code` - ICD-10 code (e.g., `code=E11`)
- `clinical-status` - active/resolved/inactive
- `onset-date` - Onset date

**Observation** (LIS only):
- `subject` - Patient reference
- `code` - LOINC code (e.g., `code=2345-7`)
- `status` - final/preliminary
- `date` - Result date
- `based-on` - Reference to ServiceRequest

**ServiceRequest** (LIS, RIS):
- `subject` - Patient reference
- `code` - Test/procedure code
- `status` - active/completed
- `authored` - Order date

**MedicationRequest** (Pharmacy only):
- `subject` - Patient reference
- `code` - RxNorm code
- `status` - active/stopped/completed
- `authoredon` - Prescription date

**Encounter** (PAS only):
- `subject` - Patient reference
- `class` - ambulatory/inpatient/emergency
- `status` - in-progress/finished
- `date` - Encounter date

**Claim** (Billing only):
- `patient` - Patient reference
- `status` - active/cancelled
- `created` - Claim date

**Coverage** (Billing only):
- `beneficiary` - Patient reference
- `status` - active/cancelled

### Pagination

```
GET /fhir/r4/{Resource}?_count=50          # Limit to 50 results
GET /fhir/r4/{Resource}?_count=50&_offset=50  # Next page
```

### Clinical Code Systems

| Type | System URI | Examples |
|------|------------|----------|
| Diagnoses (ICD-10) | `http://hl7.org/fhir/sid/icd-10-cm` | E11.9 (Type 2 Diabetes), I10 (Hypertension), E78.5 (Hyperlipidemia), J44.9 (COPD), F32.9 (Depression) |
| Diagnoses (ICD-9 legacy) | `http://hl7.org/fhir/sid/icd-9-cm` | 250.00 (Diabetes), 401.9 (Hypertension) |
| Lab Tests (LOINC) | `http://loinc.org` | 2345-7 (Glucose), 4548-4 (HbA1c), 2160-0 (Creatinine), 718-7 (Hemoglobin), 2093-3 (Cholesterol) |
| Medications (RxNorm) | `http://www.nlm.nih.gov/research/umls/rxnorm` | 860975 (Metformin 500mg), 314076 (Lisinopril 10mg), 617311 (Atorvastatin 20mg) |

### FHIR Response Format

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 100,
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "MRN-100001",
        "name": [{"family": "Smith", "given": ["John"]}],
        "birthDate": "1980-03-15",
        "gender": "male"
      }
    }
  ]
}
```

### Key FHIR Structures

**Patient references in clinical resources:**
```json
"subject": {"reference": "Patient/MRN-100001"}
```

**Code/Coding:**
```json
"code": {
  "coding": [{"system": "http://loinc.org", "code": "2345-7", "display": "Glucose"}]
}
```

**Lab Interpretation:**
```json
"interpretation": [{"coding": [{"code": "H"}]}]  // H=High, L=Low, N=Normal
```

### Example Queries

```
# List patients in EHR
GET http://localhost:8001/fhir/r4/Patient

# Get specific patient
GET http://localhost:8001/fhir/r4/Patient/MRN-100001

# Find diabetic patients
GET http://localhost:8001/fhir/r4/Condition?code=E11

# Get conditions for a patient
GET http://localhost:8001/fhir/r4/Condition?subject=Patient/MRN-100001

# Search lab results by LOINC code
GET http://localhost:8002/fhir/r4/Observation?code=2345-7

# Get medications for a patient
GET http://localhost:8005/fhir/r4/MedicationRequest?subject=Patient/RX-400001

# Search patients by name
GET http://localhost:8002/fhir/r4/Patient?name=Smith

# Search by birthdate
GET http://localhost:8001/fhir/r4/Patient?birthdate=1980-03-15
```

---

## 2. Important Data Characteristics

1. **Patient Matching is Hard**: Names may have variations (Mike vs Michael), dates may be formatted differently, some fields may be missing. You must use demographics to match patients across systems.

2. **~1,000 patients** across the dataset, with each appearing in all 6 systems under different IDs.

3. **~5% duplicate patients**: Same person registered multiple times within the same system.

4. **Data Quality Issues Exist**: Orphaned records, abandoned orders, legacy codes, inconsistencies.

5. **Code Systems Vary**: Some legacy records use ICD-9 instead of ICD-10.

6. **No Ground Truth Access**: You do not have access to the master patient index. You must discover relationships through data exploration.

---

## 3. Core Benchmark Queries (Q001-Q006)

For each query, return your results as JSON matching the specified `response_format`.

### Q001: Patient 360 View (Medium)

**Task**: Find all clinical data for the patient with EHR ID `MRN-100042`. This patient exists in multiple systems under different IDs. Return the patient's IDs in each system and summarize their clinical data.

**Required Output**:
```json
{
  "patient_ids": {
    "ehr": "string - patient ID in EHR system",
    "lis": "string - patient ID in LIS system (if found)",
    "ris": "string - patient ID in RIS system (if found)",
    "pharmacy": "string - patient ID in Pharmacy system (if found)",
    "pas": "string - patient ID in PAS system (if found)",
    "billing": "string - patient ID in Billing system (if found)"
  },
  "clinical_summary": {
    "conditions": ["list of condition descriptions"],
    "medications": ["list of medication names"],
    "recent_labs": ["list of recent lab results"],
    "encounters": ["list of encounter types/dates"]
  }
}
```

### Q002: Diabetic Patient Cohort (Easy)

**Task**: Find all patients diagnosed with Type 2 Diabetes. The diagnosis is recorded in the EHR system using ICD-10 codes starting with E11.

**Required Output**:
```json
{
  "total_count": "integer - number of diabetic patients found",
  "patient_ids": ["list of EHR patient IDs with diabetes diagnosis"]
}
```

### Q003: Abnormal Glucose Results (Medium)

**Task**: Find all patients who have had abnormal glucose lab results. Glucose is identified by LOINC code 2345-7. Abnormal results have interpretation code 'H' (high) or 'L' (low).

**Required Output**:
```json
{
  "total_count": "integer - number of patients with abnormal glucose",
  "patient_ids": ["list of LIS patient IDs with abnormal glucose"],
  "details": [
    {
      "patient_id": "string",
      "value": "number",
      "interpretation": "H or L",
      "date": "date of result"
    }
  ]
}
```

### Q004: Duplicate Patient Detection (Hard)

**Task**: Identify patient records that appear to be duplicates - the same real person registered multiple times with different IDs. Look for patients with matching or very similar demographics (name, date of birth) but different patient IDs within the same system.

**Required Output**:
```json
{
  "duplicate_groups": [
    {
      "likely_same_person": true,
      "confidence": "high/medium/low",
      "records": [
        {
          "system": "string - which system",
          "patient_id": "string",
          "name": "string",
          "birth_date": "string"
        }
      ],
      "matching_criteria": "string - why these are likely duplicates"
    }
  ],
  "total_duplicate_groups": "integer"
}
```

### Q005: Cross-System Cohort Query (Hard)

**Task**: Find patients who meet ALL of the following criteria: (1) Have a Type 2 Diabetes diagnosis in the EHR (ICD-10 E11.x), (2) Have an active metformin prescription in the Pharmacy system (RxNorm 860975), (3) Have had an HbA1c lab test in the LIS (LOINC 4548-4). This requires matching the same patient across three different systems.

**Required Output**:
```json
{
  "patients": [
    {
      "ehr_id": "string - EHR patient ID",
      "pharmacy_id": "string - Pharmacy patient ID",
      "lis_id": "string - LIS patient ID",
      "matching_confidence": "high/medium/low",
      "diabetes_diagnosis": "string - ICD-10 code",
      "metformin_status": "active/inactive",
      "latest_hba1c": {
        "value": "number",
        "date": "string"
      }
    }
  ],
  "total_count": "integer"
}
```

### Q006: Data Quality Issues (Medium)

**Task**: Identify data quality problems in the LIS system: (1) Orphaned results - Observation resources that have no basedOn reference to a ServiceRequest (results without orders), (2) Abandoned orders - ServiceRequest resources with status 'active' but authoredOn date more than 100 days ago (orders that were never completed).

**Required Output**:
```json
{
  "orphaned_results": {
    "count": "integer",
    "sample_ids": ["list of up to 5 Observation IDs without basedOn"]
  },
  "abandoned_orders": {
    "count": "integer",
    "sample_ids": ["list of up to 5 old active ServiceRequest IDs"]
  }
}
```

---

## 4. Full Benchmark Tasks (44 tasks across 8 categories)

### Category Weights for Scoring

| Category | Weight | Tasks |
|----------|--------|-------|
| patient_matching | 15% | 5 |
| cross_system_integration | 15% | 5 |
| oncology_biomarker | 15% | 5 |
| unstructured_data | 13% | 5 |
| cohort_building | 12% | 5 |
| terminology | 12% | 8 |
| data_quality | 10% | 6 |
| data_provenance | 8% | 5 |

### Difficulty Multipliers

| Difficulty | Multiplier |
|------------|------------|
| easy | 1.0x |
| medium | 1.5x |
| hard | 2.0x |
| expert | 3.0x |

---

### 4.1 Patient Matching Tasks

#### HDH-MPI-001: Find Patient in Two Systems (Easy)

**Task**: Given patient ID `MRN-100001` in the EHR system, find the same patient's ID in the LIS (Laboratory) system. The patient has the same demographics but a different ID format.

**Systems**: EHR, LIS | **Max Turns**: 10

**Required Output**:
```json
{
  "ehr_patient_id": "string",
  "lis_patient_id": "string",
  "matching_confidence": "high|medium|low",
  "matching_fields": ["array of fields used for matching"]
}
```

---

#### HDH-MPI-002: Patient 360 View (Medium)

**Task**: Find all records for patient `MRN-100042` across all 6 healthcare systems (EHR, LIS, RIS, Pharmacy, PAS, Billing). Return the patient ID used in each system.

**Systems**: All 6 | **Max Turns**: 25

**Required Output**:
```json
{
  "patient_ids": {
    "ehr": "string",
    "lis": "string",
    "ris": "string",
    "pharmacy": "string",
    "pas": "string",
    "billing": "string"
  },
  "demographics_used": {
    "name": "string",
    "birth_date": "string"
  }
}
```

---

#### HDH-MPI-003: Detect Duplicate Patients (Hard)

**Task**: Find patients in the EHR system that appear to be duplicates - the same real person registered multiple times with different MRNs. Return groups of patient IDs that likely represent the same person.

**Systems**: EHR | **Max Turns**: 30

**Required Output**:
```json
{
  "duplicate_groups": [
    {
      "patient_ids": ["array of MRNs believed to be same person"],
      "confidence": "high|medium|low",
      "matching_evidence": {
        "name_similarity": "number 0-1",
        "dob_match": "boolean",
        "other_fields": ["list"]
      }
    }
  ],
  "total_duplicate_groups_found": "integer",
  "methodology": "string describing approach"
}
```

---

#### HDH-MPI-004: Cross-System Duplicate Detection (Hard)

**Task**: Find cases where the same patient appears to have duplicate records in DIFFERENT systems. For example, a patient might have two different Pharmacy IDs that both belong to them.

**Systems**: EHR, LIS, Pharmacy, Billing | **Max Turns**: 35

**Required Output**:
```json
{
  "cross_system_duplicates": [
    {
      "canonical_patient": "primary patient identifier",
      "duplicate_records": [
        {"system": "string", "patient_id": "string"}
      ],
      "confidence": "high|medium|low"
    }
  ]
}
```

---

#### HDH-MPI-005: Probabilistic Patient Matching (Expert)

**Task**: Given a patient record with partial/fuzzy demographics (name: 'J. Smith', DOB: '1980-03-??', phone partially matching), find the most likely matching patient across all systems. Return match probabilities.

**Systems**: EHR, LIS, Pharmacy | **Max Turns**: 30

**Required Output**:
```json
{
  "query_demographics": {
    "name": "J. Smith",
    "birth_date_partial": "1980-03",
    "phone_partial": "555-123"
  },
  "candidate_matches": [
    {
      "system": "string",
      "patient_id": "string",
      "match_probability": "number 0-1",
      "matching_fields": ["list"],
      "mismatching_fields": ["list"]
    }
  ],
  "recommended_match": {
    "patient_id": "string",
    "confidence": "number"
  }
}
```

---

### 4.2 Cross-System Integration Tasks

#### HDH-CSI-001: Complete Medication History (Medium)

**Task**: For patient `MRN-100042` in the EHR, retrieve their complete medication history by: 1) Finding the patient across systems using demographics, 2) Getting current prescriptions from Pharmacy, 3) Getting encounters from PAS. Return a unified list.

**Systems**: EHR, Pharmacy, PAS | **Max Turns**: 20

**Required Output**:
```json
{
  "patient": {
    "ehr_id": "string",
    "pharmacy_id": "string",
    "pas_id": "string"
  },
  "medications": [
    {
      "name": "string",
      "rxnorm": "string",
      "source": "pharmacy|ehr|pas",
      "status": "active|completed|stopped"
    }
  ],
  "total_count": "integer"
}
```

---

#### HDH-CSI-002: Lab-Diagnosis Correlation (Hard)

**Task**: Find all patients with Type 2 Diabetes (ICD-10 E11.x) in the EHR who have had HbA1c tests in the LIS. Return the correlation between diagnosis and lab monitoring. Requires matching patients across EHR and LIS.

**Systems**: EHR, LIS | **Max Turns**: 25

**Required Output**:
```json
{
  "diabetic_patients": "integer",
  "patients_with_hba1c": "integer",
  "match_rate": "float (0-1)",
  "monitoring_stats": {
    "avg_tests_per_patient": "float",
    "patients_with_no_tests": "integer"
  },
  "sample_correlations": [
    {
      "ehr_id": "string",
      "lis_id": "string",
      "diagnosis_date": "string",
      "first_hba1c_date": "string",
      "total_hba1c_tests": "integer"
    }
  ]
}
```

---

#### HDH-CSI-003: Multi-System Care Gap Analysis (Hard)

**Task**: Identify patients with hypertension (ICD-10 I10) in the EHR who are prescribed antihypertensives in Pharmacy but have no blood pressure readings in LIS/EHR in the last 6 months.

**Systems**: EHR, Pharmacy, LIS | **Max Turns**: 30

**Required Output**:
```json
{
  "hypertension_patients": "integer",
  "on_antihypertensives": "integer",
  "missing_bp_readings": "integer",
  "care_gap_rate": "float (0-1)",
  "sample_gaps": [
    {
      "ehr_id": "string",
      "pharmacy_id": "string",
      "last_bp_date": "string or null",
      "current_medications": ["list of antihypertensive names"]
    }
  ]
}
```

---

#### HDH-CSI-004: Medication-Lab Monitoring Compliance (Expert)

**Task**: For patients on metformin (RxNorm 860975) in Pharmacy, verify they have renal function monitoring (creatinine, eGFR) in LIS. Metformin requires kidney function monitoring. Identify non-compliant patients.

**Systems**: Pharmacy, LIS, EHR | **Max Turns**: 35

**Required Output**:
```json
{
  "metformin_patients": "integer",
  "with_renal_monitoring": "integer",
  "without_monitoring": "integer",
  "compliance_rate": "float (0-1)",
  "high_risk_patients": [
    {
      "ehr_id": "string",
      "pharmacy_id": "string",
      "metformin_start_date": "string",
      "last_creatinine_date": "string or null",
      "last_egfr_value": "number or null"
    }
  ]
}
```

---

#### HDH-CSI-005: Billing Reconciliation with Clinical (Expert)

**Task**: Compare diagnoses in the EHR (Conditions) with diagnoses submitted for billing (Claims). Identify discrepancies where clinical records don't match billing codes.

**Systems**: EHR, Billing | **Max Turns**: 30

**Required Output**:
```json
{
  "patients_analyzed": "integer",
  "billing_only_diagnoses": "integer",
  "clinical_only_diagnoses": "integer",
  "matched_diagnoses": "integer",
  "discrepancy_rate": "float (0-1)",
  "sample_discrepancies": [
    {
      "patient_ehr_id": "string",
      "patient_billing_id": "string",
      "clinical_codes": ["list of ICD codes"],
      "billing_codes": ["list of ICD codes"],
      "missing_from_billing": ["list"],
      "missing_from_clinical": ["list"]
    }
  ]
}
```

---

### 4.3 Cohort Building Tasks

#### HDH-COH-001: Single-System Cohort: Diabetics (Easy)

**Task**: Find all patients in the EHR with a Type 2 Diabetes diagnosis. Diabetes is coded with ICD-10 codes starting with E11.

**Systems**: EHR | **Max Turns**: 10

**Required Output**:
```json
{
  "cohort_name": "Type 2 Diabetics",
  "patient_count": "integer",
  "patient_ids": ["array of EHR patient IDs"],
  "query_used": "string describing the query"
}
```

---

#### HDH-COH-002: Lab-Based Cohort: Abnormal Glucose (Medium)

**Task**: Find all patients who have had at least one abnormal fasting glucose result. Glucose is LOINC code 2345-7. Abnormal is interpretation 'H' (high) or 'L' (low).

**Systems**: LIS | **Max Turns**: 15

**Required Output**:
```json
{
  "cohort_name": "Abnormal Glucose",
  "patient_count": "integer",
  "patient_ids": ["array of LIS patient IDs"],
  "abnormal_results": [
    {
      "patient_id": "string",
      "value": "number",
      "unit": "string",
      "interpretation": "H|L",
      "date": "string"
    }
  ]
}
```

---

#### HDH-COH-003: Cross-System Cohort: Diabetics on Metformin (Hard)

**Task**: Find patients who have BOTH a Type 2 Diabetes diagnosis in the EHR (ICD-10 E11.x) AND an active metformin prescription in the Pharmacy system (RxNorm 860975). Requires matching patients across two systems.

**Systems**: EHR, Pharmacy | **Max Turns**: 25

**Required Output**:
```json
{
  "cohort_name": "Diabetics on Metformin",
  "patient_count": "integer",
  "patients": [
    {
      "ehr_id": "string",
      "pharmacy_id": "string",
      "diabetes_code": "string",
      "metformin_status": "active|stopped"
    }
  ]
}
```

---

#### HDH-COH-004: Three-System Cohort: Diabetics with A1C Monitoring (Hard)

**Task**: Find patients who: (1) Have Type 2 Diabetes in EHR, (2) Are on metformin in Pharmacy, (3) Have had an HbA1c test (LOINC 4548-4) in the last 6 months in LIS. Return complete information from all three systems.

**Systems**: EHR, Pharmacy, LIS | **Max Turns**: 35

**Required Output**:
```json
{
  "cohort_name": "Diabetics on Metformin with Recent A1C",
  "patient_count": "integer",
  "patients": [
    {
      "ehr_id": "string",
      "pharmacy_id": "string",
      "lis_id": "string",
      "diabetes_diagnosis": "string",
      "metformin_dose": "string",
      "latest_a1c": {
        "value": "number",
        "date": "string",
        "interpretation": "string"
      }
    }
  ]
}
```

---

#### HDH-COH-005: Complex Multi-Criteria Cohort (Expert)

**Task**: Find patients meeting ALL criteria: (1) Age 50-70, (2) Diabetes OR Hypertension diagnosis, (3) On at least 2 chronic medications, (4) Had an inpatient encounter in the past year, (5) Have recent lab results.

**Systems**: EHR, Pharmacy, PAS, LIS | **Max Turns**: 45

**Required Output**:
```json
{
  "cohort_name": "Complex Multi-Criteria Cohort",
  "criteria_summary": "string",
  "patient_count": "integer",
  "patients": [
    {
      "patient_ids": {"ehr": "string", "pharmacy": "string", "pas": "string", "lis": "string"},
      "age": "integer",
      "conditions": ["list"],
      "medication_count": "integer",
      "inpatient_encounter_date": "string",
      "recent_labs": ["list"]
    }
  ]
}
```

---

### 4.4 Data Quality Tasks

#### HDH-DQ-001: Find Orphaned Lab Results (Easy)

**Task**: Find lab results (Observations) in the LIS that do not have a corresponding order (no basedOn reference to a ServiceRequest). These are 'orphaned' results.

**Systems**: LIS | **Max Turns**: 15

**Required Output**:
```json
{
  "orphaned_count": "integer",
  "sample_orphaned_ids": ["list of up to 10 Observation IDs"],
  "methodology": "string"
}
```

---

#### HDH-DQ-002: Find Abandoned Orders (Easy)

**Task**: Find lab orders (ServiceRequests) in the LIS that are still marked as 'active' but were created more than 100 days ago. These are likely abandoned orders that were never completed.

**Systems**: LIS | **Max Turns**: 15

**Required Output**:
```json
{
  "abandoned_count": "integer",
  "sample_abandoned_ids": ["list of up to 10 ServiceRequest IDs"],
  "oldest_order_date": "string"
}
```

---

#### HDH-DQ-003: Find Future-Dated Records (Medium)

**Task**: Find any records across EHR, LIS, and Pharmacy that have dates in the future (data entry errors). Check effectiveDateTime, authoredOn, recordedDate fields.

**Systems**: EHR, LIS, Pharmacy | **Max Turns**: 20

**Required Output**:
```json
{
  "future_dated_records": [
    {
      "system": "string",
      "resource_type": "string",
      "resource_id": "string",
      "field": "string",
      "value": "string (the future date)"
    }
  ],
  "total_count": "integer"
}
```

---

#### HDH-DQ-004: Find Missing Required Fields (Medium)

**Task**: Audit Patient records in the EHR for data completeness. Find patients missing critical fields: birthDate, gender, or name. Report the completeness percentage.

**Systems**: EHR | **Max Turns**: 15

**Required Output**:
```json
{
  "total_patients": "integer",
  "completeness": {
    "birthDate": {"present": "integer", "missing": "integer", "percentage": "number"},
    "gender": {"present": "integer", "missing": "integer", "percentage": "number"},
    "name": {"present": "integer", "missing": "integer", "percentage": "number"}
  },
  "patients_missing_any_field": ["list of patient IDs"]
}
```

---

#### HDH-DQ-005: Cross-System Data Consistency (Hard)

**Task**: For 10 randomly selected patients, compare their demographics (name, DOB, gender) across all systems where they exist. Report any inconsistencies.

**Systems**: EHR, LIS, Pharmacy, PAS, Billing | **Max Turns**: 40

**Required Output**:
```json
{
  "patients_analyzed": "integer",
  "inconsistencies_found": [
    {
      "patient_canonical_id": "string",
      "field": "name|birthDate|gender",
      "values_by_system": {
        "ehr": "string",
        "lis": "string",
        "pharmacy": "string"
      },
      "recommended_value": "string"
    }
  ],
  "consistency_score": "number 0-1"
}
```

---

#### HDH-DQ-006: Referential Integrity Check (Hard)

**Task**: Check referential integrity in the LIS: Do all Observations reference valid Patients? Do all ServiceRequests reference valid Patients? Find and report broken references.

**Systems**: LIS | **Max Turns**: 25

**Required Output**:
```json
{
  "observations_checked": "integer",
  "service_requests_checked": "integer",
  "broken_patient_references": [
    {
      "resource_type": "string",
      "resource_id": "string",
      "referenced_patient": "string",
      "error": "patient_not_found|invalid_format"
    }
  ],
  "integrity_score": "number 0-1"
}
```

---

### 4.5 Terminology Tasks

#### HDH-TRM-001: Identify Code Systems in Use (Easy)

**Task**: Survey the data across EHR, LIS, and Pharmacy to identify which code systems are used for different data types (diagnoses, labs, medications). Report the code system URIs found.

**Systems**: EHR, LIS, Pharmacy | **Max Turns**: 15

**Required Output**:
```json
{
  "code_systems_found": {
    "diagnoses": ["list of code system URIs"],
    "lab_tests": ["list of code system URIs"],
    "medications": ["list of code system URIs"]
  },
  "examples": {
    "diagnosis_example": {"system": "string", "code": "string", "display": "string"},
    "lab_example": {"system": "string", "code": "string", "display": "string"},
    "medication_example": {"system": "string", "code": "string", "display": "string"}
  }
}
```

---

#### HDH-TRM-002: Find Legacy ICD-9 Codes (Medium)

**Task**: Find all conditions in the EHR that use legacy ICD-9 codes (system: `http://hl7.org/fhir/sid/icd-9-cm`) instead of current ICD-10 codes. These are records migrated from an older system.

**Systems**: EHR | **Max Turns**: 15

**Required Output**:
```json
{
  "legacy_icd9_count": "integer",
  "sample_records": [
    {
      "condition_id": "string",
      "icd9_code": "string",
      "display": "string",
      "patient_id": "string"
    }
  ],
  "percentage_of_total": "number"
}
```

---

#### HDH-TRM-003: LOINC Code Lookup (Medium)

**Task**: Given the clinical concept 'Hemoglobin A1c' (HbA1c), find all lab results in the LIS that measure this. The standard LOINC code is 4548-4, but there may be other related codes.

**Systems**: LIS | **Max Turns**: 15

**Required Output**:
```json
{
  "loinc_codes_found": ["list of LOINC codes for HbA1c"],
  "result_count": "integer",
  "sample_results": [
    {
      "observation_id": "string",
      "loinc_code": "string",
      "value": "number",
      "unit": "string",
      "patient_id": "string"
    }
  ]
}
```

---

#### HDH-TRM-004: Find All Diabetes-Related Codes (Hard)

**Task**: Find ALL records related to diabetes across all systems, accounting for different terminologies: ICD-10 E11.x (Type 2), ICD-10 E10.x (Type 1), ICD-9 250.xx (legacy), and medications like metformin, insulin.

**Systems**: EHR, Pharmacy, LIS | **Max Turns**: 30

**Required Output**:
```json
{
  "diabetes_conditions": {
    "icd10_type2": {"code_pattern": "E11.x", "count": "integer"},
    "icd10_type1": {"code_pattern": "E10.x", "count": "integer"},
    "icd9_legacy": {"code_pattern": "250.xx", "count": "integer"}
  },
  "diabetes_medications": {
    "metformin": {"rxnorm": "860975", "count": "integer"},
    "insulin_products": {"count": "integer"}
  },
  "diabetes_labs": {
    "hba1c": {"loinc": "4548-4", "count": "integer"},
    "glucose": {"loinc": "2345-7", "count": "integer"}
  },
  "total_diabetes_related_records": "integer",
  "unique_patients_with_diabetes": "integer"
}
```

---

#### HDH-TRM-005: Code Mapping Challenge (Expert)

**Task**: Given ICD-9 codes from legacy records, provide the equivalent ICD-10 codes. Verify by finding if both codes appear for the same patients.

**Systems**: EHR | **Max Turns**: 25

**Required Output**:
```json
{
  "icd9_to_icd10_mappings": [
    {
      "icd9_code": "250.00",
      "icd9_display": "string",
      "icd10_equivalent": "E11.9",
      "icd10_display": "string",
      "patients_with_both": "integer"
    }
  ],
  "mapping_confidence": "high|medium|low"
}
```

---

#### HDH-TRM-006: Cross-System Vocabulary Reconciliation (Hard)

**Task**: The same medication may be coded differently across systems - RxNorm in Pharmacy, NDC in Billing, free-text in EHR notes. For patient `MRN-100042`, reconcile all medication references to identify which refer to the same drug.

**Systems**: EHR, Pharmacy, Billing | **Max Turns**: 25

**Required Output**:
```json
{
  "patient_queried": "string",
  "medication_groups": [
    {
      "drug_name": "string (normalized)",
      "codes": {
        "rxnorm": "string or null",
        "ndc": "string or null",
        "local": "string or null"
      },
      "sources": ["pharmacy", "billing", "ehr"]
    }
  ],
  "unique_medications": "integer",
  "reconciliation_issues": ["list of unmatched codes"]
}
```

---

#### HDH-TRM-007: Local Code Translation (Expert)

**Task**: Some lab tests use local/proprietary codes instead of LOINC. Find Observations in LIS that use non-standard code systems and attempt to map them to standard LOINC codes based on the display name and units.

**Systems**: LIS | **Max Turns**: 30

**Required Output**:
```json
{
  "local_code_observations": "integer",
  "proposed_mappings": [
    {
      "local_code": "string",
      "local_system": "string",
      "display_name": "string",
      "units": "string",
      "proposed_loinc": "string",
      "loinc_display": "string",
      "confidence": "high|medium|low"
    }
  ],
  "unmappable_codes": ["list of codes that couldn't be mapped"]
}
```

---

#### HDH-TRM-008: Multi-Axial Code Resolution (Expert)

**Task**: Find all representations of 'Type 2 Diabetes with complications' across different code systems (ICD-10, ICD-9, SNOMED) and map them together.

**Systems**: EHR, Billing | **Max Turns**: 30

**Required Output**:
```json
{
  "concept": "Type 2 Diabetes with complications",
  "code_clusters": [
    {
      "clinical_concept": "string (specific complication)",
      "codes": {
        "icd10": ["list of E11.x codes"],
        "icd9": ["list of 250.xx codes"],
        "snomed": ["list of SNOMED codes if found"]
      },
      "patient_count": "integer"
    }
  ],
  "total_diabetes_codes_found": "integer",
  "unmapped_codes": ["list of codes not fitting known patterns"]
}
```

---

### 4.6 Data Provenance Tasks

#### HDH-PRV-001: Identify Source System for Data Type (Easy)

**Task**: Determine which system is the authoritative source for each type of clinical data. Which system should be queried for medications? For diagnoses? For lab results?

**Systems**: EHR, LIS, Pharmacy | **Max Turns**: 15

**Required Output**:
```json
{
  "source_of_truth": {
    "diagnoses": {"system": "string", "resource_type": "string"},
    "medications": {"system": "string", "resource_type": "string"},
    "lab_results": {"system": "string", "resource_type": "string"},
    "lab_orders": {"system": "string", "resource_type": "string"},
    "encounters": {"system": "string", "resource_type": "string"},
    "demographics": {"system": "string", "resource_type": "string"}
  },
  "reasoning": "string"
}
```

---

#### HDH-PRV-002: Trace Lab Result to Order (Medium)

**Task**: Given a specific lab result (Observation), trace it back to its originating order (ServiceRequest) and the encounter/visit when it was ordered. Return the complete chain.

**Systems**: LIS, PAS | **Max Turns**: 15

**Required Output**:
```json
{
  "observation_id": "string",
  "provenance_chain": {
    "result": {"id": "string", "code": "string", "value": "string"},
    "order": {"id": "string", "code": "string", "authored_on": "string"},
    "encounter": {"id": "string", "type": "string", "date": "string"},
    "patient": {"id": "string", "name": "string"}
  }
}
```

---

#### HDH-PRV-003: Identify Data Freshness (Medium)

**Task**: For a specific patient, determine the freshness of their data in each system. When was each system's data last updated? Which systems have stale data (>30 days old)?

**Systems**: EHR, LIS, Pharmacy, PAS | **Max Turns**: 20

**Required Output**:
```json
{
  "patient_id_queried": "string (EHR ID)",
  "data_freshness": {
    "ehr": {"last_updated": "string", "days_old": "integer", "is_stale": "boolean"},
    "lis": {"last_updated": "string", "days_old": "integer", "is_stale": "boolean"},
    "pharmacy": {"last_updated": "string", "days_old": "integer", "is_stale": "boolean"},
    "pas": {"last_updated": "string", "days_old": "integer", "is_stale": "boolean"}
  },
  "stale_systems": ["list of systems with data >30 days old"]
}
```

---

#### HDH-PRV-004: Resolve Conflicting Data (Hard)

**Task**: Patient `MRN-100042` has different values for the same attribute in different systems (e.g., different phone numbers, slightly different names). Identify all conflicts and recommend which value should be authoritative.

**Systems**: EHR, LIS, Pharmacy, Billing | **Max Turns**: 30

**Required Output**:
```json
{
  "patient_queried": "MRN-100042",
  "conflicts": [
    {
      "field": "string",
      "values": {
        "ehr": "string",
        "lis": "string",
        "pharmacy": "string",
        "billing": "string"
      },
      "recommended_value": "string",
      "recommendation_reason": "string"
    }
  ],
  "conflict_count": "integer",
  "resolution_strategy": "string"
}
```

---

#### HDH-PRV-005: Build Complete Patient Timeline (Expert)

**Task**: Construct a complete timeline of all clinical events for patient `MRN-100042` across all systems. Include diagnoses, lab orders/results, medication changes, and encounters in chronological order.

**Systems**: EHR, LIS, Pharmacy, PAS | **Max Turns**: 40

**Required Output**:
```json
{
  "patient": {
    "ehr_id": "string",
    "name": "string"
  },
  "timeline": [
    {
      "date": "string",
      "event_type": "diagnosis|lab_order|lab_result|medication_start|medication_stop|encounter",
      "source_system": "string",
      "description": "string",
      "resource_id": "string"
    }
  ],
  "total_events": "integer",
  "date_range": {"start": "string", "end": "string"}
}
```

---

### 4.7 Oncology Biomarker Tasks

#### HDH-ONC-001: Find HER2-Positive Breast Cancer Patients (Medium)

**Task**: Identify all patients with breast cancer (ICD-10 C50.x) who have HER2-positive biomarker results. HER2 status is determined by IHC (LOINC 18474-7) with result 3+ or FISH (LOINC 32996-3) with result 'positive'.

**Systems**: EHR, LIS | **Max Turns**: 20

**Required Output**:
```json
{
  "breast_cancer_patients": "integer",
  "patients_with_her2_testing": "integer",
  "her2_positive_patients": [
    {
      "ehr_id": "string",
      "lis_id": "string",
      "diagnosis_code": "string",
      "her2_result": "string (3+, positive, amplified)",
      "test_date": "string",
      "test_type": "IHC|FISH"
    }
  ],
  "her2_positive_count": "integer",
  "positivity_rate": "float"
}
```

---

#### HDH-ONC-002: EGFR Mutation Lung Cancer Cohort (Hard)

**Task**: Build a cohort of non-small cell lung cancer (NSCLC) patients with EGFR mutations. NSCLC is ICD-10 C34.x. EGFR mutations detected via molecular testing (LOINC 21659-7). Look for specific mutations like exon 19 deletion or L858R in test comments/notes.

**Systems**: EHR, LIS | **Max Turns**: 25

**Required Output**:
```json
{
  "nsclc_patients": "integer",
  "patients_with_egfr_testing": "integer",
  "egfr_mutation_positive": [
    {
      "ehr_id": "string",
      "lis_id": "string",
      "mutation_type": "string (exon 19 del, L858R, T790M, etc.)",
      "test_date": "string",
      "report_text": "string (relevant excerpt)"
    }
  ],
  "mutation_distribution": {
    "exon_19_deletion": "integer",
    "L858R": "integer",
    "T790M": "integer",
    "other": "integer"
  }
}
```

---

#### HDH-ONC-003: PD-L1 Expression for Immunotherapy (Hard)

**Task**: Find cancer patients eligible for immunotherapy based on PD-L1 expression. PD-L1 tested via IHC (LOINC 85147-9). Eligibility: >=50% TPS for first-line NSCLC, >=1% for second-line.

**Systems**: EHR, LIS | **Max Turns**: 25

**Required Output**:
```json
{
  "cancer_patients_tested": "integer",
  "pdl1_results": [
    {
      "patient_ehr_id": "string",
      "cancer_type": "string",
      "tps_percentage": "integer",
      "first_line_eligible": "boolean",
      "second_line_eligible": "boolean"
    }
  ],
  "first_line_eligible_count": "integer",
  "second_line_only_eligible_count": "integer"
}
```

---

#### HDH-ONC-004: Comprehensive Biomarker Panel Review (Expert)

**Task**: For all lung cancer patients, compile a comprehensive biomarker summary including EGFR, ALK, ROS1, BRAF, PD-L1, and KRAS status. Create a unified view showing all tested biomarkers and their results.

**Systems**: EHR, LIS | **Max Turns**: 35

**Required Output**:
```json
{
  "lung_cancer_patients": "integer",
  "biomarker_summary": [
    {
      "patient_ehr_id": "string",
      "patient_lis_id": "string",
      "diagnosis": "string",
      "biomarkers": {
        "EGFR": {"status": "positive|negative|not_tested", "mutation": "string or null"},
        "ALK": {"status": "positive|negative|not_tested"},
        "ROS1": {"status": "positive|negative|not_tested"},
        "BRAF": {"status": "positive|negative|not_tested", "mutation": "string or null"},
        "PD_L1": {"status": "tested|not_tested", "tps": "integer or null"},
        "KRAS": {"status": "positive|negative|not_tested", "mutation": "string or null"}
      },
      "recommended_therapy": "string based on biomarkers"
    }
  ],
  "testing_gaps": {
    "no_biomarker_testing": "integer",
    "incomplete_panel": "integer"
  }
}
```

---

#### HDH-ONC-005: Pathology Report Data Extraction (Expert)

**Task**: Extract tumor characteristics from pathology reports: tumor grade, tumor size, lymph node involvement, margin status, and molecular findings from narrative text.

**Systems**: EHR, LIS | **Max Turns**: 30

**Required Output**:
```json
{
  "pathology_reports_analyzed": "integer",
  "extracted_data": [
    {
      "report_id": "string",
      "patient_id": "string",
      "cancer_type": "string",
      "tumor_grade": "well|moderate|poorly differentiated",
      "tumor_size_cm": "number or null",
      "lymph_nodes_positive": "integer or null",
      "lymph_nodes_examined": "integer or null",
      "margin_status": "positive|negative|close",
      "molecular_findings": ["list of biomarkers/mutations mentioned"],
      "stage": "string or null"
    }
  ]
}
```

---

### 4.8 Unstructured Data Tasks

#### HDH-UNS-001: Extract Diagnoses from Clinical Notes (Medium)

**Task**: Clinical notes in the EHR contain diagnoses in free text that may not be coded. Find DocumentReference resources and extract any diagnoses mentioned. Compare with coded Conditions to find uncoded diagnoses.

**Systems**: EHR | **Max Turns**: 20

**Required Output**:
```json
{
  "documents_analyzed": "integer",
  "diagnoses_found": [
    {
      "document_id": "string",
      "text_mention": "string",
      "suggested_icd10": "string or null",
      "already_coded": "boolean"
    }
  ],
  "uncoded_diagnoses_count": "integer"
}
```

---

#### HDH-UNS-002: Parse Medication Instructions (Medium)

**Task**: MedicationRequest resources have dosageInstruction with free-text 'text' fields like 'Take 1 tablet by mouth twice daily with food'. Parse these to extract structured dosing information.

**Systems**: Pharmacy | **Max Turns**: 15

**Required Output**:
```json
{
  "medications_analyzed": "integer",
  "parsed_instructions": [
    {
      "medication_id": "string",
      "original_text": "string",
      "parsed": {
        "dose_value": "number",
        "dose_unit": "string",
        "route": "string",
        "frequency": "string",
        "timing": "string or null"
      }
    }
  ],
  "parsing_success_rate": "float (0-1)"
}
```

---

#### HDH-UNS-003: Reconcile Free-Text Allergies (Hard)

**Task**: AllergyIntolerance resources may have allergies as free text or coded. Find all allergies and normalize them to identify duplicates and conflicts.

**Systems**: EHR, Pharmacy | **Max Turns**: 25

**Required Output**:
```json
{
  "total_allergy_records": "integer",
  "coded_allergies": "integer",
  "freetext_allergies": "integer",
  "normalized_allergies": [
    {
      "allergen": "string (normalized name)",
      "records": ["list of allergy record IDs"],
      "systems": ["list of source systems"],
      "is_duplicate": "boolean",
      "conflict": "string or null"
    }
  ],
  "duplicate_count": "integer",
  "conflict_count": "integer"
}
```

---

#### HDH-UNS-004: Extract Lab Comments (Hard)

**Task**: Lab Observations have interpretive comments in the 'note' field. Extract and categorize these comments to identify critical values and quality issues.

**Systems**: LIS | **Max Turns**: 20

**Required Output**:
```json
{
  "observations_with_comments": "integer",
  "comment_categories": {
    "critical_value": "integer",
    "specimen_quality": "integer",
    "interpretation": "integer",
    "other": "integer"
  },
  "critical_value_alerts": [
    {
      "observation_id": "string",
      "test_name": "string",
      "value": "string",
      "comment": "string",
      "patient_id": "string"
    }
  ]
}
```

---

#### HDH-UNS-005: Cross-System Note Reconciliation (Expert)

**Task**: The same clinical event may be documented differently across systems. For a specific patient, find related documentation across systems and link them to the same clinical event.

**Systems**: EHR, LIS, Billing | **Max Turns**: 35

**Required Output**:
```json
{
  "patient_queried": "string",
  "clinical_events": [
    {
      "event_date": "string",
      "event_type": "string",
      "linked_records": {
        "ehr_documents": ["list of document IDs"],
        "lis_observations": ["list of observation IDs"],
        "billing_claims": ["list of claim IDs"]
      },
      "description": "string (synthesized from all sources)"
    }
  ],
  "total_events_identified": "integer"
}
```

---

## 5. Scoring

### Primary Metric: Success Rate
- Percentage of tasks fully completed
- Formula: `successful_tasks / total_tasks`

### Secondary Metrics
- **Progress Rate**: Average % of sub-goals completed per task
- **F1 Patient Matching**: F1 score for patient identity matching tasks
- **Action Completion**: Goals achieved / Goals stated

### Efficiency Metrics (lower is better)
- **Avg Turns**: Average API calls per task
- **Avg Time**: Average seconds per task
- **Avg Cost**: Average token cost per task (USD)

### Scoring Rules
- Tasks are scored 0.0-1.0 then multiplied by their difficulty multiplier
- Count-based tasks: full credit if within expected range, partial credit based on deviation
- Set-match tasks: 90% recall needed for success, partial credit for less
- F1 tasks: various thresholds (0.4-0.85 depending on task difficulty)
- Threshold tasks: typically 0.7-0.9 threshold for pass

### Ground Truth Ranges (for count-based tasks)
- **Diabetic patients (COH-001)**: 114-154 patients
- **Abnormal glucose (COH-002)**: 100-180 patients
- **Duplicate patients (MPI-003)**: 40-60 groups
- **Orphaned lab results (DQ-001)**: 25-35
- **Abandoned orders (DQ-002)**: 15-25
- **Legacy ICD-9 codes (TRM-002)**: 90-110

---

## 6. How to Run a Task

For each task:

1. Read the task description and understand what systems to query
2. Make HTTP GET requests to the FHIR APIs to discover and retrieve data
3. If cross-system matching is needed, first get patient demographics from one system, then search by name/DOB in other systems
4. Process the data according to the task requirements
5. Return your results as JSON matching the specified output format

You have up to the max_turns specified per task. Each API call counts as one turn.
