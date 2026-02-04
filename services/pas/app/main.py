"""PAS Service - Patient Administration System
Manages patient registration, ADT events, and scheduling:
- Patient (Master Patient Index)
- Encounter (admissions, visits)
- Appointment
- Schedule/Slot
- Location (beds, rooms)
"""
import os
import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import HTTPException
from shared.base_service import FHIRService, create_fhir_app

SUPPORTED_RESOURCES = [
    "Patient",
    "Encounter",
    "Appointment",
    "Schedule",
    "Slot",
    "Location",
    "EpisodeOfCare",
]

# ADT Event Types
ADT_EVENTS = {
    "A01": "Patient Admitted",
    "A02": "Patient Transferred",
    "A03": "Patient Discharged",
    "A04": "Patient Registered",
    "A08": "Patient Information Updated",
    "A11": "Cancel Admission",
    "A12": "Cancel Transfer",
    "A13": "Cancel Discharge",
}

# Hospital locations
LOCATIONS = [
    {"id": "loc-er", "name": "Emergency Room", "type": "ER"},
    {"id": "loc-icu", "name": "Intensive Care Unit", "type": "ICU"},
    {"id": "loc-med-surg", "name": "Medical-Surgical Unit", "type": "WARD"},
    {"id": "loc-peds", "name": "Pediatrics", "type": "WARD"},
    {"id": "loc-ob", "name": "Obstetrics", "type": "WARD"},
    {"id": "loc-or", "name": "Operating Room", "type": "OR"},
    {"id": "loc-radiology", "name": "Radiology Department", "type": "DEPT"},
    {"id": "loc-lab", "name": "Laboratory", "type": "DEPT"},
    {"id": "loc-pharmacy", "name": "Pharmacy", "type": "DEPT"},
    {"id": "loc-outpatient", "name": "Outpatient Clinic", "type": "CLINIC"},
]


class PASService(FHIRService):
    """PAS-specific service with ADT support"""

    def __init__(self):
        super().__init__("pas", SUPPORTED_RESOURCES)

    async def setup(self):
        await super().setup()
        await self._seed_locations()
        await self._seed_data()

    async def _seed_locations(self):
        """Pre-populate hospital locations"""
        for loc in LOCATIONS:
            try:
                self.create_resource("Location", {
                    "id": loc["id"],
                    "status": "active",
                    "name": loc["name"],
                    "mode": "instance",
                    "type": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode", "code": loc["type"]}]}],
                    "physicalType": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/location-physical-type", "code": "wa" if loc["type"] == "WARD" else "ro"}]}
                })
            except Exception:
                pass
        print("Hospital locations loaded")

    async def _seed_data(self):
        seed_path = Path("/app/data/seed/pas_seed.json")
        if not seed_path.exists():
            seed_path = Path("data/seed/pas_seed.json")

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
                print("PAS seed data loaded")
            except Exception as e:
                print(f"Error loading seed data: {e}")


service = PASService()
app = create_fhir_app(service)


# ===================
# ADT Operations
# ===================

@app.post("/fhir/r4/Encounter/$admit")
async def admit_patient(patient_id: str, location_id: str = "loc-med-surg", encounter_class: str = "IMP"):
    """ADT A01 - Admit patient"""
    encounter_id = str(uuid.uuid4())
    account_number = f"ACCT-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

    encounter = {
        "resourceType": "Encounter",
        "id": encounter_id,
        "identifier": [{"system": "http://hospital.example.org/encounters", "value": account_number}],
        "status": "in-progress",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": encounter_class, "display": "inpatient encounter" if encounter_class == "IMP" else encounter_class},
        "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "183452005", "display": "Inpatient stay"}]}],
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {"start": datetime.utcnow().isoformat() + "Z"},
        "location": [{"location": {"reference": f"Location/{location_id}"}, "status": "active", "period": {"start": datetime.utcnow().isoformat() + "Z"}}],
        "hospitalization": {
            "admitSource": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/admit-source", "code": "emd", "display": "Emergency Department"}]},
            "preAdmissionIdentifier": {"value": f"PRE-{random.randint(1000, 9999)}"}
        }
    }
    service.create_resource("Encounter", encounter)

    # Publish ADT A01 event
    await service.publish_event("adt.a01", {
        "eventType": "A01",
        "eventDescription": ADT_EVENTS["A01"],
        "encounter": encounter,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

    return {"message": "Patient admitted", "encounter": f"Encounter/{encounter_id}", "eventType": "ADT^A01"}


@app.post("/fhir/r4/Encounter/{encounter_id}/$transfer")
async def transfer_patient(encounter_id: str, new_location_id: str):
    """ADT A02 - Transfer patient"""
    encounter = service.read_resource("Encounter", encounter_id)

    # End current location
    for loc in encounter.get("location", []):
        if loc.get("status") == "active":
            loc["status"] = "completed"
            loc["period"]["end"] = datetime.utcnow().isoformat() + "Z"

    # Add new location
    encounter["location"].append({
        "location": {"reference": f"Location/{new_location_id}"},
        "status": "active",
        "period": {"start": datetime.utcnow().isoformat() + "Z"}
    })

    service.update_resource("Encounter", encounter_id, encounter)

    await service.publish_event("adt.a02", {
        "eventType": "A02",
        "eventDescription": ADT_EVENTS["A02"],
        "encounter": encounter,
        "newLocation": new_location_id,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

    return {"message": "Patient transferred", "encounter": f"Encounter/{encounter_id}", "eventType": "ADT^A02"}


@app.post("/fhir/r4/Encounter/{encounter_id}/$discharge")
async def discharge_patient(encounter_id: str, disposition: str = "home"):
    """ADT A03 - Discharge patient"""
    encounter = service.read_resource("Encounter", encounter_id)

    encounter["status"] = "finished"
    encounter["period"]["end"] = datetime.utcnow().isoformat() + "Z"

    # End current location
    for loc in encounter.get("location", []):
        if loc.get("status") == "active":
            loc["status"] = "completed"
            loc["period"]["end"] = datetime.utcnow().isoformat() + "Z"

    # Set discharge disposition
    encounter["hospitalization"] = encounter.get("hospitalization", {})
    encounter["hospitalization"]["dischargeDisposition"] = {
        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/discharge-disposition", "code": disposition}]
    }

    service.update_resource("Encounter", encounter_id, encounter)

    await service.publish_event("adt.a03", {
        "eventType": "A03",
        "eventDescription": ADT_EVENTS["A03"],
        "encounter": encounter,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

    return {"message": "Patient discharged", "encounter": f"Encounter/{encounter_id}", "eventType": "ADT^A03"}


@app.post("/fhir/r4/Patient/$register")
async def register_patient(patient_data: dict):
    """ADT A04 - Register outpatient"""
    # Generate MRN
    mrn = f"MRN-{random.randint(100000, 999999)}"

    patient_data["identifier"] = patient_data.get("identifier", [])
    patient_data["identifier"].append({
        "use": "usual",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
        "system": "http://hospital.example.org/mrn",
        "value": mrn
    })

    patient = service.create_resource("Patient", patient_data)

    await service.publish_event("adt.a04", {
        "eventType": "A04",
        "eventDescription": ADT_EVENTS["A04"],
        "patient": patient,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

    return {"message": "Patient registered", "patient": f"Patient/{patient['id']}", "mrn": mrn, "eventType": "ADT^A04"}


# ===================
# Scheduling
# ===================

@app.post("/fhir/r4/Appointment")
async def create_appointment(appointment_data: dict):
    """Create a new appointment"""
    appointment_data["id"] = appointment_data.get("id") or str(uuid.uuid4())
    appointment_data["status"] = appointment_data.get("status", "booked")
    appointment_data["created"] = datetime.utcnow().isoformat() + "Z"

    result = service.create_resource("Appointment", appointment_data)
    return result


@app.get("/fhir/r4/Appointment/$availability")
async def check_availability(
    practitioner: str = None,
    location: str = None,
    date: str = None,
    service_type: str = None
):
    """Check appointment availability"""
    # Generate sample available slots
    slots = []
    base_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()

    for hour in [9, 10, 11, 13, 14, 15, 16]:
        slot_start = base_date.replace(hour=hour, minute=0, second=0)
        if slot_start > datetime.now():  # Only future slots
            slots.append({
                "resourceType": "Slot",
                "id": str(uuid.uuid4()),
                "status": "free",
                "start": slot_start.isoformat() + "Z",
                "end": (slot_start + timedelta(minutes=30)).isoformat() + "Z"
            })

    return {"resourceType": "Bundle", "type": "searchset", "total": len(slots), "entry": [{"resource": s} for s in slots]}


@app.get("/fhir/r4/Encounter/$census")
async def get_census(location: str = None):
    """Get current patient census"""
    params = {"status": "in-progress"}
    if location:
        params["location"] = location

    results = service.search_resources("Encounter", params)

    # Group by location
    census = {}
    for entry in results.get("entry", []):
        enc = entry.get("resource", {})
        for loc in enc.get("location", []):
            if loc.get("status") == "active":
                loc_ref = loc.get("location", {}).get("reference", "Unknown")
                census[loc_ref] = census.get(loc_ref, 0) + 1

    return {"census": census, "total": len(results.get("entry", []))}
