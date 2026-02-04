"""LIS Service - Laboratory Information System
Manages laboratory orders, specimen tracking, and results:
- ServiceRequest (lab orders)
- Specimen
- Observation (individual test results)
- DiagnosticReport (complete lab reports)
- Task (workflow tracking)
"""
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from shared.base_service import FHIRService, create_fhir_app

SUPPORTED_RESOURCES = [
    "Patient",  # Each system has its own patient registry
    "ServiceRequest",
    "Specimen",
    "Observation",
    "DiagnosticReport",
    "Task",
]

# Common lab panels with LOINC codes
LAB_PANELS = {
    "24323-8": {
        "name": "Comprehensive Metabolic Panel",
        "tests": [
            {"code": "2345-7", "name": "Glucose", "unit": "mg/dL", "range": [70, 100]},
            {"code": "2160-0", "name": "Creatinine", "unit": "mg/dL", "range": [0.7, 1.3]},
            {"code": "3094-0", "name": "BUN", "unit": "mg/dL", "range": [7, 20]},
            {"code": "2951-2", "name": "Sodium", "unit": "mEq/L", "range": [136, 145]},
            {"code": "2823-3", "name": "Potassium", "unit": "mEq/L", "range": [3.5, 5.0]},
            {"code": "2075-0", "name": "Chloride", "unit": "mEq/L", "range": [98, 106]},
            {"code": "2028-9", "name": "CO2", "unit": "mEq/L", "range": [23, 29]},
            {"code": "17861-6", "name": "Calcium", "unit": "mg/dL", "range": [8.5, 10.5]},
            {"code": "2885-2", "name": "Total Protein", "unit": "g/dL", "range": [6.0, 8.3]},
            {"code": "1751-7", "name": "Albumin", "unit": "g/dL", "range": [3.5, 5.0]},
            {"code": "1975-2", "name": "Total Bilirubin", "unit": "mg/dL", "range": [0.1, 1.2]},
            {"code": "6768-6", "name": "ALP", "unit": "U/L", "range": [44, 147]},
            {"code": "1742-6", "name": "ALT", "unit": "U/L", "range": [7, 56]},
            {"code": "1920-8", "name": "AST", "unit": "U/L", "range": [10, 40]},
        ]
    },
    "58410-2": {
        "name": "Complete Blood Count",
        "tests": [
            {"code": "6690-2", "name": "WBC", "unit": "x10^9/L", "range": [4.5, 11.0]},
            {"code": "789-8", "name": "RBC", "unit": "x10^12/L", "range": [4.5, 5.5]},
            {"code": "718-7", "name": "Hemoglobin", "unit": "g/dL", "range": [12.0, 17.5]},
            {"code": "4544-3", "name": "Hematocrit", "unit": "%", "range": [36, 50]},
            {"code": "777-3", "name": "Platelets", "unit": "x10^9/L", "range": [150, 400]},
        ]
    },
    "24331-1": {
        "name": "Lipid Panel",
        "tests": [
            {"code": "2093-3", "name": "Total Cholesterol", "unit": "mg/dL", "range": [0, 200]},
            {"code": "2571-8", "name": "Triglycerides", "unit": "mg/dL", "range": [0, 150]},
            {"code": "2085-9", "name": "HDL", "unit": "mg/dL", "range": [40, 60]},
            {"code": "13457-7", "name": "LDL (calculated)", "unit": "mg/dL", "range": [0, 100]},
        ]
    }
}


class LISService(FHIRService):
    """LIS-specific service with lab workflow support"""

    def __init__(self):
        super().__init__("lis", SUPPORTED_RESOURCES)

    async def setup(self):
        await super().setup()
        await self._seed_data()

    async def _seed_data(self):
        """Load seed data"""
        seed_path = Path("/app/data/seed/lis_seed.json")
        if not seed_path.exists():
            seed_path = Path("data/seed/lis_seed.json")

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
                print("LIS seed data loaded")
            except Exception as e:
                print(f"Error loading seed data: {e}")


service = LISService()
app = create_fhir_app(service)


@app.post("/fhir/r4/ServiceRequest/{order_id}/$process")
async def process_lab_order(order_id: str):
    """Simulate processing a lab order and generating results"""
    import random

    # Get the order
    order = service.read_resource("ServiceRequest", order_id)

    # Get panel code
    panel_code = None
    if order.get("code", {}).get("coding"):
        panel_code = order["code"]["coding"][0].get("code")

    panel = LAB_PANELS.get(panel_code, LAB_PANELS["24323-8"])

    # Create specimen
    specimen_id = str(uuid.uuid4())
    specimen = {
        "resourceType": "Specimen",
        "id": specimen_id,
        "accessionIdentifier": {
            "system": "http://hospital.example.org/specimens",
            "value": f"SPEC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        },
        "status": "available",
        "type": {
            "coding": [{"system": "http://snomed.info/sct", "code": "119361006", "display": "Plasma specimen"}]
        },
        "subject": order.get("subject"),
        "receivedTime": datetime.utcnow().isoformat() + "Z",
        "request": [{"reference": f"ServiceRequest/{order_id}"}],
        "collection": {
            "collectedDateTime": datetime.utcnow().isoformat() + "Z",
            "bodySite": {"coding": [{"system": "http://snomed.info/sct", "code": "49852007", "display": "Median cubital vein"}]}
        }
    }
    service.create_resource("Specimen", specimen)

    # Generate observations for each test
    observations = []
    for test in panel["tests"]:
        # Generate value within or slightly outside normal range
        low, high = test["range"]
        if random.random() < 0.85:  # 85% normal
            value = round(random.uniform(low, high), 1)
            interpretation = "N"
        elif random.random() < 0.5:  # 7.5% high
            value = round(random.uniform(high, high * 1.2), 1)
            interpretation = "H"
        else:  # 7.5% low
            value = round(random.uniform(low * 0.8, low), 1)
            interpretation = "L"

        obs_id = str(uuid.uuid4())
        observation = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": test["code"], "display": test["name"]}]},
            "subject": order.get("subject"),
            "effectiveDateTime": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {"value": value, "unit": test["unit"], "system": "http://unitsofmeasure.org", "code": test["unit"]},
            "referenceRange": [{"low": {"value": low, "unit": test["unit"]}, "high": {"value": high, "unit": test["unit"]}}],
            "interpretation": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation", "code": interpretation}]}],
            "specimen": {"reference": f"Specimen/{specimen_id}"}
        }
        service.create_resource("Observation", observation)
        observations.append({"reference": f"Observation/{obs_id}"})

    # Create diagnostic report
    report_id = str(uuid.uuid4())
    report = {
        "resourceType": "DiagnosticReport",
        "id": report_id,
        "identifier": [{"system": "http://hospital.example.org/reports", "value": f"RPT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"}],
        "basedOn": [{"reference": f"ServiceRequest/{order_id}"}],
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "LAB"}]}],
        "code": order.get("code"),
        "subject": order.get("subject"),
        "effectiveDateTime": datetime.utcnow().isoformat() + "Z",
        "issued": datetime.utcnow().isoformat() + "Z",
        "specimen": [{"reference": f"Specimen/{specimen_id}"}],
        "result": observations,
        "conclusion": "See individual test results"
    }
    service.create_resource("DiagnosticReport", report)

    # Update order status
    order["status"] = "completed"
    service.update_resource("ServiceRequest", order_id, order)

    # Publish event
    await service.publish_event("completed", report)

    return {"message": "Lab order processed", "diagnosticReport": f"DiagnosticReport/{report_id}"}


@app.get("/fhir/r4/DiagnosticReport/{report_id}/$results")
async def get_full_results(report_id: str):
    """Get diagnostic report with all observations expanded"""
    report = service.read_resource("DiagnosticReport", report_id)

    expanded_results = []
    for ref in report.get("result", []):
        obs_id = ref["reference"].split("/")[-1]
        try:
            obs = service.read_resource("Observation", obs_id)
            expanded_results.append(obs)
        except Exception:
            pass

    report["_expandedResults"] = expanded_results
    return report
