# Cross System Integration Tasks

Tasks requiring coordination of data across multiple healthcare systems to answer clinical questions. This is the unique value of HDH-Bench - testing agents' ability to navigate fragmented healthcare data.

---

## HDH-CSI-001: Complete Medication History

**Difficulty**: medium

**Systems Required**: ehr, pharmacy, pas

**Max Turns**: 20

### Description

For patient MRN-100042 in the EHR, retrieve their complete medication history by: 1) Finding the patient across systems using the MPI, 2) Getting current prescriptions from Pharmacy, 3) Getting medication administrations during encounters from PAS. Return a unified list.

### Expected Response Format

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

## HDH-CSI-002: Lab-Diagnosis Correlation

**Difficulty**: hard

**Systems Required**: ehr, lis

**Max Turns**: 25

### Description

Find all patients with Type 2 Diabetes (ICD-10 E11.x) in the EHR who have had HbA1c tests in the LIS. Return the correlation between diagnosis date and lab monitoring frequency. This requires matching patients across EHR and LIS systems.

### Expected Response Format

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

## HDH-CSI-003: Multi-System Care Gap Analysis

**Difficulty**: hard

**Systems Required**: ehr, pharmacy, lis

**Max Turns**: 30

### Description

Identify patients with hypertension (ICD-10 I10) in the EHR who are prescribed antihypertensives in Pharmacy but have no blood pressure readings in LIS/EHR in the last 6 months. This is a common care gap analysis requiring cross-system data.

### Expected Response Format

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
      "current_medications": [
        "list of antihypertensive names"
      ]
    }
  ]
}
```

---

## HDH-CSI-004: Medication-Lab Monitoring Compliance

**Difficulty**: expert

**Systems Required**: pharmacy, lis, ehr

**Max Turns**: 35

### Description

For patients on metformin (RxNorm 860975) in Pharmacy, verify they have renal function monitoring (creatinine, eGFR) in LIS as per clinical guidelines. Metformin requires kidney function monitoring. Identify non-compliant patients.

### Expected Response Format

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

## HDH-CSI-005: Billing Reconciliation with Clinical

**Difficulty**: expert

**Systems Required**: ehr, billing

**Max Turns**: 30

### Description

Compare diagnoses recorded in the EHR (Conditions) with diagnoses submitted for billing (Claims in Billing system). Identify discrepancies where clinical records don't match billing codes. This tests understanding of clinical vs. administrative data.

### Expected Response Format

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
      "clinical_codes": [
        "list of ICD codes"
      ],
      "billing_codes": [
        "list of ICD codes"
      ],
      "missing_from_billing": [
        "list of codes"
      ],
      "missing_from_clinical": [
        "list of codes"
      ]
    }
  ]
}
```

---

