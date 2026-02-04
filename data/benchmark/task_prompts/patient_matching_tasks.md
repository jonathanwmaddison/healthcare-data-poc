# Patient Matching Tasks

Tasks requiring identification and matching of patient records across systems

---

## HDH-MPI-001: Find Patient in Two Systems

**Difficulty**: easy

**Systems Required**: ehr, lis

**Max Turns**: 10

### Description

Given patient ID MRN-100001 in the EHR system, find the same patient's ID in the LIS (Laboratory) system. The patient has the same demographics but a different ID format.

### Expected Response Format

```json
{
  "ehr_patient_id": "string",
  "lis_patient_id": "string",
  "matching_confidence": "high|medium|low",
  "matching_fields": [
    "array of fields used for matching"
  ]
}
```

### Hints (if enabled)

- **level_1**: Use patient demographics (name, date of birth) to match across systems
- **level_2**: The LIS uses patient IDs starting with 'LAB-'
- **level_3**: Try searching LIS patients by name extracted from the EHR patient

---

## HDH-MPI-002: Patient 360 View

**Difficulty**: medium

**Systems Required**: ehr, lis, ris, pharmacy, pas, billing

**Max Turns**: 25

### Description

Find all records for patient MRN-100042 across all 6 healthcare systems (EHR, LIS, RIS, Pharmacy, PAS, Billing). Return the patient ID used in each system.

### Expected Response Format

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

## HDH-MPI-003: Detect Duplicate Patients

**Difficulty**: hard

**Systems Required**: ehr

**Max Turns**: 30

### Description

Find patients in the EHR system that appear to be duplicates - the same real person registered multiple times with different MRNs. Return groups of patient IDs that likely represent the same person.

### Expected Response Format

```json
{
  "duplicate_groups": [
    {
      "patient_ids": [
        "array of MRNs believed to be same person"
      ],
      "confidence": "high|medium|low",
      "matching_evidence": {
        "name_similarity": "number 0-1",
        "dob_match": "boolean",
        "other_fields": [
          "list"
        ]
      }
    }
  ],
  "total_duplicate_groups_found": "integer",
  "methodology": "string describing approach"
}
```

---

## HDH-MPI-004: Cross-System Duplicate Detection

**Difficulty**: hard

**Systems Required**: ehr, lis, pharmacy, billing

**Max Turns**: 35

### Description

Find cases where the same patient appears to have duplicate records in DIFFERENT systems (not just duplicate MRNs within EHR). For example, a patient might have two different Pharmacy IDs that both belong to them.

### Expected Response Format

```json
{
  "cross_system_duplicates": [
    {
      "canonical_patient": "primary patient identifier",
      "duplicate_records": [
        {
          "system": "string",
          "patient_id": "string"
        }
      ],
      "confidence": "high|medium|low"
    }
  ]
}
```

---

## HDH-MPI-005: Probabilistic Patient Matching

**Difficulty**: expert

**Systems Required**: ehr, lis, pharmacy

**Max Turns**: 30

### Description

Given a patient record with partial/fuzzy demographics (name: 'J. Smith', DOB: '1980-03-??', phone partially matching), find the most likely matching patient across all systems. Return match probabilities.

### Expected Response Format

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
      "matching_fields": [
        "list"
      ],
      "mismatching_fields": [
        "list"
      ]
    }
  ],
  "recommended_match": {
    "patient_id": "string",
    "confidence": "number"
  }
}
```

---

