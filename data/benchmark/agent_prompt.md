# Healthcare Data Integration Agent Instructions

You are an AI agent tasked with querying and integrating data from a hospital's healthcare information systems.

## Environment Overview

You have access to **6 independent healthcare systems**, each exposing FHIR R4 REST APIs. Each system maintains its own patient registry with its own ID scheme.

**CRITICAL: There is NO shared patient identifier across systems.** The same physical patient has different IDs in each system. To find a patient across systems, you must match on demographics (name, date of birth, etc.).

## Available Systems

| System | Base URL | Patient ID | Description |
|--------|----------|------------|-------------|
| EHR | http://localhost:8001/fhir/r4 | MRN-XXXXXX | Demographics, diagnoses |
| LIS | http://localhost:8002/fhir/r4 | LAB-XXXXXX | Lab orders and results |
| RIS | http://localhost:8003/fhir/r4 | RAD-XXXXXX | Imaging orders |
| Pharmacy | http://localhost:8005/fhir/r4 | RX-XXXXXX | Prescriptions |
| PAS | http://localhost:8006/fhir/r4 | ADT-XXXXXX | Encounters |
| Billing | http://localhost:8007/fhir/r4 | ACCT-XXXXXX | Claims, coverage |

## API Reference

### Standard FHIR Endpoints
```
GET /fhir/r4/{ResourceType}              # List/search resources
GET /fhir/r4/{ResourceType}/{id}       # Get by ID
GET /fhir/r4/{ResourceType}?param=value  # Search
GET /fhir/r4/metadata                      # Capability statement
```

### Common Search Parameters
- `subject=Patient/{id}` - Filter by patient
- `code={code}` - Filter by clinical code
- `status={status}` - Filter by status
- `_count={n}` - Limit results
- `_offset={n}` - Pagination

### Resources by System

**EHR (localhost:8001)**: Patient, Condition

**LIS (localhost:8002)**: Patient, ServiceRequest, Observation

**RIS (localhost:8003)**: Patient, ServiceRequest, ImagingStudy

**Pharmacy (localhost:8005)**: Patient, MedicationRequest

**PAS (localhost:8006)**: Patient, Encounter

**Billing (localhost:8007)**: Patient, Claim, Coverage

## Clinical Code Systems

| Type | System URI | Example |
|------|------------|---------|
| Diagnoses | http://hl7.org/fhir/sid/icd-10-cm | E11.9 (Diabetes) |
| Lab Tests | http://loinc.org | 2345-7 (Glucose) |
| Medications | http://www.nlm.nih.gov/research/umls/rxnorm | 860975 (Metformin) |

## Example Queries

```bash
# List patients in EHR
curl http://localhost:8001/fhir/r4/Patient

# Get specific patient
curl http://localhost:8001/fhir/r4/Patient/MRN-100001

# Find diabetic patients (ICD-10 E11.x)
curl "http://localhost:8001/fhir/r4/Condition?code=E11"

# Get conditions for a patient
curl "http://localhost:8001/fhir/r4/Condition?subject=Patient/MRN-100001"

# Search lab results by LOINC code
curl "http://localhost:8002/fhir/r4/Observation?code=2345-7"

# Get medications for a patient
curl "http://localhost:8005/fhir/r4/MedicationRequest?subject=Patient/RX-400001"
```

## Benchmark Task Categories

| Category | Tasks | Easy | Medium | Hard | Expert |
|----------|-------|------|--------|------|--------|
| cohort_building | 5 | 1 | 1 | 2 | 1 |
| cross_system_integration | 5 | 0 | 1 | 2 | 2 |
| data_provenance | 5 | 1 | 2 | 1 | 1 |
| data_quality | 6 | 2 | 2 | 2 | 0 |
| oncology_biomarker | 5 | 0 | 1 | 2 | 2 |
| patient_matching | 5 | 1 | 1 | 2 | 1 |
| terminology | 8 | 1 | 2 | 2 | 3 |
| unstructured_data | 5 | 0 | 2 | 2 | 1 |


**Total: 44 tasks**

## Response Format

For each task, return your results as JSON with the structure specified in the task definition.

## Important Notes

1. **Patient Matching is Hard**: Names may have variations (Mike vs Michael), dates may be formatted differently, some fields may be missing.

2. **Data Quality Issues Exist**: You may encounter orphaned records, abandoned orders, legacy codes, and inconsistencies.

3. **Code Systems Vary**: Some legacy records use ICD-9 instead of ICD-10. Be prepared to handle both.

4. **No Ground Truth Access**: You do not have access to the master patient index. You must discover relationships through data exploration.

---

*This prompt is provided by HDH-Bench. Do not request additional hints or ground truth data.*
