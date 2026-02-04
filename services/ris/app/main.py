"""RIS Service - Radiology Information System
Manages radiology workflow:
- ServiceRequest (imaging orders)
- Appointment (scheduling)
- ImagingStudy (DICOM study metadata)
- DiagnosticReport (radiology reports)
"""
import os
import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from shared.base_service import FHIRService, create_fhir_app

SUPPORTED_RESOURCES = [
    "Patient",  # Each system has its own patient registry
    "ServiceRequest",
    "Appointment",
    "ImagingStudy",
    "DiagnosticReport",
    "Observation",
    "Task",
]

# Common radiology procedures
RAD_PROCEDURES = {
    "36643-5": {"name": "XR Chest 2 Views", "modality": "CR", "bodysite": "51185008", "bodysite_name": "Thorax"},
    "24558-9": {"name": "CT Head without contrast", "modality": "CT", "bodysite": "69536005", "bodysite_name": "Head"},
    "24566-2": {"name": "MRI Brain", "modality": "MR", "bodysite": "12738006", "bodysite_name": "Brain"},
    "30746-2": {"name": "CT Abdomen with contrast", "modality": "CT", "bodysite": "818983003", "bodysite_name": "Abdomen"},
    "26287-7": {"name": "US Abdomen", "modality": "US", "bodysite": "818983003", "bodysite_name": "Abdomen"},
}

# Sample radiology findings
RAD_FINDINGS = {
    "CR": [
        "No acute cardiopulmonary abnormality.",
        "Clear lungs bilaterally. No pleural effusion or pneumothorax.",
        "Mild cardiomegaly. Lungs are clear.",
        "Patchy opacity in right lower lobe, possibly atelectasis vs early infiltrate. Clinical correlation recommended.",
    ],
    "CT": [
        "No acute intracranial abnormality.",
        "No evidence of acute hemorrhage, mass effect, or midline shift.",
        "Age-appropriate involutional changes. No acute findings.",
        "Small hypodensity in left frontal lobe, likely chronic lacunar infarct.",
    ],
    "MR": [
        "No acute intracranial abnormality on MRI.",
        "Normal brain MRI. No evidence of mass, hemorrhage, or acute infarct.",
        "Scattered T2/FLAIR hyperintensities in periventricular white matter, nonspecific, possibly related to chronic microvascular disease.",
    ],
    "US": [
        "Normal abdominal ultrasound.",
        "No hepatomegaly or focal hepatic lesion. Gallbladder is normal without stones.",
        "Mild hepatic steatosis. Otherwise normal sonographic examination.",
    ],
}


class RISService(FHIRService):
    """RIS-specific service"""

    def __init__(self):
        super().__init__("ris", SUPPORTED_RESOURCES)

    async def setup(self):
        await super().setup()
        await self._seed_data()

    async def _seed_data(self):
        seed_path = Path("/app/data/seed/ris_seed.json")
        if not seed_path.exists():
            seed_path = Path("data/seed/ris_seed.json")

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
                print("RIS seed data loaded")
            except Exception as e:
                print(f"Error loading seed data: {e}")


service = RISService()
app = create_fhir_app(service)


@app.post("/fhir/r4/ServiceRequest/{order_id}/$schedule")
async def schedule_imaging(order_id: str):
    """Schedule an imaging appointment"""
    order = service.read_resource("ServiceRequest", order_id)

    # Create appointment
    apt_id = str(uuid.uuid4())
    start_time = datetime.utcnow() + timedelta(hours=random.randint(1, 48))

    appointment = {
        "resourceType": "Appointment",
        "id": apt_id,
        "status": "booked",
        "serviceType": [order.get("code")],
        "subject": order.get("subject"),
        "start": start_time.isoformat() + "Z",
        "end": (start_time + timedelta(minutes=30)).isoformat() + "Z",
        "minutesDuration": 30,
        "basedOn": [{"reference": f"ServiceRequest/{order_id}"}],
        "participant": [
            {
                "actor": order.get("subject"),
                "status": "accepted"
            }
        ]
    }
    service.create_resource("Appointment", appointment)

    # Update order status
    order["status"] = "active"
    service.update_resource("ServiceRequest", order_id, order)

    return {"message": "Imaging scheduled", "appointment": f"Appointment/{apt_id}"}


@app.post("/fhir/r4/ServiceRequest/{order_id}/$complete")
async def complete_imaging_study(order_id: str):
    """Simulate completion of imaging study with report"""
    order = service.read_resource("ServiceRequest", order_id)

    # Get procedure info
    proc_code = None
    if order.get("code", {}).get("coding"):
        proc_code = order["code"]["coding"][0].get("code")

    proc = RAD_PROCEDURES.get(proc_code, RAD_PROCEDURES["36643-5"])

    # Generate DICOM UIDs
    study_uid = f"2.16.840.1.113883.{random.randint(1000000, 9999999)}.{random.randint(1000, 9999)}"
    series_uid = f"{study_uid}.1"
    instance_uid = f"{series_uid}.1"

    # Create ImagingStudy
    study_id = str(uuid.uuid4())
    accession = f"ACC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

    imaging_study = {
        "resourceType": "ImagingStudy",
        "id": study_id,
        "identifier": [
            {"system": "urn:dicom:uid", "value": f"urn:oid:{study_uid}"},
            {"system": "http://hospital.example.org/accession", "value": accession}
        ],
        "status": "available",
        "subject": order.get("subject"),
        "started": datetime.utcnow().isoformat() + "Z",
        "basedOn": [{"reference": f"ServiceRequest/{order_id}"}],
        "numberOfSeries": 1,
        "numberOfInstances": random.randint(1, 50),
        "procedureCode": [order.get("code")],
        "series": [
            {
                "uid": series_uid,
                "number": 1,
                "modality": {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": proc["modality"]},
                "description": proc["name"],
                "numberOfInstances": random.randint(1, 50),
                "bodySite": {"system": "http://snomed.info/sct", "code": proc["bodysite"], "display": proc["bodysite_name"]},
                "instance": [
                    {
                        "uid": instance_uid,
                        "sopClass": {"system": "urn:ietf:rfc:3986", "code": "urn:oid:1.2.840.10008.5.1.4.1.1.1.1"},
                        "number": 1
                    }
                ]
            }
        ]
    }
    service.create_resource("ImagingStudy", imaging_study)

    # Create DiagnosticReport (radiology report)
    report_id = str(uuid.uuid4())
    finding = random.choice(RAD_FINDINGS.get(proc["modality"], RAD_FINDINGS["CR"]))

    report = {
        "resourceType": "DiagnosticReport",
        "id": report_id,
        "identifier": [{"system": "http://hospital.example.org/reports", "value": f"RAD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"}],
        "basedOn": [{"reference": f"ServiceRequest/{order_id}"}],
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiology"}]}],
        "code": order.get("code"),
        "subject": order.get("subject"),
        "effectiveDateTime": datetime.utcnow().isoformat() + "Z",
        "issued": datetime.utcnow().isoformat() + "Z",
        "imagingStudy": [{"reference": f"ImagingStudy/{study_id}"}],
        "conclusion": finding,
        "conclusionCode": [{"coding": [{"system": "http://snomed.info/sct", "code": "281900007", "display": "No abnormality detected"}]}] if "normal" in finding.lower() or "no acute" in finding.lower() else []
    }
    service.create_resource("DiagnosticReport", report)

    # Update order status
    order["status"] = "completed"
    service.update_resource("ServiceRequest", order_id, order)

    await service.publish_event("completed", report)

    return {
        "message": "Imaging study completed",
        "imagingStudy": f"ImagingStudy/{study_id}",
        "diagnosticReport": f"DiagnosticReport/{report_id}"
    }
