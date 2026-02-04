# Terminology Tasks

Tasks requiring understanding and mapping of clinical terminologies

---

## HDH-TRM-001: Identify Code Systems in Use

**Difficulty**: easy

**Systems Required**: ehr, lis, pharmacy

**Max Turns**: 15

### Description

Survey the data across EHR, LIS, and Pharmacy to identify which code systems are used for different data types (diagnoses, labs, medications). Report the code system URIs found.

### Expected Response Format

```json
{
  "code_systems_found": {
    "diagnoses": [
      "list of code system URIs"
    ],
    "lab_tests": [
      "list of code system URIs"
    ],
    "medications": [
      "list of code system URIs"
    ]
  },
  "examples": {
    "diagnosis_example": {
      "system": "string",
      "code": "string",
      "display": "string"
    },
    "lab_example": {
      "system": "string",
      "code": "string",
      "display": "string"
    },
    "medication_example": {
      "system": "string",
      "code": "string",
      "display": "string"
    }
  }
}
```

---

## HDH-TRM-002: Find Legacy ICD-9 Codes

**Difficulty**: medium

**Systems Required**: ehr

**Max Turns**: 15

### Description

Find all conditions in the EHR that use legacy ICD-9 codes (system: http://hl7.org/fhir/sid/icd-9-cm) instead of current ICD-10 codes. These are records migrated from an older system.

### Expected Response Format

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

## HDH-TRM-003: LOINC Code Lookup

**Difficulty**: medium

**Systems Required**: lis

**Max Turns**: 15

### Description

Given the clinical concept 'Hemoglobin A1c' (HbA1c), find all lab results in the LIS that measure this. The standard LOINC code is 4548-4, but there may be other related codes.

### Expected Response Format

```json
{
  "loinc_codes_found": [
    "list of LOINC codes for HbA1c"
  ],
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

## HDH-TRM-004: Find All Diabetes-Related Codes

**Difficulty**: hard

**Systems Required**: ehr, pharmacy, lis

**Max Turns**: 30

### Description

Find ALL records related to diabetes across all systems, accounting for different terminologies: ICD-10 E11.x (Type 2), ICD-10 E10.x (Type 1), ICD-9 250.xx (legacy), SNOMED codes, and medications like metformin, insulin.

### Expected Response Format

```json
{
  "diabetes_conditions": {
    "icd10_type2": {
      "code_pattern": "E11.x",
      "count": "integer"
    },
    "icd10_type1": {
      "code_pattern": "E10.x",
      "count": "integer"
    },
    "icd9_legacy": {
      "code_pattern": "250.xx",
      "count": "integer"
    }
  },
  "diabetes_medications": {
    "metformin": {
      "rxnorm": "860975",
      "count": "integer"
    },
    "insulin_products": {
      "count": "integer"
    }
  },
  "diabetes_labs": {
    "hba1c": {
      "loinc": "4548-4",
      "count": "integer"
    },
    "glucose": {
      "loinc": "2345-7",
      "count": "integer"
    }
  },
  "total_diabetes_related_records": "integer",
  "unique_patients_with_diabetes": "integer"
}
```

---

## HDH-TRM-005: Code Mapping Challenge

**Difficulty**: expert

**Systems Required**: ehr

**Max Turns**: 25

### Description

Given a list of ICD-9 codes from legacy records, provide the equivalent ICD-10 codes. Then verify by finding if both codes appear for the same patients (indicating mapped data).

### Expected Response Format

```json
{
  "icd9_to_icd10_mappings": [
    {
      "icd9_code": "250.00",
      "icd9_display": "string",
      "icd10_equivalent": "E11.9",
      "icd10_display": "string",
      "patients_with_both": "integer"
    },
    {
      "icd9_code": "401.9",
      "icd9_display": "string",
      "icd10_equivalent": "I10",
      "icd10_display": "string",
      "patients_with_both": "integer"
    }
  ],
  "mapping_confidence": "high|medium|low"
}
```

---

## HDH-TRM-006: Cross-System Vocabulary Reconciliation

**Difficulty**: hard

**Systems Required**: ehr, pharmacy, billing

**Max Turns**: 25

### Description

The same medication may be coded differently across systems - RxNorm in Pharmacy, NDC in Billing, and free-text in EHR notes. For patient MRN-100042, reconcile all medication references to identify which refer to the same drug.

### Expected Response Format

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
      "sources": [
        "pharmacy",
        "billing",
        "ehr"
      ]
    }
  ],
  "unique_medications": "integer",
  "reconciliation_issues": [
    "list of unmatched codes"
  ]
}
```

---

## HDH-TRM-007: Local Code Translation

**Difficulty**: expert

**Systems Required**: lis

**Max Turns**: 30

### Description

Some lab tests use local/proprietary codes instead of LOINC. Find Observations in LIS that use non-standard code systems and attempt to map them to standard LOINC codes based on the display name and units.

### Expected Response Format

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
  "unmappable_codes": [
    "list of codes that couldn't be mapped"
  ]
}
```

---

## HDH-TRM-008: Multi-Axial Code Resolution

**Difficulty**: expert

**Systems Required**: ehr, billing

**Max Turns**: 30

### Description

A diagnosis may be represented with different granularity across systems - SNOMED-CT in clinical notes (detailed), ICD-10-CM for billing (required specificity), ICD-9 in legacy data. Find all representations of 'Type 2 Diabetes with complications' and map them together.

### Expected Response Format

```json
{
  "concept": "Type 2 Diabetes with complications",
  "code_clusters": [
    {
      "clinical_concept": "string (specific complication)",
      "codes": {
        "icd10": [
          "list of E11.x codes"
        ],
        "icd9": [
          "list of 250.xx codes"
        ],
        "snomed": [
          "list of SNOMED codes if found"
        ]
      },
      "patient_count": "integer"
    }
  ],
  "total_diabetes_codes_found": "integer",
  "unmapped_codes": [
    "list of codes not fitting known patterns"
  ]
}
```

---

