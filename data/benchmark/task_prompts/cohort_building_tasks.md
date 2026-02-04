# Cohort Building Tasks

Tasks requiring building patient cohorts that span multiple systems

---

## HDH-COH-001: Single-System Cohort: Diabetics

**Difficulty**: easy

**Systems Required**: ehr

**Max Turns**: 10

### Description

Find all patients in the EHR with a Type 2 Diabetes diagnosis. Diabetes is coded with ICD-10 codes starting with E11.

### Expected Response Format

```json
{
  "cohort_name": "Type 2 Diabetics",
  "patient_count": "integer",
  "patient_ids": [
    "array of EHR patient IDs"
  ],
  "query_used": "string describing the query"
}
```

---

## HDH-COH-002: Lab-Based Cohort: Abnormal Glucose

**Difficulty**: medium

**Systems Required**: lis

**Max Turns**: 15

### Description

Find all patients who have had at least one abnormal fasting glucose result. Glucose is LOINC code 2345-7. Abnormal is interpretation 'H' (high) or 'L' (low).

### Expected Response Format

```json
{
  "cohort_name": "Abnormal Glucose",
  "patient_count": "integer",
  "patient_ids": [
    "array of LIS patient IDs"
  ],
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

## HDH-COH-003: Cross-System Cohort: Diabetics on Metformin

**Difficulty**: hard

**Systems Required**: ehr, pharmacy

**Max Turns**: 25

### Description

Find patients who have BOTH a Type 2 Diabetes diagnosis in the EHR (ICD-10 E11.x) AND an active metformin prescription in the Pharmacy system (RxNorm 860975). This requires matching patients across the two systems.

### Expected Response Format

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

## HDH-COH-004: Three-System Cohort: Diabetics with A1C Monitoring

**Difficulty**: hard

**Systems Required**: ehr, pharmacy, lis

**Max Turns**: 35

### Description

Find patients who: (1) Have Type 2 Diabetes in EHR, (2) Are on metformin in Pharmacy, (3) Have had an HbA1c test (LOINC 4548-4) in the last 6 months in LIS. Return complete patient information from all three systems.

### Expected Response Format

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

## HDH-COH-005: Complex Multi-Criteria Cohort

**Difficulty**: expert

**Systems Required**: ehr, pharmacy, pas, lis

**Max Turns**: 45

### Description

Find patients meeting ALL criteria: (1) Age 50-70, (2) Diabetes OR Hypertension diagnosis, (3) On at least 2 chronic medications, (4) Had an inpatient encounter in the past year, (5) Have recent lab results. This requires data from EHR, Pharmacy, PAS, and LIS.

### Expected Response Format

```json
{
  "cohort_name": "Complex Multi-Criteria Cohort",
  "criteria_summary": "string",
  "patient_count": "integer",
  "patients": [
    {
      "patient_ids": {
        "ehr": "string",
        "pharmacy": "string",
        "pas": "string",
        "lis": "string"
      },
      "age": "integer",
      "conditions": [
        "list"
      ],
      "medication_count": "integer",
      "inpatient_encounter_date": "string",
      "recent_labs": [
        "list"
      ]
    }
  ]
}
```

---

