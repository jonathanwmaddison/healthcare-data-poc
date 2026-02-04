# Healthcare Data System POC

A dockerized proof-of-concept replicating a large hospital's healthcare data infrastructure with realistic FHIR R4 APIs.

## Quick Start

```bash
docker-compose up --build
```

That's it! All services will start automatically with seed data.

## Services

| Service | Port | Description |
|---------|------|-------------|
| **API Gateway** | 8000 | Unified entry point |
| **EHR** | 8001 | Electronic Health Records |
| **LIS** | 8002 | Laboratory Information System |
| **RIS** | 8003 | Radiology Information System |
| **PACS** | 8004 | Picture Archiving (DICOMweb) |
| **Pharmacy** | 8005 | Medication Management |
| **PAS** | 8006 | Patient Administration (ADT) |
| **Billing** | 8007 | Claims & Coverage |
| **Integration Engine** | 8008 | Message Routing |
| **RabbitMQ** | 15672 | Message Broker UI |
| **MinIO** | 9001 | Object Storage UI |

## API Examples

### Get a Patient
```bash
curl http://localhost:8000/ehr/fhir/r4/Patient/pat-001
```

### Search Patients
```bash
curl "http://localhost:8000/ehr/fhir/r4/Patient?name=Smith"
```

### Create Lab Order
```bash
curl -X POST http://localhost:8000/lis/fhir/r4/ServiceRequest \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "ServiceRequest",
    "status": "active",
    "intent": "order",
    "code": {"coding": [{"system": "http://loinc.org", "code": "24323-8", "display": "Comprehensive metabolic panel"}]},
    "subject": {"reference": "Patient/pat-001"}
  }'
```

### Process Lab Order (generates results)
```bash
curl -X POST http://localhost:8000/lis/fhir/r4/ServiceRequest/{order_id}/\$process
```

### Admit Patient
```bash
curl -X POST "http://localhost:8000/pas/fhir/r4/Encounter/\$admit?patient_id=pat-001&location_id=loc-med-surg"
```

### Create Medication Order
```bash
curl -X POST http://localhost:8000/pharmacy/fhir/r4/MedicationRequest \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "MedicationRequest",
    "status": "active",
    "intent": "order",
    "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "197361", "display": "Lisinopril 10 MG"}]},
    "subject": {"reference": "Patient/pat-001"},
    "dosageInstruction": [{"text": "Take 1 tablet daily"}]
  }'
```

### Dispense Medication
```bash
curl -X POST http://localhost:8000/pharmacy/fhir/r4/MedicationRequest/{rx_id}/\$dispense
```

### Submit Insurance Claim
```bash
curl -X POST http://localhost:8000/billing/fhir/r4/Claim/{claim_id}/\$submit
```

## FHIR Resources by System

### EHR (Electronic Health Record)
- Patient, Practitioner, Organization
- Encounter, Condition, Procedure
- AllergyIntolerance, Observation

### LIS (Laboratory)
- ServiceRequest (lab orders)
- Specimen, Observation
- DiagnosticReport

### RIS (Radiology)
- ServiceRequest (imaging orders)
- Appointment, ImagingStudy
- DiagnosticReport

### PACS (Imaging)
- DICOMweb QIDO-RS (query)
- DICOMweb WADO-RS (retrieve)
- DICOMweb STOW-RS (store)

### Pharmacy
- Medication, MedicationRequest
- MedicationDispense
- MedicationAdministration

### PAS (Patient Administration)
- Patient (MPI)
- Encounter (ADT)
- Appointment, Schedule, Slot
- Location

### Billing
- Coverage, Claim
- ClaimResponse, ExplanationOfBenefit
- ChargeItem, Account

## Message Events

The integration engine routes events via RabbitMQ:

| Event | Description |
|-------|-------------|
| `adt.a01` | Patient Admitted |
| `adt.a02` | Patient Transferred |
| `adt.a03` | Patient Discharged |
| `lab.result.final` | Lab Results Ready |
| `rad.report.final` | Radiology Report Ready |
| `pharmacy.dispense` | Medication Dispensed |
| `billing.charge.posted` | Charge Posted |

## Code Systems

| System | Usage |
|--------|-------|
| LOINC | Lab tests |
| SNOMED CT | Clinical terms |
| ICD-10-CM | Diagnoses |
| RxNorm | Medications |
| CPT | Procedures |

## Seed Data

Pre-loaded with:
- 5 patients with demographics
- 2 practitioners
- Medical conditions & allergies
- Lab and imaging orders
- Medication prescriptions
- Insurance coverage

## API Documentation

Each service provides Swagger docs:
- EHR: http://localhost:8001/docs
- LIS: http://localhost:8002/docs
- RIS: http://localhost:8003/docs
- PACS: http://localhost:8004/docs
- Pharmacy: http://localhost:8005/docs
- PAS: http://localhost:8006/docs
- Billing: http://localhost:8007/docs

FHIR CapabilityStatement:
```bash
curl http://localhost:8001/fhir/r4/metadata
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway (:8000)                   │
└─────────────────────────────────────────────────────────┘
         │         │         │         │         │
    ┌────┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
    │  EHR   │ │  LIS  │ │  RIS  │ │Pharmacy│ │  PAS  │
    │ :8001  │ │ :8002 │ │ :8003 │ │ :8005  │ │ :8006 │
    └────┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
         │         │         │         │         │
         └─────────┴────┬────┴─────────┴─────────┘
                        │
              ┌─────────┴─────────┐
              │   Integration     │
              │   Engine :8008    │
              └─────────┬─────────┘
                        │
              ┌─────────┴─────────┐
              │    RabbitMQ       │
              │   :5672/:15672    │
              └───────────────────┘
```

## License

MIT
