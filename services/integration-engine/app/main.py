"""Integration Engine - Healthcare Message Router
Routes messages between systems, similar to Mirth Connect/Rhapsody.
Handles:
- ADT events from PAS to all systems
- Lab orders from EHR to LIS
- Lab results from LIS to EHR
- Radiology orders/results
- Pharmacy orders
- Billing events
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import aio_pika
import httpx
import redis.asyncio as redis

# Service URLs
SERVICES = {
    "ehr": os.environ.get("EHR_URL", "http://localhost:8001"),
    "lis": os.environ.get("LIS_URL", "http://localhost:8002"),
    "ris": os.environ.get("RIS_URL", "http://localhost:8003"),
    "pharmacy": os.environ.get("PHARMACY_URL", "http://localhost:8005"),
    "pas": os.environ.get("PAS_URL", "http://localhost:8006"),
    "billing": os.environ.get("BILLING_URL", "http://localhost:8007"),
}

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://healthcare:healthcare123@localhost:5672/")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/6")

# Message routing rules
ROUTING_RULES = {
    "pas.*.adt.*": ["ehr", "lis", "ris", "pharmacy", "billing"],  # ADT to all
    "ehr.servicerequest.created": ["lis", "ris"],  # Orders to ancillary
    "lis.diagnosticreport.completed": ["ehr"],  # Lab results to EHR
    "ris.diagnosticreport.completed": ["ehr"],  # Rad results to EHR
    "pharmacy.medicationdispense.dispensed": ["ehr"],  # Dispense to EHR
    "billing.charge.posted": ["ehr"],  # Charges to EHR
}

# Global connections
rabbitmq_connection = None
rabbitmq_channel = None
redis_client = None
http_client = None


class MessageRouter:
    """Routes healthcare messages between systems"""

    def __init__(self):
        self.message_log: List[Dict] = []
        self.stats = {
            "messages_received": 0,
            "messages_routed": 0,
            "errors": 0
        }

    async def process_message(self, routing_key: str, message: dict):
        """Process and route a message"""
        self.stats["messages_received"] += 1

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "routing_key": routing_key,
            "message_type": message.get("type"),
            "source": message.get("source"),
            "id": message.get("id"),
            "destinations": [],
            "status": "processing"
        }

        try:
            # Find matching routing rules
            destinations = self._find_destinations(routing_key)
            log_entry["destinations"] = destinations

            # Route to each destination
            for dest in destinations:
                await self._forward_message(dest, message)
                self.stats["messages_routed"] += 1

            log_entry["status"] = "completed"

        except Exception as e:
            log_entry["status"] = "error"
            log_entry["error"] = str(e)
            self.stats["errors"] += 1

        self.message_log.append(log_entry)

        # Keep only last 1000 messages
        if len(self.message_log) > 1000:
            self.message_log = self.message_log[-1000:]

        # Store in Redis for persistence
        if redis_client:
            await redis_client.lpush("integration:messages", json.dumps(log_entry))
            await redis_client.ltrim("integration:messages", 0, 999)

    def _find_destinations(self, routing_key: str) -> List[str]:
        """Find destination systems based on routing rules"""
        destinations = set()

        for pattern, dests in ROUTING_RULES.items():
            if self._matches_pattern(routing_key, pattern):
                destinations.update(dests)

        return list(destinations)

    def _matches_pattern(self, routing_key: str, pattern: str) -> bool:
        """Check if routing key matches pattern (supports * wildcard)"""
        key_parts = routing_key.split(".")
        pattern_parts = pattern.split(".")

        if len(key_parts) != len(pattern_parts):
            return False

        for kp, pp in zip(key_parts, pattern_parts):
            if pp != "*" and kp != pp:
                return False

        return True

    async def _forward_message(self, destination: str, message: dict):
        """Forward message to destination system"""
        url = SERVICES.get(destination)
        if not url:
            return

        # For now, just log the forward - in production would POST to destination
        # In a real system, this might:
        # - Transform the message format
        # - Call destination API
        # - Handle acknowledgments
        print(f"Forwarding to {destination}: {message.get('type')}")


router = MessageRouter()


async def consume_messages():
    """Consume messages from RabbitMQ"""
    global rabbitmq_connection, rabbitmq_channel

    try:
        rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
        rabbitmq_channel = await rabbitmq_connection.channel()

        # Declare exchange
        exchange = await rabbitmq_channel.declare_exchange(
            "healthcare.events",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )

        # Create queue for integration engine
        queue = await rabbitmq_channel.declare_queue(
            "integration.engine",
            durable=True
        )

        # Bind to all healthcare events
        await queue.bind(exchange, routing_key="#")

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    body = json.loads(message.body.decode())
                    await router.process_message(message.routing_key, body)
                except Exception as e:
                    print(f"Error processing message: {e}")

        await queue.consume(on_message)
        print("Integration engine consuming messages...")

    except Exception as e:
        print(f"RabbitMQ connection error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, http_client

    # Initialize Redis
    try:
        redis_client = redis.from_url(REDIS_URL)
    except Exception as e:
        print(f"Redis connection error: {e}")

    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)

    # Start message consumer
    asyncio.create_task(consume_messages())

    yield

    # Cleanup
    if rabbitmq_connection:
        await rabbitmq_connection.close()
    if redis_client:
        await redis_client.close()
    if http_client:
        await http_client.aclose()


app = FastAPI(
    title="Healthcare POC - Integration Engine",
    description="Message routing and integration service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "integration-engine",
        "rabbitmq": "connected" if rabbitmq_connection else "disconnected",
        "redis": "connected" if redis_client else "disconnected"
    }


@app.get("/stats")
async def get_stats():
    """Get integration engine statistics"""
    return {
        "stats": router.stats,
        "routing_rules": len(ROUTING_RULES),
        "connected_services": list(SERVICES.keys())
    }


@app.get("/messages")
async def get_messages(limit: int = 100):
    """Get recent message log"""
    return {
        "messages": router.message_log[-limit:],
        "total": len(router.message_log)
    }


@app.get("/messages/{message_id}")
async def get_message(message_id: str):
    """Get specific message by ID"""
    for msg in router.message_log:
        if msg.get("id") == message_id:
            return msg
    raise HTTPException(status_code=404, detail="Message not found")


@app.post("/route")
async def manual_route(message: dict):
    """Manually route a message (for testing)"""
    routing_key = message.get("routing_key", "manual.test.message")
    await router.process_message(routing_key, message)
    return {"status": "routed", "routing_key": routing_key}


@app.get("/rules")
async def get_rules():
    """Get routing rules"""
    return {"rules": ROUTING_RULES}


@app.post("/rules")
async def add_rule(pattern: str, destinations: List[str]):
    """Add a routing rule"""
    ROUTING_RULES[pattern] = destinations
    return {"status": "added", "pattern": pattern, "destinations": destinations}


@app.get("/services")
async def get_services():
    """Get connected service URLs"""
    return {"services": SERVICES}


@app.get("/services/{service_name}/health")
async def check_service_health(service_name: str):
    """Check health of a connected service"""
    url = SERVICES.get(service_name)
    if not url:
        raise HTTPException(status_code=404, detail="Service not found")

    try:
        response = await http_client.get(f"{url}/health", timeout=5.0)
        return {"service": service_name, "status": "healthy", "response": response.json()}
    except Exception as e:
        return {"service": service_name, "status": "unhealthy", "error": str(e)}
