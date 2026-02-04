"""FHIR R4 Resource Models"""
from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class ResourceType(str, Enum):
    PATIENT = "Patient"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    ENCOUNTER = "Encounter"
    CONDITION = "Condition"
    OBSERVATION = "Observation"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    SERVICE_REQUEST = "ServiceRequest"
    SPECIMEN = "Specimen"
    MEDICATION = "Medication"
    MEDICATION_REQUEST = "MedicationRequest"
    MEDICATION_DISPENSE = "MedicationDispense"
    IMAGING_STUDY = "ImagingStudy"
    APPOINTMENT = "Appointment"
    SCHEDULE = "Schedule"
    SLOT = "Slot"
    LOCATION = "Location"
    COVERAGE = "Coverage"
    CLAIM = "Claim"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    PROCEDURE = "Procedure"


# ============ Base Types ============

class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None


class CodeableConcept(BaseModel):
    coding: List[Coding] = []
    text: Optional[str] = None


class Identifier(BaseModel):
    use: Optional[str] = None
    type: Optional[CodeableConcept] = None
    system: Optional[str] = None
    value: Optional[str] = None


class Reference(BaseModel):
    reference: Optional[str] = None
    type: Optional[str] = None
    display: Optional[str] = None


class HumanName(BaseModel):
    use: Optional[str] = None
    family: Optional[str] = None
    given: List[str] = []
    prefix: List[str] = []
    suffix: List[str] = []


class ContactPoint(BaseModel):
    system: Optional[str] = None  # phone, email, fax, etc.
    value: Optional[str] = None
    use: Optional[str] = None  # home, work, mobile


class Address(BaseModel):
    use: Optional[str] = None
    type: Optional[str] = None
    line: List[str] = []
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class Period(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class Quantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: Optional[str] = None
    code: Optional[str] = None


class Range(BaseModel):
    low: Optional[Quantity] = None
    high: Optional[Quantity] = None


class Annotation(BaseModel):
    text: str
    time: Optional[datetime] = None
    authorReference: Optional[Reference] = None


class Meta(BaseModel):
    versionId: Optional[str] = None
    lastUpdated: Optional[datetime] = None
    source: Optional[str] = None
    profile: List[str] = []


# ============ Resources ============

class FHIRResource(BaseModel):
    resourceType: str
    id: Optional[str] = None
    meta: Optional[Meta] = None
    identifier: List[Identifier] = []

    class Config:
        extra = "allow"


class Patient(FHIRResource):
    resourceType: str = "Patient"
    active: bool = True
    name: List[HumanName] = []
    telecom: List[ContactPoint] = []
    gender: Optional[str] = None
    birthDate: Optional[date] = None
    deceasedBoolean: Optional[bool] = None
    deceasedDateTime: Optional[datetime] = None
    address: List[Address] = []
    maritalStatus: Optional[CodeableConcept] = None
    multipleBirthBoolean: Optional[bool] = None
    communication: List[dict] = []
    generalPractitioner: List[Reference] = []
    managingOrganization: Optional[Reference] = None


class Practitioner(FHIRResource):
    resourceType: str = "Practitioner"
    active: bool = True
    name: List[HumanName] = []
    telecom: List[ContactPoint] = []
    gender: Optional[str] = None
    birthDate: Optional[date] = None
    qualification: List[dict] = []


class Organization(FHIRResource):
    resourceType: str = "Organization"
    active: bool = True
    type: List[CodeableConcept] = []
    name: Optional[str] = None
    alias: List[str] = []
    telecom: List[ContactPoint] = []
    address: List[Address] = []
    partOf: Optional[Reference] = None


class Location(FHIRResource):
    resourceType: str = "Location"
    status: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[str] = None
    type: List[CodeableConcept] = []
    telecom: List[ContactPoint] = []
    address: Optional[Address] = None
    physicalType: Optional[CodeableConcept] = None
    managingOrganization: Optional[Reference] = None


class Encounter(FHIRResource):
    resourceType: str = "Encounter"
    status: str  # planned, arrived, triaged, in-progress, onleave, finished, cancelled
    statusHistory: List[dict] = []
    class_: Optional[Coding] = Field(None, alias="class")
    type: List[CodeableConcept] = []
    serviceType: Optional[CodeableConcept] = None
    priority: Optional[CodeableConcept] = None
    subject: Optional[Reference] = None
    participant: List[dict] = []
    period: Optional[Period] = None
    reasonCode: List[CodeableConcept] = []
    diagnosis: List[dict] = []
    hospitalization: Optional[dict] = None
    location: List[dict] = []
    serviceProvider: Optional[Reference] = None


class Condition(FHIRResource):
    resourceType: str = "Condition"
    clinicalStatus: Optional[CodeableConcept] = None
    verificationStatus: Optional[CodeableConcept] = None
    category: List[CodeableConcept] = []
    severity: Optional[CodeableConcept] = None
    code: Optional[CodeableConcept] = None
    bodySite: List[CodeableConcept] = []
    subject: Reference
    encounter: Optional[Reference] = None
    onsetDateTime: Optional[datetime] = None
    abatementDateTime: Optional[datetime] = None
    recordedDate: Optional[datetime] = None
    recorder: Optional[Reference] = None
    asserter: Optional[Reference] = None
    note: List[Annotation] = []


class AllergyIntolerance(FHIRResource):
    resourceType: str = "AllergyIntolerance"
    clinicalStatus: Optional[CodeableConcept] = None
    verificationStatus: Optional[CodeableConcept] = None
    type: Optional[str] = None
    category: List[str] = []
    criticality: Optional[str] = None
    code: Optional[CodeableConcept] = None
    patient: Reference
    encounter: Optional[Reference] = None
    onsetDateTime: Optional[datetime] = None
    recordedDate: Optional[datetime] = None
    recorder: Optional[Reference] = None
    reaction: List[dict] = []


class Procedure(FHIRResource):
    resourceType: str = "Procedure"
    status: str
    statusReason: Optional[CodeableConcept] = None
    category: Optional[CodeableConcept] = None
    code: Optional[CodeableConcept] = None
    subject: Reference
    encounter: Optional[Reference] = None
    performedDateTime: Optional[datetime] = None
    performedPeriod: Optional[Period] = None
    recorder: Optional[Reference] = None
    performer: List[dict] = []
    location: Optional[Reference] = None
    reasonCode: List[CodeableConcept] = []
    bodySite: List[CodeableConcept] = []
    outcome: Optional[CodeableConcept] = None
    note: List[Annotation] = []


class ServiceRequest(FHIRResource):
    resourceType: str = "ServiceRequest"
    status: str  # draft, active, on-hold, revoked, completed, entered-in-error
    intent: str  # proposal, plan, directive, order, original-order, reflex-order, filler-order, instance-order, option
    category: List[CodeableConcept] = []
    priority: Optional[str] = None
    code: Optional[CodeableConcept] = None
    subject: Reference
    encounter: Optional[Reference] = None
    occurrenceDateTime: Optional[datetime] = None
    authoredOn: Optional[datetime] = None
    requester: Optional[Reference] = None
    performer: List[Reference] = []
    reasonCode: List[CodeableConcept] = []
    specimen: List[Reference] = []
    note: List[Annotation] = []


class Specimen(FHIRResource):
    resourceType: str = "Specimen"
    accessionIdentifier: Optional[Identifier] = None
    status: Optional[str] = None
    type: Optional[CodeableConcept] = None
    subject: Optional[Reference] = None
    receivedTime: Optional[datetime] = None
    request: List[Reference] = []
    collection: Optional[dict] = None
    processing: List[dict] = []
    container: List[dict] = []
    note: List[Annotation] = []


class ReferenceRange(BaseModel):
    low: Optional[Quantity] = None
    high: Optional[Quantity] = None
    type: Optional[CodeableConcept] = None
    appliesTo: List[CodeableConcept] = []
    age: Optional[Range] = None
    text: Optional[str] = None


class Observation(FHIRResource):
    resourceType: str = "Observation"
    status: str  # registered, preliminary, final, amended, corrected, cancelled, entered-in-error
    category: List[CodeableConcept] = []
    code: CodeableConcept
    subject: Optional[Reference] = None
    encounter: Optional[Reference] = None
    effectiveDateTime: Optional[datetime] = None
    issued: Optional[datetime] = None
    performer: List[Reference] = []
    valueQuantity: Optional[Quantity] = None
    valueCodeableConcept: Optional[CodeableConcept] = None
    valueString: Optional[str] = None
    valueBoolean: Optional[bool] = None
    dataAbsentReason: Optional[CodeableConcept] = None
    interpretation: List[CodeableConcept] = []
    note: List[Annotation] = []
    bodySite: Optional[CodeableConcept] = None
    method: Optional[CodeableConcept] = None
    specimen: Optional[Reference] = None
    referenceRange: List[ReferenceRange] = []


class DiagnosticReport(FHIRResource):
    resourceType: str = "DiagnosticReport"
    basedOn: List[Reference] = []
    status: str  # registered, partial, preliminary, final, amended, corrected, appended, cancelled, entered-in-error
    category: List[CodeableConcept] = []
    code: CodeableConcept
    subject: Optional[Reference] = None
    encounter: Optional[Reference] = None
    effectiveDateTime: Optional[datetime] = None
    issued: Optional[datetime] = None
    performer: List[Reference] = []
    resultsInterpreter: List[Reference] = []
    specimen: List[Reference] = []
    result: List[Reference] = []
    conclusion: Optional[str] = None
    conclusionCode: List[CodeableConcept] = []


class Medication(FHIRResource):
    resourceType: str = "Medication"
    code: Optional[CodeableConcept] = None
    status: Optional[str] = None
    manufacturer: Optional[Reference] = None
    form: Optional[CodeableConcept] = None
    amount: Optional[dict] = None
    ingredient: List[dict] = []
    batch: Optional[dict] = None


class Dosage(BaseModel):
    sequence: Optional[int] = None
    text: Optional[str] = None
    timing: Optional[dict] = None
    route: Optional[CodeableConcept] = None
    doseAndRate: List[dict] = []


class MedicationRequest(FHIRResource):
    resourceType: str = "MedicationRequest"
    status: str
    statusReason: Optional[CodeableConcept] = None
    intent: str
    category: List[CodeableConcept] = []
    priority: Optional[str] = None
    medicationCodeableConcept: Optional[CodeableConcept] = None
    medicationReference: Optional[Reference] = None
    subject: Reference
    encounter: Optional[Reference] = None
    authoredOn: Optional[datetime] = None
    requester: Optional[Reference] = None
    performer: Optional[Reference] = None
    reasonCode: List[CodeableConcept] = []
    dosageInstruction: List[Dosage] = []
    dispenseRequest: Optional[dict] = None
    substitution: Optional[dict] = None


class MedicationDispense(FHIRResource):
    resourceType: str = "MedicationDispense"
    status: str
    statusReasonCodeableConcept: Optional[CodeableConcept] = None
    category: Optional[CodeableConcept] = None
    medicationCodeableConcept: Optional[CodeableConcept] = None
    medicationReference: Optional[Reference] = None
    subject: Optional[Reference] = None
    performer: List[dict] = []
    authorizingPrescription: List[Reference] = []
    quantity: Optional[Quantity] = None
    daysSupply: Optional[Quantity] = None
    whenPrepared: Optional[datetime] = None
    whenHandedOver: Optional[datetime] = None
    dosageInstruction: List[Dosage] = []


class ImagingStudy(FHIRResource):
    resourceType: str = "ImagingStudy"
    status: str  # registered, available, cancelled, entered-in-error
    subject: Reference
    encounter: Optional[Reference] = None
    started: Optional[datetime] = None
    basedOn: List[Reference] = []
    referrer: Optional[Reference] = None
    endpoint: List[Reference] = []
    numberOfSeries: Optional[int] = None
    numberOfInstances: Optional[int] = None
    procedureReference: Optional[Reference] = None
    procedureCode: List[CodeableConcept] = []
    location: Optional[Reference] = None
    reasonCode: List[CodeableConcept] = []
    description: Optional[str] = None
    series: List[dict] = []


class Appointment(FHIRResource):
    resourceType: str = "Appointment"
    status: str  # proposed, pending, booked, arrived, fulfilled, cancelled, noshow, entered-in-error
    cancelationReason: Optional[CodeableConcept] = None
    serviceCategory: List[CodeableConcept] = []
    serviceType: List[CodeableConcept] = []
    specialty: List[CodeableConcept] = []
    appointmentType: Optional[CodeableConcept] = None
    reasonCode: List[CodeableConcept] = []
    priority: Optional[int] = None
    description: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    minutesDuration: Optional[int] = None
    slot: List[Reference] = []
    created: Optional[datetime] = None
    participant: List[dict] = []


class Coverage(FHIRResource):
    resourceType: str = "Coverage"
    status: str  # active, cancelled, draft, entered-in-error
    type: Optional[CodeableConcept] = None
    policyHolder: Optional[Reference] = None
    subscriber: Optional[Reference] = None
    subscriberId: Optional[str] = None
    beneficiary: Reference
    dependent: Optional[str] = None
    relationship: Optional[CodeableConcept] = None
    period: Optional[Period] = None
    payor: List[Reference] = []
    class_: List[dict] = Field([], alias="class")
    order: Optional[int] = None
    network: Optional[str] = None


class Claim(FHIRResource):
    resourceType: str = "Claim"
    status: str  # active, cancelled, draft, entered-in-error
    type: CodeableConcept
    use: str  # claim, preauthorization, predetermination
    patient: Reference
    billablePeriod: Optional[Period] = None
    created: datetime
    provider: Reference
    priority: CodeableConcept
    insurance: List[dict] = []
    item: List[dict] = []
    total: Optional[dict] = None


# ============ Bundle ============

class BundleEntry(BaseModel):
    fullUrl: Optional[str] = None
    resource: Optional[dict] = None
    request: Optional[dict] = None
    response: Optional[dict] = None


class Bundle(BaseModel):
    resourceType: str = "Bundle"
    id: Optional[str] = None
    meta: Optional[Meta] = None
    type: str  # document, message, transaction, transaction-response, batch, batch-response, history, searchset, collection
    total: Optional[int] = None
    link: List[dict] = []
    entry: List[BundleEntry] = []


# ============ CapabilityStatement ============

class CapabilityStatement(BaseModel):
    resourceType: str = "CapabilityStatement"
    id: Optional[str] = None
    status: str = "active"
    date: datetime
    kind: str = "instance"
    fhirVersion: str = "4.0.1"
    format: List[str] = ["json"]
    rest: List[dict] = []
