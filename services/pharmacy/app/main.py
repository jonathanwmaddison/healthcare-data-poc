"""Pharmacy Service - Pharmacy Information System
Manages medication orders, dispensing, and inventory:
- Medication (drug catalog)
- MedicationRequest (prescriptions)
- MedicationDispense (dispensing records)
- MedicationAdministration (administration records)
"""
import os
import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from shared.base_service import FHIRService, create_fhir_app

SUPPORTED_RESOURCES = [
    "Medication",
    "MedicationRequest",
    "MedicationDispense",
    "MedicationAdministration",
    "MedicationStatement",
]

# Common medications with RxNorm codes
MEDICATIONS = {
    "197361": {"name": "Lisinopril 10 MG Oral Tablet", "form": "TAB", "dose": "10", "unit": "mg"},
    "314076": {"name": "Lisinopril 20 MG Oral Tablet", "form": "TAB", "dose": "20", "unit": "mg"},
    "197381": {"name": "Atorvastatin 20 MG Oral Tablet", "form": "TAB", "dose": "20", "unit": "mg"},
    "617314": {"name": "Atorvastatin 40 MG Oral Tablet", "form": "TAB", "dose": "40", "unit": "mg"},
    "860975": {"name": "Metformin 500 MG Oral Tablet", "form": "TAB", "dose": "500", "unit": "mg"},
    "861007": {"name": "Metformin 1000 MG Oral Tablet", "form": "TAB", "dose": "1000", "unit": "mg"},
    "310965": {"name": "Amlodipine 5 MG Oral Tablet", "form": "TAB", "dose": "5", "unit": "mg"},
    "308136": {"name": "Amlodipine 10 MG Oral Tablet", "form": "TAB", "dose": "10", "unit": "mg"},
    "312961": {"name": "Omeprazole 20 MG Delayed Release Oral Capsule", "form": "CAP", "dose": "20", "unit": "mg"},
    "198211": {"name": "Omeprazole 40 MG Delayed Release Oral Capsule", "form": "CAP", "dose": "40", "unit": "mg"},
    "197591": {"name": "Furosemide 40 MG Oral Tablet", "form": "TAB", "dose": "40", "unit": "mg"},
    "197732": {"name": "Hydrochlorothiazide 25 MG Oral Tablet", "form": "TAB", "dose": "25", "unit": "mg"},
    "857005": {"name": "Acetaminophen 325 MG Oral Tablet", "form": "TAB", "dose": "325", "unit": "mg"},
    "198440": {"name": "Ibuprofen 400 MG Oral Tablet", "form": "TAB", "dose": "400", "unit": "mg"},
    "313850": {"name": "Gabapentin 300 MG Oral Capsule", "form": "CAP", "dose": "300", "unit": "mg"},
    "197319": {"name": "Levothyroxine 50 MCG Oral Tablet", "form": "TAB", "dose": "50", "unit": "mcg"},
    "311989": {"name": "Clopidogrel 75 MG Oral Tablet", "form": "TAB", "dose": "75", "unit": "mg"},
    "849727": {"name": "Aspirin 81 MG Delayed Release Oral Tablet", "form": "TAB", "dose": "81", "unit": "mg"},
    "245314": {"name": "Amoxicillin 500 MG Oral Capsule", "form": "CAP", "dose": "500", "unit": "mg"},
    "309114": {"name": "Azithromycin 250 MG Oral Tablet", "form": "TAB", "dose": "250", "unit": "mg"},
}


class PharmacyService(FHIRService):
    """Pharmacy-specific service"""

    def __init__(self):
        super().__init__("pharmacy", SUPPORTED_RESOURCES)

    async def setup(self):
        await super().setup()
        await self._seed_medications()
        await self._seed_data()

    async def _seed_medications(self):
        """Pre-populate medication catalog"""
        for rxnorm, med in MEDICATIONS.items():
            try:
                self.create_resource("Medication", {
                    "id": f"med-{rxnorm}",
                    "code": {
                        "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxnorm, "display": med["name"]}],
                        "text": med["name"]
                    },
                    "status": "active",
                    "form": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-orderableDrugForm", "code": med["form"]}]}
                })
            except Exception:
                pass
        print("Medication catalog loaded")

    async def _seed_data(self):
        seed_path = Path("/app/data/seed/pharmacy_seed.json")
        if not seed_path.exists():
            seed_path = Path("data/seed/pharmacy_seed.json")

        if seed_path.exists():
            try:
                with open(seed_path) as f:
                    seed_data = json.load(f)
                for entry in seed_data.get("entry", []):
                    resource = entry.get("resource", {})
                    resource_type = resource.get("resourceType")
                    if resource_type in self.supported_resources:
                        try:
                            self.create_resource(resource_type, resource)
                        except Exception:
                            pass
                print("Pharmacy seed data loaded")
            except Exception as e:
                print(f"Error loading seed data: {e}")


service = PharmacyService()
app = create_fhir_app(service)


@app.get("/fhir/r4/Medication/$lookup")
async def lookup_medication(code: str = None, name: str = None):
    """Look up medications by code or name"""
    results = []

    for rxnorm, med in MEDICATIONS.items():
        if code and rxnorm != code:
            continue
        if name and name.lower() not in med["name"].lower():
            continue

        results.append({
            "resourceType": "Medication",
            "id": f"med-{rxnorm}",
            "code": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": rxnorm, "display": med["name"]}],
                "text": med["name"]
            }
        })

    return {"resourceType": "Bundle", "type": "searchset", "total": len(results), "entry": [{"resource": r} for r in results]}


@app.post("/fhir/r4/MedicationRequest/{request_id}/$dispense")
async def dispense_medication(request_id: str):
    """Process a medication dispense"""
    # Get the prescription
    rx = service.read_resource("MedicationRequest", request_id)

    # Create dispense record
    dispense_id = str(uuid.uuid4())
    quantity = rx.get("dispenseRequest", {}).get("quantity", {"value": 30, "unit": "tablet"})

    dispense = {
        "resourceType": "MedicationDispense",
        "id": dispense_id,
        "identifier": [{"system": "http://hospital.example.org/dispense", "value": f"DISP-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"}],
        "status": "completed",
        "medicationCodeableConcept": rx.get("medicationCodeableConcept"),
        "subject": rx.get("subject"),
        "authorizingPrescription": [{"reference": f"MedicationRequest/{request_id}"}],
        "quantity": quantity,
        "daysSupply": rx.get("dispenseRequest", {}).get("expectedSupplyDuration", {"value": 30, "unit": "days"}),
        "whenPrepared": datetime.utcnow().isoformat() + "Z",
        "whenHandedOver": datetime.utcnow().isoformat() + "Z",
        "dosageInstruction": rx.get("dosageInstruction", []),
        "performer": [{"actor": {"reference": "Practitioner/pharmacist-001", "display": "Pharmacist"}}]
    }
    service.create_resource("MedicationDispense", dispense)

    # Update prescription status if all refills used
    repeats_allowed = rx.get("dispenseRequest", {}).get("numberOfRepeatsAllowed", 0)
    # Check existing dispenses
    existing = service.search_resources("MedicationDispense", {"prescription": request_id})
    if len(existing.get("entry", [])) >= repeats_allowed + 1:
        rx["status"] = "completed"
        service.update_resource("MedicationRequest", request_id, rx)

    await service.publish_event("dispensed", dispense)

    return {"message": "Medication dispensed", "medicationDispense": f"MedicationDispense/{dispense_id}"}


@app.post("/fhir/r4/MedicationDispense/{dispense_id}/$administer")
async def administer_medication(dispense_id: str):
    """Record medication administration"""
    dispense = service.read_resource("MedicationDispense", dispense_id)

    admin_id = str(uuid.uuid4())
    administration = {
        "resourceType": "MedicationAdministration",
        "id": admin_id,
        "status": "completed",
        "medicationCodeableConcept": dispense.get("medicationCodeableConcept"),
        "subject": dispense.get("subject"),
        "effectiveDateTime": datetime.utcnow().isoformat() + "Z",
        "performer": [{"actor": {"reference": "Practitioner/nurse-001", "display": "Nurse"}}],
        "dosage": {
            "text": dispense.get("dosageInstruction", [{}])[0].get("text", "As directed"),
            "route": {"coding": [{"system": "http://snomed.info/sct", "code": "26643006", "display": "Oral route"}]}
        }
    }
    service.create_resource("MedicationAdministration", administration)

    await service.publish_event("administered", administration)

    return {"message": "Medication administered", "medicationAdministration": f"MedicationAdministration/{admin_id}"}


@app.get("/fhir/r4/MedicationRequest/{patient_id}/$active")
async def get_active_medications(patient_id: str):
    """Get all active medications for a patient"""
    results = service.search_resources("MedicationRequest", {"patient": patient_id, "status": "active"})
    return results
