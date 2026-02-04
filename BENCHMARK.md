# Healthcare Data Benchmark

A realistic test environment for benchmarking agentic search systems and data harmonization pipelines.

## Quick Start

```bash
# 1. Clone and enter directory
cd healthcare-data-poc

# 2. Start all services (requires Docker)
docker-compose up -d

# 3. Wait for services to be healthy (~15 seconds)
docker-compose ps

# 4. Verify data is loaded
curl -s localhost:8001/fhir/r4/Patient | jq '.total'
# Should return ~1005

# 5. Give your agent the API catalog
cat data/benchmark/api_catalog.json

# 6. Run benchmark queries
cat data/benchmark/benchmark_queries.json

# 7. Score against ground truth (don't give this to the agent!)
cat data/benchmark/master_patient_index.json
```

## Prerequisites

- Docker and Docker Compose
- ~4GB RAM for all containers
- Ports 8001-8008, 5432, 5672, 6379, 9000-9001 available

## The Challenge

In real healthcare environments, patient data is fragmented across multiple systems, each with its own:
- Patient ID scheme
- Data format conventions
- API interface

An agent or data pipeline must:
1. **Discover** available data sources and their APIs
2. **Match** patient identities across systems (MPI problem)
3. **Query** and aggregate data from multiple sources
4. **Handle** data quality issues (duplicates, orphans, inconsistencies)

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway (:8000)                         │
├─────────┬─────────┬─────────┬─────────┬─────────┬─────────────┤
│   EHR   │   LIS   │   RIS   │ Pharmacy│   PAS   │   Billing   │
│ :8001   │ :8002   │ :8003   │ :8005   │ :8006   │   :8007     │
├─────────┼─────────┼─────────┼─────────┼─────────┼─────────────┤
│MRN-*    │LAB-*    │RAD-*    │RX-*     │ADT-*    │ACCT-*       │
│Patients │Patients │Patients │Patients │Patients │Patients     │
│Conditions│Orders  │Orders   │Meds     │Encounters│Claims      │
│         │Results  │Studies  │         │         │Coverage     │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────────┘
```

## Patient ID Fragmentation

The **same patient** has **different IDs** in each system:

| System   | ID Prefix | Example        |
|----------|-----------|----------------|
| EHR      | MRN-      | MRN-100042     |
| LIS      | LAB-      | LAB-200042     |
| RIS      | RAD-      | RAD-300042     |
| Pharmacy | RX-       | RX-400042      |
| PAS      | ADT-      | ADT-500042     |
| Billing  | ACCT-     | ACCT-600042    |

There is no cross-system patient ID. Matching requires demographic comparison.

## Data Quality Issues

Realistic problems agents must handle:

1. **Duplicate Patients** (~5%): Same person registered multiple times with different IDs
2. **Demographic Variations**: Name spelling, date formats differ across systems
3. **Orphaned Records**: Lab results without orders, orders without results
4. **ID Mismatches**: References to patients that don't exist in target system

## Benchmark Queries

Located in `data/benchmark/benchmark_queries.json`:

| ID   | Difficulty | Description |
|------|------------|-------------|
| Q001 | Medium     | Find all data for patient MRN-100042 |
| Q002 | Easy       | Find all diabetic patients (ICD-10 E11.x) |
| Q003 | Medium     | Find patients with abnormal glucose |
| Q004 | Hard       | Identify duplicate patient records |
| Q005 | Hard       | Diabetics on metformin with recent HbA1c |
| Q006 | Medium     | Find orphaned records / data quality issues |

## Ground Truth

`data/benchmark/master_patient_index.json` contains the answer key:

```json
{
  "canonical_id": "patient-00042",
  "demographics": { "first_name": "John", "last_name": "Smith", ... },
  "system_ids": {
    "ehr": "MRN-100042",
    "lis": "LAB-200042",
    "ris": "RAD-300042",
    "pharmacy": "RX-400042",
    "pas": "ADT-500042",
    "billing": "ACCT-600042"
  },
  "clinical_data": {
    "condition_ids": ["cond-abc123", ...],
    "medication_ids": ["med-def456", ...],
    ...
  }
}
```

## API Reference

Each system exposes standard FHIR R4 REST APIs:

### Common Endpoints
```
GET /{Resource}                    # List all
GET /{Resource}?subject=Patient/X  # Filter by patient
GET /{Resource}/{id}               # Get by ID
GET /{Resource}?_search=...        # Search
```

### System-Specific Resources

| System   | Base URL        | Resources                          |
|----------|-----------------|-------------------------------------|
| EHR      | localhost:8001  | Patient, Condition                  |
| LIS      | localhost:8002  | Patient, ServiceRequest, Observation|
| RIS      | localhost:8003  | Patient, ServiceRequest, ImagingStudy|
| Pharmacy | localhost:8005  | Patient, MedicationRequest          |
| PAS      | localhost:8006  | Patient, Encounter                  |
| Billing  | localhost:8007  | Patient, Claim, Coverage            |

### Example Queries

```bash
# Get patient from EHR
curl localhost:8001/Patient/MRN-100042

# Get same patient's lab results (different ID!)
curl "localhost:8002/Observation?subject=Patient/LAB-200042"

# Search for diabetics in EHR
curl "localhost:8001/Condition?code=E11"

# Get medications from pharmacy
curl "localhost:8005/MedicationRequest?subject=Patient/RX-400042"
```

## Scoring Agents

To score an agent's performance:

1. **Patient Matching Accuracy**
   - Ground truth: `master_patient_index.json`
   - Metric: % of correct cross-system ID matches

2. **Query Completeness**
   - For each benchmark query, compare agent results to expected
   - Metric: Precision, Recall, F1

3. **Data Quality Detection**
   - Count correctly identified duplicates, orphans
   - Metric: Detection rate

## Running the Benchmark

### Step 1: Start the Environment

```bash
# Start all services
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check health endpoints
curl localhost:8001/health  # EHR
curl localhost:8002/health  # LIS
curl localhost:8003/health  # RIS
curl localhost:8005/health  # Pharmacy
curl localhost:8006/health  # PAS
curl localhost:8007/health  # Billing
```

### Step 2: Provide Discovery Information to Agent

Give your agent the API catalog so it can discover available systems:

```bash
cat data/benchmark/api_catalog.json
```

This tells the agent:
- What systems exist and their base URLs
- What FHIR resources each system supports
- What patient ID prefix each system uses

**Do NOT give the agent the ground truth file (`master_patient_index.json`)** - that's for scoring only.

### Step 3: Run Benchmark Queries

Each query in `data/benchmark/benchmark_queries.json` is a task for the agent:

```bash
# View all queries
cat data/benchmark/benchmark_queries.json | jq '.queries[] | {id, description, difficulty}'
```

**Query Difficulty Levels:**
- **Easy**: Single-system query (e.g., find diabetics in EHR)
- **Medium**: Cross-reference within system or simple matching
- **Hard**: Cross-system queries requiring patient identity resolution

### Step 4: Score Results

Compare agent output against ground truth:

```bash
# Ground truth for patient matching
cat data/benchmark/master_patient_index.json | jq '.patients[0]'

# Expected results for each query
cat data/benchmark/benchmark_queries.json | jq '.queries[] | {id, expected_result}'
```

---

## Benchmark Query Details

### Q001: Patient 360 (Medium)
**Task**: Find all clinical data for patient with EHR MRN `MRN-100042`

**What agent must do**:
1. Query EHR for patient MRN-100042
2. Extract demographics (name, DOB)
3. Search other systems for matching patient
4. Aggregate conditions, labs, meds, encounters, claims

**Scoring**:
- Found correct patient in all 6 systems: +1 point each
- Retrieved all conditions: +1 point
- Retrieved all medications: +1 point
- Retrieved all lab results: +1 point

### Q002: Cohort - Diabetics (Easy)
**Task**: Find all patients with Type 2 Diabetes (ICD-10 E11.x)

**What agent must do**:
1. Query EHR Conditions with code filter
2. Extract patient references

```bash
# Example query
curl "localhost:8001/fhir/r4/Condition?code=E11" | jq '.entry[].resource.subject.reference'
```

**Scoring**: Precision and Recall vs expected count

### Q003: Cohort - Abnormal Glucose (Medium)
**Task**: Find patients with abnormal glucose lab results

**What agent must do**:
1. Query LIS Observations for LOINC 2345-7 (glucose)
2. Filter for interpretation H or L

```bash
# Example query
curl "localhost:8002/fhir/r4/Observation?code=2345-7" | jq '.entry[].resource | select(.interpretation[0].coding[0].code != "N")'
```

### Q004: Duplicate Detection (Hard)
**Task**: Identify duplicate patient records

**What agent must do**:
1. Query patients from multiple systems
2. Compare demographics to find likely matches
3. Identify same-person different-ID scenarios

**Scoring**: True positive rate for detected duplicates

### Q005: Cross-System Cohort (Hard)
**Task**: Find diabetics on metformin with recent HbA1c

**What agent must do**:
1. Find diabetics in EHR (Conditions)
2. Find patients on metformin in Pharmacy (MedicationRequest)
3. Find patients with HbA1c in LIS (Observation code 4548-4)
4. Match patients across systems by demographics
5. Intersect the three sets

### Q006: Data Quality (Medium)
**Task**: Find orphaned records

**What agent must do**:
1. Find Observations without basedOn reference (orphaned results)
2. Find old ServiceRequests with status=active (abandoned orders)

---

## Scoring Framework

### Patient Matching Score
```
Accuracy = Correct Matches / Total Attempted Matches

For each patient the agent claims to match across systems:
- True Positive: Agent match agrees with ground truth
- False Positive: Agent claims match but ground truth disagrees
- False Negative: Ground truth has match but agent missed it
```

### Query Completeness Score
```
For cohort queries:
- Precision = True Positives / (True Positives + False Positives)
- Recall = True Positives / (True Positives + False Negatives)
- F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

### Aggregate Benchmark Score
```
Total Score =
  (Q001 score * 0.20) +
  (Q002 score * 0.10) +
  (Q003 score * 0.15) +
  (Q004 score * 0.25) +
  (Q005 score * 0.20) +
  (Q006 score * 0.10)
```

---

## API Cheat Sheet

### Common FHIR Queries

```bash
# List all resources of a type
curl localhost:8001/fhir/r4/Patient

# Get specific resource by ID
curl localhost:8001/fhir/r4/Patient/MRN-100042

# Search by patient reference
curl "localhost:8002/fhir/r4/Observation?subject=Patient/LAB-200042"

# Search by code
curl "localhost:8001/fhir/r4/Condition?code=E11"

# Search by status
curl "localhost:8002/fhir/r4/ServiceRequest?status=active"

# Pagination
curl "localhost:8001/fhir/r4/Patient?_count=50&_offset=100"

# FHIR capability statement (discover supported resources)
curl localhost:8001/fhir/r4/metadata
```

### System-Specific Endpoints

| Query | System | Endpoint |
|-------|--------|----------|
| Get patient demographics | EHR | `GET :8001/fhir/r4/Patient/{id}` |
| Get conditions | EHR | `GET :8001/fhir/r4/Condition?subject=Patient/{id}` |
| Get lab orders | LIS | `GET :8002/fhir/r4/ServiceRequest?subject=Patient/{id}` |
| Get lab results | LIS | `GET :8002/fhir/r4/Observation?subject=Patient/{id}` |
| Get imaging orders | RIS | `GET :8003/fhir/r4/ServiceRequest?subject=Patient/{id}` |
| Get medications | Pharmacy | `GET :8005/fhir/r4/MedicationRequest?subject=Patient/{id}` |
| Get encounters | PAS | `GET :8006/fhir/r4/Encounter?subject=Patient/{id}` |
| Get claims | Billing | `GET :8007/fhir/r4/Claim?patient=Patient/{id}` |

## Data Statistics

- **Patients**: 1,000 unique patients × 6 systems = 6,000+ records (including duplicates)
- **Conditions**: ~3,000 (ICD-10 coded)
- **Medications**: ~2,000 (RxNorm coded)
- **Lab Orders**: ~1,500 with ~6,700 results
- **Imaging Orders**: ~1,000
- **Encounters**: ~3,000
- **Claims**: ~2,700

## Extending the Benchmark

Add new benchmark queries to `data/benchmark/benchmark_queries.json`:

```json
{
  "id": "Q007",
  "description": "Your query description",
  "difficulty": "easy|medium|hard",
  "hint": "Optional hint for agents",
  "expected_result": { ... }
}
```

Regenerate data with different parameters:

```python
# In scripts/generate_benchmark_data.py
generator = BenchmarkDataGenerator(num_patients=5000)  # More patients
```
