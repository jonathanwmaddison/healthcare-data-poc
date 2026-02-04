# Unstructured Data Tasks

Tasks requiring extraction and understanding of unstructured clinical text (notes, documents, free-text fields)

---

## HDH-UNS-001: Extract Diagnoses from Clinical Notes

**Difficulty**: medium

**Systems Required**: ehr

**Max Turns**: 20

### Description

Clinical notes in the EHR contain diagnoses mentioned in free text that may not be coded. Find DocumentReference resources and extract any diagnoses mentioned in the text content. Compare with coded Conditions to find uncoded diagnoses.

### Expected Response Format

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

## HDH-UNS-002: Parse Medication Instructions

**Difficulty**: medium

**Systems Required**: pharmacy

**Max Turns**: 15

### Description

MedicationRequest resources have dosageInstruction with free-text 'text' fields like 'Take 1 tablet by mouth twice daily with food'. Parse these to extract structured dosing information (dose, route, frequency, timing).

### Expected Response Format

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

## HDH-UNS-003: Reconcile Free-Text Allergies

**Difficulty**: hard

**Systems Required**: ehr, pharmacy

**Max Turns**: 25

### Description

AllergyIntolerance resources may have allergies recorded as free text (e.g., 'Patient reports penicillin allergy - rash') or coded (RxNorm/SNOMED). Find all allergies and normalize them to identify duplicates and conflicts.

### Expected Response Format

```json
{
  "total_allergy_records": "integer",
  "coded_allergies": "integer",
  "freetext_allergies": "integer",
  "normalized_allergies": [
    {
      "allergen": "string (normalized name)",
      "records": [
        "list of allergy record IDs"
      ],
      "systems": [
        "list of source systems"
      ],
      "is_duplicate": "boolean",
      "conflict": "string or null"
    }
  ],
  "duplicate_count": "integer",
  "conflict_count": "integer"
}
```

---

## HDH-UNS-004: Extract Lab Comments

**Difficulty**: hard

**Systems Required**: lis

**Max Turns**: 20

### Description

Lab Observation resources often have interpretive comments in the 'note' field (e.g., 'Critical value - physician notified', 'Hemolyzed specimen - results may be affected'). Extract and categorize these comments to identify critical values and quality issues.

### Expected Response Format

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

## HDH-UNS-005: Cross-System Note Reconciliation

**Difficulty**: expert

**Systems Required**: ehr, lis, billing

**Max Turns**: 35

### Description

The same clinical event may be documented differently across systems - a procedure note in EHR, a result comment in LIS, and a charge description in Billing. For a specific patient, find related documentation across systems and link them to the same clinical event.

### Expected Response Format

```json
{
  "patient_queried": "string",
  "clinical_events": [
    {
      "event_date": "string",
      "event_type": "string",
      "linked_records": {
        "ehr_documents": [
          "list of document IDs"
        ],
        "lis_observations": [
          "list of observation IDs"
        ],
        "billing_claims": [
          "list of claim IDs"
        ]
      },
      "description": "string (synthesized from all sources)"
    }
  ],
  "total_events_identified": "integer"
}
```

---

