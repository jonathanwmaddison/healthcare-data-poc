"""Billing Service - Healthcare Billing System
Manages claims, coverage, and financial data:
- Coverage (insurance)
- Claim
- ClaimResponse
- ExplanationOfBenefit
- Account
- ChargeItem
"""
import os
import json
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal
from shared.base_service import FHIRService, create_fhir_app

SUPPORTED_RESOURCES = [
    "Patient",  # Each system has its own patient registry
    "Coverage",
    "Claim",
    "ClaimResponse",
    "ExplanationOfBenefit",
    "Account",
    "ChargeItem",
    "Invoice",
]

# Sample CPT codes and charges
CPT_CODES = {
    "99213": {"description": "Office visit, established patient, low complexity", "charge": 150.00},
    "99214": {"description": "Office visit, established patient, moderate complexity", "charge": 225.00},
    "99215": {"description": "Office visit, established patient, high complexity", "charge": 325.00},
    "99283": {"description": "Emergency department visit, moderate severity", "charge": 450.00},
    "99284": {"description": "Emergency department visit, high severity", "charge": 750.00},
    "99285": {"description": "Emergency department visit, highest severity", "charge": 1200.00},
    "99221": {"description": "Initial hospital care, low complexity", "charge": 275.00},
    "99222": {"description": "Initial hospital care, moderate complexity", "charge": 385.00},
    "99223": {"description": "Initial hospital care, high complexity", "charge": 500.00},
    "85025": {"description": "Complete blood count (CBC)", "charge": 45.00},
    "80053": {"description": "Comprehensive metabolic panel", "charge": 65.00},
    "71046": {"description": "Chest X-ray, 2 views", "charge": 125.00},
    "70553": {"description": "MRI brain with contrast", "charge": 2500.00},
    "74177": {"description": "CT abdomen/pelvis with contrast", "charge": 1800.00},
}

# Sample insurance payers
PAYERS = [
    {"id": "payer-bcbs", "name": "Blue Cross Blue Shield", "type": "commercial"},
    {"id": "payer-aetna", "name": "Aetna", "type": "commercial"},
    {"id": "payer-cigna", "name": "Cigna", "type": "commercial"},
    {"id": "payer-uhc", "name": "UnitedHealthcare", "type": "commercial"},
    {"id": "payer-medicare", "name": "Medicare", "type": "government"},
    {"id": "payer-medicaid", "name": "Medicaid", "type": "government"},
]


class BillingService(FHIRService):
    """Billing-specific service"""

    def __init__(self):
        super().__init__("billing", SUPPORTED_RESOURCES)

    async def setup(self):
        await super().setup()
        await self._seed_data()

    async def _seed_data(self):
        seed_path = Path("/app/data/seed/billing_seed.json")
        if not seed_path.exists():
            seed_path = Path("data/seed/billing_seed.json")

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
                print("Billing seed data loaded")
            except Exception as e:
                print(f"Error loading seed data: {e}")


service = BillingService()
app = create_fhir_app(service)


@app.post("/fhir/r4/Coverage")
async def create_coverage(coverage_data: dict):
    """Create insurance coverage record"""
    coverage_data["id"] = coverage_data.get("id") or str(uuid.uuid4())
    coverage_data["status"] = coverage_data.get("status", "active")

    result = service.create_resource("Coverage", coverage_data)
    return result


@app.post("/fhir/r4/ChargeItem")
async def post_charge(charge_data: dict):
    """Post a charge item"""
    charge_id = str(uuid.uuid4())

    # Look up CPT code details
    cpt_code = None
    if charge_data.get("code", {}).get("coding"):
        cpt_code = charge_data["code"]["coding"][0].get("code")

    cpt_info = CPT_CODES.get(cpt_code, {"description": "Unknown", "charge": 100.00})

    charge = {
        "resourceType": "ChargeItem",
        "id": charge_id,
        "identifier": [{"system": "http://hospital.example.org/charges", "value": f"CHG-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"}],
        "status": "billable",
        "code": charge_data.get("code"),
        "subject": charge_data.get("subject"),
        "context": charge_data.get("context"),  # Encounter reference
        "occurrenceDateTime": datetime.utcnow().isoformat() + "Z",
        "quantity": {"value": charge_data.get("quantity", 1)},
        "priceOverride": {
            "value": cpt_info["charge"],
            "currency": "USD"
        },
        "enterer": charge_data.get("enterer"),
        "enteredDate": datetime.utcnow().isoformat() + "Z"
    }

    service.create_resource("ChargeItem", charge)
    await service.publish_event("charge.posted", charge)

    return {"message": "Charge posted", "chargeItem": f"ChargeItem/{charge_id}", "amount": cpt_info["charge"]}


@app.post("/fhir/r4/Claim")
async def create_claim(claim_data: dict):
    """Create and optionally submit a claim"""
    claim_id = str(uuid.uuid4())

    # Calculate total from items
    total = 0.0
    for item in claim_data.get("item", []):
        if item.get("unitPrice"):
            qty = item.get("quantity", {}).get("value", 1)
            total += item["unitPrice"].get("value", 0) * qty

    claim = {
        "resourceType": "Claim",
        "id": claim_id,
        "identifier": [{"system": "http://hospital.example.org/claims", "value": f"CLM-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"}],
        "status": "active",
        "type": claim_data.get("type", {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "institutional"}]}),
        "use": claim_data.get("use", "claim"),
        "patient": claim_data.get("patient"),
        "created": datetime.utcnow().isoformat() + "Z",
        "provider": claim_data.get("provider", {"reference": "Organization/hospital-main"}),
        "priority": {"coding": [{"code": "normal"}]},
        "insurance": claim_data.get("insurance", []),
        "item": claim_data.get("item", []),
        "total": {"value": total, "currency": "USD"}
    }

    service.create_resource("Claim", claim)

    return {"message": "Claim created", "claim": f"Claim/{claim_id}", "total": total}


@app.post("/fhir/r4/Claim/{claim_id}/$submit")
async def submit_claim(claim_id: str):
    """Submit claim for adjudication (simulated)"""
    claim = service.read_resource("Claim", claim_id)

    # Simulate adjudication
    claim_total = claim.get("total", {}).get("value", 0)
    allowed_amount = claim_total * random.uniform(0.6, 0.9)  # 60-90% allowed
    patient_responsibility = allowed_amount * random.uniform(0.1, 0.3)  # 10-30% patient pays
    payer_payment = allowed_amount - patient_responsibility

    # Create ClaimResponse
    response_id = str(uuid.uuid4())
    claim_response = {
        "resourceType": "ClaimResponse",
        "id": response_id,
        "identifier": [{"system": "http://payer.example.org/responses", "value": f"RSP-{random.randint(100000, 999999)}"}],
        "status": "active",
        "type": claim.get("type"),
        "use": "claim",
        "patient": claim.get("patient"),
        "created": datetime.utcnow().isoformat() + "Z",
        "insurer": {"reference": "Organization/payer-bcbs"},
        "request": {"reference": f"Claim/{claim_id}"},
        "outcome": "complete",
        "disposition": "Claim processed successfully",
        "payment": {
            "type": {"coding": [{"code": "complete"}]},
            "adjustment": {"value": claim_total - allowed_amount, "currency": "USD"},
            "adjustmentReason": {"coding": [{"code": "contractual"}]},
            "date": (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "amount": {"value": round(payer_payment, 2), "currency": "USD"}
        },
        "total": [
            {"category": {"coding": [{"code": "submitted"}]}, "amount": {"value": claim_total, "currency": "USD"}},
            {"category": {"coding": [{"code": "benefit"}]}, "amount": {"value": round(allowed_amount, 2), "currency": "USD"}}
        ]
    }
    service.create_resource("ClaimResponse", claim_response)

    # Update claim status
    claim["status"] = "active"
    service.update_resource("Claim", claim_id, claim)

    # Create ExplanationOfBenefit
    eob_id = str(uuid.uuid4())
    eob = {
        "resourceType": "ExplanationOfBenefit",
        "id": eob_id,
        "identifier": [{"system": "http://payer.example.org/eob", "value": f"EOB-{random.randint(100000, 999999)}"}],
        "status": "active",
        "type": claim.get("type"),
        "use": "claim",
        "patient": claim.get("patient"),
        "created": datetime.utcnow().isoformat() + "Z",
        "insurer": {"reference": "Organization/payer-bcbs"},
        "provider": claim.get("provider"),
        "claim": {"reference": f"Claim/{claim_id}"},
        "claimResponse": {"reference": f"ClaimResponse/{response_id}"},
        "outcome": "complete",
        "total": [
            {"category": {"coding": [{"code": "submitted"}]}, "amount": {"value": claim_total, "currency": "USD"}},
            {"category": {"coding": [{"code": "eligible"}]}, "amount": {"value": round(allowed_amount, 2), "currency": "USD"}},
            {"category": {"coding": [{"code": "benefit"}]}, "amount": {"value": round(payer_payment, 2), "currency": "USD"}},
            {"category": {"coding": [{"code": "copay"}]}, "amount": {"value": round(patient_responsibility, 2), "currency": "USD"}}
        ],
        "payment": {
            "type": {"coding": [{"code": "complete"}]},
            "date": (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "amount": {"value": round(payer_payment, 2), "currency": "USD"}
        }
    }
    service.create_resource("ExplanationOfBenefit", eob)

    await service.publish_event("claim.adjudicated", {
        "claim": claim,
        "response": claim_response,
        "eob": eob
    })

    return {
        "message": "Claim adjudicated",
        "claimResponse": f"ClaimResponse/{response_id}",
        "explanationOfBenefit": f"ExplanationOfBenefit/{eob_id}",
        "payment": {
            "submitted": claim_total,
            "allowed": round(allowed_amount, 2),
            "payerPayment": round(payer_payment, 2),
            "patientResponsibility": round(patient_responsibility, 2)
        }
    }


@app.get("/fhir/r4/Account/{patient_id}/$balance")
async def get_patient_balance(patient_id: str):
    """Get patient account balance"""
    # Get all charges
    charges = service.search_resources("ChargeItem", {"patient": patient_id})
    total_charges = sum(
        entry.get("resource", {}).get("priceOverride", {}).get("value", 0)
        for entry in charges.get("entry", [])
    )

    # Get all EOBs to calculate payments
    eobs = service.search_resources("ExplanationOfBenefit", {"patient": patient_id})
    total_payments = 0
    patient_responsibility = 0

    for entry in eobs.get("entry", []):
        eob = entry.get("resource", {})
        for total in eob.get("total", []):
            if total.get("category", {}).get("coding", [{}])[0].get("code") == "benefit":
                total_payments += total.get("amount", {}).get("value", 0)
            if total.get("category", {}).get("coding", [{}])[0].get("code") == "copay":
                patient_responsibility += total.get("amount", {}).get("value", 0)

    return {
        "patient": f"Patient/{patient_id}",
        "totalCharges": round(total_charges, 2),
        "insurancePayments": round(total_payments, 2),
        "patientResponsibility": round(patient_responsibility, 2),
        "balance": round(patient_responsibility, 2)  # Simplified
    }
