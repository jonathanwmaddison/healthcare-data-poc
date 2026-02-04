# Data Quality Tasks

Tasks requiring detection and analysis of data quality issues

---

## HDH-DQ-001: Find Orphaned Lab Results

**Difficulty**: easy

**Systems Required**: lis

**Max Turns**: 15

### Description

Find lab results (Observations) in the LIS that do not have a corresponding order (no basedOn reference to a ServiceRequest). These are 'orphaned' results.

### Expected Response Format

```json
{
  "orphaned_count": "integer",
  "sample_orphaned_ids": [
    "list of up to 10 Observation IDs"
  ],
  "methodology": "string"
}
```

---

## HDH-DQ-002: Find Abandoned Orders

**Difficulty**: easy

**Systems Required**: lis

**Max Turns**: 15

### Description

Find lab orders (ServiceRequests) in the LIS that are still marked as 'active' but were created more than 100 days ago. These are likely abandoned orders that were never completed.

### Expected Response Format

```json
{
  "abandoned_count": "integer",
  "sample_abandoned_ids": [
    "list of up to 10 ServiceRequest IDs"
  ],
  "oldest_order_date": "string"
}
```

---

## HDH-DQ-003: Find Future-Dated Records

**Difficulty**: medium

**Systems Required**: ehr, lis, pharmacy

**Max Turns**: 20

### Description

Find any records across EHR, LIS, and Pharmacy that have dates in the future (data entry errors). Check effectiveDateTime, authoredOn, recordedDate fields.

### Expected Response Format

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

## HDH-DQ-004: Find Missing Required Fields

**Difficulty**: medium

**Systems Required**: ehr

**Max Turns**: 15

### Description

Audit Patient records in the EHR for data completeness. Find patients missing critical fields: birthDate, gender, or name. Report the completeness percentage.

### Expected Response Format

```json
{
  "total_patients": "integer",
  "completeness": {
    "birthDate": {
      "present": "integer",
      "missing": "integer",
      "percentage": "number"
    },
    "gender": {
      "present": "integer",
      "missing": "integer",
      "percentage": "number"
    },
    "name": {
      "present": "integer",
      "missing": "integer",
      "percentage": "number"
    }
  },
  "patients_missing_any_field": [
    "list of patient IDs"
  ]
}
```

---

## HDH-DQ-005: Cross-System Data Consistency

**Difficulty**: hard

**Systems Required**: ehr, lis, pharmacy, pas, billing

**Max Turns**: 40

### Description

For 10 randomly selected patients, compare their demographics (name, DOB, gender) across all systems where they exist. Report any inconsistencies.

### Expected Response Format

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

## HDH-DQ-006: Referential Integrity Check

**Difficulty**: hard

**Systems Required**: lis

**Max Turns**: 25

### Description

Check referential integrity in the LIS: Do all Observations reference valid Patients? Do all ServiceRequests reference valid Patients? Find and report broken references.

### Expected Response Format

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

