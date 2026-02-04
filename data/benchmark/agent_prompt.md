# Healthcare Data Integration Task

You are an AI agent tasked with querying and integrating data from a hospital's healthcare information systems.

## Environment

You have access to 6 healthcare systems, each exposing FHIR R4 REST APIs. Each system maintains its own patient registry with its own ID scheme. There is NO shared patient identifier across systems.

## Available Systems

| System | Base URL | Description |
|--------|----------|-------------|
| EHR | http://localhost:8001 | Electronic Health Records - patient demographics, conditions |
| LIS | http://localhost:8002 | Laboratory - lab orders and results |
| RIS | http://localhost:8003 | Radiology - imaging orders and studies |
| Pharmacy | http://localhost:8005 | Pharmacy - medication orders |
| PAS | http://localhost:8006 | Patient Administration - encounters |
| Billing | http://localhost:8007 | Billing - claims and coverage |

## API Reference

All systems implement standard FHIR R4 REST endpoints:

```
GET /fhir/r4/{ResourceType}              # Search/list resources
GET /fhir/r4/{ResourceType}/{id}         # Get resource by ID
GET /fhir/r4/{ResourceType}?param=value  # Search with parameters
GET /fhir/r4/metadata                    # Get capability statement
```

### Common Search Parameters

- `subject=Patient/{id}` - Filter by patient reference
- `patient={id}` - Alternative patient filter
- `code={code}` - Filter by code (e.g., ICD-10, LOINC)
- `status={status}` - Filter by status
- `_count={n}` - Limit results
- `_offset={n}` - Pagination offset

### Resources by System

**EHR (localhost:8001)**
- Patient - demographics, identifiers
- Condition - diagnoses (ICD-10 coded)

**LIS (localhost:8002)**
- Patient - lab system patient registry
- ServiceRequest - lab orders
- Observation - lab results (LOINC coded)

**RIS (localhost:8003)**
- Patient - radiology patient registry
- ServiceRequest - imaging orders

**Pharmacy (localhost:8005)**
- Patient - pharmacy patient registry
- MedicationRequest - prescriptions (RxNorm coded)

**PAS (localhost:8006)**
- Patient - ADT patient registry
- Encounter - visits, admissions

**Billing (localhost:8007)**
- Patient - billing patient registry
- Claim - insurance claims

## Important Notes

1. **No Shared Patient ID**: Each system has its own patient ID scheme. To find the same patient across systems, you must match on demographics (name, DOB, etc.).

2. **Data Quality Varies**: Real healthcare data has inconsistencies - name spelling variations, missing fields, duplicate records.

3. **FHIR References**: Related resources reference patients like `"subject": {"reference": "Patient/MRN-100042"}` - the ID is system-specific.

## Example Queries

```bash
# List patients in EHR
curl http://localhost:8001/fhir/r4/Patient

# Get specific patient
curl http://localhost:8001/fhir/r4/Patient/MRN-100001

# Find conditions for a patient
curl "http://localhost:8001/fhir/r4/Condition?subject=Patient/MRN-100001"

# Search lab results by LOINC code
curl "http://localhost:8002/fhir/r4/Observation?code=2345-7"

# Find medications for a patient
curl "http://localhost:8005/fhir/r4/MedicationRequest?subject=Patient/RX-400001"
```

## Your Tasks

Complete the benchmark queries provided. For each query, return your results in the specified JSON format.

---

*This prompt is provided by the Healthcare Data Harmony Benchmark. Do not request additional hints or ground truth data.*
