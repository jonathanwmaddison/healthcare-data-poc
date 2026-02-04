# Data Provenance Tasks

Tasks requiring understanding of data lineage and source of truth

---

## HDH-PRV-001: Identify Source System for Data Type

**Difficulty**: easy

**Systems Required**: ehr, lis, pharmacy

**Max Turns**: 15

### Description

Determine which system is the authoritative source for each type of clinical data. For example, which system should be queried for current medications? For diagnoses? For lab results?

### Expected Response Format

```json
{
  "source_of_truth": {
    "diagnoses": {
      "system": "string",
      "resource_type": "string"
    },
    "medications": {
      "system": "string",
      "resource_type": "string"
    },
    "lab_results": {
      "system": "string",
      "resource_type": "string"
    },
    "lab_orders": {
      "system": "string",
      "resource_type": "string"
    },
    "encounters": {
      "system": "string",
      "resource_type": "string"
    },
    "demographics": {
      "system": "string",
      "resource_type": "string"
    }
  },
  "reasoning": "string"
}
```

---

## HDH-PRV-002: Trace Lab Result to Order

**Difficulty**: medium

**Systems Required**: lis, pas

**Max Turns**: 15

### Description

Given a specific lab result (Observation), trace it back to its originating order (ServiceRequest) and the encounter/visit when it was ordered. Return the complete chain.

### Expected Response Format

```json
{
  "observation_id": "string",
  "provenance_chain": {
    "result": {
      "id": "string",
      "code": "string",
      "value": "string"
    },
    "order": {
      "id": "string",
      "code": "string",
      "authored_on": "string"
    },
    "encounter": {
      "id": "string",
      "type": "string",
      "date": "string"
    },
    "patient": {
      "id": "string",
      "name": "string"
    }
  }
}
```

---

## HDH-PRV-003: Identify Data Freshness

**Difficulty**: medium

**Systems Required**: ehr, lis, pharmacy, pas

**Max Turns**: 20

### Description

For a specific patient, determine the freshness of their data in each system. When was each system's data last updated? Which systems have stale data (>30 days old)?

### Expected Response Format

```json
{
  "patient_id_queried": "string (EHR ID)",
  "data_freshness": {
    "ehr": {
      "last_updated": "string",
      "days_old": "integer",
      "is_stale": "boolean"
    },
    "lis": {
      "last_updated": "string",
      "days_old": "integer",
      "is_stale": "boolean"
    },
    "pharmacy": {
      "last_updated": "string",
      "days_old": "integer",
      "is_stale": "boolean"
    },
    "pas": {
      "last_updated": "string",
      "days_old": "integer",
      "is_stale": "boolean"
    }
  },
  "stale_systems": [
    "list of systems with data >30 days old"
  ]
}
```

---

## HDH-PRV-004: Resolve Conflicting Data

**Difficulty**: hard

**Systems Required**: ehr, lis, pharmacy, billing

**Max Turns**: 30

### Description

Patient MRN-100042 has different values for the same attribute in different systems (e.g., different phone numbers, slightly different names). Identify all conflicts and recommend which value should be authoritative.

### Expected Response Format

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

## HDH-PRV-005: Build Complete Patient Timeline

**Difficulty**: expert

**Systems Required**: ehr, lis, pharmacy, pas

**Max Turns**: 40

### Description

Construct a complete timeline of all clinical events for patient MRN-100042 across all systems. Include diagnoses, lab orders/results, medication changes, and encounters in chronological order.

### Expected Response Format

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
  "date_range": {
    "start": "string",
    "end": "string"
  }
}
```

---

