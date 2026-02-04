# Realism Gaps: POC vs Real Healthcare Systems

## 1. Patient Identity Crisis (MPI Problems)

### Real World:
```
EHR:      MRN-12345  "John Smith"      DOB: 03/15/1980
LIS:      LAB-98765  "SMITH, JOHN R"   DOB: 3/15/80
RIS:      RAD-55555  "John R. Smith"   DOB: 1980-03-15
Pharmacy: RX-11111   "SMITH,JOHN"      DOB: 03/15/1980
Billing:  ACCT-9999  "John Robert Smith" DOB: March 15, 1980
```

Each system has its OWN patient ID. A Master Patient Index (MPI) tries to link them.
Duplicates are common - same patient registered 3 times with different MRNs.

### Our POC:
All systems use the same `Patient/pat-00123` ID. Unrealistically clean.

---

## 2. Data Synchronization Delays

### Real World:
```
Time 0:00  - Lab order placed in EHR
Time 0:05  - HL7 ORM message sent to LIS
Time 0:06  - LIS receives, creates internal order (new ID)
Time 0:10  - Specimen collected, LIS updated
Time 2:30  - Lab runs test, results entered
Time 2:35  - HL7 ORU message sent back to EHR
Time 2:40  - EHR receives, but nurse doesn't see it until refresh
Time 3:00  - Results finally visible in EHR

PROBLEM: If LIS is down, orders queue up for hours.
PROBLEM: Results may post to LIS but HL7 interface fails - EHR never gets them.
```

### Our POC:
Synchronous API calls. No delays, no failures, no queue backlogs.

---

## 3. Vendor-Specific Data Models

### Real World (Epic vs Cerner vs Meditech):

**Epic:**
```json
{
  "PatientID": "E12345",
  "PatientName": {
    "LastName": "SMITH",
    "FirstName": "JOHN",
    "MiddleName": "ROBERT"
  },
  "DOB": "1980-03-15T00:00:00",
  "SmartDataElements": { ... }  // Epic-specific
}
```

**Cerner:**
```json
{
  "person_id": 12345,
  "name_full_formatted": "Smith, John Robert",
  "birth_date": "1980-03-15",
  "millennium_person_alias": [ ... ]  // Cerner-specific
}
```

**Lab System (Sunquest):**
```
PID|1||98765^^^LAB||SMITH^JOHN^R||19800315|M|||...
```

Each vendor has completely different schemas. FHIR is supposed to fix this,
but most data exchange still happens via HL7 v2 (1990s format).

### Our POC:
All systems use identical FHIR R4 models. Unrealistically standardized.

---

## 4. Historical/Legacy Data

### Real World:
```
2010 records: ICD-9 codes (250.00 = Diabetes)
2016 records: ICD-10 codes (E11.9 = Diabetes)
2020 records: Some SNOMED, some ICD-10, some free text

Old lab results might reference tests that no longer exist.
Historical vitals might be in different units (Fahrenheit vs Celsius).
Scanned documents from 1995 - just PDFs, no structured data.
```

### Our POC:
All data uses current coding systems. No legacy format variations.

---

## 5. Incomplete/Orphaned Records

### Real World:
```
- Lab result exists but order was deleted (orphaned result)
- Order exists but was never resulted (abandoned order)
- Encounter closed but charges never posted
- Medication discontinued but refill requests keep coming
- Patient merged, but old MRN still has active orders
- Provider left practice but is still "requester" on old orders
```

### Our POC:
Clean referential relationships. Every order has a patient, every result has an order.

---

## 6. Interface Translation Losses

### Real World HL7 v2 to FHIR translation:
```
HL7 v2 OBX segment:
OBX|1|NM|2345-7^Glucose^LN||95|mg/dL|70-100|N|||F

Lost in translation:
- Performing lab information
- Specimen collection details
- Result comments/notes
- Abnormal flag qualifiers
- Order control codes

FHIR Observation created might be missing 30% of original data.
```

### Our POC:
Native FHIR throughout. No translation losses.

---

## 7. Security/Access Fragmentation

### Real World:
```
- Dr. Smith can see patients in Cardiology EHR
- Dr. Smith CANNOT see same patient's Psych notes (separate system)
- Lab tech can see lab orders but NOT clinical notes
- Billing can see charges but NOT clinical details
- Patient portal shows SOME but not all results
- Research database has de-identified subset

Break-the-glass audit when accessing VIP/employee records.
Consent directives that block certain providers.
```

### Our POC:
No authentication. Everyone sees everything.

---

## 8. Real-Time Data Conflicts

### Real World:
```
Scenario: Patient in ER
- ER doc orders CBC
- Inpatient admission happens simultaneously
- Admitting doc ALSO orders CBC
- Two CBCs drawn, two results, which one is "the" result?

Scenario: Duplicate medication orders
- Provider A orders Lisinopril 10mg in clinic
- Provider B (covering) orders Lisinopril 20mg in ER
- Patient now has two active Lisinopril orders
- Pharmacy has to call to reconcile
```

### Our POC:
No conflict detection. No duplicate checking.

---

## What Would Make This More Realistic

1. **Add MPI with duplicates** - Same patient with multiple MRNs
2. **Add message queuing delays** - Results take 30+ seconds to propagate
3. **Add interface failures** - 5% of messages fail, need retry
4. **Add legacy data** - Mix of ICD-9, ICD-10, free text
5. **Add orphaned records** - Orders without results, results without orders
6. **Add data translation layer** - HL7 v2 to FHIR with loss
7. **Add authentication/RBAC** - Different views per role
8. **Add audit logging** - Who accessed what when
9. **Add stale data** - Last updated timestamps, version conflicts
10. **Add vendor variations** - Different field mappings per source

---

## Summary

| Aspect | POC | Real World |
|--------|-----|------------|
| Patient ID consistency | Same ID everywhere | Different ID per system |
| Data format | All FHIR R4 | HL7v2, FHIR, proprietary, CSV |
| Synchronization | Instant | Minutes to hours |
| Data quality | 90% clean | 60-70% clean |
| Referential integrity | 100% | 80-90% |
| Historical consistency | 100% ICD-10 | Mixed ICD-9/10/SNOMED/text |
| Duplicates | None | 5-15% duplicate patients |
| Access control | None | Complex RBAC |

This POC is a **clean room** version of healthcare data. Real healthcare data
is more like a **crime scene** - messy, contradictory, and full of surprises.
