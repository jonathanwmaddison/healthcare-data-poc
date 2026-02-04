"""EHR Service - Electronic Health Record System
Central repository for patient clinical data including:
- Patient demographics
- Encounters/visits
- Conditions/diagnoses
- Allergies
- Procedures
- Care plans
- Clinical documents
"""
import os
import json
from pathlib import Path
from shared.base_service import FHIRService, create_fhir_app

SUPPORTED_RESOURCES = [
    "Patient",
    "Practitioner",
    "PractitionerRole",
    "Organization",
    "Encounter",
    "Condition",
    "AllergyIntolerance",
    "Procedure",
    "CarePlan",
    "CareTeam",
    "DocumentReference",
    "Observation",  # Vitals, clinical observations
]


class EHRService(FHIRService):
    """EHR-specific service with additional functionality"""

    def __init__(self):
        super().__init__("ehr", SUPPORTED_RESOURCES)

    async def setup(self):
        await super().setup()
        await self._seed_data()

    async def _seed_data(self):
        """Load seed data on startup"""
        seed_path = Path("/app/data/seed/ehr_seed.json")
        if not seed_path.exists():
            seed_path = Path("data/seed/ehr_seed.json")

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
                            pass  # Skip duplicates
                print(f"EHR seed data loaded")
            except Exception as e:
                print(f"Error loading seed data: {e}")


service = EHRService()
app = create_fhir_app(service)


# Additional EHR-specific endpoints
@app.get("/fhir/r4/Patient/{patient_id}/$everything")
async def patient_everything(patient_id: str):
    """Return all data for a patient"""
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": []
    }

    # Get patient
    try:
        patient = service.read_resource("Patient", patient_id)
        bundle["entry"].append({"resource": patient})
    except Exception:
        pass

    # Get all related resources
    for resource_type in ["Encounter", "Condition", "AllergyIntolerance", "Procedure", "Observation"]:
        try:
            results = service.search_resources(resource_type, {"patient": patient_id})
            bundle["entry"].extend(results.get("entry", []))
        except Exception:
            pass

    bundle["total"] = len(bundle["entry"])
    return bundle
