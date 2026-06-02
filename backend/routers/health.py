from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from core.database import get_chroma_client, get_neo4j_driver

router = APIRouter(prefix="/api", tags=["health"])


class ServiceStatus(BaseModel):
    status: str
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: dict[str, ServiceStatus]


@router.get("/health", response_model=HealthResponse)
def health_check():
    import time

    services = {}

    # Neo4j
    t0 = time.perf_counter()
    driver = get_neo4j_driver()
    neo4j_latency = (time.perf_counter() - t0) * 1000
    if driver:
        services["neo4j"] = ServiceStatus(status="ok", latency_ms=round(neo4j_latency, 1))
    else:
        services["neo4j"] = ServiceStatus(status="unavailable", error="Connection failed")

    # ChromaDB
    t0 = time.perf_counter()
    chroma = get_chroma_client()
    chroma_latency = (time.perf_counter() - t0) * 1000
    if chroma:
        services["chromadb"] = ServiceStatus(status="ok", latency_ms=round(chroma_latency, 1))
    else:
        services["chromadb"] = ServiceStatus(status="unavailable", error="Connection failed")

    overall = "ok" if all(s.status == "ok" for s in services.values()) else "degraded"

    return HealthResponse(
        status=overall,
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="1.0.0",
        services=services,
    )
