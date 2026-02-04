"""Base FastAPI service for FHIR-compliant healthcare services"""
import os
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Type
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, DateTime, Text, Index
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import aio_pika
import redis.asyncio as redis

Base = declarative_base()


class FHIRResourceStore(Base):
    """Generic FHIR resource storage table"""
    __tablename__ = "fhir_resources"

    id = Column(String(64), primary_key=True)
    resource_type = Column(String(64), nullable=False, index=True)
    version_id = Column(String(64), nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_resource_type_id', 'resource_type', 'id'),
    )


class FHIRService:
    """Base class for FHIR-compliant services"""

    def __init__(self, service_name: str, supported_resources: List[str]):
        self.service_name = service_name
        self.supported_resources = supported_resources
        self.db_engine = None
        self.Session = None
        self.rabbitmq_connection = None
        self.rabbitmq_channel = None
        self.redis_client = None

    async def setup(self):
        """Initialize database, message queue, and cache connections"""
        # Database
        db_url = os.environ.get("DATABASE_URL", "postgresql://healthcare:healthcare123@localhost:5432/ehr")
        self.db_engine = create_engine(db_url)
        Base.metadata.create_all(self.db_engine)
        self.Session = sessionmaker(bind=self.db_engine)

        # RabbitMQ
        rabbitmq_url = os.environ.get("RABBITMQ_URL")
        if rabbitmq_url:
            try:
                self.rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
                self.rabbitmq_channel = await self.rabbitmq_connection.channel()
                await self.rabbitmq_channel.declare_exchange(
                    "healthcare.events", aio_pika.ExchangeType.TOPIC, durable=True
                )
            except Exception as e:
                print(f"RabbitMQ connection failed: {e}")

        # Redis
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
            except Exception as e:
                print(f"Redis connection failed: {e}")

    async def cleanup(self):
        """Cleanup connections"""
        if self.rabbitmq_connection:
            await self.rabbitmq_connection.close()
        if self.redis_client:
            await self.redis_client.close()

    async def publish_event(self, event_type: str, resource: dict):
        """Publish event to RabbitMQ"""
        if not self.rabbitmq_channel:
            return

        event = {
            "specversion": "1.0",
            "type": f"org.hl7.fhir.r4.{resource.get('resourceType')}.{event_type}",
            "source": f"/{self.service_name}",
            "id": str(uuid.uuid4()),
            "time": datetime.utcnow().isoformat() + "Z",
            "datacontenttype": "application/fhir+json",
            "data": resource
        }

        routing_key = f"{self.service_name}.{resource.get('resourceType', 'unknown').lower()}.{event_type}"

        exchange = await self.rabbitmq_channel.get_exchange("healthcare.events")
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(event).encode(),
                content_type="application/json"
            ),
            routing_key=routing_key
        )

    def create_resource(self, resource_type: str, data: dict) -> dict:
        """Create a new FHIR resource"""
        if resource_type not in self.supported_resources:
            raise HTTPException(status_code=400, detail=f"Resource type {resource_type} not supported")

        resource_id = data.get("id") or str(uuid.uuid4())
        version_id = "1"

        data["id"] = resource_id
        data["resourceType"] = resource_type
        data["meta"] = {
            "versionId": version_id,
            "lastUpdated": datetime.utcnow().isoformat() + "Z"
        }

        with self.Session() as session:
            resource = FHIRResourceStore(
                id=resource_id,
                resource_type=resource_type,
                version_id=version_id,
                data=data
            )
            session.add(resource)
            session.commit()

        return data

    def read_resource(self, resource_type: str, resource_id: str) -> dict:
        """Read a FHIR resource by ID"""
        with self.Session() as session:
            resource = session.query(FHIRResourceStore).filter(
                FHIRResourceStore.resource_type == resource_type,
                FHIRResourceStore.id == resource_id
            ).first()

            if not resource:
                raise HTTPException(status_code=404, detail=f"{resource_type}/{resource_id} not found")

            return resource.data

    def update_resource(self, resource_type: str, resource_id: str, data: dict) -> dict:
        """Update an existing FHIR resource"""
        with self.Session() as session:
            resource = session.query(FHIRResourceStore).filter(
                FHIRResourceStore.resource_type == resource_type,
                FHIRResourceStore.id == resource_id
            ).first()

            if not resource:
                raise HTTPException(status_code=404, detail=f"{resource_type}/{resource_id} not found")

            new_version = str(int(resource.version_id) + 1)

            data["id"] = resource_id
            data["resourceType"] = resource_type
            data["meta"] = {
                "versionId": new_version,
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            }

            resource.data = data
            resource.version_id = new_version
            session.commit()

        return data

    def delete_resource(self, resource_type: str, resource_id: str):
        """Delete a FHIR resource"""
        with self.Session() as session:
            resource = session.query(FHIRResourceStore).filter(
                FHIRResourceStore.resource_type == resource_type,
                FHIRResourceStore.id == resource_id
            ).first()

            if not resource:
                raise HTTPException(status_code=404, detail=f"{resource_type}/{resource_id} not found")

            session.delete(resource)
            session.commit()

    def search_resources(
        self,
        resource_type: str,
        params: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> dict:
        """Search FHIR resources with query parameters"""
        with self.Session() as session:
            query = session.query(FHIRResourceStore).filter(
                FHIRResourceStore.resource_type == resource_type
            )

            # Apply JSONB filters for common search params
            for key, value in params.items():
                if key.startswith("_"):
                    continue
                if value is None:
                    continue

                # Handle common FHIR search parameters
                if key == "patient":
                    query = query.filter(
                        FHIRResourceStore.data["subject"]["reference"].astext == f"Patient/{value}"
                    )
                elif key == "subject":
                    query = query.filter(
                        FHIRResourceStore.data["subject"]["reference"].astext.contains(value)
                    )
                elif key == "status":
                    query = query.filter(
                        FHIRResourceStore.data["status"].astext == value
                    )
                elif key == "identifier":
                    # Search in identifier array
                    query = query.filter(
                        FHIRResourceStore.data["identifier"].contains([{"value": value}])
                    )
                elif key == "category":
                    query = query.filter(
                        FHIRResourceStore.data["category"].contains([{"coding": [{"code": value}]}])
                    )
                elif key == "code":
                    query = query.filter(
                        FHIRResourceStore.data["code"]["coding"].contains([{"code": value}])
                    )

            total = query.count()
            resources = query.offset(offset).limit(limit).all()

            # Build search result bundle
            bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": total,
                "link": [
                    {"relation": "self", "url": f"/fhir/r4/{resource_type}"}
                ],
                "entry": [
                    {
                        "fullUrl": f"{resource_type}/{r.id}",
                        "resource": r.data
                    }
                    for r in resources
                ]
            }

            return bundle

    def get_capability_statement(self) -> dict:
        """Generate FHIR CapabilityStatement"""
        resources = []
        for rt in self.supported_resources:
            resources.append({
                "type": rt,
                "interaction": [
                    {"code": "read"},
                    {"code": "vread"},
                    {"code": "update"},
                    {"code": "delete"},
                    {"code": "create"},
                    {"code": "search-type"}
                ],
                "versioning": "versioned",
                "readHistory": False,
                "updateCreate": True,
                "conditionalCreate": False,
                "conditionalRead": "not-supported",
                "conditionalUpdate": False,
                "conditionalDelete": "not-supported",
                "searchParam": [
                    {"name": "_id", "type": "token"},
                    {"name": "identifier", "type": "token"},
                    {"name": "patient", "type": "reference"},
                    {"name": "status", "type": "token"}
                ]
            })

        return {
            "resourceType": "CapabilityStatement",
            "id": f"{self.service_name}-capability",
            "status": "active",
            "date": datetime.utcnow().isoformat() + "Z",
            "kind": "instance",
            "software": {
                "name": f"Healthcare POC - {self.service_name.upper()}",
                "version": "1.0.0"
            },
            "fhirVersion": "4.0.1",
            "format": ["json"],
            "rest": [{
                "mode": "server",
                "resource": resources
            }]
        }


def create_fhir_app(service: FHIRService) -> FastAPI:
    """Create a FastAPI app with FHIR endpoints"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await service.setup()
        yield
        await service.cleanup()

    app = FastAPI(
        title=f"Healthcare POC - {service.service_name.upper()}",
        description=f"FHIR R4 compliant {service.service_name} service",
        version="1.0.0",
        lifespan=lifespan
    )

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": service.service_name}

    @app.get("/fhir/r4/metadata")
    async def capability_statement():
        return JSONResponse(
            content=service.get_capability_statement(),
            media_type="application/fhir+json"
        )

    # Generic FHIR CRUD endpoints
    @app.post("/fhir/r4/{resource_type}")
    async def create_resource(resource_type: str, request: Request):
        data = await request.json()
        result = service.create_resource(resource_type, data)
        await service.publish_event("created", result)
        return JSONResponse(
            content=result,
            status_code=201,
            media_type="application/fhir+json"
        )

    @app.get("/fhir/r4/{resource_type}/{resource_id}")
    async def read_resource(resource_type: str, resource_id: str):
        result = service.read_resource(resource_type, resource_id)
        return JSONResponse(content=result, media_type="application/fhir+json")

    @app.put("/fhir/r4/{resource_type}/{resource_id}")
    async def update_resource(resource_type: str, resource_id: str, request: Request):
        data = await request.json()
        result = service.update_resource(resource_type, resource_id, data)
        await service.publish_event("updated", result)
        return JSONResponse(content=result, media_type="application/fhir+json")

    @app.delete("/fhir/r4/{resource_type}/{resource_id}")
    async def delete_resource(resource_type: str, resource_id: str):
        service.delete_resource(resource_type, resource_id)
        return JSONResponse(content={"message": "Resource deleted"}, status_code=204)

    @app.get("/fhir/r4/{resource_type}")
    async def search_resources(
        resource_type: str,
        request: Request,
        _count: int = Query(100, alias="_count"),
        _offset: int = Query(0, alias="_offset")
    ):
        params = dict(request.query_params)
        result = service.search_resources(resource_type, params, limit=_count, offset=_offset)
        return JSONResponse(content=result, media_type="application/fhir+json")

    return app
