# FHIR R4 Quick Reference for HDH-Bench

## Base Pattern

All systems expose standard FHIR R4 REST APIs:

```
GET /fhir/r4/{ResourceType}              # List/search resources
GET /fhir/r4/{ResourceType}/{id}         # Get by ID
GET /fhir/r4/{ResourceType}?param=value  # Search with parameters
GET /fhir/r4/metadata                    # Capability statement
```

## Systems Overview

| System | Port | Patient ID Format | Key Resources |
|--------|------|-------------------|---------------|
| EHR | 8001 | MRN-XXXXXX | Patient, Condition |
| LIS | 8002 | LAB-XXXXXX | Patient, ServiceRequest, Observation |
| RIS | 8003 | RAD-XXXXXX | Patient, ServiceRequest, ImagingStudy |
| Pharmacy | 8005 | RX-XXXXXX | Patient, MedicationRequest |
| PAS | 8006 | ADT-XXXXXX | Patient, Encounter |
| Billing | 8007 | ACCT-XXXXXX | Patient, Claim, Coverage |

## Common Search Parameters

### Patient Searches
```bash
# Search by name
curl "http://localhost:8001/fhir/r4/Patient?name=Smith"

# Search by birth date
curl "http://localhost:8001/fhir/r4/Patient?birthdate=1980-03-15"

# Get specific patient
curl "http://localhost:8001/fhir/r4/Patient/MRN-100001"
```

### Clinical Data Searches
```bash
# Get conditions for a patient
curl "http://localhost:8001/fhir/r4/Condition?subject=Patient/MRN-100001"

# Search conditions by ICD-10 code
curl "http://localhost:8001/fhir/r4/Condition?code=E11"

# Get lab results for a patient
curl "http://localhost:8002/fhir/r4/Observation?subject=Patient/LAB-200001"

# Search labs by LOINC code
curl "http://localhost:8002/fhir/r4/Observation?code=2345-7"

# Get medications for a patient
curl "http://localhost:8005/fhir/r4/MedicationRequest?subject=Patient/RX-400001"
```

### Pagination
```bash
# Get first 50 records
curl "http://localhost:8001/fhir/r4/Patient?_count=50"

# Get next page
curl "http://localhost:8001/fhir/r4/Patient?_count=50&_offset=50"
```

## Code Systems

### Diagnoses (ICD-10-CM)
System URI: `http://hl7.org/fhir/sid/icd-10-cm`

| Code | Description |
|------|-------------|
| E11.9 | Type 2 diabetes mellitus |
| I10 | Essential hypertension |
| E78.5 | Hyperlipidemia |
| J44.9 | COPD |
| F32.9 | Major depressive disorder |

### Lab Tests (LOINC)
System URI: `http://loinc.org`

| Code | Description |
|------|-------------|
| 2345-7 | Glucose |
| 4548-4 | Hemoglobin A1c (HbA1c) |
| 2160-0 | Creatinine |
| 718-7 | Hemoglobin |
| 2093-3 | Cholesterol |

### Medications (RxNorm)
System URI: `http://www.nlm.nih.gov/research/umls/rxnorm`

| Code | Description |
|------|-------------|
| 860975 | Metformin 500 MG |
| 314076 | Lisinopril 10 MG |
| 617311 | Atorvastatin 20 MG |
| 197361 | Amlodipine 5 MG |

## Response Format

FHIR Bundle response structure:

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

## Key FHIR Concepts

### Patient References
Clinical resources reference patients like this:
```json
"subject": {"reference": "Patient/MRN-100001"}
```

### Code/Coding Structure
```json
"code": {
  "coding": [
    {
      "system": "http://loinc.org",
      "code": "2345-7",
      "display": "Glucose"
    }
  ]
}
```

### Interpretation (Lab Results)
```json
"interpretation": [
  {"coding": [{"code": "H"}]}  // H=High, L=Low, N=Normal
]
```

## Critical: Patient ID Fragmentation

**The same patient has DIFFERENT IDs in each system!**

Example mapping (hidden from agents):
- EHR: MRN-100042
- LIS: LAB-200042
- RIS: RAD-300042
- Pharmacy: RX-400042
- PAS: ADT-500042
- Billing: ACCT-600042

To find the same patient across systems, you must **match on demographics** (name, DOB, etc.).
