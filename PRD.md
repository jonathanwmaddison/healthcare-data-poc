# Healthcare Data System POC - Product Requirements Document

## Executive Summary

This document specifies a dockerized proof-of-concept (POC) that replicates the **API interfaces and data structures** found in a large hospital/medical system. The focus is on realistic FHIR R4-compliant APIs, authentic data models, and inter-system communication patterns.

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Healthcare Data Platform                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │     EHR     │  │     LIS     │  │     RIS     │  │    PACS     │        │
│  │  (Patient   │  │(Laboratory) │  │ (Radiology) │  │  (Imaging)  │        │
│  │  Records)   │  │             │  │             │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐        │
│  │ PostgreSQL  │  │ PostgreSQL  │  │ PostgreSQL  │  │  MinIO/S3   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │  Pharmacy   │  │   Billing   │  │     PAS     │                         │
│  │   System    │  │   System    │  │(Admissions) │                         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│         │                │                │                                 │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐                         │
│  │ PostgreSQL  │  │ PostgreSQL  │  │ PostgreSQL  │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │                    Integration Engine (Mirth-style)                │     │
│  │         RabbitMQ Message Broker + Event Router Service             │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │                         API Gateway (Kong/Nginx)                   │     │
│  │                    Authentication, Rate Limiting                   │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Systems & Their FHIR Resources

### 2.1 EHR (Electronic Health Record)
**Purpose**: Central repository for patient clinical data

**FHIR Resources Managed**:
| Resource | Description |
|----------|-------------|
| `Patient` | Demographics, identifiers, contact info |
| `Practitioner` | Healthcare providers |
| `PractitionerRole` | Provider roles and specialties |
| `Organization` | Hospitals, clinics, departments |
| `Encounter` | Patient visits (inpatient, outpatient, ER) |
| `Condition` | Diagnoses (ICD-10 coded) |
| `AllergyIntolerance` | Patient allergies |
| `Procedure` | Performed procedures (CPT/SNOMED coded) |
| `CarePlan` | Treatment plans |
| `CareTeam` | Care coordination |
| `DocumentReference` | Clinical documents, notes |

**API Endpoints** (FHIR R4 compliant):
```
GET    /fhir/r4/Patient/{id}
GET    /fhir/r4/Patient?identifier={mrn}
GET    /fhir/r4/Patient?name={name}&birthdate={dob}
POST   /fhir/r4/Patient
PUT    /fhir/r4/Patient/{id}
GET    /fhir/r4/Encounter?patient={patient_id}
GET    /fhir/r4/Condition?patient={patient_id}
GET    /fhir/r4/AllergyIntolerance?patient={patient_id}
GET    /fhir/r4/Procedure?patient={patient_id}
POST   /fhir/r4/Bundle (transaction bundles)
```

---

### 2.2 LIS (Laboratory Information System)
**Purpose**: Manage lab orders, specimen tracking, and results

**FHIR Resources Managed**:
| Resource | Description |
|----------|-------------|
| `ServiceRequest` | Lab orders (LOINC coded) |
| `Specimen` | Sample collection details |
| `Observation` | Individual test results |
| `DiagnosticReport` | Complete lab reports |
| `Task` | Workflow status tracking |

**API Endpoints**:
```
POST   /fhir/r4/ServiceRequest              # Create lab order
GET    /fhir/r4/ServiceRequest/{id}
GET    /fhir/r4/ServiceRequest?patient={id}&status=active
PUT    /fhir/r4/ServiceRequest/{id}         # Update order status

POST   /fhir/r4/Specimen
GET    /fhir/r4/Specimen?request={service_request_id}

POST   /fhir/r4/Observation                 # Post individual result
GET    /fhir/r4/Observation?patient={id}&category=laboratory
GET    /fhir/r4/Observation?code={loinc_code}

POST   /fhir/r4/DiagnosticReport            # Complete report
GET    /fhir/r4/DiagnosticReport/{id}
GET    /fhir/r4/DiagnosticReport?patient={id}&category=LAB
```

**Lab Order Workflow**:
```
1. EHR creates ServiceRequest (status: active)
2. LIS receives order via message queue
3. Specimen collected (Specimen resource created)
4. Lab runs tests
5. Observations created for each test result
6. DiagnosticReport created (references Observations)
7. ServiceRequest status updated to "completed"
8. Results sent back to EHR
```

---

### 2.3 RIS (Radiology Information System)
**Purpose**: Manage imaging orders, scheduling, and reports

**FHIR Resources Managed**:
| Resource | Description |
|----------|-------------|
| `ServiceRequest` | Imaging orders |
| `Appointment` | Scheduling |
| `ImagingStudy` | DICOM study metadata |
| `DiagnosticReport` | Radiology reports |
| `Observation` | Findings/measurements |

**API Endpoints**:
```
POST   /fhir/r4/ServiceRequest              # Create imaging order
GET    /fhir/r4/ServiceRequest?patient={id}&category=imaging

POST   /fhir/r4/Appointment
GET    /fhir/r4/Appointment?patient={id}&service-type=imaging
PUT    /fhir/r4/Appointment/{id}            # Reschedule/cancel

GET    /fhir/r4/ImagingStudy/{id}
GET    /fhir/r4/ImagingStudy?patient={id}
GET    /fhir/r4/ImagingStudy?identifier={accession_number}

POST   /fhir/r4/DiagnosticReport            # Radiology report
GET    /fhir/r4/DiagnosticReport?patient={id}&category=RAD
```

---

### 2.4 PACS (Picture Archiving and Communication System)
**Purpose**: Store and serve medical images (DICOM)

**APIs** (DICOMweb + FHIR reference):
```
# DICOMweb WADO-RS (retrieve)
GET    /dicomweb/studies/{studyUID}
GET    /dicomweb/studies/{studyUID}/series/{seriesUID}
GET    /dicomweb/studies/{studyUID}/series/{seriesUID}/instances/{instanceUID}
GET    /dicomweb/studies/{studyUID}/rendered          # Get rendered image

# DICOMweb STOW-RS (store)
POST   /dicomweb/studies

# DICOMweb QIDO-RS (query)
GET    /dicomweb/studies?PatientID={id}
GET    /dicomweb/studies?AccessionNumber={accession}

# FHIR Reference
GET    /fhir/r4/ImagingStudy/{id}           # Returns DICOMweb endpoints
```

---

### 2.5 Pharmacy System
**Purpose**: Medication orders, dispensing, and inventory

**FHIR Resources Managed**:
| Resource | Description |
|----------|-------------|
| `Medication` | Drug catalog (RxNorm coded) |
| `MedicationRequest` | Prescriptions/orders |
| `MedicationDispense` | Dispensing records |
| `MedicationAdministration` | Administration records |
| `MedicationStatement` | Patient-reported meds |

**API Endpoints**:
```
GET    /fhir/r4/Medication?code={rxnorm}
GET    /fhir/r4/Medication?_text={drug_name}

POST   /fhir/r4/MedicationRequest           # New prescription
GET    /fhir/r4/MedicationRequest/{id}
GET    /fhir/r4/MedicationRequest?patient={id}&status=active
PUT    /fhir/r4/MedicationRequest/{id}      # Modify/cancel

POST   /fhir/r4/MedicationDispense          # Record dispensing
GET    /fhir/r4/MedicationDispense?patient={id}
GET    /fhir/r4/MedicationDispense?prescription={med_request_id}

POST   /fhir/r4/MedicationAdministration    # Record administration
GET    /fhir/r4/MedicationAdministration?patient={id}
```

**Medication Workflow**:
```
1. Provider creates MedicationRequest in EHR
2. Pharmacy receives order (status: active)
3. Pharmacist reviews, may modify
4. MedicationDispense created when filled
5. Nurse records MedicationAdministration
6. All systems sync via integration engine
```

---

### 2.6 PAS (Patient Administration System)
**Purpose**: Admissions, discharges, transfers (ADT), scheduling

**FHIR Resources Managed**:
| Resource | Description |
|----------|-------------|
| `Patient` | Master patient index |
| `Encounter` | Admission/visit records |
| `EpisodeOfCare` | Longitudinal care episodes |
| `Appointment` | Scheduling |
| `Schedule` | Provider/resource availability |
| `Slot` | Bookable time slots |
| `Location` | Beds, rooms, departments |

**API Endpoints**:
```
# Patient Registration
POST   /fhir/r4/Patient                     # Register new patient
PUT    /fhir/r4/Patient/{id}                # Update demographics
GET    /fhir/r4/Patient/$match              # MPI matching

# ADT Operations
POST   /fhir/r4/Encounter                   # Admit patient
PUT    /fhir/r4/Encounter/{id}              # Transfer/update
GET    /fhir/r4/Encounter?patient={id}&status=in-progress
GET    /fhir/r4/Encounter?location={ward_id}&status=in-progress

# Scheduling
GET    /fhir/r4/Schedule?actor={practitioner_id}
GET    /fhir/r4/Slot?schedule={id}&status=free
POST   /fhir/r4/Appointment
PUT    /fhir/r4/Appointment/{id}            # Confirm/cancel
```

**ADT Events Published**:
```
- ADT^A01: Patient Admitted
- ADT^A02: Patient Transferred
- ADT^A03: Patient Discharged
- ADT^A04: Patient Registered (outpatient)
- ADT^A08: Patient Information Updated
- ADT^A11: Cancel Admission
```

---

### 2.7 Billing System
**Purpose**: Claims processing, insurance, and financial data

**FHIR Resources Managed**:
| Resource | Description |
|----------|-------------|
| `Claim` | Healthcare claims |
| `ClaimResponse` | Adjudication results |
| `ExplanationOfBenefit` | EOB statements |
| `Coverage` | Insurance coverage |
| `Account` | Patient financial account |
| `Invoice` | Billing invoices |
| `ChargeItem` | Billable items |

**API Endpoints**:
```
# Coverage
GET    /fhir/r4/Coverage?patient={id}
GET    /fhir/r4/Coverage?beneficiary={patient_id}&status=active
POST   /fhir/r4/Coverage

# Claims
POST   /fhir/r4/Claim                       # Submit claim
GET    /fhir/r4/Claim/{id}
GET    /fhir/r4/Claim?patient={id}
POST   /fhir/r4/Claim/$submit               # Submit for adjudication

# EOB
GET    /fhir/r4/ExplanationOfBenefit?patient={id}
GET    /fhir/r4/ExplanationOfBenefit?claim={claim_id}

# Accounts
GET    /fhir/r4/Account?patient={id}
POST   /fhir/r4/ChargeItem                  # Post charges
```

---

## 3. Integration Engine

### 3.1 Message Broker (RabbitMQ)

**Exchanges**:
```
healthcare.events     (topic exchange)
healthcare.commands   (direct exchange)
healthcare.dlx        (dead letter exchange)
```

**Routing Keys**:
```
adt.admit
adt.discharge
adt.transfer
adt.update
lab.order.new
lab.order.cancel
lab.result.preliminary
lab.result.final
rad.order.new
rad.study.completed
rad.report.final
pharmacy.order.new
pharmacy.dispense.complete
billing.charge.posted
```

### 3.2 Event Schema (CloudEvents format)
```json
{
  "specversion": "1.0",
  "type": "org.hl7.fhir.r4.ServiceRequest.created",
  "source": "/ehr/orders",
  "id": "uuid",
  "time": "2024-01-15T10:30:00Z",
  "datacontenttype": "application/fhir+json",
  "data": {
    "resourceType": "ServiceRequest",
    ...
  }
}
```

---

## 4. Data Models (Realistic Examples)

### 4.1 Patient (EHR)
```json
{
  "resourceType": "Patient",
  "id": "pat-12345",
  "meta": {
    "versionId": "1",
    "lastUpdated": "2024-01-15T10:00:00Z"
  },
  "identifier": [
    {
      "use": "usual",
      "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
      "system": "http://hospital.example.org/mrn",
      "value": "MRN-123456"
    },
    {
      "use": "official",
      "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "SS"}]},
      "system": "http://hl7.org/fhir/sid/us-ssn",
      "value": "123-45-6789"
    }
  ],
  "active": true,
  "name": [
    {
      "use": "official",
      "family": "Smith",
      "given": ["John", "Robert"],
      "prefix": ["Mr."]
    }
  ],
  "telecom": [
    {"system": "phone", "value": "(555) 123-4567", "use": "home"},
    {"system": "email", "value": "john.smith@email.com"}
  ],
  "gender": "male",
  "birthDate": "1980-07-15",
  "address": [
    {
      "use": "home",
      "line": ["123 Main Street", "Apt 4B"],
      "city": "Boston",
      "state": "MA",
      "postalCode": "02108",
      "country": "USA"
    }
  ],
  "maritalStatus": {
    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus", "code": "M"}]
  },
  "contact": [
    {
      "relationship": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0131", "code": "N"}]}],
      "name": {"family": "Smith", "given": ["Jane"]},
      "telecom": [{"system": "phone", "value": "(555) 987-6543"}]
    }
  ],
  "communication": [
    {"language": {"coding": [{"system": "urn:ietf:bcp:47", "code": "en"}]}, "preferred": true}
  ]
}
```

### 4.2 Lab Order (LIS)
```json
{
  "resourceType": "ServiceRequest",
  "id": "laborder-789",
  "identifier": [
    {"system": "http://hospital.example.org/orders", "value": "ORD-2024-00789"}
  ],
  "status": "active",
  "intent": "order",
  "category": [
    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}
  ],
  "priority": "routine",
  "code": {
    "coding": [
      {"system": "http://loinc.org", "code": "24323-8", "display": "Comprehensive metabolic panel"}
    ]
  },
  "subject": {"reference": "Patient/pat-12345"},
  "encounter": {"reference": "Encounter/enc-456"},
  "occurrenceDateTime": "2024-01-15T14:00:00Z",
  "requester": {"reference": "Practitioner/pract-001"},
  "performer": [{"reference": "Organization/lab-001"}],
  "reasonCode": [
    {"coding": [{"system": "http://snomed.info/sct", "code": "267036007", "display": "Dyspnea"}]}
  ],
  "specimen": [{"reference": "Specimen/spec-123"}],
  "note": [{"text": "Fasting specimen required"}]
}
```

### 4.3 Lab Result (LIS)
```json
{
  "resourceType": "DiagnosticReport",
  "id": "labreport-456",
  "identifier": [
    {"system": "http://hospital.example.org/reports", "value": "RPT-2024-00456"}
  ],
  "basedOn": [{"reference": "ServiceRequest/laborder-789"}],
  "status": "final",
  "category": [
    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "LAB"}]}
  ],
  "code": {
    "coding": [{"system": "http://loinc.org", "code": "24323-8", "display": "Comprehensive metabolic panel"}]
  },
  "subject": {"reference": "Patient/pat-12345"},
  "effectiveDateTime": "2024-01-15T16:30:00Z",
  "issued": "2024-01-15T17:00:00Z",
  "performer": [{"reference": "Organization/lab-001"}],
  "result": [
    {"reference": "Observation/obs-glucose"},
    {"reference": "Observation/obs-sodium"},
    {"reference": "Observation/obs-potassium"},
    {"reference": "Observation/obs-creatinine"}
  ],
  "conclusion": "All values within normal limits"
}
```

### 4.4 Lab Observation (LIS)
```json
{
  "resourceType": "Observation",
  "id": "obs-glucose",
  "status": "final",
  "category": [
    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}
  ],
  "code": {
    "coding": [{"system": "http://loinc.org", "code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma"}]
  },
  "subject": {"reference": "Patient/pat-12345"},
  "effectiveDateTime": "2024-01-15T16:30:00Z",
  "valueQuantity": {
    "value": 95,
    "unit": "mg/dL",
    "system": "http://unitsofmeasure.org",
    "code": "mg/dL"
  },
  "referenceRange": [
    {
      "low": {"value": 70, "unit": "mg/dL"},
      "high": {"value": 100, "unit": "mg/dL"},
      "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/referencerange-meaning", "code": "normal"}]}
    }
  ],
  "interpretation": [
    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": "N", "display": "Normal"}]}
  ]
}
```

### 4.5 Medication Request (Pharmacy)
```json
{
  "resourceType": "MedicationRequest",
  "id": "medrx-001",
  "identifier": [
    {"system": "http://hospital.example.org/prescriptions", "value": "RX-2024-00123"}
  ],
  "status": "active",
  "intent": "order",
  "category": [
    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category", "code": "inpatient"}]}
  ],
  "medicationCodeableConcept": {
    "coding": [
      {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "197361", "display": "Lisinopril 10 MG Oral Tablet"}
    ]
  },
  "subject": {"reference": "Patient/pat-12345"},
  "encounter": {"reference": "Encounter/enc-456"},
  "authoredOn": "2024-01-15T10:00:00Z",
  "requester": {"reference": "Practitioner/pract-001"},
  "dosageInstruction": [
    {
      "sequence": 1,
      "text": "Take 1 tablet by mouth once daily",
      "timing": {
        "repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}
      },
      "route": {"coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]},
      "doseAndRate": [
        {
          "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/dose-rate-type", "code": "ordered"}]},
          "doseQuantity": {"value": 1, "unit": "tablet", "system": "http://terminology.hl7.org/CodeSystem/v3-orderableDrugForm", "code": "TAB"}
        }
      ]
    }
  ],
  "dispenseRequest": {
    "numberOfRepeatsAllowed": 3,
    "quantity": {"value": 30, "unit": "tablet"},
    "expectedSupplyDuration": {"value": 30, "unit": "days", "system": "http://unitsofmeasure.org", "code": "d"}
  }
}
```

### 4.6 Imaging Study (RIS/PACS)
```json
{
  "resourceType": "ImagingStudy",
  "id": "imgstudy-001",
  "identifier": [
    {"system": "urn:dicom:uid", "value": "urn:oid:2.16.124.113543.6003.1154777499.30246.19789.3503430045"},
    {"system": "http://hospital.example.org/accession", "value": "ACC-2024-00567"}
  ],
  "status": "available",
  "subject": {"reference": "Patient/pat-12345"},
  "encounter": {"reference": "Encounter/enc-456"},
  "started": "2024-01-15T11:00:00Z",
  "basedOn": [{"reference": "ServiceRequest/radorder-123"}],
  "endpoint": [{"reference": "Endpoint/pacs-wado"}],
  "numberOfSeries": 2,
  "numberOfInstances": 45,
  "procedureCode": [
    {"coding": [{"system": "http://loinc.org", "code": "36643-5", "display": "XR Chest 2 Views"}]}
  ],
  "location": {"reference": "Location/rad-room-1"},
  "series": [
    {
      "uid": "2.16.124.113543.6003.1154777499.30246.19789.3503430046",
      "number": 1,
      "modality": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR"},
      "description": "PA View",
      "numberOfInstances": 1,
      "bodySite": {"system": "http://snomed.info/sct", "code": "51185008", "display": "Thorax"},
      "instance": [
        {
          "uid": "2.16.124.113543.6003.1154777499.30246.19789.3503430047",
          "sopClass": {"system": "urn:ietf:rfc:3986", "code": "urn:oid:1.2.840.10008.5.1.4.1.1.1.1"},
          "number": 1
        }
      ]
    }
  ]
}
```

---

## 5. Terminology & Code Systems

| Code System | Usage | Example |
|-------------|-------|---------|
| **LOINC** | Lab tests, observations | `2345-7` (Glucose) |
| **SNOMED CT** | Clinical findings, procedures | `267036007` (Dyspnea) |
| **ICD-10-CM** | Diagnoses | `E11.9` (Type 2 DM) |
| **CPT** | Procedures (billing) | `99213` (Office visit) |
| **RxNorm** | Medications | `197361` (Lisinopril 10mg) |
| **HCPCS** | Medical equipment, services | `J1030` (Methylprednisolone) |
| **NDC** | Drug products | `0591-0405-01` |

---

## 6. Authentication & Security

### 6.1 SMART on FHIR OAuth 2.0
```
Authorization Server: /auth
Token Endpoint:       /auth/token
Authorize Endpoint:   /auth/authorize

Scopes:
- patient/*.read
- patient/*.write
- user/*.read
- user/*.write
- launch
- launch/patient
- openid
- fhirUser
```

### 6.2 JWT Token Structure
```json
{
  "iss": "https://auth.hospital.example.org",
  "sub": "user-123",
  "aud": "https://fhir.hospital.example.org",
  "exp": 1705330800,
  "iat": 1705327200,
  "scope": "patient/*.read user/Practitioner.read",
  "fhirUser": "Practitioner/pract-001",
  "patient": "pat-12345"
}
```

### 6.3 Audit Logging (FHIR AuditEvent)
All API access logged with:
- Who (user/system)
- What (resource type, ID)
- When (timestamp)
- Where (source system)
- Why (purpose of use)

---

## 7. Technical Stack

| Component | Technology |
|-----------|------------|
| **API Services** | Python 3.11 + FastAPI |
| **Databases** | PostgreSQL 15 (per service) |
| **Message Broker** | RabbitMQ 3.12 |
| **Object Storage** | MinIO (DICOM images) |
| **API Gateway** | Kong or Nginx |
| **Cache** | Redis 7 |
| **Container Runtime** | Docker + Docker Compose |
| **Auth** | Keycloak (SMART on FHIR) |

---

## 8. Docker Services

```yaml
services:
  # Infrastructure
  - postgres-ehr
  - postgres-lis
  - postgres-ris
  - postgres-pharmacy
  - postgres-pas
  - postgres-billing
  - rabbitmq
  - redis
  - minio
  - keycloak

  # Application Services
  - ehr-service          (port 8001)
  - lis-service          (port 8002)
  - ris-service          (port 8003)
  - pacs-service         (port 8004)
  - pharmacy-service     (port 8005)
  - pas-service          (port 8006)
  - billing-service      (port 8007)
  - integration-engine   (port 8008)
  - api-gateway          (port 8000)
```

---

## 9. Seed Data

The POC will include realistic seed data:

- **50 patients** with varied demographics
- **10 practitioners** across specialties
- **5 organizations** (hospital, clinics, lab, pharmacy)
- **100 encounters** (mix of inpatient, outpatient, ER)
- **200 lab orders/results** with realistic values
- **50 imaging studies** with DICOM metadata
- **150 medication orders** with common drugs
- **Sample ADT event history**
- **Insurance coverage records**

---

## 10. API Documentation

Each service will expose:
- **OpenAPI/Swagger** spec at `/docs`
- **FHIR CapabilityStatement** at `/fhir/r4/metadata`
- **Health check** at `/health`

---

## 11. Success Criteria

1. All services start successfully with `docker-compose up`
2. Each service exposes FHIR R4 compliant APIs
3. Inter-service communication works via RabbitMQ
4. Sample workflows complete end-to-end:
   - Patient admission → triggers ADT event
   - Lab order → results → back to EHR
   - Imaging order → study completion → report
   - Medication order → dispense → administration
5. APIs return properly formatted FHIR resources
6. OAuth 2.0 authentication functions

---

## References

- [HL7 FHIR R4 Specification](https://www.hl7.org/fhir/)
- [Epic on FHIR Documentation](https://fhir.epic.com/Documentation)
- [FHIR Diagnostics Module](https://www.hl7.org/fhir/diagnostics-module.html)
- [FHIR Medications Module](https://www.hl7.org/fhir/medications-module.html)
- [Da Vinci ADT Notifications](https://build.fhir.org/ig/HL7/davinci-alerts/usecases.html)
- [DICOMweb Standard](https://www.dicomstandard.org/using/dicomweb)
- [SMART on FHIR](https://docs.smarthealthit.org/)
