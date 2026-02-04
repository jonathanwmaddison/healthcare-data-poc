"""PACS Service - Picture Archiving and Communication System
Provides DICOMweb-style APIs for medical image storage and retrieval.
Uses MinIO for object storage.
"""
import os
import io
import json
import uuid
import base64
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import Response, StreamingResponse, JSONResponse
from minio import Minio
from minio.error import S3Error

# MinIO configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "healthcare")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "healthcare123")
BUCKET_NAME = "dicom-images"

minio_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global minio_client
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    # Create bucket if not exists
    try:
        if not minio_client.bucket_exists(BUCKET_NAME):
            minio_client.make_bucket(BUCKET_NAME)
    except Exception as e:
        print(f"MinIO setup error: {e}")
    yield


app = FastAPI(
    title="Healthcare POC - PACS",
    description="DICOMweb-style API for medical image storage",
    version="1.0.0",
    lifespan=lifespan
)


# In-memory study index (in production, use database)
study_index = {}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "pacs"}


# ===================
# DICOMweb QIDO-RS (Query)
# ===================

@app.get("/dicomweb/studies")
async def search_studies(
    PatientID: Optional[str] = None,
    PatientName: Optional[str] = None,
    AccessionNumber: Optional[str] = None,
    StudyDate: Optional[str] = None,
    ModalitiesInStudy: Optional[str] = None,
    limit: int = Query(100, alias="limit"),
    offset: int = Query(0, alias="offset")
):
    """QIDO-RS: Search for studies"""
    results = []

    for study_uid, study in study_index.items():
        match = True

        if PatientID and study.get("patientId") != PatientID:
            match = False
        if AccessionNumber and study.get("accessionNumber") != AccessionNumber:
            match = False
        if ModalitiesInStudy and ModalitiesInStudy not in study.get("modalities", []):
            match = False

        if match:
            results.append({
                "0020000D": {"vr": "UI", "Value": [study_uid]},  # StudyInstanceUID
                "00100020": {"vr": "LO", "Value": [study.get("patientId", "")]},  # PatientID
                "00100010": {"vr": "PN", "Value": [study.get("patientName", "")]},  # PatientName
                "00080050": {"vr": "SH", "Value": [study.get("accessionNumber", "")]},  # AccessionNumber
                "00080020": {"vr": "DA", "Value": [study.get("studyDate", "")]},  # StudyDate
                "00080061": {"vr": "CS", "Value": study.get("modalities", [])},  # ModalitiesInStudy
                "00201206": {"vr": "IS", "Value": [study.get("numberOfSeries", 0)]},  # NumberOfStudyRelatedSeries
                "00201208": {"vr": "IS", "Value": [study.get("numberOfInstances", 0)]},  # NumberOfStudyRelatedInstances
            })

    return JSONResponse(
        content=results[offset:offset + limit],
        media_type="application/dicom+json"
    )


@app.get("/dicomweb/studies/{study_uid}/series")
async def search_series(study_uid: str):
    """QIDO-RS: Search for series in a study"""
    if study_uid not in study_index:
        raise HTTPException(status_code=404, detail="Study not found")

    study = study_index[study_uid]
    results = []

    for series in study.get("series", []):
        results.append({
            "0020000E": {"vr": "UI", "Value": [series.get("seriesUid")]},  # SeriesInstanceUID
            "00080060": {"vr": "CS", "Value": [series.get("modality")]},  # Modality
            "0020000D": {"vr": "UI", "Value": [study_uid]},  # StudyInstanceUID
            "00201209": {"vr": "IS", "Value": [series.get("numberOfInstances", 0)]},  # NumberOfSeriesRelatedInstances
        })

    return JSONResponse(content=results, media_type="application/dicom+json")


# ===================
# DICOMweb WADO-RS (Retrieve)
# ===================

@app.get("/dicomweb/studies/{study_uid}")
async def retrieve_study(study_uid: str):
    """WADO-RS: Retrieve entire study"""
    if study_uid not in study_index:
        raise HTTPException(status_code=404, detail="Study not found")

    # Return study metadata
    study = study_index[study_uid]
    return JSONResponse(
        content={"studyInstanceUID": study_uid, **study},
        media_type="application/dicom+json"
    )


@app.get("/dicomweb/studies/{study_uid}/series/{series_uid}")
async def retrieve_series(study_uid: str, series_uid: str):
    """WADO-RS: Retrieve series"""
    if study_uid not in study_index:
        raise HTTPException(status_code=404, detail="Study not found")

    study = study_index[study_uid]
    for series in study.get("series", []):
        if series.get("seriesUid") == series_uid:
            return JSONResponse(content=series, media_type="application/dicom+json")

    raise HTTPException(status_code=404, detail="Series not found")


@app.get("/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}")
async def retrieve_instance(study_uid: str, series_uid: str, instance_uid: str):
    """WADO-RS: Retrieve single instance"""
    object_name = f"{study_uid}/{series_uid}/{instance_uid}.dcm"

    try:
        response = minio_client.get_object(BUCKET_NAME, object_name)
        return StreamingResponse(
            io.BytesIO(response.read()),
            media_type="application/dicom"
        )
    except S3Error:
        raise HTTPException(status_code=404, detail="Instance not found")


@app.get("/dicomweb/studies/{study_uid}/rendered")
async def retrieve_rendered(study_uid: str, viewport: Optional[str] = None):
    """WADO-RS: Retrieve rendered image (JPEG)"""
    # In a real implementation, this would render DICOM to JPEG
    # For POC, return placeholder
    placeholder = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
        "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwh"
        "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAAR"
        "CAAyADIDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAA"
    )
    return Response(content=placeholder, media_type="image/jpeg")


# ===================
# DICOMweb STOW-RS (Store)
# ===================

@app.post("/dicomweb/studies")
async def store_instances(file: UploadFile = File(...)):
    """STOW-RS: Store DICOM instances"""
    # Generate UIDs for POC
    study_uid = f"2.16.840.1.113883.{uuid.uuid4().int >> 64}"
    series_uid = f"{study_uid}.1"
    instance_uid = f"{series_uid}.{uuid.uuid4().int >> 96}"

    # Store in MinIO
    object_name = f"{study_uid}/{series_uid}/{instance_uid}.dcm"
    content = await file.read()

    try:
        minio_client.put_object(
            BUCKET_NAME,
            object_name,
            io.BytesIO(content),
            len(content),
            content_type="application/dicom"
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")

    # Update index
    study_index[study_uid] = {
        "patientId": "UNKNOWN",
        "patientName": "UNKNOWN",
        "accessionNumber": f"ACC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "studyDate": datetime.now().strftime("%Y%m%d"),
        "modalities": ["OT"],
        "numberOfSeries": 1,
        "numberOfInstances": 1,
        "series": [{
            "seriesUid": series_uid,
            "modality": "OT",
            "numberOfInstances": 1
        }]
    }

    return JSONResponse(
        content={
            "00081199": {  # ReferencedSOPSequence
                "vr": "SQ",
                "Value": [{
                    "00081150": {"vr": "UI", "Value": ["1.2.840.10008.5.1.4.1.1.1.1"]},  # ReferencedSOPClassUID
                    "00081155": {"vr": "UI", "Value": [instance_uid]},  # ReferencedSOPInstanceUID
                    "00081190": {"vr": "UR", "Value": [f"/dicomweb/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}"]}
                }]
            }
        },
        status_code=200,
        media_type="application/dicom+json"
    )


@app.post("/dicomweb/studies/{study_uid}")
async def store_to_study(study_uid: str, file: UploadFile = File(...)):
    """STOW-RS: Store instance to existing study"""
    if study_uid not in study_index:
        study_index[study_uid] = {
            "patientId": "UNKNOWN",
            "studyDate": datetime.now().strftime("%Y%m%d"),
            "modalities": [],
            "numberOfSeries": 0,
            "numberOfInstances": 0,
            "series": []
        }

    series_uid = f"{study_uid}.{len(study_index[study_uid]['series']) + 1}"
    instance_uid = f"{series_uid}.1"

    object_name = f"{study_uid}/{series_uid}/{instance_uid}.dcm"
    content = await file.read()

    try:
        minio_client.put_object(
            BUCKET_NAME,
            object_name,
            io.BytesIO(content),
            len(content),
            content_type="application/dicom"
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")

    study_index[study_uid]["series"].append({
        "seriesUid": series_uid,
        "modality": "OT",
        "numberOfInstances": 1
    })
    study_index[study_uid]["numberOfSeries"] += 1
    study_index[study_uid]["numberOfInstances"] += 1

    return JSONResponse(
        content={"studyInstanceUID": study_uid, "seriesInstanceUID": series_uid, "sopInstanceUID": instance_uid},
        media_type="application/dicom+json"
    )


# ===================
# FHIR Reference
# ===================

@app.get("/fhir/r4/ImagingStudy")
async def search_imaging_studies(patient: Optional[str] = None, identifier: Optional[str] = None):
    """Search ImagingStudy resources (FHIR interface to PACS)"""
    results = []

    for study_uid, study in study_index.items():
        if patient and study.get("patientId") != patient:
            continue
        if identifier and study.get("accessionNumber") != identifier:
            continue

        results.append({
            "resourceType": "ImagingStudy",
            "id": study_uid.replace(".", "-"),
            "identifier": [
                {"system": "urn:dicom:uid", "value": f"urn:oid:{study_uid}"},
                {"system": "http://hospital.example.org/accession", "value": study.get("accessionNumber")}
            ],
            "status": "available",
            "subject": {"reference": f"Patient/{study.get('patientId')}"},
            "started": f"{study.get('studyDate', '20240101')[:4]}-{study.get('studyDate', '20240101')[4:6]}-{study.get('studyDate', '20240101')[6:8]}",
            "numberOfSeries": study.get("numberOfSeries", 0),
            "numberOfInstances": study.get("numberOfInstances", 0),
            "endpoint": [{"reference": f"Endpoint/pacs-wado", "display": f"/dicomweb/studies/{study_uid}"}]
        })

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(results),
        "entry": [{"resource": r} for r in results]
    }
